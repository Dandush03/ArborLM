# ruff: noqa
"""Audit 3 of M1: capacity per lineage-level and per CLUSTER-level against the worst-case demand (LEAD_RULINGS_2 R-5, checked against ADR-0033 6.2 and 8):
core level: 10 x (ceil(24,000 / G) + 100); reserve level: 10 x 100 (and, under my reading of 6.5, possibly the core demand if a reserve level enters the chosen range).
G = clusters in the part: my map has 22 clusters over the 36 proposed lineages -> 11 per part when 22 clusters are shuffled into two halves; 21 (if gcd_lcm joins crt) -> 10.
Cluster capacity: (a) n_eff of an equal-weight mixture over the cluster's lineages = L^2 / sum(1 / n_eff_i) (lineages never share a key); a lineage-level with no collision
in M draws is given n_eff = M(M-1)/6 (<= 3 pairs at about 95%); (b) sum of Chao1 support estimates.
Usage: python3 capacity_clusters_a3.py cap.json"""
import json
import math
import sys

MAP = {
    "S1_linear_solve": ["linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"],
    "S2_weighted_sum": ["shopping", "speed_distance", "mixture"],
    "S3_multiplicative_chain": ["percent_change", "fraction_remainder", "tip_split", "ratio_share"],
    "S4_product_rule_counting": ["binomial_choose_r2", "slot_permutations_r2"],
    "S5_unbounded_table": ["change_ways_r2"],  # min_cost_packs_r2 NOT REGISTERED, excluded
    "S6_exposed_faces": ["grid_perimeter_r2", "painted_cube_r2"],
    "S7_step_rule": ["arithmetic_series", "recurrence_iterate"],
}
for s in ["clock_duration", "inclusion_exclusion_r2", "pigeonhole_worst_case_r2", "gcd_lcm_r2", "crt_congruence_r2", "prime_factors_r2", "power_remainder_r2", "quadratic_area",
          "digit_puzzle_r2", "pythagoras_r2", "tiered_pricing", "finite_differences", "median_list_r2", "mode_tally_r2", "division_counting_r2"]:
    MAP[s] = [s]
assert sum(len(v) for v in MAP.values()) == 36 and len(MAP) == 22

cap = json.load(open(sys.argv[1]))


def demand(level, G, reserve_as_core=False):
    if level in (0, 6) and not reserve_as_core:
        return 10 * 100
    return 10 * (math.ceil(24000 / G) + 100)


def ne(r):
    return r["n_eff"] if r["n_eff"] is not None else r["M"] * (r["M"] - 1) / 6


print("demand core G=11:", demand(3, 11), " G=10:", demand(3, 10), " reserve:", demand(0, 11))
print("\nPER LINEAGE (n_eff, Chao1) and failing levels at G=11 [n_eff basis | Chao1 basis]")
for cl, mem in MAP.items():
    for m in mem:
        lid = "M1." + m
        r = cap[lid]
        fails_ne = [lv for lv in range(7) if ne(r[str(lv)]) < demand(lv, 11)]
        fails_c1 = [lv for lv in range(7) if r[str(lv)]["chao1"] < demand(lv, 11)]
        row = " ".join(f"{lv}:{round(ne(r[str(lv)])):>9}/{r[str(lv)]['chao1']:>9}" for lv in range(7))
        print(f"{lid:30s} {row}  fails ne {fails_ne} c1 {fails_c1}")
print("\nPER CLUSTER at G=11 and G=10: failing levels (n_eff mixture basis | Chao1-sum basis); reserve at 1,000 and [if reserve levels carried the core demand]")
for cl, mem in MAP.items():
    out = []
    for G in (11, 10):
        f_ne, f_c1, f_ne_res = [], [], []
        for lv in range(7):
            rs = [cap["M1." + m][str(lv)] for m in mem]
            mix = len(rs) ** 2 / sum(1 / ne(r) for r in rs)
            c1 = sum(r["chao1"] for r in rs)
            if mix < demand(lv, G):
                f_ne.append(lv)
            if c1 < demand(lv, G):
                f_c1.append(lv)
            if lv in (0, 6) and mix < demand(lv, G, True):
                f_ne_res.append(lv)
        out.append(f"G={G}: ne {f_ne} c1 {f_c1} [reserve-as-core ne {f_ne_res}]")
    mins = [round(len(mem) ** 2 / sum(1 / ne(cap['M1.' + m][str(lv)]) for m in mem)) for lv in range(7)]
    print(f"{cl:28s} n_eff_mix per level {mins}  " + " | ".join(out))
