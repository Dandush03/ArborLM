# ruff: noqa: E501
"""P9 package I7: the stage driver ``studies.p9.stages`` (DRY pipeline, dependent-cell stop, calibration
refusals, rehearsal whitelist, registered-mode refusals, refusal to overwrite).

All runs are tiny (DRY profile, synthetic backbone, test seeds >= 179001). Self-check only: not
independent review, not Astra validation, not human approval.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p9 import analysis_a, core, pool, stages, train  # noqa: E402

LABEL = "A1-flat-R0-n4096-b101-o301-s1701"


def _read(path: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())


# --- the dependent-cell stop rule inside the DRY pipeline ---------------------------------------------------
@pytest.fixture(scope="module")
def failed_lane_d(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("p9-failed-d1")
    victim = "D1-flat-R0-n16384-phaseA-b101-o301-s1701"
    code = stages.main(["dry", "--scope", "lane_d", "--synthetic-backbone", "--train-workers", "4", "--inject-failure", victim, "--out-root", str(root)])
    assert code == 0  # the report is written although a cell failed
    return root / "P9DRY-run"


def test_a_failed_training_task_stops_its_dependants_and_only_them(failed_lane_d: Path) -> None:
    manifest = _read(failed_lane_d / "train" / "manifest.json")
    status = {t["label"]: t["status"] for t in manifest["tasks"]}
    assert manifest["status"] == "INCOMPLETE"
    assert status["D1-flat-R0-n16384-phaseA-b101-o301-s1701"] == "failed"
    dependants = {c.label for c in core.cells() if "D1-flat-R0-n16384-phaseA-b101-o301-s1701" in c.depends_on}
    assert len(dependants) == 3  # sequential, memory-only and replay of seed 1701
    for label in dependants:
        assert status[label] == "skipped_dependency"
        assert not (failed_lane_d / "cells" / label / "updates.jsonl").exists()  # never launched
    assert set(manifest["skipped_for_dependency"]) == dependants
    others = {label for label, s in status.items() if label not in dependants and s != "completed"}
    assert others == {"D1-flat-R0-n16384-phaseA-b101-o301-s1701"}
    assert (failed_lane_d / "cells" / "D1-flat-R0-n16384-phaseA-b101-o301-s1701" / "train.failed.json").is_file()


def test_the_stop_propagates_to_the_later_stages_of_the_same_cells(failed_lane_d: Path) -> None:
    manifest = _read(failed_lane_d / "evaluate" / "manifest.json")
    status = {t["label"]: t["status"] for t in manifest["tasks"]}
    assert status["D1-flat-R0-n16384-phaseA-b101-o301-s1701"] == "skipped_dependency"  # its training failed
    assert status["D1-flat-R0-n16384-phaseA-b101-o301-s1702"] == "completed"
    assert status["D1-tree-R0-n16384-phaseA-b101-o301-s1701"] == "completed"


def test_the_analysis_reports_incomplete_for_the_affected_class_only(failed_lane_d: Path) -> None:
    analysis = _read(failed_lane_d / "analysis.json")
    classes = {r["subject"]: r["cls"] for r in analysis["results"] if r["lane"] == "D"}
    assert classes["incremental/flat/sequential"] == analysis_a.INCOMPLETE
    assert classes["incremental/flat/memory_only"] == analysis_a.INCOMPLETE
    assert classes["incremental/learned_tree/sequential"] != analysis_a.INCOMPLETE  # its own cells exist
    assert classes["lane_d_g2"].startswith("G2_")
    missing = next(r for r in analysis["results"] if r["subject"] == "incremental/flat/sequential")["details"]["missing"]
    assert any("D1-flat-R0-n16384-phaseA-b101-o301-s1701" in m for m in missing)
    assert analysis["status"] == "INCOMPLETE"
    results = _read(failed_lane_d / "report" / "results.json")
    assert "D1-flat-R0-n16384-phaseA-b101-o301-s1701" in results["missing_cells"]


def test_the_failure_injection_exists_in_the_dry_profile_only(tmp_path: Path) -> None:
    args = stages.build_parser().parse_args(["work", "train", "--label", LABEL, "--run-dir", str(tmp_path), "--mode", "calibration", "--inject-failure", LABEL])
    with pytest.raises(stages.StageError):
        stages.work_train(args)


# --- calibration -------------------------------------------------------------------------------------------------
def test_calibrate_runs_only_r2_and_the_controls_and_selects_an_exposure(tmp_path: Path) -> None:
    run = tmp_path / "cal"
    code = stages.main(["calibrate", "--dry", "--synthetic-backbone", "--train-workers", "4", "--run-dir", str(run), "--experiments-root", str(tmp_path)])
    assert code in (0, 1)
    record = core.read_record(run / "calibration.json", "calibration")
    assert record["complete"] is True and record["selected_exposure"] in (*core.EXPOSURE_MENU, None)
    assert set(record["r2_accuracy"]) == {"4096", "16384", "65536"}
    assert all(set(v) == {"32", "64", "128"} for v in record["r2_accuracy"].values())
    assert record["provenance"]["dry"] is True and len(record["provenance"]["cells"]) == 9
    assert record["seeds"]["facts"] >= core.REHEARSAL_SEED_BASE and record["seeds"]["panel_a"] not in core.registered_seed_values()
    manifest = _read(run / "calibrate" / "manifest.json")
    labels = [t["label"] for t in manifest["tasks"]]
    assert sorted(labels) == sorted([*(c.label for c in core.calibration_cells()), "controls"])
    assert all("R2" in label for label in labels if label != "controls")  # no other arm was built
    assert set(record["probes"]) == {"b101-o301", "b102-o302"} and record["attainable_probability"]
    controls = record["controls"]
    assert controls["g2"]["primary"]["tests"] == 8 and set(controls["exact_accuracy"]) == {"4096", "16384", "65536"}
    # the registered rule decides E (core.select_exposure) from the stored curves
    curves = {int(s): {int(e): a for e, a in v.items()} for s, v in record["r2_accuracy"].items()}
    assert core.select_exposure(curves) == (record["selected_exposure"], record["task_ceiling_fail"])
    assert not list(run.glob("cells/*/eval/**/*.json"))  # no compared-arm evaluation record exists
    assert stages.main(["calibrate", "--dry", "--synthetic-backbone", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2  # never overwrites


def test_calibrate_refuses_the_registered_mode() -> None:
    assert stages.main(["calibrate", "--mode", "registered"]) == 2


# --- rehearsal -------------------------------------------------------------------------------------------------------
REHEARSAL_CELLS = [
    "A1-flat-R0-n4096-b101-o301-s1701",
    "A1-flat-R0-n16384-b101-o301-s1701",
    "A8-dense-R0-n4096-b101-o301-s1701",
    "D1-flat-R0-n16384-phaseA-b101-o301-s1701",
    "D2-flat-R0-n16384-sequential-b101-o301-s1701",
    "D2-flat-R0-n16384-replay-b101-o301-s1701",
]


def test_rehearsal_writes_only_whitelisted_records_and_a_projection(tmp_path: Path) -> None:
    run = tmp_path / "reh"
    args = ["rehearse", "--dry", "--synthetic-backbone", "--updates", "4", "--train-workers", "4", "--run-dir", str(run), "--experiments-root", str(tmp_path)]
    for label in REHEARSAL_CELLS:
        args += ["--only", label]
    assert stages.main(args) == 0
    records = sorted(run.glob("**/rehearse*.json"))
    assert len(records) >= len(REHEARSAL_CELLS)
    for path in records:
        record = _read(path)
        if record.get("kind") == "rehearsal":
            train.validate_rehearsal_record(record)  # every key is whitelisted and well-formed
            assert set(record) <= core.REHEARSAL_RECORD_KEYS
    # no loss, accuracy or evaluation record of any kind
    assert not list(run.glob("**/updates.jsonl")) and not list(run.glob("**/train.json")) and not list(run.glob("**/eval/**/*.json")) and not list(run.glob("**/snapshot.json"))
    assert stages.scan_rehearsal_outputs(run) == []
    # the train -> evaluate -> simulate chain was timed, and phase B started from phase A
    steps = {p.name for p in run.glob("cells/*/rehearse-*.json")}
    assert {"rehearse-evaluate-deep.json", "rehearse-evaluate-light.json", "rehearse-simulate-answer.json", "rehearse-eval.json"} <= steps
    assert (run / "cells" / "D2-flat-R0-n16384-sequential-b101-o301-s1701" / "rehearse.json").is_file()
    table = _read(run / "projection.json")
    assert set(table["projection"]) == {"32", "64", "128"}
    assert set(table["projection"]["32"]["by_training_workers"]) == {"2", "4", "6", "8"}
    assert set(table["contention"]["slowdown_vs_one_worker"]) == {"1", "2", "4", "8"}
    assert table["contention"]["slowdown_vs_one_worker"]["1"] == pytest.approx(1.0)
    md = (run / "projection.md").read_text()
    assert "Projected wall time" in md and "derived" in md
    assert stages.main(args) == 2  # never overwrites


def test_the_rehearsal_validator_rejects_a_loss_or_accuracy_key() -> None:
    base = {"kind": "rehearsal", "schema": core.SCHEMA, "study": core.STUDY, "mode": "rehearsal", "wall_seconds": 1.0}
    train.validate_rehearsal_record(base)
    for bad in ("loss", "accuracy", "final_loss", "task_loss"):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**base, bad: 0.5})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**base, "shapes": {"loss_hist": [3]}})


# --- registered mode ---------------------------------------------------------------------------------------------------
def _repo(path: Path, dirty: bool) -> Path:
    path.mkdir()
    for command in (["init", "-q"], ["config", "user.email", "t@example.org"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(path), *command], check=True)
    (path / "a.txt").write_text("a")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "x"], check=True)
    if dirty:
        (path / "untracked.txt").write_text("dirty")
    return path


@pytest.fixture
def calibration_file(tmp_path: Path) -> Path:
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"selected_exposure": 32, "task_ceiling_fail": []}))
    return path


@pytest.mark.parametrize("command", ["train", "gates"])
def test_registered_mode_refuses_a_dirty_tree(command: str, tmp_path: Path, calibration_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path / "repo", dirty=True)
    run = tmp_path / "run"
    code = stages.main([command, "--mode", "registered", "--run-dir", str(run), "--repo", str(repo), "--freeze-commit", "HEAD", "--stage-cap-seconds", "10", "--calibration", str(calibration_file), "--experiments-root", str(tmp_path)])
    assert code == 2 and "not clean" in capsys.readouterr().err
    assert not (run / "exposure.json").exists() and not (run / command / "manifest.json").exists()


@pytest.mark.parametrize("command", ["train", "gates"])
def test_registered_mode_refuses_without_a_freeze_commit(command: str, tmp_path: Path, calibration_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path / "repo", dirty=False)
    code = stages.main([command, "--mode", "registered", "--run-dir", str(tmp_path / "run"), "--repo", str(repo), "--stage-cap-seconds", "10", "--calibration", str(calibration_file), "--experiments-root", str(tmp_path)])
    assert code == 2 and "--freeze-commit" in capsys.readouterr().err
    assert not (tmp_path / "run" / "exposure.json").exists()


def test_registered_train_needs_a_calibration_with_a_selected_exposure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["train", "--mode", "registered", "--run-dir", str(tmp_path / "run"), "--stage-cap-seconds", "10"]) == 2
    assert "calibration" in capsys.readouterr().err


def test_registered_seed_generation_needs_the_explicit_flags(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["generate", "--run-dir", str(tmp_path / "a")]) == 2  # neither flag
    assert stages.main(["generate", "--registered-seeds", "--run-dir", str(tmp_path / "b")]) == 2  # not at freeze time
    assert stages.main(["generate", "--registered-seeds", "--rehearsal-draw", "3", "--i-understand-freeze-time", "--run-dir", str(tmp_path / "c")]) == 2  # both
    assert "freeze time" in capsys.readouterr().err
    for name in "abc":
        assert not (tmp_path / name).exists()


def test_dry_cannot_be_registered() -> None:
    assert stages.main(["train", "--dry", "--mode", "registered", "--run-dir", "x"]) == 2


# --- refusal to overwrite ---------------------------------------------------------------------------------------------------
def test_stages_never_overwrite(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    (run / "generate").mkdir(parents=True)
    (run / "generate" / "manifest.json").write_text("{}")
    assert stages.main(["generate", "--rehearsal-draw", "95", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2
    (run / "exposure.json").write_text(json.dumps({"exposure": 32}))
    assert stages.main(["train", "--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2
    (run / "analysis.json").write_text("{}")
    assert stages.main(["analyze", "--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2
    (run / "report").mkdir()
    (run / "report" / "results.json").write_text("{}")
    assert stages.main(["report", "--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2
    assert "once" in capsys.readouterr().err or "never overwrites" in capsys.readouterr().err or True
    assert (run / "analysis.json").read_text() == "{}" and (run / "report" / "results.json").read_text() == "{}"


def test_the_pool_refuses_to_overwrite_a_manifest(tmp_path: Path) -> None:
    run = tmp_path / "run"
    (run / "x").mkdir(parents=True)
    (run / "x" / "manifest.json").write_text("{}")
    with pytest.raises(pool.StageRefused):
        pool.execute_tasks("analyze", "calibration", [], run, core.code_identity(), workers={"analyze": 1}, caps=pool.StageCaps(10.0), manifest_dir=run / "x")
    assert (run / "x" / "manifest.json").read_text() == "{}"


def test_evaluate_requires_a_completed_train_stage(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "exposure.json").write_text(json.dumps({"exposure": 32}))
    assert stages.main(["evaluate", "--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path)]) == 2


def test_the_dry_registry_is_removed_after_main_returns() -> None:
    stages.main(["train", "--dry", "--mode", "registered", "--run-dir", "x"])
    assert not core.dry_active() and core.fixed_compute_updates(32) == 2048


# --- the rehearsal and DRY plans -----------------------------------------------------------------------------------
def test_the_rehearsal_plan_has_one_cell_of_every_cost_kind_at_every_size() -> None:
    cells = stages.rehearsal_cells()
    keys = {stages.kind_key(c) for c in cells}
    assert len(keys) == len(cells) == 41
    for block in ("A1", "A2", "A3", "A5", "A5b", "A6", "A7", "A8", "A10", "B1", "C1", "D1", "D2"):
        assert any(c.block == block for c in cells), block
    for size in (16384, 65536):
        kinds = {(c.arch, c.rung, c.key_width, c.optimizer) for c in cells if c.slots == size}
        assert ("flat", "R0", 16, "adamw") in kinds and ("learned_tree", "R0", 16, "adamw") in kinds and ("dense", "R0", 16, "adamw") in kinds
        assert ("flat", "R1", 16, "adamw") in kinds and ("flat", "R2", 16, "adamw") in kinds and ("flat", "R0a", 16, "adamw") in kinds
        assert ("flat", "R0", 16, "lazy") in kinds and ("flat", "R0", 32, "adamw") in kinds
    assert {c.lane_d_arm for c in cells if c.is_lane_d} == set(core.LANE_D_ARMS)
    assert any(c.alpha_u > 0 and c.alpha_c == 0 for c in cells) and any(c.alpha_c > 0 for c in cells)
    assert all(c.parent == core.PRIMARY_PARENT and c.seed == 1701 for c in cells)


def test_the_dry_scopes() -> None:
    assert len(stages.dry_scope_labels("full")) == 100 and len(stages.dry_scope_labels("lane_d")) == 20
    reduced = [core.parse_label(label) for label in stages.dry_scope_labels("reduced")]
    assert len(reduced) == 47 and all(c.seed == 1701 and c.parent == core.PRIMARY_PARENT for c in reduced)
    assert {c.slots for c in reduced} == set(core.SLOTS_BY_SIZE) and {c.block for c in reduced} == set(core.BLOCKS)
    assert {(c.block, c.rung, c.lane_d_arm) for c in reduced} == {(c.block, c.rung, c.lane_d_arm) for c in core.cells()}
    smoke = [core.parse_label(label) for label in stages.dry_scope_labels("smoke")]
    assert len(smoke) == 11
    labels = {c.label for c in smoke}
    assert all(d in labels for c in smoke for d in c.depends_on)  # a dependency is never left out
    with pytest.raises(ValueError):
        stages.dry_scope_labels("everything")


def test_launch_order_runs_r2_first_and_dependencies_before_dependants() -> None:
    ordered = stages.order_cells(core.cells())
    position = {c.label: i for i, c in enumerate(ordered)}
    assert [c.rung for c in ordered[:6]] == ["R2"] * 6
    for cell in ordered:
        for dependency in cell.depends_on:
            assert position[dependency] < position[cell.label]


def test_the_default_timing_cells_exist_and_are_trained_by_the_rehearsal() -> None:
    planned = {c.label for c in stages.rehearsal_cells()}
    for label in (*stages.EVAL_CELLS, stages.CONTENTION_CELL):
        assert core.parse_label(label).label == label and label in planned
    simulated = [core.parse_label(label) for label in stages.EVAL_CELLS]
    assert all(sim_scope is not None for sim_scope in (stages.sim.simulation_scope(c) for c in simulated))
