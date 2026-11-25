# ruff: noqa: E501
"""M1 fix round 3, wording (R-4). The replacement checks fail on the pre-fix shapes (see m1_fix3_failing_first.py)."""

from __future__ import annotations

import re

from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_m1_fix3 import load_all
from studies.m0.m1_fix3_checks import (
    digit_both_readings_problems,
    format_problems,
    grid_wording_problems,
)
from studies.m0.m1_fix3_verify import verify

ALL = {x.id: x for x in load_all()}
OLD_EXISTING = {x.id: x for x in lineages_of("M1")}


def test_grid_perimeter_has_a_single_reading_and_the_text_only_solver_agrees_with_the_key() -> None:
    lin = ALL["M1.grid_perimeter_r3"]
    assert grid_wording_problems(lin) == []
    for lv in ALL_LEVELS:
        rng = stream(411201, "grid", str(lv))
        for _ in range(40):
            it = build_item(lin, lv, rng, "A", "t")
            cells = set()
            rows = re.findall(r"Row (\d+) \(counting from the top\): (.*?)\.(?= Row | Squares)", it.question)
            assert rows
            for ridx, body in rows:
                y = int(ridx)
                if body.strip() == "no squares":
                    continue
                for part in body.split(", "):
                    m = re.fullmatch(r"columns (\d+) to (\d+)", part.strip())
                    if m:
                        for x in range(int(m.group(1)), int(m.group(2)) + 1):
                            cells.add((y, x))
                    else:
                        cells.add((y, int(part.strip().removeprefix("column "))))
            # the stated rule: unit sides that belong to exactly one square
            sides = Counter_sides(cells)
            assert str(sum(1 for v in sides.values() if v == 1)) == it.answer
            assert verify("grid_perimeter", it.structured) == it.answer


def Counter_sides(cells: set[tuple[int, int]]) -> dict[tuple[str, int, int], int]:  # noqa: N802
    out: dict[tuple[str, int, int], int] = {}
    for y, x in cells:
        for side in (("h", y, x), ("h", y + 1, x), ("v", y, x), ("v", y, x + 1)):
            out[side] = out.get(side, 0) + 1
    return out


def test_digit_puzzle_answer_is_unique_under_both_readings_of_the_digit_clue() -> None:
    lin = ALL["M1.digit_puzzle_r3"]
    for lv in (0, 1, 2, 3, 6):
        assert digit_both_readings_problems(lin, lv, 200) == [], lv
    # the wording no longer says 'one of its digits is d'
    rng = stream(411202, "dp")
    for lv in (1, 3):
        for _ in range(60):
            assert "one of its digits is" not in build_item(lin, lv, rng, "A", "t").question


def test_the_sixteen_existing_lineages_have_revisions_that_state_the_format_and_the_old_ones_do_not() -> None:
    for old_id, old in OLD_EXISTING.items():
        new = ALL[old_id + "_r3"]
        assert format_problems(new) == [], old_id
        assert format_problems(old, 3), f"{old_id} (pre-fix) unexpectedly states its format"


def test_slot_permutations_states_first_and_last_digit_rules_and_the_leading_zero() -> None:
    lin = ALL["M1.slot_permutations_r3"]
    for lv in ALL_LEVELS:
        rng = stream(411203, "sp", str(lv))
        for _ in range(80):
            it = build_item(lin, lv, rng, "A", "t")
            q = it.question
            assert "the last digit must be" in q
            assert ("may not be 0" in q) or ("may be 0" in q) or 0 not in it.structured["digits"] or it.structured["first"] != "any" or "may be 0" in q
            if it.structured["first"] == "any" and 0 in it.structured["digits"]:
                assert "the first digit may be 0 (a code such as 012 is allowed)" in q
            assert ("no digit may be used more than once" in q) != ("a digit may be used more than once" in q)


def test_power_remainder_states_the_meaning_of_the_power_and_the_remainder_range() -> None:
    lin = ALL["M1.last_digit_power_r3"]
    rng = stream(411204, "pr")
    for _ in range(100):
        it = build_item(lin, 3, rng, "A", "t")
        assert "factors, each equal to" in it.question or "factors equal to" in it.question
        assert f"(a whole number from 0 to {it.structured['modulus'] - 1})" in it.question
        assert verify("last_digit_power", it.structured) == it.answer


def test_conventions_are_stated_where_an_answer_depends_on_them() -> None:
    def q(lid: str, lv: int) -> str:
        return build_item(ALL[lid], lv, stream(411205, lid, str(lv)), "A", "t").question

    assert "both included" in q("M1.arithmetic_series_r3", 2)
    assert "(counting from the moment they all flashed)" in "".join(build_item(ALL["M1.gcd_lcm_r3"], 1, stream(411206, str(i)), "A", "t").question for i in range(20))
    assert "write a minus sign" in q("M1.linear_equation_r3", 1) and "write a minus sign" in q("M1.consecutive_r3", 1)
    assert "each 'do both' number includes the people who do all three" in q("M1.inclusion_exclusion_r3", 4)
    assert "calculated on the bill before tip" in q("M1.tip_split_r3", 1)
    assert "each change applied to the price just before it" in q("M1.percent_change_r3", 1)
    assert "not counting the waiting between legs" in q("M1.clock_duration_r3", 1)
    assert "position 1 is the first number" in q("M1.recurrence_iterate_r3", 1)
    assert "whole numbers of years" in q("M1.ages_r3", 1)
    assert "Answer in dollars" in q("M1.shopping_r3", 0) or "How many dollars" in q("M1.shopping_r3", 0)
