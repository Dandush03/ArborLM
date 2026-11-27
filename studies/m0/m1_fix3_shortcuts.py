# ruff: noqa: E501
"""M1 fix round 3: cheap-rule (shortcut) battery for the new revisions. MEASURED, not thresholded: the working target of the fix round is every rule within +-0.10 of the base rate, two-sided,
at every level; it is a working target, not a registered bound.

ATTRIBUTION. The battery starts from the independent auditor's ``shortcuts_a3.py`` (arbor-auditor, Claude Opus 5.5, docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1/): the same rules, the same base
(the held-out most frequent answer, two folds), the same generic 'echo the number at the best position' rules, adapted to the structured fields of the r3 shapes, plus the rules the audit named for the
defects of this round (memorised triples, gcd of the two smallest, the first clues of a digit puzzle, off-by-one terms) and a few more (gcd of the two largest, lcm of the first two, previous and next
term of a recurrence, the first or last count of a tally). Rates are over ALL items (a rule not applicable to an item counts as a miss); ``__within_applicable`` is the rate over the items it applies to.

Rules that are the CORRECT PROCEDURE on the item class where the omitted step is idle are listed in ``PROCEDURE`` with the reason; they are measured and printed but not counted in the flags.

Run: PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_shortcuts --n 2000 --out <short.json> [--only name,name] [--before]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item, stream

SEED = 410302  # throwaway integer, not a registered study seed

# rule name -> reason it is the correct procedure on the subclass where the omitted step is idle (stem -> {rule: reason})
PROCEDURE: dict[str, dict[str, str]] = {
    "division_counting": {"k_minus_remainder_ignores_exact_fit": "ceil(N / k) * k - N = k - N mod k except when N is an exact multiple of k: the procedure with an idle step"},
    "slot_permutations": {"parity_fraction_of_total": "exact whenever the first-digit rule is 'any' (symmetry); the first-digit rule is the step it omits"},
    "ratio_share": {"largest_share": "a guess of WHICH person was asked (1 / number of parts), as costly as the procedure; not a shortcut to the answer",
                    "smallest_share": "the same guess for the smallest part"},
    "consecutive": {"mean_plus_step": "for 3 numbers the middle one is the mean, so mean + step IS the largest: the procedure for the 3-number case (right only when the ask is 'largest')"},
    "finite_differences": {"next_term_when_asked_later": "extending the table of differences once IS the procedure when the asked position is the next one", "next_term_only": "one extension of the table (right only if the asked position is the next one)"},
    "prime_factors": {"largest_le_sqrt": "needs the full factorisation, then takes the largest prime: the procedure with an idle size check (the audit's rule; with smooth numbers the largest prime is nearly always below the square root)"},
    "gcd_lcm": {"product_over_gcd_of_all": "for two values the lcm is the product over the gcd: the textbook procedure for k = 2"},
}
PROCEDURE["slot_permutations"]["ignore_first_rule"] = "exact whenever the first-digit rule is 'any' (idle); the first-digit rule is the step it omits"


def nums(q: str) -> list[F]:
    return [F(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q.replace("$", " "))]


def _c(n: int, k: int) -> int:
    return math.comb(n, k) if 0 <= k <= n else 0


def _fac(n: int) -> dict[int, int]:
    out: dict[int, int] = {}
    p = 2
    while p * p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p += 1
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def _crt_min(conds: list[list[int]]) -> int | None:
    x, step = 0, 1
    for m, r in conds:
        tries = 0
        while x % m != r:
            x += step
            tries += 1
            if tries > m:
                return None
        step = step * m // math.gcd(step, m)
    return x if x > 0 else step


_PRIM16 = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (12, 35, 37), (9, 40, 41), (28, 45, 53), (11, 60, 61), (16, 63, 65), (33, 56, 65), (48, 55, 73), (13, 84, 85), (36, 77, 85), (39, 80, 89), (65, 72, 97)]


def _catalogue_guess(shape: str, given: list[int], tri: list[tuple[int, int, int]]) -> int | None:
    g = sorted(given)
    guess = None
    for t in tri:
        for i, j in ((0, 1), (0, 2), (1, 2)):
            if g[0] * t[j] == g[1] * t[i] and g[0] % t[i] == 0:
                kk = g[0] // t[i]
                scaled = [x * kk for x in t]
                if shape in ("walk", "diagonal"):
                    guess = scaled[2]
                elif shape == "perimeter":
                    guess = sum(scaled)
                else:
                    rest = [x for x in scaled if x not in g]
                    guess = rest[0] if len(set(scaled) - set(g)) == 1 else None
    return guess


def _sequence(s: dict[str, Any]) -> list[int]:
    n = s["position"] + 2
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
            t.append(t[-1] + max(1, s["add"]) * (len(t) + 1))
    return t


def spec(n: str, s: dict[str, Any]) -> dict[str, F | None]:
    """rule name -> predicted answer (None where the rule does not apply to the item)."""
    h: dict[str, F | None] = {}
    if n == "shopping":
        h["ignore_counts"] = F(s["paid"] - sum(p for _, p in s["items"]), 100)
        h["one_item_only"] = F(s["paid"] - s["items"][0][0] * s["items"][0][1], 100)
    elif n == "speed_distance":
        legs = s["legs"]
        if s["average"]:
            h["mean_of_speeds"] = F(sum(v for _, v in legs), len(legs))
            h["last_speed"] = F(legs[-1][1])
        else:
            h["sum_speeds_x_mean_hours"] = F(sum(v for _, v in legs) * sum(t for t, _ in legs), len(legs))
            h["first_leg_only"] = F(legs[0][0] * legs[0][1])
    elif n == "pipes_work":
        h["ignore_drain"] = F(s["volume"], s["a"] + s["b"]) if s["drain"] else None
        h["one_pipe"] = F(s["volume"], s["a"])
    elif n == "percent_change":
        net = sum(p if k == "up" else -p for k, p in s["steps"])
        h["additive_percents"] = F(s["price"]) * (100 + net) / 100
        h["first_step_only"] = F(s["price"]) * (100 + s["steps"][0][1]) / 100
    elif n == "tip_split":
        h["ignore_tip"] = F(s["bill"], s["people"])
        h["no_split"] = F(s["bill"]) * (100 + s["tip"]) / 100
    elif n == "ratio_share":
        h["equal_split"] = F(s["total"], len(s["parts"]))
        h["largest_share"] = F(s["total"] * max(s["parts"]), sum(s["parts"]))
        h["smallest_share"] = F(s["total"] * min(s["parts"]), sum(s["parts"]))
    elif n == "mixture":
        h["unweighted_mean"] = F(s["a"] + s["b"], 2) + s["packing"]
        h["ignore_packing"] = F(s["x"] * s["a"] + s["y"] * s["b"], s["x"] + s["y"]) if s["packing"] else None
        h["price_of_larger_weight"] = F(s["a"] if s["x"] > s["y"] else s["b"]) + s["packing"]
    elif n == "linear_equation":
        if s["j"]:
            h["sign_error"] = F(s["m"] - s["n"], s["k"] - s["j"])
        else:
            h["ignore_constant"] = F(s["n"], s["k"])
            h["sign_error"] = F(s["n"] + s["m"], s["k"])
    elif n == "consecutive":
        h["mean_rounded"] = F(round(F(s["sum"], s["count"])))
        h["mean_plus_step"] = F(round(F(s["sum"], s["count"]))) + s["step"]
    elif n == "ages":
        mult = s["k"] if s["ask"] == "older" else 1
        h["ignore_years"] = F(s["sum"], s["k"] + 1) * mult
        h["years_once"] = F(s["sum"] - s["t"], s["k"] + 1) * mult
        h["wrong_person"] = F(s["sum"] - 2 * s["t"], s["k"] + 1) * (1 if s["ask"] == "older" else s["k"])
    elif n == "average_missing":
        h["target_mean_rounded"] = F(round(F(s["mean_cents"], 100)))
    elif n == "rectangle":
        h["square"] = F(s["perimeter"], 4) ** 2
        h["width_only"] = F(s["perimeter"], 2 * (s["ratio"] + 1)) if s["ratio"] else None
    elif n == "arithmetic_series":
        a, d, k = s["first"], s["step"], s["days"]
        h["no_growth"] = F(a * k)
        h["last_day_only"] = F(a + (k - 1) * d)
        h["off_by_one_days"] = F((k - 1) * (2 * a + (k - 2) * d), 2)
        h["off_by_one_plus"] = F((k + 1) * (2 * a + k * d), 2)
    elif n == "coins":
        h["value_over_high"] = F(s["cents"] // s["hi"])
        h["value_over_low"] = F(s["cents"] // s["lo"])
        h["half_count"] = F(s["count"] // 2)
    elif n == "clock_duration":
        h["span_incl_waits"] = F(s["legs"][-1][1] - s["legs"][0][0])
    elif n == "fraction_remainder":
        h["both_of_original"] = F(s["start"]) - F(s["start"], s["a"]) - F(s["start"], s["b"])
        h["first_step_only"] = F(s["start"]) - F(s["start"], s["a"])
    elif n == "recurrence_iterate":
        t = _sequence(s)
        h["previous_term"] = F(t[s["position"] - 2])
        h["next_term"] = F(t[s["position"]])
    elif n == "finite_differences":
        t = s["terms"]
        d1 = t[-1] - t[-2]
        h["linear_extrapolation"] = F(t[-1] + d1 * (s["ask"] - len(t)))
        dd = [t[i + 1] - t[i] for i in range(len(t) - 1)]
        d2 = [dd[i + 1] - dd[i] for i in range(len(dd) - 1)]
        h["next_term_only"] = F(t[-1] + dd[-1] + d2[-1]) if s["ask"] == len(t) + 2 else None
        h["next_term_when_asked_later"] = F(t[-1] + dd[-1] + d2[-1]) if s["ask"] == len(t) + 1 else None
    elif n == "quadratic_area":
        if s["shape"] in ("rect_area", "product"):
            h["sqrt_area"] = F(math.isqrt(s["area"]))
            h["sqrt_minus_half_d"] = F(round(math.sqrt(s["area"]) - s["d"] / 2))
        elif s["shape"] == "squares":
            h["sqrt_half_sum"] = F(math.isqrt(s["total"] // 2))
            h["sqrt_half_minus_half_d"] = F(round(math.sqrt(s["total"] / 2) - s["d"] / 2))
        else:
            h["quarter_perimeter"] = F(s["perimeter"], 4)
            h["sqrt_area"] = F(math.isqrt(s["area"]))
    elif n == "tiered_pricing":
        if s["mode"] == "bill":
            h["all_at_last_rate"] = F(s["used"] * s["last_rate"], 100)
            h["all_at_first_rate"] = F(s["used"] * s["tiers"][0][1], 100)
        else:
            h["bill_over_last_rate"] = F(round(F(s["bill_cents"], s["last_rate"])))
            h["bill_over_first_rate"] = F(round(F(s["bill_cents"], s["tiers"][0][1])))
    elif n == "gcd_lcm":
        v = s["values"]
        sv = sorted(v)
        if s["ask"] == "gcd":
            h["min_value"] = F(min(v))
            h["min_difference"] = F(min(abs(a - b) for a in v for b in v if a != b))
            h["gcd_of_two_smallest"] = F(math.gcd(*sv[:2])) if len(v) > 2 else None
            h["gcd_of_two_largest"] = F(math.gcd(*sv[-2:])) if len(v) > 2 else None
            h["gcd_of_first_two_printed"] = F(math.gcd(*v[:2])) if len(v) > 2 else None
            h["gcd_of_min_and_max"] = F(math.gcd(sv[0], sv[-1])) if len(v) > 2 else None
        else:
            h["product"] = F(math.prod(v))
            h["max_value"] = F(max(v))
            h["lcm_of_two_largest"] = F(math.lcm(*sv[-2:])) if len(v) > 2 else None
            h["lcm_of_first_two_printed"] = F(math.lcm(*v[:2])) if len(v) > 2 else None
            h["product_over_gcd_of_all"] = F(math.prod(v), math.gcd(*v)) if len(v) == 2 else None
    elif n == "crt_congruence":
        c = s["conditions"]
        h["largest_mod_remainder"] = F(max(c)[1])
        h["sum_remainders"] = F(sum(r for _, r in c))
        x = _crt_min(c[:-1])
        h["drop_last_condition"] = F(x) if x is not None else None
        x2 = _crt_min(c[1:])
        h["drop_first_condition"] = F(x2) if x2 is not None else None
        h["product_minus_one"] = F(math.prod(m for m, _ in c) - 1)
    elif n == "prime_factors":
        f = _fac(s["n"])
        a = s["ask"]
        if a == "divisors":
            h["two_pow_distinct"] = F(2 ** len(f))
            h["omega_plus_one"] = F(sum(f.values()) + 1)
        elif a == "largest":
            h["smallest_prime"] = F(min(f))
            h["largest_le_sqrt"] = F(max([p for p in f if p * p <= s["n"]] or [min(f)]))
            h["n_over_smallest_prime"] = F(s["n"] // min(f))
        elif a == "distinct_sum":
            h["sum_with_multiplicity"] = F(sum(p * e for p, e in f.items()))
        else:
            h["distinct_count"] = F(len(f))
    elif n == "last_digit_power":
        p, t = s["modulus"], s["terms"]

        def comb(vals: list[int]) -> int:
            return int((sum(vals) if s["op"] == "sum" else math.prod(vals)) % p)

        h["exp_last_digit"] = F(comb([pow(b, e % 10, p) for b, e in t]))
        h["exp_mod_p"] = F(comb([pow(b, e % p, p) for b, e in t]))
        h["base_mod_p"] = F(comb([b % p for b, _ in t]))
        h["fermat_misapplied_e_mod_p_plus_1"] = F(comb([pow(b, e % (p + 1), p) for b, e in t]))
        h["one"] = F(1)
    elif n == "inclusion_exclusion":
        tt, sm, pp, tr, a = s["total"], sum(s["sizes"]), sum(s["pairs"]), s["triple"], s["ask"]
        if tr is None:
            h["none_ignore_overlap"] = F(tt - sm) if a == "none" else None
            h["any_ignore_overlap"] = F(sm) if a == "any" else None
            h["max_size"] = F(max(s["sizes"]))
        else:
            h["forget_triple"] = {"none": F(tt - sm + pp), "any": F(sm - pp), "exactly_one": F(sm - pp), "exactly_two": F(pp)}[a]
            h["ignore_overlaps"] = {"none": F(tt - sm), "any": F(sm), "exactly_one": F(sm - 2 * pp), "exactly_two": F(pp - tr)}[a]
            h["max_size"] = F(max(s["sizes"]))
    elif n == "binomial_choose":
        gs = s["groups"]
        h["ignore_picks_total_choose"] = F(_c(sum(x for x, _ in gs), sum(j for _, j in gs)))
        h["sum_not_product"] = F(sum(_c(x, j) for x, j in gs))
        h["product_of_x_times_j"] = F(math.prod(x * j for x, j in gs))
    elif n == "slot_permutations":
        from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST

        digs, ln, rep, first, last = s["digits"], s["length"], s["repeat"], s["first"], s["last"]
        nn = len(digs)
        tot = nn**ln if rep else math.perm(nn, ln)
        h["ignore_all_restrictions"] = F(tot)
        npar = sum(1 for d in digs if _RULES_LAST[last](d))
        h["parity_fraction_of_total"] = F(round(F(tot * npar, nn)))
        nf = sum(1 for d in digs if _RULES_FIRST[first](d))
        h["ignore_last_rule"] = F(nf * (nn ** (ln - 1) if rep else math.perm(nn - 1, ln - 1)))
        h["ignore_first_rule"] = F(npar * (nn ** (ln - 1) if rep else math.perm(nn - 1, ln - 1)))
        h["swap_repeat_rule"] = F(npar * (math.perm(nn - 1, ln - 1) if rep else nn ** (ln - 1)))
    elif n == "change_ways":
        cs, tt = s["coins"], s["target"]
        h["T_over_max_plus_1"] = F(tt // max(cs) + 1)
        h["T_over_min_plus_1"] = F(tt // min(cs) + 1)
        h["two_smallest_coins_only"] = F(sum(1 for i in range(tt // cs[0] + 1) if (tt - i * cs[0]) % cs[1] == 0))
    elif n == "pigeonhole_worst_case":
        c, k = s["counts"], s["k"]
        if s["goal"] == "same":
            h["ignore_caps"] = F((k - 1) * len(c) + 1)
            h["k_times_colours"] = F(k * len(c))
        else:
            h["sum_minus_max_plus_1"] = F(sum(c) - max(c) + 1)
            h["sum_minus_min"] = F(sum(c) - min(c))
            h["max_plus_1"] = F(max(c) + 1)
    elif n == "median_list":
        v = s["values"]
        h["unsorted_middle"] = F(v[len(v) // 2])
        h["mean_rounded"] = F(round(F(sum(v), len(v))))
        sv = sorted(v)
        h["lower_middle"] = F(sv[(len(v) - 1) // 2]) if len(v) % 2 == 0 else None
        h["mode_value"] = F(Counter(v).most_common(1)[0][0])
        h["first_value"] = F(v[0])
        h["last_value"] = F(v[-1])
    elif n == "mode_tally":
        v = s["values"]
        if s["ask"] == "mode":
            h["last_value"] = F(v[-1])
            h["first_value"] = F(v[0])
            seen: set[int] = set()
            fr = None
            for x in v:
                if x in seen:
                    fr = x
                    break
                seen.add(x)
            h["first_repeated"] = F(fr) if fr is not None else None
            h["most_common_first_half"] = F(Counter(v[: len(v) // 2]).most_common(1)[0][0])
            h["most_common_second_half"] = F(Counter(v[len(v) // 2:]).most_common(1)[0][0])
        else:
            h["n_minus_2x_first_half_max"] = F(len(v) - 2 * Counter(v[: len(v) // 2]).most_common(1)[0][1])
            h["n_minus_ceil_n_over_distinct"] = F(len(v) - (-(-len(v) // len(set(v)))))
            h["n_minus_count_of_first_value"] = F(len(v) - v.count(v[0]))
            h["n_minus_count_of_last_value"] = F(len(v) - v.count(v[-1]))
    elif n == "pythagoras":
        a, b = s["legs"]
        c = s["hyp"]
        sh = s["shape"]
        if sh in ("ladder_top", "ladder_base"):
            g1, g2 = s["given"]
            h["hyp_minus_given"] = F(g1 - g2)
            h["avg"] = F(round(F(g1 + g2, 2)))
        elif sh in ("walk", "diagonal"):
            h["sum_legs"] = F(a + b)
            h["max_plus_half_min"] = F(round(max(a, b) + F(min(a, b), 2)))
        else:
            h["twice_legs"] = F(2 * (a + b))
            h["legs_plus_max"] = F(a + b + max(a, b))
        h["memorised_4_scaled"] = _opt(_catalogue_guess(sh, s["given"], _PRIM16[:4]))
        h["memorised_16_scaled"] = _opt(_catalogue_guess(sh, s["given"], _PRIM16))
    elif n == "grid_perimeter":
        cells = {(y, x) for y, rr in enumerate(s["rows"]) for a, b in rr for x in range(a, b + 1)}
        nn = len(cells)
        horiz = sum(1 for (y, x) in cells if (y, x + 1) in cells)
        h["four_n"] = F(4 * nn)
        h["horizontal_only"] = F(4 * nn - 2 * horiz)
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        bb = 2 * (max(ys) - min(ys) + 1 + max(xs) - min(xs) + 1)
        h["bbox"] = F(bb)
        h["bbox_plus_4"] = F(bb + 4)
        h["two_n_plus_2"] = F(2 * nn + 2)
        iso = sum(1 for (y, x) in cells if all((y + dy, x + dx) not in cells for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))))
        h["four_times_isolated_squares_(the_second_reading)"] = F(4 * iso)
    elif n == "painted_cube":
        a, b, c = s["dims"]
        f = s["faces"]
        allp = {0: (a - 2) * (b - 2) * (c - 2), 1: 2 * ((a - 2) * (b - 2) + (a - 2) * (c - 2) + (b - 2) * (c - 2)), 2: 4 * ((a - 2) + (b - 2) + (c - 2))}[f]
        h["ignore_bottom_rule"] = F(allp) if s["bottom_unpainted"] else None
        h["inner_block_on_unpainted_bottom"] = F((a - 2) * (b - 2) * (c - 2)) if s["bottom_unpainted"] else None
    elif n == "division_counting":
        if s["shape"] == "pallets":
            nn, k, m = s["items"], s["box"], s["crate"]
            h["full_pallets"] = F(nn // (k * m))
            h["leftover_items"] = F(nn % k)
            h["ceil_boxes_mod_m"] = F(-(-nn // k) % m)
        else:
            nn, k = s["people"], s["seats"]
            h["k_minus_remainder_ignores_exact_fit"] = F(k - nn % k)
            h["remainder"] = F(nn % k)
    elif n == "digit_puzzle":
        from studies.m0.lineages_m1_fix3_c import fit_set

        nd = s["digits"]
        cl = [tuple(c) for c in s["clues"]]

        def fs(cs: list[tuple[Any, ...]]) -> frozenset[int]:
            return frozenset.intersection(*(fit_set(nd, c) for c in cs))

        h["smallest_meeting_clue_1"] = F(min(fs(cl[:1])))
        h["largest_meeting_clue_1"] = F(max(fs(cl[:1])))
        h["smallest_meeting_clues_1_2"] = F(min(fs(cl[:2])))
        h["largest_meeting_clues_1_2"] = F(max(fs(cl[:2])))
        h["smallest_meeting_all_but_last"] = F(min(fs(cl[:-1])))
        h["smallest_meeting_all_but_first"] = F(min(fs(cl[1:])))
    return h


def _opt(v: int | None) -> F | None:
    return None if v is None else F(v)


def stem_of(lid: str) -> str:
    st = lid.split(".", 1)[1].removesuffix("_r3").removesuffix("_r2")
    return "last_digit_power" if st == "power_remainder" else st


def all_lineages(before: bool) -> dict[str, Any]:
    if before:
        from studies.m0.core import lineages_of
        from studies.m0.lineages_m1_rev2 import NOT_REGISTERED, load_rev2

        return {x.id: x for x in [*lineages_of("M1"), *load_rev2()] if x.id not in NOT_REGISTERED}
    from studies.m0.lineages_m1_fix3 import load_all

    return {x.id: x for x in load_all()}


def run(args: tuple[str, int, bool]) -> tuple[str, dict[str, Any]]:
    lid, n_items, before = args
    lin = all_lineages(before)[lid]
    stem = stem_of(lid)
    out: dict[str, Any] = {}
    for lv in ALL_LEVELS:
        rng = stream(SEED, "fix3-shortcuts", lid, str(lv))
        its = [build_item(lin, lv, rng, "A", f"s/{i}") for i in range(n_items)]
        ans = [F(it.answer) for it in its]
        n = len(its)
        a_, b_ = ans[0::2], ans[1::2]
        m_a = Counter(a_).most_common(1)[0][0]
        m_b = Counter(b_).most_common(1)[0][0]
        base = (sum(x == m_a for x in b_) / len(b_) + sum(x == m_b for x in a_) / len(a_)) / 2
        numl = [nums(it.question) for it in its]
        cands = {"first": lambda L: L[0], "second": lambda L: L[1] if len(L) > 1 else None, "last": lambda L: L[-1], "max": max, "min": min,
                 "sum": lambda L: sum(L), "max_minus_min": lambda L: max(L) - min(L), "second_last": lambda L: L[-2] if len(L) > 1 else None}

        def rate_pos(fn: Any, idx: list[int]) -> float:
            return sum(1 for i in idx if numl[i] and fn(numl[i]) == ans[i]) / len(idx)

        ev, od = list(range(0, n, 2)), list(range(1, n, 2))
        best_a = max(cands, key=lambda k: rate_pos(cands[k], ev))
        best_b = max(cands, key=lambda k: rate_pos(cands[k], od))
        echo = (rate_pos(cands[best_a], od) + rate_pos(cands[best_b], ev)) / 2
        rates: dict[str, float] = {f"echo_best_position[{best_a}/{best_b}]": echo}
        sp = [spec(stem, it.structured) for it in its]
        for k in sorted({k for d in sp for k in d}):
            app = [(d[k], a) for d, a in zip(sp, ans, strict=True) if d.get(k) is not None]
            rates[k] = sum(1 for v, a in app if v == a) / n
            if len(app) < n:
                rates[k + "__within_applicable"] = sum(1 for v, a in app if v == a) / max(1, len(app))
        out[str(lv)] = {"N": n, "base": round(base, 4), "mode_insample": round(Counter(ans).most_common(1)[0][1] / n, 4), "answer_echoed_anywhere": round(sum(1 for i in range(n) if ans[i] in numl[i]) / n, 4),
                        "rates": {k: round(v, 4) for k, v in rates.items()}, "minus_base": {k: round(v - base, 4) for k, v in rates.items()},
                        "halfwidth95": {k: round(1.96 * math.sqrt(max(v * (1 - v), 1 / n) / n), 4) for k, v in rates.items()}}
    return lid, out


def flags(res: dict[str, Any], bound: float = 0.10) -> dict[str, Any]:
    """Per lineage: rules with |rate - base| > bound at some level (excluding PROCEDURE rules and the within-applicable duplicates), the base itself, and the within-applicable rules above the bound."""
    out: dict[str, Any] = {}
    for lid, lv in sorted(res.items()):
        stem = stem_of(lid)
        proc = PROCEDURE.get(stem, {})
        over: dict[str, list[float | None]] = {}
        over_within: dict[str, list[float | None]] = {}
        names = sorted({k for L in lv for k in lv[L]["minus_base"]})
        for k in names:
            diffs = [lv[L]["minus_base"].get(k) for L in sorted(lv, key=int)]
            if any(d is not None and abs(d) > bound for d in diffs):
                (over_within if k.endswith("__within_applicable") else over)[k] = diffs
        out[lid] = {"base_per_level": [lv[L]["base"] for L in sorted(lv, key=int)], "mode_insample_per_level": [lv[L]["mode_insample"] for L in sorted(lv, key=int)],
                    "over_bound_excluding_procedure": {k: v for k, v in over.items() if k not in proc}, "over_bound_procedure_rules": {k: v for k, v in over.items() if k in proc},
                    "over_bound_within_applicable": over_within, "max_rule_minus_base_per_level": [max(v for k, v in lv[L]["minus_base"].items() if not k.endswith("__within_applicable") and k not in proc) for L in sorted(lv, key=int)]}
    return out


def main() -> None:
    import multiprocessing as mp

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--before", action="store_true", help="measure the pre-fix set (16 existing + rev2) with the same battery")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    ids = sorted(all_lineages(a.before))
    if a.only:
        ids = [i for i in ids if any(o in i for o in a.only.split(","))]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = dict(pool.map(run, [(i, a.n, a.before) for i in ids], chunksize=1))
    Path(a.out).write_text(json.dumps({"n": a.n, "seed": SEED, "results": res, "flags": flags(res)}, indent=1, sort_keys=True))
    for lid, f in flags(res).items():
        print(lid, "base", f["base_per_level"], "max_rule-base", f["max_rule_minus_base_per_level"], "OVER:", sorted(f["over_bound_excluding_procedure"]), "within:", sorted(f["over_bound_within_applicable"]), flush=True)
    print("seconds", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
