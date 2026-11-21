# ruff: noqa: E501
"""P10IS0 runner (pause, resume, identity exit code, environment pause, item errors), draw planning, the code-identity rule, the plan under two profiles, the events writer and the quiet-first timing attempt."""

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is0 import core, drivers, labels, ladder, runner  # noqa: E402
from studies.p10is0 import plan as planmod  # noqa: E402
from studies.p10is0.profile import REGISTERED, TEST  # noqa: E402

CFG = core.load_config()


def task(tmp: Path, name: str, code: str) -> runner.Task:
    d = tmp / "t"
    return runner.Task(name, (sys.executable, "-c", code), d / f"{name}.result.json", d / f"{name}.failed.json", d / f"{name}.log")


def ok_code(path: Path) -> str:
    return f"import pathlib; p = pathlib.Path({str(path)!r}); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{{}}')"


def run(tasks: list[runner.Task], cap: float = 30.0, workers: int = 2) -> dict[str, dict[str, object]]:
    out, _ = runner.run_tasks(tasks, workers=workers, cap_seconds=cap, rss_worker_bytes=2**33, rss_aggregate_bytes=2**34, poll=0.05)
    return out


def test_runner_complete_skip_and_failed_record_kept(tmp_path: Path) -> None:
    good = task(tmp_path, "good", ok_code(tmp_path / "t" / "good.result.json"))
    bad = task(tmp_path, "bad", "raise SystemExit(1)")
    out = run([good, bad])
    assert out["good"]["status"] == runner.COMPLETED and out["bad"]["status"] == runner.FAILED and bad.failed_path.is_file()
    again = run([good, bad])
    assert again["good"]["skipped"] == "result exists" and "kept" in str(again["bad"]["reason"])  # a failed cell is kept and not re-run
    assert runner.stage_status(again) == "FAILED"


def test_identity_exit_pauses_with_nothing_written_and_resumes_on_restore(tmp_path: Path) -> None:
    flag = tmp_path / "restored"
    code = f"import pathlib, sys\nif not pathlib.Path({str(flag)!r}).exists(): sys.exit({runner.IDENTITY_EXIT})\n" + ok_code(tmp_path / "t" / "idt.result.json")
    t = task(tmp_path, "idt", code)
    out = run([t])
    assert out["idt"]["status"] == runner.PAUSED_IDENTITY and not t.failed_path.exists() and not t.result_path.exists()
    assert runner.stage_status(out) == "PAUSED"
    flag.write_text("x")  # restoring the file bit for bit resumes the task
    assert run([t])["idt"]["status"] == runner.COMPLETED


def test_environment_exit_is_a_pause_not_a_failed_cell(tmp_path: Path) -> None:
    t = task(tmp_path, "env", f"raise SystemExit({runner.ENV_EXIT})")
    out = run([t])
    assert out["env"]["status"] == runner.PAUSED_ENVIRONMENT and not t.failed_path.exists() and runner.stage_status(out) == "PAUSED"


def test_cap_pauses_kills_and_lists_not_started(tmp_path: Path) -> None:
    slow = [task(tmp_path, f"s{i}", "import time; time.sleep(60)") for i in range(3)]
    out = run(slow, cap=1.0, workers=1)
    assert out["s0"]["status"] == runner.KILLED_CAP and out["s1"]["status"] == runner.NOT_STARTED and out["s2"]["status"] == runner.NOT_STARTED
    assert runner.stage_status(out) == "PAUSED"


def test_manifest_paused_then_complete_and_never_rewritten(tmp_path: Path) -> None:
    out = {"a": {"status": runner.KILLED_CAP, "seconds": 1.0, "peak_rss_bytes": 0}}
    m1 = runner.write_manifest(tmp_path, "main", "test", out, 1.0, identity={}, started="t", caps={"stage_seconds": 1.0})
    assert m1["status"] == "PAUSED"
    m2 = runner.write_manifest(tmp_path, "main", "test", {"a": {"status": runner.COMPLETED, "seconds": 2.0, "peak_rss_bytes": 0}}, 2.0, identity={}, started="t", caps={"stage_seconds": 1.0})
    assert m2["status"] == "COMPLETE" and len(m2["history"]) == 2 and m2["charged_seconds"] == 3.0
    with pytest.raises(RuntimeError, match="never rewritten"):
        runner.write_manifest(tmp_path, "main", "test", out, 1.0, identity={}, started="t", caps={})


def test_rss_guard_kills_a_worker(tmp_path: Path) -> None:
    t = task(tmp_path, "big", "x = bytearray(300 * 2**20); import time; time.sleep(30)")
    out, _ = runner.run_tasks([t], workers=1, cap_seconds=30, rss_worker_bytes=100 * 2**20, rss_aggregate_bytes=2**34, poll=0.05)
    assert out["big"]["status"] == runner.KILLED_RSS


def test_draw_plan_rules() -> None:
    names = [f"p10is0-draw-{d}" for d in range(1, 11)]
    res = [f"p10is0-reserve-{k}" for k in range(1, 5)]
    allok = dict.fromkeys([*names, *res], True)
    p = drivers.plan_draws(allok, CFG)
    assert p.ok and p.replacements == {} and p.seed_set_of[10] == "p10is0-draw-10"
    g = dict(allok)
    g["p10is0-draw-3"] = False
    g["p10is0-draw-7"] = False
    p = drivers.plan_draws(g, CFG)
    assert p.ok and p.replacements == {3: "p10is0-reserve-1", 7: "p10is0-reserve-2"}
    g["p10is0-reserve-1"] = False  # a reserve that fails is skipped
    assert drivers.plan_draws(g, CFG).replacements == {3: "p10is0-reserve-2", 7: "p10is0-reserve-3"}
    four = dict(allok)
    for d in (1, 2, 3, 4):
        four[f"p10is0-draw-{d}"] = False
    assert drivers.plan_draws(four, CFG).ok  # four failures take the four reserves
    five = {**four, "p10is0-draw-5": False}
    p = drivers.plan_draws(five, CFG)
    assert not p.ok and "ENGINEERING STOP" in str(p.reason) and "fewer than 10" in str(p.reason)
    assert not drivers.plan_draws({}, CFG).ok  # a draw with no G1 result counts as failed


def copy_code(tmp: Path) -> Path:
    root = tmp / "repo"
    shutil.copytree(REPO / "studies", root / "studies", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "freeze"))
    shutil.copytree(REPO / "configs", root / "configs")
    (root / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    return root


def test_code_identity_rule(tmp_path: Path) -> None:
    repo = copy_code(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    assert drivers.record_code_identity(run_dir, repo)["recorded"] is True
    assert drivers.record_code_identity(run_dir, repo)["recorded"] is False  # unchanged code
    drivers.check_code_identity(repo, run_dir)
    (repo / "studies/p10is0/core.py").write_text((repo / "studies/p10is0/core.py").read_text() + "\n# changed\n")
    with pytest.raises(drivers.CodeChanged, match="without a recorded cause"):
        drivers.record_code_identity(run_dir, repo)
    with pytest.raises(drivers.CodeChanged):
        drivers.check_code_identity(repo, run_dir)
    cause = tmp_path / "results" / "p10is0-cause.md"
    cause.parent.mkdir()
    cause.write_text("cause: a comment was added before durations.json existed\n")
    assert drivers.record_code_identity(run_dir, repo, cause_file=cause)["cause"] == str(cause)  # allowed before durations.json, with a recorded cause
    drivers.check_code_identity(repo, run_dir)
    write_json(repo / core.DURATIONS, ladder.durations_record({}, drivers.code_identity(repo)))  # durations.json now records the identity
    drivers.check_code_identity(repo)
    (repo / "studies/p10is0/core.py").write_text((repo / "studies/p10is0/core.py").read_text() + "\n# changed again\n")
    with pytest.raises(drivers.CodeChanged, match="differs from the code Stage R ran under"):
        drivers.check_code_identity(repo)
    with pytest.raises(drivers.CodeChanged, match="after freeze/durations.json exists"):
        drivers.record_code_identity(run_dir, repo, cause_file=cause)  # no override after durations.json exists
    # a change to an imported earlier-study file counts too
    repo2 = copy_code(tmp_path / "b")
    write_json(repo2 / core.DURATIONS, ladder.durations_record({}, drivers.code_identity(repo2)))
    (repo2 / "studies/p9ii/train.py").write_text((repo2 / "studies/p9ii/train.py").read_text() + "\n")
    with pytest.raises(drivers.CodeChanged):
        drivers.check_code_identity(repo2)


def test_the_plan_differs_between_profiles_in_seed_and_size_fields_only() -> None:
    dur = {ct.name: {"t_exposures": 1024, "convergence": "SHOWN", "reference_flags": {"cond4": False, "other": []}} for ct in core.cell_types(CFG)}
    reg = planmod.build_plan(CFG, dur, profile=REGISTERED)
    tst = planmod.build_plan(CFG, dur, profile=TEST)
    assert reg != tst and planmod.seed_blind(reg) == planmod.seed_blind(tst)
    assert {it["init_seed"] for it in tst["items"]["main"]} <= {330098, 330099}  # the test profile takes the named test initialisations only
    assert all(it["init_seed"] in (330001, 330002) for it in reg["items"]["main"])
    assert all(it["seed_set"] in tst["draws"]["seed_set_of"].values() for it in tst["items"]["main"])
    for d in range(1, 11):
        spec = core.registered_set(d, CFG, "test")
        assert 932001 <= spec.base and spec.base + 99 <= 932999 and spec.base != core.registered_set(d, CFG).base
    assert core.registered_set(1, CFG, "test").base == 932001 and core.rehearsal_set(CFG, "test").base != 309201


def test_plan_uses_the_draw_plan_and_names_manifest_hashes() -> None:
    dur = {ct.name: {"t_exposures": 1024, "convergence": "SHOWN", "reference_flags": {"cond4": False, "other": []}} for ct in core.cell_types(CFG)}
    dp = {"seed_set_of": {str(d): f"p10is0-draw-{d}" for d in range(1, 11)}}
    dp["seed_set_of"]["4"] = "p10is0-reserve-2"
    p = planmod.build_plan(CFG, dur, draw_plan=dp, manifests={"p10is0-reserve-2": "ab" * 32})
    d4 = [it for it in p["items"]["main"] if it["draw"] == 4]
    assert all(it["seed_set"] == "p10is0-reserve-2" for it in d4) and p["draw_manifests"] == {"p10is0-reserve-2": "ab" * 32}
    assert d4[0]["swap_seed"] == core.reserve_set(2, CFG).base + 51 or d4[0]["swap_seed"] == core.reserve_set(2, CFG).base + 50


def test_events_writer_and_labels(tmp_path: Path) -> None:
    cts = core.cell_types(CFG)
    ent = {ct.name: {"convergence": "SHOWN", "reference_flags": {"cond4": False, "other": []}} for ct in cts}
    ent["8K/16K"] = {"convergence": labels.NOT_SHOWN_REFUSED, "reference_flags": {"cond4": False, "other": []}}
    ev = ladder.events(ent, cts)
    files = drivers.write_events(tmp_path / "results", ev, {"cell_types": ent})
    assert [f.name for f in files] == ["EVENT_1.md"] and "(a) anchor 8K/16K" in files[0].read_text() and "the study proceeds" in files[0].read_text()
    with pytest.raises(FileExistsError):
        drivers.write_events(tmp_path / "results", ev, {})


def test_stage_r_entry_labels() -> None:
    base = {"status": ladder.STATUS_NONFINITE, "e_star": None, "t_exposures": 8192, "flat_below_floor": False, "reference_flags": None}
    e = drivers.final_entry(base, None, "none", REGISTERED, CFG)
    assert e["convergence"] == labels.NON_FINITE_REHEARSAL and e["t_exposures"] == 8192 and e["nonfinite_in_rehearsal"] and labels.NON_FINITE_REHEARSAL != labels.NOT_SHOWN_REHEARSAL
    cand = {"status": ladder.STATUS_CANDIDATE, "e_star": None, "t_exposures": 8192, "flat_below_floor": False, "reference_flags": {"cond4": False, "other": []}}
    assert drivers.final_entry(cand, None, "refused", REGISTERED, CFG)["convergence"] == labels.NOT_SHOWN_REFUSED
    ceiling = {"status": ladder.STATUS_CEILING, "e_star": None, "t_exposures": 16384, "flat_below_floor": False, "reference_flags": {"cond4": False, "other": []}}
    got = drivers.final_entry(cand, ceiling, "granted", REGISTERED, CFG)
    assert got["convergence"] == labels.NOT_SHOWN_REHEARSAL and got["t_exposures"] == 16384
    shown = {"status": ladder.STATUS_SHOWN, "e_star": 512, "t_exposures": 1024, "shown": True, "flat_below_floor": True, "reference_flags": {"cond4": True, "other": []}}
    s = drivers.final_entry(shown, None, "none", REGISTERED, CFG)
    assert s["convergence"] == "SHOWN" and s["flat_below_floor"] and labels.FLAT_BELOW_FLOOR in s["labels"] and not s["removed"]
    removed = {**shown, "reference_flags": {"cond4": False, "other": [3]}}
    assert drivers.final_entry(removed, None, "none", REGISTERED, CFG)["removed"] is True


def test_timing_attempt_not_quiet_is_kept_and_nothing_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is0 import accounting

    repo = REPO
    run_dir = tmp_path / "timing_quiet_test"
    ctx = drivers.Ctx(repo, run_dir, registered=False)
    monkeypatch.setattr(accounting, "quiet_check", lambda cfg=None: {"quiet": False, "samples": [3.0], "max_sample": 3.0, "limit": 2.0, "other_processes": [], "reasons": ["a load-average sample above 2.0"]})
    r = drivers.cmd_timing(ctx, 1.0)
    assert r["decision"] == "RETRY" and r["attempts"] == 1
    assert not (run_dir / "tasks").exists()  # no worker of this study was started
    r = drivers.cmd_timing(ctx, 1.0)
    r = drivers.cmd_timing(ctx, 1.0)
    assert r["decision"] == accounting.PAUSED_NOT_QUIET and r["attempts"] == 3
    att = core.jsonable(__import__("json").loads((run_dir / "timing" / "attempts.json").read_text()))
    assert len(att["attempts"]) == 3 and datetime.fromisoformat(att["first_started"]) <= datetime.now(UTC)
