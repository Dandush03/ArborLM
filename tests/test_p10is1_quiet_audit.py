# ruff: noqa: E501
"""P10IS1 quiet rule: the tests of the audit fixes F1 to F7 (audit of 4bb38c7; rulings in docs/decisions/ADR-0024-addendum-quiet-rule-rulings.md). Each fails on 4bb38c7 and passes after. Synthetic process tables,
injected clocks; the one real-thread test waits at most a few seconds with a deadline. Self-check only: not an independent review, not Astra validation, not human approval."""

import itertools
import json
import os
import re
import shutil
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

from arborlm.io import file_sha256  # noqa: E402
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

    assert '"P10IS1-quiet-baseline"' in Path(baseline.__file__).read_text()


def test_f4_no_option_environment_variable_or_launch_script_reaches_another_root_and_a_test_root_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import inspect

    src = inspect.getsource(baseline)
    assert "os.environ" not in src and "getenv" not in src and "import os" not in src and '"--root"' not in src  # no environment override and no option on any real path
    with pytest.raises(SystemExit):
        baseline.main(["run", "--root", str(tmp_path / "x")])
    with pytest.raises(SystemExit):
        baseline.main(["run", "--out-dir", str(tmp_path / "x")])
    for f in (TS.ROOT / "studies" / "p10is1" / "launch").glob("*.sh"):
        assert "--root" not in f.read_text() and "ROOT" not in f.read_text().replace("README", ""), f.name  # the launch scripts cannot reach the test-only override
    assert '"P10IS1-quiet-baseline"' in Path(baseline.__file__).read_text() and baseline.default_root() == baseline.canonical_root()
    # the test-only override marks the record, and the candidate plan and the freeze refuse it
    repo = TS.mini_repo(tmp_path / "m")
    cfg = core.load_config(repo / core.CONFIG)
    monkeypatch.setattr(baseline, "_test_root", tmp_path / "troot")
    rec = qr.run_session(qr.FakeMachine(), tmp_path / "troot" / "first", qr.qcfg())
    assert rec["test_root"] is True and rec["root"] == str((tmp_path / "troot").resolve())
    committed = repo / str(cfg["quiet"]["baseline_record_path"])
    committed.write_bytes((tmp_path / "troot" / "first" / baseline.RECORD).read_bytes())
    (committed.parent / baseline.SAMPLES).write_bytes((tmp_path / "troot" / "first" / baseline.SAMPLES).read_bytes())
    cfg2 = qr.qcfg(baseline_record_path=str(cfg["quiet"]["baseline_record_path"]), baseline_record_sha256=file_sha256(committed), load_p95=130, load_limit=180)
    with pytest.raises(core.StageRefused, match="test_root = false"):
        baseline.verify_against_config(repo, cfg2)
    with pytest.raises(core.StageRefused, match="test_root = false"):
        freeze.require_baseline(repo, cfg2)


def test_f4_the_freeze_refuses_when_the_canonical_root_is_absent_or_does_not_hold_the_committed_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = TS.mini_repo(tmp_path / "m")  # synthetic baseline mirrored into the test canonical root by the helper
    cfg = core.load_config(repo / core.CONFIG)
    assert freeze.require_baseline(repo, cfg)["load_limit"] == 180
    rec_path = repo / str(cfg["quiet"]["baseline_record_path"])
    monkeypatch.setattr(baseline, "canonical_root", lambda: tmp_path / "absent")
    with pytest.raises(core.StageRefused, match="does not exist"):
        freeze.require_baseline(repo, cfg)  # no skip: the baseline was not taken by the command
    other = tmp_path / "other"
    shutil.copytree(qr.CANON, other)
    monkeypatch.setattr(baseline, "canonical_root", lambda: other)
    with pytest.raises(core.StageRefused, match="not under the canonical root"):
        freeze.require_baseline(repo, cfg)  # the record says it was taken elsewhere
    monkeypatch.setattr(baseline, "canonical_root", lambda: qr.CANON)
    baseline.check_root_consistency(qr.CANON, rec_path)
    # a different record in the root (a re-rolled L): the committed one is neither its first nor its second
    keep = {f: (qr.CANON / "first" / f).read_bytes() for f in (baseline.RECORD, baseline.SAMPLES)}
    qr.synthetic_baseline(tmp_path / "rerolled", load=140)  # replaces the root's first by another accepted record
    with pytest.raises(core.StageRefused, match="neither the first ACCEPTED record nor the second"):
        baseline.check_root_consistency(qr.CANON, rec_path)
    for f, b in keep.items():
        (qr.CANON / "first" / f).write_bytes(b)
    baseline.check_root_consistency(qr.CANON, rec_path)
    # every attempt must be listed: the root's samples hold an attempt (2) that the committed record does not list
    rows = (qr.CANON / "first" / baseline.SAMPLES).read_text().splitlines()
    extra = json.loads(rows[0])
    extra["attempt"], extra["index"] = 2, 1
    for d in (qr.CANON / "first", rec_path.parent):
        (d / baseline.SAMPLES).write_text("\n".join([*rows, json.dumps(extra, sort_keys=True)]) + "\n")
        rec = core.read_record(d / baseline.RECORD, "quiet_baseline")
        rec["samples_sha256"] = file_sha256(d / baseline.SAMPLES)
        core.write_record(d / baseline.RECORD, rec, overwrite=True)
    with pytest.raises(core.StageRefused, match="every attempt must be listed"):
        baseline.check_root_consistency(qr.CANON, rec_path)


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


@pytest.fixture(autouse=True)
def _canonical_baseline_root_is_a_test_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    qr.use_canon(monkeypatch)


# --- N1: anchored markers, tested on a captured sample of this Mac's real process list ---------------------------------------------------------------
SAMPLE = TS.ROOT / "tests" / "data" / "p10is1_ps_comm_sample.txt"  # one `ps -Ao pid=,ppid=,comm=` call, user names removed, no arguments


def sample_rows() -> list[machine.Row]:
    rows = []
    for ln in SAMPLE.read_text().splitlines():
        pid, ppid, comm = ln.split(None, 2)
        rows.append((int(pid), int(ppid), comm))
    return rows


def n1_probe(extra: list[machine.Row]) -> machine.Probe:
    rows = sample_rows() + extra
    return machine.Probe(load=lambda: (1.0, 1.0), table=lambda: rows, power=lambda: {"mains": True, "low_power_mode": False}, therm=lambda: [], hid_ns=lambda: 10**13, boot=lambda: 1, pid=999999)


def test_n1_an_idle_machine_passes_and_each_real_vm_marker_fails_on_a_captured_process_list() -> None:
    rows = sample_rows()
    assert len(rows) > 500 and any("imklaunchagent" in c for _, _, c in rows) and any("TextInputMenuAgent" in c for _, _, c in rows)
    old = re.compile("UTM", re.IGNORECASE)  # the 4bb38c7 / 2449908 marker: matches always-running system processes on this Mac
    assert [c for _, _, c in rows if old.search(c)], "the captured list must contain the false positives the old marker had"
    r = machine.read_conditions(n1_probe([]), qr.Q, condition="open")
    assert "VIRTUAL MACHINE PRESENT" not in r["failed"] and r["vm_processes"] == []  # an idle machine passes
    real = {
        "Docker": "/Applications/Docker.app/Contents/MacOS/com.docker.backend", "Docker Desktop": "/Applications/Docker.app/Contents/MacOS/Docker Desktop", "Colima": "/opt/homebrew/bin/colima", "qemu": "/opt/homebrew/bin/qemu-system-aarch64",
        "UTM": "/Applications/UTM.app/Contents/MacOS/UTM", "VMware": "/Applications/VMware Fusion.app/Contents/Library/vmware-vmx", "Parallels": "/Applications/Parallels Desktop.app/Contents/MacOS/prl_vm_app",
        "Apple Virtualization": "/System/Library/Frameworks/Virtualization.framework/Versions/A/XPCServices/com.apple.Virtualization.VirtualMachine.xpc/Contents/MacOS/com.apple.Virtualization.VirtualMachine",
    }  # fmt: skip
    for name, path in real.items():
        got = machine.read_conditions(n1_probe([(900001, 1, path)]), qr.Q, condition="open")
        assert "VIRTUAL MACHINE PRESENT" in got["failed"] and got["vm_processes"][0].startswith("900001:"), name


# --- N2: only the load alone above L counts -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("failed", "status", "counted"),
    [
        (["ONE-MINUTE LOAD ABOVE L"], quiet.PAUSED_QUIET, True),
        (["ONE-MINUTE LOAD ABOVE L", "FIVE-MINUTE LOAD ABOVE L"], quiet.PAUSED_QUIET, True),
        (["ONE-MINUTE LOAD ABOVE L", "CLAUDE TOOL-CALL SHELL ACTIVE"], quiet.PAUSED_NOT_SILENT, False),
        (["CLAUDE PROCESS SET CHANGED"], quiet.PAUSED_NOT_SILENT, False),
        (["NOT ON MAINS POWER"], quiet.PAUSED_CONDITION, False),
        (["ONE-MINUTE LOAD ABOVE L", "VIRTUAL MACHINE PRESENT"], quiet.PAUSED_CONDITION, False),
        (["OTHER STUDY PROCESS ALIVE"], quiet.PAUSED_CONDITION, False),
        (["APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S"], quiet.PAUSED_CONDITION, False),
        (["LOAD UNREADABLE"], quiet.PAUSED_CONDITION, False),
    ],
)
def test_n2_a_session_whose_waits_failed_on_anything_but_the_load_never_counts(failed: list[str], status: str, counted: bool, tmp_path: Path) -> None:
    reading = {"quiet": False, "load_average": 2.5, "other_study_processes": [], "failed": failed}
    r = TQ.drive(tmp_path, TQ.Clock(), [], readings=lambda: reading)
    assert r["status"] == status and (quiet.paused_attempts(tmp_path, "timing") == [1]) is counted
    assert quiet.wait_status([reading]) == status
    assert quiet.wait_status([TQ.NOT_QUIET, reading]) == (quiet.PAUSED_QUIET if counted else status)  # one bad reading among load-only ones decides
    if not counted:  # six such sessions are not six PAUSED — QUIET CONDITION NOT MET sessions
        for _ in range(5):
            TQ.drive(tmp_path, TQ.Clock(), [], readings=lambda: reading)
        dec = quiet.decision_path(tmp_path, "timing")
        dec.parent.mkdir(parents=True)
        dec.write_text(json.dumps({"decision": "NOT MEASURED", "stage": "timing", "paused_attempts": [1, 2, 3, 4, 5, 6], "decided_by": "the lead", "table_of_section_10": "labels that become unreachable"}))
        with pytest.raises(core.StageRefused, match="only 0 attempts ended PAUSED"):
            quiet.load_decision(tmp_path, "timing")


# --- N3: the watch is a child process; its CPU is not the measuring process's ------------------------------------------------------------------------
def idle_cpu(seconds: float) -> float:
    c0 = time.process_time()
    time.sleep(seconds)
    return time.process_time() - c0


def test_n3_the_child_watch_adds_no_cpu_to_the_measuring_process_and_the_in_process_thread_does(tmp_path: Path) -> None:
    """The measuring process sleeps for one second of wall time (CPU-free); only the watch could add CPU to ``process_time``. Three conditions: no watch, the watch as a CHILD process (interval 0.05 s), and the
    previous design, the same reading in a THREAD of this process. The numbers are printed (pytest -s) and stated in the report."""
    first = {"claude_pids": None}
    cfg = qr.qcfg()
    base = min(idle_cpu(1.0) for _ in range(3))
    cw = quiet.ChildWatch(tmp_path / "w" / "watch.jsonl", first, interval=0.05).start()
    child_cpu = idle_cpu(1.0)
    res = cw.stop()
    tr = quiet.LoadTrace(0.05, load_fn=lambda: 1.0, check_fn=lambda: quiet.watch_conditions(first, cfg=cfg)).start()
    thread_cpu = idle_cpu(1.0)
    tr.stop()
    print(f"N3 parent CPU over 1.0 s idle: no watch {base * 1000:.1f} ms, child watch {child_cpu * 1000:.1f} ms (child itself {1000 * (res['child_cpu_seconds'] or 0):.1f} ms in {res['ticks']} ticks), in-process thread {thread_cpu * 1000:.1f} ms")
    assert res["ticks"] >= 5 and res["child_cpu_seconds"] and res["child_cpu_seconds"] > 0.05  # the child really read the conditions, many times, at its own CPU cost
    assert child_cpu - base < 0.01  # the child's work is not in this process's process_time
    assert thread_cpu - base > 0.04 and thread_cpu > 4 * max(child_cpu - base, 0.005)  # the thread design charged the measuring process


@pytest.mark.skipif(sys.platform != "darwin", reason="the process tree of record is macOS")
def test_n3_the_child_is_in_the_stages_own_process_family_and_records_failures(tmp_path: Path) -> None:
    cw = quiet.ChildWatch(tmp_path / "w.jsonl", {"claude_pids": [1, 2, 3]}, interval=0.05).start()  # a Claude set that cannot be the real one: the child must report a change
    try:
        assert cw.pid in machine.family(machine.ps_table(), os.getpid())  # a descendant: its command line (studies.p10is1.watch_child) is not another study's process
        assert cw.pid is not None and not any(str(cw.pid) == o.split(":")[0] for o in quiet.other_study_processes())
    finally:
        res = cw.stop()
    assert res["ticks"] >= 2 and any("CLAUDE PROCESS SET CHANGED" in f["failed"] for f in res["failures"]) and "WATCH CHILD DID NOT RUN" not in json.dumps(res)
    dead = quiet.ChildWatch(tmp_path / "never.jsonl", {}, interval=0.05)
    assert dead.stop()["failures"][0]["failed"] == ["WATCH CHILD DID NOT RUN"]  # fail closed


def test_n3_the_stage_starts_the_watch_before_the_measurement_reads_it_after_and_discards_on_its_failures(tmp_path: Path) -> None:
    log: list[str] = []

    class Fake:
        def __init__(self, fail: bool) -> None:
            self.fail = fail

        def start(self) -> "Fake":
            log.append("start")
            return self

        def stop(self) -> dict[str, Any]:
            log.append("stop")
            return {"failures": [{"t": 1.0, "failed": ["CLAUDE TOOL-CALL SHELL ACTIVE"]}] if self.fail else [], "ticks": 3, "child_cpu_seconds": 0.07}

    made = iter([Fake(True), Fake(False)])
    clk = TQ.Clock()

    def measure(guard: Any = None) -> Any:
        log.append("measure")
        return TQ.timed([1.0, 1.0, 1.0])

    r = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: TQ.QUIET, end=lambda s: TQ.OK_END, sleep=clk.sleep, clock=clk, cfg=TQ.CFG, validate=lambda res: quiet.timing_spreads(res, TQ.CFG), guarded=True, top_fn=lambda: [], trace_factory=lambda: quiet.LoadTrace(1e9, load_fn=lambda: 1.0, clock=clk), child_watch=lambda first, path: next(made))
    assert log == ["start", "measure", "stop", "start", "measure", "stop"]  # started BEFORE the measurement, read AFTER it
    assert r["status"] == "COMPLETE" and [d["status"] for d in r["discards"]] == [quiet.PAUSED_NOT_SILENT] and r["discards"][0]["failed"] == ["CLAUDE TOOL-CALL SHELL ACTIVE"]
    rec = json.loads(Path(r["attempt_record"]).read_text())
    assert rec["watch_child"]["child_cpu_seconds"] == 0.07 and quiet.paused_attempts(tmp_path, "timing") == []


def test_n3_the_registered_stage_uses_the_child_watch_unless_a_test_injects_its_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    from studies.p10is1 import items, rehearsal, stages

    root = tmp_path / "r"
    root.mkdir()
    cfg_path = root / "tiny.toml"
    cfg_path.write_text(qr.measured_quiet_text(rehearsal.tiny_config_text()))
    pl = rehearsal.tiny_plan(root, TS.ROOT, cfg_path)
    seen: list[dict[str, Any]] = []

    def spy(run_dir: Path, stage: str, measure: Any, **kw: Any) -> dict[str, Any]:
        seen.append({"child": kw["child_watch"] is not None, "watch": kw["watch"] is not None})
        return {"status": quiet.PAUSED_QUIET, "attempt_record": "x", "paused_attempts": [], "wait_seconds": 0.0, "measure_seconds": 0.0}

    monkeypatch.setattr(quiet, "run_alone_stage", spy)
    ctx = items.Ctx(core.TEST, root / "run", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    stages.execute_stage("timing", pl, ctx, root / "run", pl.path, args, repo=TS.ROOT, inline=True)  # nothing injected: the real watch
    stages.execute_stage("timing", pl, ctx, root / "run2", pl.path, args, repo=TS.ROOT, inline=True, quiet_reading=lambda: TQ.QUIET)  # a test injected the reading: no real watch
    stages.execute_stage("timing", pl, ctx, root / "run3", pl.path, args, repo=TS.ROOT, inline=True, quiet_reading=lambda: TQ.QUIET, watch_fn=lambda first: [])
    assert seen == [{"child": True, "watch": False}, {"child": False, "watch": False}, {"child": False, "watch": True}]


# --- N4: stop list and offending command lines --------------------------------------------------------------------------------------------------
def test_n4_the_baseline_refuses_before_sampling_and_prints_the_offending_command_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fm = qr.FakeMachine()
    fm.extra = [(700, 1, TOOL_SHELL), (701, 1, "python -m studies.p10is5.stages registered timing"), (702, 1, "/opt/homebrew/bin/colima daemon")]
    with pytest.raises(core.StageRefused) as ei:
        baseline.preflight(probe=fm.probe(), cfg=qr.qcfg())
    msg = str(ei.value)
    assert "tool-call shells of Claude sessions:" in msg and "700: /bin/zsh -c source /Users/x/.claude/shell-snapshots/snapshot-zsh" in msg and "701: python -m studies.p10is5.stages registered timing" in msg and "702: /opt/homebrew/bin/colima daemon" in msg
    baseline.preflight(probe=qr.FakeMachine().probe(), cfg=qr.qcfg())  # a quiet machine passes
    # through the command: exit 2, the lines on stderr, no sample and no record written
    monkeypatch.setattr(baseline, "_test_root", tmp_path / "troot")
    fake_probe = fm.probe()
    monkeypatch.setattr(machine, "Probe", lambda: fake_probe)
    assert baseline.main(["run"]) == 2
    err = capsys.readouterr().err
    assert "700: /bin/zsh -c source" in err and "stop these processes before the baseline" in err and not (tmp_path / "troot").exists()


def test_n4_the_run_sheet_says_which_processes_to_stop_before_the_baseline() -> None:
    text = (TS.ROOT / "studies" / "p10is1" / "README_RUN.md").read_text()
    for needle in ("shell-snapshots/snapshot-", "background", "tool-call shell of every Claude session", "other studies", "run_in_background"):
        assert needle in text, needle
