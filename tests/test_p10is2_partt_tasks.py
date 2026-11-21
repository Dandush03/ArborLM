# ruff: noqa: E501
"""P10IS2 Part T stages through the task runner (ADR-0025 sections 8.6, 9, 11 items 2 and 4; ruling G7, G13, G14, C10): tasks from the frozen plan only, cumulative caps and the ledger, charged time summed over
worker processes, PAUSED — IDENTITY, item errors, the memory guard, worker counts, retry. Tiny worker processes; no model except in the one worker-body test. Self-check only."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from studies.p10is2 import partt_plan, partt_real, partt_tasks  # noqa: E402
from studies.p10is2.common import core, runner  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

CALIB = {"U": 2, "converged": True, "store_rate": 0.003, "lora_rate": 0.001, "etable_rate": 0.003, "read_layer": 1, "pilot": {"passed": True}, "records": {}}


def a_plan(caps: dict[str, float] | None = None) -> planmod.Plan:
    items = partt_plan.stage_items(CALIB)
    stage_caps = {f"{k}_hours": 1.0 for k in ("gates", "calibration", "train", "evaluate", "controls", "combined", "analysis")} | {"total_hours": 3.0} | (caps or {})
    return planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "mode": "registered", "items": items, "stage_caps": stage_caps, "calibration": CALIB}, "T")


def test_tasks_come_from_the_plan_only_in_dependency_waves() -> None:
    plan = a_plan()
    w = partt_tasks.waves_of("train", plan)
    assert [len(x) for x in w] == [24, 24, 6] and {i["arm"] for i in w[2]} == {"M-ii"} and sum(len(x) for x in w) == len(plan.items("train")) == 54
    assert {i["arm"] for i in w[1]} == {"M-append", "M-seq", "D-append", "D-seq"}
    ev = partt_tasks.waves_of("evaluate", plan)
    assert [[t["id"] for t in x] for x in ev] == [["evaluate|r0", "evaluate|r1", "evaluate|r2", "evaluate|reference"]]
    assert [t["id"] for t in partt_tasks.waves_of("combined", plan)[0]] == ["combined|r0", "combined|r1", "combined|r2", "combined|reference"]
    assert partt_tasks.waves_of("gates", plan)[0][0]["gates"] == ["G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9"]
    with pytest.raises(core.StageRefused):
        partt_tasks.waves_of("analysis", plan)
    plan.data["items"]["train"] = plan.data["items"]["train"][:5]  # a different plan gives different tasks: nothing is read from the config
    assert sum(len(x) for x in partt_tasks.waves_of("train", plan)) == 5


def test_worker_policy_two_workers_while_another_study_runs() -> None:
    a, b = partt_tasks.worker_policy(CFG_T, False), partt_tasks.worker_policy(CFG_T, True)
    assert (a["workers"], a["rss_worker_bytes"], a["rss_aggregate_bytes"]) == (3, 8 * 2**30, 24 * 2**30)
    assert (b["workers"], b["rss_aggregate_bytes"]) == (2, 16 * 2**30)


def test_other_studies_alive_sees_another_study_not_this_one() -> None:
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(6)", "studies.p10ir.marker"])  # noqa: S603
    q = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(6)", "studies.p10is2.marker"])  # noqa: S603
    try:
        time.sleep(0.6)
        alive = partt_tasks.other_studies_alive()
        assert any("studies.p10ir.marker" in a for a in alive) and not any("studies.p10is2.marker" in a for a in alive)
    finally:
        p.kill()
        q.kill()


def fake_runner(outcomes: dict[str, dict], seen: list):  # type: ignore[no-untyped-def]
    def run(tasks, **kw):  # type: ignore[no-untyped-def]
        seen.append((len(tasks), kw))
        return {t.label: outcomes.get(t.label, {"status": runner.COMPLETED, "seconds": 10.0, "peak_rss_bytes": 1}) for t in tasks}, 3.0

    return run


def test_charged_time_is_the_sum_of_worker_wall_times_and_caps_are_cumulative(tmp_path: Path) -> None:
    plan = a_plan({"evaluate_hours": 100 / 3600, "total_hours": 130 / 3600})  # 100 s for the stage, 130 s in all
    seen: list = []
    out = {"evaluate|r0": {"status": runner.COMPLETED, "seconds": 40.0, "peak_rss_bytes": 1}, "evaluate|r1": {"status": runner.COMPLETED, "seconds": 35.0, "peak_rss_bytes": 1}, "evaluate|r2": {"status": runner.NOT_STARTED, "seconds": 0.0, "reason": "stage cap reached", "peak_rss_bytes": 0}}
    m = partt_tasks.run_stage_tasks("evaluate", plan, CFG_T, tmp_path, tmp_path / "run", "c" * 40, tmp_path / "q", other_alive=lambda: [], task_runner=fake_runner(out, seen))
    led = partt_tasks.ledger_of(plan, tmp_path / "run")
    assert led.charged() == 10 + 40 + 35 + 0 + 0 and m["status"] == "PAUSED" and seen[0][1]["cap_seconds"] == pytest.approx(100.0)  # the sum over worker processes: three tasks, 4 results
    assert seen[0][1]["workers"] == 3
    # a resume gets what is left: the stage has 100 - 85 = 15 s, the total 130 - 85 = 45 s; the smaller is 15
    assert partt_tasks.stage_cap_for(plan, "evaluate", led) == pytest.approx(15.0)
    seen.clear()
    partt_tasks.run_stage_tasks("evaluate", plan, CFG_T, tmp_path, tmp_path / "run", "c" * 40, tmp_path / "q", other_alive=lambda: [], task_runner=fake_runner({}, seen))
    assert seen[0][1]["cap_seconds"] == pytest.approx(15.0)
    # another stage shares the total: evaluate used 85 + 40; the total of 130 leaves 5 s however large the stage cap is
    assert partt_tasks.stage_cap_for(plan, "train", partt_tasks.ledger_of(plan, tmp_path / "run")) <= 130 - 125.0 + 1e-9


def test_a_spent_cap_pauses_without_starting_a_task(tmp_path: Path) -> None:
    plan = a_plan({"gates_hours": 10 / 3600})
    led = partt_tasks.ledger_of(plan, tmp_path / "run")
    led.charge_process("gates", "x", "w", 11.0)
    seen: list = []
    m = partt_tasks.run_stage_tasks("gates", plan, CFG_T, tmp_path, tmp_path / "run", "c" * 40, tmp_path / "q", other_alive=lambda: [], task_runner=fake_runner({}, seen))
    assert m["status"] == "PAUSED" and seen == []


def test_a_failed_task_is_an_item_error_and_stops_the_next_wave(tmp_path: Path) -> None:
    plan = a_plan()
    seen: list = []
    out = {"train|M1|AB|r0": {"status": runner.FAILED, "seconds": 5.0, "reason": "exit status 1", "peak_rss_bytes": 1}}
    m = partt_tasks.run_stage_tasks("train", plan, CFG_T, tmp_path, tmp_path / "run", "c" * 40, tmp_path / "q", other_alive=lambda: [], task_runner=fake_runner(out, seen))
    assert m["status"] == "FAILED" and len(seen) == 1  # the wave of stage-2 modules was not started
    errs = list((tmp_path / "run" / "item_errors").glob("*.json"))
    assert len(errs) == 1 and json.loads(errs[0].read_text())["task"] == "train|M1|AB|r0"
    from p10is2_partt_fixtures import build

    from studies.p10is2 import labels as L

    assert L.study_status(build(), item_errors=[str(e) for e in errs])["status"] == L.STOP_ITEMS  # the analysis refuses


def test_the_real_runner_pauses_identity_fails_and_guards_memory(tmp_path: Path) -> None:
    def task(label: str, code: str) -> runner.Task:
        d = tmp_path / label
        return runner.Task(label, (sys.executable, "-c", code), d / "result.json", d / "failed.json", d / "log.txt")

    ok = "import sys,pathlib; pathlib.Path(sys.argv[0] if False else '%s').parent.mkdir(parents=True, exist_ok=True); open('%s','w').write('{}')"
    t_ok = task("ok", ok % (tmp_path / "ok" / "result.json", tmp_path / "ok" / "result.json"))
    t_id = task("ident", "import sys; sys.exit(75)")
    t_bad = task("bad", "import sys; sys.exit(1)")
    t_mem = task("mem", "import time; x = bytearray(400 * 1024 * 1024); [x.__setitem__(i, 1) for i in range(0, len(x), 4096)]; time.sleep(30)")
    out, _ = runner.run_tasks([t_ok, t_id, t_bad, t_mem], workers=4, cap_seconds=60, rss_worker_bytes=200 * 2**20, rss_aggregate_bytes=2**33, poll=0.1)
    assert out["ok"]["status"] == runner.COMPLETED and out["ident"]["status"] == runner.PAUSED_IDENTITY and out["bad"]["status"] == runner.FAILED and out["mem"]["status"] == runner.KILLED_RSS
    assert not (tmp_path / "ident" / "failed.json").exists()  # an identity pause writes nothing and is not a failure
    assert (tmp_path / "bad" / "failed.json").is_file()
    again, _ = runner.run_tasks([t_ok, t_id, t_bad], workers=2, cap_seconds=60, rss_worker_bytes=2**33, rss_aggregate_bytes=2**33, poll=0.1)
    assert again["ok"]["skipped"] == "result exists" and again["bad"]["status"] == runner.FAILED and "not re-run" in again["bad"]["reason"] and again["ident"]["status"] == runner.PAUSED_IDENTITY  # the identity pause runs again
    assert runner.stage_status(out) == "FAILED" and runner.stage_status({"a": {"status": runner.PAUSED_IDENTITY}}) == "PAUSED"


def test_retry_releases_an_error_once_and_never_a_non_finite_cell(tmp_path: Path) -> None:
    d = partt_tasks.tasks_dir(tmp_path, "train")
    d.mkdir(parents=True)
    sid = partt_tasks.safe("train|M1|AB|r0")
    (d / f"{sid}.failed.json").write_text('{"reason": "exit status 1"}')
    (d / f"{sid}.cell.json").write_text(json.dumps({"status": "STOPPED_NONFINITE", "last_finite_checkpoint": 1500}))
    with pytest.raises(core.StageRefused, match="NON-FINITE"):
        partt_tasks.retry(tmp_path, "train", "train|M1|AB|r0", "x", False)
    (d / f"{sid}.cell.json").write_text(json.dumps({"status": "ERROR", "last_checkpoint": 1000}))
    with pytest.raises(core.StageRefused, match="frozen file"):
        partt_tasks.retry(tmp_path, "train", "train|M1|AB|r0", "a fix", True)
    with pytest.raises(core.StageRefused, match="cause"):
        partt_tasks.retry(tmp_path, "train", "train|M1|AB|r0", "", False)
    r = partt_tasks.retry(tmp_path, "train", "train|M1|AB|r0", "out of memory; closed other apps", False)
    assert r == {"released": "train|M1|AB|r0", "resume_from": 1000} and not (d / f"{sid}.failed.json").exists() and any((d / "failed_kept").iterdir())  # kept, never deleted
    with pytest.raises(core.StageRefused):
        partt_tasks.retry(tmp_path, "train", "train|M1|AB|r0", "again", False)


def test_run_task_trains_a_cell_and_resumes_a_dependent_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = world(updates=2)
    monkeypatch.setattr(partt_real, "build_world_real", lambda repo, cfg, qdir, calib, mode: (w, {}, {}))
    plan = a_plan()
    run = tmp_path / "run"
    r1 = partt_real.run_task("train", "train|M1|AB|r0", core.ROOT, run, tmp_path / "q", plan, mode="test")
    assert r1["cell"]["status"] == "COMPLETE" and (partt_tasks.tasks_dir(run, "train") / f"{partt_tasks.safe('train|M1|AB|r0')}.result.json").is_file()
    r2 = partt_real.run_task("train", "train|M-append|AB|r0", core.ROOT, run, tmp_path / "q", plan, mode="test")  # the parent comes from its snapshot
    assert r2["cell"]["status"] == "COMPLETE" and (run / "snapshots").is_dir()
    with pytest.raises(FileExistsError):
        partt_real.run_task("train", "train|M1|AB|r0", core.ROOT, run, tmp_path / "q", plan, mode="test")  # the result file is written once: the runner never calls a finished task again


def test_merge_results_and_the_recomputation_requirement(tmp_path: Path) -> None:
    d = tmp_path / "tasks" / "evaluate"
    d.mkdir(parents=True)
    core.write_record(d / "evaluate__r0.result.json", {**core.envelope("cell_record", "T"), "records": {"M1|AB|0": {"s:E_A": 0.5}}, "side": {"r0/x": {"a": 1}}})
    core.write_record(d / "evaluate__reference.result.json", {**core.envelope("cell_record", "T"), "records": {"S0|-|-": {"s:E_A": 0.1}}, "side": {}})
    (tmp_path / "tasks" / "combined").mkdir()
    assert partt_real.merge_results(tmp_path) == {"records": 2, "combined": 0}
    assert json.loads((tmp_path / "registry.json").read_text()) == {"M1|AB|0|s:E_A": 0.5, "S0|-|-|s:E_A": 0.1}
    with pytest.raises(core.StageRefused, match="no recomputation record"):
        partt_real.require_recomputation(tmp_path)
    (tmp_path / "recomputation.json").write_text(json.dumps({"ok": False, "differences": ["x"]}))
    with pytest.raises(core.StageRefused, match="ENGINEERING STOP — RECOMPUTATION"):
        partt_real.require_recomputation(tmp_path)
    (tmp_path / "recomputation.json").write_text(json.dumps({"ok": True}))
    assert partt_real.require_recomputation(tmp_path)["ok"]
