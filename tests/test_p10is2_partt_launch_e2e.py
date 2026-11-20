# ruff: noqa: E501
"""Part T's rehearsals launched the way the registered run launches its stages (ADR-0025 section 10; audit B1): through ``partt_registered.sh`` in a FRESH process per stage invocation, the stage's tasks as worker
processes of the task runner, in a synthetic repository with a synthetic Part Q directory shaped like the real one (``p10is2_partt_e2e_world``), at test size (CPU, tiny world, U = 2). Un-stubbed apart from
the tiny run configuration and the registry-checker gate (``install``). Written because Part Q's rehearsal took a path the registered run did not and stopped it five times. Self-check only."""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_partt_e2e_world import TINY_CALIB, fake_uv, make_part_q  # noqa: E402
from test_p10is2_launch import FAKE_WALK, git, make_repo  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is2 import partt_counting, partt_plan, partt_stages, partt_tasks  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"), reason="the platform of record (the platform check is the real one)")


def synthetic_repo(tmp: Path, *, installable: bool = False) -> tuple[Path, Path]:
    """A repository holding the study, a candidate Part T plan naming a synthetic Part Q directory, committed; and that Part Q directory. ``installable``: also the project's own package (LICENSE, src), so that
    ``uv run --locked`` can build the environment in a clone of it."""
    r = make_repo(tmp)
    (r / "studies/__init__.py").write_text((ROOT / "studies/__init__.py").read_text())
    if installable:
        shutil.copy(ROOT / "LICENSE", r / "LICENSE")
        shutil.copytree(ROOT / "src", r / "src", ignore=shutil.ignore_patterns("__pycache__"))
    q = make_part_q(tmp / "partq")
    cfg = core.load_config("T", r / core.CONFIG_T)
    rec = partt_plan.build_candidate(r, r / "runs", cfg, TINY_CALIB, walk=FAKE_WALK, part_q=partt_stages.part_q_block(q, None))
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
    assert partt_tasks.stage_marker(run, "report").is_file() and (run / "report.txt").is_file()


def test_the_measuring_rehearsal_measures_every_kind_through_the_same_launch_with_whole_process_timing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is2 import partt_caps

    r, q = synthetic_repo(tmp_path)
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    calib = r / "runs" / "calibration_0.json"
    calib.parent.mkdir(parents=True, exist_ok=True)
    core.write_record(calib, {**core.envelope("calibration", "T"), **{k: v for k, v in TINY_CALIB.items() if k != "records"}, "stand_in": False, "code_hashes": {}, "repetition": 0}, overwrite=False)
    monkeypatch.setattr(planmod, "import_walk", lambda repo, part: FAKE_WALK)  # the synthetic repository holds the study only: the import walk of the real tree is tested elsewhere
    run = r / "runs" / "measuring"
    rec = partt_counting.run_measuring_rehearsal(r, run, calib, q)
    plan = planmod.Plan.load(run / "measuring_plan.json", "T")
    assert rec["status"] == "COMPLETE" and rec["caps_formula"] == partt_caps.CAPS_FORMULA and rec["kind_of_rehearsal"] == "measuring" and rec["caps_provisional"] is True
    kinds = partt_caps.required_kinds(plan.data["items"], plan.data["task_units_basis"])
    assert set(kinds) <= set(rec["rates_seconds_per_unit"]) and all(v > 0 for v in rec["rates_seconds_per_unit"].values()), sorted(set(kinds) - set(rec["rates_seconds_per_unit"]))
    assert {f"train:{a}" for a in partt_caps.TRAINED_TYPES} <= set(rec["rates_seconds_per_unit"])  # all ten trained types
    assert set(rec["overhead_seconds"]) == set(partt_plan.STAGES)  # the per-process overhead of every stage, apart from the rates
    train_rows = rec["processes"]["train"]
    assert len(train_rows) == 10 and all(row["process_seconds"] > 0 and row["tree_peak_rss_bytes"] > 0 and row["worker"]["peak_rss_bytes"] > 0 for row in train_rows.values())
    assert all({"current_allocated_bytes", "driver_allocated_bytes"} <= set(row["worker"]["mps"]) and row["worker"]["disk_written_bytes"] >= 0 and row["worker"]["load_start"] >= 0 and row["worker"]["load_end"] >= 0 for row in train_rows.values())
    assert rec["load"]["start"] >= 0 and "end" in rec["load"] and rec["other_studies_alive"] is not None and rec["disk_written_bytes"] > 0
    proj = partt_caps.project_stage_seconds(plan.data["items"], plan.data["task_units_basis"], rec["rates_seconds_per_unit"], rec["overhead_seconds"])  # the shared projection accepts the record as it is
    assert set(proj) == set(partt_plan.STAGES) and all(v > 0 for v in proj.values())


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
