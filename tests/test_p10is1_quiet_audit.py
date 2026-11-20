# ruff: noqa: E501
"""P10IS1 quiet rule: the tests of the audit fixes F1 to F7 (audit of 4bb38c7; rulings in docs/decisions/ADR-0024-addendum-quiet-rule-rulings.md). Each fails on 4bb38c7 and passes after. Synthetic process tables,
injected clocks; the one real-thread test waits at most a few seconds with a deadline. Self-check only: not an independent review, not Astra validation, not human approval."""

import itertools
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import test_p10is1_quiet as TQ  # noqa: E402
import test_p10is1_quiet_rule as qr  # noqa: E402
import test_p10is1_stages as TS  # noqa: E402

from studies.p10is1 import baseline, core, freeze, machine, quiet, rehearsal_real  # noqa: E402

TOOL_SHELL = "/bin/zsh -c source /Users/x/.claude/shell-snapshots/snapshot-zsh-1795145190023-zhwmnx.sh 2>/dev/null || true && eval 'pytest tests/test_p10s1_core.py'"
REAL_PMSET = """System-wide power settings:
 Sleep On Power Button 1
 hibernatefile        /var/vm/sleepimage
 powernap             1
 networkoversleep     0
 disksleep            10
 sleep                0 (sleep prevented by caffeinate, caffeinate, caffeinate, Claude)
 displaysleep         10
 powermode            0
"""
REAL_BATT = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=36307043)\t100%; charged; 0:00 remaining present: true\n"


# --- F1: the lead's silence --------------------------------------------------------------------------------------------------------------------------
def test_f1_a_tool_call_shell_of_any_claude_session_outside_the_own_chain_fails_every_reading() -> None:
    fm = qr.FakeMachine()
    fm.extra = [(700, 1, TOOL_SHELL)]
    r = qr.reading(fm)
    assert "CLAUDE TOOL-CALL SHELL ACTIVE" in r["failed"] and r["tool_shells"][0].startswith("700:")
    # the shell that LAUNCHED the stage is an ancestor of it: the stage's own process chain is exempt
    table = [(1, 0, "/sbin/launchd"), (600, 1, TOOL_SHELL), (500, 600, "uv run python -m studies.p10is1.baseline run"), (501, 500, "python -m studies.p10is1.baseline run")]
    pr = fm.probe()
    pr.table, pr.pid = (lambda: table), 501
    assert "CLAUDE TOOL-CALL SHELL ACTIVE" not in machine.read_conditions(pr, qr.Q, condition="open")["failed"]
    table.append((800, 1, "python -m studies.p10is1.baseline run"))  # a caller that is not a descendant of the shell does see it
    pr.pid = 800
    assert "CLAUDE TOOL-CALL SHELL ACTIVE" in machine.read_conditions(pr, qr.Q, condition="open")["failed"]
    assert quiet.quiet_reading(probe=qr.FakeMachine().probe(), cfg=qr.qcfg())["quiet"] is True
    fm2 = qr.FakeMachine()
    fm2.extra = [(700, 1, TOOL_SHELL)]
    assert quiet.quiet_reading(probe=fm2.probe(), cfg=qr.qcfg())["failed"] == ["CLAUDE TOOL-CALL SHELL ACTIVE"]


def test_f1_a_tool_call_inside_a_baseline_attempt_discards_it_and_so_does_a_new_claude_process(tmp_path: Path) -> None:
    fm = qr.FakeMachine()

    def hook(m: qr.FakeMachine) -> None:
        if m.t == 200.0:
            m.extra.append((700, 1, TOOL_SHELL))
        elif m.t == 210.0:
            m.extra = [x for x in m.extra if x[0] != 700]

    fm.hooks.append(hook)
    rec = qr.run_session(fm, tmp_path / "a", qr.qcfg())
    assert rec["attempts"][0]["outcome"] == "DISCARDED" and "CLAUDE TOOL-CALL SHELL ACTIVE" in rec["attempts"][0]["reason"] and rec["status"] == "ACCEPTED" and rec["accepted"]["attempt"] == 2
    # the set of Claude processes must stay the same within an attempt: a second CLI session appears (presence unchanged: it was open)
    fm2 = qr.FakeMachine()
    fm2.extra = [(901, 1, qr.CLI_CMD)]
    fm2.hooks.append(lambda m: m.extra.append((902, 1, qr.CLI_CMD)) if m.t == 200.0 and len(m.extra) == 1 else None)
    rec2 = qr.run_session(fm2, tmp_path / "b", qr.qcfg())
    assert rec2["attempts"][0]["reason"] == "CLAUDE PROCESS SET CHANGED" and rec2["accepted"]["attempt"] == 2 and rec2["accepted"]["cli_present"] is True


def silent_watch(calls: list[int], fail_on: set[int], reason: str = "CLAUDE TOOL-CALL SHELL ACTIVE") -> Any:
    def watch(first: Any) -> list[str]:
        calls.append(1)
        return [reason] if len(calls) in fail_on else []

    return watch


def test_f1_f6_a_tool_call_during_the_measurement_discards_it_under_not_silent_and_it_never_counts(tmp_path: Path) -> None:
    clk = TQ.Clock()
    calls: list[int] = []
    # the watch runs at the first tick (measurement start) and the last (its end): the second call is the tick after the tool call
    r = TQ.drive(tmp_path, clk, [TQ.timed([1.0, 1.0, 1.0])] * 3, watch=silent_watch(calls, {2}))
    assert r["status"] == "COMPLETE" and len(r["discards"]) == 1 and r["discards"][0]["status"] == quiet.PAUSED_NOT_SILENT and r["discards"][0]["watch_failures"][0]["failed"] == ["CLAUDE TOOL-CALL SHELL ACTIVE"]
    assert quiet.paused_attempts(tmp_path, "timing") == []
    always = TQ.drive(tmp_path / "b", TQ.Clock(), itertools.repeat(TQ.timed([1.0, 1.0, 1.0])), watch=lambda first: ["CLAUDE TOOL-CALL SHELL ACTIVE"])
    assert always["status"] == quiet.PAUSED_NOT_SILENT == "PAUSED — NOT SILENT" and len(always["discards"]) >= 2  # retried inside the bounded wait, then the window runs out
    assert quiet.paused_attempts(tmp_path / "b", "timing") == [] and quiet.attempt_statuses(tmp_path / "b", "timing") == {1: quiet.PAUSED_NOT_SILENT}


def test_f1_the_set_of_claude_processes_must_be_the_same_from_the_quiet_reading_to_the_end_check(tmp_path: Path) -> None:
    quiet_r = {**TQ.QUIET, "claude_pids": [10, 11]}
    changed = {"ok": True, "other_study_processes": [], "failed": [], "conditions": {"claude_pids": [10, 11, 12]}}
    same = {"ok": True, "other_study_processes": [], "failed": [], "conditions": {"claude_pids": [10, 11]}}
    ends = itertools.chain([changed], itertools.repeat(same))
    r = TQ.drive(tmp_path, TQ.Clock(), itertools.repeat(TQ.timed([1.0, 1.0, 1.0])), readings=lambda: quiet_r, ends=lambda s: next(ends))
    assert r["status"] == "COMPLETE" and [d["status"] for d in r["discards"]] == [quiet.PAUSED_NOT_SILENT] and r["discards"][0]["failed"] == ["CLAUDE PROCESS SET CHANGED"]
    assert quiet.paused_attempts(tmp_path, "timing") == []
    # and the real end check carries the set
    fm = qr.FakeMachine()
    fm.extra = [(901, 1, qr.CLI_CMD)]
    e = quiet.end_check([], probe=fm.probe(), cfg=qr.qcfg(cli_present=True), sleep=lambda s: None)
    assert e["conditions"]["claude_pids"] == [901] and e["ok"] is True


# --- F2: no pytest exemption ------------------------------------------------------------------------------------------------------------------------
def test_f2_a_pytest_of_another_study_is_seen_by_the_baseline_and_the_stages_unless_a_test_only_allowance_is_passed(tmp_path: Path) -> None:
    fm = qr.FakeMachine()
    fm.extra = [(800, 1, "/usr/bin/python3 -m pytest tests/test_p10s5_core.py studies.p10is5.core")]
    assert qr.reading(fm)["failed"] == ["OTHER STUDY PROCESS ALIVE"]
    assert quiet.other_study_processes([(800, "pytest studies.p10s5.core")], own={1}) == ["800: pytest studies.p10s5.core"]
    pr = fm.probe()
    pr.allow = re.compile("pytest")
    assert machine.read_conditions(pr, qr.Q, condition="open")["failed"] == []
    assert quiet.other_study_processes([(800, "pytest studies.p10s5.core")], own={1}, allow=re.compile("pytest")) == []
    import inspect

    assert '"pytest" not in' not in inspect.getsource(machine) + inspect.getsource(quiet)
    rec = qr.run_session(_with_pytest_at(fm := qr.FakeMachine(), 200.0), tmp_path / "bl", qr.qcfg())
    assert rec["attempts"][0]["outcome"] == "DISCARDED" and "OTHER STUDY PROCESS ALIVE" in rec["attempts"][0]["reason"]
    assert fm.sleeps > 0


def _with_pytest_at(fm: qr.FakeMachine, at: float) -> qr.FakeMachine:
    def hook(m: qr.FakeMachine) -> None:
        if m.t == at:
            m.extra.append((800, 1, "python -m pytest studies.p10is5.tests"))
        elif m.t == at + 10.0:
            m.extra = []

    fm.hooks.append(hook)
    return fm


# --- F3: Low Power Mode ----------------------------------------------------------------------------------------------------------------------------
def test_f3_low_power_mode_is_read_from_both_spellings_and_an_unreadable_setting_refuses() -> None:
    ok = machine.parse_power(REAL_BATT, REAL_PMSET)  # this Mac's real output: `powermode 0`, no `lowpowermode`
    assert ok["mains"] is True and ok["low_power_mode"] is False and ok["power_settings"] == {"powermode": 0}
    assert machine.parse_power(REAL_BATT, REAL_PMSET.replace("powermode            0", "powermode            1"))["low_power_mode"] is True
    assert machine.parse_power(REAL_BATT, " lowpowermode 1\n")["low_power_mode"] is True and machine.parse_power(REAL_BATT, " lowpowermode 0\n")["low_power_mode"] is False
    for text in ("System-wide power settings:\n displaysleep 10\n", ""):
        with pytest.raises(ValueError, match="unreadable"):
            machine.parse_power(REAL_BATT, text)
    with pytest.raises(ValueError, match="power source"):
        machine.parse_power("", REAL_PMSET)
    assert machine.parse_power("Now drawing from 'Battery Power'\n", REAL_PMSET)["mains"] is False
    fm = qr.FakeMachine()
    pr = fm.probe()
    pr.power = lambda: machine.parse_power(REAL_BATT, "nothing\n")
    assert machine.read_conditions(pr, qr.Q, condition="open")["failed"] == ["POWER UNREADABLE"]  # never a pass
    pr.power = lambda: machine.parse_power(REAL_BATT, REAL_PMSET.replace("powermode            0", "powermode            1"))
    assert machine.read_conditions(pr, qr.Q, condition="open")["failed"] == ["LOW POWER MODE"]


# --- F4: one baseline per study ------------------------------------------------------------------------------------------------------------------
def test_f4_one_baseline_root_per_study_refuses_a_second_directory_and_a_new_first_baseline(tmp_path: Path) -> None:
    root = tmp_path / "root"
    assert baseline.resolve_out(root, False) == root / "first"  # nothing yet: the first baseline
    cfg = qr.small()
    for _ in range(2):  # a first baseline that is not settled (above the ceiling) is CONTINUED in the same place, every attempt listed
        rec = qr.run_session(qr.FakeMachine(lambda t: (2.6, 2.6)), baseline.resolve_out(root, False), cfg)
    assert rec["status"] == baseline.PAUSED_NO_BASELINE and [a["session"] for a in rec["attempts"]] == [1, 2] and len(rec["sessions"]) == 2
    assert baseline.resolve_out(root, False) == root / "first"
    with pytest.raises(core.StageRefused, match="no ACCEPTED first baseline to replace"):
        baseline.resolve_out(root, True)
    qr.run_session(qr.FakeMachine(), root / "first", cfg)  # accepted now
    with pytest.raises(core.StageRefused, match="taken once"):
        baseline.resolve_out(root, False)  # a new first baseline (in this or any other directory under this root) is refused: L cannot be re-rolled
    assert baseline.resolve_out(root, True) == root / "second"
    (root / "elsewhere").mkdir()
    qr.synthetic_baseline(root / "elsewhere")
    with pytest.raises(core.StageRefused, match="outside first/ and second/"):
        baseline.resolve_out(root, True)
    assert baseline.default_root().name == "P10IS1-quiet-baseline"


def test_f4_the_default_root_can_be_named_by_the_environment_and_the_command_uses_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P10IS1_BASELINE_ROOT", str(tmp_path / "r"))
    assert baseline.default_root() == tmp_path / "r"
    with pytest.raises(SystemExit):
        baseline.main(["run", "--out-dir", str(tmp_path / "x")])  # there is no --out-dir any more: the command works in the fixed root only


def test_f4_the_freeze_refuses_a_committed_record_that_is_not_the_roots_first_accepted_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    monkeypatch.setenv("P10IS1_BASELINE_ROOT", str(root))
    repo = TS.mini_repo(tmp_path / "m")  # its committed baseline is a synthetic record that is NOT in the root
    cfg = core.load_config(repo / core.CONFIG)
    qr.run_session(qr.FakeMachine(), root / "first", qr.qcfg())  # the study's own first baseline, a different record
    with pytest.raises(core.StageRefused, match="neither the first ACCEPTED record nor the second"):
        freeze.require_baseline(repo, cfg)
    # the committed record IS the root's first: accepted by the root check
    rec_path = repo / str(cfg["quiet"]["baseline_record_path"])
    rec_path.write_bytes((root / "first" / baseline.RECORD).read_bytes())
    (rec_path.parent / baseline.SAMPLES).write_bytes((root / "first" / baseline.SAMPLES).read_bytes())
    baseline.check_root_consistency(root, rec_path)
    # a second baseline that is ACCEPTED replaces the first: the first can no longer be the committed one
    second = root / "second"
    qr.run_session(qr.FakeMachine(), second, qr.qcfg(), condition="closed", second={"reason": "condition_change_by_human_lead", "replaces": "x", "utc": "2000-01-01T00:00:00+00:00"})
    with pytest.raises(core.StageRefused, match="the second replaced it"):
        baseline.check_root_consistency(root, rec_path)
    (second / baseline.REASON_FILE).write_text(json.dumps({"utc": "2999-01-01T00:00:00+00:00"}))
    with pytest.raises(core.StageRefused, match="reason file does not predate"):
        baseline.check_root_consistency(root, second / baseline.RECORD)
    (second / baseline.REASON_FILE).write_text(json.dumps({"utc": "2000-01-01T00:00:00+00:00"}))
    baseline.check_root_consistency(root, second / baseline.RECORD)


# --- F5: resume with another plan ---------------------------------------------------------------------------------------------------------------
def test_f5_resume_refuses_a_plan_whose_hash_differs_from_the_one_the_directory_was_started_with(tmp_path: Path) -> None:
    pl = TS.plan_of()
    pl.data.update({"caps_provisional": True, "stage_caps": {"train_hours": 1.0}})
    p1 = tmp_path / "plan1.json"
    p1.write_text(json.dumps(core.jsonable(pl.data)))
    run = tmp_path / "run"
    rehearsal_real.run_counting(p1, run, repo=TS.ROOT, chain=())
    assert json.loads((run / "counting_start.json").read_text())["plan_file_sha256"] == core.file_sha256(p1)
    rehearsal_real.run_counting(p1, run, repo=TS.ROOT, chain=(), resume=True)  # its own plan: allowed
    pl.data["stage_caps"] = {"train_hours": 2.0}
    p2 = tmp_path / "plan2.json"
    p2.write_text(json.dumps(core.jsonable(pl.data)))
    with pytest.raises(core.StageRefused, match="was started with the plan of SHA-256"):
        rehearsal_real.run_counting(p2, run, repo=TS.ROOT, chain=(), resume=True)
    with pytest.raises(core.StageRefused, match="no counting_start.json"):
        rehearsal_real.run_counting(p1, tmp_path / "other", repo=TS.ROOT, chain=(), resume=True)


# --- F6: the conditions at every tick of the measurement ------------------------------------------------------------------------------------
def test_f6_the_conditions_are_read_at_every_tick_of_the_measurement_and_a_failed_tick_is_kept() -> None:
    ticks: list[int] = []

    def check() -> list[str]:
        ticks.append(1)
        return ["CLAUDE TOOL-CALL SHELL ACTIVE"] if len(ticks) == 3 else []

    tr = quiet.LoadTrace(0.01, load_fn=lambda: 1.0, check_fn=check).start()
    deadline = time.monotonic() + 10.0
    while len(ticks) < 5 and time.monotonic() < deadline:
        time.sleep(0.01)
    tr.stop()
    assert len(ticks) >= 5 and [f["failed"] for f in tr.failures] == [["CLAUDE TOOL-CALL SHELL ACTIVE"]]  # a tick every interval, not only at the start and 120 s after the end
    boom = quiet.LoadTrace(1e9, load_fn=lambda: 1.0, check_fn=lambda: (_ for _ in ()).throw(OSError("ps")))
    boom.start()
    boom.stop()
    assert boom.failures and "UNREADABLE" in boom.failures[0]["failed"][0]


def test_f6_the_stage_reads_the_conditions_through_watch_conditions_and_compares_the_claude_set(tmp_path: Path) -> None:
    fm = qr.FakeMachine()
    first = quiet.quiet_reading(probe=fm.probe(), cfg=qr.qcfg())
    assert quiet.watch_conditions(first, probe=fm.probe(), cfg=qr.qcfg()) == []
    fm.extra = [(700, 1, TOOL_SHELL)]
    assert quiet.watch_conditions(first, probe=fm.probe(), cfg=qr.qcfg()) == ["CLAUDE TOOL-CALL SHELL ACTIVE"]
    fm.extra = [(901, 1, qr.CLI_CMD)]
    assert quiet.watch_conditions(first, probe=fm.probe(), cfg=qr.qcfg()) == ["APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S", "CLAUDE PROCESS SET CHANGED"]
    assert quiet.discard_status(["LOW POWER MODE"]) == quiet.PAUSED_DISCARDED and quiet.discard_status(["CLAUDE PROCESS SET CHANGED"]) == quiet.PAUSED_NOT_SILENT


# --- F7: a discard never counts towards NOT MEASURED ----------------------------------------------------------------------------------------------
def test_f7_end_check_and_in_measurement_discards_are_paused_retried_inside_the_wait_and_never_support_not_measured(tmp_path: Path) -> None:
    run = tmp_path
    bad_end = {"ok": False, "other_study_processes": ["5: x"], "failed": ["OTHER STUDY PROCESS ALIVE"]}
    for _ in range(6):
        r = TQ.drive(run, TQ.Clock(), itertools.repeat(TQ.timed([1.0, 1.0, 1.0])), ends=lambda s, e=bad_end: e)
        assert r["status"] == quiet.PAUSED_DISCARDED and len(r["discards"]) >= 2  # retried: the window ran out, not the first failure
    assert quiet.paused_attempts(run, "timing") == [] and set(quiet.attempt_statuses(run, "timing").values()) == {quiet.PAUSED_DISCARDED}
    dec = quiet.decision_path(run, "timing")
    dec.parent.mkdir(parents=True)
    dec.write_text(json.dumps({"decision": "NOT MEASURED", "stage": "timing", "paused_attempts": [1, 2, 3, 4, 5, 6], "decided_by": "the lead", "table_of_section_10": "labels that become unreachable"}))
    with pytest.raises(core.StageRefused, match="only 0 attempts ended PAUSED"):
        quiet.load_decision(run, "timing")  # six discarded sessions are not six PAUSED — QUIET CONDITION NOT MET sessions
    # a session with no quiet reading at all is still the one that counts
    never = TQ.drive(tmp_path / "b", TQ.Clock(), [], readings=lambda: TQ.NOT_QUIET)
    assert never["status"] == quiet.PAUSED_QUIET and quiet.paused_attempts(tmp_path / "b", "timing") == [1]


def test_f7_the_rulings_file_exists_and_states_the_standing_facts() -> None:
    text = (TS.ROOT / "docs" / "decisions" / "ADR-0024-addendum-quiet-rule-rulings.md").read_text()
    for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
        assert f"| {k} |" in text
    assert "No registered value of P10-I-S1 exists" in text and "sealed values are unopened" in text and "`Astra review: NOT_PERFORMED`" in text and "4,546.17 s = 1.2628 h" in text
