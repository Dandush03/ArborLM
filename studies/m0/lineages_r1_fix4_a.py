# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 4: seven shapes whose levels were not distinct (audit 4, section 4 'Levels'; lead rulings R-21, R-25 (c)). Ids end in ``_r6``.

Each builder below is the earlier builder (named in its docstring) with ONE change: a level parameter that takes a different value at EVERY level 0 to 6 and grows with the level. The solution
procedure, the answer rule, the statement forms and the conventions stated in the item are unchanged. The stated parameter of each shape:

event_timeline_r6                  spine length L = 4 + level (earlier: 4 + level // 2, so levels 0-1, 2-3, 4-5 shared a generator)
temporal_weekday_shift_r6          spine length L = 5 + level (earlier: 5 + level // 3)
spatial_relative_directions_r6     spine length L = 5 + level (earlier: 5 + level // 3)
equivalence_exchange_rates_r6      spine length L = 3 + level (earlier: 3 + level // 2)
knights_knaves_r6                  number of people n = 4 + level (earlier: 4 + level // 2)
graph_shortest_route_r6            planted route of h = (3, 3, 4, 4, 5, 5, 6)[level] roads as before, and the number of decoy towns 2 + level (earlier: 2 + level // 2)
conditional_decision_tree_r6       number of lights stated = depth + 2 + level (earlier: depth + 2), depth and the number of actions as before

Nothing else is changed. In particular no rejection is added or removed (the retries of the earlier builders are kept; retry rates per level are in ``manifests/r1_fix4_levels.json``).
The knights_knaves docstring of the earlier shape said the statement kind is 'independent of the speaker's type by construction'; the redraw until the solution is unique (a validity condition) makes
that only approximately true (audit 4: the asked person's own statement kind reads +0.11 to +0.14); this docstring says so.
"""

from __future__ import annotations

import itertools
import random
from math import gcd

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pl
from studies.m0.lineages_r1_fix3_b import _OPP, _STEP, DAYS, _smooth, _spine
from studies.m0.lineages_r1_fix3_c import _kk_true
from studies.m0.lineages_r1_fix4_common import fix4
from studies.m0.vocab import EVENTS, NAMES, OBJECTS, PSEUDO, TOWNS


@fix4("temporal", "R1.event_timeline_r5")
def event_timeline_r6(level: int, r: random.Random) -> Built:
    """As event_timeline_r5 (lineages_r1_fix3_b) with the spine length L = 4 + level (4 to 10 statements between X and Y; 2 + level // 3 further events hang from random events).
    structured: {"events", "rel": [[later, earlier, days]], "x", "y"}; the question asks how many days apart X and Y took place (an open number >= 1; a zero sum is a Retry, as before)."""
    L = 4 + level
    ex = 2 + level // 3
    n = L + 1 + ex
    ev = r.sample(EVENTS, n)
    spine, edges = _spine(r, L + 1, ex)
    rel: list[list] = []
    date = {0: 0}
    for a, b in edges:
        g = r.randint(1, 60)
        sign = 1 if r.random() < 0.5 else -1  # b is `sign * g` days after a
        date[b] = date[a] + sign * g
        later, earlier = (b, a) if sign > 0 else (a, b)
        rel.append([ev[later], ev[earlier], g])
    xi, yi = spine[0], spine[-1]
    ans = abs(date[yi] - date[xi])
    if ans == 0:
        raise Retry
    r.shuffle(rel)
    sents = [f"{a.capitalize()} took place {pl(g, 'day')} after {b}." if r.random() < 0.5 else f"{b.capitalize()} took place {pl(g, 'day')} before {a}." for a, b, g in rel]
    q = " ".join(sents) + f" How many days apart did {ev[xi]} and {ev[yi]} take place?"
    return Built(q, {"events": sorted(ev), "rel": rel, "x": ev[xi], "y": ev[yi]}, str(ans), "number", None)


@fix4("temporal", "R1.temporal_weekday_shift_r5")
def temporal_weekday_shift_r6(level: int, r: random.Random) -> Built:
    """As temporal_weekday_shift_r5 (lineages_r1_fix3_b) with the spine length L = 5 + level (5 to 11 links from the anchor to the asked event; 2 + level // 3 further events hang from random events).
    structured: {"days", "anchor": [event, weekday], "links": [[later, earlier, n]], "ask"}."""
    L = 5 + level
    ex = 2 + level // 3
    n = L + 1 + ex
    ev = r.sample(EVENTS, n)
    _, edges = _spine(r, L + 1, ex)
    wd = {0: r.randrange(7)}
    links: list[list] = []
    for a, b in edges:
        k = r.randint(1, 300)
        sign = 1 if r.random() < 0.5 else -1
        wd[b] = (wd[a] + sign * k) % 7
        links.append([ev[b], ev[a], k] if sign > 0 else [ev[a], ev[b], k])
    r.shuffle(links)
    sents = [f"{a.capitalize()} took place {pl(k, 'day')} after {b}." if r.random() < 0.5 else f"{b.capitalize()} took place {pl(k, 'day')} before {a}." for a, b, k in links]
    ask = ev[L]
    q = f"{ev[0].capitalize()} took place on a {DAYS[wd[0]]}. " + " ".join(sents) + f" On which day of the week did {ask} take place?"
    return Built(q, {"days": list(DAYS), "anchor": [ev[0], DAYS[wd[0]]], "links": links, "ask": ask}, DAYS[wd[L]], "word", 7)


@fix4("spatial", "R1.spatial_relative_directions_r5")
def spatial_relative_directions_r6(level: int, r: random.Random) -> Built:
    """As spatial_relative_directions_r5 (lineages_r1_fix3_b) with the spine length L = 5 + level (5 to 11 facts between X and Y; 2 + level // 3 further places hang from random places).
    structured: {"places", "facts": [[a, direction, k, b]], "x", "y"}; the answer is the street distance |dx| + |dy| (an open number >= 1, else Retry)."""
    L = 5 + level
    ex = 2 + level // 3
    n = L + 1 + ex
    places = r.sample(TOWNS, n)
    _, edges = _spine(r, L + 1, ex)
    xy = {0: (0, 0)}
    facts: list[list] = []
    for a, b in edges:
        d = r.choice(list(_STEP))
        k = r.randint(1, 9)
        xy[b] = (xy[a][0] + _STEP[d][0] * k, xy[a][1] + _STEP[d][1] * k)
        facts.append([places[b], d, k, places[a]] if r.random() < 0.5 else [places[a], _OPP[d], k, places[b]])
    ans = abs(xy[L][0] - xy[0][0]) + abs(xy[L][1] - xy[0][1])
    if ans == 0:
        raise Retry
    r.shuffle(facts)
    q = " ".join(f"{p} is {pl(k, 'block')} {d} of {o}." for p, d, k, o in facts) + f" How far apart are {places[0]} and {places[L]} by street distance (blocks north or south plus blocks east or west)?"
    return Built(q, {"places": places, "facts": facts, "x": places[0], "y": places[L]}, str(ans), "number", None)


@fix4("equivalence", "R1.equivalence_exchange_rates_r5")
def equivalence_exchange_rates_r6(level: int, r: random.Random) -> Built:
    """As equivalence_exchange_rates_r5 (lineages_r1_fix3_b) with the spine length L = 3 + level (3 to 9 rates between X and Y; 2 + level // 3 further items hang from random items).
    structured: {"items", "rates": [[p, a, q, b]] (p units of a are worth q units of b), "x", "y", "n"}; N is chosen so that the answer is a whole number."""
    L = 3 + level
    ex = 2 + level // 3
    n = L + 1 + ex
    items = r.sample(OBJECTS, n)
    smooth = [v for v in range(2, 400) if _smooth(v)]
    val = r.sample(smooth, n)
    _, edges = _spine(r, L + 1, ex)
    rates = []
    for a, b in edges:
        g = gcd(val[a], val[b])
        t = r.randint(1, 2)
        rates.append([t * val[b] // g, items[a], t * val[a] // g, items[b]])  # p units of a are worth q units of b: p v_a = q v_b
    g = gcd(val[0], val[L])
    nn = (val[L] // g) * r.randint(1, 4)
    ans = nn * val[0] // val[L]
    r.shuffle(rates)
    q = " ".join(f"{p} units of {a} are worth the same as {qq} units of {b}." for p, a, qq, b in rates) + f" How many units of {items[L]} are worth the same as {nn} units of {items[0]}?"
    return Built(q, {"items": items, "rates": rates, "x": items[0], "y": items[L], "n": nn}, str(ans), "number", None)


@fix4("truth", "R1.knights_knaves_r5")
def knights_knaves_r6(level: int, r: random.Random) -> Built:
    """As knights_knaves_r5 (lineages_r1_fix3_c) with n = 4 + level people (4 to 10). structured: {"people", "statements": [[kind, [args]]], "who"}. A hidden assignment is drawn first (a fair coin each);
    each person's statement is drawn uniformly among the statements that are true under it if the speaker is a knight and false if a knave; a statement set with more than one solution is redrawn
    (validity: a unique answer; this redraw makes the statement kind only approximately independent of the speaker's type). The asked person is uniform. Up to 400 redraws, then Retry (as before)."""
    n = 4 + level
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


@fix4("graph", "R1.graph_shortest_route_r4")
def graph_shortest_route_r6(level: int, r: random.Random) -> Built:
    """As graph_shortest_route_r4 (lineages_r1_rev4_b) with 2 + level decoy towns (earlier 2 + level // 2): the planted route has h = (3, 3, 4, 4, 5, 5, 6)[level] roads (as before), so the number of
    towns n = h + 1 + 2 + level differs at every level. structured: {"towns", "roads": [[a, b, length]] (two-way), "start", "end", "planted_roads": h}. Potentials make every other route strictly longer than the
    planted one."""
    h = (3, 3, 4, 4, 5, 5, 6)[level]
    n = h + 1 + 2 + level
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


@fix4("conditional", "R1.conditional_decision_tree_r4")
def conditional_decision_tree_r6(level: int, r: random.Random) -> Built:
    """As conditional_decision_tree_r4 (lineages_r1_rev4_b) with depth + 2 + level lights stated (earlier depth + 2): the tree (depth = 3, 3, 4, 4, 4, 5, 5 by level; four actions, eight at level 6; the
    leaf actions a shuffled list with equal counts) is as before, drawing its tests from the larger set of lights, and the facts state every light. structured: {"tree", "facts", "actions"}."""
    from studies.m0.lineages_r1_conditional import ACTIONS

    depth = (3, 3, 4, 4, 4, 5, 5)[level]
    attrs = [f"the {w} light is on" for w in r.sample(PSEUDO, depth + 2 + level)]
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
