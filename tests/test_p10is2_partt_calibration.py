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

WALK = {"outside_study_python": ["studies/p10s2/stub.py", "src/arborlm/stub.py"], "outside_study_data": ["configs/p10s2_transfer.toml"], "python_files": [], "files_opened": []}


@pytest.fixture(autouse=True)
def unsigned_commits_and_a_fixed_walk(monkeypatch: pytest.MonkeyPatch) -> None:
    """The synthetic repositories hold the study only (no studies/p10s2): the import walk is a fixed closure over stub files; log commits are unsigned here (the argv of the real, signed commit is its own test)."""
    monkeypatch.setattr(planmod, "import_walk", lambda repo, part, *a, **k: WALK)
    monkeypatch.setattr(partt_stages, "SIGN", [])
    for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@example.invalid"), ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@example.invalid"), ("GIT_CONFIG_COUNT", "1"), ("GIT_CONFIG_KEY_0", "commit.gpgsign"), ("GIT_CONFIG_VALUE_0", "false")):
        monkeypatch.setenv(k, v)


def repo_with_cap(tmp: Path, cap: float = 1.0) -> Path:
    r = make_repo(tmp)
    (r / ".gitignore").write_text("runs/\nexperiments/\n")
    for rel in ("studies/p10s2/stub.py", "src/arborlm/stub.py", "configs/p10s2_transfer.toml"):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text("# stub\n")
    p = r / core.CONFIG_T
    p.write_text(p.read_text().replace("calibration_hours = 0.0", f"calibration_hours = {cap}"))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "cap")
    return r


def fake_calibrate(repo: Path, qdir: Path, run_dir: Path, repetition: int, part_q_plan: Path | None, cap_seconds: float, on_unit: Any = None) -> dict[str, Any]:
    hashes = planmod.frozen_file_hashes(repo, "T")
    core.write_record(run_dir / f"calibration_{repetition}.json", {**core.envelope("calibration", "T"), "store_rate": 0.003, "lora_rate": 0.0003, "etable_rate": 0.003, "read_layer": 4, "U": 2000, "converged": True, "pilot": {"passed": True}, "stand_in": False, "code_hashes": hashes, "repetition": repetition}, overwrite=False)
    rec = json.loads((run_dir / f"calibration_{repetition}.json").read_text())
    (run_dir / f"calibration_{repetition}.json").write_text(json.dumps({**rec, "session_identity": partt_stages.session_identity(repo)}))
    return {"U": 2000}


def commit_repetition_record(r: Path) -> None:
    head = git(r, "rev-parse", "HEAD")
    rec = r / partt_stages.REPETITION_RECORD
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"reason: a training file had to change after the first calibration\ncommit: {head}\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "lead record: repetition")


def args(r: Path, q: Path, rep: int = 0, reason: str = "", plan: bool = True, open_: bool = False) -> list[str]:
    return ["calibrate", "--part-q-dir", str(q), *(["--part-q-plan", str(part_q_plan_of(q))] if plan else []), "--repetition", str(rep), *(["--open"] if open_ else []), "--repo", str(r)]


def open_and_commit(r: Path, q: Path, rep: int = 0) -> None:
    """The two-step calibration (ruling 29): step 1 opens the session and exits; the lead commits the log."""
    assert partt_stages.main(args(r, q, rep, open_=True)) == 0
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", f"open calibration session {rep}")
    git(r, "update-ref", "refs/remotes/origin/main", "HEAD")  # the lead pushes the open line before the run (ruling 32): a remote-tracking branch contains it


def commit_all(r: Path, msg: str) -> None:
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", msg)


def test_there_is_one_calibration_in_one_directory_with_a_tracked_log_and_a_recorded_second(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    zero = make_repo(tmp_path / "zero")
    assert partt_stages.main(args(zero, q)) == partt_stages.EXIT_REFUSED  # a cap of 0 is never "uncapped"
    r = repo_with_cap(tmp_path / "r")
    d = core.calibration_dir(r)
    assert d == r / "experiments" / core.CALIBRATION_NAME  # derived from the repository's experiments directory, never typed
    open_and_commit(r, q)
    assert partt_stages.main(args(r, q, plan=False)) == partt_stages.EXIT_REFUSED  # Part Q's plan is needed for the door
    assert partt_stages.main(args(r, q)) == 0
    assert (d / "calibration_0.json").is_file() and (d / "charged_ledger.json").is_file() and (d / "session.json").is_file()
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "end"] and log[0]["open"] is True and log[0]["identity"] and log[1]["record_sha256"]
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # no re-draw: the calibration is complete
    assert partt_stages.main(args(r, q, rep=1, open_=True)) == partt_stages.EXIT_REFUSED  # the repetition needs a committed lead record
    commit_repetition_record(r)
    open_and_commit(r, q, 1)
    assert partt_stages.main(args(r, q, rep=1)) == 0
    assert (d / "second" / "calibration_1.json").is_file() and (d / "calibration_0.json").is_file()  # the first is kept
    assert partt_stages.main(args(r, q, rep=1)) == partt_stages.EXIT_REFUSED  # the single repetition only (it is complete)
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


@pytest.mark.parametrize("stop", [MemoryError("out of memory"), partt_real.calibration.CalibrationStop("calibration reached its cap"), OSError("No space left on device"), KeyboardInterrupt()])
def test_a_calibration_that_stops_is_logged_charged_and_resumed_by_the_same_command_with_no_new_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop: BaseException) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)

    def boom(*a: object, **k: object) -> None:
        raise stop

    monkeypatch.setattr(partt_real, "calibrate_command", boom)
    with pytest.raises(type(stop)):
        partt_stages.main(args(r, q))
    assert [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start", "stopped"]
    assert (core.calibration_dir(r) / "charged_ledger.json").is_file()  # charged also when it stops
    seen: dict[str, float] = {}

    def fine(repo: Path, qdir: Path, run_dir: Path, repetition: int, plan: Path | None, cap_seconds: float, on_unit: Any = None) -> dict[str, Any]:
        seen["cap"] = cap_seconds
        return fake_calibrate(repo, qdir, run_dir, repetition, plan, cap_seconds)

    monkeypatch.setattr(partt_real, "calibrate_command", fine)
    assert partt_stages.main(args(r, q)) == 0  # the SAME command resumes it: the log was not committed in between
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "stopped", "INTERRUPTED", "start", "end"]
    assert type(stop).__name__ in log[2]["reason"]  # the reason found, from the stopped line
    assert log[3]["resumed"] is True and seen["cap"] <= 3600.0  # the resume gets what is left of the cap
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # complete: nothing more to resume


def test_a_killed_session_with_finished_units_and_no_stopped_line_gets_an_interrupted_line_with_reason_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    state = core.calibration_dir(r) / "state"
    state.mkdir(parents=True)
    (state / "grid-store-A-0.001.json").write_text("{}")
    sha = __import__("hashlib").sha256(b"{}").hexdigest()
    partt_stages.log_calibration(r, {"event": "unit", "repetition": 0, "session": "x", "unit": "grid-store-A-0.001", "state_sha256": sha})  # a power loss or a kill leaves exactly this: the unit line was appended, its commit did not happen
    assert partt_stages.main(args(r, q)) == 0
    log = partt_stages.read_calibration_log(r)
    assert [e["event"] for e in log] == ["start", "unit", "INTERRUPTED", "start", "end"] and log[2]["reason"] == "UNKNOWN"
    cap_spent = repo_with_cap(tmp_path / "spent", cap=0.001)
    open_and_commit(cap_spent, q)
    core.Ledger(core.calibration_dir(cap_spent) / "charged_ledger.json", "T", 1e12).charge_process("calibration", "earlier", "main", 10.0)
    assert partt_stages.main(args(cap_spent, q)) == partt_stages.EXIT_REFUSED  # a resume gets what is left: nothing left is the lead's extension


def stopping_after_one_unit(repo: Path, qdir: Path, run_dir: Path, repetition: int, plan: Path | None, cap_seconds: float, on_unit: Any = None) -> dict[str, Any]:
    (run_dir / "state").mkdir(parents=True, exist_ok=True)
    (run_dir / "state" / "grid-store-A-0.001.json").write_text("{}")
    on_unit("grid-store-A-0.001")  # the real run's callback: the unit line with the state's SHA-256, appended and committed
    raise MemoryError("out of memory")


def test_no_unseen_redraw_run_needs_a_committed_open_line_and_a_consistent_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # no committed open start line at all
    assert partt_stages.main(args(r, q, open_=True)) == 0  # step 1 only appends the line and runs no unit
    assert not (core.calibration_dir(r) / "calibration_0.json").exists() and [e["event"] for e in partt_stages.read_calibration_log(r)] == ["start"]
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # opened but not committed: HEAD has no log, so a run is refused
    commit_all(r, "the lead commits the open line")
    git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert partt_stages.main(args(r, q, open_=True)) == partt_stages.EXIT_REFUSED  # a session is already open: no second start line
    monkeypatch.setattr(partt_real, "calibrate_command", stopping_after_one_unit)
    with pytest.raises(MemoryError):
        partt_stages.main(args(r, q))
    # the delete-the-directory-and-check-out-the-log sequence: both halves of the evidence a redraw would hide are refused
    d = core.calibration_dir(r)
    shutil.rmtree(d)
    git(r, "checkout", "--", str(core.CALIBRATION_LOG))  # nothing to undo: the run committed its own unit and stop lines
    assert "unit" in [e["event"] for e in partt_stages.read_calibration_log(r)]
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # the directory no longer holds the session HEAD's log opened
    assert partt_stages.main(args(r, q, open_=True)) == partt_stages.EXIT_REFUSED  # and a fresh session cannot be opened over the open one
    assert not (d / "calibration_0.json").exists()


def test_a_log_that_lists_finished_units_whose_state_was_emptied_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    monkeypatch.setattr(partt_real, "calibrate_command", stopping_after_one_unit)
    with pytest.raises(MemoryError):
        partt_stages.main(args(r, q))
    shutil.rmtree(core.calibration_dir(r) / "state")  # the units are in the log (uncommitted lines), their state is gone
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED
    assert not (core.calibration_dir(r) / "calibration_0.json").exists()


def test_a_resume_under_other_code_is_refused_and_the_final_record_must_carry_every_sessions_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    monkeypatch.setattr(partt_real, "calibrate_command", stopping_after_one_unit)
    with pytest.raises(MemoryError):
        partt_stages.main(args(r, q))
    real = partt_stages.session_identity
    monkeypatch.setattr(partt_stages, "session_identity", lambda repo: {**real(repo), "studies/p10is2/partt_real.py": "0" * 64})  # a computing file changed between sessions
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED  # never a silent continue
    assert not (core.calibration_dir(r) / "calibration_0.json").exists()
    monkeypatch.setattr(partt_stages, "session_identity", real)

    def wrong_hashes(repo: Path, qdir: Path, run_dir: Path, repetition: int, plan: Path | None, cap_seconds: float, on_unit: Any = None) -> dict[str, Any]:
        out = fake_calibrate(repo, qdir, run_dir, repetition, plan, cap_seconds)
        rec = json.loads((run_dir / f"calibration_{repetition}.json").read_text())
        rec["session_identity"] = {k: "0" * 64 for k in rec["session_identity"]}
        (run_dir / f"calibration_{repetition}.json").write_text(json.dumps(rec))
        return out

    monkeypatch.setattr(partt_real, "calibrate_command", wrong_hashes)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED
    assert "end" not in [e["event"] for e in partt_stages.read_calibration_log(r)]  # no end line for a record whose hashes differ from the session's


def test_the_counting_rehearsal_cap_is_its_own_allowance_and_the_study_budget_bound_refuses() -> None:
    from studies.p10is2 import partt_tasks

    cfg = core.load_config("T")

    class P:
        data = {"counting_allowance_hours": 7.5}

    assert partt_tasks.rehearsal_cap_seconds(cfg, "counting", P) == 7.5 * 3600.0  # not the fixed 3.0 h
    assert partt_tasks.rehearsal_cap_seconds(cfg, "measuring", P) == float(cfg["caps"]["measuring_rehearsal_hours"]) * 3600.0  # the measuring rehearsal keeps the fixed cap
    assert partt_tasks.rehearsal_cap_seconds(cfg, "counting") == float(cfg["caps"]["rehearsal_hours"]) * 3600.0  # a plan without an allowance: the fixed figure
    bounded = {**cfg, "caps": {**cfg["caps"], "study_budget_hours": 60.0}}
    partt_stages.check_study_budget(bounded, 59.0, 7.5)
    with pytest.raises(core.StageRefused, match="PENDING LEAD REVIEW"):
        partt_stages.check_study_budget(bounded, 61.0, 7.5)  # the human lead decides; nothing is extended


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
    open_and_commit(r, q)
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


def test_the_log_lines_are_committed_by_the_run_itself_with_the_ruled_message_and_a_signed_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    monkeypatch.setattr(partt_real, "calibrate_command", stopping_after_one_unit)
    with pytest.raises(MemoryError):
        partt_stages.main(args(r, q))
    subjects = git(r, "log", "--format=%s", "-4").splitlines()
    session = partt_stages.read_calibration_log(r)[0]["session"]
    assert subjects[0] == f"P10-I-S2 Part T: calibration log {session} stopped [skip ci]" and subjects[1] == f"P10-I-S2 Part T: calibration log {session} unit [skip ci]"
    assert git(r, "show", "--stat", "--format=", "HEAD").split()[0] == str(core.CALIBRATION_LOG)  # the log file alone
    assert "Co-Authored" not in git(r, "log", "-1", "--format=%B") and git(r, "status", "--porcelain") == ""
    calls: list[list[str]] = []

    class Done:
        returncode, stderr, stdout = 0, "", ""

    partt_stages.SIGN = ["-S"]
    partt_stages.commit_log_line(r, "S", "unit", run=lambda argv, **k: calls.append(argv) or Done())
    commit = calls[1]
    assert "-S" in commit and "--no-verify" not in commit and "-n" not in commit and commit[commit.index("-m") + 1] == "P10-I-S2 Part T: calibration log S unit [skip ci]" and commit[-2:] == ["--", str(core.CALIBRATION_LOG)]


def test_a_failed_log_commit_stops_the_session_paused_before_the_next_unit_and_the_resume_commits_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    real = partt_stages.commit_log_line
    fail = {"on": True}

    def flaky(repo: Path, session: str, event: str, run: Any = None) -> None:
        if fail["on"] and event == "unit":
            raise partt_stages.LogCommitFailed("the signing agent is not available")
        real(repo, session, event) if run is None else real(repo, session, event, run)

    monkeypatch.setattr(partt_stages, "commit_log_line", flaky)
    trained: list[str] = []

    def two_units(repo: Path, qdir: Path, run_dir: Path, repetition: int, plan: Path | None, cap_seconds: float, on_unit: Any = None) -> dict[str, Any]:
        for u in ("u1", "u2"):
            if (run_dir / "state" / f"{u}.json").exists():
                continue
            (run_dir / "state").mkdir(parents=True, exist_ok=True)
            (run_dir / "state" / f"{u}.json").write_text("{}")
            trained.append(u)
            on_unit(u)
        return fake_calibrate(repo, qdir, run_dir, repetition, plan, cap_seconds)

    monkeypatch.setattr(partt_real, "calibrate_command", two_units)
    with pytest.raises(partt_stages.LogCommitFailed):
        partt_stages.main(args(r, q))
    assert trained == ["u1"]  # PAUSED before the next unit
    fail["on"] = False
    assert partt_stages.main(args(r, q)) == 0
    assert trained == ["u1", "u2"]  # u1 was not redrawn: its pending line was committed first and its state accepted
    assert git(r, "status", "--porcelain") == ""


def test_state_without_a_committed_unit_line_is_kept_aside_and_the_unit_waits_for_the_leads_decision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    open_and_commit(r, q)
    state = core.calibration_dir(r) / "state"
    state.mkdir(parents=True)
    (state / "grid-store-A-0.001.json").write_text("{}")  # a state file no committed unit line vouches for (a stop between the state and its line)
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED
    assert not (state / "grid-store-A-0.001.json").exists() and len(list((state / "attempts").glob("grid-store-A-0.001.*.json"))) == 1  # kept aside, not deleted
    assert not (core.calibration_dir(r) / "calibration_0.json").exists()  # nothing was run
    (r / partt_stages.UNIT_DECISION).parent.mkdir(parents=True, exist_ok=True)
    (r / partt_stages.UNIT_DECISION).write_text("unit: grid-store-A-0.001\nreason: the lead decides the unit is rerun\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "the lead's recorded decision")
    assert partt_stages.main(args(r, q)) == 0  # with the recorded decision the run proceeds


def test_the_run_needs_the_open_line_in_a_remote_tracking_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    assert partt_stages.main(args(r, q, open_=True)) == 0
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "the lead commits but does not push")
    assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED
    git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert partt_stages.main(args(r, q)) == 0


def test_the_session_identity_covers_the_import_closure_both_configs_and_the_lock_and_a_changed_file_refuses_the_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = make_part_q(tmp_path / "partq")
    r = repo_with_cap(tmp_path / "r")
    ident = partt_stages.session_identity(r)
    assert {"studies/p10s2/stub.py", "src/arborlm/stub.py", "configs/p10s2_transfer.toml", "uv.lock", str(core.CONFIG_T)} <= set(ident) and any(k.startswith("studies/p10is2/") for k in ident)
    open_and_commit(r, q)
    monkeypatch.setattr(partt_real, "calibrate_command", stopping_after_one_unit)
    with pytest.raises(MemoryError):
        partt_stages.main(args(r, q))
    monkeypatch.setattr(partt_real, "calibrate_command", fake_calibrate)
    for rel in ("studies/p10is2/partt_tasks.py", "studies/p10s2/stub.py", "src/arborlm/stub.py", "configs/p10s2_transfer.toml", str(core.CONFIG_T), "uv.lock"):
        f = r / rel
        keep = f.read_text()
        f.write_text(keep + "\n# changed after the first session\n")
        assert partt_stages.main(args(r, q)) == partt_stages.EXIT_REFUSED, rel  # a resume under other code, config or lock is refused
        f.write_text(keep)
    assert partt_stages.main(args(r, q)) == 0  # restored bit for bit: the resume goes through


def test_the_budget_bound_is_the_human_leads_and_three_commands_refuse_without_it(tmp_path: Path) -> None:
    r = repo_with_cap(tmp_path / "r")
    base = ["--repo", str(r)]
    for argv in (["caps-config", "--measuring-rehearsal", "m.json", "--apply", *base], ["candidate-plan", "--run-dir", "x", "--part-q-dir", "q", "--measuring-rehearsal", "m.json", *base], ["freeze", "--measuring-rehearsal", "m.json", "--counting-rehearsal", "c.json", *base]):
        assert partt_stages.main(argv) == partt_stages.EXIT_REFUSED, argv[0]  # 0.0: refused before anything is read
    cfg = core.load_config("T", r / core.CONFIG_T)
    assert float(cfg["caps"]["study_budget_hours"]) == 0.0
    bounded = {**cfg, "caps": {**cfg["caps"], "study_budget_hours": 60.0}}
    partt_stages.check_study_budget(bounded, 60.0, 7.5)  # at the bound it passes
    with pytest.raises(core.StageRefused, match="exceeds"):
        partt_stages.check_study_budget(bounded, 60.01, 7.5)
    with pytest.raises(core.StageRefused, match="human lead"):
        partt_stages.check_study_budget(cfg, 1.0, 0.0)
