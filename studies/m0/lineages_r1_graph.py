# ruff: noqa: E501
"""R1 pilot, family "graph" (intended part B): weighted shortest route (Dijkstra-style) and two-colouring (odd-cycle) tests."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import NAMES, TOWNS


@pilot("graph", "B")
def graph_shortest_route(level: int, r: random.Random) -> Built:
    """structured: {"towns": [name], "roads": [[a, b, length]] (two-way), "start": name, "end": name}. The shortest route from start to end is
    unique and has at least two roads. Answer: the town reached first after leaving `start` on that route."""
    n = 5 + (level + 1) // 2
    towns = r.sample(TOWNS, n)
    edges: dict[tuple[int, int], int] = {}
    for i in range(1, n):
        j = r.randrange(i)
        edges[(j, i)] = r.randint(1, 15)
    for _ in range(n // 2 + 1):
        a, b = sorted(r.sample(range(n), 2))
        edges.setdefault((a, b), r.randint(1, 15))
    s, t = r.sample(range(n), 2)
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(n)}
    for (a, b), w in edges.items():
        adj[a].append((b, w))
        adj[b].append((a, w))
    inf = 10**9
    dist, cnt, prev, done = [inf] * n, [0] * n, [-1] * n, [False] * n
    dist[s], cnt[s] = 0, 1
    for _ in range(n):
        u = min((i for i in range(n) if not done[i]), key=lambda i: dist[i], default=-1)
        if u < 0 or dist[u] == inf:
            break
        done[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v], cnt[v], prev[v] = dist[u] + w, cnt[u], u
            elif dist[u] + w == dist[v]:
                cnt[v] += cnt[u]
    if dist[t] == inf or cnt[t] != 1:
        raise Retry
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    path.reverse()
    if len(path) < 3:
        raise Retry
    roads = [[towns[a], towns[b], w] for (a, b), w in edges.items()]
    r.shuffle(roads)
    q = (" ".join(f"There is a two-way road between {a} and {b} of length {w}." for a, b, w in roads)
         + f" You drive from {towns[s]} to {towns[t]} along the route with the smallest total length. Which town do you reach first after leaving {towns[s]}? Choose from {and_(sorted(x for x in towns if x != towns[s]))}.")
    return Built(q, {"towns": towns, "roads": roads, "start": towns[s], "end": towns[t]}, towns[path[1]], "name", n - 1)


def _two_colourable(n: int, edges: list[tuple[int, int]]) -> bool:
    colour = [-1] * n
    for s in range(n):
        if colour[s] >= 0:
            continue
        colour[s] = 0
        stack = [s]
        while stack:
            u = stack.pop()
            for a, b in edges:
                for x, y in ((a, b), (b, a)):
                    if x == u:
                        if colour[y] < 0:
                            colour[y] = 1 - colour[u]
                            stack.append(y)
                        elif colour[y] == colour[u]:
                            return False
    return True


@pilot("graph", "B")
def graph_bipartite(level: int, r: random.Random) -> Built:
    """structured: {"people": [name], "rivals": [[a, b]]}. Answer yes/no: can everyone be split into two teams so that no two rivals share a team."""
    n = 4 + level
    people = r.sample(NAMES, n)
    side = [r.randrange(2) for _ in range(n)]
    if len(set(side)) < 2:
        raise Retry
    cross = [(i, j) for i in range(n) for j in range(i + 1, n) if side[i] != side[j]]
    edges = r.sample(cross, min(len(cross), n - 1 + r.randint(0, n // 2)))
    want = r.choice(("yes", "no"))
    if want == "no":
        same = [(i, j) for i in range(n) for j in range(i + 1, n) if side[i] == side[j]]
        if not same:
            raise Retry
        edges = [*edges, r.choice(same)]
    if _two_colourable(n, edges) != (want == "yes"):
        raise Retry
    rivals = [[people[a], people[b]] for a, b in edges]
    r.shuffle(rivals)
    q = (f"{and_(sorted(people))} must be split into two teams. " + " ".join(f"{a} and {b} are rivals." for a, b in rivals)
         + " Can they be split into two teams (either team may be any size) so that no two rivals are on the same team? Answer yes or no.")
    return Built(q, {"people": people, "rivals": rivals}, want, "yn", 2)
