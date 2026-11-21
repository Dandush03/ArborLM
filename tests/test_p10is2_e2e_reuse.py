# ruff: noqa: E501
"""Attempt 3 of Part Q through the real launch scripts, in fresh processes, on the synthetic world: an earlier attempt's six stages are carried into a NEW run directory by the ``reuse`` stage (every file hashed as bytes,
links, completion records), then ``regeneration`` (the identity check, run again), ``outputs`` and ``analysis`` run on them. A reused file that differs stops every stage with PAUSED — IDENTITY, and the earlier
attempt's directory is never written. Only the downloads and the teachers are fakes (``p10is2_e2e_world``). Self-check only."""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10is2_e2e_launch import fake_uv, git, synthetic_base  # noqa: E402
from test_p10is2_launch import FAKE_WALK, set_caps  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402
from studies.p10is2.partq import real_stages, reuse  # noqa: E402

ON_RECORD = platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"
pytestmark = pytest.mark.skipif(not ON_RECORD, reason="the platform of record (the platform check is the real one)")


def launch_in(r: Path, env: dict[str, str], stage: str, run: Path, commit: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_registered.sh"), stage, str(run), commit, *extra], cwd=r, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607


def freeze_plan(r: Path, run: Path, inputs: dict, **kw) -> str:  # type: ignore[type-arg, no-untyped-def]
    """A plan for ``run`` (registered mode), a freeze record, a commit and a committed Decision 2; the earlier plan and record are moved out of the way first."""
    for f in (core.PLAN_Q, core.FREEZE_RECORD_Q):
        (r / f).unlink(missing_ok=True)
    set_caps(r, "Q")
    cfg = core.load_config("Q", r / core.CONFIG_Q)
    rec = qplan.build_candidate(r, run, cfg, inputs=inputs, walk=FAKE_WALK, **kw)
    write_json(r / core.PLAN_Q, core.jsonable(rec))
    write_json(r / core.FREEZE_RECORD_Q, {"kind": "freeze_record", "plan_file_sha256": file_sha256(r / core.PLAN_Q)})
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    commit = git(r, "rev-parse", "HEAD")
    d = r / f"results/p10is2-partq-freeze-{commit[:8]}/DECISION_2_PARTQ.md"
    d.parent.mkdir(parents=True)
    d.write_text(f"freeze {commit}\nDECISION: RUN\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "decision 2")
    return commit


def test_the_completed_stages_of_an_earlier_attempt_are_reused_and_the_remaining_stages_run_on_them(tmp_path: Path) -> None:
    r, inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path)
    run2 = r / "runs" / "attempt2"
    commit2 = freeze_plan(r, run2, inputs)
    for stage in ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration"):  # the earlier attempt's six completed stages
        out = launch_in(r, env, stage, run2, commit2)
        assert out.returncode == 0, (stage, out.stderr[-800:])
    before = reuse.hash_files(run2)
    # attempt 3: a new plan for a NEW run directory that lists every file of those stages as a frozen input
    run3 = r / "runs" / "attempt3"
    block = reuse.build_block(run2, commit2)
    assert block["file_count"] == len(before) > 50 and set(block["stages"]) == set(reuse.SOURCE_STAGES)
    commit3 = freeze_plan(r, run3, {**inputs, reuse.KEY: block}, charge_before_freeze={"seconds": 5.0, "ledgers": {}})
    for stage in reuse.ORDER:
        out = launch_in(r, env, stage, run3, commit3)
        assert out.returncode == 0, (stage, out.stderr[-1500:])
        assert real_stages.completion_path(run3, stage).is_file(), stage
    assert (run3 / "qfit").is_symlink() and (run3 / "generation").is_symlink() and not (run3 / "regeneration.json").is_symlink() and (run3 / "regeneration.json").is_file()  # the regeneration check ran again
    assert json.loads((run3 / "stages/inputs.complete.json").read_text())["reused_from"] == str(run2)
    assert json.loads((run3 / "qualification.json").read_text())["label"]
    assert reuse.hash_files(run2) == before  # the earlier attempt's directory was never written
    manifest = json.loads((run3 / "manifest.json").read_text())
    assert manifest["reused"]["tree_sha256"] == block["tree_sha256"] and not [k for k in manifest["files"] if k.split("/")[0] in reuse.LINKED]  # the reused files are listed by the plan's block
    assert git(r, "status", "--porcelain") == ""


def test_a_reused_file_that_differs_stops_the_stage_with_paused_identity(tmp_path: Path) -> None:
    r, inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path)
    run2 = r / "runs" / "attempt2"
    commit2 = freeze_plan(r, run2, inputs)
    for stage in ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration"):
        assert launch_in(r, env, stage, run2, commit2).returncode == 0
    run3 = r / "runs" / "attempt3"
    commit3 = freeze_plan(r, run3, {**inputs, reuse.KEY: reuse.build_block(run2, commit2)}, charge_before_freeze={"seconds": 5.0, "ledgers": {}})
    assert launch_in(r, env, "reuse", run3, commit3).returncode == 0
    victim = next(p for p in sorted((run2 / "qfit").rglob("*.json")))
    victim.write_bytes(victim.read_bytes() + b" ")  # one byte appended to one reused file
    out = launch_in(r, env, "regeneration", run3, commit3)
    assert out.returncode == 75 and "PAUSED — IDENTITY" in out.stderr and not real_stages.completion_path(run3, "regeneration").exists()
    again = launch_in(r, env, "reuse", run3, commit3)
    assert again.returncode == 75


def test_the_analysis_derives_the_engineering_failure_label_after_a_recorded_failure(tmp_path: Path) -> None:
    r, inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path)
    run = r / "runs" / "attempt"
    commit = freeze_plan(r, run, inputs)
    for stage in ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration"):
        assert launch_in(r, env, stage, run, commit).returncode == 0
    refused = launch_in(r, env, "analysis", run, commit)  # no outputs stage and no failure: still refused by the stage order
    assert refused.returncode == 2 and "needs 'outputs'" in refused.stderr
    write_json(run / "engineering_failures.json", {"failures": ["RegisteredTestStop: tokenization test (a) on the R-gloss-icl prompts: 1 mismatches (zero required)"]})  # what a stopped outputs stage leaves
    out = launch_in(r, env, "analysis", run, commit)
    assert out.returncode == 0, out.stderr[-800:]
    assert "ENGINEERING-FAILURE" in json.loads((run / "qualification.json").read_text())["label"]
    assert os.path.exists(run / "stages/analysis.complete.json")


def test_the_prompt_check_runs_through_its_launch_script_without_writing_anything_else(tmp_path: Path) -> None:
    r, _inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path)
    out_path = tmp_path / "prompt_check.json"
    status_before = git(r, "status", "--porcelain")
    out = subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_prompt_check.sh"), str(out_path)], cwd=r, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607
    assert out.returncode == 0, out.stderr[-1200:]
    rec = json.loads(out_path.read_text())
    assert rec["required_ok"] is True and rec["items_checked"] > 0 and rec["last_newline"]["rule"] == "own-segment" and rec["left_for_outputs"]
    assert not (tmp_path / "_prompt_check_unused").exists() and git(r, "status", "--porcelain") == status_before  # nothing in the repository was written
    again = subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_prompt_check.sh"), str(out_path)], cwd=r, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607
    assert again.returncode == 2  # written once


def test_the_attempt3_counting_rehearsal_reuses_a_rehearsal_run_and_stops_on_an_altered_reused_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is2.partq import counting

    r, inputs = synthetic_base(tmp_path)
    for k, v in fake_uv(tmp_path).items():
        monkeypatch.setenv(k, v)
    set_caps(r, "Q")
    cfg = core.load_config("Q", r / core.CONFIG_Q)
    src = r / "runs" / "rehearsal_source"
    qplan.write_candidate(r, qplan.build_candidate(r, r / "runs" / "registered", cfg, inputs=inputs, walk=FAKE_WALK))
    counting.run_counting_rehearsal(r, src)  # a first-attempt counting rehearsal: its six stages are what attempt 3's rehearsal reuses
    block = reuse.build_block(src, "a" * 40, "rehearsal")
    assert any(k.startswith("sealed/") for k in block["files"])  # a rehearsal's sealed stage records are carried as bytes
    qplan.write_candidate(r, qplan.build_candidate(r, r / "runs" / "registered3", cfg, inputs={**inputs, reuse.KEY: block}, walk=FAKE_WALK, charge_before_freeze={"seconds": 5.0, "ledgers": {}}), supersede=True)
    before = reuse.hash_files(src, "rehearsal")
    rec = counting.run_reuse_counting_rehearsal(r, r / "runs" / "rehearsal3", src)
    assert rec["status"] == "COMPLETE" and rec["forced"] == {"identity_on_reused_file": True} and set(rec["stages"]) == set(reuse.ORDER)
    assert all(v["status"] == "COMPLETE" and v["within_cap"] is not False for v in rec["stages"].values())
    logs = sorted(p.name for p in (r / "runs/rehearsal3/logs").iterdir())
    assert "reuse-identity-altered-file.log" in logs and "outputs.log" in logs and "regeneration.log" in logs
    assert reuse.hash_files(src, "rehearsal") == before  # the source rehearsal directory was never written
    assert (r / "runs/rehearsal3/sealed/rehearsal_values.json").is_file()


def test_the_registered_cap_check_counts_the_charge_before_the_freeze(tmp_path: Path) -> None:
    import re

    from test_p10is2_reusecheck import fake_attempt

    r, inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path)
    cfg_path = r / core.CONFIG_Q
    cfg_path.write_text(re.sub(r"(?m)^total_hours = [0-9.]+", "total_hours = 1.0", cfg_path.read_text()))  # a total cap of 3,600 s
    src = fake_attempt(tmp_path)
    block = reuse.build_block(src, "c" * 40)
    run = r / "runs" / "capcheck"
    commit = freeze_plan(r, run, {**inputs, reuse.KEY: block}, charge_before_freeze={"seconds": 3600.0, "ledgers": {"/x/a.json": 3600.0}})  # everything charged before the freeze already equals the total cap
    out = launch_in(r, env, "reuse", run, commit)
    assert out.returncode == 4 and "cumulative hour cap is spent" in out.stderr and "Caps are frozen" in out.stderr, out.stderr[-600:]  # the OLD check (the total less this run's charges only) would have allowed 3,600 s
    assert not real_stages.completion_path(run, "reuse").exists()
    run_b = r / "runs" / "capcheck_b"
    commit_b = freeze_plan(r, run_b, {**inputs, reuse.KEY: block}, charge_before_freeze={"seconds": 100.0, "ledgers": {"/x/a.json": 100.0}})
    ok = launch_in(r, env, "reuse", run_b, commit_b)
    assert ok.returncode == 0, ok.stderr[-600:]  # 3,500 s are left: the stage runs
