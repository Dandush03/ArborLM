# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""The R1 set after fix round 4 (the human lead's fifth decision, lead rulings R-24 to R-29): which of the 37 fix-round-3 shapes are dropped, which are repaired, which survive.

Rules (R-24, R-25): a shape is dropped (NOT REGISTERED, excluded from the map, G, fixtures and capacity runs: R-12) if any cheap or approximate rule of the union of the batteries scores more than 0.15 above (or,
as the scripts measure it, below) the base rate at any level; or if it rejects items on their answer where that is not needed for the item to be well posed; or if it has another audit-4 defect outside the
three allowed repairs (hygiene, wording, collapsed levels). Rule classes follow audit 4 (``final_table4.py``): C cheap, A approximate or partial procedure of comparable cost, both counted; M misreading of a
stated convention, listed and not counted (see ``r1_fix4_table.py``). ``AUDIT4_DROPS`` is the first stage (the audit's own numbers, ``audit4_r1/final_table_run1.txt``, applied to the bound without re-measuring);
``SECOND_STAGE_DROPS`` holds what the re-run after the repairs dropped (R-26), each with its measured value (``manifests/r1_fix4_survivors.json``). No shape is added (R-25); no strict-cluster merge is changed.
"""

from __future__ import annotations

from studies.m0 import lineages_r1_fix3_clusters as v3
from studies.m0.core import Lineage
from studies.m0.lineages_r1_fix4_common import REPLACES, load_fix4

# first stage: the shape stays out because of the audit-4 measurement (max over levels of the best counted rule's excess over the base rate) or another named audit-4 defect
AUDIT4_DROPS: dict[str, str] = {
    "R1.activity_selection_r5": "audit 4 section 4/8: round(0.75 x meetings) +0.399 (cheap rule C, level 1); not an allowed repair (R-25)",
    "R1.attribute_rule_r5": "audit 4 section 4/8: fewest negated tests +0.580 (C, level 1); also a wording defect (negation scope unstated) that the repair would not cure: the rule is above the bound",
    "R1.categories_follow_r5": "audit 4 section 3/4/8: kind + number of groups lookup +0.543 (C, level 0); the class-dependent replanting (R-19) is an answer-conditional rejection that is not needed for well-posedness (the answer is computed by the closure whatever the planting gives); No-lifting-only +0.448 (A)",
    "R1.conditional_chain_r5": "audit 4 section 4/8: a rule concluding the asked variable whose antecedent holds a stated fact +0.345 (C, level 6); the rejection 'got != want' (3.8 % of draws) is also answer-conditional",
    "R1.containers_queue_line_r5": "audit 4 section 4/8: index arithmetic +0.794 (C, level 0), created by the fix-3 rebuild",
    "R1.containers_stack_piles_r4": "audit 4 section 4/8: ignore turns +0.205 (A, level 1)",
    "R1.elimination_bracket_r5": "audit 4 section 4/8: half record then head-to-head +0.430 (A, level 1), first-round winner with most wins +0.251 (C, level 0)",
    "R1.equivalence_classes_r5": "audit 4 section 4/8: counts of 'same' and 'different' sentences +0.433 (C, level 0), BFS path with 0 or 1 different links +0.616 (A)",
    "R1.graph_bipartite_r5": "audit 4 section 4/8: odd cycle of length at most 7 +0.474 (A, level 0)",
    "R1.kinship_ancestor_r4": "audit 4 section 3/4/8: options in the child's own family tree +0.187 (A, level 0); the Retry when fewer than two people share the answer's profile (4,538 per 2,100 items) is conditional on a property of the answer and is needed only to build the matched option set, not for well-posedness (R-19: answer-conditional, R-13)",
    "R1.kinship_cousins_r5": "audit 4 section 4/8: both have a grandparent and parents differ +0.304 (C), same generation and different parents +0.444 (A)",
    "R1.kinship_descendants_r5": "audit 4 section 4/8: widest generation +0.304 (A, level 4)",
    "R1.minimax_tree_r5": "audit 4 section 4/8: first leaf / greedy best leaf +0.216 (A, level 0)",
    "R1.mst_cost_r4": "audit 4 section 4/8: nearest-neighbour path +0.191 (A, level 2)",
    "R1.nim_xor_r5": "audit 4 section 4/8: partial xor of the high bits +0.330 (A, level 3)",
    "R1.one_culprit": "audit 4 section 4/8: most accused +0.191 (C, level 6)",
    "R1.order_compare_r5": "audit 4 section 4/8: bounded search of at most 5 steps +0.454 (A, level 0), connectivity +0.33 at every level",
    "R1.road_reachability_r5": "audit 4 section 4/8: within 5 roads +0.438 (A, level 0)",
    "R1.seating_row_r5": "audit 4 section 4/8: a person with no seat clue, consistent with the ends +0.192 (C, level 6); levels 1 to 6 are one generator",
    "R1.temporal_critical_path_r5": "audit 4 section 4/8: greedy backward +0.208 (A, level 0)",
    "R1.temporal_interval_overlap_r5": "audit 4 section 4/8: the longer event lasts longer than the start gap +0.180 (C, level 4)",
    "R1.topological_order_r5": "audit 4 section 4/8: layered order +0.190 (A, level 0)",
    "R1.tracking_accounts_r5": "audit 4 section 4/8: halves taken from start balances +0.390 (A, level 0)",
}

# shapes of the set that a round-4 builder replaces (the level repair); the earlier id leaves the set, the _r6 id enters it
REPAIRED: dict[str, str] = {
    "R1.conditional_decision_tree_r6": "R1.conditional_decision_tree_r4",
    "R1.equivalence_exchange_rates_r6": "R1.equivalence_exchange_rates_r5",
    "R1.event_timeline_r6": "R1.event_timeline_r5",
    "R1.graph_shortest_route_r6": "R1.graph_shortest_route_r4",
    "R1.knights_knaves_r6": "R1.knights_knaves_r5",
    "R1.spatial_relative_directions_r6": "R1.spatial_relative_directions_r5",
    "R1.temporal_weekday_shift_r6": "R1.temporal_weekday_shift_r5",
}

# second stage: dropped by the re-run after the repairs (R-26); filled from the measured table, never repaired again
SECOND_STAGE_DROPS: dict[str, str] = {
    "R1.event_timeline_r6": "R-19 / R-25: the builder redraws when the answer is 0 (audit 4 section 3: 10 of 2,100 items for the _r5 builder; 0.3 to 0.7 % of the draws here, manifests/r1_fix4_levels.json). A zero answer ('the two events took place on the same day') is a well-posed answer, so the rejection is answer-conditional and not needed for well-posedness; removing it would be a repair outside R-25 (a) to (c), so the shape is dropped. Its rules read at most 0.145 (primary run), so only this reason drops it. PENDING LEAD REVIEW",
    "R1.spatial_relative_directions_r6": "R-19 / R-25: the builder redraws when the street distance is 0 (audit 4 section 3: 7 of 2,100 items for the _r5 builder). A distance of 0 is a well-posed answer, so the rejection is answer-conditional and not needed for well-posedness; dropped, not repaired. Its counted rules read at most 0.125 (primary run); the auditor's misreading class M read +0.548 (not counted). PENDING LEAD REVIEW",
}


def registered_v4() -> list[Lineage]:
    """The fix-round-3 set minus the first-stage drops, with each repaired shape swapped for its _r6 builder, minus the second-stage drops."""
    new = {x.id: x for x in load_fix4()}
    assert set(REPAIRED) == set(new) == set(REPLACES), "every _r6 builder has exactly one entry in REPAIRED"
    gone = {*AUDIT4_DROPS, *SECOND_STAGE_DROPS}
    out: list[Lineage] = []
    for x in v3.registered_v3():
        if x.id in AUDIT4_DROPS:
            continue
        rep = next((n for n, o in sorted(REPAIRED.items()) if o == x.id), None)
        out.append(new[rep] if rep else x)
    return sorted((x for x in out if x.id not in gone), key=lambda x: x.id)


def candidates_v4() -> list[Lineage]:
    """Everything that entered the re-run (first-stage survivors, with the repaired shapes as _r6)."""
    save = dict(SECOND_STAGE_DROPS)
    SECOND_STAGE_DROPS.clear()
    try:
        return registered_v4()
    finally:
        SECOND_STAGE_DROPS.update(save)


def all_v3_ids() -> list[str]:
    return sorted(x.id for x in v3.registered_v3())


def cluster_table_v4(lins: list[Lineage] | None = None) -> dict[str, list[Lineage]]:
    return v3.cluster_table_v3(lins if lins is not None else registered_v4())


def partition_readings_v4(lins: list[Lineage] | None = None, seed: int = 400004) -> dict[str, dict[str, str]]:
    return v3.partition_readings_v3(lins if lins is not None else registered_v4(), seed)


__all__ = ["AUDIT4_DROPS", "REPAIRED", "SECOND_STAGE_DROPS", "registered_v4", "candidates_v4", "cluster_table_v4", "partition_readings_v4"]
