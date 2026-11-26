# ruff: noqa: E501
"""Read statistics of ADR-0035 section 5.2 (no decoding): per read, then mean, median, 5th and 95th percentile (the 0.05, 0.5 and 0.95 quantiles of torch.quantile, linear interpolation)."""

import math
from typing import Any

import torch
from torch import Tensor

from studies.p10s2 import core
from studies.p10s2.memory import SparseStore

from . import reads

RATIO_CONDITIONS = ("a", "c", "d", "e", "g")


@torch.no_grad()
def per_read_quantities(store: SparseStore, q: Tensor, p: int) -> dict[str, Tensor]:
    """Per read (one row of ``q``) for protected stage p: n_p (rows of stage p among the eight), displaced (8 - n_p), mass_p (softmax mass on stage-p rows in G), displaced_weight (the weight the displaced rows
    carried in b(p)'s own softmax: ranks n_p..7 of T8(Sp); G n Sp is always the top n_p of T8(Sp)), top_kept (b(p)'s top row is in G), rel_x = ||R_x - R_b(p)|| / ||R_b(p)|| for x in a, c, d, e, g (NaN where
    R_b(p) is the zero vector), and other_part = ||e(o)|| / ||R_b(p)||."""
    view = reads.slot_view(store, q)
    in_p = view.stage == p
    n_p = in_p.sum(dim=1).float()
    alone = reads.single_stage_store(store, p)
    wp = reads.slot_view(alone, q).weights
    ranks = torch.arange(core.TOP).unsqueeze(0)
    rb = alone.read(q)
    nb = rb.norm(dim=-1)
    nan = torch.full_like(nb, float("nan"))

    def ratio(x: Tensor) -> Tensor:
        return torch.where(nb > 0, (x - rb).norm(dim=-1) / nb.clamp_min(1e-300), nan)

    out = {
        "n_p": n_p,
        "displaced": core.TOP - n_p,
        "mass_p": (view.weights * in_p).sum(dim=1),
        "displaced_weight": (wp * (ranks >= n_p.unsqueeze(1))).sum(dim=1),
        "top_kept": (n_p >= 1).float(),
        "rel_a": ratio(reads.read_a(store, q)),
        "rel_c": ratio(reads.read_c(store, q)),
        "rel_d": ratio(reads.read_d(store, q, p)),
        "rel_e": ratio(reads.read_e(store, q, p)),
        "rel_g": ratio(reads.read_g(store, q, p)),
    }
    out["other_part"] = torch.where(nb > 0, reads.read_e(store, q, 1 - p).norm(dim=-1) / nb.clamp_min(1e-300), nan)
    return out


def summarise(x: Tensor) -> dict[str, Any]:
    """n (finite values), undefined (NaN values), mean, median, p5, p95 over the finite values (None where none)."""
    x = x.detach().double()
    ok = x[torch.isfinite(x)]
    out: dict[str, Any] = {"n": int(ok.numel()), "undefined": int(x.numel() - ok.numel())}
    if ok.numel() == 0:
        return {**out, "mean": None, "median": None, "p5": None, "p95": None}
    qs = torch.quantile(ok, torch.tensor([0.05, 0.5, 0.95], dtype=torch.float64))
    return {**out, "mean": float(ok.mean()), "median": float(qs[1]), "p5": float(qs[0]), "p95": float(qs[2])}


def summarise_all(quantities: dict[str, Tensor], mask: Tensor | None = None) -> dict[str, Any]:
    return {k: summarise(v if mask is None else v[mask]) for k, v in quantities.items()}


def finite_or_none(x: float) -> float | None:
    return x if math.isfinite(x) else None
