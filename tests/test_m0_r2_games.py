# ruff: noqa: E501
"""R2 batch 1, family games: mechanical checks and a test-local recursive cross-check (not the registered second solvers)."""

from __future__ import annotations

from functools import cache

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def test_family_checks() -> None:
    assert check_family_r2("games") == []


def test_subtraction_game_by_recursion_and_balance() -> None:
    answers = []
    for lv in ALL_LEVELS:
        r = stream(953807, "t", "sub", str(lv))
        for i in range(60):
            it = build_item(LIN["R2.subtraction_game"], lv, r, "A", f"t/{lv}/{i}")
            moves = tuple(it.structured["moves"])

            @cache
            def wins(n: int, moves: tuple[int, ...] = moves) -> bool:
                return any(m <= n and not wins(n - m) for m in moves)

            assert it.answer == ("yes" if wins(it.structured["n"]) else "no")
            answers.append(it.answer)
    assert 0.4 < answers.count("yes") / len(answers) < 0.6
