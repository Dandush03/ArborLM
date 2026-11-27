# ruff: noqa
"""Shortcut measurement for the M1 batch-1 lineages and their revision 2 (fix round), no model involved.

ATTRIBUTION. The heuristic definitions in the block between the two ``BEGIN COPY`` markers are COPIED VERBATIM from the independent auditor's script
``docs/reviews/m0-lineage-decision-2026-11-25/audit_m1/shortcuts_audit.py`` (arbor-auditor, Claude Opus 5.5; the generic six 'A:' heuristics are my own batch-1 ones that the auditor
re-implemented, the 'O:' ones are the auditor's own) and the PARTIAL / LIN_PARTIAL tagging from ``shortcuts_summarise_v2.py`` (same author). They are included so that the
author's battery and the auditor's battery are one battery (lead ruling R-3). The additions below the copy (heuristics for the rev2 shapes; the driver) are mine.

Per lineage and level: the absolute exact-match rate of every heuristic, beside the most-frequent-answer (constant) rate of the same items and its held-out version (mode of the first
half scored on the second half). All answers are open numbers: there is no 1/k and no closed-answer shape, so a two-sided reading (real rate against a counterfactual generator without a
redraw) is NOT APPLICABLE to the rev2 shapes: they contain no redraw to compare against (R-1). Heuristics read the structured form (only what is printed in the item) and the question.
Screening reading used for display only (not a registered threshold): rate >= max(0.25, 2 x constant rate).

Run: PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_shortcut_check_rev2 --set rev2|batch1 [--per-level 2000] [--out PATH]
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction
from itertools import product as iproduct
from pathlib import Path

from studies.m0.core import ALL_LEVELS, build_item, stream

SEED = 777103

# ======================================================= BEGIN COPY (auditor's shortcuts_audit.py, verbatim)
def nums(q):
    return [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"\d-digit", "", q))]


def cdiv(a, b):
    return -(-a // b)


def comb(n, k):
    return math.comb(n, k) if 0 <= k <= n else 0


# --------------------------------------------------------------- generic (author's six + auditor's four)
GEN_AUTHOR = {
    "A:first_number": lambda ns: ns[0] if ns else None,
    "A:last_number": lambda ns: ns[-1] if ns else None,
    "A:sum_numbers": lambda ns: sum(ns),
    "A:product_numbers": lambda ns: math.prod(ns) if len(ns) < 12 else None,
    "A:largest_number": lambda ns: max(ns) if ns else None,
    "A:smallest_number": lambda ns: min(ns) if ns else None,
}
GEN_OWN = {
    "O:second_number": lambda ns: ns[1] if len(ns) > 1 else None,
    "O:median_of_numbers": lambda ns: sorted(ns)[len(ns) // 2] if ns else None,
    "O:most_common_number": lambda ns: Counter(ns).most_common(1)[0][0] if ns else None,
    "O:abs_diff_first_two": lambda ns: abs(ns[0] - ns[1]) if len(ns) > 1 else None,
}


def ie_parts(s):
    return s["total"], s["sizes"], s["pairs"], s["triple"] or 0, s["ask"]


def cube_all(s):
    a, b, c = s["dims"]
    return {0: (a - 2) * (b - 2) * (c - 2), 1: 2 * ((a - 2) * (b - 2) + (a - 2) * (c - 2) + (b - 2) * (c - 2)), 2: 4 * ((a - 2) + (b - 2) + (c - 2))}[s["faces"]]


def slot_count(s, lead, par):
    d, L, rep = s["digits"], s["length"], s["repeat"]
    from itertools import permutations, product
    c = 0
    for t in (product(d, repeat=L) if rep else permutations(d, L)):
        if lead and t[0] == 0:
            continue
        if par == "even" and t[-1] % 2:
            continue
        if par == "odd" and not t[-1] % 2:
            continue
        c += 1
    return c


def ways(coins, t):
    w = [1] + [0] * t
    for v in coins:
        for a in range(v, t + 1):
            w[a] += w[a - v]
    return w[t]


def rec_terms(s, n):
    sh = s["shape"]
    if sh == "sum_prev_two":
        t = list(s["first"])
        while len(t) < n:
            t.append(t[-1] + t[-2])
        return t[n - 1] if n >= 1 else None
    if sh == "affine":
        t = [s["first"][0]]
        while len(t) < n:
            t.append(s["mult"] * t[-1] + s["add"])
        return t[n - 1]
    return s["first"][0] + sum(range(2, n + 1))


def poly_next_by_diffs(terms, steps, depth):
    rows = [list(terms)]
    for _ in range(depth):
        rows.append([b - a for a, b in zip(rows[-1], rows[-1][1:])])
    for _ in range(steps):
        rows[-1].append(rows[-1][-1])
        for i in range(len(rows) - 2, -1, -1):
            rows[i].append(rows[i][-1] + rows[i + 1][-1])
    return rows[0][-1]


def tier_bill(tiers, last, u, marginal=True):
    if not marginal:
        cap = 0
        for size, rate in tiers:
            cap += size
            if u <= cap:
                return u * rate
        return u * last
    left, tot = u, 0
    for size, rate in tiers:
        take = min(left, size); tot += take * rate; left -= take
    return tot + left * last


def mc_exact(need, single, packs):
    INF = 10**9
    c = [0] + [INF] * need
    for i in range(1, need + 1):
        c[i] = min([c[i - 1] + single] + [c[i - p] + q for p, q in packs if i >= p])
    return c[need]


def mc_greedy(need, single, packs):
    left, cost = need, 0
    for p, q in sorted(packs, reverse=True):
        k = left // p; cost += k * q; left -= k * p
    return cost + left * single


SPEC = {
    "M1.inclusion_exclusion": {
        "A:ignore_overlaps": lambda s, q: (s["total"] - sum(s["sizes"])) if s["ask"] == "none" else sum(s["sizes"]),
        "A:pairs_only_no_triple": lambda s, q: None if s["triple"] is None else (s["total"] - (sum(s["sizes"]) - sum(s["pairs"])) if s["ask"] == "none" else sum(s["sizes"]) - sum(s["pairs"])),
        "A:total_minus_biggest": lambda s, q: s["total"] - max(s["sizes"]),
        "O:none_any_swapped": lambda s, q: (lambda T, sz, pr, tr, ask: (sum(sz) - sum(pr) + tr) if ask == "none" else T - (sum(sz) - sum(pr) + tr))(*ie_parts(s)),
        "O:triple_sign_error": lambda s, q: (lambda T, sz, pr, tr, ask: (T - (sum(sz) - sum(pr) - tr)) if ask == "none" else (sum(sz) - sum(pr) - tr))(*ie_parts(s)),
        "O:total_minus_pairs": lambda s, q: s["total"] - sum(s["pairs"]),
        "O:sizes_minus_total": lambda s, q: abs(sum(s["sizes"]) - s["total"]),
        "O:max_minus_min_size": lambda s, q: max(s["sizes"]) - min(s["sizes"]),
        "O:any_formula_whatever_ask": lambda s, q: sum(s["sizes"]) - sum(s["pairs"]) + (s["triple"] or 0),
    },
    "M1.binomial_choose": {
        "A:plain_ignoring_condition": lambda s, q: None if s["shape"] == "plain" else comb(s["n"], s["k"]) if s["shape"] == "include" else comb(s["x"] + s["y"], s["k"]),
        "A:n_times_k": lambda s, q: (s["n"] or s["x"] + s["y"]) * s["k"],
        "A:ordered_count": lambda s, q: math.perm(s["n"] or s["x"] + s["y"], s["k"]),
        "A:two_groups_sum": lambda s, q: comb(s["x"], s["j"]) + comb(s["y"], s["k"] - s["j"]) if s["shape"] == "two_groups" else None,
        "O:C(n,k-1)": lambda s, q: comb(s["n"] or s["x"] + s["y"], s["k"] - 1),
        "O:C(n-1,k)": lambda s, q: comb((s["n"] or s["x"] + s["y"]) - 1, s["k"]),
        "O:C(n,2)": lambda s, q: comb(s["n"] or s["x"] + s["y"], 2),
        "O:C(x,j)*y": lambda s, q: comb(s["x"], s["j"]) * s["y"] if s["shape"] == "two_groups" else None,
        "O:C(n-1,k-1)_always": lambda s, q: comb((s["n"] or s["x"] + s["y"]) - 1, s["k"] - 1),
    },
    "M1.slot_permutations": {
        "A:unconstrained": lambda s, q: len(s["digits"]) ** s["length"] if s["repeat"] else math.perm(len(s["digits"]), s["length"]),
        "A:unconstrained_half_parity": lambda s, q: (len(s["digits"]) ** s["length"] if s["repeat"] else math.perm(len(s["digits"]), s["length"])) // (2 if s["parity"] != "any" else 1),
        "O:ignore_parity": lambda s, q: slot_count(s, s["lead_nonzero"], "any"),
        "O:ignore_leading_zero_rule": lambda s, q: slot_count(s, False, s["parity"]),
        "O:repeat_rule_flipped": lambda s, q: slot_count(dict(s, repeat=not s["repeat"]), s["lead_nonzero"], s["parity"]),
        "O:always_no_leading_zero": lambda s, q: slot_count(s, True, s["parity"]),
        "O:parity_flipped": lambda s, q: slot_count(s, s["lead_nonzero"], {"even": "odd", "odd": "even", "any": "any"}[s["parity"]]),
    },
    "M1.change_ways": {
        "A:target_div_biggest_plus1": lambda s, q: s["target"] // max(s["coins"]) + 1,
        "A:target_div_smallest": lambda s, q: s["target"] // min(s["coins"]),
        "A:target_div_sum": lambda s, q: s["target"] // sum(s["coins"]),
        "O:two_smallest_coins_only": lambda s, q: ways(sorted(s["coins"])[:2], s["target"]),
        "O:two_largest_coins_only": lambda s, q: ways(sorted(s["coins"])[1:], s["target"]),
        "O:smallest_and_largest_only": lambda s, q: ways([min(s["coins"]), max(s["coins"])], s["target"]),
        "O:target_div_middle_plus1": lambda s, q: s["target"] // sorted(s["coins"])[1] + 1,
        "O:sum_of_quotients": lambda s, q: sum(s["target"] // c for c in s["coins"]),
    },
    "M1.pigeonhole_worst_case": {
        "A:total_plus_one": lambda s, q: sum(s["counts"]) + 1,
        "A:(k-1)c+1": lambda s, q: (s["k"] - 1) * len(s["counts"]) + 1,
        "A:capped_sum_no_plus1": lambda s, q: sum(min(n, s["k"] - 1) for n in s["counts"]) if s["goal"] == "same" else sum(s["counts"]) - min(s["counts"]),
        "A:total_minus_min": lambda s, q: sum(s["counts"]) - min(s["counts"]),
        "O:k_times_c": lambda s, q: s["k"] * len(s["counts"]),
        "O:total_minus_max_plus1": lambda s, q: sum(s["counts"]) - max(s["counts"]) + 1,
        "O:cap_at_k_plus1": lambda s, q: sum(min(n, s["k"]) for n in s["counts"]) + 1,
        "O:max_count_plus1": lambda s, q: max(s["counts"]) + 1,
        "O:k_plus_c_minus1": lambda s, q: s["k"] + len(s["counts"]) - 1,
    },
    "M1.gcd_lcm": {
        "A:min_value": lambda s, q: min(s["values"]),
        "A:abs_diff_first_two": lambda s, q: abs(s["values"][0] - s["values"][1]),
        "A:product": lambda s, q: math.prod(s["values"]),
        "A:max_value": lambda s, q: max(s["values"]),
        "A:op_of_first_two_only": lambda s, q: (math.gcd if s["ask"] == "gcd" else math.lcm)(*s["values"][:2]) if len(s["values"]) > 2 else None,
        "O:other_operation": lambda s, q: (math.lcm if s["ask"] == "gcd" else math.gcd)(*s["values"]),
        "O:product_over_gcd_all": lambda s, q: math.prod(s["values"]) // math.gcd(*s["values"]),
        "O:smallest_pairwise_diff": lambda s, q: min(abs(a - b) for i, a in enumerate(s["values"]) for b in s["values"][:i]),
        "O:sum_values": lambda s, q: sum(s["values"]),
        "O:second_smallest": lambda s, q: sorted(s["values"])[1],
        "O:gcd_of_last_two_or_lcm": lambda s, q: (math.gcd if s["ask"] == "gcd" else math.lcm)(*s["values"][-2:]) if len(s["values"]) > 2 else None,
    },
    "M1.crt_congruence": {
        "A:first_rem_plus_mod": lambda s, q: s["conditions"][0][0] + s["conditions"][0][1],
        "A:product_moduli": lambda s, q: math.prod(m for m, _ in s["conditions"]),
        "A:sum_remainders": lambda s, q: sum(r for _, r in s["conditions"]),
        "A:first_two_only": lambda s, q: next(n for n in range(1, 10**6) if all(n % m == r for m, r in s["conditions"][:2])) if len(s["conditions"]) > 2 else None,
        "O:product_minus_one": lambda s, q: math.prod(m for m, _ in s["conditions"]) - 1,
        "O:constant_deficit_trick": lambda s, q: (math.prod(m for m, _ in s["conditions"]) - (s["conditions"][0][0] - s["conditions"][0][1])) if len({m - r for m, r in s["conditions"]}) == 1 else None,
        "O:constant_remainder_trick": lambda s, q: (math.prod(m for m, _ in s["conditions"]) + s["conditions"][0][1]) if len({r for _, r in s["conditions"]}) == 1 else None,
        "O:sum_moduli": lambda s, q: sum(m for m, _ in s["conditions"]),
        "O:last_mod_plus_rem": lambda s, q: s["conditions"][-1][0] + s["conditions"][-1][1],
        "O:largest_mod_plus_its_rem": lambda s, q: (lambda c: c[0] + c[1])(max(s["conditions"])),
    },
    "M1.prime_factors": {
        "A:n_itself": lambda s, q: s["n"],
        "A:n_halved": lambda s, q: s["n"] // 2,
        "A:smallest_prime_factor": lambda s, q: next(p for p in range(2, s["n"] + 1) if s["n"] % p == 0),
        "A:digit_count": lambda s, q: len(str(s["n"])),
        "A:count_small_prime_divisors": lambda s, q: sum(1 for p in range(2, 40) if s["n"] % p == 0),
        "O:two_pow_distinct": lambda s, q: 2 ** len(_pf(s["n"])) if s["ask"] == "divisors" else None,
        "O:omega_plus_one": lambda s, q: sum(_pf(s["n"]).values()) + 1 if s["ask"] == "divisors" else None,
        "O:sum_with_multiplicity": lambda s, q: sum(p * e for p, e in _pf(s["n"]).items()),
        "O:distinct_count": lambda s, q: len(_pf(s["n"])),
        "O:digit_sum": lambda s, q: sum(map(int, str(s["n"]))),
        "O:largest_prime_le_29_dividing": lambda s, q: max(p for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29) if s["n"] % p == 0) if any(s["n"] % p == 0 for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)) else None,
    },
    "M1.last_digit_power": {
        "A:base_last_digit": lambda s, q: s["terms"][0][0] % 10,
        "A:combined_base_last_digits": lambda s, q: (sum(b % 10 for b, _ in s["terms"]) if s["op"] == "sum" else math.prod(b % 10 for b, _ in s["terms"])) % 10,
        "A:exponent_last_digit": lambda s, q: s["terms"][0][1] % 10,
        "A:base_times_exp_last_digit": lambda s, q: (s["terms"][0][0] * s["terms"][0][1]) % 10,
        "O:e_mod4_zero_bug": lambda s, q: _comb_ld(s, lambda b, e: pow(b % 10, e % 4, 10)),
        "O:digit_pow_exp_last_digit": lambda s, q: _comb_ld(s, lambda b, e: pow(b % 10, e % 10, 10)),
        "O:power_e_plus_1": lambda s, q: _comb_ld(s, lambda b, e: pow(b, e + 1, 10)),
        "O:power_e_minus_1": lambda s, q: _comb_ld(s, lambda b, e: pow(b, e - 1, 10)),
        "O:parity_guess_even6_odd1": lambda s, q: _comb_ld(s, lambda b, e: 6 if b % 2 == 0 else 1),
        "O:square_last_digit": lambda s, q: _comb_ld(s, lambda b, e: pow(b, 2, 10)),
    },
    "M1.quadratic_area": {
        "A:isqrt_area_or_half_total": lambda s, q: math.isqrt(s["area"] or s["total"] // 2) if s["shape"] != "rect_perimeter" else s["perimeter"] // 4,
        "A:area_div_d": lambda s, q: s["area"] // s["d"] if s["d"] and s["area"] else None,
        "A:perimeter_quarter_plus1": lambda s, q: s["perimeter"] // 4 + 1 if s["shape"] == "rect_perimeter" else None,
        "A:round_sqrt_minus_half_d": lambda s, q: round(math.sqrt(s["area"]) - s["d"] / 2) if s["area"] and s["d"] else None,
        "O:isqrt_minus_d": lambda s, q: math.isqrt(s["area"] or s["total"]) - s["d"] if s["d"] else None,
        "O:d_itself": lambda s, q: s["d"] or None,
        "O:larger_root_instead": lambda s, q: (lambda x: x + s["d"])(_qroot(s)) if s["shape"] != "rect_perimeter" else _qroot(s) - 0,
        "O:half_perimeter_minus_isqrt_area": lambda s, q: s["perimeter"] // 2 - math.isqrt(s["area"]) if s["shape"] == "rect_perimeter" else None,
        "O:round_sqrt_half_total_minus_half_d": lambda s, q: round(math.sqrt(s["total"] / 2) - s["d"] / 2) if s["shape"] == "squares" else None,
        "O:isqrt_area_plus_one": lambda s, q: math.isqrt(s["area"] or s["total"]) + 1,
    },
    "M1.digit_puzzle": {
        "A:smallest_fit_first_clue": lambda s, q: _fit(s, [0], False),
        "A:largest_fit_first_clue": lambda s, q: _fit(s, [0], True),
        "A:smallest_fit_second_clue": lambda s, q: _fit(s, [1], False),
        "O:smallest_fit_first_two": lambda s, q: _fit(s, [0, 1], False) if len(s["clues"]) > 2 else None,
        "O:largest_fit_first_two": lambda s, q: _fit(s, [0, 1], True) if len(s["clues"]) > 2 else None,
        "O:smallest_fit_last_clue": lambda s, q: _fit(s, [len(s["clues"]) - 1], False),
        "O:largest_fit_last_clue": lambda s, q: _fit(s, [len(s["clues"]) - 1], True),
        "O:smallest_fit_all_but_last": lambda s, q: _fit(s, list(range(len(s["clues"]) - 1)), False),
        "O:median_fit_first_clue": lambda s, q: _fit_med(s, [0]),
    },
    "M1.pythagoras": {
        "A:sum_given": lambda s, q: sum(s["given"]),
        "A:abs_diff_given": lambda s, q: abs(s["given"][0] - s["given"][1]),
        "A:max_given": lambda s, q: max(s["given"]),
        "A:sum_for_hyp_diff_for_leg": lambda s, q: sum(s["given"]) if s["shape"] in ("walk", "diagonal") else abs(s["given"][0] - s["given"][1]),
        "O:max_plus_half_min": lambda s, q: max(s["given"]) + min(s["given"]) // 2,
        "O:perimeter_without_hyp_doubled": lambda s, q: 2 * sum(s["given"]),
        "O:perimeter_a_b_max": lambda s, q: sum(s["given"]) + max(s["given"]),
        "O:hyp_always": lambda s, q: math.isqrt(s["given"][0] ** 2 + s["given"][1] ** 2),
        "O:leg_always": lambda s, q: math.isqrt(abs(s["given"][0] ** 2 - s["given"][1] ** 2)),
    },
    "M1.grid_perimeter": {
        "A:four_times_cells": lambda s, q: 4 * _cells(s),
        "A:sum_row_perimeters": lambda s, q: sum(2 * (b - a + 1) + 2 for a, b in s["rows"]),
        "A:2widest_plus_2rows": lambda s, q: 2 * max(b - a + 1 for a, b in s["rows"]) + 2 * len(s["rows"]),
        "A:bounding_box": lambda s, q: 2 * ((max(b for _, b in s["rows"]) - min(a for a, _ in s["rows"]) + 1) + len(s["rows"])),
        "O:2cells_plus_2": lambda s, q: 2 * _cells(s) + 2,
        "O:row_perims_minus_2(rows-1)": lambda s, q: sum(2 * (b - a + 1) + 2 for a, b in s["rows"]) - 2 * (len(s["rows"]) - 1),
        "O:bbox_plus_2rows": lambda s, q: 2 * ((max(b for _, b in s["rows"]) - min(a for a, _ in s["rows"]) + 1) + len(s["rows"])) + 2 * len(s["rows"]),
        "O:bbox_plus_4": lambda s, q: 2 * ((max(b for _, b in s["rows"]) - min(a for a, _ in s["rows"]) + 1) + len(s["rows"])) + 4,
        "O:2sum_widths_plus_2rows": lambda s, q: 2 * _cells(s) + 2 * len(s["rows"]),
        "O:top_plus_bottom_plus_2rows_plus_steps": lambda s, q: (s["rows"][0][1] - s["rows"][0][0] + 1) + (s["rows"][-1][1] - s["rows"][-1][0] + 1) + 2 * len(s["rows"]) + sum(abs(a1 - a0) + abs(b1 - b0) for (a0, b0), (a1, b1) in zip(s["rows"], s["rows"][1:])),
    },
    "M1.painted_cube": {
        "A:all_faces_formula_when_bottom_unpainted": lambda s, q: cube_all(s) if s["bottom_unpainted"] else None,
        "A:product_dims": lambda s, q: math.prod(s["dims"]),
        "A:inner_block": lambda s, q: math.prod(d - 2 for d in s["dims"]),
        "O:all_faces_formula_always": lambda s, q: cube_all(s),
        "O:surface_squares": lambda s, q: 2 * (s["dims"][0] * s["dims"][1] + s["dims"][1] * s["dims"][2] + s["dims"][0] * s["dims"][2]),
        "O:edge_cubes_4(a+b+c)": lambda s, q: 4 * sum(s["dims"]),
        "O:twelve_or_eight": lambda s, q: {0: 8, 1: 12, 2: 12}[s["faces"]],
        "O:product_minus_inner": lambda s, q: math.prod(s["dims"]) - math.prod(d - 2 for d in s["dims"]),
        "O:inner_with_c_minus_1": lambda s, q: (s["dims"][0] - 2) * (s["dims"][1] - 2) * (s["dims"][2] - 1),
    },
    "M1.min_cost_packs": {
        "A:singles_only": lambda s, q: s["need"] * s["single"],
        "A:biggest_floor_then_singles": lambda s, q: (lambda p: (s["need"] // p[0]) * p[1] + (s["need"] % p[0]) * s["single"])(max(s["packs"])),
        "A:biggest_ceil": lambda s, q: (lambda p: cdiv(s["need"], p[0]) * p[1])(max(s["packs"])),
        "A:best_pack_ceil_min": lambda s, q: min(cdiv(s["need"], p) * c for p, c in s["packs"]),
        "A:best_unit_floor_then_singles": lambda s, q: (lambda b: (s["need"] // b[0]) * b[1] + (s["need"] % b[0]) * s["single"])(min(s["packs"], key=lambda pq: Fraction(pq[1], pq[0]))),
        "O:min_over_packs_floor_then_singles": lambda s, q: min((s["need"] // p) * c + (s["need"] % p) * s["single"] for p, c in s["packs"]),
        "O:greedy_largest_first_then_singles": lambda s, q: mc_greedy(s["need"], s["single"], s["packs"]),
        "O:exactly_need_dp": lambda s, q: mc_exact(s["need"], s["single"], s["packs"]),
        "O:fractional_best_unit_rounded_up": lambda s, q: math.ceil(min([Fraction(s["single"])] + [Fraction(c, p) for p, c in s["packs"]]) * s["need"]),
        "O:min_of_all_five_naive": lambda s, q: min(_naive5(s)),
        "O:best_unit_ceil_or_floor_better": lambda s, q: min(_naive5(s)[3:]),
    },
    "M1.tiered_pricing": {
        "A:units_times_first_rate": lambda s, q: Fraction(s["used"] * s["tiers"][0][1], 100) if s["used"] is not None else Fraction(s["bill_cents"], s["tiers"][0][1]),
        "A:units_times_last_rate": lambda s, q: Fraction(s["used"] * s["last_rate"], 100) if s["used"] is not None else Fraction(s["bill_cents"], s["last_rate"]),
        "A:units_times_mean_rate": lambda s, q: Fraction(s["used"] * (sum(c for _, c in s["tiers"]) + s["last_rate"]), 100 * (len(s["tiers"]) + 1)) if s["used"] is not None else None,
        "O:non_marginal_whole_bill_at_top_rate": lambda s, q: Fraction(tier_bill(s["tiers"], s["last_rate"], s["used"], False), 100) if s["used"] is not None else None,
        "O:skip_middle_tiers": lambda s, q: Fraction(s["tiers"][0][0] * s["tiers"][0][1] + (s["used"] - s["tiers"][0][0]) * s["last_rate"], 100) if s["used"] is not None else None,
        "O:answer_in_cents": lambda s, q: tier_bill(s["tiers"], s["last_rate"], s["used"]) if s["used"] is not None else s["bill_cents"],
        "O:units_from_bill_mean_rate": lambda s, q: round(Fraction(s["bill_cents"] * (len(s["tiers"]) + 1), sum(c for _, c in s["tiers"]) + s["last_rate"])) if s["used"] is None else None,
        "O:units_cap_plus_rest_at_last_rate_floor": lambda s, q: (sum(u for u, _ in s["tiers"]) + (s["bill_cents"] - sum(u * c for u, c in s["tiers"])) // s["last_rate"]) if s["used"] is None else None,
        "O:off_by_one_tier_boundary": lambda s, q: Fraction(tier_bill(s["tiers"], s["last_rate"], s["used"] - 1), 100) if s["used"] is not None else None,
    },
    "M1.recurrence_iterate": {
        "A:sum_stated_firsts": lambda s, q: sum(s["first"]),
        "A:position_times_first": lambda s, q: s["position"] * s["first"][0],
        "A:first_times_mult_pow": lambda s, q: s["first"][0] * (s["mult"] or 2) ** (s["position"] - 1),
        "O:term_n_minus_1": lambda s, q: rec_terms(s, s["position"] - 1),
        "O:term_n_plus_1": lambda s, q: rec_terms(s, s["position"] + 1),
        "O:affine_drop_add_power": lambda s, q: s["first"][0] * s["mult"] ** (s["position"] - 1) + s["add"] * (s["position"] - 1) if s["shape"] == "affine" else None,
        "O:add_index_includes_1": lambda s, q: s["first"][0] + s["position"] * (s["position"] + 1) // 2 if s["shape"] == "add_index" else None,
        "O:add_index_triangular_only": lambda s, q: s["position"] * (s["position"] + 1) // 2 if s["shape"] == "add_index" else None,
        "O:fib_ratio_golden": lambda s, q: round(s["first"][-1] * 1.618 ** (s["position"] - len(s["first"]))) if s["shape"] == "sum_prev_two" else None,
    },
    "M1.finite_differences": {
        "A:linear_extrapolation": lambda s, q: s["terms"][-1] + (s["terms"][-1] - s["terms"][-2]) * (s["ask"] - len(s["terms"])),
        "A:ratio_extrapolation": lambda s, q: round(s["terms"][-1] * s["terms"][-1] / s["terms"][-2]) if s["ask"] == len(s["terms"]) + 1 and s["terms"][-2] else None,
        "A:last_plus_first_diff": lambda s, q: s["terms"][-1] + (s["terms"][1] - s["terms"][0]) * (s["ask"] - len(s["terms"])),
        "O:one_step_even_if_two_asked": lambda s, q: poly_next_by_diffs(s["terms"], 1, s["degree"]),
        "O:quadratic_diffs_for_any_degree": lambda s, q: poly_next_by_diffs(s["terms"], s["ask"] - len(s["terms"]), 2),
        "O:twice_last": lambda s, q: 2 * s["terms"][-1],
        "O:last_plus_first": lambda s, q: s["terms"][-1] + s["terms"][0],
        "O:diffs_depth_minus_1": lambda s, q: poly_next_by_diffs(s["terms"], s["ask"] - len(s["terms"]), s["degree"] - 1),
        "O:extra_step": lambda s, q: poly_next_by_diffs(s["terms"], s["ask"] - len(s["terms"]) + 1, s["degree"]),
    },
    "M1.median_list": {
        "A:mean": lambda s, q: Fraction(sum(s["values"]), len(s["values"])) if s["shape"] == "list" else Fraction(sum(v * c for v, c in s["values"]), sum(c for _, c in s["values"])),
        "A:middle_of_printed_order": lambda s, q: s["values"][len(s["values"]) // 2] if s["shape"] == "list" else s["values"][len(s["values"]) // 2][0],
        "A:median_ignoring_multiplicities": lambda s, q: None if s["shape"] == "list" else sorted(v for v, _ in s["values"])[(len(s["values"]) - 1) // 2],
        "A:first_value": lambda s, q: s["values"][0] if s["shape"] == "list" else s["values"][0][0],
        "O:lower_middle_no_average": lambda s, q: _expand(s)[(len(_expand(s)) - 1) // 2],
        "O:upper_middle_no_average": lambda s, q: _expand(s)[len(_expand(s)) // 2],
        "O:mid_range": lambda s, q: Fraction(min(_expand(s)) + max(_expand(s)), 2),
        "O:median_of_distinct_values": lambda s, q: (lambda u: Fraction(u[(len(u) - 1) // 2] + u[len(u) // 2], 2))(sorted(set(_expand(s)))),
        "O:table_value_with_most_count": lambda s, q: max(s["values"], key=lambda vc: vc[1])[0] if s["shape"] == "table" else None,
        "O:mode_of_values": lambda s, q: Counter(_expand(s)).most_common(1)[0][0],
    },
    "M1.mode_tally": {
        "A:first_repeated_value": lambda s, q: _first_rep(s["values"]) if s["ask"] == "mode" else None,
        "A:median_value": lambda s, q: sorted(s["values"])[len(s["values"]) // 2] if s["ask"] == "mode" else None,
        "A:count_of_first_repeated": lambda s, q: s["values"].count(_first_rep(s["values"])) if s["ask"] == "mode_count" else None,
        "A:n_over_distinct": lambda s, q: round(len(s["values"]) / len(set(s["values"]))) if s["ask"] == "mode_count" else None,
        "O:last_repeated_value": lambda s, q: _last_rep(s["values"]) if s["ask"] == "mode" else None,
        "O:mode_of_first_half": lambda s, q: Counter(s["values"][: len(s["values"]) // 2]).most_common(1)[0][0] if s["ask"] == "mode" else Counter(s["values"][: len(s["values"]) // 2]).most_common(1)[0][1],
        "O:mode_of_second_half": lambda s, q: Counter(s["values"][len(s["values"]) // 2:]).most_common(1)[0][0] if s["ask"] == "mode" else None,
        "O:count_of_first_value": lambda s, q: s["values"].count(s["values"][0]) if s["ask"] == "mode_count" else None,
        "O:ceil_n_over_distinct_plus1": lambda s, q: cdiv(len(s["values"]), len(set(s["values"]))) + 1 if s["ask"] == "mode_count" else None,
        "O:count_of_last_value": lambda s, q: s["values"].count(s["values"][-1]) if s["ask"] == "mode_count" else s["values"][-1],
        "O:true_mode_count_minus_1": lambda s, q: Counter(s["values"]).most_common(1)[0][1] - 1 if s["ask"] == "mode_count" else None,
    },
    "M1.division_counting": {
        "A:rounded_quotient": lambda s, q: round(s["items"] / (s["box"] * s["crate"])) if s["shape"] == "crates" else round((s["high"] - s["low"]) / s["div"]) if s["shape"] == "multiples" else s["people"] % s["seats"],
        "A:floor_quotient": lambda s, q: s["items"] // (s["box"] * s["crate"]) if s["shape"] == "crates" else (s["high"] - s["low"]) // s["div"] if s["shape"] == "multiples" else s["people"] // s["seats"],
        "A:remainder_not_complement": lambda s, q: s["people"] % s["seats"] if s["shape"] == "empty_seats" else None,
        "A:single_ceil_boxes": lambda s, q: cdiv(s["items"], s["box"]) if s["shape"] == "crates" else None,
        "O:ceil_of_product": lambda s, q: cdiv(s["items"], s["box"] * s["crate"]) if s["shape"] == "crates" else None,
        "O:floor_boxes_then_ceil": lambda s, q: cdiv(s["items"] // s["box"], s["crate"]) if s["shape"] == "crates" else None,
        "O:floor_b_minus_floor_a": lambda s, q: s["high"] // s["div"] - s["low"] // s["div"] if s["shape"] == "multiples" else None,
        "O:range_over_d_plus1": lambda s, q: (s["high"] - s["low"]) // s["div"] + 1 if s["shape"] == "multiples" else None,
        "O:ceil_range_over_d": lambda s, q: cdiv(s["high"] - s["low"], s["div"]) if s["shape"] == "multiples" else None,
        "O:empty_seats_one_bus_extra": lambda s, q: (cdiv(s["people"], s["seats"]) + 1) * s["seats"] - s["people"] if s["shape"] == "empty_seats" else None,
        "O:buses_count_instead": lambda s, q: cdiv(s["people"], s["seats"]) if s["shape"] == "empty_seats" else None,
    },
}


def _pf(n):
    out, p = {}, 2
    while n > 1:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1; n //= p
        p += 1
    return out


def _comb_ld(s, f):
    vals = [f(b, e) for b, e in s["terms"]]
    return (sum(vals) if s["op"] == "sum" else math.prod(vals)) % 10


def _qroot(s):
    sh = s["shape"]
    if sh == "rect_perimeter":
        h = s["perimeter"] // 2
        return min(w for w in range(1, h) if w * (h - w) == s["area"])  # the SHORTER side (wrong for this shape)
    if sh == "squares":
        return next(x for x in range(1, 10**4) if x * x + (x + s["d"]) ** 2 == s["total"])
    return next(x for x in range(1, 10**5) if x * (x + s["d"]) == s["area"])


def _holds(n, c):
    from studies.m0.lineages_m1_algebra import _holds as h  # the item's own clue semantics, only to define "fits"
    return h(n, c)


def _fit(s, idx, largest):
    rng = range(10, 100) if s["digits"] == 2 else range(100, 1000)
    xs = [n for n in rng if all(_holds(n, s["clues"][i]) for i in idx)]
    if not xs:
        return None
    return xs[-1] if largest else xs[0]


def _fit_med(s, idx):
    rng = range(10, 100) if s["digits"] == 2 else range(100, 1000)
    xs = [n for n in rng if all(_holds(n, s["clues"][i]) for i in idx)]
    return xs[len(xs) // 2] if xs else None


def _345(s):
    g = s["given"]
    for (a, b, c) in ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)):
        pass
    return None


def _cells(s):
    return sum(b - a + 1 for a, b in s["rows"])


def _naive5(s):
    need, single, packs = s["need"], s["single"], s["packs"]
    big = max(packs, key=lambda p: p[0])
    unit = min(packs, key=lambda pq: Fraction(pq[1], pq[0]))
    return [need * single, (need // big[0]) * big[1] + (need % big[0]) * single, cdiv(need, big[0]) * big[1], (need // unit[0]) * unit[1] + (need % unit[0]) * single, cdiv(need, unit[0]) * unit[1]]


def _expand(s):
    if s["shape"] == "list":
        return sorted(s["values"])
    return sorted(v for v, c in s["values"] for _ in range(c))


def _first_rep(vals):
    return next(v for i, v in enumerate(vals) if v in vals[:i])


def _last_rep(vals):
    seen = set(); last = None
    for v in vals:
        if v in seen:
            last = v
        seen.add(v)
    return last


def eq(h, ans):
    try:
        return h is not None and Fraction(h) == Fraction(ans)
    except (TypeError, ValueError):
        return False



# ======================================================= END COPY

# ======================================================= BEGIN COPY (auditor's shortcuts_summarise_v2.py PARTIAL tagging, verbatim)
PARTIAL = {
    "spec:O:quadratic_diffs_for_any_degree", "spec:O:one_step_even_if_two_asked", "spec:O:extra_step",
    "spec:O:top_plus_bottom_plus_2rows_plus_steps",
    "spec:O:triple_sign_error", "spec:O:any_formula_whatever_ask", "spec:O:none_any_swapped",
    "spec:O:e_mod4_zero_bug", "spec:O:power_e_plus_1", "spec:O:power_e_minus_1",
    "spec:O:exactly_need_dp", "spec:O:min_of_all_five_naive", "spec:O:best_unit_ceil_or_floor_better",
    "spec:O:lower_middle_no_average", "spec:O:upper_middle_no_average",
    "O:most_common_number",  # for mode_tally this IS the procedure for ask=mode
    "spec:O:mode_of_first_half", "spec:O:mode_of_second_half", "spec:O:true_mode_count_minus_1",
    "spec:O:all_faces_formula_always", "spec:O:inner_with_c_minus_1",
    "spec:O:hyp_always", "spec:O:leg_always",
    "spec:O:C(n-1,k-1)_always", "spec:A:plain_ignoring_condition",
    "spec:O:always_no_leading_zero", "spec:O:ignore_parity", "spec:O:ignore_leading_zero_rule", "spec:O:repeat_rule_flipped", "spec:O:parity_flipped", "spec:A:unconstrained", "spec:A:unconstrained_half_parity",
    "spec:O:skip_middle_tiers", "spec:O:off_by_one_tier_boundary", "spec:O:answer_in_cents", "spec:O:units_cap_plus_rest_at_last_rate_floor",
    "spec:O:ceil_of_product", "spec:O:floor_b_minus_floor_a",
    "spec:O:product_over_gcd_all", "spec:O:other_operation", "spec:A:op_of_first_two_only", "spec:O:gcd_of_last_two_or_lcm",
    "spec:O:largest_prime_le_29_dividing", "spec:O:sum_with_multiplicity", "spec:O:distinct_count", "spec:O:two_pow_distinct", "spec:O:omega_plus_one",
    "spec:O:term_n_minus_1", "spec:O:term_n_plus_1",
    "spec:O:two_smallest_coins_only", "spec:O:two_largest_coins_only", "spec:O:smallest_and_largest_only",
    "spec:A:first_two_only", "spec:O:constant_deficit_trick", "spec:O:constant_remainder_trick",
    "spec:O:larger_root_instead",
    "spec:O:smallest_fit_first_two", "spec:O:largest_fit_first_two", "spec:O:smallest_fit_all_but_last",
    "spec:O:cap_at_k_plus1", "spec:A:capped_sum_no_plus1",
}

LIN_PARTIAL = {("M1.median_list", "O:median_of_numbers"), ("M1.median_list", "spec:O:median_of_distinct_values"), ("M1.binomial_choose", "spec:O:C(x,j)*y")}
# ======================================================= END COPY


# ======================================================= additions (mine): heuristics for the rev2 shapes whose structured form is new, and the driver


def _pm_comb(s, f):
    vals = [f(b, e) for b, e in s["terms"]]
    return (sum(vals) if s["op"] == "sum" else math.prod(vals)) % s["modulus"]


def _grid_cells(s):
    return sum(b - a + 1 for rr in s["rows"] for a, b in rr)


def _grid_bbox(s):
    cols = [c for rr in s["rows"] for ab in rr for c in ab]
    return 2 * ((max(cols) - min(cols) + 1) + len(s["rows"]))


EXTRA_SPEC = {
    "M1.power_remainder_r2": {
        "O:base_mod_p": lambda s, q: s["terms"][0][0] % s["modulus"],
        "O:combined_base_residues": lambda s, q: _pm_comb(s, lambda b, e: b % s["modulus"]),
        "O:base_pow_exp_last_digit": lambda s, q: _pm_comb(s, lambda b, e: pow(b, e % 10, s["modulus"])),
        "O:base_pow_exp_mod_p": lambda s, q: _pm_comb(s, lambda b, e: pow(b, e % s["modulus"], s["modulus"])),
        "O:square_of_base": lambda s, q: _pm_comb(s, lambda b, e: pow(b, 2, s["modulus"])),
        "O:exponent_mod_p": lambda s, q: s["terms"][0][1] % s["modulus"],
        "O:base_pow_exp_plus_1": lambda s, q: _pm_comb(s, lambda b, e: pow(b, e + 1, s["modulus"])),
    },
    "M1.grid_perimeter_r2": {
        "A:four_times_cells": lambda s, q: 4 * _grid_cells(s),
        "A:bounding_box": lambda s, q: _grid_bbox(s),
        "O:bbox_plus_4": lambda s, q: _grid_bbox(s) + 4,
        "O:2cells_plus_2": lambda s, q: 2 * _grid_cells(s) + 2,
        "A:sum_row_run_perimeters": lambda s, q: sum(2 * (b - a + 1) + 2 for rr in s["rows"] for a, b in rr),
        "O:bbox_plus_2rows": lambda s, q: _grid_bbox(s) + 2 * len(s["rows"]),
        "O:2cells_plus_2rows": lambda s, q: 2 * _grid_cells(s) + 2 * len(s["rows"]),
    },
}


def _holds(n, c):  # overrides the copied one: the rev2 digit puzzle has more clue kinds (same semantics for the old kinds)
    from studies.m0.lineages_m1_rev2 import _clue_holds

    return _clue_holds(n, tuple(int(x) for x in str(n)), tuple(c))


def spec_for(lid):
    stem = lid[:-3] if lid.endswith("_r2") else lid
    return {**SPEC.get(stem, {}), **EXTRA_SPEC.get(lid, {})}


def _tag(name, lid):
    return name in PARTIAL or (lid.replace("_r2", ""), name) in LIN_PARTIAL or (lid, name) in LIN_PARTIAL


def measure_lineage(args):
    which, lid, n = args
    if which == "rev2":
        from studies.m0.lineages_m1_rev2 import load_rev2 as loader
    else:
        from studies.m0.lineages_m1_common import load_batch as loader
    lin = next(x for x in loader() if x.id == lid)
    spec = spec_for(lid)
    rec = {}
    for lv in ALL_LEVELS:
        rng = stream(SEED, "rev2-shortcut", lid, str(lv))
        items = [build_item(lin, lv, rng, "A", f"{lid}/sc/{lv}/{i}") for i in range(n)]
        keys = Counter(it.answer for it in items)
        top_key, top = keys.most_common(1)[0]
        half = n // 2
        tr = Counter(it.answer for it in items[:half]).most_common(1)[0][0]
        const_ho = sum(it.answer == tr for it in items[half:]) / (n - half)
        hits, applic = Counter(), Counter()
        for it in items:
            ns = nums(it.question)
            st = dict(it.structured)
            if st.get("shape") == "pallets":
                st["shape"] = "crates"  # the batch-1 name of the same keys, so the copied division heuristics apply
            hs = {name: f(ns) for name, f in {**GEN_AUTHOR, **GEN_OWN}.items()}
            for name, f in spec.items():
                try:
                    hs["spec:" + name] = f(st, it.question)
                except (StopIteration, IndexError, ZeroDivisionError, TypeError, ValueError, KeyError):
                    hs["spec:" + name] = None
            for name, v in hs.items():
                if v is not None:
                    applic[name] += 1
                hits[name] += eq(v, it.answer)
            hits["oracle:answer_is_a_printed_number"] += it.answer in {str(x) for x in ns}
        rates = {k: round(hits[k] / n, 4) for k in sorted(hits)}
        rec[str(lv)] = {"n": n, "distinct_answers": len(keys), "const_rate": round(top / n, 4), "const_heldout": round(const_ho, 4), "top_key": top_key, "rates": rates,
                        "applicable": {k: applic[k] for k in sorted(applic)}}
    return lid, rec


def summarise(res):
    rows = {}
    for lid, rec in sorted(res.items()):
        per = {}
        for lv, r in sorted(rec.items()):
            c = r["const_rate"]
            surf = {k: v for k, v in r["rates"].items() if not k.startswith("oracle") and not _tag(k, lid)}
            part = {k: v for k, v in r["rates"].items() if not k.startswith("oracle") and _tag(k, lid)}
            bs = max(surf, key=lambda k: surf[k])
            bp = max(part, key=lambda k: part[k]) if part else None
            per[lv] = {"const": c, "const_heldout": r["const_heldout"], "oracle_printed": r["rates"].get("oracle:answer_is_a_printed_number", 0.0), "worst_surface": bs, "worst_surface_rate": surf[bs],
                       "flag": surf[bs] >= max(0.25, 2 * c), "worst_partial": bp, "worst_partial_rate": part[bp] if bp else None}
        w = max(per.items(), key=lambda kv: kv[1]["worst_surface_rate"])
        rows[lid] = {"per_level": per, "worst_level": w[0], "worst": w[1]["worst_surface"], "worst_rate": w[1]["worst_surface_rate"], "const_at_worst": w[1]["const"],
                     "max_const": max(p["const"] for p in per.values()), "flagged_levels": [int(lv) for lv, p in per.items() if p["flag"]]}
    return rows


def main():
    import multiprocessing as mp

    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["rev2", "batch1"], required=True)
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--out", default="")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    if a.set == "rev2":
        from studies.m0.lineages_m1_rev2 import load_rev2 as loader
    else:
        from studies.m0.lineages_m1_common import load_batch as loader
    ids = [x.id for x in loader() if not a.only or x.id in a.only]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = dict(pool.map(measure_lineage, [(a.set, i, a.per_level) for i in ids]))
    summ = summarise(res)
    if a.out:
        Path(a.out).write_text(json.dumps({"set": a.set, "per_level": a.per_level, "seed": SEED, "raw": res, "summary": summ}, indent=1, sort_keys=True))
    for lid, s in sorted(summ.items()):
        print(f"{lid:34s} worst {s['worst']:44s} L{s['worst_level']} {s['worst_rate']:.3f} (const there {s['const_at_worst']:.3f}; max const {s['max_const']:.3f}) flagged {s['flagged_levels']}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
