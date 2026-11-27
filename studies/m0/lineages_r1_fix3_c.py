# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 3, part c: kinship, knights and knaves, and the permutation puzzles. Ids end in ``_r5``.

kinship_cousins_r5        one family tree of four generations; the pair type is drawn first (cousins, siblings, or another relation with different parents and no common grandparent), each with probability 1/3
kinship_descendants_r5    each candidate's height (3 to 5 generations below them) is drawn independently of the number of descendants (8 or more); extra descendants never go to the candidate's children
knights_knaves_r5         statements are drawn from the truthful or the lying kind according to the hidden type of the speaker; six statement kinds; 4 + level // 2 people
pet_owners_r5             the asked pet appears in no 'owns' and no 'either' clue (the earlier shape stated its owner in 23 to 46 % of the items); 5 to 7 people
seating_row_r5            the asked seat appears in no 'pos' clue (the earlier shape stated it in 16 to 24 %); 5 to 7 seats
"""

from __future__ import annotations

import itertools
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_
from studies.m0.lineages_r1_fix3_common import fix3
from studies.m0.vocab import NAMES, PETS

# ---------------------------------------------------------------- kinship


@fix3("kinship", "R1.kinship_cousins")
def kinship_cousins_r5(level: int, r: random.Random) -> Built:
    """structured: {"parent": {child: parent}, "x", "y"} as kinship_cousins. One family: a root with 4 + level // 3 children, the first with 2 to 4 children and the others with 1 to 4, each of those with 0 to 3 children (up to four generations).
    "Two people are cousins if their parents are different people who have the same parent." The pair type is drawn first, uniformly: cousins (answer yes); siblings (same parent; they share a grandparent, so "share a grandparent" is
    wrong); another relation in which the parents differ and no grandparent is shared (second cousins, a person and their cousin's child, or an uncle and a nephew). So "same family" is always yes and the two clauses of the
    definition each leave a third of the items on the wrong side (+0.17 at best for any one clause alone; the earlier shape's same-family rule scored +0.41 to +0.45)."""
    c1 = 4 + level // 3
    names = r.sample(NAMES, 1 + c1 * 20)
    it = iter(names)
    root = next(it)
    parent: dict[str, str] = {}
    gen: dict[str, int] = {root: 0}
    for i1 in range(c1):
        a = next(it)
        parent[a], gen[a] = root, 1
        for _ in range(r.randint(2 if i1 == 0 else 1, 4)):  # the first child has at least two children, so siblings with a common grandparent always exist
            b = next(it)
            parent[b], gen[b] = a, 2
            for _ in range(r.randint(0, 3)):
                c = next(it)
                parent[c], gen[c] = b, 3
    ppl = sorted(gen)

    def gp(p: str) -> str | None:
        return parent.get(parent.get(p, ""), None)

    pairs: dict[str, list[tuple[str, str]]] = {"cousin": [], "sibling": [], "other": []}
    for i, a in enumerate(ppl):
        for b in ppl[i + 1 :]:
            if a == root or b == root:
                continue
            if parent[a] != parent[b] and gp(a) is not None and gp(a) == gp(b):
                pairs["cousin"].append((a, b))
            elif parent[a] == parent[b] and gp(a) is not None:  # siblings who share a grandparent (the children of the root do not)
                pairs["sibling"].append((a, b))
            elif parent[a] != parent[b] and (gp(a) is None or gp(a) != gp(b)):
                pairs["other"].append((a, b))
    kind = r.choice(("cousin", "sibling", "other"))
    x, y = r.choice(pairs[kind])
    if r.random() < 0.5:
        x, y = y, x
    facts = [f"{parent[c]} is the parent of {c}." for c in sorted(parent)]
    r.shuffle(facts)
    q = (" ".join(facts) + " Nobody else has a recorded parent. Two people are cousins if their parents are different people who have the same parent. " + f"Are {x} and {y} cousins? Answer yes or no.")
    return Built(q, {"parent": {c: parent[c] for c in sorted(parent)}, "x": x, "y": y}, "yes" if kind == "cousin" else "no", "yn", 2)


@fix3("kinship", "R1.kinship_descendants_r4")
def kinship_descendants_r5(level: int, r: random.Random) -> Built:
    """structured: {"people", "parent", "ask": "descendants", "candidates", "root"} as kinship_descendants_r4. Each candidate's number of descendants S_i is drawn (distinct, at least 8); the candidate has 1 to 3 children and 1 to 3
    grandchildren (independent of S_i); the height H_i (generations below the candidate, 3 to 5) is drawn independently of S_i, a line of H_i - 2 people hangs below one grandchild and the remaining
    S_i - children - grandchildren - (H_i - 2) descendants hang from random people at depth 2 or more but less than H_i (never from the candidate's children). So the number of children, grandchildren, the depth of the
    line below and the number of times a candidate is named are all independent of S_i (the earlier shape: the candidate with the deepest line scored +0.42 to +0.67)."""
    c = 3 + level // 2
    scores = r.sample(range(8, 13 + c), c)
    people = r.sample(NAMES, 1 + c + sum(scores) + 1 + 1 + 2 + 3 + 3)
    it = iter(people)
    x = next(it)
    parent: dict[str, str] = {}
    cands = [next(it) for _ in range(c)]
    for cand in cands:
        parent[cand] = x
    for cand, s in zip(cands, scores, strict=True):
        ch, gc = r.randint(1, 3), r.randint(1, 3)
        h = r.randint(3, 5)
        kids = [next(it) for _ in range(ch)]
        for kd in kids:
            parent[kd] = cand
        grand = [next(it) for _ in range(gc)]
        for g in grand:
            parent[g] = r.choice(kids)
        slots = list(grand)  # people who can still take a child, depth 2 .. h - 1 (a grandchild has depth 2)
        depth = {g: 2 for g in grand}
        tail = r.choice(grand)
        for _ in range(h - 2):  # the line that fixes the height
            nd = next(it)
            parent[nd], depth[nd] = tail, depth[tail] + 1
            tail = nd
            if depth[nd] < h:
                slots.append(nd)
        for _ in range(s - ch - gc - (h - 2)):
            host = r.choice([p for p in slots if depth[p] < h])
            nd = next(it)
            parent[nd], depth[nd] = host, depth[host] + 1
            if depth[nd] < h:
                slots.append(nd)
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
    q = f"{' '.join(facts)} Nobody else has a recorded parent. Among the children of {x}, who has the most descendants (children, their children, and so on, all the way down)? Choose from {and_(sorted(cands))}."
    used = [p for p in people if p in parent or p in parent.values()]
    return Built(q, {"people": used, "parent": {ch: parent[ch] for ch in sorted(parent)}, "ask": "descendants", "candidates": sorted(cands), "root": x}, best, "name", c)


# ---------------------------------------------------------------- knights and knaves


def _kk_true(kind: str, a: list[int], kn: tuple[bool, ...]) -> bool:
    if kind == "is_knight":
        return kn[a[0]]
    if kind == "is_knave":
        return not kn[a[0]]
    if kind == "both_knights":
        return kn[a[0]] and kn[a[1]]
    if kind == "some_knave":
        return (not kn[a[0]]) or (not kn[a[1]])
    if kind == "same_kind":
        return kn[a[0]] == kn[a[1]]
    if kind == "differ":
        return kn[a[0]] != kn[a[1]]
    raise ValueError(kind)


@fix3("truth", "R1.knights_knaves")
def knights_knaves_r5(level: int, r: random.Random) -> Built:
    """structured: {"people", "statements": [[kind, [args]]], "who"} as knights_knaves, with two more kinds ("same_kind", "differ"). 4 + level // 2 people. A hidden assignment of knights and knaves is drawn first (a fair
    coin each); each person's statement is then drawn uniformly among the statements (kind, arguments) that are TRUE under the hidden assignment if the speaker is a knight and FALSE if a knave, so the kind of statement
    is independent of the speaker's type by construction. Statement sets with more than one solution are redrawn (validity: a unique answer). The asked person is uniform. (The earlier shape: 'a speaker who accuses someone is a knight' scored +0.20 to +0.33.)"""
    n = 4 + level // 2
    people = r.sample(NAMES, n)
    kinds = ("is_knight", "is_knave", "both_knights", "some_knave", "same_kind", "differ")
    allsol = list(itertools.product((True, False), repeat=n))
    for _ in range(400):
        hidden = tuple(r.random() < 0.5 for _ in range(n))
        stm: list[tuple[str, list[int]]] = []
        for i in range(n):
            while True:
                kind = r.choice(kinds)
                if kind in ("is_knight", "is_knave"):
                    a = r.sample([j for j in range(n) if j != i], 1)
                else:
                    a = r.sample(range(n), 2)
                if _kk_true(kind, a, hidden) == hidden[i]:
                    break
            stm.append((kind, a))
        sols = [kn for kn in allsol if all(_kk_true(k, a, kn) == kn[i] for i, (k, a) in enumerate(stm))]
        if len(sols) == 1:
            break
    else:
        raise Retry
    who = r.randrange(n)
    text = []
    for i, (kind, a) in enumerate(stm):
        p = people[i]
        body = {
            "is_knight": lambda a=a: f"{people[a[0]]} is a knight",
            "is_knave": lambda a=a: f"{people[a[0]]} is a knave",
            "both_knights": lambda a=a: f"{people[a[0]]} and {people[a[1]]} are both knights",
            "some_knave": lambda a=a: f"at least one of {people[a[0]]} and {people[a[1]]} is a knave",
            "same_kind": lambda a=a: f"{people[a[0]]} and {people[a[1]]} are of the same kind",
            "differ": lambda a=a: f"exactly one of {people[a[0]]} and {people[a[1]]} is a knight",
        }[kind]()
        text.append(f'{p} says: "{body}."')
    q = ("Each person is either a knight, who always tells the truth, or a knave, who always lies. " + " ".join(text) + f" Is {people[who]} a knight or a knave? Answer knight or knave.")
    return Built(q, {"people": people, "statements": [[k, a] for k, a in stm], "who": who}, "knight" if sols[0][who] else "knave", "word", 2)


# ---------------------------------------------------------------- permutation puzzles


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


@fix3("arrangement", "R1.seating_row")
def seating_row_r5(level: int, r: random.Random) -> Built:
    """structured: {"people", "clues", "seat"} as seating_row. n = 6, 7, 7, 7, 7, 7, 7 seats (the earlier level 0 had three seats: at most a few hundred structures). The asked seat is drawn first and no clue names a person
    in that seat ('pos' clues are drawn only for the other seats), so the answer is never stated; clues of all six kinds (including 'between', which the earlier shape used only from level 3) are added at random until the
    answer is unique. With 'between' from level 0 the structure count at level 0 reaches 60,000 by the collision estimate at 20,000 draws (without it, 20,000))."""
    n = (6, 7, 7, 7, 7, 7, 7)[level]
    people = r.sample(NAMES, n)
    hidden = list(range(n))
    r.shuffle(hidden)
    pos = {p: i for i, p in enumerate(hidden)}
    seat = r.randrange(n)
    alive = list(itertools.permutations(range(n)))
    clues: list[list] = []
    kinds = ["adj", "left", "end", "pos", "notnext", "between"]
    for _ in range(40):
        if len({p[seat] for p in alive}) == 1:
            break
        t = r.choice(kinds)
        a, b, c = r.sample(range(n), 3)
        if t == "adj":
            j = r.randrange(n - 1)
            cl = ["adj", hidden[j], hidden[j + 1]]
        elif t == "left":
            x, y = sorted(r.sample(range(n), 2), key=lambda p: pos[p])
            cl = ["left", x, y]
        elif t == "end":
            cl = ["end", hidden[r.choice((0, n - 1))]]
        elif t == "pos":
            if pos[a] == seat:
                continue
            cl = ["pos", a, pos[a]]
        elif t == "notnext":
            cand = [(x, y) for x in range(n) for y in range(x + 1, n) if abs(pos[x] - pos[y]) != 1]
            cl = ["notnext", *r.choice(cand)]
        else:
            tri = sorted([a, b, c], key=lambda p: pos[p])
            cl = ["between", tri[0], tri[1], tri[2]] if r.random() < 0.5 else ["between", tri[2], tri[1], tri[0]]
        new = [p for p in alive if _seat_ok(cl, p)]
        if len(new) < len(alive):
            clues.append(cl)
            alive = new
    if len({p[seat] for p in alive}) != 1:
        raise Retry

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
    q = f"{and_(sorted(people))} sit in a row of {n} seats numbered 1 to {n} from the left, one person per seat. " + " ".join(txt(c) for c in sh) + f" Who sits in seat {seat + 1}?"
    return Built(q, {"people": people, "clues": sh, "seat": seat}, people[hidden[seat]], "name", n)


@fix3("arrangement", "R1.pet_owners")
def pet_owners_r5(level: int, r: random.Random) -> Built:
    """structured: {"people", "pets", "clues", "ask"} as pet_owners. n = 5, 5, 6, 6, 7, 7, 7 people. The asked pet is drawn first; no 'owns' clue and no 'either' clue (neither as the true pet nor as the decoy) names it,
    so the asked pet appears only in 'not' clues (at most n // 2 - 1 of them) and its owner is never stated; clues are added at random until the owner is unique."""
    n = (5, 5, 6, 6, 7, 7, 7)[level]
    people = r.sample(NAMES, n)
    pets = r.sample(PETS, n)
    hidden = list(range(n))
    r.shuffle(hidden)  # person i owns pet hidden[i]
    ask = r.randrange(n)
    alive = list(itertools.permutations(range(n)))
    clues: list[list] = []
    for _ in range(60):
        if len({p.index(ask) for p in alive}) == 1:
            break
        i = r.randrange(n)
        t = r.choice(("not", "not", "either", "owns"))
        if t == "not":
            pet = r.choice([p for p in range(n) if p != hidden[i]])
            if pet == ask and sum(1 for c in clues if c[0] == "not" and c[2] == ask) >= n // 2 - 1:
                continue  # at most n // 2 - 1 people are said not to own the asked pet, so the others cannot all be struck off by that alone
            cl = ["not", i, pet]
        elif t == "either":
            if hidden[i] == ask:
                continue
            cl = ["either", i, hidden[i], r.choice([p for p in range(n) if p not in (hidden[i], ask)])]
        else:
            if hidden[i] == ask:
                continue
            cl = ["owns", i, hidden[i]]
        new = [p for p in alive if (p[cl[1]] != cl[2] if cl[0] == "not" else p[cl[1]] in cl[2:] if cl[0] == "either" else p[cl[1]] == cl[2])]
        if len(new) < len(alive):
            clues.append(cl)
            alive = new
    if len({p.index(ask) for p in alive}) != 1:
        raise Retry
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
    q = f"{and_(sorted(people))} each own exactly one different pet from this list: {and_(sorted(pets))}. " + " ".join(out) + f" Who owns the {pets[ask]}?"
    return Built(q, {"people": people, "pets": pets, "clues": clues, "ask": ask}, people[owner], "name", n)
