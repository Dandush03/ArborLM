# ruff: noqa: E501
# The program trees are plain nested lists (the grammar of c1grammar), as in every other C1 lineage module; hence no type parameters on list.
# mypy: disable-error-code="type-arg"
"""C1 fix round 3, number procedures (while loops and conditional chains). See ``lineages_c1_fix3`` for the rules. Superseded: while_counter, euclid_gcd
(gcd and quotient and remainder shapes), cond_chain, fast_power_r2, digit_peel."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import AND, B, C, N, S, V, finish, names
from studies.m0.lineages_c1_fix3 import f3


def _call(fn: str, *args: list) -> list:
    return ["call", fn, *args]


@f3("while", supersedes="C1.while_counter")
def while_counter_f3(level: int, r: random.Random) -> Built:
    """While loops whose printed quantity is loop-carried state with no closed form. Shapes: ``grow`` (x = x * m + x % q + c until x reaches the threshold; prints the
    final x: the remainder term makes the growth factor vary, so neither a logarithm nor a geometric sum gives it); ``collatz`` (the 3x + 1 map; prints the sum of the
    values taken, added before or after the update); ``down`` (halve when even, subtract an ODD d when odd, until x is at most T; prints the sum of the values x takes after each
    step). The old shapes the audit found formula-answerable (the shrink count and the loop count of the growth loop) are gone."""
    x, acc = names(r, 2)
    shape = r.choice(("grow", "collatz", "down"))
    if shape == "grow":
        m, q, c = r.randint(2, 4), r.randint(3, 9), r.randint(1, 9)
        thr = r.randint(40 + 60 * level, 200 + 400 * level)
        prog: list[list] = [["set", x, N(r.randint(1, 9))], ["while", C("<", V(x), N(thr)), [["set", x, B("+", B("+", B("*", V(x), N(m)), B("%", V(x), N(q))), N(c))]]], ["print", V(x)]]
        return finish(prog)
    x0 = r.randint(3, 25 + 20 * level) if shape == "collatz" else r.randint(100 + 50 * level, 400 + 150 * level)
    if shape == "collatz":
        even = [["set", x, B("//", V(x), N(2))]]
        odd = [["set", x, B("+", B("*", V(x), N(3)), N(1))]]
        arms = [["if", C("==", B("%", V(x), N(2)), N(0)), even, odd]] if r.random() < 0.5 else [["if", C("==", B("%", V(x), N(2)), N(1)), odd, even]]
        add = [["aug", acc, "+", V(x)]]
        body = [*add, *arms] if r.random() < 0.5 else [*arms, *add]
        cond = C("!=", V(x), N(1))
    else:
        thr, d = r.randint(3, 12), r.choice((3, 5, 7, 9))  # d odd: an odd x minus d is even, so the two branches alternate (an even d would keep an odd x odd for ever)
        body = [["if", C("==", B("%", V(x), N(2)), N(0)), [["set", x, B("//", V(x), N(2))]], [["set", x, B("-", V(x), N(d))]]], ["aug", acc, "+", V(x)]]
        cond = C(">", V(x), N(thr))
    return finish([["set", x, N(x0)], ["set", acc, N(0)], ["while", cond, body], ["print", V(acc)]])


@f3("while", supersedes="C1.euclid_gcd")
def euclid_gcd_traced_f3(level: int, r: random.Random) -> Built:
    """Euclid's remainder algorithm with a round counter (the audit accepted ``euclid_gcd_traced``; the gcd shape and the quotient and remainder sums of ``euclid_gcd``
    are replaced by it). The loop stops after a stated number R of rounds (1 <= R < the number of rounds, so the pair is not the gcd pair). Shapes: the pair (a, b) after R rounds,
    written 'a b'; the sum of the remainders produced in those R rounds, each multiplied by its round number plus 1, that is 2, 3, ... (for this shape R is from 2 to the number of rounds minus 2: with R = rounds - 1 the plain sum of all remainders was the answer in 0.31-0.34 of items, and with R = 1 the answer was x % y in 0.4-0.67; the unweighted sum also equalled the literal y in 0.19; and with the weight equal to the round number the sum of all remainders was the answer in 0.24 at level 4, because r2 = r3 + r4 when the quotient is 1). At least max(4, 3 + level // 2) rounds are required (validity: the shapes need room). (A first draft summed the quotients that were at least 2 over ALL rounds, which had a most-frequent
    answer of up to 0.18; it is not in this file.) Widened for capacity: larger operands at every level, the loop test ``b != 0`` or ``b > 0``, and two orders of the swap
    statements (all the same algorithm)."""
    a, b, t, it, cnt = names(r, 5)
    hi = (40, 44, 50, 56, 64, 76, 96)[level]
    g = r.randint(1, 6 + level)
    x, y = g * r.randint(2, hi), g * r.randint(2, hi)
    if x == y:
        raise Retry
    p, q, rounds = x, y, 0
    while q:
        p, q, rounds = q, p % q, rounds + 1
    if rounds < max(4, 3 + level // 2):
        raise Retry
    shape = r.choice(("state", "rsum"))
    rr = r.randint(1, rounds - 1) if shape == "state" else r.randint(2, rounds - 2)
    positive = r.random() < 0.5
    test = C(">", V(b), N(0)) if positive else C("!=", V(b), N(0))
    cond = AND(test, C("<", V(it), N(rr)))
    swap = [["set", t, B("%", V(a), V(b))], ["set", a, V(b)], ["set", b, V(t)]] if r.random() < 0.5 else [["set", t, V(b)], ["set", b, B("%", V(a), V(b))], ["set", a, V(t)]]
    body: list[list] = list(swap)
    body.append(["aug", it, "+", N(1)])
    if shape == "rsum":
        body.append(["aug", cnt, "+", B("*", V(b), B("+", V(it), N(1)))])  # after the swap b holds the remainder of this round; weighted by the round number plus 1 (2, 3, ...)
    prog: list[list] = [["set", a, N(x)], ["set", b, N(y)], ["set", it, N(0)]]
    if shape == "rsum":
        prog.append(["set", cnt, N(0)])
    prog.append(["while", cond, body])
    prog.append(["print", B("+", B("+", _call("str", V(a)), S(" ")), _call("str", V(b))) if shape == "state" else V(cnt)])
    return finish(prog)


@f3("conditionals", supersedes="C1.cond_chain")
def cond_chain_f3(level: int, r: random.Random) -> Built:
    """As ``cond_chain`` (a fixed number 2 + level + (0 to 2) of rounds of: a > b -> a -= b; a == b -> a *= k (k stated, 2 to 4); else b -= a; from level 3 also: if a + b exceeds a stated number (20 to 60),
    b //= 2) with the printed quantity changed: the old shapes printed a, b or a + b after the rounds, and the answer was the gcd of the two literals (or twice it) in
    0.33-0.71 of the items because the rounds had converged. Now each round adds a value to an accumulator and the accumulator is printed: the sum of a after each round,
    the sum of b after each round, or the sum of a - b after each round. No convergence is needed or relied on. Operands are 15 to 60 + 40 * level."""
    a, b, i, tot = names(r, 4)
    hi = 60 + 40 * level
    body: list[list] = [["if", C(">", V(a), V(b)), [["set", a, B("-", V(a), V(b))]], [["if", C("==", V(a), V(b)), [["set", a, B("*", V(a), N(r.randint(2, 4)))]], [["set", b, B("-", V(b), V(a))]]]]]]
    if level >= 3:
        body.append(["if", C(">", B("+", V(a), V(b)), N(r.randint(20, 60))), [["set", b, B("//", V(b), N(2))]], []])
    add = r.choice((V(a), V(b), B("-", V(a), V(b))))
    body.append(["aug", tot, "+", add])
    return finish([["set", a, N(r.randint(15, hi))], ["set", b, N(r.randint(15, hi))], ["set", tot, N(0)], ["for", i, N(0), N(2 + level + r.randint(0, 2)), 1, body], ["print", V(tot)]])


@f3("while", supersedes="C1.fast_power_r2", variant="the squaring step is b = (b * b + c) % m with a stated c from 1 to 9; with c = 0 it is square-and-multiply")
def fast_power_f3(level: int, r: random.Random) -> Built:
    """VARIANT of binary exponentiation: while e > 0: if e is odd, res = res * b % m; b = (b * b + c) % m (c stated in the code, 1 to 9); e = e // 2. The control
    skeleton (the exponent's bits drive a multiply and a squaring) is that of ``fast_power``; the added c makes b follow the iterates of a quadratic map, so no pow()
    gives res, b, or a sum of b (the audit's formulas, all of them pow terms, no longer apply). Shapes: the final res, the final b, the sum of the values b has when each
    round starts. Modulus 40 to 200 + 60 * level, exponent with 3 + level bits. PENDING LEAD REVIEW: whether a program with the added term still counts as the
    fast_power procedure (it is the only way found to remove the closed form while keeping the loop)."""
    res, b, e, m, tot = names(r, 5)
    mod = r.randint(40, 200 + 60 * level)
    base = r.randint(2, mod - 1)
    c = r.randint(1, 9)
    bits = 3 + level
    ex = r.randint(2 ** (bits - 1), 2**bits - 1)
    shape = r.choice(("res", "base", "bsum"))
    rnd: list[list] = [["aug", tot, "+", V(b)]] if shape == "bsum" else []
    prog: list[list] = [["set", res, N(1)], ["set", b, N(base)], ["set", e, N(ex)], ["set", m, N(mod)]]
    if shape == "bsum":
        prog.append(["set", tot, N(0)])
    prog.append(["while", C(">", V(e), N(0)), [*rnd, ["if", C("==", B("%", V(e), N(2)), N(1)), [["set", res, B("%", B("*", V(res), V(b)), V(m))]], []], ["set", b, B("%", B("+", B("*", V(b), V(b)), N(c)), V(m))], ["set", e, B("//", V(e), N(2))]]])
    prog.append(["print", {"res": V(res), "base": V(b), "bsum": V(tot)}[shape]])
    return finish(prog)


@f3("while", supersedes="C1.digit_peel")
def digit_peel_f3(level: int, r: random.Random) -> Built:
    """Digit extraction (d = n % base, n = n // base until n is 0) with the base never 10 (for base 10 the digits are the written literal: the audit's tell, 44 % of the
    items), the number written in decimal, and folds whose values are wide: ``fold`` (acc = acc * k + d with a stated k from 2 to 12: the digits read back in reverse as a
    number in base k) and ``wsum`` (acc += d * position, position counted from 1). The old digit sum, even-digit sum and threshold count (small integers) are gone.
    Base 3 to 9; 4 + level digits, 2 more below base 5."""
    n, d, acc, pos = names(r, 4)
    base = r.randint(3, 9)
    nd = 4 + level + (2 if base < 5 else 0)
    digs = [r.randint(1, base - 1)] + [r.randint(0, base - 1) for _ in range(nd - 1)]
    x = 0
    for dg in digs:
        x = x * base + dg
    shape = r.choice(("fold", "fold", "wsum"))
    peel: list[list] = [["set", d, B("%", V(n), N(base))]]
    if shape == "fold":
        peel.append(["set", acc, B("+", B("*", V(acc), N(r.randint(2, 12))), V(d))])
        extra: list[list] = []
    else:
        peel.append(["aug", acc, "+", B("*", V(d), V(pos))])
        extra = [["aug", pos, "+", N(1)]]
    body = [*peel, *extra, ["set", n, B("//", V(n), N(base))]]
    cond = C(">", V(n), N(0)) if r.random() < 0.5 else C("!=", V(n), N(0))
    prog: list[list] = [["set", n, N(x)], ["set", acc, N(0)]]
    if shape == "wsum":
        prog.append(["set", pos, N(1)])
    prog += [["while", cond, body], ["print", V(acc)]]
    return finish(prog)
