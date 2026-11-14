"""Synthetic tests for the P7-A analysis (ADR-0013 section 7) on hand-calculated numbers.

Records are fabricated from tiny synthetic simulations with the warm capacity miss counts
overwritten by a rule, so every expected clause below is a hand calculation.
"""

import copy
from collections.abc import Callable
from fractions import Fraction
from functools import cache
from typing import Any

import pytest

from arborlm import p7a_analysis as an
from arborlm import p7a_core as core
from arborlm import p7a_sim as sim
from arborlm.p7a_trace import synthetic_trace

PAIRS = sorted({p for p, _ in core.registered_checkpoints()})
Q = 4 * core.CONTEXT  # small synthetic traces: counted queries = 128
COUNTED = Q // 2


def values(pairs: list[tuple[int, int, int]], numbers: list[int]) -> dict[Any, Fraction]:
    return {p: Fraction(n, COUNTED) for p, n in zip(pairs, numbers, strict=True)}


def const(n: int) -> dict[Any, Fraction]:
    return values(PAIRS, [n] * 27)


# --- ADV clauses ---
def test_adv_exact_threshold_equality_passes_the_mean_clause() -> None:
    clauses = an.adv_clauses(const(10), const(8))  # tree mean = exactly 0.80 * flat mean
    assert clauses["clause_mean_ratio"] is True
    assert clauses["ratio_of_means"] == pytest.approx(0.8)
    assert clauses["holds"] is True
    just_over = an.adv_clauses(const(10), values(PAIRS, [8] * 26 + [9]))
    assert just_over["clause_mean_ratio"] is False  # 8.037 > 8
    assert an.adv_clauses(const(10), values(PAIRS, [8] * 27))["cells_strictly_lower"] == 27


def test_adv_cell_count_boundary_is_22_of_27_and_ties_are_not_lower() -> None:
    flat = const(10)
    for lower, expected in ((22, True), (21, False)):
        tree = values(PAIRS, [1] * lower + [10] * (27 - lower))  # the rest are exact ties
        result = an.adv_clauses(flat, tree)
        assert result["cells_strictly_lower"] == lower
        assert result["cells_tied"] == 27 - lower
        assert result["clause_cells"] is expected


def test_adv_parent_count_boundary_is_8_of_9() -> None:
    flat = const(10)
    # parents are consecutive triples of pairs. One parent tied in every seed: 8 of 9 lower.
    tree = values(PAIRS, [1] * 24 + [10] * 3)
    result = an.adv_clauses(flat, tree)
    assert result["parents_strictly_lower"] == 8 and result["clause_parents"] is True
    assert result["cells_strictly_lower"] == 24
    tree = values(PAIRS, [1] * 21 + [10] * 6)  # two parents tied
    result = an.adv_clauses(flat, tree)
    assert result["parents_strictly_lower"] == 7 and result["clause_parents"] is False
    # a parent whose seeds are mixed counts by its mean: (1 + 1 + 40) / 3 = 14 > 10, not lower
    tree = values(PAIRS, [1] * 24 + [1, 1, 40])
    assert an.adv_clauses(flat, tree)["parents_strictly_lower"] == 8


def test_adv_zero_means_and_ratios_between_means_only() -> None:
    zero = an.adv_clauses(const(0), const(0))
    assert zero["clause_mean_ratio"] is True  # 0 <= 0.8 * 0 ...
    assert zero["clause_cells"] is False and zero["holds"] is False  # ... but every pair ties
    assert zero["ratio_of_means"] is None and zero["cells_tied"] == 27
    tree_only = an.adv_clauses(const(0), const(1))
    assert tree_only["clause_mean_ratio"] is False
    # ratios are of means: 26 pairs at 1/10 of flat, one pair at 100x flat
    flat = const(10)
    tree = values(PAIRS, [1] * 26 + [1000])
    result = an.adv_clauses(flat, tree)
    assert result["cells_strictly_lower"] == 26 and result["clause_cells"] is True
    assert result["clause_mean_ratio"] is False  # (26 + 1000) / 27 = 38 > 8


def test_non_degeneracy_floors_are_exact() -> None:
    # counted = 128: 0.05 = 6.4 / 128, so use the exact floor on another denominator
    flat = {p: Fraction(1, 20) for p in PAIRS}
    tree = {p: Fraction(1, 100) for p in PAIRS}
    assert an.nondegenerate(flat, tree)["non_degenerate"] is True  # equality passes
    below_flat = {p: Fraction(1, 20) - Fraction(1, 10**6) for p in PAIRS}
    result = an.nondegenerate(below_flat, tree)
    assert result["flat_floor_met"] is False and result["non_degenerate"] is False
    below_tree = {p: Fraction(1, 100) - Fraction(1, 10**6) for p in PAIRS}
    assert an.nondegenerate(flat, below_tree)["tree_floor_met"] is False
    assert an.nondegenerate(const(0), const(0))["non_degenerate"] is False
    assert an.nondegenerate(flat, tree)["flat_mean_exact"] == "1/20"


def test_outcome_table() -> None:
    assert an.outcome_for(an.DEGENERATE, an.DEGENERATE) == an.UNRESOLVED
    assert an.outcome_for(an.FAILS, an.HOLDS) == an.NO_ADVANTAGE
    assert an.outcome_for(an.FAILS, an.FAILS) == an.NO_ADVANTAGE
    assert an.outcome_for(an.HOLDS, an.HOLDS) == an.CONC_ONLY
    assert an.outcome_for(an.HOLDS, an.FAILS, robust=True) == "STRUCTURAL ADVANTAGE, robust"
    assert an.outcome_for(an.HOLDS, an.FAILS, robust=False) == "STRUCTURAL ADVANTAGE, not robust"
    # item 9: advantage found but the concentration control cannot be evaluated (reachable only
    # through the frequency-matched flat floor, see the tests below)
    assert an.outcome_for(an.HOLDS, an.DEGENERATE) == an.UNSPECIFIED
    assert an.outcome_for(an.HOLDS, an.DEGENERATE, robust=True) == an.UNSPECIFIED
    assert an.outcome_for(an.FAILS, an.DEGENERATE) == an.NO_ADVANTAGE  # LRU fails first
    assert an.outcome_for(an.DEGENERATE, an.DEGENERATE) == an.UNRESOLVED
    assert an.outcome_for(an.INCOMPLETE, an.INCOMPLETE) == an.INCOMPLETE


# --- fabricated studies ---
@cache
def _base() -> dict[str, dict[str, Any]]:
    out = {}
    for kind, seed in (("flat", 1), ("fixed_tree", 2)):
        selected, branches = synthetic_trace(kind, seed, queries=Q)
        calibration, _ = synthetic_trace(kind, seed + 50, queries=Q)
        record = sim.simulate_checkpoint(
            kind=kind,
            index=0,
            eval_selected=selected,
            eval_branches=branches,
            calibration_selected=calibration,
        )
        out[kind] = {"queries": Q, "record": record}
    return out


Rule = Callable[[str, str, str, int, int], int]


def fabricate(rule: Rule, *, drop: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """81 records whose warm capacity miss counts are ``rule(kind, stream, layout, R, C)``."""
    records: dict[str, dict[str, Any]] = {}
    for pair, kind in core.registered_checkpoints():
        label = core.cell_label(pair, kind)
        if drop and label in drop:
            continue
        rec = copy.deepcopy(_base()["flat" if kind == "flat" else "fixed_tree"])
        rec["label"], rec["kind"], rec["pair"] = label, kind, list(pair)
        rec["outcome"] = "completed"
        rec["record"]["kind"] = kind
        for stream, groups in rec["record"]["streams"].items():
            for key, group in groups.items():
                layout, r = key.split("|R")
                for cap, entry in group["by_c"].items():
                    entry["misses_warm"] = entry["first_touch_warm"] + rule(
                        kind, stream, layout, int(r), int(cap)
                    )
        records[label] = rec
    return records


PRIMARY = (core.PRIMARY_R, core.PRIMARY_C)


def structural_rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
    if kind == "flat":
        return 10
    return 5 if stream == "actual" else 10  # tree advantage vanishes under frequency matching


def test_structural_advantage_and_robustness() -> None:
    result = an.analyze_records(fabricate(structural_rule))
    kinds = result["criteria"]["tree_kinds"]
    for kind in core.TREE_KINDS:
        entry = kinds[kind]
        assert entry["LRU"] == an.HOLDS and entry["CONC"] == an.FAILS
        assert entry["outcome"] == "STRUCTURAL ADVANTAGE, robust"
        assert entry["primary"]["LRU_clauses"]["ratio_of_means"] == pytest.approx(0.5)
        assert entry["primary"]["LRU_clauses"]["cells_strictly_lower"] == 27
        assert entry["primary"]["CONC_clauses"]["ratio_of_means"] == pytest.approx(1.0)
        assert entry["robust_other_settings"]  # other R <= 8 settings hold too
        assert len(entry["robustness_grid"]) == 30
        assert all(g["status"] == "NON-DEGENERATE" for g in entry["robustness_grid"])
    assert result["checkpoints_complete"] == 81 and result["missing_or_failed"] == []


def test_structural_advantage_not_robust_when_other_settings_are_degenerate() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return structural_rule(kind, stream, layout, r, c) if (r, c) == PRIMARY else 0

    kinds = an.analyze_records(fabricate(rule))["criteria"]["tree_kinds"]
    for kind in core.TREE_KINDS:
        assert kinds[kind]["outcome"] == "STRUCTURAL ADVANTAGE, not robust"
        grid = {(g["R"], g["C"]): g for g in kinds[kind]["robustness_grid"]}
        assert grid[PRIMARY]["status"] == "NON-DEGENERATE"
        assert grid[(8, 32)]["status"] == an.DEGENERATE and grid[(8, 32)]["LRU"] == an.DEGENERATE


def test_robust_needs_r_at_most_8() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        if (r, c) == PRIMARY or r >= 32:
            return structural_rule(kind, stream, layout, r, c)
        return 0

    kinds = an.analyze_records(fabricate(rule))["criteria"]["tree_kinds"]
    for kind in core.TREE_KINDS:  # settings with R = 32, 128, 512 do not count toward robust
        assert kinds[kind]["outcome"] == "STRUCTURAL ADVANTAGE, not robust"
        assert kinds[kind]["robust_other_settings"] == []


def test_concentration_only_no_advantage_and_unresolved() -> None:
    def conc(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return 10 if kind == "flat" else 5  # the advantage is the same under frequency matching

    kinds = an.analyze_records(fabricate(conc))["criteria"]["tree_kinds"]
    assert all(kinds[k]["outcome"] == an.CONC_ONLY for k in core.TREE_KINDS)

    def none(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return 10

    kinds = an.analyze_records(fabricate(none))["criteria"]["tree_kinds"]
    assert all(kinds[k]["outcome"] == an.NO_ADVANTAGE for k in core.TREE_KINDS)
    # nothing reaches the floors: UNRESOLVED, not a fail
    kinds = an.analyze_records(fabricate(lambda *a: 0))["criteria"]["tree_kinds"]
    for k in core.TREE_KINDS:
        assert kinds[k]["outcome"] == an.UNRESOLVED
        assert kinds[k]["LRU"] == an.DEGENERATE and kinds[k]["CONC"] == an.DEGENERATE

    # tree below its 0.01 floor (1/128 = 0.0078) while flat is above 0.05
    def low_tree(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return 10 if kind == "flat" else 1

    kinds = an.analyze_records(fabricate(low_tree))["criteria"]["tree_kinds"]
    assert all(kinds[k]["outcome"] == an.UNRESOLVED for k in core.TREE_KINDS)


def test_branch_placement_criterion() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        if kind == "flat":
            return 10
        return 4 if layout == "L-ID" else 10  # L-ID lower than L-RAND, ratio 0.4

    kinds = an.analyze_records(fabricate(rule))["criteria"]["tree_kinds"]
    for k in core.TREE_KINDS:
        br = kinds[k]["branch_placement"]
        assert kinds[k]["BR"] == an.HOLDS == br["BR"]
        assert br["clauses"]["ratio_of_means"] == pytest.approx(0.4)
        assert br["clauses"]["cells_strictly_lower"] == 27

    def tie(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return 10

    kinds = an.analyze_records(fabricate(tie))["criteria"]["tree_kinds"]
    assert all(kinds[k]["BR"] == an.FAILS for k in core.TREE_KINDS)

    def small(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return 0 if layout == "L-ID" else (10 if kind == "flat" else 1)  # L-RAND mean < 0.01

    kinds = an.analyze_records(fabricate(small))["criteria"]["tree_kinds"]
    assert all(kinds[k]["BR"] == an.DEGENERATE for k in core.TREE_KINDS)


def test_l_rand_and_frequency_matched_are_averaged() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        if layout == "L-RAND-91101":
            return 30
        if layout in ("L-RAND-91102", "L-RAND-91103"):
            return 0
        return {"freq_matched_1": 9, "freq_matched_2": 0, "freq_matched_3": 0}.get(stream, 1)

    records = fabricate(rule)
    study = an.Study(records)
    value = study.values("flat", "actual", "L-RAND", 2, 32)
    assert value is not None and all(v == Fraction(10, COUNTED) for v in value.values())
    value = study.values("flat", "freq_matched", "L-FREQ", 2, 32)
    assert value is not None and all(v == Fraction(3, COUNTED) for v in value.values())


def test_missing_and_failed_checkpoints_give_incomplete_without_crashing() -> None:
    missing = {core.cell_label((102, 302, 502), "learned_tree")}
    result = an.analyze_records(fabricate(structural_rule, drop=missing))
    assert result["checkpoints_complete"] == 80
    assert result["missing_or_failed"] == sorted(missing)
    for kind in core.TREE_KINDS:
        entry = result["criteria"]["tree_kinds"][kind]
        assert entry["outcome"] == an.INCOMPLETE
        assert entry["LRU"] == entry["CONC"] == entry["BR"] == an.INCOMPLETE
    # a partial (failed) record is listed as missing too
    records = fabricate(structural_rule)
    label = core.cell_label((101, 301, 501), "flat")
    records[label]["record"]["complete"] = False
    result = an.analyze_records(records)
    assert result["missing_or_failed"] == [label]
    assert result["criteria"]["tree_kinds"]["fixed_tree"]["outcome"] == an.INCOMPLETE
    # nothing at all
    empty = an.analyze_records({})
    assert empty["checkpoints_complete"] == 0 and len(empty["missing_or_failed"]) == 81
    assert empty["criteria"]["tree_kinds"]["learned_tree"]["outcome"] == an.INCOMPLETE
    # garbage entries without a record do not raise
    odd = an.analyze_records({label: {"outcome": "cap_exceeded"}})
    assert label in odd["missing_or_failed"]


def test_descriptive_tables_and_the_decomposition_on_a_known_study() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return {"actual": 2, "order_shuffled": 4}.get(stream, 8 if kind == "flat" else 6)

    result = an.analyze_records(fabricate(rule))
    decomposition = result["descriptive"]["decomposition"]["by_kind_layout_R"]
    cell = decomposition["fixed_tree|L-FREQ|R2"]["warm_capacity_misses_per_query"]["32"]
    assert cell["frequency_matched"] == pytest.approx(6 / COUNTED)
    assert cell["order_shuffled"] == pytest.approx(4 / COUNTED)
    assert cell["actual"] == pytest.approx(2 / COUNTED)
    assert cell["effect_co_selection"] == pytest.approx(-2 / COUNTED)
    assert cell["effect_temporal_order"] == pytest.approx(-2 / COUNTED)
    assert cell["uniform"] is None  # the closed form gives pages per query only
    pages = decomposition["fixed_tree|L-ID|R2"]["pages_per_query"]
    assert pages["effect_concentration"] == pytest.approx(
        pages["frequency_matched"] - pages["uniform"]
    )
    flat_check = result["descriptive"]["flat_layout_report_only"]
    assert flat_check["R2|C32"]["flat_cells"] == 27
    assert "ssd_index_key_reads" in result["descriptive"]
    assert result["descriptive"]["branch_locality"]["fixed_tree"]["cells"] == 27


# --- item 9 (M3): CONC_K on the frequency-matched stream ---
def conc_rule(flat_fm: int, tree_fm: int, *, flat_actual: int = 10, tree_actual: int = 5) -> Rule:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        if stream.startswith("freq_matched"):
            return flat_fm if kind == "flat" else tree_fm
        return flat_actual if kind == "flat" else tree_actual

    return rule


def test_flat_null_below_its_floor_is_degenerate_and_unspecified_when_lru_holds() -> None:
    # counted = 128: 6 / 128 = 0.0469 < 0.05. The actual stream is non-degenerate and LRU holds.
    kinds = an.analyze_records(fabricate(conc_rule(flat_fm=6, tree_fm=3)))["criteria"]["tree_kinds"]
    for kind in core.TREE_KINDS:
        entry = kinds[kind]
        assert entry["LRU"] == an.HOLDS
        assert entry["CONC"] == an.DEGENERATE
        assert entry["primary"]["status"] == "NON-DEGENERATE"  # the actual stream is fine
        assert entry["primary"]["CONC_non_degeneracy"]["flat_floor_met"] is False
        assert entry["outcome"] == an.UNSPECIFIED
        assert "STRUCTURAL" not in entry["outcome"]
        assert not entry["robust_other_settings"]
    # flat null at exactly 7 / 128 = 0.0547 >= 0.05 is evaluated (here: the advantage vanishes)
    kinds = an.analyze_records(fabricate(conc_rule(flat_fm=7, tree_fm=7)))["criteria"]["tree_kinds"]
    assert all(kinds[k]["CONC"] == an.FAILS for k in core.TREE_KINDS)
    # a degenerate flat null never turns a failed LRU_K into anything but NO ADVANTAGE
    rule = conc_rule(flat_fm=0, tree_fm=0, flat_actual=10, tree_actual=10)
    kinds = an.analyze_records(fabricate(rule))["criteria"]["tree_kinds"]
    assert all(kinds[k]["outcome"] == an.NO_ADVANTAGE for k in core.TREE_KINDS)
    # both null means zero: previously a STRUCTURAL ADVANTAGE (the count clauses fail on ties)
    kinds = an.analyze_records(fabricate(conc_rule(0, 0)))["criteria"]["tree_kinds"]
    assert all(kinds[k]["outcome"] == an.UNSPECIFIED for k in core.TREE_KINDS)


def test_only_the_tree_null_below_its_floor_is_evaluated_as_written() -> None:
    # tree null 1 / 128 = 0.0078 < 0.01, flat null 10 / 128 = 0.078 >= 0.05
    kinds = an.analyze_records(fabricate(conc_rule(flat_fm=10, tree_fm=1)))["criteria"][
        "tree_kinds"
    ]
    for kind in core.TREE_KINDS:
        entry = kinds[kind]
        nd = entry["primary"]["CONC_non_degeneracy"]
        assert nd["flat_floor_met"] is True and nd["tree_floor_met"] is False
        assert entry["CONC"] == an.HOLDS  # tree 1 <= 0.8 x 10 and lower in 27 of 27 pairs
        assert entry["outcome"] == an.CONC_ONLY
    # evaluated as written means it can also fail: tree null above 0.8 x flat null
    kinds = an.analyze_records(fabricate(conc_rule(flat_fm=10, tree_fm=10)))["criteria"][
        "tree_kinds"
    ]
    assert all(kinds[k]["outcome"] == "STRUCTURAL ADVANTAGE, robust" for k in core.TREE_KINDS)


def test_degenerate_actual_stream_still_makes_every_criterion_degenerate() -> None:
    kinds = an.analyze_records(fabricate(conc_rule(10, 5, flat_actual=2, tree_actual=0)))
    for kind in core.TREE_KINDS:
        entry = kinds["criteria"]["tree_kinds"][kind]
        assert entry["LRU"] == entry["CONC"] == an.DEGENERATE and entry["outcome"] == an.UNRESOLVED


# --- item 13: per-checkpoint decomposition and the descriptive tables ---
def test_per_checkpoint_decomposition_matches_the_architecture_mean() -> None:
    def rule(kind: str, stream: str, layout: str, r: int, c: int) -> int:
        return {"actual": 2, "order_shuffled": 4}.get(stream, 8 if kind == "flat" else 6)

    decomposition = an.analyze_records(fabricate(rule))["descriptive"]["decomposition"]
    per = decomposition["per_checkpoint"]
    assert len(per) == 81
    label = core.cell_label((102, 302, 502), "fixed_tree")
    cell = per[label]["L-FREQ|R2"]["warm_capacity_misses_per_query"]["32"]
    assert cell["frequency_matched"] == pytest.approx(6 / COUNTED)
    assert cell["actual"] == pytest.approx(2 / COUNTED)
    assert cell["effect_temporal_order"] == pytest.approx(-2 / COUNTED)
    mean_cell = decomposition["by_kind_layout_R"]["fixed_tree|L-FREQ|R2"][
        "warm_capacity_misses_per_query"
    ]["32"]
    assert mean_cell == cell  # constant fabricated values: cell equals the architecture mean
    pages = per[label]["L-ID|R2"]["pages_per_query"]
    assert pages["effect_concentration"] == pytest.approx(
        pages["frequency_matched"] - pages["uniform"]
    )


def test_cold_misses_amplification_curve_and_distinct_pages_per_context_are_tabulated() -> None:
    result = an.analyze_records(fabricate(structural_rule))["descriptive"]
    row = result["cold_misses_and_amplification"]["flat|L-FREQ|R2|C32"]
    base = _base()["flat"]["record"]["streams"]["actual"]["L-FREQ|R2"]["by_c"]["32"]
    assert row["cells"] == 27
    assert row["cold_misses_per_query_whole_stream"] == pytest.approx(base["misses_all"] / Q)
    assert row["first_touch_misses_per_query_whole_stream"] == pytest.approx(
        base["first_touch_all"] / Q
    )
    # fabricated warm capacity misses = 10, first touches are the base record's
    warm = (base["first_touch_warm"] + 10) * 2 / (COUNTED * 8)
    assert row["cached_amplification_all_warm_misses"] == pytest.approx(warm)
    assert row["cached_amplification_warm_capacity_misses"] == pytest.approx(10 * 2 / (COUNTED * 8))
    curve = result["cumulative_distinct_pages"]["fixed_tree|L-ID|R2"]
    assert curve["curve_points_queries"] == [64, 128, 256]
    assert curve["mean_distinct_pages_over_first_n_queries"] == sorted(
        curve["mean_distinct_pages_over_first_n_queries"]
    )
    stats = _base()["fixed_tree"]["record"]["streams"]["actual"]["L-ID|R2"]["stats"]
    assert curve["mean_distinct_pages_per_context"] == pytest.approx(
        stats["distinct_per_context_sum"] / (Q // core.CONTEXT)
    )


def test_eviction_order_sensitivity_table_has_no_criterion() -> None:
    records = fabricate(structural_rule)
    for index, rec in enumerate(records.values()):
        rec["record"]["eviction_order_sensitivity"] = {
            "ascending": {"misses_warm": 20, "first_touch_warm": 10},
            "descending": {"misses_warm": 26 + index % 2, "first_touch_warm": 10},
        }
    result = an.analyze_records(records)
    table = result["descriptive"]["eviction_order_sensitivity"]
    assert "NO criterion" in table["label"]
    fixed = table["by_architecture"]["fixed_tree"]
    assert fixed["cells"] == 27 and fixed["pairs"] == 27
    assert fixed["mean_ascending"] == pytest.approx(10 / COUNTED)
    assert fixed["ascending_ratio_of_means_vs_flat"] == pytest.approx(1.0)  # identical rules
    assert fixed["descending_pairs_strictly_lower_than_flat"] <= 27
    assert len(table["per_checkpoint"]) == 81
    # the outcomes are the same with and without the sensitivity block
    without = an.analyze_records(fabricate(structural_rule))
    for kind in core.TREE_KINDS:
        assert (
            result["criteria"]["tree_kinds"][kind]["outcome"]
            == without["criteria"]["tree_kinds"][kind]["outcome"]
        )
    # records from before the block existed do not raise
    old = fabricate(structural_rule)
    for rec in old.values():
        rec["record"].pop("eviction_order_sensitivity")
    table = an.analyze_records(old)["descriptive"]["eviction_order_sensitivity"]
    assert table["by_architecture"] == {} and table["per_checkpoint"] == {}
