# ruff: noqa: E501
"""P10IS3 planted-positive toy and NEG-REF check (ADR-0026 section 3.4 and section 11; ruling 9).

A toy frozen backbone (identity blocks, tied embedding) and a memory whose values give, for each of 16 query directions, the exact correction that raises the logit of that direction's next byte. The planted corrections
are built with zero mean over the 16 classes, and every evaluation batch holds the 16 classes in equal numbers (each chunk cycles through them 4 times), so the batch-mean read keeps nothing of the gain.
On it P_used, X and X_mean must each be >= 0.5 C and NEG-REF must give 0. It runs in the test suite and as a gate. Nothing here touches natural text or a registered seed.
"""

from typing import Any

import torch
from torch import Tensor, nn

from arborlm.pilot_model import Memory

from . import core, model

CLASSES = 16


class _Identity(nn.Module):
    def forward(self, h: Tensor, mask: Tensor | None = None) -> Tensor:
        return h


class ToyBackbone(nn.Module):
    mask: Tensor

    def __init__(self) -> None:
        super().__init__()
        self.token = nn.Embedding(256, 32)
        self.position = nn.Embedding(64, 32)
        self.blocks = nn.ModuleList([_Identity(), _Identity()])
        self.final_norm = nn.Identity()
        with torch.no_grad():
            self.token.weight.zero_()
            self.position.weight.zero_()
            for b in range(CLASSES):
                self.token.weight[b, b] = 1.0  # the query direction e_b
                self.token.weight[b, CLASSES + b] = 1.0  # the output direction of byte b (tied embedding)
        self.register_buffer("mask", torch.zeros(64, 64), persistent=False)
        self.requires_grad_(False)


def toy_panel(chunks: int = 32) -> Tensor:
    """Chunk r holds bytes (r + t) mod 16: the next byte is always the input byte plus one, and each chunk has 4 of each class."""
    return torch.tensor([[(r + t) % CLASSES for t in range(65)] for r in range(chunks)], dtype=torch.int64)


def plant(arm: str, alpha: float = 3.0, seed: int = 1) -> model.S3Model:
    """A toy memory (``flat`` or ``learned_tree``) whose slot i serves the query direction i with the zero-mean correction raising the logit of byte i + 1."""
    m = model.S3Model(ToyBackbone(), arm, seed)
    mem = m.addition
    assert isinstance(mem, Memory)
    with torch.no_grad():
        mem.keys.zero_()
        mem.values.zero_()
        corr = torch.zeros(CLASSES, 32)
        for i in range(CLASSES):
            mem.keys[i, i] = 1.0
            corr[i, CLASSES + (i + 1) % CLASSES] = alpha
        corr[:, CLASSES:] -= corr[:, CLASSES:].mean(0, keepdim=True)  # zero mean over the classes
        corr[:, CLASSES:] *= 1.0
        mem.values[:CLASSES] = corr
        mem.wq.zero_()
        mem.wq[:, :CLASSES] = torch.eye(CLASSES)
        mem.wo.copy_(torch.eye(32))
        mem.gate.fill_(20.0)
        if arm == core.TREE:
            mem.router.zero_()
            mem.router[0] = 1.0
    return m


def _ev(m: model.S3Model, panel: Tensor, ctl: model.Ctl | None = None, col: model.Collector | None = None) -> float:
    return model.evaluate(m, panel, ctl, collector=col, expected_targets=panel.shape[0] * 64, nonfinite="value")


def effects(m: model.S3Model, panel: Tensor, seeds: core.Seeds, cell: int = 0, draws: int = 4) -> dict[str, Any]:
    """B, H and the four effects P_used, P_all, X, X_mean (each H_control - H) of one planted or reference model; the draws are averaged first (ruling 12)."""
    mem = m.addition
    assert isinstance(mem, Memory)
    base = model.S3Model(m.backbone, core.BASE, None)
    b = _ev(base, panel)
    col = model.Collector()
    h = _ev(m, panel, None, col)
    used = sorted(col.selected)
    pu = []
    for j in range(draws):
        v = model.p_used_values(mem.values, used, seeds.p_used(cell, j))
        pu.append(_ev(m, panel, model.Ctl("values", values=v)))
    xs = [_ev(m, panel, model.Ctl("X", gen=model.seeded(seeds.x(cell, j)))) for j in range(draws)]
    return {
        "B": b, "H": h, "C": b - h, "P_used": sum(pu) / draws - h, "X": sum(xs) / draws - h, "X_mean": _ev(m, panel, model.Ctl("X_mean")) - h,
        "P_all": _ev(m, panel, model.Ctl("values", values=model.p_all_values(mem.values, seeds.p_all(cell)))) - h, "used_slots": len(used), "usage": col.usage,
    }  # fmt: skip


def neg_ref(m: model.S3Model, usage: Tensor) -> model.S3Model:
    """The constant-value negative reference of a checkpoint: every value row replaced by the usage-weighted mean value (ruling 9: the weights are the summed softmax read weights per slot on the calibration-panel enabled read)."""
    import copy

    ref = copy.deepcopy(m)
    mem = ref.addition
    assert isinstance(mem, Memory)
    with torch.no_grad():
        mem.values.copy_(model.neg_ref_values(mem.values, usage))
    return ref


def neg_ref_check(m: model.S3Model, panel: Tensor, seeds: core.Seeds, th: core.Thresholds, *, cell: int = 0) -> dict[str, Any]:
    """P_all, P_used, X and X_mean of the NEG-REF must be 0 within 1e-6, and no NEG-REF cell may meet D2's or D3's per-cell condition (C > 0 and effect >= 0.5 C): ruling 9."""
    first = effects(m, panel, seeds, cell)
    ref = neg_ref(m, first["usage"])
    e = effects(ref, panel, seeds, cell)
    tol = th.tolerance_neg_ref
    zero = {k: abs(e[k]) <= tol for k in ("P_all", "P_used", "X", "X_mean")}
    d2 = e["C"] > 0 and e["P_used"] >= th.half * e["C"]
    d3 = e["C"] > 0 and e["X_mean"] >= th.half * e["C"]
    return {"passed": all(zero.values()) and not d2 and not d3, "zero_within_tolerance": zero, "meets_d2_cell": d2, "meets_d3_cell": d3, "values": {k: e[k] for k in ("C", "P_all", "P_used", "X", "X_mean")}}


def planted_positive(th: core.Thresholds, seeds: core.Seeds, arms: tuple[str, ...] = (core.FLAT, core.TREE)) -> dict[str, Any]:
    """The planted-positive test as a gate: on the toy, P_used, X and X_mean are each >= 0.5 C with C > 0, and NEG-REF gives 0."""
    out: dict[str, Any] = {"arms": {}}
    ok = True
    panel = toy_panel(32)
    for arm in arms:
        m = plant(arm)
        e = effects(m, panel, seeds)
        neg = neg_ref_check(m, panel, seeds, th)
        passed = e["C"] > 0 and all(e[k] >= th.half * e["C"] for k in ("P_used", "X", "X_mean")) and neg["passed"]
        out["arms"][arm] = {"passed": bool(passed), "C": e["C"], "P_used": e["P_used"], "X": e["X"], "X_mean": e["X_mean"], "neg_ref": neg}
        ok = ok and bool(passed)
    out["passed"] = ok
    return out
