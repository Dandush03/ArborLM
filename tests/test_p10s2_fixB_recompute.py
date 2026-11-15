# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: the recomputation compares EVERY recomputed quantity (cell scores, Stage 0 and teacher scores, retrieval, assembled arms, routers, the ensemble) and every gate and control
verdict including GEN and CONTROL-FAILED; a difference within tolerance never changes a verdict by itself; verdicts are compared as verdicts (audit B M9, audit C M3, the lead's ruling of 2026-11-15).
Synthetic records of the whole registry from the classes tests; every number is constructed. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import cell, study  # noqa: E402

from studies.p10s2 import analysis, recompute  # noqa: E402


def twin(s: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(s)


def test_a_bit_identical_study_has_no_difference_in_any_section() -> None:
    s = study()
    res = recompute.compare_study(s, twin(s), recompute.FROZEN)
    assert res.complete and res.differences == [] and res.study_level == [] and res.not_evaluated_cells == []
    out = recompute.outcome_under_recomputation(s, twin(s), recompute.FROZEN)
    assert out["label_row"] == 7 and out["recomputation"]["state"] == "complete" and out["recomputation"]["differences"] == []


@pytest.mark.parametrize(
    "section, tweak",
    [
        ("baseline", lambda r: r["baseline"]["student"]["E_A"]["panel"].update(mean=0.1 + 1e-9)),
        ("baseline", lambda r: r["baseline"]["teacher"]["E_B"].update(mean=0.8999)),
        ("r0/retrieval", lambda r: r["replicates"][0]["retrieval"]["A"]["R-nn"].update(mean=0.31)),
        ("r1/assembled", lambda r: r["replicates"][1]["assembled"]["L-sep"]["E_A"].update(mean=0.79)),
        ("r0/routers", lambda r: r["replicates"][0]["routers"]["AB"]["accuracy"].update(A=0.98)),
        ("r1/ensemble", lambda r: r["replicates"][1]["ensemble"]["oracle"].update(A=0.9001)),
    ],
)
def test_every_recomputed_quantity_is_compared_and_listed(section: str, tweak: Any) -> None:
    s = study()
    rec = twin(s)
    tweak(rec)
    res = recompute.compare_study(s, rec, recompute.FROZEN)
    assert res.complete and section in res.study_level and any(d.cell == section for d in res.differences)  # a difference in a Stage 0, teacher, retrieval, assembled, router or ensemble value is listed
    assert res.not_evaluated_cells == []  # these are not cells: they are reported as study-level differences
    own = recompute.compare_study(s, rec, recompute.OWN)  # under the auditor's own code the tolerance is 1e-6 per item score
    assert (section in own.study_level) == (abs(next(d for d in res.differences if d.cell == section).registered - next(d for d in res.differences if d.cell == section).recomputed) > 1e-6)


def test_a_difference_within_tolerance_is_not_a_difference_and_changes_no_verdict() -> None:
    s = study()
    rec = twin(s)
    rec["baseline"]["teacher"]["E_A"]["mean"] += 5e-7
    rec["replicates"][0]["retrieval"]["B"]["R-icl"]["mean"] += 5e-7
    res = recompute.compare_study(s, rec, recompute.OWN)
    assert res.differences == [] and res.study_level == []
    out = recompute.outcome_under_recomputation(s, rec, recompute.OWN)
    assert out["label_row"] == 7 and out["recomputation"]["differences"] == []
    # verdicts are compared as verdicts: numbers never enter the comparison
    a, b = analysis.analyze(s), analysis.analyze(rec)
    va, vb = analysis.verdicts_of_outcome(a), analysis.verdicts_of_outcome(b)
    assert analysis.verdict_changes(va, vb) == [] and not any(isinstance(v, float) for v in va.values())  # a verdict map holds booleans, None and words: no number


def test_a_changed_baseline_changes_the_gap_and_a_verdict_is_an_engineering_failure() -> None:
    s = study()
    rec = twin(s)
    rec["baseline"]["teacher"]["E_A"]["mean"] = 0.2  # the teacher's own score falls: every gap's denominator changes and an undefined gap makes cells NOT_EVALUATED
    res = recompute.compare_study(s, rec, recompute.FROZEN)
    assert "baseline" in res.study_level
    out = recompute.outcome_under_recomputation(s, rec, recompute.FROZEN)
    assert out["label"] == "ENGINEERING-FAILURE" and out["recomputation"]["engineering_failure"] is True and any("baseline" in d["cell"] for d in out["recomputation"]["differences"])
    # the recomputed study is analyzed with ITS OWN baseline (it does not reuse the registered one)
    assert analysis.verdict_changes(analysis.verdicts(s), analysis.verdicts({**s, "baseline": rec["baseline"]}))


def test_a_flipped_gen_verdict_is_an_engineering_failure_even_when_the_class_would_not_show_it() -> None:
    s = study()
    rec = twin(s)
    c = cell(rec, 1, "MAF", "BA")
    c["scores"][c["label"]]["gen"]["loss_increase"] = 0.5  # the GEN gate (a loss increase of at most 0.02) fails in the recomputed study only
    out = recompute.outcome_under_recomputation(s, rec, recompute.FROZEN)
    assert out["label"] == "ENGINEERING-FAILURE" and out["recomputation"]["changes"]
    assert any("gen" in x for x in out["recomputation"]["changes"])  # the GEN verdict is among the changed verdicts


def test_a_flipped_control_failed_verdict_is_an_engineering_failure() -> None:
    s = study()
    rec = twin(s)
    cell(rec, 1, "MAF", "BA")["scores"]["r1/MAF/BA"]["ablations"]["E_A"]["code_perm"]["mean"] = 0.7  # a permutation control scores like the arm: CONTROL-FAILED in the recomputed study only
    out = recompute.outcome_under_recomputation(s, rec, recompute.FROZEN)
    assert out["label"] == "ENGINEERING-FAILURE" and any("control_failed" in x for x in out["recomputation"]["changes"])


def test_a_cell_difference_beyond_tolerance_without_a_verdict_change_is_not_evaluated_and_reported_recomputed() -> None:
    s = study()
    rec = twin(s)
    rec["replicates"][0]["cells"]["r0/ETABLE/A"]["scores"]["r0/ETABLE/A"]["panels"]["E_A"]["mean"] = 0.779
    out = recompute.outcome_under_recomputation(s, rec, recompute.FROZEN)
    assert out["recomputation"]["not_evaluated_cells"] == ["r0/ETABLE/A"] and out["label_row"] == 7
    reported = recompute.reported_study(s, rec, recompute.compare_study(s, rec, recompute.FROZEN))
    assert reported["replicates"][0]["cells"]["r0/ETABLE/A"]["scores"]["r0/ETABLE/A"]["panels"]["E_A"]["mean"] == 0.779 and reported["replicates"][0]["cells"]["r0/ETABLE/A"]["recomputed_replaced"] is True
    # a study-level difference that changes no verdict: the recomputed value is the one reported
    rec2 = twin(s)
    rec2["replicates"][0]["retrieval"]["A"]["R-nn"]["mean"] = 0.31
    res2 = recompute.compare_study(s, rec2, recompute.FROZEN)
    assert recompute.reported_study(s, rec2, res2)["replicates"][0]["retrieval"]["A"]["R-nn"]["mean"] == 0.31


def test_a_missing_recomputed_section_makes_the_recomputation_incomplete_and_no_class_is_printed() -> None:
    s = study()
    for drop in (lambda r: r["replicates"][0].pop("routers"), lambda r: r["replicates"][1].pop("assembled"), lambda r: r.update(baseline={}), lambda r: r["replicates"][0]["cells"].pop("r0/LJOINT/-")):
        rec = twin(s)
        drop(rec)
        out = recompute.outcome_under_recomputation(s, rec, recompute.FROZEN)
        assert out["label"] == "INCOMPLETE" and out["recomputation"]["state"] == "incomplete"
        assert all(c["class"] == "NO CLASS (INCOMPLETE)" for by in out["classes"].values() for c in by.values())
    none = recompute.outcome_under_recomputation(s, None, recompute.FROZEN)
    assert none["label"] == "INCOMPLETE" and none["recomputation"]["state"] == "not_run"
    mem = recompute.outcome_under_recomputation(s, twin(s), recompute.FROZEN, memory_exceeded=True)
    assert mem["label"] == "INCOMPLETE" and mem["recomputation"]["state"] == "memory" and mem["annotations"] == {}


def test_greedy_sequences_must_be_identical_in_every_section_under_both_cases() -> None:
    s = study()
    rec = twin(s)
    rec["replicates"][0]["assembled"]["M-i-separate"]["E_A"]["sequences"][0] = [9, 9]
    for mode in (recompute.FROZEN, recompute.OWN):
        res = recompute.compare_study(s, rec, mode)
        assert "r0/assembled" in res.study_level and "sequences" in next(d.path for d in res.differences if d.cell == "r0/assembled")
