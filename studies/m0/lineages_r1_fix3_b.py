# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 fix round 3, part b: potential propagation over a tree (event timeline, weekday shift, relative directions, exchange rates) and kinship.

All four tree shapes ask about a pair at the two ends of a planted spine of L statements (L >= 4), so that the signed sum along the spine is not the unsigned sum, the largest stated gap or the last stated number with any
reliability: a spine of L statements with independent signs is monotone with probability 2^(1 - L) at most 1/8. Other people (places, events, items) hang from random nodes as leaves. Ids end in ``_r5``.
"""

from __future__ import annotations

import random
from math import gcd

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import pl
from studies.m0.lineages_r1_fix3_common import fix3
from studies.m0.vocab import EVENTS, OBJECTS, TOWNS

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_STEP = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
_OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _spine(r: random.Random, n_spine: int, extras: int) -> tuple[list[int], list[tuple[int, int]]]:
    """Node ids 0 .. n_spine + extras - 1 (shuffled labels are the caller's business); the spine is 0..n_spine-1 in order; each extra node hangs from a random earlier node.
    Returns (spine, edges as (existing, new))."""
    spine = list(range(n_spine))
    edges = [(i, i + 1) for i in range(n_spine - 1)]
    for e in range(n_spine, n_spine + extras):
        edges.append((r.randrange(e), e))
    return spine, edges


@fix3("temporal", "R1.event_timeline")
def event_timeline_r5(level: int, r: random.Random) -> Built:
    """structured: {"events", "rel": [[later, earlier, days]], "x", "y"}. Question: how many days apart did X and Y take place (an open number >= 1). The facts are "A took place d days after B" / "B took place d days
    before A", d uniform in 1 .. 60. The spine between X and Y has L = 4 + level // 2 statements and the sign of every one is random; 2 + level // 3 further events hang from random events. (The earlier shape asked which event came first or
    last; the event at the far end of the largest stated gap was right 40 to 48 % of the time.) The days are consecutive numbers, X and Y are on different days (the sum is not zero; otherwise Retry)."""
    L = 4 + level // 2
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


@fix3("temporal", "R1.temporal_weekday_shift")
def temporal_weekday_shift_r5(level: int, r: random.Random) -> Built:
    """structured: {"days", "anchor": [event, weekday], "links": [[later, earlier, n]], "ask"} as temporal_weekday_shift. The asked event lies at the end of a spine of L = 5 + level // 3 links from the anchor, each link
    with a random direction and n uniform in 1 .. 300 (days); 2 + level // 3 further events hang from random events. So "ignore before and after" is right only when the spine is monotone (about 1/16) or by chance (1/7)."""
    L = 5 + level // 3
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


@fix3("spatial", "R1.spatial_relative_directions_r4")
def spatial_relative_directions_r5(level: int, r: random.Random) -> Built:
    """structured: {"places", "facts": [[a, direction, k, b]], "x", "y"} as spatial_relative_directions_r4. X and Y are the ends of a spine of L = 5 + level // 3 facts (each a random direction and k uniform in 1 .. 9);
    2 + level // 3 further places hang from random places. Answer: the street distance |dx| + |dy| (an open number, >= 1, else Retry). Summing the legs ignoring direction is right only when no two legs cancel
    (about 6 % of the items at L = 6; the earlier shape: 40 to 65 % at the shorter paths)."""
    L = 5 + level // 3
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


def _smooth(v: int) -> bool:
    for p in (2, 3, 5):
        while v % p == 0:
            v //= p
    return v == 1


@fix3("equivalence", "R1.equivalence_exchange_rates")
def equivalence_exchange_rates_r5(level: int, r: random.Random) -> Built:
    """structured: {"items", "rates": [[p, a, q, b]] (p units of a are worth q units of b), "x", "y", "n"}. Question: how many units of Y are worth the same as N units of X (an open whole number). Values are drawn
    from the numbers 2 .. 399 whose only prime factors are 2, 3 and 5 (distinct), the rates are the reduced ratios of neighbours (times 1 or 2), and X and Y are the ends of a spine of L = 3 + level // 2 rates;
    N is a multiple of v_Y / gcd(v_X, v_Y) chosen so that the answer is a whole number. 2 + level // 3 further items hang from random items. (The earlier shape asked which item is worth the most per unit; the local
    maximum rule was right 20 to 49 % of the time.)"""
    L = 3 + level // 2
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
