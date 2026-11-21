# ruff: noqa: E501
"""M1, mathematics: multi-step arithmetic and simple algebra word problems from own templates (ADR-0033 section 6.2).

Not the public templated sets. Every answer is an integer or a decimal with at most two places, formatted without
trailing zeros. Money is held in whole cents inside the structured form so the second solvers use integers.
"""

from __future__ import annotations

import random
from fractions import Fraction

from studies.m0.core import Built, Retry, lineage
from studies.m0.vocab import NAMES, OBJECTS


def fmt(v: Fraction) -> str:
    """Canonical decimal text of an exact value with at most two decimal places; Retry otherwise."""
    c = v * 100
    if c.denominator != 1:
        raise Retry
    n = c.numerator
    sign = "-" if n < 0 else ""
    n = abs(n)
    whole, cents = divmod(n, 100)
    if cents == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{cents:02d}".rstrip("0")


def money(cents: int) -> str:
    return f"${cents // 100}.{cents % 100:02d}"


@lineage("M1", "shopping")
def shopping(level: int, r: random.Random) -> Built:
    name = r.choice(NAMES)
    kinds = r.sample(OBJECTS, 2 + level // 2 + (level > 0))
    items = [[r.randint(1, 6 + level), r.randint(5, 99 + 100 * (level // 2)) * (1 if level < 3 else 5)] for _ in kinds]
    total = sum(c * p for c, p in items)
    paid = (total // 500 + 1) * 500 + r.choice((0, 500, 1000, 2000))
    parts = ", ".join(f"{c} {k}s at {money(p)} each" for (c, p), k in zip(items, kinds, strict=True))
    q = f"{name} buys {parts}. {name} pays with {money(paid)}. How many dollars of change does {name} get back?"
    return Built(q, {"items": items, "paid": paid}, fmt(Fraction(paid - total, 100)), "number", None)


@lineage("M1", "rates")
def speed_distance(level: int, r: random.Random) -> Built:
    legs = [[r.randint(1, 5 + level), r.randint(20, 60 + 10 * level)] for _ in range(2 + level // 2)]
    dist = sum(h * s for h, s in legs)
    hours = sum(h for h, _ in legs)
    avg = r.random() < 0.4 and level >= 2
    txt = ", then ".join(f"drives for {h} hours at {s} kilometres per hour" for h, s in legs)
    if avg:
        q = f"A van {txt}. What is its average speed over the whole trip, in kilometres per hour?"
        ans = fmt(Fraction(dist, hours))
    else:
        q = f"A van {txt}. How many kilometres does it travel in total?"
        ans = str(dist)
    return Built(q, {"legs": legs, "average": avg}, ans, "number", None)


@lineage("M1", "rates")
def pipes_work(level: int, r: random.Random) -> Built:
    a, b = r.randint(2, 9 + level), r.randint(2, 9 + level)
    drain = r.randint(1, a + b - 1) if level >= 3 else 0
    t = r.randint(3, 20 + 5 * level)
    vol = (a + b - drain) * t
    q = (f"A tank is empty. One pipe adds {a} litres of water every minute and a second pipe adds {b} litres every minute"
         + (f", while a drain removes {drain} litres every minute" if drain else "")
         + f". How many minutes does it take for the tank to hold {vol} litres?")
    return Built(q, {"a": a, "b": b, "drain": drain, "volume": vol}, str(t), "number", None)


@lineage("M1", "percent")
def percent_change(level: int, r: random.Random) -> Built:
    price = r.randint(2, 40 + 10 * level) * 10
    up = r.choice((5, 10, 15, 20, 25, 30, 40, 50))
    down = r.choice((5, 10, 20, 25, 50))
    steps = [["up", up], ["down", down]]
    if level >= 3:
        steps.append(["up", r.choice((10, 20, 50))])
    v = Fraction(price)
    for k, p in steps:
        v = v * (100 + p if k == "up" else 100 - p) / 100
    txt = ", then ".join(f"{'rises' if k == 'up' else 'falls'} by {p} percent" for k, p in steps)
    q = f"A jacket costs {price} dollars. Its price {txt}, each change applied to the price just before it. What is the final price in dollars?"
    return Built(q, {"price": price, "steps": steps}, fmt(v), "number", None)


@lineage("M1", "percent")
def tip_split(level: int, r: random.Random) -> Built:
    n = r.randint(2, 4 + level)
    bill = r.randint(20, 90 + 20 * level) * 5
    tip = r.choice((10, 15, 20, 25))
    v = Fraction(bill) * (100 + tip) / 100 / n
    q = f"A dinner bill is {bill} dollars before tip. The group adds a {tip} percent tip on the bill and splits the total equally between {n} people. How many dollars does each person pay?"
    return Built(q, {"bill": bill, "tip": tip, "people": n}, fmt(v), "number", None)


@lineage("M1", "ratio")
def ratio_share(level: int, r: random.Random) -> Built:
    parts = [r.randint(1, 5 + level) for _ in range(2 + (level >= 2) + (level >= 4))]
    k = r.randint(2, 30 + 10 * level)
    n = k * sum(parts)
    names = r.sample(NAMES, len(parts))
    who = r.randrange(len(parts))
    ratio = ":".join(str(p) for p in parts)
    q = f"{', '.join(names[:-1])} and {names[-1]} share {n} stickers in the ratio {ratio} (in that order). How many stickers does {names[who]} get?"
    return Built(q, {"parts": parts, "total": n, "who": who}, str(k * parts[who]), "number", None)


@lineage("M1", "ratio")
def mixture(level: int, r: random.Random) -> Built:
    x, y = r.randint(1, 9 + level), r.randint(1, 9 + level)
    a, b = r.randint(2, 30), r.randint(2, 30)
    v = Fraction(x * a + y * b, x + y)
    if level >= 3:
        q = f"A shop mixes {x} kilograms of nuts costing {a} dollars per kilogram with {y} kilograms of raisins costing {b} dollars per kilogram, then adds a flat packing cost of 2 dollars per kilogram of mixture. What is the cost of one kilogram of the finished mixture, in dollars?"
        v += 2
    else:
        q = f"A shop mixes {x} kilograms of nuts costing {a} dollars per kilogram with {y} kilograms of raisins costing {b} dollars per kilogram. What is the cost of one kilogram of the mixture, in dollars?"
    return Built(q, {"x": x, "y": y, "a": a, "b": b, "packing": 2 if level >= 3 else 0}, fmt(v), "number", None)


def _adding(m: int) -> str:
    return f"adding {m}" if m >= 0 else f"subtracting {-m}"


@lineage("M1", "linear")
def linear_equation(level: int, r: random.Random) -> Built:
    x = r.randint(-20 - 10 * level, 40 + 20 * level)
    k = r.randint(2, 9)
    if level >= 3:
        j = r.choice([v for v in range(1, 9) if v != k])
        e = r.randint(-40, 60)
        m = e + (j - k) * x  # k*x + m == j*x + e
        q = (f"I think of a number. Multiplying it by {k} and then {_adding(m)} gives the same result as multiplying it by {j} and then {_adding(e)}. "
             "What is my number?")
        return Built(q, {"k": k, "m": m, "j": j, "n": e}, str(x), "number", None)
    m = r.randint(-30, 60)
    q = f"I think of a number. Multiplying it by {k} and then {_adding(m)} gives {k * x + m}. What is my number?"
    return Built(q, {"k": k, "m": m, "j": 0, "n": k * x + m}, str(x), "number", None)


@lineage("M1", "linear")
def consecutive(level: int, r: random.Random) -> Built:
    n = 3 + level // 2
    step = r.choice((1, 2)) if level >= 2 else 1
    a = r.randint(-20, 200 + 100 * level)
    nums = [a + step * i for i in range(n)]
    kind = {1: "consecutive integers", 2: "consecutive numbers that differ by 2"}[step]
    q = f"The sum of {n} {kind} is {sum(nums)}. What is the largest of them?"
    return Built(q, {"count": n, "step": step, "sum": sum(nums)}, str(nums[-1]), "number", None)


@lineage("M1", "age")
def ages(level: int, r: random.Random) -> Built:
    b = r.randint(3, 30 + 5 * level)
    k = r.randint(2, 4 + level // 2)
    t = r.randint(1, 10 + level)
    n1, n2 = r.sample(NAMES, 2)
    total = (k * b + t) + (b + t)
    q = f"{n1} is {k} times as old as {n2}. In {t} years, their ages will add up to {total}. How old is {n2} now?"
    return Built(q, {"k": k, "t": t, "sum": total}, str(b), "number", None)


@lineage("M1", "average")
def average_missing(level: int, r: random.Random) -> Built:
    n = 4 + level // 2
    scores = [r.randint(40, 100) for _ in range(n - 1)]
    last = r.randint(40, 100)
    mean = Fraction(sum(scores) + last, n)
    if mean.denominator not in (1, 2, 4, 5, 10, 20, 25, 50, 100):
        raise Retry
    name = r.choice(NAMES)
    q = f"{name} has scored {', '.join(str(s) for s in scores)} on {n - 1} tests. What score is needed on the next test to make the mean of all {n} tests exactly {fmt(mean)}?"
    return Built(q, {"scores": scores, "mean_cents": int(mean * 100), "n": n}, str(last), "number", None)


@lineage("M1", "geometry")
def rectangle(level: int, r: random.Random) -> Built:
    w = r.randint(2, 20 + 5 * level)
    k = r.randint(2, 4 + level // 2)
    per = 2 * (w + k * w)
    q = f"A rectangle has a perimeter of {per} centimetres and its length is {k} times its width. What is its area in square centimetres?"
    return Built(q, {"perimeter": per, "ratio": k}, str(w * k * w), "number", None)


@lineage("M1", "series")
def arithmetic_series(level: int, r: random.Random) -> Built:
    a, d, n = r.randint(1, 20), r.randint(1, 9), r.randint(4, 10 + 3 * level)
    name = r.choice(NAMES)
    total = n * (2 * a + (n - 1) * d) // 2
    q = f"{name} saves {a} dollars on day 1 and then saves {d} dollars more each day than on the day before. How many dollars has {name} saved in total after {n} days?"
    return Built(q, {"first": a, "step": d, "days": n}, str(total), "number", None)


@lineage("M1", "coins")
def coins(level: int, r: random.Random) -> Built:
    lo, hi = r.sample((1, 5, 10, 25, 50), 2)
    if lo > hi:
        lo, hi = hi, lo
    nl, nh = r.randint(2, 15 + 3 * level), r.randint(2, 15 + 3 * level)
    total = nl * lo + nh * hi
    ask = r.choice(("lo", "hi"))
    q = (f"A jar holds only {lo}-cent coins and {hi}-cent coins. It holds {nl + nh} coins worth {total} cents in all. "
         f"How many {lo if ask == 'lo' else hi}-cent coins are in the jar?")
    return Built(q, {"lo": lo, "hi": hi, "count": nl + nh, "cents": total, "ask": ask}, str(nl if ask == "lo" else nh), "number", None)


@lineage("M1", "time")
def clock_duration(level: int, r: random.Random) -> Built:
    legs = []
    t = r.randint(5 * 60, 14 * 60)
    for _ in range(2 + level // 2):
        dep = t + r.randint(5, 90)
        arr = dep + r.randint(20, 200)
        legs.append([dep, arr])
        t = arr
    if t >= 24 * 60:
        raise Retry

    def hhmm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    txt = "; ".join(f"leg {i + 1} leaves at {hhmm(a)} and arrives at {hhmm(b)}" for i, (a, b) in enumerate(legs))
    q = f"A journey has several legs on the same day: {txt}. How many minutes in total is the traveller actually on the move (not waiting between legs)?"
    return Built(q, {"legs": legs}, str(sum(b - a for a, b in legs)), "number", None)


@lineage("M1", "remainder")
def fraction_remainder(level: int, r: random.Random) -> Built:
    a, b = r.randint(2, 6), r.randint(2, 6)
    n = a * b * r.randint(1, 20 + 5 * level)
    spent1 = n // a
    rest = n - spent1
    if rest % b:
        raise Retry
    spent2 = rest // b
    left = rest - spent2
    name = r.choice(NAMES)
    q = (f"{name} has {n} dollars. {name} spends one {['', '', 'half', 'third', 'quarter', 'fifth', 'sixth'][a]} of it on books, then one {['', '', 'half', 'third', 'quarter', 'fifth', 'sixth'][b]} "
         f"of what is left on lunch. How many dollars does {name} have left?")
    return Built(q, {"start": n, "a": a, "b": b}, str(left), "number", None)
