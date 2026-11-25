# ruff: noqa: E501
"""C1 batch 1, family "while" (existing family): three number procedures that peel or halve a number in a while loop.

Strict procedures: ``euclid_gcd`` the remainder form of Euclid's algorithm; ``digit_peel`` extraction of the digits of a number by
remainder and integer division; ``fast_power`` modular exponentiation by repeated squaring (binary method).
"""

from __future__ import annotations

import math
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import B, C, N, V, batch, finish, names


@batch("while")
def euclid_gcd(level: int, r: random.Random) -> Built:
    """Euclid's algorithm in the remainder form (a, b -> b, a % b until b is 0). Shapes: the value left in a, the sum of the quotients
    a // b over the rounds, or the sum of the remainders. Input scale grows with the level (and so does the least number of rounds); the
    pair is built from a chosen divisor so that the gcd is spread (not mostly 1) and, for the printed-gcd shape, is never one of the two
    literals."""
    a, b, t, k = names(r, 4)
    hi = (20, 22, 26, 32, 42, 56, 80)[level]
    g = r.randint(1, 6 + level)
    x, y = g * r.randint(2, hi), g * r.randint(2, hi)
    if x == y:
        raise Retry
    shape = r.choice(("gcd", "quot", "rsum"))
    if shape == "gcd" and math.gcd(x, y) in (x, y):
        raise Retry
    p, q, rounds = x, y, 0
    while q:
        p, q, rounds = q, p % q, rounds + 1
    if rounds < 2 + level // 2:  # the number of rounds grows with the level
        raise Retry
    body: list[list] = []
    if shape == "quot":
        body.append(["aug", k, "+", B("//", V(a), V(b))])
    body += [["set", t, B("%", V(a), V(b))], ["set", a, V(b)], ["set", b, V(t)]]
    if shape == "rsum":
        body.append(["aug", k, "+", V(t)])
    prog: list[list] = [["set", a, N(x)], ["set", b, N(y)]]
    if shape != "gcd":
        prog.append(["set", k, N(0)])
    prog += [["while", C("!=", V(b), N(0)), body], ["print", V(a) if shape == "gcd" else V(k)]]
    return finish(prog)


@batch("while")
def digit_peel(level: int, r: random.Random) -> Built:
    """Digit extraction: repeat d = n % base, n = n // base until n is 0, folding the digits into one accumulator. Shapes: digit sum,
    the digits read back in reverse order as a decimal number (leading zeros vanish; base below 10 only), the count of digits at or above a threshold, the sum
    of the even digits. The base is 10 or a smaller base, the number is given in decimal."""
    n, d, acc = names(r, 3)
    shape = r.choice(("sum", "rev", "countge", "even"))
    base = 10 if (r.random() < 0.55 and shape != "rev") else r.randint(2, 9)  # a base-10 reversal would be the literal read backwards
    nd = 2 + level if base == 10 else 3 + level + (2 if base < 5 else 0)
    digs = [r.randint(1, base - 1)] + [r.randint(0, base - 1) for _ in range(nd - 1)]
    x = 0
    for dg in digs:
        x = x * base + dg
    th = r.randint(max(1, base // 3), max(1, base - 2))
    fold: list[list]
    if shape == "sum":
        fold = [["aug", acc, "+", V(d)]]
    elif shape == "rev":
        fold = [["set", acc, B("+", B("*", V(acc), N(10)), V(d))]]
    elif shape == "countge":
        fold = [["if", C(">=", V(d), N(th)), [["aug", acc, "+", N(1)]], []]]
    else:
        fold = [["if", C("==", B("%", V(d), N(2)), N(0)), [["aug", acc, "+", V(d)]], []]]
    body = [["set", d, B("%", V(n), N(base))], *fold, ["set", n, B("//", V(n), N(base))]]
    prog: list[list] = [["set", n, N(x)], ["set", acc, N(0)], ["while", C(">", V(n), N(0)), body], ["print", V(acc)]]
    return finish(prog)


@batch("while")
def fast_power(level: int, r: random.Random) -> Built:
    """Modular exponentiation by repeated squaring: while e > 0: if e is odd, res = res * b % m; b = b * b % m; e = e // 2.
    Shapes: the final result, the final value of b, the sum of the values b has when each round starts. The exponent has 2 + level bits."""
    res, b, e, m = names(r, 4)
    mod = r.randint(5, 25 + 10 * level)
    base = r.randint(2, mod + 6)
    if base % mod in (0, 1):
        raise Retry
    bits = 2 + level
    ex = r.randint(2 ** (bits - 1), 2**bits - 1)
    shape = r.choice(("res", "base", "bsum"))
    odd_body: list[list] = [["set", res, B("%", B("*", V(res), V(b)), V(m))]]
    prog: list[list] = [["set", res, N(1)], ["set", b, N(base)], ["set", e, N(ex)], ["set", m, N(mod)]]
    if shape == "bsum":
        prog.append(["set", "tot", N(0)])
    rnd: list[list] = [["aug", "tot", "+", V(b)]] if shape == "bsum" else []
    prog.append(["while", C(">", V(e), N(0)), [*rnd, ["if", C("==", B("%", V(e), N(2)), N(1)), odd_body, []], ["set", b, B("%", B("*", V(b), V(b)), V(m))], ["set", e, B("//", V(e), N(2))]]])
    prog.append(["print", {"res": V(res), "base": V(b), "bsum": V("tot")}[shape]])
    return finish(prog)
