# ruff: noqa: E501
"""R1 pilot, family "order" (intended part B): ranking by counting results (not by transitive closure)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import NAMES


@pilot("order", "B")
def order_tournament_wins(level: int, r: random.Random) -> Built:
    """structured: {"players": [name], "results": [[winner, loser]] (every pair of players exactly once), "ask": "most" | "fewest"}.
    Answer: the player with the most (or fewest) wins; the extreme is unique in every item."""
    n = 4 + (level + 1) // 2
    ps = r.sample(NAMES, n)
    wins = {p: 0 for p in ps}
    res = []
    for i in range(n):
        for j in range(i + 1, n):
            w, lo = (ps[i], ps[j]) if r.random() < 0.5 else (ps[j], ps[i])
            wins[w] += 1
            res.append([w, lo])
    r.shuffle(res)
    ask = r.choice(("most", "fewest"))
    top = max(wins.values()) if ask == "most" else min(wins.values())
    best = [p for p in ps if wins[p] == top]
    if len(best) != 1:
        raise Retry
    q = (f"{and_(sorted(ps))} played a round-robin: every pair of them played exactly one game and there were no draws. " + " ".join(f"{a} beat {b}." for a, b in res)
         + f" Who won the {'most' if ask == 'most' else 'fewest'} games?")
    return Built(q, {"players": ps, "results": res, "ask": ask}, best[0], "name", n)
