# ruff: noqa: E501
"""M1 batch 1, family "sequences": iterating a stated recurrence, and extending a polynomial pattern by finite differences."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, and_, ctx, m1


@m1("sequences")
def recurrence_iterate(level: int, r: random.Random) -> Built:
    """structured: {"shape": "sum_prev_two" | "affine" | "add_index", "first": [a] or [a, b], "mult": c, "add": d, "position": n}. Terms are numbered from 1.
    sum_prev_two: every term after the second is the sum of the two before it. affine: every term after the first is mult * previous + add.
    add_index: every term after the first is the previous term plus its own position number. Answer: the term at `position`, by applying the rule step by step."""
    shape = r.choice(("sum_prev_two", "affine", "add_index"))
    n = r.randint(6 + level, 9 + 2 * level)
    if shape == "sum_prev_two":
        a, b = r.randint(1, 29 + 3 * level), r.randint(1, 29 + 3 * level)
        t = [a, b]
        while len(t) < n:
            t.append(t[-1] + t[-2])
        rule = f"The first two numbers are {a} and {b}. Every number after those is the sum of the two numbers just before it"
        st = {"shape": shape, "first": [a, b], "mult": 0, "add": 0, "position": n}
    elif shape == "affine":
        a, c, d = r.randint(1, 29 + 3 * level), r.randint(2, 3), r.randint(-9 - level, 12 + level)
        n = min(n, 7 + level // 2)
        t = [a]
        while len(t) < n:
            t.append(c * t[-1] + d)
        rule = f"The first number is {a}. Every number after it is {c} times the number just before it, {'plus' if d >= 0 else 'minus'} {abs(d)}"
        st = {"shape": shape, "first": [a], "mult": c, "add": d, "position": n}
    else:
        a = r.randint(1, 40 + 5 * level)
        t = [a]
        while len(t) < n:
            t.append(t[-1] + len(t) + 1)
        rule = f"The first number is {a}. Every number after it is the number just before it plus its own position in the list (so the second number is the first plus 2, the third is the second plus 3, and so on)"
        st = {"shape": shape, "first": [a], "mult": 0, "add": 0, "position": n}
    if t[-1] > 10**8 or t[-1] < 0:
        raise Retry
    q = f"A list of numbers is built by a rule. {rule}. What is the number in position {n} of the list (position 1 is the first number)? {WHOLE}"
    return Built(f"{ctx(r)} {q}", st, str(t[-1]), "number", None)


@m1("sequences")
def finite_differences(level: int, r: random.Random) -> Built:
    """structured: {"terms": [the printed first terms, positions 1..m], "degree": 2 | 3, "ask": position}. The terms come from an integer polynomial of the stated degree in the position.
    Answer: the term at position `ask` (m + 1 or m + 2), found by extending the table of differences (or by fitting the polynomial)."""
    deg = 2 if level < 5 else 3
    if deg == 2:
        a, b, c = r.randint(1, 4 + level // 2), r.randint(-5, 8 + level), r.randint(-5, 30)
        poly = [c, b, a]
    else:
        poly = [r.randint(-5, 15), r.randint(-4, 6), r.randint(-2, 4), r.randint(1, 2)]

    def f(x: int) -> int:
        return sum(co * x**i for i, co in enumerate(poly))

    m = deg + 3 + (level >= 3)
    terms = [f(x) for x in range(1, m + 1)]
    ask = m + r.randint(1, 2)
    if min(terms) < 0 or f(ask) < 0 or len(set(terms)) < m:
        raise Retry
    q = f"The first {m} numbers of a pattern are {and_([str(t) for t in terms])}. The pattern continues in the same way, and each number is given by a polynomial of degree {deg} in its position (position 1 is the first number). What is the number in position {ask}? {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"terms": terms, "degree": deg, "ask": ask}, str(f(ask)), "number", None)
