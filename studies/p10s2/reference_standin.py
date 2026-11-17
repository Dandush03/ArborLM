# ruff: noqa: E501
"""An independently written stand-in for the reference implementation of the student (tests and the dry stage only).

It follows the Hugging Face ``LlamaForCausalLM`` structure and parameter names (``model.layers.N.self_attn.q_proj.weight`` ...) with explicit per-head loops and its own rotary code, and shares no code with
``model.Student``. The real reference (``transformers`` on the pinned weights) is used only in the data-generation step. This stand-in lets ``equivalence`` be exercised, including that it catches a wrong
injection index and a perturbed weight.
"""

import math
from collections.abc import Mapping

import torch

from .model import StudentConfig


class ReferenceLlama:
    def __init__(self, cfg: StudentConfig, sd: Mapping[str, torch.Tensor]) -> None:
        self.cfg = cfg
        self.sd = {k: v.detach().clone().to(torch.float64) for k, v in sd.items()}

    def _rms(self, x: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
        return w * x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.cfg.rms_norm_eps)

    def _rotary(self, x: torch.Tensor, pos: int) -> torch.Tensor:
        hd = self.cfg.head_dim
        out = x.clone()
        for i in range(hd // 2):
            theta = pos * self.cfg.rope_base ** (-2.0 * i / hd)
            c, s = math.cos(theta), math.sin(theta)
            a, b = x[i].clone(), x[i + hd // 2].clone()
            out[i] = a * c - b * s
            out[i + hd // 2] = b * c + a * s
        return out

    def _hidden(self, ids: torch.Tensor, inject: tuple[int, torch.Tensor] | None) -> torch.Tensor:
        cfg, sd = self.cfg, self.sd
        t = ids.shape[1]
        hd = cfg.head_dim
        rep = cfg.heads // cfg.kv_heads
        x = sd["model.embed_tokens.weight"][ids[0]]  # (t, d)
        for layer in range(cfg.layers):
            p = f"model.layers.{layer}."
            h = self._rms(x, sd[p + "input_layernorm.weight"])
            q, k, v = h @ sd[p + "self_attn.q_proj.weight"].T, h @ sd[p + "self_attn.k_proj.weight"].T, h @ sd[p + "self_attn.v_proj.weight"].T
            attn_out = torch.zeros(t, cfg.width, dtype=torch.float64)
            for head in range(cfg.heads):
                kv = head // rep
                qh = torch.stack([self._rotary(q[i, head * hd : (head + 1) * hd], i) for i in range(t)])
                kh = torch.stack([self._rotary(k[i, kv * hd : (kv + 1) * hd], i) for i in range(t)])
                vh = v[:, kv * hd : (kv + 1) * hd]
                for i in range(t):
                    sc = torch.stack([qh[i] @ kh[j] / math.sqrt(hd) for j in range(i + 1)])
                    w = torch.softmax(sc, dim=0)
                    attn_out[i, head * hd : (head + 1) * hd] = sum(w[j] * vh[j] for j in range(i + 1))
            x = x + attn_out @ sd[p + "self_attn.o_proj.weight"].T
            h2 = self._rms(x, sd[p + "post_attention_layernorm.weight"])
            gate = h2 @ sd[p + "mlp.gate_proj.weight"].T
            up = h2 @ sd[p + "mlp.up_proj.weight"].T
            x = x + (gate * torch.sigmoid(gate) * up) @ sd[p + "mlp.down_proj.weight"].T
            # hidden_states[layer + 1] in Hugging Face terms: the output of block ``layer`` (0-based)
            if inject is not None and inject[0] == layer:
                x = x + inject[1].to(torch.float64)
        return self._rms(x, sd["model.norm.weight"])

    def logits(self, ids: torch.Tensor) -> torch.Tensor:
        return (self._hidden(ids, None) @ self.sd["model.embed_tokens.weight"].T).to(torch.float32)[None]

    def logits_with_injection(self, ids: torch.Tensor, layer: int, vec: torch.Tensor) -> torch.Tensor:
        return (self._hidden(ids, (layer, vec)) @ self.sd["model.embed_tokens.weight"].T).to(torch.float32)[None]

    def generate(self, ids: torch.Tensor, max_new: int) -> list[int]:
        cur = ids.clone()
        out: list[int] = []
        for _ in range(max_new):
            nxt = int(torch.argmax(self.logits(cur)[0, -1]).item())
            out.append(nxt)
            cur = torch.cat([cur, torch.tensor([[nxt]])], dim=1)
        return out
