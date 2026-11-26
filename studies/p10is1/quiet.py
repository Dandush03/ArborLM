# ruff: noqa: E501
"""P10IS1 machine load rules (ADR-0024 sections 10, 16, 16.1 as amended by the quiet-rule addendum, rulings 25 and 26): the machine-wide memory check, the quiet condition of the two stages that run ALONE (the isolated
timing stage, the source of MC-T, and the read-path throughput stage), the attempts and their records, and the explicit decision without which neither ends NOT MEASURED. Every wait has a deadline. Nothing here reads a
registered seed.

* Memory check (ruling 26): available memory = (free + inactive + purgeable + speculative pages) x page size from ``vm_stat``, read at the start of each stage and before each worker is added; it must cover the stage's
  aggregate guard; retried every 10 minutes for at most 6 hours, then PAUSED — ENVIRONMENT.
* Quiet reading (addendum A3.2, A3.3): the one-minute AND the five-minute load averages (each rounded to hundredths, compared as integers) at most L, the limit MEASURED on this machine by the study's own baseline
  (``baseline.py``, never a constant here), and every condition of ``machine.read_conditions`` (no process of another study's stage (the caller's own process family excepted), no virtual machine, mains, not Low Power Mode, no
  thermal warning, idle time, the application's presence equal to the baseline's). Retried every 10 minutes for at most 6 hours in a session, EACH WAIT with its own deadline (the second wait of a re-timing too); every
  poll is appended to ``<stage>/polls.jsonl`` as it is taken, with the condition that failed. At the end: the conditions hold, no study process started during the stage and the one-minute load read 120 s after the last
  measured update is at most L. Waiting is NOT charged (ADR-0028 section 9): the charged seconds are the measuring seconds, from the quiet reading to the end check (the 120 s included), and the stage's own cap applies
  to them.
* Timing spread (addendum A3.4): per item s = (max - min) / median of the three CPU repeats must be at most 0.05; on a failure the WHOLE list is timed once more after a new quiet reading; a second failure ends the
  session PAUSED — TIMING SPREAD, a status of its own that never counts towards the six sessions of NOT MEASURED; after three such sessions the stage returns to the human lead (a refusal).
* A session without a quiet run is PAUSED — QUIET CONDITION NOT MET and the stage is rescheduled. A timeout never ends a stage NOT MEASURED. NOT MEASURED is recorded only by an explicit decision file naming the six
  PAUSED attempts (the first and five rescheduled) and the table of section 10; the code offers no other path (``load_decision``), and training does not start while the timing stage is PAUSED (``require_timing_settled``).
"""

import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import core, loadrule, machine

PAUSED_QUIET = "PAUSED — QUIET CONDITION NOT MET"
PAUSED_SPREAD = "PAUSED — TIMING SPREAD"
PAUSED_CAP = "PAUSED — STAGE CAP"
PAUSED_NOT_SILENT = "PAUSED — NOT SILENT"  # F1/F6: a tool call of a Claude session, or a changed set of Claude processes, during the measurement or at the end check; never counted
PAUSED_CONDITION = "PAUSED — MACHINE CONDITION"  # N2: wait readings failed on a machine condition other than the load being above L (and not on silence); never counted
LOAD_FAILURES = ("ONE-MINUTE LOAD ABOVE L", "FIVE-MINUTE LOAD ABOVE L")
PAUSED_DISCARDED = "PAUSED — MEASUREMENT DISCARDED"  # F7: an end-check or in-measurement discard of any other cause; never counted (it is retried inside the bounded wait)
PAUSED_ENVIRONMENT = "PAUSED — ENVIRONMENT"
NOT_MEASURED = "NOT MEASURED"
STAGES_ALONE = ("timing", "throughput")
STUDY_STAGE_RE = machine.STUDY_STAGE_RE


# --- the machine-wide memory check (section 16.1, ruling 26) -------------------------------------------------------------------------------------------
def vm_stat_text() -> str:
    return subprocess.run(["vm_stat"], capture_output=True, text=True, check=True, timeout=30).stdout  # noqa: S607


def available_bytes(text: str, kinds: Sequence[str] = ("free", "inactive", "purgeable", "speculative")) -> int:
    """(free + inactive + purgeable + speculative pages) x page size, from the text of ``vm_stat``."""
    m = re.search(r"page size of (\d+) bytes", text)
    if not m:
        raise ValueError("vm_stat output without a page size")
    size = int(m.group(1))
    pages = 0
    for kind in kinds:
        mm = re.search(rf"Pages {kind}:\s+(\d+)\.", text)
        if not mm:
            raise ValueError(f"vm_stat output without 'Pages {kind}'")
        pages += int(mm.group(1))
    return pages * size


def memory_ok_once(guard_bytes: int, *, reader: Callable[[], str] = vm_stat_text, kinds: Sequence[str] = ("free", "inactive", "purgeable", "speculative")) -> bool:
    """ONE reading, never a wait: does the available memory of the machine cover ``guard_bytes`` now? The runner calls it before each worker is added while it keeps supervising the workers that are running (finding F10);
    the retry cadence and the six-hour limit are the runner's (``memory_retry``, ``memory_max``)."""
    return available_bytes(reader(), kinds) >= guard_bytes


def check_memory(guard_bytes: int, *, reader: Callable[[], str] = vm_stat_text, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The available memory of the whole machine must cover ``guard_bytes`` (the stage's aggregate guard). Retried every ``retry_seconds`` until ``max_hours`` have passed; then ``PAUSED — ENVIRONMENT``. Bounded:
    the deadline is checked before every wait."""
    c = core.cfg_of(cfg)["memory_check"]
    retry, limit = float(c["retry_seconds"]), float(c["max_hours"]) * 3600.0
    began = clock()
    readings: list[dict[str, Any]] = []
    kinds = tuple(c["page_kinds"])
    while True:
        avail = available_bytes(reader(), kinds)
        readings.append({"available_bytes": avail, "guard_bytes": guard_bytes})
        if avail >= guard_bytes:
            return {"ok": True, "status": "OK", "attempts": len(readings), "readings": readings}
        if clock() - began + retry > limit:
            return {"ok": False, "status": PAUSED_ENVIRONMENT, "attempts": len(readings), "readings": readings, "reason": "the available memory of the machine does not cover the stage's aggregate guard"}
        sleep(retry)


# --- the quiet reading (addendum A3.2, A3.3) ----------------------------------------------------------------------------------------------------------
def ps_commands() -> list[tuple[int, str]]:
    return [(pid, cmd) for pid, _, cmd in machine.ps_table()]


def own_pids() -> set[int]:
    """This process, its ancestors (the ``uv run`` wrapper that started it names the same stage) AND its descendants (a keep-awake watcher the stage started)."""
    return machine.family(machine.ps_table(), os.getpid())


def other_study_processes(commands: Sequence[tuple[int, str]] | None = None, own: set[int] | None = None, allow: re.Pattern[str] | None = None) -> list[str]:
    """Processes of any ArborLM study's stage (``python -m studies.p9...`` / ``studies.p10...``, this study's other stages included) other than this one's own family."""
    if commands is not None:
        me = own if own is not None else own_pids()
        return [f"{pid}: {cmd}" for pid, cmd in commands if pid not in me and STUDY_STAGE_RE.search(cmd) and not (allow and allow.search(cmd))]
    table = machine.ps_table()
    me = own if own is not None else machine.family(table, os.getpid())
    return [f"{pid}: {cmd}" for pid, _, cmd in table if pid not in me and STUDY_STAGE_RE.search(cmd) and not (allow and allow.search(cmd))]


def power_state() -> dict[str, Any]:
    """Mains power and Low Power Mode from ``pmset`` (macOS)."""
    return machine.real_power()


def limit_of(cfg: Mapping[str, Any] | None = None) -> int:
    """L in hundredths from the config. The config's figure is MEASURED by the study's baseline; while ``baseline_provisional`` is true, or L is not a positive figure within the ceiling, no stage may read it."""
    q = core.cfg_of(cfg)["quiet"]
    if q["baseline_provisional"]:
        raise core.StageRefused("refused: [quiet] baseline_provisional is true: the quiet limit L is measured by the study's own baseline (python -m studies.p10is1.baseline run) and written into the config before any stage reads it")
    limit = int(q["load_limit"])
    if limit <= 0 or limit > int(q["load_ceiling"]):
        raise core.StageRefused(f"refused: the config's load_limit {limit} (hundredths) is not within (0, {int(q['load_ceiling'])}]: a limit above the ceiling is refused, never clamped")
    return limit


def expected_presence(cfg: Mapping[str, Any] | None = None) -> tuple[bool, bool]:
    q = core.cfg_of(cfg)["quiet"]
    return bool(q["app_present"]), bool(q["cli_present"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def quiet_reading(*, probe: machine.Probe | None = None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One quiet reading (A3.2): the one-minute AND the five-minute load averages, each rounded to hundredths, at most L; every condition of A3.3, the application's presence equal to the baseline's. ``failed`` names
    every condition that did not hold; ``quiet`` is true only if none failed."""
    q = core.cfg_of(cfg)["quiet"]
    limit = limit_of(cfg)
    pr = probe or machine.Probe()
    cond = machine.read_conditions(pr, q, condition=str(q["condition"]), expect=expected_presence(cfg))
    failed = list(cond["failed"])
    out: dict[str, Any] = {**cond, "utc": _now(), "limit_h": limit}
    try:
        l1, l5 = pr.load()
        h1, h5 = loadrule.hundredths(l1), loadrule.hundredths(l5)
        out.update(load_average=float(l1), load5_average=float(l5), load1_h=h1, load5_h=h5)
        if h1 > limit:
            failed.append("ONE-MINUTE LOAD ABOVE L")
        if h5 > limit:
            failed.append("FIVE-MINUTE LOAD ABOVE L")
        out["load_ok"] = h1 <= limit and h5 <= limit
    except Exception:  # noqa: BLE001 - fail closed
        failed.append("LOAD UNREADABLE")
        out.update(load_average=float("nan"), load_ok=False)
    out["processes_ok"] = not out.get("other_study_processes")
    out["failed"] = failed
    out["quiet"] = not failed
    return out


def append_line(path: Path, obj: Mapping[str, Any]) -> None:
    """One JSON line appended and forced to disk: a poll or a sample is on disk when it has been taken."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(core.jsonable(dict(obj)), sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def polls_path(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "polls.jsonl"


def quiet_session(*, reading: Callable[[], dict[str, Any]], sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic, cfg: Mapping[str, Any] | None = None, log_path: Path | None = None, wait: str = "", limit_seconds: float | None = None) -> dict[str, Any]:
    """One WAIT for a quiet reading: the start conditions are checked and, if they are not met, every ``poll_seconds`` for at most ``session_hours`` (this wait's own deadline). Bounded: the deadline is checked before
    every sleep. Every reading is appended to ``log_path`` as it is taken. Returns the readings and whether a quiet reading was found."""
    q = core.cfg_of(cfg)["quiet"]
    poll, limit = float(q["poll_seconds"]), float(q["session_hours"]) * 3600.0 if limit_seconds is None else float(limit_seconds)
    began = clock()
    readings: list[dict[str, Any]] = []
    while True:
        r = reading()
        readings.append(r)
        if log_path is not None:
            append_line(log_path, {"wait": wait, "poll": len(readings), "elapsed_seconds": clock() - began, **r})
        if r["quiet"]:
            return {"quiet": True, "readings": readings}
        if clock() - began + poll > limit:
            return {"quiet": False, "readings": readings}
        sleep(poll)


def end_check(started_pids: Sequence[int], *, probe: machine.Probe | None = None, cfg: Mapping[str, Any] | None = None, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """The end of a quiet stage (A3.2): wait ``end_load_delay_seconds`` (120 s: the stage's own thread has left the one-minute average), then every condition of A3.3 must hold, no study process may have started during
    the stage (one absent at the start and present now), and the one-minute load, rounded to hundredths, is at most L. Otherwise the figures are discarded and the run repeated."""
    q = core.cfg_of(cfg)["quiet"]
    limit = limit_of(cfg)
    pr = probe or machine.Probe()
    sleep(float(q["end_load_delay_seconds"]))
    cond = machine.read_conditions(pr, q, condition=str(q["condition"]), expect=expected_presence(cfg))
    failed = list(cond["failed"])
    started = set(started_pids)
    during = [a for a in cond["other_study_processes"] if int(a.split(":", 1)[0]) not in started]
    if during:
        failed.append("STUDY PROCESS STARTED DURING THE STAGE")
    out: dict[str, Any] = {"utc": _now(), "other_study_processes": cond["other_study_processes"], "started_during": during, "limit_h": limit, "conditions": cond}
    try:
        h1 = loadrule.hundredths(pr.load()[0])
        out["load1_h_after_delay"] = h1
        if h1 > limit:
            failed.append("ONE-MINUTE LOAD ABOVE L AT THE END")
    except Exception:  # noqa: BLE001
        failed.append("LOAD UNREADABLE AT THE END")
    out["failed"] = failed
    out["ok"] = not failed
    return out


class LoadTrace:
    """The one-minute load every ``interval`` seconds while a quiet stage measures (descriptive, A8 item 5): a sleeping thread that reads ``getloadavg``. Stopped in a ``finally``."""

    def __init__(self, interval: float, load_fn: Callable[[], float] = lambda: os.getloadavg()[0], clock: Callable[[], float] = time.monotonic, check_fn: Callable[[], list[str]] | None = None) -> None:
        self.interval, self.load_fn, self.clock = float(interval), load_fn, clock
        self.check_fn = check_fn  # F6: the machine's conditions, read at every tick; a failure is kept in ``failures``
        self.failures: list[dict[str, Any]] = []
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    def _take(self) -> None:
        try:
            self.samples.append({"t_seconds": self.clock() - self._t0, "load1_h": loadrule.hundredths(self.load_fn())})
        except Exception:  # noqa: BLE001 - descriptive only
            self.samples.append({"t_seconds": self.clock() - self._t0, "load1_h": None})
        if self.check_fn is not None:
            try:
                failed = list(self.check_fn())
            except Exception as exc:  # noqa: BLE001 - an unreadable condition fails closed
                failed = [f"CONDITIONS UNREADABLE DURING THE MEASUREMENT ({str(exc)[:80]})"]
            if failed:
                self.failures.append({"t_seconds": self.clock() - self._t0, "failed": failed})

    def start(self) -> "LoadTrace":
        self._t0 = self.clock()
        self._take()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self._take()

    def stop(self) -> list[dict[str, Any]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=30)
        self._take()
        return self.samples


def watch_conditions(first: Mapping[str, Any], *, probe: machine.Probe | None = None, cfg: Mapping[str, Any] | None = None) -> list[str]:
    """F6: the conditions of A3.3 (not the loads) read once, compared with the quiet reading the measurement started from: every condition holds and the set of Claude processes is the same. Returns the failures."""
    q = core.cfg_of(cfg)["quiet"]
    cond = machine.read_conditions(probe or machine.Probe(), q, condition=str(q["condition"]), expect=expected_presence(cfg))
    failed = list(cond["failed"])
    if first.get("claude_pids") is not None and cond.get("claude_pids") is not None and list(cond["claude_pids"]) != list(first["claude_pids"]):
        failed.append("CLAUDE PROCESS SET CHANGED")
    return failed


def wait_status(readings: Sequence[Mapping[str, Any]]) -> str:
    """N2: the status of a session that never got (another) quiet reading. Only a session in which the conditions held and the LOAD ALONE stayed above L at every reading counts (PAUSED — QUIET CONDITION NOT MET).
    A reading that failed on silence (a tool call of any Claude session, a changed Claude process set) makes it PAUSED — NOT SILENT; one that failed on any other machine condition (or an unreadable load) makes it
    PAUSED — MACHINE CONDITION. Neither counts towards NOT MEASURED."""
    seen = {f for r in readings for f in r.get("failed", [])}
    if any(f in machine.SILENCE_FAILURES for f in seen):
        return PAUSED_NOT_SILENT
    if any(f not in LOAD_FAILURES for f in seen):
        return PAUSED_CONDITION
    return PAUSED_QUIET


def discard_status(failed: Sequence[str]) -> str:
    """The status of a discarded measurement: NOT SILENT when the lead's silence failed, else MEASUREMENT DISCARDED. Neither counts towards the six sessions of NOT MEASURED (ruling F7)."""
    return PAUSED_NOT_SILENT if any(f in machine.SILENCE_FAILURES for f in failed) else PAUSED_DISCARDED


class ChildWatch:
    """N3: the in-measurement watch as a CHILD process (``watch_child.py``), started before the measurement and read after it, so that its CPU is not in the timing process's ``process_time`` (MC-T). A descendant of the
    stage: part of its own process family for the study-process check (F1). Fails closed: a child that does not start, or leaves no summary, is a failure."""

    def __init__(self, path: Path, first: Mapping[str, Any], *, cfg_path: Path | None = None, interval: float = 10.0, startup_timeout: float = 120.0, stop_timeout: float = 60.0) -> None:
        self.path, self.first, self.cfg_path, self.interval = path, dict(first), cfg_path, float(interval)
        self.startup_timeout, self.stop_timeout = float(startup_timeout), float(stop_timeout)
        self.proc: subprocess.Popen[bytes] | None = None
        self.pid: int | None = None

    def start(self) -> "ChildWatch":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        args = self.path.with_suffix(".args.json")
        args.write_text(json.dumps(core.jsonable({"first": {"claude_pids": self.first.get("claude_pids")}, "cfg_path": str(self.cfg_path) if self.cfg_path else None, "interval": self.interval, "out": str(self.path), "parent_pid": os.getpid()})), encoding="utf-8")
        err = self.path.with_suffix(".err").open("ab")
        self.proc = subprocess.Popen([sys.executable, "-m", "studies.p10is1.watch_child", "--args", str(args)], stdout=subprocess.DEVNULL, stderr=err)  # noqa: S603
        self.pid = self.proc.pid
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline and self.proc.poll() is None and not (self.path.is_file() and self.path.read_text(encoding="utf-8").strip()):
            time.sleep(0.05)  # the first tick is on disk: the watch is running before the measurement starts (bounded)
        return self

    def stop(self) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        summary: dict[str, Any] | None = None
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
            try:
                self.proc.wait(timeout=self.stop_timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=30)
        rows = [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()] if self.path.is_file() else []
        for r in rows:
            if r.get("summary"):
                summary = r
            elif r.get("failed"):
                failures.append({"t": r.get("t"), "failed": list(r["failed"])})
        if summary is None or not any("tick" in r for r in rows):
            failures.append({"t": None, "failed": ["WATCH CHILD DID NOT RUN"]})
        return {"failures": failures, "ticks": (summary or {}).get("ticks", 0), "child_cpu_seconds": (summary or {}).get("cpu_seconds"), "record": str(self.path)}


class CapReached(RuntimeError):
    """The stage's own cap on charged measuring seconds was reached inside a measurement (the attempt is discarded and the stage is PAUSED — STAGE CAP)."""


def safe_top() -> list[dict[str, Any]]:
    try:
        return machine.real_top()
    except Exception:  # noqa: BLE001 - recorded, never a condition
        return []


def timing_spreads(result: Mapping[str, Any], cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A3.4: per item s = (max - min) / median of the three CPU values per update, in floating point from the recorded values (the median of three is the middle one). Valid only if s <= ``timing_spread_max`` at every item."""
    bound = float(core.cfg_of(cfg)["quiet"]["timing_spread_max"])
    spreads: dict[str, float] = {}
    ratios: dict[str, list[float]] = {}
    for item, d in result["detail"].items():
        runs = [float(x) for x in d["runs"]]
        med = sorted(runs)[len(runs) // 2]
        spreads[item] = (max(runs) - min(runs)) / med if med > 0 and math.isfinite(med) else float("inf")
        walls = [float(x) for x in d.get("wall_runs", [])]
        ratios[item] = [c / w if w > 0 else float("nan") for c, w in zip(runs, walls, strict=False)]
    failing = [k for k, s in spreads.items() if not s <= bound]  # a NaN fails
    return {"ok": not failing, "bound": bound, "spreads": spreads, "max_spread": max(spreads.values()) if spreads else None, "failing_items": failing, "cpu_to_wall_per_repeat": ratios}


# --- attempts and the explicit decision ----------------------------------------------------------------------------------------------------------------
def attempts_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "attempts"


def record_attempt(run_dir: Path, stage: str, session: Mapping[str, Any], *, status: str, extra: Mapping[str, Any] | None = None) -> Path:
    """One session's record (``attempts/NN.json``): QUIET RUN, ``PAUSED — QUIET CONDITION NOT MET``, ``PAUSED — TIMING SPREAD`` or ``PAUSED — STAGE CAP``, with every reading. Records are numbered in order; the first is 1."""
    d = attempts_dir(run_dir, stage)
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob("[0-9][0-9].json"))) + 1
    path = d / f"{n:02d}.json"
    core.write_record(path, {**core.envelope("quiet_attempt"), "stage": stage, "attempt": n, "status": status, "readings": list(session["readings"]), **(extra or {})})
    return path


def attempt_statuses(run_dir: Path, stage: str) -> dict[int, str]:
    d = attempts_dir(run_dir, stage)
    out: dict[int, str] = {}
    for p in sorted(d.glob("[0-9][0-9].json")) if d.is_dir() else []:
        rec = read_json(p)
        out[int(rec["attempt"])] = str(rec["status"])
    return out


def paused_attempts(run_dir: Path, stage: str) -> list[int]:
    """The sessions that ended PAUSED — QUIET CONDITION NOT MET: the only ones that count towards the six of NOT MEASURED. A TIMING SPREAD or STAGE CAP session never does."""
    return sorted(n for n, s in attempt_statuses(run_dir, stage).items() if s == PAUSED_QUIET)


def spread_sessions(run_dir: Path, stage: str) -> int:
    return sum(1 for s in attempt_statuses(run_dir, stage).values() if s == PAUSED_SPREAD)


def decision_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "decisions" / f"{stage}_not_measured.json"


def load_decision(run_dir: Path, stage: str, cfg: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """The explicit decision that records ``stage`` NOT MEASURED: a file (not written by any code of this study) that names the six PAUSED attempts, the decider and the table of section 10. Returns None if there is no
    file; raises ``StageRefused`` if the file exists but does not qualify (too few PAUSED attempts, attempts not named, a named session that is not a PAUSED — QUIET CONDITION NOT MET one, no decider, no table). Before
    the first attempt and five rescheduled attempts have all ended PAUSED the decision cannot be accepted at all."""
    path = decision_path(run_dir, stage)
    if not path.is_file():
        return None
    need = int(core.cfg_of(cfg)["quiet"]["not_measured_after_paused_attempts"])
    rec = read_json(path)
    statuses = attempt_statuses(run_dir, stage)
    paused = paused_attempts(run_dir, stage)
    named = sorted(int(x) for x in rec.get("paused_attempts", []))
    problems = []
    if rec.get("decision") != NOT_MEASURED or rec.get("stage") != stage:
        problems.append("the decision does not say NOT MEASURED for this stage")
    if len(paused) < need:
        problems.append(f"only {len(paused)} attempts ended PAUSED; {need} (the first and five rescheduled) are required")
    not_quiet = [n for n in named if statuses.get(n) != PAUSED_QUIET]
    if not_quiet:
        problems.append(f"the decision names session(s) {not_quiet} that did not end {PAUSED_QUIET} (a TIMING SPREAD or STAGE CAP session never supports NOT MEASURED)")
    if named != paused[:need] or len(named) != need:
        problems.append(f"the decision must name the {need} PAUSED attempts {paused[:need]}, it names {named}")
    if not rec.get("decided_by"):
        problems.append("the decision names no decider")
    if "unreachable" not in str(rec.get("table_of_section_10", "")).lower():
        problems.append("the decision does not carry the table of section 10 (the labels that become unreachable)")
    if problems:
        raise core.StageRefused("refused: " + "; ".join(problems))
    return dict(rec)


def stage_state(run_dir: Path, stage: str, result_file: str) -> str:
    """COMPLETE (the stage's measured record exists), NOT MEASURED (a qualifying decision exists) or PAUSED. The code never writes NOT MEASURED."""
    if (run_dir / stage / result_file).is_file():
        return "COMPLETE"
    if load_decision(run_dir, stage) is not None:
        return NOT_MEASURED
    return "PAUSED"


def require_timing_settled(run_dir: Path) -> str:
    """Training does not start while the timing stage is PAUSED: it needs the measured timing record or the decision of section 16."""
    state = stage_state(run_dir, "timing", "timing.json")
    if state == "PAUSED":
        raise core.StageRefused("refused: the isolated timing stage is PAUSED (no measured record, no decision): training does not start")
    return state


def throughput_label(run_dir: Path) -> str:
    """The report prints THROUGHPUT PENDING while the stage is PAUSED; analysis and report do not wait."""
    state = stage_state(run_dir, "throughput", "throughput.json")
    return {"COMPLETE": "MEASURED", "NOT MEASURED": "THROUGHPUT NOT MEASURED", "PAUSED": "THROUGHPUT PENDING"}[state]


def run_alone_stage(
    run_dir: Path,
    stage: str,
    measure: Callable[..., Mapping[str, Any]],
    *,
    reading: Callable[[], dict[str, Any]],
    end: Callable[[Sequence[int]], dict[str, Any]],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    cfg: Mapping[str, Any] | None = None,
    validate: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None,
    cap_seconds: float | None = None,
    account: dict[str, Any] | None = None,
    guarded: bool = False,
    top_fn: Callable[[], list[dict[str, Any]]] | None = None,
    trace_factory: Callable[[], LoadTrace] | None = None,
    watch: Callable[[Mapping[str, Any]], list[str]] | None = None,
    child_watch: Callable[[Mapping[str, Any], Path], Any] | None = None,
) -> dict[str, Any]:
    """One session of a stage that runs alone (addendum A3.2 to A3.5 and the rulings F1-F7). WAIT for a quiet reading (a bounded wait window of its own; every poll appended to ``polls.jsonl``; the waiting is recorded
    in ``account['wait_seconds']`` and NOT charged), MEASURE (``account['measure_seconds']``, from the quiet reading to the end check including its 120-s delay: the charged seconds, against ``cap_seconds`` of the stage's own
    cap), END-CHECK. ``watch`` reads the conditions at every 10-s tick of the measurement (F6). A measurement whose end check or in-measurement watch fails is DISCARDED (F7): the session is not ended and nothing counts
    towards NOT MEASURED; it WAITS AGAIN inside the SAME bounded wait window (at most ``session_hours`` from its start, and at most that many polls) and measures again; a window that runs out after a discard ends the session
    PAUSED — NOT SILENT (the lead's silence failed) or PAUSED — MEASUREMENT DISCARDED. ``validate`` (the timing spread) judges a clean measurement: a failure discards it and the WHOLE list is measured once more after a
    new quiet reading with a wait window of its own; a second failure ends the session PAUSED — TIMING SPREAD. Only a session WITHOUT any quiet reading and without any discard or spread failure is PAUSED — QUIET
    CONDITION NOT MET, the only status that counts towards the six sessions. The measured record is written by the caller only on COMPLETE. The code never writes NOT MEASURED; three TIMING SPREAD sessions refuse."""
    q = core.cfg_of(cfg)["quiet"]
    acct = account if account is not None else {}
    acct.setdefault("measure_seconds", 0.0)
    acct.setdefault("wait_seconds", 0.0)
    need = int(q["timing_spread_sessions_to_human_lead"])
    if spread_sessions(run_dir, stage) >= need:
        raise core.StageRefused(f"refused: {need} sessions of the {stage} stage ended {PAUSED_SPREAD}: the matter returns to the human lead (ADR-0024 addendum A3.4); no outcome follows automatically")
    polls = polls_path(run_dir, stage)
    top = top_fn or safe_top
    poll, window_s = float(q["poll_seconds"]), float(q["session_hours"]) * 3600.0
    readings: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    discards: list[dict[str, Any]] = []
    spread_failed = False
    clean_runs = 0
    window_start, tries, max_tries, wait_no = clock(), 0, int(window_s // poll) + 2, 1

    def left() -> float | None:
        return None if cap_seconds is None else cap_seconds - acct["measure_seconds"]

    def end_status() -> str:
        if spread_failed:
            return PAUSED_SPREAD
        if discards:
            return str(discards[-1]["status"])
        return wait_status(readings)

    def paused(status: str, extra: Mapping[str, Any]) -> dict[str, Any]:
        path = record_attempt(run_dir, stage, {"readings": readings}, status=status, extra={"timing_attempts": attempts, "discards": discards, "wait_seconds": acct["wait_seconds"], "measure_seconds": acct["measure_seconds"], **extra})
        return {"status": status, "attempt_record": str(path), "paused_attempts": paused_attempts(run_dir, stage), "timing_attempts": attempts, "discards": discards, "wait_seconds": acct["wait_seconds"], "measure_seconds": acct["measure_seconds"], **extra}

    while True:
        room = left()
        if room is not None and room <= 0:
            return paused(PAUSED_CAP, {"reason": f"the stage's own cap on charged measuring seconds ({cap_seconds:.0f} s) is spent"})
        remaining = window_s - (clock() - window_start)
        tries += 1
        if remaining < 0 or tries > max_tries:
            return paused(end_status(), {})
        w0 = clock()
        sess = quiet_session(reading=reading, sleep=sleep, clock=clock, cfg=cfg, log_path=polls, wait=f"{stage} wait {wait_no}", limit_seconds=remaining)
        acct["wait_seconds"] += clock() - w0
        readings += sess["readings"]
        if not sess["quiet"]:
            return paused(end_status(), {})
        first = sess["readings"][-1]
        started = [int(p.split(":", 1)[0]) for p in first.get("other_study_processes", [])]
        top_start = top()
        check = (lambda first=first: watch(first)) if watch is not None else None
        trace = trace_factory() if trace_factory else LoadTrace(float(q["baseline_interval_seconds"]), check_fn=check)
        if trace_factory is not None and check is not None:
            trace.check_fn = check
        cw = child_watch(first, run_dir / stage / "watch" / f"watch-{clean_runs + len(discards) + 1:02d}.jsonl").start() if child_watch is not None else None  # N3: BEFORE the measurement, in its own process
        m0 = clock()

        def guard(m0: float = m0) -> None:
            if cap_seconds is not None and acct["measure_seconds"] + (clock() - m0) > cap_seconds:
                raise CapReached(f"the stage's own cap on charged measuring seconds ({cap_seconds:.0f} s) was reached inside a measurement")

        trace.start()
        capped: str | None = None
        result: dict[str, Any] = {}
        fin: dict[str, Any] = {}
        try:
            result = dict(measure(guard) if guarded else measure())
            fin = dict(end(started))
        except CapReached as exc:
            capped = str(exc)
        finally:
            load_trace = trace.stop()
            acct["measure_seconds"] += clock() - m0
            watch_res = cw.stop() if cw is not None else None  # read AFTER the measurement; its CPU was never in the timing process
        if capped is not None:
            return paused(PAUSED_CAP, {"reason": capped})
        top_end = top()
        failed = list(fin.get("failed", [])) if not fin.get("ok", False) else []
        if not fin.get("ok", False) and not failed:
            failed = ["END CHECK FAILED"]
        for f in [*trace.failures, *((watch_res or {}).get("failures") or [])]:  # F6: a condition that failed at any tick of the measurement
            failed += [x for x in f["failed"] if x not in failed]
        end_pids, first_pids = (fin.get("conditions") or {}).get("claude_pids"), first.get("claude_pids")
        if end_pids is not None and first_pids is not None and list(end_pids) != list(first_pids) and "CLAUDE PROCESS SET CHANGED" not in failed:
            failed.append("CLAUDE PROCESS SET CHANGED")  # F1: the set of Claude processes is the same from the quiet reading to the end check
        extra: dict[str, Any] = {"end_check": fin, "top_processes": {"start": top_start, "end": top_end}, "load_trace": load_trace, "watch_failures": trace.failures, "watch_child": watch_res, "attempt_in_session": clean_runs + len(discards) + 1}
        if failed:
            st = discard_status(failed)
            discards.append({"status": st, "failed": failed, "end_check": fin, "watch_failures": trace.failures, "measure_seconds": clock() - m0, "result": result, "top_processes": extra["top_processes"]})
            sleep(poll)  # let the disturbance pass, then wait again inside the same bounded window
            continue
        v = validate(result) if validate else None
        attempts.append({"attempt_in_session": clean_runs + 1, "valid": v is None or bool(v["ok"]), "validation": v, "result": result, "load_trace": load_trace, "top_processes": extra["top_processes"]})
        if v is not None and not v["ok"]:
            spread_failed = True
            print(json.dumps(core.jsonable({"timing_spread_failure": {"attempt_in_session": clean_runs + 1, "failing_items": v["failing_items"], "max_spread": v["max_spread"], "bound": v["bound"], "spreads": v["spreads"], "cpu_to_wall_per_repeat": v["cpu_to_wall_per_repeat"]}})), flush=True)
            if clean_runs == 0:
                clean_runs, window_start, tries, wait_no = 1, clock(), 0, 2  # the WHOLE list is timed once more, after a new quiet reading with a wait window of its own
                continue
            return paused(PAUSED_SPREAD, extra)
        path = record_attempt(run_dir, stage, {"readings": readings}, status="QUIET RUN", extra={**extra, "timing_attempts": attempts, "discards": discards, "retimed": clean_runs == 1, "wait_seconds": acct["wait_seconds"], "measure_seconds": acct["measure_seconds"]})
        return {"status": "COMPLETE", "result": result, "attempt_record": str(path), "end_check": fin, "validation": v, "retimed": clean_runs == 1, "discards": discards, "wait_seconds": acct["wait_seconds"], "measure_seconds": acct["measure_seconds"], "load_trace": load_trace, "top_processes": extra["top_processes"]}


def finite_seconds(values: Mapping[str, float]) -> bool:
    return all(math.isfinite(v) and v > 0 for v in values.values())
