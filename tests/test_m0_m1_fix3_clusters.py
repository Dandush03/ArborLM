# ruff: noqa: E501
"""M1 fix round 3, cluster map. The expected map is written out here from the auditor's table (AUDIT3_M1 section 4), independently of the module under test."""

from __future__ import annotations

import json
from pathlib import Path

from studies.m0.lineages_m1_fix3 import load_all, load_registered
from studies.m0.lineages_m1_fix3_clusters import (
    BORDERLINE,
    CROSS_EVALUATION,
    GROUPS,
    cluster_of,
    count_strict,
    strict_clusters,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "S1": {"linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"},
    "S2": {"shopping", "speed_distance", "mixture"},
    "S3": {"percent_change", "fraction_remainder", "tip_split", "ratio_share"},
    "S4": {"binomial_choose", "slot_permutations"},
    "S5": {"change_ways"},
    "S6": {"grid_perimeter", "painted_cube"},
    "S7": {"arithmetic_series", "recurrence_iterate"},
}
SINGLETONS = {"clock_duration", "inclusion_exclusion", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors", "last_digit_power", "quadratic_area", "digit_puzzle", "pythagoras", "tiered_pricing", "finite_differences", "median_list", "mode_tally", "division_counting"}


def stem(lid: str) -> str:
    return lid.split(".", 1)[1].removesuffix("_r3")


def test_every_lineage_lands_in_exactly_the_audits_cluster() -> None:
    expected_of = {s: k for k, v in EXPECTED.items() for s in v}
    for lin in load_all():
        st = stem(lin.id)
        want = expected_of.get(st, st)
        got = cluster_of(lin.id)
        assert (got.startswith(want) or got == want), (lin.id, got, want)
    assert {stem(x.id) for x in load_all()} == set().union(*EXPECTED.values()) | SINGLETONS


def test_the_written_map_has_22_clusters_and_the_registered_map_has_the_count_after_exclusions() -> None:
    assert count_strict([x.id for x in load_all()]) == 22  # the auditor's 22 over the 36 written lineages (min_cost_packs absent)
    reg = [x.id for x in load_registered()]
    clusters = strict_clusters(reg)
    # S4 keeps slot_permutations when binomial_choose is not registered; pythagoras and digit_puzzle are singleton clusters and disappear
    assert len(clusters) == 20
    assert "S4_product_rule_counting" in clusters and clusters["S4_product_rule_counting"] == ["M1.slot_permutations_r3"]
    assert not any("pythagoras" in c or "digit_puzzle" in c for c in clusters)


def test_borderline_merges_are_listed_not_merged() -> None:
    assert set(BORDERLINE) == {"gcd_lcm + crt_congruence", "clock_duration + S2_weighted_sum"}
    c = strict_clusters([x.id for x in load_all()])
    assert cluster_of("M1.gcd_lcm_r3") != cluster_of("M1.crt_congruence_r3")
    assert cluster_of("M1.clock_duration_r3") != cluster_of("M1.shopping_r3")
    assert len(c) == 22
    # merging each borderline pair would lower the count by one (computed here, by hand)
    merged = {k: set(v) for k, v in c.items()}
    merged["gcd_lcm"] |= merged.pop("crt_congruence")
    assert len(merged) == 21
    merged["S2_weighted_sum"] |= merged.pop("clock_duration")
    assert len(merged) == 20


def test_min_cost_packs_is_in_no_map_and_no_count() -> None:
    assert not any("min_cost" in s for g in GROUPS.values() for s in g)
    from studies.m0.lineages_m1_fix3_clusters import ALL_STEMS, CROSS_EVALUATION_BORDERLINE

    assert not any("min_cost" in x for x in ALL_STEMS) and len(ALL_STEMS) == 36
    assert not any("min_cost" in k or "min_cost" in " ".join(v) for k, v in {**CROSS_EVALUATION, **CROSS_EVALUATION_BORDERLINE}.items())
    mp = ROOT / "studies" / "m0" / "manifests" / "m1_fix3_cluster_map.json"
    if mp.exists():
        rec = json.loads(mp.read_text())
        assert not any("min_cost" in m for c in rec["clusters"].values() for m in c["members"])


def test_cross_evaluation_entries_name_existing_clusters_and_other_evaluations_only() -> None:
    known = set(GROUPS) | SINGLETONS
    for k, v in CROSS_EVALUATION.items():
        assert k in known, k
        assert all(x.split(".")[0] in ("R1", "R2", "C1") for x in v), (k, v)
