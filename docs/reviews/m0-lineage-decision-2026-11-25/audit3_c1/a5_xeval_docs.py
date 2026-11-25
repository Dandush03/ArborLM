# ruff: noqa
"""Audit 3 (C1), step 5: print docstrings / first lines of the R1, R2, M1 generator functions named as cross-evaluation candidates (parse only, no import).
python a5_xeval_docs.py <studies/m0 dir>"""
import ast, glob, os, sys

D = sys.argv[1]
WANT = {
    "R2": ["binary_search_trace", "bracket_match", "cellular_automaton", "coin_change_min", "gcd_euclid", "lcs_length", "max_subarray_sum", "modular_power",
           "permutation_power", "run_length", "palindrome_check", "stack_machine", "to_base", "from_base", "sort_list", "kth_smallest", "multiples_between", "digit_root",
           "list_ops", "count_divisible", "count_letter", "string_rewrite", "min_heap_ops", "expression_eval", "subtraction_game", "grid_sum", "lis_length", "hash_probe", "cache_eviction"],
    "M1": ["gcd_lcm", "change_ways", "min_cost_packs", "recurrence_iterate", "arithmetic_series", "mode_tally", "digit_puzzle", "last_digit_power", "median_list"],
    "R1": ["elimination_josephus", "compass_turns", "spatial_grid_walk", "road_reachability", "graph_shortest_route", "equivalence_classes", "order_extreme", "swap_tracking",
           "containers_stack_piles", "containers_queue_line", "boolean_lights", "tracking_accounts", "topological_order", "order_tournament_wins"],
}
for ev, names in WANT.items():
    files = sorted(glob.glob(os.path.join(D, f"lineages_{ev.lower()}*.py")))
    for nm in names:
        hits = []
        for fn in files:
            t = ast.parse(open(fn).read())
            for n in ast.walk(t):
                if isinstance(n, ast.FunctionDef) and (n.name == nm or n.name.startswith(nm + "_r") or n.name.startswith(nm + "_")):
                    doc = ast.get_docstring(n) or ""
                    hits.append(f"{os.path.basename(fn)}:{n.name}: {doc.replace(chr(10), ' ')[:300]}")
        print(f"{ev}.{nm}:")
        for h in hits or ["  (not found)"]:
            print("   ", h)
