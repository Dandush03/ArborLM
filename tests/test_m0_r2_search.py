# ruff: noqa: E501
"""R2 batch 1, family search: mechanical checks and a test-local cross-check written from the item's own wording (not the registered second solver)."""

from __future__ import annotations

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def test_family_checks() -> None:
    assert check_family_r2("search") == []


def test_binary_search_trace_from_the_stated_rule() -> None:
    for lv in ALL_LEVELS:
        r = stream(953811, "t", "bs", str(lv))
        for i in range(25):
            it = build_item(LIN["R2.binary_search_trace"], lv, r, "A", f"t/{lv}/{i}")
            xs, target = it.structured["xs"], it.structured["target"]
            low, high, seen = 1, len(xs), []
            while low <= high:
                mid = (low + high) // 2
                seen.append(xs[mid - 1])
                if xs[mid - 1] == target:
                    break
                if target < xs[mid - 1]:
                    high = mid - 1
                else:
                    low = mid + 1
            assert it.answer == (", ".join(map(str, seen)) if it.structured["ask"] == "values" else str(seen[2]))
            assert xs == sorted(set(xs)) and len(seen) >= 3
