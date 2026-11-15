# ruff: noqa: E501
"""P9I classes: every raw class, every class at a size, every annotation value and every selection outcome
(steps 0-4) triggered on synthetic measurements. Self-check only: not independent review, not Astra
validation, not human approval."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9i import classes as c  # noqa: E402
from studies.p9i import core  # noqa: E402
from studies.p9i.classes import Key, Measure  # noqa: E402

B101, B102 = core.PRIMARY_PARENT, core.REPLICATE_PARENT
PAIRS = [(s, p) for s in core.INIT_SEEDS for p in core.PANELS]
HI = 0.05  # upper end of the G2 interval as an accuracy


def fill(t: dict[Key, Measure], arm: str, slots: int, acc: float | dict[tuple[int, str], float], *, parent: tuple[int, int] = B101, hi: float = HI, dep: bool = True) -> None:
    pairs = PAIRS if parent == B101 else [(core.INIT_SEEDS[0], p) for p in core.PANELS]
    for s, p in pairs:
        a = acc[(s, p)] if isinstance(acc, dict) else acc
        t[(arm, slots, parent, s, p)] = Measure(a, hi, dep)


def table(r1: float = 0.95, slots: int = 16384) -> dict[Key, Measure]:
    t: dict[Key, Measure] = {}
    fill(t, "R1", slots, r1)
    return t


# --- step 1: raw classes ------------------------------------------------------------------------------------------
def test_raw_class_not_evaluated_when_r1_is_below_half_in_any_seed_or_panel() -> None:
    t = table()
    t[("R1", 16384, B101, 1802, "B")] = Measure(0.49, HI)
    fill(t, "W7", 16384, 0.99)
    assert c.size_not_evaluated(t, 16384)
    assert set(c.raw_classes(t, "W7", 16384).values()) == {c.NOT_EVALUATED}
    assert c.class_at_size(c.raw_classes(t, "W7", 16384)) == c.NOT_EVALUATED
    exactly = table(0.5)
    assert not c.size_not_evaluated(exactly, 16384)  # 0.5 is not below 0.5
    assert c.size_not_evaluated({}, 16384)  # no R1 record at all: nothing to compare with


def test_raw_class_works_partial_fails_and_their_boundaries() -> None:
    r1 = Measure(0.9, HI)
    assert c.raw_class(Measure(0.5, HI), Measure(0.5, HI)) == c.WORKS  # accuracy 0.5 and eta 1.0 are inclusive
    assert c.raw_class(Measure(0.81, HI), r1) == c.WORKS  # eta = 0.9 exactly
    assert c.raw_class(Measure(0.8099, HI), r1) == c.PARTIAL  # eta just below 0.90
    assert c.raw_class(Measure(0.6, HI, dependence_chance=False), Measure(0.6, HI)) == c.PARTIAL  # permutation or disabling not at chance
    assert c.raw_class(Measure(0.499, HI), Measure(0.5, HI)) == c.PARTIAL  # accuracy below 0.5
    assert c.raw_class(Measure(0.25, HI), r1) == c.PARTIAL  # 0.25 inclusive
    assert c.raw_class(Measure(0.2499, HI), r1) == c.FAILS
    assert c.raw_class(Measure(0.30, 0.35), r1) == c.FAILS  # not above the G2 interval
    assert c.raw_class(Measure(0.04, HI), r1) == c.FAILS
    assert c.raw_class(Measure(0.99, HI), r1, size_not_eval=True) == c.NOT_EVALUATED
    assert c.raw_class(Measure(0.6, HI), Measure(0.0, HI)) == c.WORKS  # eta = infinity
    assert c.raw_class(Measure(0.0, HI), Measure(0.0, HI)) == c.FAILS


def test_every_raw_class_is_reachable_through_the_tables() -> None:
    t = table()
    fill(t, "W7", 16384, 0.9)
    fill(t, "A4", 16384, 0.3)
    fill(t, "E7", 16384, 0.01)
    assert set(c.raw_classes(t, "W7", 16384).values()) == {c.WORKS}
    assert set(c.raw_classes(t, "A4", 16384).values()) == {c.PARTIAL}
    assert set(c.raw_classes(t, "E7", 16384).values()) == {c.FAILS}
    assert {c.NOT_EVALUATED, c.WORKS, c.PARTIAL, c.FAILS} == set(c.RAW_CLASSES)


# --- step 2: class at a size -------------------------------------------------------------------------------------------
def raws(a1: str, b1: str, a2: str, b2: str) -> dict[tuple[int, str], str]:
    return {(1801, "A"): a1, (1801, "B"): b1, (1802, "A"): a2, (1802, "B"): b2}


def test_class_at_size_every_value_and_the_precedence() -> None:
    W, P, F, N = c.WORKS, c.PARTIAL, c.FAILS, c.NOT_EVALUATED
    assert c.class_at_size(raws(W, W, W, W)) == c.INTERFACE_WORKS
    assert c.class_at_size(raws(P, P, P, P)) == c.INTERFACE_PARTIAL
    assert c.class_at_size(raws(F, F, F, F)) == c.INTERFACE_FAILS
    assert c.class_at_size(raws(W, W, P, P)) == c.INTERMEDIATE  # panels agree within a seed, seeds differ
    assert c.class_at_size(raws(W, P, W, W)) == c.NOT_REPLICATED  # panels differ in one seed
    assert c.class_at_size(raws(W, P, F, P)) == c.NOT_REPLICATED  # row 2 before row 3
    assert c.class_at_size(raws(N, N, N, N)) == c.NOT_EVALUATED
    assert c.class_at_size(raws(W, W, N, W)) == c.NOT_EVALUATED  # row 1 first
    with pytest.raises(ValueError):
        c.class_at_size({(1801, "A"): W})


def test_classify_applies_the_b102_rule_only_to_interface_works() -> None:
    t = table()
    fill(t, "W7", 16384, 0.9)
    fill(t, "R1", 16384, 0.95, parent=B102)
    fill(t, "W7", 16384, 0.9, parent=B102)
    r = c.classify(t, "W7", 16384)
    assert r.cls == c.INTERFACE_WORKS and r.b102_present and not r.b102_demoted
    fill(t, "W7", 16384, {(1801, "A"): 0.9, (1801, "B"): 0.01}, parent=B102)  # FAILS on one panel
    r = c.classify(t, "W7", 16384)
    assert r.cls == c.INTERMEDIATE and r.b102_demoted and r.b102 == {"A": c.WORKS, "B": c.FAILS}
    fill(t, "W7", 16384, {(1801, "A"): 0.9, (1801, "B"): 0.3}, parent=B102)  # PARTIAL is not FAILS
    assert c.classify(t, "W7", 16384).cls == c.INTERFACE_WORKS
    t2 = table()
    fill(t2, "W7", 16384, 0.9)
    r = c.classify(t2, "W7", 16384)  # no replicate: unchanged and reported
    assert r.cls == c.INTERFACE_WORKS and not r.b102_present
    t3 = table()
    fill(t3, "A4", 16384, 0.3)
    fill(t3, "R1", 16384, 0.95, parent=B102)
    fill(t3, "A4", 16384, 0.0, parent=B102)
    assert c.classify(t3, "A4", 16384).cls == c.INTERFACE_PARTIAL  # the rule does not touch other classes


def test_model_stores_facts_is_checked_after_the_b102_rule() -> None:
    t = table()
    fill(t, "BB", 16384, 0.9)
    fill(t, "BB-0", 16384, 0.01)
    r = c.classify(t, "BB", 16384)
    assert r.cls == c.INTERFACE_WORKS and r.model_stores_facts is False
    fill(t, "BB-0", 16384, {(1801, "A"): 0.01, (1801, "B"): 0.01, (1802, "A"): 0.01, (1802, "B"): 0.2})  # above chance on one seed and panel
    assert c.classify(t, "BB", 16384).cls == c.MODEL_STORES_FACTS
    fill(t, "BB", 16384, 0.3)  # not INTERFACE_WORKS: nothing to convert
    r = c.classify(t, "BB", 16384)
    assert r.cls == c.INTERFACE_PARTIAL and r.model_stores_facts is False
    t2 = table()  # a B102 FAILS demotes first, so BB-0 is not consulted
    fill(t2, "BB", 16384, 0.9)
    fill(t2, "BB-0", 16384, 0.9)
    fill(t2, "R1", 16384, 0.95, parent=B102)
    fill(t2, "BB", 16384, 0.0, parent=B102)
    assert c.classify(t2, "BB", 16384).cls == c.INTERMEDIATE


# --- annotations ---------------------------------------------------------------------------------------------------------
def test_dense_comparison_every_label() -> None:
    t = table()
    fill(t, "W7", 16384, 0.9)
    fill(t, "D7", 16384, 0.5)
    out = c.dense_comparison(t, "W7", 16384, c.INTERFACE_WORKS)
    assert out is not None and out["label"] == c.BEATS_DENSE and out["smallest"] == pytest.approx(1.8)
    fill(t, "D7", 16384, {(1801, "A"): 0.5, (1801, "B"): 0.5, (1802, "A"): 0.5, (1802, "B"): 0.9 / 1.05})  # one ratio 1.05
    out = c.dense_comparison(t, "W7", 16384, c.INTERFACE_WORKS)
    assert out is not None and out["label"] == c.DENSE_SUFFICES
    fill(t, "W7", 16384, 0.55)
    fill(t, "D7", 16384, 0.5)  # ratio 1.10 (>= is inclusive)
    out = c.dense_comparison(t, "W7", 16384, c.INTERFACE_PARTIAL)
    assert out is not None and out["label"] == c.BEATS_DENSE
    fill(t, "D7", 16384, 0.5001)
    out = c.dense_comparison(t, "W7", 16384, c.INTERFACE_PARTIAL)
    assert out is not None and out["label"] == c.DENSE_SUFFICES
    fill(t, "W7", 16384, 0.9)
    assert c.dense_comparison(t, "W7", 16384, c.INTERFACE_FAILS)["label"] == c.NOT_COMPARED  # type: ignore[index]
    assert c.dense_comparison(t, "W7", 16384, c.MODEL_STORES_FACTS)["label"] == c.NOT_COMPARED  # type: ignore[index]
    assert c.dense_comparison(t, "W7", 16384, c.INTERMEDIATE)["label"] == c.NOT_COMPARED  # type: ignore[index]
    assert c.dense_comparison(t, "A4", 16384, c.INTERFACE_WORKS)["label"] == c.NOT_COMPARED  # type: ignore[index]
    assert c.dense_comparison(t, "E7", 16384, c.INTERFACE_WORKS)["label"] == c.NOT_COMPARED  # type: ignore[index]
    assert c.dense_comparison(t, "W7", 4096, c.INTERFACE_WORKS) is None  # the dense arm does not run there
    fill(t, "D7", 16384, 0.0)
    out = c.dense_comparison(t, "W7", 16384, c.INTERFACE_WORKS)
    assert out is not None and out["label"] == c.BEATS_DENSE and math.isinf(out["smallest"])
    fill(t, "BB", 16384, 0.9)
    fill(t, "BB-D", 16384, 0.95)
    out = c.dense_comparison(t, "BB", 16384, c.INTERFACE_WORKS)
    assert out is not None and out["label"] == c.DENSE_SUFFICES  # BB against BB-D


def test_backbone_contrast_four_labels_and_not_printed() -> None:
    def pair(emb: float | dict[tuple[int, str], float], state: float) -> dict[Key, Measure]:
        t: dict[Key, Measure] = {}
        fill(t, "E7", 16384, emb)
        fill(t, "W7", 16384, state)
        return t

    live = {"E7": c.INTERFACE_WORKS, "W7": c.INTERFACE_WORKS}
    assert c.backbone_contrast(pair(0.93, 0.9), "E7", "W7", live)["label"] == c.BACKBONE_HURTS  # type: ignore[index]  # ratio 1.033
    assert c.backbone_contrast(pair(0.9, 0.9), "E7", "W7", live)["label"] == c.BACKBONE_NOTHING  # type: ignore[index]
    assert c.backbone_contrast(pair(0.88, 0.9), "E7", "W7", live)["label"] == c.BACKBONE_NOTHING  # type: ignore[index]  # 0.978
    assert c.backbone_contrast(pair(0.5, 0.9), "E7", "W7", live)["label"] == c.BACKBONE_CONTRIBUTES  # type: ignore[index]
    mixed = pair({(1801, "A"): 0.5, (1801, "B"): 0.9, (1802, "A"): 0.9, (1802, "B"): 0.99}, 0.9)
    assert c.backbone_contrast(mixed, "E7", "W7", live)["label"] == c.BACKBONE_MIXED  # type: ignore[index]
    both_fail = {"E7": c.INTERFACE_FAILS, "W7": c.INTERFACE_FAILS}
    assert c.backbone_contrast(pair(0.0, 0.0), "E7", "W7", both_fail) is None
    assert c.backbone_contrast(pair(0.0, 0.0), "E7", "W7", {"E7": c.INTERFACE_FAILS, "W7": c.INTERFACE_PARTIAL}) is not None
    assert c.backbone_contrast({}, "E7", "W7", live) is None  # missing measurements
    zero = c.backbone_contrast(pair(0.5, 0.0), "E7", "W7", {"E7": c.INTERFACE_PARTIAL, "W7": c.INTERFACE_FAILS})
    assert zero is not None and zero["label"] == c.BACKBONE_HURTS  # embedding positive over a zero state arm


def test_language_modelling_annotation_boundary() -> None:
    assert c.language_modelling_annotation({1801: 0.05, 1802: 0.0})["degraded"] is False  # "more than 5%"
    assert c.language_modelling_annotation({1801: 0.0, 1802: 0.0501})["label"] == c.LM_DEGRADED  # either seed
    assert c.language_modelling_annotation({1801: -0.2, 1802: 0.01})["degraded"] is False


# --- the selection rule ------------------------------------------------------------------------------------------------
ALL = core.SLOTS_BY_SIZE
W, P = c.INTERFACE_WORKS, c.INTERFACE_PARTIAL


def klasses(bb: str, a4: str, w7: str) -> dict[str, dict[int, str]]:
    return {"BB": dict.fromkeys(ALL, bb), "A4": dict.fromkeys(ALL, a4), "W7": dict.fromkeys(ALL, w7)}


def test_selection_step_0_is_inconclusive_for_each_status_and_is_not_step_4() -> None:
    for status in (core.TASK_CEILING_FAIL, core.ORACLE_QUERY_FAIL, c.NOT_EVALUATED):
        out = c.select(klasses(W, W, W), {4096: None, 16384: status, 65536: None})
        assert out.outcome == c.INCONCLUSIVE and out.step == 0 and out.inconclusive_sizes == {16384: status}
    both = c.select(klasses(P, P, P), {4096: core.TASK_CEILING_FAIL, 16384: None, 65536: c.NOT_EVALUATED})
    assert both.outcome == c.INCONCLUSIVE and set(both.inconclusive_sizes) == {4096, 65536}


def test_selection_steps_1_to_4() -> None:
    none: dict[int, str | None] = dict.fromkeys(ALL)
    assert c.select(klasses(W, W, W), none).outcome == c.SELECTED_BB  # step 1 first
    assert c.select(klasses(P, W, W), none).outcome == c.SELECTED_A4  # step 2
    assert c.select(klasses(c.MODEL_STORES_FACTS, W, W), none).outcome == c.SELECTED_A4  # MODEL_STORES_FACTS is not INTERFACE_WORKS
    assert c.select(klasses(P, P, W), none).outcome == c.SELECTED_W7  # step 3
    out = c.select(klasses(P, P, P), none)  # step 4
    assert out.outcome == c.NONE_SELECTED and out.step == 4 and not out.inconclusive_sizes
    partial_sizes = klasses(W, W, W)
    partial_sizes["BB"][65536] = c.INTERMEDIATE  # WORKS at two sizes only
    partial_sizes["A4"][4096] = c.NOT_REPLICATED
    assert c.select(partial_sizes, none).outcome == c.SELECTED_W7
    assert set(c.OUTCOMES) == {c.INCONCLUSIVE, c.SELECTED_BB, c.SELECTED_A4, c.SELECTED_W7, c.NONE_SELECTED, c.NOT_INTERPRETED, c.NOT_INTERPRETED_INCOMPLETE}


def test_selection_carries_the_scope_statements() -> None:
    none: dict[int, str | None] = dict.fromkeys(ALL)
    w7 = c.select(klasses(P, P, W), none, backbone_contrast_labels={"E7/W7": c.BACKBONE_NOTHING})
    assert c.SCOPE_ENCODER in w7.scope and c.SCOPE_W7_LIMIT in w7.scope and c.SCOPE_A4_W7_SYSTEM in w7.scope
    contributes = c.select(klasses(P, P, W), none, backbone_contrast_labels={"E7/W7": c.BACKBONE_CONTRIBUTES})
    assert c.SCOPE_ENCODER not in contributes.scope and c.SCOPE_W7_LIMIT in contributes.scope
    a4 = c.select(klasses(P, W, W), none, backbone_contrast_labels={"A4E/A4": c.BACKBONE_CONTRIBUTES, "E7/W7": None})
    assert c.SCOPE_ENCODER not in a4.scope and c.SCOPE_W7_LIMIT not in a4.scope
    assert c.select(klasses(W, W, W), none).scope == [c.SCOPE_BB]


# --- the whole analysis -----------------------------------------------------------------------------------------------------
def full_table(bb: float, a4: float, w7: float, *, r1: float = 0.95) -> dict[Key, Measure]:
    t: dict[Key, Measure] = {}
    for s in ALL:
        fill(t, "R1", s, r1)
        for arm, acc in (("BB", bb), ("A4", a4), ("W7", w7), ("BB-0", 0.01), ("D7", 0.3), ("BB-D", 0.3), ("E7", 0.01), ("A4E", 0.01), ("N", 0.01)):
            fill(t, arm, s, acc)
    return t


def test_analyze_classes_selects_bb_and_carries_annotations() -> None:
    lm = {("BB", s, seed): 0.01 for s in ALL for seed in core.INIT_SEEDS}
    out = c.analyze_classes(full_table(0.9, 0.9, 0.9), lm, {})
    assert out["selection"]["outcome"] == c.SELECTED_BB and out["selection"]["step"] == 1
    assert all(out["classes"]["BB"][str(s)] == c.INTERFACE_WORKS for s in ALL)
    assert out["classes"]["N"]["16384"] == c.INTERFACE_FAILS
    assert out["annotations"]["BB"]["16384"]["dense_comparison"]["label"] == c.BEATS_DENSE
    assert out["annotations"]["BB"]["16384"]["language_modelling"]["degraded"] is False
    assert out["backbone_contrast"]["E7/W7"]["label"] == c.BACKBONE_CONTRIBUTES  # 0.01 / 0.9
    lm_bad = {k: 0.2 for k in lm}
    degraded = c.analyze_classes(full_table(0.9, 0.9, 0.9), lm_bad, {})
    assert degraded["selection"]["outcome"] == c.SELECTED_BB  # does not block selection
    assert degraded["annotations"]["BB"]["4096"]["language_modelling"]["label"] == c.LM_DEGRADED


def test_analyze_classes_other_outcomes() -> None:
    assert c.analyze_classes(full_table(0.3, 0.9, 0.9), {}, {})["selection"]["outcome"] == c.SELECTED_A4
    assert c.analyze_classes(full_table(0.3, 0.3, 0.9), {}, {})["selection"]["outcome"] == c.SELECTED_W7
    assert c.analyze_classes(full_table(0.3, 0.3, 0.3), {}, {})["selection"]["outcome"] == c.NONE_SELECTED
    failed = c.analyze_classes(full_table(0.9, 0.9, 0.9), {}, {65536: "TASK_CEILING_FAIL"})
    assert failed["selection"]["outcome"] == c.INCONCLUSIVE and failed["selection"]["inconclusive_sizes"] == {"65536": "TASK_CEILING_FAIL"}
    assert "65536" not in failed["classes"]["BB"]  # a failed size is not run, not classified
    weak_oracle = c.analyze_classes(full_table(0.9, 0.9, 0.9, r1=0.4), {}, {})
    assert weak_oracle["selection"]["outcome"] == c.INCONCLUSIVE
    assert set(weak_oracle["size_status"].values()) == {c.NOT_EVALUATED}
    assert weak_oracle["classes"]["W7"]["4096"] == c.NOT_EVALUATED


def test_measures_from_eval_records_and_chance_interval() -> None:
    record = {
        "arm": "W7",
        "slots": 16384,
        "parent": [101, 301],
        "seed": 1801,
        "panels": {
            "A": {"accuracy": 0.5, "facts": 8192, "chance_interval": [200, 330], "memory_dependence_chance": True},
            "B": {"accuracy": 0.25, "facts": 8192, "chance_interval": [200, 330], "memory_dependence_chance": False},
        },
    }
    t = c.measures_from_eval({"x": record})
    a = t[("W7", 16384, (101, 301), 1801, "A")]
    b = t[("W7", 16384, (101, 301), 1801, "B")]
    assert a.accuracy == 0.5 and a.chance_high == pytest.approx(330 / 8192) and a.dependence_chance
    assert not b.dependence_chance
