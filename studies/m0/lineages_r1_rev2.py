# ruff: noqa: E501
"""R1 shape revisions (lineage repair, after the pilot audit AUDIT_M0_LINEAGES_1; ruling D).

Each builder here replaces an earlier shape of the SAME lineage (same strict cluster); the earlier file is kept and the earlier shape is marked
SUPERSEDED in ``lineages_r1_clusters.STATUS``. What each revision removes is listed in its docstring; the shortcut gate measures the effect.
Ids end in ``_r2``. No second solvers exist; the structured forms keep the earlier schema unless the docstring says otherwise.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from studies.m0.core import Built, Item, Retry
from studies.m0.lineages_r1 import _reach
from studies.m0.lineages_r1_common import YNU, and_, pilot
from studies.m0.lineages_r1_shortcuts import SPECIFIC, credit, generic
from studies.m0.lineages_r1_spatial import spatial_grid_walk
from studies.m0.vocab import COLOURS, NAMES, OBJECTS, PSEUDO, TOWNS


def _anti(b: Built, lid: str, r: random.Random, names: Sequence[str], p_reject: float = 0.8) -> Built:
    """Generator-side shortcut repair: an item that a named trivial heuristic (see lineages_r1_shortcuts) answers correctly is drawn again with probability
    ``p_reject``, so that heuristic is pushed towards chance. Applied only to the shortcuts the gate found for that lineage."""
    it = Item("x", "R1", "A", lid, "f", 1, b.question, b.structured, b.answer, b.answer_type, b.k)
    fns = SPECIFIC.get(lid, {})
    g = generic(it)
    for n in names:
        p = fns[n](it) if n in fns else g.get(n)
        if p not in (None, []) and credit(p, it) >= 0.5 and r.random() < p_reject:
            raise Retry
    return b


NO_COLOUR_OBJECTS = tuple(o for o in OBJECTS if o not in COLOURS)


@pilot("spatial", "?")
def spatial_grid_walk_r2(level: int, r: random.Random) -> Built:
    """Same as spatial_grid_walk, plus the column convention in the item ("column 1 is the westernmost"); the structured form gains
    "convention": "row 1 is the northernmost, column 1 is the westernmost". (Audit: 113 of 140 keys changed under the other reading.)"""
    b = spatial_grid_walk(level, r)
    q = b.question.replace(" columns. Row 1:", " columns (column 1 is the westernmost). Row 1:", 1)
    assert q != b.question
    return Built(q, {**b.structured, "convention": "row 1 is the northernmost, column 1 is the westernmost"}, b.answer, b.answer_type, b.k)


@pilot("kinship", "?")
def kinship_descendants_r2(level: int, r: random.Random) -> Built:
    """structured: {"people": [name], "parent": {child: parent}, "ask": "grandchildren" | "descendants", "candidates": [name]}. Only people WITH a recorded
    parent are candidates, so the parentless root is never the answer (the earlier shape's answer was the root in 132 of 140 items). Answer: the candidate
    with the most grandchildren (or the most descendants of any depth); unique, and at least one."""
    n = 5 + level
    ps = r.sample(NAMES, n)
    parent = {ps[i]: ps[r.randrange(i)] for i in range(1, n)}
    kids: dict[str, list[str]] = {p: [] for p in ps}
    for c, p in parent.items():
        kids[p].append(c)

    def desc(p: str) -> int:
        return sum(1 + desc(c) for c in kids[p])

    ask = r.choice(("grandchildren", "descendants"))
    cands = sorted(parent)
    score = {p: (sum(len(kids[c]) for c in kids[p]) if ask == "grandchildren" else desc(p)) for p in cands}
    top = max(score.values())
    best = [p for p in cands if score[p] == top]
    if top == 0 or len(best) != 1:
        raise Retry
    facts = [f"{parent[c]} is the parent of {c}." for c in sorted(parent)]
    r.shuffle(facts)
    what = "grandchildren (children of their children)" if ask == "grandchildren" else "descendants (children, their children, and so on, all the way down)"
    q = " ".join(facts) + f" Nobody else has a recorded parent. Among the people who have a recorded parent, who has the most {what}? Choose from {and_(cands)}."
    return _anti(Built(q, {"people": ps, "parent": {c: parent[c] for c in sorted(parent)}, "ask": ask, "candidates": cands}, best[0], "name", len(cands)), "R1.kinship_descendants_r2", r, ("most_children", "most_mentioned", "first_mentioned"))


@pilot("equivalence", "?")
def equivalence_classes_r2(level: int, r: random.Random) -> Built:
    """Same schema as equivalence_classes. The asked pair is NEVER a stated pair (earlier shape: stated verbatim in 68 of 140), and both asked
    items are mentioned in some statement (earlier shape: an unmentioned item in 26 of 140, always cannot be determined)."""
    n = 5 + level
    items = r.sample(PSEUDO, n)
    m = max(2, n // 2)
    cls = [r.randrange(m) for _ in range(n)]
    same, diff = [], []
    for c in range(m):  # each group is chained together with probability 0.75 per link, so that "same" can be derived over two or more links
        mem = [i for i in range(n) if cls[i] == c]
        r.shuffle(mem)
        same.extend((a, b) for a, b in zip(mem, mem[1:], strict=False) if r.random() < 0.75)
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
    stated = {frozenset(p) for p in [*same, *diff]}
    mentioned = {x for p in [*same, *diff] for x in p}
    want = r.choice(YNU)
    cands = []
    for i in range(n):
        for j in range(i + 1, n):
            if i not in mentioned or j not in mentioned or frozenset((i, j)) in stated:
                continue
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


@pilot("elimination", "?")
def elimination_bracket_r2(level: int, r: random.Random) -> Built:
    """structured: {"players": [name] in bracket order, "results": [[winner, loser]] (EVERY pair of players, from earlier head-to-head games, not transitive in general),
    "ask": ["runner_up"] | ["beaten_by", name]}. Adjacent players meet in round one; whenever two players meet, the one who won their earlier game wins; winners
    keep their order and are paired adjacent again. Answer: the loser of the final, or the player who knocks the named player out. (The earlier shape decided
    matches by a rating, so the runner-up was the best rating of the other half.) 4 players for levels 0 to 3, 8 for levels 4 to 6."""
    size = 4 if level <= 3 else 8
    names = r.sample(NAMES, size)
    beat: dict[tuple[str, str], bool] = {}
    res = []
    for i in range(size):
        for j in range(i + 1, size):
            w, lo = (names[i], names[j]) if r.random() < 0.5 else (names[j], names[i])
            beat[(w, lo)] = True
            res.append([w, lo])
    r.shuffle(res)
    rnd, beaten_by, final_loser = names[:], {}, ""
    while len(rnd) > 1:
        nxt = []
        for a, b in zip(rnd[0::2], rnd[1::2], strict=True):
            w, lo = (a, b) if beat.get((a, b)) else (b, a)
            beaten_by[lo] = w
            nxt.append(w)
            if len(rnd) == 2:
                final_loser = lo
        rnd = nxt
    champion = rnd[0]
    if r.random() < 0.5:
        ask, ans, qs = ["runner_up"], final_loser, "Who loses the final?"
    else:
        who = r.choice([p for p in names if p != champion])
        ask, ans, qs = ["beaten_by", who], beaten_by[who], f"Who knocks {who} out?"
    q = (f"A knockout tournament has {size} players listed in bracket order: {', '.join(names)}. In round one the first two listed play each other, the next two play each other, and so on. "
         "Whenever two players meet in the tournament, the winner is whoever won their earlier game against each other: " + " ".join(f"{a} beat {b}." for a, b in res)
         + " The winners keep their order and are paired the same way in the next round, until one player is left. " + qs)
    return _anti(Built(q, {"players": names, "results": res, "ask": ask}, ans, "name", size), "R1.elimination_bracket_r2", r, ("most_wins_logic",))


@pilot("containers", "?")
def containers_queue_line_r2(level: int, r: random.Random) -> Built:
    """structured: {"line": [front..back], "ops": [["join", n] | ["cut", n] | ["serve"] | ["leave", n] | ["front_to_back"]], "ask": ["position", j]}. Answer: the person
    in position j from the front (1 = front) at the end. (The earlier shape asked for the front or the back, so the last joiner or the last person let in was right in
    99 of 140 items.)"""
    pool = r.sample(NAMES, 14 + level)
    line = pool[: 3 + level // 2]
    fresh = pool[len(line):]
    cur = list(line)
    ops, text = [], []
    for _ in range(4 + 2 * level):
        kind = r.choice(("join", "cut", "serve", "leave", "front_to_back", "front_to_back"))
        if kind in ("serve", "leave", "front_to_back") and len(cur) <= 2:
            kind = "join"
        if kind == "join":
            p = fresh.pop()
            cur.append(p)
            ops.append(["join", p])
            text.append(f"{p} joins at the back.")
        elif kind == "cut":
            p = fresh.pop()
            cur.insert(0, p)
            ops.append(["cut", p])
            text.append(f"{p} is let in at the very front.")
        elif kind == "serve":
            cur.pop(0)
            ops.append(["serve"])
            text.append("The person at the front is served and leaves.")
        elif kind == "leave":
            p = r.choice(cur)
            cur.remove(p)
            ops.append(["leave", p])
            text.append(f"{p} gets tired and leaves.")
        else:
            cur.append(cur.pop(0))
            ops.append(["front_to_back"])
            text.append("The person at the front goes to the back of the line.")
    j = r.randint(1, min(3, len(cur)))
    allnames = sorted({*line, *(o[1] for o in ops if o[0] in ("join", "cut"))})
    q = f"A line, from front to back, is: {and_(line)}. " + " ".join(text) + f" Who is in position {j} from the front of the line at the end (position 1 is the very front)? Choose from {and_(allnames)}."
    return Built(q, {"line": line, "ops": ops, "ask": ["position", j]}, cur[j - 1], "name", len(allnames))


@pilot("categories", "?")
def categories_default_exceptions_r2(level: int, r: random.Random) -> Built:
    """Same schema as categories_default_exceptions. The asked verb has rules in at least TWO groups above the member's own group, never in the member's own group,
    with at least one rule of each sign, so the most-specific-wins rule is always needed (earlier shape: all rules agreed in 87 of 140, the member's own group
    decided in 54 of 140). Other-verb rules are distractors."""
    c = 3 + level // 2
    chain = r.sample(PSEUDO, c)
    verbs = r.sample(("swim", "glow", "hum", "jump", "float", "climb"), 2)
    ask, other = verbs
    idx = sorted(r.sample(range(1, c), r.randint(2, c - 1)))
    want = r.choice((True, False))
    signs = [want] + [r.random() < 0.5 for _ in idx[1:]]
    if all(s == want for s in signs):
        signs[-1] = not want
    rules = [[chain[i], ask, s] for i, s in zip(idx, signs, strict=True)]
    for i in range(c):
        if r.random() < 0.4:
            rules.append([chain[i], other, r.random() < 0.5])
    member = r.choice(NAMES)
    r.shuffle(rules)
    chain_text = " ".join(f"Every {chain[i]} is a {chain[i + 1]}." for i in range(c - 1))
    rule_text = " ".join(f"A {g} {'can' if ok else 'cannot'} {v}." for g, v, ok in rules)
    q = (f"{chain_text} {rule_text} When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. "
         f"{member} is a {chain[0]}. Can {member} {ask}? Answer yes or no.")
    return _anti(Built(q, {"chain": chain, "rules": rules, "member": member, "verb": ask}, "yes" if want else "no", "yn", 2), "R1.categories_default_exceptions_r2", r, ("majority_sign", "last_listed", "least_specific_rule"))


@pilot("conditional", "?")
def conditional_threshold_rule_r2(level: int, r: random.Random) -> Built:
    """structured: {"members": [[name, weight]], "votes": {name: "yes"|"no"|"abstain"}, "margin": D}. The motion passes when (total weight of yes votes) minus (total weight of no
    votes) is at least D; abstentions count for neither. No veto and no second clause (the earlier shape was decided by a vetoing no in 44 of 140 items; a two-clause
    rule lets one clause alone answer about three items in four). Answer yes/no."""
    n = 4 + level
    ps = r.sample(NAMES, n)
    w = {p: (r.randint(1, 4) if level >= 2 else 1) for p in ps}
    votes = {p: r.choice(("yes", "no", "abstain")) for p in ps}
    d = r.randint(-2, 3)
    diff = sum(w[p] for p in ps if votes[p] == "yes") - sum(w[p] for p in ps if votes[p] == "no")
    want = r.choice(("yes", "no"))
    if (diff >= d) != (want == "yes"):
        raise Retry
    q = ("A committee votes on a motion. " + ", ".join(f"{p} has weight {w[p]}" for p in ps) + f". The motion passes if the total weight of the members who vote yes, minus the total weight of the members who vote no, is at least {d} "
         "(members who abstain count for neither side). The votes: " + ", ".join(f"{p} {votes[p]}" for p in ps) + ". Does the motion pass? Answer yes or no.")
    return _anti(Built(q, {"members": [[p, w[p]] for p in ps], "votes": votes, "margin": d}, want, "yn", 2), "R1.conditional_threshold_rule_r2", r, ("yes_count_majority",))


@pilot("boolean_state", "?")
def boolean_lights_r2(level: int, r: random.Random) -> Built:
    """Same schema as boolean_lights. The asked lamp is wired to at least one switch that is pressed (earlier shape: never toggled in 31 of 140), and the initial state is
    worded without "the rest are off" when no lamp is off."""
    nl = 4 + level
    ns = 3 + level // 3
    cols = r.sample(COLOURS, ns)
    init = [r.randrange(2) for _ in range(nl)]
    wiring = {c: sorted(r.sample(range(1, nl + 1), r.randint(1, nl // 2 + 1))) for c in cols}
    presses = [r.choice(cols) for _ in range(3 + 2 * level)]
    state, toggles = list(init), [0] * nl
    for c in presses:
        for lamp in wiring[c]:
            state[lamp - 1] ^= 1
            toggles[lamp - 1] += 1
    want = r.choice(("yes", "no"))
    cand = [i + 1 for i in range(nl) if state[i] == (1 if want == "yes" else 0) and toggles[i] > 0]
    if not cand:
        raise Retry
    ask = r.choice(cand)
    on = [i + 1 for i in range(nl) if init[i]]
    if not on:
        start = "all lamps are off"
    elif len(on) == nl:
        start = "all lamps are on"
    else:
        start = f"{'lamp' if len(on) == 1 else 'lamps'} {and_([str(x) for x in on])} {'is' if len(on) == 1 else 'are'} on and every other lamp is off"
    q = (f"There are {nl} lamps numbered 1 to {nl}. At the start, {start}. "
         + " ".join(f"The {c} switch toggles {'lamp' if len(wiring[c]) == 1 else 'lamps'} {and_([str(x) for x in wiring[c]])} (each one goes from on to off or from off to on)." for c in cols)
         + f" The switches are pressed in this order: {', '.join(presses)}. Is lamp {ask} on at the end? Answer yes or no.")
    return Built(q, {"lamps": nl, "initial": init, "switches": wiring, "presses": presses, "ask": ask}, want, "yn", 2)


@pilot("graph", "?")
def graph_shortest_route_r2(level: int, r: random.Random) -> Built:
    """structured: {"towns": [name], "roads": [[a, b, length]] (two-way), "start": name, "end": name}. Answer: the smallest total length of a route from start to end (a
    number; open answer). The shortest route has at least two roads. (The earlier shape asked for the first town on the route, which the nearest neighbour of the start
    gave in 97 of 140 items.)"""
    n = 5 + (level + 1) // 2
    towns = r.sample(TOWNS, n)
    edges: dict[tuple[int, int], int] = {}
    for i in range(1, n):
        edges[(r.randrange(i), i)] = r.randint(1, 15)
    for _ in range(n // 2 + 1):
        a, b = sorted(r.sample(range(n), 2))
        edges.setdefault((a, b), r.randint(1, 15))
    s, t = r.sample(range(n), 2)
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(n)}
    for (a, b), w in edges.items():
        adj[a].append((b, w))
        adj[b].append((a, w))
    inf = 10**9
    dist, hops, done = [inf] * n, [0] * n, [False] * n
    dist[s] = 0
    for _ in range(n):
        u = min((i for i in range(n) if not done[i]), key=lambda i: dist[i], default=-1)
        if u < 0 or dist[u] == inf:
            break
        done[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v], hops[v] = dist[u] + w, hops[u] + 1
    if dist[t] == inf or hops[t] < 2:
        raise Retry
    roads = [[towns[a], towns[b], w] for (a, b), w in edges.items()]
    r.shuffle(roads)
    q = " ".join(f"There is a two-way road between {a} and {b} of length {w}." for a, b, w in roads) + f" What is the smallest total length of a route from {towns[s]} to {towns[t]} along these roads?"
    return Built(q, {"towns": towns, "roads": roads, "start": towns[s], "end": towns[t]}, str(dist[t]), "number", None)


@pilot("containers", "?")
def containers_stack_piles_r2(level: int, r: random.Random) -> Built:
    """Same schema as containers_stack_piles. Blocks are never named like a pile colour (the earlier shape could have a pile 'orange' and a block 'orange')."""
    piles = [f"the {c} pile" for c in r.sample(COLOURS, 3)]
    nb = 4 + level
    blocks = r.sample(NO_COLOUR_OBJECTS, nb)
    state = {p: [] for p in piles}
    for b in blocks:
        state[r.choice(piles)].append(b)
    initial = {p: list(v) for p, v in state.items()}
    ops, text = [], []
    for _ in range(3 + 2 * level):
        full = [p for p in piles if state[p]]
        if level >= 3 and r.random() < 0.2:
            p = r.choice(full)
            state[p].reverse()
            ops.append(["reverse", p])
            text.append(f"Turn {p} upside down.")
            continue
        a = r.choice(full)
        b = r.choice([p for p in piles if p != a])
        state[b].append(state[a].pop())
        ops.append(["move", a, b])
        text.append(f"Move the top block of {a} onto {b}.")
    ask = r.choice([p for p in piles if state[p]])
    init = " ".join(f"{p.capitalize()} holds, from bottom to top: {and_(initial[p]) if initial[p] else 'nothing'}." for p in piles)
    q = f"There are three piles of blocks. {init} {' '.join(text)} Which block is on top of {ask} at the end? Choose from {and_(sorted(blocks))}."
    return _anti(Built(q, {"piles": piles, "initial": initial, "ops": ops, "ask": ask}, state[ask][-1], "text", nb), "R1.containers_stack_piles_r2", r, ("last_block_moved_onto_asked",))


@pilot("categories", "?")
def categories_follow_r2(level: int, r: random.Random) -> Built:
    """Shape revision of the core lineage R1.categories_follow (same schema: {"cats", "all", "none", "kind", "x", "y"}). The item states that a group may have no members;
    the answer is chosen first (yes / no / cannot be determined uniformly) and a query with that answer is drawn, so the key is balanced (earlier shape: 'cannot be
    determined' in 77.6 % of items against a chance of 1/3, and an unstated existential-import convention that made 236 of 500 items ambiguous). Kinds: "all" (does
    every X belong to Y: yes or cannot), "none" (does no X belong to Y: yes or cannot), "some" (do some X belong to Y: no or cannot; yes is never forced because a group may be empty)."""
    n = 4 + (level + 1) // 2
    cats = r.sample(PSEUDO, n)
    allw = [(i, j) for i in range(n) for j in range(i + 1, n)]
    all_e = r.sample(allw, min(len(allw), n - 1 + r.randint(0, 1)))
    no_p = [tuple(r.sample(range(n), 2)) for _ in range(1 + level // 3)]
    m = _reach([(a, b) for a, b in all_e], n)

    def above(i: int) -> list[int]:
        return [t for t in range(n) if m[i][t]]

    for i in range(n):  # a group forced to be empty would make "every X is Y" vacuous: not used
        if any(p in above(i) and q in above(i) for p, q in no_p):
            raise Retry
    want = r.choice(YNU)
    cands = []
    for kind in ("all", "none", "some"):
        for x in range(n):
            for y in range(n):
                if x == y:
                    continue
                if (kind == "all" and (x, y) in all_e) or (kind != "all" and any({x, y} == {p, q} for p, q in no_p)):
                    continue  # the asked statement is never stated verbatim
                disj = any(((p in above(x) and q in above(y)) or (q in above(x) and p in above(y))) for p, q in no_p)
                if kind == "all":
                    ans = "yes" if m[x][y] else "cannot be determined"
                elif kind == "none":
                    ans = "yes" if disj else "cannot be determined"
                else:
                    ans = "no" if disj else "cannot be determined"
                if ans == want:
                    cands.append((kind, x, y))
    if not cands:
        raise Retry
    kind, x, y = r.choice(cands)
    qs = {"all": f"Does it follow that every {cats[x]} is a {cats[y]}?", "none": f"Does it follow that no {cats[x]} is a {cats[y]}?", "some": f"Does it follow that some {cats[x]} are {cats[y]}?"}[kind]
    sents = [f"All {cats[a]} are {cats[b]}." for a, b in all_e] + [f"No {cats[a]} are {cats[b]}." for a, b in no_p]
    r.shuffle(sents)
    q = " ".join(sents) + f" (A group may have no members at all; \"some X are Y\" says that at least one thing is both.) {qs} Answer yes, no or cannot be determined."
    return Built(q, {"cats": cats, "all": [list(e) for e in all_e], "none": [list(p) for p in no_p], "kind": kind, "x": x, "y": y}, want, "ynu", 3)


@pilot("kinship", "?")
def kinship_ancestor_r2(level: int, r: random.Random) -> Built:
    """Shape revision of the core lineage R1.kinship_ancestor (same schema: {"parent", "child", "generations", "people"}). The line above the asked child is 1 or 2
    generations LONGER than the asked ancestor distance, so the answer is never the parentless root (found by the shortcut gate: the earlier shape's answer was
    always the one person with no recorded parent). Answer: the ancestor k generations above the child (grandparent, great-grandparent, ...)."""
    k = 2 + (level >= 3) + (level >= 5)
    extra = r.randint(1, 2)
    chain_len = k + 1 + extra
    people = r.sample(NAMES, chain_len + 2 + level)
    chain = people[:chain_len]
    parent = {chain[i + 1]: chain[i] for i in range(chain_len - 1)}
    placed = chain[:]
    for p in people[chain_len:]:
        parent[p] = r.choice(placed)
        placed.append(p)
    term = {2: "grandparent", 3: "great-grandparent", 4: "great-great-grandparent"}[k]
    facts = [f"{parent[c]} is the parent of {c}." if r.random() < 0.5 else f"{c}'s parent is {parent[c]}." for c in sorted(parent)]
    r.shuffle(facts)
    child = chain[-1]
    q = " ".join(facts) + f" Nobody else has a recorded parent. Who is the {term} of {child}? Choose from {and_(sorted(people))}."
    return _anti(Built(q, {"parent": {c: parent[c] for c in sorted(parent)}, "child": child, "generations": k, "people": sorted(people)}, chain[-1 - k], "name", len(people)), "R1.kinship_ancestor_r2", r, ("most_mentioned",))
