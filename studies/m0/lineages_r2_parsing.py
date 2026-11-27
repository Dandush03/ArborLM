# ruff: noqa: E501
"""R2 batch 1, family "parsing": nesting-aware reading of a symbol string (matching brackets with a stack; evaluating an infix expression)."""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_r2_common import batch1, until

PAIRS = (("(", ")"), ("[", "]"), ("{", "}"))


def balanced(s: str) -> bool:
    stack: list[str] = []
    close = {c: o for o, c in PAIRS}
    for ch in s:
        if ch in close:
            if not stack or stack.pop() != close[ch]:
                return False
        else:
            stack.append(ch)
    return not stack


def match_of(s: str, p: int) -> int:
    """0-based index of the closer matching the opener at 0-based index p (s is balanced)."""
    stack: list[int] = []
    for i, ch in enumerate(s):
        if ch in "([{":
            stack.append(i)
        else:
            j = stack.pop()
            if j == p:
                return i
    raise ValueError("unmatched")


def random_balanced(r: random.Random, pairs: int, types: int) -> str:
    out: list[str] = []
    stack: list[str] = []
    opened = 0
    while opened < pairs or stack:
        if opened < pairs and (not stack or r.random() < 0.5):
            t = r.randrange(types)
            out.append(PAIRS[t][0])
            stack.append(PAIRS[t][1])
            opened += 1
        else:
            out.append(stack.pop())
    return "".join(out)


@batch1("parsing")
def bracket_match(level: int, r: random.Random) -> Built:
    """Procedure: match brackets with a last-opened-first-closed stack. structured: {"s": str, "ask": "valid" | "match", "p": int or null (1-based)}.
    Answer, valid: yes/no, is every opener closed by the same kind of bracket in the right order (wrong strings are made by swapping two unlike characters, so the counts of each kind stay equal);
    Answer, match: the 1-based position of the bracket that closes the opener at position p (the string is then balanced)."""
    types = 2 if level <= 2 else 3
    if r.random() < 0.6:
        want = r.choice(("yes", "no"))

        def make() -> str:
            t = random_balanced(r, 5 + level, types)
            if want == "no":
                i, j = sorted(r.sample(range(len(t)), 2))
                t = t[:i] + t[j] + t[i + 1 : j] + t[i] + t[j + 1 :]
            return t

        # a wrong text still starts with an opener and ends with a closer, so those two checks cannot give the answer away
        s = until(300, make, lambda t: balanced(t) == (want == "yes") and t[0] in "([{" and t[-1] in ")]}")
        q = (f"In the text {s} every opening bracket must be closed by a closing bracket of the same kind, and brackets that are opened later must be closed earlier (the kinds are round, square and curly). "
             "Is the text correctly nested? Answer yes or no.")
        return Built(q, {"s": s, "ask": "valid", "p": None}, want, "yn", 2)
    def make2() -> tuple[str, int]:
        t = random_balanced(r, 5 + level, types)
        return t, r.choice([i for i, ch in enumerate(t) if ch in "([{"])

    def ok2(sp: tuple[str, int]) -> bool:
        t, q0 = sp
        true = match_of(t, q0)
        nxt = t.find({"(": ")", "[": "]", "{": "}"}[t[q0]], q0 + 1)
        return true != nxt and true != len(t) - 1 - q0  # neither "the next closer of the same kind" nor the mirror position

    s, p = until(300, make2, ok2)
    ans = match_of(s, p) + 1
    q = (f"In the correctly nested text {s} (positions are counted from 1 at the left), every opening bracket is closed by a closing bracket of the same kind, and brackets opened later are closed earlier. "
         f"At which position is the closing bracket that belongs to the opening bracket at position {p + 1}?")
    return Built(q, {"s": s, "ask": "match", "p": p + 1}, str(ans), "number", None)


# ---- expression evaluation

_PREC = {"+": 1, "-": 1, "*": 2}


def _tree(r: random.Random, leaves: int, hi: int) -> object:
    if leaves == 1:
        return r.randint(1, hi)
    k = r.randint(1, leaves - 1)
    return (r.choice(("+", "-", "*")), _tree(r, k, hi), _tree(r, leaves - k, hi))


def _val(t: object) -> int:
    if isinstance(t, int):
        return t
    assert isinstance(t, tuple)
    op, a, b = t
    x, y = _val(a), _val(b)
    return x + y if op == "+" else x - y if op == "-" else x * y


def _render_std(t: object, extra: random.Random) -> str:
    """Minimal parentheses under 'multiplication before addition and subtraction, equal ranks left to right', plus random extra ones."""
    if isinstance(t, int):
        return str(t)
    assert isinstance(t, tuple)
    op, a, b = t

    def side(c: object, right: bool) -> str:
        s = _render_std(c, extra)
        if isinstance(c, tuple):
            cp, pp = _PREC[c[0]], _PREC[op]
            if cp < pp or (right and cp == pp and op != "+" and not (op == "*" and c[0] == "*")) or (right and op == "+" and c[0] == "-") or extra.random() < 0.2:
                return f"({s})"
        return s

    return f"{side(a, False)} {op} {side(b, True)}"


def _render_ltr(t: object) -> str:
    """Every right-hand operand that is itself an operation is parenthesised, left operands never: the text reads left to right."""
    if isinstance(t, int):
        return str(t)
    assert isinstance(t, tuple)
    op, a, b = t
    rb = f"({_render_ltr(b)})" if isinstance(b, tuple) else _render_ltr(b)
    return f"{_render_ltr(a)} {op} {rb}"


def evaluate(text: str, precedence: bool) -> int:
    toks = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def atom() -> int:
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "(":
            v = expr()
            pos += 1
            return v
        return int(t)

    def expr() -> int:
        nonlocal pos
        if precedence:
            v = term()
            while pos < len(toks) and toks[pos] in "+-":
                op = toks[pos]
                pos += 1
                w = term()
                v = v + w if op == "+" else v - w
            return v
        v = atom()
        while pos < len(toks) and toks[pos] in "+-*":
            op = toks[pos]
            pos += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    def term() -> int:
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] == "*":
            pos += 1
            v *= atom()
        return v

    return expr()


@batch1("parsing")
def expression_eval(level: int, r: random.Random) -> Built:
    """Procedure: evaluate an infix expression (operator ranks, parentheses). structured: {"text": str, "convention": "ranked" | "left_to_right"}.
    ranked: parentheses first, then multiplication, then addition and subtraction, equal ranks left to right. left_to_right: parentheses first, then every operator left to right with no ranks.
    Answer: the integer value (can be negative). In 90% of items (by internal redraw) the other convention gives a different value. In `match` items the answer is neither the next closer of the same kind nor the mirror position."""
    leaves = 4 + level + r.randint(0, 1)
    hi = 9 if level < 4 else 20
    conv = r.choice(("ranked", "left_to_right"))

    def make() -> tuple[str, int]:
        t = _tree(r, leaves, hi)
        return (_render_std(t, r) if conv == "ranked" else _render_ltr(t)), _val(t)

    def ok(tv: tuple[str, int]) -> bool:
        text, val = tv
        if evaluate(text, conv == "ranked") != val:
            raise AssertionError("renderer and evaluator disagree")
        flat = evaluate(text.replace("(", "").replace(")", ""), True)
        return evaluate(text, conv != "ranked") != val or r.random() < 0.1 and (conv != "ranked" or flat != val or r.random() < 0.1)

    text, ans = until(300, make, ok)
    if conv == "ranked":
        q = (f"Work out {text}. Do what is inside parentheses first; then multiplication; then addition and subtraction; operators of the same kind are done from left to right. What is the result?")
    else:
        q = (f"Work out {text} by this rule, which is not the usual one: do what is inside parentheses first, and then do the operators strictly in the order they are written from left to right, with multiplication getting no priority over addition or subtraction. What is the result?")
    return Built(q, {"text": text, "convention": conv}, str(ans), "number", None)
