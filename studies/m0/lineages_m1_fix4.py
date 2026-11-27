# ruff: noqa: E501
"""M1 fix round 4 (the narrow repair round; lead rulings R-24 to R-29, the human lead's fifth decision).

Only repairs allowed by R-25 live here:
  (b) the wording defect of audit 4 in ``slot_permutations`` (the leading-zero convention was printed only when the first-digit rule was 'any'),
  (c) collapsed levels: ``mixture``, ``gcd_lcm``, ``finite_differences``, ``slot_permutations`` (flattened by the round-3 capacity widening, audit 4 section 4) and, read as the same defect, ``average_missing`` and
      ``clock_duration`` (levels 0=1, 2=3, 4=5 identical, unchanged since batch 1 and listed in the same audit-4 profile). Each repaired lineage is a NEW revision ``M1.<stem>_r4`` with the SAME
      ``structured`` fields as its r3 predecessor, so every cheap rule and every canonical key written for r3 reads it unchanged.
Level 0 of each repaired builder keeps the r3 parameter ranges (level 0 of r3 is where the capacity widening was needed); the stated parameter RISES with the level above it (``LEVEL_PARAMETER`` documents it,
``level_parameter_values`` returns it and the tests check it is strictly increasing). No solution procedure changes. Nothing is redrawn conditional on a heuristic or on the answer; the only loops are the r3
validity loops (``_coprime_set``; slot_permutations' positive-answer loop is carried over from r3 unchanged and is listed in the notes under R-19). No new lineage and no replacement shape is authored.

Own registry (``FIX4``); nothing here enters ``core.REGISTRY``. Not a registration; no model was run.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from fractions import Fraction

from studies.m0.core import Built, Lineage
from studies.m0.lineages_m1_fix3 import NOT_REGISTERED as NOT_REGISTERED_FIX3
from studies.m0.lineages_m1_fix3 import load_all as load_all_fix3
from studies.m0.lineages_m1_fix3_b import (
    _FIRST_TXT,
    _LAST_TXT,
    _RULES_LAST,
    _SUBSETS,
    _coprime_set,
    slot_count,
)
from studies.m0.lineages_m1_fix3_common import DECIMAL, WHOLE, and_, ctx, fmt_exact, until
from studies.m0.vocab import NAMES

FIX4: list[Lineage] = []
REPLACES: dict[str, str] = {}  # r4 id -> the r3 id it replaces

# the stated rising parameter per repaired stem (one line each; the numeric values are in ``level_parameter_values``)
LEVEL_PARAMETER: dict[str, str] = {
    "mixture": "ceiling of the two prices per kilogram, 30 + 6 x level dollars (the weights are as in r3; packing from level 3)",
    "gcd_lcm": "ceiling of the answer: gcd ask g <= gmax and the lcm ask g x prod(q) <= gmax x top x (top-1) x ... over k factors, with (k, top, gmax) from the table GCD_LCM_TABLE (strictly rising)",
    "finite_differences": "ceiling of the answer: every coefficient at its ceiling (``fd_ceilings``: 60 + 10 x level, 25 + 5 x level, 15 + 3 x level; degree 3 from level 5 as in r3) evaluated at the farthest asked position m + 2",
    "slot_permutations": "longest code length 3 + level digits (r3: 3 up to 6)",
    "average_missing": "ceiling of the marks, 100 + 10 x level (number of tests 4 + level // 2 as in r3)",
    "clock_duration": "ceilings of the waits (40 + 4 x level minutes) and of the rides (110 + 6 x level minutes); number of legs 2 + level // 2 as in r3",
}

# gcd_lcm: level -> (k, top, gmax). Level 0, 3 and 5 are the r3 values of their k; the others widen inside k.
GCD_LCM_TABLE: dict[int, tuple[int, int, int]] = {0: (2, 50, 40), 1: (2, 60, 50), 2: (2, 75, 60), 3: (3, 30, 24), 4: (3, 36, 30), 5: (4, 24, 24), 6: (4, 28, 28)}


def gcd_lcm_ceiling(level: int) -> int:
    """Largest possible answer at the level (the lcm ask): gmax x top x (top - 1) x ... over k factors."""
    k, top, gmax = GCD_LCM_TABLE[level]
    return gmax * math.prod(top - j for j in range(k))


def fd_ceilings(level: int) -> tuple[int, ...]:
    """Upper bounds of the coefficients, constant term first (the leading coefficient last); the leading coefficient's lower bound is 1."""
    if level < 5:
        return (60 + 10 * level, 25 + 5 * level, 15 + 3 * level)
    j = level - 5
    return (60 + 10 * j, 20 + 4 * j, 9 + 2 * j, 4 + j)


def fd_answer_ceiling(level: int) -> int:
    """Largest possible answer at the level: every coefficient at its ceiling, evaluated at the farthest asked position m + 2."""
    ce = fd_ceilings(level)
    m = (2 if level < 5 else 3) + 3 + (level >= 3)
    return sum(c * (m + 2) ** i for i, c in enumerate(ce))


def level_parameter_values(stem: str) -> list[int]:
    """The rising parameter, one integer per level 0..6 (a scalar that must be strictly increasing)."""
    lv = range(7)
    if stem == "mixture":
        return [30 + 6 * x for x in lv]
    if stem == "gcd_lcm":
        return [gcd_lcm_ceiling(x) for x in lv]
    if stem == "finite_differences":
        return [fd_answer_ceiling(x) for x in lv]
    if stem == "slot_permutations":
        return [3 + x for x in lv]
    if stem == "average_missing":
        return [100 + 10 * x for x in lv]
    if stem == "clock_duration":
        return [(40 + 4 * x) + (110 + 6 * x) for x in lv]
    raise KeyError(stem)


def r4(stem: str, family: str) -> Callable[[Callable[[int, random.Random], Built]], Callable[[int, random.Random], Built]]:
    def deco(fn: Callable[[int, random.Random], Built]) -> Callable[[int, random.Random], Built]:
        lid = f"M1.{stem}_r4"
        if any(x.id == lid for x in FIX4):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX4.append(Lineage(lid, "M1", family, fn))
        REPLACES[lid] = f"M1.{stem}_r3"
        return fn

    return deco


# ------------------------------------------------------------------ S2: mixture


@r4("mixture", "ratio")
def mixture_r4(level: int, r: random.Random) -> Built:
    """As ``mixture_r3`` (total weight s from {5, 10, 20, 25, 50, 100}, x uniform in 1..s-1, two different prices, so every mean is whole cents by construction; packing 1..9 dollars from level 3) with
    the price ceiling rising by level: prices 2..30 + 6 x level (r3: 2..30 at every level, which made levels 0-2 and 3-6 identical)."""
    pmax = 30 + 6 * level
    s = r.choice((5, 10, 20, 25, 50, 100))
    x = r.randint(1, s - 1)
    y = s - x
    a = r.randint(2, pmax)
    b = r.choice([v for v in range(2, pmax + 1) if v != a])
    p = r.randint(1, 9) if level >= 3 else 0
    v = Fraction(x * a + y * b, s) + p
    pack = f", then adds a flat packing cost of {p} {'dollar' if p == 1 else 'dollars'} per kilogram of the finished mixture" if p else ""
    q = (f"A shop mixes {x} kilograms of nuts costing {a} dollars per kilogram with {y} kilograms of raisins costing {b} dollars per kilogram{pack}. "
         f"What is the cost of one kilogram of the finished mixture, in dollars? {DECIMAL}")
    return Built(q, {"x": x, "y": y, "a": a, "b": b, "packing": p}, fmt_exact(v), "number", None)


# ------------------------------------------------------------------ S3: average_missing


@r4("average_missing", "average")
def average_missing_r4(level: int, r: random.Random) -> Built:
    """As ``average_missing_r3`` (n = 4 + level // 2 tests; the missing score drawn from the values that make the mean a number with at most two decimals) with the marks' ceiling rising by level:
    marks are whole numbers from 40 to M = 100 + 10 x level, 'each marked out of M' (r3: 40..100 at every level, so levels 0=1, 2=3, 4=5 were identical)."""
    n = 4 + level // 2
    top = 100 + 10 * level
    scores = [r.randint(40, top) for _ in range(n - 1)]
    ok = [v for v in range(40, top + 1) if Fraction(sum(scores) + v, n).denominator in (1, 2, 4, 5, 10, 20, 25, 50, 100)]
    last = r.choice(ok)
    mean = Fraction(sum(scores) + last, n)
    name = r.choice(NAMES)
    q = (f"{name} has scored {', '.join(str(s) for s in scores)} on {n - 1} tests, each marked out of {top} with whole-number marks. What score is needed on the next test to make the mean of all {n} tests exactly "
         f"{fmt_exact(mean)}? {WHOLE}")
    return Built(q, {"scores": scores, "mean_cents": int(mean * 100), "n": n}, str(last), "number", None)


# ------------------------------------------------------------------ clock_duration


@r4("clock_duration", "time")
def clock_duration_r4(level: int, r: random.Random) -> Built:
    """As ``clock_duration_r3`` (2 + level // 2 legs on one day; the waits and rides are drawn first, the first departure last, so nothing is redrawn) with the ceilings rising by level: waits 5..(40 + 4 x level)
    minutes and rides 20..(110 + 6 x level) minutes (r3: 5..60 and 20..150 at every level, so levels 0=1, 2=3, 4=5 were identical). The longest wait plus ride is 210 minutes at level 6, as in r3, so five legs
    never exceed 1050 minutes and the departure range (05:00 to at most 14:00) is never empty."""
    n = 2 + level // 2
    waits = [r.randint(5, 40 + 4 * level) for _ in range(n)]
    rides = [r.randint(20, 110 + 6 * level) for _ in range(n)]
    span = sum(waits) + sum(rides)
    t = r.randint(5 * 60, min(14 * 60, 24 * 60 - 1 - span))
    legs: list[list[int]] = []
    for w, d in zip(waits, rides, strict=True):
        dep = t + w
        arr = dep + d
        legs.append([dep, arr])
        t = arr

    def hhmm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    txt = "; ".join(f"leg {i + 1} leaves at {hhmm(a)} and arrives at {hhmm(b)}" for i, (a, b) in enumerate(legs))
    q = (f"A journey has several legs on the same day (times on a 24-hour clock): {txt}. How many minutes in total is the traveller actually on the move (the time between each leg's departure and "
         f"its arrival, not counting the waiting between legs)? {WHOLE}")
    return Built(q, {"legs": legs}, str(sum(b - a for a, b in legs)), "number", None)


# ------------------------------------------------------------------ gcd_lcm


@r4("gcd_lcm", "number_theory")
def gcd_lcm_r4(level: int, r: random.Random) -> Built:
    """As ``gcd_lcm_r3`` (same ask-dependent construction: gcd values g x prod(q_j, j != i); lcm values g x q_i) with (k, top, gmax) from ``GCD_LCM_TABLE``: k = 2 at levels 0-2 (top 50, 60, 75; gmax 40, 50, 60),
    k = 3 at levels 3-4 (30, 36; 24, 30), k = 4 at levels 5-6 (24, 28; 24, 28). Levels 0, 3 and 5 are r3's values; the rest widen, so every level is a different distribution and the ceiling of the
    answer rises strictly (``gcd_lcm_ceiling``). The k >= 3 construct-validity point of audit 4 (a false general rule is exact there) is unchanged and is not repaired."""
    ask = r.choice(("gcd", "lcm"))
    k, top, gmax = GCD_LCM_TABLE[level]
    qs = _coprime_set(r, k, top)
    g = r.randint(2, gmax)
    if ask == "gcd":
        vals = [g * math.prod(q for j, q in enumerate(qs) if j != i) for i in range(k)]
        ans = g
    else:
        vals = [g * q for q in qs]
        ans = g * math.prod(qs)
    assert ans == (math.gcd(*vals) if ask == "gcd" else math.lcm(*vals))
    if ask == "gcd":
        name = r.choice(NAMES)
        q = (f"{name} has {k} ribbons of lengths {and_([str(v) for v in vals])} centimetres. {name} cuts every ribbon into pieces that all have the same whole-number length in centimetres, "
             f"with nothing left over from any ribbon. What is the greatest possible length of a piece, in centimetres? {WHOLE}")
    else:
        mid = ", ".join(f"another every {v} seconds" for v in vals[1:-1])
        q = (f"{ctx(r)} {k} lights flash at the same moment. After that, one flashes every {vals[0]} seconds, " + (mid + ", and " if k > 2 else "") + (f"the last every {vals[-1]} seconds" if k > 2 else f"the other every {vals[-1]} seconds")
             + f". After how many seconds do all {k} flash together again for the first time (counting from the moment they all flashed)? {WHOLE}")
    return Built(q, {"ask": ask, "values": vals}, str(ans), "number", None)


# ------------------------------------------------------------------ finite_differences


@r4("finite_differences", "sequences")
def finite_differences_r4(level: int, r: random.Random) -> Built:
    """As ``finite_differences_r3`` (integer polynomial with non-negative coefficients, degree 2 below level 5 and 3 from level 5; m = degree + 3 + (level >= 3) terms printed; ask = m + 1 or m + 2) with the
    coefficient ceilings rising by level (``fd_ceilings``): degree 2: constant 0..60 + 10 x level, linear 0..25 + 5 x level, quadratic 1..15 + 3 x level; degree 3: constant 0..60 + 10 j, linear 0..20 + 4 j,
    quadratic 0..9 + 2 j, cubic 1..4 + j with j = level - 5. Level 0, level 3's term count and level 5 are r3's values."""
    ce = fd_ceilings(level)
    deg = 2 if level < 5 else 3
    if deg == 2:
        poly = [r.randint(0, ce[0]), r.randint(0, ce[1]), r.randint(1, ce[2])]
    else:
        poly = [r.randint(0, ce[0]), r.randint(0, ce[1]), r.randint(0, ce[2]), r.randint(1, ce[3])]

    def f(x: int) -> int:
        return sum(co * x**i for i, co in enumerate(poly))

    m = deg + 3 + (level >= 3)
    terms = [f(x) for x in range(1, m + 1)]
    ask = m + r.randint(1, 2)
    q = (f"The first {m} numbers of a pattern are {and_([str(t) for t in terms])}. The pattern continues in the same way, and each number is given by a polynomial of degree {deg} in its position "
         f"(position 1 is the first number). What is the number in position {ask}? {WHOLE}")
    assert 0 < f(ask) < 10**8
    return Built(f"{ctx(r)} {q}", {"terms": terms, "degree": deg, "ask": ask}, str(f(ask)), "number", None)


# ------------------------------------------------------------------ slot_permutations

ZERO_SENTENCE = "A code may start with the digit 0 whenever the rules below allow it (for example 012 is a 3-digit code)."


def zero_rule_stated(digits: list[int], first: str) -> bool:
    """True when the item must carry the leading-zero sentence: 0 is an allowed digit and the first-digit rule is not the explicit 'may not be 0'."""
    return 0 in digits and first != "not0"


@r4("slot_permutations", "counting")
def slot_permutations_r4(level: int, r: random.Random) -> Built:
    """As ``slot_permutations_r3`` (digits: a uniform subset of 4..9 of 0-9; no digit twice unless `repeat`; first digit rule in {any, not 0, odd, even, >= 5, < 5}; last digit rule in {odd, even, >= 5, < 5}; the
    answer is positive, a validity loop carried over unchanged from r3, see the notes) with two repairs.
    (b) The leading-zero convention is printed in EVERY item where 0 is allowed and the first-digit rule is not 'may not be 0' (r3 printed it only for the rule 'any', which left 17.6-19.0 % of items
        where the key changes with the reading: 'even' and 'less than 5' accept 0). The sentence is ``ZERO_SENTENCE``; the 'any' rule then has no first-digit text of its own.
    (c) The longest code length is 3 + level (r3: 3, 3, 4, 4, 4, 6, 6, which made levels 0=1, 2=3=4, 5=6 identical); a code never has more digits than there are allowed digits."""
    s_hi = 3 + level

    def draw() -> tuple[list[int], int, bool, str, str, int] | None:
        digits = list(r.choice(_SUBSETS))
        s = min(r.randint(3, s_hi), len(digits))
        rep = r.random() < 0.5
        first = r.choice(["any", "not0", "odd", "even", "ge5", "lt5"] if 0 in digits else ["any", "odd", "even", "ge5", "lt5"])
        last = r.choice(list(_RULES_LAST))
        cnt = slot_count(digits, s, rep, first, last)
        return (digits, s, rep, first, last, cnt) if cnt > 0 else None

    digits, s, rep, first, last, cnt = until(draw)
    rules = ["no digit may be used more than once" if not rep else "a digit may be used more than once"]
    if first != "any":
        rules.append(_FIRST_TXT[first])
    rules.append(_LAST_TXT[last])
    lead = f"{ZERO_SENTENCE} " if zero_rule_stated(digits, first) else ""
    q = f"{ctx(r)} {lead}How many {s}-digit codes can be written using only the digits {and_([str(d) for d in digits])}, if " + and_(rules) + f"? {WHOLE}"
    return Built(q, {"digits": digits, "length": s, "repeat": rep, "first": first, "last": last}, str(cnt), "number", None)


# ------------------------------------------------------------------ loaders

# Round-4 drops (status NOT_REGISTERED, excluded everywhere: R-24, R-25, R-12). Decided mechanically by ``m1_fix4_survivors`` from the measurements (bound 0.15, two-sided) and recorded with every number in
# ``manifests/m1_fix4_survivors.json``; this is the machine-readable list the loaders use (a test checks that it equals the manifest's round-4 drops). The strings are the reasons (MEASURED, N = 2,000 per level).
NOT_REGISTERED_FIX4: dict[str, str] = {
    "M1.coins_r3": "R-24: the audit-4 rule 'floor(total / hi) - 1' scores +0.160 above the base at level 0 (+0.140, +0.128, +0.114, +0.110, +0.087, +0.076 at levels 1-6); AUDIT4_M1 sections 3 and 8. Not one of the repairs (a)-(c).",
    "M1.pigeonhole_worst_case_r3": "R-24: the audit-4 rule 'draw every other colour, then k of the largest' scores +0.287 above the base at level 1 (+0.229 to +0.287 at every level); AUDIT4_M1 sections 3 and 8. Not one of the repairs (a)-(c).",
    "M1.mode_tally_r3": "R-24: the audit-4 rule 'most frequent answer for the same visible ask and list length' scores +0.382 above the base at level 1 (+0.367 to +0.382 at every level); AUDIT4_M1 sections 3 and 8; its levels are also flat. Not one of the repairs (a)-(c).",
    "M1.slot_permutations_r4": "R-26: the round-4 repair ((b) leading-zero sentence in every item with 0 allowed; (c) longest code length 3 + level) was measured once after it was written; the audit-4 rule 'most frequent answer for the same visible first/last rule, repeat flag and code length' scores +0.188 at level 6 (+0.125 at level 4, +0.123 at level 5), above 0.15. Dropped, not repaired again. Diagnostic: the code length is capped by the number of allowed digits in 0 / 12 / 25 / 40 / 51 / 59 / 65 % of items at levels 0-6.",
}


def _repaired_stems() -> list[str]:
    return sorted(x.id.removeprefix("M1.").removesuffix("_r4") for x in FIX4)


def load_all() -> list[Lineage]:
    """The 36 written lineages of round 3 with each repaired stem replaced by its r4 revision (35 + tiered_pricing), sorted by id. Registered or not; ``load_registered`` removes the NOT REGISTERED."""
    base = {x.id: x for x in load_all_fix3()}
    for new in FIX4:
        del base[REPLACES[new.id]]
    return sorted([*base.values(), *FIX4], key=lambda x: x.id)


def not_registered() -> dict[str, str]:
    out = {k: v for k, v in NOT_REGISTERED_FIX3.items()}
    out.update(NOT_REGISTERED_FIX4)
    return out


def load_registered() -> list[Lineage]:
    nr = not_registered()
    return [x for x in load_all() if x.id not in nr]


def stem(lid: str) -> str:
    st = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        st = st.removesuffix(suf)
    return st


__all__ = ["FIX4", "GCD_LCM_TABLE", "LEVEL_PARAMETER", "NOT_REGISTERED_FIX4", "ZERO_SENTENCE", "fd_answer_ceiling", "fd_ceilings", "gcd_lcm_ceiling", "level_parameter_values", "load_all", "load_registered", "not_registered", "stem"]
