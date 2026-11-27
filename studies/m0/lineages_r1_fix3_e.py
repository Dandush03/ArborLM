# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 3, part e: categories (planted syllogisms), voting, matching and game trees. Ids end in ``_r5``.

categories_follow_r5      the class (yes / no / cannot be determined) and the kind of statement are drawn first, and the premises are PLANTED so that every yes and no needs a "No" or a "Some" lifted
                          through at least one "All" on each side; the entailment is then verified with the closure of the earlier shape
instant_runoff_r5         a hidden cyclic order of the candidates: half of the voter groups rank the others by walking round it in a random direction, so transfers snowball and plurality, a top-two runoff,
                          one elimination or Borda read chance
stable_matching_r5        the earlier planting, plus a planted rotation through (almost) every proposer, so the receiver-optimal stable matching differs from the proposer-optimal one
minimax_tree_r5           larger trees at every level (at least 8 leaves)
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pl
from studies.m0.lineages_r1_fix3_common import YNU, fix3
from studies.m0.lineages_r1_rev4 import _closure_facts  # type: ignore[attr-defined]
from studies.m0.lineages_r1_rev4_c import _deferred_acceptance  # type: ignore[attr-defined]
from studies.m0.vocab import NAMES, PSEUDO


def _plant_categories(r: random.Random, level: int, kind: str, want: str) -> tuple[int, list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int]], int, int]:
    """One planted premise set for (kind, want): returns (number of groups, All edges, No pairs, Some pairs, x, y)."""
    cnt = [0]
    all_e: list[tuple[int, int]] = []
    no_p: list[tuple[int, int]] = []
    some_p: list[tuple[int, int]] = []

    def new() -> int:
        cnt[0] += 1
        return cnt[0] - 1

    def chain(start: int, steps: int) -> int:
        cur = start
        for _ in range(steps):
            nxt = new()
            all_e.append((cur, nxt))
            cur = nxt
        return cur

    lo, hi = 1, 1 + level // 2
    if kind == "all" and want == "yes":
        x = new()
        y = chain(x, r.randint(2, 2 + level))
    elif (kind, want) in (("all", "no"), ("none", "yes"), ("some", "no")):  # x and y lie below the two ends of a "No a are b" premise
        x, y = new(), new()
        no_p.append((chain(x, r.randint(lo, hi)), chain(y, r.randint(lo, hi))))
    elif (kind, want) in (("none", "no"), ("some", "yes")):  # x and y overlap
        if r.random() < 0.5:  # a common member group w below both
            w = new()
            x, y = chain(w, r.randint(lo, hi)), chain(w, r.randint(lo, hi))
        else:  # x and y lie above the two ends of a "Some a are b" premise
            a0, b0 = new(), new()
            x, y = chain(a0, r.randint(lo, hi)), chain(b0, r.randint(lo, hi))
            some_p.append((a0, b0))
    else:  # cannot be determined: separate chains, one tied to a third group by a "No"
        x, y = new(), new()
        top_x = chain(x, r.randint(lo, hi))
        chain(y, r.randint(lo, hi))
        no_p.append((top_x, new()))
    for _ in range(3 + level // 2):  # decoy groups hang below a random group and carry a random "No" or "Some" to another group
        g = new()
        all_e.append((g, r.randrange(g)))
        h = r.randrange(cnt[0])
        if h != g:
            (no_p if r.random() < 0.5 else some_p).append((g, h))
    return cnt[0], all_e, no_p, some_p, x, y


@fix3("categories", "R1.categories_follow_r4")
def categories_follow_r5(level: int, r: random.Random) -> Built:
    """structured: {"cats", "all", "none", "some", "kind", "x", "y", "answer_convention"} as categories_follow_r4 (indices into "cats"; the same convention sentence and the same complete entailment). The kind of statement and the
    class are drawn first (each uniform, independent) and the premises are planted around the asked pair: all-yes: a chain of 2 .. 2 + level "All" steps from x to y; all-no, none-yes, some-no: x and y each lie below one end of
    a "No a are b" premise (1 .. 1 + level // 2 "All" steps on each side); none-no, some-yes: x and y have a common member group below both, or lie above the two ends of a "Some a are b" premise; cannot be determined: x and y
    lie in separate chains and a "No" premise ties one chain to a third group. 3 + level // 2 decoy groups hang below random groups with one "All" and carry a random "No" or "Some" to another group. The planting is repeated (up to
    300 times, the class and kind kept) until the closure of the earlier shape derives the drawn class with no inconsistency (validity); the asked statement is never stated verbatim. Every yes and no therefore
    needs a "No" or "Some" lifted through at least one "All" (or a chain of two), which a reading without lifting cannot do (the earlier shape: +0.38 to +0.45)."""
    want = r.choice(YNU)
    kind = r.choice(("all", "none", "some"))
    for _ in range(300):
        n, all_e, no_p, some_p, x, y = _plant_categories(r, level, kind, want)
        if n > 14:
            continue
        cl = _closure_facts(n, all_e, no_p, some_p)
        if cl is None:
            continue
        m, wit = cl
        up = [{t for t in range(n) if m[i][t]} for i in range(n)]

        def disjoint(a: int, b: int) -> bool:
            return any((p in up[a] and q in up[b]) or (q in up[a] and p in up[b]) for p, q in no_p)  # noqa: B023

        def overlap(a: int, b: int) -> bool:
            return any(a in f and b in f for f in wit)  # noqa: B023

        if kind == "all":
            got = "yes" if m[x][y] else ("no" if any(x in f and any(disjoint(g2, y) for g2 in f) for f in wit) else "cannot be determined")
        elif kind == "none":
            got = "yes" if disjoint(x, y) else ("no" if overlap(x, y) else "cannot be determined")
        else:
            got = "yes" if overlap(x, y) else ("no" if disjoint(x, y) else "cannot be determined")
        stated = {("all", a, b) for a, b in all_e} | {("none", a, b) for a, b in no_p} | {("none", b, a) for a, b in no_p} | {("some", a, b) for a, b in some_p} | {("some", b, a) for a, b in some_p}
        if got == want and (kind, x, y) not in stated and x != y:
            break
    else:
        raise Retry
    cats = r.sample(PSEUDO, n)
    stmt = {"all": f"every {cats[x]} is a {cats[y]}", "none": f"no {cats[x]} is a {cats[y]}", "some": f"some {cats[x]} are {cats[y]}"}[kind]
    sents = [f"All {cats[a]} are {cats[b]}." for a, b in all_e] + [f"No {cats[a]} are {cats[b]}." for a, b in no_p] + [f"Some {cats[a]} are {cats[b]}." for a, b in some_p]
    r.shuffle(sents)
    conv = "Every group named here has at least one member. \"Some X are Y\" means that at least one thing is both an X and a Y; \"No X are Y\" means that nothing is both."
    q = (" ".join(sents) + f" {conv} Consider the statement: \"{stmt}\". Answer yes if the statement must be true, no if the statement must be false, or cannot be determined if the statements above "
         "leave it open (it could be true and it could be false).")
    st = {"cats": cats, "all": [list(e) for e in all_e], "none": [list(p) for p in no_p], "some": [list(p) for p in some_p], "kind": kind, "x": x, "y": y,
          "answer_convention": "yes = must be true; no = must be false; cannot be determined = could be either; every named group is non-empty"}
    return Built(q, st, want, "ynu", 3)


_IRV_TOT = (10, 40)
_IRV_RING = 0.5
_IRV_C0 = 6


@fix3("voting", "R1.instant_runoff_r4")
def instant_runoff_r5(level: int, r: random.Random) -> Built:
    """structured: {"candidates", "ballots": [[count, ranking]]} as instant_runoff_r4. 4 + level // 3 candidates; first-place totals of 10 to 30 per candidate (independent), split into one to three groups of voters. A hidden cyclic order of the
    candidates is drawn per item; the ranking of a voter group is, with probability 1/2, the group's candidate followed by the others walking round the cycle in a random direction, otherwise a random order. Items with a
    tie for the fewest ballots are drawn again (validity). Transfers then snowball round the cycle, so the plurality leader, the winner of the runoff between the two leaders, the winner after one elimination and the Borda
    winner agree with the elimination result about as often as chance (the earlier shape: +0.38 to +0.40)."""
    c = _IRV_C0 + level // 2
    lo_t, hi_t = _IRV_TOT
    cands = r.sample(NAMES, c)
    ring = cands[:]
    r.shuffle(ring)
    ballots: list[list] = []
    for cand in cands:
        total = r.randint(lo_t, hi_t)
        g = r.randint(1, 3)
        cuts = sorted(r.sample(range(1, total), g - 1))
        parts = [b - a for a, b in zip([0, *cuts], [*cuts, total], strict=True)]
        for cnt in parts:
            if r.random() < _IRV_RING:
                i = ring.index(cand)
                step = r.choice((1, -1))
                rest = [ring[(i + step * k) % c] for k in range(1, c)]
            else:
                rest = [x for x in cands if x != cand]
                r.shuffle(rest)
            ballots.append([cnt, [cand, *rest]])
    r.shuffle(ballots)
    alive = list(cands)
    while len(alive) > 1:
        tally = {a: 0 for a in alive}
        for cnt, rk in ballots:
            tally[next(x for x in rk if x in alive)] += cnt
        low = min(tally.values())
        out = [a for a in alive if tally[a] == low]
        if len(out) != 1:
            raise Retry
        alive.remove(out[0])
    q = (f"{and_(sorted(cands))} are candidates. " + " ".join(f"{pl(cnt, 'voter')} rank them {' > '.join(rk)} (best first)." for cnt, rk in ballots)
         + " The count goes in rounds: each round, every ballot counts for its best candidate still in the race; the candidate with the fewest ballots counting for them is out, and the next round starts. "
           "It continues until one candidate is left. Who is left?")
    return Built(q, {"candidates": cands, "ballots": ballots}, alive[0], "name", c)


@fix3("matching", "R1.stable_matching_r4")
def stable_matching_r5(level: int, r: random.Random) -> Built:
    """structured: {"proposers", "receivers", "prefs_p", "prefs_r", "ask"} as stable_matching_r4 (the same procedure and wording). 4 + level // 2 proposers. The planting of the earlier shape (a matching M that is proposer-optimal;
    the rank of M(p) in p's list uniform) is kept, and a ROTATION is planted through all proposers except, with probability 0.15, one that is not the asked one: the second stable matching M' gives p_i the receiver M(p_{i+1}) of the next
    proposer in a random cycle; p_i's list has M'(p_i) right after M(p_i) (and never among the receivers above M(p_i)) and a receiver's list has its M'-partner right before its M-partner. So receiver-proposing deferred
    acceptance gives the asked proposer another partner in about 90 % of the items (the earlier shape: the same partner in half of them, +0.51). The answer is still computed by running the stated procedure."""
    n = 4 + level // 2
    names = r.sample(NAMES, 2 * n)
    ps, rs = names[:n], names[n:]
    perm = r.sample(rs, n)
    mm = dict(zip(ps, perm, strict=True))
    ask = r.choice(ps)
    seq = [p for p in ps if p != ask]
    r.shuffle(seq)
    seq.append(ask)
    cyc = list(ps)
    r.shuffle(cyc)
    if r.random() < 0.15:
        drop = r.choice([p for p in ps if p != ask])
        cyc.remove(drop)
    m2 = dict(mm)
    for i, p in enumerate(cyc):
        m2[p] = mm[cyc[(i + 1) % len(cyc)]]
    pp: dict[str, list[str]] = {}
    above: dict[str, list[str]] = {}
    for pos, p in enumerate(seq, start=1):
        earlier = [mm[q] for q in (seq[: pos - 1] if not _SM_ANY else [q for q in ps if q != p]) if mm[q] != m2[p]]
        rho = r.randint(1, len(earlier) + 1)
        above[p] = r.sample(earlier, rho - 1)
        rest = [x for x in rs if x != mm[p] and x not in above[p] and x != m2[p]]
        r.shuffle(rest)
        pp[p] = [*above[p], mm[p], *([m2[p]] if m2[p] != mm[p] else []), *rest]
    inv = {x: p for p, x in mm.items()}
    inv2 = {x: p for p, x in m2.items()}
    pr: dict[str, list[str]] = {}
    for x in rs:
        lst = r.sample(ps, n)
        wanters = [p for p in ps if x in above[p]]
        lst.remove(inv[x])
        if inv2[x] != inv[x]:
            lst.remove(inv2[x])
        first = min((lst.index(p) for p in wanters), default=len(lst))  # the M-partner (and the M'-partner just before it) goes above every proposer who wants x more than their own partner
        at = first
        lst[at:at] = [inv2[x], inv[x]] if inv2[x] != inv[x] else [inv[x]]
        pr[x] = lst
    match = _deferred_acceptance(ps, pp, pr)
    order = ps[:]
    r.shuffle(order)
    q = ("Some people ask others to partner with them. " + " ".join(f"{p} would like, from best to worst: {', '.join(pp[p])}." for p in order) + " " + " ".join(f"{x} would like, from best to worst: {', '.join(pr[x])}." for x in rs)
         + f" Matching goes in turns: a person from {and_(sorted(ps))} who has no partner asks the best person on their list that they have not asked yet. The person asked keeps the best proposer so far (by their own list) and says no to the others, who then ask the next person on their list. This goes on until everyone in {and_(sorted(ps))} has a partner. Who is {ask}'s partner at the end? Choose from {and_(sorted(rs))}.")
    return Built(q, {"proposers": ps, "receivers": rs, "prefs_p": pp, "prefs_r": pr, "ask": ask}, match[ask], "name", n)


_SM_ANY = False
_TREE5 = {0: (3, 3), 1: (3, 4), 2: (4, 3), 3: (3, 5), 4: (3, 6), 5: (5, 3), 6: (4, 4)}  # (depth, branching) per level: 27, 64, 81, 125, 216, 243, 256 leaves


@fix3("trees", "R1.minimax_tree_r4")
def minimax_tree_r5(level: int, r: random.Random) -> Built:
    """structured: {"tree", "first", "depth", "branching"} as minimax_tree_r4 (the same wording). Trees are larger at every level and always branch three or more ways: (depth, branching) = (3,3) (3,4) (4,3) (3,5) (3,6) (5,3) (4,4), so 27 to 256 leaves (the earlier level 0 had 4 leaves
    and 'the median leaf' scored +0.55, 'the option with the best leaf' +0.68). The first mover is drawn; leaves are integers from -50 to 50 (open number answer; the earlier range -9..9 put the answer on one value in a fifth of the deepest trees)."""
    depth, br = _TREE5[level]
    first = r.choice(("max", "min"))

    def grow(d: int) -> object:
        return r.randint(-50, 50) if d == 0 else [grow(d - 1) for _ in range(br)]

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


@fix3("elimination", "R1.elimination_bracket_r4")
def elimination_bracket_r5(level: int, r: random.Random) -> Built:
    """structured: {"players": [bracket order], "results": [[winner, loser]], "ask": ["champion"] | ["runner_up"]} as elimination_bracket_r4 (the same near-regular tournament, bracket and wording), restricted to the question kinds whose
    shortcut readings were small in the third audit: 'who wins' and 'who loses the final', never 'who knocks X out' (the other-quarter beater scored +0.36 at level 5). 8 players for levels 0 to 2 and 16 for levels 3 to 6; the question
    kind by level: champion, runner-up, either, champion, runner-up, either, either. The one reading left is 'the best record inside each half' (+0.08 to +0.17 in the earlier shape at these levels)."""
    size = 8 if level <= 2 else 16
    names = r.sample(NAMES, size)
    # a near-regular tournament (every player wins size/2 - 1 or size/2 of their games): start from the rotational one and reverse random 3-cycles (which keeps every score), then
    # give the players to the bracket positions in a random order. So the number of wins says (almost) nothing about who goes far.
    tw = [[False] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            d = (j - i) % size
            if i != j and (0 < d < size // 2 or (d == size // 2 and i < j)):
                tw[i][j] = True
    for _ in range(12 * size):
        a, b, c = r.sample(range(size), 3)
        for x, y, z in ((a, b, c), (a, c, b)):
            if tw[x][y] and tw[y][z] and tw[z][x]:
                tw[x][y], tw[y][z], tw[z][x] = False, False, False
                tw[y][x], tw[z][y], tw[x][z] = True, True, True
                break
    pos = list(range(size))
    r.shuffle(pos)
    beat = {}
    res = []
    for i in range(size):
        for j in range(i + 1, size):
            a, b = names[pos[i]], names[pos[j]]
            w, lo = (a, b) if tw[i][j] else (b, a)
            beat[(w, lo)] = True
            res.append([w, lo])
    r.shuffle(res)
    rnd, beaten_by, exit_round, rno, final_loser = names[:], {}, {}, 1, ""
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2], strict=True):
            w, lo = (a, b) if beat.get((a, b)) else (b, a)
            beaten_by[lo], exit_round[lo] = w, rno
            nxt.append(w)
            if len(rnd) == 2:
                final_loser = lo
        rnd, rno = nxt, rno + 1
    champion = rnd[0]
    kinds = {0: ["champion"], 1: ["runner_up"], 2: ["champion", "runner_up"], 3: ["champion"], 4: ["runner_up"], 5: ["champion", "runner_up"], 6: ["champion", "runner_up"]}[level]
    kind = r.choice(kinds)
    if kind == "champion":
        ask, ans, qs = ["champion"], champion, "Who wins the tournament?"
    elif kind == "runner_up":
        ask, ans, qs = ["runner_up"], final_loser, "Who loses the final?"
    else:
        who = r.choice([p for p in names if exit_round.get(p) == kind])
        ask, ans, qs = ["beaten_by", who, kind], beaten_by[who], f"Who knocks {who} out?"
    q = (f"A knockout tournament has {size} players listed in bracket order: {', '.join(names)}. In round one the first two listed play each other, the next two play each other, and so on. "
         "Whenever two players meet in the tournament, the winner is whoever won their earlier game against each other: " + " ".join(f"{a} beat {b}." for a, b in res)
         + " The winners keep their order and are paired the same way in the next round, until one player is left. " + qs + f" Choose from {and_(sorted(names))}.")
    return Built(q, {"players": names, "results": res, "ask": ask}, ans, "name", size)


# ---------------------------------------------------------------- graph bipartiteness and swap tracking (rebuilt so that capacity holds)

from collections import deque  # noqa: E402

from studies.m0.vocab import OBJECTS  # noqa: E402


def _bfs_dist(n: int, adj: list[set[int]], src: int) -> list[int]:
    dist = [-1] * n
    dist[src] = 0
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist


@fix3("graph", "R1.graph_bipartite")
def graph_bipartite_r5(level: int, r: random.Random) -> Built:
    """structured: {"people": [name], "rivals": [[a, b]]} as graph_bipartite. n = 13 + level people (the earlier 4 + level people allowed at most 11 / 34 / 156 / 1,044 / 12,346 different graphs at levels 0 to 4, far below the
    capacity the generator must have). A connected bipartite graph is built (a random spanning tree that attaches each person to one of the last three earlier people on the other side, so paths are long; then 2 + level // 2 + (0 to 2)
    more edges across the two sides). yes: one more edge across the sides. no: one edge inside a side, between two people at distance 4 or more (so the shortest odd cycle has 5 or more people: NO item has a triangle; the earlier
    rule 'a triangle means no' scored +0.40 to +0.50). The two classes have the same number of rivalries. The answer is drawn first; the graph is then checked two-colourable (yes) or not (no) as validity."""
    n = 13 + level
    people = r.sample(NAMES, n)
    want = r.choice(("yes", "no"))
    side = [r.randrange(2), 0]
    side[1] = 1 - side[0]
    edges: set[tuple[int, int]] = {(0, 1)}
    for v in range(2, n):
        side.append(r.randrange(2))
        opp = [u for u in range(v) if side[u] != side[v]]
        if not opp:
            side[v] = 1 - side[v]
            opp = [u for u in range(v) if side[u] != side[v]]
        u = r.choice(opp[-3:])
        edges.add((min(u, v), max(u, v)))
    cross = [(i, j) for i in range(n) for j in range(i + 1, n) if side[i] != side[j] and (i, j) not in edges]
    extra = min(len(cross) - 1, 2 + level // 2 + r.randint(0, 2))
    if extra < 0:
        raise Retry
    for e in r.sample(cross, extra):
        edges.add(e)
    adj: list[set[int]] = [set() for _ in range(n)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    if want == "yes":
        pool = [(i, j) for i in range(n) for j in range(i + 1, n) if side[i] != side[j] and (i, j) not in edges]
    else:
        pool = []
        for i in range(n):
            dist = _bfs_dist(n, adj, i)
            pool += [(i, j) for j in range(i + 1, n) if side[i] == side[j] and dist[j] >= 4]
    if not pool:
        raise Retry
    edges.add(r.choice(pool))
    colour = [-1] * n
    ok = True
    adj2: list[set[int]] = [set() for _ in range(n)]
    for a, b in edges:
        adj2[a].add(b)
        adj2[b].add(a)
    for s0 in range(n):
        if colour[s0] >= 0:
            continue
        colour[s0] = 0
        dq = deque([s0])
        while dq:
            u = dq.popleft()
            for v in adj2[u]:
                if colour[v] < 0:
                    colour[v] = 1 - colour[u]
                    dq.append(v)
                elif colour[v] == colour[u]:
                    ok = False
    if ok != (want == "yes"):
        raise Retry
    rivals = [[people[a], people[b]] for a, b in sorted(edges)]
    r.shuffle(rivals)
    rivals = [x if r.random() < 0.5 else [x[1], x[0]] for x in rivals]
    q = (f"{and_(sorted(people))} must be split into two teams. " + " ".join(f"{a} and {b} are rivals." for a, b in rivals)
         + " Can they be split into two teams (either team may be any size) so that no two rivals are on the same team? Answer yes or no.")
    return Built(q, {"people": people, "rivals": rivals}, want, "yn", 2)


@fix3("tracking", "R1.swap_tracking")
def swap_tracking_r5(level: int, r: random.Random) -> Built:
    """structured: {"hold": {person: item}, "ops": [["swap", a, b] | ["rotate", a, b, c]], "who": person} as swap_tracking. 5 + level // 2 people and 6 + 2 * level operations (the earlier shape had 3 people at level 0 and
    13 different structures there). Operations: a swap with probability 1/2, a three-way rotation otherwise (each person's item goes to the next in the cycle). The asked person is drawn uniformly among the people whose FINAL item
    has been moved by at least one rotation and at least one swap on its way (traced backwards through the operations): a structural condition on the question, not on any rule's answer, so no kind of
    operation can be ignored (the earlier shape: ignoring the three-way hand-overs scored +0.17 to +0.21)."""
    n = 5 + level // 2
    people = r.sample(NAMES, n)
    objs = r.sample(OBJECTS, n)
    hold = dict(zip(people, objs, strict=True))
    state = dict(hold)
    ops: list[list[str]] = []
    trace: dict[str, set[str]] = {p: set() for p in people}  # kinds of operation that have moved the item currently held by p
    for _ in range(6 + 2 * level):
        if r.random() < 0.5:
            a, b = r.sample(people, 2)
            ops.append(["swap", a, b])
            state[a], state[b] = state[b], state[a]
            trace[a], trace[b] = trace[b] | {"swap"}, trace[a] | {"swap"}
        else:
            a, b, c = r.sample(people, 3)
            ops.append(["rotate", a, b, c])
            state[b], state[c], state[a] = state[a], state[b], state[c]
            trace[b], trace[c], trace[a] = trace[a] | {"rot"}, trace[b] | {"rot"}, trace[c] | {"rot"}
    cand = [p for p in people if trace[p] == {"swap", "rot"}]
    if not cand:
        raise Retry
    who = r.choice(cand)
    txt = []
    for o in ops:
        if o[0] == "swap":
            txt.append(f"{o[1]} and {o[2]} swap what they are holding.")
        else:
            txt.append(f"{o[1]} hands their item to {o[2]}, {o[2]} hands theirs to {o[3]}, and {o[3]} hands theirs to {o[1]}, all at once.")
    start = ", ".join(f"{p} holds the {o}" for p, o in hold.items())
    q = f"At the start {start}. " + " ".join(txt) + f" What is {who} holding at the end? Choose from {and_(sorted(objs))}."
    return Built(q, {"hold": {p: hold[p] for p in people}, "ops": ops, "who": who}, state[who], "text", n)
