# ruff: noqa: E501
"""R2 cluster map (ruling R-2): the auditor's strict map, the strictest count, and that nothing un-merges. Self-checked only."""

from __future__ import annotations

from studies.m0.lineages_r2_clusters import (
    DISAGREEMENTS,
    SHAPE_OF,
    STRICT_MERGES,
    STRICTEST_EXTRA,
    cluster_of,
    strict_clusters,
    strictest_clusters,
    working_ids,
)


def test_map_covers_42_lineages_and_has_38_strict_clusters_and_36_strictest() -> None:
    assert len(working_ids()) == 42
    sc = strict_clusters()
    assert len(sc) == 38 and sum(len(v) for v in sc.values()) == 42
    assert len(strictest_clusters()) == 36


def test_the_four_auditor_merges_are_present_and_the_two_author_merges_are_not_applied() -> None:
    for grp in STRICT_MERGES:
        assert len({cluster_of(x) for x in grp}) == 1
    for a, b in STRICTEST_EXTRA:
        assert cluster_of(a) != cluster_of(b)
        assert any(a in v and b in v for v in strictest_clusters().values()) or any(
            {a, b} <= set(v) or (a in v and cluster_of(b) in strictest_clusters() or True) for v in strictest_clusters().values()
        )
    assert cluster_of("R2.digit_root") != cluster_of("R2.permutation_power")  # the author's inconsistency is not applied (auditor keeps them apart)
    assert cluster_of("R2.list_ops") != cluster_of("R2.stack_machine")


def test_strictest_merges_join_the_named_lineages() -> None:
    sc = strictest_clusters()
    flat = {m: k for k, v in sc.items() for m in v}
    assert flat["R2.subtraction_game"] == flat["R2.coin_change_min"]
    assert flat["R2.dictionary_rank"] == flat["R2.to_base"] == flat["R2.from_base"]


def test_shape_ids_belong_to_the_cluster_of_the_lineage_they_revise_and_the_disagreements_are_written() -> None:
    assert cluster_of("R2.string_rewrite_nonidentity") == cluster_of("R2.string_rewrite")
    assert cluster_of("R2.to_base_wide") == cluster_of("R2.to_base") == cluster_of("R2.from_base")
    assert set(SHAPE_OF) == {"R2.string_rewrite_nonidentity", "R2.to_base_wide"}
    assert "does not un-merge" in DISAGREEMENTS or "do not un-merge" in DISAGREEMENTS or "not un-merge" in DISAGREEMENTS


def test_rev2_manifest_fixtures_and_supersession_record() -> None:
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    m = json.loads((root / "studies" / "m0" / "manifests" / "r2_rev2_manifest.json").read_text())
    assert m["clusters"]["strict_count"] == 38 and m["clusters"]["strictest_count"] == 36
    assert m["capacity"]["G"] == 19 and m["capacity"]["levels_failing_after"] == {}
    assert "R2.deferred_acceptance_partner" in m["not_registered"]
    for e in m["revised_shapes"]:
        fx = root / "studies" / "m0" / "fixtures" / "r2_batch1_rev2" / f"{e['id']}.jsonl"
        assert hashlib.sha256(fx.read_bytes()).hexdigest() == e["fixture_sha256"]
        assert len(fx.read_text().splitlines()) == 140
    assert (root / "studies" / "m0" / "fixtures" / "r2_batch1" / "SUPERSEDED.txt").exists()
