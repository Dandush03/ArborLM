# ruff: noqa: E501
"""Part T's rehearsals launched the way the registered run launches its stages (ADR-0025 section 10; audit B1): through ``partt_registered.sh`` in a FRESH process per stage invocation, the stage's tasks as worker
processes of the task runner, in a synthetic repository with a synthetic Part Q directory shaped like the real one (``p10is2_partt_e2e_world``), at test size (CPU, tiny world, U = 2). Un-stubbed apart from
the tiny run configuration and the registry-checker gate (``install``). Written because Part Q's rehearsal took a path the registered run did not and stopped it five times. Self-check only."""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_partt_e2e_world import TINY_CALIB, fake_uv, make_part_q, part_q_plan_of  # noqa: E402
from p10is2_partt_unset import unset_config  # noqa: E402
from test_p10is2_launch import FAKE_WALK, git, make_repo  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is2 import partt_counting, partt_plan, partt_stages, partt_tasks  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"), reason="the platform of record (the platform check is the real one)")


def synthetic_repo(tmp: Path, *, installable: bool = False, with_plan: bool = True) -> tuple[Path, Path]:
    """A repository holding the study, a candidate Part T plan naming a synthetic Part Q directory, committed; and that Part Q directory. ``installable``: also the project's own package (LICENSE, src), so that
    ``uv run --locked`` can build the environment in a clone of it."""
    r = make_repo(tmp)
    (r / "studies/__init__.py").write_text((ROOT / "studies/__init__.py").read_text())
    (r / ".gitignore").write_text("runs/\nexperiments/\n.venv/\n")  # the calibration directory lives under the repository's experiments directory, as in the real repository
    unset_config(r)  # ruling 41 set the real config's values; the synthetic study starts unset
    cfg_path = r / core.CONFIG_T
    text = re.sub(r"(\[rehearsal\][^\n]*\nupdates = )200", r"\g<1>4", cfg_path.read_text())  # test size: the ADR's 200 updates scaled to 4
    text = re.sub(r"(\[rehearsal\].*?read_layer = )4", r"\g<1>1", text, flags=re.S)  # and the tiny world's read layer
    cfg_path.write_text(text.replace("study_budget_hours = 0.0", "study_budget_hours = 100000.0"))  # the human lead's bound (ruling 33), set for the synthetic study
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "test-size rehearsal updates")
    bare = tmp / "remote.git"  # a local bare repository as the calibration log's remote (no network); the config records its URL (ruling 35)
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True, capture_output=True)  # noqa: S603, S607
    git(r, "remote", "add", "origin", str(bare))
    cfg_path.write_text(cfg_path.read_text().replace('remote_url = ""', f'remote_url = "{bare}"').replace('remote_branch = ""', 'remote_branch = "main"'))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "the remote the log is pushed to")
    git(r, "push", "-q", "-u", "origin", "HEAD:main")
    if installable:
        shutil.copy(ROOT / "LICENSE", r / "LICENSE")
        shutil.copytree(ROOT / "src", r / "src", ignore=shutil.ignore_patterns("__pycache__"))
    q = make_part_q(tmp / "partq")
    if with_plan:
        cfg = core.load_config("T", r / core.CONFIG_T)
        rec = partt_plan.build_candidate(r, r / "runs", cfg, TINY_CALIB, walk=FAKE_WALK, part_q=partt_stages.part_q_block(q, part_q_plan_of(q)))
        write_json(r / core.PLAN_T, core.jsonable(rec))
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "candidate plan")
    return r, q


def test_the_counting_rehearsal_runs_every_stage_through_the_registered_launch_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r, _q = synthetic_repo(tmp_path)
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    run = r / "runs" / "counting"
    rec = partt_counting.run_counting_rehearsal(r, run)
    assert rec["status"] == "COMPLETE" and rec["forced"] == {"pause_resume": True, "paused_identity_restore": True}
    assert set(rec["stages"]) == set(partt_plan.STAGES) and all(v["status"] == "COMPLETE" for v in rec["stages"].values())
    logs = sorted(p.name for p in (r / "runs" / "counting_driver_logs").iterdir())
    assert "train-identity-altered-plan.log" in logs and "train-forced-pause.log" in logs and "train-resume.log" in logs  # one fresh process per stage invocation, the forced events among them
    tasks = sorted(p.name for p in (run / "tasks" / "train").glob("*.result.json"))
    assert len(tasks) == 10  # one cell of each of the ten trained types
    assert (run / "run_mode.json").is_file() and json.loads((run / "run_mode.json").read_text())["mode"] == "rehearsal"
    assert partt_tasks.stage_marker(run, "report").is_file() and (run / "sealed" / "report.txt").is_file() and not (run / "report.txt").exists()


def test_the_measuring_rehearsal_needs_no_calibration_and_measures_every_kind_with_whole_process_timing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is2 import partt_caps

    r, q = synthetic_repo(tmp_path, with_plan=False)
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(planmod, "import_walk", lambda repo, part: FAKE_WALK)  # the synthetic repository holds the study only: the import walk of the real tree is tested elsewhere
    assert not core.calibration_dir(r).exists()  # no calibration result exists
    run = r / "runs" / "measuring"
    rec = partt_counting.run_measuring_rehearsal(r, run, q, part_q_plan=part_q_plan_of(q))
    plan = planmod.Plan.load(run / "measuring_plan.json", "T")
    assert plan.data["calibration"]["stand_in"] is True and plan.data["calibration"]["U"] == 4  # the rehearsal's own updates, from the config
    assert rec["status"] == "COMPLETE" and rec["caps_formula"] == partt_caps.CAPS_FORMULA and rec["kind_of_rehearsal"] == "measuring" and rec["caps_provisional"] is True
    kinds = partt_caps.required_kinds(plan.data["items"], plan.data["task_units_basis"])
    assert set(kinds) <= set(rec["rates_seconds_per_unit"]) and all(v > 0 for v in rec["rates_seconds_per_unit"].values()), sorted(set(kinds) - set(rec["rates_seconds_per_unit"]))
    assert {f"train:{a}" for a in partt_caps.TRAINED_TYPES} <= set(rec["rates_seconds_per_unit"])  # all ten trained types
    assert set(rec["overhead_seconds"]) == set(partt_plan.STAGES)  # the per-process overhead of every stage, apart from the rates
    train_rows = rec["processes"]["train"]
    assert len(train_rows) == 10 and all(row["process_seconds"] > 0 and row["tree_peak_rss_bytes"] > 0 and row["worker"]["peak_rss_bytes"] > 0 for row in train_rows.values())
    assert all({"current_allocated_bytes", "driver_allocated_bytes"} <= set(row["worker"]["mps"]) and row["worker"]["disk_written_bytes"] >= 0 and row["worker"]["load_start"] >= 0 and row["worker"]["load_end"] >= 0 for row in train_rows.values())
    assert rec["load"]["start"] >= 0 and "end" in rec["load"] and rec["other_studies_alive"] is not None and rec["disk_written_bytes"] > 0
    assert not (run / "registry.json").exists() and (run / "sealed" / "registry.json").is_file() and (run / "sealed" / "report.txt").is_file()  # N8: the rehearsal's scores and its label-worded report are sealed
    proj = partt_caps.project_stage_seconds(plan.data["items"], plan.data["task_units_basis"], rec["rates_seconds_per_unit"], rec["overhead_seconds"])  # the shared projection accepts the record as it is
    assert set(proj) == set(partt_plan.STAGES) and all(v > 0 for v in proj.values())
    cfg = core.load_config("T", r / core.CONFIG_T)
    assert partt_caps.calibration_cap_hours(rec, cfg) > 0 and partt_caps.counting_allowance_hours(rec, plan.data["items"]) > 0  # the cap for calibration and the counting allowance come from the same record


def test_a_throwaway_clone_launches_the_test_size_plan_through_real_uv_run_locked(tmp_path: Path) -> None:
    """The launch script UNMODIFIED, ``uv run --locked`` for real (offline, from the lock), in a throw-away clone of the synthetic repository: a rehearsal ``gates`` stage at test size. The tiny run configuration reaches
    the child as a ``.pth`` file in the clone's own environment (the script unsets PYTHONPATH, so nothing else can); nothing in the clone's tracked files is changed."""
    r, _q = synthetic_repo(tmp_path, installable=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(r), str(clone)], check=True, capture_output=True)  # noqa: S603, S607
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    env.update(UV_OFFLINE="1", E2E_ROOT=str(ROOT), E2E_SRC=str(ROOT / "src"), E2E_TESTS=str(Path(__file__).resolve().parent), E2E_SITE=str(Path(__file__).resolve().parent / "p10is2_partt_e2e_site"), PYTHONDONTWRITEBYTECODE="1")
    made = subprocess.run(["uv", "run", "--locked", "--offline", "python", "-c", "import sys; print(sys.prefix)"], cwd=clone, env={k: v for k, v in env.items() if k != "E2E_ROOT"}, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607
    assert made.returncode == 0, made.stderr[-1500:]
    site = next((clone / ".venv" / "lib").glob("python3*/site-packages"))
    (site / "zz_p10is2_e2e.pth").write_text('import os; exec(open(os.path.join(os.environ["E2E_SITE"], "sitecustomize.py")).read()) if os.environ.get("E2E_ROOT") else None\n')
    run = clone / "runs" / "clone_rehearsal"
    out = subprocess.run(["sh", str(clone / "studies/p10is2/launch/partt_registered.sh"), "gates", str(run), "-", "--rehearsal", "--rehearsal-kind", "counting"], cwd=clone, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607
    assert out.returncode == 0, (out.stdout[-800:], out.stderr[-1500:])
    assert partt_tasks.stage_marker(run, "gates").is_file() and json.loads((run / "run_mode.json").read_text())["mode"] == "rehearsal"
    assert json.loads((run / "gates.json").read_text())["status"] == "PASSED"
    tracked = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
    assert tracked == ""  # nothing tracked was changed by the launch


def launch_registered(r: Path, env: dict[str, str], stage: str, commit: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(r / "studies/p10is2/launch/partt_registered.sh"), stage, str(r / "runs" / "registered"), commit], cwd=r, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607


def test_measuring_caps_calibration_plan_counting_freeze_then_a_registered_stage_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The whole sequence at test size in the ruled order (ruling 22): measuring rehearsal (no calibration) -> the cap for calibration -> calibration (its record and tracked log line fabricated here: calibration itself
    is unit-tested) -> candidate plan -> registered caps -> plan again -> counting rehearsal -> freeze -> registered stages, with the refusals of N2 and N3."""
    import hashlib

    from studies.p10is2.common import gates

    r, q = synthetic_repo(tmp_path, with_plan=False)
    env = fake_uv(tmp_path)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(planmod, "import_walk", lambda repo, part: FAKE_WALK)
    monkeypatch.setattr(gates, "seed_gate", lambda part, cfg, **k: {"passed": True, "problems": [], "checker": {"faked_in_this_test": True}})  # the checker itself runs on the real tree in its own test
    runs = r / "runs"
    runs.mkdir(exist_ok=True)
    for name in ("acceptance.json", "panel_ledger.json"):
        (tmp_path / name).write_text(name)
    manifests = tmp_path / "manifests.json"
    write_json(manifests, {n: {"path": str(tmp_path / f), "sha256": hashlib.sha256((tmp_path / f).read_bytes()).hexdigest()} for n, f in (("part_q_acceptance", "acceptance.json"), ("panel_ledger", "panel_ledger.json"))})
    common = ["--repo", str(r)]
    pq_plan = part_q_plan_of(q)

    # 1. the measuring rehearsal first: no calibration result, 4 updates (the test-size 200)
    partt_counting.run_measuring_rehearsal(r, runs / "measuring", q, part_q_plan=pq_plan)
    meas_path = runs / "measuring" / "rehearsal_measuring.json"
    # 2. the cap for calibration, by code, from that record; calibration is refused while it is 0 and the registered caps are refused before calibration
    assert partt_stages.main(["calibrate", "--part-q-dir", str(q), "--part-q-plan", str(pq_plan), *common]) == partt_stages.EXIT_REFUSED  # a cap of 0 is never "uncapped"
    assert partt_stages.main(["caps-config", "--measuring-rehearsal", str(meas_path), "--phase", "calibration", "--apply", *common]) == 0
    cfg = core.load_config("T", r / core.CONFIG_T)
    assert cfg["stage_caps"]["calibration_hours"] > 0 and cfg["caps"]["provisional"] is True and cfg["stage_caps"]["train_hours"] == 0.0
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "calibration cap")
    # 3. the one calibration: its record in the one directory, its ledger and its tracked log lines (the real calibrate command is unit-tested)
    cal_dir = core.calibration_dir(r)
    cal_dir.mkdir(parents=True)
    cal = cal_dir / "calibration_0.json"
    core.write_record(cal, {**core.envelope("calibration", "T"), **{k: v for k, v in TINY_CALIB.items() if k != "records"}, "stand_in": False, "code_hashes": planmod.frozen_file_hashes(r, "T"), "repetition": 0}, overwrite=False)
    session = core.utc_stamp()
    core.Ledger(cal_dir / "charged_ledger.json", "T", 1e12).charge_process("calibration", session, "main", 5.0)  # the session's start UTC is the ledger entry's run (ruling 26)
    partt_stages.log_calibration(r, {"event": "start", "repetition": 0, "session": session, "reason": "", "directory": str(cal_dir)})
    partt_stages.log_calibration(r, {"event": "end", "repetition": 0, "session": session, "record": str(cal), "record_sha256": hashlib.sha256(cal.read_bytes()).hexdigest()})
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "calibration log")  # ruling 26: the plan and the freeze read the COMMITTED log
    # 4. the candidate plan (the charge from the ledgers by rule), the registered caps by code, the plan again
    cfg_text = (r / core.CONFIG_T).read_text()
    plan_args = ["candidate-plan", "--run-dir", str(runs / "registered"), "--part-q-dir", str(q), "--part-q-plan", str(pq_plan), "--manifests", str(manifests), "--measuring-rehearsal", str(meas_path), *common]
    assert partt_stages.main(plan_args) == partt_stages.EXIT_REFUSED  # ruling 35: the finished log is committed but not pushed
    git(r, "push", "-q", "origin", "HEAD:main")
    (r / core.CONFIG_T).write_text(cfg_text.replace("study_budget_hours = 100000.0", "study_budget_hours = 0.001"))
    assert partt_stages.main(plan_args) == partt_stages.EXIT_REFUSED  # ruling 37: the plan's own projected total exceeds the bound (the config total is still 0.0)
    (r / core.CONFIG_T).write_text(cfg_text)
    assert partt_stages.main(plan_args) == 0
    plan0 = planmod.Plan.load(r / core.PLAN_T, "T")
    assert set(plan0.data["charge_before_freeze"]["ledgers"]) == {str(runs / "measuring" / "charged_ledger.json"), str(cal_dir / "charged_ledger.json")}  # the measuring and the calibration ledgers, listed by rule
    assert plan0.data["measuring_rehearsal"]["sha256"] == hashlib.sha256(meas_path.read_bytes()).hexdigest()  # the measuring record is pinned
    assert partt_stages.main(["caps-config", "--measuring-rehearsal", str(meas_path), "--apply", *common]) == 0
    cfg = core.load_config("T", r / core.CONFIG_T)
    assert cfg["caps"]["provisional"] is False and all(float(cfg["stage_caps"][f"{s}_hours"]) > 0 for s in (*partt_plan.STAGES, "calibration", "total"))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "caps by code")
    assert partt_stages.main([*plan_args, "--supersede"]) == 0
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "candidate plan with caps")
    # 5. the counting rehearsal against that plan
    count = partt_counting.run_counting_rehearsal(r, runs / "counting")
    assert count["status"] == "COMPLETE" and count["forced"] == {"pause_resume": True, "paused_identity_restore": True}
    freeze_args = ["freeze", "--measuring-rehearsal", str(meas_path), "--counting-rehearsal", str(runs / "counting" / "rehearsal_counting.json"), "--attest-sealed-unopened", "lead,implementer,auditor", *common]
    plan_now = planmod.Plan.load(r / core.PLAN_T, "T")
    allowance_s = float(plan_now.data["counting_allowance_hours"]) * 3600.0
    real_charge = partt_stages.counting_charge_of(count)
    assert 0 < real_charge <= allowance_s, (real_charge, allowance_s)  # the REAL counting charge is within 2 x its projection
    # 6. refusals of the freeze: a counting charge above the allowance; a hand-edited total (plan charge and config total edited together: N3); another measuring record; an unlisted calibration session (N2); another calibration record
    big = runs / "counting_big_ledger" / "charged_ledger.json"
    big.parent.mkdir()
    core.Ledger(big, "T", 1e12).charge_process("train", "counting", "main", allowance_s + 60.0)
    doctored = runs / "rehearsal_counting_over_allowance.json"
    write_json(doctored, {**json.loads((runs / "counting" / "rehearsal_counting.json").read_text()), "charged_ledgers": {str(big): allowance_s + 60.0}, "charged_seconds": allowance_s + 60.0})
    assert partt_stages.main([*freeze_args[:4], str(doctored), *freeze_args[5:]]) == partt_stages.EXIT_REFUSED
    plan_path, cfg_path = r / core.PLAN_T, r / core.CONFIG_T
    keep_plan, keep_cfg = plan_path.read_text(), cfg_path.read_text()
    edited = json.loads(keep_plan)
    edited["charge_before_freeze"]["seconds"] += 3600.0
    write_json(plan_path, edited)
    cfg_path.write_text(re.sub(r"(?m)^total_hours = ([0-9.]+)", lambda m: f"total_hours = {float(m.group(1)) + 1.0}", keep_cfg))
    capsys.readouterr()
    assert partt_stages.main(freeze_args) == partt_stages.EXIT_REFUSED  # the charge is re-derived from the ledgers: the edit is refused
    assert "sum of its ledgers" in capsys.readouterr().err
    plan_path.write_text(keep_plan)
    cfg_path.write_text(keep_cfg)
    other = runs / "measuring_copy.json"
    other.write_text(meas_path.read_text())
    assert partt_stages.main(["freeze", "--measuring-rehearsal", str(other), *freeze_args[3:]]) == partt_stages.EXIT_REFUSED  # not the measuring record the plan pins
    log = r / core.CALIBRATION_LOG
    keep_log = log.read_text()
    log.write_text("")
    assert partt_stages.main(freeze_args) == partt_stages.EXIT_REFUSED  # a calibration session the log does not list
    log.write_text(keep_log)
    assert partt_stages.main(freeze_args) == 0  # the REAL freeze with the REAL counting charge
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    commit = git(r, "rev-parse", "HEAD")
    # 7. a registered stage: no committed Decision 2 refuses; with it the stage runs; a changed file and a changed cap are PAUSED - IDENTITY
    out = launch_registered(r, env, "gates", commit)
    assert out.returncode == partt_stages.EXIT_REFUSED and "Decision 2" in out.stderr and not (runs / "registered" / "stages").exists()
    d = r / "results/p10is2-partt-freeze-20261201/DECISION_2_PARTT.md"
    d.parent.mkdir(parents=True)
    d.write_text(f"freeze {commit}\nDECISION: RUN\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "decision 2")
    out = launch_registered(r, env, "gates", commit)
    assert out.returncode == 0, out.stderr[-1500:]
    assert partt_tasks.stage_marker(runs / "registered", "gates").is_file() and json.loads((runs / "registered" / "run_mode.json").read_text())["mode"] == "registered"
    victim = r / "studies/p10is2/partt_tasks.py"
    keep = victim.read_text()
    victim.write_text(keep + "# a changed frozen file\n")
    out = launch_registered(r, env, "train", commit)
    assert out.returncode == 75 and "PAUSED — IDENTITY" in out.stderr and not (runs / "registered" / "tasks" / "train").exists()
    victim.write_text(keep)
    good = cfg_path.read_text()
    cfg_path.write_text(good.replace(f"evaluate_hours = {cfg['stage_caps']['evaluate_hours']}", f"evaluate_hours = {float(cfg['stage_caps']['evaluate_hours']) + 1.0}"))
    out = launch_registered(r, env, "train", commit)
    assert out.returncode == 75 and "PAUSED — IDENTITY" in out.stderr and not (runs / "registered" / "tasks" / "train").exists()
    cfg_path.write_text(good)
    out = launch_registered(r, env, "train", commit)
    assert out.returncode == 0, out.stderr[-1500:]  # the file and the cap restored bit for bit: the stage runs (54 cells at test size)
    assert len(list((runs / "registered" / "tasks" / "train").glob("*.result.json"))) == 54
