# ruff: noqa: E501
"""R1 shape revisions (ruling D): each fix has a test that FAILS on the earlier shape and passes on the revision. The bounds are the tests' own, not registered
thresholds. The earlier shapes are asserted to HAVE the defect (documenting it) and the revisions to be free of it. Self-checked only."""

from __future__ import annotations

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters as cl
from studies.m0 import lineages_r1_shortcuts as sc

LINS = {x.id: x for x in cl.all_r1_lineages()}
_CACHE: dict[str, dict] = {}


def _rows(lid: str) -> dict[str, dict]:
    if lid not in _CACHE:
        items = lg.sample_items(LINS[lid], 120, label="rev2-test")
        _CACHE[lid] = {r["heuristic"]: r | {"_items": items} for r in sc.run_battery(LINS[lid], items)["heuristics"]}
    return _CACHE[lid]


def _excess(lid: str, h: str) -> float:
    return _rows(lid)[h]["excess_over_chance"]


def _fires(lid: str, h: str) -> int:
    return _rows(lid)[h]["fires"]


def _items(lid: str):  # type: ignore[no-untyped-def]
    return next(iter(_rows(lid).values()))["_items"]


# (old id, new id, heuristic, old must exceed, new must stay below)  on "excess over chance"
EXCESS = [
    ("R1.kinship_descendants", "R1.kinship_descendants_r2", "parentless_person", 0.5, 0.05),
    ("R1.kinship_ancestor", "R1.kinship_ancestor_r2", "parentless_person", 0.5, 0.05),
    ("R1.elimination_bracket", "R1.elimination_bracket_r2", None, 0.0, 0.0),
    ("R1.containers_queue_line", "R1.containers_queue_line_r2", None, 0.0, 0.0),
    ("R1.graph_shortest_route", "R1.graph_shortest_route_r2", None, 0.0, 0.0),
    ("R1.categories_follow", "R1.categories_follow_r2", "constant_most_frequent_key", 0.3, 0.12),
]


@pytest.mark.parametrize(("old", "new", "h", "old_min", "new_max"), [e for e in EXCESS if e[2]])
def test_shortcut_present_in_the_old_shape_and_gone_in_the_new(old: str, new: str, h: str, old_min: float, new_max: float) -> None:
    assert _excess(old, h) > old_min, (old, h, _excess(old, h))
    assert _excess(new, h) < new_max, (new, h, _excess(new, h))


def test_bracket_runner_up_shortcut_and_its_replacement() -> None:
    assert _rows("R1.elimination_bracket")["runner_up_is_best_of_other_half"]["accuracy_when_fires"] == 1.0
    assert _excess("R1.elimination_bracket_r2", "most_wins_logic") < 0.05
    assert all(it.structured["ask"][0] in ("runner_up", "beaten_by") and len(it.structured["results"]) == len(it.structured["players"]) * (len(it.structured["players"]) - 1) // 2 for it in _items("R1.elimination_bracket_r2"))


def test_queue_last_joiner_shortcut_and_its_replacement() -> None:
    assert _excess("R1.containers_queue_line", "last_joiner_or_last_cutter") > 0.3
    assert _excess("R1.containers_queue_line_r2", "initial_line_position") < 0.1
    assert all(it.structured["ask"][0] == "position" for it in _items("R1.containers_queue_line_r2"))


def test_default_rules_priority_is_always_needed_in_the_revision() -> None:
    assert _fires("R1.categories_default_exceptions", "all_rules_agree") > 150
    assert _fires("R1.categories_default_exceptions_r2", "all_rules_agree") == 0
    assert _fires("R1.categories_default_exceptions_r2", "member_group_rule") == 0
    assert _excess("R1.categories_default_exceptions_r2", "majority_sign") < 0.1


def test_committee_rule_has_no_veto_shortcut_in_the_revision() -> None:
    assert _fires("R1.conditional_threshold_rule", "veto_no_means_no") > 100
    assert all("veto" not in it.question for it in _items("R1.conditional_threshold_rule_r2"))
    assert _excess("R1.conditional_threshold_rule_r2", "yes_count_majority") < 0.12


def test_lamps_asked_is_always_toggled_and_wording_is_fixed() -> None:
    assert _rows("R1.boolean_lights")["never_toggled_means_initial"]["fires"] > 40
    assert _rows("R1.boolean_lights_r2")["never_toggled_means_initial"]["fires"] == 0
    old_bad = [it for it in _items("R1.boolean_lights") if "and the rest are off" in it.question and it.structured["initial"].count(0) == 0]
    new_bad = [it for it in _items("R1.boolean_lights_r2") if "the rest are off" in it.question]
    assert old_bad and not new_bad


def test_equivalence_never_states_the_asked_pair_or_asks_about_an_unmentioned_item() -> None:
    assert _fires("R1.equivalence_classes", "stated_pair") > 100
    assert _fires("R1.equivalence_classes_r2", "stated_pair") == 0
    assert _fires("R1.equivalence_classes", "asked_pair_stated_verbatim") > 100 and _fires("R1.equivalence_classes_r2", "asked_pair_stated_verbatim") == 0
    for it in _items("R1.equivalence_classes_r2"):
        facts = {x for p in [*it.structured["same"], *it.structured["different"]] for x in p}
        assert it.structured["x"] in facts and it.structured["y"] in facts


def test_shortest_route_asks_for_a_length_and_greedy_is_useless() -> None:
    assert _excess("R1.graph_shortest_route", "nearest_neighbour_of_start") > 0.3
    its = _items("R1.graph_shortest_route_r2")
    assert {it.answer_type for it in its} == {"number"} and all(it.k is None for it in its)
    assert _excess("R1.graph_shortest_route_r2", "direct_road_length") < 0.1


def test_stack_piles_wording_and_last_moved_shortcut() -> None:
    def clash(lid: str) -> int:
        return sum(1 for it in _items(lid) if any(f"the {b} pile" in it.question for b in it.structured["initial"] for b in [b.split()[1]] if b in {x for v in it.structured["initial"].values() for x in v}))

    old = [it for it in lg.sample_items(LINS["R1.containers_stack_piles"], 600, label="orange") if "orange" in it.question and "the orange pile" in it.question and any("orange" in v for v in it.structured["initial"].values())]
    assert old, "the earlier shape can name a block like a pile colour"
    assert clash("R1.containers_stack_piles_r2") == 0
    assert _excess("R1.containers_stack_piles", "last_block_moved_onto_asked") > 0.25
    assert _excess("R1.containers_stack_piles_r2", "last_block_moved_onto_asked") < 0.1


def test_grid_walk_states_the_column_convention() -> None:
    assert all("westernmost" not in it.question for it in _items("R1.spatial_grid_walk"))
    assert all("column 1 is the westernmost" in it.question and "westernmost" in it.structured["convention"] for it in _items("R1.spatial_grid_walk_r2"))


def test_categories_follow_states_that_a_group_may_be_empty_and_is_balanced() -> None:
    assert all("may have no members" in it.question for it in _items("R1.categories_follow_r2"))
    assert all("may have no members" not in it.question for it in _items("R1.categories_follow"))
    assert _rows("R1.categories_follow")["constant_most_frequent_key"]["accuracy"] > 0.7
    assert _rows("R1.categories_follow_r2")["constant_most_frequent_key"]["accuracy"] < 0.45


def test_kinship_descendants_answer_is_never_the_parentless_root() -> None:
    for it in _items("R1.kinship_descendants_r2"):
        assert it.answer in it.structured["parent"] and it.answer in it.structured["candidates"]
        assert it.k == len(it.structured["candidates"])
