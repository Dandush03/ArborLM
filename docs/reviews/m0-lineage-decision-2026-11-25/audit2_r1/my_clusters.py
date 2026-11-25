# ruff: noqa
"""Auditor's own strict cluster map for the 43 registered R1 lineages and the partition readings.
Written BEFORE reading lineages_r1_clusters.py, NOTES_LINEAGE_REPAIR.md or manifest notes.
Uses studies.m0.core.stream only to reproduce the registered shuffle rule of core.family_partition."""
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/m0_lineage_audit2_r1_20261125")
from registry import registered  # noqa: E402
from studies.m0.core import stream  # noqa: E402

P = "R1."
# Primary strict merges (lead ruling: general algorithm is the procedure; number system, constraint mix,
# final question, names, order, negation, surface frame are parameters).
PRIMARY = [
    ("order_compare", "road_reachability", "directed reachability / transitive closure, read 3- or 2-valued"),
    ("order_compare", "categories_follow_r2", "closure of a positive relation (+ lifted negative pairs), three-valued; constraint mix is a parameter"),
    ("categories_follow_r2", "equivalence_classes_r2", "closure of a positive relation + lifting of negative pairs, three-valued (symmetric vs asymmetric relation = parameter)"),
    ("order_extreme", "order_tournament_wins", "tally losses/wins per element of a pairwise relation, take the extremum"),
    ("order_extreme", "topological_order_r2", "topological sort (repeated source selection) read at a position; chain vs DAG, tie-break and asked position are parameters"),
    ("kinship_ancestor_r3", "kinship_cousins", "follow parent pointers upward a fixed number of steps"),
    ("kinship_ancestor_r3", "categories_default_exceptions_r3", "walk up a parent chain to the first node with a property"),
    ("knights_knaves", "one_culprit", "enumerate hypotheses, evaluate statements, keep the consistent one"),
    ("seating_row", "pet_owners", "permutation/assignment CSP by elimination"),
    ("event_timeline", "temporal_weekday_shift", "potentials on a tree of signed offsets (Z vs Z mod 7)"),
    ("event_timeline", "spatial_relative_directions", "potentials on a tree of offsets (Z vs Z^2) then extremum"),
    ("event_timeline", "equivalence_exchange_rates", "potentials on a tree of ratios (Q* = Z via log) then extremum"),
    ("attribute_rule", "conditional_decision_tree", "evaluate a propositional expression tree under a given assignment"),
    ("attribute_rule", "minimax_tree", "bottom-up evaluation of an AND/OR = MAX/MIN expression tree; number system is a parameter (NEW)"),
    ("compass_turns", "boolean_lights_r2", "fold a sequence of group elements into one accumulator (Z4 vs Z2)"),
    ("containers_queue_line_r2", "elimination_josephus", "simulate a circular queue under rotate-front-to-back and remove-front; Josephus = fixed pattern (rotate^(k-1), serve). Introduced by the r2 front_to_back op (NEW)"),
]
# Borderline merges: counted only in the strictest bound.
BORDER = [
    ("knights_knaves", "seating_row", "generate-and-test over a finite hypothesis space (Boolean assignments vs permutations)"),
    ("temporal_critical_path", "graph_shortest_route_r2", "optimal path weight by relaxation/DP (max on a DAG vs min on an undirected graph)"),
    ("mst_cost", "graph_shortest_route_r2", "Prim = Dijkstra with a different key"),
    ("activity_selection", "mst_cost", "sort by a key, greedily accept items compatible with the accepted set"),
    ("instant_runoff_r2", "order_tournament_wins", "tally a relation and take the extremum, iterated with elimination"),
    ("nim_xor", "boolean_lights_r2", "XOR / parity fold (Bouton's theorem maps the game to it)"),
    ("graph_bipartite", "equivalence_classes_r2", "propagation of same/different constraints (parity union-find)"),
    ("spatial_grid_walk_r2", "compass_turns", "fold a sequence of moves into a position/heading state"),
    ("temporal_critical_path", "topological_order_r2", "process a prerequisite DAG in topological order"),
    ("conditional_chain", "knights_knaves", "entailment by enumerating assignments (the generator itself verifies by brute force)"),
    ("tracking_accounts", "swap_tracking", "multi-register transfer simulation, read one register / extremum"),
    ("instant_runoff_r2", "conditional_threshold_rule_r3", "weighted vote tally"),
    ("kinship_descendants_r3", "order_tournament_wins", "count per element, argmax (aggregated over a tree)"),
]


def components(ids, edges):
    parent = {i: i for i in ids}

    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, _ in edges:
        parent[f(P + a)] = f(P + b)
    comp = {}
    for i in ids:
        comp.setdefault(f(i), []).append(i)
    return sorted((sorted(v) for v in comp.values()), key=lambda v: v[0])


def split_keys(keys, label):
    ks = sorted(keys)
    r = stream(400004, "family-partition", label)
    sh = ks[:]
    r.shuffle(sh)
    half = len(sh) // 2
    return {k: ("A" if i < half else "B") for i, k in enumerate(sh)}


def report(name, ids, fam, comps):
    print(f"\n== {name}: {len(comps)} clusters")
    for c in comps:
        if len(c) > 1:
            print("  ", " + ".join(x[3:] for x in c), "| families:", sorted({fam[x] for x in c}))
    # literal reading: split the 22 families
    lit = split_keys({fam[i] for i in ids}, "R1")
    def per_part(pmap_lineage):
        out = {"A": 0, "B": 0, "straddle": 0}
        strad = []
        for c in comps:
            ps = {pmap_lineage[x] for x in c}
            if len(ps) == 2:
                out["straddle"] += 1
                strad.append([(x[3:], pmap_lineage[x]) for x in c])
            else:
                out[ps.pop()] += 1
        return out, strad
    pm = {i: lit[fam[i]] for i in ids}
    o, s = per_part(pm)
    nl = {"A": sum(1 for i in ids if pm[i] == "A"), "B": sum(1 for i in ids if pm[i] == "B")}
    print(f"  [literal: 22 families, label 'R1'] families A={sorted(k for k,v in lit.items() if v=='A')}")
    print(f"     lineages A={nl['A']} B={nl['B']}; clusters wholly A={o['A']} wholly B={o['B']} straddling={o['straddle']}")
    for x in s:
        print("     straddle:", x)
    # family closure reading: families joined by a cluster form one key
    fparent = {f: f for f in set(fam.values())}
    def ff(a):
        while fparent[a] != a:
            a = fparent[a]
        return a
    for c in comps:
        fs = sorted({fam[x] for x in c})
        for f2 in fs[1:]:
            fparent[ff(f2)] = ff(fs[0])
    keys = {}
    for f in fparent:
        keys.setdefault(ff(f), []).append(f)
    keyname = {ff(f): "+".join(sorted(keys[ff(f)])) for f in fparent}
    ks = sorted(set(keyname.values()))
    sk = split_keys(ks, "R1")
    pm2 = {i: sk[keyname[ff(fam[i])]] for i in ids}
    o2, s2 = per_part(pm2)
    nl2 = {"A": sum(1 for i in ids if pm2[i] == "A"), "B": sum(1 for i in ids if pm2[i] == "B")}
    print(f"  [family-closure keys ({len(ks)} keys), shuffled with the registered rule] A keys={sorted(k for k in ks if sk[k]=='A')}")
    print(f"     B keys={sorted(k for k in ks if sk[k]=='B')}")
    print(f"     lineages A={nl2['A']} B={nl2['B']}; clusters A={o2['A']} B={o2['B']} straddling={o2['straddle']}")
    # cluster reading: shuffle the clusters themselves
    cname = {x: c[0] for c in comps for x in c}
    sc = split_keys([c[0] for c in comps], "R1")
    pm3 = {i: sc[cname[i]] for i in ids}
    o3, _ = per_part(pm3)
    nl3 = {"A": sum(1 for i in ids if pm3[i] == "A"), "B": sum(1 for i in ids if pm3[i] == "B")}
    print(f"  [cluster keys shuffled with the registered rule] clusters A={o3['A']} B={o3['B']}; lineages A={nl3['A']} B={nl3['B']}")
    print("     A:", sorted(c[0][3:] for c in comps if sc[c[0]] == "A"))
    # literal split then drop straddling lineages of the minority side? report only: clusters by majority
    return lit


if __name__ == "__main__":
    reg = registered()
    ids = sorted(reg)
    fam = {i: reg[i].family for i in ids}
    for a, b, _ in PRIMARY + BORDER:
        assert P + a in reg and P + b in reg, (a, b)
    report("PRIMARY strict", ids, fam, components(ids, PRIMARY))
    report("STRICTEST (primary + borderline)", ids, fam, components(ids, PRIMARY + BORDER))
    report("LENIENT (identical algorithm and data structure only)", ids, fam, components(ids, PRIMARY[:1]))
