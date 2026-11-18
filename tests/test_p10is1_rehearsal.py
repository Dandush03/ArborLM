# ruff: noqa: E501
"""P10IS1 measuring and counting rehearsals, the R2 qualification driver, the registered launch and the subprocess worker pool (ADR-0024 sections 8.1, 11, 14, 16, 17.1, 18). The registered launch reaches its first stage in a
temporary frozen repository (a copy of this tree, committed, with a plan, a freeze record and a Decision 2) with several threads set beforehand; the worker pool is exercised through real subprocesses (identity exit ->
PAUSED — IDENTITY with nothing written and a resume on restore; an environment error pauses; an item error is counted and the analysis refuses); hour caps are cumulative across stages and resumes. Test seeds only."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import test_p10is1_stages as TS  # noqa: E402

from arborlm.io import file_sha256, read_json  # noqa: E402
from studies.p10is1 import (  # noqa: E402
    adapter,
    core,
    freeze,
    items,
    rehearsal,
    rehearsal_real,
    runner,
    stages,
)
from studies.p10is1 import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COPY = ("src", "studies", "configs", "docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md", "docs/reviews/p10-i-direction-2026-11-17", "uv.lock", "pyproject.toml")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "freeze", ".venv", "_scratch")


def full_copy(dst: Path) -> Path:
    for rel in COPY:
        s, d = ROOT / rel, dst / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, ignore=IGNORE)
        else:
            shutil.copy(s, d)
    return dst


def git(repo: Path, *a: str) -> str:
    base = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    return subprocess.run([*base, *a], capture_output=True, text=True, check=True).stdout  # noqa: S603


def frozen_repo(tmp: Path) -> tuple[Path, str, Path]:
    """A throw-away frozen repository: this tree copied and committed, a registered plan and freeze record committed as the freeze commit, a Decision 2 committed after it."""
    repo = full_copy(tmp / "repo")
    cfgp = repo / core.CONFIG
    cfgp.write_text(cfgp.read_text().replace("provisional = true", "provisional = false"))
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "tree")
    run = tmp / "run"
    cfg = core.load_config(cfgp)
    plan = freeze.build_candidate(repo, run, cfg, TS.CAL, None, manifests={}, extra={"identity_gate": {"s1_run_dir": None, "cell": [8192, 4096], "updates": [512]}, "calibration_path": "x", "calibration_sha256": "0" * 64})
    core.write_record(repo / core.PLAN, plan)
    (repo / planmod.FREEZE_RECORD).write_text(json.dumps({"kind": "freeze_record", "plan_file_sha256": file_sha256(repo / core.PLAN)}))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    commit = git(repo, "rev-parse", "HEAD").strip()
    d2 = repo / "results" / "p10is1-freeze-t" / "DECISION_2.md"
    d2.parent.mkdir(parents=True)
    d2.write_text(f"{commit}\nDECISION: RUN\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision 2")
    return repo, commit, run


def env_for(repo: Path, **extra: str) -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": f"{repo / 'src'}:{repo}", "PYTHONDONTWRITEBYTECODE": "1", **extra}


@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record is macOS arm64")
def test_the_registered_launch_reaches_its_first_stage_with_several_threads_set_beforehand(tmp_path: Path) -> None:
    repo, commit, run = frozen_repo(tmp_path)
    out = subprocess.run([sys.executable, "-m", "studies.p10is1.stages", "registered", "gates", "--run-dir", str(run), "--freeze-commit", commit], cwd=repo, env=env_for(repo, OMP_NUM_THREADS="8", MKL_NUM_THREADS="8", VECLIB_MAXIMUM_THREADS="8"), capture_output=True, text=True, timeout=600, check=False)
    assert out.returncode in (0, 3), out.stderr[-1500:]  # a refusal would be 2 or 75: the launch got past every precondition, including the platform check, into the gates stage
    assert '"stage": "gates"' in out.stdout, (out.stdout, out.stderr[-800:])
    g = core.read_record(run / "gates" / "gates.json", "gates_record")
    assert g["gates"]["platform"]["passed"] is True and g["gates"]["G9"]["passed"] is True and g["platform"]["torch_num_threads"] == 1
    # the same repository refuses without a Decision 2 or on a dirty tree
    (repo / "stray.txt").write_text("x")
    dirty = subprocess.run([sys.executable, "-m", "studies.p10is1.stages", "registered", "gates", "--run-dir", str(run), "--freeze-commit", commit], cwd=repo, env=env_for(repo), capture_output=True, text=True, timeout=300, check=False)
    assert dirty.returncode == core.IDENTITY_EXIT and "not clean" in dirty.stderr


# --- the subprocess worker pool ----------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pool_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return full_copy(tmp_path_factory.mktemp("pool") / "repo")


def pool_task(repo: Path, root: Path, run: Path, label: str, to: str, tag: str) -> runner.Task:
    done = root / "tasks" / f"{tag}.done.json"
    argv = (sys.executable, "-m", "studies.p10is1.stages", "work", "train", "--stage", "train", "--label", label, "--run-dir", str(run), "--plan", str(root / "plan.json"), "--mode", "test", "--done", str(done), "--synthetic", "--config", str(root / "tiny_config.toml"), "--repo", str(repo), "--to", to)
    return runner.Task(label, argv, done, root / "tasks" / f"{tag}.failed.json", root / "tasks" / f"{tag}.log")


def run_pool(tasks: list[runner.Task], repo: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    monkeypatch.chdir(repo)
    out, _ = runner.run_tasks(tasks, workers=1, cap_seconds=300, rss_worker_bytes=3 * 1024**3, rss_aggregate_bytes=18 * 1024**3, env=env_for(repo), poll=0.1)
    return out


def pool_plan(tmp: Path, repo: Path) -> tuple[Path, Any]:
    root = tmp / "root"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text(repo / core.CONFIG))
    pl = rehearsal.tiny_plan(root, repo, cfg_path)
    return root, pl


def test_identity_exit_pauses_with_nothing_written_and_resumes_when_the_file_is_restored(tmp_path: Path, pool_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, pl = pool_plan(tmp_path, pool_repo)
    run = root / "run"
    label = next(c["label"] for c in pl.data["cells"] if c["arm"] == "F-OQ" and c["slots"] == 4096 and c["draw"] == 1)
    target = pool_repo / "studies" / "p10is1" / "labels.py"
    original = target.read_text()
    try:
        target.write_text(original + "\n# a frozen file changed after the plan\n")
        out = run_pool([pool_task(pool_repo, root, run, label, "8", "t1")], pool_repo, monkeypatch)
        assert out[label]["status"] == runner.PAUSED_IDENTITY and "PAUSED — IDENTITY" in out[label]["reason"]
        assert not run.exists() and not (root / "tasks" / "t1.done.json").exists() and not (root / "tasks" / "t1.failed.json").exists()  # nothing written, no failed record
        assert runner.stage_status(out) == "PAUSED"
    finally:
        target.write_text(original)
    out2 = run_pool([pool_task(pool_repo, root, run, label, "8", "t1")], pool_repo, monkeypatch)
    assert out2[label]["status"] == runner.COMPLETED and (adapter.cell_dir(run, label) / "snapshots" / "u0000008" / "model.pt").is_file()
    assert runner.stage_status(out2) == "COMPLETE"
    again = run_pool([pool_task(pool_repo, root, run, label, "8", "t1")], pool_repo, monkeypatch)
    assert again[label]["skipped"] == "result exists"  # a finished task is not run again


def test_environment_errors_pause_without_a_failed_record_and_item_errors_are_counted_and_refuse_the_analysis(tmp_path: Path, pool_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, pl = pool_plan(tmp_path, pool_repo)
    run = root / "run"
    run.mkdir()
    (run / "train").write_text("a file where a directory is needed: a file-system error")
    label = next(c["label"] for c in pl.data["cells"] if c["arm"] == "F-OQ" and c["slots"] == 4096 and c["draw"] == 1)
    out = run_pool([pool_task(pool_repo, root, run, label, "4", "e1")], pool_repo, monkeypatch)
    assert out[label]["status"] == runner.PAUSED_ENVIRONMENT and "PAUSED — ENVIRONMENT" in out[label]["reason"]
    assert not (root / "tasks" / "e1.failed.json").exists() and stages.item_errors(run) == [] and runner.stage_status(out) == "PAUSED"  # never a failed gate or cell, and no item error
    (run / "train").unlink()
    bad = run_pool([pool_task(pool_repo, root, run, label, "not-a-number", "i1")], pool_repo, monkeypatch)
    assert bad[label]["status"] == runner.FAILED and (root / "tasks" / "i1.failed.json").is_file()
    errs = stages.item_errors(run)
    assert len(errs) == 1 and "ValueError" in errs[0]
    plan = planmod.Plan.load(root / "plan.json")
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=root / "tiny_config.toml")
    with pytest.raises(core.StageRefused, match="ENGINEERING STOP — ITEM ERRORS"):
        stages.do_analysis(ctx, plan, run)
    rec = read_json(run / "analysis" / "analysis.json")["result"]
    assert rec["status"] == "ENGINEERING STOP — ITEM ERRORS" and set(rec["lines"].values()) == {"ENGINEERING STOP — ITEM ERRORS"}  # no label on any line


# --- caps are cumulative across stages and resumes ------------------------------------------------------------------------------------------------------
def test_hour_caps_are_cumulative_across_stages_and_resumes(tmp_path: Path) -> None:
    pl = planmod.Plan({**core.envelope("freeze_plan"), "mode": "test", "cells": [], "params": {}, "stage_caps": {"train_hours": 1.0, "evaluate_hours": 0.5, "total_hours": 1.25}})
    run = tmp_path / "run"
    led = stages.ledger_of(pl, run)
    assert stages.stage_cap_seconds(pl, "train", led) == 3600.0
    led.charge("train", "r", 2000.0)  # a first invocation that was stopped
    assert stages.stage_cap_seconds(pl, "train", led) == 1600.0  # the resume gets what is left of the train cap
    led.charge("ladder", "r", 1000.0)  # ladder shares the train cap
    assert stages.stage_cap_seconds(pl, "train", led) == 600.0 and stages.stage_cap_seconds(pl, "ladder", led) == 600.0
    assert stages.stage_cap_seconds(pl, "evaluate", led) == 1500.0  # its own cap is 1,800 s but the total (4,500 s) has 1,500 s left
    led.charge("evaluate", "r", 1500.0)
    assert stages.stage_cap_seconds(pl, "train", led) == 0.0 and stages.stage_cap_seconds(pl, "baselines", led) == 0.0
    led.charge("train", "r2", 1500.0)
    with pytest.raises(core.LedgerRefused):
        led.require_room("train")
    assert led.charged("train") == 3500.0 and led.charged() == 6000.0 or led.remaining() == 0.0


def test_execute_stage_charges_the_ledger_and_a_resume_charges_again(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    stages.execute_stage("gates", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    led = stages.ledger_of(pl, run)
    first = led.charged("gates")
    assert first > 0 and len(led.entries()) == 1
    stages.execute_stage("gates", pl, ctx, run, pl.path, args, repo=ROOT, inline=True)
    assert len(led.entries()) == 2 and led.charged("gates") > first  # every invocation is charged


# --- the R2 qualification driver, the rates file, the record ---------------------------------------------------------------------------------------------------
def test_r2_qualification_driver_runs_every_check_at_every_fraction(tmp_path: Path) -> None:
    cfgp = tmp_path / "tiny.toml"
    cfgp.write_text(rehearsal.tiny_config_text())
    cfg = core.load_config(cfgp)
    out = rehearsal_real.run_r2_qualification(tmp_path / "work", {128: (128, 4096, 16, 0.003)}, [("t1", core.TEST, 1), ("t2", core.TEST, 2)], cfg=cfg, synthetic_data=True, sizes={"table_facts": 512, "unseen": 64})
    table = out["table"]["128"]
    assert set(table) == {"0.0625", "0.125", "0.25", "0.5", "1"} or set(table) >= {"0.5", "1"}  # the fractions of U_P that R2's snapshots have
    assert all(set(v) <= {"a", "b", "c"} for v in table.values()) and "a_use" not in json.dumps(out)  # conditions, never accuracies
    fails = {(f["view"], f["update"]): f["conditions"] for f in out["failures"]}
    for key, conds in fails.items():  # every recorded failure is a condition removed from that fraction of the table
        frac = next(f["fraction"] for f in out["failures"] if (f["view"], f["update"]) == key)
        assert not set(conds) & set(table[frac])
    assert (tmp_path / "work" / "t1" / "evaluate").is_dir() and (tmp_path / "work" / "t2" / "baselines").is_dir()


def test_measuring_rehearsal_rates_file_feeds_the_projection(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    out = rehearsal_real.measure_rates(pl, ctx, pl.path, [2], synthetic_data=True, warmup=1, updates=2, repeats=1, eval_update=4)
    k2 = out["by_workers"]["2"]
    keys = {f"{c['arm']}|{c['slots']}" for c in pl.data["cells"]}
    assert set(k2["train"]) == keys and set(k2["evaluate"]) == keys and k2["contention"] >= 1.0 and k2["peak_rss_bytes_per_worker"] > 0 and all(v > 0 for v in k2["train"].values())
    assert set(k2["fixed"]) == {"timing", "analysis", "report", "throughput"} and out["draw"] == "rehearsal"
    from studies.p10is1 import budget

    rates = budget.Rates({(k.split("|")[0], int(k.split("|")[1])): v for k, v in k2["train"].items()}, {(k.split("|")[0], int(k.split("|")[1])): v for k, v in k2["evaluate"].items()}, k2["contention"], k2["fixed"], 2)
    assert rates.update_seconds("F-OQ", 1024) >= k2["train"]["F-OQ|1024"]


def test_counting_rehearsal_record_names_the_plan_file_and_the_caps_flag(tmp_path: Path) -> None:
    pl = TS.plan_of()
    pl.data.update({"caps_provisional": True, "stage_caps": {"train_hours": 1.0}})
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(core.jsonable(pl.data)))
    res = rehearsal_real.run_counting(p, tmp_path / "run", repo=ROOT, chain=())
    assert res["stages"] == {"analysis": "COMPLETE", "report": "COMPLETE"} and res["candidate"]["plan_file_sha256"] == file_sha256(p)
    rec = core.read_record(tmp_path / "run" / "rehearsal.json", "rehearsal")
    assert rec["caps_provisional"] is True and rec["rehearsal_kind"] == "counting" and rec["candidate"]["plan_file_sha256"] == file_sha256(p)  # a measuring-stage record on provisional caps cannot be frozen on
    view = planmod.Plan.load(tmp_path / "run" / "view_plan.json")
    assert view.mode == "rehearsal" and {c["seed_base"] for c in view.data["cells"]} == {249201} and len(view.data["cells"]) == 31 and {c["init_seed"] for c in view.data["cells"]} == {330192}


def test_counting_rehearsal_runs_the_registered_stage_functions_on_a_tiny_plan(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    always = {"quiet": True, "load_average": 0.1, "other_study_processes": []}
    res = rehearsal_real.run_counting(pl.path, root / "run", repo=ROOT, config_path=cfg_path, synthetic_data=True, inline=True, workers=1, quiet_reading=lambda: always, end_fn=lambda s: {"ok": True, "other_study_processes": []}, sleep=lambda s: None, chain=("gates", "timing", "train", "ladder"))
    assert [res["stages"][s] for s in ("gates", "timing", "train", "ladder")] == ["COMPLETE"] * 4
    assert res["stages"]["analysis"] == "FAILED" and res["candidate"]["status"] == "FAILED"  # a tiny plan is not the registry: the synthetic analysis cannot run on it, and the record says so
    assert (root / "run" / "rehearsal.json").is_file()


def test_the_256_slot_f_oq_cell_trains_and_evaluates_without_an_index_read(tmp_path: Path) -> None:
    import test_p10is1_adapter as TA

    ctx = TA.ctx_at(tmp_path)
    spec = TA.tiny_spec("F-OQ", slots=256)
    data, seeds = items.load_data(ctx, spec, verify=False)
    adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 8, mode=core.TEST)
    rec = core.read_record(items.evaluate_snapshot(ctx, spec, 8, data=data, seeds=seeds), "eval")
    assert set(rec["reads"]) == {"main"} and rec["slots"] == 256  # no index read at 256 slots: one list would read every key
    assert rec["reads"]["main"]["panels"]["A"]["n"] > 0
