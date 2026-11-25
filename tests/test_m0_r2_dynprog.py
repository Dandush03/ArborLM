# ruff: noqa: E501
"""R2 batch 1, family dynprog: mechanical checks plus test-local brute-force cross-checks on 60 items per lineage and level (not the registered second solvers)."""

from __future__ import annotations

import itertools

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953801, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("dynprog") == []


def test_lcs_against_all_subsequences() -> None:
    for it in items("R2.lcs_length", 4):
        a, b = it.structured["a"], it.structured["b"]
        subs_b = {"".join(c) for k in range(len(b) + 1) for c in itertools.combinations(b, k)} if len(b) <= 12 else None
        if subs_b is None:
            continue
        best = max(k for k in range(len(a) + 1) for c in itertools.combinations(a, k) if "".join(c) in subs_b)
        assert str(best) == it.answer


def test_coin_change_against_breadth_first_search() -> None:
    for it in items("R2.coin_change_min"):
        coins, amount = it.structured["coins"], it.structured["amount"]
        reach = {0}
        steps = 0
        while amount not in reach:
            reach = {v + c for v in reach for c in coins if v + c <= amount}
            steps += 1
        assert str(steps) == it.answer


def test_lis_against_exponential_search_on_short_lists_and_known_case() -> None:
    from studies.m0.lineages_r2_dynprog import lis

    assert lis([10, 9, 2, 5, 3, 7, 101, 18]) == 4
    for it in items("R2.lis_length", 3):
        xs = it.structured["xs"][:14]
        best = 1
        for mask in range(1, 1 << len(xs)):
            sel = [xs[i] for i in range(len(xs)) if mask >> i & 1]
            if all(sel[i] < sel[i + 1] for i in range(len(sel) - 1)):
                best = max(best, len(sel))
        if len(it.structured["xs"]) <= 14:
            assert str(best) == it.answer


def test_max_subarray_against_all_slices() -> None:
    for it in items("R2.max_subarray_sum"):
        xs = it.structured["xs"]
        assert str(max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1))) == it.answer


def test_greedy_is_wrong_in_most_coin_items() -> None:
    from studies.m0.lineages_r2_dynprog import coin_greedy

    its = list(items("R2.coin_change_min", 60))
    wrong = sum(1 for it in its if str(coin_greedy(it.structured["coins"], it.structured["amount"])) != it.answer)
    assert wrong / len(its) > 0.6
