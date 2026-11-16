# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: the registered driver refuses every override (M1), stage order and write-once outputs are enforced and a missing gates record is never "all passed" (M2), every stage has a
deadline and a sampled memory watchdog and analysis and report time is reserved (M4, M6), every failed cell keeps its record and a replicate's other records survive an exception (M10), evaluation and
recomputation share one thread count and deterministic setting (m3). Tests on the stand-in world and test seeds only. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import budget, core, ledger, stages, train  # noqa: E402
from studies.p10s2.registry import replicate_cells  # noqa: E402

CAPS = str(core.CAPS_FILE)
GATES_OK = {**{f"G{i}": {"ok": True} for i in range(1, 10)}, "ok": True}


# --- M1: the registered driver has no override -----------------------------------------------------------------------------------------------------
def test_the_registered_parser_accepts_the_run_directory_the_freeze_commit_and_the_frozen_caps_path_only() -> None:
    parse = stages.build_parser().parse_args
    base = ["registered", "gates", "--run-dir", "x", "--freeze-commit", "c"]
    args = parse([*base, "--caps", CAPS])
    assert args.name == "gates" and args.caps == CAPS and not hasattr(args, "repo")
    for bad in (["--caps", "typed_caps.json"], ["--caps", "/tmp/stage_caps.json"], ["--caps", CAPS, "--repo", "y"], ["--caps", CAPS, "--device", "cpu"], ["--caps", CAPS, "--layer", "1"], ["--caps", CAPS, "--data-dir", "d"], ["--caps", CAPS, "--updates", "1"], ["--caps", CAPS, "--replicates", "1"]):
        with pytest.raises(SystemExit):
            parse([*base, *bad])
    with pytest.raises(SystemExit):
        parse(base)  # --caps is required: every launch script passes it


def test_a_registered_stage_refuses_when_the_code_that_runs_is_not_under_the_checked_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(core, "ROOT", tmp_path)  # a repository other than the code that runs
    monkeypatch.setattr(ledger, "study_ledger_path", lambda: tmp_path / "ledger.jsonl")
    code = stages.main(["registered", "gates", "--run-dir", str(tmp_path / "run"), "--freeze-commit", "abc", "--caps", CAPS])
    assert code == 2 and "not under the checked repository" in capsys.readouterr().err
    assert not (tmp_path / "run").exists() and not (tmp_path / "ledger.jsonl").exists()  # nothing was started, nothing was charged


def test_the_driver_asserts_the_code_location(tmp_path: Path) -> None:
    stages.check_code_location(core.ROOT)
    with pytest.raises(stages.StageRefused, match="not under the checked repository"):
        stages.check_code_location(tmp_path)


# --- M2: order, write-once, a missing gates record --------------------------------------------------------------------------------------------------
def write_stage(run: Path, name: str, status: str = "completed") -> None:
    p = stages.stage_record_path(run, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"stage": name, "status": status}))


def put_gates(run: Path, obj: dict[str, Any]) -> None:
    """Write gates.json and bind it to its stage record by hash (re-check B, m13), as the gates stage does."""
    from arborlm.io import file_sha256

    (run / "gates.json").write_text(json.dumps(obj))
    p = stages.stage_record_path(run, "gates")
    p.write_text(json.dumps({**json.loads(p.read_text()), "gates_sha256": file_sha256(run / "gates.json")}))


def test_stage_order_gates_first_and_each_stage_needs_its_predecessor(tmp_path: Path) -> None:
    run = tmp_path / "run"
    stages.require_order(run, "gates")  # the first stage needs nothing
    for name in budget.REGISTERED_STAGES[1:]:
        with pytest.raises(stages.StageRefused, match="requires the completion record"):
            stages.require_order(run, name)
    write_stage(run, "gates")
    with pytest.raises(stages.StageRefused, match="already has a record"):
        stages.require_order(run, "gates")  # a stage is run once and never re-run with changed settings
    with pytest.raises(stages.StageRefused, match="no gates record"):
        stages.require_order(run, "train")  # a missing gates record is never read as all gates passed
    put_gates(run, {**GATES_OK, "G5": {"ok": False}, "ok": False})
    with pytest.raises(stages.StageRefused, match="did not pass"):
        stages.require_order(run, "train")  # a failed gate stops the run
    put_gates(run, {k: v for k, v in GATES_OK.items() if k != "G9"})
    with pytest.raises(stages.StageRefused, match="did not pass"):
        stages.require_order(run, "train")  # a gate with no record is not a passed gate
    put_gates(run, GATES_OK)
    stages.require_order(run, "train")
    write_stage(run, "train", "failed")
    with pytest.raises(stages.StageRefused, match="ended with status 'failed'"):
        stages.require_order(run, "evaluate")  # nothing runs after a failed stage
    stages.stage_record_path(run, "train").unlink()
    write_stage(run, "train", "stopped")
    stages.require_order(run, "evaluate")  # a cap-stopped stage is followed by the next (the label becomes INCOMPLETE)


def test_stage_outputs_are_write_once(tmp_path: Path) -> None:
    p = tmp_path / "x" / "out.json"
    stages.record(p, {"a": 1})
    with pytest.raises(FileExistsError, match="write-once"):
        stages.record(p, {"a": 2})
    assert json.loads(p.read_text()) == {"a": 1}
    stages.record(p, {"a": 3}, overwrite=True)
    assert json.loads(p.read_text()) == {"a": 3}


def test_analysis_reads_a_missing_gates_record_or_gate_as_incomplete_and_the_outcome_is_write_once(tmp_path: Path) -> None:
    from studies.p10s2 import analysis

    assert analysis.gate_findings({}) == ([], ["the gates record is missing: the gates are not evaluated"])
    for gone in ("G2", "G3", "G9"):  # a missing gate (G2 and G3 included) is a missing registered quantity: INCOMPLETE, never passed
        eng, inc = analysis.gate_findings({k: v for k, v in GATES_OK.items() if k not in (gone, "ok")})
        assert eng == [] and inc == [f"gate {gone} has no record: not evaluated, never read as passed"]
    assert analysis.gate_findings(GATES_OK) == ([], [])
    eng, inc = analysis.gate_findings({**GATES_OK, "G2": {"ok": False, "problems": ["x"]}})
    assert len(eng) == 1 and "gate G2 failed" in eng[0] and inc == []  # a failed gate is ENGINEERING-FAILURE
    out = stages.stage_analysis(tmp_path, {"replicates": 1, "updates": 4}, {"teacher_only": True}, seed_mode="test")
    assert out["label"] == "INCOMPLETE" and any("gates record is missing" in e for e in out["incomplete"])
    assert (tmp_path / "outcome.json").exists() and (tmp_path / "seeds" / "analysis.json").exists()
    with pytest.raises(FileExistsError, match="write-once"):
        stages.stage_analysis(tmp_path, {"replicates": 1, "updates": 4}, {"teacher_only": True}, seed_mode="test")  # a rerun never replaces a written outcome
    (tmp_path / "REPORT.md").write_text("x")
    with pytest.raises(FileExistsError, match="write-once"):
        stages.stage_report(tmp_path)


def test_the_analysis_stage_may_draw_the_bootstrap_seed_only(tmp_path: Path) -> None:
    from studies.p10s2 import gates

    assert gates.g9_analysis([])["ok"]  # no interval printed: nothing drawn
    assert gates.g9_analysis([core.SeedUse(220906, "interval", "registered-analysis")])["ok"]
    bad = gates.g9_analysis([core.SeedUse(220906, "interval", "registered-analysis"), core.SeedUse(220907, "seen items", "registered-analysis")])
    assert not bad["ok"] and any("220907" in p for p in bad["problems"])
    assert not gates.g9_analysis([core.SeedUse(220906, "interval", "registered-data")])["ok"]  # a label other than the analysis stage's cannot stand in
    assert gates.g9_analysis([core.SeedUse(core.partition_seeds("test")["bootstrap"], "interval", "test")], "test")["ok"]


# --- M4: reserved analysis and report time; M6: the watchdog -------------------------------------------------------------------------------------
def test_analysis_and_report_caps_are_reserved_while_an_earlier_stage_runs() -> None:
    caps = {"n4-U2000": {"gates": 1.0, "train": 10.0, "evaluate": 5.0, "timing": 1.0, "recompute": 5.0, "analysis": 60.0, "report": 40.0}}
    assert stages.reserved_seconds(caps, "train", 4, 2000) == 100.0 and stages.reserved_seconds(caps, "gates", 4, 2000) == 100.0
    assert stages.reserved_seconds(caps, "analysis", 4, 2000) == 40.0 and stages.reserved_seconds(caps, "report", 4, 2000) == 0.0


def test_a_stage_guard_stops_work_at_its_wall_clock_cap() -> None:
    t0 = time.perf_counter()
    with pytest.raises(stages.CapReached, match="stage cap"):
        with stages.StageGuard("t", cap_seconds=0.2, interval=0.02):
            while True:
                time.sleep(0.01)
    assert time.perf_counter() - t0 < 5.0 and train.STOP.reason is None  # the stop request is cleared on exit


def test_a_stage_guard_stops_work_even_when_sigint_is_ignored_as_in_a_background_process() -> None:
    import signal

    old = signal.signal(signal.SIGINT, signal.SIG_IGN)  # a process launched with `&` or nohup ignores SIGINT: _thread.interrupt_main would do nothing
    try:
        with pytest.raises(stages.CapReached, match="stage cap"):
            with stages.StageGuard("t", cap_seconds=0.2, interval=0.02):
                while True:
                    time.sleep(0.01)
    finally:
        signal.signal(signal.SIGINT, old)


def test_a_stage_guard_stops_work_at_the_memory_limit_and_records_memory_exceeded() -> None:
    g = stages.StageGuard("t", memory_limit_bytes=1, interval=0.02)
    with pytest.raises(stages.MemoryLimitExceeded, match="memory limit"):
        with g:
            while True:
                time.sleep(0.01)
    rec = g.record()
    assert rec["memory_exceeded"] is True and rec["peak_bytes"] > 1 and rec["limit_bytes"] == 1 and "stop_reason" in rec


def test_a_stage_guard_records_the_peak_and_does_not_interfere_below_its_limits() -> None:
    with stages.StageGuard("t", cap_seconds=60.0, memory_limit_bytes=2**40, interval=0.02) as g:
        time.sleep(0.1)
    rec = g.record()
    assert rec["memory_exceeded"] is False and rec["peak_bytes"] > 0 and rec["peak_components_bytes"]["rss_peak"] > 0 and rec["stop_reason"] is None


def test_memory_measure_reads_the_mps_driver_where_mps_was_used() -> None:
    m = train.process_memory_bytes()
    assert m["max"] >= m["rss_peak"] > 0 and set(m) >= {"rss_peak", "mps_driver", "mps_allocated", "max"}
    if torch.backends.mps.is_available():
        x = torch.zeros(64 * 2**20 // 4, device="mps")  # 64 MiB on MPS: ru_maxrss does not see it
        train.MPS_IN_USE = True
        try:
            assert train.process_memory_bytes()["mps_driver"] >= 64 * 2**20
        finally:
            train.MPS_IN_USE = False
            del x


def test_evaluation_recomputation_and_gates_share_one_thread_count_and_deterministic_setting() -> None:
    threads, det = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled()
    with stages.scoring_environment() as env:
        assert env == {"threads": int(core.CFG["budget"]["timing_threads"]), "deterministic_algorithms": True}
        assert torch.get_num_threads() == 6 and torch.are_deterministic_algorithms_enabled()
    assert torch.get_num_threads() == threads and torch.are_deterministic_algorithms_enabled() == det


# --- M10: failed cells keep their records -----------------------------------------------------------------------------------------------------------
def test_an_operation_error_ends_the_cell_as_a_kept_failed_record_and_the_arm_returns_to_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    from studies.p10s2.memory import MemoryArm, SparseStore

    arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, core.SeedPlan("test", 0).gen(0, "t")), world.layer, world.codes(0))
    calls = {"n": 0}
    real = train.loss_of

    def flaky(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("operation not supported on this device")
        return real(*a, **k)

    monkeypatch.setattr(train, "loss_of", flaky)
    rec = train.train_arm(world.student, arm, world.train_examples(0, "A"), 5, world.batch, 0.003, core.SeedPlan("test", 0).gen(2, "t"), world.marker_index)
    assert rec.status == "failed" and "operation not supported" in rec.error and "at update 2" in rec.error and rec.updates == 2
    assert all(p.device.type == "cpu" for p in arm.trainable()) and all(p.device.type == "cpu" for p in world.student.parameters())


def test_one_failed_cell_keeps_its_record_stops_only_its_dependants_and_the_rest_of_the_replicate_survives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    calls = {"n": 0}
    real = train.loss_of

    def flaky(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:  # the second update of the first cell (ST1 of order AB)
            raise RuntimeError("device error")
        return real(*a, **k)

    monkeypatch.setattr(train, "loss_of", flaky)
    out = stages.stage_train(world, tmp_path)
    assert out["stopped"] == []
    rec = json.loads((tmp_path / "train" / "r0.json").read_text())
    assert len(rec) == 18 and rec["r0/ST1/AB"]["status"] == "failed" and "device error" in rec["r0/ST1/AB"]["train"][0]["error"]
    for dep in ("MAF", "MII", "MSEQ"):
        assert rec[f"r0/{dep}/AB"]["status"] == "skipped_dependency"  # only the dependants of the failed cell
    done = [k for k, v in rec.items() if v["status"] == "completed"]
    assert "r0/ST1/BA" in done and "r0/MAF/BA" in done and "r0/ETABLE/A" in done and "r0/LJOINT/-" in done and len(done) == 14  # the replicate's other records survive


def test_an_exception_out_of_a_replicate_rebuilds_its_records_from_the_snapshots(tmp_path: Path) -> None:
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    (snaps / "r0__ST1__AB.manifest.json").write_text(json.dumps({"name": "r0/ST1/AB", "file": "r0__ST1__AB.pt"}))
    recs = stages._recover_records(0, snaps, "RuntimeError: out of memory")
    assert len(recs) == len(replicate_cells(0)) and recs["r0/ST1/AB"]["status"] == "completed" and "rebuilt" in recs["r0/ST1/AB"]["note"]
    assert recs["r0/ST1/BA"]["status"] == "failed" and "out of memory" in recs["r0/ST1/BA"]["train"][0]["error"]


def test_a_stop_request_ends_every_cell_with_the_reason_and_is_recorded(tmp_path: Path) -> None:
    world, _ = dry_world()
    train.STOP.set("the stage cap of 1.0 s was reached")
    try:
        out = stages.stage_train(world, tmp_path)
    finally:
        train.STOP.clear()
    assert len(out["stopped"]) == 1 and "stage cap" in out["stopped"][0]
    rec = json.loads((tmp_path / "train" / "r0.json").read_text())
    assert all(v["status"] in ("failed", "skipped_dependency") for v in rec.values()) and "stopped before update 0" in rec["r0/ST1/AB"]["train"][0]["error"]
    assert json.loads((tmp_path / "train" / "stopped.json").read_text()) == out["stopped"]


def test_a_deadline_stops_the_cell_running_not_only_the_next_replicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    dl = stages.Deadline(1.0)
    calls = {"n": 0}

    def expired() -> bool:
        calls["n"] += 1
        return calls["n"] > 3  # not expired at the replicate check, expired a few updates into the first cell

    monkeypatch.setattr(dl, "expired", expired)
    out = stages.stage_train(world, tmp_path, dl)
    rec = json.loads((tmp_path / "train" / "r0.json").read_text())  # the replicate's record exists although the cap was reached inside it
    assert len(out["stopped"]) == 1 and "stage cap" in out["stopped"][0]
    assert any(v["status"] == "failed" and "stage cap" in v["train"][0]["error"] for v in rec.values())
    assert train.STOP.reason is None and not train.STOP.hooks  # the hook is removed when the stage function returns


def test_assemble_study_carries_a_replicate_error_into_the_incomplete_list(tmp_path: Path) -> None:
    (tmp_path / "evaluate").mkdir()
    (tmp_path / "evaluate" / "r0.json").write_text(json.dumps({"cells": {}, "error": "scoring of replicate 0 failed: RuntimeError: x"}))
    study = stages.assemble_study(tmp_path, {"replicates": 1, "updates": 4}, {}, GATES_OK, extra_engineering=["e"])
    assert study["incomplete"] == ["scoring of replicate 0 failed: RuntimeError: x"] and study["engineering"] == ["e"]
