# ruff: noqa: E501
"""P9 package I7: cross-module consistency (records written by one module are read by the next).

Pure consistency checks first (no training), then one DRY pipeline run on the ``smoke`` scope (tiny sizes,
synthetic backbone, test seeds) whose real records are checked against what the analysis modules read.
Self-check only: not independent review, not Astra validation, not human approval.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p9 import (  # noqa: E402
    analysis_a,
    analysis_b,
    analysis_c,
    analysis_d,
    core,
    data,
    evaluate,
    incremental,
    pool,
    sim,
    stages,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_p9_analysis_synth as synth  # noqa: E402


# --- no training needed ------------------------------------------------------------------------------------
def test_cell_dependencies_are_the_pool_dependencies() -> None:
    cells = core.cells()
    argv = {c.label: ["python", "-m", "studies.p9.stages"] for c in cells}
    tasks = pool.plan_stage("train", cells, Path("/nonexistent-run"), core.code_identity(), argv_for=argv)
    by_label = {t.label: t for t in tasks}
    for cell in cells:
        assert by_label[cell.label].depends_on == cell.depends_on
        for dependency in cell.depends_on:
            parent = core.parse_label(dependency)
            assert (parent.block, parent.arch, parent.parent, parent.seed) == ("D1", cell.arch, cell.parent, cell.seed)
            assert cell.block == "D2" and cell.lane_d_arm != "joint"
    d2 = [c for c in cells if c.block == "D2"]
    assert sum(1 for c in d2 if c.depends_on) == 12 and all(not c.depends_on for c in d2 if c.lane_d_arm == "joint")


def test_a_failed_d1_cell_skips_exactly_its_d2_dependants() -> None:
    cells = core.cells()
    argv = {c.label: ["python", "-m", "studies.p9.stages"] for c in cells}
    tasks = pool.plan_stage("train", cells, Path("/nonexistent-run"), core.code_identity(), argv_for=argv)
    for d1 in [c for c in cells if c.block == "D1"]:
        skipped = pool.skipped_for_dependency(tasks, {d1.label})
        expected = {c.label for c in cells if d1.label in c.depends_on}
        assert skipped == expected and skipped


def test_simulation_plan_is_exactly_the_cells_whose_traces_evaluate_writes() -> None:
    plan = sim.simulation_plan()
    simulated = plan["full"] + plan["sweep_answer_only"]
    traced = [c for c in core.cells() if c.block in evaluate.TRACE_BLOCKS and c.arch != "dense" and c.rung != "R2"]
    assert {c.label for c in simulated} == {c.label for c in traced}
    assert {c.label for c in plan["not_simulated"]} == {c.label for c in core.cells()} - {c.label for c in traced}
    for cell in simulated:
        scope = sim.simulation_scope(cell)
        assert scope is not None and set(scope.trace_kinds) <= set(core.TRACE_KINDS)
        for exposure in core.EXPOSURE_MENU:  # the traced snapshot is the matched-exposure one, which exists
            assert core.updates(cell, exposure) in core.snapshots(cell, exposure)
    assert all(c.arch != "dense" for c in simulated)


def test_lane_d_stream_names_agree_between_data_and_analysis(tmp_path: Path) -> None:
    study = data.build_study_data(core.rehearsal_seeds(95), stages.SYNTHETIC_CORPUS, sizes=stages.DRY_SIZES)
    for panel in core.PANELS:
        for which in analysis_d.LANE_D_STREAM_SETS:
            assert analysis_d.lane_d_stream(panel, which) in study.streams
    assert {n for n in study.streams if n.startswith("lane_d_")} == {analysis_d.lane_d_stream(p, s) for p in core.PANELS for s in ("A", "B")}
    assert set(core.STREAM_NAMES) <= set(study.streams)
    for panel in core.PANELS:
        assert core.PANEL_STREAM[panel] in study.streams


def test_registry_lookup_follows_the_dry_profile() -> None:
    registered = analysis_a.find_cell("A1", "flat", 4096)
    assert registered is not None and registered.facts == 2048
    core.install_dry_registry()
    try:
        dry = analysis_a.find_cell("A1", "flat", 4096)
        assert dry is not None and dry.facts == core.DRY_FACTS[2048] and dry.label == registered.label
        assert core.fixed_compute_updates(32) == core.matched_updates(core.DRY_FACTS[8192], 32)
        assert len(core.cells()) == 100
    finally:
        core.uninstall_dry_registry()
    again = analysis_a.find_cell("A1", "flat", 4096)
    assert again is not None and again.facts == 2048 and core.fixed_compute_updates(32) == 2048


def test_calibration_cells_are_r2_only_and_outside_the_registry() -> None:
    cals = core.calibration_cells()
    assert len(cals) == 9 and all(c.rung == "R2" and c.label.startswith("CAL-") for c in cals)
    assert {c.label for c in cals}.isdisjoint(core.all_labels())
    assert {(c.parent, c.seed) for c in cals} == {(core.PRIMARY_PARENT, 1701), (core.PRIMARY_PARENT, 1702), (core.REPLICATE_PARENT, 1701)}
    for c in cals:
        assert core.parse_label(c.label) is c or core.parse_label(c.label) == c
        stages.calibration_guard(c)


@pytest.mark.parametrize("label", ["A1-flat-R0-n4096-b101-o301-s1701", "A2-tree-R0-n4096-b101-o301-s1701", "A8-dense-R0-n4096-b101-o301-s1701", "A5-flat-R1-n4096-b101-o301-s1701", "A5b-flat-R0a-n16384-b101-o301-s1701", "B1-flat-R0-n16384-au0p25-b101-o301-s1701", "A10-flat-R0-n4096-lazy-b101-o301-s1701"])
def test_calibration_refuses_every_arm_other_than_r2(label: str, tmp_path: Path) -> None:
    cell = core.parse_label(label)
    with pytest.raises(stages.CalibrationRefused):
        stages.calibration_guard(cell)
    args = stages.build_parser().parse_args(["work", "calibrate-train", "--label", label, "--run-dir", str(tmp_path / "run"), "--mode", "calibration", "--experiments-root", str(tmp_path)])
    with pytest.raises(stages.CalibrationRefused):
        stages.work_calibrate_train(args)
    assert stages.main(["work", "calibrate-train", "--label", label, "--run-dir", str(tmp_path / "run"), "--mode", "calibration", "--experiments-root", str(tmp_path)]) == 2
    assert not (tmp_path / "run").exists()  # nothing was built or written


def test_registered_analysis_rules_hold_on_synthetic_records_rulings_a() -> None:
    """Lead ruling (a): a missing cell inside the class's own dependency list makes it INCOMPLETE; a
    missing cell outside it only blanks the annotation that needs it."""
    world = synth.lane_a_world()
    complete = analysis_a.classify_capacity(world.index, "flat", synth.E)
    assert complete["cls"] not in (analysis_a.INCOMPLETE,)
    b102 = analysis_a.find_cell("A1", "flat", 16384, parent=core.REPLICATE_PARENT)
    assert b102 is not None
    inside = synth.lane_a_world()
    inside.drop(b102)
    assert analysis_a.classify_capacity(inside.index, "flat", synth.E)["cls"] == analysis_a.INCOMPLETE
    assert analysis_a.classify_capacity(inside.index, "learned_tree", synth.E)["cls"] != analysis_a.INCOMPLETE
    outside = synth.lane_a_world()  # no A10 / A7 / A4 / A3 cells at all: annotations only
    result = analysis_a.classify_capacity(outside.index, "flat", synth.E)
    assert result["cls"] == complete["cls"]
    assert any("not assessed" in a for a in result["annotations"])


def test_seeds_that_disagree_give_intermediate_ruling_d() -> None:
    assert analysis_b.combine_seeds(["UTILIZATION_PRESERVED", "UTILIZATION_IMPROVED"]) == core.INTERMEDIATE
    assert analysis_b.combine_seeds(["UTILIZATION_PRESERVED", "UTILIZATION_PRESERVED"]) == "UTILIZATION_PRESERVED"
    assert analysis_d._combine(["FORGETTING", "INCREMENTAL_POSITIVE"]) == core.INTERMEDIATE


# --- one DRY run on the smoke scope ------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("p9-smoke")
    code = stages.main(["dry", "--scope", "smoke", "--synthetic-backbone", "--train-workers", "4", "--out-root", str(root)])
    run = root / "P9DRY-run"
    assert code == 0, (run / "train" / "manifest.json").read_text() if (run / "train" / "manifest.json").exists() else code
    return run


def _evals(run: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted(run.glob("cells/*/eval/*/*.json"))]


def test_dry_run_completes_every_stage_and_marks_its_outputs(smoke_run: Path) -> None:
    for stage in ("generate", "gates", "train", "evaluate", "simulate", "analyze"):
        manifest = json.loads((smoke_run / stage / "manifest.json").read_text())
        assert manifest["status"] == "COMPLETE", (stage, [t for t in manifest["tasks"] if t["status"] != "completed"])
    results = json.loads((smoke_run / "report" / "results.json").read_text())
    assert results["banner"] == stages.DRY_BANNER and (smoke_run / "report" / "DRY.json").is_file()
    assert (smoke_run / "report" / "RESULTS.md").read_text().startswith("**DRY RUN")
    assert "DRY RUN" in (smoke_run / "report" / "dashboard.html").read_text()
    assert json.loads((smoke_run / "exposure.json").read_text())["dry"] is True


def test_every_eval_record_has_the_fields_the_analyses_read(smoke_run: Path) -> None:
    records = _evals(smoke_run)
    assert records
    for rec in records:
        assert analysis_a.valid_eval(rec)
        assert set(core.EvalRecord.__annotations__) <= set(rec) | {"kind", "schema", "study"}
    flat = [r for r in records if "flat-R0-n16384" in r["label"] and r["stream"] in ("panel_a", "panel_b")]
    deep = [r for r in flat if r["useful_slots"] is not None]
    assert deep
    for rec in deep:
        for key in ("entropy_effective_hard", "entropy_soft", "key_movement_without_task_grad", "key_movement_share_without"):
            assert key in rec["usage"], key
        # lead ruling (c): the specificity record states the scope it used
        assert rec["specificity"]["scope"] == evaluate.SPECIFICITY_SCOPE == "context"


def test_lane_d_streams_are_evaluated_under_the_names_analysis_d_reads(smoke_run: Path) -> None:
    names = {r["stream"] for r in _evals(smoke_run) if "D1-flat" in r["label"] or "D2-flat" in r["label"]}
    assert names == {analysis_d.lane_d_stream(p, s) for p in core.PANELS for s in ("A", "B")}


def test_sim_records_have_the_keys_and_layout_names_analysis_c_reads(smoke_run: Path) -> None:
    files = sorted(smoke_run.glob("cells/*/sim/*/*.json"))
    assert files
    seen_layouts: set[str] = set()
    for path in files:
        payload = json.loads(path.read_text())
        assert payload["status"] == "completed"
        for rec in payload["records"]:
            assert analysis_c.valid_sim(rec)
            assert rec["update"] == int(path.parent.name[1:])
            seen_layouts.add(rec["layout"].split("@")[0])
            if rec["layout"].startswith("coaccess"):
                assert rec["e_ratio"] is None or rec["e_ratio"] >= 0
            # the E convention (lead): the primary E is the actual capacity misses over the mean of the
            # three count-preserving nulls under the FREQUENCY layout; the same-layout ratio is descriptive
            mean_null = sum(rec["null_misses"]) / len(rec["null_misses"])
            if mean_null > 0:
                assert rec["e_ratio"] == pytest.approx(rec["actual_misses"] / mean_null)
            assert rec["null_layout"] == "frequency" and "e_same_layout" in rec
    assert {"coaccess", "identity", "frequency", "random_partition", "oracle_cluster"} <= seen_layouts
    assert set(analysis_c.CONTROL_LAYOUTS) >= seen_layouts - {"coaccess"}


def test_simulated_snapshot_is_the_one_analysis_c_reads(smoke_run: Path) -> None:
    exposure = 32
    with_dry = core.dry_active()
    core.install_dry_registry() if not with_dry else None
    try:
        for path in smoke_run.glob("cells/*/sim/*/*.json"):
            label = path.parts[path.parts.index("cells") + 1]
            cell = core.parse_label(label)
            assert int(path.parent.name[1:]) == analysis_c._sim_key(cell, exposure, "matched") == core.updates(cell, exposure)
    finally:
        if not with_dry:
            core.uninstall_dry_registry()


def test_controls_record_is_what_analysis_reads(smoke_run: Path) -> None:
    analysis = json.loads((smoke_run / "analysis.json").read_text())
    controls_record = analysis["controls"]
    assert controls_record["g1"]["passed"] is True and controls_record["g4"]["passed"] is True
    gates = analysis_a.task_gates({}, None, controls_record)
    assert gates["G1"] == "pass" and gates["G2"] in ("pass", "fail") and gates["G4"] == "pass"
    for stream in ("panel_a", "panel_b"):
        entry = controls_record["no_memory"][stream]
        assert "unseen" in entry and all({"correct", "facts"} <= set(v) for v in entry.values())
    for panel in "ab":
        for which in "AB":
            assert {"correct", "facts"} <= set(controls_record["no_memory"][f"lane_d_{panel}_{which}"])
    assert set(controls_record["exact_accuracy"]) == {"4096", "16384", "65536"}
    assert all(v == 1.0 for v in controls_record["exact_accuracy"].values())
    assert controls_record["exact_lane_d"] and all("changed_bytes_keys_values" in m for m in controls_record["exact_lane_d"])
    lane_d = analysis_d.lane_d_g2({}, "A", controls_record)
    assert lane_d["status"] == "pass"
    ladder = analysis_a.ladder_report({}, "A", 32, controls=controls_record)
    assert ladder["4096"]["bits:exact"] == pytest.approx(core.fano_bits_per_fact(1.0))


def test_lane_d_bytes_are_reported_both_ways(smoke_run: Path) -> None:
    analysis = json.loads((smoke_run / "analysis.json").read_text())
    measured = next(r for r in analysis["results"] if r["subject"] == "lane_d_measurements")
    rows = [r for r in measured["details"]["rows"] if r["label"] != incremental.EXACT_LABEL]
    assert rows
    for row in rows:
        assert row["changed_bytes_keys_values"] <= row["changed_bytes"]
    sequential = next(r for r in rows if "sequential" in r["label"])
    assert sequential["changed_bytes"] > sequential["changed_bytes_keys_values"] > 0  # projections and gate change too


def test_status_is_incomplete_because_the_denominator_is_never_reduced(smoke_run: Path) -> None:
    analysis = json.loads((smoke_run / "analysis.json").read_text())
    assert analysis["status"] == "INCOMPLETE" and analysis["specificity_scope"] == "context"


def test_the_analyses_find_the_real_records_they_need(smoke_run: Path) -> None:
    """Records written by train/evaluate/simulate are found by the lane B and C analysis code under the
    keys it uses (the class itself is not asserted: tiny runs learn nothing)."""
    from studies.p9 import report

    exposure = 32
    core.install_dry_registry()
    try:
        inputs = report.load_inputs([smoke_run], exposure)
        assert not inputs.unreadable
        case = analysis_a.find_cell("C1", "flat", 16384, alpha_u=0.25, alpha_c=0.05)
        ref = analysis_c.locality_reference(case)
        assert case is not None and ref is not None and analysis_b.reference_cell(case) is not None
        settings, table, missing = analysis_c._settings_for(inputs.sims, case, ref, "A", exposure, "matched")
        assert not missing and len(settings) == len(table) == 8  # 2 rho x 2 R x 2 tie rules
        assert all(row["label"] == "SIMULATED" for row in table.values())
        b1 = analysis_a.find_cell("B1", "flat", 16384, alpha_u=0.25)
        assert b1 is not None
        assert analysis_b.classify_utilization_panel(inputs.index, b1, "A", exposure) in analysis_b.UTILIZATION_CLASSES + (analysis_a.INCOMPLETE, core.NOT_EVALUATED)
        numbers = analysis_b.seed_numbers(inputs.index, b1, "A", exposure)
        assert numbers is not None
        for label in (case.label, ref.label):
            assert any(k[0] == label for k in inputs.index)
        sim_keys = {(r["layout"], r["trace_kind"]) for r in inputs.sims[ref.label]}
        assert ("coaccess@8", "answer") in sim_keys and ("identity", "all") in sim_keys
    finally:
        core.uninstall_dry_registry()


def test_calibration_seeds_of_the_two_initializations_differ() -> None:
    study = data.build_study_data(core.rehearsal_seeds(95), stages.SYNTHETIC_CORPUS, sizes=stages.DRY_SIZES)
    a, b = (c for c in core.calibration_cells() if c.slots == 4096 and c.parent == core.PRIMARY_PARENT)
    assert {a.seed, b.seed} == {1701, 1702}
    first, second = (stages.init_seed_of(c, study, "calibration") for c in (a, b))
    assert first is not None and second is not None and first != second
    assert first >= core.REHEARSAL_SEED_BASE and second not in core.registered_seed_values()
    assert stages.init_seed_of(a, study, "registered") is None


def test_registered_mode_never_uses_a_synthetic_backbone_or_the_dry_profile(tmp_path: Path) -> None:
    args = stages.build_parser().parse_args(["work", "train", "--label", "A1-flat-R0-n4096-b101-o301-s1701", "--run-dir", str(tmp_path), "--mode", "registered", "--synthetic-backbone"])
    with pytest.raises(pool.StageRefused):
        stages.study_data(args)


def test_ruling_a_holds_for_lane_b_and_lane_d_dependencies() -> None:
    """A cell missing from a class's own dependency list makes that class INCOMPLETE and no other."""
    world = synth.util_world()
    base = {r["subject"]: r["cls"] for r in analysis_b.analyze(world.index, synth.E)}
    assert all(cls != analysis_a.INCOMPLETE for cls in base.values())
    reference = analysis_a.find_cell("A1", "flat", 16384, seed=1702)
    assert reference is not None
    world.drop(reference)
    classes = {r["subject"]: r["cls"] for r in analysis_b.analyze(world.index, synth.E)}
    assert {s for s, cls in classes.items() if cls == analysis_a.INCOMPLETE} == {s for s in classes if "/flat/" in s}
    assert all(classes[s] == base[s] for s in classes if "/learned_tree/" in s)


def test_lane_d_support_overlap_is_reported_for_memory_arms(smoke_run: Path) -> None:
    analysis = json.loads((smoke_run / "analysis.json").read_text())
    measured = next(r for r in analysis["results"] if r["subject"] == "lane_d_measurements")
    sequential = [r for r in measured["details"]["rows"] if "D2-flat-R0-n16384-sequential" in r["label"]]
    assert sequential and all("support_overlap" in r for r in sequential)
    assert (smoke_run / "cells" / "D2-flat-R0-n16384-sequential-b101-o301-s1701" / "lane_d_supports.json").is_file()
    assert not (smoke_run / "cells" / "D1-flat-R0-n16384-phaseA-b101-o301-s1701" / "lane_d_supports.json").exists()
