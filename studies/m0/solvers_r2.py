# ruff: noqa: E501
"""Independent second solvers for R2. Read only the item's structured form; import nothing from the generators.

Where the generator uses a library routine or a closed formula, these use a different method (manual scanning,
insertion sort, repeated subtraction, Horner's rule, cycle reduction, and so on). Written by the implementer, not
by a separate auditor context: ruling needed 3.
"""

from __future__ import annotations

import itertools
import re
from collections import deque
from typing import Any

_DIG = "0123456789abcdef"


def _lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


def count_letter(s: dict[str, Any]) -> str:
    return str(sum(len(re.findall(re.escape(s["letter"]), w)) for w in s["words"]))


def count_divisible(s: dict[str, Any]) -> str:
    n = 0
    for x in s["xs"]:
        if (x // s["m"]) * s["m"] == x and x - s["t"] > 0:
            n += 1
    return str(n)


def sort_list(s: dict[str, Any]) -> str:
    out: list[int] = []
    for x in s["xs"]:  # insertion sort
        i = 0
        while i < len(out) and (out[i] > x if s["desc"] else out[i] < x):
            i += 1
        out.insert(i, x)
    return _lst(out)


def kth_smallest(s: dict[str, Any]) -> str:
    pool = list(s["xs"])
    v = 0
    for _ in range(s["k"]):  # remove the minimum k times
        v = pool[0]
        for x in pool:
            if x < v:
                v = x
        pool.remove(v)
    return str(v)


def list_ops(s: dict[str, Any]) -> str:
    d = deque(s["xs"])
    for op in s["ops"]:
        if op[0] == "reverse":
            d = deque(reversed(d))
        elif op[0] == "drop_first":
            d.popleft()
        elif op[0] == "drop_last":
            d.pop()
        elif op[0] == "append":
            d.append(op[1])
        else:
            d.rotate(-1)
    return _lst(list(d))


def to_base(s: dict[str, Any]) -> str:
    n, b = s["n"], s["base"]
    p = 1
    while p * b <= n:
        p *= b
    out = ""
    while p >= 1:  # greedy: largest power first
        d = 0
        while n >= p:
            n -= p
            d += 1
        out += _DIG[d]
        p //= b
    return out


def from_base(s: dict[str, Any]) -> str:
    v = 0
    for ch in s["digits"]:
        v = v * s["base"] + _DIG.index(ch)  # Horner
    return str(v)


def string_rewrite(s: dict[str, Any]) -> str:
    cur = s["s"]
    for p, t in s["rules"]:
        out, i = [], 0
        while i < len(cur):
            if cur.startswith(p, i):
                out.append(t)
                i += len(p)
            else:
                out.append(cur[i])
                i += 1
        cur = "".join(out)
    return cur


def caesar_shift(s: dict[str, Any]) -> str:
    table = "abcdefghijklmnopqrstuvwxyz" * 2
    return "".join(c if c == " " else table[table.index(c) + s["k"]] for c in s["text"])


def run_length(s: dict[str, Any]) -> str:
    return "".join(f"{k}{len(list(g))}" for k, g in itertools.groupby(s["s"]))


def palindrome_check(s: dict[str, Any]) -> str:
    t = s["phrase"].replace(" ", "")
    i, j = 0, len(t) - 1
    while i < j:
        if t[i] != t[j]:
            return "no"
        i += 1
        j -= 1
    return "yes"


def grid_sum(s: dict[str, Any]) -> str:
    g = s["grid"]
    rows, cols = len(g), len(g[0])
    flat = [v for row in g for v in row]
    m = re.match(r"(row|column) (\d+)", s["what"])
    if m and m.group(1) == "row":
        i = int(m.group(2)) - 1
        return str(sum(flat[i * cols + j] for j in range(cols)))
    if m:
        j = int(m.group(2)) - 1
        return str(sum(flat[i * cols + j] for i in range(rows)))
    return str(sum(flat[i * cols + i] for i in range(min(rows, cols))))


def permutation_power(s: dict[str, Any]) -> str:
    img, cur = s["img"], s["s"]
    # reduce the number of steps by the length of the cycle containing the start
    length, x = 1, img[cur - 1]
    while x != cur:
        x = img[x - 1]
        length += 1
    for _ in range(s["t"] % length):
        cur = img[cur - 1]
    return str(cur)


def stack_machine(s: dict[str, Any]) -> str:
    top: Any = None  # a linked stack: (value, rest)
    for p in s["prog"]:
        if p[0] == "push":
            top = (p[1], top)
        elif p[0] == "dup":
            top = (top[0], top)
        elif p[0] == "pop":
            top = top[1]
        elif p[0] == "swap":
            (a, (b, rest)) = top
            top = (b, (a, rest))
        else:
            (b, (a, rest)) = top  # b is the top, a is second from top
            v = a + b if p[0] == "add" else (a * b if p[0] == "mul" else a - b)
            top = (v, rest)
    return str(top[0])


def multiples_between(s: dict[str, Any]) -> str:
    return str(sum(1 for x in range(s["a"], s["b"] + 1) if x % s["m"] == 0))


def digit_root(s: dict[str, Any]) -> str:
    n = s["n"]
    while n >= 10:
        n = sum(int(c) for c in str(n))
    return str(n)


SOLVERS = {
    f"R2.{f.__name__}": f
    for f in (count_letter, count_divisible, sort_list, kth_smallest, list_ops, to_base, from_base, string_rewrite, caesar_shift,
              run_length, palindrome_check, grid_sum, permutation_power, stack_machine, multiples_between, digit_root)
}
