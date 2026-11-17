# ruff: noqa: E501
"""The student: a plain Llama-style decoder in torch (ADR-0022 section 2), with the injection point of the memory and the LoRA hooks.

Interface (the same for the real SmolLM2-135M configuration and for the tiny stand-in used in tests and the dry stage):

* ``forward(ids, add=None, adapter=None, cache=None, hidden_at=None)``: logits for ``ids`` (batch, time). ``add`` (batch, time, width) is added to the **output of block L** (0-based
  block index; in Hugging Face terms ``hidden_states[L + 1]``, the off-by-one the equivalence test (d) of section 14.2 pins). ``adapter`` is a LoRA adapter applied to the query and value
  projections of every block. ``cache`` holds keys and values for incremental decoding. ``hidden_at=L`` makes the call stop after block L and return its output (the router's
  memory-free hidden state), without computing the later blocks.
* Weights are plain tensors; no module uses ``torch.nn`` default initialization (that would draw from the global generator). ``init_random`` fills them from a seeded generator.
* The student is never trained in any arm; ``requires_grad`` is False for every student parameter.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from . import core


@dataclass(frozen=True)
class StudentConfig:
    vocab: int
    width: int
    layers: int
    heads: int
    kv_heads: int
    intermediate: int
    max_positions: int
    rope_base: float
    rms_norm_eps: float

    @property
    def head_dim(self) -> int:
        return self.width // self.heads

    @staticmethod
    def from_hf_config(hf: "dict[str, Any]") -> "StudentConfig":
        """The configuration from the model's own ``config.json`` (a parsed dict). The shape values must equal the ADR's pinned ones (section 2); ``rms_norm_eps`` is not in the ADR and is read from the file,
        never assumed (the equivalence record stores it and gate G8 checks it)."""
        s = core.CFG["student"]
        got = {"vocab": hf["vocab_size"], "width": hf["hidden_size"], "layers": hf["num_hidden_layers"], "heads": hf["num_attention_heads"], "kv_heads": hf["num_key_value_heads"], "intermediate": hf["intermediate_size"], "max_positions": hf["max_position_embeddings"], "rope_base": float(hf["rope_theta"])}
        for k, v in got.items():
            if v != s[k]:
                raise ValueError(f"the model's config.json has {k} = {v}, not the pinned {s[k]} (ADR-0022 section 2)")
        return StudentConfig(got["vocab"], got["width"], got["layers"], got["heads"], got["kv_heads"], got["intermediate"], got["max_positions"], got["rope_base"], float(hf["rms_norm_eps"]))

    @staticmethod
    def tiny(vocab: int, width: int = 32, layers: int = 3, heads: int = 4, kv_heads: int = 2, intermediate: int = 64, max_positions: int = 512) -> "StudentConfig":
        return StudentConfig(vocab, width, layers, heads, kv_heads, intermediate, max_positions, 10000.0, 1e-5)


def student_parameter_count(cfg: StudentConfig) -> int:
    """Arithmetic count (tied embeddings): embedding, per block four attention matrices, three MLP matrices and two norms, the final norm."""
    d, hd = cfg.width, cfg.head_dim
    attn = d * d + 2 * d * (cfg.kv_heads * hd) + d * d
    mlp = 3 * d * cfg.intermediate
    return cfg.vocab * d + cfg.layers * (attn + mlp + 2 * d) + d


def lora_parameter_count(cfg: StudentConfig, rank: int) -> int:
    """LoRA on the query (width -> width) and value (width -> kv_heads * head_dim) projections of every block: rank * (in + out) per matrix."""
    q = rank * (cfg.width + cfg.width)
    v = rank * (cfg.width + cfg.kv_heads * cfg.head_dim)
    return cfg.layers * (q + v)


def store_parameter_count(cfg: StudentConfig, rows: int) -> int:
    """Per stage: rows * (key width + width) + one gate."""
    return rows * (core.KEY_WIDTH + cfg.width) + 1


class Lin(nn.Module):
    """A bias-free linear map whose weight is an uninitialized parameter (filled by ``init_random`` or loaded), so building a module never touches the global generator."""

    def __init__(self, n_in: int, n_out: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_out, n_in), requires_grad=False)

    def forward(self, x: Tensor) -> Tensor:
        return F.linear(x, self.weight)


class RMSNorm(nn.Module):
    def __init__(self, width: int, eps: float) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width), requires_grad=False)
        self.eps = eps

    def forward(self, x: Tensor) -> Tensor:
        xf = x.float()
        return (xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + self.eps)).to(x.dtype) * self.weight


def _rotate_half(x: Tensor) -> Tensor:
    h = x.shape[-1] // 2
    return torch.cat([-x[..., h:], x[..., :h]], dim=-1)


class Block(nn.Module):
    def __init__(self, cfg: StudentConfig) -> None:
        super().__init__()
        d, hd = cfg.width, cfg.head_dim
        self.cfg = cfg
        self.q_proj, self.k_proj = Lin(d, d), Lin(d, cfg.kv_heads * hd)
        self.v_proj, self.o_proj = Lin(d, cfg.kv_heads * hd), Lin(d, d)
        self.gate_proj, self.up_proj, self.down_proj = Lin(d, cfg.intermediate), Lin(d, cfg.intermediate), Lin(cfg.intermediate, d)
        self.input_norm, self.post_norm = RMSNorm(d, cfg.rms_norm_eps), RMSNorm(d, cfg.rms_norm_eps)

    def forward(self, x: Tensor, cos: Tensor, sin: Tensor, index: int, adapter: "LoRAAdapter | PositionAdapter | None", kv: tuple[Tensor, Tensor] | None) -> tuple[Tensor, tuple[Tensor, Tensor]]:
        cfg = self.cfg
        b, t, _ = x.shape
        h = self.input_norm(x)
        q, k, v = self.q_proj(h), self.k_proj(h), self.v_proj(h)
        if adapter is not None:
            q = q + adapter.delta(index, "q", h)
            v = v + adapter.delta(index, "v", h)
        hd = cfg.head_dim
        q = q.view(b, t, cfg.heads, hd).transpose(1, 2)
        k = k.view(b, t, cfg.kv_heads, hd).transpose(1, 2)
        v = v.view(b, t, cfg.kv_heads, hd).transpose(1, 2)
        q = q * cos + _rotate_half(q) * sin
        k = k * cos + _rotate_half(k) * sin
        if kv is not None:
            k, v = torch.cat([kv[0], k], dim=2), torch.cat([kv[1], v], dim=2)
        rep = cfg.heads // cfg.kv_heads
        ks, vs = k.repeat_interleave(rep, dim=1), v.repeat_interleave(rep, dim=1)
        scores = (q @ ks.transpose(-1, -2)) / math.sqrt(hd)
        total = ks.shape[2]
        mask = torch.ones(t, total, dtype=torch.bool, device=x.device).tril(diagonal=total - t)
        scores = scores.masked_fill(~mask, float("-inf"))
        a = torch.softmax(scores.float(), dim=-1).to(x.dtype) @ vs
        x = x + self.o_proj(a.transpose(1, 2).reshape(b, t, cfg.width))
        h2 = self.post_norm(x)
        x = x + self.down_proj(F.silu(self.gate_proj(h2)) * self.up_proj(h2))
        return x, (k, v)


class Cache:
    """Keys and values per block for incremental decoding."""

    def __init__(self) -> None:
        self.kv: list[tuple[Tensor, Tensor] | None] = []
        self.length = 0


class Student(nn.Module):
    def __init__(self, cfg: StudentConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Parameter(torch.empty(cfg.vocab, cfg.width), requires_grad=False)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.layers))
        self.final_norm = RMSNorm(cfg.width, cfg.rms_norm_eps)
        self.read_layer: int | None = None  # the block whose output receives ``add``

    # -- initialization and weights --------------------------------------------------------------------------------------------------------
    def init_random(self, generator: torch.Generator, std: float = 0.05) -> None:
        """Fill every weight from a seeded generator (stand-in student only; the real weights are loaded)."""
        with torch.no_grad():
            for name, p in sorted(self.named_parameters()):
                if name.endswith("norm.weight"):
                    p.copy_(1.0 + 0.1 * torch.randn(p.shape, generator=generator))
                else:
                    p.copy_(std * torch.randn(p.shape, generator=generator))

    def freeze(self) -> None:
        for p in self.parameters():
            p.requires_grad_(False)

    def tensor_hashes(self) -> dict[str, str]:
        """SHA-256 of every parameter's float32 bytes (gate G5: the backbone's tensor hashes equal the frozen ones after training)."""
        return {n: tensor_sha(p) for n, p in sorted(self.named_parameters())}

    def _rope(self, positions: Tensor, dtype: torch.dtype) -> tuple[Tensor, Tensor]:
        hd = self.cfg.head_dim
        inv = 1.0 / (self.cfg.rope_base ** (torch.arange(0, hd, 2, dtype=torch.float32, device=positions.device) / hd))
        freqs = positions.float()[:, None] * inv[None, :]
        emb = torch.cat([freqs, freqs], dim=-1)
        return emb.cos().to(dtype)[None, None], emb.sin().to(dtype)[None, None]

    # -- forward ---------------------------------------------------------------------------------------------------------------------------
    def forward(
        self,
        ids: Tensor,
        add: Tensor | None = None,
        adapter: "LoRAAdapter | PositionAdapter | None" = None,
        cache: Cache | None = None,
        hidden_at: int | None = None,
    ) -> Tensor:
        cfg = self.cfg
        b, t = ids.shape
        start = cache.length if cache is not None else 0
        if start + t > cfg.max_positions:
            raise ValueError("sequence longer than the model's positions")
        x: Tensor = self.embed[ids]
        positions = torch.arange(start, start + t, device=ids.device)
        cos, sin = self._rope(positions, x.dtype)
        if cache is not None and not cache.kv:
            cache.kv = [None] * cfg.layers
        if isinstance(adapter, PositionAdapter):
            adapter.set_span(start, t)  # a position-wise adapter needs the absolute positions of this call
        for i, blk in enumerate(self.blocks):
            kv = cache.kv[i] if cache is not None else None
            x, new_kv = blk(x, cos, sin, i, adapter, kv)
            if cache is not None:
                cache.kv[i] = new_kv
            if add is not None and self.read_layer == i:
                x = x + add
            if hidden_at is not None and i == hidden_at:
                if cache is not None:
                    cache.length += t
                return x
        if cache is not None:
            cache.length += t
        logits: Tensor = self.final_norm(x) @ self.embed.t()
        return logits

    def block_output(self, ids: Tensor, layer: int) -> Tensor:
        """The output of block ``layer`` (0-based) of a memory-free, adapter-free pass: the router's hidden state."""
        return self.forward(ids, hidden_at=layer)

    @torch.no_grad()
    def greedy_cached(self, prompt: Tensor, *, add: Tensor | None, adapter: "LoRAAdapter | PositionAdapter | None", max_new: int, stop_bytes: list[bytes] | None, cache: Cache | None = None) -> tuple[list[int], Cache]:
        """Greedy decoding with a key-value cache. ``prompt`` (1, T) is read with ``add``; with ``cache`` given it is the *continuation* of the sequence the cache holds (step 2 of a combined task).
        Returns the generated ids (the stop token, the first whose bytes contain 0x0A, is kept; otherwise ``max_new`` tokens) and the cache. The last generated token is not fed through the model."""
        cache = cache if cache is not None else Cache()
        out: list[int] = []
        logits = self.forward(prompt, add=add, adapter=adapter, cache=cache)
        for _ in range(max_new):
            nxt = int(torch.argmax(logits[0, -1]).item())
            out.append(nxt)
            if stop_bytes is not None and b"\n" in stop_bytes[nxt]:
                break
            if len(out) == max_new:
                break  # the last generated token is not fed (a continuation feeds it first)
            logits = self.forward(torch.tensor([[nxt]], device=prompt.device), adapter=adapter, cache=cache)
        return out, cache

    @torch.no_grad()
    def greedy(self, prompt: Tensor, *, add: Tensor | None, adapter: "LoRAAdapter | PositionAdapter | None", max_new: int, stop_bytes: list[bytes] | None, use_cache: bool = True) -> list[int]:
        """Greedy decoding of one prompt (1, T). The prompt is read with ``add``; generated positions are never read. Stops at the first token whose bytes contain 0x0A (when
        ``stop_bytes`` is given), which is kept in the output; otherwise after ``max_new`` tokens. With ``use_cache`` False every step recomputes the whole sequence (check (e))."""
        if use_cache:
            return self.greedy_cached(prompt, add=add, adapter=adapter, max_new=max_new, stop_bytes=stop_bytes)[0]
        out: list[int] = []
        ids = prompt
        for _ in range(max_new):
            padded = add if add is None or add.shape[1] == ids.shape[1] else torch.cat([add, torch.zeros(add.shape[0], ids.shape[1] - add.shape[1], add.shape[2], dtype=add.dtype, device=add.device)], dim=1)  # generated positions are never read
            logits = self.forward(ids, add=padded, adapter=adapter)
            nxt = int(torch.argmax(logits[0, -1]).item())
            out.append(nxt)
            if stop_bytes is not None and b"\n" in stop_bytes[nxt]:
                break
            ids = torch.cat([ids, torch.tensor([[nxt]], device=prompt.device)], dim=1)
        return out


def tensor_sha(p: Tensor) -> str:
    from arborlm.io import sha256

    return sha256(bytes(p.detach().cpu().to(torch.float32).clone(memory_format=torch.contiguous_format).untyped_storage()))


# --- LoRA (section 7) ------------------------------------------------------------------------------------------------------------------------
class LoRAAdapter(nn.Module):
    """LoRA on the query and value projections of all blocks. ``(alpha / r) * B A`` with alpha = r (a scale of 1); A uniform on +-1/sqrt(fan-in) from a seeded generator (``None``: zeros, for loading a stored state), B zero (an
    untrained adapter changes nothing), no dropout. The draws go block by block, query A then value A."""

    def __init__(self, cfg: StudentConfig, rank: int, generator: torch.Generator | None) -> None:
        super().__init__()
        self.rank = rank
        self.scale = 1.0  # alpha / rank with alpha = rank
        self.a = nn.ParameterList()
        self.b = nn.ParameterList()
        out_q, out_v = cfg.width, cfg.kv_heads * cfg.head_dim
        bound = 1.0 / math.sqrt(cfg.width)
        for _ in range(cfg.layers):
            for out in (out_q, out_v):
                self.a.append(nn.Parameter(torch.zeros(rank, cfg.width) if generator is None else (torch.rand(rank, cfg.width, generator=generator) * 2 - 1) * bound))
                self.b.append(nn.Parameter(torch.zeros(out, rank)))

    def delta(self, block: int, which: str, h: Tensor) -> Tensor:
        k = 2 * block + (0 if which == "q" else 1)
        out: Tensor = (h @ self.a[k].t()) @ self.b[k].t() * self.scale
        return out


class PositionAdapter:
    """L-sep on C1 and C2 (combined-tasks addendum section 7): the LoRA update used at a position is that of the task owning it. ``owner(i)`` gives the task of absolute position ``i``; the span
    of each forward call is set by the student. No parameter of its own."""

    def __init__(self, adapters: "dict[str, LoRAAdapter]", owner: "Callable[[int], str]") -> None:
        self.adapters, self.owner = adapters, owner
        self.start, self.length = 0, 0

    def set_span(self, start: int, length: int) -> None:
        self.start, self.length = start, length

    def delta(self, block: int, which: str, h: Tensor) -> Tensor:
        owners = [self.owner(self.start + i) for i in range(self.length)]
        res: Tensor | None = None
        for task, ad in self.adapters.items():
            d = ad.delta(block, which, h)
            mask = torch.tensor([o == task for o in owners], device=h.device)[None, :, None]
            piece = torch.where(mask, d, torch.zeros_like(d))  # an unowned position adds exactly zero, so an owned one equals that adapter's own update bit for bit
            res = piece if res is None else res + piece
        assert res is not None
        return res


# --- weights: conversion from the Hugging Face Llama naming (pure torch) ---------------------------------------------------------------------------
HF_BLOCK = {
    "self_attn.q_proj.weight": "q_proj.weight", "self_attn.k_proj.weight": "k_proj.weight", "self_attn.v_proj.weight": "v_proj.weight", "self_attn.o_proj.weight": "o_proj.weight",
    "mlp.gate_proj.weight": "gate_proj.weight", "mlp.up_proj.weight": "up_proj.weight", "mlp.down_proj.weight": "down_proj.weight",
    "input_layernorm.weight": "input_norm.weight", "post_attention_layernorm.weight": "post_norm.weight",
}  # fmt: skip


def convert_hf_state_dict(sd: Mapping[str, Tensor], cfg: StudentConfig) -> dict[str, Tensor]:
    """Rename a Hugging Face ``LlamaForCausalLM`` state dict to this module's names (tied embeddings: ``lm_head.weight`` is ignored if present). Rotary buffers are ignored."""
    out: dict[str, Tensor] = {"embed": sd["model.embed_tokens.weight"].to(torch.float32), "final_norm.weight": sd["model.norm.weight"].to(torch.float32)}
    for i in range(cfg.layers):
        for hf, mine in HF_BLOCK.items():
            out[f"blocks.{i}.{mine}"] = sd[f"model.layers.{i}.{hf}"].to(torch.float32)
    return out


def export_hf_state_dict(model: Student) -> dict[str, Tensor]:
    """The inverse of ``convert_hf_state_dict`` (used by the round-trip test on the stand-in)."""
    inv = {v: k for k, v in HF_BLOCK.items()}
    out: dict[str, Tensor] = {"model.embed_tokens.weight": model.embed.detach().clone(), "model.norm.weight": model.final_norm.weight.detach().clone()}
    for i in range(model.cfg.layers):
        for mine, hf in inv.items():
            mod, leaf = mine.rsplit(".", 1)
            out[f"model.layers.{i}.{hf}"] = getattr(model.blocks[i], mod).weight.detach().clone() if leaf == "weight" else model.blocks[i].state_dict()[mine]
    return out


def load_plain_state(model: Student, state: Mapping[str, Tensor]) -> None:
    """Load a converted state dict strictly (same names, same shapes)."""
    own = dict(model.named_parameters())
    if set(own) != set(state):
        raise ValueError(f"state dict names differ: missing {sorted(set(own) - set(state))[:3]}, unexpected {sorted(set(state) - set(own))[:3]}")
    with torch.no_grad():
        for n, p in own.items():
            if p.shape != state[n].shape:
                raise ValueError(f"shape mismatch for {n}")
            p.copy_(state[n])


def build_student(cfg: StudentConfig, generator: torch.Generator | None = None, std: float = 0.05) -> Student:
    """A student on CPU. With a generator the weights are random (stand-in); without one they are uninitialized until ``load_plain_state``."""
    m = Student(cfg)
    if generator is not None:
        m.init_random(generator, std)
    m.freeze()
    return m
