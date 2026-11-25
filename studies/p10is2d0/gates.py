# ruff: noqa: E501
"""The gate list of ADR-0035 section 4 (identities on the real snapshots) and the reproduction comparison of section 8.2. A gate record holds only pass/fail and the largest deviation."""

import math
from collections.abc import Mapping, Sequence
from typing import Any

import torch
from torch import Tensor

from studies.p10s2.memory import SparseStore

from . import reads

SUM_TOLERANCE = 1e-6


def _max_abs(x: Tensor, y: Tensor) -> float:
    if x.shape != y.shape:
        return math.inf
    return float((x - y).abs().max()) if x.numel() else 0.0


def within_sum_tolerance(a: Tensor, other: Tensor) -> bool:
    """a = e(1) + e(2) to a largest absolute difference <= 1e-6 * max(1, ||a||_inf)."""
    return _max_abs(a, other) <= SUM_TOLERANCE * max(1.0, float(a.abs().max()))


def _stage1_frozen(m1: SparseStore, other: SparseStore) -> dict[str, Any]:
    pairs = [(m1.keys[0], other.keys[0]), (m1.values[0], other.values[0]), (m1.gates[0], other.gates[0])]
    ok = all(torch.equal(x.detach(), y.detach()) for x, y in pairs)
    return {"pass": ok, "largest_deviation": max(_max_abs(x.detach(), y.detach()) for x, y in pairs)}


def _equal(x: Tensor, y: Tensor) -> dict[str, Any]:
    return {"pass": bool(torch.equal(x, y)), "largest_deviation": _max_abs(x, y)}


def identity_gates(m1: SparseStore, at_append: SparseStore, final: SparseStore, q: Tensor) -> dict[str, dict[str, Any]]:
    """The requirements of section 4 on one cell: stage-1 keys, values and gate of both M-append snapshots torch.equal to M1's; g2 = 0.0 exactly at append; the weight-vector computation of a torch.equal to
    SparseStore.read on every query; b(1) torch.equal to M1's read on every query; e(1) at append torch.equal to a at append; a = e(1) + e(2) within the tolerance."""
    with torch.no_grad():
        out: dict[str, dict[str, Any]] = {
            "stage1_frozen_at_append": _stage1_frozen(m1, at_append),
            "stage1_frozen_final": _stage1_frozen(m1, final),
            "g2_zero_at_append": {"pass": float(at_append.gates[1]) == 0.0, "largest_deviation": abs(float(at_append.gates[1]))},
            "a_weights_equal_registered_read_at_append": _equal(reads.read_a(at_append, q), at_append.read(q)),
            "a_weights_equal_registered_read_final": _equal(reads.read_a(final, q), final.read(q)),
            "b1_equals_m1_read_at_append": _equal(reads.read_b(at_append, q, 0), m1.read(q)),
            "b1_equals_m1_read_final": _equal(reads.read_b(final, q, 0), m1.read(q)),
            "e1_equals_a_at_append": _equal(reads.read_e(at_append, q, 0), reads.read_a(at_append, q)),
        }
        for name, store in (("at_append", at_append), ("final", final)):
            a, s = reads.read_a(store, q), reads.read_e(store, q, 0) + reads.read_e(store, q, 1)
            out[f"a_equals_e1_plus_e2_{name}"] = {"pass": within_sum_tolerance(a, s), "largest_deviation": _max_abs(a, s)}
    return out


def compare_pass(registered: Mapping[str, Sequence[Any]], got: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    """Reproduction of a registered pass (section 8.2): per-item scores equal exactly (the frozen chrF) and identical greedy sequences. ``largest_deviation`` is the largest absolute per-item score difference
    (None if the lengths differ)."""
    ri, gi = list(registered["items"]), list(got["items"])
    if len(ri) != len(gi) or len(registered["sequences"]) != len(got["sequences"]):
        return {"pass": False, "largest_deviation": None}
    dev = max((abs(float(x) - float(y)) for x, y in zip(ri, gi, strict=True)), default=0.0)
    same_items = all(float(x) == float(y) for x, y in zip(ri, gi, strict=True))
    same_seq = [list(s) for s in registered["sequences"]] == [list(s) for s in got["sequences"]]
    return {"pass": bool(same_items and same_seq), "largest_deviation": dev}
