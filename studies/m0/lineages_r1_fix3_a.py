# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 3, part a: scheduling, rule trees, conditional rules, closure relations (order, roads, equivalence). Ids end in ``_r5``.

activity_selection_r5     zones as in _r4 plus two zones that decouple the answer from the number of meetings (a clique of 2-6 mutually overlapping meetings = 1; a run of 2-4 separate meetings = their number)
attribute_rule_r5         every badge matches the SAME number k of the rule's tests (k drawn first); one badge satisfies the rule, the others do not; so counting matched tests says nothing
conditional_chain_r5      the asked variable is never a stated fact; the answer class is drawn first; derivations are 2 or more steps; every item has two rules that conclude the asked variable
order_compare_r5          the answer class is drawn first; a planted chain of d (uniform over a six-value window that starts at 2 + level) steps; the pair is stated in neither direction
road_reachability_r5      as order_compare_r5 for one-way roads; the outdegree of the start and the number of roads are drawn independently of the answer
equivalence_classes_r5    as order_compare_r5 for same / different statements: a planted chain of "same" links, with one "different" link in the middle for the answer no
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1 import _rule_eval, _rule_text
from studies.m0.lineages_r1_common import and_
from studies.m0.lineages_r1_fix3_common import YNU, fix3
from studies.m0.vocab import COLOURS, MARKS, NAMES, PSEUDO, SHAPES, TOWNS

# ---------------------------------------------------------------- activity selection


@fix3("scheduling", "R1.activity_selection_r4")
def activity_selection_r5(level: int, r: random.Random) -> Built:
    """structured: {"meetings": [[name, start, end]], "zones": [kind]}. Largest number of meetings one person can attend (open number); a meeting that ends at minute t and one that starts at minute t do not overlap.
    The day is a row of zones, none of which touches the next. Zones: A, two long meetings that touch and a short one across the join (shortest first loses one); B, one long early meeting over 2 to 6 short ones (earliest
    start gets one); C, one meeting; D, three meetings with random overlaps; E, a clique of 2 to 6 meetings that share a minute (contributes 1, adds 2 to 6 meetings); F, 1 to 10 separate meetings (contributes that many).
    E and F make the answer independent of the number of meetings (the earlier shape: "two thirds of the meetings" scored +0.46 at level 0). Every item has two A and two B zones, the rest are drawn from A, A, A, B, B, B, D, E, F (the trap zones make a greedy pass in the listed order wrong most of the time)."""
    nz = 6 + level // 2
    kinds = ["A", "B", "A", "B"] + [r.choice("AAABBBDEF") for _ in range(nz - 4)]
    r.shuffle(kinds)
    ms: list[tuple[int, int]] = []
    t = r.randint(0, 5)
    planned = 0
    for k in kinds:
        if k == "A":
            x, y = r.randint(1, 3), r.randint(1, 3)
            a, b = x + y + r.randint(1, 6), x + y + r.randint(1, 6)
            ms += [(t, t + a), (t + a, t + a + b), (t + a - x, t + a + y)]
            t += a + b
            planned += 2
        elif k == "B":
            m = r.randint(2, 6)
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
        elif k == "D":
            seg = [(t + r.randint(0, 6), 0) for _ in range(3)]
            seg = [(s0, s0 + r.randint(2, 7)) for s0, _ in seg]
            ms += seg
            best, last = 0, -1
            for s0, e0 in sorted(seg, key=lambda z: (z[1], z[0])):
                if s0 >= last:
                    best += 1
                    last = e0
            planned += best
            t = max(e for _, e in seg)
        elif k == "E":
            c = t + r.randint(2, 5)  # the shared minute is strictly inside every meeting
            for _ in range(r.randint(2, 6)):
                ms.append((c - r.randint(1, 4), c + r.randint(1, 4)))
            planned += 1
            t = max(e for _, e in ms)
        else:
            for _ in range(r.randint(1, 10)):
                d = r.randint(2, 6)
                ms.append((t, t + d))
                t += d + r.randint(0, 2)
                planned += 1
        t += r.randint(1, 3)
    chosen, last = 0, -1
    for s0, e0 in sorted(ms, key=lambda z: (z[1], z[0])):
        if s0 >= last:
            chosen += 1
            last = e0
    if chosen != planned:  # validity: the zone-wise sum must equal the earliest-finish count
        raise Retry
    ps = r.sample(NAMES, len(ms))
    items = [[p, s0, e0] for p, (s0, e0) in zip(ps, ms, strict=True)]
    r.shuffle(items)
    q = " ".join(f"{p}'s meeting runs from minute {s0} to minute {e0}." for p, s0, e0 in items) + " A meeting that ends at minute t and one that starts at minute t do not overlap. What is the largest number of these meetings that one person could attend?"
    return Built(q, {"meetings": items, "zones": kinds}, str(chosen), "number", None)


# ---------------------------------------------------------------- attribute rule (evaluation of a rule tree on a badge)


def _leaves(rule: list) -> list[list]:
    return [rule] if rule[0] == "attr" else [x for c in rule[1:] for x in _leaves(c)]


@fix3("rules", "R1.attribute_rule")
def attribute_rule_r5(level: int, r: random.Random) -> Built:
    """structured: {"rule", "owners", "items"} as attribute_rule. The rule is built as before but two deeper (depth 3 + level // 2: a rule of two tests is decided by counting them, so no k separates the satisfying badge), leaves 'colour/shape/mark is v', and, or, not). The number k of the rule's tests that a badge matches is drawn
    FIRST (uniformly among 1 .. leaves - 1 for which at least one badge that satisfies the rule and at least n - 1 that do not exist); the satisfying badge is drawn uniformly among the badges that match exactly k tests and
    satisfy the rule, and each of the other n - 1 uniformly among the distinct badges that match exactly k tests and do not. So every badge matches the same number of tests: "the badge that matches most tests" and its
    variants are uninformative by construction. Nothing is redrawn on a heuristic."""
    n = 4 + min(level, 4)
    vals = {"colour": COLOURS, "shape": SHAPES, "mark": MARKS}

    def leaf() -> list:
        a = r.choice(sorted(vals))
        return ["attr", a, r.choice(vals[a])]

    depth = 3 + level // 2
    ops = ["and", "or", *[r.choice(("and", "or")) for _ in range(depth - 2)]]  # both operators occur in every rule, so "read every operator as or / and" is never the rule's own structure
    r.shuffle(ops)
    rule: list = [ops[0], leaf(), leaf()]
    for i in range(depth - 1):
        new = ["not", leaf()] if (i == 0 or r.random() < 0.5) else leaf()  # at least one negation in every rule
        rule = [ops[i + 1], *((rule, new) if r.random() < 0.5 else (new, rule))]  # the new test comes before or after the rest of the rule
    lv = _leaves(rule)
    pool: dict[tuple[int, bool], list[dict[str, str]]] = {}
    for c in COLOURS:
        for sh in SHAPES:
            for m in MARKS:
                it = {"colour": c, "shape": sh, "mark": m}
                pool.setdefault((sum(it[x[1]] == x[2] for x in lv), _rule_eval(rule, it)), []).append(it)
    ks = [k for k in range(1, len(lv)) if len(pool.get((k, True), [])) >= 1 and len(pool.get((k, False), [])) >= n - 1]
    if not ks:
        raise Retry
    k = r.choice(ks)
    win = r.choice(pool[(k, True)])
    others = r.sample(pool[(k, False)], n - 1)
    items = [win, *others]
    owners = r.sample(NAMES, n)
    order = list(range(n))
    r.shuffle(order)
    items = [items[i] for i in order]
    ans = owners[order.index(0)]
    txt = "; ".join(f"{o}'s badge is {it['colour']}, {it['shape']} and has {it['mark']}" for o, it in zip(owners, items, strict=True))
    q = (f"A gate opens for a badge if the badge satisfies this rule: {_rule_text(rule)}. The badges: {txt}. "
         f"Whose badge opens the gate? Choose from {and_(sorted(owners))}.")
    return Built(q, {"rule": rule, "owners": owners, "items": items}, ans, "name", n)


# ---------------------------------------------------------------- conditional rules


def _models(n: int, facts: list[tuple[int, bool]], rules: list[tuple[list[tuple[int, bool]], tuple[int, bool]]], q: int) -> set[bool]:
    """Values of variable q over every assignment (n variables) that satisfies the facts and every rule (full entailment, not only forward chaining)."""
    seen: set[bool] = set()
    for w in range(1 << n):
        if any(bool((w >> v) & 1) != b for v, b in facts):
            continue
        if all(not all(bool((w >> v) & 1) == b for v, b in ante) or bool((w >> cv) & 1) == cb for ante, (cv, cb) in rules):
            seen.add(bool((w >> q) & 1))
    return seen


@fix3("conditional", "R1.conditional_chain")
def conditional_chain_r5(level: int, r: random.Random) -> Built:
    """structured: {"vars", "facts": [[v, bool]], "rules": [[[[v, bool]], [v, bool]]], "query"} as conditional_chain. The answer class (yes / no / cannot be determined) is drawn FIRST, uniformly. The asked variable q is never a stated
    fact (the earlier shape stated it in 37 to 49 % of the items). yes / no: a chain of d = 2 + level // 3 rules leads from a stated fact to q (the antecedent of a rule is the previous variable, with a second, true,
    stated fact in half of the rules); a decoy chain of the same length is added to every other item class too. Every item has exactly two rules that conclude q: yes / no: the last rule of the chain and one trap rule of the
    opposite sign whose antecedent is a literal that is false in the hidden world; cannot be determined: two trap rules of opposite signs. The remaining rules (n + level in all) are sound random rules (a rule whose antecedent
    holds in the hidden world has a conclusion that holds there; none concludes q). The class is then checked by enumerating every assignment (a Retry only when the checked class differs from the drawn one: a validity rule)."""
    n = 7 + level
    vs = list(range(n))
    want = r.choice(YNU)
    q = r.randrange(n)
    hidden = [r.random() < 0.5 for _ in range(n)]
    if want != "cannot be determined":
        hidden[q] = want == "yes"
    others = [v for v in vs if v != q]
    r.shuffle(others)
    nf = 2 + level // 2
    d = 2 + level // 3
    facts_v = others[:nf]
    inter = others[nf : nf + d - 1]  # intermediate variables of the chain (or of the decoy chain)
    free = others[nf + d - 1 :]
    if len(free) < 3:
        raise Retry
    facts = [(v, hidden[v]) for v in facts_v]
    rules: list[tuple[list[tuple[int, bool]], tuple[int, bool]]] = []
    path = [facts_v[0], *inter]
    end = q if want != "cannot be determined" else free.pop()  # the decoy chain of the other classes ends at a variable that is not q
    path.append(end)
    for a, b in zip(path, path[1:], strict=False):
        ante = [(a, hidden[a])]
        if r.random() < 0.5:
            ante.append((r.choice(facts_v), True))
            ante[-1] = (ante[-1][0], hidden[ante[-1][0]])
        rules.append((ante, (b, hidden[b])))
    u1, u2 = free[0], free[1]
    if want == "cannot be determined":
        rules.append(([(u1, not hidden[u1])], (q, True)))
        rules.append(([(u2, not hidden[u2])], (q, False)))
    else:
        rules.append(([(u1, not hidden[u1])], (q, not hidden[q])))
    total = n + level
    guard = 0
    while len(rules) < total and guard < 200:
        guard += 1
        ante_v = r.sample(vs, r.randint(1, 2))
        ante = [(v, hidden[v] if r.random() < 0.7 else not hidden[v]) for v in ante_v]
        cv = r.choice([v for v in vs if v != q])
        sound = all(hidden[v] == b for v, b in ante)
        cb = hidden[cv] if sound else r.random() < 0.5
        rules.append((ante, (cv, cb)))
    seen = _models(n, facts, rules, q)
    got = "cannot be determined" if len(seen) == 2 else ("yes" if True in seen else "no")
    if got != want:
        raise Retry
    letters = [chr(65 + i) for i in vs]

    def lit(v: int, b: bool) -> str:
        return f"{letters[v]} is {'true' if b else 'false'}"

    sents = [f"{lit(v, b)}." for v, b in facts]
    sents += [f"If {' and '.join(lit(v, b) for v, b in ante)}, then {lit(cv, cb)}." for ante, (cv, cb) in rules]
    r.shuffle(sents)
    text = " ".join(sents) + f" Is {letters[q]} true? Answer yes, no or cannot be determined."
    st = {"vars": letters, "facts": [[letters[v], b] for v, b in facts], "rules": [[[[letters[v], b] for v, b in a], [letters[c[0]], c[1]]] for a, c in rules], "query": letters[q]}
    return Built(text, st, want, "ynu", 3)


# ---------------------------------------------------------------- closure shapes: order, roads, equivalence (planted chains; the class is drawn first)


def _reach_set(edges: list[tuple[int, int]], n: int, src: int) -> set[int]:
    seen = {src}
    stack = [src]
    while stack:
        u = stack.pop()
        for a, b in edges:
            if a == u and b not in seen:
                seen.add(b)
                stack.append(b)
    return seen


@fix3("order", "R1.order_compare_r4")
def order_compare_r5(level: int, r: random.Random) -> Built:
    """structured: {"taller": [[a, b]] (a is taller than b), "x", "y"} as order_compare. The answer class is drawn first (uniform over yes, no, cannot be determined). The depth is controlled by level: a planted chain whose
    x-to-y part has d steps, d uniform in 2 + level .. 7 + level, with 1 or 2 more people above x and below y. yes: x is d steps above y; no: the reverse; cannot be determined: x and y lie in two separate chains of about d / 2 steps each. Every person outside the
    chains is a leaf: x and y each get 0 to 3 shorter and 0 to 3 taller leaves (independent of the class), and 1 + level // 3 more hang from random chain persons, so the degrees of x and y say nothing. The asked pair is stated in neither direction. So a search of k steps answers only the items with d <= k (at most a sixth of the yes / no items), and
    the earlier shape's "two steps, else cannot be determined" (+0.64 at every level) reads chance."""
    want = r.choice(YNU)
    d = r.randint(2 + level, 7 + level)
    lx = [r.randint(0, 3), r.randint(0, 3)]  # leaves that x is taller than / shorter than, and the same for y: drawn independently of the class
    ly = [r.randint(0, 3), r.randint(0, 3)]
    ex = sum(lx) + sum(ly) + 1 + level // 3
    pad = r.randint(1, 2)  # chain people above x and below y (or the reverse), so x and y are never the ends of a chain: each has a taller and a shorter neighbour
    if want == "cannot be determined":
        la, lb = (d + 1) // 2 + 2, d // 2 + 3
        n = la + 1 + lb + 1 + ex
    else:
        n = d + 1 + 2 * pad + ex
    order = r.sample(NAMES, n)
    ids = list(range(n))
    r.shuffle(ids)
    edges: list[tuple[int, int]] = []  # (taller, shorter) as indices into order
    if want == "cannot be determined":
        ca, cb = ids[: la + 1], ids[la + 1 : la + 1 + lb + 1]
        for ch in (ca, cb):
            edges += list(zip(ch, ch[1:], strict=False))
        x, y = r.choice(ca[1:-1]), r.choice(cb[1:-1])
        if r.random() < 0.5:
            x, y = y, x
        rest = ids[la + 1 + lb + 1 :]
        comps = [ca, cb]
    else:
        ch = ids[: d + 1 + 2 * pad]
        edges += list(zip(ch, ch[1:], strict=False))
        top, bottom = ch[pad], ch[pad + d]
        x, y = (top, bottom) if want == "yes" else (bottom, top)
        rest = ids[d + 1 + 2 * pad :]
        comps = [ch]
    it = iter(rest)
    for who, (tl, sl) in ((x, lx), (y, ly)):
        for _ in range(tl):
            edges.append((who, next(it)))  # who is taller than the leaf
        for _ in range(sl):
            edges.append((next(it), who))
    for e in it:  # the remaining leaves hang from a random chain person
        anchor = r.choice(r.choice(comps))
        edges.append((anchor, e) if r.random() < 0.5 else (e, anchor))
    facts = [(order[a], order[b]) for a, b in edges]
    r.shuffle(facts)
    q = " ".join(f"{p} is taller than {s}." for p, s in facts) + f" Is {order[x]} taller than {order[y]}? Answer yes, no or cannot be determined."
    return Built(q, {"taller": [list(f) for f in facts], "x": order[x], "y": order[y]}, want, "ynu", 3)


@fix3("graph", "R1.road_reachability")
def road_reachability_r5(level: int, r: random.Random) -> Built:
    """structured: {"towns", "roads": [[a, b]] (one-way a -> b), "x", "y"} as road_reachability. The answer (yes / no) is drawn first. The route is a planted chain x = c0 -> c1 -> ... -> cd = y with d uniform in 3 + level .. 6 + level.
    yes: the chain is complete. no: the link c_j -> c_{j+1} is missing (j uniform in 0 .. d - 2), so y is out of reach; every other town of the 'no' item is placed so that no road leads from the towns x can reach to the
    others. In both classes the outdegree k of x is drawn first (1 to 3, extra roads of x go to other towns that x can reach), a reversed road c_{i+1} -> c_i is added with probability 1/2, and the number of further roads is drawn
    independently of the answer (2 to n / 2 + 2). So the outdegree of x, the number of roads, and 'within two roads' carry no information (the earlier shape: outdegree >= 2 scored +0.35)."""
    want = r.choice(("yes", "no"))
    d = r.randint(3 + level, 6 + level)
    ex = r.randint(3, 5)
    n = d + 1 + ex
    towns = r.sample(TOWNS, n)
    ids = list(range(n))
    r.shuffle(ids)
    ch, extra = ids[: d + 1], ids[d + 1 :]
    x, y = ch[0], ch[-1]
    edges: set[tuple[int, int]] = set()
    if want == "yes":
        edges.update(zip(ch, ch[1:], strict=False))
        reach_core = set(ids)
        allowed = [(a, b) for a in ids for b in ids if a != b]
        out_pool = [e for e in extra]
    else:
        j = r.randint(0, d - 2)
        edges.update(e for i, e in enumerate(zip(ch, ch[1:], strict=False)) if i != j)
        er = r.sample(extra, r.randint(min(2, len(extra)), len(extra)))  # the extra towns placed with x (at least two, so the outdegree of x can be drawn as in a yes item)
        reach_core = {*ch[: j + 1], *er}  # what x can reach (the chain up to c_j and the extra towns placed with it)
        allowed = [(a, b) for a in ids for b in ids if a != b and not (a in reach_core and b not in reach_core)]
        out_pool = er
    k = r.randint(1, 3)
    cand = [t for t in (out_pool if want == "no" else extra) if t != x and (x, t) not in edges]
    for t in r.sample(cand, min(k - 1, len(cand))):
        edges.add((x, t))
    if r.random() < 0.5:
        i = r.randrange(d)
        if (ch[i + 1], ch[i]) in allowed:
            edges.add((ch[i + 1], ch[i]))
    m = r.randint(2, n // 2 + 2)
    pool = [e for e in allowed if e not in edges and e != (x, y) and not (e[0] == x and e not in edges)]
    for e in r.sample(pool, min(m, len(pool))):
        edges.add(e)
    if want == "no" and y in _reach_set(sorted(edges), n, x):
        raise Retry  # cannot happen by construction; kept as a validity check
    if want == "yes" and y not in _reach_set(sorted(edges), n, x):
        raise Retry
    el = sorted(edges)
    r.shuffle(el)
    q = (" ".join(f"There is a one-way road from {towns[a]} to {towns[b]}." for a, b in el)
         + f" There are no other roads. Can you travel from {towns[x]} to {towns[y]} using these roads? Answer yes or no.")
    return Built(q, {"towns": towns, "roads": [list(e) for e in el], "x": x, "y": y}, want, "yn", 2)


@fix3("kinship", "R1.equivalence_classes_r2")
def equivalence_classes_r5(level: int, r: random.Random) -> Built:
    """structured: {"items", "same": [[a, b]], "different": [[a, b]], "x", "y"} as equivalence_classes. The answer class is drawn first. A planted chain of d "same" links (d uniform in 2 + level .. 7 + level) joins x and y (yes);
    for no, the chain is cut in the middle by one "different" link (d links in all); for cannot be determined x and y lie in two separate chains of about d / 2 links. Decoy items (6 + level of them) form separate small groups that
    are tied to the chains by "different" links (never between the groups of x and y unless the answer is no) and by "same" links within themselves. The asked pair is never stated and a common same-neighbour exists only by chance
    (the earlier shape: common neighbour scored +0.29)."""
    want = r.choice(YNU)
    d = r.randint(2 + level, 7 + level)
    ex = 6 + level
    if want == "cannot be determined":
        la, lb = (d + 1) // 2, d // 2
        n = la + 1 + lb + 1 + ex
    else:
        n = d + 1 + ex
    items = r.sample(PSEUDO, n)
    ids = list(range(n))
    r.shuffle(ids)
    same: list[tuple[int, int]] = []
    diff: list[tuple[int, int]] = []
    if want == "yes":
        ch = ids[: d + 1]
        same += list(zip(ch, ch[1:], strict=False))
        x, y = ch[0], ch[-1]
        rest = ids[d + 1 :]
        gx = gy = 0
        groups = [ch]
    elif want == "no":
        ch = ids[: d + 1]
        cut = r.randint(0, d - 1)  # link number `cut` is the different one
        for i, e in enumerate(zip(ch, ch[1:], strict=False)):
            (diff if i == cut else same).append(e)
        x, y = ch[0], ch[-1]
        rest = ids[d + 1 :]
        groups = [ch[: cut + 1], ch[cut + 1 :]]
        gx, gy = 0, 1
    else:
        ca, cb = ids[: la + 1], ids[la + 1 : la + lb + 2]
        for c in (ca, cb):
            same += list(zip(c, c[1:], strict=False))
        x, y = ca[0], cb[-1]
        rest = ids[la + lb + 2 :]
        groups = [ca, cb]
        gx, gy = 0, 1
    for e in rest:  # each decoy item joins a decoy group of its own, or is tied by a different link
        if r.random() < 0.5 and len(groups) > 2:
            g = r.randrange(2, len(groups))
            same.append((r.choice(groups[g]), e))
            groups[g].append(e)
        else:
            groups.append([e])
    for _ in range(3 + level // 2):
        ga, gb = r.sample(range(len(groups)), 2)
        if {ga, gb} == {gx, gy} and want != "no":
            continue
        diff.append((r.choice(groups[ga]), r.choice(groups[gb])))
    # validity: the drawn class must be the entailed one
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in same:
        parent[find(a)] = find(b)
    if any(find(a) == find(b) for a, b in diff):
        raise Retry
    forced = {(find(a), find(b)) for a, b in diff} | {(find(b), find(a)) for a, b in diff}
    got = "yes" if find(x) == find(y) else ("no" if (find(x), find(y)) in forced else "cannot be determined")
    if got != want or frozenset((x, y)) in {frozenset(p) for p in [*same, *diff]}:
        raise Retry
    sents = [f"{items[a]} is the same thing as {items[b]}." for a, b in same] + [f"{items[a]} is a different thing from {items[b]}." for a, b in diff]
    r.shuffle(sents)
    q = " ".join(sents) + f" Is {items[x]} the same thing as {items[y]}? Answer yes (they must be the same), no (they must be different) or cannot be determined."
    return Built(q, {"items": items, "same": [[items[a], items[b]] for a, b in same], "different": [[items[a], items[b]] for a, b in diff], "x": items[x], "y": items[y]}, want, "ynu", 3)
