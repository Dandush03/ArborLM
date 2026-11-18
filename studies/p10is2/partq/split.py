# ruff: noqa: E501
"""The pre-generation source split and the training draws (ADR-0025 section 4.3 rules 4-6; ruling G17).

Rule 4: each identity unit that is a no-gold source for both capabilities is assigned to B with probability 4/5 (seed 250904), otherwise to A. Each teacher generates only on its own sources.
Rule 6: if both capabilities reach 24,000 accepted sources, one seeded permutation per capability (250916 for A, 250917 for B) orders its accepted pool and replicate r takes positions
8,000 r .. 8,000 r + 7,999 (DISJOINT DRAWS); otherwise, if both reach 10,000, each replicate draws 8,000 with its own training-draw seed from the whole pool (OVERLAPPING DRAWS; the shared share is printed
beside every line that says "every cell"); otherwise DATA-EXHAUSTED. The decision is by rule and is never chosen.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from ..common import core

DISJOINT, OVERLAPPING, EXHAUSTED = "DISJOINT DRAWS", "OVERLAPPING DRAWS", "DATA-EXHAUSTED"


def assign_shared(units: Sequence[str], seed: int, allowed: frozenset[int] | set[int], share_b: float) -> dict[str, str]:
    """G17. THE DRAW ORDER IS PART OF THE DEFINITION (a vectorised ``torch.rand(n)`` is a different definition and gives other values): ``units`` are the identity units that are no-gold sources for both capabilities; they are taken in SORTED key order; each gets one uniform draw from a generator seeded ``seed`` (250904, one
    ``torch.rand(1)`` per unit, in that order); B if u < ``share_b`` (0.8), else A."""
    g = core.seeded_generator(seed, "source split", allowed)
    out: dict[str, str] = {}
    for u in sorted(set(units)):
        draw = float(torch.rand(1, generator=g).item())
        out[u] = "B" if draw < share_b else "A"
    return out


def split_sources(pool_a: Sequence[Any], pool_b: Sequence[Any], unit_of: Any, seed: int, allowed: frozenset[int] | set[int], share_b: float) -> dict[str, Any]:
    """Each capability's own sources: its exclusive sources plus the shared units assigned to it, in the pool's own order. ``unit_of(item)`` is the identity unit (P10-S2's ``source_unit``)."""
    ua, ub = {unit_of(x) for x in pool_a}, {unit_of(x) for x in pool_b}
    shared = sorted(ua & ub)
    owner = assign_shared(shared, seed, allowed, share_b)
    own_a = [x for x in pool_a if unit_of(x) not in owner or owner[unit_of(x)] == "A"]
    own_b = [x for x in pool_b if unit_of(x) not in owner or owner[unit_of(x)] == "B"]
    return {
        "A": own_a, "B": own_b, "owner": owner,
        "counts": {"A_pool": len(pool_a), "B_pool": len(pool_b), "shared_units": len(shared), "shared_to_A": sum(1 for v in owner.values() if v == "A"), "shared_to_B": sum(1 for v in owner.values() if v == "B"), "A_sources": len(own_a), "B_sources": len(own_b)},
    }  # fmt: skip


def draws_label(accepted_counts: Mapping[str, int], cfg: Mapping[str, Any]) -> str:
    """Rule 6 by the counts alone. Both >= 24,000: DISJOINT; else both >= 10,000: OVERLAPPING; else EXHAUSTED (either below 10,000)."""
    g = cfg["generation"]
    both = [int(accepted_counts[c]) for c in core.TASKS]
    if all(n >= int(g["accepted_disjoint"]) for n in both):
        return DISJOINT
    if all(n >= int(g["accepted_min"]) for n in both):
        return OVERLAPPING
    return EXHAUSTED


def disjoint_positions(n_pool: int, seed: int, allowed: frozenset[int] | set[int], replicates: int, per_replicate: int) -> list[list[int]]:
    """One seeded permutation orders the accepted pool; replicate r takes permutation positions per_replicate r .. per_replicate r + per_replicate - 1. Returns pool indices per replicate."""
    if n_pool < replicates * per_replicate:
        raise ValueError("a disjoint draw needs replicates x per_replicate accepted items")
    g = core.seeded_generator(seed, "disjoint draws permutation", allowed)
    perm = torch.randperm(n_pool, generator=g).tolist()
    return [perm[per_replicate * r : per_replicate * (r + 1)] for r in range(replicates)]


def overlapping_positions(n_pools: Mapping[str, int], seeds: Sequence[int], allowed: frozenset[int] | set[int], per_replicate: int) -> dict[str, list[list[int]]]:
    """Each replicate draws ``per_replicate`` items from the whole pool of each capability with its OWN training-draw seed: one generator per replicate, capability A drawn first and then B (one randperm
    each, first ``per_replicate``)."""
    if any(int(n) < per_replicate for n in n_pools.values()):
        raise ValueError("a pool is smaller than one draw")
    out: dict[str, list[list[int]]] = {c: [] for c in core.TASKS}
    for s in seeds:
        g = core.seeded_generator(s, "overlapping draw", allowed)
        for c in core.TASKS:
            out[c].append(torch.randperm(int(n_pools[c]), generator=g).tolist()[:per_replicate])
    return out


@dataclass(frozen=True)
class Draws:
    label: str
    indices: dict[str, list[list[int]]]  # capability -> replicate -> pool indices
    shared_share: dict[str, float]  # printed beside every "every cell" line when OVERLAPPING; zero when DISJOINT

    def to_json(self) -> dict[str, Any]:
        return {"label": self.label, "indices": self.indices, "shared_share": self.shared_share}


def shared_share(indices: Sequence[Sequence[int]]) -> float:
    """The mean over replicate pairs of |intersection| / draw size."""
    pairs = [(i, j) for i in range(len(indices)) for j in range(i + 1, len(indices))]
    if not pairs:
        return 0.0
    return float(sum(len(set(indices[i]) & set(indices[j])) / len(indices[i]) for i, j in pairs) / len(pairs))


def make_draws(counts: Mapping[str, int], cfg: Mapping[str, Any], part_seeds: Mapping[str, int], draw_seeds: Sequence[int], allowed: frozenset[int] | set[int]) -> Draws:
    """The registered decision and the draws. ``part_seeds`` has ``disjoint_permutation_a`` and ``..._b``; ``draw_seeds`` is the training-draw seed (base + 1) of each replicate, used for OVERLAPPING draws."""
    label = draws_label(counts, cfg)
    if label == EXHAUSTED:
        raise ValueError("no draw is made: a pool is below the minimum (DATA-EXHAUSTED)")
    g = cfg["generation"]
    reps, per = int(g["replicates"]), int(g["per_replicate"])
    idx: dict[str, list[list[int]]] = {}
    if label == DISJOINT:
        for c, key in (("A", "disjoint_permutation_a"), ("B", "disjoint_permutation_b")):
            idx[c] = disjoint_positions(int(counts[c]), int(part_seeds[key]), allowed, reps, per)
    else:
        idx = overlapping_positions(counts, draw_seeds, allowed, per)
    share = {c: shared_share(idx[c]) for c in core.TASKS}
    return Draws(label, idx, share)
