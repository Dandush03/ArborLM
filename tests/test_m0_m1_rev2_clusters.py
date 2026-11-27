# ruff: noqa: E501
"""M1 rev2: the strict cluster map (lead ruling R-2) reproduces the auditor's 22 clusters over the 37 lineages, on the batch-1 ids and on the rev2 effective set."""

from __future__ import annotations

from studies.m0.core import lineages_of
from studies.m0.lineages_m1_clusters import (
    ALL_STEMS,
    BORDERLINE,
    DISAGREEMENTS,
    GROUPS,
    count_strict,
    strict_clusters,
)
from studies.m0.lineages_m1_common import load_batch
from studies.m0.lineages_m1_rev2 import load_rev2


def test_all_37_lineages_are_mapped_and_the_strict_count_is_22() -> None:
    ids = [x.id for x in lineages_of("M1")] + [x.id for x in load_batch()]
    assert len(ids) == 37 == len(ALL_STEMS)
    assert {i.removeprefix("M1.") for i in ids} == set(ALL_STEMS)
    assert count_strict(ids) == 22


def test_rev2_effective_set_has_the_same_22_clusters() -> None:
    ids = [x.id for x in lineages_of("M1")] + [x.id for x in load_rev2()]
    assert len(ids) == 37
    assert count_strict(ids) == 22
    assert set(strict_clusters(ids)) == set(strict_clusters([x.id for x in lineages_of("M1")] + [x.id for x in load_batch()]))


def test_the_seven_groups_have_the_auditors_sizes_and_clock_duration_stays_open() -> None:
    assert sorted(len(v) for v in GROUPS.values()) == [2, 2, 2, 2, 3, 4, 7]
    assert not any("clock_duration" in v for v in GROUPS.values())
    assert "clock_duration" in BORDERLINE
    merged_into_s2 = count_strict([f"M1.{s}" for s in ALL_STEMS if s != "clock_duration"]) + 0
    assert merged_into_s2 == 21 + 0  # the strict count if clock_duration were merged away
    assert all(k.split(":")[0].split("_")[0] in {"S1", "S3", "S4", "S5", "S6", "S7"} for k in DISAGREEMENTS)
