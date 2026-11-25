# ruff: noqa
"""Recompute the author's strict cluster count and part split with my own code (author's merge list transcribed by hand
from lineages_r1_clusters.py STRICT_MERGES, base ids mapped to registered ids), then cross-check against the author's
function output. Also: per-part cluster counts under my map for every reading."""
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/m0_lineage_audit2_r1_20261125")
from registry import registered  # noqa: E402
from my_clusters import components, report, PRIMARY  # noqa: E402

AUTHOR_GROUPS = [
    ("order_compare", "road_reachability"),
    ("event_timeline", "temporal_weekday_shift", "spatial_relative_directions", "equivalence_exchange_rates"),
    ("kinship_ancestor_r3", "kinship_cousins", "categories_default_exceptions_r3"),
    ("knights_knaves", "one_culprit"),
    ("seating_row", "pet_owners"),
    ("attribute_rule", "conditional_decision_tree"),
    ("compass_turns", "boolean_lights_r2"),
    ("categories_follow_r2", "equivalence_classes_r2"),
    ("order_extreme", "order_tournament_wins"),
]
edges = [(g[0], x, "author") for g in AUTHOR_GROUPS for x in g[1:]]

reg = registered()
ids = sorted(reg)
fam = {i: reg[i].family for i in ids}
comps = components(ids, edges)
report("AUTHOR map (own code)", ids, fam, comps)

from studies.m0 import lineages_r1_clusters as C  # read-only cross-check of the author's own function
cp = C.clusters_per_part()
print("\nauthor function clusters_per_part: A", len(cp["A"]), "B", len(cp["B"]))
print("author partition keys:", C.partition())
print("author registered count", len(C.registered_lineages()), "clusters", len(C.cluster_table()))
