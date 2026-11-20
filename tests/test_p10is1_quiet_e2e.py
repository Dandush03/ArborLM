# ruff: noqa: E501
"""P10IS1 quiet rule, end to end on synthetic inputs (ADR-0024 addendum A3, A8): baseline -> config -> candidate plan -> freeze (the baseline re-derived), and the quiet stages through the SAME ``execute_stage`` the
registered launch and the counting rehearsal use, with an injected machine (process table, load reader, clock): an application presence that changed, a wait that reaches its bound, waiting that is not charged, the
stage's own cap, a timing-spread failure and its re-timing, three spread sessions, the counting rehearsal's retry of a PAUSED quiet stage by itself, the launch scripts. No test waits. Self-check only: not an
independent review, not Astra validation, not human approval."""

import argparse
import inspect
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import test_p10is1_quiet_rule as qr  # noqa: E402
import test_p10is1_rehearsal as TR  # noqa: E402
import test_p10is1_stages as TS  # noqa: E402

from arborlm.io import file_sha256, read_json  # noqa: E402
from studies.p10is1 import (  # noqa: E402
    baseline,
    core,
    freeze,
    items,
    quiet,
    rehearsal,
    rehearsal_real,
    stages,
)
from studies.p10is1 import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = "/Applications/Claude.app/Contents/MacOS/Claude"


# --- baseline -> config -> candidate plan -> freeze --------------------------------------------------------------------------------------------------
def provisional_repo(tmp: Path) -> Path:
    """A throw-away repository in the state before the baseline: ``baseline_provisional = true``."""
    repo = TS.mini_repo(tmp)
    p = repo / core.CONFIG
    p.write_text(qr.set_quiet_figures(p.read_text(), baseline_provisional="true", baseline_record_path='""', baseline_record_sha256='""'))
    TR.git(repo, "add", "-A")
    TR.git(repo, "commit", "-q", "-m", "provisional baseline")
    return repo


def write_config_from(repo: Path, out: Path, rec: dict[str, Any]) -> None:
    """What the lead does after an accepted baseline: the figures `baseline verify` prints go into [quiet] (by hand) and the record is committed."""
    d = baseline.rederive(out / baseline.RECORD, qr.qcfg()["quiet"])
    p = repo / core.CONFIG
    rel = out.relative_to(repo)
    p.write_text(qr.set_quiet_figures(p.read_text(), baseline_provisional="false", load_p95=str(d["load_p95"]), load_limit=str(d["load_limit"]), condition=f'"{d["condition"]}"', app_present=str(d["app_present"]).lower(), cli_present=str(d["cli_present"]).lower(), baseline_record_path=f'"{rel}/{baseline.RECORD}"', baseline_record_sha256=f'"{d["record_sha256"]}"'))
    assert rec["status"] == "ACCEPTED"


def candidate(repo: Path, tmp: Path) -> int:
    run = tmp / "run"
    if not (run / "draws").exists():
        TS.seed_manifests(run)
    cal = tmp / "cal.json"
    cal.write_text(json.dumps(TS.CAL))
    return freeze.cmd_candidate_plan(TS.candidate_args(repo, run, cal))


def test_the_candidate_plan_refuses_while_the_baseline_is_provisional(tmp_path: Path) -> None:
    repo = provisional_repo(tmp_path)
    with pytest.raises(core.StageRefused, match="baseline_provisional is true"):
        candidate(repo, tmp_path)
    assert not (repo / core.PLAN).exists()
    with pytest.raises(core.StageRefused, match="no candidate plan"):
        freeze.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(tmp_path / "r.json")))  # no baseline, so no plan, so nothing to freeze
    p = repo / core.CONFIG
    assert "load_average_max" not in p.read_text()


def test_the_freeze_without_a_baseline_says_so_when_a_plan_exists(tmp_path: Path) -> None:
    repo = TS.mini_repo(tmp_path)  # a measured baseline installed
    assert candidate(repo, tmp_path) == 0
    p = repo / core.CONFIG
    p.write_text(qr.set_quiet_figures(p.read_text(), baseline_provisional="true"))
    with pytest.raises(core.StageRefused, match="baseline_provisional is true"):
        freeze.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(tmp_path / "r.json")))  # before the caps and the rehearsal are even looked at


@pytest.mark.parametrize("shape", ["rising", "falling", "above_ceiling"])
def test_a_refused_baseline_cannot_reach_a_candidate_plan(shape: str, tmp_path: Path) -> None:
    """Unsettled (rising and falling) and above the ceiling: the command ends PAUSED — NO QUIET BASELINE with its samples kept; a config that names that record is refused by the candidate plan."""
    repo = provisional_repo(tmp_path)
    ramp = {"rising": lambda t: 1.0 + 0.005 * t, "falling": lambda t: max(0.2, 3.0 - 0.005 * t), "above_ceiling": lambda t: 2.60}[shape]
    out = repo / "results" / "refused"
    rec = qr.run_session(qr.FakeMachine(lambda t: (ramp(t), ramp(t))), out, qr.small())
    assert rec["status"] == baseline.PAUSED_NO_BASELINE and rec["accepted"] is None and (out / baseline.SAMPLES).is_file()
    reason = rec["attempts"][0]["reason"]
    assert reason.startswith("NOT SETTLED") if shape != "above_ceiling" else "ABOVE CEILING" in reason
    p = repo / core.CONFIG
    p.write_text(qr.set_quiet_figures(p.read_text(), baseline_provisional="false", load_p95="130", load_limit="180", baseline_record_path='"results/refused/record.json"', baseline_record_sha256=f'"{file_sha256(out / baseline.RECORD)}"'))
    with pytest.raises(core.StageRefused, match="not an ACCEPTED quiet baseline|other \\[quiet\\] rules"):
        candidate(repo, tmp_path)
    assert not (repo / core.PLAN).exists()


def test_a_limit_above_the_ceiling_in_the_config_is_never_read_or_clamped(tmp_path: Path) -> None:
    repo = TS.mini_repo(tmp_path)
    p = repo / core.CONFIG
    p.write_text(qr.set_quiet_figures(p.read_text(), load_limit="301"))
    with pytest.raises(core.StageRefused, match="differ from the ones re-derived"):
        candidate(repo, tmp_path)  # the committed samples give 180
    with pytest.raises(core.StageRefused, match="never clamped"):
        quiet.quiet_reading(probe=qr.FakeMachine().probe(), cfg=core.load_config(p))


def test_the_baseline_taken_by_the_command_flows_into_the_config_the_plan_and_the_freeze(tmp_path: Path) -> None:
    repo = provisional_repo(tmp_path)
    shutil.rmtree(qr.CANON / "first", ignore_errors=True)  # the synthetic mirror of the provisional repo is not this study's baseline
    canon_first = qr.CANON / "first"  # the baseline is taken by the command in the canonical root, then its record and samples are copied into results/ and committed
    rec = qr.run_session(qr.FakeMachine(lambda t: (1.30 + (0.05 if int(t / 10) % 7 == 0 else 0.0), 1.30)), canon_first, qr.qcfg(), sessions_log=repo / baseline.SESSIONS_LOG)
    assert rec["status"] == "ACCEPTED" and rec["accepted"]["load_limit"] == 185 and rec["test_root"] is False and rec["root"] == str(qr.CANON.resolve())
    out = repo / "results" / "p10is1-quiet-baseline-e2e"
    out.mkdir(parents=True)
    for f in (baseline.RECORD, baseline.SAMPLES):
        (out / f).write_bytes((canon_first / f).read_bytes())
    write_config_from(repo, out, rec)  # the figures are written into [quiet] BEFORE the candidate plan
    TR.git(repo, "add", "-A")
    TR.git(repo, "commit", "-q", "-m", "baseline and its figures")
    assert candidate(repo, tmp_path) == 0
    pl = planmod.Plan.load(repo / core.PLAN)
    assert "configs/p10is1_capacity.toml" in pl.data["frozen_files"]  # the figures and the record's hash are frozen with the plan through the config
    cfg = core.load_config(repo / core.CONFIG)
    assert (cfg["quiet"]["load_p95"], cfg["quiet"]["load_limit"], cfg["quiet"]["baseline_provisional"]) == (135, 185, False)
    assert baseline.verify_against_config(repo, cfg)["load_limit"] == 185
    # the freeze re-derives from the committed samples and refuses each difference: a figure edited in the config after the plan was written...
    p = repo / core.CONFIG
    original = p.read_text()
    fargs = argparse.Namespace(repo=str(repo), rehearsal=str(tmp_path / "r.json"))
    p.write_text(qr.set_quiet_figures(original, load_limit="200"))
    with pytest.raises(core.StageRefused, match="differ from the ones re-derived"):
        freeze.cmd_freeze(fargs)
    p.write_text(qr.set_quiet_figures(original, app_present="true"))
    with pytest.raises(core.StageRefused, match="differ from the ones re-derived"):
        freeze.cmd_freeze(fargs)
    p.write_text(original)
    # ...or a sample edited after the record was written
    sp = out / baseline.SAMPLES
    lines = sp.read_text().splitlines()
    row = json.loads(lines[200])
    row["load1_h"] = 99
    lines[200] = json.dumps(row, sort_keys=True)
    sp.write_text("\n".join(lines) + "\n")
    with pytest.raises(core.StageRefused, match="samples file is missing or does not hash"):
        freeze.cmd_freeze(fargs)


def test_the_freeze_prints_the_report_notice_for_a_limit_above_250_and_it_is_not_a_gate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = provisional_repo(tmp_path)
    shutil.rmtree(qr.CANON / "first", ignore_errors=True)
    canon_first = qr.CANON / "first"
    rec = qr.run_session(qr.FakeMachine(lambda t: (2.20, 2.20)), canon_first, qr.qcfg(), sessions_log=repo / baseline.SESSIONS_LOG)
    assert rec["accepted"]["load_limit"] == 270
    out = repo / "results" / "high"
    out.mkdir(parents=True)
    for f in (baseline.RECORD, baseline.SAMPLES):
        (out / f).write_bytes((canon_first / f).read_bytes())
    write_config_from(repo, out, rec)
    assert candidate(repo, tmp_path) == 0  # written: a report, not a gate
    assert "above 250" in capsys.readouterr().out


# --- the quiet stages through execute_stage with an injected machine -----------------------------------------------------------------------------------
def tiny(tmp: Path, *, text_hook: Any = None) -> tuple[Path, Path, planmod.Plan, Any]:
    root = tmp / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    text = qr.measured_quiet_text(rehearsal.tiny_config_text())
    cfg_path.write_text(text_hook(text) if text_hook else text)
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    return root, cfg_path, pl, core.load_config(cfg_path)


def run_stage(stage: str, pl: planmod.Plan, root: Path, cfg_path: Path, cfg: Any, fm: qr.FakeMachine, *, run: str = "run") -> dict[str, Any]:
    ctx = items.Ctx(core.TEST, root / run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    probe = fm.probe()
    return stages.execute_stage(
        stage, pl, ctx, root / run, pl.path, argparse.Namespace(freeze_commit=None, synthetic=True), repo=ROOT, inline=True,
        quiet_reading=lambda: quiet.quiet_reading(probe=probe, cfg=cfg), end_fn=lambda s: quiet.end_check(s, probe=probe, cfg=cfg, sleep=fm.sleep), sleep=fm.sleep, clock=fm.clock,
    )  # fmt: skip


def fake_timing(fm: qr.FakeMachine, results: list[Any], *, spend: float = 7.0, calls: list[int] | None = None) -> Any:
    seq = iter(results)

    def measure(pl: Any, ctx: Any, *, guard: Any = None, **kw: Any) -> Any:
        fm.t += spend  # the measurement takes ``spend`` seconds of the injected clock
        if calls is not None:
            calls.append(1)
        if guard is not None:
            guard()
        return next(seq)

    return measure


def spread_ok() -> dict[str, Any]:
    return {"cpu": {"A|1": 1.0}, "detail": {"A|1": {"runs": [1.0, 1.01, 1.0], "wall_runs": [1.1, 1.1, 1.1]}}, "draw": "rehearsal", "platform": {}}


def spread_bad() -> dict[str, Any]:
    return {"cpu": {"A|1": 1.0}, "detail": {"A|1": {"runs": [1.0, 1.2, 1.0], "wall_runs": [1.1, 1.3, 1.1]}}, "draw": "rehearsal", "platform": {}}


def test_a_stage_refuses_every_poll_when_the_applications_presence_differs_from_the_baselines_and_nothing_is_charged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)  # the baseline had the application closed
    fm = qr.FakeMachine()
    fm.extra = [(900, 1, APP)]  # the application was opened after the baseline
    calls: list[int] = []
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [], calls=calls))
    rec = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert rec["status"] == "PAUSED" and not calls and rec["charged_seconds"] == 0.0 and rec["waited_seconds_not_charged"] == 21600.0
    rows = [json.loads(x) for x in quiet.polls_path(root / "run", "timing").read_text().splitlines()]
    assert len(rows) == 37 and all(r["failed"] == ["APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S"] and r["app_present"] is True and r["limit_h"] == 180 for r in rows)
    assert quiet.paused_attempts(root / "run", "timing") == [] and quiet.attempt_statuses(root / "run", "timing") == {1: quiet.PAUSED_CONDITION} and not (root / "run" / "timing" / "timing.json").exists()  # N2: a machine-condition failure never counts
    led = stages.ledger_of(pl, root / "run")
    assert led.charged("timing") == 0.0  # six hours of waiting, none charged: the per-stage cap is not eaten by the wait


def test_a_wait_that_reaches_its_bound_ends_paused_and_the_next_session_is_a_new_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    fm = qr.FakeMachine(lambda t: (2.5, 2.5))  # above L = 1.80 for ever
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [spread_ok()]))
    rec = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert rec["status"] == "PAUSED" and fm.t == 21600.0 and rec["charged_seconds"] == 0.0
    rows = [json.loads(x) for x in quiet.polls_path(root / "run", "timing").read_text().splitlines()]
    assert len(rows) == 37 and rows[-1]["elapsed_seconds"] == 21600.0 and rows[0]["failed"] == ["ONE-MINUTE LOAD ABOVE L", "FIVE-MINUTE LOAD ABOVE L"]
    fm.load = lambda t: (1.0, 1.0)  # the machine is quiet at the next session
    rec2 = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert rec2["status"] == "COMPLETE" and quiet.paused_attempts(root / "run", "timing") == [1]
    assert read_json(root / "run" / "timing" / "attempts" / "02.json")["status"] == "QUIET RUN"
    # training is allowed now that the timing stage holds its record
    assert quiet.require_timing_settled(root / "run") == "COMPLETE"


def test_waiting_is_not_charged_and_the_measuring_seconds_are_the_quiet_reading_to_the_end_check_with_the_delay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    fm = qr.FakeMachine(lambda t: (2.5, 2.5) if t < 3000 else (1.0, 1.0))
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [spread_ok()], spend=7.0))
    rec = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert rec["status"] == "COMPLETE" and rec["waited_seconds_not_charged"] == 3000.0
    assert rec["charged_seconds"] == 7.0 + 120.0  # the measurement and the 120-s delay of the end check; the fifty minutes of waiting are not charged
    assert stages.ledger_of(pl, root / "run").charged("timing") == 127.0
    t = core.read_record(root / "run" / "timing" / "timing.json", "timing")
    assert t["wait_seconds"] == 3000.0 and t["measure_seconds"] == 127.0 and t["retimed"] is False and t["timing_spread"]["ok"] is True and t["timing_spread"]["max_spread"] == pytest.approx(0.01)
    assert t["detail"]["A|1"]["runs"] == [1.0, 1.01, 1.0]  # the per-repeat values are kept
    att = read_json(root / "run" / "timing" / "attempts" / "01.json")
    assert att["end_check"]["load1_h_after_delay"] == 100 and att["end_check"]["limit_h"] == 180 and att["top_processes"]["start"] is not None


def test_the_stages_own_cap_is_enforced_for_the_two_quiet_stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    pl.data["stage_caps"]["timing_hours"] = 100.0 / 3600.0  # 100 charged seconds
    fm = qr.FakeMachine(lambda t: (2.5, 2.5) if t < 36000 else (1.0, 1.0))  # ten hours of waiting before the first quiet reading (two sessions)
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [spread_ok(), spread_ok()], spend=200.0))
    first = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert first["status"] == "PAUSED" and quiet.paused_attempts(root / "run", "timing") == [1]
    second = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert second["status"] == "PAUSED" and second["result"]["status"] == quiet.PAUSED_CAP  # the measurement ran 200 s against a cap of 100: discarded, its own status
    assert second["charged_seconds"] == 200.0 and quiet.paused_attempts(root / "run", "timing") == [1]  # a cap pause is not a quiet failure: it never counts towards NOT MEASURED
    third = run_stage("timing", pl, root, cfg_path, cfg, fm)  # the cap is spent (200 s charged): no wait, no measurement
    assert third["status"] == "PAUSED" and third["result"]["status"] == quiet.PAUSED_CAP and third["charged_seconds"] == 0.0 and third["waited_seconds_not_charged"] == 0.0
    # the throughput stage has its own cap of the same kind
    pl.data["stage_caps"]["throughput_hours"] = 10.0 / 3600.0
    monkeypatch.setattr(stages, "require_gates_passed", lambda run_dir: None)

    def slow_throughput(pl_: Any, ctx: Any, guard: Any = None) -> Any:
        fm.t += 30.0  # one item takes 30 s against a cap of 10: the guard before the next item stops it
        guard()
        return {"results": {}}

    monkeypatch.setattr(stages, "measure_throughput", slow_throughput)
    thr = run_stage("throughput", pl, root, cfg_path, cfg, fm)
    assert thr["status"] == "PAUSED" and thr["result"]["status"] == quiet.PAUSED_CAP and thr["charged_seconds"] == 30.0 and quiet.paused_attempts(root / "run", "throughput") == []


def test_a_spread_failure_times_the_whole_list_again_after_a_new_quiet_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    fm = qr.FakeMachine()
    calls: list[int] = []
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [spread_bad(), spread_ok()], calls=calls))
    rec = run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert rec["status"] == "COMPLETE" and len(calls) == 2 and rec["charged_seconds"] == 2 * (7.0 + 120.0)  # both measurements are charged
    t = core.read_record(root / "run" / "timing" / "timing.json", "timing")
    assert t["retimed"] is True and t["detail"]["A|1"]["runs"] == [1.0, 1.01, 1.0]  # only the second attempt's list is the record: readings are never combined
    att = read_json(root / "run" / "timing" / "attempts" / "01.json")
    assert att["status"] == "QUIET RUN" and [a["valid"] for a in att["timing_attempts"]] == [False, True] and att["timing_attempts"][0]["result"]["detail"]["A|1"]["runs"] == [1.0, 1.2, 1.0]  # the failed attempt is kept
    assert att["timing_attempts"][0]["validation"]["failing_items"] == ["A|1"] and att["timing_attempts"][0]["validation"]["max_spread"] == pytest.approx(0.2)
    assert quiet.paused_attempts(root / "run", "timing") == []


def test_three_sessions_ending_in_a_spread_failure_return_the_stage_to_the_lead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    fm = qr.FakeMachine()
    monkeypatch.setattr(stages, "measure_timing", fake_timing(fm, [spread_bad()] * 8))
    for k in range(3):
        rec = run_stage("timing", pl, root, cfg_path, cfg, fm)
        assert rec["status"] == "PAUSED" and rec["result"]["status"] == quiet.PAUSED_SPREAD and quiet.spread_sessions(root / "run", "timing") == k + 1
    assert quiet.paused_attempts(root / "run", "timing") == []  # none of the three counts towards the six sessions of NOT MEASURED
    with pytest.raises(core.StageRefused, match="the matter returns to the human lead"):
        run_stage("timing", pl, root, cfg_path, cfg, fm)
    assert quiet.stage_state(root / "run", "timing", "timing.json") == "PAUSED"  # and nothing writes NOT MEASURED
    with pytest.raises(core.StageRefused, match="training does not start"):
        quiet.require_timing_settled(root / "run")


def test_the_real_measurement_keeps_the_per_repeat_values_and_the_cpu_to_wall_ratio(tmp_path: Path) -> None:
    root, cfg_path, pl, cfg = tiny(tmp_path)
    ctx = items.Ctx(core.TEST, root / "run", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    out = stages.measure_timing(pl, ctx, warmup=1, updates=2, repeats=3)
    assert out["detail"] and all(len(d["runs"]) == 3 and len(d["wall_runs"]) == 3 and len(d["cpu_to_wall_per_repeat"]) == 3 for d in out["detail"].values())
    for k, d in out["detail"].items():
        assert out["cpu"][k] == sorted(d["runs"])[1]  # the recorded CPU figure is still the median of the three
    sp = quiet.timing_spreads(out, cfg)
    assert set(sp["spreads"]) == set(out["cpu"]) and all(v >= 0 for v in sp["spreads"].values())


# --- the counting rehearsal: the same code, the measured rule, a retry of a PAUSED quiet stage by itself ---------------------------------------------------
def registered_plan_file(tmp: Path, cfg: Any) -> Path:
    pl = TS.plan_of()
    pl.data.update({"caps_provisional": False, "stage_caps": {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}})
    p = tmp / "plan.json"
    p.write_text(json.dumps(core.jsonable(pl.data)))
    return p


def test_the_counting_rehearsal_uses_the_measured_rule_and_retries_a_paused_quiet_stage_by_itself(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(qr.measured_quiet_text(core.repo_root().joinpath(core.CONFIG).read_text()))
    cfg = core.load_config(cfg_path)
    plan = registered_plan_file(tmp_path, cfg)
    run = tmp_path / "run"
    state: dict[str, Any] = {"timing": 0, "throughput": 0, "released": False}
    # the machine is busy once the timing stage has its record (until released): the throughput stage cannot get a quiet reading in its session
    fm = qr.FakeMachine(lambda t: (2.5, 2.5) if (run / "timing" / "timing.json").exists() and not state["released"] else (1.0, 1.0))

    def timing(pl: Any, ctx: Any, *, guard: Any = None, **kw: Any) -> Any:
        state["timing"] += 1
        return spread_ok()

    def throughput(pl: Any, ctx: Any, guard: Any = None) -> Any:
        state["throughput"] += 1
        return {"results": {}}

    monkeypatch.setattr(stages, "measure_timing", timing)
    monkeypatch.setattr(stages, "measure_throughput", throughput)
    monkeypatch.setattr(stages, "require_gates_passed", lambda run_dir: None)
    probe = fm.probe()
    kw: dict[str, Any] = {"quiet_reading": lambda: quiet.quiet_reading(probe=probe, cfg=cfg), "end_fn": lambda s: quiet.end_check(s, probe=probe, cfg=cfg, sleep=fm.sleep), "sleep": fm.sleep, "clock": fm.clock}
    first = rehearsal_real.run_counting(plan, run, repo=ROOT, config_path=cfg_path, chain=("timing", "throughput"), **kw)
    assert first["stages"]["timing"] == "COMPLETE" and first["stages"]["throughput"] == "PAUSED" and first["candidate"]["status"] == "FAILED"  # COMPLETE only when both quiet stages have a quiet run
    assert first["waited_seconds"] == 21600.0 and (state["timing"], state["throughput"]) == (1, 0)
    rows = [json.loads(x) for x in quiet.polls_path(run, "throughput").read_text().splitlines()]
    assert rows[0]["limit_h"] == 180 and rows[0]["failed"] == ["ONE-MINUTE LOAD ABOVE L", "FIVE-MINUTE LOAD ABOVE L"]  # the config's MEASURED limit, not a constant
    timing_manifest = (run / "timing" / "manifest.json").read_bytes()
    state["released"] = True
    second = rehearsal_real.run_counting(plan, run, repo=ROOT, config_path=cfg_path, chain=("timing", "throughput"), resume=True, **kw)
    assert second["stages"]["timing"] == "COMPLETE" and second["stages"]["throughput"] == "COMPLETE" and second["candidate"]["status"] == "COMPLETE"
    assert (state["timing"], state["throughput"]) == (1, 1) and (run / "timing" / "manifest.json").read_bytes() == timing_manifest  # the completed stage was not run again; the paused one was retried by itself
    assert quiet.paused_attempts(run, "throughput") == [1] and quiet.throughput_label(run) == "MEASURED"


def test_the_registered_launch_and_the_counting_rehearsal_reach_the_same_quiet_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both entry points call ``stages.execute_stage`` -> ``quiet.run_alone_stage``, the only code that reads the quiet rule. A spy in each (the registered launch in a child process on a throw-away frozen repository) records the
    same keyword set and the same measured limit; neither runs a measurement."""
    for fn, name in ((stages.cmd_registered, "execute_stage"), (rehearsal_real.run_counting, "execute_stage")):
        assert f"{name}(" in inspect.getsource(fn)
    src = inspect.getsource(stages._execute_stage_body)  # noqa: SLF001
    assert src.count("quiet.run_alone_stage(") == 1 and 'elif stage in ("timing", "throughput"):' in src
    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(qr.measured_quiet_text(core.repo_root().joinpath(core.CONFIG).read_text()))
    cfg = core.load_config(cfg_path)
    seen: list[dict[str, Any]] = []

    def spy(run_dir: Path, stage: str, measure: Any, **kw: Any) -> dict[str, Any]:
        seen.append({"stage": stage, "kw": sorted(kw), "limit": quiet.limit_of(kw["cfg"]), "validate": kw["validate"] is not None, "guarded": kw["guarded"], "cap": kw["cap_seconds"] is not None})
        return {"status": quiet.PAUSED_QUIET, "attempt_record": "x", "paused_attempts": [], "wait_seconds": 0.0, "measure_seconds": 0.0}

    monkeypatch.setattr(quiet, "run_alone_stage", spy)
    plan = registered_plan_file(tmp_path, cfg)
    rehearsal_real.run_counting(plan, tmp_path / "run", repo=ROOT, config_path=cfg_path, chain=("timing",))
    counting = seen[0]
    assert counting["stage"] == "timing" and counting["limit"] == 180 and counting["validate"] is True and counting["cap"] is True
    repo, commit, run = TR.frozen_repo(tmp_path / "frozen")
    code = (
        "import json\nfrom studies.p10is1 import quiet, stages\nseen = []\n"
        "def spy(run_dir, stage, measure, **kw):\n"
        "    seen.append({'stage': stage, 'kw': sorted(kw), 'limit': quiet.limit_of(kw['cfg']), 'validate': kw['validate'] is not None, 'guarded': kw['guarded'], 'cap': kw['cap_seconds'] is not None})\n"
        "    return {'status': quiet.PAUSED_QUIET, 'attempt_record': 'x', 'paused_attempts': [], 'wait_seconds': 0.0, 'measure_seconds': 0.0}\n"
        "quiet.run_alone_stage = spy\n"
        f"rc = stages.main(['registered', 'timing', '--run-dir', {str(run)!r}, '--freeze-commit', {commit!r}])\n"
        "print(json.dumps({'rc': rc, 'seen': seen}))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=repo, env=TR.env_for(repo), capture_output=True, text=True, timeout=600, check=False)  # noqa: S603
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["rc"] == 3 and len(got["seen"]) == 1, (out.stdout[-800:], out.stderr[-800:])
    assert got["seen"][0] == counting  # the same keyword set, the same limit read from the config, the same validation and cap


def test_the_launch_scripts_are_single_commands_with_a_timeout_above_the_deadline_and_no_wrapper_watcher() -> None:
    q = core.load_config()["quiet"]
    session = float(q["session_hours"]) * 3600.0
    for name, waits in (("baseline", 1), ("timing", 2), ("throughput", 1), ("rehearse_counting", 3)):
        text = (ROOT / "studies" / "p10is1" / "launch" / f"{name}.sh").read_text()
        cmds = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("exec ")]
        assert len(cmds) == (2 if name == "rehearse_counting" else 1), name  # (the counting rehearsal has a fresh and a resume form)
        for cmd in cmds:
            assert ">>" in cmd and "2>&1" in cmd, name  # one command, the output in a file
            timeout = int(re.search(r"exec timeout (\d+) ", cmd).group(1))  # type: ignore[union-attr]
            assert timeout > waits * session + (3600 if name == "rehearse_counting" else 0), name  # above every wait of the stage's session
            assert "caffeinate" not in cmd, name  # the watcher is the stage's own child (machine.keep_awake), never a sibling wrapper: P10-I-S5's defect
    assert "baseline_session_hours" in q
    mach = (ROOT / "studies" / "p10is1" / "machine.py").read_text()
    assert '"caffeinate"' not in mach.split("def keep_awake")[0] and "subprocess.Popen([exe, \"-i\", \"-w\"" in mach
    assert 'machine.keep_awake()' in inspect.getsource(stages.cmd_registered) and "keep_awake" in inspect.getsource(baseline.run_baseline.__globals__["machine"].keep_awake) + inspect.getsource(baseline.run_baseline)


@pytest.fixture(autouse=True)
def _canonical_baseline_root_is_a_test_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """The freeze requires the study's canonical baseline root; these tests use synthetic records mirrored into a per-process TEST directory standing in for it, and never touch the real one (F4)."""
    import test_p10is1_quiet_rule as qr

    qr.use_canon(monkeypatch)
