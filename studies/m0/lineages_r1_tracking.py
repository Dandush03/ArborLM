# ruff: noqa: E501
"""R1 pilot, family "tracking" (intended part B): arithmetic state tracking (balances), unlike the swap-tracking rule."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot, pl
from studies.m0.vocab import NAMES


@pilot("tracking", "B")
def tracking_accounts(level: int, r: random.Random) -> Built:
    """structured: {"start": {name: dollars}, "ops": [["pay", a, b, amount] | ["earn", a, amount] | ["half", a, b]], "ask": "most" | "least"}.
    pay moves `amount` from a to b; earn adds to a; half moves half of a's money (always an even amount) from a to b. Nobody ever goes below zero.
    Answer: the person with the most (or least) money at the end (unique)."""
    n = 3 + (level + 1) // 2
    ps = r.sample(NAMES, n)
    bal = {p: r.randint(2, 10) * 10 for p in ps}
    start = dict(bal)
    ops, text = [], []
    for _ in range(4 + 2 * level):
        kind = r.choice(("pay", "pay", "earn", "half"))
        a, b = r.sample(ps, 2)
        if kind == "half" and bal[a] % 2:
            kind = "earn"
        if kind == "pay":
            amt = r.randint(1, max(1, bal[a] // 2))
            bal[a] -= amt
            bal[b] += amt
            ops.append(["pay", a, b, amt])
            text.append(f"{a} pays {b} {pl(amt, 'dollar')}.")
        elif kind == "earn":
            amt = r.randint(5, 40)
            bal[a] += amt
            ops.append(["earn", a, amt])
            text.append(f"{a} earns {pl(amt, 'dollar')}.")
        else:
            h = bal[a] // 2
            bal[a] -= h
            bal[b] += h
            ops.append(["half", a, b])
            text.append(f"{a} gives half of their money to {b}.")
    ask = r.choice(("most", "least"))
    top = max(bal.values()) if ask == "most" else min(bal.values())
    who = [p for p in ps if bal[p] == top]
    if len(who) != 1:
        raise Retry
    q = "At the start " + ", ".join(f"{p} has {pl(start[p], 'dollar')}" for p in ps) + ". " + " ".join(text) + f" Who has the {ask} money at the end? Choose from {and_(sorted(ps))}."
    return Built(q, {"start": start, "ops": ops, "ask": ask}, who[0], "name", n)
