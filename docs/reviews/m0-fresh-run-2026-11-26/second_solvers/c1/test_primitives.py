"""Check the interpreter's hand-written primitives against the host's built-in
operators on synthetic values (no item code is executed here)."""
import os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solver2_c1 as S
import ast
bad = 0; n = 0
for a in range(-40, 41):
    for b in range(-13, 14):
        if b == 0: continue
        n += 2
        if S.floordiv(a, b) != a // b: bad += 1; print("floordiv", a, b)
        if S.mod(a, b) != a % b: bad += 1; print("mod", a, b)
for big in (10**30 + 7, -(10**30) - 7):
    for b in (3, -3, 10**15 + 1, -(10**15) - 1):
        n += 2
        bad += (S.floordiv(big, b) != big // b) + (S.mod(big, b) != big % b)
vals = [None] + list(range(-9, 10))
for L in range(0, 8):
    seq = list(range(100, 100 + L)); s = "abcdefgh"[:L]
    for lo, hi, st in itertools.product(vals, vals, [None, -3, -2, -1, 1, 2, 3]):
        n += 2
        if S.do_slice(seq, lo, hi, st) != seq[lo:hi:st]: bad += 1; print("slice", L, lo, hi, st)
        if S.do_slice(s, lo, hi, st) != s[lo:hi:st]: bad += 1; print("sslice", L, lo, hi, st)
    for i in range(-10, 10):
        n += 1
        try: mine = seq[S.norm_index(seq, i)]
        except S.ItemRuntimeError: mine = "IE"
        try: host = seq[i]
        except IndexError: host = "IE"
        bad += mine != host
for x in [0, 7, -7, 123456789, -10**40, True, False, None, "ab", "a'b", 'a"b', "a'\"b", "a\\b",
          [1, -2, [3, "x"], "y'z", True], []]:
    n += 2
    if S.render_str(x) != str(x): bad += 1; print("str", repr(x), S.render_str(x))
    if S.render_repr(x) != repr(x): bad += 1; print("repr", repr(x), S.render_repr(x))
for s, o, w in [("tolek", "k", "ee"), ("aaaa", "aa", "b"), ("ab", "", "-"), ("", "", "x"), ("abc", "z", "q"), ("abab", "ab", "")]:
    n += 1; bad += S.str_replace(s, o, w) != s.replace(o, w)
for s in ["Hello World", "abc", "XYZ-1"]:
    n += 2; bad += (S.ascii_lower(s) != s.lower()) + (S.ascii_upper(s) != s.upper())
for a, b in [([1, 2], [1, 3]), ([1, 2], [1, 2, 0]), ([2], [1, 9]), ("ab", "b"), ("ab", "a"), (3, True), ([1, [2]], [1, [2]])]:
    for op in (ast.Lt(), ast.Gt(), ast.LtE(), ast.GtE(), ast.Eq(), ast.NotEq()):
        n += 1
        host = {ast.Lt: lambda: a < b, ast.Gt: lambda: a > b, ast.LtE: lambda: a <= b, ast.GtE: lambda: a >= b,
                ast.Eq: lambda: a == b, ast.NotEq: lambda: a != b}[type(op)]()
        if S.compare(op, a, b) != host: bad += 1; print("cmp", a, type(op).__name__, b)
# and/or return operands; chained comparisons; aliasing; list +=; recursion (via the interpreter on literal test programs)
progs = {
    "print(0 and 5, 3 and 5, 0 or 'z', 4 or 9)": "0 5 z 4",
    "print(1 < 2 < 3, 1 < 3 < 2, 3 > 2 == 2)": "True False True",
    "a = [1, 2]\nb = a\nb.append(3)\nb[0] = 9\nprint(a)": "[9, 2, 3]",
    "a = [1]\nb = a\nb += [2]\nb = b + [3]\nprint(a, b)": "[1, 2] [1, 2, 3]",
    "def f(n):\n    if n < 2:\n        return n\n    return f(n - 1) + f(n - 2)\nprint(f(15))": "610",
    "def g(x):\n    x.append(1)\n    x = [7]\n    return x\nq = []\nr = g(q)\nprint(q, r)": "[1] [7]",
    "print(-7 // 2, -7 % 2, 7 // -2, 7 % -2, str(-5) + 'a')": "-4 1 -4 -1 -5a",
    "print(not 0, not [1], 'abc'[::-1], [1, 2, 3][-1:-5:-1])": "True False cba [3, 2, 1]",
}
for src, want in progs.items():
    n += 1
    got = S.run_module(ast.parse(src))
    if got != want: bad += 1; print("prog", repr(src), got, want)
# unsupported constructs must raise Unsupported naming them
for src in ["x = {1: 2}\nprint(x)", "for c in 'ab':\n    print(c)", "print(3 / 2)", "x = 1\nx **= 2\nprint(x)", "print([i for i in range(3)])"]:
    n += 1
    try:
        S.run_module(ast.parse(src)); bad += 1; print("no error for", repr(src))
    except S.Unsupported as e:
        print("  Unsupported raised as intended:", repr(src.splitlines()[0]), "->", e)
print("checks", n, "failures", bad)
