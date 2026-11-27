# ruff: noqa: E501
"""R1 revision 4, part 1: relation and rule shapes (second audit AUDIT_M0_R1_2.md; lead rulings R-1 and R-4). No redraw on a heuristic's outcome in any shape here.

boolean_lights_r4            asked lamp's toggle parity is drawn first (a fair coin, independent of its initial state) and its wiring built to realise it; start sentence reworded
conditional_threshold_rule_r4 the threshold is set from the computed margin (threshold = margin minus a small offset), so no vote-only or threshold-only reading carries the answer
kinship_descendants_r4       the candidates are all at one depth below a named person, and each candidate's number of children is drawn independently of its number of descendants
kinship_ancestor_r4          the answer may be the root; several trees, so "the parentless person" is not one person
categories_default_exceptions_r4  the nearest rule's distance is spread over the chain; the sign multiset of the rules is symmetric about the answer
categories_follow_r4         the convention that "no" means "must be false" is stated in the item; groups are non-empty by a stated convention; "some" premises exist, so every answer
                             is reachable for every kind of statement
elimination_bracket_r4       a near-regular tournament (wins say nothing); asks champion, runner-up, or who knocks out a player chosen by round of exit (never round 1 or 2)
"""

from __future__ import annotations

import random
from collections import Counter

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1 import _reach
from studies.m0.lineages_r1_common import YNU, and_
from studies.m0.lineages_r1_rev4_common import rev4
from studies.m0.vocab import COLOURS, NAMES, PSEUDO


@rev4("boolean_state", "R1.boolean_lights_r2")
def boolean_lights_r4(level: int, r: random.Random) -> Built:
    """Same schema as boolean_lights: {"lamps", "initial", "switches": {colour: [lamp]}, "presses": [colour], "ask": lamp}. The asked lamp's toggle parity pi (0 or 1) is drawn first,
    with a fair coin, independent of its initial state; the set of pressed switches wired to it is then drawn uniformly among the non-empty sets with that parity (so the lamp is
    toggled at least once); unpressed switches may be wired to it or not (a coin). The answer is initial xor pi, which is therefore independent of the initial state, of the parity and
    of every other lamp. The start sentence names the lamps that are on and says "all the lamps not named here are off" (the earlier "every other lamp is off" could be read as
    alternate lamps)."""
    nl = 4 + level
    ns = 3 + level // 3
    cols = r.sample(COLOURS, ns)
    init = [r.randrange(2) for _ in range(nl)]
    presses = [r.choice(cols) for _ in range(3 + 2 * level)]
    cnt = Counter(presses)
    pressed = sorted(cnt)
    ask = r.randint(1, nl)
    pi = r.randrange(2)
    s_ask: set[str] = set()
    for _ in range(200):
        s_ask = {c for c in pressed if r.random() < 0.5}
        if s_ask and sum(cnt[c] for c in s_ask) % 2 == pi:
            break
    else:
        raise Retry
    wiring: dict[str, list[int]] = {}
    others = [i for i in range(1, nl + 1) if i != ask]
    for c in cols:
        w = set(r.sample(others, r.randint(1, max(1, nl // 2))))
        if c in s_ask or (c not in cnt and r.random() < 0.5):
            w.add(ask)
        wiring[c] = sorted(w)
    state = list(init)
    for c in presses:
        for lamp in wiring[c]:
            state[lamp - 1] ^= 1
    on = [i + 1 for i in range(nl) if init[i]]
    if not on:
        start = "all lamps are off"
    elif len(on) == nl:
        start = "all lamps are on"
    else:
        start = f"{'lamp' if len(on) == 1 else 'lamps'} {and_([str(x) for x in on])} {'is' if len(on) == 1 else 'are'} on, and all the lamps not named here are off"
    q = (f"There are {nl} lamps numbered 1 to {nl}. At the start, {start}. "
         + " ".join(f"The {c} switch toggles {'lamp' if len(wiring[c]) == 1 else 'lamps'} {and_([str(x) for x in wiring[c]])} (each one goes from on to off or from off to on)." for c in cols)
         + f" The switches are pressed in this order: {', '.join(presses)}. Is lamp {ask} on at the end? Answer yes or no.")
    return Built(q, {"lamps": nl, "initial": init, "switches": wiring, "presses": presses, "ask": ask}, "yes" if state[ask - 1] else "no", "yn", 2)


@rev4("conditional", "R1.conditional_threshold_rule_r3")
def conditional_threshold_rule_r4(level: int, r: random.Random) -> Built:
    """Same schema as conditional_threshold_rule_r2/_r3: {"members": [[name, weight]], "votes": {name: "yes"|"no"|"abstain"}, "margin": D}. The motion passes when the weight
    of the yes votes minus the weight of the no votes (abstentions count for neither) is at least D. Weights 1 to 9 and 6 to 12 members, so the margin has a wide spread and a partial sum (yes weight alone, say) is rarely the margin. The votes are
    drawn first; the answer is then drawn (a fair coin) and D is set from the computed margin d: D = d - offset with offset in {0, 1} for yes (d >= D) and in {-1, -2} for no
    (d < D). So the answer is a function of the offset alone, which is independent of the votes: no reading of the votes alone (heaviest voter, counts, sign of the margin) and no reading
    of D alone carries it except through the offset's size (at most 2, against a margin spread of about 10). Nothing is redrawn on a heuristic's outcome."""
    n = 6 + level
    ps = r.sample(NAMES, n)
    w = {p: r.randint(1, 9) for p in ps}
    votes = {p: r.choices(("yes", "no", "abstain"), (0.4, 0.4, 0.2))[0] for p in ps}
    diff = sum(w[p] for p in ps if votes[p] == "yes") - sum(w[p] for p in ps if votes[p] == "no")
    want = r.choice(("yes", "no"))
    offset = r.randint(0, 1) if want == "yes" else -r.randint(1, 2)
    d = diff - offset
    q = ("A committee votes on a motion. " + ", ".join(f"{p} has weight {w[p]}" for p in ps) + f". The motion passes if the total weight of the members who vote yes, minus the total weight of the members who vote no, is at least {d} "
         "(members who abstain count for neither side). The votes: " + ", ".join(f"{p} {votes[p]}" for p in ps) + ". Does the motion pass? Answer yes or no.")
    return Built(q, {"members": [[p, w[p]] for p in ps], "votes": votes, "margin": d}, want, "yn", 2)


@rev4("kinship", "R1.kinship_descendants_r3")
def kinship_descendants_r4(level: int, r: random.Random) -> Built:
    """structured: {"people", "parent": {child: parent}, "ask": "descendants", "candidates": [the children of "root"], "root": name}. Question: among a named person's children, who has
    the most descendants (children, their children, and so on). All candidates are at the same depth, so depth says nothing. Each candidate's number of descendants S_i is drawn
    (distinct values, at least 6), and its numbers of children (1 to 3) and of grandchildren (1 to 3) are drawn independently of S_i; the other S_i - children - grandchildren descendants form a line
    below one grandchild. So the number of children, of grandchildren and the number of times a candidate is named are independent of the answer. The named person has a parent and a brother with children, and there is an
    unrelated family, so the named person is not the parentless root. (The earlier shape's answer was a child of the root 86 to 100 % of the time.)"""
    c = 3 + level // 2
    scores = r.sample(range(6, 8 + level + c), c)
    s_total = sum(scores)
    people = r.sample(NAMES, 1 + c + s_total + 1 + 1 + 2 + 3)
    it = iter(people)
    x = next(it)
    parent: dict[str, str] = {}
    cands = [next(it) for _ in range(c)]
    for cand in cands:
        parent[cand] = x
    for cand, s in zip(cands, scores, strict=True):
        ch, gc = r.randint(1, 3), r.randint(1, 3)  # children and grandchildren: drawn independently of the number of descendants s >= 6
        kids = [next(it) for _ in range(ch)]
        for kd in kids:
            parent[kd] = cand
        grand = [next(it) for _ in range(gc)]
        for g in grand:
            parent[g] = r.choice(kids)
        tail = r.choice(grand)
        for _ in range(s - ch - gc):  # the rest is a line hanging from one grandchild
            nd = next(it)
            parent[nd] = tail
            tail = nd
    p0, z = next(it), next(it)
    parent[x], parent[z] = p0, p0
    for _ in range(2):
        parent[next(it)] = z
    root2 = next(it)
    for _ in range(2):
        parent[next(it)] = root2
    facts = [f"{parent[ch]} is the parent of {ch}." for ch in sorted(parent)]
    r.shuffle(facts)
    best = cands[max(range(c), key=lambda i: scores[i])]
    q = " ".join(facts) + f" Nobody else has a recorded parent. Among the children of {x}, who has the most descendants (children, their children, and so on, all the way down)? Choose from {and_(sorted(cands))}."
    used = [p for p in people if p in parent or p in parent.values()]
    return Built(q, {"people": used, "parent": {ch: parent[ch] for ch in sorted(parent)}, "ask": "descendants", "candidates": sorted(cands), "root": x}, best, "name", c)


@rev4("kinship", "R1.kinship_ancestor_r3")
def kinship_ancestor_r4(level: int, r: random.Random) -> Built:
    """Same schema as kinship_ancestor: {"parent", "child", "generations", "people"}. The people form three families, each a random tree in which a new person is attached to one of the
    last three people added (long lines, few leaves). The asked person is drawn among the members of the first family at least k generations below its root (weight depth - k + 1), and the answer is
    its ancestor k generations up, which may be the root of that family (earlier shapes: never the root in _r3, always the root in the first shape). Three roots exist, and the options are the answer plus up to five people with the same number of children and the same "has a parent" status as the answer, so how often a person is
    named, whether they are a leaf and whether they are parentless say nothing about which option is right. No redraw on a heuristic's outcome."""
    k = 2 + (level >= 3) + (level >= 5)

    def grow(n: int, nodes: list[str], parent: dict[str, str]) -> None:
        for i in range(1, n):
            parent[nodes[i]] = nodes[r.randrange(0, i)]

    na, nb, nc = 10 + 2 * level, 4 + level // 2, 4 + level // 2
    people = r.sample(NAMES, na + nb + nc)
    parent: dict[str, str] = {}
    grow(na, people[:na], parent)
    grow(nb, people[na : na + nb], parent)
    grow(nc, people[na + nb :], parent)
    depth = {people[0]: 0}
    for p in people[1:na]:
        depth[p] = depth[parent[p]] + 1
    cands = [p for p in people[:na] if depth[p] >= k]
    if not cands:
        raise Retry
    child = r.choices(cands, [depth[p] - k + 1 for p in cands])[0]  # deeper people are likelier, so the answer is the root only occasionally
    ans = child
    for _ in range(k):
        ans = parent[ans]
    term = {2: "grandparent", 3: "great-grandparent", 4: "great-great-grandparent"}[k]
    facts = [f"{parent[c]} is the parent of {c}." if r.random() < 0.5 else f"{c}'s parent is {parent[c]}." for c in sorted(parent)]
    r.shuffle(facts)
    nkids = Counter(parent.values())

    def profile(p: str) -> tuple[int, bool]:
        return nkids.get(p, 0), p in parent

    pool = [p for p in people if p not in (ans, child) and profile(p) == profile(ans)]
    if len(pool) < 2:
        raise Retry
    opts = sorted([ans, *r.sample(pool, min(5, len(pool)))])
    q = " ".join(facts) + f" Nobody else has a recorded parent. Who is the {term} of {child}? Choose from {and_(opts)}."
    return Built(q, {"parent": {c: parent[c] for c in sorted(parent)}, "child": child, "generations": k, "people": sorted(people), "options": opts}, ans, "name", len(opts))


@rev4("categories", "R1.categories_default_exceptions_r3")
def categories_default_exceptions_r4(level: int, r: random.Random) -> Built:
    """Same schema as categories_default_exceptions: {"chain", "rules": [[group, verb, bool]], "member", "verb"}. The member is in the smallest group of a chain of c = T + 8 + 2 level groups;
    T = 9 + 2 (level // 2) rules (always odd, so a majority never ties) concern the asked verb, none on the member's own group; the rule on the NEAREST group (the one that decides) sits at a distance d drawn uniformly from 1 to
    c - T, so a rule at a given distance is the answer for only a small share of the items (the earlier shape put it at distance 1 in every level-0 and level-1 item and in 61 to 84 % of
    the rest). The signs: the answer is drawn first (a fair coin); the number Y of yes
    signs among the T rules is drawn uniformly from 1..T-1, independent of the answer (so the majority sign, the parity of the count, "all rules agree" and the sign of a randomly listed
    rule carry no information about the answer: each is exactly independent of it); the signs are then placed at random on the rules beyond the nearest. The one reading this cannot
    remove is a rule at a fixed distance beyond the nearest, whose sign agrees with the answer with probability 1/2 - 1/(2 (T - 1)) (an answer-sized hole in the multiset), between 0.06
    and 0.03 below chance. Chain sentences are shuffled. No redraw."""
    t = 9 + 2 * (level // 2)
    c = t + 8 + 2 * level
    chain = r.sample(PSEUDO, c)
    ask, other = r.sample(("swim", "glow", "hum", "jump", "float", "climb"), 2)
    want = r.choice((True, False))
    d = r.randint(1, c - t)
    beyond = sorted(r.sample(range(d + 1, c), t - 1))
    y = r.randint(1, t - 1)  # the number of yes signs among the T rules, uniform and independent of the answer
    n_yes_beyond = y - (1 if want else 0)
    signs = [True] * n_yes_beyond + [False] * (t - 1 - n_yes_beyond)
    r.shuffle(signs)
    rules = [[chain[d], ask, want]] + [[chain[i], ask, sg] for i, sg in zip(beyond, signs, strict=True)]
    for i in range(c):
        if r.random() < 0.3:
            rules.append([chain[i], other, r.random() < 0.5])
    member = r.choice(NAMES)
    r.shuffle(rules)
    sents = [f"Every {chain[i]} is a {chain[i + 1]}." for i in range(c - 1)]
    r.shuffle(sents)
    rule_text = " ".join(f"A {g} {'can' if ok else 'cannot'} {v}." for g, v, ok in rules)
    q = (f"{' '.join(sents)} {rule_text} When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. "
         f"{member} is a {chain[0]}. Can {member} {ask}? Answer yes or no.")
    return Built(q, {"chain": chain, "rules": rules, "member": member, "verb": ask}, "yes" if want else "no", "yn", 2)


def _closure_facts(n: int, all_e: list[tuple[int, int]], no_p: list[tuple[int, int]], some_p: list[tuple[int, int]]) -> tuple[list[list[bool]], list[set[int]]] | None:
    """Reflexive-transitive closure of the "All" edges and the witness sets: one witness per group (in the group and every group above it) and one per "Some" premise (in the groups above
    either side). Returns None when the premises are inconsistent (a group forced empty, or an overlap forced and a disjointness forced for one pair)."""
    m = _reach(all_e, n)
    up = [{t for t in range(n) if m[i][t]} for i in range(n)]

    def disjoint(x: int, y: int) -> bool:
        return any((p in up[x] and q in up[y]) or (q in up[x] and p in up[y]) for p, q in no_p)

    wit = [set(up[i]) for i in range(n)] + [up[a] | up[b] for a, b in some_p]
    if any(disjoint(i, i) for i in range(n)):
        return None
    for x in range(n):
        for y in range(x + 1, n):
            if disjoint(x, y) and any(x in f and y in f for f in wit):
                return None
    return m, wit


@rev4("categories", "R1.categories_follow_r2")
def categories_follow_r4(level: int, r: random.Random) -> Built:
    """structured: {"cats", "all": [[a, b]], "none": [[a, b]], "some": [[a, b]], "kind": "all"|"none"|"some", "x", "y", "answer_convention"}; indices into "cats".
    Premises: "All A are B." (a), "No A are B." and "Some A are B." The item STATES (ruling R-4) that every group named has at least one member, what "some" and "no" say, and what the three
    answers mean: yes = the statement must be true, no = it must be false (its opposite must be true), cannot be determined = it could be either. (The earlier frame, "Does it follow that
    ...? yes, no or cannot be determined", did not define "no": read as "no, it does not follow", 1,394 of 3,500 keys would change.)
    Entailment (complete for this fragment; witnesses: one per group, in every group above it, and one per "Some" premise, in the groups above both its sides): "All x are y" must be true iff
    y is above x; must be false iff some witness lies in x and in a group disjoint from y; "No x are y" is true iff x and y are disjoint (a "No" pair above one each) and false iff some witness
    lies in both; "Some x are y" is true iff some witness lies in both, false iff x and y are disjoint. The answer and the kind of statement are drawn first (each uniform, independent); then the pair is
    drawn uniformly among the statements of that kind with that answer that are not stated verbatim (Retry when there is none). So the kind carries no information about the answer."""
    n = 4 + (level + 1) // 2
    cats = r.sample(PSEUDO, n)
    want = r.choice(YNU)
    kind = r.choice(("all", "none", "some"))  # the answer and the kind of statement are drawn first; premises are redrawn until a statement with both exists
    for _ in range(80):
        allw = [(i, j) for i in range(n) for j in range(i + 1, n)]
        all_e = r.sample(allw, min(len(allw), n - 1 + r.randint(0, 1)))
        no_p = [tuple(r.sample(range(n), 2)) for _ in range(1 + level // 3)]
        some_p = [tuple(r.sample(range(n), 2)) for _ in range(1 + level // 2)]
        if {x for e in [*all_e, *no_p, *some_p] for x in e} != set(range(n)):
            continue
        cl = _closure_facts(n, all_e, no_p, some_p)  # type: ignore[arg-type]
        if cl is None:
            continue
        m, wit = cl
        up = [{t for t in range(n) if m[i][t]} for i in range(n)]

        def disjoint(x: int, y: int) -> bool:
            return any((p in up[x] and q in up[y]) or (q in up[x] and p in up[y]) for p, q in no_p)  # noqa: B023

        def overlap(x: int, y: int) -> bool:
            return any(x in f and y in f for f in wit)  # noqa: B023

        def false_all(x: int, y: int) -> bool:
            return any(x in f and any(disjoint(g, y) for g in f) for f in wit)  # noqa: B023

        stated = {("all", a, b) for a, b in all_e} | {("none", a, b) for a, b in no_p} | {("none", b, a) for a, b in no_p} | {("some", a, b) for a, b in some_p} | {("some", b, a) for a, b in some_p}
        cands = []
        for x in range(n):
            for y in range(n):
                if x == y or (kind, x, y) in stated:
                    continue
                if kind == "all":
                    ans = "yes" if m[x][y] else ("no" if false_all(x, y) else "cannot be determined")
                elif kind == "none":
                    ans = "yes" if disjoint(x, y) else ("no" if overlap(x, y) else "cannot be determined")
                else:
                    ans = "yes" if overlap(x, y) else ("no" if disjoint(x, y) else "cannot be determined")
                if ans == want:
                    cands.append((x, y))
        if cands:
            break
    else:
        raise Retry
    x, y = r.choice(cands)
    stmt = {"all": f"every {cats[x]} is a {cats[y]}", "none": f"no {cats[x]} is a {cats[y]}", "some": f"some {cats[x]} are {cats[y]}"}[kind]
    sents = [f"All {cats[a]} are {cats[b]}." for a, b in all_e] + [f"No {cats[a]} are {cats[b]}." for a, b in no_p] + [f"Some {cats[a]} are {cats[b]}." for a, b in some_p]
    r.shuffle(sents)
    conv = ("Every group named here has at least one member. \"Some X are Y\" means that at least one thing is both an X and a Y; \"No X are Y\" means that nothing is both.")
    q = (" ".join(sents) + f" {conv} Consider the statement: \"{stmt}\". Answer yes if the statement must be true, no if the statement must be false, or cannot be determined if the statements above "
         "leave it open (it could be true and it could be false).")
    return Built(q, {"cats": cats, "all": [list(e) for e in all_e], "none": [list(p) for p in no_p], "some": [list(p) for p in some_p], "kind": kind, "x": x, "y": y, "answer_convention": "yes = must be true; no = must be false; cannot be determined = could be either; every named group is non-empty"}, want, "ynu", 3)


@rev4("elimination", "R1.elimination_bracket_r3")
def elimination_bracket_r4(level: int, r: random.Random) -> Built:
    """structured: {"players": [bracket order], "results": [[winner, loser]] (every pair, a random near-regular tournament), "ask": ["champion"] | ["runner_up"] | ["beaten_by", name, exit_round]}.
    Adjacent players meet in round one, the winner of a meeting is the one who won their earlier game; winners keep their order and pair adjacent again. 8 players for levels 0 to 2, 16 for
    levels 3 to 6. The tournament of results is a random NEAR-REGULAR one (every player wins half their games, give or take one), so a player's number of wins says almost nothing about how far
    they go (a random tournament made the most-wins player champion 47 % of the time). Question by level: 0 champion; 1 runner-up; 2 champion or runner-up; 3 champion; 4 runner-up; 5 "who
    knocks X out" for X drawn uniformly among the players who lose in round 3 (the semi-finals); 6 any of the three kinds. Never round one (so the first-round neighbour is never the answer; the
    earlier shape: neighbour right in 69 % of the "knocks out" items) and never round two (the knocker is then one of two players of X's own quarter, which the bracket geometry gives away).
    The round of exit is chosen first; nothing is redrawn on a heuristic's outcome."""
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
    kinds = {0: ["champion"], 1: ["runner_up"], 2: ["champion", "runner_up"], 3: ["champion"], 4: ["runner_up"], 5: [3], 6: ["champion", "runner_up", 3]}[level]
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
