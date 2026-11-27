"""Second solvers (M0, addendum 1 s8 item 1) for 10 M1 lineages, NAME=m1a.

Written from fixtures (question text + structured) and SCHEMA.md only.
Standard library only. Each solver computes from `structured`; each also has a
text parser (TEXT_PARSERS) used by run_solver2.py to cross-check that the
structured fields equal what the question states, and where the text carries
something structured lacks (ages: which name is asked; average_missing: the
maximum mark), the text is read directly.
Solvers raise ValueError when the item has no well-defined answer under the
reading implemented (non-integer, out of range, inconsistent).
"""
import math
import re
from fractions import Fraction

PREFIX = "M1."


# ---------------------------------------------------------------- ages_r3
def _ages_text(q):
    m = re.match(r"(\w+) is (\d+) times as old as (\w+) now\. In (\d+) years? from now, their two ages added together will be (\d+)\. .*How old is (\w+) now, in years\?", q)
    if not m:
        raise ValueError("ages: text not parsed")
    older, k, younger, t, s, who = m.groups()
    if older == younger:
        raise ValueError("ages: both people have the same name")
    if who == older:
        ask = "older"
    elif who == younger:
        ask = "younger"
    else:
        raise ValueError("ages: asked name is neither person")
    return {"k": int(k), "t": int(t), "sum": int(s), "ask": ask}


def ages(question, st):
    k, t, s = st["k"], st["t"], st["sum"]
    ask = _ages_text(question)["ask"]  # identity of the asked person from text
    if ask != st["ask"]:
        raise ValueError("ages: text ask != structured ask")
    # older = k*y; (k*y + t) + (y + t) = s
    num = s - 2 * t
    if num <= 0 or num % (k + 1):
        raise ValueError("ages: non-integer or non-positive age")
    y = num // (k + 1)
    return str(y if ask == "younger" else k * y)


# ---------------------------------------------------- arithmetic_series_r3
def _arith_text(q):
    m = re.search(r"saves (\d+) dollars on day 1 and then saves (\d+) dollars more each day .*after (\d+) days \(counting day 1 to day (\d+), both included\)", q)
    if not m or m.group(3) != m.group(4):
        raise ValueError("arith: text not parsed")
    return {"first": int(m.group(1)), "step": int(m.group(2)), "days": int(m.group(3))}


def arithmetic_series(question, st):
    a, d, n = st["first"], st["step"], st["days"]
    return str(sum(a + d * i for i in range(n)))


# ------------------------------------------------------ average_missing_r4
def _avg_text(q):
    m = re.search(r"has scored ([\d, ]+) on (\d+) tests, each marked out of (\d+) with whole-number marks\. What score is needed on the next test to make the mean of all (\d+) tests exactly (\d+)(?:\.(\d+))?\?", q)
    if not m:
        raise ValueError("avg: text not parsed")
    scores = [int(x) for x in m.group(1).split(",")]
    if len(scores) != int(m.group(2)) or int(m.group(4)) != len(scores) + 1:
        raise ValueError("avg: counts inconsistent")
    mean = Fraction(m.group(5) + "." + (m.group(6) or "0"))
    return {"scores": scores, "n": int(m.group(4)), "mean_cents": mean * 100, "max": int(m.group(3))}


def average_missing(question, st):
    mx = _avg_text(question)["max"]  # max mark only in the text
    need = Fraction(st["mean_cents"], 100) * st["n"] - sum(st["scores"])
    if need.denominator != 1:
        raise ValueError("avg: needed score not a whole number")
    need = int(need)
    if not 0 <= need <= mx:
        raise ValueError("avg: needed score outside 0..max")
    return str(need)


# ---------------------------------------------------------- change_ways_r3
def _change_text(q):
    m = re.search(r"coins worth (\d+), (\d+) and (\d+) cents, .* can exactly (\d+) cents be paid\?", q)
    if not m:
        raise ValueError("change: text not parsed")
    return {"coins": [int(m.group(i)) for i in (1, 2, 3)], "target": int(m.group(4))}


def change_ways(question, st):
    coins, target = st["coins"], st["target"]
    if len(set(coins)) != len(coins) or min(coins) <= 0:
        raise ValueError("change: coin values not distinct positive")
    ways = [1] + [0] * target
    for c in coins:
        for v in range(c, target + 1):
            ways[v] += ways[v - c]
    return str(ways[target])


# ------------------------------------------------------- clock_duration_r4
def _clock_text(q):
    legs = re.findall(r"leg (\d+) leaves at (\d\d):(\d\d) and arrives at (\d\d):(\d\d)", q)
    if not legs or [int(x[0]) for x in legs] != list(range(1, len(legs) + 1)):
        raise ValueError("clock: text not parsed")
    return {"legs": [[int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)] for _, h1, m1, h2, m2 in legs]}


def clock_duration(question, st):
    tot = 0
    prev_arr = -1
    for dep, arr in st["legs"]:
        if not (0 <= dep < arr < 1440) or dep < prev_arr:
            raise ValueError("clock: leg times not ordered within one day")
        tot += arr - dep
        prev_arr = arr
    return str(tot)


# ---------------------------------------------------------- consecutive_r3
def _consec_text(q):
    m = re.match(r"The sum of (\d+) consecutive (integers|numbers that each differ from the next by (\d+)) \(listed from smallest to largest, positive or negative whole numbers\) is (-?\d+)\. What is the (largest|smallest) of them\?", q)
    if not m:
        raise ValueError("consec: text not parsed")
    return {"count": int(m.group(1)), "step": int(m.group(3)) if m.group(3) else 1, "sum": int(m.group(4)), "ask": m.group(5)}


def consecutive(question, st):
    c, d, s = st["count"], st["step"], st["sum"]
    num = s - d * c * (c - 1) // 2
    if num % c:
        raise ValueError("consec: no integer solution")
    lo = num // c
    return str(lo if st["ask"] == "smallest" else lo + d * (c - 1))


# ------------------------------------------------------- crt_congruence_r3
def _crt_text(q):
    conds = re.findall(r"[Dd]ividing it by (\d+) leaves remainder (\d+)", q)
    if not conds:
        raise ValueError("crt: text not parsed")
    return {"conditions": [[int(a), int(b)] for a, b in conds]}


def crt_congruence(question, st):
    conds = st["conditions"]
    for m, r in conds:
        if not 0 <= r < m:
            raise ValueError("crt: remainder out of range")
    L = 1
    for m, _ in conds:
        L = L * m // math.gcd(L, m)
    # Brute force over one full period: smallest positive x (x=L if all r=0).
    m0, r0 = max(conds)
    x = r0 if r0 > 0 else m0
    while x <= L:
        if all(x % m == r for m, r in conds):
            return str(x)
        x += m0
    raise ValueError("crt: no solution")


# ---------------------------------------------------- division_counting_r3
def _div_text(q):
    m = re.match(r"(\d+) people must travel by bus, and \w+ hires as few buses as possible\. Each bus has (\d+) seats, and nobody stands\. When all (\d+) people are on board, how many seats in total are empty\?", q)
    if m:
        if m.group(1) != m.group(3):
            raise ValueError("div: people counts differ")
        return {"shape": "empty_seats", "people": int(m.group(1)), "seats": int(m.group(2))}
    m = re.search(r"A factory makes (\d+) (\w+)\. They are packed into boxes that each hold exactly (\d+) (\w+); (\w+) that do not fill a box are left out\. The boxes are then put on pallets that each hold (\d+) boxes, and as many full pallets as possible are made\. How many boxes are not on a full pallet\?", q)
    if m:
        return {"shape": "pallets", "items": int(m.group(1)), "box": int(m.group(3)), "crate": int(m.group(6))}
    raise ValueError("div: text not parsed")


def division_counting(question, st):
    if st["shape"] == "empty_seats":
        p, s = st["people"], st["seats"]
        buses = -(-p // s)
        return str(buses * s - p)
    if st["shape"] == "pallets":
        boxes = st["items"] // st["box"]
        return str(boxes % st["crate"])
    raise ValueError("div: unknown shape")


# --------------------------------------------------- finite_differences_r4
def _fd_text(q):
    m = re.search(r"The first (\d+) numbers of a pattern are ([\d, ]+) and (\d+)\. .*polynomial of degree (\d+) in its position \(position 1 is the first number\)\. What is the number in position (\d+)\?", q)
    if not m:
        raise ValueError("fd: text not parsed")
    terms = [int(x) for x in m.group(2).split(",")] + [int(m.group(3))]
    if len(terms) != int(m.group(1)):
        raise ValueError("fd: count mismatch")
    return {"terms": terms, "degree": int(m.group(4)), "ask": int(m.group(5))}


def _lagrange(xs, ys, x):
    tot = Fraction(0)
    for i, (xi, yi) in enumerate(zip(xs, ys)):
        p = Fraction(yi)
        for j, xj in enumerate(xs):
            if j != i:
                p *= Fraction(x - xj, xi - xj)
        tot += p
    return tot


def finite_differences(question, st):
    terms, deg, ask = st["terms"], st["degree"], st["ask"]
    n = len(terms)
    if n < deg + 1:
        raise ValueError("fd: too few terms for the degree")
    xs = list(range(1, deg + 2))
    ys = terms[: deg + 1]
    # every given term must lie on the degree-`deg` polynomial
    for i in range(deg + 1, n):
        if _lagrange(xs, ys, i + 1) != terms[i]:
            raise ValueError("fd: terms not on a polynomial of the stated degree")
    # stated degree must be exact (leading difference non-zero)
    diffs = list(terms)
    for _ in range(deg):
        diffs = [b - a for a, b in zip(diffs, diffs[1:])]
    if diffs[0] == 0:
        raise ValueError("fd: polynomial has lower degree than stated")
    v = _lagrange(xs, ys, ask)
    if v.denominator != 1:
        raise ValueError("fd: non-integer value")
    return str(int(v))


# --------------------------------------------------- fraction_remainder_r3
_ORD = {"half": 2, "third": 3, "quarter": 4, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
        "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}


def _frac_text(q):
    m = re.match(r"(\w+) has (\d+) dollars\. \w+ spends one (\w+) of it on books, then one (\w+) of what is left on lunch\. How many dollars does \w+ have left\?", q)
    if not m or m.group(3) not in _ORD or m.group(4) not in _ORD:
        raise ValueError("frac: text not parsed")
    return {"start": int(m.group(2)), "a": _ORD[m.group(3)], "b": _ORD[m.group(4)]}


def fraction_remainder(question, st):
    s, a, b = st["start"], st["a"], st["b"]
    if s % a:
        raise ValueError("frac: first spend not whole dollars")
    left = s - s // a
    if left % b:
        raise ValueError("frac: second spend not whole dollars")
    return str(left - left // b)


SOLVERS = {
    PREFIX + "ages_r3": ages,
    PREFIX + "arithmetic_series_r3": arithmetic_series,
    PREFIX + "average_missing_r4": average_missing,
    PREFIX + "change_ways_r3": change_ways,
    PREFIX + "clock_duration_r4": clock_duration,
    PREFIX + "consecutive_r3": consecutive,
    PREFIX + "crt_congruence_r3": crt_congruence,
    PREFIX + "division_counting_r3": division_counting,
    PREFIX + "finite_differences_r4": finite_differences,
    PREFIX + "fraction_remainder_r3": fraction_remainder,
}

TEXT_PARSERS = {
    PREFIX + "ages_r3": _ages_text,
    PREFIX + "arithmetic_series_r3": _arith_text,
    PREFIX + "average_missing_r4": _avg_text,
    PREFIX + "change_ways_r3": _change_text,
    PREFIX + "clock_duration_r4": _clock_text,
    PREFIX + "consecutive_r3": _consec_text,
    PREFIX + "crt_congruence_r3": _crt_text,
    PREFIX + "division_counting_r3": _div_text,
    PREFIX + "finite_differences_r4": _fd_text,
    PREFIX + "fraction_remainder_r3": _frac_text,
}
