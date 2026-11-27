# ruff: noqa: E501
"""R1 strict cluster map, version 2 (ruling R-2) and the partition readings (ruling R-6). Failing-first: the version-1 map gives 31 clusters, the auditor's gives 27.
The counts below are those of audit 2 (AUDIT_M0_R1_2.md section 1 and 2) reproduced by this code. Self-checked only."""

from __future__ import annotations

from studies.m0 import lineages_r1_clusters as v1
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0.lineages_r1_clusters_v2 import (
    BORDERLINE,
    STRICT_MERGES_V2,
    cluster_of_v2,
    cluster_table_v2,
)


def test_version_1_gives_31_and_version_2_gives_27_on_the_same_43_lineages() -> None:
    reg = v1.registered_lineages()
    assert len(reg) == 43
    assert len(v1.cluster_table(reg)) == 31  # the earlier author's map (unchanged)
    assert len(cluster_table_v2(reg)) == 27  # the auditor's strict map (ruling R-2)


def test_the_revision_4_set_is_43_shapes_in_27_clusters() -> None:
    reg = v2.registered_v2()
    assert len(reg) == 43 and len({x.id for x in reg}) == 43
    assert len(cluster_table_v2(reg)) == 27
    assert not {x.id for x in reg} & set(v2.REPLACES.values())  # every replaced shape has left the set
    assert sum(1 for x in reg if x.id.endswith("_r4")) == 21


def test_nine_groups_every_member_exists_and_none_is_in_two_groups() -> None:
    flat = [m for g in STRICT_MERGES_V2 for m in g]
    assert len(STRICT_MERGES_V2) == 9 and len(flat) == len(set(flat))
    ids = {v1.base_id(x.id) for x in v2.all_lineages_v2()}
    assert set(flat) <= ids


def test_the_four_new_merges_of_audit_2() -> None:
    c = cluster_of_v2
    assert c("R1.minimax_tree_r4") == c("R1.attribute_rule") == c("R1.conditional_decision_tree_r4")
    assert c("R1.topological_order_r4") == c("R1.order_extreme") == c("R1.order_tournament_wins")
    assert c("R1.containers_queue_line_r2") == c("R1.elimination_josephus")
    assert len({c("R1.order_compare_r4"), c("R1.road_reachability"), c("R1.categories_follow_r4"), c("R1.equivalence_classes_r2")}) == 1


def test_a_revised_shape_stays_in_the_cluster_of_the_shape_it_replaces() -> None:
    for new, old in v2.REPLACES.items():
        assert cluster_of_v2(new) == cluster_of_v2(old), (new, old)


def test_borderline_pairs_are_listed_not_merged_and_give_the_strictest_14() -> None:
    reg = v2.registered_v2()
    ids = {v1.base_id(x.id) for x in reg}
    for a, b, why in BORDERLINE:
        assert a in ids and b in ids and why
        assert cluster_of_v2(a) != cluster_of_v2(b), (a, b)  # not merged by the working map
    parent = {x: x for x in {cluster_of_v2(i) for i in ids}}

    def find(a: str) -> str:
        while parent[a] != a:
            a = parent[a]
        return a

    for a, b, _ in BORDERLINE:
        parent[find(cluster_of_v2(a))] = find(cluster_of_v2(b))
    assert len({find(x) for x in parent}) == 14  # the auditor's strictest count


def test_partition_readings_reproduce_the_audit_tabulation() -> None:
    reg = v2.registered_v2()
    ct = cluster_table_v2(reg)
    rd = v2.partition_readings(reg)

    def stats(name: str) -> tuple[int, int, int, int, int]:
        m = rd[name]
        both = sum(1 for ms in ct.values() if len({m[x.id] for x in ms}) == 2)
        wa = sum(1 for ms in ct.values() if {m[x.id] for x in ms} == {"A"})
        wb = sum(1 for ms in ct.values() if {m[x.id] for x in ms} == {"B"})
        return sum(1 for v in m.values() if v == "A"), sum(1 for v in m.values() if v == "B"), wa, wb, both

    assert stats("literal") == (21, 22, 9, 10, 8)  # audit: lineages 21/22, A 9, B 10, 8 straddle
    assert stats("family_closure") == (10, 33, 8, 19, 0)  # audit: lineages 10/33, clusters A 8, B 19
    assert stats("cluster_keys") == (16, 27, 13, 14, 0)  # audit: clusters A 13, B 14, lineages 16/27
    assert stats("literal_move_to_B")[4] == 0
    # version 1's own partition (the earlier author's map) is unchanged
    assert sum(len(x) for x in v1.clusters_per_part().values()) == 31
