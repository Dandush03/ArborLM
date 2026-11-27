# ruff: noqa: E501
"""C1 fix round 3: the measuring instrument. A rule that is supposed to be the program's own algorithm in other code (a 'control', prefix ``C.``) must reproduce the key in every item of
its shape; otherwise the parser that reads the rendered source is wrong and every low rate beside it means nothing. Self-checked only."""

from __future__ import annotations

import ast

from studies.m0.c1_fix3_battery import draw, specific

CONTROLS = {
    "C1.counter_list_f3": ("C.self_check",),
    "C1.euclid_gcd_traced_f3": ("C.algorithm_rerun",),
    "C1.merge_two_sorted_f3": ("C.algorithm_rerun",),
}


def test_controls_reproduce_the_key() -> None:
    for lid, rules in CONTROLS.items():
        for lv in (0, 3, 6):
            for row in draw(lid, 7, 60):
                if row["lv"] != lv:
                    continue
                _sh, rr = specific(lid, row["src"], ast.parse(row["src"]))
                for rn in rules:
                    assert rr[rn] == row["key"], (lid, rn, row["src"], rr[rn], row["key"])


def test_collatz_control_matches_one_of_the_two_orders() -> None:
    for lv in (0, 3):
        for row in draw("C1.while_counter_f3", 7, 120):
            if row["lv"] != lv:
                continue
            sh, rr = specific("C1.while_counter_f3", row["src"], ast.parse(row["src"]))
            if sh == "collatz":
                assert row["key"] in {rr["C.algorithm_rerun_after"], rr["C.algorithm_rerun_before"]}


def test_mutation_that_changes_nothing_does_not_apply() -> None:
    from studies.m0.c1_fix3_battery import DropIf, mut

    assert mut("x = 1\nprint(x)", DropIf(r"zzz").visit) is None
    assert mut("x = 1\nif x == 1:\n    x = 5\nprint(x)", DropIf(r"== 1").visit) == "1"
