# ruff: noqa: E501
"""P8 analysis (ADR-0015 revision 2): classification branches, undefined handling, incompleteness."""

import json
from fractions import Fraction
from pathlib import Path

import pytest
from p8_fake import Spec, make_cells

from arborlm import p7b_core as b_core
from arborlm import p8_analysis as an
from arborlm import p8_core as core
from arborlm.io import write_json

F = Fraction


def cond(
    m: object = F(1, 2),
    e: object = F(1, 2),
    rho: object = F(1, 2),
    pairs: int = 6,
    parents: int = 3,
) -> dict:
    return {
        "m_ratio": m,
        "e_ratio": e,
        "rho_adj": rho,
        "pairs_e_lower": pairs,
        "parents_e_below_one": parents,
    }


def four(**kw: object) -> list[dict]:
    return [cond(**kw) for _ in range(4)]  # type: ignore[arg-type]


# --- pure classification rules ---------------------------------------------------------------------
def test_each_class_branch() -> None:
    c = an.classify_case
    assert c(False, 1.0, four())[0] == an.QUALITY_FAILED
    assert c(False, 0.3, four())[0] == an.QUALITY_FAILED  # quality is checked first
    assert c(True, 0.49, four())[0] == an.COLLAPSED
    assert c(True, 1.0, four())[0] == an.POSITIVE
    assert c(True, 0.8, four())[0] == an.POSITIVE  # boundary: 0.80 is retained
    assert c(True, 0.7, four())[0] == an.REDUCED
    assert c(True, 0.5, four())[0] == an.REDUCED  # boundary: 0.50 is reduced, not collapsed
    assert c(True, 1.0, four(e=F(1)))[0] == an.CONC_ONLY
    assert c(True, 1.0, four(m=F(1), e=F(1)))[0] == an.NO_DIFF
    assert c(True, 1.0, four(m=F(9, 10), e=F(11, 10)))[0] == an.NO_DIFF  # band is inclusive
    assert c(True, 1.0, four(m=F(1), e=F(5, 4)))[0] == an.WORSE
    assert c(True, 1.0, four(m=F(5, 4), e=F(1)))[0] == an.WORSE  # M-ratio alone suffices
    assert c(True, 1.0, four(m=F(1), e=F(1, 2)))[0] == an.INTERMEDIATE


def test_loc_requires_every_clause() -> None:
    assert an.classify_case(True, 1.0, four(rho=F(81, 100)))[0] == an.CONC_ONLY
    assert an.classify_case(True, 1.0, four(rho=None))[0] == an.CONC_ONLY  # undefined fails
    assert an.classify_case(True, 1.0, four(pairs=4))[0] == an.CONC_ONLY
    assert an.classify_case(True, 1.0, four(parents=2))[0] == an.CONC_ONLY
    assert an.classify_case(True, 1.0, four(pairs=5))[0] == an.POSITIVE


def test_worse_must_be_the_same_ratio_everywhere() -> None:
    mixed = [
        cond(m=F(5, 4), e=F(1)),
        cond(m=F(1), e=F(5, 4)),
        cond(m=F(5, 4), e=F(1)),
        cond(m=F(1), e=F(5, 4)),
    ]
    assert an.classify_case(True, 1.0, mixed)[0] == an.INTERMEDIATE


def test_tie_rule_or_setting_disagreement_is_intermediate() -> None:
    conditions = four()
    conditions[3] = cond(m=F(95, 100), e=F(95, 100), rho=F(95, 100))
    assert an.classify_case(True, 1.0, conditions)[0] == an.INTERMEDIATE


def test_undefined_inputs_cannot_satisfy_a_class() -> None:
    assert an.classify_case(True, 1.0, four(m=None, e=None, rho=None))[0] == an.INTERMEDIATE
    assert (
        an.classify_case(True, 1.0, four(m=F(1), e=None))[0] == an.INTERMEDIATE
    )  # no NO DIFFERENCE
    assert (
        an.classify_case(True, None, four())[0] == an.INTERMEDIATE
    )  # u undefined: not positive/reduced


def test_quality_guard_four_conditions() -> None:
    g = an.quality_guard
    ok = (F(5, 1000), 1, F(3, 4), F(3, 4))
    assert g(*ok)["passes"]
    assert not g(F(51, 10000), 1, F(3, 4), F(3, 4))["passes"]  # mean dNLL just above +0.005
    assert not g(F(0), 2, F(1), F(1))["passes"]  # two pairs above
    assert not g(F(0), 0, F(74, 100), F(1))["passes"]  # gain retention < 0.75
    assert not g(F(0), 0, F(1), F(74, 100))["passes"]  # association retention < 0.75
    assert not g(F(0), 0, None, F(1))["passes"]  # undefined fails
    assert an.utilization_guard(0.8) == "retained" and an.utilization_guard(0.79) == "reduced"
    assert an.utilization_guard(0.5) == "reduced" and an.utilization_guard(0.49) == "collapsed"


def test_study_class_and_decision_map() -> None:
    assert an.study_class("X", "X")["class"] == "X"
    s = an.study_class(an.POSITIVE, an.NO_DIFF)
    assert s["class"] == an.NOT_REPLICATED and s["panel_A"] == an.POSITIVE
    d = an.decision_option
    assert d(True, True, ["C07"], ["C06"])[0] == "c"  # concentration controls bind
    assert d(False, True, ["C07"], [])[0] == "a"
    assert d(False, True, ["C07"], ["C06"])[0] == "a"  # (a) takes precedence over (b)
    assert d(False, True, [], ["C06"])[0] == "b"
    assert d(False, True, [], [])[0] == "c"
    assert d(False, False, [], [])[0] == "none"
    classes = {"A": {"C04": an.NO_DIFF, "C05": an.POSITIVE}, "B": {"C04": an.NO_DIFF}}
    assert an.concentration_controls_bind(classes)
    assert not an.concentration_controls_bind(
        {"A": {"C04": an.REDUCED}, "B": {"C05": an.CONC_ONLY}}
    )


# --- exact helpers and undefined handling -----------------------------------------------------------
def test_retention_undefined_for_nonpositive_baseline_fails_guard() -> None:
    value, why = an.retention(F(1, 50), F(0), "gain retention", "gain")
    assert value is None and why is not None and "<= 0" in why
    assert an.retention(F(-4, 1000), F(-2, 1000), "x", "gain")[0] is None  # no sign flip
    assert an.retention(F(1, 50), F(1, 50), "x", "gain")[0] == 1
    guard = an.quality_guard(F(0), 0, None, F(1))
    assert guard["passes"] is False and guard["undefined"] == ["gain_retention"]
    # through the pipeline: a baseline with a non-positive mean gain makes every case QUALITY-FAILED
    cells = make_cells({("C01", "*"): Spec(gain=-0.1), ("C04", "*"): GOOD})
    comp = an.compare(cells, "C04", "C01", "A", (an.L_COAX,))
    assert comp["quality"]["gain_retention"] is None
    assert comp["quality"]["retention_undefined_reasons"]
    r = an.analyse(cells, [])
    assert r["cases"]["C04"]["study_classification"]["class"] == an.QUALITY_FAILED


def test_ratio_reports_undefined() -> None:
    assert an.ratio(F(1), F(2), "x") == (F(1, 2), None)
    value, why = an.ratio(F(1), F(0), "x")
    assert value is None and why is not None and "zero" in why
    assert an.ratio(None, F(1), "x")[0] is None
    assert an.geometric_mean_ratio([4.0, 1.0], [1.0, 1.0])[0] == pytest.approx(2.0)
    assert an.geometric_mean_ratio([0.0], [1.0])[0] is None


def test_e_undefined_below_null_floor() -> None:
    cells = make_cells({("C01", "*"): Spec(nf=0.04)})
    c = cells[core.parse_label("b101-o301-s601-C01").label]
    value, why = c.e("A", 2, "asc", b_core.L_COAX)
    assert value is None and why is not None and "undefined" in why
    ok = cells[core.parse_label("b101-o301-s601-C02").label]
    assert ok.e("A", 2, "asc", b_core.L_COAX)[0] is not None


def test_e_ratio_and_adjustment_undefined_when_a_member_is_undefined() -> None:
    cells = make_cells({("C01", "*"): Spec(nf=0.04)})
    comp = an.compare(cells, "C04", "C01", "A", (an.L_COAX,))
    c0 = comp["tags"][an.L_COAX]["R2|C32|asc"]
    assert c0["e_ratio"] is None and c0["rho_adj"] is None and c0["m_ratio"] is not None
    assert any("E undefined" in r for r in c0["undefined_reasons"])


def test_adjusted_ratio_undefined_without_range_overlap() -> None:
    cells = make_cells({("C04", "*"): Spec(neff=100.0)})  # x ranges do not overlap
    comp = an.compare(cells, "C04", "C01", "A", (an.L_COAX,))
    cond0 = comp["tags"][an.L_COAX]["R2|C32|asc"]
    assert cond0["rho_adj"] is None
    assert any("do not overlap" in r for r in cond0["undefined_reasons"])
    assert cond0["e_ratio"] is not None


# --- full pipeline on synthetic records ------------------------------------------------------------
GOOD = Spec(m=0.5, nf=1.0)
SPECS = {
    ("C04", "*"): GOOD,  # LOCALITY-POSITIVE
    ("C05", "*"): Spec(m=0.5, neff=0.65),  # reduced utilization
    ("C06", "*"): Spec(m=0.5, nf=0.5),  # concentration only (E unchanged)
    ("C07", "*"): Spec(m=0.5, neff=0.3),  # collapsed
    ("C08", "*"): Spec(m=1.3),  # worse
    ("C09", "*"): Spec(gain=0.5),  # quality failed
    ("C10", "*"): Spec(m=0.85),  # intermediate
}


@pytest.fixture(scope="module")
def result() -> dict:
    cells = make_cells(SPECS)
    return an.analyse(cells, [])


def test_pipeline_classes(result: dict) -> None:
    got = {c: result["cases"][c]["study_classification"]["class"] for c in core.CASE_BASELINE}
    assert got == {
        "C04": an.POSITIVE,
        "C05": an.REDUCED,
        "C06": an.CONC_ONLY,
        "C07": an.COLLAPSED,
        "C08": an.WORSE,
        "C09": an.QUALITY_FAILED,
        "C10": an.INTERMEDIATE,
    }
    assert result["study_status"] == "COMPLETE" and result["cells_expected"] == 60
    assert result["concentration_controls_bind"] is True  # C04 is LOCALITY-POSITIVE
    assert result["decision_inputs"]["section_8_option_indicated"] == "c"
    assert result["cases"]["C04"]["beats_optimized_flat"]["holds"] is True


def test_open_questions_listed_and_decision_rules(result: dict) -> None:
    open_cases = {q["case"]: q["class"] for q in result["open_questions"]}
    assert open_cases["C10"] == an.INTERMEDIATE and "C04" not in open_cases
    assert result["decision_inputs"]["open_questions"] == result["open_questions"]
    # non-replication of another case does not void (a)
    specs = {("C09", "*"): GOOD, ("C06", "A"): GOOD, ("C06", "B"): Spec(m=1.0)}
    r = an.analyse(make_cells(specs), [])
    assert r["decision_inputs"]["section_8_option_indicated"] == "a"
    assert {q["case"] for q in r["open_questions"]} == {"C06"}


def test_no_difference_is_the_default(result: dict) -> None:
    cells = make_cells({})
    r = an.analyse(cells, [])
    assert all(
        r["cases"][c]["study_classification"]["class"] == an.NO_DIFF for c in core.CASE_BASELINE
    )
    assert r["decision_inputs"]["section_8_option_indicated"] == "c"
    assert not r["concentration_controls_bind"]


def test_tie_rule_and_panel_disagreement() -> None:
    specs = {
        ("C06", "A"): GOOD,
        ("C06", "B"): Spec(m=1.0),
        ("C08", "*"): Spec(m=0.5, m_desc=1.8),  # asc improves, desc does not (0.9 vs 1.0 band edge)
    }
    r = an.analyse(make_cells(specs), [])
    study = r["cases"]["C06"]["study_classification"]
    assert study["class"] == an.NOT_REPLICATED
    assert (study["panel_A"], study["panel_B"]) == (an.POSITIVE, an.NO_DIFF)
    assert r["cases"]["C08"]["study_classification"]["class"] == an.INTERMEDIATE


def test_decision_a_requires_architecture_advantage_vs_counterpart() -> None:
    specs = {("C07", "*"): GOOD}  # C06 stays at the baseline: C07 beats it by 0.5
    r = an.analyse(make_cells(specs), [])
    c07 = r["cases"]["C07"]
    assert c07["study_classification"]["class"] == an.POSITIVE
    assert c07["architecture_advantage"]["holds"] is True
    assert r["decision_inputs"]["section_8_option_indicated"] == "a"
    # the same case with C06 equally good: beats flat but no architecture advantage; flat positive -> (b)
    specs2 = {("C07", "*"): GOOD, ("C06", "*"): GOOD}
    r2 = an.analyse(make_cells(specs2), [])
    assert r2["cases"]["C07"]["architecture_advantage"]["holds"] is False
    assert r2["decision_inputs"]["section_8_option_indicated"] == "b"


def test_ratios_of_means_and_parent_count() -> None:
    r = an.analyse(make_cells({("C04", "*"): GOOD}), [])
    c = r["cases"]["C04"]["panels"]["A"]["vs_baseline"]
    first = c["tags"][an.L_COAX]["R2|C32|asc"]
    assert float(first["m_ratio"]) == pytest.approx(0.5, rel=0.05)
    assert first["parents_e_below_one"] == 3 and first["pairs_e_lower"] == 6
    assert c["quality"]["gain_retention"] == F(1)
    assert c["quality"]["context_breadth_ratio"] == pytest.approx(1.0)
    assert set(c["tags"]) == {an.L_COAX}  # flat case has no L-BCOAX


def test_tree_cases_report_bcoax() -> None:
    r = an.analyse(make_cells({}), [])
    comp = r["cases"]["C05"]["panels"]["A"]["vs_baseline"]
    assert set(comp["tags"]) == {an.L_COAX, an.L_BCOAX}
    assert comp["tags"][an.L_BCOAX]["R2|C32|asc"]["layout_case"] == an.L_BCOAX
    vs_flat = r["cases"]["C05"]["panels"]["A"]["vs_other"]["flat_counterpart"]
    assert vs_flat["reference"] == "C04"
    assert vs_flat["tags"][an.L_BCOAX]["R2|C32|asc"]["layout_reference"] == an.L_COAX
    c10 = r["cases"]["C10"]["panels"]["A"]["vs_other"]
    assert {"flat_counterpart_C06", "flat_counterpart_C08", "c01"} <= set(c10)


def test_controls_and_means(result: dict) -> None:
    ctrl = result["cases"]["C06"]["panels"]["A"]["controls"]["R2|C32|asc"]
    assert ctrl["partition_over_coax"] == pytest.approx(
        1.2, rel=1e-3
    )  # fake: partitions are 1.2 x L-COAX
    assert ctrl["id_over_coax"] == pytest.approx(2.0, rel=1e-3)
    assert result["cases"]["C07"]["panels"]["A"]["controls"]["R2|C32|asc"][
        "bcoax_over_partition"
    ] == (pytest.approx(0.9 / 1.2, rel=1e-3))
    means = result["cases"]["C04"]["panels"]["A"]["means"]
    assert means["cells"] == 6 and means["context_breadth"] == 100.0
    assert means["memory_gain"] == pytest.approx(0.02)


# --- incompleteness ---------------------------------------------------------------------------------
def test_incomplete_study_never_reduces_the_denominator() -> None:
    cells = make_cells(SPECS)
    gone = core.parse_label("b102-o302-s602-C04").label
    del cells[gone]
    r = an.analyse(cells, [{"label": gone, "reasons": ["eval.json missing"]}])
    assert r["study_status"] == "INCOMPLETE" and r["cells_expected"] == 60
    assert r["cells_with_complete_records"] == 59
    assert r["cases"]["C04"]["study_classification"]["class"] == an.INCOMPLETE
    comp = r["cases"]["C04"]["panels"]["A"]["vs_baseline"]
    assert comp["pairs_expected"] == 6 and comp["pairs_available"] == 5 and comp["missing_cells"]
    assert r["cases"]["C05"]["study_classification"]["class"] == an.REDUCED  # unaffected cases stay
    assert r["decision_inputs"]["section_8_option_indicated"] == "none"


def test_run_analysis_refuses_unless_allowed(tmp_path: Path) -> None:
    for name in ("eval", "sim"):
        (tmp_path / name).mkdir()
        write_json(
            tmp_path / name / "manifest.json",
            {
                "dry_run": True,
                "source_sha256": "s",
                "spec_sha256": "p",
                "panel_record_sha256": None,
            },
        )
    with pytest.raises(b_core.GateError, match="of 60 cells"):
        an.run_analysis(tmp_path / "eval", tmp_path / "sim", tmp_path / "out", dry_run=True)
    run = an.run_analysis(
        tmp_path / "eval", tmp_path / "sim", tmp_path / "out", dry_run=True, allow_incomplete=True
    )
    data = json.loads((run / "analysis.json").read_text())
    assert data["study_status"] == "INCOMPLETE" and len(data["missing_cells"]) == 60
    assert data["cases"]["C04"]["study_classification"]["class"] == an.INCOMPLETE
    for name in ("scorecard.csv", "cells.csv", "pairs.csv"):
        assert (run / name).is_file()


def test_outputs_written_and_json_clean(tmp_path: Path) -> None:
    cells = make_cells(SPECS)
    clean = an.jsonable(an.analyse(cells, []))
    json.dumps(clean, allow_nan=False)  # no NaN/inf, no Fractions left
    header, rows = an.scorecard_rows(an.jsonable_floats(an.analyse(cells, [])))
    assert len(rows) == 10 and all(len(r) == len(header) for r in rows)
    h2, r2 = an.cells_rows(cells)
    assert len(r2) == 60 * 2 * 4 and all(len(r) == len(h2) for r in r2)
    h3, r3 = an.pairs_rows(cells)
    assert r3 and all(len(r) == len(h3) for r in r3)


def test_provenance_must_be_consistent() -> None:
    manifest = {
        "dry_run": True,
        "source_sha256": "s",
        "spec_sha256": "p",
        "panel_record_sha256": "r",
    }
    good = {"dry_run": True, "source_sha256": "s", "spec_sha256": "p", "panel_record_sha256": "r"}
    records = [
        ("eval:x", dict(good)),
        ("sim:x", {k: v for k, v in good.items() if k != "panel_record_sha256"}),
    ]
    assert an.check_provenance(manifest, dict(manifest), records, True)["source_sha256"] == "s"
    for bad_records, dry in (
        ([("eval:x", {**good, "source_sha256": "other"})], True),  # source differs
        ([("eval:x", {**good, "spec_sha256": "other"})], True),  # spec differs
        ([("eval:x", {**good, "panel_record_sha256": "other"})], True),  # panel record differs
        ([("eval:x", {**good, "dry_run": False})], True),  # dry-run record in the other mode
        ([("eval:x", dict(good))], False),  # dry-run records in a registered analysis
    ):
        with pytest.raises(b_core.GateError, match="inconsistent provenance"):
            an.check_provenance(manifest, dict(manifest), bad_records, dry)
    registered = {**manifest, "dry_run": False}
    with pytest.raises(b_core.GateError):  # no freeze commit in the manifests
        an.check_provenance(
            registered, dict(registered), [("eval:x", {**good, "dry_run": False})], False
        )


def test_registered_analysis_requires_freeze_commit(tmp_path: Path) -> None:
    with pytest.raises(b_core.GateError, match="--freeze-commit"):
        an.run_analysis(tmp_path, tmp_path, tmp_path, dry_run=False)
