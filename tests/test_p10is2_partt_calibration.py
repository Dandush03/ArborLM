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


def commit_repetition_record(r: Path) -> None:
    head = git(r, "rev-parse", "HEAD")
    rec = r / partt_stages.REPETITION_RECORD
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"reason: a training file had to change after the first calibration\ncommit: {head}\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "lead record: repetition")


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
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # no re-draw: the calibration is complete
    assert partt_stages.main(args(r, q, rep=1)) == partt_stages.EXIT_REFUSED  # the repetition needs a committed lead record
    commit_repetition_record(r)
    assert partt_stages.main(args(r, q, rep=1)) == 0
    assert (d / "second" / "calibration_1.json").is_file() and (d / "calibration_0.json").is_file()  # the first is kept
    assert partt_stages.main(args(r, q, rep=1)) == partt_stages.EXIT_REFUSED  # the single repetition only (it is complete)
    assert [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start", "end", "start", "end"]
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "calibration log")
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


@pytest.mark.parametrize("stop", [MemoryError("out of memory"), partt_real.calibration.CalibrationStop("calibration reached its cap"), OSError("No space left on device"), KeyboardInterrupt()])
def test_a_calibration_that_stops_is_logged_charged_and_resumed_by_the_same_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop: BaseException) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")

    def boom(*a: object, **k: object) -> None:
        raise stop

    monkeypatch.setattr(partt_real, "calibrate_command", boom)
    with pytest.raises(type(stop)):
        partt_stages.main(args(r, q))
    assert [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start", "stopped"]
    assert (core.calibration_dir(r) / "charged_ledger.json").is_file()  # charged also when it stops
    seen: dict[str, float] = {}

    def fine(repo: Path, qdir: Path, run_dir: Path, repetition: int, plan: Path | None, cap_seconds: float) -> dict[str, Any]:
        seen["cap"] = cap_seconds
        return fake_calibrate(repo, qdir, run_dir, repetition, plan, cap_seconds)

    monkeypatch.setattr(partt_real, "calibrate_command", fine)
    assert partt_stages.main(args(r, q)) == 0  # the SAME command resumes it
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "stopped", "INTERRUPTED", "start", "end"]
    assert type(stop).__name__ in log[2]["reason"]  # the reason found, from the stopped line
    assert log[3]["resumed"] is True and seen["cap"] <= 3600.0  # the resume gets what is left of the cap
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # complete: nothing more to resume


def test_a_killed_session_with_only_a_start_line_gets_an_interrupted_line_with_reason_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    partt_stages.log_calibration(r, {"event": "start", "repetition": 0, "session": "killed", "directory": "x"})  # a power loss or a kill leaves exactly this
    assert partt_stages.main(args(r, q)) == 0
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "INTERRUPTED", "start", "end"] and log[1]["reason"] == "UNKNOWN"
    cap_spent = repo_with_cap(tmp_path / "spent", cap=0.001)
    core.Ledger(core.calibration_dir(cap_spent) / "charged_ledger.json", "T", 1e12).charge_process("calibration", "earlier", "main", 10.0)
    assert partt_stages.main(args(cap_spent, q)) == partt_stages.EXIT_REFUSED  # a resume gets what is left: nothing left is the lead's extension


def test_units_run_in_an_earlier_session_are_read_back_not_drawn_again_and_a_non_finite_outcome_is_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from p10is2_engine_fixtures import world

    w = world(updates=2, n_reps=2)
    unit = {"id": "grid-store-A-0.01", "module": "store", "capability": "A", "updates": 2, "snapshots": []}
    state = tmp_path / "state"
    trained = {"n": 0}
    real_train = partt_real.engine.train_cell

    def counting(*a: Any, **k: Any) -> Any:
        trained["n"] += 1
        return real_train(*a, **k)

    def oom(*a: Any, **k: Any) -> Any:
        raise MemoryError("out of memory")

    partt_real._STATE.append(state)
    try:
        monkeypatch.setattr(partt_real.engine, "train_cell", oom)
        with pytest.raises(MemoryError):
            partt_real.run_unit(w, unit, 0.01, 1, 0)
        assert not list(state.glob("*.json"))  # nothing stored for a unit that did not finish
        monkeypatch.setattr(partt_real.engine, "train_cell", counting)
        first = partt_real.run_unit(w, unit, 0.01, 1, 0)
        n = trained["n"]
        again = partt_real.run_unit(w, unit, 0.01, 1, 0)
        assert trained["n"] == n and again == first and (state / "grid-store-A-0.01.json").is_file()  # read back, never drawn again
        monkeypatch.setattr(partt_real.engine.p10train, "loss_of", lambda *a, **k: __import__("torch").tensor(float("nan")))
        nf = {**unit, "id": "grid-store-A-0.001"}
        out = partt_real.run_unit(w, nf, 0.001, 1, 0)
        assert out["diverged"] is True and out["status"] == "STOPPED_NONFINITE"
        n2 = trained["n"]
        assert partt_real.run_unit(w, nf, 0.001, 1, 0)["diverged"] is True and trained["n"] == n2  # the outcome stands; it is not retried
        monkeypatch.setattr(partt_real.time, "monotonic", lambda: 1e9)
        partt_real._DEADLINE.append(1.0)
        try:
            with pytest.raises(partt_real.calibration.CalibrationStop, match="cap"):
                partt_real.run_unit(w, {**unit, "id": "grid-store-A-0.003"}, 0.003, 1, 0)  # the cap stop is a PAUSE at the next unit
        finally:
            partt_real._DEADLINE.pop()
        assert not (state / "grid-store-A-0.003.json").exists()
    finally:
        partt_real._STATE.pop()


def commit_log(r: Path, text: str, msg: str) -> None:
    p = r / core.CALIBRATION_LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", msg)


def test_the_committed_log_is_what_counts_it_must_be_clean_and_append_only(tmp_path: Path) -> None:
    r = repo_with_cap(tmp_path / "r")

    def line(n: int) -> str:
        return json.dumps({"event": "start", "repetition": 0, "session": f"s{n}"}) + "\n"

    with pytest.raises(core.StageRefused, match="not committed"):
        partt_stages.committed_calibration_log(r)
    commit_log(r, line(1), "log 1")
    commit_log(r, line(1) + line(2), "log 2")
    assert [e["session"] for e in partt_stages.committed_calibration_log(r)] == ["s1", "s2"]
    (r / core.CALIBRATION_LOG).write_text(line(1) + line(2) + line(3))  # an uncommitted append
    with pytest.raises(core.StageRefused, match="differs from HEAD"):
        partt_stages.committed_calibration_log(r)
    git(r, "checkout", "--", str(core.CALIBRATION_LOG))
    commit_log(r, line(9) + line(2), "a rewritten line")  # committed, but not a prefix extension
    with pytest.raises(core.StageRefused, match="not append-only"):
        partt_stages.committed_calibration_log(r)


def test_the_ledger_sessions_must_match_the_logged_ones(tmp_path: Path) -> None:
    r = repo_with_cap(tmp_path / "r")
    led = core.Ledger(core.calibration_dir(r) / "charged_ledger.json", "T", 1e12)
    led.charge_process("calibration", "s1", "main", 3.0)
    ok = [{"event": "start", "session": "s1"}, {"event": "end", "session": "s1"}]
    partt_stages.check_calibration_ledger(r, ok)
    with pytest.raises(core.StageRefused, match="does not list"):
        partt_stages.check_calibration_ledger(r, [{"event": "start", "session": "s2"}])  # a charged session the log omits
    with pytest.raises(core.StageRefused, match="no ledger entry"):
        partt_stages.check_calibration_ledger(r, [*ok, {"event": "start", "session": "s3"}])  # a logged session nobody charged and nobody marked interrupted
    partt_stages.check_calibration_ledger(r, [*ok, {"event": "start", "session": "s3"}, {"event": "INTERRUPTED"}])  # a killed process charges nothing: its INTERRUPTED line says so


def test_a_code_edit_alone_never_switches_to_the_second_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    assert partt_stages.main(args(r, q)) == 0
    d = core.calibration_dir(r)
    (d / "second").mkdir()
    first = json.loads((d / "calibration_0.json").read_text())
    (d / "second" / "calibration_1.json").write_text(json.dumps({**first, "repetition": 1}))
    (d / "calibration_0.json").write_text(json.dumps({**first, "code_hashes": {k: "0" * 64 for k in first["code_hashes"]}}))  # a code edit: the first no longer matches the frozen files
    with pytest.raises(core.StageRefused, match="committed lead record"):
        partt_stages.chosen_calibration(r)
    commit_repetition_record(r)
    assert partt_stages.chosen_calibration(r)[1] == 1
    (r / partt_stages.REPETITION_RECORD).write_text("reason: x\ncommit: " + "0" * 40 + "\n")  # a commit that is not an ancestor
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "bad record")
    assert partt_stages.repetition_record_problems(r)
