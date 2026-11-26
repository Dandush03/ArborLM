# ruff: noqa
"""Final C1 audit (fix 4), step 10: assemble final_c1.json from my outputs (stdlib only). Usage: python3 f10_assemble.py SCRATCH OUT_JSON"""
import json, os, sys
from collections import Counter

D, outp = sys.argv[1], sys.argv[2]
J = lambda n: json.load(open(os.path.join(D, n)))
keys, pool, lev, cap, capsh, cons = J("keys9311.json"), J("f4b_pooled_v2.json"), J("f7_levels_9311.json"), J("f6b_capacity_summary.json"), J("f6d_capacity_shared.json"), J("f8_consistency.json")
cf_mine, cf_impl = J("f5b_closed_forms_v2_9311.json"), J("f5b_closed_forms_v2_impl_gen72.json")
meta = J("gen9311/meta.json")
MEMBERS = {
    "B1": ["C1.string_build_f3", "C1.list_build_f3", "C1.nested_pairs_f3"], "B2": ["C1.func_branch_f4", "C1.func_compose_f4"],
    "B3": ["C1.slices_f4", "C1.string_methods_f3"], "B5": ["C1.euclid_gcd_traced_f3", "C1.cond_chain_f3"],
    "B6": ["C1.fib_like_f3", "C1.fib_shapes_recursive_f3", "C1.recursive_calls_r2"], "B7": ["C1.bytecode_loop_f3", "C1.turtle_walk_f3"],
    "B8": ["C1.bracket_matching_f3", "C1.postfix_evaluation"], "C1.while_counter": ["C1.while_counter_f3"], "C1.digit_peel": ["C1.digit_peel_f3"],
    "C1.run_length_scan": ["C1.run_length_scan"], "C1.sieve_marking": ["C1.sieve_marking_f4"], "C1.binary_search": ["C1.binary_search_f3"],
    "C1.merge_two_sorted": ["C1.merge_two_sorted_f3"], "C1.union_find_links": ["C1.union_find_links_f3"], "C1.circle_elimination": ["C1.circle_elimination_r2"],
    "C1.shared_lists": ["C1.shared_lists_f3"], "C1.fast_power_square_map": ["C1.fast_power_f4"], "C1.counter_list_state_machine": ["C1.counter_list_f3"]}
VARIANTS = {"C1.fast_power_square_map", "C1.counter_list_state_machine"}
R19 = {
    "C1.run_length_scan": "answer-conditional (the 'long' shape with no run >= 2, empty answer); NEEDED: an empty gold key is not gradable (scoring.in_grammar returns False for '')",
    "C1.slices_f4": "answer-conditional via the shared finish (empty string answer when both slices are empty); NEEDED (empty key not gradable)",
    "C1.string_methods_f3": "answer-conditional for an empty final answer (shared finish; NEEDED) and state-conditional for an empty intermediate string (builder; not strictly needed for well-posedness, it avoids r.choice('') in a later replace; 22 per 14,000 draws) - PENDING LEAD REVIEW (minor)",
    "C1.euclid_gcd_traced_f3": "trace-conditioned, not on the answer: equal operands and fewer than max(4, 3 + L // 2) Euclid rounds; rounds >= 4 is needed for the rsum shape's R range, the higher minimum at L >= 4 is a difficulty condition; 2.0 retries per item - PENDING LEAD REVIEW (R-13 wording)",
    "C1.shared_lists_f3": "structural, not on the answer: an alias statement of a name to itself",
    "C1.circle_elimination_r2": "structural, not on the answer: fewer than 4 live flags (never fired in 14,000 draws)",
}
out = {"audit": "final C1 re-measurement after fix 4 (independent auditor, Claude Opus 5.5); Astra review: NOT_PERFORMED; not human approval",
       "worktree_commit": "7cd0ac5a (C1 code unchanged from the uncommitted state read at 22:11, before my draws)",
       "seeds": {"draw_keys_rules_levels": 9311, "battery": 9323, "reproducibility": 9337, "capacity_per_level": 9341, "capacity_shared_levels": 9343, "trial": 1},
       "bound": 0.15, "lineages": {}, "clusters": {}}
kt = keys["per_lineage_level"]
for cl, ms in MEMBERS.items():
    for lid in ms:
        kk = {k: v for k, v in kt.items() if k.startswith(lid + "|")}
        tot = Counter()
        for v in kk.values():
            tot.update(v)
        p = pool[lid]
        levs = lev[lid]
        rs = Counter()
        for lv, x in meta["retry_reasons"][lid].items():
            rs.update(x)
        caprows = [r for r in cap["rows"] if r["lid"] == lid]
        sh = {r["G"]: r["pass"] for r in capsh["jobs"] if r["lid"] == lid}
        rec = {
            "cluster": cl, "variant": cl in VARIANTS,
            "keys": {"items": tot["n"], "per_level_min": min(v["n"] for v in kk.values()), "problems": {k: v for k, v in tot.items() if k != "n"}},
            "pooled_strict_max": {"excess": p["strict_max"][0], "level": p["strict_max"][1], "rule": p["strict_max"][2]},
            "pooled_implementer_reading_max": {"excess": p["implementer_reading_max"][0], "level": p["implementer_reading_max"][1], "rule": p["implementer_reading_max"][2]},
            "pooled_with_partial_trace_max": {"excess": p["with_partial_trace_max"][0], "level": p["with_partial_trace_max"][1], "rule": p["with_partial_trace_max"][2]},
            "a3_mutation_artefact_max": p["a3_mutation_artefact_max"], "in_shape_max": p["in_shape_max"],
            "verdict_R31_counted_rules": p["verdict_strict"],
            "would_drop_if_partial_trace_counted": p["would_drop_if_partial_trace_counted"],
            "r19": R19.get(lid, "no reject or redraw of its own; the shared finish never fired in 14,000 draws"),
            "retries_per_14000": dict(rs),
            "levels": {"min_distinct_share": min(v["distinct_share"] for v in levs["levels"].values()),
                       "max_cross_level_repeat_share": max(v["cross_level_repeat_share"] for v in levs["levels"].values()),
                       "steps_rising": sum(1 for v in levs["steps"].values() if v["RISES"]), "steps_not_distinct": [k for k, v in levs["steps"].items() if v["NOT_DISTINCT"]],
                       "param_feature": levs["param_feature"], "steps_param_not_rising": [k for k, v in levs["steps"].items() if not v["param_feature_rises"]],
                       "steps_rising_only_in_max_literal": [k for k, v in levs["steps"].items() if v["rises_in"] == ["max_literal"]]},
            "capacity": {"per_level_alone_min_supplied": min(r["supplied"] for r in caprows), "G9_27680": all(r["G9_pass_alone"] for r in caprows),
                         "G8_31000": all(r["G8_pass_alone"] for r in caprows), "G7_35300": all(r["G7_pass_alone"] for r in caprows),
                         "shared_taken_all_levels": {f"G{g}": v for g, v in sorted(sh.items())},
                         "max_attempts_per_item_at_35300": round(max((r["G7_attempt_at_demand"] or 0) / 35300 for r in caprows), 3)},
        }
        if lid in cf_mine:
            rec["closed_form_search"] = {"mine_gen9311": cf_mine[lid]["per_level"], "implementer_gen72": cf_impl[lid]["per_level"]}
        out["lineages"][lid] = rec
stay = [l for l, r in out["lineages"].items() if r["verdict_R31_counted_rules"] == "STAYS"]
out["result_R31_counted_rules"] = {"lineages": sorted(stay), "n_lineages": len(stay),
                                   "clusters": sorted(c for c, ms in MEMBERS.items() if any(m in stay for m in ms)),
                                   "n_clusters": sum(1 for c, ms in MEMBERS.items() if any(m in stay for m in ms)),
                                   "n_clusters_without_variants": sum(1 for c, ms in MEMBERS.items() if c not in VARIANTS and any(m in stay for m in ms))}
def scen(drop):
    s = [l for l in stay if l not in drop]
    c = [cl for cl, ms in MEMBERS.items() if any(m in s for m in ms)]
    return {"dropped": sorted(drop), "n_lineages": len(s), "n_clusters": len(c), "n_clusters_without_variants": len([x for x in c if x not in VARIANTS]), "clusters_lost": sorted(set(MEMBERS) - set(c))}
mdrop = [l for l, r in out["lineages"].items() if r["would_drop_if_partial_trace_counted"]]
out["scenarios"] = {"partial_trace_counted": scen(mdrop), "NEW_sieve_closed_form_counted": scen(["C1.sieve_marking_f4"]),
                    "both": scen(mdrop + ["C1.sieve_marking_f4"])}
out["capacity_note"] = "per level alone: every lineage-level supplied 35,300 text-distinct items within the draw_items budget; with one shared taken over the 7 levels (as generate_pool shares it within a pool) see shared_taken_all_levels; 12,700 texts were drawn at two levels of the same lineage, none across lineages"
out["keys_totals"] = keys["totals"]
out["keys_interpreters"] = keys["interpreters"]
out["consistency"] = {k: v for k, v in cons.items() if k != "my_current_set"}
json.dump(out, open(outp, "w"), indent=1, sort_keys=True)
print(json.dumps({"result": out["result_R31_counted_rules"]["n_lineages"], "clusters": out["result_R31_counted_rules"]["n_clusters"], "wo_var": out["result_R31_counted_rules"]["n_clusters_without_variants"], "scenarios": out["scenarios"], "keys": keys["totals"]}, indent=1))
