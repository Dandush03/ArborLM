# ruff: noqa: E501
"""Strict clusters, lineage status and the cluster-closed partition for R1 (lineage repair, rulings A and B of the lead).

Ruling A: "a distinct solution procedure" is read STRICTLY (the general algorithm is the procedure; number system, constraint mix and final question are
parameters). Lineages that the audit (docs/reviews/m0-lineage-decision-2026-11-25/audit1/AUDIT_M0_LINEAGES_1.md, ``pairs_judgement.csv``) merges under the
strict reading are registered as ONE lineage (one cluster) with several shapes; no lineage is deleted.
Ruling B: a strict cluster may not have members in both parts. The parts follow ``core.family_partition``'s own rule (shuffle of the sorted family keys with the
stream of seed 400004, first half A); where a cluster joins two families, those families are one key of that rule (so the whole cluster is in one part).
This reading of "the whole cluster goes to one part by the registered partition rule" is the implementer's (ruling needed, see NOTES_LINEAGE_REPAIR.md).
"""

from __future__ import annotations

from studies.m0.core import Lineage, lineages_of, stream

# strict-merge groups among the 35 lineages of the pilot audit, base ids (without the revision suffix)
STRICT_MERGES: tuple[tuple[str, ...], ...] = (
    ("R1.order_compare", "R1.road_reachability"),  # directed reachability (merged under both readings)
    ("R1.event_timeline", "R1.temporal_weekday_shift", "R1.spatial_relative_directions", "R1.equivalence_exchange_rates"),  # potential propagation over a tree
    ("R1.kinship_ancestor", "R1.kinship_cousins", "R1.categories_default_exceptions"),  # pointer chasing up a chain
    ("R1.knights_knaves", "R1.one_culprit"),  # hypothesis enumeration against statements
    ("R1.seating_row", "R1.pet_owners"),  # permutation constraint elimination
    ("R1.attribute_rule", "R1.conditional_decision_tree"),  # evaluating a propositional structure under an assignment
    ("R1.compass_turns", "R1.boolean_lights"),  # folding a command list into a cyclic accumulator
    ("R1.categories_follow", "R1.equivalence_classes"),  # closing a positive relation and lifting a negative one
    ("R1.order_extreme", "R1.order_tournament_wins"),  # degree tally of a pairwise relation, extremum
)

# shape revisions (ruling D): old shape id -> new shape id. The old shape is kept in its file and is not registered.
SUPERSEDED: dict[str, str] = {
    "R1.spatial_grid_walk": "R1.spatial_grid_walk_r2",
    "R1.kinship_descendants": "R1.kinship_descendants_r2",
    "R1.equivalence_classes": "R1.equivalence_classes_r2",
    "R1.elimination_bracket": "R1.elimination_bracket_r2",
    "R1.containers_queue_line": "R1.containers_queue_line_r2",
    "R1.categories_default_exceptions": "R1.categories_default_exceptions_r2",
    "R1.conditional_threshold_rule": "R1.conditional_threshold_rule_r2",
    "R1.boolean_lights": "R1.boolean_lights_r2",
    "R1.graph_shortest_route": "R1.graph_shortest_route_r2",
    "R1.containers_stack_piles": "R1.containers_stack_piles_r2",
    "R1.categories_follow": "R1.categories_follow_r2",
    "R1.kinship_ancestor": "R1.kinship_ancestor_r2",  # found by the shortcut gate: the answer was always the parentless root
}

# lineages that are not registered, with the reason (filled in as the gates decide; none yet)
NOT_REGISTERED: dict[str, str] = {}


def base_id(lid: str) -> str:
    return lid[: -len("_r2")] if lid.endswith("_r2") else lid


def cluster_of(lid: str) -> str:
    """Cluster id: the smallest base id of the strict group (or the base id itself for a singleton)."""
    b = base_id(lid)
    for grp in STRICT_MERGES:
        if b in grp:
            return min(grp)
    return b


def all_r1_lineages() -> list[Lineage]:
    from studies.m0.lineages_r1_common import load_pilot

    return sorted([*lineages_of("R1"), *load_pilot()], key=lambda x: x.id)


def registered_lineages() -> list[Lineage]:
    """Every R1 lineage that is not superseded and not NOT REGISTERED."""
    return [x for x in all_r1_lineages() if x.id not in SUPERSEDED and x.id not in NOT_REGISTERED]


def cluster_table(lins: list[Lineage] | None = None) -> dict[str, list[Lineage]]:
    out: dict[str, list[Lineage]] = {}
    for lin in lins if lins is not None else registered_lineages():
        out.setdefault(cluster_of(lin.id), []).append(lin)
    return out


def family_groups(lins: list[Lineage] | None = None) -> dict[str, str]:
    """family -> group key, where families joined by a strict cluster share one key (the sorted families joined by '+')."""
    lins = lins if lins is not None else registered_lineages()
    parent = {f: f for f in sorted({x.family for x in lins})}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for members in cluster_table(lins).values():
        fams = sorted({m.family for m in members})
        for f in fams[1:]:
            parent[find(f)] = find(fams[0])
    groups: dict[str, list[str]] = {}
    for f in sorted(parent):
        groups.setdefault(find(f), []).append(f)
    return {f: "+".join(sorted(fs)) for fs in groups.values() for f in fs}


def partition(lins: list[Lineage] | None = None, seed: int = 400004) -> dict[str, str]:
    """group key -> "A" | "B": core.family_partition's rule applied to the cluster-closed family groups."""
    keys = sorted(set(family_groups(lins).values()))
    r = stream(seed, "family-partition", "R1")
    shuffled = keys[:]
    r.shuffle(shuffled)
    half = len(shuffled) // 2
    return {k: ("A" if i < half else "B") for i, k in enumerate(shuffled)}


def clusters_per_part(lins: list[Lineage] | None = None) -> dict[str, list[str]]:
    lins = lins if lins is not None else registered_lineages()
    fg, part = family_groups(lins), partition(lins)
    out: dict[str, set[str]] = {"A": set(), "B": set()}
    for cid, members in cluster_table(lins).items():
        parts = {part[fg[m.family]] for m in members}
        if len(parts) != 1:
            raise AssertionError(f"cluster {cid} spans both parts")
        out[parts.pop()].add(cid)
    return {p: sorted(v) for p, v in out.items()}
