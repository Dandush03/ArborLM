# ruff: noqa: E501
"""P10S2 fix lane C, the science rules (audit C-M1, C-M2, C-M4, readings 4 and 5, C-m1 to C-m3, C-m8, the verdict function). Synthetic records of the whole registry; the numbers are constructed to
exercise the rules, they are not results. Test seeds 229001-229999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import cell, cells_of, panel, rec_outcome, set_panels, study  # noqa: E402

from studies.p10s2 import analysis, core, recompute, report  # noqa: E402
from studies.p10s2 import classes as C  # noqa: E402


def snap(s: dict[str, Any], r: int, group: str, variant: str) -> dict[str, Any]:
    c = cell(s, r, group, variant)
    out: dict[str, Any] = c["scores"][c["label"]]
    return out


def positive(out: dict[str, Any]) -> bool:
    return out["label_row"] in (6, 7, 8)


# --- C-M1: a missing control record is NOT_EVALUATED, never "not applicable" ----------------------------------------------------------------------------
def test_the_audits_case_e5_ablations_deleted_gives_no_positive_label() -> None:
    def tweak(s: dict[str, Any]) -> None:
        del snap(s, 0, "ST1", "AB")["ablations"]  # r0/ST1/AB: no ablation section at all
        del snap(s, 1, "MAF", "BA")["ablations"]["E_A"]  # E_A of r1/MAF/BA: the panel of the second capability
    out = analysis.analyze(study(tweak=tweak))
    assert not positive(out) and out["label_row"] == 12
    assert out["classes"]["M-append-frozen"]["AB"]["class"] == "NOT_EVALUATED" and out["classes"]["M-append-frozen"]["BA"]["class"] == "NOT_EVALUATED"
    assert any("control record missing" in r for r in out["classes"]["M-append-frozen"]["AB"]["reasons"])
    assert any("NOT_EVALUATED (control record missing)" in x for x in out["control_not_evaluated"]) and out["control_failed"] == []


@pytest.mark.parametrize("kind", ["unablated", "value_perm", "code_perm", "marker_only"])
def test_every_missing_control_entry_blocks_acq_and_the_control_verdict(kind: str) -> None:
    def tweak(s: dict[str, Any]) -> None:
        del snap(s, 0, "ST1", "AB")["ablations"]["E_A"][kind]
    out = analysis.analyze(study(tweak=tweak))
    assert not positive(out)
    assert out["classes"]["M-append-frozen"]["AB"]["class"] == "NOT_EVALUATED"
    if kind in ("value_perm", "code_perm"):
        assert any(c["cell"] == "r0/ST1/AB" and c["kind"] == kind and c["failed"] is None for c in out["controls"])


def test_a_missing_control_of_a_cell_that_enters_no_class_blocks_a_positive_label_too() -> None:
    def tweak(s: dict[str, Any]) -> None:  # MA-gold and M-joint enter only CONTROL-FAILED
        del snap(s, 0, "MJOINT", "-")["ablations"]
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] == 12 and out["control_not_evaluated"] and any("r0/MJOINT/-" in x for x in out["not_evaluated_reasons"])
    def tweak2(s: dict[str, Any]) -> None:
        del snap(s, 1, "MAGOLD", "B")["ablations"]["E_B"]["code_perm"]
    assert analysis.analyze(study(tweak=tweak2))["label_row"] == 12


def test_a_failed_control_still_gives_row_5_and_a_missing_one_never_hides_it() -> None:
    def tweak(s: dict[str, Any]) -> None:
        snap(s, 1, "MAF", "BA")["ablations"]["E_A"]["code_perm"] = panel(0.7)
        del snap(s, 0, "MJOINT", "-")["ablations"]
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] == 5 and out["control_failed"] and out["control_not_evaluated"]


def test_only_the_lora_path_skips_the_permutation_controls() -> None:
    s = study()
    assert all("ablations" not in snap(s, 0, g, o) for g, o in (("LORA1", "AB"), ("LSEQ", "AB")))  # an adapter has no rows or codes to permute
    out = analysis.analyze(s)
    assert out["classes"]["L-seq"]["AB"]["class"] == "FORGETS" and out["label_row"] == 7
    assert not any(c["cell"].split("/")[1] in ("LORA1", "LSEQ", "LJOINT", "ETABLE") for c in out["controls"])
    assert {c["cell"].split("/")[1] for c in out["controls"]} == {"ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD"}
    assert C.acq1(0.9, None, lexical_applies=False).ok is True and C.acq1(0.9, None).ok is None and C.acq2(0.9, 0.9, None).reasons[0] == "control record missing"


def test_a_partial_ablation_record_does_not_crash_and_is_not_evaluated() -> None:  # C-m3 (the audit's E6)
    def tweak(s: dict[str, Any]) -> None:
        del snap(s, 0, "MSEQ", "AB")["ablations"]["E_B"]["marker_only"]  # the second panel of order AB: read by ACQ2 of M-seq
        snap(s, 1, "MAF", "AB")["ablations"]["E_B"]["value_perm"] = {"items": [0.1]}  # no mean
        snap(s, 1, "MII", "AB")["ablations"] = {"E_A": "garbage"}
    out = analysis.analyze(study(tweak=tweak))
    assert not positive(out) and out["label_row"] in (11, 12) and out["classes"]["M-seq"]["AB"]["class"] == "NOT_EVALUATED"


# --- C-M2: every gate G1 and G4-G9 present and passed ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("missing", ["G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9"])
def test_a_missing_gate_is_never_passed(missing: str) -> None:
    out = analysis.analyze(study(tweak=lambda s: s["gates"].pop(missing)))
    assert not positive(out) and out["label_row"] == 2 and out["label"] == "INCOMPLETE" and any(f"gate {missing} has no record" in x for x in out["incomplete"])
    assert out["gate_verdicts"][missing] is None


def test_an_empty_or_absent_gates_record_is_never_passed() -> None:  # the audit's E1 and E2
    for tweak in (lambda s: s.update(gates={}), lambda s: s.pop("gates")):
        out = analysis.analyze(study(tweak=tweak))
        assert out["label_row"] == 2 and any("gates record is missing" in x for x in out["incomplete"])


def test_a_gate_that_is_present_but_not_a_boolean_true_failed() -> None:
    for bad in ({"ok": "yes"}, {"ok": 1}, {}, {"problems": []}):
        out = analysis.analyze(study(tweak=lambda s, bad=bad: s["gates"].update(G6=bad)))
        assert out["label_row"] == 1 and out["gate_verdicts"]["G6"] is False


def test_a_failed_g2_is_an_engineering_failure_and_g3_is_not_read() -> None:
    out = analysis.analyze(study(tweak=lambda s: s["gates"].update(G2={"ok": False, "scored_identically_twice": False})))
    assert out["label_row"] == 1 and out["label"] == "ENGINEERING-FAILURE" and out["gate_verdicts"]["G2"] is False
    assert analysis.analyze(study(tweak=lambda s: s["gates"].update(G2={"ok": True}, G3={"ok": False})))["label_row"] == 7


# --- C-M4: an undefined gap is never hidden by another failed clause --------------------------------------------------------------------------------
def test_an_undefined_single_teacher_gap_is_not_hidden_by_a_failed_clause() -> None:
    v = C.acq2(0.4, None, C.Lexical(0.9, 0.2, 0.3, 0.1))  # below 0.50 AND the single-teacher gap undefined
    assert v.ok is None and v.reasons[0] == "undefined gap" and "acquisition below 0.50" in v.reasons
    v = C.acq2(0.9, 0.9, C.Lexical(0.9, 0.8, 0.3, None))  # marker-only gap undefined while the margin fails
    assert v.ok is None and "lexical margin below 0.30" in v.reasons
    assert C.acq1(0.4, C.Lexical(0.9, 0.2, 0.3, float("nan"))).ok is None
    assert C.acq2(0.4, 0.9, C.Lexical(0.9, 0.2, 0.3, 0.1)).ok is False  # a defined failure stays a failure


def test_the_mseq_forgets_case_of_the_audit_is_not_evaluated() -> None:
    def tweak(s: dict[str, Any]) -> None:  # M-seq forgets, and the second-capability gap of its lexical subsample is undefined
        for r in range(2):
            set_panels(s, r, "MSEQ", "AB", 0.15, 0.78)
            snap(s, r, "MSEQ", "AB")["ablations"]["E_B"]["marker_only"] = panel("nan")
    out = analysis.analyze(study(tweak=tweak))
    assert out["classes"]["M-seq"]["AB"]["class"] == "NOT_EVALUATED"  # not FORGETS
    assert out["classes"]["M-seq"]["BA"]["class"] == "FORGETS"


# --- reading 4 and C-m1/C-m2: missing or non-finite GEN and ensemble ----------------------------------------------------------------------------------
@pytest.mark.parametrize("value", [None, "nan", "inf", "-inf"])
def test_a_missing_or_non_finite_gen_value_is_not_evaluated_not_row_6(value: Any) -> None:
    def tweak(s: dict[str, Any]) -> None:
        g = snap(s, 1, "MAF", "BA")["gen"]
        g.pop("loss_increase_first_marker") if value is None else g.update(loss_increase_first_marker=value)
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] == 12 and out["gen"]["status"]["M-append-frozen"]["BA"] == "not_evaluated" and not positive(out)
    assert any("GEN value is missing or not finite" in x for x in out["not_evaluated_reasons"])
    assert out["gen_table"][0]["gen_gate"] is True and any(r["gen_gate"] is None for r in out["gen_table"])


def test_a_missing_gen_record_is_not_evaluated_and_a_measured_failure_still_wins() -> None:
    out = analysis.analyze(study(tweak=lambda s: snap(s, 0, "ST1", "AB").pop("gen")))
    assert out["label_row"] == 12
    def both(s: dict[str, Any]) -> None:
        snap(s, 0, "ST1", "AB").pop("gen")
        snap(s, 1, "MAF", "AB")["gen"]["loss_increase"] = 0.5
    assert analysis.analyze(study(tweak=both))["label_row"] == 6  # a measured failure anywhere is row 6; the missing value does not hide it


def test_m_ii_with_a_missing_gen_value_is_row_8_and_the_report_says_not_evaluated() -> None:
    out = analysis.analyze(study(tweak=lambda s: snap(s, 0, "MII", "AB")["gen"].pop("loss_increase_first_marker")))
    assert out["label_row"] == 8 and out["gen"]["status"]["M-ii"]["AB"] == "not_evaluated" and out["gen"]["M-ii alone fails GEN"] is False
    assert "M-ii's GEN is NOT_EVALUATED" in report.render_report(out) and "measured failure" in report.render_report(out)


def test_m_ii_alone_failing_gen_gives_row_8_and_the_report_says_so() -> None:
    out = analysis.analyze(study(tweak=lambda s: snap(s, 0, "MII", "AB")["gen"].update(loss_increase_first_marker=0.3)))
    assert out["label_row"] == 8 and out["gen"]["M-ii alone fails GEN"] is True
    assert "M-ii alone fails GEN while M-append-frozen holds it: row 8 applies" in report.render_report(out)
    assert "M-ii alone fails GEN" not in report.render_report(analysis.analyze(study()))


def test_the_threshold_must_hold_under_both_decisions() -> None:
    assert C.gen_gate(0.0, 0.021) is False and C.gen_gate(0.021, 0.0) is False and C.gen_gate(0.02, 0.02) is True and C.gen_gate(0.0, None) is None and C.gen_gate(float("nan"), 0.0) is None
    assert C.gen_gate(None, 0.5) is False and C.gen_gate() is None and C.gen_gate(0.02) is True
    out = analysis.analyze(study(tweak=lambda s: snap(s, 0, "MAF", "AB")["gen"].update(loss_increase=0.0, loss_increase_first_marker=0.0201)))
    assert out["label_row"] == 6  # registered decision silent, first-marker decision over the existing threshold: GEN fails


@pytest.mark.parametrize("mutation", ["missing", "none", "partial", "nan", "differs"])
def test_a_missing_or_unusable_ensemble_record_is_not_evaluated_not_skipped(mutation: str) -> None:  # C-m2 (the audit's E3)
    def tweak(s: dict[str, Any]) -> None:
        rep = s["replicates"][0]
        if mutation == "missing":
            del rep["ensemble"]
        elif mutation == "none":
            rep["ensemble"] = None
        elif mutation == "partial":
            rep["ensemble"] = {"oracle": {"A": 0.9, "B": 0.9}}
        elif mutation == "nan":
            rep["ensemble"]["teacher_own"] = {"A": "nan", "B": 0.9}
        else:
            rep["ensemble"]["oracle"] = {"A": 0.8, "B": 0.9}
    out = analysis.analyze(study(tweak=tweak))
    assert not positive(out)
    if mutation == "differs":
        assert out["label_row"] == 1 and out["ensemble_checks"]["r0"] is False
    else:
        assert out["label_row"] == 2 and out["ensemble_checks"]["r0"] is None and any("NOT_EVALUATED, not skipped" in x for x in out["incomplete"])
    assert out["ensemble_checks"]["r1"] is True


def test_analysis_never_crashes_on_a_partial_record() -> None:
    def tweak(s: dict[str, Any]) -> None:
        snap(s, 0, "MAF", "AB").pop("learned_route")
        snap(s, 1, "ST1", "AB").pop("panels")
        cell(s, 0, "MII", "AB")["extras"] = {}
        s["replicates"][1]["routers"] = {}
        s["replicates"][0]["retrieval"] = {}
        s["replicates"][1]["assembled"]["L-sep"] = {}
        snap(s, 0, "LSEQ", "AB")["combined"] = {"C1": {}}
    out = analysis.analyze(study(tweak=tweak))
    assert out["label_row"] in (2, 12) and not positive(out)


# --- reading 5: warning annotations print if they hold in any replicate or order, with the mean beside them -----------------------------------------
def test_warning_annotations_hold_if_they_hold_in_any_replicate_or_order() -> None:
    def tweak(s: dict[str, Any]) -> None:
        # replicate 1, order BA only: L-sep, R-gloss and R-icl reach M-append-frozen's level there, MA-gold equals ST1 in replicate 1 only, M-joint is far above M-append-frozen in one cell
        for r in (0, 1):
            s["replicates"][r]["assembled"]["L-sep"].update(E_A=panel(0.2), E_B=panel(0.2))
            for c in core.TASKS:
                for n in ("R-icl", "R-nn", "R-gloss"):
                    s["replicates"][r]["retrieval"][c][n]["mean"] = 0.2
            set_panels(s, r, "MAGOLD", "A", 0.2, 0.1)
            set_panels(s, r, "MAGOLD", "B", 0.1, 0.2)
        s["replicates"][1]["assembled"]["L-sep"].update(E_A=panel(0.79), E_B=panel(0.79))
        for c in core.TASKS:
            s["replicates"][1]["retrieval"][c]["R-icl"]["mean"] = 0.79
            s["replicates"][1]["retrieval"][c]["R-gloss"]["mean"] = 0.79
        set_panels(s, 1, "MAGOLD", "A", 0.8, 0.1)
        set_panels(s, 1, "MAGOLD", "B", 0.1, 0.8)
        set_panels(s, 0, "MJOINT", "-", 0.95, 0.95)
    out = analysis.analyze(study(tweak=tweak))
    a, d = out["annotations"], out["annotation_detail"]
    for name in ("NO ADVANTAGE OVER SEPARATE ADAPTERS", "RETRIEVAL SUFFICES", "LEXICON-EQUIVALENT", "TEACHER-EQUIVALENT-TO-GOLD", "BELOW JOINT BOUND"):
        assert a[name] is True, name  # holds in one replicate
        assert d[name]["rule"].startswith("any replicate") and d[name]["mean"] and any(v is not None for v in d[name]["mean"].values())
    assert d["RETRIEVAL SUFFICES"]["values"]["r1/AB"] is True and d["RETRIEVAL SUFFICES"]["values"]["r0/AB"] is False
    base = analysis.analyze(study(tweak=lambda s: [s["replicates"][r]["assembled"]["L-sep"].update(E_A=panel(0.2), E_B=panel(0.2)) for r in (0, 1)]))
    assert base["annotations"]["NO ADVANTAGE OVER SEPARATE ADAPTERS"] is False
    text = report.render_report(out)
    assert "NO ADVANTAGE OVER SEPARATE ADAPTERS: yes (rule: any replicate or order; means beside it: L-sep A 0.495" in text  # the mean over the two replicates is printed beside the warning
    assert "R-gloss A" in text and "MA-gold G A" in text


def test_exact_match_weak_keeps_its_floor_and_prints_not_evaluated_with_a_note() -> None:
    def tweak(s: dict[str, Any]) -> None:  # teacher exact rate 0.2 over Stage 0's 0.0: the 0.30 definedness floor of the exact-match gap is not met
        for c in ("E_A", "E_B"):
            s["baseline"]["teacher"][c]["exact_rate"] = 0.2
    out = analysis.analyze(study(tweak=tweak))
    assert out["annotations"]["EXACT-MATCH WEAK"] is None
    text = report.render_report(out)
    assert "EXACT-MATCH WEAK: NOT_EVALUATED" in text and "expected to print NOT_EVALUATED" in text
    one = analysis.analyze(study(tweak=lambda s: [cell(s, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["panels"][p].update(exact_rate=0.0) for p in ("E_A", "E_B")]))
    assert one["annotations"]["EXACT-MATCH WEAK"] is True  # weak in one replicate and order is enough (the study fixture has teacher 0.9, Stage 0 0.0)


def test_router_annotation_with_a_missing_accuracy_is_not_evaluated_not_a_miss() -> None:
    out = analysis.analyze(study(tweak=lambda s: s["replicates"][0]["routers"]["AB"]["accuracy"].pop("general")))
    assert out["annotations"]["ROUTER (keyword-level) QUALIFIED"] is None
    out = analysis.analyze(study(tweak=lambda s: s["replicates"][0]["routers"]["AB"].pop("accuracy")))
    assert out["annotations"]["ROUTER (keyword-level) QUALIFIED"] is None
    out = analysis.analyze(study(tweak=lambda s: s["replicates"][0]["routers"]["AB"]["accuracy"].update(general=0.98)))
    assert out["annotations"]["ROUTER (keyword-level) QUALIFIED"] is False


# --- the verdict function the recomputation compares -----------------------------------------------------------------------------------------------
def test_verdicts_are_a_pure_function_of_the_records() -> None:
    s = study()
    v1, v2 = analysis.verdicts(s), analysis.verdicts(copy.deepcopy(s))
    assert v1 == v2 and analysis.verdict_changes(v1, v2) == []
    assert v1["label_row"] == 7 and v1["control_failed"] is False and v1["class/M-append-frozen/AB"] == "ACQUIRES-AND-RETAINS" and v1["gate/G1"] is True
    assert v1["gen/r0/MAF/AB/registered"] is True and v1["gen/r0/MAF/AB/first_marker"] is True and v1["gen/r0/MAF/AB/both"] is True
    assert v1["control/r0/ST1/AB/E_A/value_perm"] is False and v1["annotation/RETRIEVAL SUFFICES"] is False and v1["composition/C1/M-append-frozen"] == "COMPOSES"
    assert v1["gen_status/M-ii/BA"] == "holds" and v1["ensemble/r0"] is True and v1["cell/M-append-frozen/AB/0/acq2"] is True
    assert not any(isinstance(x, float) for x in v1.values())  # no number is a verdict


def test_a_numeric_change_within_the_tolerance_changes_no_verdict_but_a_gen_flip_does() -> None:
    s = study()
    s2 = copy.deepcopy(s)
    snap(s2, 0, "MAF", "AB")["gen"]["loss_increase"] += 1e-9  # a number moved, no verdict
    snap(s2, 0, "MAF", "AB")["panels"]["E_A"]["mean"] += 1e-9
    assert analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts(s2)) == []
    s3 = copy.deepcopy(s)
    snap(s3, 0, "MAF", "AB")["gen"]["loss_increase_first_marker"] = 0.5  # the GEN gate of one snapshot flips under the first-marker decision
    ch = analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts(s3))
    assert "gen/r0/MAF/AB/first_marker" in ch and "gen/r0/MAF/AB/both" in ch and "label_row" in ch
    s4 = copy.deepcopy(s)
    snap(s4, 0, "MSEQ", "AB")["gen"]["loss_increase"] = 0.5  # the GEN gate of a cell that enters no class still differs as a verdict
    assert "gen/r0/MSEQ/AB/registered" in analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts(s4))
    s5 = copy.deepcopy(s)
    snap(s5, 1, "MJOINT", "-")["ablations"]["E_A"]["code_perm"] = panel(0.9)
    assert "control/r1/MJOINT/-/E_A/code_perm" in analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts(s5))


def test_a_recomputation_difference_within_tolerance_in_a_cost_input_is_not_an_engineering_failure() -> None:  # C-M3 (a), the analysis side
    s = study()
    rec = copy.deepcopy(cells_of(s))
    rec["r0/MAF/AB"]["scores"]["r0/MAF/AB@append"]["panels"]["E_A"]["mean"] += 4e-7  # feeds APPEND COST; own-code tolerance 1e-6
    rec["r0/MAF/AB"]["scores"]["r0/MAF/AB@append"]["panels"]["E_A"]["items"][0] += 4e-7
    out = rec_outcome(s, rec, recompute.OWN)
    assert out["label_row"] == 7 and out["engineering"] == [] and out["recomputation"]["differences"] == []


def test_a_recomputed_gen_flip_is_an_engineering_failure() -> None:  # C-M3 (b), the analysis side
    s = study()
    rec = copy.deepcopy(cells_of(s))
    rec["r0/MSEQ/AB"]["scores"]["r0/MSEQ/AB"]["gen"]["loss_increase"] = 0.5
    out = rec_outcome(s, rec, recompute.FROZEN)
    assert out["label_row"] == 1 and any("gen/r0/MSEQ/AB/registered" in x for x in out["recomputation"]["changes"])


def test_the_recomputed_study_uses_the_recomputed_baseline_and_parts() -> None:
    s = study()
    rec_cells = copy.deepcopy(cells_of(s))
    rs = copy.deepcopy(s)
    for p in ("E_A", "E_B"):
        rs["baseline"]["teacher"][p] = {"mean": 0.3, "subsample_mean": 0.3, "exact_rate": 0.9}  # every gap undefined in the recomputed baseline
    out = rec_outcome(s, rec_cells, recompute.FROZEN, recomputed_study=rs)
    assert out["label_row"] == 1 and out["recomputation"]["changes"]  # the verdicts differ: the recomputed Stage 0/teacher scores are used
    same = rec_outcome(s, copy.deepcopy(rec_cells), recompute.FROZEN, recomputed_study=copy.deepcopy(s))
    assert same["label_row"] == 7
    rs2 = copy.deepcopy(s)
    rs2["replicates"][0]["routers"]["AB"]["accuracy"]["general"] = 0.5
    ch = rec_outcome(s, copy.deepcopy(rec_cells), recompute.FROZEN, recomputed_study=rs2)
    assert ch["label_row"] == 1  # a recomputed router record changes ROUTER QUALIFIED


def test_gate_function_signatures_keep_their_old_behaviour_for_existing_callers() -> None:
    lex: Callable[..., Any] = C.Lexical
    assert C.acq1(0.9, lex(0.9, 0.2, 0.3, 0.1)).ok is True and C.gen_gate(0.02) is True and C.gen_gate(0.0201) is False
