# ruff: noqa: E501
"""ONE calibration in one fixed directory with a tracked log (ruling 21, audit N2), the door that admits generation/result.json through Part Q's plan (N1), the calibration cap, the stage guard (N7), resumable rehearsal
records (N4), sealed rehearsal records (N8) and the two-phase caps (ruling 22). Self-check only."""

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_partt_e2e_world import make_part_q, part_q_plan_of  # noqa: E402
from test_p10is2_launch import git, make_repo  # noqa: E402

from studies.p10is2 import partt_caps, partt_counting, partt_real, partt_stages  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partt_door import PartQDoor  # noqa: E402


def repo_with_cap(tmp: Path, cap: float = 1.0) -> Path:
    r = make_repo(tmp)
    (r / ".gitignore").write_text("runs/\nexperiments/\n")
    p = r / core.CONFIG_T
    p.write_text(p.read_text().replace("calibration_hours = 0.0", f"calibration_hours = {cap}"))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "cap")
    return r


def fake_calibrate(repo: Path, qdir: Path, run_dir: Path, repetition: int, part_q_plan: Path | None, cap_seconds: float) -> dict[str, Any]:
    hashes = planmod.frozen_file_hashes(repo, "T")
    core.write_record(run_dir / f"calibration_{repetition}.json", {**core.envelope("calibration", "T"), "store_rate": 0.003, "lora_rate": 0.0003, "etable_rate": 0.003, "read_layer": 4, "U": 2000, "converged": True, "pilot": {"passed": True}, "stand_in": False, "code_hashes": hashes, "repetition": repetition}, overwrite=False)
    return {"U": 2000}


def args(r: Path, q: Path, rep: int = 0, reason: str = "", plan: bool = True) -> list[str]:
    return ["calibrate", "--part-q-dir", str(q), *(["--part-q-plan", str(part_q_plan_of(q))] if plan else []), "--repetition", str(rep), "--reason", reason, "--repo", str(r)]


def test_there_is_one_calibration_in_one_directory_with_a_tracked_log_and_a_recorded_second(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    zero = make_repo(tmp_path / "zero")
    assert partt_stages.main(args(zero, q)) == partt_stages.EXIT_REFUSED  # a cap of 0 is never "uncapped"
    r = repo_with_cap(tmp_path / "r")
    d = core.calibration_dir(r)
    assert d == r / "experiments" / core.CALIBRATION_NAME  # derived from the repository's experiments directory, never typed
    assert partt_stages.main(args(r, q, plan=False)) == partt_stages.EXIT_REFUSED  # Part Q's plan is needed for the door
    assert partt_stages.main(args(r, q)) == 0
    assert (d / "calibration_0.json").is_file() and (d / "charged_ledger.json").is_file()
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "end"] and log[1]["record_sha256"] and (r / core.CALIBRATION_LOG).is_file()
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # no re-draw: there is ONE calibration
    assert partt_stages.main(args(r, q, rep=1)) == partt_stages.EXIT_REFUSED  # the repetition needs its reason
    assert partt_stages.main(args(r, q, rep=1, reason="a training file changed after the first")) == 0
    assert (d / "second" / "calibration_1.json").is_file() and (d / "calibration_0.json").is_file()  # the first is kept
    assert partt_stages.main(args(r, q, rep=1, reason="again")) == partt_stages.EXIT_REFUSED  # the single repetition only
    assert [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start", "end", "start", "end"]
    # the plan takes the first when both match the frozen files; the second only when the first no longer does
    assert partt_stages.chosen_calibration(r) == (d / "calibration_0.json", 0)
    first = json.loads((d / "calibration_0.json").read_text())
    first["code_hashes"] = {k: "0" * 64 for k in first["code_hashes"]}
    (d / "calibration_0.json").write_text(json.dumps(first))
    assert partt_stages.chosen_calibration(r) == (d / "second" / "calibration_1.json", 1)


def test_the_candidate_plan_takes_no_free_calibration_path() -> None:
    parser = partt_stages.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["candidate-plan", "--run-dir", "x", "--calibration", "any.json", "--part-q-dir", "q", "--measuring-rehearsal", "m"])
    with pytest.raises(SystemExit):
        parser.parse_args(["calibrate", "--part-q-dir", "q", "--run-dir", "anywhere"])  # no free directory either


def test_the_checked_door_admits_generation_result_through_part_q_plan_only(tmp_path: Path) -> None:
    q = make_part_q(tmp_path / "partq")  # shaped like the real one: generation/result.json is in no manifest list, only in the plan's reuse list
    assert "generation/result.json" not in json.loads((q / "manifest.json").read_text())["files"]
    with pytest.raises(core.StageRefused, match="not listed"):
        PartQDoor.from_dir(q).read_json("generation/result.json")
    door = PartQDoor.from_plan(partt_stages.part_q_block(q, part_q_plan_of(q)))
    assert door.read_json("generation/result.json")["draws_label"] == "DISJOINT DRAWS"


def test_calibration_stops_at_its_cap() -> None:
    from p10is2_engine_fixtures import CFG_T, world

    with pytest.raises(partt_real.calibration.CalibrationStop, match="cap"):
        partt_real.run_calibration(world(updates=2, n_reps=2), CFG_T, deadline=time.monotonic() - 1.0)


def test_the_stage_guard_pauses_a_stage_that_spends_its_cap_or_its_memory(tmp_path: Path) -> None:
    trips: list[str] = []
    led = core.Ledger(tmp_path / "charged_ledger.json", "T", 1e12)
    with partt_real.StageGuard("recompute", tmp_path, led, cap_seconds=0.2, rss_limit=2**40, poll=0.05, on_trip=trips.append):
        time.sleep(0.8)
    assert len(trips) == 1 and "cap" in trips[0] and led.charged("recompute") > 0
    assert json.loads((tmp_path / "stages" / "recompute.paused.json").read_text())["status"] == "PAUSED"
    trips.clear()
    with partt_real.StageGuard("analysis", tmp_path, led, cap_seconds=1e6, rss_limit=1, poll=0.05, on_trip=trips.append):
        time.sleep(0.5)
    assert len(trips) == 1 and "guard" in trips[0]


def test_a_rehearsal_record_can_be_resumed_and_a_complete_one_is_never_replaced(tmp_path: Path) -> None:
    p = tmp_path / "rehearsal_counting.json"
    rec = {**core.envelope("rehearsal", "T"), "kind_of_rehearsal": "counting"}
    partt_counting.write_rehearsal_record(p, {**rec, "status": "INCOMPLETE"})
    partt_counting.write_rehearsal_record(p, {**rec, "status": "COMPLETE"})  # the resumed run: the INCOMPLETE record is kept beside it
    assert (tmp_path / "rehearsal_counting.attempt2.json").is_file() and json.loads(p.read_text())["status"] == "COMPLETE"
    with pytest.raises(core.StageRefused, match="COMPLETE"):
        partt_counting.write_rehearsal_record(p, {**rec, "status": "COMPLETE"})


def test_a_rehearsal_directory_writes_its_records_under_sealed(tmp_path: Path) -> None:
    reg = tmp_path / "reg"
    reg.mkdir()
    (reg / "run_mode.json").write_text(json.dumps({"mode": "registered"}))
    reh = tmp_path / "reh"
    reh.mkdir()
    (reh / "run_mode.json").write_text(json.dumps({"mode": "rehearsal"}))
    assert core.records_dir(reg) == reg and core.records_dir(reh) == reh / "sealed" and (reh / "sealed").is_dir() and core.records_dir(tmp_path / "none") == tmp_path / "none"


def test_the_first_cap_write_is_the_calibration_cap_only() -> None:
    text = (Path(__file__).resolve().parents[1] / core.CONFIG_T).read_text()
    out = partt_caps.apply_caps_text(text, {"calibration_hours": 1.25}, final=False)
    cfg = __import__("tomllib").loads(out)
    assert cfg["stage_caps"]["calibration_hours"] == 1.25 and cfg["caps"]["provisional"] is True and cfg["stage_caps"]["train_hours"] == 0.0


def test_a_calibration_that_stops_is_logged_charged_and_not_repeatable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise partt_real.calibration.CalibrationStop("every rate diverged")

    monkeypatch.setattr(partt_real, "calibrate_command", boom)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    with pytest.raises(partt_real.calibration.CalibrationStop):
        partt_stages.main(args(r, q))
    assert [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start", "stopped"]
    assert core.Ledger(core.calibration_dir(r) / "charged_ledger.json", "T", 1e12).charged("calibration") >= 0.0 and (core.calibration_dir(r) / "charged_ledger.json").is_file()  # charged also when it stops
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # a stopped session is not re-drawn: it returns to the lead
