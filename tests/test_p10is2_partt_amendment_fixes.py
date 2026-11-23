# ruff: noqa: E501
"""P10IS2 Part T cap amendment, audit 17 fixes: D1 (the plan difference check on the REAL import walk), D2 (a registered launch refuses --rehearsal-arms), and the read-only checkpoint health check. CPU only. Self-check only."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10is2 import partt_amendment as am  # noqa: E402
from studies.p10is2 import partt_stages, partt_targeted  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIRST_FREEZE = "c25d4f0b1d0ff5f529072cc7983c835a0267e2fb"


def first_plan() -> dict:  # type: ignore[type-arg]
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{FIRST_FREEZE}:studies/p10is2/freeze/partt_plan.json"], capture_output=True, check=False, timeout=60)  # noqa: S603, S607
    if r.returncode != 0:
        pytest.skip("the first freeze commit is not in this clone")
    return json.loads(r.stdout)  # type: ignore[no-any-return]


def test_the_plan_difference_check_passes_on_the_real_import_walk_and_refuses_one_extra_file() -> None:
    old = first_plan()
    amend = am.load(core.load_config("T"), ROOT)
    assert amend is not None
    walk = planmod.import_walk(ROOT, "T")  # the REAL walk of the real tree
    new = json.loads(json.dumps(old))
    new["import_walk"] = {k: walk[k] for k in ("python_files", "files_opened", "outside_study_python", "outside_study_data")}
    added = set(walk["python_files"]) - set(old["import_walk"]["python_files"])
    assert "studies/p10is2/partt_targeted.py" in added and "studies/p10is2/partt_amendment/__init__.py" in added  # the walk now reaches the amendment's files
    assert added <= {*amend["exempt_files"]} | {f for f in added if "studies/p10is2/partt_amendment/" in f}  # and only those
    assert [d for d in am.plan_diff_problems(old, new, amend) if d.startswith(".import_walk")] == []
    new["import_walk"]["python_files"] = [*new["import_walk"]["python_files"], "studies/p10is2/engine_extra.py"]
    assert ".import_walk.python_files" in am.plan_diff_problems(old, new, amend)  # one extra file refuses


def test_a_registered_launch_refuses_rehearsal_arms(tmp_path: Path) -> None:
    args = argparse.Namespace(rehearsal=False, plan_file=None, pause_after_updates=None, rehearsal_arms="M-ii", run_dir=str(tmp_path), freeze_commit="a" * 40)
    with pytest.raises(core.StageRefused, match="--rehearsal-arms"):
        partt_stages.plan_for(args, ROOT, "train")


def save_ck(path: Path, **over: object) -> None:
    ck = {"update": 3, "params": [torch.ones(2)], "opt": {"state": {}, "param_groups": []}, "losses": [0.1, 0.2, 0.3]} | over
    torch.save(ck, path)


def test_the_checkpoint_health_check_is_read_only_and_reports_only_loadable_and_the_update(tmp_path: Path) -> None:
    save_ck(tmp_path / "r1__M-ii__AB.ckpt")
    save_ck(tmp_path / "r1__M-ii__BA.ckpt", params=[torch.tensor([float("nan")])])
    save_ck(tmp_path / "r2__M-ii__AB.ckpt", losses=[0.1])
    good = tmp_path / "r1__M-ii__AB.ckpt"
    (tmp_path / "r2__M-ii__BA.ckpt").write_bytes(good.read_bytes()[: len(good.read_bytes()) // 2])  # a save cut off by a kill
    (tmp_path / "other.ckpt").write_bytes(b"x")
    before = {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in tmp_path.iterdir()}
    out = partt_targeted.checkpoint_health(tmp_path)
    assert set(out) == {"r1__M-ii__AB.ckpt", "r1__M-ii__BA.ckpt", "r2__M-ii__AB.ckpt", "r2__M-ii__BA.ckpt"}
    assert out["r1__M-ii__AB.ckpt"] == {"loadable": True, "update": 3, "problem": None}
    assert out["r1__M-ii__BA.ckpt"]["loadable"] is False and out["r2__M-ii__AB.ckpt"]["loadable"] is False and out["r2__M-ii__BA.ckpt"]["loadable"] is False and out["r2__M-ii__BA.ckpt"]["update"] is None
    assert all(set(v) == {"loadable", "update", "problem"} for v in out.values())  # nothing else is returned: no tensor, no loss
    assert {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in tmp_path.iterdir()} == before  # nothing written, nothing touched


def test_the_plan_takes_the_one_calibration_record_with_the_amendment_in_force() -> None:
    """candidate-plan chooses the calibration record by the code hashes too (``chosen_calibration``); with the exemption of the amendment it still finds the record of repetition 0 on the real tree (skipped where the calibration directory is not on this machine)."""
    if not core.calibration_dir(ROOT).is_dir():
        pytest.skip("the calibration directory is not on this machine")
    path, rep = partt_stages.chosen_calibration(ROOT)
    assert rep == 0 and path.name == "calibration_0.json"
