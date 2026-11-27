# ruff: noqa
"""Audit 3 (R1): the auditor's own strict cluster map (written from reading the 43 generators), compared with
lineages_r1_clusters_v2 (imported ONLY to compare), and the cluster-keys split of manifests/r1_rev4_parts.md re-read
under this map. Rule: two shapes are one cluster when the same algorithm solves both up to renaming, presentation and
parameter values (operator, number system, hypothesis domain size, asked position are parameters).
"""
import sys
sys.path.insert(0, ".")

MINE = {
    "closure_three_valued": ["road_reachability", "order_compare_r4", "categories_follow_r4", "equivalence_classes_r2"],
    "potential_over_tree": ["event_timeline", "temporal_weekday_shift", "spatial_relative_directions_r4", "equivalence_exchange_rates"],
    "pointer_chasing": ["kinship_ancestor_r4", "kinship_cousins", "categories_default_exceptions_r4"],
    # boolean-assignment enumeration against clauses: knights (speaker <-> content), culprit (one-hot assignment, count of true statements),
    # conditional_chain (facts + material implications; the generator itself decides it by enumerating all 2^n assignments)
    "assignment_enumeration": ["knights_knaves", "one_culprit", "conditional_chain"],
    "permutation_elimination": ["seating_row", "pet_owners"],
    # bottom-up evaluation of a tree with a binary/n-ary operator: AND/OR, if-then-else, MIN/MAX, and the knockout bracket (operator = head-to-head table)
    "tree_evaluation": ["attribute_rule", "conditional_decision_tree_r4", "minimax_tree_r4", "elimination_bracket_r4"],
    "cyclic_accumulator_fold": ["compass_turns", "boolean_lights_r4"],
    "source_selection_degree": ["order_extreme", "order_tournament_wins", "topological_order_r4"],
    "circular_queue": ["containers_queue_line_r2", "elimination_josephus"],
}
SINGLE = ["activity_selection_r4", "conditional_threshold_rule_r4", "containers_stack_piles_r4", "graph_bipartite", "graph_shortest_route_r4", "instant_runoff_r4",
          "kinship_descendants_r4", "mst_cost_r4", "nim_xor_r4", "spatial_grid_walk_r2", "stable_matching_r4", "swap_tracking", "temporal_critical_path_r4",
          "temporal_interval_overlap", "tracking_accounts", "venn_counting_r4"]

from studies.m0.lineages_r1_clusters_v2 import registered_v2, cluster_of_v2, partition_readings

reg = sorted(x.id for x in registered_v2())
mine = {}
for c, ms in MINE.items():
    for m in ms:
        mine["R1." + m] = c
for m in SINGLE:
    mine["R1." + m] = m
assert sorted(mine) == reg, (set(reg) ^ set(mine))
print("shapes", len(reg), "my clusters", len(set(mine.values())), "map v2 clusters", len({cluster_of_v2(x) for x in reg}))
# disagreements: pairs together in one map and apart in the other
import itertools
for a, b in itertools.combinations(reg, 2):
    m1 = mine[a] == mine[b]; m2 = cluster_of_v2(a) == cluster_of_v2(b)
    if m1 != m2:
        print("DISAGREE", a, b, "mine:", "same" if m1 else "apart", "| v2:", "same" if m2 else "apart")
# the cluster-keys split as tabulated (by v2 cluster), read under my clusters
ck = partition_readings()["cluster_keys"]
for c in sorted(set(mine.values())):
    parts = {ck[x] for x in reg if mine[x] == c}
    if len(parts) > 1:
        print("MY CLUSTER SPANS BOTH PARTS under the tabulated cluster_keys split:", c, {x: ck[x] for x in reg if mine[x] == c})
for p in "AB":
    print("part", p, "my clusters wholly in it:", len({mine[x] for x in reg if ck[x] == p} - {mine[x] for x in reg if ck[x] != p}))
