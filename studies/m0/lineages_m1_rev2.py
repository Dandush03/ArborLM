# ruff: noqa: E501
"""M1 batch 1, revision 2 (fix round after the independent audit AUDIT_M0_M1_1 and lead rulings R-1 to R-5).

NEW shapes only; the batch-1 shapes in ``lineages_m1_<family>.py`` are kept unchanged and are SUPERSEDED where a ``_r2`` id exists (``SUPERSEDES``). The four lineages
without a ``_r2`` id (finite_differences, quadratic_area, recurrence_iterate, tiered_pricing) are carried over unchanged: ``load_rev2`` returns the effective set of 21.

Rules applied here (lead rulings 2, 2026-11-25):
  * R-1: NO redraw conditional on a heuristic's outcome. A builder draws its question type FIRST and then loops internally only on validity (a unique answer, a size cap);
    it never raises ``Retry``, so the shape mix of the design holds at every level. A tell is removed by the structure of the problem or the lineage is marked NOT REGISTERED
    (``NOT_REGISTERED``, with the reason).
  * R-4: every convention an answer depends on is stated in the item (leading zero, the meaning of a power, the reversal of a number).
  * R-5: capacity is counted on structure (see ``m1_rev2_gates.py``); names, the setting sentence and presentation order do not count.
Own registry (``REV2``), not ``core.REGISTRY``. Ids ``M1.<name>_r2``.
"""

from __future__ import annotations

import importlib
import itertools
import math
import random
from collections.abc import Callable
from fractions import Fraction
from typing import Any

from studies.m0.core import Built, Lineage, lineages_of
from studies.m0.lineages_m1 import fmt
from studies.m0.lineages_m1_common import DECIMAL, WHOLE, and_, ctx, load_batch
from studies.m0.vocab import NAMES, OBJECTS

REV2: list[Lineage] = []
REV2_FAMILY: dict[str, str] = {}
SUPERSEDES: dict[str, str] = {}  # rev2 id -> batch-1 id it supersedes
UNCHANGED = ("M1.finite_differences", "M1.quadratic_area", "M1.recurrence_iterate", "M1.tiered_pricing")
# Lineages the lead is told are NOT REGISTERED (rev2 id or carried-over id -> reason). Filled from the measurements in m1_rev2_gates.py (see the manifest); kept here as data.
NOT_REGISTERED: dict[str, str] = {
    "M1.min_cost_packs_r2": (
        "The audit's 'greedy' tell (0.41-0.47 at L0-L4) is gone, but the tell moved: with the redraws withdrawn (R-1) the best heuristic of the combined battery is the continuous relaxation "
        "'least unit price x need, rounded up' (0.65 at every level with equal unit prices; 'one kind of pack, floor, then singles' reached 0.65 with independent prices in the trial). The "
        "optimum of an unbounded min-cost cover is near its linear relaxation for any natural pack system, so no construction was found that makes every cheap plan uninformative. "
        "Rev2 shape kept for the record; NOT REGISTERED."
    ),
}

Builder = Callable[[int, random.Random], Built]


def r2(family: str, supersedes: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"M1.{fn.__name__}"
        if any(x.id == lid for x in REV2) or any(x.id == lid for x in lineages_of("M1")):
            raise ValueError(f"duplicate lineage id {lid}")
        REV2.append(Lineage(lid, "M1", family, fn))
        REV2_FAMILY[lid] = family
        SUPERSEDES[lid] = supersedes
        return fn

    return deco


def _until(fn: Callable[[], Any], tries: int = 5000) -> Any:
    """Loop on VALIDITY only (the callable returns None for an invalid draw). Never conditional on a heuristic."""
    for _ in range(tries):
        out = fn()
        if out is not None:
            return out
    raise RuntimeError("no valid draw")


# ------------------------------------------------------------------ number theory


@r2("number_theory", "M1.gcd_lcm")
def gcd_lcm_r2(level: int, r: random.Random) -> Built:
    """structured: {"ask": "gcd" | "lcm", "values": [positive integers, distinct]}. All values are multiples of a common factor d >= 2 (so the product is never the lcm and the
    smallest value is rarely the gcd, by construction). gcd: the largest whole length dividing every value; lcm: the first common time of periodic events with these periods.
    The ask is drawn before any other choice and nothing is redrawn but a repeated value."""
    ask = r.choice(("gcd", "lcm"))
    k = 2 if level < 3 else (3 if level < 5 else 4)
    dmax, umax = 20 + 6 * level, 40 + 10 * level

    def draw() -> list[int] | None:
        d = r.randint(2, dmax)
        us = [r.randint(2, umax) for _ in range(k)]
        return [d * u for u in us] if len(set(us)) == k else None

    vals = _until(draw)
    ans = math.gcd(*vals) if ask == "gcd" else math.lcm(*vals)
    if ask == "gcd":
        name = r.choice(NAMES)
        q = (f"{name} has {k} ribbons of lengths {and_([str(v) for v in vals])} centimetres. {name} cuts every ribbon into pieces that all have the same whole-number length in centimetres, "
             f"with nothing left over from any ribbon. What is the greatest possible length of a piece, in centimetres? {WHOLE}")
    else:
        q = (f"{ctx(r)} {k} lights flash at the same moment. After that, one flashes every {vals[0]} seconds, "
             + ", ".join(f"another every {v} seconds" for v in vals[1:-1]) + (", and " if k > 2 else "") + (f"the last every {vals[-1]} seconds" if k > 2 else f"the other every {vals[-1]} seconds")
             + f". After how many seconds do all {k} flash together again for the first time? {WHOLE}")
    return Built(q, {"ask": ask, "values": vals}, str(ans), "number", None)


@r2("number_theory", "M1.crt_congruence")
def crt_congruence_r2(level: int, r: random.Random) -> Built:
    """structured: {"conditions": [[modulus, remainder]]}, pairwise coprime moduli, 0 < remainder < modulus. Answer: the least positive whole number meeting every condition.
    Unchanged from batch 1 except that the redraw 'answer must exceed the largest modulus' (a heuristic-conditional redraw) is withdrawn."""
    k = 2 if level < 3 else (3 if level < 5 else 4)
    top = 30 + 10 * level if k == 2 else 14 + 3 * level

    def draw() -> list[int] | None:
        mods: list[int] = []
        for _ in range(k):
            m = r.randint(3, top)
            if any(math.gcd(m, x) != 1 for x in mods):
                return None
            mods.append(m)
        return mods

    mods = _until(draw)
    rems = [r.randint(1, m - 1) for m in mods]
    P = math.prod(mods)
    ans = next(n for n in range(1, P + 1) if all(n % m == rr for m, rr in zip(mods, rems, strict=True)))
    conds = [[m, rr] for m, rr in zip(mods, rems, strict=True)]
    name = r.choice(NAMES)
    txt = "; ".join(f"dividing it by {m} leaves remainder {rr}" for m, rr in conds)
    q = f"{name} is thinking of a positive whole number. {txt[0].upper() + txt[1:]}. What is the smallest positive whole number that {name} could be thinking of? {WHOLE}"
    return Built(q, {"conditions": conds}, str(ans), "number", None)


_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


@r2("number_theory", "M1.prime_factors")
def prime_factors_r2(level: int, r: random.Random) -> Built:
    """structured: {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. As batch 1 with a wider prime pool and N range (capacity, ruling R-5)."""
    ask = r.choice(("divisors", "largest", "distinct_sum", "factor_count"))
    pool = _PRIMES[: min(len(_PRIMES), 12 + level)]
    nmax = 20000 * 4**level

    def draw() -> int | None:
        npr = r.randint(2, 3) if level < 3 else r.randint(3, 4) if level < 5 else r.randint(3, 5)
        ps = sorted(r.sample(pool, npr))
        es = [r.randint(1, 2 + level // 2 + (1 if p == 2 else 0)) for p in ps]
        n = math.prod(p**e for p, e in zip(ps, es, strict=True))
        return n if 12 <= n <= nmax else None

    n = _until(draw)
    fac: dict[int, int] = {}
    m, p = n, 2
    while m > 1:
        while m % p == 0:
            fac[p] = fac.get(p, 0) + 1
            m //= p
        p += 1
    ans = {"divisors": math.prod(e + 1 for e in fac.values()), "largest": max(fac), "distinct_sum": sum(fac), "factor_count": sum(fac.values())}[ask]
    what = {
        "divisors": "How many different positive whole numbers divide it exactly (counting 1 and the number itself)?",
        "largest": "What is the largest prime number that divides it exactly?",
        "distinct_sum": "Add up the different prime numbers that divide it exactly (each different prime counted once). What is the sum?",
        "factor_count": "Write it as a product of prime numbers, repeating a prime as often as needed (for example 12 = 2 x 2 x 3 uses three primes). How many primes are multiplied?",
    }[ask]
    return Built(f"{ctx(r)} Consider the number {n}. {what} {WHOLE}", {"n": n, "ask": ask}, str(ans), "number", None)


@r2("number_theory", "M1.last_digit_power")
def power_remainder_r2(level: int, r: random.Random) -> Built:
    """structured: {"modulus": p, "op": "sum" | "product", "terms": [[base, exponent]]}, p in {17, 19, 23, 29}, no base a multiple of p. Each term is the product of `exponent` factors, each equal to `base`
    (said so in the item). Answer: the remainder of the sum (or product) of the terms on division by p, by reducing each exponent modulo p - 1 (Fermat) and combining.
    Supersedes last_digit_power: its heuristics '(last digit of the base)^(last digit of the exponent)' and 'square of the base digit' were right 0.33 to 0.44 of the time because
    10 = 2 mod 4 (so e and e mod 10 share a residue mod 4 half the time); with a prime modulus p whose p - 1 is not a multiple of 5 (so not 11 or 31) the exponent's last digit carries almost no information about its residue mod p - 1 (the copied heuristic fails whenever the order of the base does not divide 10).
    The batch-1 rejections (answer never the base digit; even exponents forced for bases ending 4 or 9) are gone."""
    p = r.choice((17, 19, 23, 29))
    t = 1 if level < 2 else (2 if level < 5 else 3)
    op = r.choice(("sum", "product")) if t > 1 else "sum"

    def one() -> list[int]:
        while True:
            b = r.randint(2, 99 + 30 * level)
            if b % p:
                return [b, r.randint(12, 300 + 100 * level)]

    terms = [one() for _ in range(t)]
    vals = [pow(b, e, p) for b, e in terms]
    ans = (sum(vals) if op == "sum" else math.prod(vals)) % p
    parts = [f"the product of {e} factors, each equal to {b}" for b, e in terms]
    if t == 1:
        body = f"Let X be {parts[0]}."
    elif op == "sum":
        body = "Let X be the sum of " + and_(parts) + "."
    else:
        body = "Let X be the product of all the following factors: " + and_([f"{e} factors equal to {b}" for b, e in terms]) + "."
    q = f"{ctx(r)} {body} What is the remainder when X is divided by {p}? {WHOLE}"
    return Built(q, {"modulus": p, "op": op, "terms": terms}, str(ans), "number", None)


# ------------------------------------------------------------------ counting


@r2("counting", "M1.inclusion_exclusion")
def inclusion_exclusion_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1. The ask is drawn first; the redraw 'the answer is never a stated number' is withdrawn (it was conditional on a heuristic)."""
    three = level >= 3
    ask = r.choice(("none", "any", "exactly_one", "exactly_two") if level >= 5 else ("none", "any"))
    m = 8 + 8 * level
    acts = r.sample(("play chess", "play tennis", "swim", "paint", "sing in the choir", "read comics", "ride a bike"), 3 if three else 2)
    if not three:
        ao, bo, ab, none = (r.randint(1, m) for _ in range(4))
        sizes, pairs, triple, total = [ao + ab, bo + ab], [ab], None, ao + bo + ab + none
        reg = {"none": none, "any": ao + bo + ab}
    else:
        g = {s: r.randint(1, m) for s in ("a", "b", "c", "ab", "ac", "bc", "abc", "none")}
        sizes = [g["a"] + g["ab"] + g["ac"] + g["abc"], g["b"] + g["ab"] + g["bc"] + g["abc"], g["c"] + g["ac"] + g["bc"] + g["abc"]]
        pairs = [g["ab"] + g["abc"], g["ac"] + g["abc"], g["bc"] + g["abc"]]
        triple, total = g["abc"], sum(g.values())
        reg = {"none": g["none"], "any": total - g["none"], "exactly_one": g["a"] + g["b"] + g["c"], "exactly_two": g["ab"] + g["ac"] + g["bc"]}
    ans = reg[ask]
    what = {"none": "do none of these things", "any": "do at least one of these things", "exactly_one": "do exactly one of these things", "exactly_two": "do exactly two of these things"}[ask]
    if not three:
        facts = f"{sizes[0]} of them {acts[0]}, {sizes[1]} of them {acts[1]}, and {pairs[0]} of them do both"
    else:
        facts = (f"{sizes[0]} {acts[0]}, {sizes[1]} {acts[1]} and {sizes[2]} {acts[2]}; {pairs[0]} do both the first and the second, {pairs[1]} do both the first and the third, "
                 f"{pairs[2]} do both the second and the third, and {triple} do all three")
    q = f"{total} people were asked what they do. {facts[0].upper() + facts[1:]}. How many of the {total} people {what}? {WHOLE}"
    return Built(q, {"total": total, "sets": acts, "sizes": sizes, "pairs": pairs, "triple": triple, "ask": ask}, str(ans), "number", None)


@r2("counting", "M1.binomial_choose")
def binomial_choose_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1 ({"shape": "plain" | "include" | "two_groups", "n", "k", "x", "y", "j"}) with wider ranges (capacity, ruling R-5) and a cap of 10**12 on the answer
    (a size cap, the only loop). The shape is drawn first, so the mix is a third each at every level."""
    shape = r.choice(("plain", "include", "two_groups"))
    top = 20 + 3 * level
    name = r.choice(NAMES)

    def draw() -> tuple[str, dict[str, int], int] | None:
        if shape == "two_groups":
            x, y = r.randint(3, top - 2), r.randint(3, top - 2)
            k = r.randint(3, min(x + y - 2, 5 + 2 * level))
            j = r.randint(max(1, k - y), min(x, k - 1))
            ans = math.comb(x, j) * math.comb(y, k - j)
            return f"A group has {x} women and {y} men. A team of {k} people is chosen (the order does not matter) with exactly {j} {'woman' if j == 1 else 'women'} on it. How many different teams are possible? {WHOLE}", {"shape": shape, "n": 0, "k": k, "x": x, "y": y, "j": j}, ans
        n = r.randint(8, top)
        k = r.randint(3, min(n - 3, 6 + 2 * level))
        if shape == "plain":
            return f"A club has {n} members. A committee of {k} members is chosen (the order of choosing does not matter). How many different committees are possible? {WHOLE}", {"shape": shape, "n": n, "k": k, "x": 0, "y": 0, "j": 0}, math.comb(n, k)
        return (f"A club has {n} members, and {name} is one of them. A committee of {k} members is chosen (the order does not matter), and {name} must be on it. How many different committees are possible? {WHOLE}",
                {"shape": shape, "n": n, "k": k, "x": 0, "y": 0, "j": 0}, math.comb(n - 1, k - 1))

    q, st, ans = _until(lambda: (lambda d: d if d is not None and d[2] <= 10**12 else None)(draw()))
    return Built(f"{ctx(r)} {q}", st, str(ans), "number", None)


def _slot_count(digits: list[int], s: int, rep: bool, lead: bool, parity: str) -> int:
    """Count s-digit codes by filling the last, then the first, then the middle slots (product rule)."""
    n = len(digits)
    total = 0
    for last in digits:
        if (parity == "even") != (last % 2 == 0):
            continue
        for first in digits:
            if lead and first == 0:
                continue
            if not rep and first == last:
                continue
            mid = (n**(s - 2)) if rep else math.perm(n - 2, s - 2)
            total += mid
    return total


@r2("counting", "M1.slot_permutations")
def slot_permutations_r2(level: int, r: random.Random) -> Built:
    """structured: {"digits": [allowed digits], "length": s, "repeat": bool, "lead_nonzero": bool, "parity": "even" | "odd"}. Codes of s digits, every position from `digits`; no digit twice
    unless `repeat`; when 0 is among the digits the item STATES whether the first digit may be 0 (a code such as 012 is then allowed); the last digit has the stated parity.
    Supersedes slot_permutations: batch 1 did not state the leading-zero rule (13 of 140 fixture keys changed under the ordinary reading) and drew parity 'any' with a redraw
    that forced a restriction (withdrawn: the parity restriction is now always present, by construction)."""
    n = r.randint(5, 9 + (level >= 4))
    digits = sorted(r.sample(range(10), n))
    s = min(r.randint(3, 3 + (level + 1) // 3 + (level >= 5)), n)
    rep = r.random() < 0.35
    lead = 0 in digits and r.random() < 0.5
    par = r.choice(("even", "odd"))
    cnt = _slot_count(digits, s, rep, lead, par)
    rules = ["no digit may be used more than once" if not rep else "a digit may be used more than once"]
    if 0 in digits:
        rules.append("the first digit may not be 0" if lead else "the first digit may be 0 (a code such as 012 is allowed)")
    rules.append(f"the last digit must be {par}")
    q = f"{ctx(r)} How many {s}-digit codes can be written using only the digits {and_([str(d) for d in digits])}, if " + and_(rules) + f"? {WHOLE}"
    return Built(q, {"digits": digits, "length": s, "repeat": rep, "lead_nonzero": lead, "parity": par}, str(cnt), "number", None)


@r2("counting", "M1.change_ways")
def change_ways_r2(level: int, r: random.Random) -> Built:
    """structured: {"coins": [values in cents, distinct], "target": T}. Answer: the number of different multisets of coins that add up to exactly T. T is built from a random combination of the coins
    (so at least one way exists, by construction); the batch-1 redraws (4 <= answer <= 150; answer != T // largest coin + 1) are withdrawn."""
    coins = sorted(r.sample((2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25), 3))
    xmax = 3 + 2 * level
    t = sum(c * r.randint(0, xmax) for c in coins) + coins[0] * 6
    ways = [1] + [0] * t
    for v in coins:
        for a in range(v, t + 1):
            ways[a] += ways[a - v]
    q = (f"{ctx(r)} Using only coins worth {and_([str(v) for v in coins])} cents, with as many coins of each value available as you like, in how many different ways can exactly {t} cents be paid? "
         f"(Two ways are the same if they use the same number of coins of each value; the order does not matter.) {WHOLE}")
    return Built(q, {"coins": coins, "target": t}, str(ways[t]), "number", None)


@r2("counting", "M1.pigeonhole_worst_case")
def pigeonhole_worst_case_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1 ({"counts", "goal": "same" | "all", "k"}). The goal is drawn first; for goal "same", k is drawn from 2..max(count) (so a colour with k marbles exists, by construction);
    the redraws 'the cap bites' and 'counts not all equal' are withdrawn. Wider counts (capacity, R-5)."""
    goal = r.choice(("same", "all"))
    c = 3 + (level >= 2) + (level >= 4)
    counts = [r.randint(2, 30 + 8 * level) for _ in range(c)]
    if goal == "same":
        k = r.randint(2, max(counts))
        ans = 1 + sum(min(n, k - 1) for n in counts)
        what = f"at least {k} marbles of the same colour"
    else:
        k = 1
        ans = sum(counts) - min(counts) + 1
        what = "at least one marble of every colour"
    cols = r.sample(("red", "blue", "green", "yellow", "purple", "white", "black"), c)
    inv = ", ".join(f"{n} {col}" for n, col in zip(counts, cols, strict=True))
    q = f"A bag holds marbles of {c} colours: {inv}. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the draws are, of having {what}? {WHOLE}"
    return Built(q, {"counts": counts, "goal": goal, "k": k}, str(ans), "number", None)


# ------------------------------------------------------------------ statistics


@r2("statistics", "M1.median_list")
def median_list_r2(level: int, r: random.Random) -> Built:
    """structured: {"shape": "list", "values": [numbers in the order printed]}. List shape only (the batch-1 table shape needed a redraw so that the multiplicities mattered; that redraw is
    withdrawn and the shape is dropped from this revision, by construction). Values may repeat. Answer: the median (the mean of the two middle values when the count is even)."""
    n = r.randint(5 + level, 8 + 2 * level)
    hi = 30 + 20 * level
    vals = [r.randint(1, hi) for _ in range(n)]
    s = sorted(vals)
    mid = Fraction(s[(n - 1) // 2] + s[n // 2], 2)
    q = f"{ctx(r)} The values are {and_([str(v) for v in vals])}. What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, the number halfway between them)? {DECIMAL}"
    return Built(q, {"shape": "list", "values": vals}, fmt(mid), "number", None)


@r2("statistics", "M1.mode_tally")
def mode_tally_r2(level: int, r: random.Random) -> Built:
    """structured: {"values": [numbers in the order printed], "ask": "mode" | "mode_count"}. Built from counts: one mode with f occurrences, r in 2..4 rival values with f - 1 each,
    and a long tail of values with 1..f - 2 occurrences, then shuffled. Many rivals and many distinct values make the mode's share of the list small, so 'the last value listed',
    'the first value repeated' and 'the value near the middle' are uninformative by the construction (no redraw on any heuristic). The ask is drawn first."""
    ask = r.choice(("mode", "mode_count"))
    f = r.randint(3, 6 + level)
    rivals = r.randint(2, 4)
    tail = r.randint(4, 8 + level)
    hi = 12 + 6 * level + 2 * (rivals + tail)
    pool = r.sample(range(1, hi + 1), 1 + rivals + tail)
    counts = [f] + [f - 1] * rivals + [r.randint(1, max(1, f - 2)) for _ in range(tail)]
    vals = [v for v, c in zip(pool, counts, strict=True) for _ in range(c)]
    r.shuffle(vals)
    n = len(vals)
    ans = pool[0] if ask == "mode" else f
    what = "Which value occurs most often? There is exactly one such value." if ask == "mode" else "How many times does the most frequent value occur? There is exactly one most frequent value."
    q = f"A teacher wrote down {n} test scores: {and_([str(v) for v in vals])}. {what} {WHOLE}"
    return Built(q, {"values": vals, "ask": ask}, str(ans), "number", None)


# ------------------------------------------------------------------ algebra: digit puzzles

_NUMS: dict[int, list[tuple[int, tuple[int, ...]]]] = {nd: [(n, tuple(int(c) for c in str(n))) for n in range(10 ** (nd - 1), 10**nd)] for nd in (2, 3)}
_FIT: dict[tuple[int, tuple[Any, ...]], frozenset[int]] = {}


def _clue_holds(n: int, ds: tuple[int, ...], c: tuple[Any, ...]) -> bool:
    k = c[0]
    if k == "digit_sum":
        return sum(ds) == c[1]
    if k == "digit_product":
        return math.prod(ds) == c[1]
    if k == "reverse_gap":
        return int(str(n)[::-1]) - n == c[1]
    if k == "multiple_of":
        return n % c[1] == 0
    if k == "parity":
        return (n % 2 == 0) == (c[1] == "even")
    if k == "first_gt_last":
        return ds[0] > ds[-1]
    if k == "contains_digit":
        return c[1] in ds
    if k == "ends_differ_by":
        return abs(ds[0] - ds[-1]) == c[1]
    if k == "digits_distinct":
        return len(set(ds)) == len(ds)
    if k == "middle_is_mean":
        return len(ds) == 3 and 2 * ds[1] == ds[0] + ds[2]
    return ds[0] == c[1] * ds[-1]


def fit_set(nd: int, c: tuple[Any, ...]) -> frozenset[int]:
    key = (nd, c)
    if key not in _FIT:
        _FIT[key] = frozenset(n for n, ds in _NUMS[nd] if _clue_holds(n, ds, c))
    return _FIT[key]


def clue_text(c: list[Any]) -> str:
    k = c[0]
    if k == "digit_sum":
        return f"its digits add up to {c[1]}"
    if k == "digit_product":
        return f"the product of its digits is {c[1]}"
    if k == "reverse_gap":
        rv = "the number made by writing its digits in the opposite order (a leading 0 is dropped, so 120 turned round gives 21)"
        return f"{rv} is the same as it" if c[1] == 0 else f"{rv} is {abs(c[1])} {'more' if c[1] > 0 else 'less'} than it"
    if k == "multiple_of":
        return f"it is a multiple of {c[1]}"
    if k == "parity":
        return f"it is {c[1]}"
    if k == "first_gt_last":
        return "its first digit is larger than its last digit"
    if k == "contains_digit":
        return f"one of its digits is {c[1]}"
    if k == "ends_differ_by":
        return f"its first and last digits differ by {c[1]} (in either order)"
    if k == "digits_distinct":
        return "no two of its digits are the same"
    if k == "middle_is_mean":
        return "its middle digit is exactly halfway between its first and last digits"
    return f"its first digit is {c[1]} times its last digit"


@r2("algebra", "M1.digit_puzzle")
def digit_puzzle_r2(level: int, r: random.Random) -> Built:
    """structured: {"digits": 2 | 3, "clues": [[kind, parameter?]]} (kinds digit_sum S, digit_product P, reverse_gap D = reversed number minus the number, multiple_of m, parity, first_gt_last,
    digit_relation q = first digit is q times the last, contains_digit d, ends_differ_by d = |first - last|, digits_distinct, middle_is_mean (3 digits)). The reversed number drops a leading zero and the item says so (120 turned round gives 21). The secret is drawn, then clues that hold for it are
    added one at a time (at least 2 + (level >= 3) + (level >= 5)) until exactly one number with that many digits (no leading 0) fits all clues; that is the only loop (a unique answer).
    The batch-1 redraws 'no single clue leaves fewer than 4 candidates' and 'no clue is redundant' (heuristic-conditional) are withdrawn. Level 0 uses 2-digit, all other levels 3-digit numbers."""
    nd = 2 if level == 0 else 3
    lo = 10 ** (nd - 1)
    need = 2 + (level >= 3) + (level >= 5)

    def draw() -> tuple[int, list[list[Any]]] | None:
        secret = r.randint(lo, 10**nd - 1)
        ds = tuple(int(c) for c in str(secret))
        pool: list[tuple[Any, ...]] = [("digit_sum", sum(ds)), ("digit_product", math.prod(ds)), ("reverse_gap", int(str(secret)[::-1]) - secret), ("multiple_of", r.choice((3, 4, 6, 7, 9, 11))),
                                       ("parity", "even" if secret % 2 == 0 else "odd"), ("first_gt_last",), ("digit_relation", r.choice((2, 3))),
                                       ("contains_digit", r.choice(ds)), ("ends_differ_by", abs(ds[0] - ds[-1])), ("digits_distinct",), ("middle_is_mean",)]
        r.shuffle(pool)
        clues: list[tuple[Any, ...]] = []
        cand: frozenset[int] | None = None
        for c in pool:
            if not _clue_holds(secret, ds, c):
                continue
            clues.append(c)
            cand = fit_set(nd, c) if cand is None else cand & fit_set(nd, c)
            if len(clues) >= need and cand == frozenset({secret}):
                return secret, [list(x) for x in clues]
        return None

    secret, clues = _until(draw)
    q = f"{ctx(r)} Find the {nd}-digit number (it does not start with 0) for which all of these are true: " + "; ".join(clue_text(c) for c in clues) + f". There is exactly one such number. {WHOLE}"
    return Built(q, {"digits": nd, "clues": clues}, str(secret), "number", None)


# ------------------------------------------------------------------ geometry


def _triples(limit: int) -> list[tuple[int, int, int]]:
    """All integer Pythagorean triples (a < b, hypotenuse <= limit), by Euclid's formula and multiples."""
    out: set[tuple[int, int, int]] = set()
    m = 2
    while m * m + 1 <= limit:
        for n in range(1, m):
            if (m - n) % 2 and math.gcd(m, n) == 1:
                a0, b0, c0 = sorted((m * m - n * n, 2 * m * n))[0], sorted((m * m - n * n, 2 * m * n))[1], m * m + n * n
                for k in range(1, limit // c0 + 1):
                    out.add((a0 * k, b0 * k, c0 * k))
        m += 1
    return sorted(out)


_T = _triples(2800)


@r2("geometry", "M1.pythagoras")
def pythagoras_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1 ({"shape", "legs": [a, b], "hyp": c, "given": [..]}), (a, b, c) an integer Pythagorean triple with c <= limit(level) = 400 + 400 * level (capacity, R-5)."""
    limit = 400 + 400 * level
    a, b, c = r.choice([t for t in _T if t[2] <= limit])
    if r.random() < 0.5:
        a, b = b, a
    shape = r.choice(("ladder_top", "ladder_base", "walk", "diagonal", "perimeter"))
    name = r.choice(NAMES)
    if shape == "ladder_top":
        ans, given = b, [c, a]
        q = f"A ladder {c} metres long leans against a vertical wall. Its foot is {a} metres from the base of the wall, on level ground. How high up the wall does the top of the ladder reach, in metres? {WHOLE}"
    elif shape == "ladder_base":
        ans, given = a, [c, b]
        q = f"A ladder {c} metres long leans against a vertical wall and its top reaches {b} metres up the wall. How far is its foot from the base of the wall, in metres, on level ground? {WHOLE}"
    elif shape == "walk":
        ans, given = c, [a, b]
        q = f"{name} walks {a} metres due east and then {b} metres due north. How far is {name} now from the starting point in a straight line, in metres? {WHOLE}"
    elif shape == "diagonal":
        ans, given = c, [a, b]
        q = f"A rectangular screen is {a} centimetres wide and {b} centimetres tall. What is the length of its diagonal, in centimetres? {WHOLE}"
    else:
        ans, given = a + b + c, [a, b]
        q = f"A right-angled triangle has two short sides (the sides next to the right angle) of {a} centimetres and {b} centimetres. What is the length of the whole boundary of the triangle (its perimeter), in centimetres? {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"shape": shape, "legs": [a, b], "hyp": c, "given": given}, str(ans), "number", None)


@r2("geometry", "M1.grid_perimeter")
def grid_perimeter_r2(level: int, r: random.Random) -> Built:
    """structured: {"rows": [[[first_column, last_column], ...] per row, top row first]}. n = 9 + 3 * level unit squares are placed on distinct cells chosen uniformly at random from a box of
    about 3 n cells; some squares touch and some do not. Each row is listed as runs of columns (a row without squares says so). Answer: the perimeter in unit lengths = the number of sides of
    squares that do not touch another square of the set (4 n - 2 x the number of touching pairs).
    Supersedes grid_perimeter: its shapes were rows of one overlapping run each and a redraw rejected shapes whose perimeter equalled the bounding box's, which moved the mass to 'bounding box + 4'
    (0.30 to 0.35). A compact random blob (tried and measured in the scratch notes) keeps the perimeter within a few units of the bounding box's whatever the generator does; a scattered
    set does not, so 'bounding box', 'bounding box + 4' and '2 x cells + 2' are uninformative by construction and nothing is redrawn."""
    ncell = 9 + 3 * level
    w = round(math.sqrt(3 * ncell))
    h = -(-3 * ncell // w)
    cells = set(r.sample([(y, x) for y in range(h) for x in range(w)], ncell))
    per = sum(1 for (y, x) in cells for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (y + dy, x + dx) not in cells)
    ys = sorted({y for y, _ in cells})
    rows: list[list[list[int]]] = []
    for y in range(ys[0], ys[-1] + 1):
        xs = sorted(x for yy, x in cells if yy == y)
        runs: list[list[int]] = []
        for x in xs:
            if runs and runs[-1][1] == x - 1:
                runs[-1][1] = x
            else:
                runs.append([x, x])
        rows.append([[a + 1, b + 1] for a, b in runs])
    txt = " ".join(f"Row {i + 1} (counting from the top): " + (", ".join(f"columns {a} to {b}" if a != b else f"column {a}" for a, b in rr) if rr else "no squares") + "." for i, rr in enumerate(rows))
    q = (f"Unit squares (each side 1 unit long) are placed on a grid. {txt} Squares with the same column number in neighbouring rows sit directly above and below each other, so some squares touch and some do not. "
         f"The perimeter is the total length of all the sides of squares that do not touch another square. What is the perimeter, in units? {WHOLE}")
    return Built(q, {"rows": rows}, str(per), "number", None)


@r2("geometry", "M1.painted_cube")
def painted_cube_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1 ({"dims", "bottom_unpainted", "faces"}). Faces (0, 1 or 2) drawn first; wider dimensions (capacity, R-5); the redraw 'the answer is not a dimension and is at least 4'
    (conditional on 'answer is a printed number') is withdrawn."""
    f = r.choice((0, 1, 2))
    ba = r.random() < 0.5
    top = 24 + 4 * level
    a, b, c = (r.randint(3, top) for _ in range(3))
    cnt = 0
    for x in range(a):
        for y in range(b):
            for z in range(c):
                p = (x in (0, a - 1)) + (y in (0, b - 1)) + (z == c - 1) + (z == 0 and not ba)
                cnt += p == f
    paint = "every outer face is painted red except the bottom face, which stays unpainted" if ba else "every outer face (including the bottom) is painted red"
    q = (f"{ctx(r)} A block is made from small cubes of the same size glued together into a box {a} cubes long, {b} cubes wide and {c} cubes high. The whole box is placed on a table and {paint}. "
         f"Then the box is taken apart into the small cubes. How many small cubes have exactly {f} painted {'face' if f == 1 else 'faces'}? {WHOLE}")
    return Built(q, {"dims": [a, b, c], "bottom_unpainted": ba, "faces": f}, str(cnt), "number", None)


# ------------------------------------------------------------------ pricing and division


def _best_cover(n: int, single: int, packs: list[list[int]]) -> int:
    top = n + max(p for p, _ in packs)
    cost = [0] + [10**9] * top
    for i in range(1, top + 1):
        cost[i] = min([cost[i - 1] + single] + [cost[i - p] + q for p, q in packs if i >= p])
    return min(cost[n:])


@r2("pricing", "M1.min_cost_packs")
def min_cost_packs_r2(level: int, r: random.Random) -> Built:
    """structured as batch 1 ({"item", "need", "single", "packs": [[size, price]]}). Answer: the least cost of at least `need` items from singles and packs. All redraws on naive plans are
    withdrawn (R-1). By construction: four pack sizes (five from level 5) whose prices are all the SAME per-item rate (60 to 90 percent of the single price, rounded to whole dollars), so no pack
    is the bargain and 'biggest pack first', 'best unit price' and 'one kind of pack only' have no structural edge; need is between 2 and 4 times the largest pack. In the measurement the
    best of the audit's heuristics ('one kind of pack, floor, then singles') is about 0.25; see the manifest for the exact rates and whether the lineage is marked NOT REGISTERED."""
    npk = 4 + (level >= 5)
    single = r.randint(5, 12)
    base = Fraction(r.randint(60, 90), 100) * single
    sizes = r.sample(range(3, 14 + 3 * level + 2 * npk), npk)
    packs = sorted([[s, max(2, round(s * base))] for s in sizes])
    need = r.randint(2 * max(sizes), 4 * max(sizes) + 5 * level)
    best = _best_cover(need, single, packs)
    item = r.choice(OBJECTS)
    deals = ", ".join(f"a pack of {p} {item}s costs {q} dollars" for p, q in packs[:-1]) + f" and a pack of {packs[-1][0]} {item}s costs {packs[-1][1]} dollars"
    name = r.choice(NAMES)
    q = (f"At a shop, one {item} costs {single} dollars, {deals}. {name} needs at least {need} {item}s and wants to spend as little as possible; {name} may buy more than needed and may mix packs and single items. "
         f"What is the smallest total cost, in dollars? {WHOLE}")
    return Built(q, {"item": item, "need": need, "single": single, "packs": packs}, str(best), "number", None)


@r2("division", "M1.division_counting")
def division_counting_r2(level: int, r: random.Random) -> Built:
    """structured: {"shape": "pallets" | "empty_seats", ...}. The shape is drawn first and no draw is rejected, so the mix is a half each at every level (batch 1: 0.07-0.11 / 0.28 / 0.60-0.65).
    pallets {"items": N, "box": k, "crate": m}: items are packed into full boxes of k (items that do not fill a box are left out); boxes go on pallets of m, as many full pallets as possible;
    answer the boxes NOT on a full pallet: (N // k) % m (this replaces batch 1's 'crates', which was one ceiling, ceil(N / (k m)), an identity).
    empty_seats {"people": N, "seats": k}: buses of k seats, as few as possible; answer the empty seats: ceil(N / k) * k - N.
    DROPPED from this revision: batch 1's 'multiples in a range' shape. Without its redraw (R-1) the heuristic 'round((high - low) / d)' is exact on about 0.9 of its items (0.27 to 0.30 of the
    whole lineage at every level), because a count of multiples is within one of range / d by construction; there is no construction that removes that, so the shape is dropped (it also
    duplicates R2.multiples_between, audit section 3)."""
    shape = r.choice(("pallets", "empty_seats"))
    s = 1 + level
    if shape == "pallets":
        k, m = r.randint(4, 9 + 3 * s), r.randint(3, 6 + 2 * s)
        n = r.randint(3 * k * m, 20 * k * m + 400 * level)
        ans = (n // k) % m
        item = r.choice(OBJECTS)
        q = (f"{ctx(r)} A factory makes {n} {item}s. They are packed into boxes that each hold exactly {k} {item}s; {item}s that do not fill a box are left out. The boxes are then put on pallets that each hold {m} boxes, "
             f"and as many full pallets as possible are made. How many boxes are not on a full pallet? {WHOLE}")
        st = {"shape": shape, "items": n, "box": k, "crate": m}
    else:
        k = r.randint(8, 20 + 5 * s)
        n = r.randint(3 * k, 25 * k + 100 * level)
        ans = -(-n // k) * k - n
        name = r.choice(NAMES)
        q = f"{n} people must travel by bus, and {name} hires as few buses as possible. Each bus has {k} seats, and nobody stands. When all {n} people are on board, how many seats in total are empty? {WHOLE}"
        st = {"shape": shape, "people": n, "seats": k}
    return Built(q, st, str(ans), "number", None)


# ------------------------------------------------------------------ the effective set


def load_rev2() -> list[Lineage]:
    """The effective 21: the 17 revised shapes plus the 4 carried-over batch-1 lineages, sorted by id."""
    importlib.import_module("studies.m0.lineages_m1_rev2")  # idempotent
    base = {x.id: x for x in load_batch()}
    keep = [base[i] for i in UNCHANGED]
    return sorted([*REV2, *keep], key=lambda x: x.id)


__all__ = ["NOT_REGISTERED", "REV2", "SUPERSEDES", "UNCHANGED", "itertools", "load_rev2"]
