# ruff: noqa: E501
"""Lineage repair, pilot batch 1 (R1): the mechanical gates and the batch's bookkeeping. Self-checked only. No threshold is registered here:
the answer-distribution and overlap numbers are measurements; only the capacity factor (10 at the G = 300 demand) is a rule of ADR-0033."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0.core import REGISTRY, Built, Item, Lineage, lineages_of, stream
from studies.m0.lineages_r1_common import FAMILY_MODULES, INTENDED_PART, PILOT, load_pilot

ROOT = Path(__file__).resolve().parents[1]
NEW = load_pilot()


def test_twenty_new_lineages_ten_per_intended_part_in_at_least_four_new_families() -> None:
    assert len(NEW) == 20 and len({x.id for x in NEW}) == 20
    assert sum(1 for x in NEW if INTENDED_PART[x.id] == "A") == 10 and sum(1 for x in NEW if INTENDED_PART[x.id] == "B") == 10
    old_fams = {x.family for x in lineages_of("R1")}
    assert len({x.family for x in NEW} - old_fams) >= 4
    assert len({x.family for x in NEW}) >= 4 and set(FAMILY_MODULES) == {x.family for x in NEW}


def test_pilot_lineages_are_not_in_the_core_registry_and_ids_do_not_collide() -> None:
    core_ids = {x.id for x in REGISTRY["R1"]}
    assert not core_ids & {x.id for x in PILOT}
    assert len(lineages_of("R1")) == 15  # the suite's solver tests still see exactly the 15 original lineages


def test_signatures_are_distinct_between_all_fifteen_old_and_twenty_new_builders() -> None:
    sigs = {x.id: lg.signature(x.build) for x in [*lineages_of("R1"), *NEW]}
    assert len(set(sigs.values())) == 35


def test_signature_ignores_names_and_constants_but_not_structure() -> None:
    def a(level: int, r):  # type: ignore[no-untyped-def]
        x = r.randint(1, 5)
        return [x + 1 for _ in range(3)]

    def b(level: int, r):  # type: ignore[no-untyped-def]
        y = r.randint(7, 90)
        return [y + 2 for _ in range(4)]

    def c(level: int, r):  # type: ignore[no-untyped-def]
        x = r.randint(1, 5)
        return [x * 1 for _ in range(3)]

    assert lg.signature(a) == lg.signature(b) != lg.signature(c)


def test_skeleton_abstracts_numbers_and_vocabulary() -> None:
    assert lg.skeleton("Ada has 12 apples. Ben has 7 apples.") == lg.skeleton("Cara has 3 apples. Zed has 99 apples.")
    assert lg.jaccard(lg.sentence_skeletons("Ada has 12 dollars. Who wins?"), lg.sentence_skeletons("Ben has 3 dollars. Who loses?")) == pytest.approx(1 / 3)


def test_answer_statistics_on_a_known_distribution_and_the_known_bad_lineage() -> None:
    items = [Item(str(i), "R1", "A", "x", "f", 1, "q", {}, "yes" if i < 8 else "no", "yn", 2) for i in range(10)]
    s = lg.answer_stats(items)
    assert s["top_share"] == 0.8 and s["chance_mean_1_over_k"] == 0.5 and s["top_over_chance"] == 1.6
    bad = next(x for x in lineages_of("R1") if x.id == "R1.categories_follow")
    st = lg.answer_stats(lg.sample_items(bad, 100))
    assert st["top_over_chance"] > 2.0 and st["top_key"] == "cannot be determined"  # the measurement that would have caught the defect


def test_capacity_at_the_proposed_g_is_proved_for_every_new_lineage_and_level() -> None:
    assert lg.demand_at_g(300, 3) == 180 and lg.demand_at_g(300, 0) == 100
    for lin in NEW:
        for lv in lg.ALL_LEVELS:
            need = lg.CAPACITY_FACTOR * lg.demand_at_g(300, lv)
            found, _ = lg.exhibit(lin, lv, need)
            assert found >= need, (lin.id, lv, found, need)


def test_capacity_gate_can_fail() -> None:
    def tiny(level: int, r):  # type: ignore[no-untyped-def]
        return Built(f"pick {r.randint(1, 5)}", {}, "1", "number", None)

    found, _ = lg.exhibit(Lineage("R1.tiny", "R1", "t", tiny), 1, 1800)
    assert found == 5


def test_family_check_detects_planted_defects(monkeypatch: pytest.MonkeyPatch) -> None:
    def leaky(level: int, r):  # type: ignore[no-untyped-def]
        return Built(f"Which? {r.randint(1, 10**6)}", {"answer": "x"}, "not a number!", "number", 1)

    monkeypatch.setattr("studies.m0.lineages_r1_common.PILOT", [*PILOT, Lineage("R1.leaky", "R1", "zz", leaky)])
    probs = lg.check_family("zz")
    assert any("grammar" in p for p in probs) and any("k < 2" in p for p in probs) and any("carries the key" in p for p in probs)


def test_manifest_and_fixtures_match_the_current_code() -> None:
    m = json.loads((ROOT / "studies" / "m0" / "manifests" / "r1_pilot_manifest.json").read_text())
    by_id = {x["id"]: x for x in m["new_lineages"]}
    assert set(by_id) == {x.id for x in NEW}
    for lin in NEW:
        assert by_id[lin.id]["signature"] == lg.signature(lin.build), lin.id  # the builder changed since the manifest: regenerate
        assert by_id[lin.id]["capacity_passed_all_levels"] is True
        fx = (ROOT / "studies" / "m0" / "fixtures" / "r1_pilot" / f"{lin.id}.jsonl").read_text().splitlines()
        assert len(fx) == 140  # 20 items for each of the 7 levels
        first = json.loads(fx[0])
        r = stream(lg.STAT_SEED, "fixture", lin.id, "0")
        from studies.m0.core import build_item

        assert build_item(lin, 0, r, "A", first["id"]).question == first["question"]
    assert (ROOT / "studies" / "m0" / "fixtures" / "R1_PILOT_SCHEMA.md").exists()
