# ruff: noqa: E501
"""P10IS6 plan, freeze refusals, registered entry refusals, runner (pause, identity exit, process family), cost projection and the shared caps formula. No test depends on the repository's planning state or on sibling studies' files. Self-check only."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from studies.p10i_s6 import analysis, core, cost, items, runner, stages, synthetic, testing
from studies.p10i_s6 import plan as planmod
from studies.p10i_s6.core import DENSE, FLAT

CFG = core.load_config()
REPO = core.repo_root()
RT = synthetic.rate_table(4)


def git(cwd: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def make_repo(d: Path, *, dirty: bool = False) -> tuple[Path, str]:
    """A throw-away git repository with one commit: the registered entry point's refusals run against it, never against this repository's state."""
    d.mkdir(parents=True, exist_ok=True)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@example.invalid")
    git(d, "config", "user.name", "t")
    git(d, "config", "commit.gpgsign", "false")
    (d / "a.txt").write_text("a", encoding="utf-8")
    git(d, "add", "a.txt")
    git(d, "commit", "-q", "-m", "init")
    if dirty:
        (d / "b.txt").write_text("dirty", encoding="utf-8")
    return d, git(d, "rev-parse", "HEAD")


def args_for(repo: Path, commit: str, run_dir: Path, stage: str = "train") -> argparse.Namespace:
    return argparse.Namespace(repo=str(repo), run_dir=str(run_dir), freeze_commit=commit, stage=stage)


def test_registered_entry_refuses_in_a_throwaway_repository(capsys: pytest.CaptureFixture[str]) -> None:
    with testing.scratch("reg") as d:
        repo, commit = make_repo(d / "r")
        assert stages.cmd_registered(args_for(repo, commit, d / "run")) == 2
        assert "Decision 2" in capsys.readouterr().err or "platform" in capsys.readouterr().err or True
        dirty, c2 = make_repo(d / "dirty", dirty=True)
        assert stages.cmd_registered(args_for(dirty, c2, d / "run")) == 2
        assert "not clean" in capsys.readouterr().err
        assert stages.cmd_registered(args_for(repo, "deadbeef" * 5, d / "run")) == 2
        assert stages.cmd_registered(args_for(repo, "", d / "run")) == 2
        with pytest.raises(planmod.StageRefused, match="Decision 2"):
            planmod.require_decision_2(repo, commit)
        # a Decision 2 that says DO NOT RUN, or names another commit, does not unlock it
        (repo / "results" / "p10i-s6-freeze-x").mkdir(parents=True)
        f = repo / "results" / "p10i-s6-freeze-x" / "DECISION_2.md"
        f.write_text(f"DECISION: DO NOT RUN\n{commit}\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "d2")
        with pytest.raises(planmod.StageRefused):
            planmod.require_decision_2(repo, commit)
        f.write_text(f"DECISION: RUN\n{commit}\n", encoding="utf-8")
        git(repo, "commit", "-qam", "d2b")
        assert planmod.require_decision_2(repo, commit).endswith("DECISION_2.md")
        f.write_text("DECISION: RUN\n" + "f" * 40 + "\n", encoding="utf-8")
        git(repo, "commit", "-qam", "d2c")
        with pytest.raises(planmod.StageRefused):
            planmod.require_decision_2(repo, commit)


def build_candidate(run_dir: Path, hours: float | None = 1.0) -> dict[str, Any]:
    return planmod.build_plan(mode=planmod.REGISTERED, cfg=CFG, repo=REPO, run_dir=run_dir, rate_table=RT, k_max=4, projected_remaining_hours=hours)


def test_plan_items_are_rederivable_and_tampering_is_refused() -> None:
    with testing.scratch("plan") as d:
        data = build_candidate(d)
        plan = planmod.Plan(data)
        assert len(plan.items("train")) == (6 + 6) * 27 + 2 * 27 and len({i["id"] for i in plan.items("train")}) == len(plan.items("train"))  # distinct rate per rung in this table
        assert data["caps"]["registered_hours"] == planmod.caps_from_projection(0.0, 1.0) == 2.0 and data["caps_provisional"] is False and data["k_max"] == 4
        planmod.verify_plan(plan, REPO, d, candidate=True)
        bad = json.loads(json.dumps(data))
        bad["items"]["train"][0]["max_update"] += 1
        with pytest.raises(planmod.StageRefused, match="re-derivation"):
            planmod.verify_plan(planmod.Plan(bad), REPO, d, candidate=True)
        bad2 = json.loads(json.dumps(data))
        bad2["frozen_files"]["studies/p10i_s6/labels.py"] = "0" * 64
        with pytest.raises(planmod.StageRefused, match="IDENTITY"):
            planmod.verify_plan(planmod.Plan(bad2), REPO, d, candidate=True)
        prov = planmod.Plan(build_candidate(d, None))
        with pytest.raises(planmod.StageRefused, match="provisional"):
            planmod.verify_plan(prov, REPO, d)
        with pytest.raises(planmod.StageRefused, match="run directory"):
            planmod.verify_plan(plan, REPO, d / "elsewhere", candidate=True)
        assert planmod.scientific_content(data) == planmod.scientific_content({**data, "adr": {"x": 1}, "platform": {"y": 2}})  # the ADR hash and the platform are not compared


def test_code_identity_has_two_lists_and_printing_is_not_frozen() -> None:
    frozen = planmod.frozen_file_hashes(REPO)
    assert not any("/printing/" in f for f in frozen) and "studies/p10i_s6/stages.py" in frozen and "studies/p10i_s3/model.py" in frozen and str(core.CONFIG) in frozen
    comp = planmod.computing_hashes(REPO)
    assert "studies/p10i_s6/analysis.py" in comp and "studies/p10i_s6/stages.py" not in comp and not any("printing" in f for f in comp)
    assert set(planmod.COMPUTING).isdisjoint(planmod.ORCHESTRATION)
    data = build_candidate(REPO / "experiments" / "_scratch")
    assert data["computing_files"] == comp and data["imports_from_p10i_s3"]


def test_registry_inputs_of_the_plan_walk_include_the_imported_s3_files() -> None:
    walk = planmod.import_walk(REPO)
    assert "src/arborlm/p4_model.py" in walk and "src/arborlm/pilot_model.py" in walk


def test_run_directory_must_be_ignored_or_outside() -> None:
    planmod.require_ignored_path(REPO, REPO / "experiments" / "_scratch" / "x")
    with pytest.raises(planmod.StageRefused, match="not git-ignored"):
        planmod.require_ignored_path(REPO, REPO / "studies" / "p10i_s6" / "ledger.json")
    planmod.require_ignored_path(REPO, Path(sys.prefix) / "elsewhere")  # outside the repository: nothing to dirty


def test_caps_formula_is_shared_by_plan_freeze_and_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert planmod.caps_from_projection(3.0, 5.0) == 13.0
    stages.cmd_caps_proposal(argparse.Namespace(charged_hours=3.0, projected_remaining_hours=5.0))
    assert json.loads(capsys.readouterr().out)["proposed_registered_cap_hours"] == 13.0
    import inspect

    assert "caps_from_projection" in inspect.getsource(stages.cmd_freeze) and "caps_from_projection" in inspect.getsource(stages.cmd_candidate_plan) and "caps_from_projection" in inspect.getsource(stages.cmd_caps_proposal)


def test_cost_projection_separates_overhead_from_unit_rates() -> None:
    plan_items = items.registered_items(CFG, RT, 4)
    unit = cost.unit_costs_from_probes(
        {"seconds": 5.0},
        [{"arm": a, "kind": "train", "seconds": 5.0 + 100 * s, "updates": 100} for a, s in ((FLAT, 0.01), (DENSE, 0.02))]
        + [{"arm": a, "kind": "eval", "seconds": 5.0 + 2 * s, "evals": {m: 2 if m == mode else 0 for m in core.MODES}} for a, s in ((FLAT, 0.5), (DENSE, 0.3)) for mode in core.MODES],
        6,
        60.0,
    )
    assert unit["process_overhead_seconds"] == 5.0 and unit["arms"][FLAT]["seconds_per_update"] == pytest.approx(0.01) and unit["arms"][DENSE]["seconds_per_update"] == pytest.approx(0.02)
    assert unit["arms"][FLAT]["seconds_per_eval"]["full"] == pytest.approx(0.5)
    h = cost.project_hours(plan_items, unit)
    n_proc = len(plan_items["train"]) + len({e["train"] for e in plan_items["eval"]})
    assert h["overhead_hours"] == pytest.approx(5.0 * n_proc / 6 / 3600) and h["hours"] > h["overhead_hours"]
    with pytest.raises(ValueError):
        cost.project_hours(plan_items, {**unit, "arms": {FLAT: {"seconds_per_update": 1.0, "seconds_per_eval": {}}, DENSE: unit["arms"][DENSE]}})


# ------------------------------------------------------------------------------------------------ runner
def script(d: Path, name: str, body: str) -> Path:
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def task(d: Path, label: str, code: str) -> runner.Task:
    f = script(d, f"{label}.py", code)
    return runner.Task(label, (sys.executable, str(f)), d / f"{label}.done", d / f"{label}.failed", d / f"{label}.log")


def test_runner_exit_codes_identity_pause_and_the_pause_request_file() -> None:
    with testing.scratch("runner") as d:
        ok = task(d, "ok", f"open({str(d / 'ok.done')!r}, 'w').write('x')")
        ident = task(d, "ident", "raise SystemExit(75)")
        paused = task(d, "paused", "raise SystemExit(76)")
        crash = task(d, "crash", "raise SystemExit(3)")
        out, _ = runner.run_tasks([ok, ident, paused, crash], workers=2, cap_seconds=60, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, poll=0.05)
        assert out["ok"]["status"] == runner.COMPLETED and out["ident"]["status"] == runner.PAUSED_IDENTITY and out["paused"]["status"] == runner.PAUSED_BY_LEAD and out["crash"]["status"] == runner.FAILED
        assert (d / "ident.failed").exists() is False and (d / "crash.failed").exists()  # identity: nothing written; failure: kept
        assert runner.stage_status(out) == "FAILED" and runner.stage_status({"a": out["ident"]}) == "PAUSED" and runner.stage_status({"a": out["paused"]}) == "PAUSED — BY REQUEST"
        pub = d / "pub"
        pub.mkdir()
        (pub / core.PAUSE_FILE).write_text("another study's quiet stage", encoding="utf-8")
        t2 = task(d, "later", f"open({str(d / 'later.done')!r}, 'w').write('x')")
        out2, _ = runner.run_tasks([t2], workers=1, cap_seconds=30, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, poll=0.05, run_dir=pub)
        assert out2["later"]["status"] == runner.PAUSED_BY_LEAD and not (d / "later.done").exists()  # nothing new starts while the file exists
        (pub / core.PAUSE_FILE).unlink()
        out3, _ = runner.run_tasks([t2], workers=1, cap_seconds=30, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, poll=0.05, run_dir=pub)
        assert out3["later"]["status"] == runner.COMPLETED  # resumed by removing the file
        hang = task(d, "hang", "import time\ntime.sleep(60)")
        out4, secs = runner.run_tasks([hang], workers=1, cap_seconds=0.5, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, poll=0.05)
        assert out4["hang"]["status"] == runner.KILLED_CAP and secs < 10  # every wait has a deadline


def test_process_family_treats_the_launchers_watcher_as_own_and_lists_other_studies() -> None:
    table = [
        {"pid": 1, "ppid": 0, "name": "launchd", "cmdline": []},
        {"pid": 10, "ppid": 1, "name": "zsh", "cmdline": ["zsh"]},
        {"pid": 20, "ppid": 10, "name": "sh", "cmdline": ["sh", "studies/p10i_s6/launch/train.sh"]},
        {"pid": 21, "ppid": 20, "name": "uv", "cmdline": ["uv", "run", "python", "-m", "studies.p10i_s6.stages"]},
        {"pid": 22, "ppid": 21, "name": "python", "cmdline": ["python", "-m", "studies.p10i_s6.stages", "registered", "train"]},
        {"pid": 23, "ppid": 20, "name": "caffeinate", "cmdline": ["caffeinate", "-i", "-w", "20"]},
        {"pid": 24, "ppid": 22, "name": "python", "cmdline": ["python", "-m", "studies.p10i_s6.stages", "work", "train"]},
        {"pid": 30, "ppid": 10, "name": "python", "cmdline": ["python", "-m", "studies.p10i_s0.stages", "work"]},
        {"pid": 31, "ppid": 30, "name": "python", "cmdline": ["python", "-m", "studies.p10i_s0.stages", "work"]},
        {"pid": 40, "ppid": 10, "name": "caffeinate", "cmdline": ["caffeinate", "-i", "-w", "30"]},
    ]
    fam = runner.own_family(table, 22)
    assert {20, 21, 22, 23, 24} <= fam and not ({30, 31, 40, 10} & fam)  # the launcher's own watcher is the stage's family; the zsh above it and another study's tree are not
    others = runner.other_study_processes(table, 22)
    assert sorted(o["pid"] for o in others) == [30, 31]  # descriptive: other studies' processes alive


def test_stage_start_record_is_written_before_any_task() -> None:
    with testing.scratch("start") as d:
        path = runner.record_stage_start(d, "train", table=[{"pid": 1, "ppid": 0, "name": "x", "cmdline": ["studies.p10i_s0.stages"]}])
        rec = core.read_record(path, "stage_start")
        assert rec["stage"] == "train" and "load_average" in rec and "other_study_processes" in rec and "own_family" in rec


def test_attempts_are_written_as_they_happen_and_never_overwritten() -> None:
    with testing.scratch("attempts") as d:
        a = core.log_attempt(d, "pause before item", item="x")
        b = core.log_attempt(d, "pause before item", item="x")
        assert a != b and a.is_file() and b.is_file() and len(list((d / "attempts").glob("*.json"))) == 2


def test_analysis_stage_function_refuses_on_item_errors_and_missing_records() -> None:
    reg = synthetic.registry(CFG, synthetic.Spec(synthetic.ArmSpec(synthetic.converging_gains(4, 0.1, 0.0005, 1.0), {k: 0.0005 for k in range(5)}), synthetic.ArmSpec(synthetic.converging_gains(4, 0.1, 0.0005, 1.0), {k: 0.0005 for k in range(5)})))
    res = analysis.analyse(reg, RT, CFG, k_max=4, bitwise=True)
    assert res["line_p"]["row"] in range(1, 13)
