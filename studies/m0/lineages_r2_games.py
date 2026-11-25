# ruff: noqa: E501
"""R2 batch 1, family "games": win/lose labelling of positions by backward induction."""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_r2_common import batch1, until


def first_player_wins(n: int, moves: list[int]) -> bool:
    win = [False] * (n + 1)
    for s in range(1, n + 1):
        win[s] = any(m <= s and not win[s - m] for m in moves)
    return win[n]


@batch1("games")
def subtraction_game(level: int, r: random.Random) -> Built:
    """Procedure: label every pile size win/lose from small to large (a size is a win when some allowed move reaches a losing size). structured: {"n": int, "moves": [int]}.
    Answer: yes/no, does the player who moves first win with perfect play. A player who cannot move loses. The wanted answer is drawn 50/50 per item; in 70% of items the "pile size mod (largest move + 1)" rule is wrong."""
    top = 6 + level
    want = r.choice(("yes", "no"))

    def make() -> tuple[int, list[int]]:
        return r.randint(12, 40 + 8 * level), sorted(r.sample(range(1, top + 1), r.randint(2, 4)))

    def ok(nm: tuple[int, list[int]]) -> bool:
        n, moves = nm
        return first_player_wins(n, moves) == (want == "yes") and (("no" if n % (max(moves) + 1) == 0 else "yes") != want or r.random() < 0.3)

    n, moves = until(500, make, ok)
    q = (f"Two players take turns removing stones from one pile of {n} stones. On a turn a player must remove one of these amounts of stones: {" or ".join(str(m) for m in moves)}; an amount can be chosen only if the pile still has at least that many stones. "
         "A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.")
    return Built(q, {"n": n, "moves": moves}, want, "yn", 2)
