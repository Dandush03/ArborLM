# ruff: noqa: E501
"""M1 batch 1, family number_theory: mechanical checks of the new lineages (no independent solver exists yet; see studies/m0/manifests/m1_batch1_manifest.json)."""

from __future__ import annotations

from studies.m0.lineages_m1_common import check_family


def test_family_number_theory_lineages_build_deterministic_in_grammar_and_state_their_format() -> None:
    assert check_family("number_theory") == []


def test_batch_ids_do_not_collide_and_are_not_in_the_core_registry() -> None:
    from studies.m0.core import REGISTRY, lineages_of
    from studies.m0.lineages_m1_common import FIRMNESS, load_batch

    batch = load_batch()
    ids = [x.id for x in batch]
    assert len(ids) == len(set(ids)) == len(FIRMNESS)
    assert not set(ids) & {x.id for x in lineages_of("M1")}
    assert not set(ids) & {x.id for bucket in REGISTRY.values() for x in bucket}
    assert all(x.eval == "M1" and x.id.startswith("M1.") for x in batch)
    assert {x.family for x in batch} == {"number_theory", "counting", "statistics", "sequences", "algebra", "geometry", "pricing", "division"}


def test_every_lineage_has_every_level_and_a_procedure_text() -> None:
    from studies.m0.core import ALL_LEVELS, build_item, stream
    from studies.m0.lineages_m1_common import load_batch
    from studies.m0.m1_batch1_gates import PROCEDURE

    for lin in load_batch():
        assert lin.id in PROCEDURE
        for lv in ALL_LEVELS:
            it = build_item(lin, lv, stream(953704, lin.id, str(lv)), "A", "t")
            assert it.level == lv and it.answer_type == "number" and it.k is None
