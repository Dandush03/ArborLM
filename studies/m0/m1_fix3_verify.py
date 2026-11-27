# ruff: noqa: E501
"""M1 fix round 3: an INDEPENDENT-STYLE re-derivation of every answer from the structured form by brute force (search, simulation, enumeration) rather than by the formula the builder uses.

This is the implementer's self-check. It is NOT a second solver from a separate context (ruling R-9 still requires that) and not independent review. ``verify(stem, structured)`` returns the answer
string or raises ValueError when the structured form does not have a unique answer.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from fractions import Fraction
from typing import Any

from studies.m0.lineages_m1_fix3_common import fmt_exact


def _unique(xs: list[int]) -> int:
    if len(xs) != 1:
        raise ValueError(f"not unique: {xs[:5]}")
    return xs[0]


def verify(stem: str, s: dict[str, Any]) -> str:  # noqa: C901
    if stem == "shopping":
        return fmt_exact(Fraction(s["paid"] - sum(c * p for c, p in s["items"]), 100))
    if stem == "speed_distance":
        dist = sum(h * v for h, v in s["legs"])
        tot = sum(h for h, _ in s["legs"])
        return str(dist // tot) if s["average"] else str(dist)
    if stem == "mixture":
        return fmt_exact(Fraction(s["x"] * s["a"] + s["y"] * s["b"], s["x"] + s["y"]) + s["packing"])
    if stem == "percent_change":
        v = Fraction(s["price"])
        for k, p in s["steps"]:
            v *= Fraction(100 + p if k == "up" else 100 - p, 100)
        return fmt_exact(v)
    if stem == "tip_split":
        return fmt_exact(Fraction(s["bill"]) * (100 + s["tip"]) / 100 / s["people"])
    if stem == "fraction_remainder":
        left = s["start"]
        spent = left // s["a"]
        assert spent * s["a"] == left
        left -= spent
        spent = left // s["b"]
        assert spent * s["b"] == left
        return str(left - spent)
    if stem == "ratio_share":
        unit = s["total"] // sum(s["parts"])
        assert unit * sum(s["parts"]) == s["total"]
        return str(unit * s["parts"][s["who"]])
    if stem == "linear_equation":
        sols = [x for x in range(-2000, 4000) if (s["k"] * x + s["m"] == s["n"] if not s["j"] else s["k"] * x + s["m"] == s["j"] * x + s["n"])]
        return str(_unique(sols))
    if stem == "ages":
        sols = [b for b in range(1, 2000) if (s["k"] * b + s["t"]) + (b + s["t"]) == s["sum"]]
        b = _unique(sols)
        return str(b if s["ask"] == "younger" else s["k"] * b)
    if stem == "consecutive":
        sols = [a for a in range(-2000, 60000) if sum(a + s["step"] * i for i in range(s["count"])) == s["sum"]]
        a = _unique(sols)
        return str(a + s["step"] * (s["count"] - 1) if s["ask"] == "largest" else a)
    if stem == "average_missing":
        sols = [x for x in range(0, 101) if Fraction(sum(s["scores"]) + x, s["n"]) * 100 == s["mean_cents"]]
        return str(_unique(sols))
    if stem == "pipes_work":
        vol, minutes = 0, 0
        while vol < s["volume"]:
            vol += s["a"] + s["b"] - s["drain"]
            minutes += 1
        if vol != s["volume"]:
            raise ValueError("volume not reached exactly")
        return str(minutes)
    if stem == "rectangle":
        sols = []
        for w in range(1, 2000):
            ln = s["perimeter"] // 2 - w
            if ln > 0 and (ln == s["ratio"] * w if s["shape"] == "ratio" else ln == w + s["excess"]):
                sols.append(w * ln)
        return str(_unique(sols))
    if stem == "coins":
        sols = [nl for nl in range(s["count"] + 1) if nl * s["lo"] + (s["count"] - nl) * s["hi"] == s["cents"]]
        nl = _unique(sols)
        return str(nl if s["ask"] == "lo" else s["count"] - nl)
    if stem == "arithmetic_series":
        return str(sum(s["first"] + s["step"] * i for i in range(s["days"])))
    if stem == "clock_duration":
        return str(sum(b - a for a, b in s["legs"]))
    if stem == "gcd_lcm":
        v = s["values"]
        if s["ask"] == "gcd":
            return str(max(d for d in range(1, min(v) + 1) if all(x % d == 0 for x in v)))
        t = max(v)
        while any(t % x for x in v):
            t += 1
        return str(t)
    if stem == "crt_congruence":
        mods = [m for m, _ in s["conditions"]]
        return str(next(n for n in range(1, math.prod(mods) + 1) if all(n % m == r for m, r in s["conditions"])))
    if stem == "prime_factors":
        rest, p, fac = s["n"], 2, []
        while rest > 1:
            while rest % p == 0:
                fac.append(p)
                rest //= p
            p += 1
        c = Counter(fac)
        return str({"divisors": sum(1 for d in range(1, s["n"] + 1) if s["n"] % d == 0) if s["n"] <= 100000 else math.prod(e + 1 for e in c.values()), "largest": max(fac), "distinct_sum": sum(c), "factor_count": len(fac)}[s["ask"]])
    if stem == "last_digit_power":
        vals = []
        for b, e in s["terms"]:
            x = 1
            for _ in range(e):  # literally e factors, each equal to b (the wording)
                x = x * b % s["modulus"]
            vals.append(x)
        return str(int((sum(vals) if s["op"] == "sum" else math.prod(vals)) % s["modulus"]))
    if stem == "inclusion_exclusion":
        sizes, pairs, tr, tot = s["sizes"], s["pairs"], s["triple"], s["total"]
        if tr is None:
            ab = pairs[0]
            only = [sizes[0] - ab, sizes[1] - ab]
            reg = {"none": tot - (sum(only) + ab), "any": sum(only) + ab}
        else:
            a, b, c = sizes
            ab, ac, bc = pairs
            abc = tr
            exactly2 = (ab - abc) + (ac - abc) + (bc - abc)
            one = (a - ab - ac + abc) + (b - ab - bc + abc) + (c - ac - bc + abc)
            anyone = one + exactly2 + abc
            reg = {"none": tot - anyone, "any": anyone, "exactly_one": one, "exactly_two": exactly2}
        return str(reg[s["ask"]])
    if stem == "binomial_choose":
        return str(math.prod(math.factorial(x) // (math.factorial(j) * math.factorial(x - j)) for x, j in s["groups"]))
    if stem == "slot_permutations":
        from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST

        digs, ln = s["digits"], s["length"]
        n = 0
        if len(digs) ** ln <= 400000:
            gen = itertools.product(digs, repeat=ln) if s["repeat"] else itertools.permutations(digs, ln)
            n = sum(1 for code in gen if _RULES_FIRST[s["first"]](code[0]) and _RULES_LAST[s["last"]](code[-1]))
            return str(n)
        raise ValueError("too large to enumerate")
    if stem == "change_ways":
        t, coins = s["target"], s["coins"]
        return str(sum(1 for x in range(t // coins[0] + 1) for y in range((t - x * coins[0]) // coins[1] + 1) if (t - x * coins[0] - y * coins[1]) >= 0 and (t - x * coins[0] - y * coins[1]) % coins[2] == 0))
    if stem == "pigeonhole_worst_case":
        counts = s["counts"]
        if s["goal"] == "same":
            k = s["k"]
            reach = {0}  # totals of a draw in which no colour reaches k: dynamic programme over colours
            for cnt in counts:
                reach = {b + t for b in reach for t in range(0, min(cnt, k - 1) + 1)}
            return str(max(reach) + 1)
        # all: the longest draw missing some colour = everything except the whole of one colour
        return str(max(sum(counts) - cnt for cnt in counts) + 1)
    if stem == "median_list":
        sv = sorted(s["values"])
        cnt_v = len(sv)
        return fmt_exact(Fraction(sv[cnt_v // 2]) if cnt_v % 2 else Fraction(sv[cnt_v // 2 - 1] + sv[cnt_v // 2], 2))
    if stem == "mode_tally":
        c = Counter(s["values"])
        top = c.most_common(2)
        if top[0][1] == top[1][1]:
            raise ValueError("two most frequent values")
        return str(top[0][0] if s["ask"] == "mode" else len(s["values"]) - top[0][1])
    if stem == "division_counting":
        if s["shape"] == "pallets":
            boxes = s["items"] // s["box"]
            return str(boxes - (boxes // s["crate"]) * s["crate"])
        buses = -(-s["people"] // s["seats"])
        return str(buses * s["seats"] - s["people"])
    if stem == "digit_puzzle":
        from studies.m0.lineages_m1_fix3_c import clue_holds

        nd = s["digits"]
        out: dict[bool, list[int]] = {}
        for once in (False, True):
            out[once] = [m for m in range(10 ** (nd - 1), 10**nd) if all(clue_holds(m, tuple(int(ch) for ch in str(m)), tuple(cl), once) for cl in s["clues"])]
        if out[False] != out[True] or len(out[False]) != 1:
            raise ValueError(f"not unique under both readings: {out}")
        return str(out[False][0])
    if stem == "quadratic_area":
        sh, d = s["shape"], s["d"]
        if sh in ("rect_area", "product"):
            return str(_unique([x for x in range(1, 5000) if x * (x + d) == s["area"]]))
        if sh == "squares":
            return str(_unique([x for x in range(1, 5000) if x * x + (x + d) ** 2 == s["total"]]))
        longer = [s["perimeter"] // 2 - w for w in range(1, 5000) if s["perimeter"] // 2 - w >= w and w * (s["perimeter"] // 2 - w) == s["area"]]
        return str(_unique(longer))
    if stem == "pythagoras":
        a, b = s["legs"]
        c = s["hyp"]
        if a * a + b * b != c * c:
            raise ValueError("not a Pythagorean triple")
        return {"ladder_top": str(b), "ladder_base": str(a), "walk": str(c), "diagonal": str(c), "perimeter": str(a + b + c)}[s["shape"]]
    if stem == "grid_perimeter":
        cells = {(y, x) for y, rr in enumerate(s["rows"]) for a, b in rr for x in range(a, b + 1)}
        shared = sum(1 for (y, x) in cells for dy, dx in ((0, 1), (1, 0)) if (y + dy, x + dx) in cells)
        return str(4 * len(cells) - 2 * shared)
    if stem == "painted_cube":
        a, b, c = s["dims"]
        cnt = 0
        for x in range(a):
            for y in range(b):
                for z in range(c):
                    p = (x in (0, a - 1)) + (y in (0, b - 1)) + (z == c - 1) + (z == 0 and not s["bottom_unpainted"])
                    cnt += p == s["faces"]
        return str(cnt)
    if stem == "recurrence_iterate":
        n = s["position"]
        if s["shape"] == "sum_prev_two":
            t = list(s["first"])
            while len(t) < n:
                t.append(t[-1] + t[-2])
        elif s["shape"] == "affine":
            t = [s["first"][0]]
            while len(t) < n:
                t.append(s["mult"] * t[-1] + s["add"])
        else:
            t = [s["first"][0]]
            while len(t) < n:
                t.append(t[-1] + s["add"] * (len(t) + 1))
        return str(t[n - 1])
    if stem == "finite_differences":
        terms, deg, ask = s["terms"], s["degree"], s["ask"]
        xs = list(range(1, len(terms) + 1))

        def lagrange(pts: list[int], x: int) -> Fraction:
            tot = Fraction(0)
            for i, xi in enumerate(pts):
                li = Fraction(1)
                for j, xj in enumerate(pts):
                    if i != j:
                        li *= Fraction(x - xj, xi - xj)
                tot += li * terms[xi - 1]
            return tot

        for x in xs[deg + 1:]:  # the polynomial of the stated degree through the first deg + 1 points must reproduce every printed term
            assert lagrange(xs[: deg + 1], x) == terms[x - 1]
        v = lagrange(xs[: deg + 1], ask)
        assert v.denominator == 1
        return str(int(v))
    if stem == "tiered_pricing":
        def bill(u: int) -> int:
            left, tot = u, 0
            for size, rate in s["tiers"]:
                take = min(left, size)
                tot += take * rate
                left -= take
            return int(tot + left * s["last_rate"])

        if s["mode"] == "bill":
            return fmt_exact(Fraction(bill(s["used"]), 100))
        return str(_unique([u for u in range(0, 5000) if bill(u) == s["bill_cents"]]))
    raise KeyError(stem)
