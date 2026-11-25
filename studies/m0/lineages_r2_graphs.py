# ruff: noqa: E501
"""R2 batch 1, family "graphs": cheapest connecting network (cycle-avoiding edge selection) and deferred-acceptance matching."""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_r2_common import and_, batch1, until
from studies.m0.vocab import NAMES, TOWNS


def mst_weight(n: int, edges: list[list[int]]) -> int | None:
    """edges are [a, b, w] on 0..n-1; Kruskal; None when the graph is not connected."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total, used = 0, 0
    for a, b, w in sorted(edges, key=lambda e: e[2]):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += w
            used += 1
    return total if used == n - 1 else None


@batch1("graphs")
def cheapest_network(level: int, r: random.Random) -> Built:
    """Procedure: Kruskal-style cycle-free edge selection. structured: {"towns": [name], "cables": [[a, b, cost]] (a, b are town names)}.
    Answer: the least total cost of a set of cables that connects every town to every other (directly or through other towns). In 70% of items (drawn per item)
    neither adding up the n-1 cheapest cables nor adding up each town's cheapest cable gives the answer."""
    n = 5 + (level + 1) // 2
    towns = r.sample(TOWNS, n)
    hard = r.random() < 0.7

    def make() -> list[list[int]]:
        pairs: dict[tuple[int, int], int] = {}
        for i in range(1, n):
            pairs[(r.randrange(i), i)] = r.randint(1, 20)
        for _ in range(n // 2 + 2):
            a, b = sorted(r.sample(range(n), 2))
            pairs.setdefault((a, b), r.randint(1, 20))
        return [[a, b, w] for (a, b), w in pairs.items()]

    def best_per_town(es: list[list[int]]) -> int:
        b: dict[int, int] = {}
        for a, c, w in es:
            for t in (a, c):
                b[t] = min(b.get(t, 10**9), w)
        return sum(b.values())

    def ok(es: list[list[int]]) -> bool:
        a = mst_weight(n, es)
        return a is not None and ((not hard) or (sum(sorted(e[2] for e in es)[: n - 1]) != a and best_per_town(es) != a))

    edges = until(500, make, ok)
    ans = mst_weight(n, edges)
    assert ans is not None
    r.shuffle(edges)
    cables = [[towns[a], towns[b], w] for a, b, w in edges]
    text = " ".join(f"A cable between {a} and {b} would cost {w}." for a, b, w in cables)
    q = (f"The towns {and_(sorted(towns))} must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. {text} "
         "What is the smallest total cost of a set of cables that joins all the towns?")
    return Built(q, {"towns": towns, "cables": cables}, str(ans), "number", None)


def deferred_acceptance(prop_prefs: list[list[int]], resp_prefs: list[list[int]]) -> list[int]:
    n = len(prop_prefs)
    rank = [[0] * n for _ in range(n)]
    for j in range(n):
        for pos, i in enumerate(resp_prefs[j]):
            rank[j][i] = pos
    nxt = [0] * n
    holder: list[int | None] = [None] * n  # responder -> proposer
    free = list(range(n))
    while free:
        i = free.pop(0)
        j = prop_prefs[i][nxt[i]]
        nxt[i] += 1
        cur = holder[j]
        if cur is None:
            holder[j] = i
        elif rank[j][i] < rank[j][cur]:
            holder[j] = i
            free.append(cur)
        else:
            free.append(i)
    out = [0] * n
    for j, i in enumerate(holder):
        assert i is not None
        out[i] = j
    return out


@batch1("graphs")
def deferred_acceptance_partner(level: int, r: random.Random) -> Built:
    """Procedure: proposal-and-hold rounds (Gale-Shapley). structured: {"proposers": [name], "responders": [name], "prefs_p": {proposer: [responder best first]}, "prefs_r": {responder: [proposer best first]}, "who": proposer}.
    Answer: the responder that `who` ends up with. The end result does not depend on the order of proposals. In 70% of items (drawn per item) it is neither `who`'s first choice nor the responder who ranks `who` highest."""
    n = 3 + level // 2
    names = r.sample(NAMES, 2 * n)
    props, resps = names[:n], names[n:]
    hard = r.random() < 0.7

    def make() -> tuple[list[list[int]], list[list[int]], int]:
        return [r.sample(range(n), n) for _ in range(n)], [r.sample(range(n), n) for _ in range(n)], r.randrange(n)

    def ok(x: tuple[list[list[int]], list[list[int]], int]) -> bool:
        a, b, w = x
        o = deferred_acceptance(a, b)[w]
        best_by = min(range(n), key=lambda j: (b[j].index(w), j))
        return (not hard) or (o != a[w][0] and o != best_by)

    pp, rp, who = until(300, make, ok)
    out = deferred_acceptance(pp, rp)
    lines = " ".join(f"{props[i]} ranks {and_([resps[j] for j in pp[i]])} from best to worst." for i in range(n))
    lines2 = " ".join(f"{resps[j]} ranks {and_([props[i] for i in rp[j]])} from best to worst." for j in range(n))
    q = (f"{and_(sorted(props))} each want to be paired with one of {and_(sorted(resps))}, and each of those wants one of the first group. {lines} {lines2} "
         f"They are paired by rounds: in each round every unpaired person from the first group asks the best-ranked person (on their own list) they have not asked before; "
         "a person who is asked keeps the best-ranked asker so far and turns the others down (a person who was kept is let go if someone better asks later). Rounds go on until everyone is paired. "
         f"Who is {props[who]} paired with? Choose from {and_(sorted(resps))}.")
    structured = {"proposers": props, "responders": resps, "prefs_p": {props[i]: [resps[j] for j in pp[i]] for i in range(n)},
                  "prefs_r": {resps[j]: [props[i] for i in rp[j]] for j in range(n)}, "who": props[who]}
    return Built(q, structured, resps[out[who]], "name", n)
