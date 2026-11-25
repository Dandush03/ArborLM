# ruff: noqa: E501
"""M1 batch 1, family "algebra": quadratic equations from areas and products, and digit puzzles solved by testing candidates against clues."""

from __future__ import annotations

import math
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, ctx, m1


@m1("algebra")
def quadratic_area(level: int, r: random.Random) -> Built:
    """structured: {"shape": "rect_area" | "rect_perimeter" | "product" | "squares", "d": d, "area": A, "perimeter": P, "total": S}. All answers are the positive whole root x of a quadratic.
    rect_area: width x, length x + d, area A; answer x. rect_perimeter: a rectangle with perimeter P and area A; answer the LONGER side. product: two whole numbers that differ by d have product A;
    answer the smaller. squares: two whole numbers that differ by d have squares adding up to S; answer the smaller. (Fields not used by a shape are 0.) d >= 3."""
    shape = r.choice(("rect_area", "rect_perimeter", "product", "squares"))
    hi = 30 + 10 * level
    x = r.randint(2, hi)
    lo_d = max(3, math.isqrt(4 * x) + 3)
    d = r.randint(lo_d, lo_d + max(2, hi // 2))
    name = r.choice(("garden", "poster", "playing field", "banner"))
    if shape == "rect_area":
        ans, A = x, x * (x + d)
        q = f"A rectangular {name} has an area of {A} square metres. Its length is {d} metres more than its width. What is its width, in metres? {WHOLE}"
        st = {"shape": shape, "d": d, "area": A, "perimeter": 0, "total": 0}
    elif shape == "rect_perimeter":
        w = x
        ln = x + d
        A, P = w * ln, 2 * (w + ln)
        ans = ln
        q = f"A rectangular {name} has a perimeter of {P} metres and an area of {A} square metres. What is the length of its longer side, in metres? {WHOLE}"
        st = {"shape": shape, "d": 0, "area": A, "perimeter": P, "total": 0}
    elif shape == "product":
        ans, A = x, x * (x + d)
        q = f"Two positive whole numbers differ by {d}, and their product is {A}. What is the smaller of the two numbers? {WHOLE}"
        st = {"shape": shape, "d": d, "area": A, "perimeter": 0, "total": 0}
    else:
        ans, S = x, x * x + (x + d) ** 2
        q = f"Two positive whole numbers differ by {d}, and the sum of their squares is {S}. What is the smaller of the two numbers? {WHOLE}"
        st = {"shape": shape, "d": d, "area": 0, "perimeter": 0, "total": S}
    return Built(f"{ctx(r)} {q}", st, str(ans), "number", None)


_CLUES = ("digit_sum", "digit_product", "reverse_gap", "multiple_of", "parity", "first_gt_last", "digit_relation")


def _clue_text(c: list, n_digits: int) -> str:
    k = c[0]
    if k == "digit_sum":
        return f"its digits add up to {c[1]}"
    if k == "digit_product":
        return f"the product of its digits is {c[1]}"
    if k == "reverse_gap":
        if c[1] == 0:
            return "reversing its digits gives the same number"
        return f"reversing its digits gives a number that is {abs(c[1])} {'more' if c[1] > 0 else 'less'} than it"
    if k == "multiple_of":
        return f"it is a multiple of {c[1]}"
    if k == "parity":
        return f"it is {c[1]}"
    if k == "first_gt_last":
        return "its first digit is larger than its last digit"
    return f"its first digit is {c[1]} times its last digit"


def _holds(n: int, c: list) -> bool:
    ds = [int(ch) for ch in str(n)]
    k = c[0]
    if k == "digit_sum":
        return sum(ds) == c[1]
    if k == "digit_product":
        p = 1
        for v in ds:
            p *= v
        return p == c[1]
    if k == "reverse_gap":
        return int(str(n)[::-1]) - n == c[1]
    if k == "multiple_of":
        return n % c[1] == 0
    if k == "parity":
        return (n % 2 == 0) == (c[1] == "even")
    if k == "first_gt_last":
        return ds[0] > ds[-1]
    return ds[0] == c[1] * ds[-1]


@m1("algebra")
def digit_puzzle(level: int, r: random.Random) -> Built:
    """structured: {"digits": 2 | 3, "clues": [[kind, parameter?]]} with kinds digit_sum S, digit_product P, reverse_gap D (reversed number minus the number), multiple_of m, parity "even"|"odd",
    first_gt_last, digit_relation q (first digit = q times last digit). Answer: the one number with that many digits (no leading zero) for which every clue holds; the generator
    checks, by testing all candidates, that it is unique and that dropping any one clue leaves more than one candidate."""
    nd = 2 if level == 0 else 3
    lo, hi = (10, 99) if nd == 2 else (100, 999)
    secret = r.randint(lo, hi)
    pool = [list(c) for c in (("digit_sum", sum(int(ch) for ch in str(secret))), ("digit_product", math.prod(int(ch) for ch in str(secret))),
                              ("reverse_gap", int(str(secret)[::-1]) - secret), ("multiple_of", r.choice((3, 4, 6, 7, 9, 11))),
                              ("parity", "even" if secret % 2 == 0 else "odd"), ("first_gt_last",), ("digit_relation", r.choice((2, 3))))]
    r.shuffle(pool)
    want = r.randint(2, 2 + (level >= 3) + (level >= 5))
    clues = [c for c in pool if _holds(secret, c)][:want]
    if len(clues) < 2:
        raise Retry
    cands = [n for n in range(lo, hi + 1) if all(_holds(n, c) for c in clues)]
    if cands != [secret]:
        raise Retry
    if any(sum(_holds(n, c) for n in range(lo, hi + 1)) < 4 for c in clues):
        raise Retry
    for i in range(len(clues)):
        if len([n for n in range(lo, hi + 1) if all(_holds(n, c) for j, c in enumerate(clues) if j != i)]) == 1:
            raise Retry
    q = f"Find the {nd}-digit number (it does not start with 0) for which all of these are true: " + "; ".join(_clue_text(c, nd) for c in clues) + f". There is exactly one such number. {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"digits": nd, "clues": clues}, str(secret), "number", None)
