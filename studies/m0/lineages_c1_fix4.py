# ruff: noqa: E501
# The program trees are plain nested lists (the grammar of c1grammar), as in every other C1 lineage module; hence no type parameters on list.
# mypy: disable-error-code="type-arg"
"""C1, narrow repair round ("fix 4"; lead rulings 5, R-24 to R-29; the human lead's fifth decision: shortcut bound 0.15, two-sided, everything else that fails is DROPPED).

NEW file; nothing existing is edited. Nothing is registered. What this module holds:

* ``DROPPED_AUDIT4``: lineages dropped because the fourth audit (``audit4_c1/AUDIT4_C1.md``) names a failure that R-25 does not allow to be repaired (a closed form, a cheap rule above 0.15,
  an answer-conditional reject that is not needed for well-posedness, a capacity failure). Status NOT REGISTERED: excluded from the cluster map, G, fixtures and capacity runs (R-12).
* ``DROPPED_AFTER_REMEASURE`` (filled from the fix-4 measurements, see ``manifests/c1_fix4_survivors.json``): lineages that the re-run of the rule scripts, the level check or the capacity check
  dropped (R-26: no repair after the re-run).
* three lineages whose LEVELS were collapsed and are repaired as the human lead allowed (repair (c): every level produces distinct items, difficulty rising by a stated parameter; the algorithm
  is unchanged): ``func_branch_f4`` (``func_branch`` ignored the level at 0 vs 1 and from 3 up), ``func_compose_f4`` (``func_compose_f3`` likewise) and ``slices_f4`` (``slices`` drew the same
  string length for level pairs). The repaired lineages are re-measured with everything else (R-26): if they fail they are dropped, not repaired again.
* two lineages that keep ONE shape of a fix-3 lineage (ruling R-20 for ``fast_power_f3``: its ``res`` shape only; the audit's advice for ``sieve_marking_f3``: its strike-sum shape only, the
  flag-list shape has an order-free closed form). They are the fix-3 builders with the dropped shapes removed from the shape draw: no redraw, no new shape, no new algorithm.
* ``current_after_audit4()``: the ids in force after the drops named by the audit (the fix-3 builders unchanged, plus the two above), before the fix-4 measurements.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, lineages_of
from studies.m0.lineages_c1 import FUNCS, LETTERS, PSEUDO
from studies.m0.lineages_c1_common import IDX, LIST, B, C, N, S, V, finish, load_batch1, names
from studies.m0.lineages_c1_fix3 import load_fix3
from studies.m0.lineages_c1_rev2 import load_rev2

FIX4: list[Lineage] = []
SUPERSEDES4: dict[str, str] = {}
Builder = Callable[[int, random.Random], Built]

# audit-4 reasons. Every entry is a drop (NOT REGISTERED); the reason names the audit section. R-19: an answer-conditional reject is kept only where the item is not well posed without it.
DROPPED_AUDIT4: dict[str, str] = {
    "C1.partition_pass_f3": "audit4 section 3: closed form 2*xs[0] + xs[1] answers the disp shape in 1.000 of items and a fixed permutation answers the list and mid shapes in 1.000 (every level); R-24/R-25 closed form",
    "C1.loop_sum": "audit4 section 3: arithmetic-series closed form 1.000 at every level; R-25 closed form",
    "C1.grid_path_table": "audit4 sections 3, 4, 5: greedy path 0.37-0.89 in shape (level-wide 0.78), binomial 0.37 at level 0; and it rejects draws whose count is 0 (216 retries), a valid answer: R-19 not needed for well-posedness",
    "C1.string_pair_table": "audit4 section 5: edit-cell hamming + |len a - len b| 0.43-0.98 and LCS-cell common-letter multiset 0.47-0.85 in shape, level-wide 0.395 (above 0.15)",
    "C1.coin_change_table_f3": "audit4 section 5: fewest-coin greedy 0.52-0.84, ceil(T / max coin) 0.53-0.68 in shape, level-wide 0.328; and it rejects draws whose answer is the unreachable sentinel 99 (147 retries per 2,800), a valid answer: R-19 not needed for well-posedness",
    "C1.bubble_pass": "audit4 section 5: 'move the extreme to the end' 0.58 at level 0 and 0.48 at level 1 (level-wide 0.585)",
    "C1.mirror_pointers": "audit4 sections 4, 5: level-wide 0.230 (above 0.15; the poss shape's most frequent key 0.61 at level 0) and it rejects draws with no unequal pair (1,245 retries), which for the poss shape is the answer 0: R-19 not needed for well-posedness",
    "C1.cellular_update_f3": "audit4 sections 5, 7: level-wide cheap 0.188 (above 0.15); capacity at level 0 is 22,196 at the draw budget, below the demand at G <= 11",
    "C1.majority_vote_scan_f3": "audit4 section 5: level-wide cheap 0.190 (above 0.15); the fix-4 re-run on another draw measured 0.145 (not above), so it is dropped on the audit's figure: a measurement above the bound exists in the union of the scripts' runs",
    "C1.bfs_queue": "audit4 section 5: level-wide cheap 0.247 (target shape: the answer 2 hits 0.36-0.58 in shape); above 0.15",
    "C1.insertion_sort": "NOT REGISTERED in fix 3 (closed form); stays out (brief)",
    "C1.minmax_track": "NOT REGISTERED in fix 3 (closed form); stays out (brief)",
    "C1.kadane_scan": "NOT REGISTERED in fix 3 (closed form); stays out (brief)",
}

# filled from the fix-4 measurements (rule scripts, level check, capacity); see manifests/c1_fix4_survivors.json
DROPPED_AFTER_REMEASURE: dict[str, str] = {}


def f4(supersedes: str, family: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"C1.{fn.__name__}"
        if any(x.id == lid for x in FIX4):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX4.append(Lineage(lid, "C1", family, fn))
        SUPERSEDES4[lid] = supersedes
        return fn

    return deco


@f4("C1.sieve_marking_f3", "lists")
def sieve_marking_f4(level: int, r: random.Random) -> Built:
    """``sieve_marking_f3`` with its flag-list shape removed (audit4: the order-free divisor test answers it in 1.000 of items); the strike-sum shape is the fix-3 builder unchanged.

    Sieve marking pass over a literal 0/1 flag list (flags[2] is always 1; a prime index is 1 with a chance drawn per item from 0.25, 0.4 or 0.5 and any other index with chance 0.9): for i from 2, if
    flags[i] is 1, strike flags[j] = 0 for j = start(i), start(i) + i, ... below n (start(i) = i + i or 3 * i, stated). The answer is the sum of the indices struck (every strike write counts). Difficulty
    parameter by level: the number of flags n = 30, 34, 38, 42, 46, 50, 56 for levels 0 to 6."""
    fl, i, j, tot = names(r, 4)
    n = (30, 34, 38, 42, 46, 50, 56)[level]
    q = r.choice((0.25, 0.4, 0.5))

    def prime(k: int) -> bool:
        return k >= 2 and all(k % d for d in range(2, int(k**0.5) + 1))

    flags = [1 if r.random() < (q if prime(k) else 0.9) else 0 for k in range(n)]
    flags[2] = 1
    start = r.choice((B("+", V(i), V(i)), B("*", N(3), V(i))))
    strike: list[list] = [["aug", tot, "+", V(j)], ["setidx", fl, V(j), N(0)], ["aug", j, "+", V(i)]]
    run: list[list] = [["set", j, start], ["while", C("<", V(j), N(n)), strike]]
    prog: list[list] = [["set", fl, LIST(flags)], ["set", tot, N(0)], ["for", i, N(2), N(n), 1, [["if", C("==", IDX(V(fl), V(i)), N(1)), run, []]]], ["print", V(tot)]]
    return finish(prog)


@f4("C1.fast_power_f3", "while")
def fast_power_f4(level: int, r: random.Random) -> Built:
    """``fast_power_f3`` with its ``res`` shape only (ruling R-20; audit4 section 6: the base and bsum shapes use the exponent only as a round count).

    while e > 0: if e is odd, res = res * b % m; b = (b * b + c) % m (c stated in the code, 1 to 9); e = e // 2; print res. Difficulty parameter by level: the exponent has 3 + level bits
    (levels 0 to 6: 3 to 9 bits) and the modulus is drawn from 40 to 200 + 60 * level. PENDING LEAD REVIEW (as in fix 3): whether a program with the added c is still the fast_power procedure;
    it is filed as its own cluster (R-20)."""
    res, b, e, m = names(r, 4)
    mod = r.randint(40, 200 + 60 * level)
    base = r.randint(2, mod - 1)
    c = r.randint(1, 9)
    bits = 3 + level
    ex = r.randint(2 ** (bits - 1), 2**bits - 1)
    prog: list[list] = [["set", res, N(1)], ["set", b, N(base)], ["set", e, N(ex)], ["set", m, N(mod)]]
    prog.append(["while", C(">", V(e), N(0)), [["if", C("==", B("%", V(e), N(2)), N(1)), [["set", res, B("%", B("*", V(res), V(b)), V(m))]], []], ["set", b, B("%", B("+", B("*", V(b), V(b)), N(c)), V(m))], ["set", e, B("//", V(e), N(2))]]])
    prog.append(["print", V(res)])
    return finish(prog)


def _call(fn: str, *args: list) -> list:
    return ["call", fn, *args]


@f4("C1.func_branch", "functions")
def func_branch_f4(level: int, r: random.Random) -> Built:
    """``func_branch`` with distinct levels. A function with a threshold branch (x > t: a * x - b), an else branch x + c, from level 2 an even test inside the else branch (x // 2), called 2 times (3 from
    level 3, 4 from level 5) with the results added or subtracted. The old builder drew the same program from level 3 up and the same at levels 0 and 1. Stated parameters by level (distinct at every
    level): threshold t from 2 to 12 + 2 * level, call arguments from 0 to 20 + 4 * level, multiplier a from 2 to 4 + level // 2 + 1, offsets b and c from 1 to 9 + level."""
    f = r.choice(FUNCS)
    x = names(r, 1)[0]
    t = r.randint(2, 12 + 2 * level)
    a, b, c = r.randint(2, 5 + level // 2), r.randint(1, 9 + level), r.randint(1, 9 + level)
    other: list[list] = [["ret", B("+", V(x), N(c))]]
    if level >= 2:
        other = [["if", C("==", B("%", V(x), N(2)), N(0)), [["ret", B("//", V(x), N(2))]], other]]
    fn = ["def", f, [x], [["if", C(">", V(x), N(t)), [["ret", B("-", B("*", V(x), N(a)), N(b))]], other]]]
    calls = [_call(f, N(r.randint(0, 20 + 4 * level))) for _ in range(2 + (level >= 3) + (level >= 5))]
    total = calls[0]
    for cl in calls[1:]:
        total = B(r.choice("+-"), total, cl)
    return finish([fn, ["print", total]])


@f4("C1.func_compose_f3", "functions")
def func_compose_f4(level: int, r: random.Random) -> Built:
    """``func_compose_f3`` with distinct levels (the fix-3 builder ignored the level at 0 vs 1 and from 3 up). Compose small functions: f(x) = a * x + b; g is one of f(f(x)) +- c, f(f(x)) - f(x // 2) + c,
    f(f(x) % k) + c; from level 3 h(x) = g(x) % m; from level 2 half the items print the sum or difference of two calls. Stated parameters by level (the level-6 ranges are those of the fix-3 builder): a from 2 to
    3 + level, b and c from 1 to 13 + level, the call argument from -9 to 24 + level, the modulus m from 7 to 17 + 2 * level, k from 7 to 40."""
    f, g, h = r.sample(FUNCS, 3)
    x = names(r, 1)[0]
    a, b, c = r.randint(2, 3 + level), r.randint(1, 13 + level), r.randint(1, 13 + level)
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
        defs.append(["def", h, [x], [["ret", B("%", _call(g, V(x)), N(r.randint(7, 17 + 2 * level)))]]])
        top = h

    def arg() -> list:
        return N(r.randint(-9, 24 + level))

    out = B(r.choice("+-"), _call(top, arg()), _call(top, arg())) if (level >= 2 and r.random() < 0.5) else _call(top, arg())
    return finish([*defs, ["print", out]])


@f4("C1.slices", "slices")
def slices_f4(level: int, r: random.Random) -> Built:
    """``slices`` with distinct levels. The old builder drew a string of ``1 + level // 2 + 1`` pseudo-words, so levels 0 and 1, 2 and 3, 4 and 5 drew strings of the same length. Here the string has
    ``2 + level // 2`` pseudo-words plus ``level % 2`` extra letters (so its length rises at every level: the stated parameter), and the list has ``6 + level`` values as before. The item: s = literal
    (string or list); print s[a:b:c] + s[a:b:c] (or, for a list half the time, the sum of one slice)."""
    s = names(r, 1)[0]
    if r.random() < 0.5:
        w = "".join(r.choice(PSEUDO) for _ in range(2 + level // 2)) + "".join(r.choice(LETTERS) for _ in range(level % 2))
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
    return finish([["set", s, base], ["print", tail]])


def all_written() -> dict[str, Lineage]:
    """Every C1 lineage written so far (old registry, batch 1, revision 2, fix 3, fix 4), by id."""
    return {x.id: x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2(), *load_fix3(), *FIX4]}


def current_after_audit4() -> list[str]:
    """The ids in force after the drops the audit names: the fix-3 current set (audit4 section 1: 37 lineages) minus ``DROPPED_AUDIT4``, with the two one-shape lineages in place of their fix-3 originals."""
    from studies.m0.lineages_c1_fix3 import NOT_REGISTERED as NR3
    from studies.m0.lineages_c1_fix3 import SUPERSEDES3
    from studies.m0.lineages_c1_rev2 import PROPOSED
    from studies.m0.lineages_c1_rev2 import SUPERSEDES as SUP2

    written = all_written()
    superseded = {*SUPERSEDES3.values(), *SUP2.values(), *SUPERSEDES4.values()}
    excluded = {k for k in NR3 if "[" not in k}
    return [i for i in sorted(written) if i not in superseded and i not in PROPOSED and i not in excluded and i not in DROPPED_AUDIT4]


# R-19: every reject (``raise Retry``) in the builders of the SURVIVING lineages, with what it conditions on and why it is needed. The dropped lineages whose reject was on a valid answer
# (coin_change_table_f3: the sentinel 99; grid_path_table: the count 0; mirror_pointers: no unequal pair, which for the poss shape is the answer 0) are in ``DROPPED_AUDIT4``: removing an unneeded
# answer-conditional reject is not an allowed repair (R-25), so they are dropped, not changed.
RETRY_SITES: dict[str, tuple[str, str, str]] = {
    # lineage: (kind, condition, why it is needed for the item to be well posed)
    "C1.run_length_scan": ("answer-conditional", "the 'long' shape with no run of length 2 or more (its answer would be the empty string)", "an empty gold answer is not gradable: the scorer treats an empty answer as no answer (scoring.extract, in_grammar('line', '') is False); the shared finish would refuse it anyway"),
    "C1.string_methods_f3": ("answer-conditional", "an empty string, at any step of the chain or as the answer", "an empty gold answer is not gradable (as above); an empty intermediate string leaves no letter for the next replace step to name"),
    "C1.euclid_gcd_traced_f3": ("validity (structure of the trace)", "equal operands; fewer than max(4, 3 + level // 2) Euclid rounds", "the question asks for the state after R rounds with 1 <= R < the number of rounds (and R from 2 to rounds - 2 for the weighted shape): it has no answer to ask for with fewer rounds"),
    "C1.shared_lists_f3": ("validity (structure of the program)", "an alias statement of a name to itself", "'a = a' changes nothing, so the statement says nothing about aliasing"),
    "C1.circle_elimination_r2": ("validity (structure of the program)", "fewer than 4 live flags in the ring", "the counting round needs enough live flags to strike several; with fewer the questions have no elimination order to trace"),
}
# the shared finish (``lineages_c1._finish``, used by every builder) rejects a program that cannot run (ZeroDivisionError, IndexError, ValueError, TypeError, KeyError) and an answer that is not a fixed point of
# the scorer's normalisation (upper case, leading or trailing space, a double space, empty, a final full stop): a gold key that normalisation would change could never be matched by a correct answer.
SHARED_FINISH_REJECT = "answer not a fixed point of scoring.normalise_answer, or the program cannot run (validity)"
