# ruff: noqa: E501
"""C1 batch 1, family "lists" (existing family): three procedures over a list literal.

Strict procedures: ``sieve_marking`` the sieve of Eratosthenes marking pass (strike the multiples of each unstruck index) over a flag list;
``binary_search`` repeated halving of an interval of a sorted list; ``merge_two_sorted`` the two-pointer comparison loop of merge sort.
"""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, S, V, batch, finish, names


@batch("lists")
def sieve_marking(level: int, r: random.Random) -> Built:
    """Sieve marking pass over a literal 0/1 flag list (not necessarily the usual all-ones start, so no prime table helps): for i from 2:
    if flags[i] is 1, strike flags[j] = 0 for j = start(i), start(i) + i, ... below n, with start(i) = i * i, i + i or 3 * i (stated in the
    code). Shapes: how many flags remain 1, the sum of the indices that remain 1, how many strike writes were executed (re-strikes count). 10 to 38 flags."""
    fl, i, j, k, tot = names(r, 5)
    n = (10, 13, 17, 22, 27, 32, 38)[level]
    flags = [1 if r.random() < 0.75 else 0 for _ in range(n)]
    start = r.choice((B("*", V(i), V(i)), B("+", V(i), V(i)), B("*", N(3), V(i))))
    shape = r.choice(("count", "indexsum", "writes"))
    strike: list[list] = [["setidx", fl, V(j), N(0)], ["aug", j, "+", V(i)]]
    if shape == "writes":
        strike.insert(0, ["aug", tot, "+", N(1)])
    prog: list[list] = [["set", fl, LIST(flags)]]
    if shape != "count":
        prog.append(["set", tot, N(0)])
    prog += [["for", i, N(2), N(n), 1, [["if", C("==", IDX(V(fl), V(i)), N(1)), [["set", j, start], ["while", C("<", V(j), N(n)), strike]], []]]]]
    if shape == "count":
        prog.append(["print", ["call", "sum", V(fl)]])
    elif shape == "indexsum":
        prog += [["for", k, N(0), N(n), 1, [["if", C("==", IDX(V(fl), V(k)), N(1)), [["aug", tot, "+", V(k)]], []]]], ["print", V(tot)]]
    else:
        prog.append(["print", V(tot)])
    return finish(prog)


@batch("lists")
def binary_search(level: int, r: random.Random) -> Built:
    """Binary search on a sorted list of distinct integers, in one of two stated styles: closed interval (lo <= hi, stop when found) or
    half-open lower bound (lo < hi, hi = mid). Shapes: the sum of the probed values, the index probed last, the string of moves made (one
    letter per probe: l when the probe was below the target and lo moved up, r when it was above and hi moved down, h when it hit the
    target). The target is in the list about half the time. The list has 5 to 45 entries."""
    xs, t, lo, hi, mid, cnt = names(r, 6)
    n = (5, 7, 10, 15, 22, 31, 45)[level]
    vals = sorted(r.sample(range(1, 3 * n + 12), n))
    target = r.choice(vals) if r.random() < 0.5 else r.randint(0, 3 * n + 12)
    style = r.choice(("closed", "half"))
    shape = r.choice(("sum", "last", "path"))

    def mark(letter: str) -> list[list]:
        return [["set", cnt, B("+", V(cnt), S(letter))]] if shape == "path" else []

    probe: list[list] = [["set", mid, B("//", B("+", V(lo), V(hi)), N(2))]]
    if shape == "sum":
        probe.append(["aug", cnt, "+", IDX(V(xs), V(mid))])
    elif shape == "last":
        probe.append(["set", cnt, V(mid)])
    below = C("<", IDX(V(xs), V(mid)), V(t))
    if style == "closed":
        hit: list[list] = [*mark("h"), ["set", lo, B("+", V(hi), N(1))]]
        loop = ["while", C("<=", V(lo), V(hi)), [*probe, ["if", C("==", IDX(V(xs), V(mid)), V(t)), hit,
                [["if", below, [*mark("l"), ["set", lo, B("+", V(mid), N(1))]], [*mark("r"), ["set", hi, B("-", V(mid), N(1))]]]]]]]
        hi0: list = B("-", ["call", "len", V(xs)], N(1))
    else:
        loop = ["while", C("<", V(lo), V(hi)), [*probe, ["if", below, [*mark("l"), ["set", lo, B("+", V(mid), N(1))]], [*mark("r"), ["set", hi, V(mid)]]]]]
        hi0 = ["call", "len", V(xs)]
    prog = [["set", xs, LIST(vals)], ["set", t, N(target)], ["set", lo, N(0)], ["set", hi, hi0], ["set", cnt, S("") if shape == "path" else N(0)], loop, ["print", V(cnt)]]
    return finish(prog)


@batch("lists")
def merge_two_sorted(level: int, r: random.Random) -> Built:
    """The comparison loop of merging two sorted lists with two read positions: while both lists have a next element, move the smaller (the
    left one when equal, or when 'strictly less' is the stated test, the right one) to the output. Shapes: the number of comparisons, the
    output list built so far when one list runs out (the leftover is NOT appended), the number of times the source list changed. Values
    repeat across the two lists, so ties matter."""
    a, b, i, j, out, cnt, src = names(r, 7)
    na, nb = r.randint(3 + level // 2, 4 + level), r.randint(3 + level // 2, 4 + level)
    hi = max(na, nb) + 3 + level
    la, lb = sorted(r.randint(1, hi) for _ in range(na)), sorted(r.randint(1, hi) for _ in range(nb))
    cmp_op = r.choice(("<=", "<"))
    shape = r.choice(("cmp", "out", "switch"))
    take_a: list[list] = [["append", out, IDX(V(a), V(i))], ["aug", i, "+", N(1)]]
    take_b: list[list] = [["append", out, IDX(V(b), V(j))], ["aug", j, "+", N(1)]]
    if shape == "cmp":
        take_a.insert(0, ["aug", cnt, "+", N(1)])
        take_b.insert(0, ["aug", cnt, "+", N(1)])
    elif shape == "switch":
        take_a = [["if", C("!=", V(src), N(0)), [["aug", cnt, "+", N(1)], ["set", src, N(0)]], []], *take_a]
        take_b = [["if", C("!=", V(src), N(1)), [["aug", cnt, "+", N(1)], ["set", src, N(1)]], []], *take_b]
    prog: list[list] = [["set", a, LIST(la)], ["set", b, LIST(lb)], ["set", i, N(0)], ["set", j, N(0)], ["set", out, ["list"]]]
    if shape != "out":
        prog.append(["set", cnt, N(0)])
    if shape == "switch":
        prog.append(["set", src, N(-1)])
    prog += [["while", AND(C("<", V(i), ["call", "len", V(a)]), C("<", V(j), ["call", "len", V(b)])), [["if", C(cmp_op, IDX(V(a), V(i)), IDX(V(b), V(j))), take_a, take_b]]],
                        ["print", V(out) if shape == "out" else V(cnt)]]
    return finish(prog)
