# ruff: noqa: E501
"""P9 Lane D analysis (package I6): incremental classes, NO ADVANTAGE OVER DENSE, the a_A0 floors, Lane D G2.

Synthetic records only. Self-check only: not independent review, not Astra validation, not human approval.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p9_analysis_synth import E, Synth, patch  # noqa: E402

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import analysis_d as D  # noqa: E402
from studies.p9 import core  # noqa: E402

Acc = dict[str, float]


def base(c: core.Cell) -> Acc:
    """flat/tree arms retain well; the dense arm forgets (a_A0 0.9 -> a_A 0.5)."""
    if c.block == "D1":
        return {"A": 0.9}
    if c.lane_d_arm == "joint":
        return {"A": 0.9, "B": 0.9}
    if c.arch == "dense":
        return {"A": 0.5, "B": 0.85}
    return {"A": 0.85, "B": 0.85}


def d_world(profile: Callable[[core.Cell], Acc] = base) -> Synth:
    w = Synth()
    for c in core.cells():
        if c.block in ("D1", "D2"):
            for panel in core.PANELS:
                for s, a in profile(c).items():
                    w.put(c, core.updates(c, E), D.lane_d_stream(panel, s), a, facts=4096)
    return w


def override(**table: Acc) -> Callable[[core.Cell], Acc]:
    """``flat_sequential=...`` replaces the accuracies of that arm; ``flat_phaseA``, ``dense_sequential`` ..."""

    def profile(c: core.Cell) -> Acc:
        key = f"{c.arch}_{c.lane_d_arm}"
        return table.get(key, base(c))

    return profile


def arm(w: Synth, arch: str = "flat", name: str = "sequential", **kw: Any) -> core.ClassResult:
    return D.classify_arm(w.index, arch, name, E, **kw)


# --- streams and readers ---------------------------------------------------------------------------------------
def test_stream_names_and_phase_accuracies() -> None:
    assert D.lane_d_stream("A", "B") == "lane_d_a_B" and D.lane_d_stream("B", "A") == "lane_d_b_A"
    with pytest.raises(ValueError):
        D.lane_d_stream("C", "A")
    w = d_world()
    seq = D.d_cell("flat", "sequential", 1701)
    assert seq is not None
    assert D.phase_accuracies(w.index, seq.label, E, "A") == {
        "a_A": pytest.approx(0.85, abs=1e-3),
        "a_B": pytest.approx(0.85, abs=1e-3),
        "a_A0": pytest.approx(0.9, abs=1e-3),
    }
    joint = D.d_cell("flat", "joint", 1701)
    assert joint is not None and "a_A0" not in D.phase_accuracies(w.index, joint.label, E, "B")
    with pytest.raises(A.MissingRecord):
        D.phase_accuracies({}, seq.label, E, "A")


# --- every class -------------------------------------------------------------------------------------------------
def test_incremental_positive_with_dense_forgetting_and_replay_beside() -> None:
    w = d_world()
    r = arm(w)
    assert r["cls"] == "INCREMENTAL_POSITIVE" and r["panel_classes"] == {
        "A": "INCREMENTAL_POSITIVE",
        "B": "INCREMENTAL_POSITIVE",
    }
    assert D.NO_ADVANTAGE not in r["annotations"]
    nums = r["details"]["panels"]["A"]["numbers"]["1701"]
    assert nums["forgetting"] == pytest.approx(0.05, abs=1e-3) and nums[
        "dense_forgetting"
    ] == pytest.approx(0.4, abs=1e-3)
    assert nums["beside_the_class_no_class"]["flat_replay"]["a_A"] == pytest.approx(
        0.85, abs=1e-3
    ) and nums["joint_bound"]["a_B"] == pytest.approx(0.9, abs=1e-3)
    assert r["lane"] == "D" and r["subject"] == "incremental/flat/sequential"


def test_no_new_capability_before_forgetting() -> None:
    r = arm(d_world(override(flat_sequential={"A": 0.3, "B": 0.3})))
    assert r["cls"] == "NO_NEW_CAPABILITY"  # a_B < 0.5 x 0.9; the forgetting row is never reached
    edge = arm(d_world(override(flat_sequential={"A": 0.85, "B": 0.45})))
    assert edge["cls"] != "NO_NEW_CAPABILITY"  # exactly 0.5 x the bound is not below it


def test_forgetting() -> None:
    r = arm(d_world(override(flat_sequential={"A": 0.5, "B": 0.85})))
    assert r["cls"] == "FORGETTING"
    dense = {"a_A0": 0.9, "a_A": 0.5, "a_B": 0.85}
    assert (
        D.seed_class({"a_A0": 1.0, "a_A": 0.7, "a_B": 0.9}, dense, 0.9) == core.INTERMEDIATE
    )  # a_A = 0.70 x a_A0 is not below it
    assert D.seed_class({"a_A0": 1.0, "a_A": 0.69, "a_B": 0.9}, dense, 0.9) == "FORGETTING"


def test_intermediate_and_no_advantage_over_dense() -> None:
    mid = arm(d_world(override(flat_sequential={"A": 0.75, "B": 0.85})))
    assert mid["cls"] == "INTERMEDIATE" and D.NO_ADVANTAGE not in mid["annotations"]
    even = arm(d_world(override(dense_sequential={"A": 0.85, "B": 0.85})))
    assert (
        even["cls"] == "INTERMEDIATE" and D.NO_ADVANTAGE in even["annotations"]
    )  # dense forgets only 0.05
    # the dense forgetting threshold itself (<= 0.10) and the gap of 0.10, on the pure function
    arm_ = {"a_A0": 1.0, "a_A": 0.95, "a_B": 0.9}
    assert (
        D.seed_class(arm_, {"a_A0": 1.0, "a_A": 0.85, "a_B": 0.9}, 0.9) == "INCREMENTAL_POSITIVE"
    )  # forgetting 0.05 vs 0.15: gap 0.10
    assert (
        D.seed_class(arm_, {"a_A0": 1.0, "a_A": 0.86, "a_B": 0.9}, 0.9) == "INTERMEDIATE"
    )  # gap 0.09
    assert D.seed_class(arm_, {"a_A0": 1.0, "a_A": 0.5, "a_B": 0.9}, 0.9) == "INCREMENTAL_POSITIVE"


def test_b_must_reach_ninety_percent_of_the_joint_bound() -> None:
    r = arm(d_world(override(flat_sequential={"A": 0.85, "B": 0.80})))  # 0.80 < 0.9 x 0.9 = 0.81
    assert r["cls"] == "INTERMEDIATE"
    ok = arm(d_world(override(flat_sequential={"A": 0.85, "B": 0.82})))
    assert ok["cls"] == "INCREMENTAL_POSITIVE"
    retention = arm(
        d_world(override(flat_sequential={"A": 0.80, "B": 0.85}))
    )  # 0.80 < 0.90 x 0.9 = 0.81
    assert retention["cls"] == "INTERMEDIATE"


# --- the a_A0 floors --------------------------------------------------------------------------------------------------
def test_not_evaluated_when_the_arms_a_a0_is_below_half() -> None:
    r = arm(d_world(override(flat_phaseA={"A": 0.4})))
    assert r["cls"] == core.NOT_EVALUATED


def test_not_evaluated_when_dense_a_a0_is_below_half_but_only_if_rows_2_and_3_do_not_match() -> (
    None
):
    dense_weak = override(dense_phaseA={"A": 0.4}, dense_sequential={"A": 0.2, "B": 0.85})
    assert arm(d_world(dense_weak))["cls"] == core.NOT_EVALUATED
    forgetting = override(
        dense_phaseA={"A": 0.4},
        dense_sequential={"A": 0.2, "B": 0.85},
        flat_sequential={"A": 0.5, "B": 0.85},
    )
    assert (
        arm(d_world(forgetting))["cls"] == "FORGETTING"
    )  # row 3 precedes the dense floor of row 4
    no_new = override(dense_phaseA={"A": 0.4}, flat_sequential={"A": 0.85, "B": 0.1})
    assert arm(d_world(no_new))["cls"] == "NO_NEW_CAPABILITY"


def test_seed_and_panel_combination() -> None:
    w = d_world()
    seq2 = D.d_cell("flat", "sequential", 1702)
    assert seq2 is not None
    for panel in core.PANELS:
        patch(w, seq2, None, **{})
    # seed 1702 forgets, seed 1701 retains: the seeds disagree
    for (label, _u, stream), rec in w.index.items():
        if label == seq2.label and stream.endswith("_A"):
            rec["correct"], rec["accuracy"] = round(0.5 * 4096), 0.5
    r = arm(w)
    assert r["cls"] == core.INTERMEDIATE and r["details"]["panels"]["A"]["seed_classes"] == {
        "1701": "INCREMENTAL_POSITIVE",
        "1702": "FORGETTING",
    }
    # panels disagree: panel B forgets in both seeds
    w2 = d_world()
    for seed in core.INIT_SEEDS:
        cell = D.d_cell("flat", "sequential", seed)
        assert cell is not None
        for (label, _u, stream), rec in w2.index.items():
            if label == cell.label and stream == "lane_d_b_A":
                rec["correct"] = round(0.5 * 4096)
    r2 = arm(w2)
    assert (
        r2["panel_classes"] == {"A": "INCREMENTAL_POSITIVE", "B": "FORGETTING"}
        and r2["cls"] == core.NOT_REPLICATED
    )
    # one seed not evaluable: not evaluated
    w3 = d_world()
    d1 = D.d_cell("flat", "phaseA", 1702)
    assert d1 is not None
    for (label, _u, stream), rec in w3.index.items():
        if label == d1.label:
            rec["correct"] = round(0.3 * 4096)
    assert arm(w3)["cls"] == core.NOT_EVALUATED


def test_incomplete_with_one_missing_cell() -> None:
    w = d_world()
    victim = D.d_cell("dense", "sequential", 1702)
    assert victim is not None
    w.drop(victim, ())  # no panel stream names: nothing dropped by the helper, remove by hand
    for key in [k for k in w.index if k[0] == victim.label and k[2] == "lane_d_a_B"]:
        del w.index[key]
    r = arm(w)
    assert r["cls"] == A.INCOMPLETE and any(victim.label in m for m in r["details"]["missing"])
    assert D.classify_arm_panel(w.index, "flat", "sequential", "A", E) == A.INCOMPLETE
    assert D.classify_arm_panel(w.index, "flat", "sequential", "B", E) == "INCREMENTAL_POSITIVE"
    assert (
        arm(Synth())["cls"] == A.INCOMPLETE
        and [x["cls"] for x in D.analyze({}, E)[:3]] == [A.INCOMPLETE] * 3
    )


def test_task_ceiling_fail_at_16k_makes_lane_d_not_evaluated() -> None:
    r = arm(d_world(), ceiling_fail=(16384,))
    assert r["cls"] == core.NOT_EVALUATED and "TASK_CEILING_FAIL(16384)" in r["annotations"]
    assert arm(d_world(), ceiling_fail=(65536,))["cls"] == "INCREMENTAL_POSITIVE"


# --- G2 and leakage -----------------------------------------------------------------------------------------------------
def test_lane_d_g2_uses_the_four_test_interval() -> None:
    interval = core.chance_interval(4096, 4)
    assert interval.level == pytest.approx(1 - 0.001 / 4)
    inside = {
        "no_memory": {
            f"lane_d_{p}_{s}": {"correct": 128, "facts": 4096} for p in "ab" for s in "AB"
        }
    }
    assert D.lane_d_g2({}, "A", inside)["status"] == "pass"
    outside = {"no_memory": {**inside["no_memory"], "lane_d_a_B": {"correct": 200, "facts": 4096}}}
    g = D.lane_d_g2({}, "A", outside)
    assert g["status"] == "fail" and g["streams"]["lane_d_a_B"]["inside_interval"] is False  # type: ignore[index]
    assert D.lane_d_g2({}, "B", outside)["status"] == "pass"
    assert D.lane_d_g2({}, "A", None)["status"] == "not_reported" and g["interval_correct"] == [
        interval.low,
        interval.high,
    ]


def test_a_failed_lane_d_g2_makes_every_arm_not_evaluated() -> None:
    w = d_world()
    controls = {
        "no_memory": {
            f"lane_d_{p}_{s}": {"correct": 128 if (p, s) != ("b", "A") else 250, "facts": 4096}
            for p in "ab"
            for s in "AB"
        }
    }
    res = D.analyze(w.index, E, controls=controls)
    arms = [r for r in res if r["subject"].startswith("incremental/")]
    assert [r["cls"] for r in arms] == [core.NOT_EVALUATED] * 3 and all(
        r["details"]["class_if_g2_passed"] == "INCREMENTAL_POSITIVE" for r in arms
    )
    g2 = next(r for r in res if r["subject"] == "lane_d_g2")
    assert g2["cls"] == "G2_FAIL"
    ok = D.analyze(
        w.index,
        E,
        controls={
            "no_memory": {
                f"lane_d_{p}_{s}": {"correct": 128, "facts": 4096} for p in "ab" for s in "AB"
            }
        },
    )
    assert next(r for r in ok if r["subject"] == "lane_d_g2")["cls"] == "G2_PASS"
    plain = D.analyze(w.index, E)
    assert next(r for r in plain if r["subject"] == "lane_d_g2")["annotations"] == [
        "GATES NOT REPORTED"
    ]


def test_leakage_on_lane_d_cells() -> None:
    w = d_world()
    seq = D.d_cell("flat", "sequential", 1701)
    assert seq is not None
    patch(w, seq, None, unseen_correct=500)
    r = arm(w)
    assert (
        D.LEAKAGE in r["annotations"]
        and "interpretation_withheld" in r["details"]
        and r["cls"] == "INCREMENTAL_POSITIVE"
    )


# --- the three classed arms --------------------------------------------------------------------------------------------------
def test_classed_arms_are_flat_sequential_flat_memory_only_and_tree_sequential() -> None:
    res = D.analyze(d_world().index, E, controls={"exact_lane_d": {"accuracy_a": 1.0}})
    assert [r["subject"] for r in res[:3]] == [
        "incremental/flat/sequential",
        "incremental/flat/memory_only",
        "incremental/learned_tree/sequential",
    ]
    assert all(r["cls"] == "INCREMENTAL_POSITIVE" for r in res[:3])
    assert res[0]["details"]["exact_retrieval_append"] == {"accuracy_a": 1.0}
    assert D.CLASSED_ARMS == (
        ("flat", "sequential"),
        ("flat", "memory_only"),
        ("learned_tree", "sequential"),
    )
    memory_only = D.d_cell("flat", "memory_only", 1701)
    assert (
        memory_only is not None and memory_only.depends_on and "phaseA" in memory_only.depends_on[0]
    )
    tree_only = d_world(override(learned_tree_sequential={"A": 0.5, "B": 0.85}))
    assert [r["cls"] for r in D.analyze(tree_only.index, E)[:3]] == [
        "INCREMENTAL_POSITIVE",
        "INCREMENTAL_POSITIVE",
        "FORGETTING",
    ]


def test_seed_class_pure_function() -> None:
    arm_ok = {"a_A0": 0.9, "a_A": 0.85, "a_B": 0.85}
    dense = {"a_A0": 0.9, "a_A": 0.5, "a_B": 0.85}
    assert D.seed_class(arm_ok, dense, 0.9) == "INCREMENTAL_POSITIVE"
    assert D.seed_class({**arm_ok, "a_A0": 0.49}, dense, 0.9) == core.NOT_EVALUATED
    assert D.seed_class(arm_ok, {**dense, "a_A0": 0.49}, 0.9) == core.NOT_EVALUATED
    assert (
        D.seed_class(arm_ok, dense, 0.0) == "INCREMENTAL_POSITIVE"
    )  # a zero bound cannot make B 'no new capability'
