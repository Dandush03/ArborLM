# ruff: noqa: E501
"""P9II stages: guards (calibration, modes and seeds, freeze, ledgers), the draw plan, the stage gates, the calibration finalizer, the gates at real size on test
seeds, and the DRY stage end to end (generate, calibrate, gates, rehearse, Stage 1, the Stage 1 gate, Stage 2, the Stage 3 gate, Stage 3, analysis, report) at tiny
synthetic sizes. Nothing here uses a verified backbone, a calibration or rehearsal draw or a registered seed. Self-check only: not independent review, not Astra
validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p9 import controls, pool  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9ii import budget, core, gates, stages, train  # noqa: E402
from studies.p9ii import classes as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def parse(*argv: str) -> Any:
    return stages.build_parser().parse_args(list(argv))


# --- guards ---------------------------------------------------------------------------------------------------------------------------
def test_calibration_guard_allows_only_the_22_calibration_cells() -> None:
    for cell in core.calibration_cells():
        stages.calibration_guard(cell)
    for cell in core.stage1_cells():
        with pytest.raises(stages.CalibrationRefused):
            stages.calibration_guard(cell)
    for bad in (core.make_cell("A0", 4096), core.make_cell("A1", 4096, 0, 3, 0, 0.5), core.make_cell("A0", 4096, 0, 5, 0), core.make_cell("A6", 16384, 0, 3, 0)):
        with pytest.raises(stages.CalibrationRefused):
            stages.calibration_guard(bad)


def test_calibrate_worker_refuses_other_cells_before_building_anything(tmp_path: Path) -> None:
    for label in ("S1-A0-n4096-d01-j0", "TEST-S1-A0-n4096-d01-j0", "CAL-A0-n4096-d5-j0", "CAL-A1-v0.5-n4096-d3-j0"):
        code = stages.main(["work", "calibrate-cell", "--labels", label, "--run-dir", str(tmp_path), "--mode", "calibration", "--dry"])
        assert code == 2
    assert not list(tmp_path.rglob("*"))


def test_seed_sets_follow_the_mode() -> None:
    assert stages.seeds_named(parse("train", "--mode", "registered", "--draw", "3")).facts == 190201
    assert stages.seeds_named(parse("train", "--mode", "registered", "--reserve", "2")).facts == 191501
    assert stages.seeds_named(parse("train", "--mode", "calibration", "--draw", "3")).facts == 179301
    assert stages.seeds_named(parse("train", "--mode", "calibration", "--draw", "4")).facts == 179401
    assert stages.seeds_named(parse("train", "--mode", "rehearsal")).facts == 179501
    assert stages.seeds_named(parse("train", "--mode", "calibration", "--dry")).facts == 910001
    for bad in (("--mode", "registered", "--dry"), ("--mode", "registered", "--synthetic-backbone")):
        with pytest.raises(pool.StageRefused):
            stages.seeds_named(parse("train", *bad))
    with pytest.raises(ValueError):
        stages.seeds_named(parse("train", "--mode", "calibration", "--draw", "5"))
    with pytest.raises(ValueError):
        stages.seeds_named(parse("train", "--mode", "registered", "--draw", "15"))
    with pytest.raises(ValueError):
        core.check_seed_set("rehearsal", stages.seeds_named(parse("train", "--mode", "calibration", "--draw", "3")).name)
    ns = core.seed_namespaces()
    assert stages.seeds_named(parse("train", "--mode", "calibration", "--draw", "3")).facts in ns["calibration_data_3"]


def test_registered_mode_refuses_without_freeze_plan_or_commit(tmp_path: Path) -> None:
    assert stages.main(["registered", "stage1", "--run-dir", str(tmp_path), "--repo", str(tmp_path)]) == 2  # no freeze commit
    assert stages.main(["registered", "stage1", "--run-dir", str(tmp_path), "--repo", str(tmp_path), "--freeze-commit", "deadbeef"]) == 2  # not a commit
    with pytest.raises(SystemExit):
        stages.main(["registered", "stage9", "--run-dir", str(tmp_path)])
    with pytest.raises(pool.StageRefused, match="no freeze plan"):
        stages.load_plan(tmp_path)
    assert stages.main(["train", "--dry", "--mode", "registered", "--run-dir", str(tmp_path)]) == 2
    assert stages.main(["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp_path)]) == 2  # needs --i-understand-freeze-time


def test_registered_driver_checks_the_frozen_plan_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stages, "check_preconditions", lambda *a, **k: {"commit": "x", "tree": "y"})
    repo = tmp_path / "repo"
    (repo / "studies" / "p9ii" / "freeze").mkdir(parents=True)
    assert stages.main(["registered", "stage1", "--run-dir", str(tmp_path / "run"), "--repo", str(repo), "--freeze-commit", "x"]) == 2  # no plan
    cal = tmp_path / "calibration.json"
    cal.write_text("{}")
    proj = tmp_path / "projection.json"
    proj.write_text("{}")
    plan = {"caps": {"gates": 1.0}, "calibration": {"path": str(cal), "sha256": "0" * 64}, "projection": {"path": str(proj), "sha256": "0" * 64}}
    (repo / stages.FREEZE_PLAN).write_text(json.dumps(plan))
    assert stages.main(["registered", "stage1", "--run-dir", str(tmp_path / "run"), "--repo", str(repo), "--freeze-commit", "x"]) == 2  # a record does not hash to the frozen value


def test_a_stage_refuses_when_its_budget_cannot_cover_its_cap(tmp_path: Path) -> None:
    ledger = core.Ledger(tmp_path / "P9II-ledger-A.json", "A")
    ledger.charge("calibrate", "earlier", ledger.cap_seconds - 50.0)
    code = stages.main(["calibrate", "--dry", "--run-dir", str(tmp_path / "run"), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path), "--stage-cap-seconds", "100"])
    assert code == 2 and not list((tmp_path / "run" / "calibrate").glob("*.json"))


def test_worker_argv_and_task_ids() -> None:
    ident = core.code_identity()
    argv = stages.worker_argv("train", "--labels", "x")
    task = stages.make_task("train1", "x", argv, Path("/tmp/r"), ident, Path("/tmp/r/o.json"))
    assert task.group == "train" and task.argv[1:3] == ("-m", "studies.p9ii.stages") and task.task_id == pool.task_id("train1", "x", ident)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        stages.make_task("train1", "x", ("python", "-m", "studies.p9.stages", "work", "train"), Path("/tmp/r"), ident, Path("/tmp/r/o.json"))
    assert stages.make_task("evaluate2", "x", argv, Path("/tmp/r"), ident, Path("/tmp/o")).group == "evaluate"
    assert stages.make_task("generate-p9ii-draw-1", "x", argv, Path("/tmp/r"), ident, Path("/tmp/o")).group == "analyze"


# --- the draw plan, stage cells from gate records, the calibration finalizer ---------------------------------------------------------------
def _fake_draws(run: Path, failing: set[str]) -> None:
    for name in (*core.DRAW_NAMES, *core.RESERVE_NAMES):
        folder = stages.manifest_dir(run, name)
        core.write_record(folder / "data_manifest.json", {**core.envelope("data_manifest"), "seed_set": name, "g1_passed": name not in failing})


def test_draw_plan_command_records_replacements(tmp_path: Path) -> None:
    _fake_draws(tmp_path, {"p9ii-draw-4"})
    assert stages.cmd_draw_plan(parse("draw-plan", "--run-dir", str(tmp_path))) == 0
    plan = core.read_record(tmp_path / "draw_plan.json", "draw_plan")
    assert plan["ok"] and plan["replacements"] == {"4": "p9ii-reserve-1"} and plan["seed_set_of"]["4"] == "p9ii-reserve-1"
    assert stages.seeds_named(parse("train", "--mode", "registered", "--run-dir", str(tmp_path), "--draw", "4")).facts == 191401  # the cells of draw slot 4 read the reserve
    assert stages.seeds_named(parse("train", "--mode", "registered", "--run-dir", str(tmp_path), "--draw", "5")).facts == 190401
    bad = tmp_path / "bad"
    _fake_draws(bad, {"p9ii-draw-1", "p9ii-draw-2", "p9ii-draw-3"})
    assert stages.cmd_draw_plan(parse("draw-plan", "--run-dir", str(bad))) == 1
    assert not core.read_record(bad / "draw_plan.json", "draw_plan")["ok"]


def test_later_stage_cells_come_from_the_gate_records_never_by_hand(tmp_path: Path) -> None:
    args = parse("train", "--run-dir", str(tmp_path), "--stage", "2", "--mode", "registered")
    with pytest.raises(FileNotFoundError):
        stages.stage_cells(args, 2)
    core.write_record(tmp_path / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "status": None, "advancing": ["A5-C"], "arms": ["A0", "A5-C"]})
    assert len(stages.stage_cells(args, 2)) == 24 and {c.arm for c in stages.stage_cells(args, 2)} == {"A0", "A5-C", "A6", "A7"}
    forced = parse("train", "--run-dir", str(tmp_path), "--stage", "2", "--mode", "registered", "--dry-advancing", "A2,A1")
    assert len(stages.stage_cells(forced, 2)) == 24  # outside the DRY stage the flag is ignored
    core.write_record(tmp_path / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": False, "status": "NOT RUN — SCHEDULED ARM", "selected": "A4"})
    with pytest.raises(pool.StageRefused, match="SCHEDULED ARM"):
        stages.stage_cells(parse("train", "--run-dir", str(tmp_path), "--stage", "3", "--mode", "registered"), 3)
    assert len(stages.stage_cells(parse("train", "--run-dir", str(tmp_path), "--stage", "1"), 1)) == 128
    dry = parse("train", "--run-dir", str(tmp_path), "--dry", "--dry-advancing", "A2,A1")
    assert len(stages.stage_cells(dry, 2)) == 40
    only = parse("train", "--run-dir", str(tmp_path), "--only", "S1-A0-n4096-d01-j0")
    assert [c.label for c in stages.stage_cells(only, 1)] == ["S1-A0-n4096-d01-j0"]


def test_finalize_calibration_applies_the_rule_on_calibration_records(tmp_path: Path) -> None:
    cells = core.calibration_cells()
    accuracy = {"A6": 0.99, "A0": 0.2, "A7": 0.5}
    for c in cells:
        a = accuracy.get(c.arm, 0.5)
        if c.arm == "A1":
            a = 0.8 if c.value == 1.0 else 0.4
        if c.arm == "A2":
            a = 0.6 if c.value == 1024.0 else 0.5999  # a tie within 0.02: the secondary criterion decides
        if c.arm == "A4":
            a = 0.5  # all equal: the first value listed
        if c.arm == "A5-D":
            a = 0.1
        folder = core.cell_dir(tmp_path, c.label)
        core.write_record(folder / "calibration_cell.json", {**core.envelope("calibration"), "label": c.label, "arm": c.arm, "value": c.value, "draw": c.draw, "accuracy": a, "status": "completed"})
        if c.arm == "A2":  # time to first success: 2,048 reaches the line sooner than 1,024
            line = [{"update": u, "probe_accuracy": 0.95 if (c.value == 2048.0 and u >= 64) or u >= 192 else 0.0} for u in (64, 128, 192)]
            (folder / "diagnostics.jsonl").write_text("\n".join(json.dumps(x) for x in line) + "\n")
    args = parse("calibrate", "--dry")
    path = stages.finalize_calibration(args, tmp_path, cells)
    record = core.read_record(path, "calibration")
    hyper = core.Hyper.from_json(record["hyper"])
    assert hyper.lambda_ == 1.0  # the higher minimum accuracy
    assert hyper.u_pre == 2048.0  # tie within 0.02 -> earlier median time to first success
    assert hyper.k0_fraction == 0.125  # tied everywhere, never succeeding: the first value listed
    assert hyper.mu == 0.1
    assert record["table"]["A1"]["min_accuracy"] == {"0.1": 0.4, "1.0": 0.8} and "never as results" in record["calibration_accuracy_note"]
    assert record["pipeline_check"]
    with pytest.raises(FileExistsError):
        stages.finalize_calibration(args, tmp_path, cells)


# --- the gates at real size on test seeds (the P9-I attempt-1 lesson) ---------------------------------------------------------------------------
def test_gates_run_at_real_size_on_test_seeds(tmp_path: Path) -> None:
    g = torch.Generator().manual_seed(21)
    corpus = bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())
    data = d.build_study_data(core.test_seeds(2), corpus)  # the registered sizes: 32,768 trained facts and 2,048 unseen controls
    assert data.facts.trained == 32768
    backbone = controls.synthetic_backbone()
    rows = torch.frombuffer(bytearray(corpus), dtype=torch.uint8).to(torch.int64).reshape(-1, 65)
    r = gates.run_g4_g5_g6(data, backbone, mode="rehearsal", facts=2048, restore_split=16, out_dir=tmp_path, init_seed=core.test_seeds(2).facts, rows=rows)
    assert r["g4_defects"] == [] and r["g4_passed"] and r["g5_passed"] and r["g6_passed"], r["g4_defects"]
    checks = r["checks"]
    assert checks["a0_identity"]["passed"] and checks["schedules"]["passed"] and checks["full_scores"]["passed"] and checks["determinism"]["identical"]
    assert set(checks["gradient_reach"]) == set(core.ARMS) and set(checks["restoration"]) == set(core.LEARNED_ARMS)
    assert all(v["identical"] and v["resumed_from_update"] == 16 for v in checks["restoration"].values())
    assert set(r["g5"]) == set(core.ARMS)


# --- the DRY stage end to end ------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dry_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("dry")
    code = stages.main(["dry", "--out-root", str(root), "--workers", "6", "--dry-advancing", "A5-C,A2", "--dry-selected", "A5-C"])
    summary = json.loads((root / "DRY_SUMMARY.json").read_text())
    return {"root": root, "run": Path(summary["run_dir"]), "summary": summary, "code": code}


def test_dry_runs_every_stage_and_writes_the_report(dry_run: dict[str, Any]) -> None:
    s = dry_run["summary"]
    assert dry_run["code"] == 0 and set(s["stages"].values()) == {0}
    assert set(s["stages"]) == {"generate", "calibrate", "gates", "rehearse", "stage1", "stagegate1", "stage2", "stagegate3", "stage3", "analyze", "report"}
    assert s["status"] == "COMPLETE" and s["outcome"] in C.OUTCOMES  # a tiny run measures nothing
    results = Path(s["report"]).parent
    assert {p.name for p in results.iterdir()} == {"RESULTS.md", "results.json", "classes.csv", "cells.csv"}
    text = Path(s["report"]).read_text()
    assert "DRY: tiny synthetic sizes" in text and "Astra review: NOT_PERFORMED" in text and "What must not be claimed" in text
    json.loads((results / "results.json").read_text())  # strict JSON
    assert "Outcome:" in text


def test_dry_cells_and_records_cover_the_registry(dry_run: dict[str, Any]) -> None:
    run = dry_run["run"]
    cells = sorted((run / "cells").iterdir())
    assert len(cells) == 128 + 40 + 8 and all((c / "train.json").is_file() for c in cells)
    assert len(list((run / "cells").glob("S1-*"))) == 128 and len(list((run / "cells").glob("S2-*"))) == 40 and len(list((run / "cells").glob("S3-*"))) == 8
    train_rec = core.read_record(run / "cells" / "S2-A2-n16384-d09-j0" / "train.json", "train")
    assert train_rec["matched_updates"] == 32 and train_rec["snapshots"] == [8, 32] and train_rec["schedule"]["u_pre"] == 4 and train_rec["environment"]["torch"]
    assert core.read_record(run / "cells" / "S2-A2-n16384-d09-j0" / "eval" / core.snapshot_stem(32) / "eval.json", "eval")["update"] == 32
    assert (run / "cells" / "S1-A0-n4096-d01-j0" / "diagnostics.jsonl").is_file() and (run / "cells" / "S1-A0-n4096-d01-j0" / "updates.jsonl").is_file()
    ev = core.read_record(run / "cells" / "S1-A1-n4096-d01-j0" / "eval" / core.snapshot_stem(8) / "eval.json", "eval")
    assert {"panels", "secondary", "probe", "panel_statistics", "language_modelling", "g5"} <= set(ev) and ev["g5"]["passed"]
    for stage in ("train1", "evaluate1", "train2", "evaluate2", "train3", "evaluate3", "gates", "analyze", "report"):
        manifest = core.read_record(run / stage / "manifest.json", "stage_manifest")
        assert manifest["status"] == "COMPLETE" and manifest["study"] == "P9II" and manifest["environment"]["platform"] and manifest["environment"]["threads"]


def test_dry_gates_calibration_projection_and_ledgers(dry_run: dict[str, Any]) -> None:
    run, root = dry_run["run"], dry_run["root"]
    gates_rec = core.read_record(run / "gates.json", "gates")
    assert all(gates_rec[f"{g}_passed"] is True for g in ("g1", "g2", "g4", "g5", "g6")) and gates_rec["dry"] and gates_rec["g4_defects"] == []
    cal = core.read_record(root / "P9IIDRY-calibration" / "calibration.json", "calibration")
    hyper = core.Hyper.from_json(cal["hyper"])
    assert hyper.lambda_ in (0.1, 1.0) and hyper.u_pre in (1024.0, 2048.0) and hyper.k0_fraction in (0.125, 1.0) and hyper.mu in (0.1, 1.0)
    assert len(list((root / "P9IIDRY-calibration" / "cells").iterdir())) == 22
    proj = core.read_record(root / "P9IIDRY-rehearsal" / "projection.json", "projection")
    at_4096 = [i for i in budget.rehearsal_items() if i[1] == 4096]
    assert len(proj["rates"]) == len(at_4096) == 12 and "stage2_table" not in proj and len(proj["missing_items"]) == 30 - 12  # the DRY rehearsal covers 4,096 slots only
    for item_dir in (root / "P9IIDRY-rehearsal" / "rehearsal").iterdir():
        files = {p.name for p in item_dir.rglob("*") if p.is_file()}
        assert files == {"rehearsal.json", "rehearsal_evaluate.json"}  # the whitelist: nothing else was written
        for name in files:
            train.validate_rehearsal_record(json.loads((item_dir / name).read_text()))
    a, b = core.Ledger(root / "P9II-ledger-A.json", "A"), core.Ledger(root / "P9II-ledger-B.json", "B")
    assert a.charged() > 0 and b.charged() > 0 and {e["stage"] for e in b.entries()} == {"train2", "evaluate2", "train3", "evaluate3"}
    assert "train1" in {e["stage"] for e in a.entries()} and "calibrate" in {e["stage"] for e in a.entries()}


def test_dry_stage_gate_records_and_single_computation(dry_run: dict[str, Any]) -> None:
    run = dry_run["run"]
    g1 = core.read_record(run / "stage_gate_1.json", "stage_gate")
    assert g1["after_stage"] == 1 and "classes" in g1 and g1["run"] in (True, False) and g1["environment"]["torch"]
    g3 = core.read_record(run / "stage_gate_3.json", "stage_gate")
    assert g3["after_stage"] == 2
    with pytest.raises(pool.StageRefused, match="computed once"):
        stages.cmd_stagegate(parse("stagegate", "--run-dir", str(run), "--dry", "--after", "1", "--dry-advancing", "A5-C,A2"))
    again = stages.main(["analyze", "--dry", "--run-dir", str(run), "--experiments-root", str(dry_run["root"]), "--ledger-root", str(dry_run["root"]), "--dry-advancing", "A5-C,A2", "--dry-selected", "A5-C"])
    assert again == 2  # a stage is run once and never overwritten
    analysis = core.read_record(run / "analysis.json", "analysis")
    result = analysis["result"]
    assert result["stage2"]["status"] in ("COMPLETE", "NOT_EVALUATED") and result["stage3"]["status"] == "COMPLETE"  # a tiny run: A6 is below 0.90, so the draws are NOT_EVALUATED and set(result["stage2"]["arms"]) == {"A0", "A5-C", "A2", "A1-S"}
    assert result["stage2"]["arms"]["A2"]["readout_u"]["label"].startswith("MID-SCHEDULE") and result["stage2"]["arms"]["A0"]["readout_u"]["class"] is not None
    assert "paired_against_a0" in result["stage1"]["arms"]["A5-D"] and "draw_sensitivity" in result["stage1"]["arms"]["A0"]
    write_json(run / "scratch.json", {"ok": True})
