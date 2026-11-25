# ruff: noqa: E501
"""M1 fix round 3, part B: number theory, counting and statistics (revisions of the rev2 shapes ``lineages_m1_rev2.py``, immutable). New ids ``M1.<stem>_r3``."""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Callable
from fractions import Fraction

from studies.m0.core import Built
from studies.m0.lineages_m1_fix3_common import DECIMAL, WHOLE, and_, ctx, fmt_exact, pl, r3, until
from studies.m0.vocab import NAMES

# ------------------------------------------------------------------ number theory


def _coprime_set(r: random.Random, k: int, top: int, lo: int = 2) -> list[int]:
    def draw() -> list[int] | None:
        out: list[int] = []
        for _ in range(k):
            m = r.randint(lo, top)
            if m in out or any(math.gcd(m, x) != 1 for x in out):
                return None
            out.append(m)
        return out

    return list(until(draw))


@r3("gcd_lcm", "number_theory")
def gcd_lcm_r3(level: int, r: random.Random) -> Built:
    """structured {"ask": "gcd" | "lcm", "values": [positive integers]}. Ask drawn first; pairwise coprime q_1..q_k (k = 2 below level 3, 3 for levels 3-4, 4 from level 5; q <= 50 / 30 / 24) and a common
    factor g (2..40 / 24 / 24). The values depend on the ask, BY CONSTRUCTION:
      gcd: v_i = g * prod(q_j, j != i). gcd(values) = g exactly, while the gcd of ANY proper subset is larger (it contains the omitted q's), so 'gcd of the two smallest', 'of the two largest',
      'of the first two', 'smallest value', 'smallest difference' are not the gcd (audit: gcd of the two smallest +0.32 to +0.38 with values d * u for random u).
      lcm: v_i = g * q_i. lcm(values) = g * prod(q), while the lcm of any proper subset is smaller, so 'lcm of the two largest' and 'lcm of the first two' are not the lcm, and neither is the product
      (it carries g^k) nor the largest value. (The dual construction would make the lcm of any two values the lcm of all: first attempt, measured +0.49 on the lcm ask, kept in the notes.)
    gcd: the longest ribbon piece cutting every ribbon exactly; lcm: the first common flash time."""
    ask = r.choice(("gcd", "lcm"))
    k = 2 if level < 3 else (3 if level < 5 else 4)
    top, gmax = {2: (50, 40), 3: (30, 24), 4: (24, 24)}[k]
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


@r3("crt_congruence", "number_theory")
def crt_congruence_r3(level: int, r: random.Random) -> Built:
    """structured {"conditions": [[modulus, remainder]]}. Pairwise coprime moduli, every modulus >= 9 (k = 2 below level 3: up to 60 + 10 * level; k = 3, 4: up to 24 + 4 * level), remainder 1..m-1 uniformly.
    The answer is the least positive solution. Moduli of 9 or more make 'the remainder of the largest modulus' and 'the solution of all but the last condition' right only with chance about 1 / modulus
    (audit: +0.09 to +0.12 with moduli from 3); nothing is redrawn on the answer."""
    k = 2 if level < 3 else (3 if level < 5 else 4)
    top = 60 + 10 * level if k == 2 else 24 + 4 * level
    mods = _coprime_set(r, k, top, 9)
    rems = [r.randint(1, m - 1) for m in mods]
    P = math.prod(mods)
    x, step = 0, 1
    for m, rr in zip(mods, rems, strict=True):
        while x % m != rr:
            x += step
        step *= m
    ans = x if x > 0 else P
    assert 0 < ans <= P and all(ans % m == rr for m, rr in zip(mods, rems, strict=True))
    conds = [[m, rr] for m, rr in zip(mods, rems, strict=True)]
    name = r.choice(NAMES)
    txt = "; ".join(f"dividing it by {m} leaves remainder {rr}" for m, rr in conds)
    q = f"{name} is thinking of a positive whole number. {txt[0].upper() + txt[1:]}. What is the smallest positive whole number that {name} could be thinking of? {WHOLE}"
    return Built(q, {"conditions": conds}, str(ans), "number", None)


_SMOOTH_CACHE: dict[int, list[int]] = {}
_P97 = tuple(p for p in range(2, 98) if all(p % q for q in range(2, int(p**0.5) + 1)))
_NMAX = (30000, 50000, 100000, 200000, 400000, 800000, 1600000)


def _smooth(level: int) -> list[int]:
    """All n in 12..nmax(level) whose prime factors are all <= 97 and that have at least two distinct prime factors (sorted)."""
    if level not in _SMOOTH_CACHE:
        nmax = _NMAX[level]
        out: list[int] = []

        def rec(i: int, n: int, k: int) -> None:
            if i == len(_P97):
                if k >= 2 and n >= 12:
                    out.append(n)
                return
            rec(i + 1, n, k)
            m = n * _P97[i]
            while m <= nmax:
                rec(i + 1, m, k + 1)
                m *= _P97[i]

        rec(0, 1, 0)
        _SMOOTH_CACHE[level] = sorted(out)
    return _SMOOTH_CACHE[level]


@r3("prime_factors", "number_theory")
def prime_factors_r3(level: int, r: random.Random) -> Built:
    """structured {"n": N, "ask": "divisors" | "largest" | "distinct_sum" | "factor_count"}. Ask drawn first. N is drawn UNIFORMLY from the integers 12..nmax(level) (30,000 at level 0 up to 1,600,000 at level 6)
    whose prime factors are all at most 97 and that have at least two different prime factors (a precomputed list; no rejection). Batch 1 and rev2 built N from a small prime pool, which capped capacity."""
    ask = r.choice(("divisors", "largest", "distinct_sum", "factor_count"))
    n = r.choice(_smooth(level))
    fac: dict[int, int] = {}
    m = n
    for p in _P97:
        while m % p == 0:
            fac[p] = fac.get(p, 0) + 1
            m //= p
    assert m == 1
    ans = {"divisors": math.prod(e + 1 for e in fac.values()), "largest": max(fac), "distinct_sum": sum(fac), "factor_count": sum(fac.values())}[ask]
    what = {
        "divisors": "How many different positive whole numbers divide it exactly (counting 1 and the number itself)?",
        "largest": "What is the largest prime number that divides it exactly?",
        "distinct_sum": "Add up the different prime numbers that divide it exactly (each different prime counted once). What is the sum?",
        "factor_count": "Write it as a product of prime numbers, repeating a prime as often as needed (for example 12 = 2 x 2 x 3 uses three primes). How many primes are multiplied?",
    }[ask]
    return Built(f"{ctx(r)} Consider the number {n}. {what} {WHOLE}", {"n": n, "ask": ask}, str(ans), "number", None)


_PRIMES_P = (29, 37, 43, 47, 53, 59, 67, 79)  # p - 1 is never a multiple of 5 (so the exponent's last digit says nothing about the exponent modulo p - 1)


@r3("last_digit_power", "number_theory")
def power_remainder_r3(level: int, r: random.Random) -> Built:
    """structured {"modulus": p, "op": "sum" | "product", "terms": [[base, exponent]]}. As rev2 with the prime set {29, 37, 43, 47, 53, 59, 67, 79} (all have p - 1 not a multiple of 5);
    a larger p flattens the answer distribution (rev2 with p in 17..29: the most frequent answer was 0.15-0.16 at levels 0-1; a first widening to 17..59 gave 0.117). Each term is the product of `exponent` factors, each equal to `base` (stated)."""
    p = r.choice(_PRIMES_P)
    t = 1 if level < 2 else (2 if level < 5 else 3)
    op = r.choice(("sum", "product")) if t > 1 else "sum"
    terms: list[list[int]] = []
    for _ in range(t):
        b = r.choice([v for v in range(2, 100 + 30 * level) if v % p])
        terms.append([b, r.randint(12, 300 + 100 * level)])
    vals = [pow(b, e, p) for b, e in terms]
    ans = (sum(vals) if op == "sum" else math.prod(vals)) % p
    parts = [f"the product of {e} factors, each equal to {b}" for b, e in terms]
    if t == 1:
        body = f"Let X be {parts[0]}."
    elif op == "sum":
        body = "Let X be the sum of " + and_(parts) + "."
    else:
        body = "Let X be the product of all the following factors: " + and_([f"{e} factors equal to {b}" for b, e in terms]) + "."
    q = f"{ctx(r)} {body} What is the remainder when X is divided by {p} (a whole number from 0 to {p - 1})? {WHOLE}"
    return Built(q, {"modulus": p, "op": op, "terms": terms}, str(ans), "number", None)


# ------------------------------------------------------------------ counting


@r3("inclusion_exclusion", "counting")
def inclusion_exclusion_r3(level: int, r: random.Random) -> Built:
    """structured {"total", "sets", "sizes", "pairs", "triple", "ask"}. As rev2 with a wider region size (1..20+8*level; rev2 had 1..8+8*level, which gave only 4,356 distinct level-0 items) and an explicit
    convention: in a three-set item every 'do both' number includes the people who do all three."""
    three = level >= 3
    ask = r.choice(("none", "any", "exactly_one", "exactly_two") if level >= 5 else ("none", "any"))
    m = 20 + 8 * level
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
    what = {"none": "do none of these things", "any": "do at least one of these things", "exactly_one": "do exactly one of these things", "exactly_two": "do exactly two of these things"}[ask]
    if not three:
        facts = f"{sizes[0]} of them {acts[0]}, {sizes[1]} of them {acts[1]}, and {pairs[0]} of them do both"
    else:
        facts = (f"{sizes[0]} {acts[0]}, {sizes[1]} {acts[1]} and {sizes[2]} {acts[2]}; {pairs[0]} do both the first and the second, {pairs[1]} do both the first and the third, "
                 f"{pairs[2]} do both the second and the third, and {triple} do all three (each 'do both' number includes the people who do all three)")
    q = f"{total} people were asked what they do. {facts[0].upper() + facts[1:]}. How many of the {total} people {what}? {WHOLE}"
    return Built(q, {"total": total, "sets": acts, "sizes": sizes, "pairs": pairs, "triple": triple, "ask": ask}, str(reg[ask]), "number", None)


@r3("binomial_choose", "counting")
def binomial_choose_r3(level: int, r: random.Random) -> Built:
    """structured {"groups": [[size, picked]]}. A team is chosen from g groups of people (g = 2 below level 3, 3 from level 3) with exactly `picked` from each group; the order does not matter.
    Answer: the product of binomial coefficients. Group size 3..14+2*level, picked 1..3+level//2 (and at most the size); the answer is capped at 10**(4 + level) (a size cap, the only loop).
    The plain 'choose k from n' and 'must include one person' shapes of rev2 are DROPPED: their space is a few hundred items (n_eff 224 at level 0) however they are widened. See NOTES_FIX3_M1.md:
    even so this lineage does not reach the demand at low levels."""
    g = 2 if level < 3 else 3
    cap = 10 ** (4 + level)

    def draw() -> list[list[int]] | None:
        gs = [[x, r.randint(1, min(x, 3 + level // 2))] for x in (r.randint(3, 14 + 2 * level) for _ in range(g))]
        return gs if math.prod(math.comb(x, j) for x, j in gs) <= cap else None

    gs = until(draw)
    ans = math.prod(math.comb(x, j) for x, j in gs)
    kinds = ["women", "men", "children"][:g]
    sing = {"women": "woman", "men": "man", "children": "child"}
    total = sum(j for _, j in gs)
    have = and_([f"{x} {k}" for (x, _), k in zip(gs, kinds, strict=True)])
    pick = and_([f"{j} {sing[k] if j == 1 else k}" for (_, j), k in zip(gs, kinds, strict=True)])
    q = f"{ctx(r)} A group has {have}. A team of {total} people is chosen (the order does not matter) with exactly {pick} on it. How many different teams are possible? {WHOLE}"
    return Built(q, {"groups": gs}, str(ans), "number", None)


_RULES_FIRST: dict[str, Callable[[int], bool]] = {"any": lambda d: True, "not0": lambda d: d != 0, "odd": lambda d: d % 2 == 1, "even": lambda d: d % 2 == 0, "ge5": lambda d: d >= 5, "lt5": lambda d: d < 5}
_RULES_LAST: dict[str, Callable[[int], bool]] = {"odd": lambda d: d % 2 == 1, "even": lambda d: d % 2 == 0, "ge5": lambda d: d >= 5, "lt5": lambda d: d < 5}
_SUBSETS = [c for n in range(4, 10) for c in itertools.combinations(range(10), n)]


def slot_count(digits: list[int], s: int, rep: bool, first: str, last: str) -> int:
    """Product rule: fill the first and last positions (restricted), then the middle ones."""
    n = len(digits)
    f = [d for d in digits if _RULES_FIRST[first](d)]
    p = [d for d in digits if _RULES_LAST[last](d)]
    if rep:
        return int(len(f) * len(p) * n ** (s - 2))
    both = len(set(f) & set(p))
    return (len(f) * len(p) - both) * math.perm(n - 2, s - 2)


_FIRST_TXT = {"any": "", "not0": "the first digit may not be 0", "odd": "the first digit must be odd", "even": "the first digit must be even", "ge5": "the first digit must be 5 or more", "lt5": "the first digit must be less than 5"}
_LAST_TXT = {"odd": "the last digit must be odd", "even": "the last digit must be even", "ge5": "the last digit must be 5 or more", "lt5": "the last digit must be less than 5"}


@r3("slot_permutations", "counting")
def slot_permutations_r3(level: int, r: random.Random) -> Built:
    """structured {"digits": [..], "length": s, "repeat": bool, "first": rule, "last": rule}. Codes of s digits written with the allowed digits (4..9 of 0-9, uniformly among the 847 subsets); no digit twice unless `repeat`;
    the FIRST digit obeys one of {any, not 0, odd, even, >= 5, < 5} (not 0 only when 0 is allowed; for 'any' with 0 allowed the item says a code such as 012 is allowed) and the LAST digit one of {odd, even,
    >= 5, < 5} (always a restriction, by construction). The answer is positive (a validity loop). Level: the code length is as in rev2 (3 at levels 0-1 up to 6 at level 5). Widened from rev2's parity-only
    last-digit rule (capacity: 1,163 distinct at level 1)."""
    s_hi = 3 + (level + 1) // 3 + (level >= 5)

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
    if first == "any":
        if 0 in digits:
            rules.append("the first digit may be 0 (a code such as 012 is allowed)")
    else:
        rules.append(_FIRST_TXT[first])
    rules.append(_LAST_TXT[last])
    q = f"{ctx(r)} How many {s}-digit codes can be written using only the digits {and_([str(d) for d in digits])}, if " + and_(rules) + f"? {WHOLE}"
    return Built(q, {"digits": digits, "length": s, "repeat": rep, "first": first, "last": last}, str(cnt), "number", None)


@r3("change_ways", "counting")
def change_ways_r3(level: int, r: random.Random) -> Built:
    """structured {"coins": [3 values in cents], "target": T}. Coins drawn from 17 values (2..9, 10, 12, 15, 20, 25, 30, 40, 50); T = sum of c_i * x_i (x_i uniform 0..5+2*level) + 6 * smallest coin, so at least one
    way exists by construction. Answer: the number of multisets of coins summing to T (a change-making table). No redraw."""
    coins = sorted(r.sample((2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50), 3))
    xmax = 5 + 2 * level
    t = sum(c * r.randint(0, xmax) for c in coins) + coins[0] * 6
    ways = [1] + [0] * t
    for v in coins:
        for a in range(v, t + 1):
            ways[a] += ways[a - v]
    q = (f"{ctx(r)} Using only coins worth {and_([str(v) for v in coins])} cents, with as many coins of each value available as you like, in how many different ways can exactly {t} cents be paid? "
         f"(Two ways are the same if they use the same number of coins of each value; the order does not matter.) {WHOLE}")
    return Built(q, {"coins": coins, "target": t}, str(ways[t]), "number", None)


@r3("pigeonhole_worst_case", "counting")
def pigeonhole_worst_case_r3(level: int, r: random.Random) -> Built:
    """structured {"counts", "goal": "same" | "all", "k"}. Goal drawn first. Colour counts are drawn LOG-uniformly on 2..200+30*level, so the smallest count is usually far below the largest and 'ignore the caps,
    (k - 1) c + 1' is right only when every colour has at least k - 1 marbles (audit: +0.10 to +0.18 with uniform counts); for goal 'same', k is uniform on 2..max(count), so a colour with k marbles exists."""
    goal = r.choice(("same", "all"))
    c = 3 + (level >= 2) + (level >= 4)
    top = 200 + 30 * level
    counts = [max(2, min(top, round(math.exp(r.uniform(math.log(2), math.log(top)))))) for _ in range(c)]
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
    q = (f"A bag holds marbles of {c} colours: {inv}. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the "
         f"draws are, of having {what}? {WHOLE}")
    return Built(q, {"counts": counts, "goal": goal, "k": k}, str(ans), "number", None)


# ------------------------------------------------------------------ statistics


@r3("median_list", "statistics")
def median_list_r3(level: int, r: random.Random) -> Built:
    """structured {"shape": "list", "values": [..]}. n = 7+level .. 10+2*level values (so odd and even counts both occur), each 1..200+60*level (rev2: 1..30+20*level); repeats are rare, so 'the mode of the values' and
    'a printed value at a fixed position' are right only by chance (audit: +0.155 at level 0). Answer: the median (the mean of the two middle values when the count is even), at most two decimals."""
    n = r.randint(7 + level, 10 + 2 * level)
    vals = [r.randint(1, 200 + 60 * level) for _ in range(n)]
    s = sorted(vals)
    mid = Fraction(s[(n - 1) // 2] + s[n // 2], 2)
    q = (f"{ctx(r)} The values are {and_([str(v) for v in vals])}. What is the median of all the values (the middle value once they are sorted from smallest to largest; if there are two middle values, "
         f"the number halfway between them)? {DECIMAL}")
    return Built(q, {"shape": "list", "values": vals}, fmt_exact(mid), "number", None)


@r3("mode_tally", "statistics")
def mode_tally_r3(level: int, r: random.Random) -> Built:
    """structured {"values": [..], "ask": "mode" | "others"}. Ask drawn first. One mode occurring f times (f 4..6), R rivals (7..10) occurring f - 1 times each, and a tail of T (2..4) values occurring
    1..f - 2 times, then shuffled. 'mode': which value occurs most often. 'others' (replaces rev2's 'how many times does the mode occur', whose answer had only 4-8 possible values, a most frequent answer of
    0.15 at level 0): how many of the scores are NOT equal to the most frequent value (n - f, a number that varies over about 30 values). Both need the full frequency table. More rivals than rev2 (2-4) lower
    the chance that 'the first value that repeats' or 'the most common value of the first half' is the mode. There is exactly one most frequent value (said in the item). The list grows with the level only
    through the value range (a longer list would be a different task)."""
    ask = r.choice(("mode", "others"))
    f = r.randint(4, 6)
    rivals = r.randint(7, 10)
    tail = r.randint(2, 4)
    hi = 40 + 8 * level + 2 * (rivals + tail)
    pool = r.sample(range(1, hi + 1), 1 + rivals + tail)
    counts = [f] + [f - 1] * rivals + [r.randint(1, f - 2) for _ in range(tail)]
    vals = [v for v, c in zip(pool, counts, strict=True) for _ in range(c)]
    r.shuffle(vals)
    n = len(vals)
    ans = pool[0] if ask == "mode" else n - f
    what = ("Which value occurs most often? There is exactly one such value." if ask == "mode"
            else "How many of the scores are not equal to the value that occurs most often (every score that is not that value counts, once for each time it is written)? There is exactly one most frequent value.")
    q = f"A teacher wrote down {n} test scores: {and_([str(v) for v in vals])}. {what} {WHOLE}"
    return Built(q, {"values": vals, "ask": ask}, str(ans), "number", None)


# ------------------------------------------------------------------ division


@r3("division_counting", "division")
def division_counting_r3(level: int, r: random.Random) -> Built:
    """structured {"shape": "pallets" | "empty_seats", ...}. Shape drawn first (half each). pallets {"items": N, "box": k, "crate": m}: answer (N // k) % m, the boxes not on a full pallet.
    empty_seats {"people": N, "seats": k}: answer ceil(N / k) * k - N. Ranges widened (rev2 level 0 had 20,040 distinct items): box 4..30+3*level, pallet 3..20+2*level, seats 8..60+5*level."""
    shape = r.choice(("pallets", "empty_seats"))
    s = 1 + level
    if shape == "pallets":
        k, m = r.randint(4, 30 + 3 * s), r.randint(3, 20 + 2 * s)
        n = r.randint(3 * k * m, 20 * k * m + 400 * level)
        ans = (n // k) % m
        item = r.choice(("apple", "book", "candle", "ribbon", "spoon", "kettle"))
        q = (f"{ctx(r)} A factory makes {n} {item}s. They are packed into boxes that each hold exactly {k} {item}s; {item}s that do not fill a box are left out. The boxes are then put on pallets that each hold {m} boxes, "
             f"and as many full pallets as possible are made. How many boxes are not on a full pallet? {WHOLE}")
        st: dict[str, object] = {"shape": shape, "items": n, "box": k, "crate": m}
    else:
        k = r.randint(8, 60 + 5 * s)
        n = r.randint(3 * k, 25 * k + 100 * level)
        ans = -(-n // k) * k - n
        name = r.choice(NAMES)
        q = f"{n} people must travel by bus, and {name} hires as few buses as possible. Each bus has {k} seats, and nobody stands. When all {n} people are on board, how many seats in total are empty? {WHOLE}"
        st = {"shape": shape, "people": n, "seats": k}
    return Built(q, st, str(ans), "number", None)


__all__ = ["pl"]
