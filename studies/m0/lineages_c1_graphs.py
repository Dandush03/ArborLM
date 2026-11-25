# ruff: noqa: E501
"""C1 batch 1, family "graphs" (new family): programs over adjacency lists stored as lists of lists.

Strict procedures: ``bfs_queue`` breadth-first search with an array queue (head and tail pointers) and a distance list; ``union_find_links`` a
parent array with a find loop that follows parent links to a root and a link rule that hangs one root under another.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import IDX, LIST, B, C, N, V, batch, finish, names


@batch("graphs")
def bfs_queue(level: int, r: random.Random) -> Built:
    """Breadth-first search from a start node over adjacency lists (the neighbour order inside each list is as written), with dist = -1 for
    unseen nodes and a queue array with head and tail pointers. About one edge in four is one-way. Shapes: the distance of a target node
    (always reached, so never -1), the order in which nodes were enqueued, the sum of the distances of the nodes taken off the queue, the
    node enqueued last. 5 + level nodes."""
    adj, dist, q, head, tail, u, v, k, nb, tot = names(r, 10)
    n = 5 + level
    arcs: set[tuple[int, int]] = set()
    for i in range(1, n):
        j = r.randrange(i)
        arcs.add((i, j) if r.random() < 0.5 else (j, i))
        if r.random() < 0.7:
            arcs.update({(i, j), (j, i)})
    for _ in range(r.randint(1, 1 + n // 2)):
        a, b = r.sample(range(n), 2)
        arcs.add((a, b))
        if r.random() < 0.75:
            arcs.add((b, a))
    lists: list[list[int]] = [[] for _ in range(n)]
    for a, b in sorted(arcs):
        lists[a].append(b)
    for lst in lists:
        r.shuffle(lst)
    start = r.randrange(n)
    seen, order, dd = {start}, [start], {start: 0}
    for x in order:
        for y in lists[x]:
            if y not in seen:
                seen.add(y)
                dd[y] = dd[x] + 1
                order.append(y)
    if len(order) < max(3, n - 1 - level // 2):
        raise Retry
    shape = r.choice(("target", "order", "distsum", "last"))
    target = r.choice(order[2:]) if len(order) > 2 else order[-1]
    prog: list[list] = [["set", adj, ["list", *[LIST(x) for x in lists]]], ["set", dist, LIST([-1] * n)], ["set", q, LIST([0] * n)],
                        ["setidx", q, N(0), N(start)], ["setidx", dist, N(start), N(0)], ["set", head, N(0)], ["set", tail, N(1)]]
    if shape == "distsum":
        prog.append(["set", tot, N(0)])
    pop: list[list] = [["set", u, IDX(V(q), V(head))], ["aug", head, "+", N(1)]]
    if shape == "distsum":
        pop.append(["aug", tot, "+", IDX(V(dist), V(u))])
    pop += [["set", nb, IDX(V(adj), V(u))],
            ["for", k, N(0), ["call", "len", V(nb)], 1, [["set", v, IDX(V(nb), V(k))], ["if", C("==", IDX(V(dist), V(v)), N(-1)),
              [["setidx", dist, V(v), B("+", IDX(V(dist), V(u)), N(1))], ["setidx", q, V(tail), V(v)], ["aug", tail, "+", N(1)]], []]]]]
    prog.append(["while", C("<", V(head), V(tail)), pop])
    prog.append(["print", {"target": IDX(V(dist), N(target)), "order": ["slice", V(q), N(0), V(tail), None], "distsum": V(tot), "last": IDX(V(q), B("-", V(tail), N(1)))}[shape]])
    return finish(prog)


@batch("graphs")
def union_find_links(level: int, r: random.Random) -> Built:
    """Parent array p (p[x] == x for a root); find(p, x) follows p[x] until a root. For each listed pair the two roots are found and, when
    different, one is hung under the other by a rule stated in the code (first under second, second under first, or the larger root under the
    smaller). Shapes: the root of a queried node, the whole parent array, the sum of the roots of all nodes.
    5 + level nodes and 3 + level pairs (the number of components is never asked)."""
    p, us, vs, k, a, b, x, hops = names(r, 8)
    n = 5 + level
    m = 3 + level
    pu, pv = [r.randrange(n) for _ in range(m)], []
    for u in pu:
        w = r.randrange(n)
        while w == u:
            w = r.randrange(n)
        pv.append(w)
    rule = r.choice(("first", "second", "smaller"))
    par = list(range(n))

    def find(z: int) -> int:
        while par[z] != z:
            z = par[z]
        return z

    for u, w in zip(pu, pv, strict=True):
        ra, rb = find(u), find(w)
        if ra != rb:
            if rule == "first":
                par[ra] = rb
            elif rule == "second":
                par[rb] = ra
            elif ra < rb:
                par[rb] = ra
            else:
                par[ra] = rb
    shape = r.choice(("root", "parents", "rootsum", "parents"))
    qn = r.randrange(n)
    if shape == "root" and par[qn] == qn:
        raise Retry
    fdef = ["def", "find", [p, x], [["while", C("!=", IDX(V(p), V(x)), V(x)), [["set", x, IDX(V(p), V(x))]]], ["ret", V(x)]]]
    link_first = ["setidx", p, V(a), V(b)]
    link_second = ["setidx", p, V(b), V(a)]
    link = {"first": [link_first], "second": [link_second],
            "smaller": [["if", C("<", V(a), V(b)), [link_second], [link_first]]]}[rule]
    loop = ["for", k, N(0), ["call", "len", V(us)], 1, [["set", a, ["call", "find", V(p), IDX(V(us), V(k))]], ["set", b, ["call", "find", V(p), IDX(V(vs), V(k))]],
                                                       ["if", C("!=", V(a), V(b)), link, []]]]
    prog: list[list] = [fdef, ["set", p, LIST(list(range(n)))], ["set", us, LIST(pu)], ["set", vs, LIST(pv)], loop]
    if shape == "root":
        prog.append(["print", ["call", "find", V(p), N(qn)]])
    elif shape == "parents":
        prog.append(["print", V(p)])
    else:
        prog += [["set", hops, N(0)], ["for", k, N(0), N(n), 1, [["aug", hops, "+", ["call", "find", V(p), V(k)]]]], ["print", V(hops)]]
    return finish(prog)
