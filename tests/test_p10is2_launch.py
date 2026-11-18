# ruff: noqa: E501
"""Each registered launch reaches its first stage in a temporary FROZEN repository with other thread settings made beforehand (ADR-0025 section 11 item 10): the process is configured (six threads, deterministic
algorithms) BEFORE the platform check, so a fresh process whose default thread count is not six is not refused for it. The platform check itself is the real one (macOS arm64, torch 2.8.0): on another
machine these tests are skipped. The stage bodies are replaced by a recorder; nothing registered runs. Self-check only."""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2 import partt_plan, partt_stages, partt_tasks  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402
from studies.p10is2.partq import real as qreal  # noqa: E402
from studies.p10is2.partq import stages as qstages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FAKE_WALK = {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}
CALIB = {"U": 2000, "converged": True, "store_rate": 0.003, "lora_rate": 0.0003, "etable_rate": 0.003, "read_layer": 4, "pilot": {"passed": True}, "records": {}}

pytestmark = pytest.mark.skipif(not (platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"), reason="the platform of record is macOS arm64 with torch 2.8.0")


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def make_repo(tmp: Path) -> Path:
    r = tmp / "repo"
    for rel in ("studies/p10is2", "studies/p10s2/requirements-datagen.txt", "configs/p10is2_partq.toml", "configs/p10is2_partt.toml", "uv.lock", "pyproject.toml", core.SPEC):
        src, dst = ROOT / rel, r / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "freeze")) if src.is_dir() else shutil.copy(src, dst)
    (r / "studies/p10is2/freeze").mkdir(exist_ok=True)
    git(r, "init", "-q")
    (r / ".gitignore").write_text("runs/\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    return r


def set_caps(r: Path, part: str) -> None:
    p = r / (core.CONFIG_Q if part == "Q" else core.CONFIG_T)
    t = p.read_text().replace("provisional = true", "provisional = false")
    stages = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis") if part == "Q" else ("gates", "calibration", "train", "evaluate", "controls", "combined", "analysis")
    for k in (*stages, "total"):
        t = t.replace(f"{k}_hours = 0.0", f"{k}_hours = 1.0")
    p.write_text(t)


def freeze(r: Path, part: str, decision: bool = True, inputs: dict | None = None) -> str:  # type: ignore[type-arg]
    set_caps(r, part)
    cfg = core.load_config(part, r / (core.CONFIG_Q if part == "Q" else core.CONFIG_T))
    if part == "Q":
        rec = qplan.build_candidate(r, r / "runs", cfg, inputs=inputs or {"x": {"path": "/x", "sha256": "0" * 64}}, walk=FAKE_WALK, test_mode=True)
        plan_path, rec_path = core.PLAN_Q, core.FREEZE_RECORD_Q
    else:
        rec = partt_plan.build_candidate(r, r / "runs", cfg, CALIB, walk=FAKE_WALK)
        plan_path, rec_path = core.PLAN_T, core.FREEZE_RECORD_T
    write_json(r / plan_path, core.jsonable(rec))
    write_json(r / rec_path, {"kind": "freeze_record", "plan_file_sha256": file_sha256(r / plan_path)})
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    commit = git(r, "rev-parse", "HEAD")
    if decision:
        d = r / f"results/p10is2-part{part.lower()}-freeze-20261201/DECISION_2_PART{part}.md"
        d.parent.mkdir(parents=True)
        d.write_text(f"freeze {commit}\nDECISION: RUN\n")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "decision 2")
    return commit


def test_part_q_launch_reaches_its_first_stage_after_other_thread_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r = make_repo(tmp_path)
    commit = freeze(r, "Q")
    seen: dict[str, object] = {}
    monkeypatch.setattr(qreal, "run_registered_stage", lambda stage, repo, run_dir, plan: seen.update(stage=stage, threads=torch.get_num_threads(), deterministic=torch.are_deterministic_algorithms_enabled()) or {"status": "COMPLETE"})
    keep = torch.get_num_threads()
    torch.set_num_threads(3)
    torch.use_deterministic_algorithms(False)
    try:
        rc = qstages.main(["registered", "--stage", "qfit", "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r)])
    finally:
        torch.set_num_threads(keep)
    assert rc == 0 and seen == {"stage": "qfit", "threads": 6, "deterministic": True}


def test_part_t_launch_reaches_its_first_stage_after_other_thread_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r = make_repo(tmp_path)
    commit = freeze(r, "T")
    seen: dict[str, object] = {}
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.setattr(partt_tasks, "run_stage_tasks", lambda stage, plan, cfg, repo, run_dir, fc, qdir, **k: seen.update(stage=stage, threads=torch.get_num_threads(), deterministic=torch.are_deterministic_algorithms_enabled()) or {"status": "COMPLETE", "charged_seconds": 0.0})
    keep = torch.get_num_threads()
    torch.set_num_threads(2)
    try:
        rc = partt_stages.main(["registered", "--stage", "gates", "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r)])
    finally:
        torch.set_num_threads(keep)
    assert rc == 0 and seen == {"stage": "gates", "threads": 6, "deterministic": True}


def test_without_decision_2_the_launch_still_refuses_after_configuring(tmp_path: Path) -> None:
    r = make_repo(tmp_path)
    commit = freeze(r, "T", decision=False)
    assert partt_stages.main(["registered", "--stage", "gates", "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r)]) == partt_stages.EXIT_REFUSED
    commit_q = freeze(make_repo(tmp_path / "q"), "Q", decision=False)
    del commit_q
