# ruff: noqa
"""Emit the verdict for all 666 pairs of the 37 M1 lineages from the auditor's judgement (JUDGEMENT_1_clusters.txt, hashed before the manifest was read).

Run: python3 pairs_table.py > pairs_666.tsv
"""
import itertools

E = ["shopping", "speed_distance", "pipes_work", "percent_change", "tip_split", "ratio_share", "mixture", "linear_equation", "consecutive", "ages",
     "average_missing", "rectangle", "arithmetic_series", "coins", "clock_duration", "fraction_remainder"]
N = ["inclusion_exclusion", "binomial_choose", "slot_permutations", "change_ways", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors",
     "last_digit_power", "quadratic_area", "digit_puzzle", "pythagoras", "grid_perimeter", "painted_cube", "min_cost_packs", "tiered_pricing",
     "recurrence_iterate", "finite_differences", "median_list", "mode_tally", "division_counting"]
ALL = E + N
assert len(ALL) == 37 and len(set(ALL)) == 37

STRICT = {
    "S1 linear-solve": ["linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"],
    "S2 weighted-sum": ["shopping", "speed_distance", "mixture"],
    "S3 multiplicative-scaling": ["percent_change", "fraction_remainder", "tip_split", "ratio_share"],
    "S4 product-rule counting": ["binomial_choose", "slot_permutations"],
    "S5 unbounded-knapsack table": ["change_ways", "min_cost_packs"],
    "S6 exposed faces of unit cells": ["grid_perimeter", "painted_cube"],
    "S7 arithmetic accumulation": ["arithmetic_series", "recurrence_iterate"],
}
LENIENT = {"L1 successive fractional change": ["percent_change", "fraction_remainder"]}
NEAR = {
    frozenset(p): why for p, why in [
        (("median_list", "mode_tally"), "sort-and-select vs tally-and-argmax"),
        (("change_ways", "digit_puzzle"), "count all Diophantine solutions vs filter 900 candidates by digit clues"),
        (("last_digit_power", "crt_congruence"), "exponent cycle mod 10 vs simultaneous congruences"),
        (("gcd_lcm", "prime_factors"), "Euclid/multiples canonical; factorising is one route to gcd/lcm"),
        (("gcd_lcm", "crt_congruence"), "lcm by multiples vs residue matching"),
        (("recurrence_iterate", "finite_differences"), "finite differences must infer the rule first"),
        (("quadratic_area", "pythagoras"), "quadratic root vs root of a sum of squares"),
        (("quadratic_area", "rectangle"), "quadratic vs linear"),
        (("tiered_pricing", "shopping"), "tier split (min(left,size)) and inverse mode vs plain dot product"),
        (("coins", "change_ways"), "unique 2x2 solution vs counting all solutions"),
        (("division_counting", "pipes_work"), "ceil/floor division vs exact division"),
        (("pigeonhole_worst_case", "division_counting"), "worst-case adversary sum vs ceilings"),
        (("clock_duration", "shopping"), "base-60 subtraction and sum vs dot product"),
        (("tip_split", "ratio_share"), "kept apart under lenient only"),
        (("arithmetic_series", "consecutive"), "forward AP sum vs inverse (strict puts consecutive in S1)"),
        (("min_cost_packs", "tiered_pricing"), "both pricing; search over pack counts vs marginal-rate split"),
        (("average_missing", "median_list"), "mean inversion vs sort-and-select"),
        (("average_missing", "mode_tally"), "mean inversion vs tally"),
        (("finite_differences", "arithmetic_series"), "difference-table inference vs AP sum"),
        (("painted_cube", "rectangle"), "region decomposition vs linear solve"),
    ]
}


def group_of(table, x):
    for g, xs in table.items():
        if x in xs:
            return g
    return None


rows = []
for a, b in itertools.combinations(ALL, 2):
    gs, gl = group_of(STRICT, a), group_of(LENIENT, a)
    strict = gs is not None and gs == group_of(STRICT, b)
    lenient = gl is not None and gl == group_of(LENIENT, b)
    if lenient:
        v = "MERGE (strict and lenient): " + gl
    elif strict:
        v = "MERGE strict only: " + gs
    elif frozenset((a, b)) in NEAR:
        v = "NEAR-MISS kept apart: " + NEAR[frozenset((a, b))]
    else:
        v = "distinct"
    rows.append((a, b, ("E" if a in E else "N") + ("E" if b in E else "N"), v))
print("a\tb\tkind\tverdict")
for r in rows:
    print("\t".join(r))
import collections
c = collections.Counter(r[3].split(":")[0] for r in rows)
print(f"# pairs {len(rows)}; " + "; ".join(f"{k} {v}" for k, v in sorted(c.items())))


def clusters(table, members):
    seen, n = set(), 0
    for x in members:
        g = group_of(table, x)
        if g is None:
            n += 1
        elif g not in seen:
            seen.add(g); n += 1
    return n


for name, mem in (("existing", E), ("new", N), ("overall", ALL)):
    print(f"# {name}: strict {clusters(STRICT, mem)}  lenient {clusters(LENIENT, mem)}")
