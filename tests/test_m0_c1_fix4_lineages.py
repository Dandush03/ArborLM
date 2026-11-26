# ruff: noqa: E501
"""C1 fix round 4: the new builders (two one-shape lineages, three level repairs), the drop list and the reject table. Self-checked only; nothing is registered."""

from __future__ import annotations

import ast
import inspect
import random
import re

import pytest

from studies.m0.c1grammar import render
from studies.m0.core import Retry, normalise
from studies.m0.lineages_c1 import _finish
from studies.m0.lineages_c1_fix4 import (
    DROPPED_AFTER_REMEASURE,
    DROPPED_AUDIT4,
    FIX4,
    RETRY_SITES,
    SUPERSEDES4,
    all_written,
    current_after_audit4,
)
from studies.m0.scoring import in_grammar, normalise_answer
from studies.m0.solvers_c1 import c1_trace

F4 = [x.id for x in FIX4]


def _items(lid: str, lv: int, n: int, seed: int = 3):  # type: ignore[no-untyped-def]
    lin = all_written()[lid]
    r = random.Random(seed * 1000 + lv)
    out = []
    while len(out) < n:
        try:
            out.append(lin.build(lv, r))
        except Retry:
            continue
    return out


def test_the_five_fix4_lineages_exist() -> None:
    assert sorted(F4) == ["C1.fast_power_f4", "C1.func_branch_f4", "C1.func_compose_f4", "C1.sieve_marking_f4", "C1.slices_f4"]
    assert SUPERSEDES4 == {"C1.sieve_marking_f4": "C1.sieve_marking_f3", "C1.fast_power_f4": "C1.fast_power_f3", "C1.func_branch_f4": "C1.func_branch", "C1.func_compose_f4": "C1.func_compose_f3", "C1.slices_f4": "C1.slices"}


@pytest.mark.parametrize("lid", F4)
@pytest.mark.parametrize("lv", range(7))
def test_keys_match_the_second_solver_and_one_line(lid: str, lv: int) -> None:
    for b in _items(lid, lv, 25):
        assert c1_trace(b.structured) == b.answer
        assert "\n" not in b.answer and b.answer == normalise_answer(b.answer)
        assert in_grammar("line", b.answer)


@pytest.mark.parametrize("lid", F4)
def test_builders_are_deterministic(lid: str) -> None:
    lin = all_written()[lid]
    for lv in (0, 3, 6):
        a = [lin.build(lv, random.Random(11)).question for _ in range(1)]
        b = [lin.build(lv, random.Random(11)).question for _ in range(1)]
        assert a == b


def test_fix4_builders_have_no_reject_of_their_own() -> None:
    for lid in F4:
        tree = ast.parse(inspect.getsource(all_written()[lid].build))
        assert not [n for n in ast.walk(tree) if isinstance(n, ast.Raise)], lid


def test_sieve_keeps_only_the_strike_sum_shape() -> None:
    for lv in range(7):
        for b in _items("C1.sieve_marking_f4", lv, 40):
            tree = ast.parse(render(b.structured["program"]))
            flags_name = tree.body[0].targets[0].id  # type: ignore[attr-defined]
            printed = tree.body[-1].value.args[0]  # type: ignore[attr-defined]
            assert isinstance(printed, ast.Name) and printed.id != flags_name  # the flag list is never the printed value
            n = len(tree.body[0].value.elts)  # type: ignore[attr-defined]
            assert n == (30, 34, 38, 42, 46, 50, 56)[lv]


def _sim_fast_power(src: str) -> str:
    tree = ast.parse(src)
    vals = {t.targets[0].id: t.value.value for t in tree.body[:4]}  # type: ignore[attr-defined]
    names = [t.targets[0].id for t in tree.body[:4]]  # type: ignore[attr-defined]
    res, b, e, m = (vals[x] for x in names)
    c = int(re.search(r"\(\w+ \* \w+ \+ (\d+)\) % ", src).group(1))  # type: ignore[union-attr]
    while e > 0:
        if e % 2 == 1:
            res = res * b % m
        b = (b * b + c) % m
        e //= 2
    return str(res)


@pytest.mark.parametrize("lv", range(7))
def test_fast_power_is_res_only_and_matches_an_independent_simulation(lv: int) -> None:
    for b in _items("C1.fast_power_f4", lv, 60):
        src = render(b.structured["program"])
        tree = ast.parse(src)
        assert tree.body[-1].value.args[0].id == tree.body[0].targets[0].id  # type: ignore[attr-defined]  # prints res, the first name assigned
        assert _sim_fast_power(src) == b.answer
        e0 = tree.body[2].value.value  # type: ignore[attr-defined]
        assert e0.bit_length() == 3 + lv


def test_repaired_levels_are_not_identical_where_the_old_builders_were() -> None:
    from studies.m0.c1_fix4_levels import shared_stream_identity

    for old, new in (("C1.func_branch", "C1.func_branch_f4"), ("C1.func_compose_f3", "C1.func_compose_f4")):
        for lv in (0, 3, 4, 5):  # the steps L0->L1, L3->L4, L4->L5, L5->L6 where the old builder ignored the level
            assert shared_stream_identity(old, lv, n=60) == 1.0, (old, lv)  # failing-first: the old builder drew the same item
            assert shared_stream_identity(new, lv, n=60) < 0.99, (new, lv)


def test_slices_string_length_rises_at_every_level() -> None:
    means = []
    for lv in range(7):
        lens = []
        for b in _items("C1.slices_f4", lv, 400):
            tree = ast.parse(render(b.structured["program"]))
            v = tree.body[0].value  # type: ignore[attr-defined]
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                lens.append(len(v.value))
        means.append(sum(lens) / len(lens))
    assert all(b > a for a, b in zip(means, means[1:], strict=False)), means
    old = []
    for lv in range(7):
        lens = []
        for b in _items("C1.slices", lv, 400):
            v = ast.parse(render(b.structured["program"])).body[0].value  # type: ignore[attr-defined]
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                lens.append(len(v.value))
        old.append(sum(lens) / len(lens))
    # failing-first: the old builder drew the same string length for levels (0, 1), (2, 3), (4, 5): the means of a pair do not differ by more than sampling noise
    assert abs(old[1] - old[0]) < 0.8 and abs(old[3] - old[2]) < 0.8 and abs(old[5] - old[4]) < 0.8, old


@pytest.mark.parametrize("lid", ["C1.func_branch_f4", "C1.func_compose_f4", "C1.slices_f4"])
def test_repaired_lineages_distinct_questions_across_levels(lid: str) -> None:
    seen: dict[str, int] = {}
    dup = 0
    for lv in range(7):
        for b in _items(lid, lv, 150):
            k = normalise(b.question)
            if k in seen and seen[k] != lv:
                dup += 1
            seen[k] = lv
    assert dup <= 0.01 * 7 * 150


def test_current_set_after_the_audit_drops() -> None:
    cur = current_after_audit4()
    assert len(cur) == 27 and len(set(cur)) == 27
    for gone in ("C1.partition_pass_f3", "C1.loop_sum", "C1.grid_path_table", "C1.string_pair_table", "C1.coin_change_table_f3", "C1.bubble_pass", "C1.mirror_pointers", "C1.cellular_update_f3", "C1.bfs_queue", "C1.majority_vote_scan_f3"):
        assert gone not in cur and gone in DROPPED_AUDIT4 and DROPPED_AUDIT4[gone]
    for stay_out in ("C1.insertion_sort", "C1.minmax_track", "C1.kadane_scan"):
        assert stay_out in DROPPED_AUDIT4 and stay_out not in cur
    for superseded in ("C1.sieve_marking_f3", "C1.fast_power_f3", "C1.func_branch", "C1.func_compose_f3", "C1.slices"):
        assert superseded not in cur
    assert DROPPED_AFTER_REMEASURE == {}  # nothing further fell in the fix-4 re-run


def test_reject_table_covers_every_survivor_with_a_reject_of_its_own() -> None:
    have = set()
    for lid in current_after_audit4():
        tree = ast.parse(inspect.getsource(all_written()[lid].build))
        if [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]:
            have.add(lid)
    assert have == set(RETRY_SITES), (sorted(have ^ set(RETRY_SITES)))
    for lid, (kind, cond, why) in RETRY_SITES.items():
        assert kind and cond and why, lid


def test_empty_and_unnormalised_answers_cannot_be_graded_so_those_rejects_are_needed() -> None:
    assert not in_grammar("line", "")  # an empty gold answer is no answer to the scorer
    for bad in ("AB", " ab", "a  b", "ab.", ""):
        if bad != "":
            assert normalise_answer(bad) != bad  # a correct answer could never equal this key
    from studies.m0.lineages_c1_common import S

    for lit in ("AB", "ab.", ""):
        with pytest.raises(Retry):
            _finish([["print", S(lit)]])


def test_the_answer_conditional_rejects_that_were_dropped_are_dropped_for_that_reason() -> None:
    for lid in ("C1.coin_change_table_f3", "C1.grid_path_table", "C1.mirror_pointers"):
        assert "R-19" in DROPPED_AUDIT4[lid]
