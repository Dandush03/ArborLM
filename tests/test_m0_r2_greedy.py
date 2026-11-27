# ruff: noqa: E501
"""R2 batch 1, family greedy: mechanical checks and test-local brute-force cross-checks (not the registered second solvers)."""

from __future__ import annotations

import itertools

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953805, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("greedy") == []


def test_interval_scheduling_against_subset_search() -> None:
    for it in items("R2.interval_scheduling", 3):
        iv = it.structured["meetings"]
        if len(iv) > 15:
            continue
        best = 0
        for mask in range(1 << len(iv)):
            sel = [iv[i] for i in range(len(iv)) if mask >> i & 1]
            if len(sel) > best and all(a[1] <= b[0] or b[1] <= a[0] for a, b in itertools.combinations(sel, 2)):
                best = len(sel)
        assert it.answer == str(best)


def test_merge_cost_against_exhaustive_merge_orders() -> None:
    def best(ws: tuple[int, ...]) -> int:
        if len(ws) == 1:
            return 0
        out = 10**9
        for i, j in itertools.combinations(range(len(ws)), 2):
            rest = [w for k, w in enumerate(ws) if k not in (i, j)]
            out = min(out, ws[i] + ws[j] + best(tuple(sorted([*rest, ws[i] + ws[j]]))))
        return out

    for it in items("R2.merge_smallest_cost", 3):
        ws = it.structured["ws"]
        if len(ws) <= 7:
            assert it.answer == str(best(tuple(sorted(ws))))
