# ruff: noqa: E501
"""C1 fix round 3: the cluster map. The auditor's strict map (``audit3_c1/AUDIT3_C1.md`` section 2: 28 clusters, ``recursive_calls_r2`` merged into the fib cluster) is the reference; the
test recomputes the partition of the 39 written lineages induced by the new map and compares it with the auditor's merges B1 to B8. Self-checked only."""

from __future__ import annotations

from studies.m0.lineages_c1_clusters import ALL_IDS, STRICT_GROUPS
from studies.m0.lineages_c1_fix3 import SUPERSEDES3
from studies.m0.lineages_c1_fix3_clusters import (
    CROSS_EVALUATION,
    EXCLUDED_LINEAGES,
    MEMBERS,
    VARIANT_CLUSTERS,
    check_consistency,
    clusters,
    registered_candidate_clusters,
)
from studies.m0.lineages_c1_rev2 import SUPERSEDES as REV2_SUPERSEDES


def test_map_is_consistent() -> None:
    assert check_consistency() == []


def test_counts() -> None:
    assert len(clusters()) == 28  # the auditor's strict map
    assert len(registered_candidate_clusters()) == 25  # 28 less insertion_sort, minmax_track, kadane_scan (R-12)
    assert len(registered_candidate_clusters(include_variants=False)) == 23  # and without the fast_power and counter_list variants
    assert set(VARIANT_CLUSTERS) == {"C1.fast_power", "C1.counter_list"}
    assert set(EXCLUDED_LINEAGES) == {c for c, ms in MEMBERS.items() if not ms}


def _cluster_of_written(lid: str) -> str:
    """The cluster of the new map that holds a written lineage (itself, what supersedes it, or its own excluded cluster)."""
    for c, ms in MEMBERS.items():
        for m in ms:
            chain = {m}
            cur = m
            while cur in SUPERSEDES3 or cur in REV2_SUPERSEDES:
                cur = SUPERSEDES3.get(cur) or REV2_SUPERSEDES[cur]
                chain.add(cur)
            if lid in chain:
                return c
    return lid if lid in MEMBERS else ""


def test_partition_equals_the_auditors_strict_map() -> None:
    ref: dict[str, str] = {}
    for lid in ALL_IDS:
        grp = next((g for g, ms in STRICT_GROUPS.items() if lid in ms), lid)
        ref[lid] = "B6" if grp == "B6" else grp
    mine = {lid: _cluster_of_written(lid) for lid in ALL_IDS}
    assert all(mine.values()), [i for i, c in mine.items() if not c]
    # same partition: ids are together in one map exactly when they are together in the other
    by_ref: dict[str, set[str]] = {}
    by_mine: dict[str, set[str]] = {}
    for lid in ALL_IDS:
        by_ref.setdefault(ref[lid], set()).add(lid)
        by_mine.setdefault(mine[lid], set()).add(lid)
    assert sorted(map(sorted, by_ref.values())) == sorted(map(sorted, by_mine.values()))
    assert len(by_mine) == 28


def test_recursive_calls_r2_is_in_the_fib_cluster() -> None:
    assert "C1.recursive_calls_r2" in MEMBERS["B6"] and "C1.fib_like_f3" in MEMBERS["B6"]
    assert sum("C1.recursive_calls_r2" in ms for ms in MEMBERS.values()) == 1


def test_cross_evaluation_lists_name_real_clusters() -> None:
    assert set(CROSS_EVALUATION) <= set(MEMBERS)
    strong = {c for c, d in CROSS_EVALUATION.items() if "strong" in d}
    assert {"B4", "B5", "B6", "B8", "C1.binary_search", "C1.cellular_update", "C1.circle_elimination", "C1.digit_peel", "C1.fast_power", "C1.kadane_scan", "C1.run_length_scan"} <= strong
