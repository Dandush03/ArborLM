# ruff: noqa
"""Audit 4 of M1: capacity per cluster on the AUDITOR's strict map, from capacity_a4.py output. Standard library only.
Demand (R-10, R-11): 10 x (ceil(4000/G) + ceil(20000/G) + 100) per cluster and level, reserve levels the same.
Bases: (a) mixture n_eff with equal weight over members, L^2 / sum(1/n_i); (b) sum of Chao1; (c) equal share: every member must reach demand / L on its own n_eff;
(d) the EXISTING pool builder (core.generate_pool / m0_draw) balances per LINEAGE, not per cluster: each lineage-level must then reach 10 x (ceil(4000/N) + ceil(20000/N) + 100),
N = the number of lineages in the part; shown for N = 10 (worst: ten one-lineage clusters), 13, 16, 23 (best: the part holding S1, S2, S3).
Usage: python3 capacity_clusters_a4.py cap_M30000.json"""
import json
import math
import sys

MAP = {
    "S1_linear_solve": ["linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"],
    "S2_weighted_sum": ["shopping", "speed_distance", "mixture"],
    "S3_multiplicative_chain": ["percent_change", "fraction_remainder", "tip_split", "ratio_share"],
    "S4_product_rule_counting": ["slot_permutations"],
    "S5_unbounded_table": ["change_ways"],
    "S6_exposed_faces": ["grid_perimeter", "painted_cube"],
    "S7_step_rule": ["arithmetic_series", "recurrence_iterate"],
}
SINGLE = ["clock_duration", "inclusion_exclusion", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors", "last_digit_power", "quadratic_area", "tiered_pricing",
          "finite_differences", "median_list", "mode_tally", "division_counting"]


def demand(g):
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def lid(st):
    return "M1.tiered_pricing" if st == "tiered_pricing" else f"M1.{st}_r3"


if __name__ == "__main__":
    cap = json.load(open(sys.argv[1]))["levels"]
    M = 30000

    def ne(r):
        return r["n_eff"] if r["n_eff"] is not None else M * (M - 1) / 6

    clusters = dict(MAP)
    clusters.update({s: [s] for s in SINGLE})
    print("clusters on the auditor's map:", len(clusters), "; registered lineages:", sum(len(v) for v in clusters.values()))
    for G in (10, 9, 8):
        d = demand(G)
        print(f"\nG = {G}: demand {d}")
        for cl, mem in clusters.items():
            L = len(mem)
            fails = {"mixture": [], "chao1": [], "equal_share": []}
            tight = []
            for lv in range(7):
                rs = [cap[lid(m)][str(lv)] for m in mem]
                mix = L * L / sum(1 / ne(r) for r in rs)
                c1 = sum(r["chao1"] for r in rs)
                share = min(ne(r) for r in rs) * L
                if mix < d:
                    fails["mixture"].append(lv)
                if c1 < d:
                    fails["chao1"].append(lv)
                if share < d:
                    fails["equal_share"].append(lv)
                tight.append(round(share))
            if any(fails.values()) or G == 10:
                print(f"  {cl:26s} equal-share n_eff*L per level {tight}  fails {fails}")
    print("\nExisting pool builder (per-LINEAGE balance): lineage-levels below the per-lineage demand")
    allst = [m for v in clusters.values() for m in v]
    for N in (10, 13, 16, 23):
        d = demand(N)
        bad = {}
        for st in allst:
            lv_bad = [lv for lv in range(7) if ne(cap[lid(st)][str(lv)]) < d]
            if lv_bad:
                bad[st] = lv_bad
        print(f"  N = {N} lineages in the part, demand {d}: {len(bad)} lineages fail: {bad}")
