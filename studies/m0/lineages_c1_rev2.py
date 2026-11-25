# ruff: noqa: E501
"""C1 batch 1, revision 2 (fix round after the independent audit; lead rulings 2, R-1 to R-9). NEW file: the old shapes stay untouched in
``lineages_c1_<family>.py`` and are SUPERSEDED where a ``_r2`` or other revised shape exists here (list in ``SUPERSEDES``).

Rules followed here: a tell is removed BY CONSTRUCTION (the program's structure makes the heuristic uninformative); no item is redrawn
conditional on a heuristic's outcome; a shape whose tell cannot be removed by construction is NOT REGISTERED (``NOT_REGISTERED`` states
why). Lineages here live in their own registry ``REV2``; ids are ``C1.<function name>``. ``PROPOSED`` marks shapes that are only proposals
(traced-state questions for lineages whose old shapes are answerable by a formula): whether formula-answerable shapes stay is the human
lead's decision.

Every identifier of a program, fixed or drawn, comes out of ``names`` (one ``sample`` per item), so a fixed name can never collide with a drawn one.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, lineages_of
from studies.m0.lineages_c1 import FUNCS
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, S, V, finish, names

REV2: list[Lineage] = []
PROPOSED: set[str] = set()
SUPERSEDES: dict[str, str] = {}
NOT_REGISTERED: dict[str, str] = {
    "C1.merge_two_sorted[cmp shape]": "the comparison count is len(a) + len(b) minus the leftover, and the leftover is usually one element: 'len(a) + len(b) - 1' hits 0.50-0.57 of the shape at levels 1, 3 and 5 (battery R.len_a+len_b-1); the leftover cannot be hidden by construction",
    "C1.majority_vote_scan[cand shape]": "the final candidate equals the LAST element in 0.75-0.79 of the shape (battery num[-k] rule, levels 1-5) once the old redraws are gone; it is inherent to the pairing scan (whenever the count is 0 before the last element the last element becomes the candidate); the old redraws that hid it were conditional on heuristic outcomes (R-1) and moved the tell to the elements next to the last",
    "C1.merge_two_sorted[out shape]": "the partial output list is sorted(a + b) without the leftover; 'sorted all but last' hits 0.50-0.52 of that shape (audit R.sorted_all_but_last); the leftover cannot be hidden by construction",
    "C1.sieve_marking[count shape]": "the count of flags still 1 after striking is, in 36-48 % of the shape, the count of ones at indices 0, 1 and at primes (audit R.ones_minus_strikes_naive); with an all-ones start it would be a prime-count lookup",
    "C1.turtle_walk[manhattan shape]": "distance equals the number of F commands whenever the path does not double back (audit count_F 0.79 in the shape at level 1); turns do not remove it by construction at short lengths",
    "C1.turtle_walk[far shape]": "same reason as the manhattan shape (audit count_F 0.81 in the shape at level 1)",
}
Builder = Callable[[int, random.Random], Built]


def rev2(family: str, supersedes: str | None = None, proposed: bool = False) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"C1.{fn.__name__}"
        if any(x.id == lid for x in REV2) or any(x.id == lid for x in lineages_of("C1")):
            raise ValueError(f"duplicate lineage id {lid}")
        REV2.append(Lineage(lid, "C1", family, fn))
        if supersedes:
            SUPERSEDES[lid] = supersedes
        if proposed:
            PROPOSED.add(lid)
        return fn

    return deco


def load_rev2() -> list[Lineage]:
    import studies.m0.lineages_c1_rev2_traced  # noqa: F401  (registers the PROPOSED shapes)

    return sorted(REV2, key=lambda x: x.id)


def call(fn: str, *args: list) -> list:
    return ["call", fn, *args]


# ------------------------------------------------------------------------------------------------ 2. cellular_update: no fixed identifier


@rev2("simulation", supersedes="C1.cellular_update")
def cellular_update_r2(level: int, r: random.Random) -> Built:
    """As ``cellular_update`` (one-dimensional automaton on a ring from an eight-entry rule table, fresh row per generation; shapes: the row,
    the sum over cells of index times cell value) but the accumulator of the weighted shape is one of the six drawn names, so it can never collide
    with the loop variable (the old fixed name ``w`` did, in 3.7 % of weighted draws)."""
    cells, rule, nxt, g, i, w = names(r, 6)
    size = 5 + level
    gens = (1, 2, 3, 3, 4, 4, 5)[level]
    init = [r.randint(0, 1) for _ in range(size)]
    tbl = [r.randint(0, 1) for _ in range(8)]
    from studies.m0.core import Retry

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
        prog += [["set", w, N(0)], ["for", i, N(0), N(size), 1, [["aug", w, "+", B("*", V(i), IDX(V(cells), V(i)))]]], ["print", V(w)]]
    return finish(prog)


# ------------------------------------------------------------------------------------------------ 3. shortcuts by construction


@rev2("simulation", supersedes="C1.turtle_walk")
def turtle_walk_r2(level: int, r: random.Random) -> Built:
    """Walker with position (x, y) and heading d in 0..3 reading a LIST of integer commands: 1, 2 or 3 move forward that many cells in the
    current heading; 4 turns one way; 5 turns the other way; 6 (from level 3) moves one cell backward. What each heading means and which turn adds
    what is written in the code. Compared with ``turtle_walk`` (letters F, L, R, B, where the number of F commands equalled the distance
    in about 0.8 of the distance shapes) the step lengths vary and turns are as frequent as steps, so no count of commands gives a coordinate, and the
    distance shapes are dropped (NOT REGISTERED, see ``NOT_REGISTERED``). Shapes: the final position written 'x,y'; the final x; the final y; the
    sum of the forward steps made while the heading was 2 or 3 (traced through the heading)."""
    cmds, x, y, d, i, c, cnt = names(r, 7)
    n = (6, 8, 10, 12, 14, 16, 18)[level]
    pool = [1, 2, 3, 4, 4, 5, 5] + ([6] if level >= 3 else [])
    text = [r.choice(pool) for _ in range(n)]
    rot = r.randint(0, 3)
    base = [("y", 1), ("x", 1), ("y", -1), ("x", -1)]
    headings = [base[(h + rot) % 4] for h in range(4)]
    turn_l = r.choice((1, 3))
    turn_r = (4 - turn_l) % 4
    d0 = r.randint(0, 3)
    shape = r.choice(("pos", "x", "y", "far_half"))

    def move(sign: int, amount: list) -> list:
        acts = [["aug", x if axis == "x" else y, "+" if step * sign > 0 else "-", amount] for axis, step in headings]
        node: list = [acts[3]]
        for h in (2, 1, 0):
            node = [["if", C("==", V(d), N(h)), [acts[h]], node]]
        return node

    forward = move(1, V(c))
    if shape == "far_half":
        forward = [*forward, ["if", C(">=", V(d), N(2)), [["aug", cnt, "+", V(c)]], []]]
    arms: list = [["if", C("<=", V(c), N(3)), forward,
                   [["if", C("==", V(c), N(4)), [["set", d, B("%", B("+", V(d), N(turn_l)), N(4))]],
                     [["if", C("==", V(c), N(5)), [["set", d, B("%", B("+", V(d), N(turn_r)), N(4))]],
                       [["if", C("==", V(c), N(6)), move(-1, N(1)), []]]]]]]]]
    prog: list[list] = [["set", cmds, LIST(text)], ["set", x, N(0)], ["set", y, N(0)], ["set", d, N(d0)]]
    if shape == "far_half":
        prog.append(["set", cnt, N(0)])
    prog.append(["for", i, N(0), call("len", V(cmds)), 1, [["set", c, IDX(V(cmds), V(i))], *arms]])
    if shape == "pos":
        prog.append(["print", B("+", B("+", call("str", V(x)), S(",")), call("str", V(y)))])
    else:
        prog.append(["print", {"x": V(x), "y": V(y), "far_half": V(cnt)}[shape]])
    return finish(prog)


@rev2("simulation", supersedes="C1.bytecode_loop")
def bytecode_loop_r2(level: int, r: random.Random) -> Built:
    """As ``bytecode_loop`` (code is a flat list of (opcode, argument) pairs; a program counter fetches a pair, advances by two, then acts on
    acc and reg; opcode numbers are a random assignment written in the code) with two changes made by construction. (1) From level 1 the
    program contains exactly three skip pairs, at random positions after the first pair and before the last, and a
    skip fires when acc and its argument have the same parity (about one time in two), so the sum of ALL arguments is the sum of the executed
    ones only when no skip fires. (2) The register shape is offered whenever the code contains a store pair (no condition on the value).
    Ops: add arg; multiply by arg; subtract arg (from level 0); skip the next pair if acc % 2 == arg % 2 (from level 1); acc = acc % arg
    (from level 2); reg = acc and acc = acc + reg (from level 3). Shapes: final acc, the sum of the arguments of the pairs executed
    (from level 1; a skipped pair does not count), final reg. 4 to 12 pairs."""
    code, pc, acc, reg, op, arg, ex = names(r, 7)
    n_pairs = (4, 7, 8, 9, 10, 12, 14)[level]
    ops = ["add", "mul", "sub"] + (["skip"] if level >= 1 else []) + (["mod"] if level >= 2 else []) + (["store", "load"] if level >= 3 else [])
    num = dict(zip(ops, r.sample(range(1, 10), len(ops)), strict=True))
    plain = [o for o in ops if o != "skip"]
    skips = set(r.sample(range(1, n_pairs - 1), 3)) if "skip" in ops else set()
    args = {"add": (1, 9), "mul": (2, 3), "sub": (1, 9), "skip": (0, 9), "mod": (2, 9), "store": (1, 9), "load": (1, 9)}
    pairs: list[tuple[str, int]] = []
    for k in range(n_pairs):
        o = "add" if k == 0 else ("skip" if k in skips else r.choice(plain))
        pairs.append((o, r.randint(*args[o])))
    has_store = any(o == "store" for o, _ in pairs)
    shapes = ["acc"] + (["sumarg"] if level >= 1 else []) + (["reg"] if has_store else [])
    shape = r.choice(shapes)
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
    prog.append(["while", C("<", V(pc), call("len", V(code))), body])
    prog.append(["print", {"acc": V(acc), "sumarg": V(ex), "reg": V(reg)}[shape]])
    return finish(prog)


@rev2("lists", supersedes="C1.merge_two_sorted")
def merge_two_sorted_r2(level: int, r: random.Random) -> Built:
    """As ``merge_two_sorted`` (comparison loop of a two-pointer merge; values repeat across the lists, ties matter) with TWO shapes dropped
    (NOT REGISTERED, see ``NOT_REGISTERED``): the partial output list (it is sorted(a + b) minus the leftover) and the comparison count
    (len(a) + len(b) - 1 hits 0.50-0.57 of its cell at every level). The one shape kept: the number of times the source list changed."""
    a, b, i, j, out, cnt, src = names(r, 7)
    na, nb = r.randint(3 + level // 2, 4 + level), r.randint(3 + level // 2, 4 + level)
    hi = max(na, nb) + 3 + level
    la, lb = sorted(r.randint(1, hi) for _ in range(na)), sorted(r.randint(1, hi) for _ in range(nb))
    cmp_op = r.choice(("<=", "<"))
    take_a: list[list] = [["if", C("!=", V(src), N(0)), [["aug", cnt, "+", N(1)], ["set", src, N(0)]], []], ["append", out, IDX(V(a), V(i))], ["aug", i, "+", N(1)]]
    take_b: list[list] = [["if", C("!=", V(src), N(1)), [["aug", cnt, "+", N(1)], ["set", src, N(1)]], []], ["append", out, IDX(V(b), V(j))], ["aug", j, "+", N(1)]]
    prog: list[list] = [["set", a, LIST(la)], ["set", b, LIST(lb)], ["set", i, N(0)], ["set", j, N(0)], ["set", out, ["list"]], ["set", cnt, N(0)], ["set", src, N(-1)]]
    prog += [["while", AND(C("<", V(i), call("len", V(a))), C("<", V(j), call("len", V(b)))), [["if", C(cmp_op, IDX(V(a), V(i)), IDX(V(b), V(j))), take_a, take_b]]], ["print", V(cnt)]]
    return finish(prog)


@rev2("lists", supersedes="C1.sieve_marking")
def sieve_marking_r2(level: int, r: random.Random) -> Built:
    """As ``sieve_marking`` (sieve marking pass over a literal 0/1 flag list with a stated start rule) with the count shape dropped (NOT
    REGISTERED, see ``NOT_REGISTERED``). Shapes: the sum of the indices that remain 1, the sum of the indices struck (every strike write counts, re-strikes too; replaces the old count
    of strike writes, whose answers were concentrated on a few small values).
    10 to 38 flags."""
    fl, i, j, k, tot = names(r, 5)
    n = (10, 13, 17, 22, 27, 32, 38)[level]
    flags = [1 if r.random() < 0.75 else 0 for _ in range(n)]
    start = r.choice((B("*", V(i), V(i)), B("+", V(i), V(i)), B("*", N(3), V(i))))
    shape = r.choice(("indexsum", "strikesum"))
    strike: list[list] = [["setidx", fl, V(j), N(0)], ["aug", j, "+", V(i)]]
    if shape == "strikesum":
        strike.insert(0, ["aug", tot, "+", V(j)])
    prog: list[list] = [["set", fl, LIST(flags)], ["set", tot, N(0)],
                        ["for", i, N(2), N(n), 1, [["if", C("==", IDX(V(fl), V(i)), N(1)), [["set", j, start], ["while", C("<", V(j), N(n)), strike]], []]]]]
    if shape == "indexsum":
        prog.append(["for", k, N(0), N(n), 1, [["if", C("==", IDX(V(fl), V(k)), N(1)), [["aug", tot, "+", V(k)]], []]]])
    prog.append(["print", V(tot)])
    return finish(prog)


# ------------------------------------------------------------------------------------------------ 6/7. recursive_calls split, widened capacity


@rev2("functions", supersedes="C1.recursive_calls")
def recursive_calls_r2(level: int, r: random.Random) -> Built:
    """Recursive definitions that are NOT the fib-like recurrences (those two shapes, 'two' and 'tri', moved to ``fib_shapes_recursive`` in the
    fib_like cluster). Shapes: halving split f(n // 2) and f(n - n // 2) with random multipliers plus n % m; index recursion over a list literal
    (skip or add by a parity or divisibility test); mutual recursion of two functions with random multipliers and offsets. Parameters are widened
    (multipliers 1-4, offsets 0-6, moduli 2-5, base values) so each shape has far more than a few hundred distinct programs per level."""
    f, g = r.sample(FUNCS, 2)
    n, i, xs = names(r, 3)
    shape = r.choice(("split", "listfold", "mutual"))
    a, b, c = r.randint(1, 4), r.randint(1, 4), r.randint(0, 6)
    b0, b1 = r.randint(0, 6), r.randint(1, 7)
    m = r.randint(2, 5)
    if shape == "split":
        arg = r.randint(6 + 4 * level, 12 + 6 * level)
        half = B("//", V(n), N(2))
        fn = ["def", f, [n], [["if", C("<", V(n), N(2)), [["ret", N(b1)]], [["ret", B("+", B("+", B("*", call(f, half), N(a)), B("*", call(f, B("-", V(n), half)), N(b))), B("%", V(n), N(m)))]]]]]
        prog = [fn, ["print", call(f, N(arg))]]
    elif shape == "listfold":
        size = 4 + 2 * level
        vals = [r.randint(1, 9) for _ in range(size)]
        test = C("==", B("%", IDX(V(xs), V(i)), N(m)), N(r.randrange(m)))
        nxt = call(f, V(xs), B("+", V(i), N(1)))
        fn = ["def", f, [xs, i], [["if", C(">=", V(i), call("len", V(xs))), [["ret", N(b0)]], [["if", test, [["ret", B("+", IDX(V(xs), V(i)), nxt)]], [["ret", B("-", B("*", N(a + 1), nxt), N(c))]]]]]]]
        prog = [fn, ["print", call(f, LIST(vals), N(0))]]
    else:
        arg = 3 + 2 * level + r.randint(0, 1)
        fa = ["def", f, [n], [["if", C("<", V(n), N(1)), [["ret", N(b1)]], [["ret", B("+", call(g, B("-", V(n), N(1))), N(c))]]]]]
        fb = ["def", g, [n], [["if", C("<", V(n), N(1)), [["ret", N(b0)]], [["ret", B("+", B("*", call(f, B("-", V(n), N(1))), N(a)), B("*", call(f, B("//", V(n), N(2))), N(b)))]]]]]
        prog = [fa, fb, ["print", call(f, N(arg))]]
    return finish(prog)


@rev2("accumulators", supersedes="C1.recursive_calls")
def fib_shapes_recursive(level: int, r: random.Random) -> Built:
    """The two fib-like recursive shapes of the old ``recursive_calls``: two-branch (f(n-1), f(n-2) with small multipliers) and three-branch
    (n-1, n-2, n-3). Parameters widened (multipliers 1-5, offsets 0-9, base values 0-9, argument up to +2) after the capacity count showed about 1,570 programs per level. Per ruling R-2 and the audit (B6) these are shapes of the ``fib_like`` cluster (a linear recurrence), written recursively,
    and carry that cluster in ``lineages_c1_clusters``. Family: accumulators, as fib_like."""
    f = r.choice(FUNCS)
    (n,) = names(r, 1)
    a, b, c = r.randint(1, 5), r.randint(1, 5), r.randint(0, 9)
    b0, b1 = r.randint(0, 9), r.randint(1, 9)
    if r.random() < 0.5:
        arg = 3 + level + r.randint(0, 2)
        fn = ["def", f, [n], [["if", C("<", V(n), N(2)), [["ret", B("+", V(n), N(b1))]], [["ret", B("+", B("+", B("*", call(f, B("-", V(n), N(1))), N(a)), B("*", call(f, B("-", V(n), N(2))), N(b))), N(c))]]]]]
    else:
        arg = 3 + level + r.randint(0, 1)
        fn = ["def", f, [n], [["if", C("<", V(n), N(3)), [["ret", B("+", V(n), N(b0))]], [["ret", B("+", B("+", call(f, B("-", V(n), N(1))), call(f, B("-", V(n), N(2)))), B("-", call(f, B("-", V(n), N(3))), N(c)))]]]]]
    return finish([fn, ["print", call(f, N(arg))]])


@rev2("while", supersedes="C1.fast_power")
def fast_power_r2(level: int, r: random.Random) -> Built:
    """As ``fast_power`` (modular exponentiation by repeated squaring; shapes: the result, the final b, the sum of b at the start of each round)
    with the level-0 space widened: exponent bits 2 + level, plus one more bit at level 0 half the time, and the modulus up to 40 at level 0.
    The formula-answerable status of these shapes (result = pow) is unchanged and goes to the human lead."""
    res, b, e, m, tot = names(r, 5)
    from studies.m0.core import Retry

    mod = r.randint(5, 40 if level == 0 else 25 + 10 * level)
    base = r.randint(2, mod + 6)
    if base % mod in (0, 1):
        raise Retry
    bits = 2 + level + (r.randint(0, 1) if level == 0 else 0)
    ex = r.randint(2 ** (bits - 1), 2**bits - 1)
    shape = r.choice(("res", "base", "bsum"))
    rnd: list[list] = [["aug", tot, "+", V(b)]] if shape == "bsum" else []
    prog: list[list] = [["set", res, N(1)], ["set", b, N(base)], ["set", e, N(ex)], ["set", m, N(mod)]]
    if shape == "bsum":
        prog.append(["set", tot, N(0)])
    prog.append(["while", C(">", V(e), N(0)), [*rnd, ["if", C("==", B("%", V(e), N(2)), N(1)), [["set", res, B("%", B("*", V(res), V(b)), V(m))]], []], ["set", b, B("%", B("*", V(b), V(b)), V(m))], ["set", e, B("//", V(e), N(2))]]])
    prog.append(["print", {"res": V(res), "base": V(b), "bsum": V(tot)}[shape]])
    return finish(prog)


@rev2("simulation", supersedes="C1.circle_elimination")
def circle_elimination_r2(level: int, r: random.Random) -> Built:
    """As ``circle_elimination`` (Josephus counting around a ring of flags; shapes: the index struck last, the sum of the indices struck, the
    survivor) with the space widened: n = 9 + level, plus one more flag at level 0 half the time, and the position the counting starts from is drawn (stated in the code) instead of always the last flag."""
    flags, pos, rd, c, tot, i, surv = names(r, 7)
    from studies.m0.core import Retry

    n = 9 + level + (r.randint(0, 1) if level == 0 else 0)
    start = [1 if r.random() < 0.85 else 0 for _ in range(n)]
    m = sum(start)
    if m < 4:
        raise Retry
    kk = r.randint(2, 5)
    pos0 = r.randrange(n)  # the counting starts from a stated position, not always the last flag
    shape = r.choice(("last", "sum", "survivor"))
    rounds = m - 1 if shape == "survivor" else r.randint(2, m - 1)
    strike: list[list] = [["set", c, N(0)], ["while", C("<", V(c), N(kk)), [["set", pos, B("%", B("+", V(pos), N(1)), N(n))], ["if", C("==", IDX(V(flags), V(pos)), N(1)), [["aug", c, "+", N(1)]], []]]], ["setidx", flags, V(pos), N(0)]]
    if shape == "sum":
        strike.append(["aug", tot, "+", V(pos)])
    prog: list[list] = [["set", flags, LIST(start)], ["set", pos, N(pos0)]]
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


@rev2("minmax", supersedes="C1.majority_vote_scan")
def majority_vote_scan_r2(level: int, r: random.Random) -> Built:
    """As ``majority_vote_scan`` (Boyer-Moore pairing scan; shapes: the final candidate; 'candidate count'; the number of times a new candidate
    was taken) WITHOUT the old redraws (final candidate neither first nor last element, mode 25 %). Those redraws were conditioned on two
    heuristics' outcomes (ruling R-1) and moved the tell to the elements next to the last: the audit battery's literal-position rules reached
    0.85 inside the candidate shape at level 4. Items are now drawn as they come, and the candidate-alone shape is dropped (NOT REGISTERED, see
    ``NOT_REGISTERED``: the final candidate is the last element in about 0.75-0.79 of its cell, inherent to the pairing scan). Shapes: 'candidate
    count' and the sum of the candidates taken (the value of every new candidate, added when it is taken). The list has 6 + 2 * level values from 1 to 6."""
    xs, cand, cnt, i, rep = names(r, 5)
    n = 6 + 2 * level
    k = r.randint(3, 6)
    vals = [r.randint(1, k) for _ in range(n)]
    shape = r.choice(("pair", "repl"))
    take: list[list] = [["set", cand, IDX(V(xs), V(i))], ["set", cnt, N(1)]]
    if shape == "repl":
        take.append(["aug", rep, "+", V(cand)])
    body = [["if", C("==", V(cnt), N(0)), take, [["if", C("==", IDX(V(xs), V(i)), V(cand)), [["aug", cnt, "+", N(1)]], [["aug", cnt, "-", N(1)]]]]]]
    prog: list[list] = [["set", xs, LIST(vals)], ["set", cand, N(0)], ["set", cnt, N(0)]]
    if shape == "repl":
        prog.append(["set", rep, N(0)])
    prog.append(["for", i, N(0), N(n), 1, body])
    prog.append(["print", {"cand": V(cand), "pair": B("+", B("+", call("str", V(cand)), S(" ")), call("str", V(cnt))), "repl": V(rep)}[shape]])
    return finish(prog)
