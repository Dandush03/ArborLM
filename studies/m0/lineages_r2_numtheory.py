# ruff: noqa: E501
"""R2 batch 1, family "numtheory" (the name of an existing R2 family): Euclid, square-and-multiply, congruence search, factorisation."""

from __future__ import annotations

import math
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1

PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97)


def euclid_steps(a: int, b: int) -> int:
    n = 0
    while b:
        a, b = b, a % b
        n += 1
    return n


@batch1("numtheory")
def gcd_euclid(level: int, r: random.Random) -> Built:
    """Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm" | "steps"} with a > b > 0.
    Answer: the greatest common divisor, the least common multiple, or the number of replacements (x, y) -> (y, x mod y) made until the second number is 0."""
    g = r.randint(2, 15 + 6 * level)
    hi = 20 + 12 * level
    p, q2 = r.randint(2, hi), r.randint(2, hi)
    if abs(p - q2) < 2 or math.gcd(p, q2) != 1:
        raise Retry
    a, b = g * max(p, q2), g * min(p, q2)
    ask = r.choice(("gcd", "lcm", "steps")) if level >= 2 else r.choice(("gcd", "lcm"))
    if ask == "gcd":
        ans, text = g, f"What is the greatest common divisor of {a} and {b}?"
    elif ask == "lcm":
        ans, text = a * b // g, f"What is the least common multiple of {a} and {b}?"
    else:
        ans = euclid_steps(a, b)
        text = (f"Start with the pair ({a}, {b}). One step replaces a pair (x, y) by the pair (y, the remainder of x divided by y). "
                "Keep taking steps until the second number of the pair is 0. How many steps are taken?")
    return Built(text, {"a": a, "b": b, "ask": ask}, str(ans), "number", None)


@batch1("numtheory")
def modular_power(level: int, r: random.Random) -> Built:
    """Procedure: repeated squaring modulo m. structured: {"a": int, "e": int, "m": int}. Answer: the remainder of a^e divided by m (never 0 or 1)."""
    m = r.randint(6 + 4 * level, 20 + 15 * level)
    a = r.randint(2, m - 1)
    e = r.randint(8 + 6 * level, 30 + 40 * level)
    ans = pow(a, e, m)
    if ans in (0, 1) or ans == a:
        raise Retry
    q = f"Multiply together {e} copies of the number {a} (a product with {e} factors, each equal to {a}). What is the remainder when this product is divided by {m}?"
    return Built(q, {"a": a, "e": e, "m": m}, str(ans), "number", None)


@batch1("numtheory")
def crt_smallest(level: int, r: random.Random) -> Built:
    """Procedure: combine congruences (Chinese remainder). structured: {"congruences": [[remainder, modulus]]} with pairwise coprime moduli.
    Answer: the smallest positive integer x with x mod modulus = remainder for every pair (unique and at most the product of the moduli)."""
    k = 2 if level <= 2 else 3
    ms = sorted(r.sample(range(3, 12 + 3 * level), k))
    if any(math.gcd(ms[i], ms[j]) != 1 for i in range(k) for j in range(i + 1, k)):
        raise Retry
    prod = math.prod(ms)
    x = r.randint(1, prod)
    cons = [[x % m, m] for m in ms]
    parts = [f"leaves remainder {c} when divided by {m}" for c, m in cons]
    q = "What is the smallest positive whole number that " + ", and ".join(parts) + "?"
    return Built(q, {"congruences": cons}, str(x), "number", None)


@batch1("numtheory")
def prime_factor_query(level: int, r: random.Random) -> Built:
    """Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}.
    Answer: the largest prime factor of n, or the sum of all the primes in its prime factorisation, repeated primes counted each time (12 = 2 x 2 x 3 gives 7)."""
    k = (3, 4, 4, 4, 4, 4, 5)[level]
    pool = PRIMES[: 16 + level]
    fs = sorted(r.choice(pool) for _ in range(k))
    if fs[-1] <= 13:
        raise Retry  # at least one prime above 13, so "the biggest of the small primes" is not the procedure
    n = math.prod(fs)
    ds = sorted(set(fs))
    ask = r.choice(("largest", "sum_all"))
    if ask == "largest":
        ans, text = ds[-1], f"What is the largest prime number that divides {n} exactly?"
    else:
        ans, text = sum(fs), f"Write {n} as a product of prime numbers (for example, 12 is 2 x 2 x 3). Add up the primes in that product, counting a prime as many times as it appears. What is the sum?"
    return Built(text, {"n": n, "ask": ask}, str(ans), "number", None)
