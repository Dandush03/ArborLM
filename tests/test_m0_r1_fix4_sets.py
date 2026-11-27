# ruff: noqa: E501
"""R1 fix round 4: the set after the narrow repair round (lead rulings R-24 to R-29): which shapes survive, the drop reasons, the repaired levels, the manifests. Self-checks only; nothing is registered."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from studies.m0 import lineages_r1_fix3_b as b3
from studies.m0 import lineages_r1_fix3_c as c3
from studies.m0 import lineages_r1_fix3_clusters as v3
from studies.m0 import lineages_r1_fix4_a as a4
from studies.m0 import lineages_r1_fix4_clusters as c4
from studies.m0 import lineages_r1_rev4_b as rb
from studies.m0.core import REGISTRY, Retry
from studies.m0.lineages_r1_fix4_common import load_fix4
from studies.m0.r1_fix4_levels import PARAM, level_classes

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "studies/m0/manifests"
FINAL = c4.registered_v4()
CANDS = c4.candidates_v4()


def test_the_set_after_round_4_is_twelve_shapes_in_ten_clusters() -> None:
    assert len(FINAL) == 12
    assert len(c4.cluster_table_v4()) == 10
    assert len({x.id for x in FINAL}) == 12


def test_every_fix3_shape_is_dropped_or_survives_exactly_once_and_every_drop_has_a_reason() -> None:
    v3_ids = set(c4.all_v3_ids())
    assert len(v3_ids) == 37
    assert set(c4.AUDIT4_DROPS) <= v3_ids and len(c4.AUDIT4_DROPS) == 23
    first_stage_survivors = {x.id for x in CANDS}
    assert len(first_stage_survivors) == 14
    assert set(c4.SECOND_STAGE_DROPS) <= first_stage_survivors
    final = {x.id for x in FINAL}
    assert final == first_stage_survivors - set(c4.SECOND_STAGE_DROPS)
    for lid, why in {**c4.AUDIT4_DROPS, **c4.SECOND_STAGE_DROPS}.items():
        assert len(why) > 40 and ("audit 4" in why or "R-19" in why), lid
    # the replaced shapes leave the set and the _r6 builders enter it
    for new, old in c4.REPAIRED.items():
        assert old in v3_ids and old not in {x.id for x in CANDS} and new in first_stage_survivors


def test_dropped_shapes_are_nowhere_in_the_map_or_the_candidates() -> None:
    ct = {x.id for ms in c4.cluster_table_v4().values() for x in ms}
    for lid in [*c4.AUDIT4_DROPS, *c4.SECOND_STAGE_DROPS]:
        assert lid not in ct
    # R-9: no round-4 builder enters core.REGISTRY (compass_turns, a pilot lineage kept unchanged since round 3, is there from the start)
    assert not {x.id for x in REGISTRY.get("R1", [])} & {x.id for x in load_fix4()}


def test_no_cluster_spans_both_parts_and_both_parts_are_nonempty() -> None:
    pm = c4.partition_readings_v4()["cluster_keys"]
    for cid, members in c4.cluster_table_v4().items():
        assert len({pm[m.id] for m in members}) == 1, cid
    assert {pm[x.id] for x in FINAL} == {"A", "B"}


def test_the_strict_cluster_map_is_the_round_3_map_restricted_not_changed() -> None:
    table = c4.cluster_table_v4()
    for cid, members in table.items():
        for x in members:
            assert v3.cluster_of_v3(c4.REPAIRED.get(x.id, x.id)) == cid, x.id


# ---------------------------------------------------------------- levels (R-21, R-25 c)


@pytest.mark.parametrize("lin", CANDS, ids=lambda x: x.id)
def test_every_level_of_every_candidate_is_a_distinct_generator(lin) -> None:
    assert level_classes(lin) == [[lv] for lv in range(7)]


def test_the_collapsed_levels_the_audit_named_are_collapsed_in_the_old_builders_and_not_in_the_new() -> None:
    old = {"R1.event_timeline_r5": b3.event_timeline_r5, "R1.temporal_weekday_shift_r5": b3.temporal_weekday_shift_r5, "R1.knights_knaves_r5": c3.knights_knaves_r5,
           "R1.graph_shortest_route_r4": rb.graph_shortest_route_r4, "R1.conditional_decision_tree_r4": rb.conditional_decision_tree_r4}
    from studies.m0.core import Lineage

    for lid, fn in old.items():
        assert len(level_classes(Lineage(lid, "R1", "x", fn))) < 7, lid
    assert len(CANDS) == 14


@pytest.mark.parametrize(
    ("lid", "param", "formula"),
    [
        ("R1.event_timeline_r6", lambda s: len(s["rel"]), lambda lv: 4 + lv + 2 + lv // 3),
        ("R1.temporal_weekday_shift_r6", lambda s: len(s["links"]), lambda lv: 5 + lv + 2 + lv // 3),
        ("R1.spatial_relative_directions_r6", lambda s: len(s["facts"]), lambda lv: 5 + lv + 2 + lv // 3),
        ("R1.equivalence_exchange_rates_r6", lambda s: len(s["rates"]), lambda lv: 3 + lv + 2 + lv // 3),
        ("R1.knights_knaves_r6", lambda s: len(s["people"]), lambda lv: 4 + lv),
        ("R1.graph_shortest_route_r6", lambda s: len(s["towns"]), lambda lv: (3, 3, 4, 4, 5, 5, 6)[lv] + 3 + lv),
        ("R1.conditional_decision_tree_r6", lambda s: len(s["facts"]), lambda lv: (3, 3, 4, 4, 4, 5, 5)[lv] + 2 + lv),
    ],
)
def test_the_stated_level_parameter_of_each_repaired_shape_is_exact_and_rises(lid, param, formula) -> None:
    lin = next(x for x in load_fix4() if x.id == lid)
    vals = []
    for lv in range(7):
        r = random.Random(5000 + lv)
        got = []
        while len(got) < 12:
            try:
                got.append(param(lin.build(lv, r).structured))
            except Retry:
                pass
        assert set(got) == {formula(lv)}, (lid, lv, got)
        vals.append(formula(lv))
    assert vals == sorted(vals) and len(set(vals)) == 7


@pytest.mark.parametrize(
    ("new", "old"),
    [(a4.event_timeline_r6, b3.event_timeline_r5), (a4.temporal_weekday_shift_r6, b3.temporal_weekday_shift_r5), (a4.spatial_relative_directions_r6, b3.spatial_relative_directions_r5),
     (a4.equivalence_exchange_rates_r6, b3.equivalence_exchange_rates_r5), (a4.knights_knaves_r6, c3.knights_knaves_r5), (a4.graph_shortest_route_r6, rb.graph_shortest_route_r4),
     (a4.conditional_decision_tree_r6, rb.conditional_decision_tree_r4)],
)
def test_at_level_zero_the_repaired_builder_is_the_earlier_builder_exactly(new, old) -> None:
    """Level 0 has the same parameter in both builders, so the same stream gives the same items: only the level terms changed."""
    for seed in (1, 2, 3):
        r1, r2 = random.Random(seed), random.Random(seed)
        for _ in range(15):
            try:
                a = new(0, r1)
            except Retry:
                a = None
            try:
                b = old(0, r2)
            except Retry:
                b = None
            assert (a is None) == (b is None)
            if a is not None and b is not None:
                assert (a.question, a.answer) == (b.question, b.answer)


def test_every_candidate_has_a_stated_parameter_entry() -> None:
    import re

    for x in CANDS:
        assert re.sub(r"_r\d+$", "", x.id.split(".", 1)[1]) in PARAM


# ---------------------------------------------------------------- the manifests


def test_survivors_manifest_agrees_with_the_code_and_the_bound() -> None:
    m = json.loads((MAN / "r1_fix4_survivors.json").read_text())
    assert m["bound"] == 0.15 and m["bound_two_sided"] is True
    assert len(m["shapes"]) == 37
    names = {s["name"] for s in m["shapes"]}
    assert names == {*(x.id for x in CANDS), *c4.AUDIT4_DROPS}  # the earlier ids of the repaired shapes appear under their _r6 names
    surv = sorted(s["name"] for s in m["shapes"] if s["status"] == "SURVIVES")
    assert surv == sorted(x.id for x in FINAL)
    assert m["surviving_cluster_count"] == len(c4.cluster_table_v4()) == len(m["surviving_clusters"]) == 10
    for s in m["shapes"]:
        assert s["status"] in ("SURVIVES", "NOT_REGISTERED") and s["reason"] and set(s["per_level"]) == {str(i) for i in range(7)}
        if s["status"] == "SURVIVES":
            assert s["largest"]["excess"] <= 0.15, s["name"]
            assert s["levels_distinct"] == 7


def test_capacity_manifest_has_no_shortfall_and_the_demand_formula_is_the_rulings() -> None:
    m = json.loads((MAN / "r1_fix4_survivors.json").read_text())["capacity"]
    assert (m["G_total"], m["G_part"], m["D_total"], m["D_part_used"]) == (10, 5, 25000, 49000)
    assert m["cells_total"] == 14 and m["cells_with_shortfall"] == 0 and m["cells_with_repeated_text"] == 0
    for cl, levels in m["per_cluster_and_level"].items():
        assert set(levels) == {str(i) for i in range(7)}, cl
        for lv, cell in levels.items():
            assert cell["result"] == "PASS" and cell["supplied"] >= 49000, (cl, lv)
