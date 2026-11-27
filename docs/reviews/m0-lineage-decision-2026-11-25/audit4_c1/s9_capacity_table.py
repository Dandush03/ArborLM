# ruff: noqa
"""Audit 4 (C1), step 9: capacity table from s6_capacity.py output (hash sets per cell). Readings:
 (a) K1 per CLUSTER (union of member lineages' K1 hashes) on MY strict map;  (b) K1 per LINEAGE;  (c) K2 per lineage and per cluster.
Demand per cluster-level (R-10, R-11): 10 * (ceil(4000/G) + ceil(20000/G) + 100), all seven levels. A count marked * stopped at the draw budget
(lower bound); a count that reached the run's target is exactly the target (so it passes any demand <= target).
Usage: python3 s9_capacity_table.py CAP_DIR
"""
import gzip, json, math, os, sys

MAP = {  # my strict map (b0 section 6 plus the predecessor's B7 and B8 merges, adopted after reading the implementer's map; see AUDIT4_C1.md)
    "bfs": ["bfs_queue"], "union_find": ["union_find_links_f3"], "binary_search": ["binary_search_f3"],
    "stack_B8": ["bracket_matching_f3", "postfix_evaluation"], "bubble": ["bubble_pass"], "partition": ["partition_pass_f3"],
    "interp_B7": ["bytecode_loop_f3", "turtle_walk_f3"], "cellular": ["cellular_update_f3"], "circle": ["circle_elimination_r2"],
    "dp_tables_B4": ["coin_change_table_f3", "grid_path_table", "string_pair_table"], "euclid_B5": ["euclid_gcd_traced_f3", "cond_chain_f3"],
    "digit_peel": ["digit_peel_f3"], "recurrence_B6": ["fib_like_f3", "fib_shapes_recursive_f3", "recursive_calls_r2"],
    "functions_B2": ["func_branch", "func_compose_f3"], "accumulate_B1": ["loop_sum", "list_build_f3", "nested_pairs_f3", "string_build_f3"],
    "majority": ["majority_vote_scan_f3"], "merge": ["merge_two_sorted_f3"], "mirror": ["mirror_pointers"], "run_length": ["run_length_scan"],
    "sieve": ["sieve_marking_f3"], "shared_lists": ["shared_lists_f3"], "seq_expr_B3": ["slices", "string_methods_f3"], "while": ["while_counter_f3"],
    "VARIANT_counter_list_f3": ["counter_list_f3"], "VARIANT_fast_power_f3": ["fast_power_f3"],
}


def demand(g):
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def main():
    cd = sys.argv[1]
    summ = json.load(open(os.path.join(cd, "summary.json")))
    rows, target, budget = summ["rows"], summ["target"], summ["budget"]
    print(f"run target {target}, budget {budget}, seed {summ['seed']}; demands: G=12 {demand(12)}, G=11 {demand(11)}, G=10 {demand(10)}")
    sets = {}
    for lid in rows:
        for lv in range(7):
            d = json.load(gzip.open(os.path.join(cd, f"{lid.replace('C1.', '')}_L{lv}.json.gz"), "rt"))
            sets[(lid.replace("C1.", ""), lv)] = (set(d["k1"]), set(d["k2"]))
    out = {"lineage": {}, "cluster": {}}
    print("\n(b) per lineage K1 (and K1old, K2): cells below each demand")
    for g in (12, 11, 10):
        need = demand(g)
        failb = [(lid, lv, r["K1"], "*" if r["capped_by_budget"] else "") for lid, per in rows.items() for lv, r in ((int(k), v) for k, v in per.items()) if r["K1"] < need]
        print(f"  G={g} need {need}: {len(failb)} of {len(rows) * 7} lineage-levels below need: " + ", ".join(f"{a.replace('C1.', '')} L{b} {c}{d}" for a, b, c, d in sorted(failb)))
    print("\n(a) per cluster K1 union, (c) per cluster K2 union, my map")
    for g in (12, 11, 10):
        need = demand(g)
        fa, fc = [], []
        for cl, mem in MAP.items():
            for lv in range(7):
                k1 = set().union(*(sets[(m, lv)][0] for m in mem))
                k2 = set().union(*(sets[(m, lv)][1] for m in mem))
                if len(k1) < need:
                    fa.append(f"{cl} L{lv} {len(k1)}")
                if len(k2) < need:
                    fc.append((cl, lv, len(k2)))
                out["cluster"][f"{cl}|L{lv}"] = {"K1": len(k1), "K2": len(k2)}
        print(f"  G={g} need {need}: (a) {len(fa)} of {len(MAP) * 7} cluster-levels below: {', '.join(fa)}")
        print(f"  G={g} need {need}: (c) {len(fc)} of {len(MAP) * 7} cluster-levels below")
    print("\n(c) K2 per cluster and level (min over levels shown first):")
    for cl, mem in MAP.items():
        v = [out["cluster"][f"{cl}|L{lv}"]["K2"] for lv in range(7)]
        print(f"  {cl:26s} min {min(v):6d}  " + " ".join(f"{x:6d}" for x in v))
    print("\nK1 vs K1old (predecessor keep list incl. 'count'), per lineage-level where they differ by > 5 %:")
    for lid, per in sorted(rows.items()):
        for lv in range(7):
            r = per[str(lv)]
            if r["K1old"] > 1.05 * r["K1"]:
                print(f"  {lid.replace('C1.', ''):28s} L{lv} K1 {r['K1']:6d}{'*' if r['capped_by_budget'] else ' '} K1old {r['K1old']:6d} draws {r['draws']}")
    json.dump(out, open(os.path.join(cd, "s9_table.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
