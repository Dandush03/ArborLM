# ruff: noqa: E501
"""P9 Lane B analysis (package I6): utilization classes, SOFT-USAGE ONLY, REGULARIZER-DRIVEN MOVEMENT.

Synthetic records only. Self-check only: not independent review, not Astra validation, not human approval.
"""

import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p9_analysis_synth import (  # noqa: E402
    REF_ACC,
    E,
    case_cells,
    patch,
    patch_usage,
    util_world,
)

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import analysis_b as B  # noqa: E402
from studies.p9 import core  # noqa: E402

FLAT, TREE = "flat", "learned_tree"


def world(
    case: dict[str, Any] | None = None,
    *,
    acc: float | dict[str, float] = REF_ACC,
    ref_acc: float = REF_ACC,
    target: tuple[str, float] = (FLAT, 0.25),
    per_seed: dict[int, dict[str, Any]] | None = None,
):  # type: ignore[no-untyped-def]
    """B1 world in which the cells of ``target`` (arch, alpha_u) get ``acc`` and the ``case`` fields."""

    def acc_fn(c: core.Cell) -> float | dict[str, float]:
        return (
            acc
            if c.block == "B1" and (c.arch, c.alpha_u) == target
            else (ref_acc if c.block in ("A1", "A2") else REF_ACC)
        )

    def kw_fn(c: core.Cell) -> dict[str, Any]:
        if c.block == "B1" and (c.arch, c.alpha_u) == target:
            out = dict(case or {})
            out.update((per_seed or {}).get(c.seed, {}))
            return out
        return {}

    return util_world(acc_fn, kw_fn)


def group(target: tuple[str, float] = (FLAT, 0.25)) -> list[core.Cell]:
    return case_cells("B1", target[0], target[1])


def classify(w: Any, target: tuple[str, float] = (FLAT, 0.25), **kw: Any) -> core.ClassResult:
    return B.classify_utilization(w.index, group(target), E, **kw)


# --- references --------------------------------------------------------------------------------------------
def test_reference_labels() -> None:
    for c in core.cells():
        if c.block == "B1":
            ref = core.parse_label(B.reference_label(c))
            assert (
                ref.block,
                ref.arch,
                ref.slots,
                ref.seed,
                ref.alpha_u,
                ref.alpha_c,
                ref.parent,
            ) == ("A1" if c.arch == FLAT else "A2", c.arch, 16384, c.seed, 0.0, 0.0, c.parent)
        if c.block == "C1":
            ref = core.parse_label(B.reference_label(c))
            assert (ref.block, ref.arch, ref.alpha_u, ref.alpha_c, ref.seed) == (
                "B1",
                c.arch,
                0.25,
                0.0,
                c.seed,
            )
    with pytest.raises(ValueError):
        B.reference_label(next(c for c in core.cells() if c.block == "A1"))


def test_lane_b_evaluable_floor() -> None:
    assert B.lane_b_evaluable(world().index, E) == {FLAT: True, TREE: True}
    low = world(ref_acc=0.2)
    assert B.lane_b_evaluable(low.index, E) == {FLAT: False, TREE: False}
    one = world()
    victim = next(
        c
        for c in core.cells()
        if c.block == "A2"
        and c.slots == 16384
        and c.seed == 1702
        and c.parent == core.PRIMARY_PARENT
    )
    patch(one, victim, "B", correct=10, accuracy=10 / 8192)
    assert B.lane_b_evaluable(one.index, E) == {FLAT: True, TREE: False}
    assert B.lane_b_evaluable({}, E) == {FLAT: False, TREE: False}


# --- each class -------------------------------------------------------------------------------------------
def test_preserved() -> None:
    r = classify(world(acc=0.79))
    assert r["cls"] == "UTILIZATION_PRESERVED" and r["panel_classes"] == {
        "A": "UTILIZATION_PRESERVED",
        "B": "UTILIZATION_PRESERVED",
    }
    nums = r["details"]["panels"]["A"]["numbers"]["1701"]
    assert nums["I"] == pytest.approx(0.979, abs=0.003) and nums["ustar"] == 1.0
    assert r["lane"] == "B" and r["subject"] == "B1/flat/au0.25/ac0"


def test_improved_and_the_support_length_condition() -> None:
    r = classify(world({"useful_slots": 1100, "mean_support_length": 2.1}, acc=0.85))
    assert r["cls"] == "UTILIZATION_IMPROVED"
    longer = classify(
        world({"useful_slots": 1100, "mean_support_length": 2.3}, acc=0.85)
    )  # ratio 1.15 > 1.10
    assert longer["cls"] == "UTILIZATION_PRESERVED"
    no_ustar_gain = classify(world({"useful_slots": 1010}, acc=0.85))
    assert no_ustar_gain["cls"] == "UTILIZATION_PRESERVED"


def test_collapsed_by_ustar_by_information_and_before_entropy_inflation() -> None:
    assert classify(world({"useful_slots": 700}))["cls"] == "COLLAPSED"
    assert classify(world(acc=0.6))["cls"] == "COLLAPSED"  # I ratio about 0.62
    assert (
        classify(
            world(
                {
                    "useful_slots": 700,
                    "usage": {
                        "entropy_effective_hard": 2000.0,
                        "entropy_soft": 6.0,
                        "key_movement_without_task_grad": 10.0,
                        "key_movement_share_without": 0.9,
                    },
                }
            )
        )["cls"]
        == "COLLAPSED"
    )


def test_entropy_inflation() -> None:
    usage = {
        "entropy_effective_hard": 1300.0,
        "entropy_soft": 6.0,
        "key_movement_without_task_grad": 10.0,
        "key_movement_share_without": 0.9,
    }
    assert classify(world({"usage": usage}))["cls"] == "ENTROPY_INFLATION"
    assert (
        classify(world({"usage": {**usage, "entropy_effective_hard": 1200.0}}))["cls"]
        == "UTILIZATION_PRESERVED"
    )  # ratio 1.2 < 1.25
    assert (
        classify(world({"usage": usage, "useful_slots": 1040}))["cls"] == "UTILIZATION_PRESERVED"
    )  # U* ratio 1.04 >= 1.03


def test_no_difference_intermediate() -> None:
    r = classify(world(acc=0.78))
    assert r["cls"] == B.NO_DIFFERENCE == "NO DIFFERENCE / INTERMEDIATE"


def test_accuracy_drop_clause_and_nan_never_satisfy_a_rule() -> None:
    n = B.SeedNumbers(1.0, 1.0, 1.0, 1.0, 0.03, True)
    assert B.class_from_numbers(n) == B.NO_DIFFERENCE  # drop 0.03 > 0.02
    assert (
        B.class_from_numbers(B.SeedNumbers(1.0, 1.0, 1.0, 1.0, 0.02, True))
        == "UTILIZATION_PRESERVED"
    )
    assert (
        B.class_from_numbers(B.SeedNumbers(math.nan, math.nan, math.nan, math.nan, 0.0, True))
        == B.NO_DIFFERENCE
    )
    assert (
        B.class_from_numbers(B.SeedNumbers(1.0, 1.0, 1.0, math.nan, 0.0, True))
        == "UTILIZATION_PRESERVED"
    )
    assert (
        B.class_from_numbers(B.SeedNumbers(1.06, 1.06, 1.0, math.nan, 0.0, True))
        == "UTILIZATION_PRESERVED"
    )  # IMPROVED needs the support-length ratio


def test_ustar_not_interpretable_rules() -> None:
    good = {"useful_slots": 1100, "mean_support_length": 2.1}
    r = classify(world({**good, "ustar_interpretable": False}, acc=0.85))
    assert r["cls"] == core.INTERMEDIATE  # IMPROVED becomes INTERMEDIATE
    # collapse of U* alone is not judged; the I ratio alone decides
    assert (
        classify(world({"useful_slots": 500, "ustar_interpretable": False}))["cls"]
        == core.INTERMEDIATE
    )
    assert (
        classify(world({"useful_slots": 500, "ustar_interpretable": False}, acc=0.6))["cls"]
        == "COLLAPSED"
    )
    # U* NOT INTERPRETABLE for the reference only
    w = world({"useful_slots": 500})
    ref = next(
        c
        for c in core.cells()
        if c.block == "A1"
        and c.slots == 16384
        and c.seed == 1701
        and c.parent == core.PRIMARY_PARENT
    )
    patch(w, ref, ustar_interpretable=False)
    assert classify(w)["cls"] == core.INTERMEDIATE
    # an unrecorded flag (None) counts as not interpretable
    none = world({"ustar_interpretable": None})
    assert classify(none)["cls"] == core.INTERMEDIATE


# --- seeds and panels -------------------------------------------------------------------------------------------
def test_seeds_that_disagree_give_intermediate() -> None:
    r = classify(world(per_seed={1702: {"useful_slots": 700}}))
    assert r["cls"] == core.INTERMEDIATE
    assert r["details"]["panels"]["A"]["seed_classes"] == {
        "1701": "UTILIZATION_PRESERVED",
        "1702": "COLLAPSED",
    }
    # improved in one seed, preserved in the other: the seeds disagree
    mixed = classify(
        world(
            {"useful_slots": 1100, "mean_support_length": 2.1},
            acc=0.85,
            per_seed={1702: {"mean_support_length": 2.4}},
        )
    )
    assert (
        mixed["details"]["panels"]["A"]["seed_classes"]
        == {"1701": "UTILIZATION_IMPROVED", "1702": "UTILIZATION_PRESERVED"}
        and mixed["cls"] == core.INTERMEDIATE
    )
    assert (
        B.combine_seeds(["COLLAPSED", "COLLAPSED"]) == "COLLAPSED"
        and B.combine_seeds([B.NO_DIFFERENCE, core.INTERMEDIATE]) == core.INTERMEDIATE
    )


def test_panels_that_disagree_are_not_replicated() -> None:
    r = classify(world(acc={"A": 0.79, "B": 0.6}))
    assert (
        r["panel_classes"] == {"A": "UTILIZATION_PRESERVED", "B": "COLLAPSED"}
        and r["cls"] == core.NOT_REPLICATED
    )
    # 'NO DIFFERENCE / INTERMEDIATE' and 'INTERMEDIATE' both mean 'no class' and do not disagree
    both = classify(world(acc={"A": 0.78, "B": 0.78}, per_seed={1702: {"useful_slots": 700}}))
    assert both["cls"] == core.INTERMEDIATE


def test_not_evaluated_conditions() -> None:
    low = classify(world(ref_acc=0.2, acc=0.2))
    assert low["cls"] == core.NOT_EVALUATED and "below 0.25" in low["details"]["reason"]
    ceiling = classify(world(), ceiling_fail=(16384,))
    assert (
        ceiling["cls"] == core.NOT_EVALUATED
        and "TASK_CEILING_FAIL(16384)" in ceiling["annotations"]
    )
    assert classify(world(), ceiling_fail=(65536,))["cls"] == "UTILIZATION_PRESERVED"


def test_incomplete_when_a_cell_is_missing() -> None:
    w = world()
    victim = group()[1]
    w.drop(victim, ("B",))
    r = classify(w)
    assert r["cls"] == A.INCOMPLETE and any(victim.label in m for m in r["details"]["missing"])
    assert B.classify_utilization_panel(w.index, victim, "B", E) == A.INCOMPLETE
    assert B.classify_utilization(util_world(blocks=()).index, group(), E)["cls"] == A.INCOMPLETE


# --- annotations ----------------------------------------------------------------------------------------------------
M = math.log(core.usage_floor_support(16384, 8192))  # ln 8192, the floor of the global usage term


def usage(**kw: float) -> dict[str, float]:
    return {
        "entropy_effective_hard": 1000.0,
        "entropy_soft": 6.0,
        "key_movement_without_task_grad": 10.0,
        "key_movement_share_without": 0.9,
        **kw,
    }


def test_soft_usage_only() -> None:
    soft = world({"usage": usage(entropy_soft=M + 0.1)})
    r = classify(soft)
    assert (
        B.SOFT_USAGE_ONLY in r["annotations"] and r["cls"] == "UTILIZATION_PRESERVED"
    )  # the annotation does not change the class
    assert B.soft_usage_only(soft.index, group()[0], "A", E) is True
    below = world({"usage": usage(entropy_soft=M - 0.1)})
    assert B.SOFT_USAGE_ONLY not in classify(below)["annotations"]
    harder = world(
        {"usage": usage(entropy_soft=M + 0.1, entropy_effective_hard=1100.0)}
    )  # hard ratio 1.10 >= 1.05
    assert B.SOFT_USAGE_ONLY not in classify(harder)["annotations"]
    one_seed = world(per_seed={1702: {"usage": usage(entropy_soft=M + 0.1)}})
    assert B.SOFT_USAGE_ONLY not in classify(one_seed)["annotations"]
    missing_key = world({"usage": {"entropy_effective_hard": 1000.0}})
    assert B.SOFT_USAGE_ONLY not in classify(missing_key)["annotations"]
    assert B.USAGE_KEYS["soft_entropy"] == "entropy_soft"


def test_regularizer_driven_movement() -> None:
    drive = world({"usage": usage(key_movement_without_task_grad=16.0)})  # 1.6 x the reference (10)
    r = classify(drive)
    assert B.REGULARIZER_MOVEMENT in r["annotations"] and r["cls"] == "UTILIZATION_PRESERVED"
    assert B.regularizer_driven_movement(drive.index, group()[0], E) is True
    assert (
        B.REGULARIZER_MOVEMENT
        not in classify(world({"usage": usage(key_movement_without_task_grad=14.0)}))["annotations"]
    )
    assert (
        B.REGULARIZER_MOVEMENT
        not in classify(world({"usage": usage(key_movement_without_task_grad=15.0)}))["annotations"]
    )  # exactly 1.5 x is not more than 1.5 x
    only_one = world(per_seed={1702: {"usage": usage(key_movement_without_task_grad=30.0)}})
    assert B.REGULARIZER_MOVEMENT not in classify(only_one)["annotations"]
    # the share of movement without gradient is reported but never compared with a fixed fraction
    share = world({"usage": usage(key_movement_share_without=0.99)})
    assert B.REGULARIZER_MOVEMENT not in classify(share)["annotations"]
    assert B.usage_value(
        share.index[next(iter(share.index))], "movement_share_without"
    ) == pytest.approx(0.9)


def test_leakage_annotation_on_a_b1_class() -> None:
    w = world()
    patch(w, group()[0], "A", unseen_correct=500)
    r = classify(w)
    assert (
        B.LEAKAGE in r["annotations"]
        and "interpretation_withheld" in r["details"]
        and r["cls"] == "UTILIZATION_PRESERVED"
    )


def test_ratios_named_by_seed() -> None:
    w = world({"useful_slots": 1100, "mean_support_length": 2.1}, acc=0.85)
    ratios = B.utilization_ratios(w.index, group()[1], "B", E)
    assert set(ratios) == {
        "I_s1702",
        "ustar_s1702",
        "eff_hard_s1702",
        "support_length_s1702",
        "accuracy_drop_s1702",
    }
    assert (
        ratios["ustar_s1702"] == pytest.approx(1.1)
        and ratios["support_length_s1702"] == pytest.approx(1.05)
        and ratios["accuracy_drop_s1702"] == pytest.approx(-0.05, abs=0.01)
    )
    with pytest.raises(A.MissingRecord):
        B.utilization_ratios({}, group()[0], "A", E)


def test_analyze_returns_the_four_b1_cases_for_both_architectures() -> None:
    results = B.analyze(world().index, E)
    assert [r["subject"] for r in results] == [
        "B1/flat/au0.25/ac0",
        "B1/flat/au1/ac0",
        "B1/learned_tree/au0.25/ac0",
        "B1/learned_tree/au1/ac0",
    ]
    assert all(r["lane"] == "B" for r in results)
    assert [r["cls"] for r in B.analyze({}, E)] == [A.INCOMPLETE] * 4
    assert {r["cls"] for r in B.analyze(world().index, E, ceiling_fail=(16384,))} == {
        core.NOT_EVALUATED
    }


def test_every_utilization_class_is_reachable() -> None:
    reached = {
        classify(world({"useful_slots": 700}))["cls"],
        classify(world({"usage": usage(entropy_effective_hard=1300.0)}))["cls"],
        classify(world({"useful_slots": 1100, "mean_support_length": 2.1}, acc=0.85))["cls"],
        classify(world(acc=0.79))["cls"],
        classify(world(acc=0.78))["cls"],
        classify(world(acc={"A": 0.79, "B": 0.6}))["cls"],
        classify(world(per_seed={1702: {"useful_slots": 700}}))["cls"],
    }
    assert reached == {
        "COLLAPSED",
        "ENTROPY_INFLATION",
        "UTILIZATION_IMPROVED",
        "UTILIZATION_PRESERVED",
        B.NO_DIFFERENCE,
        core.NOT_REPLICATED,
        core.INTERMEDIATE,
    }
    assert set(B.UTILIZATION_CLASSES) >= reached - {core.INTERMEDIATE}


def test_usage_patch_helper_is_used_for_per_cell_usage() -> None:
    w = world()
    patch_usage(w, group()[0], "A", entropy_soft=99.0)
    assert (
        w.index[(group()[0].label, core.updates(group()[0], E), "panel_a")]["usage"]["entropy_soft"]
        == 99.0
    )
