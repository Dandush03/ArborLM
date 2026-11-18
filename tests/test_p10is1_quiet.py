# ruff: noqa: E501
"""P10IS1 machine load rules (ADR-0024 sections 10, 16, 16.1, rulings 25 and 26): the machine-wide memory check from vm_stat, the quiet condition and its bounded sessions, the attempts, and the explicit decision without
which neither timing nor throughput ends NOT MEASURED. Every wait is driven by an injected clock: no test sleeps. Self-check only."""

import inspect
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is1 import core, quiet  # noqa: E402

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


def test_quiet_reading_each_condition() -> None:
    def reading(load: float = 0.5, cmds: list[tuple[int, str]] | None = None, mains: bool = True, low: bool = False) -> dict[str, Any]:
        return quiet.quiet_reading(load_fn=lambda: load, commands_fn=lambda: cmds or [], power_fn=lambda: {"mains": mains, "low_power_mode": low}, own={1})

    assert reading()["quiet"] is True and reading(load=1.0)["quiet"] is True  # at most 1.0
    r = reading(load=1.34)
    assert r["quiet"] is False and r["load_ok"] is False and r["processes_ok"] is True
    assert reading(load=0.73)["quiet"] is True
    other = [(5, "python -m studies.p10s1.stages timing --mode registered"), (6, "python -m studies.p10is1.stages train --run-dir x"), (7, "uv run python -m studies.p10ir.stages a1"), (1, "python -m studies.p10is1.stages timing")]
    r2 = reading(cmds=other)
    assert r2["quiet"] is False and len(r2["other_study_processes"]) == 3 and not any(p.startswith("1:") for p in r2["other_study_processes"])  # this process (pid 1) is not "another"
    assert reading(cmds=[(9, "pytest tests/test_p10s1_core.py studies.p10s1"), (10, "vim studies/p10s1/core.py")])["quiet"] is True
    assert reading(mains=False)["quiet"] is False and reading(low=True)["quiet"] is False


def test_a_session_waits_every_ten_minutes_for_at_most_six_hours() -> None:
    clk = Clock()
    seq = iter([{"quiet": False}, {"quiet": False}, {"quiet": True}])
    s = quiet.quiet_session(reading=lambda: next(seq), sleep=clk.sleep, clock=clk)
    assert s["quiet"] and len(s["readings"]) == 3 and clk.sleeps == [600.0, 600.0]
    clk2 = Clock()
    n = quiet.quiet_session(reading=lambda: {"quiet": False}, sleep=clk2.sleep, clock=clk2)
    assert n["quiet"] is False and len(n["readings"]) == 37 and clk2.t == 21600.0  # bounded: a session ends at 6 hours


def test_end_check_catches_a_process_that_started_during_the_run() -> None:
    cmds = [(5, "python -m studies.p10s2.stages train")]
    res = quiet.end_check([], commands_fn=lambda: cmds, own={1})
    assert res["ok"] is False and res["started_during"] and quiet.end_check([5], commands_fn=lambda: cmds, own={1})["started_during"] == []
    assert quiet.end_check([], commands_fn=lambda: [], own={1})["ok"] is True


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
            assert "write" not in line.lower().replace("def decision_path", "") or "read_json" in line  # the decision file is only ever read here
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

    not_quiet = {"quiet": False, "load_average": 1.5, "other_study_processes": [], "load_ok": False}
    quiet_r = {"quiet": True, "load_average": 0.5, "other_study_processes": []}
    r = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: not_quiet, end=lambda s: {"ok": True}, sleep=clk.sleep, clock=clk)
    assert r["status"] == "PAUSED — QUIET CONDITION NOT MET" and calls["measured"] == 0 and quiet.paused_attempts(tmp_path, "timing") == [1]  # a session without a quiet run: PAUSED and rescheduled, never ended
    bad_end = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: quiet_r, end=lambda s: {"ok": False, "other_study_processes": ["5: x"]}, sleep=clk.sleep, clock=clk)
    assert bad_end["status"] == "PAUSED — QUIET CONDITION NOT MET" and bad_end["discarded"] and calls["measured"] == 1 and quiet.paused_attempts(tmp_path, "timing") == [1, 2]
    good = quiet.run_alone_stage(tmp_path, "timing", measure, reading=lambda: quiet_r, end=lambda s: {"ok": True, "other_study_processes": []}, sleep=clk.sleep, clock=clk)
    assert good["status"] == "COMPLETE" and good["result"]["cpu"]["F-OQ|1024"] == 0.006 and calls["measured"] == 2 and quiet.paused_attempts(tmp_path, "timing") == [1, 2]
    rec = json.loads(Path(good["attempt_record"]).read_text())
    assert rec["attempt"] == 3 and rec["status"] == "QUIET RUN"
