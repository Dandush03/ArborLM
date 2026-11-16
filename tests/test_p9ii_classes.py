# ruff: noqa: E501
"""P9II classes and analysis (ADR-0019 section 8): every cell condition, class, annotation, paired reading, gate, outcome row and estimator on synthetic
measurements, and the whole analysis on synthetic records of the FULL registry (128 Stage 1 cells, Stage 2 and 3), including missing cells, failed gates, non-finite
values, NOT_EVALUATED draws and a reserve-draw substitution. Self-check only: not independent review, not Astra validation, not human approval."""

import itertools
import json
import math
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9ii import analysis as A  # noqa: E402
from studies.p9ii import classes as C  # noqa: E402
from studies.p9ii import core  # noqa: E402

GOOD = dict(acc_a=0.95, acc_b=0.95, dep_chance_a=True, dep_chance_b=True, h1=0.93, h2=0.93, leakage=False, distinct_top1=200, largest_share=0.01, probe_facts=256, lm_rise=0.10, address_stability=0.9, recall_top8=0.95)
A6REF = C.A6Reference(0.99, 0.99, 0.10)


def obs(**kw: object) -> C.Observation:
    return C.Observation(**{**GOOD, **kw})  # type: ignore[arg-type]


def verdict(success: bool | None) -> C.CellVerdict:
    return C.CellVerdict(C.CELL_NOT_EVALUATED if success is None else (C.SUCCEEDED if success else C.FAILED))


def verdicts(pattern: Callable[[int, int], bool | None], draws: tuple[int, ...] = core.STAGE_DRAWS[1]) -> dict[C.CellKey, C.CellVerdict]:
    return {(d, j): verdict(pattern(d, j)) for d in draws for j in (0, 1)}


# --- cell success (8.3) ---------------------------------------------------------------------------------------------------------
def test_cell_conditions_each_fail_alone() -> None:
    assert C.cell_verdict(obs(), A6REF).status == C.SUCCEEDED
    cases = {
        1: dict(acc_a=0.5),
        2: dict(dep_chance_b=False),
        3: dict(distinct_top1=100),
        4: dict(h2=0.5),
        5: dict(leakage=True),
    }
    for number, change in cases.items():
        v = C.cell_verdict(obs(**change), A6REF)
        assert v.status == C.FAILED and v.failed_conditions == (number,)
    assert C.cell_verdict(obs(largest_share=0.0201), A6REF).failed_conditions == (3,)
    assert C.cell_verdict(obs(distinct_top1=128), A6REF).status == C.SUCCEEDED  # exactly 0.50 x 256
    assert C.cell_verdict(obs(acc_a=math.nan), A6REF).failed_conditions[0] == 1  # a NaN never satisfies a condition


def test_not_evaluated_when_a6_missing_or_low() -> None:
    assert C.cell_verdict(obs(), None).status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(obs(), C.A6Reference(0.89, 0.99, 0.1)).status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(obs(), C.A6Reference(0.99, 0.5, 0.1)).status == C.CELL_NOT_EVALUATED
    assert C.cell_verdict(obs(), C.A6Reference(math.nan, 0.99, 0.1)).status == C.CELL_NOT_EVALUATED


def test_condition_one_is_relative_to_a6_on_the_same_panel() -> None:
    ref = C.A6Reference(1.0, 1.0, 0.1)
    assert C.cell_verdict(obs(acc_a=0.90, acc_b=0.90, h1=0.82, h2=0.82), ref).status == C.SUCCEEDED
    assert C.cell_verdict(obs(acc_a=0.899), ref).failed_conditions == (1,)


def test_lm_flag_is_relative_to_a6_plus_margin() -> None:
    assert not C.lm_flagged(0.15, 0.10)  # equal to A6 + 0.05 is not above it
    assert C.lm_flagged(0.1501, 0.10)
    assert C.lm_flagged(math.inf, 0.10) and C.lm_flagged(math.nan, 0.10)
    assert not C.lm_flagged(5.0, math.nan)
    assert C.cell_verdict(obs(lm_rise=0.30), A6REF).lm_flagged


# --- arm class (8.4) -------------------------------------------------------------------------------------------------------------
def klass(stage: int, pattern: Callable[[int, int], bool | None], lm: Callable[[int, int], bool] = lambda d, j: False) -> C.ArmClass:
    draws = core.STAGE_DRAWS[stage]
    vs = {(d, j): C.CellVerdict(verdict(pattern(d, j)).status, (), lm(d, j)) for d in draws for j in (0, 1)}
    return C.arm_class("A0", stage, vs, list(vs))


def test_every_arm_class_and_the_boundaries() -> None:
    assert klass(1, lambda d, j: True).cls == C.RELIABLE
    assert klass(1, lambda d, j: (d, j) != (1, 0)).cls == C.RELIABLE  # one failed cell
    assert klass(1, lambda d, j: (d, j) not in ((1, 0), (1, 1))).cls == C.UNRELIABLE  # two failed
    assert klass(1, lambda d, j: d <= 2).cls == C.UNRELIABLE  # four successes
    assert klass(1, lambda d, j: d == 1 or (d, j) == (2, 0)).cls == C.FAILS  # three successes
    assert klass(1, lambda d, j: None if d == 1 else True).cls == C.RELIABLE  # 14 evaluated cells
    assert klass(1, lambda d, j: None if d <= 2 else True).cls == C.NOT_EVALUATED  # 12 evaluated
    assert klass(2, lambda d, j: True).cls == C.RELIABLE
    assert klass(2, lambda d, j: None if d == 9 else True).cls == C.NOT_EVALUATED  # any NOT_EVALUATED draw at Stage 2
    assert klass(2, lambda d, j: d in (9, 10) and False).cls == C.FAILS  # none
    assert klass(2, lambda d, j: d == 9).cls == C.UNRELIABLE  # two successes
    assert klass(2, lambda d, j: (d, j) == (9, 0)).cls == C.FAILS  # one success
    with pytest.raises(ValueError):
        klass(3, lambda d, j: True)


def test_lm_capability_reduced_blocks_reliable_and_is_printed() -> None:
    c = klass(1, lambda d, j: True, lambda d, j: d == 1)  # two flagged cells
    assert c.lm_reduced and c.cls == C.UNRELIABLE and c.label == C.UNRELIABLE_LM
    one = klass(1, lambda d, j: True, lambda d, j: (d, j) == (1, 0))  # one flagged cell is tolerated
    assert not one.lm_reduced and one.cls == C.RELIABLE
    many_failures = klass(1, lambda d, j: d <= 2, lambda d, j: True)
    assert many_failures.cls == C.UNRELIABLE and many_failures.lm_reduced and many_failures.label == C.UNRELIABLE


# --- paired reading, negative control ---------------------------------------------------------------------------------------------
def test_paired_labels_and_sign_test() -> None:
    a0 = verdicts(lambda d, j: False)
    assert C.paired_against_a0("A1", verdicts(lambda d, j: d <= 2), a0).label == C.IMPROVES  # d = 4
    assert C.paired_against_a0("A1", verdicts(lambda d, j: d <= 2 and j == 0), a0).label == C.NOT_DISTINGUISHED  # d = 2 (below 4)
    harmed = C.paired_against_a0("A1", a0, verdicts(lambda d, j: d <= 2))
    assert harmed.label == C.HARMS and harmed.d == -4
    same = C.paired_against_a0("A1", a0, a0)
    assert same.label == C.NOT_DISTINGUISHED and same.p_value == 1.0
    p = C.paired_against_a0("A1", verdicts(lambda d, j: d <= 2), a0)
    assert p.x_only == 4 and p.a0_only == 0 and p.p_value == pytest.approx(2 * 0.5**4)
    assert C.sign_test_p(5, 5) == 1.0 and C.sign_test_p(0, 0) == 1.0
    # cells that are NOT_EVALUATED in either arm are not paired
    assert C.paired_against_a0("A1", verdicts(lambda d, j: None), a0).pairs == 0


def test_d_equals_the_difference_of_successes_over_the_paired_cells() -> None:
    """Over the same paired cells d(X) = successes(X) - successes(A0), so the clause "and X has more successes than A0" follows from d >= 4 (a redundancy
    of the ADR's rule, recorded here; the code still applies both)."""
    a0 = verdicts(lambda d, j: j == 1)
    x = verdicts(lambda d, j: j == 0 and d <= 6 or j == 1 and d > 6)
    p = C.paired_against_a0("A4", x, a0)
    assert p.d == p.x_successes - p.a0_successes == 0 and p.label == C.NOT_DISTINGUISHED
    x2 = verdicts(lambda d, j: j == 0 or d <= 2)
    p2 = C.paired_against_a0("A4", x2, a0)
    assert p2.d == p2.x_successes - p2.a0_successes and p2.label == (C.IMPROVES if p2.d >= 4 else C.NOT_DISTINGUISHED)


def test_negative_control_failed_cases() -> None:
    rel = C.ArmClass("A1-S", 1, C.RELIABLE, C.RELIABLE, 16, 16, 0, 0, False, 16, 0)
    unrel = C.ArmClass("A1-S", 1, C.UNRELIABLE, C.UNRELIABLE, 16, 8, 8, 0, False, 16, 0)
    imp = C.Paired("A1-S", C.IMPROVES, 4, 4, 0, 8, 4, 16, 0.1)
    nd = C.Paired("A1-S", C.NOT_DISTINGUISHED, 0, 0, 0, 8, 8, 16, 1.0)
    assert C.negative_control_failed(rel, nd)  # RELIABLE alone fails the control
    assert C.negative_control_failed(unrel, imp)  # improving alone fails it
    assert not C.negative_control_failed(unrel, nd)  # UNRELIABLE and not distinguished is not a failure
    assert not C.negative_control_failed(None, None)


# --- the gates between stages --------------------------------------------------------------------------------------------------------
def ac(arm: str, cls: str, stage: int = 1) -> C.ArmClass:
    return C.ArmClass(arm, stage, cls, cls, 16, 16 if cls == C.RELIABLE else 5, 0 if cls == C.RELIABLE else 11, 0, False, 16, 0)


def test_stage1_gate_is_a_pure_function_of_the_classes() -> None:
    reliable = {a: ac(a, C.RELIABLE) for a in core.LEARNED_ARMS}
    g = C.stage1_gate(reliable, False)
    assert g.run and g.advancing == ["A5-C", "A5-D"] and g.arms == ["A0", "A5-C", "A5-D"]  # the first two in the order, A1-S never
    only_a0 = {a: ac(a, C.FAILS) for a in core.LEARNED_ARMS} | {"A0": ac("A0", C.RELIABLE)}
    g = C.stage1_gate(only_a0, False)
    assert g.run and g.advancing == [] and g.arms == ["A0"]  # Stage 2 with A0 alone
    supervised = {a: ac(a, C.FAILS) for a in core.LEARNED_ARMS} | {"A2": ac("A2", C.RELIABLE), "A1": ac("A1", C.RELIABLE)}
    g = C.stage1_gate(supervised, False)
    assert g.run and g.advancing == ["A2", "A1"] and g.arms == ["A0", "A2", "A1", "A1-S"]  # A1-S runs with a supervised arm
    g = C.stage1_gate(supervised, True)
    assert not g.run and g.advancing == []  # NEGATIVE CONTROL FAILED: A1 and A2 do not advance
    g = C.stage1_gate({"A4": ac("A4", C.RELIABLE), "A0": ac("A0", C.UNRELIABLE)}, False)
    assert g.run and g.advancing == ["A4"]
    none = C.stage1_gate({a: ac(a, C.UNRELIABLE) for a in core.LEARNED_ARMS}, False)
    assert not none.run and C.NOT_RUN_NO_ARM in none.reason
    # A1-S RELIABLE alone never advances
    assert not C.stage1_gate({a: ac(a, C.FAILS) for a in core.LEARNED_ARMS} | {"A1-S": ac("A1-S", C.RELIABLE)}, False).run


def test_stage3_gate_selection_and_scheduled_arms() -> None:
    def c16(**kw: str) -> dict[str, C.ArmClass]:
        return {a: ac(a, kw.get(a.replace("-", "_"), C.FAILS), 2) for a in core.LEARNED_ARMS}

    assert C.stage3_gate(c16(A0=C.RELIABLE), False, C.COMPLETE) == ("A0", "run", None)
    assert C.stage3_gate(c16(A5_C=C.RELIABLE, A1=C.RELIABLE), False, C.COMPLETE) == ("A5-C", "run", None)
    assert C.stage3_gate(c16(A4=C.RELIABLE, A1=C.RELIABLE), False, C.COMPLETE) == ("A4", "not run", C.NOT_RUN_SCHEDULED)  # no later arm substituted
    assert C.stage3_gate(c16(A2=C.RELIABLE), False, C.COMPLETE)[2] == C.NOT_RUN_SCHEDULED
    assert C.stage3_gate(c16(A2=C.RELIABLE, A1=C.RELIABLE), True, C.COMPLETE) == (None, "not run", C.NOT_RUN_NO_ARM)  # A1 and A2 skipped
    assert C.stage3_gate(c16(A1=C.RELIABLE), True, C.COMPLETE)[0] is None
    assert C.stage3_gate(c16(), False, C.COMPLETE)[2] == C.NOT_RUN_NO_ARM
    assert C.stage3_gate(c16(A0=C.RELIABLE), False, C.INCOMPLETE)[1] == "not run"


def test_scale_probe_labels() -> None:
    assert C.scale_probe({(13, 0): verdict(True), (14, 0): verdict(True)})["label"] == C.SCALE_POSITIVE
    r = C.scale_probe({(13, 0): verdict(True), (14, 0): verdict(False)})
    assert r["label"] == C.SCALE_UNINFORMATIVE and r["successes"] == 1
    assert C.scale_probe({(13, 0): verdict(True), (14, 0): verdict(None)})["label"] == C.SCALE_UNINFORMATIVE


# --- the training-time categories (8.1) ----------------------------------------------------------------------------------------------------
def pts(distinct: list[int], share: float = 0.01, facts: int = 256) -> list[C.ProbePoint]:
    return [C.ProbePoint(64 * (i + 1), n, share, facts, 0.99 if n < 32 else 0.2, 0.05, 0.5) for i, n in enumerate(distinct)]


def test_four_categories_never_merged() -> None:
    assert C.category_of(pts([200, 210, 220])).name == C.NEVER_SEPARATED
    assert C.category_of(pts([60, 70, 90])).name == C.NEVER_NOT_SEPARATED  # an untrained query is not separated (0.33 x probe facts)
    assert C.category_of(pts([200, 2, 3, 200, 210])).name == C.COLLAPSED_RECOVERED
    assert C.category_of(pts([200, 2, 3, 60, 70])).name == C.COLLAPSED_NOT_RECOVERED
    assert C.category_of(pts([200, 200], share=0.5)).name == C.NEVER_NOT_SEPARATED  # a hub slot is not separated
    c = C.category_of(pts([200, 2, 3, 200, 210]))
    assert c.onset == 128 and c.escape == 256  # the first later record from which separation holds to the end
    assert C.category_of(pts([200, 2, 200, 200, 3])).name == C.COLLAPSED_NOT_RECOVERED  # it must hold to the end


def test_onset_is_slot_based_and_cosine_is_reported_only() -> None:
    points = [C.ProbePoint(64, 33, 0.01, 256, 0.99, 0.0, 0.0), C.ProbePoint(128, 32, 0.01, 256, 0.1, 0.0, 0.0), C.ProbePoint(192, 200, 0.01, 256, 0.1, 0.0, 0.0)]
    c = C.category_of(points)
    assert c.onset == 128  # at most 32 distinct top-1 slots, whatever the cosine
    assert c.cosine_onset == 64 and c.cosine_escape == 128


def test_first_success_sustained_and_gradient_ratio() -> None:
    points = [C.ProbePoint(64 * i, 100, 0.01, 256, 0.1, a, 0.0) for i, a in enumerate([0.1, 0.5, 0.95, 0.92, 0.97], start=1)]
    assert C.first_success_update(points, 0.9) == 192
    assert C.sustained_success(points, 0.9) is True
    dips = [*points[:3], C.ProbePoint(256, 100, 0.01, 256, 0.1, 0.80, 0.0)]  # below the line by more than 0.05
    assert C.sustained_success(dips, 0.9) is False
    assert C.sustained_success(points[:2], 0.9) is None and C.first_success_update(points[:2], 0.9) is None
    ups = [{"update": u, "grad_norm": {"wq": 0.001, "wo": 1.0}} for u in (63, 64, 500, 1024, 1025)]
    assert C.gradient_ratio(ups) == pytest.approx(0.001)
    assert math.isnan(C.gradient_ratio([{"update": 5, "grad_norm": {"wq": 1.0, "wo": 1.0}}]))


def test_summarize_training_a2_clauses_and_onset() -> None:
    updates = [{"update": u, "grad_norm": {"wq": 0.01, "wo": 1.0}, "param_change_norm": {"wq": 0.1, "keys": 0.2}} for u in range(1, 129)]
    diag = [{"update": 64, "distinct_top1": 200, "largest_top1_share": 0.01, "probe_facts": 256, "probe_accuracy": 0.9, "target_top8_recall": 0.9}, {"update": 128, "distinct_top1": 2, "largest_top1_share": 0.9, "probe_facts": 256, "probe_accuracy": 0.04, "target_top8_recall": 0.1}]
    readout = C.ProbePoint(128, 2, 0.9, 256, 0.99, 0.04, 0.1)
    s = C.summarize_training("A2", updates, diag, readout, 0.9, u_pre=64, succeeded=True)
    assert s.supervision_acc_drop and s.supervision_collapse and s.category.name == C.COLLAPSED_NOT_RECOVERED and s.onset_within_256
    assert s.remapped and s.movement_after_removal == pytest.approx(64 * 0.3)
    assert C.path_after(s.path, 64) == pytest.approx(64 * 0.3)
    a0 = C.summarize_training("A0", updates, diag, readout, 0.9)
    assert a0.supervision_acc_drop is None and a0.movement_after_removal is None
    assert C.cumulative_path([]) == ()


# --- annotations ---------------------------------------------------------------------------------------------------------------------------
def summary(**kw: object) -> C.TrainingSummary:
    base = dict(category=C.Category(C.NEVER_SEPARATED, None, None, None, None), onset_within_256=False, gradient_ratio=0.5, first_success=64, sustained=True)
    return C.TrainingSummary(**{**base, **kw})  # type: ignore[arg-type]


def test_supervision_dependent_needs_more_than_half_of_the_cells() -> None:
    collapse = summary(supervision_collapse=True, supervision_acc_drop=False)
    fine = summary(supervision_collapse=False, supervision_acc_drop=False)
    half = {(d, j): (collapse if (d, j) in [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (4, 1)] else fine) for d in range(1, 9) for j in (0, 1)}
    assert C.supervision_dependent(half)["label"] is None  # exactly half
    half[(5, 0)] = collapse
    assert C.supervision_dependent(half)["label"] == C.SUPERVISION_DEPENDENT
    only_accuracy = {k: summary(supervision_collapse=False, supervision_acc_drop=True) for k in half}
    assert C.supervision_dependent(only_accuracy)["label"] == C.SUPERVISION_DEPENDENT  # the accuracy clause exists, though A2 cannot trigger it


def test_address_recall_and_stable_labels() -> None:
    cells = {(d, 0): obs(recall_top8=0.9, address_stability=0.8) for d in range(1, 9)}
    a = C.address_labels(cells, "A1")
    assert a["recall"]["label"] == C.ADDRESS_RECALL and a["stable"]["label"] == C.ADDRESS_STABLE  # thresholds are inclusive
    low = {(d, 0): obs(recall_top8=0.89, address_stability=0.79) for d in range(1, 9)}
    b = C.address_labels(low, "A2")
    assert b["recall"]["label"] is None and b["stable"]["label"] is None
    assert "recall" not in C.address_labels(cells, "A0")  # recall exists for A1 and A2 only


def test_dense_comparison_three_labels() -> None:
    draws = {d: 0.9 for d in range(1, 9)}
    assert C.dense_comparison({d: 0.99 for d in draws}, {d: 0.5 for d in draws})["label"] == C.BEATS_DENSE
    assert C.dense_comparison({d: 0.99 for d in draws}, {d: 0.95 for d in draws})["label"] == C.DENSE_AT_CEILING  # 1.10 cannot be reached
    assert C.dense_comparison({d: 0.9 for d in draws}, {d: 0.85 for d in draws})["label"] == C.DENSE_SUFFICES
    r = C.dense_comparison({1: 0.9, 2: 0.9}, {1: 0.8, 2: 0.95})
    assert r["draws_arm_higher"] == 1 and r["differences"]["1"] == pytest.approx(0.1)
    assert C.dense_comparison({1: 0.5}, {1: 0.0})["median_ratio"] == math.inf


# --- estimators (8.7) -------------------------------------------------------------------------------------------------------------------------
def test_clopper_pearson_bounds_of_section_5() -> None:
    assert C.clopper_pearson_lower(8, 8) == pytest.approx(0.05 ** (1 / 8), abs=1e-9)  # the ADR's 0.69
    assert round(C.clopper_pearson_lower(8, 8), 2) == 0.69 and round(C.clopper_pearson_lower(7, 8), 2) == 0.53 and round(C.clopper_pearson_lower(4, 4), 2) == 0.47
    lo, hi = C.clopper_pearson(3, 8)
    assert 0 < lo < 3 / 8 < hi < 1 and C.clopper_pearson_upper(8, 8) == 1.0 and C.clopper_pearson_lower(0, 8) == 0.0


def test_permutation_test_matches_brute_force() -> None:
    for per_draw in ([2, 0, 1], [2, 2, 0, 1], [1, 1, 1], [0, 0]):
        d, s = len(per_draw), sum(per_draw)
        observed = sum(1 for v in per_draw if v != 1)
        stats = []
        for chosen in itertools.combinations(range(2 * d), s):
            counts = [sum(1 for c in chosen if c // 2 == i) for i in range(d)]
            stats.append(sum(1 for v in counts if v != 1))
        expected_p = sum(1 for x in stats if x >= observed) / len(stats)
        got = C.permutation_test_clustering(per_draw)
        assert got["p_value"] == pytest.approx(expected_p) and got["null_mean"] == pytest.approx(sum(stats) / len(stats))
    assert C.permutation_test_clustering([])["draws"] == 0


def test_anova_and_draw_sensitivity_table() -> None:
    r = C.anova_log_escape({1: [100, 110], 2: [1000, 900], 3: [None, 300], 4: [500, 520]})
    assert r["draws_used"] == 3 and r["censored_cells"] == 1 and r["ms_between"] > r["ms_within"]
    assert math.isnan(C.anova_log_escape({1: [None, None]})["ms_between"])
    vs = verdicts(lambda d, j: d <= 3 or (d == 4 and j == 0))
    sums = {k: summary(category=C.Category(C.COLLAPSED_RECOVERED, 64, 640 if k[0] % 2 else None, None, None)) for k in vs}
    ds = C.draw_sensitivity("A0", vs, sums, 8192)
    assert ds["draw_counts"] == {"2/2": 3, "1/2": 1, "0/2": 4} and ds["discordance_rate"] == 1 / 8 and ds["failure_rate"] == 5 / 8
    assert ds["escape_censored_cells"] == 8 and ds["median_escape_update_censored_at_readout"] > 0
    assert ds["sustained_success_frequency"] == 1.0 and ds["first_success_cells"] == 16
    assert ds["table"]["4"] == {"0": C.SUCCEEDED, "1": C.FAILED}


# --- outcomes and readings (8.6) ----------------------------------------------------------------------------------------------------------------
def size(stage: int, classes: dict[str, str], paired: dict[str, str] | None = None, nc: bool = False) -> C.SizeAnalysis:
    s = C.SizeAnalysis(stage, {a: ac(a, c, stage) for a, c in classes.items()}, {}, nc)
    for arm, label in (paired or {}).items():
        s.paired[arm] = C.Paired(arm, label, 4, 4, 0, 8, 4, 16, 0.1)
    return s


FAILS_ALL = dict.fromkeys(core.LEARNED_ARMS, C.FAILS)


def test_every_outcome_row() -> None:
    row = lambda o: o.row  # noqa: E731
    assert row(C.study_outcome(size(1, FAILS_ALL | {"A0": C.NOT_EVALUATED}), None, C.NOT_RUN_NO_ARM)) == 2
    assert C.study_outcome(size(1, FAILS_ALL, nc=True), None, C.NOT_RUN_NO_ARM).row == 2  # NEGATIVE CONTROL FAILED, no label-free arm RELIABLE
    only_a1 = size(1, FAILS_ALL | {"A1": C.RELIABLE}, nc=True)
    assert C.study_outcome(only_a1, None, C.NOT_RUN_NO_ARM).row == 2
    a0 = C.study_outcome(size(1, FAILS_ALL | {"A0": C.RELIABLE}), size(2, {"A0": C.RELIABLE}), C.COMPLETE)
    assert a0.row == 3 and a0.outcome == C.ANSWER_ONLY_RELIABLE and "(LABEL-FREE)" in a0.label and "Stage 2 status COMPLETE" in a0.label and "A0's Stage 2 class RELIABLE" in a0.label
    s1 = size(1, FAILS_ALL | {"A5-C": C.RELIABLE}, {"A5-C": C.IMPROVES})
    o4 = C.study_outcome(s1, size(2, {"A5-C": C.RELIABLE}, {"A5-C": C.NOT_DISTINGUISHED}), C.COMPLETE)
    assert o4.row == 4 and "A5-C (LABEL-FREE)" in o4.label and C.IMPROVES in o4.label and C.NOT_DISTINGUISHED in o4.label  # the row does not require IMPROVES at 16,384
    o5 = C.study_outcome(s1, size(2, {"A5-C": C.UNRELIABLE}), C.COMPLETE)
    assert o5.row == 5 and o5.outcome == C.ADDRESSING_RELIABLE_4096_ONLY
    for status in (C.NOT_RUN_BUDGET, C.INCOMPLETE, "NOT_EVALUATED"):
        o6 = C.study_outcome(s1, None, status)
        assert o6.row == 6 and status in o6.label and "not read as a failure to scale" in o6.label
    sup = size(1, FAILS_ALL | {"A2": C.RELIABLE}, {"A2": C.IMPROVES})
    assert "(ADDRESS-SUPERVISED IN TRAINING)" in C.study_outcome(sup, None, C.NOT_RUN_BUDGET).label
    assert C.study_outcome(size(1, FAILS_ALL | {"A4": C.UNRELIABLE}), None, C.NOT_RUN_NO_ARM).row == 7
    assert C.study_outcome(size(1, FAILS_ALL | {"A1-S": C.UNRELIABLE}), None, C.NOT_RUN_NO_ARM).row == 8  # A1-S is not counted
    o8 = C.study_outcome(size(1, FAILS_ALL), None, C.NOT_RUN_NO_ARM)
    assert o8.row == 8 and "change the retrieval architecture" in o8.label
    # A1 and A2 skipped in the rows where NEGATIVE CONTROL FAILED, and A4 can carry
    skip = size(1, FAILS_ALL | {"A1": C.RELIABLE, "A4": C.RELIABLE}, {"A1": C.IMPROVES, "A4": C.IMPROVES}, nc=True)
    assert C.study_outcome(skip, None, C.NOT_RUN_BUDGET).arm == "A4"


def test_carry_forward_order_and_skips() -> None:
    assert C.carry_forward(None) is None
    assert C.carry_forward(size(2, {"A1": C.RELIABLE, "A4": C.RELIABLE, "A5-D": C.RELIABLE})) == "A5-D"
    assert C.carry_forward(size(2, {"A1": C.RELIABLE, "A0": C.RELIABLE})) == "A0"
    assert C.carry_forward(size(2, {"A1": C.RELIABLE, "A2": C.RELIABLE}, nc=True)) is None
    assert C.carry_forward(size(2, {"A2": C.RELIABLE, "A1": C.RELIABLE})) == "A2"
    assert C.carry_forward(size(2, {"A0": C.UNRELIABLE})) is None  # an LM-reduced arm is UNRELIABLE and is never carried forward


def test_hypothesis_readings() -> None:
    h = {"onset_cells": 12, "ratio_cells": 12}
    s = size(1, FAILS_ALL | {"A5-C": C.RELIABLE, "A1": C.RELIABLE, "A2": C.RELIABLE, "A4": C.RELIABLE, "A5-D": C.RELIABLE}, {"A5-C": C.IMPROVES, "A1": C.IMPROVES, "A2": C.IMPROVES, "A4": C.HARMS, "A5-D": C.NOT_DISTINGUISHED})
    r = C.hypothesis_readings(s, h)
    assert r["H19-A"]["reading"] == "supported"
    assert r["H19-B"]["reading"] == "supported" and r["H19-C"]["reading"] == "supported" and r["H19-F"]["reading"] == "supported"
    assert r["H19-D"]["reading"] == "CONTRADICTED" and r["H19-G"]["reading"] == "not supported"
    s.negative_control_failed = True
    r = C.hypothesis_readings(s, h)
    assert r["H19-B"]["reading"] == "not supported" and r["H19-C"]["reading"] == "not supported"
    s.negative_control_failed, s.supervision_dependent["A2"] = False, True
    assert C.hypothesis_readings(s, h)["H19-C"]["reading"] == "not supported"  # SUPERVISION-DEPENDENT
    assert C.hypothesis_readings(s, {"onset_cells": 11, "ratio_cells": 12})["H19-A"]["reading"] == "not supported"
    a0_reliable = size(1, FAILS_ALL | {"A0": C.RELIABLE})
    assert C.hypothesis_readings(a0_reliable, h)["H19-A"]["reading"] == "not supported"  # A0 must not be RELIABLE
    assert C.hypothesis_readings(a0_reliable, h)["H19-E (A0)"]["reading"] == "supported"
    row3 = C.hypothesis_readings(s, h, reading_stage=size(2, {"A5-C": C.RELIABLE}, {"A5-C": C.NOT_DISTINGUISHED}))
    assert row3["H19-F"]["reading"] == "not supported"  # read at 16,384 in the case of row 3


# --- the whole analysis on synthetic records of the full registry -----------------------------------------------------------------------
def stage_data(stage: int, success: dict[str, Callable[[int, int], bool]], cells: list[core.Cell], *, drop: set[str] = frozenset(), a6: Callable[[int], float] = lambda d: 0.99, lm: Callable[[str, int, int], float] = lambda a, d, j: 0.1, summaries: bool = True) -> A.StageData:  # type: ignore[assignment]
    sd = A.StageData(stage, A.expected_of(cells), {}, [], core.UPDATES)
    for c in cells:
        label = f"{c.arm}/d{c.draw}/j{c.seed_index}"
        if label in drop:
            continue
        if c.arm == "A6":
            o = obs(acc_a=a6(c.draw), acc_b=a6(c.draw), lm_rise=0.10)
        elif c.arm == "A7":
            o = obs(acc_a=0.5, acc_b=0.5, distinct_top1=0, largest_share=1.0, lm_rise=0.2)
        else:
            ok = success.get(c.arm, lambda d, j: False)(c.draw, c.seed_index)
            o = obs(lm_rise=lm(c.arm, c.draw, c.seed_index)) if ok else obs(acc_a=0.1, acc_b=0.1, h1=0.1, h2=0.1, distinct_top1=3, largest_share=0.9, lm_rise=lm(c.arm, c.draw, c.seed_index))
        sd.cells[(c.arm, c.draw, c.seed_index)] = A.CellData({u: o for u in sd.readouts}, summary() if summaries and c.arm in core.LEARNED_ARMS else None)
    return sd


ALL = lambda d, j: True  # noqa: E731
NONE = lambda d, j: False  # noqa: E731
GATES_OK = {"g1_passed": True, "g2_passed": True, "g4_passed": True, "g5_passed": True, "g6_passed": True, "g4_defects": []}


def test_full_registry_answer_only_reliable() -> None:
    assert len(core.stage1_cells()) == 128
    s1 = stage_data(1, {"A0": ALL, "A4": ALL}, core.stage1_cells())
    s2 = stage_data(2, {"A0": ALL, "A4": ALL}, core.stage2_cells(["A4"]))
    result = A.analyze_study(s1, s2, None, stage3_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert result["outcome"]["outcome"] == C.ANSWER_ONLY_RELIABLE and result["assessment"]["status"] == "COMPLETE"
    assert result["stage2"]["status"] == C.COMPLETE and result["stage2"]["arms"]["A0"]["class"] == C.RELIABLE
    assert result["stage1"]["arms"]["A4"]["paired_against_a0"]["label"] == C.NOT_DISTINGUISHED
    assert result["stage2"]["arms"]["A4"]["readout_u"]["label"] == C.MID_SCHEDULE and result["stage2"]["arms"]["A0"]["readout_u"]["label"] == C.ALSO_AT_MATCHED_UPDATES
    assert result["carried_forward"]["arm"] == "A0"
    assert result["stage1"]["arms"]["A0"]["dense_comparison"]["label"] == C.BEATS_DENSE  # A7 at 0.5 against 0.95
    json.dumps(core.jsonable(result), allow_nan=False)


def test_full_registry_addressing_reliable_and_improves() -> None:
    s1 = stage_data(1, {"A5-C": ALL, "A0": lambda d, j: d <= 3}, core.stage1_cells())
    s2 = stage_data(2, {"A5-C": ALL, "A0": NONE}, core.stage2_cells(["A5-C"]))
    result = A.analyze_study(s1, s2, None, stage3_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert result["outcome"]["row"] == 4 and "A5-C (LABEL-FREE)" in result["outcome"]["label"] and C.IMPROVES in result["outcome"]["label"]
    assert result["hypotheses"]["H19-F"]["reading"] == "supported" and result["hypotheses"]["H19-G"]["reading"] == "CONTRADICTED"  # A5-D never succeeds where A0 does: it HARMS
    assert result["carried_forward"]["arm"] == "A5-C"
    gate = C.stage1_gate({a: v for a, v in A.analyze_stage(s1).classes.items()}, False)
    assert gate.advancing == ["A5-C"] and gate.arms == ["A0", "A5-C"]


def test_full_registry_stage3_probe_and_statuses() -> None:
    s1 = stage_data(1, {"A5-C": ALL}, core.stage1_cells())
    s2 = stage_data(2, {"A5-C": ALL}, core.stage2_cells(["A5-C"]))
    s3 = stage_data(3, {"A5-C": ALL, "A0": NONE}, core.stage3_cells("A5-C"))
    result = A.analyze_study(s1, s2, s3, stage3_selected="A5-C", gates=GATES_OK)
    assert result["stage3"]["label"] == C.SCALE_POSITIVE and result["stage3"]["status"] == C.COMPLETE
    s3.cells.pop(("A5-C", 14, 0))
    assert A.analyze_study(s1, s2, s3, stage3_selected="A5-C", gates=GATES_OK)["stage3"]["status"] == C.INCOMPLETE
    s2.cells.pop(("A0", 9, 1))
    r = A.analyze_study(s1, s2, None, stage3_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK)
    assert r["stage2"]["status"] == C.INCOMPLETE and r["outcome"]["row"] == 6 and C.INCOMPLETE in r["outcome"]["label"]
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, stage3_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK)
    assert r["stage2"]["status"] == C.NOT_RUN_BUDGET and C.NOT_RUN_BUDGET in r["outcome"]["label"]


def test_missing_cell_is_not_interpreted_incomplete_with_no_class() -> None:
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells(), drop={"A4/d3/j1"})
    r = A.analyze_study(s1, None, None, gates=GATES_OK)
    assert r["outcome"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and r["stage1"] is None and "A4/d3/j1" in r["outcome"]["missing"]
    assert r["assessment"]["status"] == "INCOMPLETE"
    no_gates = A.analyze_study(stage_data(1, {"A0": ALL}, core.stage1_cells()), None, None, gates=None)
    assert no_gates["outcome"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and "gates record" in no_gates["outcome"]["missing"]
    failed = A.analyze_study(stage_data(1, {"A0": ALL}, core.stage1_cells()), None, None, gates=GATES_OK, failed_tasks=["train1:g-d01-n4096"])
    assert failed["outcome"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE


def test_failed_gates_status_and_reasons() -> None:
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells())
    g1 = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK | {"g1_passed": False})
    assert g1["outcome"]["outcome"] == C.NOT_INTERPRETED and "G1 failed" in g1["outcome"]["label"] and g1["stage1"] is not None  # classes still returned, marked not interpreted
    assert g1["outcome"]["descriptive_outcome"].startswith("ANSWER-ONLY RELIABLE")
    g2 = A.analyze_study(s1, None, None, gates=GATES_OK | {"g2_passed": False})
    assert g2["outcome"]["outcome"] == C.NOT_INTERPRETED
    for gate in ("g4", "g5", "g6"):
        e = A.analyze_study(s1, None, None, gates=GATES_OK | {f"{gate}_passed": False})
        assert e["outcome"]["outcome"] == C.ENGINEERING_FAIL and e["assessment"]["status"] == "ENGINEERING_FAIL"
    d = A.analyze_study(s1, None, None, gates=GATES_OK | {"g4_defects": ["gradient reach failed for A2"], "g4_passed": False})
    assert d["outcome"]["outcome"] == C.ENGINEERING_FAIL and d["outcome"]["defects"] == ["gradient reach failed for A2"]
    unrecorded = A.analyze_study(s1, None, None, gates={"g4_defects": []})
    assert "G1 not recorded" in unrecorded["assessment"]["gate_reasons"]


def test_not_evaluated_draws_at_stage_one() -> None:
    one = stage_data(1, {"A0": ALL}, core.stage1_cells(), a6=lambda d: 0.5 if d == 1 else 0.99)
    r = A.analyze_study(one, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK)
    assert r["stage1"]["arms"]["A0"]["counts"]["evaluated"] == 14 and r["outcome"]["outcome"] == C.ANSWER_ONLY_RELIABLE  # 13 of 14 is enough
    two = stage_data(1, {"A0": ALL}, core.stage1_cells(), a6=lambda d: 0.5 if d <= 2 else 0.99)
    r = A.analyze_study(two, None, None, gates=GATES_OK)
    assert r["stage1"]["arms"]["A0"]["class"] == C.NOT_EVALUATED and r["outcome"]["outcome"] == C.INCONCLUSIVE and r["outcome"]["row"] == 2
    s2 = stage_data(2, {"A0": ALL}, core.stage2_cells([]), a6=lambda d: 0.5 if d == 9 else 0.99)
    r = A.analyze_study(stage_data(1, {"A0": ALL}, core.stage1_cells()), s2, None, stage3_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert r["stage2"]["status"] == "NOT_EVALUATED" and r["stage2"]["arms"]["A0"]["class"] == C.NOT_EVALUATED


def test_non_finite_values_are_read_and_written_as_markers() -> None:
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells(), lm=lambda a, d, j: math.inf if (a, d) == ("A0", 1) else 0.1)
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK)
    assert r["stage1"]["arms"]["A0"]["lm_capability"]["reduced"] and r["stage1"]["arms"]["A0"]["class"] == C.UNRELIABLE_LM  # two non-finite rises
    text = json.dumps(core.jsonable(r), allow_nan=False)
    assert '"+inf"' in text
    nan_acc = stage_data(1, {"A0": ALL}, core.stage1_cells())
    nan_acc.cells[("A0", 1, 0)] = A.CellData({core.UPDATES: obs(acc_a=math.nan, acc_b=math.nan)}, summary())
    assert A.analyze_stage(nan_acc).verdicts["A0"][(1, 0)].status == C.FAILED
    ev = {"panels": {"A": {"accuracy": "nan", "memory_dependence_chance": True}, "B": {"accuracy": "+inf", "memory_dependence_chance": True}}, "secondary": {"H1": {"accuracy": 0.5}, "H2": {"accuracy": 0.5}}, "language_modelling": {"relative_rise": "-inf"}}
    o = C.observation_from_eval(ev)
    assert math.isnan(o.acc_a) and o.acc_b == math.inf and o.lm_rise == -math.inf


def test_negative_control_failure_skips_supervised_arms_in_the_analysis() -> None:
    s1 = stage_data(1, {"A1": ALL, "A2": ALL, "A1-S": ALL, "A4": NONE}, core.stage1_cells())
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_NO_ARM, gates=GATES_OK)
    assert r["stage1"]["negative_control_failed"] and r["outcome"]["row"] == 2


def test_negative_a2_against_a1_is_descriptive_and_stage_two_annotations() -> None:
    s1 = stage_data(1, {"A2": ALL, "A1": NONE, "A0": NONE}, core.stage1_cells())
    r = A.analyze_stage(s1)
    assert r.details["arms"]["A2"]["paired_against_a1"]["label"] == C.IMPROVES and r.details["arms"]["A2"]["paired_against_a1"]["descriptive"]
    assert "supervision_dependent" in r.details["arms"]["A2"] and "movement_after_removal_relative_to_a0" in r.details["arms"]["A2"]
    with pytest.raises(ValueError):
        A.analyze_stage(stage_data(3, {}, core.stage3_cells("A0")))


def test_a_replaced_draw_slot_is_analysed_like_any_other_slot() -> None:
    """A reserve draw takes the failed draw's place and stage: cells are keyed by the slot, so the analysis does not know which seed set served it; the draw
    plan is recorded beside the result (``stages.work_analyze``) and the plan itself is tested in test_p9ii_core."""
    plan = core.plan_draws({n: n != "p9ii-draw-3" for n in (*core.DRAW_NAMES, *core.RESERVE_NAMES)})
    assert plan.replacements == {3: "p9ii-reserve-1"}
    s1 = stage_data(1, {"A0": ALL}, core.stage1_cells())
    r = A.analyze_study(s1, None, None, stage2_not_run=C.NOT_RUN_BUDGET, gates=GATES_OK)
    assert r["stage1"]["arms"]["A0"]["draw_sensitivity"]["table"]["3"] == {"0": C.SUCCEEDED, "1": C.SUCCEEDED} and r["outcome"]["outcome"] == C.ANSWER_ONLY_RELIABLE
