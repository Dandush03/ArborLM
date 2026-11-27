# ruff: noqa
# ruff: noqa
"""Auditor's pairwise judgement over all 595 pairs of the 35 R1 lineages.

The judgement is encoded explicitly (merge lists and near-miss lists written by
the auditor before reading the author's notes); every pair not listed is
"distinct". Clusters are the connected components of the merge graph.
Usage: python pairs.py <out csv>
"""
import itertools
import sys

OLD = ["order_extreme", "order_compare", "kinship_ancestor", "kinship_cousins", "categories_follow",
       "conditional_chain", "knights_knaves", "seating_row", "pet_owners", "event_timeline",
       "swap_tracking", "road_reachability", "one_culprit", "attribute_rule", "compass_turns"]
NEW = ["boolean_lights", "categories_default_exceptions", "conditional_decision_tree", "conditional_threshold_rule",
       "containers_queue_line", "containers_stack_piles", "elimination_bracket", "elimination_josephus",
       "equivalence_classes", "equivalence_exchange_rates", "graph_bipartite", "graph_shortest_route",
       "kinship_descendants", "order_tournament_wins", "spatial_grid_walk", "spatial_relative_directions",
       "temporal_critical_path", "temporal_interval_overlap", "temporal_weekday_shift", "tracking_accounts"]
ALL = OLD + NEW
assert len(ALL) == 35 and len(set(ALL)) == 35

# merges under BOTH readings
BOTH = {
    ("order_compare", "road_reachability"): "directed reachability (DFS/closure) in a digraph; ynu adds the reverse query (order change), DAG vs cyclic is a parameter",
}
# merges under the STRICT reading only (algorithmic schema; value domain / constraint mix / read-out treated as parameters)
STRICT = {
    ("event_timeline", "temporal_weekday_shift"): "same template ('X took place k days after/before Y') over a random tree; propagate additive offsets; read-out argmin/argmax vs one value mod 7",
    ("event_timeline", "spatial_relative_directions"): "propagate additive offsets over a tree of relative facts (Z vs Z^2), then an extremum (coordinate vs L1 distance)",
    ("event_timeline", "equivalence_exchange_rates"): "propagate potentials over a tree of pairwise relations, then argmax; multiplicative (Q*) is the additive case under log",
    ("temporal_weekday_shift", "spatial_relative_directions"): "as above (tree offset propagation)",
    ("temporal_weekday_shift", "equivalence_exchange_rates"): "as above (tree potential propagation)",
    ("spatial_relative_directions", "equivalence_exchange_rates"): "as above (tree potential propagation, argmax)",
    ("kinship_ancestor", "kinship_cousins"): "chase parent pointers k steps; cousins = compare 2-step and 1-step ancestors of two nodes",
    ("kinship_ancestor", "categories_default_exceptions"): "walk up a linked parent chain from a start node (fixed k steps vs until first node carrying a rule for the verb)",
    ("kinship_cousins", "categories_default_exceptions"): "transitively via the pointer-chasing cluster",
    ("knights_knaves", "one_culprit"): "enumerate hypotheses (assignments / culprits), evaluate every statement under each, keep the one meeting the truth constraint",
    ("seating_row", "pet_owners"): "find the unique permutation satisfying constraints by elimination over permutations (positional vs unary membership constraints)",
    ("attribute_rule", "conditional_decision_tree"): "evaluate a propositional structure (formula / nested if-else) under a complete assignment of atomic facts",
    ("compass_turns", "boolean_lights"): "fold a command sequence into a cyclic-group accumulator (Z4 heading / Z2 parity of the asked lamp), ignoring irrelevant steps",
    ("categories_follow", "equivalence_classes"): "close a positive relation (subset / equality), lift a negative relation (no / different) through the closure, answer yes/no/cbd",
    ("order_extreme", "order_tournament_wins"): "tally per-person degree of a stated pairwise win/taller relation, take the extremum (in-degree 0 vs max out-degree)",
}
NEAR = {
    ("order_compare", "categories_follow"): "categories 'all' queries are reachability, but 'none'/'some' need disjointness lifting: superset procedure, kept apart",
    ("road_reachability", "graph_bipartite"): "both graph traversals; property differs (reach vs odd-cycle/parity)",
    ("equivalence_classes", "graph_bipartite"): "union-find with equality vs parity propagation with conflict detection",
    ("order_compare", "equivalence_classes"): "3-valued; 'no' from reverse reachability vs from a negative edge between components",
    ("graph_shortest_route", "temporal_critical_path"): "min-plus over a general weighted graph (Dijkstra) vs max-plus DP over a DAG",
    ("graph_shortest_route", "road_reachability"): "weights and minimisation vs plain reachability",
    ("event_timeline", "temporal_critical_path"): "additive offsets on a tree vs max over several predecessors on a DAG",
    ("temporal_weekday_shift", "compass_turns"): "both modular sums (mod 7 / mod 4) but tree-path finding vs linear fold",
    ("spatial_grid_walk", "compass_turns"): "sequential movement; position with walls vs heading only",
    ("swap_tracking", "tracking_accounts"): "registers indexed by people; permutation vs additive transfers with argmax",
    ("containers_queue_line", "containers_stack_piles"): "list-container simulation; FIFO deque vs three LIFO stacks with reversal",
    ("containers_queue_line", "elimination_josephus"): "Josephus is a rotating queue, but the operations are implied by a rule, not listed",
    ("elimination_bracket", "order_tournament_wins"): "tournament surface; pairwise max rounds vs win tally",
    ("kinship_descendants", "order_tournament_wins"): "count-and-argmax; recursive subtree aggregation vs flat tally",
    ("kinship_descendants", "order_extreme"): "intended: subtree aggregation; but 132/140 fixture answers are the unique parentless person (in-degree 0), the order_extreme shortcut. Kept apart on intended procedure; quality defect reported",
    ("kinship_descendants", "kinship_ancestor"): "same tree, downward aggregation vs upward chase",
    ("categories_follow", "conditional_chain"): "syllogisms are monadic Horn inference, but the query is an entailment with existential 'some'; kept apart",
    ("conditional_threshold_rule", "attribute_rule"): "rule evaluation, but weighted sum vs threshold arithmetic",
    ("conditional_threshold_rule", "conditional_decision_tree"): "rule evaluation, arithmetic vs tree descent",
    ("categories_default_exceptions", "categories_follow"): "same 'Every A is a B' surface; first-rule lookup on a chain vs closure + disjointness",
    ("temporal_interval_overlap", "temporal_critical_path"): "both day arithmetic; interval intersection vs DAG DP",
    ("one_culprit", "pet_owners"): "hypothesis filtering vs bijection elimination",
    ("swap_tracking", "containers_stack_piles"): "object tracking through moves; permutation vs stacks",
}


def key(a, b):
    return tuple(sorted((a, b)))


def norm(d):
    out = {}
    for (a, b), v in d.items():
        assert a in ALL and b in ALL, (a, b)
        out[key(a, b)] = v
    return out


BOTH, STRICT, NEAR = norm(BOTH), norm(STRICT), norm(NEAR)
assert not (set(BOTH) & set(STRICT)) and not (set(NEAR) & (set(BOTH) | set(STRICT)))


def clusters(edges, nodes):
    parent = {n: n for n in nodes}
    def f(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for a, b in edges:
        if a in parent and b in parent:
            parent[f(a)] = f(b)
    comps = {}
    for n in nodes:
        comps.setdefault(f(n), []).append(n)
    return sorted(sorted(c) for c in comps.values())


rows = []
for a, b in itertools.combinations(ALL, 2):
    k = key(a, b)
    if k in BOTH:
        st, why = "merge(strict+lenient)", BOTH[k]
    elif k in STRICT:
        st, why = "merge(strict only)", STRICT[k]
    elif k in NEAR:
        st, why = "near-miss kept apart", NEAR[k]
    else:
        st, why = "distinct", ""
    rows.append((k[0], k[1], st, why))
assert len(rows) == 595
with open(sys.argv[1], "w") as fh:
    fh.write("a,b,status,reason\n")
    for r in rows:
        fh.write(",".join('"' + x.replace('"', "'") + '"' for x in r) + "\n")

for label, edges in (("strict", list(BOTH) + list(STRICT)), ("lenient", list(BOTH))):
    for name, nodes in (("old", OLD), ("new", NEW), ("overall", ALL)):
        cs = clusters(edges, nodes)
        print(f"{label:8s} {name:8s} lineages={len(nodes):2d} clusters={len(cs)}")
    print(f"  {label} multi-member clusters (overall):")
    for c in clusters(edges, ALL):
        if len(c) > 1:
            print("   ", " + ".join(c))
print("pairs:", len(rows), "merge both:", len(BOTH), "strict-only:", len(STRICT), "near-miss:", len(NEAR))
