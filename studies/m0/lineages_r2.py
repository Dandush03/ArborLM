# ruff: noqa: E501
"""R2, reasoning: algorithmic and symbolic tasks with an exact answer (ADR-0033 section 6.2). Lineages as in R1."""

from __future__ import annotations

import random
import string

from studies.m0.core import Built, Retry, lineage
from studies.m0.vocab import PSEUDO

ALPHA = string.ascii_lowercase


def _lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


@lineage("R2", "counting")
def count_letter(level: int, r: random.Random) -> Built:
    words = r.sample(PSEUDO, 3 + 2 * level)
    letter = r.choice(sorted({c for w in words for c in w}))
    ans = sum(w.count(letter) for w in words)
    q = f"How many times does the letter '{letter}' appear in total in these words: {' '.join(words)}?"
    return Built(q, {"words": words, "letter": letter}, str(ans), "number", None)


@lineage("R2", "counting")
def count_divisible(level: int, r: random.Random) -> Built:
    xs = [r.randint(10, 99 + 100 * (level // 2)) for _ in range(5 + 3 * level)]
    m = r.randint(2, 9)
    t = r.randint(10, 60)
    ans = sum(1 for x in xs if x % m == 0 and x > t)
    q = f"How many of the numbers in this list are divisible by {m} and greater than {t}? List: {_lst(xs)}."
    return Built(q, {"xs": xs, "m": m, "t": t}, str(ans), "number", None)


@lineage("R2", "sorting")
def sort_list(level: int, r: random.Random) -> Built:
    xs = r.sample(range(-50, 100 * (1 + level)), 4 + level)
    desc = r.random() < 0.5
    ans = sorted(xs, reverse=desc)
    q = f"Sort these numbers from {'largest to smallest' if desc else 'smallest to largest'} and give them separated by commas: {_lst(xs)}."
    return Built(q, {"xs": xs, "desc": desc}, _lst(ans), "list", None)


@lineage("R2", "sorting")
def kth_smallest(level: int, r: random.Random) -> Built:
    n = 5 + 2 * level
    xs = r.sample(range(1, 500), n)
    k = r.randint(2, n - 1)
    ans = sorted(xs)[k - 1]
    q = f"What is the number that would be in position {k} if these numbers were sorted from smallest to largest (position 1 is the smallest)? Numbers: {_lst(xs)}."
    return Built(q, {"xs": xs, "k": k}, str(ans), "number", None)


@lineage("R2", "listops")
def list_ops(level: int, r: random.Random) -> Built:
    xs = [r.randint(1, 99) for _ in range(4 + level // 2)]
    cur = xs[:]
    ops, text = [], []
    for _ in range(2 + level):
        o = r.choice(("reverse", "drop_first", "drop_last", "append", "first_to_end"))
        if o in ("drop_first", "drop_last") and len(cur) <= 2:
            o = "append"
        if o == "reverse":
            cur.reverse()
            ops.append([o])
            text.append("reverse the list")
        elif o == "drop_first":
            cur.pop(0)
            ops.append([o])
            text.append("remove the first element")
        elif o == "drop_last":
            cur.pop()
            ops.append([o])
            text.append("remove the last element")
        elif o == "append":
            v = r.randint(1, 99)
            cur.append(v)
            ops.append([o, v])
            text.append(f"add {v} at the end")
        else:
            cur.append(cur.pop(0))
            ops.append([o])
            text.append("move the first element to the end")
    q = f"Start with the list {_lst(xs)}. Do these steps in order: {'; '.join(text)}. What is the final list? Give the numbers separated by commas."
    return Built(q, {"xs": xs, "ops": ops}, _lst(cur), "list", None)


_DIG = "0123456789abcdef"


@lineage("R2", "base")
def to_base(level: int, r: random.Random) -> Built:
    b = r.choice((2, 3, 4, 5, 7, 8, 9, 16) if level >= 2 else (2, 3, 4, 5, 8))
    n = r.randint(10, 40 * 4 ** (level + 1))
    s, x = "", n
    while x:
        s = _DIG[x % b] + s
        x //= b
    q = f"Write the decimal number {n} in base {b}. Use digits 0-9 and then lowercase letters a-f for ten to fifteen."
    return Built(q, {"n": n, "base": b}, s, "text", None)


@lineage("R2", "base")
def from_base(level: int, r: random.Random) -> Built:
    b = r.choice((2, 3, 4, 5, 7, 8, 9, 16) if level >= 2 else (2, 3, 4, 5, 8))
    ln = 3 + level + r.randint(0, 2)
    s = _DIG[r.randint(1, b - 1)] + "".join(_DIG[r.randrange(b)] for _ in range(ln - 1))
    q = f"What is the base-{b} number {s} written in decimal? (Digits above 9 are lowercase letters: a is ten, b is eleven, and so on.)"
    return Built(q, {"digits": s, "base": b}, str(int(s, b)), "number", None)


@lineage("R2", "rewrite")
def string_rewrite(level: int, r: random.Random) -> Built:
    s = "".join(r.choice("abc") for _ in range(6 + 2 * level))
    rules = []
    for _ in range(1 + (level + 1) // 2):
        p = "".join(r.choice("abc") for _ in range(r.randint(1, 2)))
        t = "".join(r.choice("abc") for _ in range(r.randint(0, 3)))
        rules.append([p, t])
    cur = s
    for p, t in rules:
        cur = cur.replace(p, t)
    if cur == "" or cur == s:
        raise Retry
    steps = "; ".join(f"replace every '{p}' with '{t}'" if t else f"delete every '{p}'" for p, t in rules)
    q = (f"Start with the string {s}. Do these steps in order, each step scanning left to right over non-overlapping matches in the string as it is when the step starts: {steps}. "
         "What is the final string?")
    return Built(q, {"s": s, "rules": rules}, cur, "text", None)


@lineage("R2", "caesar")
def caesar_shift(level: int, r: random.Random) -> Built:
    ws = r.sample(PSEUDO, 1 + level // 2)
    k = r.randint(1, 25)
    text = " ".join(ws)
    ans = "".join(" " if c == " " else ALPHA[(ALPHA.index(c) + k) % 26] for c in text)
    q = f"Shift every letter of '{text}' forward by {k} places in the alphabet, wrapping from z back to a. Spaces stay. What is the result?"
    return Built(q, {"text": text, "k": k}, ans, "text", None)


@lineage("R2", "rle")
def run_length(level: int, r: random.Random) -> Built:
    runs = [(r.choice("abcxyz"), r.randint(1, 3 + level)) for _ in range(3 + level)]
    s = ""
    for c, k in runs:
        if s and s[-1] == c:
            raise Retry
        s += c * k
    ans = "".join(f"{c}{k}" for c, k in runs)
    q = f"Compress {s} by run-length encoding: replace each maximal run of one repeated letter by the letter followed by the run length (for example aaab becomes a3b1). What is the result?"
    return Built(q, {"s": s}, ans, "text", None)


@lineage("R2", "palindrome")
def palindrome_check(level: int, r: random.Random) -> Built:
    half = "".join(r.choice(ALPHA[:12]) for _ in range(3 + level))
    pal = half + (r.choice(ALPHA[:12]) if r.random() < 0.5 else "") + half[::-1]
    if r.random() < 0.5:
        i = r.randrange(len(pal))
        c = r.choice([x for x in ALPHA[:12] if x != pal[i]])
        pal = pal[:i] + c + pal[i + 1 :]
    cuts = sorted(r.sample(range(1, len(pal)), min(len(pal) - 1, 2 + level // 2)))
    parts, last = [], 0
    for c in [*cuts, len(pal)]:
        parts.append(pal[last:c])
        last = c
    phrase = " ".join(parts)
    ans = "yes" if pal == pal[::-1] else "no"
    q = f"Ignoring the spaces, does the text '{phrase}' read the same forwards and backwards? Answer yes or no."
    return Built(q, {"phrase": phrase}, ans, "yn", 2)


@lineage("R2", "grid")
def grid_sum(level: int, r: random.Random) -> Built:
    rows, cols = 3 + level // 2, 3 + (level + 1) // 2
    g = [[r.randint(0, 9) for _ in range(cols)] for _ in range(rows)]
    kind = r.choice(("row", "column", "diagonal"))
    if kind == "row":
        i = r.randrange(rows)
        ans, what = sum(g[i]), f"row {i + 1}"
    elif kind == "column":
        j = r.randrange(cols)
        ans, what = sum(g[i][j] for i in range(rows)), f"column {j + 1}"
    else:
        ans, what = sum(g[i][i] for i in range(min(rows, cols))), "the diagonal from the top left corner (cells (1,1), (2,2), and so on)"
    text = " / ".join(" ".join(str(v) for v in row) for row in g)
    q = f"A grid has {rows} rows and {cols} columns. The rows, from top to bottom, are: {text}. What is the sum of the numbers in {what}?"
    return Built(q, {"grid": g, "what": what}, str(ans), "number", None)


@lineage("R2", "permutation")
def permutation_power(level: int, r: random.Random) -> Built:
    n = 4 + level
    img = list(range(1, n + 1))
    r.shuffle(img)
    s = r.randint(1, n)
    t = r.randint(5, 30 + 10 * level)
    cur = s
    for _ in range(t):
        cur = img[cur - 1]
    mp = ", ".join(f"{i + 1} goes to {img[i]}" for i in range(n))
    q = f"A mapping on the numbers 1 to {n} sends: {mp}. Start at {s} and apply the mapping {t} times in a row. Which number do you end on?"
    return Built(q, {"img": img, "s": s, "t": t}, str(cur), "number", None)


_STACK_TEXT = {
    "add": "add the top two (replace them by their sum)",
    "mul": "multiply the top two (replace them by their product)",
    "sub": "subtract: second from top minus top (replace both by the result)",
    "dup": "duplicate the top",
    "pop": "discard the top",
    "swap": "swap the top two",
}


@lineage("R2", "stack")
def stack_machine(level: int, r: random.Random) -> Built:
    st: list[int] = []
    prog: list[list] = []
    for _ in range(4 + 2 * level):
        choices = ["push", "push"]
        if len(st) >= 1:
            choices += ["dup", "pop"] if len(st) >= 2 else ["dup"]
        if len(st) >= 2:
            choices += ["add", "mul", "swap", "sub"]
        o = r.choice(choices)
        if o == "push":
            v = r.randint(1, 9)
            st.append(v)
            prog.append([o, v])
        elif o == "dup":
            st.append(st[-1])
            prog.append([o])
        elif o == "pop":
            st.pop()
            prog.append([o])
        elif o == "swap":
            st[-1], st[-2] = st[-2], st[-1]
            prog.append([o])
        else:
            b, a = st.pop(), st.pop()
            st.append({"add": a + b, "mul": a * b, "sub": a - b}[o])
            prog.append([o])
    if not st:
        raise Retry
    text = ", ".join(f"push {p[1]}" if p[0] == "push" else _STACK_TEXT[p[0]] for p in prog)
    q = f"A stack starts empty. Do these steps in order: {text}. What number is on top of the stack at the end?"
    return Built(q, {"prog": prog}, str(st[-1]), "number", None)


@lineage("R2", "numtheory")
def multiples_between(level: int, r: random.Random) -> Built:
    m = r.randint(3, 19)
    a = r.randint(1, 50 * (level + 1))
    b = a + r.randint(20, 200 * (level + 1))
    ans = b // m - (a - 1) // m
    q = f"How many whole numbers from {a} to {b}, counting both ends, are multiples of {m}?"
    return Built(q, {"a": a, "b": b, "m": m}, str(ans), "number", None)


@lineage("R2", "numtheory")
def digit_root(level: int, r: random.Random) -> Built:
    n = r.randint(10 ** (4 + level), 10 ** (5 + level) - 1)
    ans = 1 + (n - 1) % 9
    q = f"Add up the digits of {n}. If the result has more than one digit, add up its digits again, and keep going until a single digit is left. What is that digit?"
    return Built(q, {"n": n}, str(ans), "number", None)
