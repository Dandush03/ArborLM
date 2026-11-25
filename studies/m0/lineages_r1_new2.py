# ruff: noqa: E501
"""R1, second authoring round: eight further lineages, each defended as a distinct STRICT procedure (the general algorithm differs from every strict cluster
of the pilot audit). Families are new: scheduling, network, voting, matching, games, sets. Parts are given by the registered partition rule, not by me.

Defence of distinctness (one line each; the auditor must repeat it):
  topological_order     Kahn's algorithm with a priority rule on a prerequisite DAG (not reachability, not a longest-path DP).
  activity_selection    greedy earliest-finish selection of non-overlapping intervals (not a pairwise intersection test).
  mst_cost              minimum spanning tree (cycle-avoiding greedy on edges, not a shortest path).
  instant_runoff        repeated elimination of the weakest candidate with transfer of ballots (an iterated tally, not a single tally).
  stable_matching       deferred acceptance (Gale-Shapley) over two preference lists.
  nim_xor               impartial-game analysis by the xor of pile sizes (Sprague-Grundy), not a simulation.
  minimax_tree          backward induction on an explicit two-player game tree.
  venn_counting         inclusion-exclusion over overlapping groups (set-size algebra).
Possible strict merges an auditor may make: minimax_tree with any other tree evaluation; activity_selection with interval_overlap (both intervals); topological_order with
temporal_critical_path (both DAG processing). They are listed here so nobody has to find them.
"""

from __future__ import annotations

import heapq
import random

from studies.m0.core import Built, Item, Retry
from studies.m0.lineages_r1_common import and_, pilot, pl
from studies.m0.lineages_r1_shortcuts import SPECIFIC, credit, generic
from studies.m0.vocab import NAMES, TOWNS


def _anti(b: Built, lid: str, r: random.Random, names: tuple[str, ...], p_reject: float = 0.8) -> Built:
    it = Item("x", "R1", "A", lid, "f", 1, b.question, b.structured, b.answer, b.answer_type, b.k)
    fns = SPECIFIC.get(lid, {})
    g = generic(it)
    for n in names:
        p = fns[n](it) if n in fns else g.get(n)
        if p not in (None, []) and credit(p, it) >= 0.5 and r.random() < p_reject:
            raise Retry
    return b


@pilot("scheduling", "?")
def topological_order(level: int, r: random.Random) -> Built:
    """structured: {"jobs": [[name, [prerequisite names]]], "day": j}. One job is done per day; on each day, among the jobs whose prerequisites are all done, the one whose
    name comes first in alphabetical order is done. Answer: the job done on day j (2 <= j <= n)."""
    n = 4 + level
    ps = r.sample(NAMES, n)
    jobs = [[p, sorted(r.sample(ps[:i], min(i, r.choice((0, 1, 1, 2)))))] for i, p in enumerate(ps)]
    r.shuffle(jobs)
    deps = {p: set(d) for p, d in jobs}
    done: list[str] = []
    heap = [p for p, d in deps.items() if not d]
    heapq.heapify(heap)
    left = {p: set(d) for p, d in deps.items()}
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
    return _anti(Built(q, {"jobs": jobs, "day": j}, done[j - 1], "name", n), "R1.topological_order", r, ("jth_alphabetical",))


@pilot("scheduling", "?")
def activity_selection(level: int, r: random.Random) -> Built:
    """structured: {"meetings": [[name, start, end]]}. A person can attend several meetings if they do not overlap (a meeting that ends exactly when another starts is fine).
    Answer: the largest number of meetings one person can attend (a number)."""
    n = 6 + 2 * level
    ps = r.sample(NAMES, n)
    ms = []
    for p in ps:
        s = r.randint(0, 60 + 4 * level)
        ms.append([p, s, s + r.randint(2, 9)])
    chosen, last = 0, -1
    for _, s, e in sorted(ms, key=lambda m: (m[2], m[1])):
        if s >= last:
            chosen += 1
            last = e
    r.shuffle(ms)
    q = " ".join(f"{p}'s meeting runs from minute {s} to minute {e}." for p, s, e in ms) + " A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?"
    return _anti(Built(q, {"meetings": ms}, str(chosen), "number", None), "R1.activity_selection", r, ("greedy_by_start",), 0.95)


@pilot("network", "?")
def mst_cost(level: int, r: random.Random) -> Built:
    """structured: {"towns": [name], "roads": [[a, b, length]]}. The roads connect all towns. Keep as few roads as possible so that every town can still be reached from every other,
    choosing them to make the total length as small as possible. Answer: that smallest total length (a number)."""
    n = 4 + (level + 1) // 2
    towns = r.sample(TOWNS, n)
    edges: dict[tuple[int, int], int] = {}
    for i in range(1, n):
        edges[(r.randrange(i), i)] = r.randint(1, 20)
    for _ in range(n):
        a, b = sorted(r.sample(range(n), 2))
        edges.setdefault((a, b), r.randint(1, 20))
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    total = 0
    for (a, b), w in sorted(edges.items(), key=lambda kv: (kv[1], kv[0])):
        if find(a) != find(b):
            parent[find(a)] = find(b)
            total += w
    roads = [[towns[a], towns[b], w] for (a, b), w in edges.items()]
    r.shuffle(roads)
    q = (" ".join(f"A road between {a} and {b} could be built with length {w}." for a, b, w in roads)
         + " Some of these roads will be built so that every town can be reached from every other town, using as few roads as possible and the smallest possible total length. What is that total length?")
    return _anti(Built(q, {"towns": towns, "roads": roads}, str(total), "number", None), "R1.mst_cost", r, ("smallest_n_minus_1_roads",), 0.95)


@pilot("voting", "?")
def instant_runoff(level: int, r: random.Random) -> Built:
    """structured: {"candidates": [name], "ballots": [[count, [ranking, best first]]]}. Every ballot ranks every candidate. Repeat: count the first places among the candidates still in; the
    candidate with the fewest is out (never tied in these items) and its ballots go to their next candidate still in; stop when one candidate is left. Answer: the last one left."""
    c = 3 + level // 3
    cands = r.sample(NAMES, c)
    groups = 4 + level
    ballots = [[r.randint(1, 9), r.sample(cands, c)] for _ in range(groups)]
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
    first: dict[str, int] = {}
    for cnt, rk in ballots:
        first[rk[0]] = first.get(rk[0], 0) + cnt
    q = (f"{and_(sorted(cands))} are candidates. " + " ".join(f"{pl(cnt, 'voter')} rank them {' > '.join(rk)} (best first)." for cnt, rk in ballots)
         + " The count goes in rounds: each round, every ballot counts for its best candidate still in the race; the candidate with the fewest ballots counting for them is out, and the next round starts. "
           "It continues until one candidate is left. Who is left?")
    return _anti(Built(q, {"candidates": cands, "ballots": ballots}, alive[0], "name", c), "R1.instant_runoff", r, ("plurality_winner",), 0.9)


@pilot("matching", "?")
def stable_matching(level: int, r: random.Random) -> Built:
    """structured: {"proposers": [name], "receivers": [name], "prefs_p": {proposer: [receivers, best first]}, "prefs_r": {receiver: [proposers, best first]}, "ask": proposer}.
    Deferred acceptance: every free proposer asks the best receiver not yet asked; a receiver holds the best proposer asked so far and turns the others away; repeat until all are held.
    Answer: the receiver held by `ask` at the end."""
    n = 3 + level // 2
    names = r.sample(NAMES, 2 * n)
    ps, rs = names[:n], names[n:]
    pp = {p: r.sample(rs, n) for p in ps}
    pr = {x: r.sample(ps, n) for x in rs}
    nxt = {p: 0 for p in ps}
    held: dict[str, str] = {}
    free = list(ps)
    while free:
        p = free.pop(0)
        rcv = pp[p][nxt[p]]
        nxt[p] += 1
        if rcv not in held:
            held[rcv] = p
        elif pr[rcv].index(p) < pr[rcv].index(held[rcv]):
            free.append(held[rcv])
            held[rcv] = p
        else:
            free.append(p)
    match = {p: x for x, p in held.items()}
    ask = r.choice(ps)
    q = ("Some people ask others to partner with them. " + " ".join(f"{p} would like, from best to worst: {', '.join(pp[p])}." for p in ps) + " " + " ".join(f"{x} would like, from best to worst: {', '.join(pr[x])}." for x in rs)
         + f" Matching goes in turns: a person from {and_(sorted(ps))} who has no partner asks the best person on their list that they have not asked yet. The person asked keeps the best proposer so far (by their own list) and says no to the others, who then ask the next person on their list. This goes on until everyone in {and_(sorted(ps))} has a partner. Who is {ask}'s partner at the end? Choose from {and_(sorted(rs))}.")
    return _anti(Built(q, {"proposers": ps, "receivers": rs, "prefs_p": pp, "prefs_r": pr, "ask": ask}, match[ask], "name", n), "R1.stable_matching", r, ("first_choice",), 0.6)


@pilot("games", "?")
def nim_xor(level: int, r: random.Random) -> Built:
    """structured: {"piles": [sizes]}. Two players alternate; on a turn a player removes at least one stone from ONE pile; whoever takes the last stone wins; the first player moves first.
    Answer: "first" or "second" (the player who wins with perfect play)."""
    k = 3 + level // 3
    want = r.choice(("first", "second"))
    for _ in range(400):  # draw piles until the xor matches the wanted winner (the answer is chosen first, so the key is balanced)
        piles = [r.randint(1, 20 + 4 * level) for _ in range(k)]
        x = 0
        for p in piles:
            x ^= p
        if (x != 0) == (want == "first") and sum(piles) % 2 == 0:  # an even total in every item: the parity of the total says nothing
            break
    else:
        raise Retry
    q = (f"A game has {k} piles of stones: " + ", ".join(str(p) for p in piles) + ". Two players take turns. On a turn, a player must remove at least one stone, all from a single pile (any number up to the whole pile). "
         "The player who takes the very last stone wins. Both play perfectly and the first player moves first. Who wins, the first player or the second player? Answer first or second.")
    return Built(q, {"piles": piles}, want, "word", 2)


@pilot("games", "?")
def minimax_tree(level: int, r: random.Random) -> Built:
    """structured: {"tree": nested list (a leaf is an integer payoff to the maximiser; an inner node is a list of its children), "first": "max"}. The maximiser chooses at the root and the two
    players alternate by depth; both play perfectly. Answer: the payoff (a number)."""
    depth = 2 + (level >= 3) + (level >= 5)

    def grow(d: int) -> object:
        return r.randint(-9, 9) if d == 0 else [grow(d - 1), grow(d - 1)]

    tree = grow(depth)

    def val(t: object, maxing: bool) -> int:
        if isinstance(t, int):
            return t
        vals = [val(c, not maxing) for c in t]  # type: ignore[attr-defined]
        return max(vals) if maxing else min(vals)

    def txt(t: object) -> str:
        return str(t) if isinstance(t, int) else "(" + " or ".join(txt(c) for c in t) + ")"  # type: ignore[attr-defined]

    ans = val(tree, True)
    q = (f"Two players, Max and Min, play a game with {depth} choices in a row, Max choosing first and then Min, and so on in turn. At each choice the mover picks one of the two options shown. "
         f"The game is written as nested options: {txt(tree)}. When the options are all numbers, the number picked is the payoff. Max wants the payoff as large as possible and Min as small as possible, and both play perfectly. What is the payoff?")
    return Built(q, {"tree": tree, "first": "max"}, str(ans), "number", None)


@pilot("sets", "?")
def venn_counting(level: int, r: random.Random) -> Built:
    """structured: {"total": N, "groups": [names], "sizes": {group: size}, "pairs": {"a|b": size of the overlap}, "triple": size or null}. Every person is counted once. Answer: the number of people
    in none of the groups (a number), by inclusion and exclusion."""
    g = 2 if level <= 1 else 3
    groups = r.sample(("chess", "choir", "diving", "poetry", "rowing", "archery", "baking"), g)
    regions = {}
    for mask in range(1, 1 << g):
        regions[mask] = r.randint(0, 6 + 3 * level)
    none = r.randint(0, 9 + level)
    total = sum(regions.values()) + none
    sizes = {groups[i]: sum(v for m, v in regions.items() if m >> i & 1) for i in range(g)}
    pairs = {f"{groups[i]}|{groups[j]}": sum(v for m, v in regions.items() if (m >> i & 1) and (m >> j & 1)) for i in range(g) for j in range(i + 1, g)}
    triple = regions[(1 << g) - 1] if g == 3 else None
    text = [f"{sizes[x]} people are in the {x} group" for x in groups] + [f"{v} are in both the {k.split('|')[0]} and the {k.split('|')[1]} groups" for k, v in pairs.items()]
    if triple is not None:
        text.append(f"{triple} are in all three groups")
    q = f"Among {total} people, " + "; ".join(text) + ". Each person is counted once in each number that applies to them. How many of the people are in none of these groups?"
    return Built(q, {"total": total, "groups": groups, "sizes": sizes, "pairs": pairs, "triple": triple}, str(none), "number", None)
