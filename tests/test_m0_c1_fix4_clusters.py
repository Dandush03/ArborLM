# ruff: noqa: E501
"""C1 fix round 4: the corrected cluster map (R-20) and the demand formula. Self-checked only; nothing is registered."""

from __future__ import annotations

from studies.m0.c1_fix4_capacity import demand
from studies.m0.lineages_c1_fix3_clusters import MEMBERS as FIX3_MEMBERS
from studies.m0.lineages_c1_fix4_clusters import (
    DROPPED_CLUSTERS,
    MEMBERS,
    VARIANT_CLUSTERS,
    check_consistency,
    cluster_of,
    smaller_part,
    surviving_clusters,
)


def test_map_is_consistent() -> None:
    assert check_consistency() == []


def test_counts() -> None:
    assert len(surviving_clusters()) == 18
    assert len(surviving_clusters(include_variants=False)) == 16
    assert set(VARIANT_CLUSTERS) == {"C1.fast_power_square_map", "C1.counter_list_state_machine"}


def test_the_variants_are_in_their_own_clusters_not_under_the_originals() -> None:
    assert cluster_of("C1.fast_power_f4") == "C1.fast_power_square_map"
    assert cluster_of("C1.counter_list_f3") == "C1.counter_list_state_machine"
    assert "C1.fast_power" not in MEMBERS and "C1.counter_list" not in MEMBERS
    for c in VARIANT_CLUSTERS:
        assert len(MEMBERS[c]) == 1
    for c, ms in MEMBERS.items():
        if c not in VARIANT_CLUSTERS:
            assert "C1.fast_power_f4" not in ms and "C1.counter_list_f3" not in ms


def test_the_map_accounts_for_every_fix3_cluster() -> None:
    fix3 = set(FIX3_MEMBERS)
    now = {c for c in MEMBERS if c not in VARIANT_CLUSTERS} | set(DROPPED_CLUSTERS)
    # the fix-3 clusters of the two originals are replaced by the two variant clusters
    assert fix3 == now | {"C1.fast_power", "C1.counter_list"}
    assert not (set(MEMBERS) & set(DROPPED_CLUSTERS))


def test_strict_clusters_are_those_of_the_audit() -> None:
    assert set(MEMBERS["B1"]) == {"C1.string_build_f3", "C1.list_build_f3", "C1.nested_pairs_f3"}  # loop_sum is dropped
    assert set(MEMBERS["B8"]) == {"C1.bracket_matching_f3", "C1.postfix_evaluation"}
    assert set(MEMBERS["B6"]) == {"C1.fib_like_f3", "C1.fib_shapes_recursive_f3", "C1.recursive_calls_r2"}
    assert "B4" in DROPPED_CLUSTERS and len(DROPPED_CLUSTERS["B4"]) == 3


def test_demand_formula_and_smaller_part() -> None:
    assert demand(12) == 21010 and demand(11) == 22830 and demand(10) == 25000  # the audit's figures
    assert demand(9) == 27680 and demand(7) == 35300
    assert smaller_part(18) == 9 and smaller_part(25) == 12 and smaller_part(17) == 8
