# ruff: noqa: E501
"""P9I stages: guards (calibration, mode and seeds, freeze, ledger), the whitelisted rehearsal and the DRY
stage end to end at tiny synthetic sizes. Nothing here uses a verified backbone, a rehearsal draw or a
registered seed. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import pool  # noqa: E402
from studies.p9i import core, report, stages, train  # noqa: E402


# --- guards ---------------------------------------------------------------------------------------------------------------
def test_calibration_guard_allows_only_r1_r2_calibration_cells() -> None:
    for cell in core.calibration_cells():
        stages.calibration_guard(cell)  # the eighteen runs
    for cell in core.cells():
        with pytest.raises(stages.CalibrationRefused):
            stages.calibration_guard(cell)
    for arm in core.ARMS:
        if arm not in ("R1", "R2"):
            with pytest.raises(stages.CalibrationRefused):
                stages.calibration_guard(core.make_cell(arm, 4096))
    with pytest.raises(stages.CalibrationRefused):
        stages.calibration_guard(core.make_cell("R1", 4096))  # an R1 cell of the registered matrix is not a calibration run


def test_calibrate_worker_refuses_other_arms_before_building_anything(tmp_path: Path) -> None:
    for label in ("N-n4096-b101-o301-s1801", "BB-n16384-b101-o301-s1801", "TEST-W7-n4096-b101-o301-s1801"):
        code = stages.main(["work", "calibrate-cell", "--label", label, "--run-dir", str(tmp_path), "--mode", "calibration", "--dry"])
        assert code == 2
    assert not list(tmp_path.rglob("*"))  # nothing was created


def test_seed_sets_follow_the_mode() -> None:
    ns = core.seed_namespaces()
    parser = stages.build_parser()

    def args(*argv: str) -> Any:
        return parser.parse_args(["train", *argv])

    assert stages.seeds_for(args("--mode", "registered")).facts == 182001
    assert stages.seeds_for(args("--mode", "calibration")).facts == 179101
    assert stages.seeds_for(args("--mode", "rehearsal", "--draw", "2")).facts == 179201
    assert stages.seeds_for(args("--mode", "calibration", "--dry")).facts == 900001
    for bad in (("--mode", "rehearsal", "--draw", "1"), ("--mode", "registered", "--dry"), ("--mode", "registered", "--synthetic-backbone")):
        with pytest.raises(pool.StageRefused):
            stages.seeds_for(args(*bad))
    with pytest.raises(ValueError):
        stages.seeds_for(args("--mode", "rehearsal", "--draw", "12"))
    assert stages.seeds_for(args("--mode", "rehearsal", "--draw", "2")).facts in ns["rehearsal_data"]


def test_dry_cannot_be_registered() -> None:
    assert stages.main(["train", "--dry", "--mode", "registered", "--run-dir", "/nonexistent"]) == 2


def _repo(path: Path) -> Path:
    def git(*a: str) -> None:
        subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)

    path.mkdir()
    git("init", "-q")
    (path / "f.txt").write_text("x")
    git("add", "f.txt")
    git("commit", "-q", "-m", "c", "--no-gpg-sign")
    return path


def test_registered_stage_needs_a_clean_tree_and_a_freeze_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    assert stages.check_preconditions("calibration", repo, None) is None
    assert stages.check_preconditions("rehearsal", repo, None) is None
    with pytest.raises(pool.StageRefused, match="freeze-commit"):
        stages.check_preconditions("registered", repo, None)
    with pytest.raises(pool.StageRefused, match="not a commit"):
        stages.check_preconditions("registered", repo, "deadbeef")
    (repo / "g.txt").write_text("dirty")
    with pytest.raises(pool.StageRefused, match="not clean"):
        stages.check_preconditions("registered", repo, "HEAD")


def test_a_stage_refuses_to_start_when_the_ledger_cannot_cover_its_cap(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = core.Ledger(tmp_path / "ledger.json", cap_seconds=core.CAP_SECONDS)
    ledger.charge("calibrate", "earlier", core.CAP_SECONDS - 500.0)
    run = tmp_path / "run"
    base = ["--dry", "--mode", "calibration", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger", str(tmp_path / "ledger.json")]
    assert stages.main(["train", *base, "--stage-cap-seconds", "501"]) == 2
    assert "REFUSED" in capsys.readouterr().err
    assert not (run / "train" / "manifest.json").exists()
    assert ledger.charged() == core.CAP_SECONDS - 500.0  # a refused stage charges nothing
    with pytest.raises(pool.StageRefused):  # outside the DRY stage a cap must be given
        stages.stage_cap(stages.build_parser().parse_args(["train", "--mode", "calibration"]))


def test_task_argv_is_checked() -> None:
    ident = core.code_identity()
    with pytest.raises(ValueError):
        stages.make_task("train", "x", (sys.executable, "-m", "studies.p9.stages", "work", "train"), Path("/tmp/r"), ident, Path("/tmp/r/x.json"))
    ok = stages.make_task("train", "x", stages.worker_argv("train", "--label", "x"), Path("/tmp/r"), ident, Path("/tmp/r/x.json"))
    assert ok.argv[2] == "studies.p9i.stages" and ok.group == "train"


# --- rehearsal ----------------------------------------------------------------------------------------------------------
def test_rehearsal_stage_writes_only_whitelisted_records(tmp_path: Path) -> None:
    run = tmp_path / "rehearsal-run"
    label = "TEST-BB-n4096-b101-o301-s1801"
    code = stages.main(["rehearse", "--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger", str(tmp_path / "l.json"), "--workers", "2", "--updates", "2", "--only", label, "--only", "TEST-R1-n4096-b101-o301-s1801", "--stage-cap-seconds", "600"])
    assert code == 0
    cell = run / "cells" / label
    for name in ("rehearsal.json", "rehearsal_evaluate.json"):
        record = json.loads((cell / name).read_text())
        train.validate_rehearsal_record(record)
    text = (cell / "rehearsal.json").read_text() + (cell / "rehearsal_evaluate.json").read_text()
    assert "accuracy" not in text.lower() and "task_loss" not in text.lower()
    files = {p.name for p in cell.rglob("*") if p.is_file()}
    assert "train.json" not in files and "updates.jsonl" not in files and "eval.json" not in files and "snapshot.json" not in files
    assert json.loads((cell / "rehearsal.json").read_text())["trainable_backbone_parameters"] == 4224
    assert 0 < core.Ledger(tmp_path / "l.json").charged() < 600  # the time was charged
    manifest = core.read_record(run / "rehearse" / "manifest.json", "stage_manifest")
    assert manifest["study"] == "P9I" and manifest["status"] == "COMPLETE" and manifest["mode"] == "rehearsal"


# --- the DRY stage end to end ----------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dry(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("p9i-dry")
    code = stages.main(["dry", "--out-root", str(root), "--workers", "4"])
    summary = json.loads((root / "DRY_SUMMARY.json").read_text())
    return {"root": root, "code": code, "summary": summary, "run": Path(summary["run_dir"])}


def test_dry_runs_every_stage_end_to_end(dry: dict[str, Any]) -> None:
    assert dry["code"] == 0
    s = dry["summary"]
    assert s["stages"] == {"generate": 0, "calibrate": 0, "gates": 0, "train": 0, "evaluate": 0, "analyze": 0, "report": 0}
    assert s["status"] == "COMPLETE" and s["banner"].startswith("DRY") and len(s["cells"]) == 24
    run: Path = dry["run"]
    for stage in ("generate", "gates", "train", "evaluate", "analyze", "report"):
        manifest = core.read_record(run / stage / "manifest.json", "stage_manifest")
        assert manifest["status"] == "COMPLETE" and manifest["study"] == "P9I" and manifest["mode"] == "calibration"
    assert len(core.read_record(run / "train" / "manifest.json", "stage_manifest")["tasks"]) == 24
    assert len(core.read_record(run / "evaluate" / "manifest.json", "stage_manifest")["tasks"]) == 24
    assert core.Ledger(dry["root"] / "P9I-ledger.json").charged() == pytest.approx(s["charged_seconds"])
    assert s["charged_seconds"] > 0 and len(core.Ledger(dry["root"] / "P9I-ledger.json").entries()) >= 7


def test_dry_records_carry_the_study_code_and_test_seeds(dry: dict[str, Any]) -> None:
    run: Path = dry["run"]
    manifest = json.loads((run / "data_manifest.json").read_text())
    assert manifest["study"] == "P9I" and manifest["seed_set"] == "p9i-test-0" and manifest["dry"] is True and manifest["g1_passed"] is True
    assert min(manifest["seeds"][k] for k in ("facts", "templates", "panel_a")) >= 900001
    train_record = core.read_record(run / "cells" / "TEST-BB-n4096-b101-o301-s1801" / "train.json", "train")
    assert train_record["study"] == "P9I" and train_record["matched_updates"] == stages.DRY_UPDATES
    assert train_record["trainable_backbone_parameters"] == 4224
    gates = core.read_record(run / "gates.json", "gates")
    assert gates["g4_passed"] is True and gates["g4_defects"] == []
    assert all(v["n_against_r0a"]["logits_identical"] for v in gates["identity"])
    assert all(all(v["initial_identities"].values()) for v in gates["identity"])
    assert gates["restoration"]["N"]["identical"] and gates["restoration"]["BB"]["identical"]
    assert all(r["all_reached"] and not r["stray"] for r in gates["gradient_reach"].values())
    assert set(gates["gradient_reach"]) == set(core.ARMS)


def test_dry_calibration_runs_only_r1_and_r2_and_records_u_and_failed_sizes(dry: dict[str, Any]) -> None:
    cal_dir = dry["root"] / "P9IDRY-calibration"
    record = core.read_record(cal_dir / "calibration.json", "calibration")
    assert record["dry"] is True and "selected_updates" in record and set(record["failed_sizes"]) <= {"4096"}
    cell_dirs = sorted((cal_dir / "cells").glob("*"))
    assert len(cell_dirs) == 6 and all(p.name.startswith("CAL-R") for p in cell_dirs)
    assert record["controls"] is not None and "g2" in record["controls"]


def test_dry_analysis_and_report_files(dry: dict[str, Any]) -> None:
    run: Path = dry["run"]
    analysis = core.read_record(run / "analysis.json", "analysis")
    assert analysis["status"] == "COMPLETE" and analysis["missing_cells"] == [] and analysis["dry"] is True
    assert analysis["analysis"]["selection"]["outcome"] in ("INCONCLUSIVE", "BB", "A4", "W7", "NO_INTERFACE_SELECTED")
    out = run / "results"
    assert {p.name for p in out.iterdir()} == {"classes.csv", "cells.csv", "RESULTS.md", "results.json"}
    text = (out / "RESULTS.md").read_text()
    assert "DRY" in text and "What must not be claimed" in text and "Astra review: NOT_PERFORMED" in text
    cells = (out / "cells.csv").read_text().splitlines()
    assert len(cells) == 25 and "optimizer_state_bytes" in cells[0] and "trainable_backbone_parameters" in cells[0]
    results = json.loads((out / "results.json").read_text())
    assert len(results["cells"]) == 24 and results["banner"] is not None


def test_stages_never_overwrite_or_rerun(dry: dict[str, Any]) -> None:
    run = dry["run"]
    base = ["--dry", "--mode", "calibration", "--run-dir", str(run), "--experiments-root", str(dry["root"]), "--ledger", str(dry["root"] / "P9I-ledger.json"), "--stage-cap-seconds", "600"]
    for command in ("train", "evaluate", "gates", "analyze", "report"):
        assert stages.main([command, *base]) == 2, command
    with pytest.raises(FileExistsError):
        report.write_report(run, run / "results")
    assert stages.main(["generate", *base]) == 2


def test_report_never_describes_a_result_as_success(dry: dict[str, Any]) -> None:
    text = (dry["run"] / "results" / "RESULTS.md").read_text().lower()
    assert "speedup" not in text and "success" not in text.replace("does not", "")


def test_a_failing_cell_leaves_a_failed_record_marks_the_stage_incomplete_and_is_not_rerun(tmp_path: Path) -> None:
    run = tmp_path / "run"
    base = ["--dry", "--mode", "calibration", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger", str(tmp_path / "l.json"), "--workers", "2", "--stage-cap-seconds", "600"]
    assert stages.main(["generate", *base]) == 0
    bad, good = "TEST-N-n4096-b101-o301-s1801", "TEST-N-n4096-b101-o301-s1802"
    blocker = run / "cells" / bad / "updates.jsonl"  # the worker opens its update log exclusively and fails
    blocker.parent.mkdir(parents=True)
    blocker.write_text("pre-existing")
    assert stages.main(["train", *base, "--only", bad, "--only", good]) == 1
    manifest = core.read_record(run / "train" / "manifest.json", "stage_manifest")
    status = {t["label"]: t["status"] for t in manifest["tasks"]}
    assert manifest["status"] == "INCOMPLETE" and status == {bad: "failed", good: "completed"}
    failed = json.loads((run / "train" / f"{bad}.failed.json").read_text())
    assert failed["status"] == "failed" and "not re-run" in failed["note"]
    assert not (run / "cells" / bad / "train.json").exists() and (run / "cells" / good / "train.json").is_file()
    assert blocker.read_text() == "pre-existing"
    before = (run / "train" / "manifest.json").read_text()
    assert stages.main(["train", *base, "--only", bad, "--only", good]) == 2  # a stage is run once
    assert (run / "train" / "manifest.json").read_text() == before and blocker.read_text() == "pre-existing"
    assert stages.main(["evaluate", *base, "--only", bad, "--only", good]) == 1  # the failed cell is skipped, not re-run
    ev = {t["label"]: t["status"] for t in core.read_record(run / "evaluate" / "manifest.json", "stage_manifest")["tasks"]}
    assert ev == {bad: "skipped_dependency", good: "completed"}
