# ruff: noqa: E501
"""R1, reasoning: deduction over stated relations (ADR-0033 section 6.2). Hand-written base rules (lineages).

Each builder takes (level, rng) with level 0 (reserve, easier) to 6 (reserve, harder) and returns one item.
The answer is fixed by construction here; the independent second solvers are in ``solvers_r1`` and read only
the item's structured form. No builder iterates a set or dict of strings without sorting and none calls hash().
"""

from __future__ import annotations

import itertools
import random

from studies.m0.core import Built, Retry, lineage
from studies.m0.vocab import COLOURS, EVENTS, MARKS, NAMES, OBJECTS, PETS, PSEUDO, SHAPES, TOWNS

YNU = ("yes", "no", "cannot be determined")


def _and(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _reach(edges: list[tuple[int, int]], n: int) -> list[list[bool]]:
    m = [[i == j for j in range(n)] for i in range(n)]
    for a, b in edges:
        m[a][b] = True
    for k in range(n):
        for i in range(n):
            if m[i][k]:
                for j in range(n):
                    if m[k][j]:
                        m[i][j] = True
    return m


# ---------------------------------------------------------------- order (linear order)


@lineage("R1", "order")
def order_extreme(level: int, r: random.Random) -> Built:
    n = 3 + level
    order = r.sample(NAMES, n)  # order[0] is the tallest
    ask = r.choice(("tallest", "shortest"))
    rels = [(order[i], order[i + 1]) for i in range(n - 1)]
    r.shuffle(rels)
    sents = [f"{a} is taller than {b}." if r.random() < 0.5 else f"{b} is shorter than {a}." for a, b in rels]
    people = sorted(order)
    q = " ".join(sents) + f" Who is the {ask} of {_and(people)}?"
    ans = order[0] if ask == "tallest" else order[-1]
    return Built(q, {"people": people, "taller": [list(x) for x in rels], "ask": ask}, ans, "name", n)


@lineage("R1", "order")
def order_compare(level: int, r: random.Random) -> Built:
    n = 3 + level
    order = r.sample(NAMES, n)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    given = r.sample(pairs, min(len(pairs), n - 1 + r.randint(0, 1)))
    edges = [(a, b) for a, b in given]  # order[a] is taller than order[b] (a < b)
    m = _reach(edges, n)
    target = r.choice(YNU)
    cands = []
    for x in range(n):
        for y in range(n):
            if x == y:
                continue
            a = "yes" if m[x][y] else ("no" if m[y][x] else "cannot be determined")
            if a == target:
                cands.append((x, y, a))
    if not cands:
        raise Retry
    x, y, a = r.choice(cands)
    facts = [(order[i], order[j]) for i, j in given]
    r.shuffle(facts)
    q = " ".join(f"{p} is taller than {s}." for p, s in facts) + f" Is {order[x]} taller than {order[y]}? Answer yes, no or cannot be determined."
    return Built(q, {"taller": [list(f) for f in facts], "x": order[x], "y": order[y]}, a, "ynu", 3)


# ---------------------------------------------------------------- kinship


def _tree(r: random.Random, chain_len: int, extras: int) -> tuple[list[str], dict[str, str], list[str]]:
    people = r.sample(NAMES, chain_len + extras)
    chain = people[:chain_len]
    parent: dict[str, str] = {chain[i + 1]: chain[i] for i in range(chain_len - 1)}
    placed = chain[:]
    for p in people[chain_len:]:
        parent[p] = r.choice(placed)
        placed.append(p)
    return people, parent, chain


@lineage("R1", "kinship")
def kinship_ancestor(level: int, r: random.Random) -> Built:
    k = 2 + (level >= 3) + (level >= 5)
    people, parent, chain = _tree(r, k + 1, 2 + level)
    term = {2: "grandparent", 3: "great-grandparent", 4: "great-great-grandparent"}[k]
    facts = [f"{parent[c]} is the parent of {c}." if r.random() < 0.5 else f"{c}'s parent is {parent[c]}." for c in sorted(parent)]
    r.shuffle(facts)
    q = " ".join(facts) + f" Nobody else has a recorded parent. Who is the {term} of {chain[-1]}? Choose from {_and(sorted(people))}."
    return Built(q, {"parent": {c: parent[c] for c in sorted(parent)}, "child": chain[-1], "generations": k, "people": sorted(people)}, chain[0], "name", len(people))


@lineage("R1", "kinship")
def kinship_cousins(level: int, r: random.Random) -> Built:
    fam = 2 + level // 2 + 1  # children of the root
    names = r.sample(NAMES, 60)
    it = iter(names)
    parent: dict[str, str] = {}
    grand: list[str] = []
    for _ in range(2):  # two unrelated roots
        root = next(it)
        kids = [next(it) for _ in range(r.randint(2, fam))]
        for kd in kids:
            parent[kd] = root
            for _ in range(r.randint(1, 2)):
                gc = next(it)
                parent[gc] = kd
                grand.append(gc)
    pairs = [(a, b) for i, a in enumerate(grand) for b in grand[i + 1 :]]
    want = r.choice(("yes", "no"))
    good = [(a, b) for a, b in pairs if (parent[parent[a]] == parent[parent[b]] and parent[a] != parent[b]) == (want == "yes")]
    if not good:
        raise Retry
    a, b = r.choice(good)
    facts = [f"{parent[c]} is the parent of {c}." for c in sorted(parent)]
    r.shuffle(facts)
    q = (" ".join(facts) + " Nobody else has a recorded parent. Two people are cousins if their parents are different people who have the same parent. "
         f"Are {a} and {b} cousins? Answer yes or no.")
    return Built(q, {"parent": {c: parent[c] for c in sorted(parent)}, "x": a, "y": b}, want, "yn", 2)


# ---------------------------------------------------------------- categories (syllogisms)


@lineage("R1", "categories")
def categories_follow(level: int, r: random.Random) -> Built:
    n = 4 + (level + 1) // 2
    cats = r.sample(PSEUDO, n)
    # all-edges respect a hidden order so that the statements are consistent; no-pairs avoid emptying a category by hand
    allw = [(i, j) for i in range(n) for j in range(i + 1, n)]
    all_e = r.sample(allw, min(len(allw), n - 1 + r.randint(0, 1)))
    # exclusion pairs: only between categories that share no common subcategory, kept few
    no_p: list[tuple[int, int]] = []
    for _ in range(1 + level // 3):
        i, j = r.sample(range(n), 2)
        no_p.append((i, j))
    m = _reach([(a, b) for a, b in all_e], n)
    kind = r.choice(("all", "none", "some"))
    x, y = r.sample(range(n), 2)

    def above(i: int) -> list[int]:
        return [t for t in range(n) if m[i][t]]

    for i in range(n):  # a category forced empty would make "all" vacuous; the type semantics of the second solver differs
        if any(p in above(i) and q in above(i) for p, q in no_p):
            raise Retry
    disj = any(((p in above(x) and q in above(y)) or (q in above(x) and p in above(y))) for p, q in no_p)
    if kind == "all":
        ans = "yes" if m[x][y] else "cannot be determined"
        qs = f"Does it follow that every {cats[x]} is a {cats[y]}?"
    elif kind == "none":
        ans = "yes" if disj else "cannot be determined"
        qs = f"Does it follow that no {cats[x]} is a {cats[y]}?"
    else:
        ans = "no" if disj else "cannot be determined"
        qs = f"Does it follow that some {cats[x]} are {cats[y]}?"
        if not disj and m[x][y]:
            raise Retry  # "some" with an implied containment would need an existence premise
    target = r.choice(YNU)
    if ans != target and r.random() < 0.85:
        raise Retry
    sents = [f"All {cats[a]} are {cats[b]}." for a, b in all_e] + [f"No {cats[a]} are {cats[b]}." for a, b in no_p]
    r.shuffle(sents)
    q = " ".join(sents) + f" {qs} Answer yes, no or cannot be determined."
    st = {"cats": cats, "all": [list(e) for e in all_e], "none": [list(p) for p in no_p], "kind": kind, "x": x, "y": y}
    return Built(q, st, ans, "ynu", 3)


# ---------------------------------------------------------------- conditional rules


@lineage("R1", "conditional")
def conditional_chain(level: int, r: random.Random) -> Built:
    n = 5 + level
    vs = [chr(65 + i) for i in range(n)]
    hidden = {v: r.random() < 0.5 for v in vs}
    facts_n = 2 + level // 2
    fact_vars = r.sample(vs, facts_n)
    facts = [(v, hidden[v]) for v in fact_vars]
    rules: list[tuple[list[tuple[str, bool]], tuple[str, bool]]] = []
    for _ in range(n + level):
        ante = [(v, hidden[v] if r.random() < 0.8 else not hidden[v]) for v in r.sample(vs, r.randint(1, 2))]
        concl_v = r.choice(vs)
        sound = all(hidden[v] == b for v, b in ante)
        # a rule whose antecedent holds in the hidden world must have a conclusion true there
        concl = (concl_v, hidden[concl_v]) if sound else (concl_v, r.random() < 0.5)
        rules.append((ante, concl))
    # forward chaining over literals
    known = dict(facts)
    changed = True
    while changed:
        changed = False
        for ante, (cv, cb) in rules:
            if all(known.get(v) is b for v, b in ante) and cv not in known:
                known[cv] = cb
                changed = True
    q_v = r.choice(vs)
    ans = "cannot be determined" if q_v not in known else ("yes" if known[q_v] else "no")
    # forward chaining alone is incomplete (modus tollens); keep only items whose full entailment agrees
    idx = {v: i for i, v in enumerate(vs)}
    clauses = []
    for ante, (cv, cb) in rules:
        am = sum(1 << idx[v] for v, _ in ante)
        av = sum(1 << idx[v] for v, b in ante if b)
        clauses.append((am, av, 1 << idx[cv], cb))
    fm = sum(1 << idx[v] for v, _ in facts)
    fv = sum(1 << idx[v] for v, b in facts if b)
    seen = set()
    for w in range(1 << n):
        if (w & fm) != fv:
            continue
        if all(((w & am) != av) or (bool(w & cm) == cb) for am, av, cm, cb in clauses):
            seen.add(bool(w & (1 << idx[q_v])))
    full = "cannot be determined" if len(seen) == 2 else ("yes" if True in seen else "no")
    if full != ans:
        raise Retry
    if ans != r.choice(YNU) and r.random() < 0.8:
        raise Retry

    def lit(v: str, b: bool) -> str:
        return f"{v} is {'true' if b else 'false'}"

    sents = [f"{lit(v, b)}." for v, b in facts]
    sents += [f"If {' and '.join(lit(v, b) for v, b in ante)}, then {lit(cv, cb)}." for ante, (cv, cb) in rules]
    r.shuffle(sents)
    q = " ".join(sents) + f" Is {q_v} true? Answer yes, no or cannot be determined."
    st = {"vars": vs, "facts": [[v, b] for v, b in facts], "rules": [[[[v, b] for v, b in a], [c[0], c[1]]] for a, c in rules], "query": q_v}
    return Built(q, st, ans, "ynu", 3)


# ---------------------------------------------------------------- knights and knaves


def _kk_holds(kind: str, args: list[int], who: int, kn: tuple[bool, ...]) -> bool:
    """Truth value of a statement under the assignment kn (True = knight)."""
    if kind == "is_knight":
        return kn[args[0]]
    if kind == "is_knave":
        return not kn[args[0]]
    if kind == "both_knights":
        return kn[args[0]] and kn[args[1]]
    if kind == "some_knave":
        return (not kn[args[0]]) or (not kn[args[1]])
    raise ValueError(kind)


@lineage("R1", "truth")
def knights_knaves(level: int, r: random.Random) -> Built:
    n = 2 + (level + 1) // 2
    people = r.sample(NAMES, n)
    for _ in range(300):
        stm: list[tuple[str, list[int]]] = []
        for i in range(n):
            others = [j for j in range(n) if j != i]
            kind = r.choice(("is_knight", "is_knave", "both_knights", "some_knave"))
            # statements about one other person; or about a pair that may include the speaker
            stm.append((kind, r.sample(others, 1) if kind in ("is_knight", "is_knave") else r.sample(range(n), 2)))
        sols = [kn for kn in itertools.product((True, False), repeat=n)
                if all(_kk_holds(s[0], s[1], i, kn) == kn[i] for i, s in enumerate(stm))]
        if len(sols) != 1:
            continue
        who = r.randrange(n)
        text = []
        for i, (kind, a) in enumerate(stm):
            p = people[i]
            if kind == "is_knight":
                body = f"{people[a[0]]} is a knight"
            elif kind == "is_knave":
                body = f"{people[a[0]]} is a knave"
            elif kind == "both_knights":
                body = f"{people[a[0]]} and {people[a[1]]} are both knights"
            else:
                body = f"at least one of {people[a[0]]} and {people[a[1]]} is a knave"
            text.append(f'{p} says: "{body}."')
        q = ("Each person is either a knight, who always tells the truth, or a knave, who always lies. " + " ".join(text)
             + f" Is {people[who]} a knight or a knave? Answer knight or knave.")
        ans = "knight" if sols[0][who] else "knave"
        return Built(q, {"people": people, "statements": [[k, a] for k, a in stm], "who": who}, ans, "word", 2)
    raise Retry


# ---------------------------------------------------------------- arrangement


def _seat_ok(c: list, perm: tuple[int, ...]) -> bool:
    pos = {p: i for i, p in enumerate(perm)}
    t = c[0]
    if t == "adj":
        return pos[c[2]] == pos[c[1]] + 1
    if t == "left":
        return pos[c[1]] < pos[c[2]]
    if t == "end":
        return pos[c[1]] in (0, len(perm) - 1)
    if t == "pos":
        return pos[c[1]] == c[2]
    if t == "between":
        return pos[c[1]] < pos[c[2]] < pos[c[3]] or pos[c[3]] < pos[c[2]] < pos[c[1]]
    if t == "notnext":
        return abs(pos[c[1]] - pos[c[2]]) != 1
    raise ValueError(t)


@lineage("R1", "arrangement")
def seating_row(level: int, r: random.Random) -> Built:
    n = {0: 3, 1: 4, 2: 5, 3: 5, 4: 6, 5: 6, 6: 7}[level]
    people = r.sample(NAMES, n)
    hidden = list(range(n))
    r.shuffle(hidden)  # hidden[i] = index of the person in seat i
    pos = {p: i for i, p in enumerate(hidden)}
    alive = list(itertools.permutations(range(n)))
    clues: list[list] = []
    kinds = ["adj", "left", "end", "pos", "notnext"] + (["between"] if level >= 3 else [])
    for _ in range(40):
        if len(alive) == 1:
            break
        t = r.choice(kinds)
        a, b, c = r.sample(range(n), 3) if n >= 3 else (0, 1, 2)
        cl: list
        if t == "adj":
            j = r.randrange(n - 1)
            a, b = hidden[j], hidden[j + 1]
            cl = ["adj", a, b]
        elif t == "left":
            x, y = sorted(r.sample(range(n), 2), key=lambda p: pos[p])
            cl = ["left", x, y]
        elif t == "end":
            cl = ["end", hidden[r.choice((0, n - 1))]]
        elif t == "pos":
            cl = ["pos", a, pos[a]]
        elif t == "notnext":
            cand = [(x, y) for x in range(n) for y in range(x + 1, n) if abs(pos[x] - pos[y]) != 1]
            if not cand:
                continue
            cl = ["notnext", *r.choice(cand)]
        else:
            tri = sorted([a, b, c], key=lambda p: pos[p])
            cl = ["between", tri[0], tri[1], tri[2]]
            if r.random() < 0.5:
                cl = ["between", tri[2], tri[1], tri[0]]
        new = [p for p in alive if _seat_ok(cl, p)]
        if len(new) < len(alive):
            clues.append(cl)
            alive = new
    if len(alive) != 1:
        raise Retry
    seat = r.randrange(n)

    def txt(c: list) -> str:
        nm = lambda i: people[i]  # noqa: E731
        return {
            "adj": lambda: f"{nm(c[1])} sits immediately to the left of {nm(c[2])}.",
            "left": lambda: f"{nm(c[1])} sits somewhere to the left of {nm(c[2])}.",
            "end": lambda: f"{nm(c[1])} sits at one of the two ends of the row.",
            "pos": lambda: f"{nm(c[1])} sits in seat {c[2] + 1}.",
            "between": lambda: f"{nm(c[2])} sits somewhere between {nm(c[1])} and {nm(c[3])}.",
            "notnext": lambda: f"{nm(c[1])} and {nm(c[2])} do not sit next to each other.",
        }[c[0]]()

    sh = clues[:]
    r.shuffle(sh)
    q = (f"{_and(sorted(people))} sit in a row of {n} seats numbered 1 to {n} from the left, one person per seat. " + " ".join(txt(c) for c in sh)
         + f" Who sits in seat {seat + 1}?")
    return Built(q, {"people": people, "clues": sh, "seat": seat}, people[hidden[seat]], "name", n)


@lineage("R1", "arrangement")
def pet_owners(level: int, r: random.Random) -> Built:
    n = 3 + min(level, 3)
    people = r.sample(NAMES, n)
    pets = r.sample(PETS, n)
    hidden = list(range(n))
    r.shuffle(hidden)  # person i owns pet hidden[i]
    alive = list(itertools.permutations(range(n)))
    clues: list[list] = []
    for _ in range(40):
        if len(alive) == 1:
            break
        i = r.randrange(n)
        t = r.choice(("not", "not", "either", "owns"))
        if t == "not":
            cl = ["not", i, r.choice([p for p in range(n) if p != hidden[i]])]
        elif t == "either":
            cl = ["either", i, hidden[i], r.choice([p for p in range(n) if p != hidden[i]])]
        else:
            cl = ["owns", i, hidden[i]]
        new = [p for p in alive if (p[cl[1]] != cl[2] if cl[0] == "not" else p[cl[1]] in cl[2:] if cl[0] == "either" else p[cl[1]] == cl[2])]
        if len(new) < len(alive):
            clues.append(cl)
            alive = new
    if len(alive) != 1 or any(c[0] == "owns" for c in clues) and sum(c[0] == "owns" for c in clues) > n - 2:
        raise Retry
    ask = r.randrange(n)  # which pet to ask about
    owner = hidden.index(ask)
    out = []
    for c in clues:
        if c[0] == "not":
            out.append(f"{people[c[1]]} does not own the {pets[c[2]]}.")
        elif c[0] == "either":
            a, b = c[2], c[3]
            if r.random() < 0.5:
                a, b = b, a
            out.append(f"{people[c[1]]} owns either the {pets[a]} or the {pets[b]}.")
        else:
            out.append(f"{people[c[1]]} owns the {pets[c[2]]}.")
    r.shuffle(out)
    q = f"{_and(sorted(people))} each own exactly one different pet from this list: {_and(sorted(pets))}. " + " ".join(out) + f" Who owns the {pets[ask]}?"
    return Built(q, {"people": people, "pets": pets, "clues": clues, "ask": ask}, people[owner], "name", n)


# ---------------------------------------------------------------- temporal


@lineage("R1", "temporal")
def event_timeline(level: int, r: random.Random) -> Built:
    n = 3 + level
    ev = r.sample(EVENTS, n)
    days = r.sample(range(1, 400), n)
    nodes = list(range(n))
    r.shuffle(nodes)
    edges = []
    for i in range(1, n):
        a, b = nodes[i], nodes[r.randrange(i)]
        edges.append((a, b))
    r.shuffle(edges)
    sents, rel = [], []
    for a, b in edges:
        d = abs(days[a] - days[b])
        later, earlier = (a, b) if days[a] > days[b] else (b, a)
        rel.append([ev[later], ev[earlier], d])
        if r.random() < 0.5:
            sents.append(f"{ev[later].capitalize()} took place {d} days after {ev[earlier]}.")
        else:
            sents.append(f"{ev[earlier].capitalize()} took place {d} days before {ev[later]}.")
    ask = r.choice(("first", "last"))
    q = " ".join(sents) + f" Which of these events took place {ask}: {_and(sorted(ev))}?"
    order = sorted(range(n), key=lambda i: days[i])
    ans = ev[order[0] if ask == "first" else order[-1]]
    return Built(q, {"events": sorted(ev), "rel": rel, "ask": ask}, ans, "text", n)


# ---------------------------------------------------------------- tracking


@lineage("R1", "tracking")
def swap_tracking(level: int, r: random.Random) -> Built:
    n = 3 + min(level, 3)
    people = r.sample(NAMES, n)
    objs = r.sample(OBJECTS, n)
    hold = dict(zip(people, objs, strict=True))
    ops = []
    steps = 2 + 2 * level
    state = dict(hold)
    for _ in range(steps):
        if n >= 3 and r.random() < 0.3:
            a, b, c = r.sample(people, 3)
            ops.append(["rotate", a, b, c])  # a's item goes to b, b's to c, c's to a
            state[b], state[c], state[a] = state[a], state[b], state[c]
        else:
            a, b = r.sample(people, 2)
            ops.append(["swap", a, b])
            state[a], state[b] = state[b], state[a]
    who = r.choice(people)
    txt = []
    for o in ops:
        if o[0] == "swap":
            txt.append(f"{o[1]} and {o[2]} swap what they are holding.")
        else:
            txt.append(f"{o[1]} hands their item to {o[2]}, {o[2]} hands theirs to {o[3]}, and {o[3]} hands theirs to {o[1]}, all at once.")
    start = ", ".join(f"{p} holds the {o}" for p, o in hold.items())
    q = f"At the start {start}. " + " ".join(txt) + f" What is {who} holding at the end? Choose from {_and(sorted(objs))}."
    return Built(q, {"hold": {p: hold[p] for p in people}, "ops": ops, "who": who}, state[who], "text", n)


# ---------------------------------------------------------------- graph


@lineage("R1", "graph")
def road_reachability(level: int, r: random.Random) -> Built:
    n = min(5 + level, 10)
    towns = r.sample(TOWNS, n)
    x, y = r.sample(range(n), 2)
    want = r.choice(("yes", "no"))
    edges: set[tuple[int, int]] = set()
    if want == "yes":
        mid = r.sample([t for t in range(n) if t not in (x, y)], min(n - 2, 1 + r.randint(0, 2)))
        path = [x, *mid, y]
        edges.update(zip(path, path[1:], strict=False))
        allowed = [(a, b) for a in range(n) for b in range(n) if a != b]
    else:
        reach = {x, *r.sample([t for t in range(n) if t not in (x, y)], r.randint(0, max(0, n // 2 - 1)))}
        allowed = [(a, b) for a in range(n) for b in range(n) if a != b and not (a in reach and b not in reach)]
        if not allowed:
            raise Retry
    extra = r.randint(n - 2, 2 * n)
    for e in r.sample(allowed, min(extra, len(allowed))):
        edges.add(e)
    el = sorted(edges)
    r.shuffle(el)
    q = (" ".join(f"There is a one-way road from {towns[a]} to {towns[b]}." for a, b in el)
         + f" There are no other roads. Can you travel from {towns[x]} to {towns[y]} using these roads? Answer yes or no.")
    return Built(q, {"towns": towns, "roads": [list(e) for e in el], "x": x, "y": y}, want, "yn", 2)


# ---------------------------------------------------------------- culprit


@lineage("R1", "culprit")
def one_culprit(level: int, r: random.Random) -> Built:
    n = 4 + level // 2
    people = r.sample(NAMES, n)
    for _ in range(200):
        culprit = r.randrange(n)
        st: list[list] = []
        for i in range(n):
            t = r.choice(("was", "not", "either"))
            if t == "was":
                st.append(["was", r.randrange(n)])
            elif t == "not":
                st.append(["not", r.randrange(n)])
            else:
                st.append(["either", *r.sample(range(n), 2)])

        def true_count(c: int) -> int:
            return sum(1 for s in st if (s[1] == c if s[0] == "was" else (s[1] != c if s[0] == "not" else c in s[1:])))

        k = true_count(culprit)
        if sum(1 for c in range(n) if true_count(c) == k) != 1:
            continue
        txt = []
        for i, s in enumerate(st):
            body = {"was": f"It was {people[s[1]]}", "not": f"It was not {people[s[1]]}",
                    "either": f"It was {people[s[1]]} or {people[s[2]]}" if s[0] == "either" else ""}[s[0]]
            txt.append(f'{people[i]} says: "{body}."')
        q = (f"One of {_and(sorted(people))} took the last cake. " + " ".join(txt) + f" Exactly {k} of these {n} statements are true. Who took the cake?")
        return Built(q, {"people": people, "statements": st, "true_count": k}, people[culprit], "name", n)
    raise Retry


# ---------------------------------------------------------------- attribute rule


def _rule_eval(rule: list, it: dict[str, str]) -> bool:
    op = rule[0]
    if op == "attr":
        return it[rule[1]] == rule[2]
    if op == "not":
        return not _rule_eval(rule[1], it)
    if op == "and":
        return all(_rule_eval(x, it) for x in rule[1:])
    if op == "or":
        return any(_rule_eval(x, it) for x in rule[1:])
    raise ValueError(op)


def _rule_text(rule: list) -> str:
    op = rule[0]
    if op == "attr":
        return {"colour": f"it is {rule[2]}", "shape": f"it is {rule[2]}", "mark": f"it has {rule[2]}"}[rule[1]]
    if op == "not":
        inner = _rule_text(rule[1])
        return f"it is not true that ({inner})" if rule[1][0] != "attr" else f"it is not true that {inner}"
    return f" {op} ".join("(" + _rule_text(x) + ")" if x[0] in ("and", "or") else _rule_text(x) for x in rule[1:])


@lineage("R1", "rules")
def attribute_rule(level: int, r: random.Random) -> Built:
    n = 4 + min(level, 4)
    vals = {"colour": COLOURS, "shape": SHAPES, "mark": MARKS}

    def leaf() -> list:
        a = r.choice(sorted(vals))
        return ["attr", a, r.choice(vals[a])]

    for _ in range(400):
        depth = 1 + level // 2
        rule: list = [r.choice(("and", "or")), leaf(), leaf()]
        for _ in range(depth - 1):
            rule = [r.choice(("and", "or")), rule, ["not", leaf()] if r.random() < 0.5 else leaf()]
        owners = r.sample(NAMES, n)
        items = [{"colour": r.choice(COLOURS), "shape": r.choice(SHAPES), "mark": r.choice(MARKS)} for _ in range(n)]
        ok = [i for i, it in enumerate(items) if _rule_eval(rule, it)]
        if len(ok) != 1:
            continue
        txt = "; ".join(f"{o}'s badge is {it['colour']}, {it['shape']} and has {it['mark']}" for o, it in zip(owners, items, strict=True))
        q = (f"A gate opens for a badge if the badge satisfies this rule: {_rule_text(rule)}. The badges: {txt}. "
             f"Whose badge opens the gate? Choose from {_and(sorted(owners))}.")
        return Built(q, {"rule": rule, "owners": owners, "items": items}, owners[ok[0]], "name", n)
    raise Retry


# ---------------------------------------------------------------- spatial


@lineage("R1", "spatial")
def compass_turns(level: int, r: random.Random) -> Built:
    dirs = ["north", "east", "south", "west"]
    start = r.randrange(4)
    cmds = [("left", 270), ("right", 90), ("around", 180), ("cw90", 90), ("cw270", 270), ("ccw90", 270), ("cw180", 180)]
    steps = 3 + 2 * level
    seq = []
    for _ in range(steps):
        if r.random() < 0.3:
            seq.append(["walk", r.randint(2, 99)])
        else:
            c = r.choice(cmds)
            seq.append(["turn", c[0]])
    text = {"left": "turn left", "right": "turn right", "around": "turn around", "cw90": "turn 90 degrees clockwise",
            "cw270": "turn 270 degrees clockwise", "ccw90": "turn 90 degrees counterclockwise", "cw180": "turn 180 degrees clockwise"}
    amount = dict(cmds)
    cur = start
    for k, v in seq:
        if k == "turn":
            cur = (cur + amount[v] // 90) % 4
    body = ", then ".join(f"walk {v} steps" if k == "walk" else text[v] for k, v in seq)
    q = f"You are facing {dirs[start]}. You {body}. Which direction are you facing now? Answer north, east, south or west."
    return Built(q, {"start": dirs[start], "seq": seq}, dirs[cur], "word", 4)
