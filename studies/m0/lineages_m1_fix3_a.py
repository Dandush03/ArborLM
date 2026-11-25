# ruff: noqa: E501
"""M1 fix round 3, part A: revisions of the sixteen existing ``core.REGISTRY`` lineages (``lineages_m1.py``, immutable). Each states its answer format and conventions inside the item,
never raises ``Retry``, and has its parameter space widened (capacity, R-10/R-11) without changing the number of steps of the level. See ``NOTES_FIX3_M1.md`` for what changed per lineage."""

from __future__ import annotations

import math
import random
from fractions import Fraction

from studies.m0.core import Built
from studies.m0.lineages_m1_fix3_common import (
    DECIMAL,
    WHOLE,
    WHOLE_SIGNED,
    adding,
    fmt_exact,
    money,
    pl,
    r3,
    until,
)
from studies.m0.vocab import NAMES, OBJECTS

# ------------------------------------------------------------------ S2 weighted sum


@r3("shopping", "shopping")
def shopping_r3(level: int, r: random.Random) -> Built:
    """structured {"items": [[count, price_cents]], "paid": cents}. Unchanged computation (change = paid - total); states the answer format (dollars, up to two decimals)."""
    name = r.choice(NAMES)
    kinds = r.sample(OBJECTS, 2 + level // 2 + (level > 0))
    items = [[r.randint(1, 6 + level), r.randint(5, 99 + 100 * (level // 2)) * (1 if level < 3 else 5)] for _ in kinds]
    total = sum(c * p for c, p in items)
    paid = (total // 500 + 1) * 500 + r.choice((0, 500, 1000, 2000))
    parts = ", ".join(f"{pl(c, k)} at {money(p)} each" for (c, p), k in zip(items, kinds, strict=True))
    q = f"{name} buys {parts}. {name} pays with {money(paid)}. How many dollars of change does {name} get back? {DECIMAL}"
    return Built(q, {"items": items, "paid": paid}, fmt_exact(Fraction(paid - total, 100)), "number", None)


@r3("speed_distance", "rates")
def speed_distance_r3(level: int, r: random.Random) -> Built:
    """structured {"legs": [[hours, speed]], "average": bool}. The leg durations are DISTINCT by construction (sampled without replacement), so 'sum of speeds x mean hours' is not
    right when the hours are equal (audit: +0.21 at L0-L1). The average ask (levels >= 2) is built so that the total distance is a multiple of the total hours (the average is a whole number):
    the last speed is drawn from the values that make it so (batch 1 did this with a Retry). Distance in kilometres, speeds in kilometres per hour, durations in whole hours."""
    n = 2 + level // 2
    hours = r.sample(range(1, 6 + level + n), n)
    avg = level >= 2 and r.random() < 0.4
    smax = 60 + 10 * level

    def draw() -> list[list[int]] | None:
        speeds = [r.randint(20, smax) for _ in range(n - 1)]
        if avg:
            tot = sum(hours)
            part = sum(h * s for h, s in zip(hours[:-1], speeds, strict=True))
            ok = [s for s in range(20, smax + 1) if (part + hours[-1] * s) % tot == 0]
            if not ok:
                return None
            speeds.append(r.choice(ok))
        else:
            speeds.append(r.randint(20, smax))
        return [[h, s] for h, s in zip(hours, speeds, strict=True)]

    legs = until(draw)
    dist = sum(h * s for h, s in legs)
    txt = ", then ".join(f"drives for {pl(h, 'hour')} at {s} kilometres per hour" for h, s in legs)
    if avg:
        q = f"A van {txt}. What is its average speed over the whole trip (the total distance divided by the total time), in kilometres per hour? {WHOLE}"
        ans = str(dist // sum(h for h, _ in legs))
    else:
        q = f"A van {txt}. How many kilometres does it travel in total? {WHOLE}"
        ans = str(dist)
    return Built(q, {"legs": legs, "average": avg}, ans, "number", None)


@r3("mixture", "ratio")
def mixture_r3(level: int, r: random.Random) -> Built:
    """structured {"x", "y", "a", "b", "packing"}. Batch 1 retried until the cost was a whole number of cents, which favoured x = y (the unweighted mean of the two prices was right on 0.24-0.28).
    Here the total weight s = x + y is drawn from the divisors of 100 that give no equal split by default (5, 10, 20, 25, 50, 100), x uniformly in 1..s-1, and the two prices are DIFFERENT, so every
    mean is a whole number of cents by construction and no retry exists. Levels >= 3 add a flat packing cost of p dollars (1..9) per kilogram."""
    s = r.choice((5, 10, 20, 25, 50, 100))
    x = r.randint(1, s - 1)
    y = s - x
    a = r.randint(2, 30)
    b = r.choice([v for v in range(2, 31) if v != a])
    p = r.randint(1, 9) if level >= 3 else 0
    v = Fraction(x * a + y * b, s) + p
    pack = f", then adds a flat packing cost of {p} {'dollar' if p == 1 else 'dollars'} per kilogram of the finished mixture" if p else ""
    q = (f"A shop mixes {x} kilograms of nuts costing {a} dollars per kilogram with {y} kilograms of raisins costing {b} dollars per kilogram{pack}. "
         f"What is the cost of one kilogram of the finished mixture, in dollars? {DECIMAL}")
    return Built(q, {"x": x, "y": y, "a": a, "b": b, "packing": p}, fmt_exact(v), "number", None)


# ------------------------------------------------------------------ S3 multiplicative chain


@r3("percent_change", "percent")
def percent_change_r3(level: int, r: random.Random) -> Built:
    """structured {"price": P, "steps": [["up" | "down", percent]]}. Two steps (up then down) below level 3, three (up, down, up) from level 3. Percents are multiples of 5 (up 5..80, down 5..75, third up 5..60).
    The price is a multiple of 4 (two steps) or of 80 (three steps), which makes the final price a whole number of cents by construction (batch 1 retried); the step count per level is unchanged."""
    ups = list(range(5, 81, 5))
    downs = list(range(5, 76, 5))
    steps: list[list[object]] = [["up", r.choice(ups)], ["down", r.choice(downs)]]
    if level >= 3:
        steps.append(["up", r.choice(range(5, 61, 5))])
        price = 80 * r.randint(1, 6 + level)
    else:
        price = 4 * r.randint(3, 60 + 10 * level)
    v = Fraction(price)
    for k, p in steps:
        v = v * (100 + int(p) if k == "up" else 100 - int(p)) / 100  # type: ignore[call-overload]
    txt = ", then ".join(f"{'rises' if k == 'up' else 'falls'} by {p} percent" for k, p in steps)
    q = f"A jacket costs {price} dollars. Its price {txt}, each change applied to the price just before it. What is the final price in dollars? {DECIMAL}"
    return Built(q, {"price": price, "steps": steps}, fmt_exact(v), "number", None)


@r3("tip_split", "percent")
def tip_split_r3(level: int, r: random.Random) -> Built:
    """structured {"bill": B, "tip": percent, "people": n}. Tip is any whole percent 5..30, people 2..6+level, bill 20..400+100*level dollars chosen as a multiple of n / gcd(n, 100 + tip), so each
    person's share is a whole number of cents by construction (batch 1 retried). The tip is on the bill before tip, the total is split equally."""
    n = r.randint(2, 6 + level)
    tip = r.randint(5, 30)
    step = n // math.gcd(n, 100 + tip)
    lo, hi = -(-20 // step), (400 + 100 * level) // step
    bill = step * r.randint(lo, hi)
    v = Fraction(bill * (100 + tip), 100 * n)
    q = (f"A dinner bill is {bill} dollars before tip. The group adds a {tip} percent tip, calculated on the bill before tip, and splits the total (bill plus tip) equally between {n} people. "
         f"How many dollars does each person pay? {DECIMAL}")
    return Built(q, {"bill": bill, "tip": tip, "people": n}, fmt_exact(v), "number", None)


@r3("fraction_remainder", "remainder")
def fraction_remainder_r3(level: int, r: random.Random) -> Built:
    """structured {"start": n, "a": a, "b": b}. a, b in 2..12 (one a-th, then one b-th of what is left). n is a multiple of a * b / gcd(b, a - 1), the least start for which both spends are whole
    numbers of dollars, up to 3000 + 500 * level (a bound on size, not a retry)."""
    names = {2: "half", 3: "third", 4: "quarter", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}
    a, b = r.randint(2, 12), r.randint(2, 12)
    step = a * (b // math.gcd(b, a - 1))
    n = step * r.randint(1, (3000 + 500 * level) // step)
    rest = n - n // a
    assert rest % b == 0
    left = rest - rest // b
    name = r.choice(NAMES)
    q = (f"{name} has {n} dollars. {name} spends one {names[a]} of it on books, then one {names[b]} of what is left on lunch. How many dollars does {name} have left? {WHOLE}")
    return Built(q, {"start": n, "a": a, "b": b}, str(left), "number", None)


@r3("ratio_share", "ratio")
def ratio_share_r3(level: int, r: random.Random) -> Built:
    """structured {"parts": [..], "total": n, "who": index}. Parts are 1..16 (two parts, three from level 2, four from level 4); total = k * sum(parts), k in 2..60+20*level; every share is a whole number of stickers."""
    parts = [r.randint(1, 16) for _ in range(2 + (level >= 2) + (level >= 4))]
    k = r.randint(2, 60 + 20 * level)
    n = k * sum(parts)
    names = r.sample(NAMES, len(parts))
    who = r.randrange(len(parts))
    ratio = ":".join(str(p) for p in parts)
    q = (f"{', '.join(names[:-1])} and {names[-1]} share {n} stickers in the ratio {ratio} (in that order: the first named person gets the first number of parts, and so on; every part has the same number of stickers, "
         f"and the shares are whole numbers of stickers). How many stickers does {names[who]} get? {WHOLE}")
    return Built(q, {"parts": parts, "total": n, "who": who}, str(k * parts[who]), "number", None)


# ------------------------------------------------------------------ S1 linear solve


@r3("linear_equation", "linear")
def linear_equation_r3(level: int, r: random.Random) -> Built:
    """structured {"k", "m", "j", "n"}: k*x + m = n (j = 0) or k*x + m = j*x + n (j != 0). The constants are never 0 (batch 1 could print 'adding 0'); the answer may be negative and the item says how to write it."""
    x = r.randint(-20 - 10 * level, 40 + 20 * level)
    k = r.randint(2, 9)
    if level >= 3:
        j = r.choice([v for v in range(1, 9) if v != k])
        e = r.choice([v for v in range(-40, 61) if v != 0])
        m = e + (j - k) * x
        while m == 0:  # validity only: the printed constant must not be 0 ('adding 0'); x is redrawn, the equation is built from it
            x = r.randint(-20 - 10 * level, 40 + 20 * level)
            m = e + (j - k) * x
        q = (f"I think of a number. Multiplying it by {k} and then {adding(m)} gives the same result as multiplying it by {j} and then {adding(e)}. What is my number? {WHOLE_SIGNED}")
        return Built(q, {"k": k, "m": m, "j": j, "n": e}, str(x), "number", None)
    m = r.choice([v for v in range(-30, 61) if v != 0])
    q = f"I think of a number. Multiplying it by {k} and then {adding(m)} gives {k * x + m}. What is my number? {WHOLE_SIGNED}"
    return Built(q, {"k": k, "m": m, "j": 0, "n": k * x + m}, str(x), "number", None)


@r3("ages", "age")
def ages_r3(level: int, r: random.Random) -> Built:
    """structured {"k", "t", "sum", "ask": "younger" | "older"}. n1 is k times as old as n2 now; in t years their ages add up to `sum`. The ask (drawn first) is the younger person's age now or the older person's age now.
    Ranges widened: younger age 3..70+10*level, k 2..6+level//2, t 1..15+level. Ages are whole numbers of years."""
    ask = r.choice(("younger", "older"))
    b = r.randint(3, 70 + 10 * level)
    k = r.randint(2, 6 + level // 2)
    t = r.randint(1, 15 + level)
    n1, n2 = r.sample(NAMES, 2)
    total = (k * b + t) + (b + t)
    who, val = (n2, b) if ask == "younger" else (n1, k * b)
    q = (f"{n1} is {k} times as old as {n2} now. In {pl(t, 'year')} from now, their two ages added together will be {total}. All ages are whole numbers of years. How old is {who} now, in years? {WHOLE}")
    return Built(q, {"k": k, "t": t, "sum": total, "ask": ask}, str(val), "number", None)


@r3("consecutive", "linear")
def consecutive_r3(level: int, r: random.Random) -> Built:
    """structured {"count": n, "step": 1 | 2, "sum": S, "ask": "largest" | "smallest"}. n = 3 + level // 2 numbers in a row (step 2 allowed from level 2); first number -200..4000+2000*level (may be negative)."""
    n = 3 + level // 2
    step = r.choice((1, 2)) if level >= 2 else 1
    ask = r.choice(("largest", "smallest"))
    a = r.randint(-200, 4000 + 2000 * level)
    nums = [a + step * i for i in range(n)]
    kind = {1: "consecutive integers", 2: "consecutive numbers that each differ from the next by 2"}[step]
    q = f"The sum of {n} {kind} (listed from smallest to largest, positive or negative whole numbers) is {sum(nums)}. What is the {ask} of them? {WHOLE_SIGNED}"
    return Built(q, {"count": n, "step": step, "sum": sum(nums), "ask": ask}, str(nums[-1] if ask == "largest" else nums[0]), "number", None)


@r3("average_missing", "average")
def average_missing_r3(level: int, r: random.Random) -> Built:
    """structured {"scores": [..], "mean_cents": c, "n": n}. n = 4 + level // 2 tests, scores 40..100. The missing score is drawn from the values that make the mean a number with at most two decimals
    (batch 1 retried), so no draw is rejected."""
    n = 4 + level // 2
    scores = [r.randint(40, 100) for _ in range(n - 1)]
    ok = [v for v in range(40, 101) if Fraction(sum(scores) + v, n).denominator in (1, 2, 4, 5, 10, 20, 25, 50, 100)]
    last = r.choice(ok)
    mean = Fraction(sum(scores) + last, n)
    name = r.choice(NAMES)
    q = (f"{name} has scored {', '.join(str(s) for s in scores)} on {n - 1} tests, each marked out of 100 with whole-number marks. What score is needed on the next test to make the mean of all {n} tests exactly "
         f"{fmt_exact(mean)}? {WHOLE}")
    return Built(q, {"scores": scores, "mean_cents": int(mean * 100), "n": n}, str(last), "number", None)


@r3("pipes_work", "rates")
def pipes_work_r3(level: int, r: random.Random) -> Built:
    """structured {"a", "b", "drain", "volume"}. Two filling pipes (litres per minute 2..24+2*level), a drain from level 3 (1..a+b-1 litres per minute), minutes 3..40+5*level; the tank starts empty and all run together."""
    a, b = r.randint(2, 24 + 2 * level), r.randint(2, 24 + 2 * level)
    drain = r.randint(1, a + b - 1) if level >= 3 else 0
    t = r.randint(3, 40 + 5 * level)
    vol = (a + b - drain) * t
    q = (f"A tank is empty. One pipe adds {a} litres of water every minute and a second pipe adds {b} litres every minute"
         + (f", while a drain removes {drain} litres every minute" if drain else "")
         + f", all at the same time and at a steady rate. How many minutes does it take for the tank to hold {vol} litres? {WHOLE}")
    return Built(q, {"a": a, "b": b, "drain": drain, "volume": vol}, str(t), "number", None)


@r3("rectangle", "geometry")
def rectangle_r3(level: int, r: random.Random) -> Built:
    """structured {"shape": "ratio" | "excess", "perimeter": P, "ratio": k, "excess": d}. Shape (drawn first; 'ratio' with probability 0.3, 'excess' with 0.7, because the ratio shape has a space of only 649 items at level 0): the length is k times the width (k 2..12), or the length is d centimetres more than the width (d 1..60).
    Width 2..60+10*level; the perimeter is built from the whole width, so it is always consistent. Answer: the area in square centimetres (whole by construction)."""
    shape = "ratio" if r.random() < 0.3 else "excess"
    w = r.randint(2, 60 + 10 * level)
    if shape == "ratio":
        k = r.randint(2, 12)
        ln, per = k * w, 2 * (w + k * w)
        q = f"A rectangle has a perimeter of {per} centimetres and its length is {k} times its width. What is its area in square centimetres? {WHOLE}"
        st = {"shape": shape, "perimeter": per, "ratio": k, "excess": 0}
    else:
        d = r.randint(1, 60)
        ln, per = w + d, 2 * (2 * w + d)
        q = f"A rectangle has a perimeter of {per} centimetres and its length is {d} centimetres more than its width. What is its area in square centimetres? {WHOLE}"
        st = {"shape": shape, "perimeter": per, "ratio": 0, "excess": d}
    return Built(q, st, str(w * ln), "number", None)


@r3("coins", "coins")
def coins_r3(level: int, r: random.Random) -> Built:
    """structured {"lo", "hi", "count", "cents", "ask": "lo" | "hi"}. The coin pair is drawn from pairs with hi / lo <= 10 (1,2,5,10,20,25,50,100,200 cents). Counts: the number of LOW coins is at least
    ceil(hi / lo) (so the low coins are worth at least one high coin), 2..30+4*level otherwise; this is a range of the draw, not a retry, and it makes 'total value / high coin' wrong by construction
    (audit: +0.12 to +0.17). Answer: the count of the asked coin."""
    vals = (1, 2, 5, 10, 20, 25, 50, 100, 200)
    pairs = [(lo, hi) for lo in vals for hi in vals if hi > lo and hi <= 10 * lo]
    lo, hi = r.choice(pairs)
    cmax = 30 + 4 * level
    nl = r.randint(max(2, -(-hi // lo)), cmax)
    nh = r.randint(2, cmax)
    total = nl * lo + nh * hi
    ask = r.choice(("lo", "hi"))
    q = (f"A jar holds only {lo}-cent coins and {hi}-cent coins. It holds {nl + nh} coins worth {total} cents in all. "
         f"How many {lo if ask == 'lo' else hi}-cent coins are in the jar? {WHOLE}")
    return Built(q, {"lo": lo, "hi": hi, "count": nl + nh, "cents": total, "ask": ask}, str(nl if ask == "lo" else nh), "number", None)


@r3("arithmetic_series", "series")
def arithmetic_series_r3(level: int, r: random.Random) -> Built:
    """structured {"first": a, "step": d, "days": n}. a 1..99, d 1..30, n 4..12+3*level days; day 1 is the first day and the total counts days 1..n inclusive."""
    a, d, n = r.randint(1, 99), r.randint(1, 30), r.randint(4, 12 + 3 * level)
    name = r.choice(NAMES)
    total = n * (2 * a + (n - 1) * d) // 2
    q = (f"{name} saves {a} dollars on day 1 and then saves {d} dollars more each day than on the day before. How many dollars has {name} saved in total after {n} days "
         f"(counting day 1 to day {n}, both included)? {WHOLE}")
    return Built(q, {"first": a, "step": d, "days": n}, str(total), "number", None)


@r3("clock_duration", "time")
def clock_duration_r3(level: int, r: random.Random) -> Built:
    """structured {"legs": [[departure_minutes, arrival_minutes]]}. 2 + level // 2 legs on one day. Waits 5..60 minutes and rides 20..150 minutes are drawn first; the first departure is then drawn from
    05:00..min(14:00, the latest start that still ends before midnight), which is never empty for five legs (worst case 1050 minutes), so nothing is redrawn (batch 1 retried)."""
    n = 2 + level // 2
    waits = [r.randint(5, 60) for _ in range(n)]
    rides = [r.randint(20, 150) for _ in range(n)]
    span = sum(waits) + sum(rides)
    t = r.randint(5 * 60, min(14 * 60, 24 * 60 - 1 - span))
    legs: list[list[int]] = []
    for w, d in zip(waits, rides, strict=True):
        dep = t + w
        arr = dep + d
        legs.append([dep, arr])
        t = arr

    def hhmm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    txt = "; ".join(f"leg {i + 1} leaves at {hhmm(a)} and arrives at {hhmm(b)}" for i, (a, b) in enumerate(legs))
    q = (f"A journey has several legs on the same day (times on a 24-hour clock): {txt}. How many minutes in total is the traveller actually on the move (the time between each leg's departure and "
         f"its arrival, not counting the waiting between legs)? {WHOLE}")
    return Built(q, {"legs": legs}, str(sum(b - a for a, b in legs)), "number", None)
