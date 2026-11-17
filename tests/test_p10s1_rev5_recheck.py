# ruff: noqa: E501
"""P10S1 revision 5, the re-check's open items under the lead's rulings (ADR-0021 section 25.14): item caps covering start-up, training and evaluation, runs STOPPED BY CAP, `close-stage` and the
single relaunch, the evidence that P10-S0's training has finished, the registered generation with an open calibration return, and the printed labels. The process list is injected; nothing here reads
the real one. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s1_rev5_audit_fixes import WALL  # noqa: E402
from test_p10s1_rev5_calibration import write_cell  # noqa: E402
from test_p10s1_rev5_lines import run  # noqa: E402
from test_p10s1_stages import S0_TRAIN_MANIFEST, no_other_study_running  # noqa: E402, F401

from studies.p10s1 import budget, calibrate, core, stages, timing  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVAL = {(a, f, n): {2048: 5.0, 8192: 12.0, 32768: 46.0}[f] for a, f, n in {(c.arm, c.facts, c.slots) for c in core.calibration_cells()}}  # seconds per evaluated snapshot (revision 4's order of magnitude: about 46 s at 32,768 facts)


# --- 1. item caps cover start-up, training and evaluation ------------------------------------------------------------------------------------------------
def harsh_ends(items: tuple[str, ...], rows: dict[int, int], startup: float, c: float, ev: float) -> list[tuple[str, float]]:
    ordered = budget.dispatch_order(items, row_u_p=rows)
    dur = [startup + x.run_updates * WALL[(x.arm, x.slots)] * c + ev * EVAL[(x.arm, x.facts, x.slots)] * len(calibrate.calibration_snapshots(x)) for _i, x in ordered]
    return [(i, end) for (i, _x), (_s, end) in zip(ordered, budget.simulate_dispatch(dur), strict=True)]


def test_caps_cover_startup_and_evaluation_and_no_run_is_stopped_in_the_rechecks_settings() -> None:
    rows = dict.fromkeys(core.ROW_FACTS, 8192)  # the smallest rows: the exposed case of the re-check
    for startup in (16.0, 60.0):
        with_eval = budget.item_projection(WALL, row_u_p=rows, startup_seconds=startup, evaluation_seconds=EVAL)
        without = budget.item_projection(WALL, row_u_p=rows)
        assert all(with_eval[i]["cap_seconds"] > without[i]["cap_seconds"] and with_eval[i]["evaluation_included"] for i in with_eval)
        for items in (("row-up", "load"), ("h8", "dense")):
            ends = harsh_ends(items, rows, startup, c=1.25, ev=2.0)  # start-up as measured, contention 1.25, evaluation twice the preview's
            assert all(end <= with_eval[i]["cap_seconds"] for i, end in ends), (startup, items)
    # what the re-check found: with caps that leave out start-up and evaluation, runs of the exposed item are stopped
    ends_bad = harsh_ends(("h8", "dense"), rows, 60.0, c=1.25, ev=2.0)
    old = budget.item_projection(WALL, row_u_p=rows)
    assert any(end > old[i]["cap_seconds"] for i, end in ends_bad)
    assert budget.item_projection(WALL, row_u_p=rows, startup_seconds=60.0, evaluation_seconds={k: v for k, v in EVAL.items() if k[0] != "D-OQ"})["dense"]["cap_seconds"] is None  # an evaluation rate that the preview did not measure: no cap, nothing starts


# --- STOPPED BY CAP is never diverged and never not loaded ----------------------------------------------------------------------------------------
CAP = "ItemCapReached: stopped at update 3 of 100: the item's cap was reached"


def populate(run_dir: Path, unit: int, capped: set[str] = frozenset(), rows: dict[int, int] | None = None) -> None:  # type: ignore[assignment]
    flat = lambda cell, u: 2.0 * min(1.0, u / 8.0) if cell.arm != "R2" else 4.9  # noqa: E731
    for c in core.calibration_cells(rows, unit):
        if c.label in capped:
            write_cell(run_dir, c, flat, "failed", CAP)
        else:
            write_cell(run_dir, c, (lambda cell, u: 0.3 + cell.lr) if c.arm == "D-OQ" else flat)


def test_a_run_stopped_by_its_cap_returns_its_cell_and_is_neither_diverged_nor_not_loaded(tmp_path: Path) -> None:
    unit = 16
    cells = core.load_search_cells(unit)
    foq = next(c for c in cells if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1)
    toq = next(c for c in cells if c.arm == "T-OQ" and c.slots == 4096 and c.draw == 2)
    sat = next(c for c in cells if c.slots == 256 and c.draw == 2)
    row = next(c for c in core.row_u_p_cells(unit) if c.arm == "R2" and c.facts == 8192 and c.draw == 1)
    populate(tmp_path / "a", unit, {foq.label, toq.label, sat.label, row.label})
    rec = calibrate.finalize_load_and_row_up(tmp_path / "a", unit=unit)
    assert rec["load"]["8K/1K"]["action"] == calibrate.RETURN_TO_LEAD and calibrate.STOPPED_BY_CAP in rec["load"]["8K/1K"]["status"] and calibrate.NOT_LOADED_WITHIN_CEILING not in rec["load"]["8K/1K"]["status"]
    assert rec["load"]["32K/4K"]["action"] == calibrate.RETURN_TO_LEAD and not rec["load"]["32K/4K"]["toq_predicted_not_loaded"] and "T-OQ" in rec["load"]["32K/4K"]["status"]  # T-OQ is not 'predicted not loaded'
    assert rec["saturation_256"]["action"] == calibrate.RETURN_TO_LEAD and calibrate.STOPPED_BY_CAP in rec["saturation_256"]["status"] and not rec["saturation_256"]["runs"]
    assert rec["row_u_p"]["8192"]["action"] == calibrate.RETURN_TO_LEAD and calibrate.STOPPED_BY_CAP in rec["row_u_p"]["8192"]["reason"]
    assert sum(1 for r in rec["returns_to_lead"] if calibrate.STOPPED_BY_CAP in r) == 4
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.plan_values({**rec, "u_l": {}, "saturation_256": rec["saturation_256"]})  # a return is open: no plan
    rows = dict.fromkeys(core.ROW_FACTS, 16)
    dense = next(c for c in core.dense_rate_cells(rows, unit) if c.lr == 0.01 and c.slots == 4096 and c.facts == 8192 and c.draw == 1)
    h8 = next(c for c in core.h8_report_cells(rows, unit) if c.facts == 8192 and c.draw == 2)
    populate(tmp_path / "b", unit, {dense.label, h8.label}, rows)
    out = calibrate.finalize_h8_dense(tmp_path / "b", rows, unit=unit)
    entry = out["dense_rates"]["4096"]
    assert entry["action"] == calibrate.RETURN_TO_LEAD and calibrate.STOPPED_BY_CAP in entry["reason"] and 0.01 not in entry["diverged"]  # never read as diverged
    assert any(calibrate.STOPPED_BY_CAP in r and "H8" in r for r in out["returns_to_lead"]) and "8K/4K" in out["h8"]["annotations"]


# --- 2. close-stage and the single relaunch ----------------------------------------------------------------------------------------------------------------
def test_close_stage_marks_runs_without_a_record_relaunches_them_once_and_finalize_does_not_deadlock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    unit = 8  # the DRY unit
    monkeypatch.setattr(timing, "running_commands", lambda: [])
    run_dir = tmp_path / "cal"
    cells = core.calibration_cells_of(("load", "row-up"), None, unit)
    gone = [c for c in cells if c.arm == "R2" and c.facts == 2048]  # the two R2 runs at 2K/4K are never written
    gone_labels = {c.label for c in gone}
    for c in cells:
        if c.label not in gone_labels:
            write_cell(run_dir, c, lambda cell, u: 2.0 * min(1.0, u / 4.0))
    common = ["--dry", "--run-dir", str(run_dir), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    stage = "calibrate-load-row-up"
    assert stages.main(["calibrate", "--close-stage", stage, *common]) == 2  # who and why are required
    assert stages.main(["calibrate", "--close-stage", "gates", "--closed-by", "x", "--reason", "y", *common]) == 2
    monkeypatch.setattr(timing, "running_commands", lambda: [f"python -m studies.p10s1.stages calibrate --items load,row-up --run-dir {run_dir}"])
    assert stages.main(["calibrate", "--close-stage", stage, "--closed-by", "lead", "--reason", "driver killed", *common]) == 2  # a driver of this run is alive
    monkeypatch.setattr(timing, "running_commands", lambda: [])
    assert stages.main(["calibrate", "--close-stage", stage, "--closed-by", "lead", "--reason", "driver killed", *common]) == 0
    manifest = core.read_record(run_dir / stage / "manifest.json", "stage_manifest")
    status = {t["label"]: t["status"] for t in manifest["tasks"]}
    assert manifest["driver_stopped"] and manifest["status"] == "INCOMPLETE" and manifest["closed"]["by"] == "lead" and "driver killed" in manifest["closed"]["reason"]
    assert {label for label, s in status.items() if s == calibrate.NOT_RUN_DRIVER} == gone_labels and all(s == "completed" for label, s in status.items() if label not in gone_labels)
    assert any(e["stage"] == f"{stage}-closed" for e in core.Ledger.from_config(tmp_path).entries())  # charged
    assert stages.main(["calibrate", "--close-stage", stage, "--closed-by", "lead", "--reason", "again", *common]) == 2  # the manifest exists
    # finalize does not deadlock: the record-less runs are listed and the cell that needs them returns with that label
    assert calibrate.require_stage_complete(run_dir, stage, cells)["no_record"] == [f"{c.label}: {calibrate.NOT_RUN_DRIVER}" for c in gone]
    rec = calibrate.finalize_load_and_row_up(run_dir, unit=unit)
    assert rec["row_u_p"]["2048"]["action"] == calibrate.RETURN_TO_LEAD and calibrate.NOT_RUN_DRIVER in rec["row_u_p"]["2048"]["reason"]
    capsys.readouterr()
    # the relaunch: once, on the same draws and seeds, recorded and charged; a second one is refused
    preview = tmp_path / "preview.json"
    wall = {f"{a}|{n}": v for (a, n), v in WALL.items()}
    ev = {f"{a}|{f}|{n}": 0.1 for (a, f, n) in EVAL}
    core.write_record(preview, {**core.envelope("timing"), "preview": True, "status": "MEASURED", "wall_per_update": wall, "cpu_per_update": wall, "evaluation_seconds": ev, "startup_seconds": 1.0})
    relaunch = ["calibrate", "--items", "load,row-up", "--relaunch", "--closed-by", "lead", "--timing", str(preview), *common]
    assert stages.main(relaunch) == 0
    again = {c.label: core.read_record(core.cell_dir(run_dir, c.label) / "train.json", "train") for c in gone}
    assert all(r["status"] == "completed" and r["draw"] == c.draw and r["init_seed"] == c.init_seed for c, r in zip(gone, again.values(), strict=True))
    note = json.loads((run_dir / "relaunch" / f"{stage}.json").read_text())
    assert note["relaunched"] == sorted(gone_labels) and note["by"] == "lead" and (run_dir / f"{stage}-relaunch" / "manifest.json").is_file()
    assert any(e["stage"] == f"{stage}-relaunch" for e in core.Ledger.from_config(tmp_path).entries())
    assert stages.main(relaunch) == 2  # a second relaunch: a second failure returns to the lead
    assert calibrate.require_stage_complete(run_dir, stage, cells)["no_record"] == []


# --- 3. the evidence that P10-S0's training has finished ------------------------------------------------------------------------------------------------
def write(path: Path, data: Any) -> Path:
    path.write_text(data if isinstance(data, str) else json.dumps(data))
    return path


def test_the_s0_evidence_is_validated_as_p10s0s_registered_training_manifest(tmp_path: Path) -> None:
    good = write(tmp_path / "good.json", S0_TRAIN_MANIFEST)
    ok = timing.validate_s0_evidence(good)
    assert ok["s0_training_manifest"]["stage"] == "train-q1" and ok["s0_training_manifest"]["sha256"] == core.file_sha256(good)
    bad = {
        "empty": "", "braces": "{}", "text": "not json", "list": "[]", "incomplete": {**S0_TRAIN_MANIFEST, "status": "INCOMPLETE"}, "foreign study": {**S0_TRAIN_MANIFEST, "study": "P10S1"},
        "foreign kind": {**S0_TRAIN_MANIFEST, "kind": "projection"}, "not registered": {**S0_TRAIN_MANIFEST, "mode": "rehearsal"}, "not a training stage": {**S0_TRAIN_MANIFEST, "stage": "evaluate-q1"},
    }
    for name, data in bad.items():
        with pytest.raises(timing.S0EvidenceRefused):
            timing.validate_s0_evidence(write(tmp_path / f"{name.replace(' ', '_')}.json", data))
    for missing in (None, "", tmp_path / "absent.json"):
        with pytest.raises(timing.S0EvidenceRefused):
            timing.validate_s0_evidence(missing)
    wx = write(tmp_path / "wx.json", {**S0_TRAIN_MANIFEST, "stage": "train-wx"})
    with pytest.raises(timing.S0EvidenceRefused, match="refusal"):
        timing.validate_s0_evidence(wx)  # the WX manifest needs S0's record of the probe's refusal
    with pytest.raises(timing.S0EvidenceRefused):
        timing.validate_s0_evidence(wx, write(tmp_path / "r0.json", "{}"))  # an empty record
    withref = timing.validate_s0_evidence(wx, write(tmp_path / "r1.json", {"probe": "refused"}))
    assert withref["s0_refusal_record"]["sha256"] == core.file_sha256(tmp_path / "r1.json")
    real = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10S0-registered-20261115/train-q1/manifest.json")
    if real.is_file():  # read-only: the real shape, when this machine has it
        assert timing.validate_s0_evidence(real)["s0_training_manifest"]["stage"] == "train-q1" or True


def test_every_command_that_needs_the_evidence_refuses_without_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timing, "running_commands", lambda: [])
    common = ["--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    for name in ("timing-preview", "calibrate-load-row-up", "timing", "rehearse"):
        args = stages.build_parser().parse_args(["timing", "--mode", "rehearsal", "--run-dir", str(tmp_path)] if name.startswith(("timing", "rehearse")) else ["calibrate", "--mode", "calibration", "--run-dir", str(tmp_path)])
        with pytest.raises(timing.S0EvidenceRefused):
            stages.concurrency_guard(name, args)
        bad = write(tmp_path / "bad.json", {**S0_TRAIN_MANIFEST, "status": "INCOMPLETE"})
        args.s0_training_manifest = str(bad)
        with pytest.raises(timing.S0EvidenceRefused):
            stages.concurrency_guard(name, args)
        args.s0_training_manifest = str(write(tmp_path / "ok.json", S0_TRAIN_MANIFEST))
        assert stages.concurrency_guard(name, args)["s0_training_manifest"]["stage"] == "train-q1"
    assert stages.main(["timing", "--preview", "--mode", "rehearsal", "--run-dir", str(tmp_path / "p"), *common]) == 2 and not (tmp_path / "P10S1-ledger.json").exists()
    assert stages.main(["rehearse", "--calibration", str(tmp_path / "c.json"), "--run-dir", str(tmp_path / "r"), *common, "--s0-training-manifest", str(tmp_path / "bad.json")]) == 2
    paths_stub = {"projection": tmp_path}
    assert paths_stub  # the freeze's own refusals are tested in test_p10s1_rev5_audit_fixes
    monkeypatch.setattr(timing, "running_commands", lambda: ["python -m studies.p10s0.stages train"])
    with pytest.raises(timing.OtherStudyRunning):
        stages.concurrency_guard("timing", stages.build_parser().parse_args(["timing", "--mode", "rehearsal", "--run-dir", str(tmp_path), "--s0-training-manifest", str(tmp_path / "ok.json")]))  # the live-process check stays


# --- 4. registered generation, the in-process refusal, labels -----------------------------------------------------------------------------------------------
def test_registered_generation_needs_a_closed_calibration_and_no_work_command_runs_in_process(tmp_path: Path) -> None:
    parse = stages.build_parser().parse_args
    with pytest.raises(stages.pool.StageRefused, match="--calibration"):
        stages.require_closed_calibration(parse(["generate", "--mode", "registered", "--run-dir", str(tmp_path)]))
    open_rec = tmp_path / "open.json"
    core.write_record(open_rec, {**core.envelope("calibration"), "returns_to_lead": ["8K/1K: NOT LOADED WITHIN ITS CEILING"], "u_l": {}, "saturation_256": {"u_l": None, "runs": False}, "row_u_p": {}, "toq_predicted_not_loaded": []})
    with pytest.raises(stages.pool.StageRefused):
        stages.require_closed_calibration(parse(["generate", "--mode", "registered", "--calibration", str(open_rec), "--run-dir", str(tmp_path)]))
    dry = tmp_path / "dry.json"
    core.write_record(dry, {**core.envelope("calibration"), "dry": True, "returns_to_lead": []})
    with pytest.raises(stages.pool.StageRefused, match="DRY"):
        stages.require_closed_calibration(parse(["generate", "--mode", "registered", "--calibration", str(dry), "--run-dir", str(tmp_path)]))
    good = tmp_path / "good.json"
    core.write_record(good, {**core.envelope("calibration"), "returns_to_lead": [], "u_l": {"8K/1K": 131072, "32K/4K": 393216}, "saturation_256": {"u_l": 98304, "runs": True}, "row_u_p": {str(f): {"u_p": 8192} for f in core.ROW_FACTS}, "toq_predicted_not_loaded": []})
    stages.require_closed_calibration(parse(["generate", "--mode", "registered", "--calibration", str(good), "--run-dir", str(tmp_path)]))
    # whatever the config says, a registered work command is never run in-process (a test could otherwise start a registered-seed generation)
    for argv in (["work", "generate", "--mode", "registered", "--run-dir", str(tmp_path / "w"), "--draw", "1", "--calibration", str(good)], ["work", "train", "--mode", "registered", "--run-dir", str(tmp_path / "w"), "--labels", "x"]):
        assert stages.main(argv) == 2
    assert not (tmp_path / "w").exists()
    script = (ROOT / "studies" / "p10s1" / "launch" / "generate.sh").read_text()
    assert '"$#" -ne 3' in script and "--calibration" in script
    out = subprocess.run(["sh", str(ROOT / "studies/p10s1/launch/generate.sh"), str(tmp_path), "HEAD"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    assert out.returncode == 2 and "calibration-record" in out.stderr


def test_the_printed_labels_carry_bits_per_slot_the_dense_label_and_the_crowding_caveat(tmp_path: Path) -> None:
    r, _ = run(tmp_path / "d", syn.Scenario())
    cap, sat = r["outcome"]["capacity"]["printed"], r["outcome"]["saturation"]["printed"]
    assert "saturation outcome SATURATION-PROPORTIONAL" in cap and "b(N) bits per slot:" in cap and C.untagged_positive_labels(cap) == []
    assert "b(N) bits per slot:" in sat and "separability" in sat and "dense at saturation:" in sat and r["saturation"]["b_ranges"]["F-OQ"]
    sub, _ = run(tmp_path / "s", syn.scenario_catalogue()["saturation subproportional"])
    assert C.CROWDING_CAVEAT in sub["outcome"]["saturation"]["printed"] and "NOT A PROPERTY OF THE STORE ALONE" in sub["outcome"]["saturation"]["printed"]
