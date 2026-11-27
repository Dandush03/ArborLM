# ruff: noqa: E501
"""C1 batch 1, family "simulation" (new family): programs that simulate a small system step by step.

Strict procedures: ``circle_elimination`` counting around a circle of flags and striking every K-th live one (Josephus counting);
``cellular_update`` a synchronous update of a row of cells from a rule table, built into a fresh list each generation; ``turtle_walk``
a position and a heading changed by a string of commands (a four-state turn counter); ``bytecode_loop`` a program counter fetching
(opcode, argument) pairs from a list and updating an accumulator and a register.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import IDX, LIST, B, C, N, S, V, batch, finish, names


@batch("simulation")
def circle_elimination(level: int, r: random.Random) -> Built:
    """A circle of n flags (1 live, 0 already out). pos starts at n - 1; each round moves pos forward K live flags (counting only live ones,
    wrapping) and strikes the flag it lands on. Shapes after R rounds: the index struck last, the sum of the indices struck, the index of the
    only live flag after all but one are struck. n = 9 + level; K from 2 to 5; some flags start out."""
    flags, pos, rd, c, tot, i, surv = names(r, 7)
    n = 9 + level
    start = [1 if r.random() < 0.85 else 0 for _ in range(n)]
    m = sum(start)
    if m < 4:
        raise Retry
    kk = r.randint(2, 5)
    shape = r.choice(("last", "sum", "survivor"))
    rounds = m - 1 if shape == "survivor" else r.randint(2, m - 1)
    strike: list[list] = [["set", c, N(0)], ["while", C("<", V(c), N(kk)), [["set", pos, B("%", B("+", V(pos), N(1)), N(n))], ["if", C("==", IDX(V(flags), V(pos)), N(1)), [["aug", c, "+", N(1)]], []]]], ["setidx", flags, V(pos), N(0)]]
    if shape == "sum":
        strike.append(["aug", tot, "+", V(pos)])
    prog: list[list] = [["set", flags, LIST(start)], ["set", pos, N(n - 1)]]
    if shape == "sum":
        prog.append(["set", tot, N(0)])
    prog.append(["for", rd, N(0), N(rounds), 1, strike])
    if shape == "last":
        prog.append(["print", V(pos)])
    elif shape == "sum":
        prog.append(["print", V(tot)])
    else:
        prog += [["for", i, N(0), N(n), 1, [["if", C("==", IDX(V(flags), V(i)), N(1)), [["set", surv, V(i)]], []]]], ["print", V(surv)]]
    return finish(prog)


@batch("simulation")
def cellular_update(level: int, r: random.Random) -> Built:
    """One-dimensional cellular automaton on a ring: the new cell is rule[4 * left + 2 * centre + right], the neighbours wrapping around, the
    whole new row built in a fresh list before it replaces the old one. The eight-entry rule table is random (never all equal) and shown in
    the program. Shapes after G generations: the row, the sum over cells of (index times cell value). 5 + level cells, G from 1 to 5."""
    cells, rule, nxt, g, i = names(r, 5)
    size = 5 + level
    gens = (1, 2, 3, 3, 4, 4, 5)[level]
    init = [r.randint(0, 1) for _ in range(size)]
    tbl = [r.randint(0, 1) for _ in range(8)]
    if len(set(tbl)) < 2 or len(set(init)) < 2:
        raise Retry
    shape = r.choice(("row", "weighted"))
    left = IDX(V(cells), B("%", B("+", V(i), N(size - 1)), N(size)))
    right = IDX(V(cells), B("%", B("+", V(i), N(1)), N(size)))
    index = B("+", B("+", B("*", left, N(4)), B("*", IDX(V(cells), V(i)), N(2))), right)
    prog: list[list] = [["set", cells, LIST(init)], ["set", rule, LIST(tbl)],
                        ["for", g, N(0), N(gens), 1, [["set", nxt, ["list"]], ["for", i, N(0), N(size), 1, [["append", nxt, IDX(V(rule), index)]]], ["set", cells, V(nxt)]]]]
    if shape == "row":
        prog.append(["print", V(cells)])
    else:
        w = "w"
        prog += [["set", w, N(0)], ["for", i, N(0), N(size), 1, [["aug", w, "+", B("*", V(i), IDX(V(cells), V(i)))]]], ["print", V(w)]]
    return finish(prog)


@batch("simulation")
def turtle_walk(level: int, r: random.Random) -> Built:
    """A walker with position (x, y) and heading d in 0..3 reads a string of commands: F steps forward, B steps backward (from level 3), L and
    R turn (d changes by 3 and 1 mod 4, or 1 and 3, as the code states). What each heading means is written in the code. Shapes: Manhattan
    distance from the start, the final position written 'x,y', the greatest Manhattan distance reached at the end of any command. 5, 7, 9,
    11, 13, 15 or 18 commands."""
    cmds, x, y, d, i, c = names(r, 6)
    n = (5, 7, 9, 11, 13, 15, 18)[level]
    alphabet = "FFFLRB" if level >= 3 else "FFFLR"
    text = "".join(r.choice(alphabet) for _ in range(n))
    rot = r.randint(0, 3)
    base = [("y", 1), ("x", 1), ("y", -1), ("x", -1)]
    headings = [base[(h + rot) % 4] for h in range(4)]
    turn_l = r.choice((1, 3))
    shape = r.choice(("manhattan", "pos", "far"))

    def move(sign: int) -> list:
        acts = [["aug", x if axis == "x" else y, "+" if step * sign > 0 else "-", N(1)] for axis, step in headings]
        node: list = [acts[3]]
        for h in (2, 1, 0):
            node = [["if", C("==", V(d), N(h)), [acts[h]], node]]
        return node

    turn_r = (4 - turn_l) % 4
    arms: list = [["if", C("==", V(c), S("F")), move(1),
                   [["if", C("==", V(c), S("L")), [["set", d, B("%", B("+", V(d), N(turn_l)), N(4))]],
                     [["if", C("==", V(c), S("R")), [["set", d, B("%", B("+", V(d), N(turn_r)), N(4))]],
                       [["if", C("==", V(c), S("B")), move(-1), []]]]]]]]]
    dist = B("+", ["call", "abs", V(x)], ["call", "abs", V(y)])
    prog: list[list] = [["set", cmds, S(text)], ["set", x, N(0)], ["set", y, N(0)], ["set", d, N(0)]]
    tail: list[list] = []
    if shape == "far":
        prog.append(["set", "far", N(0)])
        tail = [["set", "far", ["call", "max", V("far"), dist]]]
    prog.append(["for", i, N(0), ["call", "len", V(cmds)], 1, [["set", c, IDX(V(cmds), V(i))], *arms, *tail]])
    if shape == "manhattan":
        prog.append(["print", dist])
    elif shape == "pos":
        prog.append(["print", B("+", B("+", ["call", "str", V(x)], S(",")), ["call", "str", V(y)])])
    else:
        prog.append(["print", V("far")])
    return finish(prog)


@batch("simulation")
def bytecode_loop(level: int, r: random.Random) -> Built:
    """A tiny machine: code is a flat list of (opcode, argument) pairs; a program counter fetches a pair, advances by two, then acts on the
    accumulator acc and register reg, the opcode numbers being a random assignment written in the code. Ops: add arg; multiply by arg;
    subtract arg (from level 0); skip the next pair if acc > arg (from level 1); acc = acc % arg (from level 2); reg = acc, acc = acc + reg
    (from level 3). Shapes: final acc, the sum of the arguments of the pairs executed (a skipped pair does not count; from level 1), final reg (from level 3,
    kept only when it is not 0). 4 to 12 pairs."""
    code, pc, acc, reg, op, arg, ex = names(r, 7)
    n_pairs = (4, 5, 6, 7, 9, 10, 12)[level]
    ops = ["add", "mul", "sub"] + (["skip"] if level >= 1 else []) + (["mod"] if level >= 2 else []) + (["store", "load"] if level >= 3 else [])
    num = dict(zip(ops, r.sample(range(1, 10), len(ops)), strict=True))
    pairs: list[tuple[str, int]] = [("add", r.randint(1, 9))]
    for _ in range(n_pairs - 1):
        o = r.choice(ops)
        pairs.append((o, {"add": r.randint(1, 9), "mul": r.randint(2, 3), "sub": r.randint(1, 9), "skip": r.randint(2, 30), "mod": r.randint(2, 9), "store": r.randint(0, 9), "load": r.randint(0, 9)}[o]))
    a_v, g_v, p_i = 0, 0, 0
    while p_i < 2 * n_pairs:
        o, ar = pairs[p_i // 2]
        p_i += 2
        if o == "add":
            a_v += ar
        elif o == "mul":
            a_v *= ar
        elif o == "sub":
            a_v -= ar
        elif o == "skip":
            p_i += 2 if a_v > ar else 0
        elif o == "mod":
            a_v %= ar
        elif o == "store":
            g_v = a_v
        else:
            a_v += g_v
    shapes = ["acc"] + (["sumarg"] if level >= 1 else []) + (["reg"] if level >= 3 and g_v != 0 else [])
    shape = r.choice(shapes)
    flat: list[int] = []
    for o, ar in pairs:
        flat += [num[o], ar]
    arms: dict[str, list] = {"add": [["set", acc, B("+", V(acc), V(arg))]], "mul": [["set", acc, B("*", V(acc), V(arg))]], "sub": [["set", acc, B("-", V(acc), V(arg))]],
                             "skip": [["if", C(">", V(acc), V(arg)), [["set", pc, B("+", V(pc), N(2))]], []]], "mod": [["set", acc, B("%", V(acc), V(arg))]],
                             "store": [["set", reg, V(acc)]], "load": [["set", acc, B("+", V(acc), V(reg))]]}
    chain: list = []
    for o in reversed(ops):
        chain = [["if", C("==", V(op), N(num[o])), arms[o], chain]]
    prog: list[list] = [["set", code, LIST(flat)], ["set", pc, N(0)], ["set", acc, N(0)]]
    if "store" in ops:
        prog.append(["set", reg, N(0)])
    if shape == "sumarg":
        prog.append(["set", ex, N(0)])
    body: list[list] = [["set", op, IDX(V(code), V(pc))], ["set", arg, IDX(V(code), B("+", V(pc), N(1)))], ["set", pc, B("+", V(pc), N(2))]]
    if shape == "sumarg":
        body.append(["aug", ex, "+", V(arg)])
    body += chain
    prog.append(["while", C("<", V(pc), ["call", "len", V(code)]), body])
    prog.append(["print", {"acc": V(acc), "sumarg": V(ex), "reg": V(reg)}[shape]])
    return finish(prog)
