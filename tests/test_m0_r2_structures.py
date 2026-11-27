# ruff: noqa: E501
"""R2 batch 1, family structures: mechanical checks and test-local cross-checks (not the registered second solvers)."""

from __future__ import annotations

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953803, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("structures") == []


def test_bst_walks_have_the_defining_properties() -> None:
    from studies.m0.lineages_r2_structures import bst_order

    assert bst_order([5, 3, 8, 1, 4], "pre") == [5, 3, 1, 4, 8]
    assert bst_order([5, 3, 8, 1, 4], "post") == [1, 4, 3, 8, 5]
    assert bst_order([5, 3, 8, 1, 4], "level") == [5, 3, 8, 1, 4]
    for it in items("R2.bst_traversal", 15):
        xs, kind = it.structured["xs"], it.structured["kind"]
        got = [int(v) for v in it.answer.split(", ")]
        assert sorted(got) == sorted(xs) and got != xs and got != sorted(xs)
        if kind == "pre":
            assert got[0] == xs[0]
        if kind == "post":
            assert got[-1] == xs[0]


def test_heap_answers_are_valid_heaps_of_the_right_numbers() -> None:
    for it in items("R2.min_heap_ops", 15):
        h = [int(v) for v in it.answer.split(", ")]
        assert all(h[p - 1] <= h[c - 1] for p in range(1, len(h) + 1) for c in (2 * p, 2 * p + 1) if c <= len(h))
        want = sorted(it.structured["xs"])[it.structured["removals"] :]
        assert sorted(h) == want


def test_cache_reference_run() -> None:
    from studies.m0.lineages_r2_structures import cache_run

    assert cache_run(list("abcab"), 2, "fifo")[0] == 5 and cache_run(list("abab"), 2, "lru")[0] == 2
    assert cache_run(list("aba"), 2, "lru") == (2, ["b", "a"])
    for it in items("R2.cache_eviction", 10):
        s = it.structured
        miss, cache = cache_run(s["seq"], s["cap"], s["policy"])
        assert it.answer == (str(miss) if s["ask"] == "misses" else ("yes" if s["item"] in cache else "no"))


def test_hash_probe_by_direct_insertion() -> None:
    for it in items("R2.hash_probe", 15):
        s = it.structured
        slots: dict[int, int] = {}
        probes = 0
        for k in s["keys"]:
            pos, probes = k % s["m"], 1
            while pos in slots:
                pos, probes = (pos + 1) % s["m"], probes + 1
            slots[pos] = k
        if s["ask"] == "slot":
            assert it.answer == str(next(p for p, k in slots.items() if k == s["target"]))
        else:
            assert it.answer == str(probes)
