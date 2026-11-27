# ruff: noqa
"""Final M1 audit: capacity verdicts from capacity_M30000.json.
Cluster map: AUDIT4_M1.md section 5 (strict map over the 33 round-3 candidates), typed here from the report text, minus the round-4 drops
(coins, slot_permutations, pigeonhole_worst_case, mode_tally); compared with the manifest's surviving_clusters.
Demand D(G) = 10 x (ceil(4000/G) + ceil(20000/G) + 100) (R-11, R-30).
(i) core.generate_pool AS WRITTEN: allocation equal per LINEAGE over part_lineages(family_partition); the partition rule (sorted families, core.stream(400004,
    'family-partition', 'M1').shuffle, first half -> A) applied to the survivors' families (they are not in core.REGISTRY, so generate_pool cannot run on them).
    Demand per lineage-level, four readings: own-part lineage count; smaller part decides; each one lower; and the per-cluster demand applied to each lineage.
(ii) HYPOTHETICAL per-cluster builder: equal split by cluster then by member; bases mixture k^2 / sum(1/n_i), Chao1 sum, equal share k x min n_i; G = 8 and 7.
Keys: TEXT (primary, the de-duplication draw_items does), STRUCT (secondary) and A4KEY (audit 4's canonical key, the implementer's basis)."""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import survivors
from studies.m0.core import stream

A4_MAP = {"S1_linear_solve": ["linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"], "S2_weighted_sum": ["shopping", "speed_distance", "mixture"],
          "S3_multiplicative_chain": ["percent_change", "fraction_remainder", "tip_split", "ratio_share"], "S4_product_rule_counting": ["slot_permutations"], "S5_unbounded_table": ["change_ways"],
          "S6_exposed_faces": ["grid_perimeter", "painted_cube"], "S7_step_rule": ["arithmetic_series", "recurrence_iterate"]}
for s in ("clock_duration", "inclusion_exclusion", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors", "last_digit_power", "quadratic_area", "tiered_pricing", "finite_differences", "median_list", "mode_tally", "division_counting"):
    A4_MAP[s] = [s]


def D(g):
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def stem(lid):
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        s = s.removesuffix(suf)
    return s


if __name__ == "__main__":
    cap = json.load(open(sys.argv[1]))
    man = json.load(open("studies/m0/manifests/m1_fix4_survivors.json"))
    reg = survivors()
    ids = sorted(reg)
    cl_of = {i: next(c for c, mem in A4_MAP.items() if stem(i) in mem) for i in ids}
    clusters = {}
    for i in ids:
        clusters.setdefault(cl_of[i], []).append(i)
    clusters = dict(sorted(clusters.items()))
    same_map = {k: sorted(v) for k, v in clusters.items()} == {k: sorted(v) for k, v in man["surviving_clusters"].items()}
    ncl = len(clusters)
    G = ncl // 2
    fam = {i: reg[i].family for i in ids}
    fams = sorted(set(fam.values()))
    r = stream(400004, "family-partition", "M1")
    sh = fams[:]
    r.shuffle(sh)
    part_of_fam = {f: ("A" if k < len(sh) // 2 else "B") for k, f in enumerate(sh)}
    part = {i: part_of_fam[fam[i]] for i in ids}
    npart = {p: sum(1 for i in ids if part[i] == p) for p in "AB"}
    nsmall = min(npart.values())
    out = {"clusters": clusters, "cluster_count": ncl, "G": G, "map_equals_manifest": same_map, "families": len(fams), "family_part": part_of_fam, "lineages_per_part": npart,
           "demands": {"cluster_G": D(G), "cluster_G_minus_1": D(G - 1)}}
    print(f"clusters {ncl} (map equals the manifest's: {same_map}); G = {G}; D(G) = {D(G)}, D(G-1) = {D(G-1)}; families {len(fams)}; lineages per part {npart}")
    readings = {
        "own_part_count": {i: D(npart[part[i]]) for i in ids},
        "smaller_part_decides": {i: D(nsmall) for i in ids},
        "own_part_count_minus_1": {i: D(npart[part[i]] - 1) for i in ids},
        "smaller_part_minus_1": {i: D(nsmall - 1) for i in ids},
        "cluster_demand_G_per_lineage": {i: D(G) for i in ids},
        "cluster_demand_G_minus_1_per_lineage": {i: D(G - 1) for i in ids},
    }
    neff = {key: {i: [cap["results"][i][str(L)][key]["n_eff"] for L in range(7)] for i in ids} for key in ("text", "struct", "a4key")}
    nocol = {key: {i: [cap["results"][i][str(L)][key]["no_collision"] for L in range(7)] for i in ids} for key in ("text", "struct", "a4key")}
    aw = {}
    for key in ("text", "struct", "a4key"):
        for rd, dem in readings.items():
            fails = {i: [L for L in range(7) if neff[key][i][L] < dem[i]] for i in ids}
            fails = {i: v for i, v in fails.items() if v}
            remaining = sorted({cl_of[i] for i in ids if i not in fails})
            aw[f"{key}/{rd}"] = {"fails": fails, "clusters_remaining_if_failing_dropped": len(remaining), "clusters_lost": sorted(set(clusters) - set(remaining))}
            print(f"AS WRITTEN [{key}] {rd}: {len(fails)} failing lineages {sorted(stem(i) for i in fails)}; clusters left if dropped: {len(remaining)} (lost {sorted(set(clusters) - set(remaining))})")
    out["as_written"] = aw
    out["per_lineage"] = {i: {"cluster": cl_of[i], "family": fam[i], "part": part[i], "n_eff_text": [round(x) for x in neff["text"][i]], "n_eff_struct": [round(x) for x in neff["struct"][i]], "n_eff_a4key": [round(x) for x in neff["a4key"][i]],
                              "no_collision_text": nocol["text"][i], "no_collision_struct": nocol["struct"][i]} for i in ids}
    hyp = {}
    for key in ("text", "struct", "a4key"):
        for g in (G, G - 1):
            d = D(g)
            res = {}
            for c, mem in clusters.items():
                k = len(mem)
                rows = {"mixture": [], "chao1": [], "equal_share": []}
                for L in range(7):
                    ns = [cap["results"][i][str(L)][key]["n_eff"] for i in mem]
                    rows["mixture"].append(round(k * k / sum(1 / n for n in ns)))
                    rows["chao1"].append(round(sum(cap["results"][i][str(L)][key]["chao1"] for i in mem)))
                    rows["equal_share"].append(round(k * min(ns)))
                res[c] = {"rows": rows, "fails": {b: [L for L in range(7) if v[L] < d] for b, v in rows.items()}}
            hyp[f"{key}/G={g}"] = {"demand": d, "clusters": res}
            fl = {b: sorted(c for c, v in res.items() if v["fails"][b]) for b in ("mixture", "chao1", "equal_share")}
            print(f"HYPOTHETICAL per-cluster [{key}] G={g} demand {d}: failing clusters by basis {fl}")
            for c, v in res.items():
                if any(v["fails"].values()):
                    print(f"     {c}: " + "; ".join(f"{b} {v['rows'][b]} fails {v['fails'][b]}" for b in v["rows"] if v["fails"][b]))
    out["hypothetical_per_cluster"] = hyp
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    print("per-lineage n_eff (text | struct), part, smallest first by struct:")
    for i in sorted(ids, key=lambda i: min(neff["a4key"][i])):
        print(f"  {i} [{part[i]}] text {[round(x) for x in neff['text'][i]]} | struct {[round(x) for x in neff['struct'][i]]} | a4key {[round(x) for x in neff['a4key'][i]]}")
