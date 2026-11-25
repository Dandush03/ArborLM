# ruff: noqa: E501
"""R1 pilot, family "kinship" (intended part B): downward aggregation over a parent tree (counting grandchildren or all descendants)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import NAMES


@pilot("kinship", "B")
def kinship_descendants(level: int, r: random.Random) -> Built:
    """structured: {"people": [name], "parent": {child: parent}, "ask": "grandchildren" | "descendants"}. Every listed child has exactly one recorded
    parent; one person (the root) has none. Answer: the person with the most grandchildren (or the most descendants of any depth); unique."""
    n = 5 + level
    ps = r.sample(NAMES, n)
    parent = {ps[i]: ps[r.randrange(i)] for i in range(1, n)}
    kids: dict[str, list[str]] = {p: [] for p in ps}
    for c, p in parent.items():
        kids[p].append(c)

    def desc(p: str) -> int:
        return sum(1 + desc(c) for c in kids[p])

    ask = r.choice(("grandchildren", "descendants"))
    score = {p: (sum(len(kids[c]) for c in kids[p]) if ask == "grandchildren" else desc(p)) for p in ps}
    top = max(score.values())
    best = [p for p in ps if score[p] == top]
    if top == 0 or len(best) != 1:
        raise Retry
    facts = [f"{parent[c]} is the parent of {c}." for c in sorted(parent)]
    r.shuffle(facts)
    what = "grandchildren (children of their children)" if ask == "grandchildren" else "descendants (children, their children, and so on, all the way down)"
    q = " ".join(facts) + f" Nobody else has a recorded parent. Who has the most {what}? Choose from {and_(sorted(ps))}."
    return Built(q, {"people": ps, "parent": {c: parent[c] for c in sorted(parent)}, "ask": ask}, best[0], "name", n)
