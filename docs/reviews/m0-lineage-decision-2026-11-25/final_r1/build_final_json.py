# ruff: noqa
"""Final R1 audit: assemble final_r1.json from this audit's raw outputs (check_keys_run1.jsonl.counts.json, pool_run1.json, levels_run2.json,
capacity_set11.json, capacity_set12.json, repro_*.txt, exclusion_run1.txt, new_rules_run1.txt). usage: python build_final_json.py <deliver dir>"""
import json, os, re, sys
D = sys.argv[1]
J = lambda f: json.load(open(os.path.join(D, f)))
keys = J("check_keys_run1.jsonl.counts.json")
pool = J("pool_run1.json")["lineages"]
lev = J("levels_run2.json")
cap11, cap12 = J("capacity_set11.json"), J("capacity_set12.json")
CL = {"R1.attribute_rule": ["R1.conditional_decision_tree_r6"], "R1.boolean_lights": ["R1.boolean_lights_r4", "R1.compass_turns"],
      "R1.categories_default_exceptions": ["R1.categories_default_exceptions_r4"], "R1.conditional_chain": ["R1.knights_knaves_r6"],
      "R1.conditional_threshold_rule": ["R1.conditional_threshold_rule_r4"], "R1.equivalence_exchange_rates": ["R1.equivalence_exchange_rates_r6", "R1.temporal_weekday_shift_r6"],
      "R1.graph_shortest_route": ["R1.graph_shortest_route_r6"], "R1.spatial_grid_walk": ["R1.spatial_grid_walk_r5"], "R1.swap_tracking": ["R1.swap_tracking_r5"], "R1.venn_counting": ["R1.venn_counting_r5"]}
cl_of = {l: c for c, ls in CL.items() for l in ls}
STATED = {"R1.boolean_lights_r4": ["presses", "lamps"], "R1.categories_default_exceptions_r4": ["chain_from_person"], "R1.compass_turns": ["commands"],
          "R1.conditional_decision_tree_r6": ["lights_stated"], "R1.conditional_threshold_rule_r4": ["members"], "R1.equivalence_exchange_rates_r6": ["hops_between_asked"],
          "R1.graph_shortest_route_r6": ["towns"], "R1.knights_knaves_r6": ["people"], "R1.spatial_grid_walk_r5": ["moves", "cells"], "R1.swap_tracking_r5": ["operations"],
          "R1.temporal_weekday_shift_r6": ["hops_anchor_to_asked"], "R1.venn_counting_r5": ["groups", "total"]}
out = {"auditor": "arbor-auditor context (Claude Opus 5.5); independent engineering/mathematical evidence; not Astra validation, not human approval",
       "worktree": "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f (claude/m0-impl, HEAD 9bcec484, uncommitted fix-4 files read as they are)",
       "bound": 0.15, "rule": "R-31 classes C and A of audit 4 counted; R-32 item-weighted pooled excess over impl primary + impl replicate + auditor fresh; R-34 per shape and level",
       "lineages": {}}
for lid in sorted(cl_of):
    k = keys[lid]
    p = pool[lid]
    L = lev[lid]
    c11 = [c for c in cap11["runs"]["4"]["cells"] if c["lineage"] == lid]
    out["lineages"][lid] = {
        "cluster": cl_of[lid],
        "keys": {"n": sum(r["n"] for r in k), "mismatch": sum(r["mismatch"] for r in k), "ambiguous": sum(r["ambiguous"] for r in k), "parse_errors": sum(r["parse"] for r in k), "per_level_n": [r["n"] for r in k]},
        "ambiguous_share": sum(r["ambiguous"] for r in k) / sum(r["n"] for r in k),
        "pooled": {"largest": p["largest"], "per_level": {lv: {kk: v[kk] for kk in ("pooled_max_counted", "rule", "class", "n_pooled", "per_run_max_counted", "M_max_not_counted", "EXCL_max_not_counted", "most_negative_eff_counted")} for lv, v in p["per_level"].items()},
                   "largest_M_not_counted": p["largest_M_not_counted"],
                   "largest_EXCL_not_counted": max((v["EXCL_max_not_counted"] for v in p["per_level"].values()), key=lambda x: x["excess"])},
        "verdict": p["verdict"],
        "levels": {"identity_classes": L["n_identity_classes"], "cross_level_text_overlap_max": L["cross_level_text_overlap_max"],
                   "stated_parameter_means": {s: L["trend"][s]["means"] for s in STATED[lid]}, "stated_parameter_strictly_rising": {s: L["trend"][s]["strictly_rising"] for s in STATED[lid]},
                   "chars_means": L["trend"]["chars"]["means"]},
        "capacity": {}}
    for setname, cap, gs in (("set12_impl", cap12, ("5", "4")), ("set11_after_this_audit", cap11, ("4", "3"))):
        for g in gs:
            cells = [c for c in cap["runs"][g]["cells"] if c["lineage"] == lid]
            if cells:
                out["lineages"][lid]["capacity"][f"{setname}_G{g}"] = {"D": cap["runs"][g]["D"], "q_per_level": cells[0]["q"], "min_distinct_over_levels": min(c["distinct"] for c in cells),
                                                                       "shortfall_levels": [c["level"] for c in cells if c["shortfalls"]]}
stays = sorted(l for l, v in out["lineages"].items() if v["verdict"] == "STAYS")
out["final_surviving_shapes"] = stays
out["final_surviving_clusters"] = sorted({cl_of[l] for l in stays})
out["dropped_here"] = sorted(l for l, v in out["lineages"].items() if v["verdict"] == "DROPS")
out["dropped_clusters_here"] = sorted(set(CL) - set(out["final_surviving_clusters"]))
for name, cap in (("set12_impl", cap12), ("set11_after_this_audit", cap11)):
    out[f"capacity_{name}"] = {"clusters": cap["clusters"], "G_by_R30": cap["G_by_R30"], "G_smaller_part": cap["G_smaller_part"], "parts": cap["parts"], "pool_seed": cap["pool_seed"],
                               "runs": {g: {"D": r["D"], "all_pass": r["all_pass"], "shortfall_cells": r["shortfall_cells"], "within_cell_repeats": r["within_cell_repeats"],
                                            "cross_lineage_repeats_total": sum(r["cross_lineage_repeats"].values()),
                                            "clusters_failing": sorted({k for k, d in r["per_cluster"].items() for v in d.values() if not v["pass"]})} for g, r in cap["runs"].items()}}
out["would_drop_if_M_counted"] = sorted(l for l, v in out["lineages"].items() if v["pooled"]["largest_M_not_counted"]["excess"] > 0.15)
out["would_drop_if_EXCL_counted"] = {l: v["pooled"]["largest_EXCL_not_counted"] for l, v in out["lineages"].items() if v["pooled"]["largest_EXCL_not_counted"]["excess"] > 0.15}
nr = {}
for line in open(os.path.join(D, "new_rules_run1.txt")):
    m = re.match(r"(R1\.\S+)\s+(.+?)\s+eff ((?:[+-]\d\.\d{3}\s*){7})\s+anti ((?:[+-]\d\.\d{3}\s*){7})$", line.strip())
    if m:
        e = [float(x) for x in m.group(3).split()]; a = [float(x) for x in m.group(4).split()]
        nr.setdefault(m.group(1), []).append({"rule": m.group(2), "eff": e, "anti": a, "max_excess": max(max(e), max(a))})
out["NEW_rules"] = nr
r1, r2, r3 = (open(os.path.join(D, f)).read() for f in ("repro_h1.txt", "repro_h98765.txt", "repro_hrandom.txt"))
out["reproducibility"] = {"PYTHONHASHSEED": ["1", "98765", "random"], "byte_identical": r1 == r2 == r3, "ALL_digest": r1.strip().splitlines()[-1].split()[-1]}
out["seeds"] = {"keys": "Random(31000+level), 1000 per level (trial: 30000+level, 30 per level)", "aud_battery": "items Random(32000+level) n=3000, fit Random(32100+level) 400",
                "impl_battery": "items Random(33000*1000+level) n=3000, fit Random(33100*1000+level) 300 (its own items_of)", "feature_lookups": "fit Random(34000+level) 3000, test Random(34100+level) 3000",
                "levels": "Random(35000+level) 1000; identity streams Random(4243) 100", "new_rules": "fit Random(36000+level), test Random(36100+level), 3000", "repro": "Random(37000+level) 300; pool seed 8900",
                "capacity": "core.generate_pool pool seed 8800, role development"}
json.dump(out, open(os.path.join(D, "final_r1.json"), "w"), indent=1, sort_keys=True)
print(json.dumps({k: out[k] for k in ("final_surviving_shapes", "final_surviving_clusters", "dropped_here", "dropped_clusters_here", "would_drop_if_M_counted", "would_drop_if_EXCL_counted", "reproducibility")}, indent=1))
for n in ("capacity_set12_impl", "capacity_set11_after_this_audit"):
    print(n, json.dumps(out[n]["runs"]))
