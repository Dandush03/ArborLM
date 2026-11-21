# ruff: noqa: E501
"""P10IS3 arms, reads, interventions, streams, training and evaluation (ADR-0026 sections 3 and 16 rulings 1, 2, 3, 7, 8, 12).

Existing classes are imported unmodified (``pilot_model.Memory`` / ``stable_top`` / ``tree_candidates``, ``p4_model.DenseAdapter`` / ``Backbone``). Interventions never mutate a model: they are overrides of the read (a values
tensor, a keys tensor, a seeded query permutation, a batch-mean read, a changed visit count). Reads and evaluations run under ``torch.no_grad()``.
Self-check only.
"""

import hashlib
import math
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch.optim import AdamW

from arborlm.engine import optimizer_for as adamw_for
from arborlm.io import canonical_json, read_json, sha256, write_json
from arborlm.longer_training import _isolated_rng
from arborlm.p4_model import Backbone, DenseAdapter
from arborlm.pilot_metrics import loss_for
from arborlm.pilot_model import (
    BRANCHES,
    CONTEXT,
    EPS,
    PER_BRANCH,
    SLOTS,
    TEMP,
    TOP,
    VOCAB,
    Lookup,
    Memory,
    stable_top,
    tree_candidates,
)

from . import core
from .core import DENSE, FLAT, TREE, FailedCell

PANEL_BATCH = 8


# --- the read -----------------------------------------------------------------------------------------------------------
@dataclass
class Ctl:
    """One intervention (``kind``) of the read, applied to every batch of one evaluation."""

    kind: str | None = None  # None | "values" (P_all, P_used, NEG-REF) | "joint" | "X" | "X_mean" | "exhaustive" | "prior_off"
    values: Tensor | None = None
    keys: Tensor | None = None
    gen: torch.Generator | None = None
    visit: int = 2
    use_prior: bool = True
    collect: dict[str, Any] | None = None


class Collector:
    """Used slots (the set S, ruling of section 3.4), usage weights (NEG-REF), branch use, and the batch starts that prove panel order."""

    def __init__(self) -> None:
        self.selected: set[int] = set()
        self.usage = torch.zeros(SLOTS, dtype=torch.float64)
        self.branches = torch.zeros(BRANCHES, dtype=torch.float64)
        self.batches = 0

    def add(self, weights: Tensor, lookup: Lookup) -> None:
        sel = lookup.selected.reshape(-1)
        self.selected.update(int(x) for x in torch.unique(sel).tolist())
        self.usage.index_add_(0, sel, weights.reshape(-1).double())
        if lookup.branch_ids is not None:
            self.branches.index_add_(0, lookup.branch_ids.reshape(-1), torch.ones(lookup.branch_ids.numel(), dtype=torch.float64))

    def entropy(self) -> float | None:
        tot = float(self.branches.sum())
        if tot <= 0:
            return None
        p = self.branches[self.branches > 0] / tot
        return float(-(p * p.log()).sum())


def memory_read(mem: Memory, h: Tensor, ctl: Ctl | None, collector: Collector | None = None) -> tuple[Tensor, Lookup]:
    """``Memory.forward`` with the study's overrides. With ``ctl`` None or kind None it is bitwise equal to ``Memory.forward`` (the read-equality gate)."""
    ctl = ctl or Ctl()
    q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
    keys = ctl.keys if ctl.keys is not None else mem.keys
    values = ctl.values if ctl.values is not None else mem.values
    if ctl.kind == "X":
        assert ctl.gen is not None
        sigma = torch.randperm(q.shape[0], generator=ctl.gen, device="cpu")
        q_use = q.clone()
        q_use[sigma] = q[sigma.roll(-1)]
        q = q_use
    if mem.variant == "flat":
        scores = (q @ F.normalize(keys, dim=-1, eps=EPS).T) / TEMP
        weights, selected = stable_top(scores, TOP)
        lookup = Lookup(selected, None)
    else:
        routes = (q @ F.normalize(mem.router, dim=-1, eps=EPS).T) / TEMP
        visit = ctl.visit if ctl.kind in ("exhaustive", "prior_off") else 2
        use_prior = ctl.use_prior if ctl.kind in ("exhaustive", "prior_off") else True
        weights, selected, candidates, branches = tree_candidates(q, keys, routes, visit=visit, use_prior=use_prior)
        lookup = Lookup(selected, candidates, branch_ids=branches, route_scores=routes)
    soft = weights.softmax(-1)
    if collector is not None:
        collector.add(soft, lookup)
    combined = (soft[..., None] * values[lookup.selected]).sum(dim=-2)
    if ctl.kind == "X_mean":
        c3 = combined.reshape(h.shape)
        combined = c3.mean(dim=(0, 1), keepdim=True).expand_as(c3).reshape(combined.shape)
    return h + mem.gate.sigmoid() * F.linear(combined.reshape(h.shape), mem.wo), lookup


def dense_read(ad: DenseAdapter, h: Tensor, ctl: Ctl | None) -> Tensor:
    """``DenseAdapter.forward`` with the like-for-like controls of ruling 7: X_dense moves the delta (computed from h of sigma[t+1]) onto position sigma[t], the residual stays; X_mean_dense replaces the delta by its batch mean."""
    kind = ctl.kind if ctl else None
    if kind is None:
        return ad(h)[0]
    delta = ad.gate.sigmoid() * F.linear(F.gelu(F.linear(h, ad.w1), approximate="none"), ad.w2)
    if kind == "X":
        assert ctl is not None and ctl.gen is not None
        flat = delta.reshape(-1, delta.shape[-1])
        sigma = torch.randperm(flat.shape[0], generator=ctl.gen, device="cpu")
        use = flat.clone()
        use[sigma] = flat[sigma.roll(-1)]
        delta = use.reshape(h.shape)
    elif kind == "X_mean":
        delta = delta.mean(dim=(0, 1), keepdim=True).expand_as(delta)
    else:
        raise ValueError(f"no dense control {kind!r}")
    return h + delta


class S3Model(nn.Module):
    """Frozen backbone plus one addition. ``bypass`` is the memory-disabled control."""

    def __init__(self, backbone: Any, arm: str, init_seed: int | None) -> None:
        super().__init__()
        self.backbone = backbone
        self.arm = arm
        self.addition: Memory | DenseAdapter | None
        if arm == TREE:
            self.addition = Memory("learned_tree", init_seed or 0)
        elif arm == FLAT:
            self.addition = Memory("flat", init_seed or 0)
        elif arm == DENSE:
            self.addition = DenseAdapter(init_seed or 0)
        elif arm == core.BASE:
            self.addition = None
        else:
            raise ValueError(f"unknown arm {arm!r}")
        self.bypass = arm == core.BASE

    def forward(self, tokens: Tensor, ctl: Ctl | None = None, collector: Collector | None = None) -> tuple[Tensor, Lookup | None]:
        if tokens.ndim != 2 or tokens.shape[0] == 0 or not 1 <= tokens.shape[1] <= CONTEXT or tokens.dtype != torch.int64 or tokens.device.type != "cpu":
            raise ValueError("expected nonempty CPU int64 [B,T] with 1 <= T <= 64")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("expected byte token IDs")
        b = self.backbone
        t = tokens.shape[1]
        h = b.token(tokens) + b.position(torch.arange(t, device="cpu"))
        h = b.blocks[0](h, b.mask[:t, :t])
        lookup = None
        if self.addition is not None and not self.bypass:
            if isinstance(self.addition, Memory):
                h, lookup = memory_read(self.addition, h, ctl, collector)
            else:
                h = dense_read(self.addition, h, ctl)
        h = b.blocks[1](h, b.mask[:t, :t])
        return F.linear(b.final_norm(h), b.token.weight), lookup

    def trainable(self) -> list[nn.Parameter]:
        return [p for p in self.addition.parameters()] if self.addition is not None else []


def build_model(backbone: Backbone, arm: str, init_seed: int) -> S3Model:
    """P4's seeding: the global RNGs are set from the cell seed before the addition is built (the components use their own generators)."""
    random.seed(init_seed)
    torch.default_generator.manual_seed(init_seed)
    model = S3Model(backbone, arm, init_seed)
    random.seed(init_seed)
    torch.default_generator.manual_seed(init_seed)
    model.backbone.requires_grad_(False)
    return model


def trainable_count(model: S3Model) -> int:
    return sum(p.numel() for p in model.trainable())


# --- evaluation (ruling 1: one arithmetic path) ---------------------------------------------------------------------------------
def evaluate(model: S3Model, data: Tensor, ctl: Ctl | None = None, *, collector: Collector | None = None, expected_targets: int = 32768, nonfinite: str = "raise") -> float:
    """Per-batch ``loss_for(..., "sum")`` in float32, accumulated as a Python float, divided by the target count (as ``p4_model.evaluate``). Interventions that give a non-finite value return it with ``nonfinite="value"``;
    the enabled reference raises ``FailedCell`` instead (section 6.1)."""
    was_training = model.training
    model.eval()
    total, count = 0.0, 0
    try:
        with _isolated_rng(), torch.no_grad():
            for start in range(0, data.shape[0], PANEL_BATCH):
                if collector is not None:
                    assert start == collector.batches * PANEL_BATCH, "the used-slot set must be collected in panel order"  # an item error, not a failed cell (section 10)
                    collector.batches += 1
                batch = data[start : start + PANEL_BATCH]
                logits, _ = model(batch[:, :-1], ctl, collector)
                total += float(loss_for(logits, batch[:, 1:], "sum"))
                count += batch[:, 1:].numel()
    finally:
        model.train(was_training)
    if count != expected_targets or count <= 0:
        raise ValueError("wrong evaluation target count")
    value = total / count
    if not math.isfinite(value) and nonfinite == "raise":
        raise FailedCell("non-finite evaluation NLL")
    return value


def seeded(seed: int) -> torch.Generator:
    return torch.Generator(device="cpu").manual_seed(seed)


def p_all_values(values: Tensor, seed: int) -> Tensor:
    """One permutation of all 4,096 value rows (P4's control, with this study's seed): slot i receives the value of slot ids[i]."""
    ids = torch.randperm(values.shape[0], generator=seeded(seed), device="cpu")
    return values[ids]


def p_used_values(values: Tensor, used: Sequence[int], seed: int) -> Tensor | None:
    """S sorted by slot id; sigma = S in a seeded random order; slot sigma[t] receives the value of slot sigma[t+1 mod |S|]. None if fewer than two slots are used (COLLAPSED)."""
    s = torch.tensor(sorted(used), dtype=torch.int64)
    if s.numel() < 2:
        return None
    sigma = s[torch.randperm(s.numel(), generator=seeded(seed), device="cpu")]
    out = values.clone()
    out[sigma] = values[sigma.roll(-1)]
    return out


def joint_permutation(keys: Tensor, values: Tensor, seed: int) -> tuple[Tensor, Tensor]:
    """ADR-0009's construction with this study's joint seed (P4's helper is not called): one seeded randperm(256) per branch, branches in order, applied to keys and values together."""
    gen = seeded(seed)
    ids = torch.cat([b * PER_BRANCH + torch.randperm(PER_BRANCH, generator=gen, device="cpu") for b in range(BRANCHES)])
    return keys[ids], values[ids]


def neg_ref_values(values: Tensor, usage: Tensor) -> Tensor:
    """Every value row replaced by the usage-weighted mean value (the read is the same for every address by construction)."""
    w = usage.to(values.dtype)
    mean = (w[:, None] * values).sum(0) / w.sum()
    return mean.expand_as(values).clone()


def evaluate_reads(model: S3Model, panel: Tensor, seeds: core.Seeds, cell: int, *, with_controls: bool = True, draws_p: int = 4, draws_x: int = 4, exhaustive_visit: int = 16, prior_off_visit: int = 2, expected_targets: int = 32768) -> dict[str, Any]:
    """Every read of one checkpoint of one arm (section 3.4; ruling 10: step 0 uses ``with_controls=False``: enabled and disabled only). Keys ``"<read>|<draw>"``; a non-finite intervention value is None.
    ``used_slots`` and ``branch_entropy`` are the statistics of the enabled read. The replay is made by the caller after a fresh restore."""
    arm = model.arm

    def ev(m: S3Model, data: Tensor, ctl: Ctl | None = None, *, collector: Collector | None = None, nonfinite: str = "raise") -> float:
        return evaluate(m, data, ctl, collector=collector, expected_targets=expected_targets, nonfinite=nonfinite)

    out: dict[str, float | None] = {}
    stats: dict[str, Any] = {}

    def put(read: str, draw: int, v: float) -> None:
        out[f"{read}|{draw}"] = v if math.isfinite(v) else None

    col = Collector() if arm in (TREE, FLAT) else None
    put(core.READ_ENABLED, 0, ev(model, panel, collector=col))
    if col is not None:
        stats["used_slots"] = len(col.selected)
        stats["branch_entropy"] = col.entropy()
        stats["usage"] = [float(x) for x in col.usage.tolist()]
    model.bypass = True
    try:
        put(core.READ_DISABLED, 0, ev(model, panel))
    finally:
        model.bypass = False
    if not with_controls:
        return {"reads": out, "stats": stats}
    nf = "value"
    if arm in (TREE, FLAT):
        mem = model.addition
        assert isinstance(mem, Memory) and col is not None
        put(core.READ_P_ALL, 0, ev(model, panel, Ctl("values", values=p_all_values(mem.values, seeds.p_all(cell))), nonfinite=nf))
        for j in range(draws_p):
            v = p_used_values(mem.values, sorted(col.selected), seeds.p_used(cell, j))
            out[f"{core.READ_P_USED}|{j}"] = None if v is None else _fin(ev(model, panel, Ctl("values", values=v), nonfinite=nf))
        put(core.READ_X_MEAN, 0, ev(model, panel, Ctl("X_mean"), nonfinite=nf))
        for j in range(draws_x):
            put(core.READ_X, j, ev(model, panel, Ctl("X", gen=seeded(seeds.x(cell, j))), nonfinite=nf))
        if arm == TREE:
            k2, v2 = joint_permutation(mem.keys, mem.values, seeds.joint(cell))
            put(core.READ_JOINT, 0, ev(model, panel, Ctl("joint", keys=k2, values=v2), nonfinite=nf))
            put(core.READ_EXHAUSTIVE, 0, ev(model, panel, Ctl("exhaustive", visit=exhaustive_visit, use_prior=True), nonfinite=nf))
            put(core.READ_PRIOR_OFF, 0, ev(model, panel, Ctl("prior_off", visit=prior_off_visit, use_prior=False), nonfinite=nf))
    else:
        for j in range(draws_x):
            put(core.READ_X_DENSE, j, ev(model, panel, Ctl("X", gen=seeded(seeds.x(cell, j))), nonfinite=nf))
        put(core.READ_X_MEAN_DENSE, 0, ev(model, panel, Ctl("X_mean"), nonfinite=nf))
    return {"reads": out, "stats": stats}


def _fin(v: float) -> float | None:
    return v if math.isfinite(v) else None


# --- streams (ruling 3) ----------------------------------------------------------------------------------------------------
class Stream:
    """One CPU generator seeded with the stream seed. REP / REP-U: successive ``randperm(n)`` per epoch (n = 2048); FRESH: one ``randperm(len(rows))`` over the pool in rank order. Update k takes entries 8k to 8k+7."""

    def __init__(self, rows: Tensor, seed: int, *, fresh: bool, batch: int = 8) -> None:
        self.rows, self.fresh, self.batch = rows, fresh, batch
        self.gen = seeded(seed)
        self.n = rows.shape[0]
        self.perms: list[Tensor] = [torch.randperm(self.n, generator=self.gen, device="cpu")] if fresh else []

    def max_updates(self) -> int | None:
        return self.n // self.batch if self.fresh else None

    def indices(self, k: int) -> Tensor:
        lo = k * self.batch
        if self.fresh:
            if lo + self.batch > self.n:
                raise core.EngineeringStop(f"ENGINEERING STOP — the FRESH pool of {self.n} chunks supports {self.n // self.batch} updates, not {k + 1}")
            return self.perms[0][lo : lo + self.batch]
        epoch = lo // self.n
        while len(self.perms) <= epoch:
            self.perms.append(torch.randperm(self.n, generator=self.gen, device="cpu"))
        off = lo - epoch * self.n
        if off + self.batch > self.n:
            raise ValueError("a batch must not straddle an epoch (2048 is a multiple of 8)")
        return self.perms[epoch][off : off + self.batch]

    def get(self, k: int) -> Tensor:
        return self.rows[self.indices(k)]


# --- training (ruling 2) ---------------------------------------------------------------------------------------------------
def make_optimizer(model: S3Model, rate: float) -> AdamW:
    """``engine.optimizer_for`` (foreach=False, fused=False, amsgrad=False) over the addition only; the rate is written into ``param_groups[0]["lr"]`` before the first step."""
    params = nn.ParameterList(model.trainable())
    opt = adamw_for(params)
    opt.param_groups[0]["lr"] = float(rate)
    return opt


def train_step(model: S3Model, optimizer: AdamW, batch: Tensor, step: int) -> tuple[float, float]:
    """Step order as ``p4_model.train_step``. The three failures of section 6.1 raise ``FailedCell``: a non-finite loss; a non-finite clipped gradient norm (``clip_grad_norm_`` is called with
    ``error_if_nonfinite=False`` and the norm is tested here, because torch raises a RuntimeError, not a ValueError, with ``True``); a non-finite parameter."""
    params = model.trainable()
    optimizer.zero_grad(set_to_none=True)
    logits, _ = model(batch[:, :-1])
    loss = loss_for(logits, batch[:, 1:], "mean")
    if not math.isfinite(loss.item()):
        raise FailedCell(f"non-finite training loss at step {step}")
    loss.backward()  # type: ignore[no-untyped-call]
    if any(p.grad is None for p in params):
        raise ValueError(f"missing addition gradients at step {step}")
    norm = nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=False)
    if not math.isfinite(norm.item()):
        raise FailedCell(f"non-finite gradient norm at step {step}")
    optimizer.step()
    if not all(bool(p.isfinite().all()) for p in params):
        raise FailedCell(f"non-finite parameter at step {step}")
    return loss.item(), norm.item()


def state_digest(model: S3Model) -> str:
    h = hashlib.sha256()
    for name, t in sorted(model.addition.state_dict().items()) if model.addition is not None else []:
        h.update(name.encode())
        h.update(bytes(t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist()))
    return h.hexdigest()


def snapshot_dir(root: Path, step: int) -> Path:
    return root / f"snap-u{step:05d}"


def save_snapshot(root: Path, model: S3Model, optimizer: AdamW | None, step: int, identity: dict[str, Any]) -> dict[str, Any]:
    d = snapshot_dir(root, step)
    d.mkdir(parents=True, exist_ok=True)
    assert model.addition is not None
    torch.save({"addition": model.addition.state_dict(), "optimizer": optimizer.state_dict() if optimizer else None, "step": step, "identity": identity}, d / "state.pt")
    digest = hashlib.file_digest((d / "state.pt").open("rb"), "sha256").hexdigest()
    write_json(d / "index.json", {"state_sha256": digest, "step": step, "identity_sha256": sha256(canonical_json(identity)), "bytes": (d / "state.pt").stat().st_size})
    return {"sha256": digest, "bytes": (d / "state.pt").stat().st_size}


def restore_snapshot(root: Path, model: S3Model, step: int, identity: dict[str, Any]) -> None:
    d = snapshot_dir(root, step)
    index = read_json(d / "index.json")
    with (d / "state.pt").open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("snapshot checksum mismatch")
    state = torch.load(d / "state.pt", weights_only=True, map_location="cpu")
    if state["step"] != step or state["identity"] != identity:
        raise ValueError("snapshot step or identity mismatch")
    assert model.addition is not None
    model.addition.load_state_dict(state["addition"], strict=True)


def train_run(model: S3Model, stream: Stream, rate: float, root: Path, snapshots: Sequence[int], max_update: int, identity: dict[str, Any], *, hook: Callable[[int, Tensor], None] | None = None) -> dict[str, Any]:
    """Train from update 0 (ruling 6: a restart is from 0 and partial checkpoints are discarded by the caller), saving a snapshot after each update count in ``snapshots``. A ``FailedCell`` ends the run with status
    ``failed_cell``; the snapshots made before it are kept. Any other exception propagates (an item error / engineering stop)."""
    opt = make_optimizer(model, rate)
    snaps: dict[int, dict[str, Any]] = {}
    status: dict[str, Any] = {"status": "ok"}
    began = time.monotonic()
    model.train()
    if 0 in snapshots:
        snaps[0] = save_snapshot(root, model, opt, 0, identity)
    losses: list[float] = []
    try:
        for k in range(max_update):
            loss, _ = train_step(model, opt, stream.get(k), k + 1)
            losses.append(loss)
            if hook is not None:
                hook(k + 1, stream.get(k))
            if (k + 1) in snapshots:
                snaps[k + 1] = save_snapshot(root, model, opt, k + 1, identity)
    except FailedCell as e:
        status = {"status": "failed_cell", "reason": str(e), "failed_at_update": len(losses) + 1}
    return {**status, "snapshots": {str(k): v for k, v in snaps.items()}, "seconds": time.monotonic() - began, "updates_done": len(losses), "bytes": sum(v["bytes"] for v in snaps.values())}
