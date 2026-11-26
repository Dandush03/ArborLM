# ruff: noqa: E501
"""M1 strict cluster map for the fix-round-4 set (R-24, R-25, R-26). Same strict map as round 3 (``lineages_m1_fix3_clusters.GROUPS``, the audit-4 map of 20 clusters over the 33 candidates);
a lineage marked NOT REGISTERED (round 3 or round 4) is removed, and a cluster with no registered member disappears (a cluster survives if at least one of its lineages survives, R-24).
No strata are proposed; a lineage is a cluster member, the cluster is the unit."""

from __future__ import annotations

from studies.m0.lineages_m1_fix3_clusters import GROUPS
from studies.m0.lineages_m1_fix4 import stem


def cluster_of(lineage_id: str) -> str:
    st = stem(lineage_id)
    for name, members in GROUPS.items():
        if st in members:
            return name
    return st


def strict_clusters(ids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in sorted(ids):
        out.setdefault(cluster_of(i), []).append(i)
    return dict(sorted(out.items()))


def count_strict(ids: list[str]) -> int:
    return len(strict_clusters(ids))
