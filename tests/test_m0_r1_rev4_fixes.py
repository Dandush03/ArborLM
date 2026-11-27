# ruff: noqa: E501
"""R1 revision 4: each audited defect is present in the shape it replaces and absent (to the stated bound) in the revision-4 shape (ruling R-1: removed by construction). Failing-first: every
assertion on the NEW shape fails if it is pointed at the OLD one (the first half of each case asserts the old shape's defect). The bounds are this test's own (MEASURED values with a margin),
not registered thresholds. 300 items per level, levels 0 to 6, ``lineage_gates``' test-block seed. Self-checked only."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0 import r1_rev4_battery as bat
from studies.m0.core import ALL_LEVELS, Item
from studies.m0.lineages_r1_rev4_common import REPLACES

LINS = {x.id: x for x in v2.all_lineages_v2()}
_M: dict[str, dict] = {}
_I: dict[str, list[Item]] = {}


def meas(lid: str) -> dict:
    if lid not in _M:
        _M[lid] = bat.measure(LINS[lid], 300)
    return _M[lid]


def items(lid: str) -> list[Item]:
    if lid not in _I:
        _I[lid] = lg.sample_items(LINS[lid], 300, ALL_LEVELS, label="rev4-measure")
    return _I[lid]


def eff(lid: str, h: str, level: str = "all", key: str = "effective_gain") -> float:
    c = meas(lid)["heuristics"].get(h, {}).get(level)
    return 0.0 if c is None else c[key]


# (old id, new id, heuristic, level, metric, old must exceed, new must stay below); metric "effective_gain" unless "gain"
CASES = [
    ("R1.activity_selection", "R1.activity_selection_r4", "M:greedy_by_shortest_duration", "all", "gain", 0.5, 0.05),  # shortest-first greedy (a wrong algorithm): 0.75 -> -0.09
    ("R1.boolean_lights_r2", "R1.boolean_lights_r4", "A:initial_state", "0", "gain", 0.10, 0.09),  # flipping or keeping the initial state at level 0: 0.157 -> 0.05
    ("R1.categories_default_exceptions_r3", "R1.categories_default_exceptions_r4", "M:rule_on_immediate_supergroup_chain1", "all", "effective_gain", 0.30, 0.10),  # the rule on the first-named group: 0.41 -> 0.044
    ("R1.categories_default_exceptions_r3", "R1.categories_default_exceptions_r4", "M:second_most_specific_rule", "all", "effective_gain", 0.10, 0.08),  # 0.18 -> 0.029
    ("R1.categories_follow_r2", "R1.categories_follow_r4", "M:kind_default_all_none_yes_some_no", "all", "effective_gain", 0.20, 0.06),  # the kind of question leaves two answers: 0.27 -> 0.01
    ("R1.categories_follow_r2", "R1.categories_follow_r4", "M:no_sentence_mentions_x_or_y", "all", "effective_gain", 0.20, 0.08),  # 0.31 -> 0.029
    ("R1.conditional_decision_tree", "R1.conditional_decision_tree_r4", "A:most_mentioned", "all", "effective_gain", 0.10, 0.03),  # the most-named action: 0.14 -> 0.0
    ("R1.conditional_threshold_rule_r3", "R1.conditional_threshold_rule_r4", "M:margin_le_zero", "all", "effective_gain", 0.20, 0.06),  # the margin alone: 0.27 (0.45 at level 1) -> 0.02
    ("R1.conditional_threshold_rule_r3", "R1.conditional_threshold_rule_r4", "M:margin_le_zero", "1", "effective_gain", 0.30, 0.08),
    ("R1.conditional_threshold_rule_r3", "R1.conditional_threshold_rule_r4", "M:weighted_yes_ge_no_ignore_margin", "all", "effective_gain", 0.10, 0.06),  # 0.15 -> 0.006
    ("R1.containers_stack_piles_r3", "R1.containers_stack_piles_r4", "M:initial_bottom_of_asked", "all", "effective_gain", 0.09, 0.08),  # 0.12 -> 0.055 (the audit's 0.30 accuracy)
    ("R1.elimination_bracket_r3", "R1.elimination_bracket_r4", "X:round_one_neighbour", "all", "effective_gain", 0.15, 0.02),  # the first-round neighbour: 0.23 -> 0.001
    ("R1.graph_shortest_route_r2", "R1.graph_shortest_route_r4", "M:best_within_two_roads", "all", "gain", 0.4, 0.02),  # two roads: 0.79 -> -0.06
    ("R1.graph_shortest_route_r2", "R1.graph_shortest_route_r4", "M:greedy_nearest_walk", "all", "effective_gain", 0.2, 0.05),  # 0.33 -> 0.008
    ("R1.kinship_descendants_r3", "R1.kinship_descendants_r4", "M:parent_of_most_children_person", "all", "effective_gain", 0.2, 0.03),  # the hub's parent: 0.34 -> 0.003
    ("R1.mst_cost", "R1.mst_cost_r4", "M:sum_of_each_towns_cheapest_road", "all", "gain", 0.3, 0.02),  # each town's cheapest road: 0.50 -> -0.04
    ("R1.mst_cost", "R1.mst_cost_r4", "M:sum_of_each_towns_cheapest_road", "0", "gain", 0.7, 0.02),  # level 0: 0.88 -> -0.08
    ("R1.nim_xor", "R1.nim_xor_r4", "M:largest_exceeds_rest_first", "all", "effective_gain", 0.08, 0.06),  # 0.126 -> 0.026
    ("R1.stable_matching_r2", "R1.stable_matching_r4", "M:asks_second_choice", "all", "effective_gain", 0.15, 0.03),  # the asker's second choice (the redraw's by-product): 0.20 -> 0.001
    ("R1.stable_matching_r2", "R1.stable_matching_r4", "M:receiver_ranking_ask_highest", "all", "effective_gain", 0.15, 0.14),  # 0.18 -> 0.099 (a residual, stated)
]


@pytest.mark.parametrize(("old", "new", "h", "lv", "key", "old_min", "new_max"), CASES)
def test_the_defect_is_in_the_old_shape_and_absent_from_the_new_one(old: str, new: str, h: str, lv: str, key: str, old_min: float, new_max: float) -> None:
    assert REPLACES[new] == old
    assert eff(old, h, lv, key) > old_min, (old, h, lv, eff(old, h, lv, key))
    assert eff(new, h, lv, key) < new_max, (new, h, lv, eff(new, h, lv, key))


def test_order_compare_never_states_the_asked_pair_and_the_old_shape_did() -> None:
    def stated(it: Item) -> bool:
        e = {tuple(f) for f in it.structured["taller"]}
        x, y = it.structured["x"], it.structured["y"]
        return (x, y) in e or (y, x) in e

    old = sum(stated(it) for it in items("R1.order_compare")) / len(items("R1.order_compare"))
    new = sum(stated(it) for it in items("R1.order_compare_r4"))
    assert old > 0.4 and new == 0  # audit: 55.8 % of the old items were decided by one stated fact


def test_kinship_descendants_answer_was_a_child_of_the_root_and_candidates_are_now_one_depth() -> None:
    def root_child(it: Item) -> bool:
        par = it.structured["parent"]
        return par.get(it.answer) not in par

    old = items("R1.kinship_descendants_r3")
    assert sum(root_child(it) for it in old) / len(old) > 0.8  # audit: 86 to 100 % by level
    for it in items("R1.kinship_descendants_r4"):
        par = it.structured["parent"]
        assert {par[c] for c in it.structured["candidates"]} == {it.structured["root"]} and it.structured["root"] in par  # one depth, and the named person is not the root


def test_kinship_ancestor_root_can_be_the_answer_now() -> None:
    def is_root(it: Item) -> bool:
        return it.answer not in it.structured["parent"]

    assert sum(is_root(it) for it in items("R1.kinship_ancestor_r3")) == 0  # the earlier revision: never
    new = items("R1.kinship_ancestor_r4")
    assert 0.03 < sum(is_root(it) for it in new) / len(new) < 0.5


def test_temporal_critical_path_answer_was_always_a_job_nobody_waits_for() -> None:
    old = items("R1.temporal_critical_path")
    assert all(all(it.answer not in deps for _, _, deps in it.structured["jobs"]) for it in old)  # inherent to "who finishes last"
    assert all(it.answer_type == "number" and it.k is None for it in items("R1.temporal_critical_path_r4"))
    assert eff("R1.temporal_critical_path", "A:longest_job", "all", "gain") > 0.08 or eff("R1.temporal_critical_path", "longest_job", "all", "gain") > 0.08  # the possessive bug had hidden +0.12
    assert max((c["gain"] for h, row in meas("R1.temporal_critical_path_r4")["heuristics"].items() for k, c in row.items() if k == "all" and c["fires"] >= 100), default=0) < 0.03


def _depth(t: object) -> int:
    return 0 if isinstance(t, int) else 1 + _depth(t[0])  # type: ignore[index]


def test_minimax_levels_were_identical_generators_and_are_now_all_distinct() -> None:
    by_old = {lv: {_depth(it.structured["tree"]) for it in items("R1.minimax_tree") if it.level == lv} for lv in ALL_LEVELS}
    assert by_old[0] == by_old[1] == by_old[2] and by_old[3] == by_old[4] and by_old[5] == by_old[6]  # audit: L0=L1=L2, L3=L4, L5=L6
    shapes = {lv: {(it.structured["depth"], it.structured["branching"]) for it in items("R1.minimax_tree_r4") if it.level == lv} for lv in ALL_LEVELS}
    assert all(len(v) == 1 for v in shapes.values()) and len({next(iter(v)) for v in shapes.values()}) == 7
    assert {it.structured["first"] for it in items("R1.minimax_tree_r4")} == {"max", "min"}
    assert any(c["gain"] > 0 for c in [meas("R1.minimax_tree_r4")["heuristics"]["X:median_leaf_low"]["0"]])  # the order-statistic reading stays (honest mathematics), stated in the plan


def test_nim_levels_differ_in_structure_and_level_zero_has_capacity() -> None:
    old_k = {lv: {len(it.structured["piles"]) for it in items("R1.nim_xor") if it.level == lv} for lv in ALL_LEVELS}
    assert old_k[0] == old_k[1] == old_k[2] == {3}  # levels 0 to 2 differ only in size
    new = {lv: {(len(it.structured["piles"]), it.structured["size_class"]) for it in items("R1.nim_xor_r4") if it.level == lv} for lv in ALL_LEVELS}
    assert len({next(iter(v)) for v in new.values()}) == 7
    # distinct unordered pile tuples at level 0 of the old shape were few (audit: 270 ordered 'second' tuples); the new level 0 reaches 1,000 distinct multisets at once
    seen = {tuple(sorted(it.structured["piles"])) for it in lg.sample_items(LINS["R1.nim_xor_r4"], 1500, (0,), label="nim-cap")}
    assert len(seen) >= 1000


def test_venn_levels_were_magnitude_only_and_now_differ_in_groups_and_question() -> None:
    old_g = {lv: {len(it.structured["groups"]) for it in items("R1.venn_counting") if it.level == lv} for lv in ALL_LEVELS}
    assert old_g[0] == old_g[1] == {2} and all(old_g[lv] == {3} for lv in range(2, 7))
    new = {lv: {(len(it.structured["groups"]), it.structured["ask"]) for it in items("R1.venn_counting_r4") if it.level == lv} for lv in ALL_LEVELS}
    assert all(len(v) == 1 for v in new.values()) and len({next(iter(v)) for v in new.values()}) == 7


def test_topological_prerequisites_are_denser() -> None:
    def mean_deps(lid: str) -> float:
        its = items(lid)
        return sum(len(d) for it in its for _, d in it.structured["jobs"]) / sum(len(it.structured["jobs"]) for it in its)

    assert mean_deps("R1.topological_order_r4") > mean_deps("R1.topological_order_r2") + 0.4


def test_categories_follow_states_what_no_means_and_every_answer_is_reachable_for_every_kind() -> None:
    assert not any("must be false" in it.question for it in items("R1.categories_follow_r2"))  # the earlier frame did not say what "no" means
    assert all("must be false" in it.question and "must be true" in it.question for it in items("R1.categories_follow_r4"))
    c: Counter[tuple[str, str]] = Counter((it.structured["kind"], it.answer) for it in items("R1.categories_follow_r4"))
    assert len(c) == 9 and min(c.values()) > 100  # three kinds x three answers, each well represented out of 2,100
    old = Counter((it.structured["kind"], it.answer) for it in items("R1.categories_follow_r2"))
    assert len(old) < 9  # the earlier shape: "some" was never "yes" (and "all"/"none" never "no")


def test_boolean_lights_start_sentence_no_longer_says_every_other() -> None:
    assert any("every other lamp is off" in it.question for it in items("R1.boolean_lights_r2"))
    assert not any("every other" in it.question for it in items("R1.boolean_lights_r4"))
    assert any("not named here are off" in it.question for it in items("R1.boolean_lights_r4"))


def test_instant_runoff_plurality_leader_wins_a_minority_of_the_time_at_every_level() -> None:
    by = {lv: [it for it in items("R1.instant_runoff_r4") if it.level == lv] for lv in ALL_LEVELS}
    for lv, its in by.items():
        share = sum(1 for it in its if it.answer == max(it.structured["candidates"], key=lambda c: sum(n for n, rk in it.structured["ballots"] if rk[0] == c))) / len(its)
        assert 0.1 < share < 0.6, (lv, share)  # a coin flip among 4 to 6 candidates, not 79 %
        assert all(len(it.structured["candidates"]) >= 4 for it in its)


def test_no_revision_4_module_conditions_items_on_a_heuristic_outcome() -> None:
    """Ruling R-1: no import of the redraw machinery (credit, ANTI_P, anti_override, the retuned probabilities) in any revision-4 module, and no call of a heuristic function."""
    for name in ("lineages_r1_rev4", "lineages_r1_rev4_b", "lineages_r1_rev4_c", "lineages_r1_rev4_common"):
        src = (Path(__file__).resolve().parents[1] / f"studies/m0/{name}.py").read_text()
        code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
        # drop docstrings (they may name the withdrawn machinery); keep code
        code = re.sub(r'"""(?:.|\n)*?"""', "", code)
        for banned in ("lineages_r1_shortcuts", "lineages_r1_rev3", "lineages_r1_rev2", "lineages_r1_new2", "ANTI_P", "anti_override", "credit(", "SPECIFIC", "generic("):
            assert banned not in code, (name, banned)
