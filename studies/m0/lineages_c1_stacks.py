# ruff: noqa: E501
"""C1 batch 1, family "stacks" (new family): programs that keep a stack in a list plus a top pointer (no pop method in the grammar).

Strict procedures: ``bracket_matching`` a stack of open brackets matched against each closing bracket; ``postfix_evaluation`` a stack of
operands from which two are replaced by the result of each operator (reverse Polish evaluation).
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, S, V, batch, finish, names


@batch("stacks")
def bracket_matching(level: int, r: random.Random) -> Built:
    """Two kinds of brackets, "()" and "[]". Open brackets are pushed (1 for round, 2 for square); a closing bracket pops when the top has its
    kind, otherwise it counts as an error and the stack is left alone. Shapes: the errors and the final height written as one number (10 * errors + height), the final
    stack height, the index of the first error. A draw whose answer would be 0 (no error, nothing left open) or -1 is redrawn. The string has 6, 7, 9, 12, 15, 18 or 21 characters, drawn as a random walk that mostly closes what is open
    but sometimes closes the wrong kind or closes an empty stack."""
    s, st, sp, err, first, ch, i = names(r, 7)
    n = (6, 7, 9, 12, 15, 18, 21)[level]
    opens, depth, text = [], 0, ""
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
    shape = r.choice(("code", "code", "height", "first"))

    def close(code: int) -> list:
        fail: list[list] = [["aug", err, "+", N(1)]]
        if shape == "first":
            fail.append(["if", C("<", V(first), N(0)), [["set", first, V(i)]], []])
        return ["if", AND(C(">", V(sp), N(0)), C("==", IDX(V(st), B("-", V(sp), N(1))), N(code))), [["aug", sp, "-", N(1)]], fail]

    stack: list[int] = []
    errs, firsterr = 0, -1
    for pos, chr_ in enumerate(text):
        if chr_ in "([":
            stack.append(1 if chr_ == "(" else 2)
        elif stack and stack[-1] == (1 if chr_ == ")" else 2):
            stack.pop()
        else:
            errs += 1
            firsterr = pos if firsterr < 0 else firsterr
    if (shape == "code" and errs * 10 + len(stack) == 0) or (shape == "height" and not stack) or (shape == "first" and firsterr < 0):
        raise Retry
    prog: list[list] = [["set", s, S(text)], ["set", st, ["list"]],
                        ["for", i, N(0), ["call", "len", V(s)], 1, [["append", st, N(0)]]],
                        ["set", sp, N(0)], ["set", err, N(0)]]
    if shape == "first":
        prog.append(["set", first, N(-1)])
    loop_body = [["set", ch, IDX(V(s), V(i))],
                 ["if", C("==", V(ch), S("(")), [["setidx", st, V(sp), N(1)], ["aug", sp, "+", N(1)]],
                  [["if", C("==", V(ch), S("[")), [["setidx", st, V(sp), N(2)], ["aug", sp, "+", N(1)]],
                    [["if", C("==", V(ch), S(")")), [close(1)], [close(2)]]]]]]]
    prog.append(["for", i, N(0), ["call", "len", V(s)], 1, loop_body])
    prog.append(["print", {"code": B("+", B("*", V(err), N(10)), V(sp)), "height": V(sp), "first": V(first) if shape == "first" else V(err)}[shape]])
    return finish(prog)


@batch("stacks")
def postfix_evaluation(level: int, r: random.Random) -> Built:
    """Reverse Polish evaluation over a list of ints: a token >= 0 is pushed; a negative token pops two values x (below) and y (top) and
    pushes x + y, x - y or x * y, the code of each operator being fixed by a random assignment shown in the program. Shapes: the final top,
    the sum of the values the operators wrote back. 3 + level operands (1 to 9)."""
    toks, st, sp, i, t, x, y, neg = names(r, 8)
    m = 3 + level
    codes = r.sample((-1, -2, -3), 3)  # codes[0] adds, codes[1] subtracts, codes[2] multiplies
    seq: list[int] = []
    size, pushed = 0, 0
    while pushed < m or size > 1:
        if pushed < m and (size < 2 or r.random() < 0.55):
            seq.append(r.randint(1, 9))
            pushed += 1
            size += 1
        else:
            seq.append(codes[r.choice((0, 1, 2, 2))])
            size -= 1
    shape = r.choice(("top", "opsum"))
    arms = [["if", C("==", V(t), N(codes[0])), [["setidx", st, B("-", V(sp), N(1)), B("+", V(x), V(y))]],
             [["if", C("==", V(t), N(codes[1])), [["setidx", st, B("-", V(sp), N(1)), B("-", V(x), V(y))]], [["setidx", st, B("-", V(sp), N(1)), B("*", V(x), V(y))]]]]]]
    if shape == "opsum":
        arms.append(["aug", neg, "+", IDX(V(st), B("-", V(sp), N(1)))])
    push: list[list] = [["setidx", st, V(sp), V(t)], ["aug", sp, "+", N(1)]]
    prog: list[list] = [["set", toks, LIST(seq)], ["set", st, ["list"]], ["for", i, N(0), ["call", "len", V(toks)], 1, [["append", st, N(0)]]], ["set", sp, N(0)]]
    if shape == "opsum":
        prog.append(["set", neg, N(0)])
    pop: list[list] = [["set", y, IDX(V(st), B("-", V(sp), N(1)))], ["set", x, IDX(V(st), B("-", V(sp), N(2)))], ["aug", sp, "-", N(1)], *arms]
    prog.append(["for", i, N(0), ["call", "len", V(toks)], 1, [["set", t, IDX(V(toks), V(i))], ["if", C(">=", V(t), N(0)), push, pop]]])
    prog.append(["print", {"top": IDX(V(st), B("-", V(sp), N(1))), "opsum": V(neg)}[shape]])
    return finish(prog)
