# ruff: noqa: E501
"""C1 cluster map (lead rulings R-2, R-8): the auditor's strict map reproduces 28 over the 39 written lineages and 22 with the author's borderline groups; the split of
recursive_calls makes the current set 29 and 23. Self-checked only."""

from __future__ import annotations

from studies.m0 import lineages_c1_clusters as cl
from studies.m0.lineages_c1_rev2 import PROPOSED, SUPERSEDES


def test_39_lineages_are_written_and_the_strict_map_gives_28_clusters() -> None:
    assert len(cl.OLD_IDS) == 14 and len(cl.NEW_IDS) == 25 and len(cl.ALL_IDS) == 39
    sc = cl.strict_clusters()
    assert len(sc) == 28
    assert sorted(m for ms in sc.values() for m in ms) == sorted(cl.ALL_IDS)  # every lineage in exactly one cluster
    assert {k: len(v) for k, v in sc.items() if k.startswith("B")} == {"B1": 4, "B2": 2, "B3": 2, "B4": 3, "B5": 2, "B6": 2, "B7": 2, "B8": 2}


def test_the_strictest_map_with_the_authors_borderline_groups_gives_22() -> None:
    st = cl.strictest_clusters()
    assert len(st) == 22
    assert sorted(m for ms in st.values() for m in ms) == sorted(cl.ALL_IDS)
    assert set(st["S1"]) >= {"C1.euclid_gcd", "C1.cond_chain", "C1.while_counter", "C1.digit_peel", "C1.fast_power"}
    assert len(st["S2"]) == 3 and len(st["S3"]) == 2


def test_after_the_recursive_split_the_current_set_has_29_strict_and_23_strictest_clusters() -> None:
    ids = cl.current_ids()
    assert len(ids) == len(set(ids)) == 40
    assert not set(SUPERSEDES.values()) & set(ids)  # the superseded lineages are out of the current set
    assert not PROPOSED & set(ids)  # proposals are shapes of existing clusters, not lineages
    cc = cl.current_strict_clusters()
    assert len(cc) == 29 and len(cl.current_strictest_clusters()) == 23
    assert "C1.fib_shapes_recursive" in cc["B6"] and "C1.fib_like" in cc["B6"]
    assert cc["C1.recursive_calls_r2"] == ("C1.recursive_calls_r2",)  # the other three shapes stand alone


def test_every_proposed_and_revised_lineage_resolves_to_a_cluster_and_every_disagreement_names_a_group() -> None:
    for lid in (*cl.REV2_IDS,):
        assert cl.current_cluster_of(lid)
    assert set(cl.DISAGREEMENTS) <= set(cl.STRICT_GROUPS)


def test_joined_family_groups_partition_the_families_of_the_current_set() -> None:
    groups = cl.joined_family_groups()
    fams = sorted(set(cl.families_of_current().values()))
    assert sorted(f for g in groups for f in g) == fams
    assert any(len(g) > 1 for g in groups)  # a cluster does join families (B1, B3, B5)
