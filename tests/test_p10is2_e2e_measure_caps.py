# ruff: noqa: E501
"""Part Q: the road measuring -> caps -> candidate plan -> counting, through the real launch scripts in fresh processes on tiny synthetic inputs, with a synthetic PER-PROCESS overhead (the world build of every stage
process) that is large against the per-unit cost. The old caps rule (rate x units, the rates taken inside one process) gives caps below what a fresh stage process really takes; the whole-process rule does not.
Written after the counting rehearsal's `partition` stopped on a cap that excluded the world build. Self-check only."""

import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10is2_e2e_launch import fake_uv, git, synthetic_base  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import freeze, real_stages, stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402

OVERHEAD = 3.0
ON_RECORD = platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"


def script(r: Path, name: str, env: dict[str, str], *args: str, timeout: float = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(r / "studies/p10is2/launch" / name), *args], cwd=r, env=env, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603, S607


@pytest.mark.skipif(not ON_RECORD, reason="the platform of record (the platform check is the real one)")
def test_measuring_caps_and_counting_agree_when_every_stage_process_pays_a_large_overhead(tmp_path: Path) -> None:
    r, inputs = synthetic_base(tmp_path)
    env = fake_uv(tmp_path, overhead=OVERHEAD)
    inputs_file = tmp_path / "inputs.json"
    write_json(inputs_file, inputs)
    # 1. the caps the repository holds are reset by code (recorded), then a measuring rehearsal runs with the caps unset
    assert stages.main(["caps-reset", "--reason", "test: a correction of a cost projection", "--repo", str(r)]) == 0
    cfg = core.load_config("Q", r / core.CONFIG_Q)
    assert cfg["caps"]["provisional"] is True and all(v == 0.0 for v in cfg["stage_caps"].values()) and "caps reset" in (r / core.CONFIG_Q).read_text()
    assert list((r / core.FREEZE_DIR / "superseded").glob("partq_caps_superseded_*.json"))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "caps reset")
    out = script(r, "partq_rehearse.sh", env, "measuring", str(r / "runs" / "measuring"), "--inputs", str(inputs_file))
    assert out.returncode == 0, out.stderr[-1500:]
    rec = core.read_record(r / "runs/measuring/rehearsal_measuring.json", "rehearsal")
    assert rec["status"] == "COMPLETE" and rec["caps_formula"] == qplan.CAPS_FORMULA and set(rec["overhead_seconds"]) == set(real_stages.STAGE_ORDER)
    world_stages = [s for s in real_stages.STAGE_ORDER if s != "analysis"]
    assert all(rec["overhead_seconds"][s] >= OVERHEAD for s in world_stages)  # the world build of each process is measured apart from the per-unit rate
    # 2. the caps by the whole-process rule are not below what a fresh process takes; the old rule's are
    proj = freeze.projection_from_record(rec)
    old = {s: rec["projection_units"][s] * rec["rates_seconds_per_unit"][s] for s in proj}
    taken = {s: rec["stage_process_seconds"][s] for s in proj}
    assert all(2 * proj[s] >= taken[s] for s in proj)  # the new cap holds for the very processes it was measured on
    assert any(2 * old[s] < taken[s] for s in world_stages)  # the OLD rule (rate x units) gives a cap below the real charge of a fresh process: this test fails on it
    assert stages.main(["caps-config", "--measuring-rehearsal", str(r / "runs/measuring/rehearsal_measuring.json"), "--repo", str(r), "--apply"]) == 0
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "caps")
    # 3. the candidate plan (the study's builder, the import walk faked) and the counting rehearsal through the launch script
    cfg = core.load_config("Q", r / core.CONFIG_Q)
    qplan.write_candidate(r, qplan.build_candidate(r, r / "runs" / "registered", cfg, inputs=inputs, walk={"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "candidate plan")
    cnt = script(r, "partq_rehearse.sh", env, "counting", str(r / "runs" / "counting"))
    assert cnt.returncode == 0, cnt.stderr[-1500:]
    crec = json.loads((r / "runs/counting/rehearsal_counting.json").read_text())
    assert crec["status"] == "COMPLETE" and all(v["status"] == "COMPLETE" for v in crec["stages"].values())
    for s, v in crec["stages"].items():
        assert v["within_cap"] is True, (s, v)  # every stage, its world build included, within the cap the measuring record gave
        if s != "analysis":
            assert v["seconds"] >= OVERHEAD, (s, v)  # and `seconds` does include that overhead
