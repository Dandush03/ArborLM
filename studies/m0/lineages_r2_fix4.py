# ruff: noqa: E501
"""R2 fix round 4 (the narrow repair round of ``LEAD_RULINGS_5.md``: R-24 to R-29). Same ids ``R2.<name>``, own registry ``FIX4``; nothing is put in ``core.REGISTRY``.

Allowed repairs only (R-25): (b) a wording defect named in audit 4, (c) a collapsed level pair. No new lineage, no new procedure, no redraw conditional on an answer or a rule. Self-checked,
not independent review, not Astra validation, not human approval.

(b) ``count_divisible``: audit 4 (section 2) found 'the sum of the numbers in this list that are divisible by m and greater than t' open to a set-of-values reading that changes the key on 0.27-0.38
of items. The question now says that every entry counts each time it appears. The builder is the fix-round-3 builder (same draws), only the sentence differs.

(c) Collapsed level pairs. A pair of adjacent levels is collapsed when no numeric leaf of the structured form differs in distribution between them (two-sample KS statistic below 0.20 on 300 + 300
draws; ``r2_fix4_levels``). Five surviving lineages had a ``level // 2`` size parameter (identical levels 0/1, 2/3, 4/5) or a size range that hardly moves. Each is rewritten with the stated parameter:
- ``caesar_shift``: 1 + level words (was 1 + level // 2).
- ``cheapest_network``: 8 + level towns (was 8 + level // 2); the other construction is unchanged.
- ``interval_scheduling``: 5 + level blocks (was 5 + level // 2); the other construction is unchanged.
- ``expression_eval``: the chain has 3 + level (+0/1) terms (ranked) or 4 + level (+0/1) numbers (left_to_right) (was ``level // 2``); the planted structure and the rest are unchanged.
- ``crt_smallest``: the moduli are sampled from ``range(3 + 5*level, 30 + 10*level)`` (the widened rev2 shape of the set was ``range(3, 30 + 10*level)``, kept wide for capacity), so the smallest allowed modulus rises with the level; k = 2 congruences up to level 2 and 3 above, as before.
Level 0 of each is the level 0 of the fix-round-3 shape except where the formula above moves it (none of the five: at level 0 every formula equals the old one).
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, Retry
from studies.m0.lineages_r2 import ALPHA
from studies.m0.lineages_r2_common import and_, lst
from studies.m0.lineages_r2_fix3 import _pick_earliest_finish
from studies.m0.lineages_r2_fix3_b import _num, _paren_sum
from studies.m0.lineages_r2_graphs import mst_weight
from studies.m0.lineages_r2_parsing import evaluate
from studies.m0.vocab import PSEUDO, TOWNS

FIX4: list[Lineage] = []
SUPERSEDES: dict[str, str] = {}
Builder = Callable[[int, random.Random], Built]


def fix4(family: str, supersedes: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R2.{fn.__name__}"
        if any(x.id == lid for x in FIX4):
            raise ValueError(f"duplicate {lid}")
        FIX4.append(Lineage(lid, "R2", family, fn))
        SUPERSEDES[lid] = supersedes
        return fn

    return deco


def load_fix4() -> list[Lineage]:
    return sorted(FIX4, key=lambda x: x.id)


# ---------------------------------------------------------------- (b) wording


@fix4("counting", "R2.count_divisible")
def count_divisible(level: int, r: random.Random) -> Built:
    """Procedure and draws as in fix round 3 (``lineages_r2_fix3_c.count_divisible``); structured: {"xs": [int], "m": int, "t": int, "ask": "sum"}. Wording (audit 4, section 2): the question adds that
    every entry counts each time it appears. Answer: the sum of the entries that are divisible by m and greater than t, repeats included. Levels: 18 + 4*level numbers (stated parameter: list length)."""
    m = r.choice((2, 3, 4))
    hi = 99 + 100 * (level // 2)
    t = m * r.randint(-(-(hi // 4) // m), (3 * hi // 5) // m)
    n = 18 + 4 * level
    xs = [r.randint(10, hi) for _ in range(n - 1)] + [t]
    r.shuffle(xs)
    sel = [x for x in xs if x % m == 0 and x > t]
    q = (f"What is the sum of the numbers in this list that are divisible by {m} and greater than {t}? Every entry of the list counts each time it appears: "
         f"a number that is listed twice is added twice if it qualifies. List: {lst(xs)}.")
    return Built(q, {"xs": xs, "m": m, "t": t, "ask": "sum"}, str(sum(sel)), "number", None)


# ---------------------------------------------------------------- (c) levels


@fix4("caesar", "R2.caesar_shift")
def caesar_shift(level: int, r: random.Random) -> Built:
    """Procedure: shift each letter by k with wrap-around (core R2 text). structured: {"text": str, "k": int}. Stated parameter: 1 + level words (core: 1 + level // 2, so levels 0/1, 2/3, 4/5 were the same)."""
    ws = r.sample(PSEUDO, 1 + level)
    k = r.randint(1, 25)
    text = " ".join(ws)
    ans = "".join(" " if c == " " else ALPHA[(ALPHA.index(c) + k) % 26] for c in text)
    q = f"Shift every letter of '{text}' forward by {k} places in the alphabet, wrapping from z back to a. Spaces stay. What is the result?"
    return Built(q, {"text": text, "k": k}, ans, "text", None)


@fix4("graphs", "R2.cheapest_network")
def cheapest_network(level: int, r: random.Random) -> Built:
    """Procedure: cycle-avoiding cheapest-edge selection (as fix round 3). structured: {"towns": [name], "cables": [[a, b, cost]]}. Towns are points on a 26 x 26 grid, a cable costs the walking
    distance (at least 1), the 2n cheapest pairs are offered. Stated parameter: n = 8 + level towns (fix round 3: 8 + level // 2). A draw whose cables do not connect all the towns is drawn again (validity)."""
    n = 8 + level
    pts = [(r.randint(0, 25), r.randint(0, 25)) for _ in range(n)]
    allp = sorted((max(1, abs(pts[a][0] - pts[b][0]) + abs(pts[a][1] - pts[b][1])), a, b) for a, b in itertools.combinations(range(n), 2))
    edges = [[a, b, w] for w, a, b in allp[: 2 * n]]
    ans = mst_weight(n, edges)
    if ans is None:
        raise Retry
    towns = r.sample(TOWNS, n)
    r.shuffle(edges)
    cables = [[towns[a], towns[b], w] for a, b, w in edges]
    text = " ".join(f"A cable between {a} and {b} would cost {w}." for a, b, w in cables)
    q = (f"The towns {and_(sorted(towns))} must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. {text} "
         "What is the smallest total cost of a set of cables that joins all the towns?")
    return Built(q, {"towns": towns, "cables": cables}, str(ans), "number", None)


@fix4("greedy", "R2.interval_scheduling")
def interval_scheduling(level: int, r: random.Random) -> Built:
    """Procedure: earliest-finish selection (as fix round 3). structured: {"meetings": [[start, end]], "ask": "chosen"}. The day is made of independent blocks of 4-6 meetings, each in its own window
    (windows 24 minutes apart; a meeting starts 0-12 minutes into its window and lasts 2-9), numbered in a shuffled order; the answer is the list of chosen numbers (ties: the smaller number).
    Stated parameter: 5 + level blocks (fix round 3: 5 + level // 2)."""
    nb = 5 + level
    iv: list[list[int]] = []
    for b in range(nb):
        for _ in range(r.randint(4, 6)):
            s = 24 * b + r.randint(0, 12)
            iv.append([s, s + r.randint(2, 9)])
    r.shuffle(iv)
    text = "; ".join(f"meeting {i + 1} runs from {s} to {e}" for i, (s, e) in enumerate(iv))
    q = (f"A person can attend only one meeting at a time. Times are whole numbers of minutes: {text}. Two meetings clash if they share any stretch of time; "
         "a meeting that ends at the very minute another starts does not clash with it. The person chooses meetings in rounds: in each round, among the meetings that do not clash with any meeting already chosen, "
         "the one that ends first is chosen (if two end at the same minute, the one with the smaller number); rounds go on until no meeting can be added. "
         "Which meetings are chosen? Give their numbers, smallest first, separated by commas.")
    return Built(q, {"meetings": iv, "ask": "chosen"}, lst(_pick_earliest_finish(iv)), "list", None)


@fix4("parsing", "R2.expression_eval")
def expression_eval(level: int, r: random.Random) -> Built:
    """Procedure: evaluate an infix expression under a stated convention (as fix round 3; the planted structure and the wording are unchanged). structured: {"text": str, "convention": "ranked" | "left_to_right"}.
    Stated parameter: a chain of 3 + level (+0/1) terms (ranked) or 4 + level (+0/1) numbers (left_to_right) (fix round 3: ``level // 2``). Numbers are 2..9 (2..20 from level 4)."""
    conv = r.choice(("ranked", "left_to_right"))
    if conv == "ranked":
        k = 3 + level + r.randint(0, 1)
        terms = [[str(_num(r, level))] for _ in range(k)]
        ops = [r.choice("+-") for _ in range(k - 1)]
        i = r.randrange(1, k)
        terms[i].append(str(_num(r, level)))
        j = r.randrange(0, k - 2)
        ops[j], ops[j + 1] = "-", "+"
        terms[i][r.randrange(len(terms[i]))] = _paren_sum(r, level)
        for t_ in terms:
            if level >= 2 and r.random() < 0.15 * (level // 2):
                t_.append(str(_num(r, level)))
        if level >= 3:
            for t_ in terms:
                if len(t_) > 1 and r.random() < 0.3:
                    f = r.randrange(len(t_))
                    if t_[f].isdigit():
                        t_[f] = _paren_sum(r, level)
        text = ""
        for n_, t_ in enumerate(terms):
            text += ("" if n_ == 0 else f" {ops[n_ - 1]} ") + " * ".join(t_)
        q = (f"Work out {text}. Use these rules, in this order, also inside every pair of parentheses: do what is inside parentheses first, innermost first; then do all the multiplications, from left to right; "
             "then do all the additions and subtractions together as one group, strictly from left to right (so 8 - 3 + 2 is worked as (8 - 3) + 2 = 7, and 8 + 3 - 2 as (8 + 3) - 2 = 9). What is the result?")
        ans = evaluate(text, True)
    else:
        k = 4 + level + r.randint(0, 1)
        atoms = [str(_num(r, level)) for _ in range(k)]
        ops = [r.choice("+-*") for _ in range(k - 1)]
        i = r.randrange(0, k - 2)
        ops[i], ops[i + 1] = r.choice("+-"), "*"
        p = r.randrange(1, k)
        atoms[p] = f"({_num(r, level)} {r.choice('+-')} {_num(r, level)} * {_num(r, level)})"
        for n_ in range(k):
            if n_ != p and n_ >= 1 and level >= 2 and r.random() < 0.1 * (level // 2):
                atoms[n_] = f"({_num(r, level)} {r.choice('+-*')} {_num(r, level)})"
        text = atoms[0]
        for n_ in range(1, k):
            text += f" {ops[n_ - 1]} {atoms[n_]}"
        q = (f"Work out {text} by this rule, which is not the usual one: work out each pair of parentheses first, innermost first, and inside a pair of parentheses use the same rule as outside; "
             "the rule is that the operators are done strictly in the order they are written, from left to right, and multiplication gets no priority over addition or subtraction "
             "(so 2 + 3 * 4 is worked as (2 + 3) * 4 = 20). What is the result?")
        ans = evaluate(text, False)
    return Built(q, {"text": text, "convention": conv}, str(ans), "number", None)


@fix4("numtheory", "R2.crt_smallest")
def crt_smallest(level: int, r: random.Random) -> Built:
    """Procedure: combine congruences (Chinese remainder). structured: {"congruences": [[remainder, modulus]]} with pairwise coprime moduli. Answer: the smallest positive integer x with x mod modulus =
    remainder for every pair. Stated parameter: the moduli are sampled from range(3 + 5*level, 30 + 10*level), so the smallest and the largest allowed modulus both rise with the level (rev2: range(3, 30 + 10*level),
    whose levels 0-2 and 3-6 hardly differ; the wide range is kept for capacity); k = 2 congruences up to level 2, 3 above."""
    k = 2 if level <= 2 else 3
    ms = sorted(r.sample(range(3 + 5 * level, 30 + 10 * level), k))
    if any(math.gcd(ms[i], ms[j]) != 1 for i in range(k) for j in range(i + 1, k)):
        raise Retry
    prod = math.prod(ms)
    x = r.randint(1, prod)
    cons = [[x % m, m] for m in ms]
    parts = [f"leaves remainder {c} when divided by {m}" for c, m in cons]
    q = "What is the smallest positive whole number that " + ", and ".join(parts) + "?"
    return Built(q, {"congruences": cons}, str(x), "number", None)
