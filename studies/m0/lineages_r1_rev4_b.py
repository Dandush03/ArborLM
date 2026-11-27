# ruff: noqa: E501
"""R1 revision 4, part 2: algorithm shapes (second audit AUDIT_M0_R1_2.md; lead rulings R-1). No redraw on a heuristic's outcome in any shape here.

graph_shortest_route_r4     a planted shortest route of a level-set number of roads (potentials make every other route strictly longer; decoy towns near the route are joined to it by short roads, so the nearest neighbour of the start is not on the route)
activity_selection_r4       the meetings are built from zones, each a known trap for one wrong rule (shortest first, earliest start) or a plain meeting; every item has both traps
mst_cost_r4                 towns in groups joined by dearer roads than any road inside a group, so each town's cheapest road and the n-1 cheapest roads never give the answer
order_compare_r4            the asked pair is stated in neither direction; the answer is drawn first
spatial_relative_directions_r4  asks the street distance between two places that no fact links directly (an open number), not the farthest place
conditional_decision_tree_r4  each action sits at the same number of leaves, so no action is more likely from how often it is named
temporal_critical_path_r4   asks the day on which the last job finishes (an open number) instead of who finishes last (the answer was always a job nobody waits for)
minimax_tree_r4             every level has its own depth and branching; the first mover is drawn; leaf payoffs are signed
nim_xor_r4                  an even number of piles all of the same size class (never one larger than the rest together), the total always even; levels differ in piles and size
venn_counting_r4            levels differ in the number of groups (2 to 4) and in what is asked (none, exactly one, exactly two, at least two)
topological_order_r4        denser prerequisites (one to three each), so the order is nearly forced and the alphabetical rule rarely decides
"""

from __future__ import annotations

import heapq
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pl
from studies.m0.lineages_r1_rev4_common import rev4
from studies.m0.vocab import NAMES, TOWNS

# ---------------------------------------------------------------- graph


@rev4("graph", "R1.graph_shortest_route_r2")
def graph_shortest_route_r4(level: int, r: random.Random) -> Built:
    """structured: {"towns", "roads": [[a, b, length]] (two-way), "start", "end", "planted_roads": h}. Answer: the smallest total length of a route from start to end (open number). The route
    is PLANTED with h = (3, 3, 4, 4, 5, 5, 6)[level] roads: every town gets a potential (the spine towns the running length along the route, the decoy towns a value within 1 of a spine town) and every road has
    length >= the difference of its ends' potentials, with equality only on the spine, so any other route is strictly longer. The shortest route therefore has exactly h roads at every level
    (the earlier shape: two roads in 58 to 77 % of the items at every level), and a direct road start-end, if present, is strictly longer than the answer."""
    h = (3, 3, 4, 4, 5, 5, 6)[level]
    n = h + 1 + 2 + level // 2
    towns = r.sample(TOWNS, n)
    spine = towns[: h + 1]
    w = [r.randint(3, 9) for _ in range(h)]
    pot = {spine[0]: 0}
    for i in range(h):
        pot[spine[i + 1]] = pot[spine[i]] + w[i]
    total = pot[spine[h]]
    edges: dict[frozenset[str], int] = {frozenset((spine[i], spine[i + 1])): w[i] for i in range(h)}
    for t in towns[h + 1 :]:  # decoy towns sit near a spine town (potential within 1) and are joined to it by a road that is often cheaper than the spine's own roads
        anchor = r.choice(spine)
        pot[t] = pot[anchor] + r.randint(-1, 1)
        edges.setdefault(frozenset((t, anchor)), abs(pot[t] - pot[anchor]) + r.randint(1, 3))
    for _ in range(n):
        a, b = r.sample(towns, 2)
        edges.setdefault(frozenset((a, b)), abs(pot[a] - pot[b]) + r.randint(1, 6))
    roads = [[*sorted(e), wt] for e, wt in edges.items()]
    r.shuffle(roads)
    s, t = spine[0], spine[h]
    q = " ".join(f"There is a two-way road between {a} and {b} of length {wt}." for a, b, wt in roads) + f" What is the smallest total length of a route from {s} to {t} along these roads?"
    return Built(q, {"towns": towns, "roads": roads, "start": s, "end": t, "planted_roads": h}, str(total), "number", None)


# ---------------------------------------------------------------- activity selection


@rev4("scheduling", "R1.activity_selection")
def activity_selection_r4(level: int, r: random.Random) -> Built:
    """structured: {"meetings": [[name, start, end]]}. A person can attend several meetings if they do not overlap (a meeting that ends exactly when another starts is fine). Answer: the largest
    number of meetings one person can attend (open number). The day is a row of zones; each zone is one of: A, two long meetings that touch plus a short one across the join (the shortest-first
    rule loses one there); B, one long early meeting over two to four short ones (the earliest-start rule gets one where the answer is the number of shorts); C, a single meeting; D, three meetings
    with random overlaps. Every item has at least one A zone and one B zone, so shortest-first and earliest-start are wrong in every item and by a varying amount (the earlier shape: shortest-first
    right in 93 % of the items). The answer is computed by the earliest-finish rule over all meetings and checked against the zone-wise sum."""
    nz = 3 + level
    kinds = ["A", "B"] + [r.choice("ABCD") for _ in range(nz - 2)]
    r.shuffle(kinds)
    ms: list[tuple[int, int]] = []
    t = r.randint(0, 5)
    planned = 0
    for k in kinds:
        if k == "A":
            x, y = r.randint(1, 3), r.randint(1, 3)
            a, b = x + y + r.randint(1, 6), x + y + r.randint(1, 6)  # both long meetings are strictly longer than the short one that crosses their join
            ms += [(t, t + a), (t + a, t + a + b), (t + a - x, t + a + y)]
            t += a + b
            planned += 2
        elif k == "B":
            m = r.randint(2, 4)
            widths = [r.randint(2, 4) for _ in range(m)]
            gaps = [r.randint(0, 2) for _ in range(m + 1)]
            cur = t + 1 + gaps[0]
            for i in range(m):
                ms.append((cur, cur + widths[i]))
                cur += widths[i] + gaps[i + 1]
            ms.append((t, cur + r.randint(0, 1)))
            t = max(e for _, e in ms)
            planned += m
        elif k == "C":
            d = r.randint(2, 8)
            ms.append((t, t + d))
            t += d
            planned += 1
        else:
            seg = [(t + r.randint(0, 6), 0) for _ in range(3)]
            seg = [(s0, s0 + r.randint(2, 7)) for s0, _ in seg]
            ms += seg
            best = 0
            last = -1
            for s0, e0 in sorted(seg, key=lambda z: (z[1], z[0])):
                if s0 >= last:
                    best += 1
                    last = e0
            planned += best
            t = max(e for _, e in seg)
        t += r.randint(1, 3)  # a gap: the zones do not touch
    chosen, last = 0, -1
    for s0, e0 in sorted(ms, key=lambda z: (z[1], z[0])):
        if s0 >= last:
            chosen += 1
            last = e0
    if chosen != planned:
        raise Retry
    ps = r.sample(NAMES, len(ms))
    items = [[p, s0, e0] for p, (s0, e0) in zip(ps, ms, strict=True)]
    r.shuffle(items)
    q = " ".join(f"{p}'s meeting runs from minute {s0} to minute {e0}." for p, s0, e0 in items) + " A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?"
    return Built(q, {"meetings": items, "zones": kinds}, str(chosen), "number", None)


# ---------------------------------------------------------------- minimum spanning tree


@rev4("network", "R1.mst_cost")
def mst_cost_r4(level: int, r: random.Random) -> Built:
    """structured: {"towns", "roads": [[a, b, length]], "groups": [[town]]}. Answer: the smallest total length of roads that connect every town to every other (open number). The towns are in
    2 to 4 groups of at least 3 (the groups are not stated); every pair inside a group is joined by a road of length 1 to 9, and groups are joined by roads of length 11 to 20 only. So each
    town's cheapest road lies inside its group and the n - 1 cheapest roads all lie inside groups, whence neither "sum of each town's cheapest road" nor "sum of the n - 1 cheapest roads" is a
    spanning tree: both differ from the answer in every item (the earlier shape: 0.93 at level 0)."""
    g = 2 + level // 3
    sizes = [r.randint(3, 4 if level >= 3 else 3) for _ in range(g)]
    n = sum(sizes)
    towns = r.sample(TOWNS, n)
    groups, i = [], 0
    for sz in sizes:
        groups.append(towns[i : i + sz])
        i += sz
    edges: dict[tuple[str, str], int] = {}

    def put(a: str, b: str, w: int) -> None:  # one road per pair of towns, whichever way round it was drawn
        edges.setdefault((min(a, b), max(a, b)), w)

    for grp in groups:
        for a in range(len(grp)):
            for b in range(a + 1, len(grp)):
                put(grp[a], grp[b], r.randint(1, 9))
    for a in range(g - 1):  # a path of groups, then extra links
        put(r.choice(groups[a]), r.choice(groups[a + 1]), r.randint(11, 20))
    for _ in range(g + level // 2):
        a, b = r.sample(range(g), 2)
        put(r.choice(groups[a]), r.choice(groups[b]), r.randint(11, 20))
    idx = {t: j for j, t in enumerate(towns)}
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    total = 0
    for (a, b), wt in sorted(edges.items(), key=lambda kv: (kv[1], kv[0])):
        if find(idx[a]) != find(idx[b]):
            parent[find(idx[a])] = find(idx[b])
            total += wt
    roads = [[a, b, wt] for (a, b), wt in edges.items()]
    r.shuffle(roads)
    q = (" ".join(f"A road between {a} and {b} could be built with length {wt}." for a, b, wt in roads)
         + " Some of these roads will be built so that every town can be reached from every other town, using as few roads as possible and the smallest possible total length. What is that total length?")
    return Built(q, {"towns": towns, "roads": roads, "groups": groups}, str(total), "number", None)


# ---------------------------------------------------------------- order


@rev4("order", "R1.order_compare")
def order_compare_r4(level: int, r: random.Random) -> Built:
    """Same schema as order_compare: {"taller": [[a, b]] (a is taller than b), "x", "y"}. The asked pair is stated in NEITHER direction (the earlier shape: the asked or the reverse pair was
    stated in 55.8 % of the items, always giving yes or no), the asked x is stated taller than someone and the asked y shorter than someone (so "x is never taller than anyone" and its mirror never apply), and the answer is drawn first (uniform over yes, no, cannot be determined); the pair is then
    drawn uniformly among the pairs with that answer."""
    n = 7 + level
    order = r.sample(NAMES, n)
    want = r.choice(YNU_)
    for _ in range(600):
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        given = r.sample(pairs, min(len(pairs), n - 1 + r.randint(0, 1)))
        m = [[i == j for j in range(n)] for i in range(n)]
        for a, b in given:
            m[a][b] = True
        for k in range(n):
            for i in range(n):
                if m[i][k]:
                    for j in range(n):
                        if m[k][j]:
                            m[i][j] = True
        stated = {frozenset(p) for p in given}
        tall = {a for a, _ in given}  # people stated taller than someone
        short = {b for _, b in given}  # people stated shorter than someone
        cands = []
        for x in tall:
            for y in short:
                if x == y or frozenset((x, y)) in stated:
                    continue
                a = "yes" if m[x][y] else ("no" if m[y][x] else "cannot be determined")
                if a == want:
                    cands.append((x, y))
        if cands:
            break
    else:
        raise Retry
    x, y = r.choice(sorted(cands))
    facts = [(order[i], order[j]) for i, j in given]
    r.shuffle(facts)
    q = " ".join(f"{p} is taller than {s}." for p, s in facts) + f" Is {order[x]} taller than {order[y]}? Answer yes, no or cannot be determined."
    return Built(q, {"taller": [list(f) for f in facts], "x": order[x], "y": order[y]}, want, "ynu", 3)


YNU_ = ("yes", "no", "cannot be determined")


# ---------------------------------------------------------------- spatial


_STEP = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
_OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


@rev4("spatial", "R1.spatial_relative_directions")
def spatial_relative_directions_r4(level: int, r: random.Random) -> Built:
    """structured: {"places", "facts": [[a, direction, k, b]] (a lies k blocks <direction> of b), "x", "y"}. Streets form a grid. Answer: the street distance between x and y (blocks north or
    south plus blocks east or west; an open number), where x and y are joined by no fact (at least two facts lie between them) and the distance is at least 1. The earlier shape asked for the
    farthest place from an anchor; the farthest place was a leaf of the fact tree (least mentioned 0.383 against 0.245)."""
    n = 5 + level
    places = r.sample(TOWNS, n)
    xy = {places[0]: (0, 0)}
    facts = []
    nb: dict[str, set[str]] = {p: set() for p in places}
    for i in range(1, n):
        parent = places[r.randrange(i)]
        d = r.choice(list(_STEP))
        k = r.randint(1, 9)
        xy[places[i]] = (xy[parent][0] + _STEP[d][0] * k, xy[parent][1] + _STEP[d][1] * k)
        facts.append([places[i], d, k, parent] if r.random() < 0.5 else [parent, _OPP[d], k, places[i]])
        nb[places[i]].add(parent)
        nb[parent].add(places[i])
    cands = []
    for a in places:
        for b in places:
            if a < b and b not in nb[a] and abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1]) >= 1:
                cands.append((a, b))
    if not cands:
        raise Retry
    a, b = r.choice(cands)
    r.shuffle(facts)
    ans = abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1])
    q = " ".join(f"{p} is {pl(k, 'block')} {d} of {o}." for p, d, k, o in facts) + f" How far apart are {a} and {b} by street distance (blocks north or south plus blocks east or west)?"
    return Built(q, {"places": places, "facts": facts, "x": a, "y": b}, str(ans), "number", None)


# ---------------------------------------------------------------- conditional decision tree


@rev4("conditional", "R1.conditional_decision_tree")
def conditional_decision_tree_r4(level: int, r: random.Random) -> Built:
    """Same schema as conditional_decision_tree: {"tree", "facts", "actions"}. Four actions (eight at level 6); the leaves of the tree (2^depth of them, depth = 3, 3, 4, 4, 4, 5, 5 by level) carry each action the same
    number of times (the leaf actions are a shuffled list with equal counts), so how often an action is named says nothing about which is reached (earlier shape: the most-mentioned
    action was right 0.408 of the time against 0.271)."""
    from studies.m0.lineages_r1_conditional import ACTIONS
    from studies.m0.vocab import PSEUDO

    depth = (3, 3, 4, 4, 4, 5, 5)[level]
    attrs = [f"the {w} light is on" for w in r.sample(PSEUDO, depth + 2)]
    na = 8 if level == 6 else 4
    actions = r.sample(ACTIONS, na)
    leaf_actions = actions * (2**depth // na)
    r.shuffle(leaf_actions)
    it = iter(leaf_actions)

    def grow(d: int, avail: list[str]) -> list:
        if d == 0:
            return ["do", next(it)]
        a = r.choice(avail)
        rest = [x for x in avail if x != a]
        return ["if", a, grow(d - 1, rest), grow(d - 1, rest)]

    tree = grow(depth, attrs)
    facts = {a: r.random() < 0.5 for a in attrs}
    node = tree
    while node[0] == "if":
        node = node[2] if facts[node[1]] else node[3]

    def render(n: list) -> str:
        return n[1] if n[0] == "do" else f"if {n[1]}, then ({render(n[2])}), otherwise ({render(n[3])})"

    state = "; ".join(f"it is {'true' if v else 'false'} that {a}" for a, v in sorted(facts.items()))
    q = f"Your rule is: {render(tree)}. Right now, {state}. What do you do? Choose from {and_(sorted(actions))}."
    return Built(q, {"tree": tree, "facts": facts, "actions": sorted(actions)}, node[1], "text", na)


# ---------------------------------------------------------------- critical path


@rev4("temporal", "R1.temporal_critical_path")
def temporal_critical_path_r4(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[person, days, [persons it waits for]]]}. A job with no wait starts on day 0, otherwise it starts the day all its predecessors are finished and lasts its number of days.
    Answer: the day on which the last job finishes (an open number; day 0 is the start). The earlier shape asked WHO finishes last, so the answer was always a job nobody waits for and the
    longest job (+0.12) or the deepest job (0.72) pointed at it; a number has neither tell. Jobs: 4 + level; each waits for 0 to 2 earlier jobs; durations 1 to 15."""
    n = 4 + level
    people = r.sample(NAMES, n)
    jobs, finish = [], {}
    for i, p in enumerate(people):
        deps = r.sample(people[:i], min(i, r.choice((0, 1, 1, 2)))) if i else []
        d = r.randint(1, 15)
        jobs.append([p, d, sorted(deps)])
        finish[p] = max([finish[x] for x in deps], default=0) + d
    order = jobs[:]
    r.shuffle(order)
    text = [f"{p}'s job takes {pl(d, 'day')} and starts on day 0." if not deps else f"{p}'s job takes {pl(d, 'day')} and starts as soon as {'the job of ' + deps[0] + ' is' if len(deps) == 1 else 'the jobs of ' + and_(deps) + ' are all'} finished." for p, d, deps in order]
    q = " ".join(text) + " Counting the start as day 0, on which day is the last of these jobs finished?"
    return Built(q, {"jobs": jobs}, str(max(finish.values())), "number", None)


# ---------------------------------------------------------------- game trees, nim, venn


_TREE_SHAPE = [(2, 2), (2, 3), (3, 2), (2, 4), (3, 3), (4, 2), (3, 4)]  # (depth, branching) per level: every level its own generator


@rev4("games", "R1.minimax_tree")
def minimax_tree_r4(level: int, r: random.Random) -> Built:
    """structured: {"tree": nested list (a leaf is an integer payoff to Max; an inner node lists its options), "first": "max" | "min", "depth", "branching"}. Every level has its own depth and
    branching: (2,2) (2,3) (3,2) (2,4) (3,3) (4,2) (3,4) for levels 0 to 6 (earlier shape: levels 0 to 2 identical, 3 and 4, 5 and 6). The first mover is drawn (Max or Min); leaves are signed
    integers from -9 to 9. Answer: the payoff under perfect play (open number)."""
    depth, br = _TREE_SHAPE[level]
    first = r.choice(("max", "min"))

    def grow(d: int) -> object:
        return r.randint(-9, 9) if d == 0 else [grow(d - 1) for _ in range(br)]

    tree = grow(depth)

    def val(t: object, maxing: bool) -> int:
        if isinstance(t, int):
            return t
        vals = [val(c, not maxing) for c in t]  # type: ignore[attr-defined]
        return max(vals) if maxing else min(vals)

    def txt(t: object) -> str:
        return str(t) if isinstance(t, int) else "(" + " or ".join(txt(c) for c in t) + ")"  # type: ignore[attr-defined]

    ans = val(tree, first == "max")
    second = "Min" if first == "max" else "Max"
    q = (f"Two players, Max and Min, play a game with {depth} choices in a row, {first.capitalize()} choosing first and then {second}, and so on in turn. At each choice the mover picks one of the {br} options shown. "
         f"The game is written as nested options: {txt(tree)}. When the options are all numbers, the number picked is the payoff. Max wants the payoff as large as possible and Min as small as possible, and both play perfectly. What is the payoff?")
    return Built(q, {"tree": tree, "first": first, "depth": depth, "branching": br}, str(ans), "number", None)


_NIM_SHAPE = [(4, 32), (4, 64), (4, 128), (6, 64), (6, 128), (8, 64), (8, 128)]  # (piles, size class m: piles in [m, 2m)) per level


@rev4("games", "R1.nim_xor")
def nim_xor_r4(level: int, r: random.Random) -> Built:
    """structured: {"piles": [sizes], "size_class": m}. Two players alternate; on a turn a player removes at least one stone from ONE pile; whoever takes the last stone wins; the first player moves
    first. Answer "first" or "second". Piles: an even number k (4, 4, 4, 6, 6, 8, 8), every pile in [m, 2m) (m = 32, 64, 128, 64, 128, 64, 128), so the largest pile is never larger than the rest together
    and the top bit is set in every pile (an odd count of them would make the xor non-zero). The answer is drawn first; "second" (xor 0): k - 1 piles drawn, the last is their xor (in [m, 2m) because k - 1
    is odd); "first": all piles drawn. The low bit of the last pile is set so the total is always even. Levels differ in the number of piles and the size class (the earlier levels differed only in size,
    and level 0 had 270 distinct pile tuples)."""
    k, m = _NIM_SHAPE[level]
    want = r.choice(("first", "second"))
    piles = [r.randint(m, 2 * m - 1) for _ in range(k - 1)]
    x = 0
    for p in piles:
        x ^= p
    if want == "second":
        last = x
        if (sum(piles) + last) % 2:
            raise Retry
    else:
        last = r.randint(m, 2 * m - 1)
        if (sum(piles) + last) % 2:
            last = last + 1 if last + 1 < 2 * m else last - 1
        if x ^ last == 0:
            raise Retry
    piles.append(last)
    r.shuffle(piles)
    q = (f"A game has {k} piles of stones: " + ", ".join(str(p) for p in piles) + ". Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). "
         "The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.")
    return Built(q, {"piles": piles, "size_class": m}, want, "word", 2)


_VENN = [(2, "none"), (2, "one"), (3, "none"), (3, "two"), (3, "atleast_two"), (4, "none"), (4, "two")]


@rev4("sets", "R1.venn_counting")
def venn_counting_r4(level: int, r: random.Random) -> Built:
    """structured: {"total", "groups", "sizes": {group: size}, "pairs": {"a|b": n}, "triples": {"a|b|c": n}, "quad": n | null, "triple": n | null (3 groups), "ask": ...}. Every person is counted once. Given the
    total, every group size, every overlap of two, of three and of four. Per level (groups, asked quantity): (2 none) (2 exactly one) (3 none) (3 exactly two) (3 at least two) (4 none) (4 exactly two)
    (earlier shape: levels differed only in magnitudes). Answer: the number of people asked for (open number)."""
    g, ask = _VENN[level]
    groups = r.sample(("chess", "choir", "diving", "poetry", "rowing", "archery", "baking"), g)
    regions = {mask: r.randint(1, 9 + 4 * level) for mask in range(1, 1 << g)}  # every region is occupied, so no group sits inside another
    none = r.randint(0, 14 + 2 * level)
    total = sum(regions.values()) + none

    def inter(idx: tuple[int, ...]) -> int:
        return sum(v for mk, v in regions.items() if all(mk >> i & 1 for i in idx))

    sizes = {groups[i]: inter((i,)) for i in range(g)}
    pairs = {f"{groups[i]}|{groups[j]}": inter((i, j)) for i in range(g) for j in range(i + 1, g)}
    triples = {f"{groups[i]}|{groups[j]}|{groups[k]}": inter((i, j, k)) for i in range(g) for j in range(i + 1, g) for k in range(j + 1, g)}
    quad = inter(tuple(range(4))) if g == 4 else None
    pop = {mk: bin(mk).count("1") for mk in regions}
    ans = {"none": none, "one": sum(v for mk, v in regions.items() if pop[mk] == 1), "two": sum(v for mk, v in regions.items() if pop[mk] == 2), "atleast_two": sum(v for mk, v in regions.items() if pop[mk] >= 2)}[ask]
    text = [f"{sizes[x]} people are in the {x} group" for x in groups] + [f"{v} are in both the {k.split('|')[0]} and the {k.split('|')[1]} groups" for k, v in pairs.items()]
    text += [f"{v} are in all of the {and_(k.split('|'))} groups" for k, v in triples.items()]
    if quad is not None:
        text.append(f"{quad} are in all four groups")
    what = {"none": "in none of these groups", "one": "in exactly one of these groups", "two": "in exactly two of these groups", "atleast_two": "in at least two of these groups"}[ask]
    q = f"Among {total} people, " + "; ".join(text) + f". Each person is counted once in each number that applies to them. How many of the people are {what}?"
    return Built(q, {"total": total, "groups": groups, "sizes": sizes, "pairs": pairs, "triples": triples, "quad": quad, "triple": (triples and next(iter(triples.values()))) if g == 3 else None, "ask": ask}, str(ans), "number", None)


# ---------------------------------------------------------------- topological order


@rev4("scheduling", "R1.topological_order_r2")
def topological_order_r4(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[name, [prerequisite names]]], "day": j}. One job is done per day; each day, among the jobs whose prerequisites are all done, the one whose name comes first in
    alphabetical order is done. Answer: the job done on day j (2 <= j <= n). Prerequisites: every job after the first has 1 to 3 of them (earlier shape: 0 to 2), so the order is nearly forced and
    the j-th name in alphabetical order rarely decides; no redraw."""
    n = 6 + level
    ps = r.sample(NAMES, n)
    jobs = [[p, sorted(r.sample(ps[:i], min(i, r.choice((1, 2, 2, 3)))))] if i else [p, []] for i, p in enumerate(ps)]
    r.shuffle(jobs)
    deps = {p: set(d) for p, d in jobs}
    done: list[str] = []
    left = {p: set(d) for p, d in deps.items()}
    heap = [p for p, d in deps.items() if not d]
    heapq.heapify(heap)
    while heap:
        p = heapq.heappop(heap)
        done.append(p)
        for q in sorted(left):
            if p in left[q]:
                left[q].discard(p)
                if not left[q] and q not in done and q not in heap:
                    heapq.heappush(heap, q)
    j = r.randint(2, n)
    text = [f"{p} has no prerequisite." if not d else f"{p} needs {and_(d)} to be done first." for p, d in jobs]
    q = (f"There are {n} jobs and one job is done each day. " + " ".join(text) + " Each day, among the jobs that can be done (all their prerequisites are already done), the job whose name comes first in alphabetical order is done."
         f" Which job is done on day {j}? Choose from {and_(sorted(ps))}.")
    return Built(q, {"jobs": jobs, "day": j}, done[j - 1], "name", n)

