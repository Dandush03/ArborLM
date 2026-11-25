# ruff: noqa: E501
# The program trees are plain nested lists (the grammar of c1grammar), as in every other C1 lineage module; hence no type parameters on list.
# mypy: disable-error-code="type-arg"
"""C1 fix round 3, stacks, graphs, references, simulation, functions, accumulators and strings. See ``lineages_c1_fix3`` for the rules. Superseded:
bracket_matching and the PROPOSED bracket_matching_traced (merged here into one lineage), union_find_links, shared_lists, bytecode_loop_r2, turtle_walk_r2,
cellular_update_r2, func_compose, fib_like, fib_shapes_recursive, string_methods, string_build."""

from __future__ import annotations

import itertools
import random
from typing import Any

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1 import FUNCS
from studies.m0.lineages_c1_common import AND, IDX, LETTERS, LIST, B, C, N, S, V, finish, names
from studies.m0.lineages_c1_fix3 import f3
from studies.m0.vocab import PSEUDO


def _call(fn: str, *args: list) -> list:
    return ["call", fn, *args]


# ------------------------------------------------------------------------------------------------ stacks


@f3("stacks", supersedes="C1.bracket_matching")
def bracket_matching_f3(level: int, r: random.Random) -> Built:
    """Four kinds of brackets "()", "[]", "{}", "<>" (codes 1 to 4). Open brackets are pushed; a closing bracket pops when the top has its kind, otherwise it counts as an
    error and the stack is left alone. The string is a random walk (open with chance 0.5 or when the stack is empty; a stray closer on an empty stack with chance 0.15; a closer
    names the top's kind with chance 0.4 and another kind otherwise), so most closers fail and 'opens minus closes' is not the height. NO answer is redrawn: balanced strings,
    height 0 and 'no error' occur at their natural rate, which is low by the construction. Shapes: 10 * errors + final height; the codes left on the stack bottom to top (a list);
    the sum of the positions of the failed closers; the codes on the stack after the first p characters (the loop stops at the stated p, 3 * n // 4 <= p < n); the sum of the positions
    of the closers that popped. Merges the earlier bracket_matching and its PROPOSED traced shapes (one procedure). 14 to 24 characters (the earlier 6 to 21: at 6 to 9 characters
    a prefix of 3 to 5 characters made 'a stack that pops on any closer' right in 0.5-0.6 of the items; a second draft with 10 to 24 characters and p from 3 still left
    'no pop at all' right in 0.2-0.38 of the prefix items)."""
    s, st, sp, err, ch, i, tot = names(r, 7)
    n = (14, 15, 16, 18, 20, 22, 24)[level]
    opens: list[int] = []
    text = ""
    open_ch, close_ch = "([{<", ")]}>"
    for _ in range(n):
        if not opens and r.random() < 0.15:
            text += close_ch[r.randrange(4)]
        elif not opens or r.random() < 0.5:
            k = r.randrange(4)
            text += open_ch[k]
            opens.append(k)
        elif r.random() < 0.4:
            text += close_ch[opens.pop()]
        else:
            text += close_ch[r.choice([k for k in range(4) if k != opens[-1]])]
    shape = r.choice(("code", "remain", "errpos", "remain_at", "popsum"))
    stop: list = N(r.randint(3 * n // 4, n - 1)) if shape == "remain_at" else _call("len", V(s))

    def close(code: int) -> list:
        hit: list[list] = [["aug", sp, "-", N(1)]] + ([["aug", tot, "+", V(i)]] if shape == "popsum" else [])
        fail: list[list] = [["aug", err, "+", N(1)]] + ([["aug", tot, "+", V(i)]] if shape == "errpos" else [])
        return ["if", AND(C(">", V(sp), N(0)), C("==", IDX(V(st), B("-", V(sp), N(1))), N(code))), hit, fail]

    def push(code: int) -> list[list]:
        return [["setidx", st, V(sp), N(code)], ["aug", sp, "+", N(1)]]

    chain: list = [close(4)]
    for code, c_close in ((3, "}"), (2, "]"), (1, ")")):
        chain = [["if", C("==", V(ch), S(c_close)), [close(code)], chain]]
    for code, c_open in ((4, "<"), (3, "{"), (2, "["), (1, "(")):
        chain = [["if", C("==", V(ch), S(c_open)), push(code), chain]]
    body = [["set", ch, IDX(V(s), V(i))], *chain]
    prog: list[list] = [["set", s, S(text)], ["set", st, ["list"]], ["for", i, N(0), _call("len", V(s)), 1, [["append", st, N(0)]]], ["set", sp, N(0)], ["set", err, N(0)], ["set", tot, N(0)]]
    prog.append(["for", i, N(0), stop, 1, body])
    last = {"code": B("+", B("*", V(err), N(10)), V(sp)), "remain": ["slice", V(st), N(0), V(sp), None], "errpos": V(tot), "remain_at": ["slice", V(st), N(0), V(sp), None], "popsum": V(tot)}[shape]
    prog.append(["print", last])
    return finish(prog)


# ------------------------------------------------------------------------------------------------ graphs and references


@f3("graphs", supersedes="C1.union_find_links")
def union_find_links_f3(level: int, r: random.Random) -> Built:
    """Parent array p (p[x] == x for a root); find(p, x) follows p[x] to a root. For each listed pair the two roots are found and, when different, one is hung under the other by
    a stated rule (first under second, second under first, larger root under the smaller). The old 'root of a queried node' shape needed a redraw (query not a root) and is
    dropped (NOT a redraw any more). Shapes: the whole parent array; the sum of the roots of all nodes; the sum of k * p[k] over the nodes. 9 + level nodes, 4 + level pairs
    (the earlier 5 + level nodes and 3 + level pairs gave 0.14-0.17 for two cheap rules at level 0, and 7 + level nodes still 0.14)."""
    p, us, vs, k, a, b, x, tot = names(r, 8)
    n = 9 + level
    m = 4 + level
    pu = [r.randrange(n) for _ in range(m)]
    pv = []
    for u in pu:
        w = r.randrange(n)
        while w == u:
            w = r.randrange(n)
        pv.append(w)
    rule = r.choice(("first", "second", "smaller"))
    shape = r.choice(("parents", "parents", "rootsum", "wsum"))
    fdef = ["def", "find", [p, x], [["while", C("!=", IDX(V(p), V(x)), V(x)), [["set", x, IDX(V(p), V(x))]]], ["ret", V(x)]]]
    link_first, link_second = ["setidx", p, V(a), V(b)], ["setidx", p, V(b), V(a)]
    link = {"first": [link_first], "second": [link_second], "smaller": [["if", C("<", V(a), V(b)), [link_second], [link_first]]]}[rule]
    loop = ["for", k, N(0), _call("len", V(us)), 1, [["set", a, _call("find", V(p), IDX(V(us), V(k)))], ["set", b, _call("find", V(p), IDX(V(vs), V(k)))], ["if", C("!=", V(a), V(b)), link, []]]]
    prog: list[list] = [fdef, ["set", p, LIST(list(range(n)))], ["set", us, LIST(pu)], ["set", vs, LIST(pv)], loop]
    if shape == "parents":
        prog.append(["print", V(p)])
    else:
        term = _call("find", V(p), V(k)) if shape == "rootsum" else B("*", V(k), IDX(V(p), V(k)))
        prog += [["set", tot, N(0)], ["for", k, N(0), N(n), 1, [["aug", tot, "+", term]]], ["print", V(tot)]]
    return finish(prog)


@f3("references", supersedes="C1.shared_lists")
def shared_lists_f3(level: int, r: random.Random) -> Built:
    """Two or three list names and 2 + level operations from: ``b = a`` (same list), ``b = a[:]``, ``b = a + [v]``, ``b.append(v)``, ``b[i] = v``, ``b = bump(a, i, v)`` (adds v
    to xs[i] IN the list it is given and returns it) and ``b = grow(a, v)`` (rebinds its parameter to xs + [v]). NO redraw on the naive-copy answer. Instead, with chance 0.85,
    the LAST TWO operations are written by construction as 'd = s' (or d = bump(s, ...), which also aliases) followed by a mutation of s (an append, or an index assignment of a
    NEW value), and the printed name is d, so the sharing matters in those items by the structure of the program; with chance 0.15 all operations are random and any name may
    be printed. Shapes: one list, its sum (the length and 'one element' shapes of the first version are gone: the length changed only under an append and the element was the
    appended literal in 0.45 of its items). The first 2 + level - 2 operations are random."""
    pool = names(r, 6)
    k = r.randint(2, 3)
    lst = pool[:k]
    fparam, fi, fv = pool[3:6]
    f_bump, f_grow = r.sample(FUNCS, 2)
    real: dict[str, Any] = {nm: [r.randint(1, 9) for _ in range(r.randint(2, 4))] for nm in lst}
    init = {nm: list(v) for nm, v in real.items()}
    stmts: list[list] = []
    used: set[str] = set()
    total_ops = 2 + level
    constructed = r.random() < 0.85
    s_nm, d_nm = r.sample(lst, 2)

    def mutate(name: str) -> None:
        if r.random() < 0.6:
            v = r.randint(1, 9)
            stmts.append(["append", name, N(v)])
            real[name].append(v)
        else:
            ix = r.randrange(len(real[name]))
            v = r.choice([q for q in range(1, 10) if q != real[name][ix]])
            stmts.append(["setidx", name, N(ix), N(v)])
            real[name][ix] = v

    def alias(dst: str, src: str, via_bump: bool) -> None:
        if via_bump:
            ix, v = r.randrange(len(real[src])), r.randint(1, 9)
            stmts.append(["set", dst, _call(f_bump, V(src), N(ix), N(v))])
            used.add("bump")
            real[src][ix] += v
        else:
            stmts.append(["set", dst, V(src)])
        real[dst] = real[src]

    random_ops = total_ops - 2 if constructed else total_ops
    for _ in range(random_ops):
        kind = r.choice(("alias", "copy", "concat", "append", "setidx", "bump", "grow"))
        dst, src = r.choice(lst), r.choice(lst)
        v = r.randint(1, 9)
        if kind == "alias":
            if dst == src:
                raise Retry  # an assignment of a name to itself says nothing (validity)
            alias(dst, src, False)
        elif kind == "copy":
            stmts.append(["set", dst, ["slice", V(src), None, None, None]])
            real[dst] = list(real[src])
        elif kind == "concat":
            stmts.append(["set", dst, B("+", V(src), LIST([v]))])
            real[dst] = real[src] + [v]
        elif kind in ("append", "setidx"):
            mutate(dst)
        elif kind == "bump":
            alias(dst, src, True)
        else:
            stmts.append(["set", dst, _call(f_grow, V(src), N(v))])
            used.add("grow")
            real[dst] = real[src] + [v]
    if constructed:
        alias(d_nm, s_nm, r.random() < 0.3)
        mutate(s_nm)
        target = d_nm
    else:
        target = r.choice(lst)
    shape = r.choice(("list", "sum"))
    defs: list[list] = []
    if "bump" in used:
        defs.append(["def", f_bump, [fparam, fi, fv], [["setidx", fparam, V(fi), B("+", IDX(V(fparam), V(fi)), V(fv))], ["ret", V(fparam)]]])
    if "grow" in used:
        defs.append(["def", f_grow, [fparam, fv], [["set", fparam, B("+", V(fparam), ["list", V(fv)])], ["ret", V(fparam)]]])
    final = V(target) if shape == "list" else _call("sum", V(target))
    return finish([*defs, *[["set", nm, LIST(init[nm])] for nm in lst], *stmts, ["print", final]])


# ------------------------------------------------------------------------------------------------ simulation


@f3("simulation", supersedes="C1.bytecode_loop_r2")
def bytecode_loop_f3(level: int, r: random.Random) -> Built:
    """As ``bytecode_loop_r2`` (a program counter fetches (opcode, argument) pairs, opcode numbers a stated random assignment) with the skips built so that ignoring them or always
    taking them is not an answer (audit: the no-skip rule hit 0.28-0.39; a first draft of this module with a skip that fired two times in three was answered by 'always skip' in
    0.30-0.39): from level 1 there are FOUR skip pairs (five from 11 pairs), never adjacent and never last, each skipping the next pair when acc and its argument have the same parity (one time in
    two), and the pair after every skip is an add, multiply or subtract so a skipped pair always changes acc. Shapes: final acc, the sum of the arguments of the pairs executed
    (level 1 up), final reg (when the code contains a store). Level 0 has no skips and 4 pairs; otherwise 9 to 14 pairs."""
    code, pc, acc, reg, op, arg, ex = names(r, 7)
    n_pairs = (4, 9, 9, 10, 11, 12, 14)[level]
    ops = ["add", "mul", "sub"] + (["skip"] if level >= 1 else []) + (["mod"] if level >= 2 else []) + (["store", "load"] if level >= 3 else [])
    num = dict(zip(ops, r.sample(range(1, 10), len(ops)), strict=True))
    plain = [o for o in ops if o != "skip"]
    effect = ["add", "mul", "sub"]
    skips: set[int] = set()
    if "skip" in ops:
        want = 4 if n_pairs < 11 else 5
        combos = [c for c in itertools.combinations(range(1, n_pairs - 1), want) if all(c[q + 1] - c[q] > 1 for q in range(want - 1))]
        skips = set(r.choice(combos))
    args = {"add": (1, 9), "mul": (2, 3), "sub": (1, 9), "skip": (0, 9), "mod": (11, 60), "store": (1, 9), "load": (1, 9)}
    pairs: list[tuple[str, int]] = []
    for q in range(n_pairs):
        o = "add" if q == 0 else ("skip" if q in skips else (r.choice(effect) if (q - 1) in skips else r.choice(plain)))
        pairs.append((o, r.randint(*args[o])))
    has_store = any(o == "store" for o, _ in pairs)
    shape = r.choice(["acc"] + (["sumarg"] if level >= 1 else []) + (["reg"] if has_store else []))
    flat: list[int] = []
    for o, ar in pairs:
        flat += [num[o], ar]
    arms: dict[str, list] = {"add": [["set", acc, B("+", V(acc), V(arg))]], "mul": [["set", acc, B("*", V(acc), V(arg))]], "sub": [["set", acc, B("-", V(acc), V(arg))]],
                             "skip": [["if", C("==", B("%", V(acc), N(2)), B("%", V(arg), N(2))), [["set", pc, B("+", V(pc), N(2))]], []]],
                             "mod": [["set", acc, B("%", V(acc), V(arg))]], "store": [["set", reg, V(acc)]], "load": [["set", acc, B("+", V(acc), V(reg))]]}
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
    prog.append(["while", C("<", V(pc), _call("len", V(code))), body])
    prog.append(["print", {"acc": V(acc), "sumarg": V(ex), "reg": V(reg)}[shape]])
    return finish(prog)


@f3("simulation", supersedes="C1.turtle_walk_r2")
def turtle_walk_f3(level: int, r: random.Random) -> Built:
    """As ``turtle_walk_r2`` (integer commands: 1, 2, 3 move that many cells forward, 4 and 5 turn, 6 from level 3 one cell backward; headings and turns stated in the code)
    with the single-coordinate shapes dropped (small integers, '0' in 0.21 of level 1) and one shape added. Shapes: the position 'x,y'; the sum over all commands of a * x + b * y after each
    command (a from 1 to 3, b from -3 to 3 without 0, stated in the code; it needs the whole path). A draft with |x| + |y| was dropped: a path that never turns back keeps |x| + |y| when
    its turns are ignored, 0.31-0.34 of the items at levels 0 and 1. The earlier shape 'sum of the forward steps made while the heading was 2 or 3' is gone (it
    needs only the heading: 0 in 0.18-0.32 of items at the low levels, and 'ignore the turns' hit 0.27). 14 to 26 commands (the earlier 6 to 18: at 6 commands 'ignore the turns' hit 0.31-0.54)."""
    cmds, x, y, d, i, c, cnt = names(r, 7)
    n = (14, 16, 18, 20, 22, 24, 26)[level]
    pool = [1, 2, 3, 4, 4, 5, 5] + ([6] if level >= 3 else [])
    text = [r.choice(pool) for _ in range(n)]
    rot = r.randint(0, 3)
    base = [("y", 1), ("x", 1), ("y", -1), ("x", -1)]
    headings = [base[(h + rot) % 4] for h in range(4)]
    turn_l = r.choice((1, 3))
    turn_r = (4 - turn_l) % 4
    d0 = r.randint(0, 3)
    shape = r.choice(("pos", "pathsum", "pathsum"))
    ca, cb = r.randint(1, 3), r.choice((-3, -2, -1, 1, 2, 3))

    def move(sign: int, amount: list) -> list:
        acts = [["aug", x if axis == "x" else y, "+" if step * sign > 0 else "-", amount] for axis, step in headings]
        node: list = [acts[3]]
        for h in (2, 1, 0):
            node = [["if", C("==", V(d), N(h)), [acts[h]], node]]
        return node

    forward = move(1, V(c))
    arms: list = [["if", C("<=", V(c), N(3)), forward,
                   [["if", C("==", V(c), N(4)), [["set", d, B("%", B("+", V(d), N(turn_l)), N(4))]],
                     [["if", C("==", V(c), N(5)), [["set", d, B("%", B("+", V(d), N(turn_r)), N(4))]],
                       [["if", C("==", V(c), N(6)), move(-1, N(1)), []]]]]]]]]
    prog: list[list] = [["set", cmds, LIST(text)], ["set", x, N(0)], ["set", y, N(0)], ["set", d, N(d0)]]
    if shape != "pos":
        prog.append(["set", cnt, N(0)])
    tail: list[list] = [["aug", cnt, "+", B("+", B("*", V(x), N(ca)), B("*", V(y), N(cb)))]] if shape == "pathsum" else []
    prog.append(["for", i, N(0), _call("len", V(cmds)), 1, [["set", c, IDX(V(cmds), V(i))], *arms, *tail]])
    prog.append(["print", B("+", B("+", _call("str", V(x)), S(",")), _call("str", V(y))) if shape == "pos" else V(cnt)])
    return finish(prog)


@f3("simulation", supersedes="C1.cellular_update_r2")
def cellular_update_f3(level: int, r: random.Random) -> Built:
    """One-dimensional cellular automaton, a fresh row each generation, 5 + level cells, 1 to 5 generations. Widened STRUCTURALLY (audit: 13 programs once literals that do not
    change control flow are discounted): three update styles (the eight-entry rule table indexed by 4 * left + 2 * centre + right; 'left + centre + right equals t' with t
    stated as 1 or 2; a three-way branch on left, centre and right), two boundaries (ring, or the end cells repeated by max and min), and the two shapes of before (the row; the sum
    of index times cell). The branch and equality styles make the executed path depend on the data. The table is never constant; the branch outputs are never all equal."""
    cells, rule, nxt, g, i, w, lf, ce, rt = names(r, 9)
    size = 5 + level
    gens = (1, 2, 3, 3, 4, 4, 5)[level]
    init = [r.randint(0, 1) for _ in range(size)]
    if len(set(init)) < 2:
        raise Retry
    style = r.choice(("table", "equals", "branch"))
    ring = r.random() < 0.5
    shape = r.choice(("row", "weighted"))
    left = IDX(V(cells), B("%", B("+", V(i), N(size - 1)), N(size))) if ring else IDX(V(cells), _call("max", B("-", V(i), N(1)), N(0)))
    right = IDX(V(cells), B("%", B("+", V(i), N(1)), N(size))) if ring else IDX(V(cells), _call("min", B("+", V(i), N(1)), N(size - 1)))
    pre: list[list] = []
    prefix: list[list] = []
    if style == "table":
        tbl = [r.randint(0, 1) for _ in range(8)]
        if len(set(tbl)) < 2:
            raise Retry
        pre = [["set", rule, LIST(tbl)]]
        step: list[list] = [["append", nxt, IDX(V(rule), B("+", B("+", B("*", left, N(4)), B("*", IDX(V(cells), V(i)), N(2))), right))]]
    else:
        prefix = [["set", lf, left], ["set", ce, IDX(V(cells), V(i))], ["set", rt, right]]
        if style == "equals":
            t = r.choice((1, 2))
            step = [["if", C("==", B("+", B("+", V(lf), V(ce)), V(rt)), N(t)), [["append", nxt, N(1)]], [["append", nxt, N(0)]]]]
        else:
            o = [r.randint(0, 1) for _ in range(3)]
            if len(set(o)) < 2:
                raise Retry
            step = [["if", C("==", V(lf), V(rt)), [["append", nxt, N(o[0])]], [["if", C("==", V(ce), N(1)), [["append", nxt, N(o[1])]], [["append", nxt, N(o[2])]]]]]]
    prog: list[list] = [["set", cells, LIST(init)], *pre,
                        ["for", g, N(0), N(gens), 1, [["set", nxt, ["list"]], ["for", i, N(0), N(size), 1, [*prefix, *step]], ["set", cells, V(nxt)]]]]
    if shape == "row":
        prog.append(["print", V(cells)])
    else:
        prog += [["set", w, N(0)], ["for", i, N(0), N(size), 1, [["aug", w, "+", B("*", V(i), IDX(V(cells), V(i)))]]], ["print", V(w)]]
    return finish(prog)


# ------------------------------------------------------------------------------------------------ functions and accumulators


@f3("functions", supersedes="C1.func_compose")
def func_compose_f3(level: int, r: random.Random) -> Built:
    """Compose small functions: f(x) = a * x + b; g is one of f(f(x)) +- c, f(f(x)) - f(x // 2) + c, f(f(x) % k) + c; from level 3 h(x) = g(x) % m with m 7 to 29 (the old m of 3 to 9
    gave nine distinct answers, the most frequent 0.15-0.23 of items; a modulus below most values of g also means that dropping the modulus is not the answer); from level 2 half the items print the sum of two calls. Widened (a up to 9, b and c up to 19, the
    argument -9 to 30) because the old version had 4 programs per level once literals that do not change control flow were discounted and 8,450 up to renaming."""
    f, g, h = r.sample(FUNCS, 3)
    x = names(r, 1)[0]
    a, b, c = r.randint(2, 9), r.randint(1, 19), r.randint(1, 19)
    fx = B("+", B("*", V(x), N(a)), N(b))
    form = r.randrange(3)
    if form == 0:
        gbody = B(r.choice("+-"), _call(f, _call(f, V(x))), N(c))
    elif form == 1:
        gbody = B("+", B("-", _call(f, _call(f, V(x))), _call(f, B("//", V(x), N(2)))), N(c))
    else:
        gbody = B("+", _call(f, B("%", _call(f, V(x)), N(r.randint(7, 40)))), N(c))
    defs: list[list] = [["def", f, [x], [["ret", fx]]], ["def", g, [x], [["ret", gbody]]]]
    top = g
    if level >= 3:
        defs.append(["def", h, [x], [["ret", B("%", _call(g, V(x)), N(r.randint(7, 29)))]]])
        top = h

    def arg() -> list:
        return N(r.randint(-9, 30))

    out = B(r.choice("+-"), _call(top, arg()), _call(top, arg())) if (level >= 2 and r.random() < 0.5) else _call(top, arg())
    return finish([*defs, ["print", out]])


@f3("accumulators", supersedes="C1.fib_like")
def fib_like_f3(level: int, r: random.Random) -> Built:
    """Iterate a linear recurrence over a pair (a, b): t = a + b, a + b + c, 2 * a + b or a + 2 * b (c stated, 1 to 9), optionally reduced modulo m (7 to 97); then a = b, b = t;
    print a or b. Widened for capacity (the old version had four start values and one recurrence: 16,660 programs per level up to renaming)."""
    a, b, t, i = names(r, 4)
    n = r.randint(4, 8) + 3 * level
    m = r.choice((None, r.randint(7, 97)))
    form = r.randrange(4)
    c = r.randint(1, 9)
    nxt = [B("+", V(a), V(b)), B("+", B("+", V(a), V(b)), N(c)), B("+", B("*", N(2), V(a)), V(b)), B("+", V(a), B("*", N(2), V(b)))][form]
    if m is not None:
        nxt = B("%", nxt, N(m))
    body = [["set", t, nxt], ["set", a, V(b)], ["set", b, V(t)]]
    return finish([["set", a, N(r.randint(0, 9))], ["set", b, N(r.randint(1, 9))], ["for", i, N(0), N(n), 1, body], ["print", r.choice((V(a), V(b)))]])


@f3("accumulators", supersedes="C1.fib_shapes_recursive")
def fib_shapes_recursive_f3(level: int, r: random.Random) -> Built:
    """The two fib-like recursive shapes: two-branch (f(n-1), f(n-2) with multipliers 1 to 7, offset 0 to 19, base n + b1 with b1 1 to 15) and three-branch (n-1, n-2, n-3, base n + b0
    with b0 0 to 12, offset 0 to 14, and now a stated multiplier on the first call, 1 to 3). Widened for capacity (the earlier version had about 8,300 programs per level up to
    renaming, below the 20,940 demanded at G = 12). A shape of the fib_like cluster."""
    f = r.choice(FUNCS)
    (n,) = names(r, 1)
    a, b, c = r.randint(1, 7), r.randint(1, 7), r.randint(0, 19)
    b0, b1 = r.randint(0, 12), r.randint(1, 15)
    if r.random() < 0.5:
        arg = 3 + level + r.randint(0, 2)
        fn = ["def", f, [n], [["if", C("<", V(n), N(2)), [["ret", B("+", V(n), N(b1))]], [["ret", B("+", B("+", B("*", _call(f, B("-", V(n), N(1))), N(a)), B("*", _call(f, B("-", V(n), N(2))), N(b))), N(c))]]]]]
    else:
        arg = 3 + level + r.randint(0, 1)
        mu = r.randint(1, 3)
        fn = ["def", f, [n], [["if", C("<", V(n), N(3)), [["ret", B("+", V(n), N(b0))]], [["ret", B("+", B("+", B("*", _call(f, B("-", V(n), N(1))), N(mu)), _call(f, B("-", V(n), N(2)))), B("-", _call(f, B("-", V(n), N(3))), N(c)))]]]]]
    return finish([fn, ["print", _call(f, N(arg))]])


# ------------------------------------------------------------------------------------------------ strings


@f3("string_methods", supersedes="C1.string_methods")
def string_methods_f3(level: int, r: random.Random) -> Built:
    """A chain of 2 + level string operations on a pseudo-word, each chosen from: upper, lower, replace a letter that the current string contains by one or two other letters,
    reverse, append two letters, twice, slice from 0 to 2; then a tail that is ALWAYS a string: the lower-cased text, or the lower-cased text sliced ([1:], [::2], [::-1], [:-2]).
    The old tails 'length' and 'count of a letter' (small integers; the count was '0' in 0.83-0.89 of its items) are gone: there is no numeric answer. The letter to replace is
    drawn from the letters the string has at that point (the generator tracks the value), so a replace always does something; the chain is one longer than before (a one-step chain
    left the lower-cased word unchanged in 0.15 of the level-0 items). A draw whose answer is empty is redrawn (validity)."""
    s = names(r, 1)[0]
    w = r.choice(PSEUDO)
    expr: list = S(w)
    val = w
    for _ in range(2 + level):
        op = r.choice(("upper", "replace", "rev", "add", "twice", "lower", "slice", "replace"))
        if op == "upper":
            expr, val = ["m", expr, "upper"], val.upper()
        elif op == "lower":
            expr, val = ["m", expr, "lower"], val.lower()
        elif op == "replace":
            old = r.choice(val)
            new = r.choice(LETTERS) * r.randint(1, 2)
            expr, val = ["m", expr, "replace", S(old), S(new)], val.replace(old, new)
        elif op == "rev":
            expr, val = ["slice", expr, None, None, N(-1)], val[::-1]
        elif op == "add":
            extra = r.choice(LETTERS) + r.choice(LETTERS)
            expr, val = B("+", expr, S(extra)), val + extra
        elif op == "twice":
            expr, val = B("*", expr, N(2)), val * 2
        else:
            k = r.randint(0, 2)
            expr, val = ["slice", expr, N(k), None, None], val[k:]
        if not val:
            raise Retry
    low: list = ["m", V(s), "lower"]
    tail = {"text": low, "tail1": ["slice", low, N(1), None, None], "alt": ["slice", low, None, None, N(2)], "rev": ["slice", low, None, None, N(-1)], "cut": ["slice", low, None, N(-2), None]}[r.choice(("text", "tail1", "alt", "rev", "cut"))]
    return finish([["set", s, expr], ["print", tail]])


@f3("strings", supersedes="C1.string_build")
def string_build_f3(level: int, r: random.Random) -> Built:
    """Build a string over a loop of 4 + 2 * level to 12 + 2 * level iterations (step 1, or 2 a quarter of the time): every m-th index appends one letter, from level 2 every (m + 1)-th
    other index a second letter, else a third. The old length shape (b - a, a closed formula: audit) is gone. Shapes: the string; the string reversed; every other character."""
    s, i = names(r, 2)
    l1, l2, l3 = r.sample(LETTERS, 3)
    m = r.randint(2, 4)
    a = r.randint(0, 3)
    step = 2 if r.random() < 0.25 else 1
    b = a + r.randint(4, 8) * step + 2 * level
    inner: list[list] = [["set", s, B("+", V(s), S(l2))]]
    if level >= 2:
        inner = [["if", C("==", B("%", V(i), N(m + 1)), N(1)), [["set", s, B("+", V(s), S(l3))]], inner]]
    body = [["if", C("==", B("%", V(i), N(m)), N(0)), [["set", s, B("+", V(s), S(l1))]], inner]]
    tail = {"s": V(s), "rev": ["slice", V(s), None, None, N(-1)], "alt": ["slice", V(s), None, None, N(2)]}[r.choice(("s", "rev", "alt"))]
    return finish([["set", s, S("")], ["for", i, N(a), N(b), step, body], ["print", tail]])
