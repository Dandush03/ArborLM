# ruff: noqa: E501
"""P10IS1 fixes for the independent audit of commit 0285825 (findings F1-F14). Each test fails on the old behaviour and stubs nothing it tests: registered workers in a frozen repository with several threads set beforehand,
cumulative caps and the ledger charged on a failed stage, the calibration on the worker pool (bit-identical to one worker, a cumulative cap with PAUSED and resume, the i* > 4.0 stop), either-panel dependence, row 4(b)
without MC-T, the dense-at-saturation block at U_run/2, the non-blocking memory check, a missing ladder decision as a status, a non-finite cell that is not an item error, and the printed departures. Test seeds only."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import test_p10is1_calibrate_engine as TCE  # noqa: E402
import test_p10is1_rehearsal as TR  # noqa: E402

from arborlm.io import read_json  # noqa: E402
from studies.p10is1 import (  # noqa: E402
    adapter,
    analysis,
    calibrate_engine,
    core,
    items,
    quiet,
    rehearsal,
    report,
    runner,
    stages,
    synthetic,
)
from studies.p10is1 import labels as L  # noqa: E402
from studies.p10is1 import plan as planmod  # noqa: E402
from studies.p10s1 import train as s1train  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- F1: registered workers ---------------------------------------------------------------------------------------------------------------
@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record is macOS arm64")
def test_f1_registered_train_evaluate_and_baseline_workers_pass_the_platform_check_with_several_threads_set(tmp_path: Path) -> None:
    import subprocess

    repo, commit, run = TR.frozen_repo(tmp_path)
    plan = read_json(repo / core.PLAN)
    cell = next(c for c in plan["cells"] if c["arm"] == "F-OQ" and c["slots"] == 1024 and c["draw"] == 1)
    base = ["--stage", "x", "--label", cell["label"], "--run-dir", str(run), "--plan", str(repo / core.PLAN), "--mode", "registered", "--freeze-commit", commit, "--repo", str(repo)]
    env = TR.env_for(repo, OMP_NUM_THREADS="8", MKL_NUM_THREADS="8", VECLIB_MAXIMUM_THREADS="8")
    for kind, extra in (("train", ["--to", "8"]), ("evaluate", ["--updates", "8"]), ("baseline", ["--draw", "1", "--facts", str(cell["facts"])])):
        out = subprocess.run([sys.executable, "-m", "studies.p10is1.stages", "work", kind, *base, "--done", str(tmp_path / f"{kind}.done"), *extra], cwd=repo, env=env, capture_output=True, text=True, timeout=600, check=False)
        # the old worker checked the platform BEFORE configuring the process and exited 75 (PAUSED — IDENTITY) here, so no registered task could ever start. Now it passes every precondition and the plan identity and starts the
        # task: in a throw-away repository there is no corpus, so the task stops on the missing file (an environment error, 76), having generated nothing and trained nothing
        assert out.returncode == runner.ENVIRONMENT_EXIT, (kind, out.returncode, out.stderr[-600:])
        assert "FileNotFoundError" in out.stderr and "not the platform of record" not in out.stderr
    assert not (run / "train").exists() and not (run / "evaluate").exists()
    syn = subprocess.run([sys.executable, "-m", "studies.p10is1.stages", "work", "train", *base, "--done", str(tmp_path / "s.done"), "--to", "8", "--synthetic"], cwd=repo, env=env, capture_output=True, text=True, timeout=600, check=False)
    assert syn.returncode == core.IDENTITY_EXIT and "never uses the synthetic" in syn.stderr  # a registered task cannot run on the synthetic backbone


# --- F2 and F12: caps are cumulative, the ledger is charged when a stage raises, a non-finite cell is not an item error -----------------------------------
def tiny_run(tmp: Path) -> tuple[planmod.Plan, items.Ctx, Path, argparse.Namespace, Path]:
    root = tmp / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    return pl, ctx, run, argparse.Namespace(freeze_commit=None, synthetic=True), cfg_path


def test_f2_pool_caps_are_cumulative_across_rounds(tmp_path: Path) -> None:
    pl, ctx, run, args, cfg_path = tiny_run(tmp_path)
    label = next(c["label"] for c in pl.data["cells"] if c["arm"] == "F-OQ" and c["slots"] == 4096 and c["draw"] == 1)
    extra = ["--synthetic", "--config", str(cfg_path), "--repo", str(ROOT)]
    pool = stages.Pool(pl, run, pl.path, args, ctx, inline=False, workers=1, cap_seconds=0.8, extra_argv=extra)
    first = pool.run("train", [(label, "train", {"to": 8})])
    assert first[f"train|{label}|" + json.dumps({"to": 8}, sort_keys=True)]["status"] == runner.KILLED_CAP and pool.seconds >= 0.8
    t0 = time.monotonic()
    second = pool.run("train", [(label, "train", {"to": 16})])  # the same pool: the cap is spent, the next round gets what is LEFT (nothing), not a fresh 0.8 s
    assert time.monotonic() - t0 < 0.6 and {v["status"] for v in second.values()} == {runner.NOT_STARTED}


def test_f2_and_f12_a_failed_ladder_round_charges_the_ledger_and_a_non_finite_cell_is_not_an_item_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pl, ctx, run, args, _ = tiny_run(tmp_path)
    stages.execute_stage("gates", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    (run / "timing").mkdir(exist_ok=True)
    core.write_record(run / "timing" / "timing.json", {**core.envelope("timing"), "cpu": {}})
    real = s1train.Trainer.step

    def boom(self: Any, batch: Any) -> Any:
        if self.update + 1 >= 3:
            raise ValueError("non-finite task loss at update 3")
        return real(self, batch)

    monkeypatch.setattr(s1train.Trainer, "step", boom)
    with pytest.raises(core.StageRefused, match="could not finish the round"):
        stages.execute_stage("ladder", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    led = stages.ledger_of(pl, run)
    assert led.charged("ladder") > 0.0  # charged in a finally: a raising stage used to charge nothing, so every resume got the full cap again
    assert stages.item_errors(run) == []  # FAILED — NON-FINITE is the cell's own record (section 14), not also an item error
    failed = stages.failed_cells(run)
    assert failed and all("NON-FINITE" in f for f in failed)
    res = stages.do_analysis(ctx, pl, run)  # the analysis does not refuse (no item error): it prints INCOMPLETE with the failed cells and no outcome
    assert res["status"] == "INCOMPLETE" and res["failed_cells"] and set(res["lines"].values()) == {"INCOMPLETE"}
    # a second invocation finds the cells kept (not re-run), still no item error
    monkeypatch.setattr(s1train.Trainer, "step", real)
    with pytest.raises(core.StageRefused):
        stages.execute_stage("ladder", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    assert stages.item_errors(run) == [] and led.charged("ladder") > 0.0


# --- F4: calibration on the worker pool ------------------------------------------------------------------------------------------------------
def pool_engine(tmp: Path, workers: int, ledger: core.Ledger | None = None) -> calibrate_engine.RealEngine:
    tmp.mkdir(parents=True, exist_ok=True)
    cfgp = TCE.tiny_cfg_path(tmp)
    ctx = items.Ctx("calibration", tmp / "sealed", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfgp)
    return calibrate_engine.RealEngine(ctx, core.load_config(cfgp), TCE.FACTS_MAP, workers=workers, ledger=ledger, env={"PYTHONPATH": str(ROOT)})


def test_f4_the_pool_gives_bit_identical_results_to_one_worker_and_workers_are_single_thread_processes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    reqs = [("F-OQ|1024", 0.003, 16), ("T-OQ|1024", 0.003, 16), ("H8|1024", 0.01, 16)]
    a, b = pool_engine(tmp_path / "a", 1), pool_engine(tmp_path / "b", 3)
    a.prefetch(reqs)
    b.prefetch(reqs)
    ra, rb = [a.measure(*r) for r in reqs], [b.measure(*r) for r in reqs]
    assert ra == rb  # exact equality of every float: the same runs in another order, on another number of processes
    files_a = sorted(p.relative_to(a.ctx.run_dir) for p in (a.ctx.run_dir / "evaluate").rglob("*.json"))
    assert files_a and files_a == sorted(p.relative_to(b.ctx.run_dir) for p in (b.ctx.run_dir / "evaluate").rglob("*.json"))
    for rel in files_a:
        assert read_json(a.ctx.run_dir / rel)["reads"] == read_json(b.ctx.run_dir / rel)["reads"]
    assert len(list((a.ctx.run_dir / "jobs").glob("*.done.json"))) == 6 and len(a.runs) == 6  # six jobs, each a worker process
    # a finished job is not run again
    n = len(b.runs)
    b.prefetch(reqs)
    assert len(b.runs) == n


def test_f4_the_cumulative_cap_pauses_and_a_resume_gets_what_is_left(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    led_path = tmp_path / "sealed" / "ledger.json"
    first = pool_engine(tmp_path, 1, core.Ledger(led_path, 0.2))  # a 0.2-second cap (a worker needs about a second on an idle machine: a one-second cap was a race): the first worker cannot finish
    with pytest.raises(calibrate_engine.CalibrationPaused):
        first.prefetch([("F-OQ|1024", 0.003, 16)])
    assert core.Ledger(led_path, 0.2).charged("calibration") >= 0.15 and not list((first.ctx.run_dir / "evaluate").rglob("*.json"))
    with pytest.raises(core.LedgerRefused):
        pool_engine(tmp_path, 1, core.Ledger(led_path, 0.2)).prefetch([("F-OQ|1024", 0.003, 16)])  # nothing left: PAUSED, not run
    resumed = pool_engine(tmp_path, 1, core.Ledger(led_path, 600.0))  # the lead extends the cap by a decision on cost: the same records resume
    resumed.prefetch([("F-OQ|1024", 0.003, 16)])
    assert resumed.measure("F-OQ|1024", 0.003, 16).readout_a_use >= 0.0 and core.Ledger(led_path, 600.0).charged("calibration") > 1.0


def test_f4_cmd_calibrate_records_paused_and_charges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    args = argparse.Namespace(sealed_dir=str(tmp_path / "sealed"), run_dir=str(tmp_path / "run"), workers="1")
    rc = calibrate_engine.cmd_calibrate(args, make_engine=lambda ctx: pool_engine(tmp_path, 1, core.Ledger(Path(ctx.run_dir) / "l.json", 1.0)))
    assert rc == 4
    st = read_json(tmp_path / "run" / "calibration_status.json")
    assert st["status"] == "PAUSED" and st["charged_hours"] > 0 and "reason" in st and not (tmp_path / "run" / "calibration_public.json").exists()  # no public record until it is complete


def test_f4_a_ladder_search_stops_as_soon_as_a_view_exceeds_4_bits(tmp_path: Path) -> None:
    """ADR-0024 section 7.2 item 4: in the calibration 'full' also needs i*(U) <= 4.0 on every view and i* never falls, so a view above 4.0 bits fixes the outcome: no further ladder point is run."""
    eng, ctx = TCE.make_engine(tmp_path)
    for k in (1, 2):
        spec = eng.spec("F-OQ", 8192, 1024, k, 0.003, ladder_name="8K/1K")
        out = adapter.cell_dir(ctx.run_dir, spec["label"])
        (out / "snapshots" / "u0000032").mkdir(parents=True)
        (out / "snapshots" / "u0000032" / "snapshot.json").write_text("{}")
        (out / "snapshots" / "u0000032" / "model.pt").write_bytes(b"x")
        for u in (16, 32):
            pan = {p: {"n": 128, "correct": 126, "useful": 125} for p in core.PANELS}  # a_use 0.977: about 4.5 bits
            core.write_record(ctx.eval_path(spec["label"], u), {**core.envelope("eval"), "label": spec["label"], "update": u, "reads": {"main": {"panels": pan}}})
    t0 = time.monotonic()
    series = eng.ladder_batch([("8K/1K", "F-OQ", 0.003, 192)])[("8K/1K", "F-OQ")]
    assert set(series[(1, "A")]) == {16, 32} and max(series[(1, "A")].values()) > 4.0 and time.monotonic() - t0 < 2.0  # stopped after the first point (the old search went on to the ceiling, 192)
    assert eng.runs == []  # nothing was trained: the second point was never requested
    from studies.p10is1 import calibrate

    assert calibrate.arm_calibrated_length(series, 192, eng.cfg) is None  # not full: an outcome of the registered table (F-OQ not full at its ceiling returns to the lead)


# --- F5: either-panel dependence ------------------------------------------------------------------------------------------------------------------
def _panel_a(draws: set[int], reads: tuple[str, ...] = ("main", "ivf")) -> Any:
    def ex(a: str, f: int, n: int, d: int, u: int, r: str, panel: str) -> int:
        return 2000 if (a, f, n, u) == ("F-OQ", 8192, 4096, 4096) and d in draws and r in reads and panel == "A" else 0  # panel A ONLY

    return ex


def test_f5_a_dependence_failure_on_either_panel_blocks_the_step_on_both() -> None:
    res = analysis.analyze(synthetic.build(excess=_panel_a({3})))
    c1 = res["capacity"]["arms"]["F-OQ"]["steps"]["C1"]
    assert c1["verdicts"][2] == "DEPENDENCE_FAILED"  # it used to be PANEL-DISAGREE (panel B passed)
    assert c1["replicates"][2]["detail"]["panels"]["A"]["verdict"] == c1["replicates"][2]["detail"]["panels"]["B"]["verdict"] == "DEPENDENCE_FAILED"
    two = analysis.analyze(synthetic.build(excess=_panel_a({3, 4})))
    arms = two["capacity"]["arms"]
    assert arms["F-OQ"]["steps"]["C1"]["class"] == "DEPENDENCE_FAILED" and arms["F-OQ"]["class"] == "DEPENDENCE_FAILED" and arms["F-OQ-IVF"]["class"] == "DEPENDENCE_FAILED"
    # no supported arm is left: the line is INCONCLUSIVE (the per-panel reading gave NOT REPLICATED steps and a CAPACITY_ONE_TRANSITION arm, and a positive could survive on the other reads)
    assert two["capacity"]["outcome"]["label"] == "CAPACITY-INCONCLUSIVE"
    only_main = analysis.analyze(synthetic.build(excess=_panel_a({3, 4}, reads=("main",))))
    assert only_main["capacity"]["arms"]["F-OQ-IVF"]["class"] == "CAPACITY_SUPPORTED" and only_main["capacity"]["outcome"]["post_hoc_only"] is True  # the index read has its own record


# --- F8: row 4(b) without MC-T -----------------------------------------------------------------------------------------------------------------
def test_f8_the_efficiency_negative_stays_reachable_through_e_a_when_mc_t_is_not_measured() -> None:
    lv = synthetic.positive_levels()
    lv[("D-OQ", 2048, 4096)] = (4.0, 512)  # D-OQ reaches 3 bits in a few hundred updates at 2K/4K
    lv[("D-OQ", 8192, 16384)] = (4.0, 512)
    res = analysis.analyze(synthetic.build(levels=lv, cpu=None))
    eff = res["efficiency"]
    assert eff["readings"]["E-A"]["arms"]["F-OQ"]["class"] == "EFFICIENCY_SUPPORTED" and set(eff["readings"]["E-A"]["arms"]["F-OQ"]["dense_speed"].values()) == {"DENSE FASTER"}
    assert eff["outcome"]["label"] == "EFFICIENCY-NEGATIVE" and eff["outcome"]["e_a_only"] is True  # row 4 (b) read over the readings that exist; it was INCONCLUSIVE
    both = analysis.analyze(synthetic.build(levels=lv))["efficiency"]["outcome"]
    assert both["label"] == "EFFICIENCY-NEGATIVE" and both["e_a_only"] is False
    unreached = analysis.analyze(synthetic.build(cpu=None))["efficiency"]["outcome"]
    assert unreached["label"] != "EFFICIENCY-POSITIVE"  # the positive stays unreachable without E-T


# --- F9: dense at saturation blocks on U_run/2 ----------------------------------------------------------------------------------------------------
def test_f9_store_holds_more_is_blocked_by_d_oq_dependence_at_u_run_over_2() -> None:
    # 32K/4K at U_run 131,072: D-OQ is full at 98,304 (its own length), so its own length/2 is 49,152 while U_run/2 is 65,536. D-OQ fails DEP-c at 65,536 in draw 1.
    def ex(a: str, f: int, n: int, d: int, u: int, r: str, panel: str) -> int:
        return 2000 if (a, f, n, d, u, r) == ("D-OQ", 32768, 4096, 1, 65536, "main") else 0

    clean = analysis.analyze(synthetic.build())["capacity"]["arms"]["F-OQ"]["dense_at_saturation"]["32K/4K"]
    assert clean["label"] == "STORE HOLDS MORE AT SATURATION"
    blocked = analysis.analyze(synthetic.build(excess=ex))["capacity"]["arms"]["F-OQ"]["dense_at_saturation"]["32K/4K"]
    assert blocked["label"] == "SAME AT SATURATION" and "D-OQ DEP" in blocked["failing"]  # the old code read 49,152 and kept STORE HOLDS MORE


# --- F10: the memory check does not block the runner ------------------------------------------------------------------------------------------------
def test_f10_short_memory_pauses_the_pending_tasks_while_running_workers_stay_supervised(tmp_path: Path) -> None:
    done = tmp_path / "t1.done"
    t1 = runner.Task("t1", (sys.executable, "-c", f"import time, pathlib; time.sleep(1.0); pathlib.Path({str(done)!r}).write_text('x')"), done, tmp_path / "t1.failed", tmp_path / "t1.log")
    t2 = runner.Task("t2", (sys.executable, "-c", "pass"), tmp_path / "t2.done", tmp_path / "t2.failed", tmp_path / "t2.log")
    seq = iter([True])  # memory covers the guard once (the first worker starts), then it does not
    began = time.monotonic()
    out, _ = runner.run_tasks([t1, t2], workers=2, cap_seconds=30, rss_worker_bytes=3 * 1024**3, rss_aggregate_bytes=18 * 1024**3, memory_ok=lambda: next(seq, False), memory_retry=0.05, memory_max=0.4, poll=0.05)
    assert out["t1"]["status"] == runner.COMPLETED  # the running worker was supervised to its end
    assert out["t2"]["status"] == runner.PAUSED_ENVIRONMENT and "PAUSED — ENVIRONMENT" in out["t2"]["reason"]
    assert time.monotonic() - began < 10 and not (tmp_path / "t2.failed").exists()
    assert runner.stage_status(out) == "PAUSED"
    text = "Pages free: 10.\nPages inactive: 10.\nPages purgeable: 0.\nPages speculative: 0.\nMach Virtual Memory Statistics: (page size of 4096 bytes)\n"
    assert quiet.memory_ok_once(20 * 4096, reader=lambda: text) and not quiet.memory_ok_once(21 * 4096, reader=lambda: text)


# --- F11: a missing ladder decision is a status ------------------------------------------------------------------------------------------------------
def test_f11_a_missing_ladder_decision_is_incomplete_not_a_crash_and_paused_stages_are_seen(tmp_path: Path) -> None:
    reg = synthetic.build()
    reg.ladder_stops = {}
    res = analysis.analyze(reg)
    assert res["status"] == "INCOMPLETE" and res["missing_ladder_decisions"] == ["2K/256", "32K/4K", "8K/1K"] and set(res["lines"].values()) == {"INCOMPLETE"}
    reg.status = {**reg.status, "paused": ["ladder: PAUSED"]}
    assert analysis.analyze(reg)["status"] == "PAUSED"
    pl, ctx, run, _args, _ = tiny_run(tmp_path)
    core.write_record(run / "ladder" / "manifest.json", {**core.envelope("stage_manifest"), "stage": "ladder", "status": "PAUSED"})
    assert stages.build_registry(ctx, pl, run).status["paused"] == ["ladder: PAUSED"]  # the registry carries the PAUSED stage
    assert analysis.analyze(stages.build_registry(ctx, pl, run))["status"] == "PAUSED"


# --- F6 and F7 -----------------------------------------------------------------------------------------------------------------------------------
def test_f6_the_measuring_rehearsal_uses_the_configs_timing_figures_by_default(tmp_path: Path) -> None:
    real = core.load_config()
    assert (real["quiet"]["timing_warmup_updates"], real["quiet"]["timing_updates"], real["quiet"]["timing_repeats"]) == (32, 256, 3)
    pl, ctx, run, _a, _c = tiny_run(tmp_path)
    out = rehearsal_real_measure(pl, ctx)
    assert out["timing_config"] == {"warmup_updates": 2, "updates": 4, "repeats": 1}  # the (tiny) config's figures, not eight updates and one repeat
    k = out["by_workers"]["2"]
    assert set(k["evaluate"]) == set(k["train"]) and k["peak_rss_bytes_per_worker"] > 0 and {"gates", "baselines"} <= set(k["fixed"])


def rehearsal_real_measure(pl: planmod.Plan, ctx: items.Ctx) -> dict[str, Any]:
    from studies.p10is1 import rehearsal_real

    return rehearsal_real.measure_rates(pl, ctx, pl.path, [2], synthetic_data=True, eval_update=4)


# --- F13: the readings taken here are printed ---------------------------------------------------------------------------------------------------------
def test_f13_the_report_prints_the_departures_and_readings_taken_here() -> None:
    text = report.render(analysis.analyze(synthetic.build()))
    sec = text[text.index("## Readings taken here") :]
    for needle in ("DEPARTURE (stricter for the store): a dependence failure on EITHER panel", "DENSE NOT FASTER is not established in a replicate in which D-OQ failed", "off the grid", "2026-11-18", "recomputed from the data"):
        assert needle in sec, needle
    assert L.untagged_positive_labels(text) == []


def test_f8_label_level_row_4b_over_the_readings_that_exist() -> None:
    SUP, NS = "EFFICIENCY_SUPPORTED", "EFFICIENCY_NOT_SUPPORTED"
    out = L.efficiency_outcome({"E-A": {"F-OQ": SUP, "T-OQ": NS}}, {"E-A": {"F-OQ": [L.DENSE_FASTER]}}, mct_measured=False)
    assert out["label"] == L.EFFICIENCY_NEGATIVE and out["e_a_only"] is True
    assert L.efficiency_outcome({"E-A": {"F-OQ": SUP, "T-OQ": NS}}, {"E-A": {"F-OQ": [L.DENSE_NOT_FASTER]}}, mct_measured=False)["label"] == L.EFFICIENCY_INCONCLUSIVE  # no positive without E-T


_ = os


# --- N1: the calibration pool applies the machine-wide memory check -----------------------------------------------------------------------------------
def test_n1_the_calibration_pool_applies_the_memory_check_and_pauses_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    eng = pool_engine(tmp_path, 2)
    assert isinstance(eng.memory_ok(), bool) and eng.memory_retry == 600.0 and eng.memory_max == 6 * 3600.0  # the default is the machine-wide vm_stat check of section 16.1, every 10 minutes for at most 6 hours
    eng.memory_ok = lambda: False  # the machine's memory does not cover the aggregate guard
    eng.memory_retry, eng.memory_max = 0.05, 0.3
    t0 = time.monotonic()
    with pytest.raises(calibrate_engine.CalibrationPaused) as exc:
        eng.prefetch([("F-OQ|1024", 0.003, 16)])
    assert set(exc.value.statuses.values()) == {runner.PAUSED_ENVIRONMENT} and time.monotonic() - t0 < 30
    assert not list((eng.ctx.run_dir / "jobs").glob("*.log")) and not list((eng.ctx.run_dir / "evaluate").rglob("*.json"))  # no worker was started
    eng.memory_ok = lambda: True  # memory returns: the same engine resumes and finishes the same jobs
    eng.prefetch([("F-OQ|1024", 0.003, 16)])
    assert eng.measure("F-OQ|1024", 0.003, 16).readout_a_use >= 0.0


# --- N2: H_c is in the registered ledger, every cap is checked against the projection -------------------------------------------------------------------
def test_n2_the_registered_ledger_carries_h_c_and_the_total_binds_on_the_true_total(tmp_path: Path) -> None:
    pl = planmod.Plan({**core.envelope("freeze_plan"), "mode": "registered", "cells": [], "params": {}, "projection": {"h_charged_hours": 12.0}, "stage_caps": {"train_hours": 14.0, "evaluate_hours": 1.0, "total_hours": 30.0}})
    run = tmp_path / "run"
    led = stages.ledger_of(pl, run)
    assert led.charged("pre-freeze") == 12.0 * 3600 and led.remaining() == 18.0 * 3600  # the registered stages may spend 30 - 12 h, not 30 h
    assert stages.stage_cap_seconds(pl, "train", led) == 14.0 * 3600
    led.charge("train", "r", 14.0 * 3600)
    assert stages.stage_cap_seconds(pl, "evaluate", led) == 1.0 * 3600 and stages.stage_cap_seconds(pl, "train", led) == 0.0
    led.charge("evaluate", "r", 1.0 * 3600)
    led.charge("timing", "r", 2.0 * 3600)
    assert stages.ledger_of(pl, run).charged() == (12.0 + 14.0 + 1.0 + 2.0) * 3600  # a second call does not charge H_c again
    big = planmod.Plan({**pl.data, "stage_caps": {"train_hours": 30.0, "evaluate_hours": 1.0, "total_hours": 30.0}})
    assert stages.stage_cap_seconds(big, "train", stages.ledger_of(big, run)) == 1.0 * 3600  # train's own cap (30 h) is cut to what the total has left (30 - 29 h)


def test_n2_the_freeze_checks_every_stage_cap_against_the_projection(tmp_path: Path) -> None:
    import re

    import test_p10is1_stages as TS

    repo, rpath = TS.projected_candidate(tmp_path)
    plan = read_json(repo / core.PLAN)
    caps = plan["projection"]["caps"]["config_caps"]
    assert set(caps) == {"train_hours", "evaluate_hours", "timing_hours", "throughput_hours", "analysis_hours", "rehearsal_hours", "total_hours"} and plan["projection"]["h_charged_hours"] == 4.0
    with pytest.raises(core.StageRefused, match="gate G9"):
        TS.freeze.cmd_freeze(TS.rehearsal_record(rpath, repo))  # consistent: the freeze reaches G9
    cfgp = repo / core.CONFIG
    text = cfgp.read_text()
    for key in ("timing_hours", "throughput_hours", "analysis_hours", "rehearsal_hours"):
        cfgp.write_text(re.sub(rf"^{key} = .*$", f"{key} = 99.0", text, flags=re.M))
        with pytest.raises(core.StageRefused, match="are not the caps the projection's rule gives"):
            TS.freeze.cmd_freeze(TS.rehearsal_record(rpath, repo))
    cfgp.write_text(text)


def test_projection_prints_the_measured_slowdown_per_item_beside_the_rule_figure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import test_p10is1_stages as TS

    from studies.p10is1 import freeze

    repo = TS.mini_repo(tmp_path / "m")
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(TS.CAL))
    keys = [f"{a}|{n}" for a in core.ARMS for n in (256, 1024, 4096, 16384, 32768)]
    by_item = {k: 1.3 + 0.01 * i for i, k in enumerate(keys)}
    by_item["D-OQ|1024"] = 1.95  # the worst item: the rule multiplies EVERY item by it
    rates = {"by_workers": {"6": {"train": dict.fromkeys(keys, 0.001), "evaluate": dict.fromkeys(keys, 0.01), "contention": 1.95, "contention_by_item": by_item, "contention_worst_item": "D-OQ|1024", "fixed": {"gates": 60.0, "timing": 100.0}}}}
    rf = tmp_path / "rates.json"
    rf.write_text(json.dumps(rates))
    led = core.Ledger(tmp_path / "calib-ledger.json", 1e9)
    led.charge("calibration", "c", 7200.0)
    out = tmp_path / "projection.json"
    rc = freeze.cmd_project(argparse.Namespace(repo=str(repo), calibration=str(cal), rates=str(rf), charged_hours=1.0, ledger=[str(tmp_path / "calib-ledger.json")], out=str(out)))
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    proj = read_json(out)
    assert rc == 0 and proj["h_charged_hours"] == 3.0 and proj["h_charged_breakdown"]["typed_hours"] == 1.0  # 1 typed + 2 from the calibration ledger
    sd = proj["measured_slowdown"]
    assert sd["rule_value_used_for_every_item"] == 1.95 and sd["rule_worst_item"] == "D-OQ|1024" and sd["by_item"] == by_item and sd["minimum"] == 1.3 and sd["median"] > 1.3
    assert printed["slowdown_rule_worst_item"] == 1.95 and printed["slowdown_by_item"] == by_item and printed["h_charged_hours"] == 3.0
    assert set(proj["caps"]["config_caps"]) >= {"timing_hours", "throughput_hours", "analysis_hours"}


def test_prefreeze_stages_charge_a_ledger(tmp_path: Path) -> None:
    run = tmp_path / "gen" / "run"
    led = core.prefreeze_ledger(run)
    led.charge("generate", "run", 90.0)
    led.charge("qualify", "run", 30.0)
    assert core.read_ledger_seconds(run.parent / "P10IS1-prefreeze-ledger.json") == 120.0


@pytest.fixture(autouse=True)
def _no_real_baseline_root(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """The freeze checks the committed baseline against the study's real baseline root when that exists on this machine; these tests use synthetic records and never depend on it (F4)."""
    monkeypatch.setenv("P10IS1_BASELINE_ROOT", str(tmp_path_factory.mktemp("no_baseline_root") / "absent"))
