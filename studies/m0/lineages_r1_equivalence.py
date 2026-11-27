# ruff: noqa: E501
"""R1 pilot, family "equivalence" (intended part B): union of "same" statements with "different" statements, and exchange-rate propagation."""

from __future__ import annotations

import random
from math import gcd

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import YNU, and_, pilot
from studies.m0.vocab import OBJECTS, PSEUDO


@pilot("equivalence", "B")
def equivalence_classes(level: int, r: random.Random) -> Built:
    """structured: {"items": [name], "same": [[a, b]], "different": [[a, b]], "x": name, "y": name}. Answer: yes if x and y are forced to be the
    same thing (a chain of `same`), no if they are forced to be different (their groups have a `different` statement between them),
    otherwise cannot be determined."""
    n = 5 + level
    items = r.sample(PSEUDO, n)
    m = max(2, n // 2)
    cls = [r.randrange(m) for _ in range(n)]
    same, diff = [], []
    for _ in range(n - m + 1 + r.randint(0, 2)):
        i, j = r.sample(range(n), 2)
        if cls[i] == cls[j]:
            same.append((i, j))
    for _ in range(2 + level // 2):
        i, j = r.sample(range(n), 2)
        if cls[i] != cls[j]:
            diff.append((i, j))
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in same:
        parent[find(i)] = find(j)
    forced = {(find(i), find(j)) for i, j in diff} | {(find(j), find(i)) for i, j in diff}
    want = r.choice(YNU)
    cands = []
    for i in range(n):
        for j in range(i + 1, n):
            a = "yes" if find(i) == find(j) else ("no" if (find(i), find(j)) in forced else "cannot be determined")
            if a == want:
                cands.append((i, j))
    if not cands:
        raise Retry
    x, y = r.choice(cands)
    sents = [f"{items[i]} is the same thing as {items[j]}." for i, j in same] + [f"{items[i]} is a different thing from {items[j]}." for i, j in diff]
    r.shuffle(sents)
    q = " ".join(sents) + f" Is {items[x]} the same thing as {items[y]}? Answer yes (they must be the same), no (they must be different) or cannot be determined."
    return Built(q, {"items": items, "same": [[items[i], items[j]] for i, j in same], "different": [[items[i], items[j]] for i, j in diff], "x": items[x], "y": items[y]}, want, "ynu", 3)


@pilot("equivalence", "B")
def equivalence_exchange_rates(level: int, r: random.Random) -> Built:
    """structured: {"items": [name], "rates": [[p, a, q, b]] meaning p units of a are worth the same as q units of b}. The rates connect all items.
    Answer: the item whose single unit is worth the most (unique)."""
    n = 3 + level
    items = r.sample(OBJECTS, n)
    val = r.sample(range(1, 40), n)
    rates = []
    for i in range(1, n):
        j = r.randrange(i)
        g = gcd(val[i], val[j])
        t = r.randint(1, 3)
        rates.append([t * val[j] // g, items[i], t * val[i] // g, items[j]])  # p units of i are worth q units of j
    r.shuffle(rates)
    top = max(range(n), key=lambda i: val[i])
    q = " ".join(f"{p} units of {a} are worth the same as {qq} units of {b}." for p, a, qq, b in rates) + f" Which of {and_(sorted(items))} is worth the most per single unit?"
    return Built(q, {"items": items, "rates": rates}, items[top], "text", n)
