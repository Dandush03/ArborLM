# ruff: noqa: E501
"""C1, code tracing (output prediction): small deterministic Python programs from a typed grammar (ADR-0033 6.2, 6.3).

Each lineage is a hand-written program-construction rule. The program tree (see ``c1grammar``) is rendered to
source, and the answer is what the locked interpreter prints. The question is that one printed line. No imports, no
input, bounded loops, exactly one print. Model-written code is never executed anywhere in M0.
"""

from __future__ import annotations

import random
from typing import Any

from studies.m0.c1grammar import render, run_inprocess
from studies.m0.core import Built, Retry, lineage
from studies.m0.vocab import PSEUDO

VARS = ["a", "b", "c", "d", "e", "m", "n", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "total", "count", "acc", "res", "val", "cur", "best", "out", "k", "j"]
FUNCS = ["f", "g", "h", "calc", "step", "mix", "score", "shift"]
LETTERS = "abcdefghmnopqrstuvwxyz"

N = lambda v: ["n", v]  # noqa: E731
S = lambda v: ["s", v]  # noqa: E731
V = lambda v: ["v", v]  # noqa: E731
B = lambda op, a, b: ["b", op, a, b]  # noqa: E731
C = lambda op, a, b: ["c", op, a, b]  # noqa: E731


def _finish(prog: list[list], evalid: str = "C1") -> Built:
    src = render(prog)
    try:
        ans = run_inprocess(src)
    except (ZeroDivisionError, IndexError, ValueError, TypeError, KeyError):
        raise Retry from None
    if ans != ans.lower() or ans != ans.strip() or "  " in ans or ans == "" or ans.endswith("."):
        raise Retry  # the answer must be unchanged by the scorer's normalisation
    q = f"Here is a Python program.\n\n{src}\n\nWhat exactly does it print? It prints a single line."
    return Built(q, {"program": prog}, ans, "line", None)


def _names(r: random.Random, k: int) -> list[str]:
    return r.sample(VARS, k)


@lineage("C1", "loops")
def loop_sum(level: int, r: random.Random) -> Built:
    acc, i = _names(r, 2)
    start = r.randint(0, 5)
    stop = start + r.randint(6, 12) + 4 * level
    step = r.choice((1, 1, 2, 3))
    m = r.randint(2, 5)
    rem = r.randrange(m)
    c = r.randint(1, 5)
    cmp_op = r.choice(("==", "!="))
    body: list[list] = [["if", C(cmp_op, B("%", V(i), N(m)), N(rem)), [["aug", acc, r.choice("+-"), B("*", V(i), N(c))]],
                         [["aug", acc, "+", N(r.randint(0, 2))]] if level >= 2 else []]]
    prog = [["set", acc, N(r.randint(0, 9))], ["for", i, N(start), N(stop), step, body], ["print", V(acc)]]
    return _finish(prog)


@lineage("C1", "while")
def while_counter(level: int, r: random.Random) -> Built:
    x, k = _names(r, 2)
    shape = r.choice(("grow", "collatz", "shrink"))
    if shape == "grow":
        prog = [["set", x, N(r.randint(1, 4))], ["set", k, N(0)],
                ["while", C("<", V(x), N(r.randint(50, 400 * (level + 1)))), [["set", x, B("+", B("*", V(x), N(r.randint(2, 3))), N(r.randint(1, 5)))], ["aug", k, "+", N(1)]]],
                ["print", V(k)]]
    elif shape == "collatz":
        prog = [["set", x, N(r.randint(3, 20 + 10 * level))], ["set", k, N(0)],
                ["while", C("!=", V(x), N(1)), [["if", C("==", B("%", V(x), N(2)), N(0)), [["set", x, B("//", V(x), N(2))]], [["set", x, B("+", B("*", V(x), N(3)), N(1))]]], ["aug", k, "+", N(1)]]],
                ["print", V(k)]]
    else:
        d = r.randint(3, 9)
        prog = [["set", x, N(r.randint(40, 200 + 100 * level))],
                ["while", C(">", V(x), N(r.randint(3, 30))), [["aug", x, "-", N(d)]]],
                ["print", V(x)]]
    return _finish(prog)


@lineage("C1", "strings")
def string_build(level: int, r: random.Random) -> Built:
    s, i = _names(r, 2)
    l1, l2, l3 = r.sample(LETTERS, 3)
    m = r.randint(2, 4)
    a = r.randint(0, 3)
    b = a + r.randint(4, 8) + 2 * level
    inner: list[list] = [["set", s, B("+", V(s), S(l2))]]
    if level >= 2:
        inner = [["if", C("==", B("%", V(i), N(m + 1)), N(1)), [["set", s, B("+", V(s), S(l3))]], inner]]
    body = [["if", C("==", B("%", V(i), N(m)), N(0)), [["set", s, B("+", V(s), S(l1))]], inner]]
    tail = r.choice(("s", "len", "rev"))
    last = {"s": ["print", V(s)], "len": ["print", ["call", "len", V(s)]], "rev": ["print", ["slice", V(s), None, None, N(-1)]]}[tail]
    prog = [["set", s, S("")], ["for", i, N(a), N(b), 1, body], last]
    return _finish(prog)


@lineage("C1", "string_methods")
def string_methods(level: int, r: random.Random) -> Built:
    s = _names(r, 1)[0]
    w = r.choice(PSEUDO)
    expr: list = S(w)
    for _ in range(1 + level):
        op = r.choice(("upper", "replace", "rev", "add", "twice", "lower", "slice"))
        if op == "upper":
            expr = ["m", expr, "upper"]
        elif op == "lower":
            expr = ["m", expr, "lower"]
        elif op == "replace":
            expr = ["m", expr, "replace", S(r.choice(LETTERS)), S(r.choice(LETTERS) * r.randint(1, 2))]
        elif op == "rev":
            expr = ["slice", expr, None, None, N(-1)]
        elif op == "add":
            expr = B("+", expr, S(r.choice(LETTERS) + r.choice(LETTERS)))
        elif op == "twice":
            expr = B("*", expr, N(2))
        else:
            expr = ["slice", expr, N(r.randint(0, 2)), None, None]
    final = r.choice(("text", "len", "count"))
    tail = {"text": ["m", V(s), "lower"], "len": ["call", "len", V(s)], "count": ["m", V(s), "count", S(r.choice(LETTERS))]}[final]
    prog = [["set", s, expr], ["print", tail]]
    return _finish(prog)


@lineage("C1", "functions")
def func_branch(level: int, r: random.Random) -> Built:
    f = r.choice(FUNCS)
    x = _names(r, 1)[0]
    t = r.randint(2, 12)
    a, b, c = r.randint(2, 5), r.randint(1, 9), r.randint(1, 9)
    other: list[list] = [["ret", B("+", V(x), N(c))]]
    if level >= 2:
        other = [["if", C("==", B("%", V(x), N(2)), N(0)), [["ret", B("//", V(x), N(2))]], other]]
    fn = ["def", f, [x], [["if", C(">", V(x), N(t)), [["ret", B("-", B("*", V(x), N(a)), N(b))]], other]]]
    calls = [["call", f, N(r.randint(0, 20))] for _ in range(2 + (level >= 3))]
    total = calls[0]
    for cl in calls[1:]:
        total = B(r.choice("+-"), total, cl)
    return _finish([fn, ["print", total]])


@lineage("C1", "functions")
def func_compose(level: int, r: random.Random) -> Built:
    f, g, h = r.sample(FUNCS, 3)
    x = _names(r, 1)[0]
    a, b, c, m = r.randint(2, 4), r.randint(1, 9), r.randint(1, 9), r.randint(3, 9)
    defs: list[list] = [["def", f, [x], [["ret", B("+", B("*", V(x), N(a)), N(b))]]]]
    defs.append(["def", g, [x], [["ret", B(r.choice("+-"), ["call", f, ["call", f, V(x)]], N(c))]]])
    top = g
    if level >= 3:
        defs.append(["def", h, [x], [["ret", B("%", ["call", g, V(x)], N(m))]]])
        top = h
    return _finish([*defs, ["print", ["call", top, N(r.randint(-3, 9))]]])


@lineage("C1", "lists")
def list_build(level: int, r: random.Random) -> Built:
    xs, i = _names(r, 2)
    n = r.randint(4, 7) + level
    m = r.randint(3, 9)
    expr = B("%", B("*", V(i), V(i)), N(m)) if r.random() < 0.5 else B("%", B("+", B("*", V(i), N(r.randint(2, 5))), N(r.randint(0, 6))), N(m))
    last = r.choice((["print", ["call", "sum", V(xs)]], ["print", V(xs)], ["print", ["call", "max", V(xs)]]))
    prog = [["set", xs, ["list"]], ["for", i, N(0), N(n), 1, [["append", xs, expr]]], last]
    return _finish(prog)


@lineage("C1", "lists")
def counter_list(level: int, r: random.Random) -> Built:
    data, counts, i = _names(r, 3)
    k = r.randint(2, 4)
    vals = [r.randint(0, 30) for _ in range(5 + 2 * level)]
    idx = B("%", ["idx", V(data), V(i)], N(k))
    prog = [["set", data, ["list", *[N(v) for v in vals]]], ["set", counts, ["list", *[N(0)] * k]],
            ["for", i, N(0), ["call", "len", V(data)], 1, [["setidx", counts, idx, B("+", ["idx", V(counts), idx], N(1))]]],
            ["print", V(counts)]]
    return _finish(prog)


@lineage("C1", "nested")
def nested_pairs(level: int, r: random.Random) -> Built:
    c, i, j = _names(r, 3)
    a, b = r.randint(3, 5 + level), r.randint(3, 5 + level)
    m = r.randint(2, 5)
    kind = r.choice(("mod", "less", "prod"))
    cond = {"mod": C("==", B("%", B("+", V(i), V(j)), N(m)), N(r.randrange(m))), "less": C("<", V(i), V(j)),
            "prod": C(">", B("*", V(i), V(j)), N(r.randint(2, 8)))}[kind]
    inc: list = N(1) if r.random() < 0.5 else B("+", V(i), V(j))
    prog = [["set", c, N(0)], ["for", i, N(0), N(a), 1, [["for", j, N(0), N(b), 1, [["if", cond, [["aug", c, "+", inc]], []]]]]], ["print", V(c)]]
    return _finish(prog)


@lineage("C1", "swaps")
def bubble_pass(level: int, r: random.Random) -> Built:
    xs, i, t = _names(r, 3)
    vals = [r.randint(1, 40) for _ in range(5 + level)]
    passes = 1 + level // 2
    swap = [["set", t, ["idx", V(xs), V(i)]], ["setidx", xs, V(i), ["idx", V(xs), B("+", V(i), N(1))]], ["setidx", xs, B("+", V(i), N(1)), V(t)]]
    cmp_op = r.choice((">", "<"))
    one_pass = ["for", i, N(0), B("-", ["call", "len", V(xs)], N(1)), 1,
                [["if", C(cmp_op, ["idx", V(xs), V(i)], ["idx", V(xs), B("+", V(i), N(1))]), swap, []]]]
    prog: list[list] = [["set", xs, ["list", *[N(v) for v in vals]]]]
    for _ in range(passes):
        prog.append(one_pass)
    prog.append(["print", V(xs)])
    return _finish(prog)


@lineage("C1", "conditionals")
def cond_chain(level: int, r: random.Random) -> Built:
    a, b, i = _names(r, 3)
    k = 2 + level
    body = [["if", C(">", V(a), V(b)), [["set", a, B("-", V(a), V(b))]],
             [["if", C("==", V(a), V(b)), [["set", a, B("*", V(a), N(2))]], [["set", b, B("-", V(b), V(a))]]]]]]
    if level >= 3:
        body.append(["if", C(">", B("+", V(a), V(b)), N(r.randint(20, 40))), [["set", b, B("//", V(b), N(2))]], []])
    tail = r.choice((["print", V(a)], ["print", V(b)], ["print", B("+", V(a), V(b))]))
    prog = [["set", a, N(r.randint(5, 30))], ["set", b, N(r.randint(5, 30))], ["for", i, N(0), N(k), 1, body], tail]
    return _finish(prog)


@lineage("C1", "minmax")
def minmax_track(level: int, r: random.Random) -> Built:
    xs, best, pos, i = _names(r, 4)
    vals = [r.randint(1, 60) for _ in range(5 + level)]
    op = r.choice((">", "<"))
    body = [["if", C(op, ["idx", V(xs), V(i)], V(best)), [["set", best, ["idx", V(xs), V(i)]], ["set", pos, V(i)]], []]]
    last = r.choice((["print", V(pos)], ["print", V(best)], ["print", B("+", V(best), V(pos))]))
    prog = [["set", xs, ["list", *[N(v) for v in vals]]], ["set", best, ["idx", V(xs), N(0)]], ["set", pos, N(0)],
            ["for", i, N(1), ["call", "len", V(xs)], 1, body], last]
    return _finish(prog)


@lineage("C1", "slices")
def slices(level: int, r: random.Random) -> Built:
    s = _names(r, 1)[0]
    if r.random() < 0.5:
        w = "".join(r.choice(PSEUDO) for _ in range(1 + level // 2 + 1))
        base: list = S(w)
        n = len(w)
    else:
        vals = [r.randint(1, 50) for _ in range(6 + level)]
        base = ["list", *[N(v) for v in vals]]
        n = len(vals)

    def cut() -> list:
        a = r.choice((None, N(r.randint(0, n - 1)), N(-r.randint(1, n))))
        b = r.choice((None, N(r.randint(1, n)), N(-r.randint(1, n))))
        c = r.choice((None, N(2), N(-1), N(3), N(-2)))
        return ["slice", V(s), a, b, c]

    first, second = cut(), cut()
    tail: list = B("+", first, second)
    if base[0] == "list" and r.random() < 0.5:
        tail = ["call", "sum", first]
    prog = [["set", s, base], ["print", tail]]
    return _finish(prog)


@lineage("C1", "accumulators")
def fib_like(level: int, r: random.Random) -> Built:
    a, b, t, i = _names(r, 4)
    n = r.randint(4, 8) + 3 * level
    m = r.choice((None, r.randint(7, 50)))
    nxt: Any = B("+", V(a), V(b))
    if m is not None:
        nxt = B("%", nxt, N(m))
    body = [["set", t, nxt], ["set", a, V(b)], ["set", b, V(t)]]
    prog = [["set", a, N(r.randint(0, 4))], ["set", b, N(r.randint(1, 5))], ["for", i, N(0), N(n), 1, body], ["print", r.choice((V(a), V(b)))]]
    return _finish(prog)
