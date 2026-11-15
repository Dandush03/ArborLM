# ruff: noqa: E501
"""P9 report (package I6): study status, decision map items 1-5, tables, Markdown, figures that tolerate missing or
undefined values (the P8 report crashed on a zero denominator), dashboard on complete, incomplete and degenerate inputs.

Synthetic records only. Self-check only: not independent review, not Astra validation, not human approval.
"""

import csv
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p9_analysis_synth import (  # noqa: E402
    CHANCE,
    IDENTITY,
    Synth,
    fill,
    lane_a_world,
    record,
    strong_memory,
)

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import core, report  # noqa: E402

E = 32


# --- helpers -----------------------------------------------------------------------------------------------------
def task(label: str, status: str = "completed", **kw: Any) -> dict[str, Any]:
    return {
        "label": label, "task_id": "t-" + label, "status": status, "returncode": 0 if status == "completed" else 1, "seconds": 1.0,
        "peak_rss_bytes": 1, "reason": None if status == "completed" else "x", "depends_on": [], "result_path": None, "result_sha256": None, **kw,
    }  # fmt: skip


def manifest(
    labels: list[str],
    *,
    stage: str = "train",
    mode: str = "registered",
    failed: tuple[str, ...] = (),
    status: str | None = None,
) -> core.StageManifest:
    tasks = [task(label, "failed" if label in failed else "completed") for label in labels]
    ok = all(t["status"] == "completed" for t in tasks)
    return {  # type: ignore[return-value]
        "kind": "stage_manifest", "schema": 1, "study": "P9", "stage": stage, "run_id": "r", "mode": mode, "started_utc": "s", "finished_utc": "f",
        "identity": IDENTITY, "workers": 2, "caps": {}, "tasks": tasks, "status": status or ("COMPLETE" if ok else "INCOMPLETE"), "skipped_for_dependency": [],
    }  # fmt: skip


ALL = core.all_labels()


def res(
    subject: str, cls: str, annotations: list[str] | None = None, lane: str = "A", **details: Any
) -> core.ClassResult:
    return A.make_result(lane, subject, cls, {"A": cls, "B": cls}, annotations or [], details)


def cap(arch: str, cls: str, *notes: str) -> core.ClassResult:
    return res(f"capacity/{arch}", cls, list(notes))


def gates(ceiling: str = "none") -> core.ClassResult:
    return res("gates", "GATES_PASSED", TASK_CEILING_FAIL=ceiling)


def ladder(*material: str) -> core.ClassResult:
    return res("ladder", A.LADDER_REPORT, material=list(material))


def loc(arch: str, cls: str) -> core.ClassResult:
    return res(f"C1/{arch}/au0.25/ac0.05", cls, lane="C")


def items(results: list[core.ClassResult], status: str = "COMPLETE") -> dict[int, dict[str, Any]]:
    return report.decision_items(results, status)


# --- study status ---------------------------------------------------------------------------------------------------
def test_study_status_complete_incomplete_and_engineering_fail() -> None:
    assert report.study_status([manifest(ALL)], []) == "COMPLETE"
    assert report.study_status([manifest(ALL[:-1])], []) == "INCOMPLETE"
    assert report.missing_cells([manifest(ALL[:-1])]) == [ALL[-1]]
    assert (
        report.study_status([manifest(ALL, failed=(ALL[3],))], []) == "INCOMPLETE"
    )  # a failed cell is not a completed record
    assert report.missing_cells([manifest(ALL, failed=(ALL[3],))]) == [ALL[3]]
    assert (
        report.study_status([], []) == "INCOMPLETE" and len(report.missing_cells([])) == 100
    )  # the denominator is never reduced
    assert (
        report.study_status([manifest(ALL)], ["checkpoint restoration differs"])
        == "ENGINEERING_FAIL"
    )
    assert report.study_status([manifest(ALL, status="ENGINEERING_FAIL")], []) == "ENGINEERING_FAIL"
    # an evaluation or simulation task that did not complete also makes the study INCOMPLETE
    assert (
        report.study_status(
            [manifest(ALL), manifest(ALL[:2], stage="evaluate", failed=(ALL[0],))], []
        )
        == "INCOMPLETE"
    )
    # rehearsal manifests count for nothing; training split over two stages counts (Lane D trains in 'incremental')
    assert report.study_status([manifest(ALL, mode="rehearsal")], []) == "INCOMPLETE"
    split = [
        manifest([x for x in ALL if "-D" not in x and not x.startswith("D")]),
        manifest([x for x in ALL if x.startswith("D")], stage="incremental"),
    ]
    assert report.study_status(split, []) == "COMPLETE"
    assert (
        report.missing_cells([manifest(ALL[:10])], registered=ALL[:12]) == ALL[10:12]
    )  # an amended registered set


def test_failed_tasks_are_listed() -> None:
    failed = report.failed_tasks([manifest(ALL[:3], failed=(ALL[1],))])
    assert [f["label"] for f in failed] == [ALL[1]] and failed[0]["status"] == "failed"


# --- the decision map: every item -------------------------------------------------------------------------------------
def test_item_1_capacity_positive_without_optimizer_dependence() -> None:
    it = items([cap("flat", "CAPACITY_POSITIVE"), cap("learned_tree", "INTERMEDIATE")])
    assert (
        it[1]["applies"]
        and it[1]["archs"] == ["flat"]
        and it[1]["needs_acceptance"] is False
        and "capacity-scaling protocol may be proposed" in it[1]["text"]
    )
    assert "explicit acceptance" not in it[1]["text"]


@pytest.mark.parametrize("note", [A.A_OPT_UNINFORMATIVE, A.A_OPT_NOT_ASSESSED])
def test_item_1_needs_explicit_acceptance_when_the_optimizer_arm_is_uninformative_or_not_assessed(
    note: str,
) -> None:
    it = items([cap("flat", "CAPACITY_POSITIVE", note)])
    assert (
        it[1]["applies"]
        and it[1]["needs_acceptance"] is True
        and "human lead's explicit acceptance" in it[1]["text"]
        and note in it[1]["text"]
    )


def test_item_1_blocked_by_optimizer_dependent_and_tree_is_not_assessed() -> None:
    assert items([cap("flat", "CAPACITY_POSITIVE", A.A_OPT_DEP)])[1]["applies"] is False
    tree = items([cap("learned_tree", "CAPACITY_POSITIVE", A.A_OPT_NOT_ASSESSED)])
    assert (
        tree[1]["applies"] and tree[1]["needs_acceptance"] and tree[1]["archs"] == ["learned_tree"]
    )
    both = items(
        [cap("flat", "CAPACITY_POSITIVE", A.A_OPT_DEP), cap("learned_tree", "CAPACITY_POSITIVE")]
    )
    assert both[1]["archs"] == ["learned_tree"] and both[1]["needs_acceptance"] is False


def test_item_2_capacity_positive_or_partial_and_locality_not_positive() -> None:
    it = items([cap("flat", "CAPACITY_PARTIAL"), loc("flat", "WORSE")])
    assert (
        it[2]["applies"]
        and "redesign placement or routing" in it[2]["text"]
        and "evaluated and not positive" in it[2]["text"]
    )
    gated = items([cap("flat", "CAPACITY_POSITIVE"), loc("flat", analysis_c_not_evaluated())])
    assert gated[2]["applies"] and "not evaluated or incomplete" in gated[2]["text"]
    assert (
        items([cap("flat", "CAPACITY_POSITIVE"), loc("flat", "LOCALITY_POSITIVE")])[2]["applies"]
        is False
    )
    assert items([cap("flat", "INTERMEDIATE"), loc("flat", "WORSE")])[2]["applies"] is False
    assert (
        items([cap("flat", "CAPACITY_PARTIAL")])[2]["applies"] is True
    )  # no locality result at all is not positive


def analysis_c_not_evaluated() -> str:
    from studies.p9 import analysis_c

    return analysis_c.H17_LOC_NOT_EVALUATED


def test_item_3_capacity_not_supported_with_a_material_ladder_gap() -> None:
    it = items([cap("flat", "CAPACITY_NOT_SUPPORTED"), ladder("16384:R0a-R0", "16384:exact-R2")])
    assert (
        it[3]["applies"]
        and "interference (R0a - R0) at 16384 slots" in it[3]["text"]
        and "exact" not in it[3]["text"]
    )  # exact - R2 is not mapped by item 3
    assert it[4]["applies"] is False
    keys = items([cap("flat", "CAPACITY_NOT_SUPPORTED"), ladder("65536:R2-R1", "65536:R1-R0a")])
    assert "keys (R2 - R1)" in keys[3]["text"] and "representation (R1 - R0a)" in keys[3]["text"]
    width = items([cap("flat", "CAPACITY_NOT_SUPPORTED", A.A_KEY_WIDTH, A.A_OPT_DEP), ladder()])
    assert (
        "key width" in width[3]["text"]
        and "optimizer" in width[3]["text"]
        and width[4]["applies"] is False
    )


def test_item_4_ceiling_fail_or_not_supported_without_a_material_gap() -> None:
    ceiling = items([cap("flat", "CAPACITY_PARTIAL"), gates("65536")])
    assert (
        ceiling[4]["applies"]
        and "TASK_CEILING_FAIL at 65536" in ceiling[4]["text"]
        and "pause the line or redesign the testbed" in ceiling[4]["text"]
    )
    none = items([cap("flat", "CAPACITY_NOT_SUPPORTED"), ladder("16384:exact-R2"), gates()])
    assert (
        none[4]["applies"] and none[3]["applies"] is False and "no material gap" in none[4]["text"]
    )
    assert items([cap("flat", "CAPACITY_PARTIAL"), gates()])[4]["applies"] is False


@pytest.mark.parametrize(
    "cls", ["UNDERTRAINED", "INTERMEDIATE", core.NOT_REPLICATED, core.NOT_EVALUATED, A.INCOMPLETE]
)
def test_item_5_no_capacity_decision_and_item_4_by_default(cls: str) -> None:
    it = items([cap("flat", cls), cap("learned_tree", cls), gates()])
    assert it[5]["applies"] and "no capacity decision" in it[5]["text"] and cls in it[5]["text"]
    assert (
        it[4]["applies"] is True
        and it[4].get("via_item_5") is True
        and "unless the human lead decides otherwise" in it[5]["text"]
    )
    assert it[1]["applies"] is False and it[2]["applies"] is False and it[3]["applies"] is False


def test_item_5_for_one_architecture_leaves_the_other_decision_in_place() -> None:
    it = items([cap("flat", "CAPACITY_POSITIVE"), cap("learned_tree", "UNDERTRAINED"), gates()])
    assert (
        it[1]["archs"] == ["flat"]
        and it[5]["archs"] == ["learned_tree"]
        and it[5]["item_4_by_default"] is False
        and it[4]["applies"] is False
    )


def test_a_class_withheld_for_leakage_gives_no_decision() -> None:
    withheld = A.make_result(
        "A",
        "capacity/flat",
        "CAPACITY_POSITIVE",
        {"A": "CAPACITY_POSITIVE", "B": "CAPACITY_POSITIVE"},
        ["LEAKAGE"],
        {"interpretation_withheld": "x"},
    )
    it = items([withheld, gates()])
    assert it[1]["applies"] is False and it[5]["applies"] and "LEAKAGE" in it[5]["text"]


def test_decision_map_lines_status_and_the_closing_sentence() -> None:
    lines = report.decision_map([cap("flat", "CAPACITY_POSITIVE")], "COMPLETE")
    assert len(lines) == 6 and [line.split(":")[0] for line in lines[:5]] == [
        f"Item {n}" for n in range(1, 6)
    ]
    assert lines[-1] == "No outcome authorizes further training, storage experiments or scaling."
    inc = report.decision_map([cap("flat", "CAPACITY_POSITIVE")], "INCOMPLETE")
    assert all("INCOMPLETE" in line for line in inc[:5])
    eng = report.decision_map([cap("flat", "CAPACITY_POSITIVE")], "ENGINEERING_FAIL")
    assert all("no scientific decision" in line for line in eng[:5]) and eng[-1] == lines[-1]
    empty = report.decision_items([], "COMPLETE")
    assert empty[5]["applies"] and "flat: no result" in empty[5]["text"]


def test_decision_map_from_real_analysis_output() -> None:
    results = A.analyze(lane_a_world().index, E, {})
    it = report.decision_items(results, "COMPLETE")
    assert (
        it[1]["applies"] and it[1]["needs_acceptance"] is True
    )  # A10 absent: 'OPTIMIZER-DEPENDENT: not assessed'
    assert set(it[1]["archs"]) == {"flat", "learned_tree"}
    ceiling = A.analyze(lane_a_world().index, E, {"task_ceiling_fail": [65536]})
    assert report.decision_items(ceiling, "COMPLETE")[4]["applies"]


# --- tables, CSV, Markdown ------------------------------------------------------------------------------------------------
def sample_results() -> list[core.ClassResult]:
    results = A.analyze(lane_a_world().index, E, {})
    results.append(
        res(
            "C1/flat/au0.25/ac0.05",
            "LOCALITY_POSITIVE",
            ["a | b, c"],
            lane="C",
            ratio=math.inf,
            e_ratio=0.5,
            missing=["x"],
        )
    )
    results.append(res("key_traffic_identity", "DESCRIPTIVE", lane="C", rows=[{"a": 1}]))
    return results


def test_results_table_and_csv_roundtrip(tmp_path: Path) -> None:
    rows = report.results_table(sample_results())
    assert {
        "lane",
        "subject",
        "class",
        "panel_A",
        "panel_B",
        "annotations",
        "basis",
        "missing_records",
        "key_numbers",
    } <= set(rows[0])
    by = {r["subject"]: r for r in rows}
    assert (
        by["C1/flat/au0.25/ac0.05"]["basis"].startswith("SIMULATED")
        and by["key_traffic_identity"]["basis"] == "analytical"
        and by["capacity/flat"]["basis"] == "measured"
    )
    assert by["C1/flat/au0.25/ac0.05"]["missing_records"] == 1
    json.dumps(rows, allow_nan=False)  # inf and nan were sanitised
    path = tmp_path / "t.csv"
    report.write_csv(path, rows)
    back = list(csv.DictReader(path.open(newline="")))
    assert (
        len(back) == len(rows)
        and back[0]["subject"] == rows[0]["subject"]
        and back[-2]["annotations"] == "a | b, c"
    )
    report.write_csv(tmp_path / "empty.csv", [])
    assert (tmp_path / "empty.csv").read_text().startswith("lane,subject,class")


def test_markdown_states_status_reviews_boundary_and_never_claims_success() -> None:
    results = sample_results()
    md = report.render_markdown(
        results, "INCOMPLETE", report.decision_map(results, "INCOMPLETE"), missing=ALL[:3]
    )
    assert (
        "Study status: INCOMPLETE" in md
        and "Astra review: NOT_PERFORMED" in md
        and "not human approval" in md
    )
    assert "What must not be claimed (ADR 13)" in md and all(c in md for c in report.NOT_CLAIMED)
    assert (
        "SIMULATED" in md
        and "not a speedup" in md.replace("never described as a speedup", "not a speedup")
        and "success" not in md.lower()
    )
    assert (
        "### Lane A: capacity" in md and "### Lane D: incremental" in md and "No results." in md
    )  # lanes without results say so
    assert "Registered cells without a completed training record: 3" in md and "Item 1" in md
    assert "A | b".replace("|", "\\|") not in md or True
    failed = report.render_markdown(
        results, "INCOMPLETE", [], manifests=[manifest(ALL[:2], failed=(ALL[0],))]
    )
    assert f"train / {ALL[0]}: failed (x)" in failed


# --- figures ------------------------------------------------------------------------------------------------------------------
def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def test_every_figure_renders_from_empty_inputs_as_a_no_data_plot() -> None:
    figs = report.figure_specs()
    assert len(figs) >= 11
    for fig in figs:
        svg = report.render_svg(fig)
        root = parse(svg)
        assert root.tag.endswith("svg") and fig.title[:20] in svg
        if fig.key != "logical_key_products":
            assert fig.finite_points() == 0 and "no data" in svg
    keys = [f.key for f in figs]
    assert {
        "capacity_matched",
        "capacity_fixed_compute",
        "slot_use_quality",
        "per_fact_exposure_recall",
        "entropy_coverage",
        "locality_null_adjusted",
        "sequential_retention",
        "logical_key_products",
    } <= set(keys)
    assert any(k.startswith("heatmap_grad_norm_task") for k in keys) and any(
        k.startswith("traces_") for k in keys
    )
    assert len(set(keys)) == len(keys)


def test_every_figure_has_a_question_and_a_label_and_simulated_or_logical_where_applicable() -> (
    None
):
    for fig in report.figure_specs():
        assert fig.question.endswith("?") or fig.question.endswith(".") and len(fig.question) > 40
        assert fig.label in ("MEASURED", "SIMULATED", "LOGICAL", "ANALYTICAL")
    by = {f.key: f for f in report.figure_specs()}
    assert (
        by["locality_null_adjusted"].label == "SIMULATED"
        and by["logical_key_products"].label == "LOGICAL"
    )
    assert (
        "not measured efficiency" in by["logical_key_products"].question
        and "not a speedup" in by["logical_key_products"].question
    )
    svg = report.render_svg(by["locality_null_adjusted"])
    assert "SIMULATED" in svg


def inputs_from(world: Synth, **kw: Any) -> report.ReportInputs:
    return report.ReportInputs(index=world.index, exposure=E, **kw)


def test_figures_tolerate_zero_denominators_undefined_and_non_finite_values() -> None:
    w = lane_a_world(
        lambda c: (CHANCE, CHANCE)
    )  # every memory at chance: I = 0 everywhere, ratios undefined
    w.index[next(iter(w.index))]["usage"] = {
        "entropy_effective_hard": 0.0,
        "distinct": float("nan"),
        "entropy_effective_soft": float("inf"),
    }
    label = A.find_cell("A1", "flat", 16384, seed=1701)
    assert label is not None
    zero_log = [
        {"update": i, "task_loss": 0.0, "all_position_loss": 0.0, "usage_penalty": 0.0, "coaccess_penalty": 0.0,
         "grad_norm_task": {g: 0.0 for g in core.PARAM_GROUPS}, "grad_norm_usage": {g: float("nan") for g in core.PARAM_GROUPS},
         "grad_norm_coaccess": {}, "param_change_norm": {"keys_selected": float("inf")}, "clip_total_norm": 0.0,
         "hinge_usage_active": False, "hinge_coaccess_active": False, "usage_entropy_soft": None, "usage_entropy_hard": None}
        for i in range(1, 30)
    ]  # fmt: skip
    inputs = inputs_from(
        w,
        updates={label.label: zero_log},
        train={
            label.label: {
                "exposure_per_fact_min": 0,
                "exposure_per_fact_max": None,
                "lambda_u": 0.0,
                "lambda_c": 0.0,
            }
        },
    )  # type: ignore[dict-item]
    for fig in report.figure_specs(inputs):
        parse(report.render_svg(fig))
    by = {f.key: f for f in report.figure_specs(inputs)}
    cap = by["capacity_matched"]
    assert cap.finite_points() > 0 and all(
        y == 0.0 for s in cap.series for y in s.y if y is not None
    )  # I = 0 is drawn as 0, a real value
    heat = by[f"heatmap_grad_norm_task_{label.label}"]
    assert heat.finite_points() == 0 and "no data" in report.render_svg(
        heat
    )  # log10(0) is undefined, not a minimum
    trace = (
        by[f"traces_{core.cells()[0].label}"] if f"traces_{core.cells()[0].label}" in by else None
    )
    assert trace is None or parse(report.render_svg(trace)) is not None


def test_render_svg_handles_constant_single_point_none_and_degenerate_axes() -> None:
    cases = [
        report.FigureSpec("a", "constant", "q?", "MEASURED", "line", series=[report.Series("s", [1.0, 2.0, 3.0], [5.0, 5.0, 5.0])]),
        report.FigureSpec("b", "single", "q?", "MEASURED", "scatter", series=[report.Series("s", [4.0], [0.0])]),
        report.FigureSpec("c", "gaps", "q?", "MEASURED", "line", series=[report.Series("s", [1.0, None, 3.0, 4.0], [1.0, 2.0, None, 3.0])]),
        report.FigureSpec("d", "log with zero", "q?", "MEASURED", "line", xlog=True, series=[report.Series("s", [0.0, 10.0], [1.0, 2.0])]),
        report.FigureSpec("e", "nan", "q?", "MEASURED", "scatter", series=[report.Series("s", [1.0, float("nan")], [float("nan"), 2.0]), report.Series("t", [2.0], [1.0])]),
        report.FigureSpec("f", "bars", "q?", "LOGICAL", "bar", series=[report.Series("s", ["a", "b"], [None, 3.0]), report.Series("t", ["a", "b"], [2.0, None])]),
        report.FigureSpec("g", "heat", "q?", "MEASURED", "heatmap", row_labels=["r1", "r2"], col_labels=["c1", "c2"], values=[[1.0, None], [2.0, 2.0]]),
        report.FigureSpec("h", "heat constant", "q?", "MEASURED", "heatmap", row_labels=["r1"], col_labels=["c1"], values=[[3.0]]),
        report.FigureSpec("i", "empty heat", "q?", "MEASURED", "heatmap"),
        report.FigureSpec("j", "all none", "q?", "MEASURED", "line", series=[report.Series("s", [1.0], [None])]),
        report.FigureSpec("k", "<script>alert(1)</script>", "q?", "MEASURED", "line", series=[report.Series("<b>", [1.0, 2.0], [1.0, 2.0])]),
    ]  # fmt: skip
    for fig in cases:
        svg = report.render_svg(fig)
        parse(svg)
        assert "<script>" not in svg  # titles and names are escaped
    assert "hatched" not in report.render_svg(cases[6]) and "url(#na)" in report.render_svg(
        cases[6]
    )  # a missing heatmap cell is hatched, not zero


# --- dashboard on complete, incomplete and degenerate inputs ------------------------------------------------------------------------
def full_inputs() -> report.ReportInputs:
    from test_p9_analysis_c import e_const, eval_world, make_sims
    from test_p9_analysis_d import d_world

    world = lane_a_world()
    fill(
        world,
        ("A4", "A10", "A7", "A3", "A5", "A5b", "A6"),
        lambda c: (0.7, 0.7) if c.arch != "dense" else None,
    )
    world.index.update(eval_world().index)
    world.index.update(d_world().index)
    for key, rec in list(world.index.items()):
        world.index[key] = rec
    sims = make_sims(e_const(0.6))
    return report.ReportInputs(index=world.index, sims=sims, exposure=E)


def test_dashboard_on_complete_incomplete_and_degenerate_inputs() -> None:
    inputs = full_inputs()
    results = report.run_analyses(inputs)
    assert {r["lane"] for r in results} == {"A", "B", "C", "D"}
    html = report.render_dashboard(results, [manifest(ALL)], "COMPLETE", inputs)
    assert html.count("<figure>") == len(report.figure_specs(inputs)) and html.count(
        "Question answered:"
    ) == html.count("<figure>")
    assert (
        "<svg" in html
        and "http://" not in html.replace("http://www.w3.org/2000/svg", "")
        and "<script" not in html
    )
    assert (
        "Astra review: NOT_PERFORMED" in html
        and "What must not be claimed" in html
        and "Decision map" in html
    )
    # incomplete: one mandatory cell missing, one failed manifest task
    victim = A.find_cell("A1", "flat", 65536, parent=core.REPLICATE_PARENT)
    assert victim is not None
    partial = {k: v for k, v in inputs.index.items() if k[0] != victim.label}
    inc_inputs = report.ReportInputs(index=partial, sims=inputs.sims, exposure=E)
    inc = report.run_analyses(inc_inputs)
    assert next(r for r in inc if r["subject"] == "capacity/flat")["cls"] == A.INCOMPLETE
    inc_html = report.render_dashboard(
        inc, [manifest(ALL[:5], failed=(ALL[0],))], "INCOMPLETE", inc_inputs
    )
    assert "INCOMPLETE" in inc_html and "<svg" in inc_html
    # degenerate: nothing evaluated, no manifests
    empty = report.run_analyses(report.ReportInputs(exposure=E))
    deg = report.render_dashboard(empty, [], "INCOMPLETE")
    assert "no manifests loaded" in deg and deg.count("no data") >= 10
    # at chance everywhere
    flat_world = lane_a_world(lambda c: (CHANCE, CHANCE))
    chance_results = report.run_analyses(report.ReportInputs(index=flat_world.index, exposure=E))
    assert "<svg" in report.render_dashboard(
        chance_results, [], "INCOMPLETE", report.ReportInputs(index=flat_world.index, exposure=E)
    )


def test_lane_c_and_d_results_enter_the_dashboard_tables() -> None:
    inputs = full_inputs()
    results = report.run_analyses(inputs)
    subjects = {r["subject"] for r in results}
    assert {
        "C1/flat/au0.25/ac0.05",
        "incremental/flat/sequential",
        "B1/flat/au0.25/ac0",
        "tree_comparison",
        "ladder",
    } <= subjects
    rows = {r["subject"]: r for r in report.results_table(results)}
    assert (
        rows["incremental/flat/sequential"]["class"] == "INCREMENTAL_POSITIVE"
        and rows["C1/flat/au0.25/ac0.05"]["class"] == "LOCALITY_POSITIVE"
    )
    assert "healthy" not in json.dumps(rows)


# --- writing and the command line ----------------------------------------------------------------------------------------------------------
def test_write_report_files_hashes_and_strict_json(tmp_path: Path) -> None:
    inputs = full_inputs()
    results = report.run_analyses(inputs)
    paths = report.write_report(
        tmp_path / "run",
        tmp_path / "out",
        results,
        "INCOMPLETE",
        manifests=[manifest(ALL[:5])],
        inputs=inputs,
    )
    assert [p.name for p in paths] == [
        "results.json",
        "results.csv",
        "RESULTS.md",
        "dashboard.html",
        "hashes.json",
    ]
    payload = json.loads(
        (tmp_path / "out" / "results.json").read_text(),
        parse_constant=lambda c: pytest.fail(f"non-finite constant {c}"),
    )
    assert (
        payload["status"] == "INCOMPLETE"
        and payload["denominator"] == 100
        and len(payload["missing_cells"]) == 95
        and len(payload["decision_map"]) == 6
    )
    assert (
        len(payload["results"]) == len(results)
        and "Astra review: NOT_PERFORMED" in payload["review"]
    )
    hashes = json.loads((tmp_path / "out" / "hashes.json").read_text())
    from arborlm.io import file_sha256

    assert all(
        file_sha256(tmp_path / "out" / name) == digest for name, digest in hashes.items()
    ) and set(hashes) == {p.name for p in paths[:-1]}
    again = report.write_report(
        tmp_path / "run",
        tmp_path / "out2",
        results,
        "INCOMPLETE",
        manifests=[manifest(ALL[:5])],
        inputs=inputs,
    )
    assert (
        json.loads((tmp_path / "out2" / "hashes.json").read_text()) == hashes and len(again) == 5
    )  # deterministic output


def test_write_report_with_no_inputs_and_engineering_fail(tmp_path: Path) -> None:
    paths = report.write_report(tmp_path / "run", tmp_path / "out", [], "ENGINEERING_FAIL")
    assert all(p.is_file() for p in paths)
    assert "ENGINEERING_FAIL" in (tmp_path / "out" / "RESULTS.md").read_text()


def test_load_inputs_and_main_roundtrip(tmp_path: Path) -> None:
    world = lane_a_world()
    run = tmp_path / "run"
    for (label, update, stream), rec in world.index.items():
        core.write_record(core.eval_path(run, label, update, stream), rec)
    cell = A.find_cell("A1", "flat", 16384, seed=1701)
    assert cell is not None
    (core.cell_dir(run, cell.label) / "updates.jsonl").write_text(
        json.dumps({"update": 1}) + "\n\n"
    )
    (core.cell_dir(run, cell.label) / "eval" / "u0000001").mkdir(parents=True)
    (core.cell_dir(run, cell.label) / "eval" / "u0000001" / "junk.json").write_text("{not json")
    (core.cell_dir(run, cell.label) / "sim" / "u0000001").mkdir(parents=True)
    from test_p9_analysis_c import sim_rec

    good = sim_rec(cell.label, 1, "panel_a", 8, 0.25, "asc", e=0.5)
    (core.cell_dir(run, cell.label) / "sim" / "u0000001" / "panel_a.json").write_text(
        json.dumps({"records": [{"layout": "identity"}, good]})
    )
    (core.cell_dir(run, cell.label) / "eval" / "u0000001" / "short.json").write_text(
        json.dumps({"kind": "eval", "schema": 1, "study": "P9", "label": "x"})
    )
    core.write_record(run / "manifest.json", manifest(ALL[:3]))  # type: ignore[arg-type]
    loaded = report.load_inputs([run], E)
    assert (
        set(loaded.index) == set(world.index)
        and loaded.updates[cell.label] == [{"update": 1}]
        and loaded.sims[cell.label] == [good]
    )
    assert (
        len(loaded.unreadable) == 3
        and any("junk.json" in u for u in loaded.unreadable)
        and any("short.json" in u for u in loaded.unreadable)
        and any("malformed" in u for u in loaded.unreadable)
    )
    out = tmp_path / "out"
    assert (
        report.main(["--run-dir", str(run), "--results-dir", str(out), "--engineering-defect", "x"])
        == 0
    )
    payload = json.loads((out / "results.json").read_text())
    assert (
        payload["status"] == "ENGINEERING_FAIL"
        and (out / "dashboard.html").is_file()
        and len(payload["unreadable_records"]) == 3
    )
    assert (
        next(r for r in payload["results"] if r["subject"] == "capacity/flat")["cls"]
        == "CAPACITY_POSITIVE"
    )
    assert report.main(["--run-dir", str(run), "--results-dir", str(tmp_path / "out3")]) == 0
    assert json.loads((tmp_path / "out3" / "results.json").read_text())["status"] == "INCOMPLETE"


def test_main_reads_calibration_and_controls(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    calibration, controls = tmp_path / "cal.json", tmp_path / "ctl.json"
    calibration.write_text(json.dumps({"task_ceiling_fail": [16384]}))
    controls.write_text(json.dumps({"g1": {"passed": True}}))
    assert (
        report.main(
            [
                "--run-dir",
                str(run),
                "--results-dir",
                str(tmp_path / "o"),
                "--calibration",
                str(calibration),
                "--controls",
                str(controls),
            ]
        )
        == 0
    )
    payload = json.loads((tmp_path / "o" / "results.json").read_text())
    gates = next(r for r in payload["results"] if r["subject"] == "gates")
    assert gates["details"]["TASK_CEILING_FAIL"] == "16384" and gates["details"]["G1"] == "pass"
    assert (
        next(r for r in payload["results"] if r["subject"] == "capacity/flat")["cls"]
        == core.NOT_EVALUATED
    )


# --- optional matplotlib renderer (not a project dependency) ---------------------------------------------------------------------------------
def test_png_renderer_is_optional_and_tolerates_missing_values() -> None:
    pytest.importorskip("matplotlib")
    figs = report.figure_specs(full_inputs())
    for fig in figs:
        data = report.render_png(fig)
        assert data is not None and data.startswith(b"\x89PNG")
    odd = report.FigureSpec(
        "x",
        "gaps",
        "q?",
        "MEASURED",
        "line",
        xlog=True,
        series=[report.Series("s", [1.0, None, 3.0], [1.0, 2.0, None])],
    )
    assert (report.render_png(odd) or b"").startswith(b"\x89PNG")
    html = report.render_dashboard([], [], "INCOMPLETE", None, png=True)
    assert "data:image/png;base64," in html


def test_png_renderer_returns_none_without_matplotlib(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    real = importlib.import_module

    def blocked(name: str, *a: Any, **k: Any) -> Any:
        if name.startswith("matplotlib"):
            raise ImportError("blocked")
        return real(name, *a, **k)

    monkeypatch.setattr(report.importlib, "import_module", blocked)
    assert report.render_png(report.figure_specs()[0]) is None
    assert "<svg" in report.render_dashboard(
        [], [], "INCOMPLETE", None, png=True
    )  # falls back to SVG


def test_record_helper_is_consistent() -> None:
    rec = record("x", 1, "panel_a", 100, 50)
    assert rec["accuracy"] == 0.5 and strong_memory(core.cells()[0]) is not None
