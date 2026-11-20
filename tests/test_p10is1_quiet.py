# ruff: noqa: E501
"""P10IS1 machine load rules (ADR-0024 sections 10, 16, 16.1, rulings 25 and 26): the machine-wide memory check from vm_stat, the quiet condition and its bounded sessions, the attempts, and the explicit decision without
which neither timing nor throughput ends NOT MEASURED. Every wait is driven by an injected clock: no test sleeps. Self-check only."""

import inspect
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import test_p10is1_quiet_rule as qr  # noqa: E402

from studies.p10is1 import core, machine, quiet  # noqa: E402

VM = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               100.
Pages active:                             999.
Pages inactive:                           200.
Pages speculative:                         25.
Pages throttled:                            0.
Pages purgeable:                           50.
Pages wired down:                         777.
"""


class Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def test_available_memory_is_free_inactive_purgeable_speculative_pages_times_the_page_size() -> None:
    assert quiet.available_bytes(VM) == (100 + 200 + 50 + 25) * 16384  # active, wired and throttled pages are not counted
    with pytest.raises(ValueError):
        quiet.available_bytes("nothing")
    with pytest.raises(ValueError):
        quiet.available_bytes("page size of 4096 bytes\nPages free: 1.\n")


def test_memory_check_retries_every_ten_minutes_for_at_most_six_hours_then_pauses_environment() -> None:
    clk = Clock()
    texts = iter([VM.replace("free:                               100.", "free:                                 1."), VM])
    ok = quiet.check_memory(300 * 16384, reader=lambda: next(texts), sleep=clk.sleep, clock=clk)
    assert ok["ok"] and ok["attempts"] == 2 and clk.sleeps == [600.0]
    clk2 = Clock()
    never = quiet.check_memory(10**15, reader=lambda: VM, sleep=clk2.sleep, clock=clk2)
    assert never["ok"] is False and never["status"] == "PAUSED — ENVIRONMENT" and never["attempts"] == 37 and clk2.t == 21600.0  # 0, 600, ..., 21,600 s: 37 readings, then it stops
    assert all(s == 600.0 for s in clk2.sleeps)
    first = quiet.check_memory(1, reader=lambda: VM, sleep=Clock().sleep, clock=Clock())
    assert first["ok"] and first["attempts"] == 1  # no wait when the memory covers the guard at once


def _fake(load: tuple[float, float] = (1.0, 1.0), extra: list[tuple[int, int, str]] | None = None, **kw: Any) -> machine.Probe:
    rows = [(1, 0, "/sbin/launchd"), (500, 1, "python -m studies.p10is1.stages registered timing"), *(extra or [])]
    return machine.Probe(load=lambda: load, table=lambda: rows, power=lambda: {"mains": kw.get("mains", True), "low_power_mode": kw.get("low", False)}, therm=lambda: [], hid_ns=lambda: kw.get("hid", 10**13), boot=lambda: 1, pid=500)


CFG = qr.qcfg()  # a MEASURED quiet block: L = 180 hundredths (1.80), open condition, the application and Claude Code absent


def test_quiet_reading_is_one_and_five_minute_load_at_most_l_in_integer_hundredths() -> None:
    def rd(load: tuple[float, float], **kw: Any) -> dict[str, Any]:
        return quiet.quiet_reading(probe=_fake(load, **kw), cfg=CFG)

    assert rd((1.80, 1.80))["quiet"] is True and rd((0.5, 1.0))["quiet"] is True  # at most L, no fixed 1.0 anywhere
    assert rd((1.804, 1.80))["quiet"] is True and rd((1.806, 1.80))["failed"] == ["ONE-MINUTE LOAD ABOVE L"]  # rounded to hundredths first
    r = rd((1.20, 1.81))
    assert r["quiet"] is False and r["failed"] == ["FIVE-MINUTE LOAD ABOVE L"] and r["load_ok"] is False  # the five-minute average above L with the one-minute below
    assert rd((1.81, 1.81))["failed"] == ["ONE-MINUTE LOAD ABOVE L", "FIVE-MINUTE LOAD ABOVE L"]
    assert rd((1.0, 1.0), mains=False)["failed"] == ["NOT ON MAINS POWER"] and rd((1.0, 1.0), low=True)["failed"] == ["LOW POWER MODE"] and rd((1.0, 1.0), hid=10**9)["failed"] == ["IDLE TIME UNDER THE MINIMUM"]
    other = [(5, 1, "python -m studies.p10s1.stages timing --mode registered"), (6, 1, "python -m studies.p10is1.stages train --run-dir x"), (7, 1, "uv run python -m studies.p10ir.stages a1")]
    r2 = rd((1.0, 1.0), extra=other)
    assert r2["quiet"] is False and len(r2["other_study_processes"]) == 3 and not any(p.startswith("500:") for p in r2["other_study_processes"])  # this process is not "another"
    assert rd((1.0, 1.0), extra=[(9, 1, "pytest tests/test_p10s1_core.py studies.p10s1"), (10, 1, "vim studies/p10s1/core.py")])["quiet"] is True
    assert rd((1.0, 1.0), extra=[(900, 1, "/Applications/Claude.app/Contents/MacOS/Claude")])["failed"] == ["APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S"]  # the baseline had it closed
    app_cfg = qr.qcfg(app_present=True)
    assert quiet.quiet_reading(probe=_fake((1.0, 1.0), extra=[(900, 1, "/Applications/Claude.app/Contents/MacOS/Claude")]), cfg=app_cfg)["quiet"] is True
    assert quiet.quiet_reading(probe=_fake((1.0, 1.0)), cfg=app_cfg)["failed"] == ["APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S"]  # and the other direction


def test_a_provisional_or_out_of_range_limit_is_never_read() -> None:
    with pytest.raises(core.StageRefused, match="baseline_provisional is true"):
        quiet.quiet_reading(probe=_fake(), cfg=qr.qcfg(baseline_provisional=True))
    with pytest.raises(core.StageRefused, match="never clamped"):
        quiet.limit_of(qr.qcfg(load_limit=301))
    with pytest.raises(core.StageRefused, match="never clamped"):
        quiet.limit_of(qr.qcfg(load_limit=0))
    assert quiet.limit_of(qr.qcfg(load_limit=300)) == 300
    assert "load_average_max" not in core.load_config()["quiet"]  # the fixed 1.0 is removed, not left


def test_a_session_waits_every_ten_minutes_for_at_most_six_hours() -> None:
    clk = Clock()
    seq = iter([{"quiet": False}, {"quiet": False}, {"quiet": True}])
    s = quiet.quiet_session(reading=lambda: next(seq), sleep=clk.sleep, clock=clk)
    assert s["quiet"] and len(s["readings"]) == 3 and clk.sleeps == [600.0, 600.0]
    clk2 = Clock()
    n = quiet.quiet_session(reading=lambda: {"quiet": False}, sleep=clk2.sleep, clock=clk2)
    assert n["quiet"] is False and len(n["readings"]) == 37 and clk2.t == 21600.0  # bounded: a session ends at 6 hours


def test_end_check_waits_the_delay_then_needs_the_conditions_no_new_process_and_the_load_at_most_l() -> None:
    clk = Clock()
    cmds = [(5, 1, "python -m studies.p10s2.stages train")]
    res = quiet.end_check([], probe=_fake(extra=cmds), cfg=CFG, sleep=clk.sleep)
    assert clk.sleeps == [120.0]  # the load is read 120 s after the last measured update
    assert res["ok"] is False and res["started_during"] and quiet.end_check([5], probe=_fake(extra=cmds), cfg=CFG, sleep=clk.sleep)["started_during"] == []
    assert quiet.end_check([5], probe=_fake(extra=cmds), cfg=CFG, sleep=clk.sleep)["ok"] is False  # still alive at the end: another study's stage
    assert quiet.end_check([], probe=_fake(), cfg=CFG, sleep=clk.sleep)["ok"] is True
    late = quiet.end_check([], probe=_fake((1.81, 1.0)), cfg=CFG, sleep=clk.sleep)
    assert late["ok"] is False and late["failed"] == ["ONE-MINUTE LOAD ABOVE L AT THE END"] and late["load1_h_after_delay"] == 181
    assert quiet.end_check([], probe=_fake((1.80, 9.0)), cfg=CFG, sleep=clk.sleep)["ok"] is True  # only the one-minute load is read at the end
    assert quiet.end_check([], probe=_fake(hid=1), cfg=CFG, sleep=clk.sleep)["failed"] == ["IDLE TIME UNDER THE MINIMUM"]
    assert quiet.end_check([], probe=_fake(extra=[(900, 1, "/Applications/Claude.app/Contents/MacOS/Claude")]), cfg=CFG, sleep=clk.sleep)["ok"] is False


def _paused(run: Path, n: int, stage: str = "timing") -> None:
    for _ in range(n):
        quiet.record_attempt(run, stage, {"readings": [{"quiet": False, "load_average": 1.5}]}, status=quiet.PAUSED_QUIET)


def test_not_measured_needs_six_paused_attempts_and_an_explicit_decision_naming_them(tmp_path: Path) -> None:
    run = tmp_path
    dec = quiet.decision_path(run, "timing")
    assert quiet.load_decision(run, "timing") is None and quiet.stage_state(run, "timing", "timing.json") == "PAUSED"
    _paused(run, 5)
    body = {"decision": "NOT MEASURED", "stage": "timing", "paused_attempts": [1, 2, 3, 4, 5], "decided_by": "the lead", "table_of_section_10": "labels that are unreachable: CAPACITY-POSITIVE ..."}
    dec.parent.mkdir(parents=True)
    dec.write_text(json.dumps(body))
    with pytest.raises(core.StageRefused, match="only 5 attempts ended PAUSED; 6"):
        quiet.load_decision(run, "timing")  # before the first attempt and five rescheduled attempts have all ended PAUSED it cannot be accepted at all
    _paused(run, 1)
    with pytest.raises(core.StageRefused, match="must name the 6 PAUSED attempts"):
        quiet.load_decision(run, "timing")  # it names five
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6]}))
    assert quiet.load_decision(run, "timing")["decided_by"] == "the lead" and quiet.stage_state(run, "timing", "timing.json") == "NOT MEASURED"
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6], "decided_by": ""}))
    with pytest.raises(core.StageRefused, match="no decider"):
        quiet.load_decision(run, "timing")
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6], "table_of_section_10": "none"}))
    with pytest.raises(core.StageRefused, match="table of section 10"):
        quiet.load_decision(run, "timing")
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6], "decision": "MEASURED"}))
    with pytest.raises(core.StageRefused, match="NOT MEASURED for this stage"):
        quiet.load_decision(run, "timing")


def test_the_code_has_no_path_that_writes_a_not_measured_decision() -> None:
    src = inspect.getsource(quiet)
    assert "decision_path(" in src
    for line in src.splitlines():
        if "decision_path" in line:
            assert not any(w in line for w in ("write_text", "write_record", "write_json", "open(", ".mkdir")), line  # the decision file is only ever read here
    stages = Path(__file__).resolve().parents[1] / "studies" / "p10is1"
    for f in stages.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "write_record(quiet.decision_path" not in text and "write_record(decision_path" not in text and "_not_measured.json\"," not in text, f.name


def test_training_does_not_start_while_the_timing_stage_is_paused(tmp_path: Path) -> None:
    with pytest.raises(core.StageRefused, match="training does not start"):
        quiet.require_timing_settled(tmp_path)
    (tmp_path / "timing").mkdir()
    (tmp_path / "timing" / "timing.json").write_text("{}")
    assert quiet.require_timing_settled(tmp_path) == "COMPLETE"
    assert quiet.throughput_label(tmp_path) == "THROUGHPUT PENDING"  # analysis and report print it meanwhile
    (tmp_path / "throughput").mkdir()
    (tmp_path / "throughput" / "throughput.json").write_text("{}")
    assert quiet.throughput_label(tmp_path) == "MEASURED"


def test_run_alone_stage_pauses_discards_and_completes(tmp_path: Path) -> None:
    clk = Clock()
    calls = {"measured": 0}

    def measure() -> dict[str, Any]:
        calls["measured"] += 1
        return {"cpu": {"F-OQ|1024": 0.006}}

    not_quiet = {"quiet": False, "load_average": 1.5, "other_study_processes": [], "load_ok": False, "failed": ["ONE-MINUTE LOAD ABOVE L"]}
    quiet_r = {"quiet": True, "load_average": 0.5, "other_study_processes": []}
    kw: dict[str, Any] = {"sleep": clk.sleep, "clock": clk, "cfg": CFG, "top_fn": lambda: []}
    r = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: not_quiet, end=lambda s: {"ok": True}, **kw)
    assert r["status"] == "PAUSED — QUIET CONDITION NOT MET" and calls["measured"] == 0 and quiet.paused_attempts(tmp_path, "timing") == [1]  # a session without a quiet run: PAUSED and rescheduled, never ended
    bad_end = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: quiet_r, end=lambda s: {"ok": False, "other_study_processes": ["5: x"]}, **kw)
    assert bad_end["status"] == "PAUSED — QUIET CONDITION NOT MET" and bad_end["discarded"] and calls["measured"] == 1 and quiet.paused_attempts(tmp_path, "timing") == [1, 2]
    good = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: quiet_r, end=lambda s: {"ok": True, "other_study_processes": []}, **kw)
    assert good["status"] == "COMPLETE" and good["result"]["cpu"]["F-OQ|1024"] == 0.006 and calls["measured"] == 2 and quiet.paused_attempts(tmp_path, "timing") == [1, 2]
    rec = json.loads(Path(good["attempt_record"]).read_text())
    assert rec["attempt"] == 3 and rec["status"] == "QUIET RUN"


# --- the waiting, the polls, the caps, the timing spread (ADR-0024 addendum A3.2, A3.4, A8 items 5, 6, 9) -------------------------------------------------
NOT_QUIET = {"quiet": False, "load_average": 2.5, "other_study_processes": [], "failed": ["ONE-MINUTE LOAD ABOVE L"]}
QUIET = {"quiet": True, "load_average": 0.5, "other_study_processes": [], "failed": []}
OK_END = {"ok": True, "other_study_processes": [], "failed": []}


def timed(runs: list[float]) -> dict[str, Any]:
    return {"cpu": {"A|1": sorted(runs)[1]}, "detail": {"A|1": {"runs": runs, "wall_runs": [r * 1.1 for r in runs]}}}


def drive(run: Path, clk: Clock, results: list[Any], *, readings: Any = None, stage: str = "timing", cap: float | None = None, spend: float = 5.0, account: dict[str, Any] | None = None, ends: Any = None) -> dict[str, Any]:
    seq = iter(results)

    def measure(guard: Any = None) -> Any:
        clk.t += spend  # the measurement takes ``spend`` seconds of the injected clock
        if guard is not None:
            guard()
        return next(seq)

    return quiet.run_alone_stage(
        run, stage, measure, reading=readings or (lambda: QUIET), end=ends or (lambda s: OK_END), sleep=clk.sleep, clock=clk, cfg=CFG, validate=(lambda res: quiet.timing_spreads(res, CFG)) if stage == "timing" else None, cap_seconds=cap, account=account,
        guarded=True, top_fn=lambda: [{"pid": 1, "pcpu": 9.0, "comm": "x"}], trace_factory=lambda: quiet.LoadTrace(1e9, load_fn=lambda: 1.0, clock=clk),
    )  # fmt: skip


def test_every_poll_is_written_to_the_run_directory_as_it_is_taken_with_the_failed_condition(tmp_path: Path) -> None:
    clk = Clock()
    seen: list[int] = []
    polls = quiet.polls_path(tmp_path, "timing")
    seq = iter([NOT_QUIET, NOT_QUIET, QUIET])

    def reading() -> dict[str, Any]:
        seen.append(len(polls.read_text().splitlines()) if polls.exists() else 0)  # what is on disk when the next poll is about to be taken
        return next(seq)

    r = drive(tmp_path, clk, [timed([1.0, 1.0, 1.0])], readings=reading)
    assert r["status"] == "COMPLETE" and seen == [0, 1, 2]
    rows = [json.loads(x) for x in polls.read_text().splitlines()]
    assert [x["poll"] for x in rows] == [1, 2, 3] and rows[0]["failed"] == ["ONE-MINUTE LOAD ABOVE L"] and rows[2]["quiet"] is True and rows[0]["wait"] == "timing wait 1"
    assert [x["elapsed_seconds"] for x in rows] == [0.0, 600.0, 1200.0]


def test_waiting_is_recorded_and_not_charged_and_the_wait_is_bounded(tmp_path: Path) -> None:
    clk = Clock()
    acct: dict[str, Any] = {}
    r = drive(tmp_path, clk, [], readings=lambda: NOT_QUIET, account=acct)
    assert r["status"] == quiet.PAUSED_QUIET and acct["wait_seconds"] == 21600.0 and acct["measure_seconds"] == 0.0  # six hours waited, nothing charged
    assert len(quiet.polls_path(tmp_path, "timing").read_text().splitlines()) == 37 and quiet.paused_attempts(tmp_path, "timing") == [1]
    clk2 = Clock()
    acct2: dict[str, Any] = {}
    seq = iter([NOT_QUIET] * 5 + [QUIET])
    ok = drive(tmp_path / "b", clk2, [timed([1.0, 1.0, 1.0])], readings=lambda: next(seq), account=acct2, spend=130.0)
    assert ok["status"] == "COMPLETE" and acct2["wait_seconds"] == 3000.0 and acct2["measure_seconds"] == 130.0  # the 50 minutes of waiting are not in the charged figure
    assert ok["wait_seconds"] == 3000.0 and ok["measure_seconds"] == 130.0


def test_the_stages_own_cap_applies_to_the_measuring_seconds_and_a_capped_session_is_its_own_status(tmp_path: Path) -> None:
    clk = Clock()
    acct: dict[str, Any] = {}
    r = drive(tmp_path, clk, [timed([1.0, 1.0, 1.0])], cap=10.0, spend=30.0, account=acct)
    assert r["status"] == quiet.PAUSED_CAP and acct["measure_seconds"] == 30.0 and quiet.paused_attempts(tmp_path, "timing") == []  # not a quiet failure: it never counts towards NOT MEASURED
    assert "cap" in r["reason"]
    clk2 = Clock()
    none_left = drive(tmp_path / "b", clk2, [], cap=0.0)
    assert none_left["status"] == quiet.PAUSED_CAP and clk2.t == 0.0  # no wait is begun when the cap is spent
    under = drive(tmp_path / "c", Clock(), [timed([1.0, 1.0, 1.0])], cap=100.0, spend=30.0)
    assert under["status"] == "COMPLETE"
    thr = drive(tmp_path / "d", Clock(), [{"results": {}}], stage="throughput", cap=10.0, spend=30.0)
    assert thr["status"] == quiet.PAUSED_CAP  # the same cap rule for the throughput stage


def test_the_top_ten_processes_and_the_load_trace_are_recorded_at_the_start_and_the_end(tmp_path: Path) -> None:
    r = drive(tmp_path, Clock(), [timed([1.0, 1.0, 1.0])])
    rec = json.loads(Path(r["attempt_record"]).read_text())
    assert rec["top_processes"]["start"] == rec["top_processes"]["end"] == [{"pid": 1, "pcpu": 9.0, "comm": "x"}] and len(rec["load_trace"]) >= 2 and rec["load_trace"][0]["load1_h"] == 100
    assert rec["wait_seconds"] == 0.0 and rec["measure_seconds"] == 5.0 and rec["retimed"] is False


@pytest.mark.parametrize(("runs", "ok"), [([100.0, 105.0, 100.0], True), ([100.0, 105.001, 100.0], False), ([100.0, 100.0, 100.0], True), ([100.0, 90.0, 100.0], False), ([0.0, 0.0, 0.0], False)])
def test_the_spread_is_max_minus_min_over_the_median_and_at_most_005_passes(runs: list[float], ok: bool) -> None:
    s = quiet.timing_spreads(timed(runs), CFG)
    assert s["ok"] is ok and s["bound"] == 0.05
    assert (s["failing_items"] == []) is ok


def test_a_spread_failure_times_the_whole_list_again_once_and_keeps_both(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clk = Clock()
    acct: dict[str, Any] = {}
    bad, good = timed([1.0, 1.2, 1.0]), timed([1.0, 1.01, 1.0])
    seq = iter([NOT_QUIET, QUIET, NOT_QUIET, QUIET])
    r = drive(tmp_path, clk, [bad, good], readings=lambda: next(seq), account=acct)
    assert r["status"] == "COMPLETE" and r["retimed"] is True and r["result"] == good and acct["measure_seconds"] == 10.0  # the retiming is charged: both measurements
    rec = json.loads(Path(r["attempt_record"]).read_text())
    assert rec["status"] == "QUIET RUN" and rec["retimed"] is True and [a["valid"] for a in rec["timing_attempts"]] == [False, True]
    assert rec["timing_attempts"][0]["result"] == bad and rec["timing_attempts"][1]["result"] == good  # readings of two attempts are never combined; both are kept
    assert "timing_spread_failure" in capsys.readouterr().out  # and printed
    waits = [json.loads(x)["wait"] for x in quiet.polls_path(tmp_path, "timing").read_text().splitlines()]
    assert waits == ["timing wait 1", "timing wait 1", "timing wait 2", "timing wait 2"]  # the second wait has its own name and its own deadline
    assert quiet.paused_attempts(tmp_path, "timing") == [] and quiet.spread_sessions(tmp_path, "timing") == 0


def test_the_second_wait_is_bounded_separately_from_the_first(tmp_path: Path) -> None:
    clk = Clock()
    n = {"i": 0}

    def reading() -> dict[str, Any]:
        n["i"] += 1
        return QUIET if n["i"] == 1 else NOT_QUIET  # quiet once, then never again

    acct: dict[str, Any] = {}
    r = drive(tmp_path, clk, [timed([1.0, 1.2, 1.0])], readings=reading, account=acct)
    assert r["status"] == quiet.PAUSED_SPREAD  # a session that held a spread failure is never a counted quiet failure
    assert acct["wait_seconds"] == 21600.0 and clk.t == 21600.0 + 5.0  # the second wait ran its own six hours, then stopped
    assert quiet.paused_attempts(tmp_path, "timing") == [] and quiet.spread_sessions(tmp_path, "timing") == 1
    assert len(quiet.polls_path(tmp_path, "timing").read_text().splitlines()) == 1 + 37


def test_a_second_spread_failure_ends_the_session_paused_timing_spread_and_three_sessions_return_to_the_lead(tmp_path: Path) -> None:
    for k in range(3):
        r = drive(tmp_path, Clock(), [timed([1.0, 1.2, 1.0]), timed([1.0, 1.3, 1.0])])
        assert r["status"] == quiet.PAUSED_SPREAD and quiet.paused_attempts(tmp_path, "timing") == [] and quiet.spread_sessions(tmp_path, "timing") == k + 1
        rec = json.loads(Path(r["attempt_record"]).read_text())
        assert rec["status"] == "PAUSED — TIMING SPREAD" and len(rec["timing_attempts"]) == 2
    with pytest.raises(core.StageRefused, match="3 sessions of the timing stage ended PAUSED — TIMING SPREAD: the matter returns to the human lead"):
        drive(tmp_path, Clock(), [timed([1.0, 1.0, 1.0])])
    assert quiet.stage_state(tmp_path, "timing", "timing.json") == "PAUSED"  # no outcome follows automatically


def test_a_failed_end_check_after_a_spread_failure_is_still_not_a_counted_session(tmp_path: Path) -> None:
    ends = iter([OK_END, {"ok": False, "other_study_processes": ["5: x"], "failed": ["OTHER STUDY PROCESS ALIVE"]}])
    r = drive(tmp_path, Clock(), [timed([1.0, 1.2, 1.0]), timed([1.0, 1.0, 1.0])], ends=lambda s: next(ends))
    assert r["status"] == quiet.PAUSED_SPREAD and r["discarded"] and quiet.paused_attempts(tmp_path, "timing") == []


def test_the_six_session_decision_refuses_when_the_sessions_it_names_include_a_timing_spread_one(tmp_path: Path) -> None:
    run = tmp_path
    for k in range(6):
        _paused(run, 1)
        if k == 2:  # a TIMING SPREAD session between the third and the fourth PAUSED
            quiet.record_attempt(run, "timing", {"readings": []}, status=quiet.PAUSED_SPREAD)
    assert quiet.paused_attempts(run, "timing") == [1, 2, 3, 5, 6, 7] and quiet.spread_sessions(run, "timing") == 1
    dec = quiet.decision_path(run, "timing")
    dec.parent.mkdir(parents=True)
    body = {"decision": "NOT MEASURED", "stage": "timing", "decided_by": "the lead", "table_of_section_10": "labels that become unreachable"}
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6]}))  # names the spread session 4
    with pytest.raises(core.StageRefused, match=r"did not end PAUSED — QUIET CONDITION NOT MET \(a TIMING SPREAD"):
        quiet.load_decision(run, "timing")
    dec.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 5, 6, 7]}))
    assert quiet.load_decision(run, "timing")["decided_by"] == "the lead"  # six PAUSED quiet sessions, the spread one not counted: qualifies
    only_spread = tmp_path / "b"
    for _ in range(6):
        quiet.record_attempt(only_spread, "timing", {"readings": []}, status=quiet.PAUSED_SPREAD)
    d2 = quiet.decision_path(only_spread, "timing")
    d2.parent.mkdir(parents=True)
    d2.write_text(json.dumps({**body, "paused_attempts": [1, 2, 3, 4, 5, 6]}))
    with pytest.raises(core.StageRefused, match="only 0 attempts ended PAUSED"):
        quiet.load_decision(only_spread, "timing")  # six TIMING SPREAD sessions never support NOT MEASURED
