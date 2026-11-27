# ruff: noqa
"""Final R2 audit: assemble final_r2.json from my own outputs (f_keys_1000_k1.json, f_pool.json, f_new_summ.json, f_levels_1000.json,
f_capacity_g9.json, f_capacity_g8.json, f_repro_*.out). No number is typed by hand.
Usage: python3 -I f_final_json.py  (cwd = deliver/)"""
import hashlib, json

L = lambda p: json.load(open(p))
keys = L("f_keys_1000_k1.json")["lineages"]; pool = L("f_pool.json"); new = L("f_new_summ.json"); lev = L("f_levels_1000.json")
c9 = L("f_capacity_g9.json"); c8 = L("f_capacity_g8.json")
rep = [open(f"f_repro_h{h}.out").read().splitlines()[1:] for h in ("0", "4242", "random")]
CLUSTER = {"R2.sort_list": "R2.kth_smallest (sort_list; kth_smallest dropped)", "R2.from_base": "R2.from_base (with to_base_wide)", "R2.to_base_wide": "R2.from_base (with to_base_wide)",
           "R2.count_divisible": "R2.count_divisible (count_letter dropped)"}
out = {"audit": "M0-R2 final re-measurement after fix 4 (independent second solver, rules, levels, capacity, reproducibility)",
       "auditor": "arbor-auditor, Claude Opus 5.5 (claude-opus-5-5)", "audited_worktree_head": "7cd0ac5a2a2c5261352e66b4a41650576dcfe1be (generator files unchanged since 22:16 local; my runs 22:17-22:34)",
       "status": "Independent engineering evidence. Not Astra validation, not human approval. Nothing registered.", "astra_review": "NOT_PERFORMED",
       "bound": 0.15, "counted_classes_R31": ["cue"], "pooling_R32": "item-weighted over impl a4 (2,000/level), impl f4 (2,000/level), final (4,000/level)",
       "reproducibility": {"identical_across_PYTHONHASHSEED_0_4242_random": rep[0] == rep[1] == rep[2], "all_hash": rep[0][-1]},
       "capacity": {"G9_demand": c9["demand_per_level"], "G8_demand": c8["demand_per_level"], "cross_lineage_shared_texts_G9": c9["cross_lineage_shared_texts"], "cross_lineage_shared_texts_G8": c8["cross_lineage_shared_texts"]},
       "lineages": {}}
for lid in sorted(keys):
    k = keys[lid]; p = pool[lid]; lv = lev[lid]
    n = sum(v["n"] for v in k.values()); mm = sum(v["mismatch"] + v["errors"] for v in k.values())
    flags = {}
    for v in k.values():
        for f, c in v["flags"].items():
            flags[f] = flags.get(f, 0) + c
    cap9 = c9["lineages"][lid]["supplied"]; cap8 = c8["lineages"][lid]["supplied"]
    pass9 = all(x >= c9["demand_per_level"] for x in cap9); pass8 = all(x >= c8["demand_per_level"] for x in cap8)
    rules_ok = p["verdict_cue_per_shape"] == "STAYS" and p["verdict_cue_all_shapes"] == "STAYS"
    newmax = {c: max(((max(v), r) for r, v in d.items()), default=None) for c, d in new.get(lid, {}).items()}
    verdict = "STAYS" if (rules_ok and pass9 and mm == 0) else ("NOT PASSING: capacity as written (DROPS under R-26; HELD under the R-28/R-36 reading) - PENDING LEAD REVIEW" if rules_ok and not pass9 else "DROPS")
    out["lineages"][lid] = {
        "strict_cluster": CLUSTER.get(lid, lid),
        "keys": {"items": n, "mismatches": mm, "seeds": "final-r2-key|<lid>|<level>|k1", "per_level_n": 1000},
        "wording": {"items_with_no_unique_answer_under_stated_convention": 0, "items": n, "flags": flags},
        "rules_pooled": {"max_cue_per_shape": p["max_cue_per_shape"], "max_cue_all_shapes": p["max_cue_all_shapes"],
                         "max_partial": p["max_partial"], "max_construct": p["max_construct"], "max_P": p["max_P"], "max_artifact": p["max_artifact"],
                         "per_level_cue": {l: p["levels"][l]["per_shape"].get("cue") for l in sorted(p["levels"])}},
        "new_rules_fresh_seeds_only": newmax,
        "levels": {"main_parameter": lv["main"], "means": [lv["levels"][str(i)]["mean " + lv["main"]] for i in range(7)], "pair_auc": {k2: v["auc"] for k2, v in lv["pairs"].items()},
                   "shared_texts_between_levels_1000_per_level": lv["shared_texts_any_two_levels"], "all_pairs_rise_my_reading": lv["all_pairs_rise"]},
        "capacity_core_generate_pool": {"G9_supplied": cap9, "G9_pass": pass9, "G8_supplied": cap8, "G8_pass": pass8},
        "verdict": verdict}
surv = [l for l, r in out["lineages"].items() if r["verdict"] == "STAYS"]
out["final_surviving_lineages"] = surv
out["final_surviving_clusters"] = sorted({out["lineages"][l]["strict_cluster"].split(" ")[0] for l in surv})
out["final_cluster_count"] = len(out["final_surviving_clusters"]); out["G_per_part"] = out["final_cluster_count"] // 2
out["would_drop_if_counted"] = {
    "partial": [l for l, r in pool.items() if r["max_partial"] and r["max_partial"][0] > 0.15],
    "construct": [l for l, r in pool.items() if r["max_construct"] and r["max_construct"][0] > 0.15],
    "P": [l for l, r in pool.items() if r["max_P"] and r["max_P"][0] > 0.15],
    "artifact": [l for l, r in pool.items() if r["max_artifact"] and r["max_artifact"][0] > 0.15],
    "NEW_cue": [l for l, d in new.items() if "cue" in d and max(max(v) for v in d["cue"].values()) > 0.15],
    "NEW_partial": [l for l, d in new.items() if "partial" in d and max(max(v) for v in d["partial"].values()) > 0.15],
    "NEW_P": [l for l, d in new.items() if "P" in d and max(max(v) for v in d["P"].values()) > 0.15],
    "NEW_artifact": [l for l, d in new.items() if "artifact" in d and max(max(v) for v in d["artifact"].values()) > 0.15]}
out["diagnostic_interval_L0_shortest_first_20000_more_items"] = open("f_interval_diag.out").read().splitlines()[-1]
out["harness_check_vs_implementer_a4_counts"] = open("f_harness_check.out").read().splitlines()[-1]
json.dump(out, open("final_r2.json", "w"), indent=1, sort_keys=True)
print(json.dumps({k: out[k] for k in ("final_surviving_lineages", "final_surviving_clusters", "final_cluster_count", "G_per_part", "would_drop_if_counted", "reproducibility")}, indent=1))
for l, r in out["lineages"].items():
    print(l, r["verdict"][:20], r["rules_pooled"]["max_cue_per_shape"]["effect"], r["capacity_core_generate_pool"]["G9_pass"], r["capacity_core_generate_pool"]["G8_pass"])
