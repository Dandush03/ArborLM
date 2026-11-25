# ruff: noqa: E501
"""M1 fix round 3: loader of the new revisions, the NOT REGISTERED list, and the carried-over lineage.

Own registry (``FIX3``); nothing here enters ``core.REGISTRY``. ``tiered_pricing`` is carried over unchanged from batch 1 (audit verdict: REGISTRABLE AS IS; it states its format, never retries and
passes capacity). ``min_cost_packs_r2`` is NOT REGISTERED and appears nowhere in this module's loaders (ruling R-12).
"""

from __future__ import annotations

import importlib

from studies.m0.core import Lineage
from studies.m0.lineages_m1_fix3_common import FIX3, STEM_OF

CARRIED_OVER = ("M1.tiered_pricing",)
EXCLUDED_EVERYWHERE = ("M1.min_cost_packs_r2", "M1.min_cost_packs")  # ruling R-12: not in the loader, fixtures, capacity run, cluster map or its count

# Lineages (r3 ids) that are NOT REGISTERED, with the reason; filled from the measurements (see NOTES_FIX3_M1.md and the manifest). Builders stay on file as attempts.
NOT_REGISTERED: dict[str, str] = {
    "M1.pythagoras_r3": (
        "Capacity and the memorised-triple tell cannot both be fixed. Integer right triangles are sparse: 294 with hypotenuse <= 400, 1,981 with <= 2,000, 3,414 with <= 3,200 (exact enumeration). The mixture of the five "
        "shapes needs about 8,300 triangles for the demand with margin (n_eff = 3.57 x the number of triangles), which needs hypotenuse <= about 7,000 (squares of 5 x 10^7) even at level 0, so no level-meaningful widening exists. "
        "Measured n_eff of the primitive-first attempt: 345, 704, 1,066, 1,431, 1,743, 2,098, 2,491 (levels 0-6) against 22,830. The catalogue of the 16 primitive triples scaled still scores +0.23 at level 0 "
        "(+0.13 at level 1). The builder stays on file as an attempt."
    ),
    "M1.binomial_choose_r3": (
        "Capacity at the low levels cannot be reached without changing the difficulty. The plain and 'must include' shapes of rev2 are a few hundred items; the group-product shape that replaces them has exact support "
        "620, 892 and 1,982 at levels 0-2 (caps 10^4..10^6, groups of at most 14..18 people); even groups of 30 people picking up to 5 (answers up to 10^10) give 9,447. Measured n_eff 613, 883, 1,957 at levels 0-2 against 22,830 "
        "(and against 11,415 as one of two members of S4). Cluster S4 continues with slot_permutations alone (a one-member cluster; the cluster count is unchanged)."
    ),
    "M1.digit_puzzle_r3": (
        "Capacity and the tell, both measured. The wording and the 'exactly once / at least once' ambiguity are fixed, and the printed clue set is minimal (and every all-but-one set leaves at least 4 numbers), but (a) the number "
        "of distinct puzzles is bounded by the 90 two-digit and 900 three-digit secrets times their clue sets: measured n_eff of the final shape (M = 6,000) is 82, 1,956, 2,023, 1,682, 1,735, 177, 190 at levels 0-6 against 22,830; "
        "the version without the 'at least 4 left' condition reached 1,787, 6,486, 6,546, 14,398, 14,443, 11,628, 11,507 (three necessary clues from level 0) and an earlier one with two necessary clues 1,905-26,110; "
        "no level-meaningful version reaches the demand at levels 0-2, so there is no 'partial level' set; (b) with three or more necessary clues the first two printed clues still leave only a few numbers, so 'the smallest "
        "number meeting the first two clues' scores +0.12 to +0.28 (requiring 8 left over by every all-but-one set made a valid draw take seconds at levels 5-6; 4 was kept). The builder stays on file as an attempt."
    ),
}


def load_all() -> list[Lineage]:
    """Every r3 revision (registered or not) plus the carried-over lineage, sorted by id. ``min_cost_packs`` is never returned."""
    for m in ("a", "b", "c"):
        importlib.import_module(f"studies.m0.lineages_m1_fix3_{m}")
    from studies.m0.lineages_m1_common import load_batch

    base = {x.id: x for x in load_batch()}
    return sorted([*FIX3, *(base[i] for i in CARRIED_OVER)], key=lambda x: x.id)


def load_registered() -> list[Lineage]:
    return [x for x in load_all() if x.id not in NOT_REGISTERED]


def stem(lid: str) -> str:
    return STEM_OF.get(lid, lid.removeprefix("M1."))
