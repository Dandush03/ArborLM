# ruff: noqa: E501
"""Shortcut check for the M1 batch-1 lineages: score trivial heuristics on 2,000 items per level (all seven levels) with no model involved.

For an open numeric answer the reference is the constant most-frequent-answer rate of the same items (the score of always giving the commonest key); there is no 1/k.
A heuristic "far above chance" is flagged by a SCREENING rule of mine, not a registered threshold: accuracy >= max(0.25, 2 x the constant rate) on any level. Flagged lineages
are fixed or dropped before delivery. Heuristics read only the structured form and the numbers printed in the item.

Run: ``uv run --locked --offline python -m studies.m0.m1_shortcut_check [--per-level 2000] [--out PATH]``.
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_common import load_batch

SEED = 953703
_NUM = re.compile(r"\d+(?:\.\d+)?")
Heur = Callable[[dict[str, Any]], int | Fraction | None]


def nums_in(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"\b\d-digit", "", text))]


def _ceil(a: int, b: int) -> int:
    return -(-a // b)


# ------------------------------------------------------------------ lineage-specific heuristics (name -> function of the structured form)


def _ie(s: dict[str, Any]) -> dict[str, Callable[[], int]]:
    tot, sz, pr, ask = s["total"], s["sizes"], s["pairs"], s["ask"]
    return {
        "ignore_overlaps": lambda: tot - sum(sz) if ask == "none" else sum(sz),
        "pairs_only_no_triple": lambda: tot - (sum(sz) - sum(pr)) if ask == "none" else sum(sz) - sum(pr),
    }


def _hyp(s: dict[str, Any]) -> dict[str, Callable[[], int]]:
    g = s["given"]
    return {"sum_of_given": lambda: sum(g), "abs_diff_of_given": lambda: abs(g[0] - g[1]), "max_given": lambda: max(g), "sum_given_plus_isqrt": lambda: math.isqrt(g[0] ** 2 + g[1] ** 2)}


SPECIFIC: dict[str, dict[str, Heur]] = {
    "M1.gcd_lcm": {
        "min_value": lambda s: min(s["values"]),
        "abs_diff_first_two": lambda s: abs(s["values"][0] - s["values"][1]),
        "product_of_all": lambda s: math.prod(s["values"]),
        "max_value": lambda s: max(s["values"]),
        "gcd_or_lcm_of_the_first_two_only(correct only when two values)": lambda s: (math.gcd if s["ask"] == "gcd" else math.lcm)(*s["values"][:2]) if len(s["values"]) > 2 else None,
    },
    "M1.crt_congruence": {
        "first_remainder_plus_modulus": lambda s: s["conditions"][0][1] + s["conditions"][0][0],
        "product_of_moduli": lambda s: math.prod(m for m, _ in s["conditions"]),
        "sum_of_remainders": lambda s: sum(rr for _, rr in s["conditions"]),
        "search_using_first_two_conditions_only(correct only when two)": lambda s: next((n for n in range(1, 100000) if n % s["conditions"][0][0] == s["conditions"][0][1] and n % s["conditions"][1][0] == s["conditions"][1][1]), None) if len(s["conditions"]) > 2 else None,
    },
    "M1.prime_factors": {
        "n_itself": lambda s: s["n"],
        "n_halved": lambda s: s["n"] // 2,
        "smallest_prime_factor": lambda s: next(p for p in range(2, s["n"] + 1) if s["n"] % p == 0),
        "digit_count_of_n": lambda s: len(str(s["n"])),
        "count_of_all_prime_factors_ignoring_ask": lambda s: sum(1 for p in range(2, 40) if s["n"] % p == 0),
    },
    "M1.last_digit_power": {
        "base_last_digit": lambda s: s["terms"][0][0] % 10,
        "sum_or_product_of_base_last_digits": lambda s: (sum(b % 10 for b, _ in s["terms"]) if s["op"] == "sum" else math.prod(b % 10 for b, _ in s["terms"])) % 10,
        "exponent_last_digit": lambda s: s["terms"][0][1] % 10,
        "last_digit_of_base_times_exponent": lambda s: (s["terms"][0][0] * s["terms"][0][1]) % 10,
    },
    "M1.inclusion_exclusion": {"ignore_overlaps": lambda s: _ie(s)["ignore_overlaps"](), "pairs_only_no_triple": lambda s: _ie(s)["pairs_only_no_triple"]() if s["triple"] is not None else None,
                               "total_minus_biggest": lambda s: s["total"] - max(s["sizes"])},
    "M1.binomial_choose": {
        "plain_formula_ignoring_condition": lambda s: None if s["shape"] == "plain" else math.comb(s["n"], s["k"]) if s["shape"] == "include" else math.comb(s["x"] + s["y"], s["k"]),
        "n_times_k": lambda s: (s["n"] or s["x"] + s["y"]) * s["k"],
        "ordered_count": lambda s: math.perm(s["n"] or s["x"] + s["y"], s["k"]),
        "two_groups_sum_of_the_two_counts": lambda s: math.comb(s["x"], s["j"]) + math.comb(s["y"], s["k"] - s["j"]) if s["shape"] == "two_groups" else None,
    },
    "M1.slot_permutations": {
        "unconstrained_count": lambda s: len(s["digits"]) ** s["length"] if s["repeat"] else math.perm(len(s["digits"]), s["length"]),
        "unconstrained_half_for_parity": lambda s: (len(s["digits"]) ** s["length"] if s["repeat"] else math.perm(len(s["digits"]), s["length"])) // (2 if s["parity"] != "any" else 1),
    },
    "M1.change_ways": {
        "target_div_biggest_coin_plus1": lambda s: s["target"] // max(s["coins"]) + 1,
        "target_div_smallest_coin": lambda s: s["target"] // min(s["coins"]),
        "target_div_sum_of_coins": lambda s: s["target"] // sum(s["coins"]),
    },
    "M1.pigeonhole_worst_case": {
        "total_plus_one": lambda s: sum(s["counts"]) + 1,
        "k_minus_one_times_colours_plus_one": lambda s: (s["k"] - 1) * len(s["counts"]) + 1,
        "capped_sum_without_plus_one": lambda s: sum(min(n, s["k"] - 1) for n in s["counts"]) if s["goal"] == "same" else sum(s["counts"]) - min(s["counts"]),
        "total_minus_min": lambda s: sum(s["counts"]) - min(s["counts"]),
    },
    "M1.median_list": {
        "mean_of_values": lambda s: Fraction(sum(v for v in s["values"]), len(s["values"])) if s["shape"] == "list" else Fraction(sum(v * c for v, c in s["values"]), sum(c for _, c in s["values"])),
        "middle_of_printed_order": lambda s: s["values"][len(s["values"]) // 2] if s["shape"] == "list" else s["values"][len(s["values"]) // 2][0],
        "median_ignoring_multiplicities": lambda s: None if s["shape"] == "list" else sorted(v for v, _ in s["values"])[(len(s["values"]) - 1) // 2],
        "first_value": lambda s: s["values"][0] if s["shape"] == "list" else s["values"][0][0],
    },
    "M1.mode_tally": {
        "first_repeated_value": lambda s: next((v for i, v in enumerate(s["values"]) if v in s["values"][:i]), None) if s["ask"] == "mode" else None,
        "median_value": lambda s: sorted(s["values"])[len(s["values"]) // 2] if s["ask"] == "mode" else None,
        "count_of_first_repeated_value": lambda s: (lambda v: s["values"].count(v))(next(v for i, v in enumerate(s["values"]) if v in s["values"][:i])) if s["ask"] == "mode_count" else None,
        "count_is_n_over_distinct": lambda s: round(len(s["values"]) / len(set(s["values"]))) if s["ask"] == "mode_count" else None,
    },
    "M1.recurrence_iterate": {
        "sum_of_stated_numbers": lambda s: sum(s["first"]),
        "position_times_first": lambda s: s["position"] * s["first"][0],
        "first_times_mult_pow": lambda s: s["first"][0] * (s["mult"] or 2) ** (s["position"] - 1),
    },
    "M1.finite_differences": {
        "linear_extrapolation": lambda s: s["terms"][-1] + (s["terms"][-1] - s["terms"][-2]) * (s["ask"] - len(s["terms"])),
        "ratio_extrapolation": lambda s: round(s["terms"][-1] * s["terms"][-1] / s["terms"][-2]) if s["ask"] == len(s["terms"]) + 1 else None,
        "last_plus_first_difference": lambda s: s["terms"][-1] + (s["terms"][1] - s["terms"][0]) * (s["ask"] - len(s["terms"])),
    },
    "M1.quadratic_area": {
        "isqrt_of_area_or_total": lambda s: math.isqrt(s["area"] or s["total"] // 2) if s["shape"] != "rect_perimeter" else s["perimeter"] // 4,
        "area_div_d": lambda s: s["area"] // s["d"] if s["d"] and s["area"] else None,
        "perimeter_quarter_plus_one": lambda s: s["perimeter"] // 4 + 1 if s["shape"] == "rect_perimeter" else None,
        "round_sqrt_area_minus_half_d": lambda s: round(math.sqrt(s["area"]) - s["d"] / 2) if s["area"] and s["d"] else None,
    },
    "M1.digit_puzzle": {
        "smallest_fit_for_first_clue": lambda s: next((n for n in _range(s) if _holds_clue(n, s["clues"][0])), None),
        "largest_fit_for_first_clue": lambda s: next((n for n in reversed(list(_range(s))) if _holds_clue(n, s["clues"][0])), None),
        "smallest_fit_for_second_clue": lambda s: next((n for n in _range(s) if _holds_clue(n, s["clues"][1])), None),
    },
    "M1.pythagoras": {"sum_of_given": lambda s: sum(s["given"]), "abs_diff_of_given": lambda s: abs(s["given"][0] - s["given"][1]), "max_given": lambda s: max(s["given"]),
                      "sum_for_hyp_diff_for_leg": lambda s: sum(s["given"]) if s["shape"] in ("walk", "diagonal") else abs(s["given"][0] - s["given"][1])},
    "M1.grid_perimeter": {
        "four_times_cells": lambda s: 4 * sum(b - a + 1 for a, b in s["rows"]),
        "sum_of_row_perimeters": lambda s: sum(2 * (b - a + 1) + 2 for a, b in s["rows"]),
        "twice_widest_row_plus_twice_rows": lambda s: 2 * max(b - a + 1 for a, b in s["rows"]) + 2 * len(s["rows"]),
        "bounding_box_perimeter": lambda s: 2 * ((max(b for _, b in s["rows"]) - min(a for a, _ in s["rows"]) + 1) + len(s["rows"])),
    },
    "M1.painted_cube": {
        "all_faces_painted_formula(ignores the unpainted bottom)": lambda s: _cube_formula(s) if s["bottom_unpainted"] else None,
        "product_of_dims": lambda s: math.prod(s["dims"]),
        "inner_block": lambda s: math.prod(d - 2 for d in s["dims"]),
    },
    "M1.min_cost_packs": {
        "singles_only": lambda s: s["need"] * s["single"],
        "biggest_pack_then_singles": lambda s: (s["need"] // max(s["packs"])[0]) * max(s["packs"])[1] + (s["need"] % max(s["packs"])[0]) * s["single"],
        "all_biggest_packs_ceil": lambda s: _ceil(s["need"], max(s["packs"])[0]) * max(s["packs"])[1],
        "best_unit_price_pack_ceil": lambda s: min(_ceil(s["need"], p) * q for p, q in s["packs"]),
        "best_unit_price_pack_then_singles": lambda s: (lambda b: (s["need"] // b[0]) * b[1] + (s["need"] % b[0]) * s["single"])(min(s["packs"], key=lambda pq: Fraction(pq[1], pq[0]))),
    },
    "M1.tiered_pricing": {
        "units_times_first_rate": lambda s: Fraction((s["used"] or 0) * s["tiers"][0][1], 100) if s["used"] is not None else Fraction(s["bill_cents"], s["tiers"][0][1]),
        "units_times_last_rate": lambda s: Fraction((s["used"] or 0) * s["last_rate"], 100) if s["used"] is not None else Fraction(s["bill_cents"], s["last_rate"]),
        "units_times_mean_rate": lambda s: Fraction((s["used"] or 0) * (sum(c for _, c in s["tiers"]) + s["last_rate"]), 100 * (len(s["tiers"]) + 1)) if s["used"] is not None else None,
    },
    "M1.division_counting": {
        "rounded_quotient": lambda s: round(s["items"] / (s["box"] * s["crate"])) if s["shape"] == "crates" else round((s["high"] - s["low"]) / s["div"]) if s["shape"] == "multiples" else s["people"] % s["seats"],
        "floor_quotient": lambda s: s["items"] // (s["box"] * s["crate"]) if s["shape"] == "crates" else (s["high"] - s["low"]) // s["div"] if s["shape"] == "multiples" else s["people"] // s["seats"],
        "remainder_not_complement": lambda s: s["people"] % s["seats"] if s["shape"] == "empty_seats" else None,
        "single_ceil_only": lambda s: _ceil(s["items"], s["box"]) if s["shape"] == "crates" else None,
    },
}


def _range(s: dict[str, Any]) -> range:
    return range(10, 100) if s["digits"] == 2 else range(100, 1000)


def _holds_clue(n: int, c: list[Any]) -> bool:
    from studies.m0.lineages_m1_algebra import _holds

    return _holds(n, c)


def _cube_formula(s: dict[str, Any]) -> int | None:
    a, b, c = s["dims"]
    return {0: (a - 2) * (b - 2) * (c - 2), 1: 2 * ((a - 2) * (b - 2) + (a - 2) * (c - 2) + (b - 2) * (c - 2)), 2: 4 * ((a - 2) + (b - 2) + (c - 2))}[s["faces"]]


def _gen_heuristics() -> dict[str, Callable[[list[int], str], int | Fraction | None]]:
    return {
        "first_number_stated": lambda ns, _a: ns[0] if ns else None,
        "last_number_stated": lambda ns, _a: ns[-1] if ns else None,
        "sum_of_all_numbers": lambda ns, _a: sum(ns),
        "product_of_all_numbers": lambda ns, _a: math.prod(ns) if len(ns) < 12 else None,
        "largest_number_stated": lambda ns, _a: max(ns) if ns else None,
        "smallest_number_stated": lambda ns, _a: min(ns) if ns else None,
    }


def _eq(h: int | Fraction | None, ans: str) -> bool:
    return h is not None and Fraction(ans) == Fraction(h)


def run(per_level: int = 2000, only: list[str] | None = None) -> dict[str, Any]:
    gen = _gen_heuristics()
    out: dict[str, Any] = {}
    for lin in load_batch():
        if only and lin.id not in only:
            continue
        rec: dict[str, Any] = {"family": lin.family, "levels": {}}
        for lv in ALL_LEVELS:
            rng = stream(SEED, "shortcut", lin.id, str(lv))
            items = []
            for i in range(per_level):
                items.append(build_item(lin, lv, rng, "A", f"{lin.id}/sc/{lv}/{i}"))
            n = len(items)
            keys = Counter(it.answer for it in items)
            top_key, top = keys.most_common(1)[0]
            half = n // 2
            tr = Counter(it.answer for it in items[:half]).most_common(1)[0][0]
            const_heldout = sum(it.answer == tr for it in items[half:]) / (n - half)
            hits: dict[str, int] = {}
            for it in items:
                ns = nums_in(it.question)
                for name, f in gen.items():
                    hits[name] = hits.get(name, 0) + _eq(f(ns, it.answer), it.answer)
                hits["answer_is_some_stated_number(oracle)"] = hits.get("answer_is_some_stated_number(oracle)", 0) + (it.answer in {str(x) for x in ns})
                for name, f2 in SPECIFIC.get(lin.id, {}).items():
                    try:
                        v = f2(it.structured)
                    except (StopIteration, IndexError, ZeroDivisionError, TypeError, ValueError):
                        v = None
                    hits["spec:" + name] = hits.get("spec:" + name, 0) + _eq(v, it.answer)
            acc = {k: round(v / n, 4) for k, v in sorted(hits.items())}
            real = {k: v for k, v in acc.items() if "oracle" not in k}
            worst_name = max(real, key=lambda k: real[k])
            const = top / n
            rec["levels"][str(lv)] = {
                "n": n, "distinct_answers": len(keys), "constant_most_frequent_rate": round(const, 4), "constant_heldout_rate": round(const_heldout, 4), "top_key": top_key,
                "oracle_answer_is_some_stated_number": acc.get("answer_is_some_stated_number(oracle)", 0.0),
                "worst_heuristic": worst_name, "worst_accuracy": real[worst_name], "flag": real[worst_name] >= max(0.25, 2 * const), "all": acc,
            }
        lv_rows = rec["levels"].values()
        w = max(lv_rows, key=lambda x: x["worst_accuracy"])
        rec["worst_over_levels"] = {"heuristic": w["worst_heuristic"], "accuracy": w["worst_accuracy"], "constant_rate_same_level": w["constant_most_frequent_rate"]}
        rec["max_constant_rate"] = max(x["constant_most_frequent_rate"] for x in lv_rows)
        rec["flagged_levels"] = [int(k) for k, x in rec["levels"].items() if x["flag"]]
        out[lin.id] = rec
    return out


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--out", default="")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    res = run(a.per_level, a.only)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    for lid, rec in sorted(res.items()):
        w = rec["worst_over_levels"]
        print(f"{lid:34s} worst {w['heuristic']:42s} {w['accuracy']:.3f}  max-const {rec['max_constant_rate']:.3f}  flagged levels {rec['flagged_levels']}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
