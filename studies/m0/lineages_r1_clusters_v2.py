# ruff: noqa: E501
"""R1 strict cluster map, version 2, and the set of shapes it would register (lead rulings R-1, R-2, R-6, R-9 of docs/reviews/m0-lineage-decision-2026-11-25/LEAD_RULINGS_2.md).

``lineages_r1_clusters`` (version 1, the earlier author's map: 31 clusters) is kept unchanged. Ruling R-2 adopts the second auditor's strict map (AUDIT_M0_R1_2.md section 1,
``my_clusters.py`` PRIMARY): the nine merge groups of the first audit, with four more merges, 27 strict clusters for the 43 registered lineages:

  (i)   minimax_tree joins attribute_rule / conditional_decision_tree (bottom-up evaluation of an AND/OR = MAX/MIN tree; the number system is a parameter);
  (ii)  topological_order joins order_extreme / order_tournament_wins (repeated source selection read at a position; chain versus DAG, tie-break and asked position are parameters);
  (iii) containers_queue_line joins elimination_josephus (the "front goes to the back" operation of the _r2 shape makes Josephus a fixed pattern of the same circular queue);
  (iv)  order_compare / road_reachability join categories_follow / equivalence_classes (closure of a positive relation plus lifted negative pairs, read three-valued).

Where the author of a lineage disagrees, the disagreement is written beside the map (``AUTHOR_NOTES``) and does not un-merge (R-2). The auditor's "strictest" reading (14 clusters) is listed as
``BORDERLINE`` pairs, NOT merged. Nothing here enters ``core.REGISTRY`` (R-9).
"""

from __future__ import annotations

from studies.m0 import lineages_r1_clusters as v1
from studies.m0.core import Lineage, stream
from studies.m0.lineages_r1_rev4_common import REPLACES, load_rev4

STRICT_MERGES_V2: tuple[tuple[str, ...], ...] = (
    ("R1.order_compare", "R1.road_reachability", "R1.categories_follow", "R1.equivalence_classes"),  # audit 1 merged the first two and the last two; audit 2 joins both pairs (iv)
    ("R1.event_timeline", "R1.temporal_weekday_shift", "R1.spatial_relative_directions", "R1.equivalence_exchange_rates"),  # potential propagation over a tree
    ("R1.kinship_ancestor", "R1.kinship_cousins", "R1.categories_default_exceptions"),  # pointer chasing up a chain
    ("R1.knights_knaves", "R1.one_culprit"),  # hypothesis enumeration against statements
    ("R1.seating_row", "R1.pet_owners"),  # permutation constraint elimination
    ("R1.attribute_rule", "R1.conditional_decision_tree", "R1.minimax_tree"),  # evaluating an expression tree (i)
    ("R1.compass_turns", "R1.boolean_lights"),  # folding a command list into a cyclic accumulator
    ("R1.order_extreme", "R1.order_tournament_wins", "R1.topological_order"),  # tally / repeated source selection on a pairwise relation (ii)
    ("R1.containers_queue_line", "R1.elimination_josephus"),  # simulating a circular queue (iii)
)

# Borderline pairs of the auditor's "strictest" bound (14 clusters): LISTED, NOT MERGED (ruling R-2). (id, id, the auditor's reason)
BORDERLINE: tuple[tuple[str, str, str], ...] = (
    ("R1.knights_knaves", "R1.seating_row", "generate-and-test over a finite hypothesis space (Boolean assignments versus permutations)"),
    ("R1.temporal_critical_path", "R1.graph_shortest_route", "optimal path weight by relaxation or dynamic programming (max on a DAG versus min on an undirected graph)"),
    ("R1.mst_cost", "R1.graph_shortest_route", "Prim is Dijkstra with a different key"),
    ("R1.activity_selection", "R1.mst_cost", "sort by a key, greedily accept items compatible with the accepted set"),
    ("R1.instant_runoff", "R1.order_tournament_wins", "tally a relation and take the extremum, iterated with elimination"),
    ("R1.nim_xor", "R1.boolean_lights", "XOR or parity fold (Bouton's theorem maps the game to it)"),
    ("R1.graph_bipartite", "R1.equivalence_classes", "propagation of same/different constraints (parity union-find)"),
    ("R1.spatial_grid_walk", "R1.compass_turns", "fold a sequence of moves into a position and heading state"),
    ("R1.temporal_critical_path", "R1.topological_order", "process a prerequisite DAG in topological order"),
    ("R1.conditional_chain", "R1.knights_knaves", "entailment by enumerating assignments (the generator itself verifies by brute force)"),
    ("R1.tracking_accounts", "R1.swap_tracking", "multi-register transfer simulation, read one register or an extremum"),
    ("R1.instant_runoff", "R1.conditional_threshold_rule", "weighted vote tally"),
    ("R1.kinship_descendants", "R1.order_tournament_wins", "count per element, argmax (aggregated over a tree)"),
)

# Disagreements by the authors, written beside the map; they do NOT un-merge (ruling R-2). (merge, who, reason)
AUTHOR_NOTES: tuple[tuple[str, str, str], ...] = (
    ("(i) minimax_tree with attribute_rule / conditional_decision_tree", "earlier implementer (lineages_r1_new2.py docstring)", "none recorded: the docstring lists 'minimax_tree with any other tree evaluation' among the merges an auditor may make"),
    ("(ii) topological_order with order_extreme / order_tournament_wins", "earlier implementer (NOTES_LINEAGE_REPAIR.md, pilot design rejections)", "the pilot notes rejected 'topological-order questions' as 'the same procedure as reachability' and later wrote topological_order as a priority-queue Kahn sort; the author's stated difference is the alphabetical priority rule, which audit 2 reads as a parameter"),
    ("(iii) containers_queue_line with elimination_josephus", "earlier implementer", "the 'front goes to the back' operation was added by the _r2 shape to remove a shortcut; the author did not mention the Josephus overlap. Under the rev-4 rulings the shape keeps that operation (_r2 is unchanged in this revision)"),
    ("(iv) order_compare / road_reachability with categories_follow / equivalence_classes", "audit 1 (not an author)", "audit 1 kept order_compare apart from categories_follow; audit 2 merges them under the explicit strict ruling; ruling R-2 adopts audit 2"),
)

# shapes of the 43 that this revision does not replace stay as they are. Shapes NOT REGISTERED, with the reason (filled from the rev-4 measurement; see r1_registration_plan.md)
NOT_REGISTERED_V2: dict[str, str] = {}


def cluster_of_v2(lid: str) -> str:
    b = v1.base_id(lid)
    for grp in STRICT_MERGES_V2:
        if b in grp:
            return min(grp)
    return b


def all_lineages_v2() -> list[Lineage]:
    """Every shape that exists in a file: the 85 of version 1 and the revision-4 shapes."""
    return sorted([*v1.all_r1_lineages(), *load_rev4()], key=lambda x: x.id)


def replaced_by_rev4() -> dict[str, str]:
    """registered shape id (of version 1) -> the rev4 shape that replaces it."""
    return {old: new for new, old in REPLACES.items()}


def registered_v2() -> list[Lineage]:
    """Version 1's registered shapes minus those a rev4 shape replaces, plus the rev4 shapes, minus NOT REGISTERED ones."""
    rev4 = load_rev4()  # fills REPLACES
    gone = set(REPLACES.values())
    base = [x for x in v1.registered_lineages() if x.id not in gone]
    return sorted([x for x in [*base, *rev4] if x.id not in NOT_REGISTERED_V2], key=lambda x: x.id)


def cluster_table_v2(lins: list[Lineage] | None = None) -> dict[str, list[Lineage]]:
    out: dict[str, list[Lineage]] = {}
    for lin in lins if lins is not None else registered_v2():
        out.setdefault(cluster_of_v2(lin.id), []).append(lin)
    return out


# ---------------------------------------------------------------- partition readings (ruling R-6: reported, not chosen)


def _shuffle_split(keys: list[str], seed: int = 400004, label: str = "R1") -> dict[str, str]:
    ks = sorted(keys)
    r = stream(seed, "family-partition", label)
    sh = ks[:]
    r.shuffle(sh)
    half = len(sh) // 2
    return {k: ("A" if i < half else "B") for i, k in enumerate(sh)}


def family_groups_v2(lins: list[Lineage]) -> dict[str, str]:
    """family -> group key, families joined by a strict cluster sharing one key."""
    parent = {f: f for f in sorted({x.family for x in lins})}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for members in cluster_table_v2(lins).values():
        fams = sorted({m.family for m in members})
        for f in fams[1:]:
            parent[find(f)] = find(fams[0])
    groups: dict[str, list[str]] = {}
    for f in sorted(parent):
        groups.setdefault(find(f), []).append(f)
    return {f: "+".join(sorted(fs)) for fs in groups.values() for f in fs}


def partition_readings(lins: list[Lineage] | None = None, seed: int = 400004) -> dict[str, dict[str, str]]:
    """For each reading, the part (A or B) of every registered lineage id.
    literal: ``core.family_partition``'s rule on the families as they are (a cluster may straddle);
    family_closure: families joined by a strict cluster are one key of the rule;
    cluster_keys: the clusters themselves are the keys of the rule (not the registered unit);
    literal_move_to_B: literal, then every straddling cluster moved whole to part B (the earlier author's alternative)."""
    lins = lins if lins is not None else registered_v2()
    lit = _shuffle_split(sorted({x.family for x in lins}), seed)
    out: dict[str, dict[str, str]] = {"literal": {x.id: lit[x.family] for x in lins}}
    fg = family_groups_v2(lins)
    fc = _shuffle_split(sorted(set(fg.values())), seed)
    out["family_closure"] = {x.id: fc[fg[x.family]] for x in lins}
    ct = cluster_table_v2(lins)
    ck = _shuffle_split(sorted(ct), seed)
    out["cluster_keys"] = {x.id: ck[cluster_of_v2(x.id)] for x in lins}
    mv = dict(out["literal"])
    for cid, members in ct.items():
        if len({out["literal"][m.id] for m in members}) > 1:
            for m in members:
                mv[m.id] = "B"
    out["literal_move_to_B"] = mv
    return out
