# ruff: noqa: E501
"""P10S2 gates, mechanism classes, study labels, annotations, cost lines and the recomputation rule, on synthetic records of the whole registry (ADR-0022 sections 11, 13.3): missing, failed and non-finite
cells, rejected consolidations, inertia cells and every outcome row. The numbers are constructed to exercise the rules; they are not results. Self-check only: not independent review, not Astra
validation, not human approval."""

import copy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import analysis, core, recompute  # noqa: E402
from studies.p10s2 import classes as C  # noqa: E402
from studies.p10s2.registry import registry  # noqa: E402

S0, TEACHER = 0.1, 0.9  # Stage 0 and teacher scores on every panel: G = (s - 0.1) / 0.8


def comb_rec(s_a: float = 0.8, s_b: float = 0.8, c1: tuple[float, float] = (0.78, 0.78), c2: tuple[float, float] = (0.78, 0.78), n: int = 6, pass_rate: float = 0.5) -> dict[str, Any]:
    """A combined-task record of the addendum's structure: single-task scores per E_C sentence (constant per language), and per-answer means for the items in which an answer is tested (C1: second
    position; C2: both answers on all items)."""
    half = n // 2
    tested1 = {"A": list(range(half)), "B": list(range(half, n))}
    tested2 = {"A": list(range(n)), "B": list(range(n))}
    return {
        "n": n, "arm": "synthetic", "single": {"scores": {"A": [s_a] * n, "B": [s_b] * n}},
        "C1": {"mean": (c1[0] + c1[1]) / 2, "pass_rate": pass_rate, "tested_sentences": tested1, "tested_by_language": {"A": c1[0], "B": c1[1]}, "second_by_language": {"A": c1[0], "B": c1[1]}},
        "C2": {"mean": (c2[0] + c2[1]) / 2, "pass_rate": pass_rate, "tested_sentences": tested2, "tested_by_language": {"A": c2[0], "B": c2[1]}, "second_by_language": {"A": None, "B": c2[1]}},
    }  # fmt: skip


def panel(m: Any) -> dict[str, Any]:
    return {"mean": m, "items": [m, m, m], "exact": [False, False, False], "sequences": [[1, 2], [3], [4]], "exact_rate": 0.0}


def good_scores() -> dict[tuple[str, str], tuple[float, float]]:
    return {
        ("ST1", "AB"): (0.8, 0.1), ("ST1", "BA"): (0.1, 0.8), ("MAF", "AB"): (0.8, 0.78), ("MAF", "BA"): (0.78, 0.8), ("MII", "AB"): (0.8, 0.78), ("MII", "BA"): (0.78, 0.8),
        ("MSEQ", "AB"): (0.15, 0.78), ("MSEQ", "BA"): (0.78, 0.15), ("LORA1", "AB"): (0.8, 0.1), ("LORA1", "BA"): (0.1, 0.8), ("LSEQ", "AB"): (0.1, 0.8), ("LSEQ", "BA"): (0.8, 0.1),
        ("ETABLE", "A"): (0.78, 0.1), ("ETABLE", "B"): (0.1, 0.78), ("MAGOLD", "A"): (0.8, 0.1), ("MAGOLD", "B"): (0.1, 0.8), ("MJOINT", "-"): (0.78, 0.78), ("LJOINT", "-"): (0.8, 0.8),
    }  # fmt: skip


MEMORY = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD")
GEN_GROUPS = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "LSEQ")


def cell_record(r: int, group: str, variant: str, ea: float, eb: float) -> dict[str, Any]:
    label = f"r{r}/{group}/{variant}"
    snap: dict[str, Any] = {"panels": {"E_A": panel(ea), "E_B": panel(eb)}, "arm_hash": "h", "parameters": 1}
    if group in MEMORY:
        snap["ablations"] = {p: {"subsample_indices": [0, 1], "unablated": panel(m), "off": panel(0.1), "value_perm": panel(0.1), "code_perm": panel(0.1), "marker_only": panel(0.15), "words_only": panel(0.12)} for p, m in (("E_A", ea), ("E_B", eb))}
    if group in GEN_GROUPS:
        snap["gen"] = {"loss_increase": 0.001, "loss_increase_first_marker": 0.001, "false_trigger_count": {"marker": 0, "ordinary": 0}, "stratum_sizes": {"marker": 4, "ordinary": 4}, "passes": True}
        snap["gen_by_construction"] = {"bit_identical_to_student": True, "label": "BY CONSTRUCTION"}
        if group in ("MAF", "LSEQ"):
            snap["gen"]["always_on_loss_increase"] = 0.2
    if group in ("ST1", "MAF"):
        snap["learned_route"] = {"E_A": panel(ea), "E_B": panel(eb)}
    if group in ("MAF", "MII", "MJOINT", "LSEQ", "LJOINT"):
        snap["combined"] = comb_rec()
    snap["work"] = {"kind": "memory", "key_products_per_read": 2 * 4096, "value_parameters_read_per_generated_token": 100.0} if group in MEMORY else {"kind": "lora", "adapter_parameters_applied_per_generated_token": 2419200}
    scores = {label: snap}
    extras: dict[str, Any] = {}
    if group == "MAF":
        scores[label + "@append"] = {"panels": {"E_A": panel(0.5 if variant[0] == "A" else 0.78), "E_B": panel(0.5 if variant[0] == "B" else 0.78)}}
    if group == "MII":
        extras["consolidation"] = {"rejected": False, "below_floor": False, "relative_change": 0.3, "published": True}
    return {"label": label, "status": "completed", "train": [{"wall_seconds": 10.0 if group != "LORA1" else 8.0, "status": "completed"}], "scores": scores, "extras": extras}


def study(n: int = 2, tweak: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    reps = []
    for r in range(n):
        cells = {c.label: cell_record(r, c.group, c.variant, *good_scores()[(c.group, c.variant)]) for c in registry(n) if c.replicate == r}
        reps.append({
            "cells": cells,
            "assembled": {"L-sep": {"E_A": panel(0.8), "E_B": panel(0.8), "combined": comb_rec()}, "M-i-separate": {"E_A": panel(0.8), "E_B": panel(0.8), "combined": comb_rec()}},
            "retrieval": {c: {"R-icl": {"mean": 0.3}, "R-nn": {"mean": 0.3}, "R-gloss": {"mean": 0.3}, "R-exact": {"hits": 0, "mean": 0.0}} for c in core.TASKS},
            "routers": {"AB": {"accuracy": {"A": 1.0, "B": 1.0, "general": 1.0}}},
            "ensemble": {"oracle": {"A": 0.9, "B": 0.9}, "teacher_own": {"A": 0.9, "B": 0.9}},
        })  # fmt: skip
    base = {"student": {p: {"panel": {**panel(S0)}, "subsample": panel(S0)} for p in ("E_A", "E_B")}, "teacher": {p: {"mean": TEACHER, "subsample_mean": TEACHER, "exact_rate": 0.9} for p in ("E_A", "E_B")},
            "combined": {"stage0": comb_rec(S0, S0, (S0, S0), (S0, S0)), "ensemble": comb_rec(TEACHER, TEACHER, (TEACHER, TEACHER), (TEACHER, TEACHER))}}  # fmt: skip
    for p in base["student"].values():
        p["panel"]["exact_rate"] = 0.0
    s: dict[str, Any] = {"design": {"replicates": n, "updates": 2000}, "prefreeze": {"teacher_only": True, "stop": None}, "gates": {g: {"ok": True} for g in ("G1", "G4", "G5", "G6", "G7", "G8", "G9")}, "baseline": base, "replicates": reps, "incomplete": [], "engineering": []}
    if tweak:
        tweak(s)
    return s


def cell(s: dict[str, Any], r: int, group: str, variant: str) -> dict[str, Any]:
    c: dict[str, Any] = s["replicates"][r]["cells"][f"r{r}/{group}/{variant}"]
    return c


def set_panels(s: dict[str, Any], r: int | None, group: str, variant: str, ea: float | str, eb: float | str) -> None:
    for rr in range(len(s["replicates"])) if r is None else [r]:
        c = cell(s, rr, group, variant)
        sn = c["scores"][c["label"]]
        sn["panels"]["E_A"], sn["panels"]["E_B"] = panel(ea), panel(eb)
        if "ablations" in sn:
            for p, m in (("E_A", ea), ("E_B", eb)):
                sn["ablations"][p]["unablated"] = panel(m)


def classes_of(out: dict[str, Any], mech: str) -> tuple[str, str]:
    return out["classes"][mech]["AB"]["class"], out["classes"][mech]["BA"]["class"]


# --- the all-good scenario and each label row -----------------------------------------------------------------------------------------------------------
def test_all_good_gives_row_7_and_classes() -> None:
    out = analysis.analyze(study())
    assert out["label_row"] == 7 and out["label"] == "TRANSFER-POSITIVE (append-frozen + consolidation)"
    assert out["label_with_design"] == "TRANSFER-POSITIVE (append-frozen + consolidation) (2 replicates, U = 2000)"
    assert classes_of(out, "M-append-frozen") == ("ACQUIRES-AND-RETAINS",) * 2 and classes_of(out, "M-ii") == ("ACQUIRES-AND-RETAINS",) * 2
    assert classes_of(out, "M-seq") == ("FORGETS",) * 2 and classes_of(out, "L-seq") == ("FORGETS",) * 2  # sequential training without growth or replay forgets
    assert out["engineering"] == [] and out["incomplete"] == [] and out["control_failed"] == []
    a = out["annotations"]
    assert a["TASK-CODED SPARSE RETENTION"] is False  # both forget by the same amount here
    assert a["EQUIVALENT TO A WORD TABLE"] is True and a["NO ADVANTAGE OVER SEPARATE ADAPTERS"] is True and a["BELOW JOINT BOUND"] is False
    assert a["ROUTER (keyword-level) QUALIFIED"] is True and a["TEACHER-EQUIVALENT-TO-GOLD"] is True
    assert a["APPEND COST"]["change_in_G_first_at_append"]["r0/AB"] == pytest.approx((0.5 - S0) / 0.8 - (0.8 - S0) / 0.8)
    comp = out["composition"]["arms"]
    assert all(comp[k][arm]["composition"] == "COMPOSES" for k in ("C1", "C2") for arm in ("M-append-frozen", "M-ii", "L-seq", "M-joint", "L-joint", "M-i-separate", "L-sep")) and "COMPOSES" not in a
    assert a["RETRIEVAL SUFFICES"] is False and a["LEXICON-EQUIVALENT"] is False
    assert len(out["cost_lines"]) == 4 and out["cost_lines"][0].startswith("TRAINING COST HIGHER") is False
    assert any("FEWER VALUE ROWS ACTIVE" in x for x in out["cost_lines"]) and any("0.938" in x for x in out["cost_lines"])
    assert out["gates"]["M-append-frozen/AB"][0]["acq2"]["ok"] is True


def test_row_8_when_the_consolidation_arm_is_rejected_or_inert_or_fails_gen_alone() -> None:
    rej = analysis.analyze(study(tweak=lambda s: cell(s, 1, "MII", "AB")["extras"]["consolidation"].update(rejected=True, published=False)))
    assert classes_of(rej, "M-ii")[0] == "INTERMEDIATE" and classes_of(rej, "M-ii")[1] == "ACQUIRES-AND-RETAINS"
    assert rej["label_row"] == 8 and rej["label"] == "TRANSFER-POSITIVE (append-frozen)"
    inert = analysis.analyze(study(tweak=lambda s: cell(s, 0, "MII", "BA")["extras"]["consolidation"].update(below_floor=True, relative_change=0.01)))
    assert classes_of(inert, "M-ii") == ("ACQUIRES-AND-RETAINS", "RETENTION BY INERTIA") and inert["label_row"] == 8
    gen_alone = analysis.analyze(study(tweak=lambda s: cell(s, 0, "MII", "AB")["scores"]["r0/MII/AB"]["gen"].update(loss_increase=0.05)))
    assert gen_alone["label_row"] == 8  # when M-ii alone fails GEN, row 8 applies


def test_row_6_when_general_quality_is_not_preserved_under_the_learned_route() -> None:
    def tweak(s: dict[str, Any]) -> None:
        cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["gen"]["loss_increase"] = 0.0201
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] == 6 and out["label"].startswith("TRANSFER-POSITIVE WITHHELD") and "GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE" in out["label"]
    boundary = analysis.analyze(study(tweak=lambda s: cell(s, 0, "MAF", "AB")["scores"]["r0/MAF/AB"]["gen"].update(loss_increase=0.02)))
    assert boundary["label_row"] == 7  # exactly 0.02 nats passes (loss <= student + 0.02)
    def st1_fail(s: dict[str, Any]) -> None:
        cell(s, 0, "ST1", "AB")["scores"]["r0/ST1/AB"]["gen"]["loss_increase"] = 0.5
    assert analysis.analyze(study(tweak=st1_fail))["label_row"] == 6  # GEN is measured for every ST1 and stage-2 snapshot
    nonfinite = analysis.analyze(study(tweak=lambda s: cell(s, 0, "MAF", "AB")["scores"]["r0/MAF/AB"]["gen"].update(loss_increase="nan")))
    assert nonfinite["label_row"] == 12 and nonfinite["gen"]["status"]["M-append-frozen"]["AB"] == "not_evaluated"  # a non-finite value is not a hold, and not a measured failure either: row 6 asserts a failure
    not_teacher_only = analysis.analyze(study(tweak=lambda s: s["prefreeze"].update(teacher_only=False)))
    assert not_teacher_only["label_row"] == 12  # no positive row without teacher-only training material


def test_rows_9_10_11_12_forgetting_no_additional_acquisition_order_and_the_rest() -> None:
    def forgets(s: dict[str, Any]) -> None:
        set_panels(s, None, "MAF", "AB", 0.15, 0.78)
        set_panels(s, None, "MAF", "BA", 0.78, 0.15)
    f = analysis.analyze(study(tweak=forgets))
    assert classes_of(f, "M-append-frozen") == ("FORGETS", "FORGETS") and f["label_row"] == 9 and f["label"] == "TRANSFER-NEGATIVE: FORGETTING"

    def none_new(s: dict[str, Any]) -> None:
        set_panels(s, None, "MAF", "AB", 0.8, 0.1)
        set_panels(s, None, "MAF", "BA", 0.1, 0.8)
    n = analysis.analyze(study(tweak=none_new))
    assert classes_of(n, "M-append-frozen") == ("NO-NEW-CAPABILITY",) * 2 and n["label_row"] == 10 and n["label"] == "TRANSFER-NEGATIVE: NO-ADDITIONAL-ACQUISITION"

    o = analysis.analyze(study(tweak=lambda s: set_panels(s, None, "MAF", "BA", 0.1, 0.8)))
    assert classes_of(o, "M-append-frozen")[0] == "ACQUIRES-AND-RETAINS" and classes_of(o, "M-append-frozen")[1] != "ACQUIRES-AND-RETAINS"
    assert o["label_row"] == 11 and o["label"] == "TRANSFER-INCONCLUSIVE: ORDER-DEPENDENT"

    def middling(s: dict[str, Any]) -> None:
        set_panels(s, None, "MAF", "AB", 0.8, 0.45)  # G_second 0.44: not the negative zone, below 0.50
        set_panels(s, None, "MAF", "BA", 0.45, 0.8)
    m = analysis.analyze(study(tweak=middling))
    assert classes_of(m, "M-append-frozen") == ("INTERMEDIATE",) * 2 and m["label_row"] == 12 and m["label"] == "TRANSFER-INCONCLUSIVE"


def test_not_replicated_needs_one_passing_replicate_and_one_in_a_negative_zone() -> None:
    def tweak(s: dict[str, Any]) -> None:
        set_panels(s, 1, "MAF", "AB", 0.8, 0.1)  # replicate 1: the second capability is not acquired (negative zone); replicate 0 passes
    out = analysis.analyze(study(tweak=tweak))
    assert classes_of(out, "M-append-frozen")[0] == "NOT REPLICATED" and classes_of(out, "M-append-frozen")[1] == "ACQUIRES-AND-RETAINS"
    assert out["label_row"] == 11
    def retention_zone(s: dict[str, Any]) -> None:
        set_panels(s, 1, "MAF", "BA", 0.1, 0.8)  # replicate 1 forgets the first capability, replicate 0 passes
    assert analysis.analyze(study(tweak=retention_zone))["classes"]["M-append-frozen"]["BA"]["class"] == "NOT REPLICATED"


def test_not_evaluated_when_acq1_fails_or_a_gap_is_undefined_or_a_value_is_not_finite() -> None:
    def lexical(s: dict[str, Any]) -> None:  # the permuted control gives G 0.6 on the subsample: the margin 0.875 - 0.625 < 0.30
        cell(s, 0, "ST1", "AB")["scores"]["r0/ST1/AB"]["ablations"]["E_A"]["value_perm"] = panel(0.6)
    out = analysis.analyze(study(tweak=lexical))
    assert classes_of(out, "M-append-frozen")[0] == "NOT_EVALUATED" and any("lexical margin below 0.30" in r for r in out["classes"]["M-append-frozen"]["AB"]["reasons"])
    assert out["label_row"] == 5 and out["label"] == "TRANSFER-INCONCLUSIVE: CONTROL-FAILED"  # a value permutation gives G >= 0.50 in a cell (0.625)

    def marker(s: dict[str, Any]) -> None:
        cell(s, 0, "ST1", "BA")["scores"]["r0/ST1/BA"]["ablations"]["E_B"]["marker_only"] = panel(0.5)  # G 0.5 > 0.25
    out = analysis.analyze(study(tweak=marker))
    assert any("marker-only above 0.25" in r for r in out["classes"]["M-append-frozen"]["BA"]["reasons"]) and out["label_row"] == 11  # one order is NOT_EVALUATED, the other acquires and retains
    assert any("marker-only above 0.25" in x for x in out["not_evaluated_reasons"])  # every TRANSFER-INCONCLUSIVE label prints the reason of each NOT_EVALUATED class

    def low(s: dict[str, Any]) -> None:
        set_panels(s, 0, "ST1", "AB", 0.45, 0.1)
    out = analysis.analyze(study(tweak=low))
    assert any("acquisition below 0.50" in r for r in out["classes"]["M-append-frozen"]["AB"]["reasons"])

    def undefined(s: dict[str, Any]) -> None:
        s["baseline"]["teacher"]["E_B"] = {"mean": 0.3, "subsample_mean": 0.3, "exact_rate": 0.9}  # 0.3 - 0.1 = 0.2 < 0.30
    out = analysis.analyze(study(tweak=undefined))
    assert any("undefined gap" in r for r in out["classes"]["M-append-frozen"]["AB"]["reasons"]) and out["label"] == "TRANSFER-INCONCLUSIVE"

    out = analysis.analyze(study(tweak=lambda s: set_panels(s, 0, "MAF", "AB", 0.8, "nan")))
    assert classes_of(out, "M-append-frozen")[0] == "NOT_EVALUATED"  # a non-finite score is never turned into a number
    out = analysis.analyze(study(tweak=lambda s: set_panels(s, 0, "MAF", "AB", 0.8, "inf")))
    assert classes_of(out, "M-append-frozen")[0] == "NOT_EVALUATED"


def test_rows_4_and_5_no_acquisition_and_control_failed() -> None:
    def none(s: dict[str, Any]) -> None:
        for o in core.ORDERS:
            first = (0.15, 0.1) if o == "AB" else (0.1, 0.15)
            set_panels(s, None, "ST1", o, *first)
    out = analysis.analyze(study(tweak=none))
    assert out["label_row"] == 4 and out["label"] == "TRANSFER-NEGATIVE: NO-ACQUISITION"
    one = analysis.analyze(study(tweak=lambda s: set_panels(s, 0, "ST1", "AB", 0.15, 0.1)))
    assert one["label_row"] != 4  # in every replicate and for both capabilities

    def code_ctrl(s: dict[str, Any]) -> None:
        cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["ablations"]["E_A"]["code_perm"] = panel(0.7)  # the second capability of order BA is A
    out = analysis.analyze(study(tweak=code_ctrl))
    assert out["label_row"] == 5 and any("code_perm" in x for x in out["control_failed"])
    # the control of a stage-2 arm is read on the second capability's panel: a permuted first-stage read leaves the first capability intact and is not a failure
    def first_panel(s: dict[str, Any]) -> None:
        cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["ablations"]["E_B"]["code_perm"] = panel(0.7)
    assert analysis.analyze(study(tweak=first_panel))["label_row"] == 7


def test_incomplete_for_missing_failed_skipped_cells_and_caps() -> None:
    def missing(s: dict[str, Any]) -> None:
        del s["replicates"][1]["cells"]["r1/MAF/AB"]
    out = analysis.analyze(study(tweak=missing))
    assert out["label_row"] == 2 and out["label"] == "INCOMPLETE" and any("r1/MAF/AB: no record" in x for x in out["incomplete"])
    assert out["classes"]["M-append-frozen"]["AB"]["class"] == "NO CLASS (INCOMPLETE)" and out["classes"]["M-append-frozen"]["BA"]["class"] != "NO CLASS (INCOMPLETE)"  # no class for a mechanism with a missing cell
    assert out["annotations"] == {}
    def failed(s: dict[str, Any]) -> None:
        cell(s, 0, "ST1", "AB")["status"] = "failed"
        cell(s, 0, "MAF", "AB")["status"] = "skipped_dependency"
    out = analysis.analyze(study(tweak=failed))
    assert out["label"] == "INCOMPLETE" and any("failed" in x for x in out["incomplete"]) and any("skipped_dependency" in x for x in out["incomplete"])
    capped = analysis.analyze(study(tweak=lambda s: s["incomplete"].append("a cap stopped the train stage")))
    assert capped["label"] == "INCOMPLETE" and capped["label_row"] == 2
    assert analysis.analyze({**study(), "replicates": []})["label"] == "INCOMPLETE"


def test_row_1_engineering_failure_outranks_everything() -> None:
    for g in ("G1", "G4", "G5", "G6", "G7", "G8", "G9"):
        out = analysis.analyze(study(tweak=lambda s, g=g: s["gates"][g].update(ok=False, problems=["x"])))
        assert out["label_row"] == 1 and out["label"] == "ENGINEERING-FAILURE", g
    g2 = analysis.analyze(study(tweak=lambda s: s["gates"].update({"G2": {"ok": False}})))
    assert g2["label_row"] == 1 and any("gate G2 failed" in x for x in g2["engineering"])  # a failed G2 (scored differently twice) is an engineering defect
    assert analysis.analyze(study(tweak=lambda s: s["gates"].update({"G3": {"ok": False}})))["label_row"] == 7  # G3 stops before the freeze: not read here
    ens = analysis.analyze(study(tweak=lambda s: s["replicates"][0]["ensemble"].update(oracle={"A": 0.8, "B": 0.9})))
    assert ens["label_row"] == 1 and any("ensemble" in x for x in ens["engineering"])
    both = analysis.analyze(study(tweak=lambda s: (s["gates"]["G4"].update(ok=False), s["incomplete"].append("x"))))
    assert both["label_row"] == 1  # 1 before 2


def test_row_3_stops_before_the_freeze() -> None:
    for stop in ("TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED", "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"):
        out = analysis.analyze(study(tweak=lambda s, stop=stop: s["prefreeze"].update(stop=stop)))
        assert out["label_row"] == 3 and out["label"] == stop


def test_nothing_printed_by_construction_satisfies_a_row() -> None:
    def tweak(s: dict[str, Any]) -> None:  # the assembled composites and the oracle-route general quality are perfect, everything else is poor
        for o in core.ORDERS:
            set_panels(s, None, "MAF", o, 0.1, 0.1)
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] not in (6, 7, 8) and set(out["by_construction"].values()) == {"BY CONSTRUCTION"}
    assert "M-i-separate" not in out["classes"] and "L-sep" not in out["classes"]  # no class for what is assembled


def test_class_function_directly_over_the_table_order() -> None:
    ok = C.Verdict(True)
    base = C.CellEval(ok, ok, ok, False, False)
    assert C.mechanism_class("M-append-frozen", [base, base]).name == "ACQUIRES-AND-RETAINS"
    assert C.mechanism_class("M-ii", [base, C.CellEval(ok, ok, ok, False, False, rejected=True)]).name == "INTERMEDIATE"
    assert C.mechanism_class("M-ii", [base, C.CellEval(ok, ok, ok, False, False, below_floor=True)]).name == "RETENTION BY INERTIA"
    assert C.mechanism_class("M-append-frozen", [base, C.CellEval(ok, ok, ok, False, False, below_floor=True)]).name == "ACQUIRES-AND-RETAINS"  # inertia is an M-ii class only
    assert C.mechanism_class("M-append-frozen", [base, C.CellEval(ok, ok, ok, False, False, recompute_ne=True)]).name == "NOT_EVALUATED"
    assert C.mechanism_class("M-append-frozen", [base, C.CellEval(C.Verdict(False, ("acquisition below 0.50",)), ok, ok, False, False)]).name == "NOT_EVALUATED"  # row 1 before everything
    assert C.mechanism_class("M-append-frozen", [C.CellEval(ok, C.Verdict(False), ok, True, False)] * 2).name == "NO-NEW-CAPABILITY"
    assert C.mechanism_class("M-append-frozen", [C.CellEval(ok, C.Verdict(True), C.Verdict(False), False, True)] * 2).name == "FORGETS"
    both_zones = C.CellEval(ok, C.Verdict(False), C.Verdict(False), True, True)
    assert C.mechanism_class("M-append-frozen", [both_zones] * 2).name == "NO-NEW-CAPABILITY"  # row 2 before row 3
    assert C.mechanism_class("M-append-frozen", []).name == "NOT_EVALUATED"


def test_gate_functions_hand_cases() -> None:
    lex = C.Lexical(0.9, 0.2, 0.3, 0.1)
    assert C.acq1(0.9, lex).ok is True and C.acq1(0.49, lex).ok is False and C.acq1(None, lex).ok is None
    assert C.acq1(0.9, C.Lexical(0.9, 0.7, 0.3, 0.1)).reasons == ("lexical margin below 0.30",)  # 0.9 - 0.7 < 0.30
    assert C.acq1(0.9, C.Lexical(0.9, 0.2, 0.3, 0.26)).reasons == ("marker-only above 0.25",)
    assert C.acq1(0.9, C.Lexical(0.9, 0.6, 0.3, 0.1)).ok is True  # margin exactly 0.30 passes
    assert C.acq1(0.9, C.Lexical(0.9, None, 0.3, 0.1)).ok is None
    assert C.acq2(0.6, 0.8, lex).ok is False and C.acq2(0.65, 0.8, lex).ok is True and C.acq2(0.6, None, lex).ok is None  # 0.80 x the single-teacher student's G
    assert C.ret(0.77, 0.8, 0.9, 0.9).ok is True and C.ret(0.769, 0.8, 0.9, 0.9).ok is False and C.ret(0.8, 0.8, 0.809, 0.9).ok is False and C.ret(0.8, 0.8, 0.81, 0.9).ok is True
    assert C.negative_acquisition(0.249) is True and C.negative_acquisition(0.25) is False and C.negative_acquisition(None) is None
    assert C.negative_retention(0.69, 1.0) is True and C.negative_retention(0.70, 1.0) is False
    assert C.gen_gate(0.02) is True and C.gen_gate(0.0201) is False and C.gen_gate(None) is None and C.gen_gate(float("nan")) is None
    assert C.within(0.77, 0.8) is True and C.within(0.769, 0.8) is False and C.within(None, 0.8) is None
    assert C.training_cost([15.0], [10.0])["word"] == "TRAINING COST COMPARABLE" and C.training_cost([15.1], [10.0])["word"] == "TRAINING COST HIGHER"
    assert C.value_rows(10.0, 100.0, 8192)["word"] == "FEWER VALUE ROWS ACTIVE" and "key products per read 8192" in C.value_rows(11.0, 100.0, 8192)["line"]
    assert C.stored_size_line(134_515_008, 8192, [73_944_309, 74_669_178], 0.9, None, 576).count("0.938") == 1


def test_annotation_rules() -> None:
    def tweak(s: dict[str, Any]) -> None:
        for o in core.ORDERS:
            for r in range(2):  # M-seq loses less than L-seq by 0.10 or more in every replicate of both orders
                set_panels(s, r, "MSEQ", o, *((0.7, 0.78) if o == "AB" else (0.78, 0.7)))
        for r in range(2):
            s["replicates"][r]["retrieval"]["A"]["R-icl"]["mean"] = 0.79  # within 0.03 of M-append-frozen's 0.78-0.8
            s["replicates"][r]["retrieval"]["B"]["R-icl"]["mean"] = 0.79
    a = analysis.analyze(study(tweak=tweak))["annotations"]
    assert a["TASK-CODED SPARSE RETENTION"] is True and a["RETRIEVAL SUFFICES"] is True
    above = analysis.analyze(study(tweak=lambda s: set_panels(s, None, "MJOINT", "-", 0.95, 0.95)))["annotations"]
    assert above["BELOW JOINT BOUND"] is True  # M-append-frozen's G (0.85) is below 0.90 x the joint's G (1.0625)
    assert analysis.analyze(study())["annotations"]["BELOW JOINT BOUND"] is False and analysis.analyze(study())["annotations"]["BELOW ADAPTER JOINT"] is False
    adapter = analysis.analyze(study(tweak=lambda s: set_panels(s, None, "LJOINT", "-", 0.95, 0.95)))["annotations"]
    assert adapter["BELOW ADAPTER JOINT"] is True  # the memory-form joint student is below 0.90 x the adapter-form one
    em = analysis.analyze(study(tweak=lambda s: [cell(s, 0, "MAF", o)["scores"][f"r0/MAF/{o}"]["panels"]["E_A"].update(exact_rate=0.0) for o in core.ORDERS]))["annotations"]
    assert em["EXACT-MATCH WEAK"] is True  # gap closed on exact-match rate 0 < 0.10
    noroute = analysis.analyze(study(tweak=lambda s: s["replicates"][0]["routers"]["AB"]["accuracy"].update(general=0.98)))["annotations"]
    assert noroute["ROUTER (keyword-level) QUALIFIED"] is False  # accuracy below 0.99 on general prefixes
    nolearned = analysis.analyze(study(tweak=lambda s: cell(s, 0, "MAF", "AB")["scores"]["r0/MAF/AB"]["learned_route"].update(E_B=panel(0.1))))["annotations"]
    assert nolearned["ROUTER (keyword-level) QUALIFIED"] is False  # M-append-frozen fails ACQ2 under the learned route


def test_synthetic_records_cover_the_registry() -> None:
    s = study(4)
    assert sum(len(r["cells"]) for r in s["replicates"]) == 72 and len(study(3)["replicates"]) == 3
    assert analysis.analyze(s)["label_row"] == 7


# --- the recomputation rule (section 13.3) ------------------------------------------------------------------------------------------------------------
def cells_of(s: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {lab: rec for rep in s["replicates"] for lab, rec in rep["cells"].items()}


def test_bit_identical_recomputation_changes_nothing() -> None:
    s = study()
    out = analysis.analyze_with_recomputation(s, copy.deepcopy(cells_of(s)), recompute.FROZEN)
    assert out["label_row"] == 7 and out["recomputation"]["state"] == "complete" and out["recomputation"]["not_evaluated_cells"] == [] and out["recomputation"]["differences"] == []


def test_own_code_tolerance_and_frozen_code_exactness() -> None:
    s = study()
    rec = copy.deepcopy(cells_of(s))
    rec["r0/MAF/AB"]["scores"]["r0/MAF/AB"]["panels"]["E_A"]["items"][0] += 5e-7
    own = analysis.analyze_with_recomputation(s, rec, recompute.OWN)
    assert own["label_row"] == 7 and own["recomputation"]["differences"] == [] and own["recomputation"]["not_evaluated_cells"] == []  # within 1e-6 under the auditor's own code
    frozen = analysis.analyze_with_recomputation(s, rec, recompute.FROZEN)
    assert frozen["recomputation"]["not_evaluated_cells"] == ["r0/MAF/AB"] and len(frozen["recomputation"]["differences"]) == 1  # bit-identical is required for the frozen code
    assert classes_of(frozen, "M-append-frozen")[0] == "NOT_EVALUATED" and any("recomputation difference" in r for r in frozen["classes"]["M-append-frozen"]["AB"]["reasons"])
    assert frozen["label_row"] == 11  # no gate, class, annotation or label differs between the registered and the recomputed scores: the cell is NOT_EVALUATED and the label follows from the classes
    rec2 = copy.deepcopy(cells_of(s))
    rec2["r0/MAF/AB"]["scores"]["r0/MAF/AB"]["panels"]["E_A"]["items"][0] += 2e-6
    assert analysis.analyze_with_recomputation(s, rec2, recompute.OWN)["recomputation"]["not_evaluated_cells"] == ["r0/MAF/AB"]


def test_a_greedy_sequence_difference_is_a_difference_under_both_cases() -> None:
    s = study()
    rec = copy.deepcopy(cells_of(s))
    rec["r1/ST1/BA"]["scores"]["r1/ST1/BA"]["panels"]["E_B"]["sequences"][0] = [9, 9]
    for mode in (recompute.FROZEN, recompute.OWN):
        r = recompute.compare_cells(cells_of(s), rec, mode)
        assert r.complete and r.not_evaluated_cells == ["r1/ST1/BA"] and "sequences" in r.differences[0].path


def test_a_difference_that_changes_a_class_or_label_is_an_engineering_failure() -> None:
    s = study()
    rec = copy.deepcopy(cells_of(s))
    for r in range(2):
        for o in core.ORDERS:
            c = rec[f"r{r}/MAF/{o}"]["scores"][f"r{r}/MAF/{o}"]
            first, second = ("E_A", "E_B") if o == "AB" else ("E_B", "E_A")
            c["panels"][second]["mean"] = 0.1  # the recomputed second capability collapses: the class and the label would change
    out = analysis.analyze_with_recomputation(s, rec, recompute.FROZEN)
    assert out["label_row"] == 1 and out["label"] == "ENGINEERING-FAILURE" and out["recomputation"]["engineering_failure"] is True and out["recomputation"]["changes"]
    changes = recompute.outcome_changes(analysis.analyze(s), analysis.analyze(study(tweak=lambda t: [set_panels(t, None, "MAF", "AB", 0.8, 0.1)])))
    assert any(x.startswith("classes") for x in changes) and any(x.startswith("label") for x in changes)


def test_incomplete_recomputation_and_memory_limits() -> None:
    s = study()
    missing = copy.deepcopy(cells_of(s))
    del missing["r0/LJOINT/-"]
    out = analysis.analyze_with_recomputation(s, missing, recompute.FROZEN)
    assert out["label"] == "INCOMPLETE" and out["recomputation"]["state"] == "incomplete" and out["recomputation"]["incomplete"] is True
    assert all(c["class"] == "NO CLASS (INCOMPLETE)" for by in out["classes"].values() for c in by.values())  # no class is printed
    mem = analysis.analyze_with_recomputation(s, copy.deepcopy(cells_of(s)), recompute.FROZEN, memory_exceeded=True)
    assert mem["label"] == "INCOMPLETE" and mem["recomputation"]["state"] == "memory" and mem["annotations"] == {}
    none = analysis.analyze_with_recomputation(s, None, recompute.FROZEN)  # no result is reported before the recomputation completes
    assert none["label"] == "INCOMPLETE" and none["recomputation"]["state"] == "not_run"
    with pytest.raises(ValueError):
        recompute.compare_cells({}, {}, "other")


def test_recomputed_value_is_the_one_reported_for_a_difference_beyond_tolerance() -> None:
    s = study()
    rec = copy.deepcopy(cells_of(s))
    rec["r0/ETABLE/A"]["scores"]["r0/ETABLE/A"]["panels"]["E_A"]["mean"] = 0.779  # does not change any gate, class, annotation or label
    res = recompute.compare_cells(cells_of(s), rec, recompute.FROZEN)
    reported = recompute.reported_cells(cells_of(s), rec, res)
    assert reported["r0/ETABLE/A"]["scores"]["r0/ETABLE/A"]["panels"]["E_A"]["mean"] == 0.779 and reported["r0/ETABLE/A"]["recomputed_replaced"] is True
    assert reported["r0/MAF/AB"] == cells_of(s)["r0/MAF/AB"]
    out = analysis.analyze_with_recomputation(s, rec, recompute.FROZEN)
    assert out["recomputation"]["not_evaluated_cells"] == ["r0/ETABLE/A"] and out["label_row"] == 7
