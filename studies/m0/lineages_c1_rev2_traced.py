# ruff: noqa: E501
"""C1 batch 1, revision 2: PROPOSED traced-state shapes (audit finding: the old shapes of insertion_sort, fast_power, euclid_gcd's gcd shape,
kadane_scan's best shape and bracket_matching are answerable by a closed form or the standard algorithm without following the program).

Per the coordinator's instruction these are ADDITIONAL shapes, marked PROPOSED, not a redesign: whether the formula-answerable old shapes stay
is the human lead's decision. Each asks for a quantity that is read off the program's state at a stated point or counts one named branch:
an intermediate variable after a stated number of rounds, or the number of times one branch ran. They are shapes of the same clusters as
the lineages they extend (see ``lineages_c1_clusters``), not new lineages. Note: some of these quantities are still functions of the input
(the proposal is about what the reader must follow, not a claim that no formula exists); the shortcut battery reports them like any shape.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, S, V, finish, names
from studies.m0.lineages_c1_rev2 import call, rev2


@rev2("swaps", proposed=True)
def insertion_sort_traced(level: int, r: random.Random) -> Built:
    """PROPOSED shapes of insertion sort (same program as ``insertion_sort``, K rounds, ascending or descending, strict or not): the value of the
    hole index j after the inner while loop of the LAST round run; the sum, over the rounds run, of the hole index j after the inner loop (a sum of an intermediate variable)."""
    xs, i, j, key, act = names(r, 5)
    n = 4 + level
    vals = [r.randint(1, 3 * n) for _ in range(n)]
    k_rounds = r.randint(3, n)
    op = r.choice((">", "<", ">=", "<="))
    shape = r.choice(("hole", "holesum"))
    inner: list[list] = [["setidx", xs, B("+", V(j), N(1)), IDX(V(xs), V(j))], ["set", j, B("-", V(j), N(1))]]
    body: list[list] = [["set", key, IDX(V(xs), V(i))], ["set", j, B("-", V(i), N(1))], ["while", AND(C(">=", V(j), N(0)), C(op, IDX(V(xs), V(j)), V(key))), inner]]
    if shape == "holesum":
        body.append(["aug", act, "+", V(j)])
    body.append(["setidx", xs, B("+", V(j), N(1)), V(key)])
    prog: list[list] = [["set", xs, LIST(vals)]]
    if shape == "holesum":
        prog.append(["set", act, N(0)])
    prog.append(["for", i, N(1), N(k_rounds), 1, body])
    prog.append(["print", V(j) if shape == "hole" else V(act)])
    return finish(prog)


@rev2("while", proposed=True)
def fast_power_traced(level: int, r: random.Random) -> Built:
    """PROPOSED shapes of square-and-multiply (the program of ``fast_power`` with a round counter): the result after a stated number s of rounds
    (the loop also stops when it has run s rounds, 1 <= s < the number of bits); the sum of the values b has at the start of the rounds in which the
    exponent bit was 1 (a sum over one branch)."""
    res, b, e, m, it, wraps = names(r, 6)
    mod = r.randint(60, 300 + 100 * level)  # large moduli: a small one makes b^(2^k) settle, so the value after s rounds would already be the final result
    base = r.randint(2, mod + 6)
    if base % mod in (0, 1):
        raise Retry
    bits = 3 + level
    ex = r.randint(2 ** (bits - 1), 2**bits - 1)
    shape = r.choice(("res_after", "oddsum"))
    s = r.randint(1, bits - 1)
    cond = AND(C(">", V(e), N(0)), C("<", V(it), N(s))) if shape == "res_after" else C(">", V(e), N(0))
    odd_add: list[list] = [["aug", wraps, "+", V(b)]] if shape == "oddsum" else []
    prog: list[list] = [["set", res, N(1)], ["set", b, N(base)], ["set", e, N(ex)], ["set", m, N(mod)], ["set", it, N(0)]]
    if shape == "oddsum":
        prog.append(["set", wraps, N(0)])
    prog.append(["while", cond, [["if", C("==", B("%", V(e), N(2)), N(1)), [*odd_add, ["set", res, B("%", B("*", V(res), V(b)), V(m))]], []], ["set", b, B("%", B("*", V(b), V(b)), V(m))], ["set", e, B("//", V(e), N(2))], ["aug", it, "+", N(1)]]])
    prog.append(["print", V(res) if shape == "res_after" else V(wraps)])
    return finish(prog)


@rev2("while", proposed=True)
def euclid_gcd_traced(level: int, r: random.Random) -> Built:
    """PROPOSED shapes of Euclid's remainder algorithm (as ``euclid_gcd`` with a round counter): the pair (a, b) after a stated number R of rounds,
    written 'a b' (1 <= R < the number of rounds, so it is not the gcd); the sum of the quotients a // b over the rounds in which the quotient was at least 2."""
    a, b, t, it, cnt = names(r, 5)
    hi = (20, 22, 26, 32, 42, 56, 80)[level]
    g = r.randint(1, 6 + level)
    x, y = g * r.randint(2, hi), g * r.randint(2, hi)
    if x == y:
        raise Retry
    p, q, rounds = x, y, 0
    while q:
        p, q, rounds = q, p % q, rounds + 1
    if rounds < 3 + level // 2:
        raise Retry
    shape = r.choice(("state", "bigq"))
    rr = r.randint(1, rounds - 1)
    cond = AND(C("!=", V(b), N(0)), C("<", V(it), N(rr))) if shape == "state" else C("!=", V(b), N(0))
    body: list[list] = []
    if shape == "bigq":
        body.append(["if", C(">=", B("//", V(a), V(b)), N(2)), [["aug", cnt, "+", B("//", V(a), V(b))]], []])
    body += [["set", t, B("%", V(a), V(b))], ["set", a, V(b)], ["set", b, V(t)], ["aug", it, "+", N(1)]]
    prog: list[list] = [["set", a, N(x)], ["set", b, N(y)], ["set", it, N(0)]]
    if shape == "bigq":
        prog.append(["set", cnt, N(0)])
    prog.append(["while", cond, body])
    prog.append(["print", B("+", B("+", call("str", V(a)), S(" ")), call("str", V(b))) if shape == "state" else V(cnt)])
    return finish(prog)


@rev2("minmax", proposed=True)
def kadane_scan_traced(level: int, r: random.Random) -> Built:
    """PROPOSED shapes of the maximum-subarray scan (as ``kadane_scan``): the value of cur after the first p elements (the loop stops at the
    stated p, 3 <= p < n); the sum of the indices i at which cur was negative before the step (the restart branch ran)."""
    xs, cur, best, i, cnt = names(r, 5)
    n = 6 + 2 * level
    vals = [-r.randint(1, 9) if r.random() < 0.4 else r.randint(1, 9) for _ in range(n)]
    shape = r.choice(("cur_at", "restarts"))
    stop = r.randint(3, n - 1) if shape == "cur_at" else n
    body: list[list] = []
    if shape == "restarts":
        body.append(["if", C("<", V(cur), N(0)), [["aug", cnt, "+", V(i)]], []])
    body += [["set", cur, call("max", B("+", V(cur), IDX(V(xs), V(i))), IDX(V(xs), V(i)))], ["set", best, call("max", V(best), V(cur))]]
    prog: list[list] = [["set", xs, LIST(vals)], ["set", cur, IDX(V(xs), N(0))], ["set", best, V(cur)]]
    if shape == "restarts":
        prog.append(["set", cnt, N(0)])
    prog.append(["for", i, N(1), N(stop), 1, body])
    prog.append(["print", V(cur) if shape == "cur_at" else V(cnt)])
    return finish(prog)


@rev2("stacks", proposed=True)
def bracket_matching_traced(level: int, r: random.Random) -> Built:
    """PROPOSED shapes of the bracket stack (as ``bracket_matching``): the stack height after the first p characters (the loop stops at the stated
    p, 3 <= p < the length); the sum of the positions of the closing brackets that popped (matched), a sum over one branch."""
    s, st, sp, pops, ch, i = names(r, 6)
    n = (6, 7, 9, 12, 15, 18, 21)[level]
    opens: list[int] = []
    depth, text = 0, ""
    for _ in range(n):
        if depth == 0 or r.random() < 0.5:
            kind = r.randint(1, 2)
            if depth == 0 and r.random() < 0.15:
                text += ")" if kind == 1 else "]"
            else:
                text += "(" if kind == 1 else "["
                opens.append(kind)
                depth += 1
        else:
            kind = opens.pop() if r.random() < 0.7 else r.randint(1, 2)
            text += ")" if kind == 1 else "]"
            depth -= 1 if depth else 0
    shape = r.choice(("height_at", "pops"))
    stop: list = N(r.randint(3, n - 1)) if shape == "height_at" else call("len", V(s))

    def close(code: int) -> list:
        fail: list[list] = []
        hit: list[list] = [["aug", sp, "-", N(1)]] + ([["aug", pops, "+", V(i)]] if shape == "pops" else [])
        return ["if", AND(C(">", V(sp), N(0)), C("==", IDX(V(st), B("-", V(sp), N(1))), N(code))), hit, fail]

    prog: list[list] = [["set", s, S(text)], ["set", st, ["list"]], ["for", i, N(0), call("len", V(s)), 1, [["append", st, N(0)]]], ["set", sp, N(0)]]
    if shape == "pops":
        prog.append(["set", pops, N(0)])
    loop_body = [["set", ch, IDX(V(s), V(i))],
                 ["if", C("==", V(ch), S("(")), [["setidx", st, V(sp), N(1)], ["aug", sp, "+", N(1)]],
                  [["if", C("==", V(ch), S("[")), [["setidx", st, V(sp), N(2)], ["aug", sp, "+", N(1)]],
                    [["if", C("==", V(ch), S(")")), [close(1)], [close(2)]]]]]]]
    prog.append(["for", i, N(0), stop, 1, loop_body])
    prog.append(["print", V(sp) if shape == "height_at" else V(pops)])
    return finish(prog)
