# ruff: noqa
"""Audit 4 (R1): the auditor's strict cluster map of the 37 shapes, written from the generators (imports the implementer's map only to
compare), its count, and G under the seeded cluster-key split (the split function v2._shuffle_split, seed 400004, imported read-only).
MINE: the six merge groups below (same as audit 3's, with conditional_chain kept where audit 3 put it). ALT: conditional_chain moved to the
closure group (forward chaining is exact on it; PENDING LEAD REVIEW). Borderline (not merged) listed.
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this>"""
import os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen4
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0 import lineages_r1_fix3_clusters as c3

MINE = [("order_compare", "road_reachability", "categories_follow", "equivalence_classes"),          # closure of a relation, read three-valued
        ("event_timeline", "temporal_weekday_shift", "spatial_relative_directions", "equivalence_exchange_rates"),  # potentials along a tree path
        ("kinship_ancestor", "kinship_cousins", "categories_default_exceptions"),                    # pointer chasing up a chain
        ("knights_knaves", "one_culprit", "conditional_chain"),                                      # truth assignments against clauses
        ("attribute_rule", "conditional_decision_tree", "minimax_tree", "elimination_bracket"),      # bottom-up evaluation of a tree
        ("compass_turns", "boolean_lights")]                                                         # folding commands into a cyclic accumulator
ALT = [tuple(x for x in g if x != "conditional_chain") for g in MINE]
ALT[0] = ALT[0] + ("conditional_chain",)
BORDER = [("seating_row", "knights_knaves/one_culprit"), ("tracking_accounts", "swap_tracking", "containers_queue_line", "containers_stack_piles"),
          ("spatial_grid_walk", "compass_turns"), ("temporal_critical_path", "topological_order"), ("graph_bipartite", "equivalence_classes"),
          ("kinship_descendants", "kinship_ancestor")]

def base(l): return re.sub(r"_r\d+$", "", l.split(".", 1)[1])
def table(groups, ids):
    out = defaultdict(list)
    for i in ids:
        b = base(i); k = "R1." + b
        for g in groups:
            if b in g: k = "R1." + min(g); break
        out[k].append(i)
    return out
ids = sorted(gen4.lineages())
theirs = {k: sorted(x.id for x in v) for k, v in c3.cluster_table_v3().items()}
for name, groups in (("MINE", MINE), ("ALT", ALT)):
    t = table(groups, ids)
    split = v2._shuffle_split(sorted(t), 400004)
    A = sorted(k for k in t if split[k] == "A"); B = sorted(k for k in t if split[k] == "B")
    same = {k: sorted(v) for k, v in t.items()} == theirs
    print(f"{name}: {len(t)} clusters; identical to the implementer's map: {same}; parts A {len(A)} / B {len(B)}; G = {min(len(A), len(B))}")
    print("   A:", [a.split('.')[1] for a in A]); print("   B:", [b.split('.')[1] for b in B])
print("borderline pairs (not merged):", BORDER)
