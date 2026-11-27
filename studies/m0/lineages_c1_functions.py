# ruff: noqa: E501
"""C1 batch 1, family "functions" (existing family): recursion.

Strict procedure: ``recursive_calls`` evaluation of a recursive function by expanding its call tree (a function that calls itself, or a
partner, on smaller arguments until a base case). The existing ``func_branch`` and ``func_compose`` are non-recursive calls.
"""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_c1 import FUNCS
from studies.m0.lineages_c1_common import IDX, LIST, B, C, N, V, batch, finish, names


@batch("functions")
def recursive_calls(level: int, r: random.Random) -> Built:
    """A recursive definition printed at one argument. Shapes of the recurrence (the code states base cases and every step): two-branch
    (f(n-1) and f(n-2) with small multipliers), three-branch (n-1, n-2, n-3), halving split (f(n // 2) and f(n - n // 2) plus n % 3),
    index recursion over a list literal (skip or add the element, by parity), mutual recursion of two functions. The argument grows with
    the level so that the call tree has roughly 5 to 150 calls."""
    f, g = r.sample(FUNCS, 2)
    n, i, xs = names(r, 3)
    shape = r.choice(("two", "tri", "split", "listfold", "mutual"))
    a, b, c = r.randint(1, 3), r.randint(1, 3), r.randint(0, 4)
    b0, b1 = r.randint(0, 4), r.randint(1, 5)
    call = lambda fn, *args: ["call", fn, *args]  # noqa: E731
    if shape == "two":
        arg = 3 + level + r.randint(0, 1)
        fn = ["def", f, [n], [["if", C("<", V(n), N(2)), [["ret", B("+", V(n), N(b1))]], [["ret", B("+", B("+", B("*", call(f, B("-", V(n), N(1))), N(a)), B("*", call(f, B("-", V(n), N(2))), N(b))), N(c))]]]]]
        prog = [fn, ["print", call(f, N(arg))]]
    elif shape == "tri":
        arg = 3 + level
        fn = ["def", f, [n], [["if", C("<", V(n), N(3)), [["ret", B("+", V(n), N(b0))]], [["ret", B("+", B("+", call(f, B("-", V(n), N(1))), call(f, B("-", V(n), N(2)))), B("-", call(f, B("-", V(n), N(3))), N(c)))]]]]]
        prog = [fn, ["print", call(f, N(arg))]]
    elif shape == "split":
        arg = r.randint(6 + 4 * level, 12 + 6 * level)
        half = B("//", V(n), N(2))
        fn = ["def", f, [n], [["if", C("<", V(n), N(2)), [["ret", N(b1)]], [["ret", B("+", B("+", call(f, half), call(f, B("-", V(n), half))), B("%", V(n), N(3)))]]]]]
        prog = [fn, ["print", call(f, N(arg))]]
    elif shape == "listfold":
        size = 4 + 2 * level
        vals = [r.randint(1, 9) for _ in range(size)]
        fn = ["def", f, [xs, i], [["if", C(">=", V(i), ["call", "len", V(xs)]), [["ret", N(b0)]],
                                  [["if", C("==", B("%", IDX(V(xs), V(i)), N(2)), N(0)), [["ret", B("+", IDX(V(xs), V(i)), call(f, V(xs), B("+", V(i), N(1))))]],
                                   [["ret", B("-", B("*", N(2), call(f, V(xs), B("+", V(i), N(1)))), N(1))]]]]]]]
        prog = [fn, ["print", call(f, LIST(vals), N(0))]]
    else:
        arg = 3 + 2 * level + r.randint(0, 1)
        fa = ["def", f, [n], [["if", C("<", V(n), N(1)), [["ret", N(b1)]], [["ret", B("+", call(g, B("-", V(n), N(1))), N(a))]]]]]
        fb = ["def", g, [n], [["if", C("<", V(n), N(1)), [["ret", N(b0)]], [["ret", B("+", B("*", call(f, B("-", V(n), N(1))), N(b + 1)), call(f, B("//", V(n), N(2))))]]]]]
        prog = [fa, fb, ["print", call(f, N(arg))]]
    return finish(prog)
