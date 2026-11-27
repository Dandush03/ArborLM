# ruff: noqa: E501
"""M1 batch 1, family "number_theory": Euclid / lcm, simultaneous congruences, prime factorisation, cycles of last digits."""

from __future__ import annotations

import math
import random
from functools import reduce

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, and_, ctx, m1
from studies.m0.vocab import NAMES

_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)


@m1("number_theory")
def gcd_lcm(level: int, r: random.Random) -> Built:
    """structured: {"ask": "gcd" | "lcm", "values": [positive integers, distinct]}.
    gcd: the largest whole length that divides every value exactly (ribbons cut with nothing left over). lcm: the smallest positive time at which
    every periodic event (periods = values) happens together again, all having started together. Generator guarantees gcd >= 2 and gcd < min(values),
    or max(values) < lcm < product(values); with three or four values, dropping any one value changes the answer; for gcd no two values differ by exactly the answer."""
    k = 2 if level < 3 else (3 if level < 5 else 4)
    ask = r.choice(("gcd", "lcm"))
    if ask == "gcd":
        g = r.randint(2, 12 + 3 * level)
        vals = [g * r.randint(2, 14 + 6 * level) for _ in range(k)]
        ans = reduce(math.gcd, vals)
        if len(set(vals)) < k or ans == min(vals) or any(abs(vals[i] - vals[j]) == ans for i in range(k) for j in range(i)) or any(reduce(math.gcd, [v for j, v in enumerate(vals) if j != i]) == ans for i in range(k) if k > 2):
            raise Retry
        name = r.choice(NAMES)
        q = (f"{name} has {k} ribbons of lengths {and_([str(v) for v in vals])} centimetres. {name} cuts every ribbon into pieces that all have the same whole-number length in centimetres, "
             f"with nothing left over from any ribbon. What is the greatest possible length of a piece, in centimetres? {WHOLE}")
    else:
        vals = [r.randint(4, 30 + 5 * level) for _ in range(k)]
        ans = reduce(math.lcm, vals)
        if len(set(vals)) < k or ans == math.prod(vals) or ans == max(vals) or any(reduce(math.lcm, [v for j, v in enumerate(vals) if j != i]) == ans for i in range(k) if k > 2):
            raise Retry
        q = (f"{k} lights flash at the same moment. After that, one flashes every {vals[0]} seconds, "
             + ", ".join(f"another every {v} seconds" for v in vals[1:-1]) + (", and " if k > 2 else "") + (f"the last every {vals[-1]} seconds" if k > 2 else f"the other every {vals[-1]} seconds")
             + f". After how many seconds do all {k} flash together again for the first time? {WHOLE}")
    return Built(q if ask == "gcd" else f"{ctx(r)} {q}", {"ask": ask, "values": vals}, str(ans), "number", None)


@m1("number_theory")
def crt_congruence(level: int, r: random.Random) -> Built:
    """structured: {"conditions": [[modulus, remainder]]} with pairwise coprime moduli and 0 < remainder < modulus.
    Answer: the smallest positive whole number that leaves each remainder on division by its modulus (it is at most the product of the moduli)."""
    k = 2 if level < 3 else (3 if level < 5 else 4)
    top = 15 + 5 * level if k == 2 else 9 + 2 * level
    mods: list[int] = []
    for _ in range(k):
        m = r.randint(3, top)
        if any(math.gcd(m, x) != 1 for x in mods):
            raise Retry
        mods.append(m)
    rems = [r.randint(1, m - 1) for m in mods]
    P = math.prod(mods)
    ans = next(n for n in range(1, P + 1) if all(n % m == rr for m, rr in zip(mods, rems, strict=True)))
    if ans <= max(mods):
        raise Retry
    conds = [[m, rr] for m, rr in zip(mods, rems, strict=True)]
    name = r.choice(NAMES)
    txt = "; ".join(f"dividing it by {m} leaves remainder {rr}" for m, rr in conds)
    q = f"{name} is thinking of a positive whole number. {txt[0].upper() + txt[1:]}. What is the smallest positive whole number that {name} could be thinking of? {WHOLE}"
    return Built(q, {"conditions": conds}, str(ans), "number", None)


@m1("number_theory")
def prime_factors(level: int, r: random.Random) -> Built:
    """structured: {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. N is factorised into primes.
    divisors: how many positive whole numbers divide N exactly (1 and N included). largest: the largest prime that divides N. distinct_sum: the sum of the
    different primes that divide N. factor_count: how many primes are multiplied when N is written as a product of primes (a prime used twice counts twice)."""
    npr = r.randint(2, 3) if level < 3 else r.randint(3, 4) if level < 5 else r.randint(3, 5)
    pool = _PRIMES[: min(10, 7 + level // 2)]
    ps = sorted(r.sample(pool, npr))
    es = [r.randint(1, 2 + level // 2 + (1 if p == 2 else 0)) for p in ps]
    n = math.prod(p**e for p, e in zip(ps, es, strict=True))
    if n > 3000 * 3**level or n < 12:
        raise Retry
    ask = r.choice(("divisors", "largest", "distinct_sum", "factor_count"))
    ans = {"divisors": math.prod(e + 1 for e in es), "largest": max(ps), "distinct_sum": sum(ps), "factor_count": sum(es)}[ask]
    what = {
        "divisors": "How many different positive whole numbers divide it exactly (counting 1 and the number itself)?",
        "largest": "What is the largest prime number that divides it exactly?",
        "distinct_sum": "Add up the different prime numbers that divide it exactly (each different prime counted once). What is the sum?",
        "factor_count": "Write it as a product of prime numbers, repeating a prime as often as needed (for example 12 = 2 x 2 x 3 uses three primes). How many primes are multiplied?",
    }[ask]
    return Built(f"{ctx(r)} Consider the number {n}. {what} {WHOLE}", {"n": n, "ask": ask}, str(ans), "number", None)


@m1("number_theory", "borderline")
def last_digit_power(level: int, r: random.Random) -> Built:
    """structured: {"op": "sum" | "product", "terms": [[base, exponent]]}. Answer: the last (units) digit of the sum (or product) of the numbers base**exponent.
    Borderline: modular arithmetic like crt_congruence, but the procedure is cycle-finding in the last digit of powers."""
    t = 1 if level < 2 else (2 if level < 5 else 3)
    op = r.choice(("sum", "product")) if t > 1 else "sum"
    terms = [[r.randint(2, 49 + 25 * level), r.randint(12, 300 + 100 * level)] for _ in range(t)]
    if any(b % 10 in (0, 1, 5, 6) or pow(b, e, 10) == b % 10 or (t == 1 and b % 10 in (4, 9)) for b, e in terms):
        raise Retry
    vals = [pow(b, e, 10) for b, e in terms]
    ans = (sum(vals) if op == "sum" else math.prod(vals)) % 10
    if t > 1 and ans == (sum(b % 10 for b, _ in terms) if op == "sum" else math.prod(b % 10 for b, _ in terms)) % 10:
        raise Retry
    pw = [f"{b} raised to the power {e}" for b, e in terms]
    expr = pw[0] if t == 1 else (f" {'plus' if op == 'sum' else 'times'} ").join(pw)
    q = f"Let the number X be {expr} (the power means {terms[0][0]} multiplied by itself {terms[0][1]} times" + ("" if t == 1 else ", and likewise for the others") + f"). What is the last digit of X, that is, its digit in the units place? {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"op": op, "terms": terms}, str(ans), "number", None)
