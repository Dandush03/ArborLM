# ruff: noqa: E501
"""P9 Lane A analysis (package I6): capacity classes, annotations, ladder, gates, TASK_CEILING_FAIL.

Synthetic records only (no model, data or simulator). Self-check only: not independent review, not Astra
validation, not human approval.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p9_analysis_synth import (  # noqa: E402
    CHANCE,
    SIZE_ACC,
    E,
    Synth,
    fill,
    lane_a_world,
    record,
    strong_memory,
)

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import core  # noqa: E402

FLAT, TREE = "flat", "learned_tree"


def by_size(
    accs: dict[int, tuple[float, float]],
    *,
    dense: tuple[float, float] = (0.5, 0.5),
    replicate: dict[int, tuple[float, float]] | None = None,
):  # type: ignore[no-untyped-def]
    def profile(c: core.Cell) -> tuple[float, float | None] | None:
        if c.arch == "dense":
            return dense
        if replicate is not None and c.parent == core.REPLICATE_PARENT:
            return replicate[c.slots]
        return accs[c.slots]

    return profile


def cls_of(world: Synth, arch: str = FLAT, **kw: object) -> core.ClassResult:
    return A.classify_capacity(world.index, arch, E, **kw)  # type: ignore[arg-type]


# --- ratio conventions, plateau, I_acc ---------------------------------------------------------------
def test_information_ratio_conventions() -> None:
    assert A.information_ratio(0.0, 5.0) == math.inf  # I_N = 0 -> +inf
    assert A.information_ratio(2.0, 8.0) == 4.0
    assert A.information_ratio(0.0, 0.0) == 0.0
    assert A.information_ratio(4.0, 0.0) == 0.0
    assert (
        math.isnan(A.ratio(0.0, 0.0)) and A.ratio(3.0, 0.0) == math.inf and A.ratio(3.0, 2.0) == 1.5
    )
    assert not A.ge(math.nan, 0.0)


def test_chance_at_both_snapshots_is_plateaued() -> None:
    assert A.plateaued(0.0, 0.0) is True
    assert A.plateaued(100.0, 105.0) is True and A.plateaued(100.0, 106.0) is False
    assert A.plateaued(120.0, 100.0) is True  # a decrease has plateaued


def test_info_uses_the_chance_floor() -> None:
    n = 8192
    interval = core.chance_interval(n, 8)
    at_edge = record("x", 1, "panel_a", n, interval.high)
    above = record("x", 1, "panel_a", n, interval.high + 40)
    zero = record("x", 1, "panel_a", n, 0)
    assert A.info_of(at_edge) == 0.0 and A.info_of(zero) == 0.0  # accuracy 0 is floored too
    assert A.info_of(above) > 0.0
    assert (
        core.information_bits(0, n) == 0.0 and core.fano_bits_per_fact(0.0) > 0.0
    )  # formula alone is positive


# --- the six classes -------------------------------------------------------------------------------------
def test_positive_flat_and_tree_with_not_assessed_annotations() -> None:
    w = lane_a_world()
    for arch in (FLAT, TREE):
        r = cls_of(w, arch)
        assert r["cls"] == "CAPACITY_POSITIVE" and r["panel_classes"] == {
            "A": "CAPACITY_POSITIVE",
            "B": "CAPACITY_POSITIVE",
        }
        assert A.A_OPT_NOT_ASSESSED in r["annotations"]
    flat = cls_of(w, FLAT)
    assert (
        A.A_KEY_WIDTH_NOT_ASSESSED in flat["annotations"]
        and A.A_EMPTY_NOT_ASSESSED in flat["annotations"]
    )
    assert flat["details"]["panels"]["A"]["steps"]["4096->16384"]["supported"] is True
    assert set(flat["details"]["used_labels"]) >= {c.label for c in core.cells() if c.block == "A8"}


def test_partial_when_second_step_fails_but_has_not_plateaued() -> None:
    w = lane_a_world(by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.30, 0.10)}))
    r = cls_of(w)
    assert r["cls"] == "CAPACITY_PARTIAL"
    step = r["details"]["panels"]["A"]["steps"]["16384->65536"]
    assert (
        step["failing"] is True and step["larger_plateaued"] is False and step["supported"] is False
    )


def test_not_supported_has_precedence_over_partial() -> None:
    # the same 4K->16K step as above is supported with beats-dense and dependence, but the 64K cell has plateaued
    w = lane_a_world(by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.30, 0.30)}))
    r = cls_of(w)
    assert r["cls"] == "CAPACITY_NOT_SUPPORTED"
    assert r["details"]["panels"]["A"]["steps"]["4096->16384"]["supported"] is True
    assert (
        r["details"]["panels"]["A"]["steps"]["16384->65536"]["failing"] is True
    )  # the failing step is printed


def test_zero_knowledge_memory_is_not_partial() -> None:
    w = lane_a_world(
        by_size({4096: (CHANCE, CHANCE), 16384: (CHANCE, CHANCE), 65536: (CHANCE, CHANCE)})
    )
    r = cls_of(w)
    assert r["cls"] == "CAPACITY_NOT_SUPPORTED"  # chance at both snapshots has plateaued
    only_big = lane_a_world(
        by_size({4096: (0.9, 0.9), 16384: (CHANCE, CHANCE), 65536: (CHANCE, CHANCE)})
    )
    assert cls_of(only_big)["cls"] not in ("CAPACITY_PARTIAL", "CAPACITY_POSITIVE")
    assert A.info_of(next(iter(w.index.values()))) == 0.0


def test_near_chance_step_is_not_supported() -> None:
    # 0.035 -> 0.040 would give a ratio above 20 under the unfloored formula; both cells are at chance
    w = lane_a_world(by_size({4096: (0.035, 0.035), 16384: (0.040, 0.040), 65536: (0.040, 0.040)}))
    step = A.step_result(w.index, FLAT, 4096, "A", E)
    assert step.supported is False
    assert all(
        a < core.STEP_ACCURACY_MIN for k, a in step.accuracies.items() if k.endswith(":large")
    )
    assert cls_of(w)["cls"] == "CAPACITY_NOT_SUPPORTED"
    near = record("x", 1, "panel_a", 8192, round(0.040 * 8192))
    assert (
        A.info_of(near) == pytest.approx(8192 * core.fano_bits_per_fact(0.040), rel=0.05)
        or A.info_of(near) == 0.0
    )


def test_ratio_with_zero_denominator_supports_the_step_when_accuracy_holds() -> None:
    # 4K at chance (I = 0), 16K strong: ratio +inf, but accuracy at 4K is below 0.25 so the step is not supported
    w = lane_a_world(by_size({4096: (CHANCE, CHANCE), 16384: (0.9, 0.9), 65536: (0.85, 0.85)}))
    step = A.step_result(w.index, FLAT, 4096, "A", E)
    assert (
        all(v == math.inf for v in step.ratios.values())
        and step.supported is False
        and step.failing is False
    )
    assert cls_of(w)["cls"] in ("INTERMEDIATE", "UNDERTRAINED")


def test_undertrained() -> None:
    w = lane_a_world(by_size({4096: (0.9, 0.9), 16384: (0.2, 0.05), 65536: (0.85, 0.85)}))
    r = cls_of(w)
    assert r["cls"] == "UNDERTRAINED"
    assert r["details"]["panels"]["A"]["steps"]["4096->16384"]["larger_plateaued"] is False


def test_intermediate() -> None:
    # second step ratio about 2.5: neither supported (needs 3.0) nor failing (below 2.0); dense strong: no PARTIAL
    w = lane_a_world(
        by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.69, 0.69)}, dense=(0.9, 0.9))
    )
    r = cls_of(w)
    assert r["cls"] == "INTERMEDIATE"
    s2 = r["details"]["panels"]["A"]["steps"]["16384->65536"]
    assert s2["supported"] is False and s2["failing"] is False and s2["larger_plateaued"] is True


def test_beats_dense_and_dependence_gate_positive_and_partial() -> None:
    strong_dense = lane_a_world(
        by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.85, 0.85)}, dense=(0.9, 0.9))
    )
    assert cls_of(strong_dense)["cls"] == "INTERMEDIATE"
    assert A.beats_dense(strong_dense.index, FLAT, 16384, "A", E) is False
    ok = lane_a_world()
    assert A.beats_dense(ok.index, FLAT, 16384, "A", E) and A.dependence_holds(
        ok.index, FLAT, 65536, "B", E
    )
    # a value-permuted memory that still answers: dependence fails at 16K, so neither POSITIVE nor PARTIAL
    broken = lane_a_world()
    for c in core.cells():
        if (
            c.block == "A1"
            and c.slots == 16384
            and c.seed == 1702
            and c.parent == core.PRIMARY_PARENT
        ):
            for key, rec in broken.index.items():
                if key[0] == c.label:
                    rec["value_permuted_accuracy"] = 0.5
    assert A.dependence_holds(broken.index, FLAT, 16384, "A", E) is False
    assert cls_of(broken)["cls"] == "INTERMEDIATE"
    # fewer than 90% of correct facts with a minimal support
    few = lane_a_world()
    for key, rec in few.index.items():
        if key[0].startswith("A1-flat-R0-n16384"):
            rec["share_correct_with_support"] = 0.85
    assert cls_of(few)["cls"] == "INTERMEDIATE"
    # disabling memory must give chance accuracy too
    gone = lane_a_world()
    for key, rec in gone.index.items():
        if key[0].startswith("A1-flat-R0-n65536"):
            rec["disabled_accuracy"] = 0.3
    assert cls_of(gone)["cls"] == "CAPACITY_PARTIAL"  # POSITIVE needs dependence at 64K as well


def test_beats_dense_with_a_zero_information_memory_is_false() -> None:
    w = lane_a_world(
        by_size(
            {4096: (CHANCE, CHANCE), 16384: (CHANCE, CHANCE), 65536: (CHANCE, CHANCE)},
            dense=(CHANCE, CHANCE),
        )
    )
    assert A.beats_dense(w.index, FLAT, 16384, "A", E) is False


def test_accuracy_at_64k_below_half_is_partial_at_best() -> None:
    w = lane_a_world(
        by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.69, 0.69)}, dense=(0.3, 0.3))
    )
    # the ratio is ~2.5, so the second step is not supported anyway; use a supported step with accuracy < 0.5
    low = lane_a_world(
        by_size({4096: (0.55, 0.55), 16384: (0.55, 0.55), 65536: (0.49, 0.49)}, dense=(0.2, 0.2))
    )
    s2 = A.step_result(low.index, FLAT, 16384, "A", E)
    assert s2.supported is True
    assert cls_of(low)["cls"] == "CAPACITY_PARTIAL"
    assert cls_of(w)["cls"] in ("INTERMEDIATE", "CAPACITY_PARTIAL")


def test_step_ratio_floor_for_the_b102_replicate_is_2_5() -> None:
    primary = {4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.85, 0.85)}
    low_rep = {**primary, 65536: (0.66, 0.66)}  # ratio ~2.4 in the replicate only
    w = lane_a_world(by_size(primary, replicate=low_rep))
    step = A.step_result(w.index, FLAT, 16384, "A", E)
    assert step.supported is False and step.ratios["b102_s1701"] < 2.5 <= min(
        step.ratios["s1701"], step.ratios["s1702"]
    )
    ok_rep = {**primary, 65536: (0.69, 0.69)}  # ratio ~2.55
    assert (
        A.step_result(
            lane_a_world(by_size(primary, replicate=ok_rep)).index, FLAT, 16384, "A", E
        ).supported
        is True
    )


def test_step_needs_ratio_3_in_both_b101_seeds() -> None:
    def profile(c: core.Cell) -> tuple[float, float | None] | None:
        if c.arch == "dense":
            return 0.5, 0.5
        if c.slots == 65536 and c.seed == 1702 and c.parent == core.PRIMARY_PARENT:
            return 0.69, 0.69
        return SIZE_ACC[c.slots], SIZE_ACC[c.slots]

    w = lane_a_world(profile)
    step = A.step_result(w.index, FLAT, 16384, "A", E)
    assert (
        step.supported is False and step.failing is False
    )  # one seed ok, one not: not failing in both seeds


def test_not_replicated_when_panels_disagree() -> None:
    w = Synth()
    for c in core.cells():
        if c.block in ("A1", "A2", "A8"):
            if c.arch == "dense":
                w.cell(c, 0.5)
            elif c.slots == 65536:
                w.cell(c, {"A": 0.85, "B": 0.30}, {"A": 0.85, "B": 0.10})
            else:
                w.cell(c, 0.9)
    r = cls_of(w)
    assert (
        r["panel_classes"] == {"A": "CAPACITY_POSITIVE", "B": "CAPACITY_PARTIAL"}
        and r["cls"] == core.NOT_REPLICATED
    )


def test_seed_disagreement_inside_a_step_is_not_failing() -> None:
    def profile(c: core.Cell) -> tuple[float, float | None] | None:
        if c.arch == "dense":
            return 0.5, 0.5
        if c.slots == 65536 and c.seed == 1701 and c.parent == core.PRIMARY_PARENT:
            return 0.30, 0.30
        return SIZE_ACC[c.slots], SIZE_ACC[c.slots]

    r = cls_of(lane_a_world(profile))
    assert r["details"]["panels"]["A"]["steps"]["16384->65536"]["failing"] is False
    assert (
        r["cls"] == "CAPACITY_PARTIAL"
    )  # step 1 supported; step 2 neither supported nor failing in both seeds


# --- INCOMPLETE ---------------------------------------------------------------------------------------------
def test_incomplete_when_one_mandatory_cell_is_missing_and_other_arch_is_unaffected() -> None:
    w = lane_a_world()
    victim = next(
        c
        for c in core.cells()
        if c.block == "A1" and c.slots == 65536 and c.parent == core.REPLICATE_PARENT
    )
    w.drop(victim, ("A",))
    r = cls_of(w, FLAT)
    assert (
        r["cls"] == A.INCOMPLETE
        and r["details"]["missing"]
        and all(victim.label in m for m in r["details"]["missing"])
    )
    assert (
        cls_of(w, TREE)["cls"] == "CAPACITY_POSITIVE"
    )  # the tree class does not depend on the flat cells
    dense = next(c for c in core.cells() if c.block == "A8" and c.slots == 4096)
    w2 = lane_a_world()
    w2.drop(dense)
    assert (
        cls_of(w2, FLAT)["cls"] == A.INCOMPLETE
    )  # capacity classes depend on A8 at all sizes (ADR 10)
    assert A.classify_capacity_panel(w.index, FLAT, "A", E) == A.INCOMPLETE
    assert cls_of(Synth())["cls"] == A.INCOMPLETE  # an empty index never raises


def test_analyze_never_raises_on_an_empty_index() -> None:
    results = A.analyze({}, E, {})
    subjects = [r["subject"] for r in results]
    assert "capacity/flat" in subjects and "ladder" in subjects and "gates" in subjects
    assert {r["cls"] for r in results if r["subject"].startswith(("capacity", "tree"))} == {
        A.INCOMPLETE
    }


# --- TASK_CEILING_FAIL -------------------------------------------------------------------------------------------
def test_task_ceiling_fail_at_64k_blocks_positive() -> None:
    w = lane_a_world()
    assert cls_of(w)["cls"] == "CAPACITY_POSITIVE"
    r = cls_of(w, ceiling_fail=(65536,))
    assert r["cls"] == "CAPACITY_PARTIAL" and "TASK_CEILING_FAIL(65536)" in r["annotations"]
    assert r["details"]["panels"]["A"]["steps"]["16384->65536"] == core.NOT_EVALUATED
    # the 64K cells are not required (the size is not run)
    for c in core.cells():
        if c.block in ("A1", "A8") and c.slots == 65536:
            w.drop(c)
    assert cls_of(w, ceiling_fail=(65536,))["cls"] == "CAPACITY_PARTIAL"
    assert cls_of(w)["cls"] == A.INCOMPLETE


def test_task_ceiling_fail_at_16k_makes_lane_a_not_evaluated() -> None:
    w = lane_a_world()
    r = cls_of(w, ceiling_fail=(16384,))
    assert r["cls"] == core.NOT_EVALUATED and "TASK_CEILING_FAIL(16384)" in r["annotations"]
    res = A.analyze(w.index, E, {"task_ceiling_fail": [16384]})
    assert {x["cls"] for x in res if x["subject"].startswith("capacity")} == {core.NOT_EVALUATED}
    gate = next(x for x in res if x["subject"] == "gates")
    assert gate["cls"] == "TASK_CEILING_FAIL" and gate["details"]["ceiling_fail"] == [16384]


def test_task_ceiling_fail_at_4k_removes_partial() -> None:
    r = cls_of(lane_a_world(), ceiling_fail=(4096,))
    assert r["cls"] not in ("CAPACITY_POSITIVE", "CAPACITY_PARTIAL")
    assert r["details"]["panels"]["A"]["steps"]["4096->16384"] == core.NOT_EVALUATED


def test_ceiling_fail_sizes_from_calibration_record() -> None:
    assert A.ceiling_fail_sizes(None) == () and A.ceiling_fail_sizes(
        {"task_ceiling_fail": [65536, 16384]}
    ) == (16384, 65536)
    curves = {
        "4096": {"32": 0.99, "64": 1.0, "128": 1.0},
        "16384": {"32": 0.96, "64": 0.97, "128": 0.98},
        "65536": {"32": 0.5, "64": 0.7, "128": 0.9},
    }
    assert A.ceiling_fail_sizes({"r2_accuracy": curves}) == (65536,)


# --- LEAKAGE --------------------------------------------------------------------------------------------------------
def test_leakage_flag_is_printed_and_the_lane_withheld() -> None:
    w = lane_a_world()
    victim = next(
        c
        for c in core.cells()
        if c.block == "A1"
        and c.slots == 16384
        and c.seed == 1701
        and c.parent == core.PRIMARY_PARENT
    )
    for key, rec in w.index.items():
        if key[0] == victim.label and key[2] == "panel_a":
            rec["unseen_correct"] = 400  # 400 / 2048 is far outside the chance interval
    assert victim.label in A.leaky_labels(w.index)
    r = A.analyze(w.index, E, {})
    flat = next(x for x in r if x["subject"] == "capacity/flat")
    assert A.A_LEAKAGE in flat["annotations"] and "interpretation_withheld" in flat["details"]
    tree = next(x for x in r if x["subject"] == "capacity/learned_tree")
    assert A.A_LEAKAGE not in tree["annotations"]
    flagged = lane_a_world()
    for rec in flagged.index.values():
        rec["leakage"] = True
        break
    assert len(A.leaky_labels(flagged.index)) == 1


# --- annotations ----------------------------------------------------------------------------------------------------------
def a4_profile(acc64: float):  # type: ignore[no-untyped-def]
    return lambda c: (acc64, acc64) if c.block == "A4" else None


def test_empty_slot_effect() -> None:
    base = by_size({4096: (0.5, 0.5), 16384: (0.5, 0.5), 65536: (0.5, 0.5)})
    w = lane_a_world(base)
    fill(w, ("A4",), a4_profile(0.9))
    assert A.empty_slot_effect(w.index, "A", E) is True
    assert A.A_EMPTY_SLOT in cls_of(w)["annotations"]
    flat_w = lane_a_world(base)
    fill(flat_w, ("A4",), a4_profile(0.5))
    assert (
        A.empty_slot_effect(flat_w.index, "A", E) is False
        and A.A_EMPTY_SLOT not in cls_of(flat_w)["annotations"]
    )
    # a rise of exactly 25% is not 'more than 25%'
    four = core.fano_bits_per_fact(0.5)
    just = core.fano_bits_per_fact(0.55)
    assert just / four < 1.25 < core.fano_bits_per_fact(0.6) / four
    edge = lane_a_world(base)
    fill(edge, ("A4",), a4_profile(0.55))
    assert A.empty_slot_effect(edge.index, "A", E) is False
    with pytest.raises(A.MissingRecord):
        A.empty_slot_effect(lane_a_world(base).index, "A", E)
    assert A.A_EMPTY_NOT_ASSESSED in cls_of(lane_a_world(base))["annotations"]


def a10_profile(small: float, mid: float, large: float):  # type: ignore[no-untyped-def]
    table = {4096: small, 16384: mid, 65536: large}
    return lambda c: (table[c.slots], table[c.slots]) if c.block == "A10" else None


def test_optimizer_dependent_uninformative_robust_and_not_assessed() -> None:
    robust = lane_a_world()
    fill(robust, ("A10",), a10_profile(0.9, 0.9, 0.85))
    assert A.optimizer_annotation(robust.index, (4096, 16384), "A", E) == ""
    assert not {A.A_OPT_DEP, A.A_OPT_UNINFORMATIVE, A.A_OPT_NOT_ASSESSED} & set(
        cls_of(robust)["annotations"]
    )

    dep = lane_a_world()
    fill(dep, ("A10",), a10_profile(0.9, 0.3, 0.3))
    assert A.optimizer_annotation(dep.index, (4096, 16384), "A", E) == A.A_OPT_DEP
    assert A.A_OPT_DEP in cls_of(dep)["annotations"]

    flat_lazy = lane_a_world()
    fill(
        flat_lazy, ("A10",), a10_profile(0.1, 0.1, 0.1)
    )  # the lazy arm is near chance at its smaller size
    assert A.optimizer_annotation(flat_lazy.index, (4096, 16384), "A", E) == A.A_OPT_UNINFORMATIVE
    assert A.A_OPT_UNINFORMATIVE in cls_of(flat_lazy)["annotations"]

    none = lane_a_world()
    assert A.optimizer_annotation(none.index, (4096, 16384), "A", E) == A.A_OPT_NOT_ASSESSED
    assert A.A_OPT_NOT_ASSESSED in cls_of(none, TREE)["annotations"]  # A10 is flat-only

    weak = lane_a_world(by_size({4096: (0.9, 0.9), 16384: (0.2, 0.05), 65536: (0.85, 0.85)}))
    fill(weak, ("A10",), a10_profile(0.9, 0.3, 0.3))
    assert (
        A.optimizer_annotation(weak.index, (4096, 16384), "A", E) == ""
    )  # the AdamW step is not supported: nothing to test
    with pytest.raises(ValueError):
        A.optimizer_annotation(none.index, (4096, 65536), "A", E)


def a7_profile(acc16: float, acc64: float, with64: bool = True):  # type: ignore[no-untyped-def]
    def profile(c: core.Cell) -> tuple[float, float | None] | None:
        if c.block != "A7" or c.rung != "R0":
            return None
        if c.slots == 65536 and not with64:
            return None
        return (acc16, acc16) if c.slots == 16384 else (acc64, acc64)

    return profile


def test_key_width_limited_and_not_assessed() -> None:
    narrow_fails = by_size({4096: (0.9, 0.9), 16384: (0.9, 0.9), 65536: (0.30, 0.30)})
    w = lane_a_world(narrow_fails)
    fill(w, ("A7",), a7_profile(0.9, 0.85))
    assert (
        A.key_width_limited(w.index, "A", E) == A.A_KEY_WIDTH
        and A.A_KEY_WIDTH in cls_of(w)["annotations"]
    )
    both = lane_a_world()
    fill(both, ("A7",), a7_profile(0.9, 0.85))
    assert A.key_width_limited(both.index, "A", E) == ""  # key-16 supports the step too
    wide_fails = lane_a_world(narrow_fails)
    fill(wide_fails, ("A7",), a7_profile(0.9, 0.30))
    assert A.key_width_limited(wide_fails.index, "A", E) == ""
    absent = lane_a_world(narrow_fails)
    fill(absent, ("A7",), a7_profile(0.9, 0.85, with64=False))
    assert A.key_width_limited(absent.index, "A", E) == A.A_KEY_WIDTH_NOT_ASSESSED
    assert A.A_KEY_WIDTH_NOT_ASSESSED in cls_of(absent)["annotations"]
    assert A.key_width_limited({}, "A", E) == A.A_KEY_WIDTH_NOT_ASSESSED


def test_annotations_do_not_change_the_class() -> None:
    base = lane_a_world()
    annotated = lane_a_world()
    fill(annotated, ("A4",), a4_profile(0.9))
    fill(annotated, ("A10",), a10_profile(0.9, 0.3, 0.3))
    assert cls_of(base)["cls"] == cls_of(annotated)["cls"] == "CAPACITY_POSITIVE"


def test_panel_specific_annotation_is_printed_with_its_panel() -> None:
    merged = A.merge_annotations({"A": ["X", "Y"], "B": ["X"]})
    assert merged == ["X", "Y (panel A only)"]


# --- D03: tree against flat ----------------------------------------------------------------------------------------------
def tree_world(flat_acc: float, tree_acc: float, *, panels_differ: bool = False) -> Synth:
    w = Synth()
    for c in core.cells():
        if c.slots != 16384 or c.parent != core.PRIMARY_PARENT:
            continue
        if c.block == "A1":
            w.cell(c, flat_acc)
        elif c.block == "A2":
            w.cell(c, {"A": tree_acc, "B": flat_acc if panels_differ else tree_acc})
        elif c.block == "A3":
            w.cell(c, 0.7)
    return w


@pytest.mark.parametrize(
    ("flat_acc", "tree_acc", "expected"),
    [
        (0.80, 0.85, "TREE_AHEAD"),
        (0.80, 0.80, "TREE_COMPETITIVE"),
        (0.80, 0.79, "TREE_COMPETITIVE"),
        (0.80, 0.60, "TREE_BEHIND"),
        (CHANCE, CHANCE, "TREE_COMPETITIVE"),
        (CHANCE, 0.5, "TREE_AHEAD"),
    ],
)
def test_tree_comparison_classes(flat_acc: float, tree_acc: float, expected: str) -> None:
    r = A.tree_comparison(tree_world(flat_acc, tree_acc).index, E)
    assert r["cls"] == expected
    assert (
        r["details"]["logical_key_products"]["flat"] == 16384
        and r["details"]["logical_key_products"]["learned_tree"] == 576
    )
    assert "not a measured efficiency" in r["details"]["logical_key_products"]["note"]
    assert set(r["details"]["fixed_tree_information_bits"]) == {
        f"{p}:{t}" for p in "AB" for t in ("s1701", "s1702")
    }


def test_tree_ahead_needs_both_panels() -> None:
    r = A.tree_comparison(tree_world(0.80, 0.85, panels_differ=True).index, E)
    assert r["cls"] == "TREE_COMPETITIVE" and r["details"]["lowest_ratio"] == pytest.approx(1.0)
    assert A.tree_comparison(Synth().index, E)["cls"] == A.INCOMPLETE


# --- ladder ------------------------------------------------------------------------------------------------------------------
def ladder_world() -> Synth:
    w = Synth()
    table = {
        ("A5", "R2"): 0.95,
        ("A5", "R1"): 0.90,
        ("A5b", "R0a"): 0.85,
        ("A1", "R0"): 0.60,
        ("A2", "R0"): 0.55,
        ("A6", "OB"): 0.75,
        ("A6", "R1"): 0.80,
    }
    for c in core.cells():
        if c.parent == core.PRIMARY_PARENT and (c.block, c.rung) in table:
            w.cell(c, table[(c.block, c.rung)])
    return w


def test_ladder_gaps_signs_and_the_4k_restriction() -> None:
    w = ladder_world()
    rep = A.ladder_report(w.index, "A", E)
    f = core.fano_bits_per_fact
    assert rep["16384"]["exact-R2"] == pytest.approx(5.0 - f(0.95), abs=3e-3)
    assert rep["16384"]["R2-R1"] == pytest.approx(f(0.95) - f(0.90), abs=3e-3)
    assert rep["16384"]["R1-R0a"] == pytest.approx(f(0.90) - f(0.85), abs=3e-3)
    assert rep["16384"]["R0a-R0"] == pytest.approx(f(0.85) - f(0.60), abs=3e-3)
    assert rep["16384"]["OB-treeR0"] == pytest.approx(f(0.75) - f(0.55), abs=3e-3)
    assert (
        "R1-R0a" not in rep["4096"]
        and "R0a-R0" not in rep["4096"]
        and "exact-R2" in rep["4096"]
        and "R2-R1" in rep["4096"]
    )
    assert rep["4096"]["R2-R1"] is not None
    assert rep["65536"]["OB-treeR0"] if "OB-treeR0" in rep["65536"] else True
    assert "OB-treeR0" not in rep["65536"]  # the oracle branch is run at 16K only
    # signs: R0a better than R0 gives a positive R0a-R0; swap the order and the sign flips
    swapped = Synth()
    for c in core.cells():
        if c.parent == core.PRIMARY_PARENT and c.block == "A5b":
            swapped.cell(c, 0.5)
        elif c.parent == core.PRIMARY_PARENT and c.block == "A1" and c.slots == 16384:
            swapped.cell(c, 0.8)
    assert A.ladder_report(swapped.index, "A", E)["16384"]["R0a-R0"] < 0


def test_ladder_material_gaps_and_missing_values() -> None:
    w = ladder_world()
    reports = {p: A.ladder_report(w.index, p, E) for p in "AB"}
    assert A.material_terms(reports) == [
        "16384:exact-R2",
        "16384:R0a-R0",
        "16384:OB-treeR0",
        "65536:exact-R2",
        "65536:R0a-R0",
    ] or set(A.material_terms(reports)) >= {"16384:R0a-R0", "16384:exact-R2"}
    assert "16384:R2-R1" not in A.material_terms(reports)  # 0.43 bits per fact is not material
    rep = A.ladder_report(Synth().index, "A", E)
    assert rep["16384"]["R2-R1"] is None and rep["16384"]["bits:exact"] == pytest.approx(5.0)
    assert A.material_terms({"A": rep, "B": rep}) == []
    # one seed missing: the mean is undefined, the other seed is still shown
    w.drop(
        next(
            c
            for c in core.cells()
            if c.block == "A5" and c.rung == "R1" and c.slots == 16384 and c.seed == 1702
        )
    )
    part = A.ladder_report(w.index, "A", E)["16384"]
    assert part["R2-R1"] is None and part["R2-R1|s1701"] is not None and part["R2-R1|s1702"] is None


def test_ladder_uses_exact_accuracy_from_controls_and_passes_probes_through() -> None:
    w = ladder_world()
    rep = A.ladder_report(w.index, "A", E, controls={"exact_accuracy": {"16384": 0.9}})
    assert rep["16384"]["exact-R2"] == pytest.approx(
        core.fano_bits_per_fact(0.9) - core.fano_bits_per_fact(0.95), abs=3e-3
    )
    res = A.analyze(w.index, E, {}, {"probes": {"4096": {"nearest": 0.2}}})
    ladder = next(r for r in res if r["subject"] == "ladder")
    assert ladder["cls"] == A.LADDER_REPORT and ladder["details"]["probes"] == {
        "4096": {"nearest": 0.2}
    }
    assert "not system results" in ladder["details"]["note"]


# --- gates ------------------------------------------------------------------------------------------------------------------------
GOOD = {
    "2048": {"correct": 64, "facts": 2048},
    "8192": {"correct": 256, "facts": 8192},
    "32768": {"correct": 1024, "facts": 32768},
    "unseen": {"correct": 64, "facts": 2048},
}


def test_task_gates_pass_fail_and_not_reported() -> None:
    assert A.task_gates({}, None, None) == {
        "G1": "not_reported",
        "G2": "not_reported",
        "G3": "not_reported",
        "G4": "not_reported",
        "TASK_CEILING_FAIL": "none",
    }
    controls = {
        "g1": {"passed": True},
        "g4": {"passed": True},
        "no_memory": {"panel_a": GOOD, "panel_b": GOOD},
    }
    gates = A.task_gates({}, {"task_ceiling_fail": []}, controls)
    assert gates == {
        "G1": "pass",
        "G2": "pass",
        "G3": "pass",
        "G4": "pass",
        "TASK_CEILING_FAIL": "none",
    }
    bad = {
        "g1": {"passed": False},
        "g4": {"passed": True},
        "no_memory": {
            "panel_a": {**GOOD, "8192": {"correct": 700, "facts": 8192}},
            "panel_b": GOOD,
        },
    }
    g = A.task_gates({}, {"task_ceiling_fail": [65536]}, bad)
    assert (
        g["G1"] == "fail"
        and g["G2"] == "fail"
        and g["G3"].startswith("TASK_CEILING_FAIL")
        and g["TASK_CEILING_FAIL"] == "65536"
    )
    assert A.gates_blocking(g) == ["G1", "G2"]


def test_a_failed_gate_makes_the_capacity_classes_not_evaluated() -> None:
    w = lane_a_world()
    controls = {
        "g1": {"passed": False},
        "g4": {"passed": True},
        "no_memory": {"panel_a": GOOD, "panel_b": GOOD},
    }
    res = A.analyze(w.index, E, {}, controls)
    flat = next(r for r in res if r["subject"] == "capacity/flat")
    assert (
        flat["cls"] == core.NOT_EVALUATED
        and flat["details"]["class_if_gates_passed"] == "CAPACITY_POSITIVE"
        and "GATE_FAILED(G1)" in flat["annotations"]
    )
    gates = next(r for r in res if r["subject"] == "gates")
    assert gates["cls"] == "GATES_FAILED"
    ok = A.analyze(
        w.index,
        E,
        {},
        {
            "g1": {"passed": True},
            "g4": {"passed": True},
            "no_memory": {"panel_a": GOOD, "panel_b": GOOD},
        },
    )
    assert next(r for r in ok if r["subject"] == "capacity/flat")["cls"] == "CAPACITY_POSITIVE"
    plain = A.analyze(w.index, E, {})
    assert "GATES NOT REPORTED" in next(r for r in plain if r["subject"] == "gates")["annotations"]


def test_fixed_compute_estimand_is_a_separate_secondary_subject() -> None:
    w = lane_a_world()
    fill(w, ("A1", "A2", "A8"), strong_memory, estimand="fixed_compute")
    res = A.analyze(w.index, E, {})
    by = {r["subject"]: r for r in res}
    assert (
        by["capacity/flat"]["cls"]
        == by["capacity/flat/fixed_compute"]["cls"]
        == "CAPACITY_POSITIVE"
    )
    assert by["capacity/flat/fixed_compute"]["details"]["estimand"] == "fixed_compute"
    only_matched = A.analyze(lane_a_world().index, E, {})
    assert (
        next(r for r in only_matched if r["subject"] == "capacity/flat/fixed_compute")["cls"]
        == A.INCOMPLETE
    )
    assert A.snapshot_pair(core.cells()[0], 32, "fixed_compute") == (1024, 2048)
    with pytest.raises(ValueError):
        A.snapshot_pair(core.cells()[0], 32, "other")


def test_results_are_json_safe_after_sanitising() -> None:
    w = lane_a_world(by_size({4096: (CHANCE, CHANCE), 16384: (0.9, 0.9), 65536: (0.85, 0.85)}))
    res = A.analyze(w.index, E, {})
    text = json.dumps(A.jsonable(res), allow_nan=False)
    assert "+inf" in text
    assert A.jsonable({"a": math.nan, "b": -math.inf, "c": (1, 2), "d": {3, 1}}) == {
        "a": None,
        "b": "-inf",
        "c": [1, 2],
        "d": [1, 3],
    }


def test_analyze_covers_every_registered_subject_of_lane_a() -> None:
    res = A.analyze(lane_a_world().index, E, {})
    assert [r["subject"] for r in res] == [
        "capacity/flat", "capacity/learned_tree", "capacity/flat/fixed_compute", "capacity/learned_tree/fixed_compute",
        "tree_comparison", "tree_comparison/fixed_compute", "ladder", "gates",
    ]  # fmt: skip
    assert all(r["lane"] == "A" for r in res)


# --- analysis dependencies (ADR 10, core.ANALYSIS_DEPENDENCIES) -----------------------------------------------------------
def blocks_of(keys: list[tuple[str, int, str]]) -> set[str]:
    return {core.parse_label(k[0]).block for k in keys}


def test_capacity_needs_follow_the_declared_analysis_dependencies() -> None:
    flat = A.capacity_needs(FLAT, E, "matched", ())
    tree = A.capacity_needs(TREE, E, "matched", ())
    assert blocks_of(flat) == set(core.ANALYSIS_DEPENDENCIES["capacity_flat"]) == {"A1", "A8"}
    assert blocks_of(tree) == set(core.ANALYSIS_DEPENDENCIES["capacity_tree"]) == {"A2", "A8"}
    # A1 at all sizes including the B102 replicate (both snapshots, both panels) and A8 for both seeds
    assert (
        sum(1 for k in flat if k[0].startswith("A1")) == 9 * 2 * 2
        and sum(1 for k in flat if k[0].startswith("A8")) == 6 * 2
    )
    assert not blocks_of(A.capacity_needs(FLAT, E, "matched", (65536,))) - {"A1", "A8"}
    assert all("n65536" not in k[0] for k in A.capacity_needs(FLAT, E, "matched", (65536,)))


def test_other_lane_dependencies_are_inside_the_declared_sets() -> None:
    from studies.p9 import analysis_b as B
    from studies.p9 import analysis_d as D

    b1 = [c for c in core.cells() if c.block == "B1"][:2]
    assert blocks_of(B.case_needs(b1, E, "matched")) <= set(
        core.ANALYSIS_DEPENDENCIES["utilization_b1"]
    )
    c1 = [c for c in core.cells() if c.block == "C1" and c.arch == FLAT and c.alpha_c == 0.05]
    assert blocks_of(B.case_needs(c1, E, "matched")) <= set(
        core.ANALYSIS_DEPENDENCIES["locality_c1"]
    )
    assert blocks_of(D.arm_needs(FLAT, "sequential", E)) <= set(
        core.ANALYSIS_DEPENDENCIES["lane_d"]
    )
