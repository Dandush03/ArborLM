# ruff: noqa: E501, F401, F811
"""Part Q: one mode per run directory and the rehearsal's refusals (R1), caps that are frozen (R2): the PAUSED message, within_cap in the completion record, the freeze requiring it, a killed process charged on resume.
Each test fails on the behaviour the check of f36a46e found. Self-check only."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_e2e_launch import fake_uv, launch, synthetic_repo  # noqa: E402
from test_p10is2_partq_freeze import (  # noqa: E402
    FAKE_WALK,
    INPUTS,
    freeze_args,
    measuring_record,
    platform_ok,  # noqa: F401
    repo,  # noqa: F401
    set_caps,
)

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partq import batches as bt  # noqa: E402
from studies.p10is2.partq import freeze, real_stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402


def ledger(run: Path) -> core.Ledger:
    run.mkdir(parents=True, exist_ok=True)
    return core.Ledger(run / "charged_ledger.json", "Q", 1e12)


# --- R1 ----------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record")
def test_a_registered_launch_cannot_be_turned_into_a_rehearsal(tmp_path: Path) -> None:
    r, commit = synthetic_repo(tmp_path)  # frozen: plan, freeze record, Decision 2
    env = fake_uv(tmp_path)
    run = r / "runs"
    for argv in (["--rehearsal"],):  # the registered commit with --rehearsal
        out = launch(r, env, "inputs", commit, *argv)
        assert out.returncode == 2 and "takes '-'" in out.stderr, out.stderr[-400:]
    out = launch(r, env, "inputs", "-", "--rehearsal")  # '-' on the registered run directory, with a freeze record present
    assert out.returncode == 2 and "freeze record exists" in out.stderr, out.stderr[-400:]
    import subprocess

    led = subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_ledger.sh"), "rehearsal", str(run)], cwd=r, env=env, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603, S607
    assert led.returncode == 2 and "plan's own" in led.stderr, led.stderr[-400:]
    assert not (run / "panel_ledger_candidate.json").exists() and not real_stages.completion_path(run, "inputs").exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record")
def test_a_rehearsal_stage_refuses_the_plans_own_run_directory_before_the_freeze(tmp_path: Path) -> None:
    r, _commit = synthetic_repo(tmp_path, decision=False, record=False)  # a candidate plan only
    out = launch(r, fake_uv(tmp_path), "inputs", "-", "--rehearsal")  # launch() names the plan's run directory
    assert out.returncode == 2 and "plan's own" in out.stderr, out.stderr[-400:]


def test_a_stage_refuses_a_run_directory_holding_a_record_of_another_mode(tmp_path: Path) -> None:
    run = tmp_path / "run"
    led = ledger(run)
    real_stages._mark(run, "inputs", "COMPLETE", mode="rehearsal")  # a rehearsal's completion record
    with pytest.raises(core.StageRefused, match="one mode only"):
        real_stages.require_one_mode(run, "registered", led)
    real_stages.require_one_mode(run, "rehearsal", led)  # its own mode is fine
    other = tmp_path / "run2"
    real_stages._mark(other, "inputs", "COMPLETE", mode="registered")
    with pytest.raises(core.StageRefused, match="one mode only"):
        real_stages.require_one_mode(other, "rehearsal", ledger(other))
    noted = tmp_path / "run3"
    (noted / "stages").mkdir(parents=True)
    write_json(noted / "stages/inputs.complete.json", {"stage": "inputs", "status": "COMPLETE"})  # no mode at all
    with pytest.raises(core.StageRefused, match="one mode only"):
        real_stages.require_one_mode(noted, "registered", ledger(noted))
    charged = tmp_path / "run4"
    l4 = ledger(charged)
    l4.charge_process("inputs", "rehearsal", "main", 1.0)  # a ledger entry of another mode
    with pytest.raises(core.StageRefused, match="entries of mode"):
        real_stages.require_one_mode(charged, "registered", l4)


def test_every_completion_paused_and_refused_record_carries_its_mode(tmp_path: Path) -> None:
    run = tmp_path / "run"
    real_stages._mark(run, "inputs", "COMPLETE", mode="rehearsal")
    real_stages._mark(run, "partition", "PAUSED", mode="rehearsal")
    real_stages._mark(run, "qfit", "REFUSED", "x", mode="rehearsal")
    assert {json.loads(f.read_text())["mode"] for f in (run / "stages").glob("*.json")} == {"rehearsal"}


# --- R2 ----------------------------------------------------------------------------------------------------------------------------------------------
class CapGuard:
    reason = "cap: 10 s of this stage's remaining hours used"

    def __call__(self) -> bool:
        return True


def test_a_cap_stop_says_that_the_caps_are_frozen(tmp_path: Path) -> None:
    run = tmp_path / "run"

    def stop() -> dict[str, object]:
        raise bt.StageCapExceeded("cap")

    out = real_stages.execute("qfit", run, "test", ledger(run), CapGuard(), 1e12, stop, {"ctx": None}, lambda: [])
    assert out["status"] == "PAUSED" and real_stages.CAP_SENTENCE in out["reason"] and "new freeze by the lead" in out["reason"] and "no code path extends a cap" in out["reason"]


def test_a_stage_without_a_guard_that_ends_past_its_cap_records_within_cap_false(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    out = real_stages.execute("partition", run, "test", ledger(run), lambda: False, 1e12, lambda: {"ok": 1}, {"ctx": None}, lambda: [], stage_cap_total=5.0, prior_charged=10.0)
    rec = json.loads(real_stages.completion_path(run, "partition").read_text())
    assert out["status"] == "COMPLETE" and rec["within_cap"] is False and rec["stage_cap_seconds"] == 5.0 and rec["stage_seconds"] >= 10.0
    assert "within_cap false" in capsys.readouterr().err  # never silent
    ok = real_stages.execute("regeneration", run, "test", ledger(run), lambda: False, 1e12, lambda: {}, {"ctx": None}, lambda: [], stage_cap_total=1e6, prior_charged=0.0)
    assert ok["status"] == "COMPLETE" and json.loads(real_stages.completion_path(run, "regeneration").read_text())["within_cap"] is True


def counting_freeze_setup(repo, tmp_path, monkeypatch, within):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(planmod, "import_walk", lambda *a, **k: FAKE_WALK)
    units, rates = {k: 100.0 for k in qplan.STAGES}, {k: 36.0 for k in qplan.STAGES}
    set_caps(repo, qplan.caps_proposal(3600.0, qplan.project_stage_seconds(units, rates)))
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    path = qplan.write_candidate(repo, qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK, test_mode=True))
    measuring_record(tmp_path, units, rates)
    stages = {s: {"status": "COMPLETE", "seconds": 10.0, "cap_seconds": 7200.0, **({} if within == "missing" else {"within_cap": within})} for s in qplan.REHEARSAL_STAGES}
    core.write_record(tmp_path / "cnt.json", {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "counting", "caps_provisional": False, "plan_file_sha256": file_sha256(path), "stages": stages, "forced": {"pause_resume": True, "paused_identity_restore": True}}, overwrite=True)


@pytest.mark.parametrize("within", [False, None, "missing"])
def test_the_freeze_requires_every_stage_of_the_counting_record_within_its_cap(repo, tmp_path, platform_ok, monkeypatch, within, capsys):  # type: ignore[no-untyped-def]
    counting_freeze_setup(repo, tmp_path, monkeypatch, within)
    with pytest.raises(core.StageRefused, match="within its cap"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path))
    assert "counting_rehearsal_stage_seconds_against_caps" in capsys.readouterr().out  # each stage's seconds against its cap is printed


# --- killed process ----------------------------------------------------------------------------------------------------------------------------
def test_a_killed_process_is_charged_by_the_next_one_from_its_start_marker(tmp_path: Path) -> None:
    run = tmp_path / "run"
    led = ledger(run)
    marker = real_stages.running_path(run, "generation")
    now = time.time()
    marker.parent.mkdir(parents=True, exist_ok=True)
    write_json(marker, {"stage": "generation", "mode": "registered", "pid": 0, "start_utc": "x", "start_epoch": now - 100.0})  # pid 0: no process
    os.utime(marker, (now - 60.0, now - 60.0))  # the last heartbeat, 60 s ago: the process lived 40 s
    assert abs(real_stages.settle_killed(run, "generation", "registered", led) - 40.0) < 0.5
    assert abs(led.charged("generation") - 40.0) < 0.5 and not marker.exists()
    assert real_stages.settle_killed(run, "generation", "registered", led) == 0.0  # nothing left to settle


def test_a_stage_whose_start_marker_names_a_live_process_is_refused(tmp_path: Path) -> None:
    run = tmp_path / "run"
    real_stages.running_path(run, "qfit").parent.mkdir(parents=True, exist_ok=True)
    write_json(real_stages.running_path(run, "qfit"), {"stage": "qfit", "mode": "registered", "pid": os.getppid(), "pid_start": real_stages.process_start(os.getppid()), "start_utc": "x", "start_epoch": time.time()})
    with pytest.raises(core.StageRefused, match="still running"):
        real_stages.settle_killed(run, "qfit", "registered", ledger(run))


def test_a_reused_process_id_does_not_make_a_stage_refuse_for_ever(tmp_path: Path) -> None:
    run = tmp_path / "run"
    led = ledger(run)
    marker = real_stages.running_path(run, "qfit")
    marker.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    # the marker names a pid that is alive NOW (the parent of this process) but recorded another start time: the original process died and its ID was reused
    write_json(marker, {"stage": "qfit", "mode": "registered", "pid": os.getppid(), "pid_start": "Mon Jan  1 00:00:00 2001", "start_utc": "x", "start_epoch": now - 50.0})
    os.utime(marker, (now - 20.0, now - 20.0))
    assert abs(real_stages.settle_killed(run, "qfit", "registered", led) - 30.0) < 0.5 and not marker.exists()
    assert real_stages.process_is_the_same(os.getpid(), real_stages.process_start(os.getpid())) and not real_stages.process_is_the_same(2**22 - 3, None)


def test_the_manifest_excludes_exactly_the_volatile_files() -> None:
    from studies.p10is2.partq import pipeline

    for rel in ("stages/analysis.running.json", "stages/inputs.complete.json", "charged_ledger.json", "manifest.json", "analysis/manifest.json", "outputs/manifest.json", "sealed/x.json", "logs/qfit.log"):
        assert pipeline.manifest_excluded(Path(rel)), rel
    for rel in ("qualification.json", "outputs/bundle/manifest.json", "outputs/step8_record.json", "generation/teacher_A/block_0000/batch_0000000.json", "qfit/record.json"):
        assert not pipeline.manifest_excluded(Path(rel)), rel


def test_the_heartbeat_refreshes_the_marker_and_stop_removes_it(tmp_path: Path) -> None:
    path = real_stages.running_path(tmp_path / "run", "qfit")
    beat = real_stages.Heartbeat(path, "qfit", "registered", interval=0.05)
    first = path.stat().st_mtime
    time.sleep(0.4)
    assert path.stat().st_mtime > first and json.loads(path.read_text())["pid"] == os.getpid()
    beat.stop()
    assert not path.exists()


def test_execute_leaves_no_start_marker_behind_in_a_registered_stage(tmp_path: Path) -> None:
    run = tmp_path / "run"
    real_stages.execute("partition", run, "registered", ledger(run), lambda: False, 1e12, lambda: {}, {"ctx": None}, lambda: [], stage_cap_total=1e6, heartbeat_seconds=0.05)
    assert not real_stages.running_path(run, "partition").exists() and json.loads(real_stages.completion_path(run, "partition").read_text())["mode"] == "registered"
