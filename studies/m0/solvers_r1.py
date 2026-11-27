# ruff: noqa: E501
"""Independent second solvers for R1 (ADR-0033 section 6.2).

Each solver reads ONLY the item's structured form (a dict) and returns the answer string, or raises if the item
does not have exactly one answer. This module imports nothing from the generator modules. Where the generator
computes forward from a hidden world, these solvers search the statements for every world that satisfies them.
Written by the implementer, not by a separate auditor context (ADR-0033 section 13): ruling needed 3.
"""

from __future__ import annotations

import itertools
from typing import Any

YNU = ("yes", "no", "cannot be determined")


def _unique(xs: list[str]) -> str:
    if len(set(xs)) != 1:
        raise ValueError(f"not exactly one answer: {sorted(set(xs))}")
    return xs[0]


def order_extreme(s: dict[str, Any]) -> str:
    # tallest = the person nobody is taller than; shortest = the person taller than nobody (count over all statements)
    people = s["people"]
    if s["ask"] == "tallest":
        c = [p for p in people if not any(b == p for _, b in s["taller"])]
    else:
        c = [p for p in people if not any(a == p for a, _ in s["taller"])]
    if len(c) != 1:
        raise ValueError("no unique extreme")
    return c[0]


def _acyclic(edges: list[tuple[str, str]]) -> bool:
    nodes = sorted({v for e in edges for v in e})
    indeg = {v: 0 for v in nodes}
    for _, b in edges:
        indeg[b] += 1
    queue = [v for v in nodes if indeg[v] == 0]
    done = 0
    while queue:
        v = queue.pop()
        done += 1
        for a, b in edges:
            if a == v:
                indeg[b] -= 1
                if indeg[b] == 0:
                    queue.append(b)
    return done == len(nodes)


def order_compare(s: dict[str, Any]) -> str:
    # "x above y" is forced iff adding "y above x" makes the statements contradictory (a cycle), and vice versa
    base = [(a, b) for a, b in s["taller"]]
    x, y = s["x"], s["y"]
    if not _acyclic([*base, (y, x)]):
        return "yes"
    if not _acyclic([*base, (x, y)]):
        return "no"
    return "cannot be determined"


def _ancestor(parent: dict[str, str], who: str, k: int) -> str:
    for _ in range(k):
        who = parent[who]
    return who


def kinship_ancestor(s: dict[str, Any]) -> str:
    return _ancestor(s["parent"], s["child"], s["generations"])


def kinship_cousins(s: dict[str, Any]) -> str:
    par = s["parent"]
    x, y = s["x"], s["y"]
    px, py = par.get(x), par.get(y)
    if px is None or py is None or px == py:
        return "no"
    return "yes" if par.get(px) is not None and par.get(px) == par.get(py) else "no"


def categories_follow(s: dict[str, Any]) -> str:
    # enumerate every possible kind of individual (the set of categories it belongs to) that the statements allow
    n = len(s["cats"])
    types = []
    for bits in range(1 << n):
        mem = [(bits >> i) & 1 for i in range(n)]
        if any(mem[a] and not mem[b] for a, b in s["all"]):
            continue
        if any(mem[a] and mem[b] for a, b in s["none"]):
            continue
        types.append(mem)
    x, y = s["x"], s["y"]
    if s["kind"] == "all":
        return "yes" if all(t[y] for t in types if t[x]) else "cannot be determined"
    both = any(t[x] and t[y] for t in types)
    if s["kind"] == "none":
        return "cannot be determined" if both else "yes"
    return "cannot be determined" if both else "no"


def conditional_chain(s: dict[str, Any]) -> str:
    vs = s["vars"]
    seen = set()
    for vals in itertools.product((False, True), repeat=len(vs)):
        w = dict(zip(vs, vals, strict=True))
        if any(w[v] != b for v, b in s["facts"]):
            continue
        ok = True
        for ante, concl in s["rules"]:
            if all(w[v] == b for v, b in ante) and w[concl[0]] != concl[1]:
                ok = False
                break
        if ok:
            seen.add(w[s["query"]])
    if not seen:
        raise ValueError("inconsistent statements")
    return "cannot be determined" if len(seen) == 2 else ("yes" if True in seen else "no")


def _kk(kind: str, a: list[int], kn: tuple[bool, ...]) -> bool:
    if kind == "is_knight":
        return kn[a[0]]
    if kind == "is_knave":
        return not kn[a[0]]
    if kind == "both_knights":
        return kn[a[0]] and kn[a[1]]
    return not (kn[a[0]] and kn[a[1]])  # some_knave


def knights_knaves(s: dict[str, Any]) -> str:
    n = len(s["people"])
    out = []
    for kn in itertools.product((True, False), repeat=n):
        # a knight's statement is true, a knave's statement is false
        if all((_kk(k, a, kn)) is kn[i] for i, (k, a) in enumerate(s["statements"])):
            out.append("knight" if kn[s["who"]] else "knave")
    return _unique(out)


def _seat(c: list, order: tuple[int, ...]) -> bool:
    where = {p: i for i, p in enumerate(order)}
    t = c[0]
    if t == "adj":
        return where[c[1]] + 1 == where[c[2]]
    if t == "left":
        return where[c[1]] < where[c[2]]
    if t == "end":
        return where[c[1]] in (0, len(order) - 1)
    if t == "pos":
        return where[c[1]] == c[2]
    if t == "between":
        lo, hi = sorted((where[c[1]], where[c[3]]))
        return lo < where[c[2]] < hi
    return abs(where[c[1]] - where[c[2]]) > 1  # notnext


def seating_row(s: dict[str, Any]) -> str:
    n = len(s["people"])
    out = [s["people"][order[s["seat"]]] for order in itertools.permutations(range(n)) if all(_seat(c, order) for c in s["clues"])]
    return _unique(out)


def pet_owners(s: dict[str, Any]) -> str:
    n = len(s["people"])
    out = []
    for own in itertools.permutations(range(n)):  # own[i] = pet index of person i
        ok = True
        for c in s["clues"]:
            if c[0] == "not":
                ok = own[c[1]] != c[2]
            elif c[0] == "either":
                ok = own[c[1]] in (c[2], c[3])
            else:
                ok = own[c[1]] == c[2]
            if not ok:
                break
        if ok:
            out.append(s["people"][own.index(s["ask"])])
    return _unique(out)


def event_timeline(s: dict[str, Any]) -> str:
    # place every event on a day axis by walking the statements outwards from one event
    pos: dict[str, int] = {s["rel"][0][1]: 0}
    todo = [list(r) for r in s["rel"]]
    while todo:
        rest = []
        for later, earlier, d in todo:
            if earlier in pos and later not in pos:
                pos[later] = pos[earlier] + d
            elif later in pos and earlier not in pos:
                pos[earlier] = pos[later] - d
            elif later in pos and earlier in pos:
                if pos[later] - pos[earlier] != d:
                    raise ValueError("inconsistent")
            else:
                rest.append([later, earlier, d])
        if len(rest) == len(todo):
            raise ValueError("disconnected")
        todo = rest
    vals = sorted(pos.values())
    if len(set(vals)) != len(vals) or set(pos) != set(s["events"]):
        raise ValueError("ties or missing events")
    target = vals[0] if s["ask"] == "first" else vals[-1]
    return _unique([e for e in sorted(pos) if pos[e] == target])


def swap_tracking(s: dict[str, Any]) -> str:
    # trace the item held by `who` at the end backwards through the operations
    who = s["who"]
    for op in reversed(s["ops"]):
        if op[0] == "swap":
            if who == op[1]:
                who = op[2]
            elif who == op[2]:
                who = op[1]
        else:  # rotate a b c: a's item went to b, b's to c, c's to a
            a, b, c = op[1:]
            who = {b: a, c: b, a: c}.get(who, who)
    return s["hold"][who]


def road_reachability(s: dict[str, Any]) -> str:
    seen = {s["x"]}
    frontier = [s["x"]]
    while frontier:
        cur = frontier.pop()
        for a, b in s["roads"]:
            if a == cur and b not in seen:
                seen.add(b)
                frontier.append(b)
    return "yes" if s["y"] in seen else "no"


def one_culprit(s: dict[str, Any]) -> str:
    n = len(s["people"])
    out = []
    for c in range(n):
        true = 0
        for st in s["statements"]:
            if st[0] == "was":
                true += st[1] == c
            elif st[0] == "not":
                true += st[1] != c
            else:
                true += c in (st[1], st[2])
        if true == s["true_count"]:
            out.append(s["people"][c])
    return _unique(out)


def _holds(rule: list, it: dict[str, str]) -> bool:
    if rule[0] == "attr":
        return it[rule[1]] == rule[2]
    if rule[0] == "not":
        return not _holds(rule[1], it)
    vals = [_holds(x, it) for x in rule[1:]]
    return all(vals) if rule[0] == "and" else any(vals)


def attribute_rule(s: dict[str, Any]) -> str:
    return _unique([o for o, it in zip(s["owners"], s["items"], strict=True) if _holds(s["rule"], it)])


def compass_turns(s: dict[str, Any]) -> str:
    degrees = {"north": 0, "east": 90, "south": 180, "west": 270}
    delta = {"left": -90, "right": 90, "around": 180, "cw90": 90, "cw270": 270, "ccw90": -90, "cw180": 180}
    a = degrees[s["start"]]
    for kind, v in s["seq"]:
        if kind == "turn":
            a = (a + delta[v]) % 360
    return {v: k for k, v in degrees.items()}[a]


SOLVERS = {
    "R1.order_extreme": order_extreme,
    "R1.order_compare": order_compare,
    "R1.kinship_ancestor": kinship_ancestor,
    "R1.kinship_cousins": kinship_cousins,
    "R1.categories_follow": categories_follow,
    "R1.conditional_chain": conditional_chain,
    "R1.knights_knaves": knights_knaves,
    "R1.seating_row": seating_row,
    "R1.pet_owners": pet_owners,
    "R1.event_timeline": event_timeline,
    "R1.swap_tracking": swap_tracking,
    "R1.road_reachability": road_reachability,
    "R1.one_culprit": one_culprit,
    "R1.attribute_rule": attribute_rule,
    "R1.compass_turns": compass_turns,
}
