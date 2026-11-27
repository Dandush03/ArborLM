# ruff: noqa: E501
"""M1 batch 1, family "statistics": the median (sort and select) and the mode (tally and select)."""

from __future__ import annotations

import random
from fractions import Fraction

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1 import fmt
from studies.m0.lineages_m1_common import DECIMAL, WHOLE, and_, m1


@m1("statistics")
def median_list(level: int, r: random.Random) -> Built:
    """structured: {"shape": "list" | "table", "values": [numbers in the order printed] (list) or [[value, how_many], ...] (table)}.
    Answer: the median: sort all the values (a table row counts `how_many` times); the middle value if the count is odd, the mean of the two middle values if even."""
    shape = "table" if level >= 3 and r.random() < 0.5 else "list"
    hi = 30 + 20 * level
    if shape == "list":
        n = r.randint(5 + level, 8 + 2 * level)
        vals = [r.randint(1, hi) for _ in range(n)]
        s = sorted(vals)
        total = n
        body = f"The values are {and_([str(v) for v in vals])}."
        st: dict[str, object] = {"shape": shape, "values": vals}
    else:
        rows = r.randint(4, 5 + level // 2)
        vs = sorted(r.sample(range(1, hi), rows))
        r.shuffle(vs)
        tab = [[v, r.randint(1, 6)] for v in vs]
        s = sorted(v for v, c in tab for _ in range(c))
        total = len(s)
        if Fraction(s[(total - 1) // 2] + s[total // 2], 2) == Fraction(sorted(vs)[(rows - 1) // 2] + sorted(vs)[rows // 2], 2):
            raise Retry
        body = "The table shows each value and how many times it occurs: " + "; ".join(f"the value {v} occurs {pl_times(c)}" for v, c in tab) + "."
        st = {"shape": shape, "values": tab}
    mid = Fraction(s[(total - 1) // 2] + s[total // 2], 2)
    if mid.denominator not in (1, 2):
        raise Retry
    q = f"{body} What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, the number halfway between them)? {DECIMAL}"
    return Built(q, st, fmt(mid), "number", None)


def pl_times(c: int) -> str:
    return "once" if c == 1 else f"{c} times"


@m1("statistics", "borderline")
def mode_tally(level: int, r: random.Random) -> Built:
    """structured: {"values": [numbers in the order printed], "ask": "mode" | "mode_count"}. Tally how often each value occurs; the most frequent value is unique in every item.
    Answer: that value ("mode"), or how many times it occurs ("mode_count"). The printed order is drawn so that the first value to repeat is the mode in only a minority of items.
    Borderline against median_list (statistic of a list; here the procedure is a tally, not a sort)."""
    hi = 12 + 6 * level
    f = r.randint(3, 5 + level)
    m = r.randint(4, 6 + level)
    pool = r.sample(range(1, hi + 1), m)
    counts = [f] + [r.randint(1, f - 1) for _ in range(m - 1)]
    vals = [v for v, c in zip(pool, counts, strict=True) for _ in range(c)]
    r.shuffle(vals)
    n = len(vals)
    first_rep = next(v for i, v in enumerate(vals) if v in vals[:i])
    if first_rep == pool[0] and r.random() < 0.85:
        raise Retry
    ask = r.choice(("mode", "mode_count"))
    ans = pool[0] if ask == "mode" else f
    what = "Which value occurs most often? There is exactly one such value." if ask == "mode" else "How many times does the most frequent value occur? There is exactly one most frequent value."
    q = f"A teacher wrote down {n} test scores: {and_([str(v) for v in vals])}. {what} {WHOLE}"
    return Built(q, {"values": vals, "ask": ask}, str(ans), "number", None)
