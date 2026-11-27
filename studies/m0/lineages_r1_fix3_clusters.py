# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""R1 strict cluster map, version 3, and the set of shapes it registers (fix round 3; the human lead's fourth decision, lead rulings R-1, R-2, R-6, R-12 of LEAD_RULINGS_2.md and LEAD_RULINGS_3.md).

Version 2 (``lineages_r1_clusters_v2``) is kept unchanged. This map takes the third auditor's two further merges (AUDIT3_R1.md section 2) and applies ruling R-12: a shape marked NOT REGISTERED is removed from the
cluster map, from G, from fixtures and from capacity runs. Where my rebuild changes no algorithm the auditor's map governs; the two merges:
  (v) conditional_chain joins knights_knaves / one_culprit (enumerate truth assignments against stated clauses; my rebuild of conditional_chain still decides its key by enumerating assignments);
  (vi) elimination_bracket joins attribute_rule / conditional_decision_tree / minimax_tree (a knockout bracket is bottom-up evaluation of a tree; the rebuild asks only 'who wins' and 'who loses the final').
Nothing here enters ``core.REGISTRY`` (ruling R-9).
"""

from __future__ import annotations

from studies.m0 import lineages_r1_clusters as v1
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0.core import Lineage, stream
from studies.m0.lineages_r1_fix3_common import REPLACES, load_fix3

STRICT_MERGES_V3: tuple[tuple[str, ...], ...] = (
    ("R1.order_compare", "R1.road_reachability", "R1.categories_follow", "R1.equivalence_classes"),  # closure of a positive relation plus lifted negative pairs, read three-valued
    ("R1.event_timeline", "R1.temporal_weekday_shift", "R1.spatial_relative_directions", "R1.equivalence_exchange_rates"),  # potential propagation over a tree
    ("R1.kinship_ancestor", "R1.kinship_cousins", "R1.categories_default_exceptions"),  # pointer chasing up a chain
    ("R1.knights_knaves", "R1.one_culprit", "R1.conditional_chain"),  # enumeration of truth assignments against clauses (v: the third auditor's merge)
    ("R1.attribute_rule", "R1.conditional_decision_tree", "R1.minimax_tree", "R1.elimination_bracket"),  # bottom-up evaluation of a tree (vi: the third auditor's merge)
    ("R1.compass_turns", "R1.boolean_lights"),  # folding a command list into a cyclic accumulator
)

# shapes the round could not make registrable (ruling R-12: excluded from the map, G, fixtures and capacity runs); id -> reason with the measured residual
NOT_REGISTERED_V3: dict[str, str] = {
    "R1.elimination_josephus": "capacity: 16 (level 0) to 40 (level 6) different structures (exact, audit 3); the procedure has two parameters (people, step) and cannot carry 22,830 items per level",
    "R1.order_extreme": "capacity: 2 different structures per level (a chain of people and the end that is asked); also a least-mentioned reading of +0.17 to +0.39",
    "R1.order_tournament_wins": "capacity: 4 to 524 different structures per level (exact, audit 3); a tally of half the results reads +0.29 to +0.40",
    "R1.pet_owners": "rebuilt as pet_owners_r5 (the asked pet named in no 'owns' or 'either' clue): when the asked pet is never stated the owner is the one person left over by the other clues, and the partial elimination 'not struck off and not owning another named pet' reads +0.63 to +0.73; when it is stated the answer is verbatim (23 to 46 %). Both removed",
    "R1.pet_owners_r5": "the rebuild above (the cluster keeps seating_row_r5)",
    "R1.instant_runoff_r4": "rebuilt as instant_runoff_r5 (a hidden cycle of candidates; wider first-place totals; 6 to 9 candidates; four settings tried): the winner of the runoff between the two plurality leaders still reads +0.25 to +0.57, one elimination then plurality +0.31 to +0.42, Borda +0.28 to +0.37, the Condorcet winner +0.20 to +0.39: the other voting rules agree with the elimination count whatever the profile",
    "R1.instant_runoff_r5": "the rebuild above",
    "R1.stable_matching_r4": "rebuilt as stable_matching_r5 (a planted rotation so that the two optimal matchings differ): the receiver-proposing reading falls from +0.51 to below +0.17 but serial dictatorship in the order of the text reads +0.14 to +0.34 and the first choice +0.27 to +0.44, and the last choice is never the answer (a floor); two plantings tried",
    "R1.stable_matching_r5": "the rebuild above",
}


def base(lid: str) -> str:
    return v1.base_id(lid)


def cluster_of_v3(lid: str) -> str:
    b = base(lid)
    for grp in STRICT_MERGES_V3:
        if b in grp:
            return min(grp)
    return b


def registered_v3() -> list[Lineage]:
    """The version-2 set, with every shape a round-3 shape replaces swapped for it and every NOT REGISTERED shape removed."""
    new = load_fix3()
    gone = set(REPLACES.values()) | set(NOT_REGISTERED_V3)
    base_set = [x for x in v2.registered_v2() if x.id not in gone]
    return sorted([*base_set, *[x for x in new if x.id not in NOT_REGISTERED_V3]], key=lambda x: x.id)


def cluster_table_v3(lins: list[Lineage] | None = None) -> dict[str, list[Lineage]]:
    out: dict[str, list[Lineage]] = {}
    for lin in lins if lins is not None else registered_v3():
        out.setdefault(cluster_of_v3(lin.id), []).append(lin)
    return out


def family_groups_v3(lins: list[Lineage]) -> dict[str, str]:
    parent = {f: f for f in sorted({x.family for x in lins})}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for members in cluster_table_v3(lins).values():
        fams = sorted({m.family for m in members})
        for f in fams[1:]:
            parent[find(f)] = find(fams[0])
    groups: dict[str, list[str]] = {}
    for f in sorted(parent):
        groups.setdefault(find(f), []).append(f)
    return {f: "+".join(sorted(fs)) for fs in groups.values() for f in fs}


def partition_readings_v3(lins: list[Lineage] | None = None, seed: int = 400004) -> dict[str, dict[str, str]]:
    """As ``lineages_r1_clusters_v2.partition_readings`` on this map (reported, not chosen; ruling R-6)."""
    lins = lins if lins is not None else registered_v3()
    lit = v2._shuffle_split(sorted({x.family for x in lins}), seed)
    out: dict[str, dict[str, str]] = {"literal": {x.id: lit[x.family] for x in lins}}
    fg = family_groups_v3(lins)
    fc = v2._shuffle_split(sorted(set(fg.values())), seed)
    out["family_closure"] = {x.id: fc[fg[x.family]] for x in lins}
    ct = cluster_table_v3(lins)
    ck = v2._shuffle_split(sorted(ct), seed)
    out["cluster_keys"] = {x.id: ck[cluster_of_v3(x.id)] for x in lins}
    mv = dict(out["literal"])
    for members in ct.values():
        if len({out["literal"][m.id] for m in members}) > 1:
            for m in members:
                mv[m.id] = "B"
    out["literal_move_to_B"] = mv
    return out


__all__ = ["STRICT_MERGES_V3", "NOT_REGISTERED_V3", "cluster_of_v3", "registered_v3", "cluster_table_v3", "partition_readings_v3", "stream"]
