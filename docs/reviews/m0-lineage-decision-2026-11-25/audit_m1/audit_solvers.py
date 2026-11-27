# ruff: noqa
"""Auditor's independent solvers for the 21 M1 batch-1 lineages.

Each solver reads ONLY the rendered question text (never `structured`, never the key) and recomputes the answer by a method chosen
to differ from the generator's where practical (brute force, closed forms, interpolation). Nothing from studies.m0 is imported here.

solve(lineage_id, question) -> dict with
  "answer": canonical answer text under the reading the item states;
  "alt": optional {reading_name: answer} for readings the auditor considers plausible alternatives (ambiguity probes).
"""
from __future__ import annotations

import itertools
import math
import re
import statistics
from collections import Counter
from fractions import Fraction


def canon(v) -> str:
    v = Fraction(v)
    c = v * 100
    if c.denominator != 1:
        raise ValueError(f"not representable with 2 decimals: {v}")
    n = int(c)
    s = "-" if n < 0 else ""
    n = abs(n)
    w, cents = divmod(n, 100)
    if cents == 0:
        return f"{s}{w}"
    return (f"{s}{w}." + f"{cents:02d}").rstrip("0")


INT = r"(-?\d+)"
WORDNUM = {"one": 1, "two": 2, "three": 3}


def ints(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


# ---------------------------------------------------------------- counting
def s_inclusion_exclusion(q):
    total = int(re.search(r"^(?:.*?\. )?(\d+) people were asked", q).group(1))
    m2 = re.search(r"(\d+) of them ([a-z ]+?), (\d+) of them ([a-z ]+?), and (\d+) of them do both", q)
    if m2:
        A, B, AB = int(m2.group(1)), int(m2.group(3)), int(m2.group(5))
        anyone = A + B - AB
        reg = {"none": total - anyone, "at least one": anyone, "exactly one": A + B - 2 * AB, "exactly two": AB}
    else:
        m3 = re.search(r"(\d+) [a-z ]+?, (\d+) [a-z ]+? and (\d+) [a-z ]+?; (\d+) do both the first and the second, (\d+) do both the first and the third, (\d+) do both the second and the third, and (\d+) do all three", q)
        A, B, C, AB, AC, BC, T = (int(x) for x in m3.groups())
        anyone = A + B + C - AB - AC - BC + T
        reg = {"none": total - anyone, "at least one": anyone, "exactly one": A + B + C - 2 * (AB + AC + BC) + 3 * T, "exactly two": AB + AC + BC - 3 * T}
    ask = re.search(r"How many of the \d+ people do (none|at least one|exactly one|exactly two) of these things", q).group(1)
    return {"answer": canon(reg[ask])}


def s_binomial_choose(q):
    m = re.search(r"A club has (\d+) members, and (\w+) is one of them\. A committee of (\d+) members .*must be on it", q)
    if m:
        n, k = int(m.group(1)), int(m.group(3))
        # forced member: committees containing a given person = C(n,k) * k / n
        v = Fraction(math.comb(n, k) * k, n)
        return {"answer": canon(v), "alt": {"ignore_forced": canon(math.comb(n, k))}}
    m = re.search(r"A club has (\d+) members\. A committee of (\d+) members is chosen", q)
    if m:
        n, k = int(m.group(1)), int(m.group(2))
        # multiplicative formula, computed independently
        v = Fraction(1)
        for i in range(k):
            v = v * (n - i) / (i + 1)
        return {"answer": canon(v)}
    m = re.search(r"A group has (\d+) women and (\d+) men\. A team of (\d+) people is chosen .* with exactly (\d+) women", q)
    x, y, k, j = (int(g) for g in m.groups())
    return {"answer": canon(math.comb(x, j) * math.comb(y, k - j)), "alt": {"at_least_j": canon(sum(math.comb(x, t) * math.comb(y, k - t) for t in range(j, min(x, k) + 1)))}}


def s_slot_permutations(q):
    m = re.search(r"How many (\d+)-digit numbers can be written using only the digits ([\d, and]+), if (.*)\?", q)
    s = int(m.group(1))
    digits = sorted(int(d) for d in re.findall(r"\d", m.group(2)))
    rules = m.group(3)
    rep = "may be used more than once" in rules and "no digit may" not in rules
    lead_rule = "may not start with the digit 0" in rules
    par = "even" if "must be even" in rules else "odd" if "must be odd" in rules else "any"

    def count(no_leading_zero):
        # positional product rule over the last slot class (independent of the generator's enumeration)
        tot = 0
        for tup in (itertools.product(digits, repeat=s) if rep else itertools.permutations(digits, s)):
            if no_leading_zero and tup[0] == 0:
                continue
            if par == "even" and tup[-1] % 2:
                continue
            if par == "odd" and not tup[-1] % 2:
                continue
            tot += 1
        return tot

    stated = count(lead_rule)
    conventional = count(True)  # an s-digit number never starts with 0
    alt = {}
    if conventional != stated:
        alt["conventional_no_leading_zero"] = canon(conventional)
    return {"answer": canon(stated), "alt": alt}


def s_change_ways(q):
    m = re.search(r"coins worth ([\d, and]+) cents, .* exactly (\d+) cents be paid", q)
    coins = [int(c) for c in re.findall(r"\d+", m.group(1))]
    t = int(m.group(2))
    a, b, c = coins
    n = 0
    for x in range(t // a + 1):
        for y in range((t - a * x) // b + 1):
            if (t - a * x - b * y) % c == 0:
                n += 1
    return {"answer": canon(n)}


def s_pigeonhole(q):
    inv = re.search(r"colours: (.*?)\. Marbles", q).group(1)
    counts = [int(x) for x in re.findall(r"(\d+) [a-z]+", inv)]
    m = re.search(r"at least (\d+) marbles of the same colour", q)
    # adversary simulation: draw while the goal is not yet forced
    if m:
        k = int(m.group(1))
        drawn = [0] * len(counts)
        steps = 0
        while True:
            # adversary picks a colour that keeps every colour below k, if one is available
            opts = [i for i in range(len(counts)) if drawn[i] < counts[i] and drawn[i] + 1 < k]
            if not opts:
                break
            drawn[opts[0]] += 1
            steps += 1
        return {"answer": canon(steps + 1)}
    assert "at least one marble of every colour" in q
    drawn = [0] * len(counts)
    steps = 0
    # adversary avoids the colour with the fewest marbles as long as possible
    order = sorted(range(len(counts)), key=lambda i: counts[i])
    avoid = order[0]
    for i in range(len(counts)):
        if i != avoid:
            steps += counts[i]
    return {"answer": canon(steps + 1)}


# ---------------------------------------------------------------- number theory
def s_gcd_lcm(q):
    m = re.search(r"has \d+ ribbons of lengths ([\d, and]+) centimetres", q)
    if m:
        vals = [int(v) for v in re.findall(r"\d+", m.group(1))]
        g = max(d for d in range(1, min(vals) + 1) if all(v % d == 0 for v in vals))
        return {"answer": canon(g)}
    vals = [int(v) for v in re.findall(r"every (\d+) seconds", q)]
    t = max(vals)
    while any(t % v for v in vals):
        t += max(vals)
    return {"answer": canon(t)}


def s_crt(q):
    conds = [(int(a), int(b)) for a, b in re.findall(r"ividing it by (\d+) leaves remainder (\d+)", q)]
    n = 1
    while not all(n % m == r for m, r in conds):
        n += 1
        if n > 10**7:
            raise RuntimeError("no solution")
    return {"answer": canon(n)}


def s_prime_factors(q):
    n = int(re.search(r"Consider the number (\d+)\.", q).group(1))
    fac = []
    x, p = n, 2
    while x > 1:
        while x % p == 0:
            fac.append(p)
            x //= p
        p += 1
    if "How many different positive whole numbers divide it" in q:
        a = sum((1 if d * d == n else 2) for d in range(1, math.isqrt(n) + 1) if n % d == 0)
    elif "largest prime number that divides" in q:
        a = max(fac)
    elif "Add up the different prime numbers" in q:
        a = sum(set(fac))
    elif "How many primes are multiplied" in q:
        a = len(fac)
    else:
        raise ValueError("unknown ask")
    return {"answer": canon(a)}


def s_last_digit_power(q):
    expr = re.search(r"Let the number X be (.*?) \(the power means", q).group(1)
    terms = [(int(b), int(e)) for b, e in re.findall(r"(\d+) raised to the power (\d+)", expr)]
    op = "times" if " times " in expr else "plus"

    def comb(vals):
        return (sum(vals) if op == "plus" else math.prod(vals)) % 10

    std = comb([pow(b, e, 10) for b, e in terms])
    plus_one = comb([pow(b, e + 1, 10) for b, e in terms])  # "b multiplied by itself e times" read literally = b^(e+1)
    alt = {}
    if plus_one != std:
        alt["literal_multiplied_by_itself_e_times"] = canon(plus_one)
    return {"answer": canon(std), "alt": alt}


# ---------------------------------------------------------------- algebra
def s_quadratic_area(q):
    m = re.search(r"has an area of (\d+) square metres\. Its length is (\d+) metres more than its width", q)
    if m:
        A, d = int(m.group(1)), int(m.group(2))
        sols = [x for x in range(1, A + 1) if x * (x + d) == A]
        return {"answer": canon(sols[0])} if len(sols) == 1 else {"answer": "NO_UNIQUE"}
    m = re.search(r"has a perimeter of (\d+) metres and an area of (\d+) square metres", q)
    if m:
        P, A = int(m.group(1)), int(m.group(2))
        sols = [(w, P // 2 - w) for w in range(1, P // 2) if w * (P // 2 - w) == A and P % 2 == 0]
        return {"answer": canon(max(max(s) for s in sols))}
    m = re.search(r"differ by (\d+), and their product is (\d+)", q)
    if m:
        d, A = int(m.group(1)), int(m.group(2))
        sols = [x for x in range(1, A + 1) if x * (x + d) == A]
        return {"answer": canon(sols[0])} if len(sols) == 1 else {"answer": "NO_UNIQUE"}
    m = re.search(r"differ by (\d+), and the sum of their squares is (\d+)", q)
    d, S = int(m.group(1)), int(m.group(2))
    sols = [x for x in range(1, math.isqrt(S) + 1) if x * x + (x + d) ** 2 == S]
    return {"answer": canon(sols[0])} if len(sols) == 1 else {"answer": "NO_UNIQUE"}


def _clue_fns(text):
    out = []
    for c in [c.strip() for c in text.split(";")]:
        if m := re.fullmatch(r"its digits add up to (\d+)", c):
            v = int(m.group(1)); out.append(lambda n, v=v: sum(map(int, str(n))) == v)
        elif m := re.fullmatch(r"the product of its digits is (\d+)", c):
            v = int(m.group(1)); out.append(lambda n, v=v: math.prod(map(int, str(n))) == v)
        elif c == "reversing its digits gives the same number":
            out.append(lambda n: str(n) == str(n)[::-1])
        elif m := re.fullmatch(r"reversing its digits gives a number that is (\d+) (more|less) than it", c):
            v = int(m.group(1)) * (1 if m.group(2) == "more" else -1); out.append(lambda n, v=v: int(str(n)[::-1]) - n == v)
        elif m := re.fullmatch(r"it is a multiple of (\d+)", c):
            v = int(m.group(1)); out.append(lambda n, v=v: n % v == 0)
        elif c == "it is even":
            out.append(lambda n: n % 2 == 0)
        elif c == "it is odd":
            out.append(lambda n: n % 2 == 1)
        elif c == "its first digit is larger than its last digit":
            out.append(lambda n: str(n)[0] > str(n)[-1])
        elif m := re.fullmatch(r"its first digit is (\d+) times its last digit", c):
            v = int(m.group(1)); out.append(lambda n, v=v: int(str(n)[0]) == v * int(str(n)[-1]))
        else:
            raise ValueError(f"unknown clue {c!r}")
    return out


def s_digit_puzzle(q):
    m = re.search(r"Find the (\d)-digit number \(it does not start with 0\) for which all of these are true: (.*?)\. There is exactly one", q)
    nd = int(m.group(1))
    fns = _clue_fns(m.group(2))
    cands = [n for n in range(10 ** (nd - 1), 10**nd) if all(f(n) for f in fns)]
    if len(cands) != 1:
        return {"answer": f"NOT_UNIQUE:{cands[:5]}"}
    # alternative reading: a reversal with a leading zero is not a number of the same length (trailing-zero numbers excluded)
    alt = {}
    if any("reversing" in c for c in m.group(2).split(";")) and str(cands[0]).endswith("0"):
        alt["reverse_of_trailing_zero_is_not_a_number"] = "AMBIG"
    return {"answer": canon(cands[0]), "alt": alt}


# ---------------------------------------------------------------- geometry
def s_pythagoras(q):
    if m := re.search(r"A ladder (\d+) metres long .* Its foot is (\d+) metres from the base", q):
        c, a = int(m.group(1)), int(m.group(2)); v = math.isqrt(c * c - a * a); assert v * v == c * c - a * a
    elif m := re.search(r"A ladder (\d+) metres long .* its top reaches (\d+) metres up", q):
        c, b = int(m.group(1)), int(m.group(2)); v = math.isqrt(c * c - b * b); assert v * v == c * c - b * b
    elif m := re.search(r"walks (\d+) metres due east and then (\d+) metres due north", q):
        a, b = int(m.group(1)), int(m.group(2)); v = math.isqrt(a * a + b * b); assert v * v == a * a + b * b
    elif m := re.search(r"is (\d+) centimetres wide and (\d+) centimetres tall", q):
        a, b = int(m.group(1)), int(m.group(2)); v = math.isqrt(a * a + b * b); assert v * v == a * a + b * b
    else:
        m = re.search(r"two short sides .* of (\d+) centimetres and (\d+) centimetres", q)
        a, b = int(m.group(1)), int(m.group(2)); c = math.isqrt(a * a + b * b); assert c * c == a * a + b * b; v = a + b + c
    return {"answer": canon(v)}


def s_grid_perimeter(q):
    rows = [(int(a), int(b)) for a, b in re.findall(r"has squares in columns (\d+) to (\d+), both included", q)]
    cells = {(r, c) for r, (a, b) in enumerate(rows) for c in range(a, b + 1)}
    per = sum(1 for (r, c) in cells for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (r + dr, c + dc) not in cells)
    return {"answer": canon(per)}


def s_painted_cube(q):
    a, b, c = (int(x) for x in re.search(r"into a box (\d+) cubes long, (\d+) cubes wide and (\d+) cubes high", q).groups())
    bottom_unpainted = "except the bottom face" in q
    f = int(re.search(r"have exactly (\d) painted", q).group(1))
    # class sizes per axis: (number of positions, painted faces contributed)
    xs = [(2, 1), (a - 2, 0)]
    ys = [(2, 1), (b - 2, 0)]
    zs = [(1, 1), (1, 0 if bottom_unpainted else 1), (c - 2, 0)]
    tot = sum(nx * ny * nz for nx, px in xs for ny, py in ys for nz, pz in zs if px + py + pz == f)
    return {"answer": canon(tot)}


# ---------------------------------------------------------------- pricing
def s_min_cost_packs(q):
    m = re.search(r"one (\S+?) costs (\d+) dollars, and (.*?)\. (\w+) needs at least (\d+)", q)
    single = int(m.group(2))
    packs = [(int(p), int(c)) for p, c in re.findall(r"a pack of (\d+) \S+ costs (\d+) dollars", m.group(3))]
    need = int(m.group(5))
    best = None
    ranges = [range(0, need // p + 2) for p, _ in packs]
    for combo in itertools.product(*ranges):
        got = sum(k * p for k, (p, _) in zip(combo, packs))
        cost = sum(k * c for k, (_, c) in zip(combo, packs)) + max(0, need - got) * single
        if best is None or cost < best:
            best = cost
    return {"answer": canon(best)}


def s_tiered_pricing(q):
    first = re.search(r"the first (\d+) units cost (\d+) cents each", q)
    tiers = [(int(first.group(1)), int(first.group(2)))] + [(int(u), int(c)) for u, c in re.findall(r"the next (\d+) units cost (\d+) cents each", q)]
    last = int(re.search(r"every unit after that costs (\d+) cents each", q).group(1))
    rates = []
    for u, c in tiers:
        rates += [c] * u

    def bill(n):
        return sum(rates[i] if i < len(rates) else last for i in range(n))

    if m := re.search(r"What is the bill for (\d+) units", q):
        return {"answer": canon(Fraction(bill(int(m.group(1))), 100))}
    b = Fraction(re.search(r"A customer's bill is ([\d.]+) dollars", q).group(1)) * 100
    n = 0
    while bill(n) < b:
        n += 1
    return {"answer": canon(n) if bill(n) == b else "NO_EXACT"}


# ---------------------------------------------------------------- sequences
def s_recurrence(q):
    pos = int(re.search(r"What is the number in position (\d+)", q).group(1))
    if m := re.search(r"The first two numbers are (\d+) and (\d+)\. Every number after those is the sum of the two", q):
        t = [int(m.group(1)), int(m.group(2))]
        while len(t) < pos:
            t.append(t[-2] + t[-1])
    elif m := re.search(r"The first number is (\d+)\. Every number after it is (\d+) times the number just before it, (plus|minus) (\d+)", q):
        c = int(m.group(2)); d = int(m.group(4)) * (1 if m.group(3) == "plus" else -1)
        t = [int(m.group(1))]
        while len(t) < pos:
            t.append(c * t[-1] + d)
    else:
        m = re.search(r"The first number is (\d+)\. Every number after it is the number just before it plus its own position", q)
        a = int(m.group(1))
        t = [a + sum(range(2, pos + 1))]  # closed form
    return {"answer": canon(t[-1])}


def s_finite_differences(q):
    m = re.search(r"The first (\d+) numbers of a pattern are ([\-\d, and]+)\. .* polynomial of degree (\d) .* What is the number in position (\d+)\?", q)
    terms = [int(x) for x in re.findall(r"-?\d+", m.group(2))]
    deg, ask = int(m.group(3)), int(m.group(4))
    xs = list(range(1, len(terms) + 1))
    # Lagrange interpolation through the first deg+1 points, then verify on every printed term
    pts = list(zip(xs[: deg + 1], terms[: deg + 1]))

    def L(x):
        s = Fraction(0)
        for i, (xi, yi) in enumerate(pts):
            p = Fraction(yi)
            for j, (xj, _) in enumerate(pts):
                if j != i:
                    p *= Fraction(x - xj, xi - xj)
            s += p
        return s

    if any(L(x) != y for x, y in zip(xs, terms)):
        return {"answer": "NOT_DEGREE"}
    return {"answer": canon(L(ask))}


# ---------------------------------------------------------------- statistics
def s_median(q):
    if m := re.search(r"The values are ([\-\d, and]+)\.", q):
        vals = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    else:
        vals = []
        for v, c in re.findall(r"the value (\d+) occurs (once|\d+ times)", q):
            vals += [int(v)] * (1 if c == "once" else int(c.split()[0]))
    return {"answer": canon(Fraction(statistics.median(vals)).limit_denominator(100))}


def s_mode(q):
    vals = [int(x) for x in re.findall(r"\d+", re.search(r"test scores: ([\d, and]+)\.", q).group(1))]
    cnt = Counter(vals)
    top = max(cnt.values())
    winners = [v for v, c in cnt.items() if c == top]
    if len(winners) != 1:
        return {"answer": "TIE"}
    if "Which value occurs most often" in q:
        return {"answer": canon(winners[0])}
    return {"answer": canon(top)}


# ---------------------------------------------------------------- division
def s_division(q):
    if m := re.search(r"A factory makes (\d+) \S+\. They are packed into boxes that each hold (\d+) .* crates that each hold (\d+) boxes", q):
        n, k, cm = (int(x) for x in m.groups())
        boxes = 0
        left = n
        while left > 0:
            left -= k; boxes += 1
        crates = 0
        while boxes > 0:
            boxes -= cm; crates += 1
        return {"answer": canon(crates)}
    if m := re.search(r"How many whole numbers from (\d+) to (\d+), both included, are exactly divisible by (\d+)", q):
        a, b, d = (int(x) for x in m.groups())
        return {"answer": canon(sum(1 for x in range(a, b + 1) if x % d == 0)), "alt": {"exclusive_of_both_ends": canon(sum(1 for x in range(a + 1, b) if x % d == 0))}}
    m = re.search(r"(\d+) people must travel by bus, .* Each bus has (\d+) seats", q)
    n, k = int(m.group(1)), int(m.group(2))
    buses = 0
    while buses * k < n:
        buses += 1
    return {"answer": canon(buses * k - n)}


SOLVERS = {
    "M1.inclusion_exclusion": s_inclusion_exclusion,
    "M1.binomial_choose": s_binomial_choose,
    "M1.slot_permutations": s_slot_permutations,
    "M1.change_ways": s_change_ways,
    "M1.pigeonhole_worst_case": s_pigeonhole,
    "M1.gcd_lcm": s_gcd_lcm,
    "M1.crt_congruence": s_crt,
    "M1.prime_factors": s_prime_factors,
    "M1.last_digit_power": s_last_digit_power,
    "M1.quadratic_area": s_quadratic_area,
    "M1.digit_puzzle": s_digit_puzzle,
    "M1.pythagoras": s_pythagoras,
    "M1.grid_perimeter": s_grid_perimeter,
    "M1.painted_cube": s_painted_cube,
    "M1.min_cost_packs": s_min_cost_packs,
    "M1.tiered_pricing": s_tiered_pricing,
    "M1.recurrence_iterate": s_recurrence,
    "M1.finite_differences": s_finite_differences,
    "M1.median_list": s_median,
    "M1.mode_tally": s_mode,
    "M1.division_counting": s_division,
}


def solve(lid, q):
    return SOLVERS[lid](q)
