# ruff: noqa: E501
"""R1 two-sided shortcut reading (rulings 2 and 5 of 2025-11-25): the redraw repair must leave each repaired heuristic near chance on BOTH sides. The band (0.08) is a
measurement used by these tests, not a registered threshold. Earlier shapes that overshot are asserted to leave the band (so the band assertion fails on them). Self-checked only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters as cl
from studies.m0 import lineages_r1_rev3 as r3
from studies.m0 import lineages_r1_shortcuts as sc
from studies.m0.core import Item

ROOT = Path(__file__).resolve().parents[1]
LINS = {x.id: x for x in cl.all_r1_lineages()}
BAND = 0.08
_CACHE: dict[str, dict[str, dict]] = {}


def _rows(lid: str) -> dict[str, dict]:
    if lid not in _CACHE:
        items = lg.sample_items(LINS[lid], 200, label="two-sided-test")
        _CACHE[lid] = {r["heuristic"]: r for r in sc.run_battery(LINS[lid], items)["heuristics"]}
    return _CACHE[lid]


def _dev(lid: str, h: str) -> float:
    r = _rows(lid)[h]
    return max(abs(r["excess_over_chance"]), abs(r["anti_excess"] or 0.0))


# retuned shape -> the heuristics it repairs
RETUNED_CASES = [(shape, n) for shape, (_, names) in r3.RETUNED.items() for n in names if not (shape == "R1.stable_matching_r2" and n == "first_mentioned")]


@pytest.mark.parametrize(("shape", "name"), RETUNED_CASES)
def test_retuned_shape_has_the_repaired_heuristic_near_chance_on_both_sides(shape: str, name: str) -> None:
    assert _dev(shape, name) < BAND, (shape, name, _rows(shape)[name]["excess_over_chance"], _rows(shape)[name]["anti_excess"])


# (earlier shape, heuristic, the earlier shape left the band on the BELOW-chance side)
OVERSHOOTS = [
    ("R1.categories_default_exceptions_r2", "last_listed"),
    ("R1.categories_default_exceptions_r2", "least_specific_rule"),
    ("R1.elimination_bracket_r2", "most_wins_logic"),
    ("R1.topological_order", "jth_alphabetical"),
    ("R1.kinship_descendants_r2", "first_mentioned"),
]


@pytest.mark.parametrize(("old", "name"), OVERSHOOTS)
def test_the_earlier_shape_overshot_below_chance_and_left_the_band(old: str, name: str) -> None:
    r = _rows(old)[name]
    assert r["excess_over_chance"] < -0.04 and _dev(old, name) > (0.04 if old != "R1.categories_default_exceptions_r2" else 0.3)


def test_categories_default_exceptions_r3_is_balanced_by_construction() -> None:
    lin = LINS["R1.categories_default_exceptions_r3"]
    items = lg.sample_items(lin, 200, label="cat3")
    for it in items:
        signs = [x[2] for x in it.structured["rules"] if x[1] == it.structured["verb"]]
        assert len(signs) == 5 and any(s != (it.answer == "yes") for s in signs)  # the priority rule is always needed
        assert all(x[0] != it.structured["chain"][0] for x in it.structured["rules"] if x[1] == it.structured["verb"])
    for h in ("majority_sign", "last_listed", "least_specific_rule"):
        assert _dev("R1.categories_default_exceptions_r3", h) < 0.06, h


def test_anti_credit_and_validity_mechanics() -> None:
    it = Item("i", "R1", "A", "x", "f", 1, "q. Who? Choose from Ada, Ben, Cy and Dee.", {}, "Ada", "name", 4)
    assert sc.anti_credit("Ada", it) == 0.0  # the heuristic chose the right option: its opposite scores 0
    assert sc.anti_credit("Ben", it) == pytest.approx(1 / 3)  # uniform among the 3 options not chosen, Ada among them
    assert sc.anti_credit(["Ada", "Ben", "Cy", "Dee"], it) == 0.25  # it chose everything: nothing to invert
    assert sc.anti_credit(None, it) == 0.25
    assert sc.anti_credit("Zed", it) == 0.25  # a name the item does not offer does not fire
    assert sc.credit("Zed", it) == 0.25
    open_item = Item("i", "R1", "A", "x", "f", 1, "q", {}, "7", "number", None)
    assert sc.anti_credit("7", open_item) is None


def test_open_answers_are_reported_as_absolute_rates_never_as_excess_over_chance() -> None:
    res = {lid: sc.run_battery(LINS[lid], lg.sample_items(LINS[lid], 60, label="open")) for lid in ("R1.mst_cost", "R1.activity_selection")}
    text = sc.two_sided_markdown(res, sorted(res)) + sc.markdown(res)
    assert "exact-match rate" in text and "most-frequent-answer" in text or "| open |" in text
    for line in text.splitlines():
        if "R1.mst_cost" in line or "R1.activity_selection" in line:
            assert "n/a" in line
    assert all(r["open_answers"] for r in res.values()) and all("per_level_accuracy" in r["worst"] for r in res.values())


def test_manifest_notes_the_conditioning_of_every_repaired_lineage_and_the_stale_table_is_marked() -> None:
    m = json.loads((ROOT / "studies" / "m0" / "manifests" / "r1_pilot_manifest.json").read_text())
    by = {x["id"]: x for x in m["lineages"]}
    for lid in r3.ANTI_REPAIRED:
        assert "CONDITIONS THE ITEM DISTRIBUTION ON A HEURISTIC'S OUTCOME" in by[lid]["repair_note"], lid
    assert not any("repair_note" in x for x in m["lineages"] if x["id"] not in r3.ANTI_REPAIRED)
    sup = (ROOT / "studies" / "m0" / "fixtures" / "r1_pilot" / "SUPERSEDED.txt").read_text()
    assert "r1_pilot_stats_table.md is SUPERSEDED by" in sup and (ROOT / "studies" / "m0" / "manifests" / "r1_pilot_stats_table.md").exists()
    assert (ROOT / "studies" / "m0" / "manifests" / "r1_stats_table_v2.md").exists() and (ROOT / "studies" / "m0" / "manifests" / "r1_two_sided_table.md").exists()
    rep = json.loads((ROOT / "studies" / "m0" / "manifests" / "r1_two_sided.json").read_text())
    for shape, v in rep["retuned"].items():
        assert v["redraw_probabilities"] == r3.P.get(v["retunes"], {})


def test_retuned_shapes_stay_in_the_cluster_of_the_shape_they_replace() -> None:
    for old, new in cl.SUPERSEDED.items():
        assert cl.cluster_of(old) == cl.cluster_of(new)
    assert len(cl.registered_lineages()) == 43 and len(cl.cluster_table()) == 31
