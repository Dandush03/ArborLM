# ruff: noqa: E501
"""R1 pilot, family "elimination" (intended part A): circular counting-out and a knockout bracket (tree evaluation)."""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import NAMES


@pilot("elimination", "A")
def elimination_josephus(level: int, r: random.Random) -> Built:
    """structured: {"people": [name] in circle order (after the last comes the first), "step": k, "ask": ["last"] | ["leave", j]}.
    Counting starts at the first person as 1; the k-th person counted leaves, and counting restarts at the next person still in
    the circle. Answer: the last person left, or the j-th person to leave."""
    n = 4 + level
    people = r.sample(NAMES, n)
    k = r.randint(2, 5)
    circle, pos, out = list(people), 0, []
    while circle:
        pos = (pos + k - 1) % len(circle)
        out.append(circle.pop(pos))
        if circle:
            pos %= len(circle)
    if r.random() < 0.5:
        ask, ans, qs = ["last"], out[-1], "Who is the last person left in the circle?"
    else:
        j = r.randint(1, n - 1)
        ask, ans, qs = ["leave", j], out[j - 1], f"Who is number {j} to leave the circle (number 1 is the first to leave)?"
    q = (f"{and_(people)} stand in a circle in this order, and after {people[-1]} comes {people[0]} again. Counting starts at {people[0]} as 1 and goes around in that order. "
         f"Every time the count reaches {k}, the person counted leaves the circle, and counting starts again from 1 at the next person still in the circle. {qs}")
    return Built(q, {"people": people, "step": k, "ask": ask}, ans, "name", n)


@pilot("elimination", "A")
def elimination_bracket(level: int, r: random.Random) -> Built:
    """structured: {"players": [[name, rating]] in bracket order, "ask": ["runner_up"] | ["beaten_by", name]}. Adjacent players meet in round
    one, the higher rating always wins, winners keep their order and are paired adjacent again. Answer: the loser of the final, or the
    player who knocked the named player out."""
    size = 4 if level <= 2 else (8 if level <= 5 else 16)
    names = r.sample(NAMES, size)
    rating = dict(zip(names, r.sample(range(10, 100), size), strict=True))
    rnd, beaten_by = names[:], {}
    final_loser = ""
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2], strict=True):
            w, lo = (a, b) if rating[a] > rating[b] else (b, a)
            beaten_by[lo] = w
            nxt.append(w)
            if len(rnd) == 2:
                final_loser = lo
        rnd = nxt
    champion = rnd[0]
    if r.random() < 0.5:
        ask, ans, qs = ["runner_up"], final_loser, "Who loses the final?"
    else:
        who = r.choice([p for p in names if p != champion])
        ask, ans, qs = ["beaten_by", who], beaten_by[who], f"Who knocks {who} out?"
    q = (f"A knockout tournament has {size} players listed in bracket order: " + ", ".join(f"{p} (rating {rating[p]})" for p in names)
         + ". In round one the first two listed play each other, the next two play each other, and so on. The player with the higher rating always wins. "
         "The winners keep their order and are paired the same way in the next round, until one player is left. " + qs)
    return Built(q, {"players": [[p, rating[p]] for p in names], "ask": ask}, ans, "name", size)
