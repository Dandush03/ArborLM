# ruff: noqa: E501
"""P10IS1 machine load rules (ADR-0024 sections 10, 16, 16.1): the machine-wide memory check, the quiet condition of the two stages that run ALONE (the isolated timing stage, the source of MC-T, and the read-path
throughput stage), the attempts and their records, and the explicit decision without which neither ends NOT MEASURED. Every wait has a deadline. Nothing here reads a registered seed.

* Memory check (ruling 26): available memory = (free + inactive + purgeable + speculative pages) x page size from ``vm_stat``, read at the start of each stage and before each worker is added; it must cover the stage's
  aggregate guard; retried every 10 minutes for at most 6 hours, then PAUSED — ENVIRONMENT.
* Quiet condition: one-minute load average <= 1.0, no process of another ArborLM study's stage (nor of this study's other stages) alive, mains power, not Low Power Mode, at the start; the process check is repeated at the
  end and none may have started during the run, else the figures are discarded and the run repeated. Retried every 10 minutes for up to 6 hours in a session (an attempt); a session without a quiet run is recorded
  PAUSED — QUIET CONDITION NOT MET and the stage is rescheduled. A timeout never ends a stage NOT MEASURED. NOT MEASURED is recorded only by an explicit decision file naming the six PAUSED attempts (the first and
  five rescheduled) and the table of section 10; the code offers no other path (``load_decision``), and training does not start while the timing stage is PAUSED (``require_timing_settled``).
"""

import math
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import core

PAUSED_QUIET = "PAUSED — QUIET CONDITION NOT MET"
PAUSED_ENVIRONMENT = "PAUSED — ENVIRONMENT"
NOT_MEASURED = "NOT MEASURED"
STAGES_ALONE = ("timing", "throughput")
STUDY_STAGE_RE = re.compile(r"(?<![\w.])studies\.(?:p9[\w]*|p10[\w]+)(?:\.stages|\.[a-z_]+)?(?![\w])")


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


# --- the quiet condition -------------------------------------------------------------------------------------------------------------------------------
def ps_commands() -> list[tuple[int, str]]:
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=True, timeout=30).stdout  # noqa: S607
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            rows.append((int(parts[0]), parts[1]))
    return rows


def own_pids() -> set[int]:
    """This process and its ancestors (the ``uv run`` wrapper that started it names the same stage)."""
    pids = {os.getpid()}
    try:
        import psutil

        pids |= {p.pid for p in psutil.Process().parents()}
    except Exception:  # noqa: BLE001
        pids.add(os.getppid())
    return pids


def other_study_processes(commands: Sequence[tuple[int, str]] | None = None, own: set[int] | None = None) -> list[str]:
    """Processes of any ArborLM study's stage (``python -m studies.p9...`` / ``studies.p10...``, this study's other stages included) other than this one."""
    rows = commands if commands is not None else ps_commands()
    me = own if own is not None else own_pids()
    return [f"{pid}: {cmd[:160]}" for pid, cmd in rows if pid not in me and STUDY_STAGE_RE.search(cmd) and "pytest" not in cmd]


def power_state() -> dict[str, Any]:
    """Mains power and Low Power Mode from ``pmset`` (macOS)."""
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, check=False, timeout=30).stdout  # noqa: S607
    full = subprocess.run(["pmset", "-g"], capture_output=True, text=True, check=False, timeout=30).stdout  # noqa: S607
    low = re.search(r"lowpowermode\s+(\d)", full)
    return {"mains": "AC Power" in batt, "low_power_mode": bool(low and low.group(1) == "1"), "raw": batt.splitlines()[:2]}


def quiet_reading(*, load_fn: Callable[[], float] = lambda: os.getloadavg()[0], commands_fn: Callable[[], list[tuple[int, str]]] = ps_commands, power_fn: Callable[[], dict[str, Any]] = power_state, own: set[int] | None = None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One reading of the start conditions: one-minute load average at most 1.0, no other study's stage alive, mains power, not Low Power Mode."""
    limit = float(core.cfg_of(cfg)["quiet"]["load_average_max"])
    load = float(load_fn())
    procs = other_study_processes(commands_fn(), own)
    power = power_fn()
    return {"load_average": load, "load_ok": load <= limit, "other_study_processes": procs, "processes_ok": not procs, "power": power, "power_ok": bool(power.get("mains")) and not power.get("low_power_mode"), "quiet": load <= limit and not procs and bool(power.get("mains")) and not power.get("low_power_mode")}


def quiet_session(*, reading: Callable[[], dict[str, Any]], sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One attempt: the start conditions are checked and, if they are not met, every ``poll_seconds`` for at most ``session_hours``. The wait is bounded. Returns the readings and whether a quiet reading was found."""
    q = core.cfg_of(cfg)["quiet"]
    poll, limit = float(q["poll_seconds"]), float(q["session_hours"]) * 3600.0
    began = clock()
    readings: list[dict[str, Any]] = []
    while True:
        r = reading()
        readings.append(r)
        if r["quiet"]:
            return {"quiet": True, "readings": readings}
        if clock() - began + poll > limit:
            return {"quiet": False, "readings": readings}
        sleep(poll)


def end_check(started_pids: Sequence[int], *, commands_fn: Callable[[], list[tuple[int, str]]] = ps_commands, own: set[int] | None = None) -> dict[str, Any]:
    """At the end of the run no other study's stage may be alive and none may have started during it (a process absent at the start and present now); otherwise the figures are discarded and the run repeated."""
    alive = other_study_processes(commands_fn(), own)
    return {"ok": not alive, "other_study_processes": alive, "started_during": [a for a in alive if int(a.split(":", 1)[0]) not in set(started_pids)]}


# --- attempts and the explicit decision ----------------------------------------------------------------------------------------------------------------
def attempts_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "attempts"


def record_attempt(run_dir: Path, stage: str, session: Mapping[str, Any], *, status: str, extra: Mapping[str, Any] | None = None) -> Path:
    """One attempt's record (``attempts/NN.json``): QUIET RUN or ``PAUSED — QUIET CONDITION NOT MET`` with every reading. Attempts are numbered in order; the first is attempt 1."""
    d = attempts_dir(run_dir, stage)
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob("[0-9][0-9].json"))) + 1
    path = d / f"{n:02d}.json"
    core.write_record(path, {**core.envelope("quiet_attempt"), "stage": stage, "attempt": n, "status": status, "readings": list(session["readings"]), **(extra or {})})
    return path


def paused_attempts(run_dir: Path, stage: str) -> list[int]:
    d = attempts_dir(run_dir, stage)
    return sorted(int(read_json(p)["attempt"]) for p in d.glob("[0-9][0-9].json") if read_json(p)["status"] == PAUSED_QUIET) if d.is_dir() else []


def decision_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "decisions" / f"{stage}_not_measured.json"


def load_decision(run_dir: Path, stage: str, cfg: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """The explicit decision that records ``stage`` NOT MEASURED: a file (not written by any code of this study) that names the six PAUSED attempts, the decider and the table of section 10. Returns None if there is no
    file; raises ``StageRefused`` if the file exists but does not qualify (too few PAUSED attempts, attempts not named, no decider, no table). Before the first attempt and five rescheduled attempts have all ended PAUSED the
    decision cannot be accepted at all."""
    path = decision_path(run_dir, stage)
    if not path.is_file():
        return None
    need = int(core.cfg_of(cfg)["quiet"]["not_measured_after_paused_attempts"])
    rec = read_json(path)
    paused = paused_attempts(run_dir, stage)
    named = sorted(int(x) for x in rec.get("paused_attempts", []))
    problems = []
    if rec.get("decision") != NOT_MEASURED or rec.get("stage") != stage:
        problems.append("the decision does not say NOT MEASURED for this stage")
    if len(paused) < need:
        problems.append(f"only {len(paused)} attempts ended PAUSED; {need} (the first and five rescheduled) are required")
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


def run_alone_stage(run_dir: Path, stage: str, measure: Callable[[], Mapping[str, Any]], *, reading: Callable[[], dict[str, Any]], end: Callable[[Sequence[int]], dict[str, Any]], sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One attempt of a stage that runs alone. A session without a quiet start is recorded PAUSED — QUIET CONDITION NOT MET (the stage is rescheduled, never ended). A quiet start runs ``measure``; if the end check
    finds another study's stage alive, or one started during the run, the figures are discarded, the attempt is recorded as discarded, and the stage stays PAUSED. The measured record is written by ``measure``'s caller only on a
    clean run."""
    session = quiet_session(reading=reading, sleep=sleep, clock=clock, cfg=cfg)
    if not session["quiet"]:
        path = record_attempt(run_dir, stage, session, status=PAUSED_QUIET)
        return {"status": PAUSED_QUIET, "attempt_record": str(path), "paused_attempts": paused_attempts(run_dir, stage)}
    started = [int(p.split(":", 1)[0]) for p in session["readings"][-1]["other_study_processes"]]
    result = dict(measure())
    fin = end(started)
    if not fin["ok"]:
        path = record_attempt(run_dir, stage, session, status=PAUSED_QUIET, extra={"discarded": True, "end_check": fin})
        return {"status": PAUSED_QUIET, "discarded": True, "attempt_record": str(path), "end_check": fin, "paused_attempts": paused_attempts(run_dir, stage)}
    path = record_attempt(run_dir, stage, session, status="QUIET RUN", extra={"end_check": fin})
    return {"status": "COMPLETE", "result": result, "attempt_record": str(path), "end_check": fin}


def finite_seconds(values: Mapping[str, float]) -> bool:
    return all(math.isfinite(v) and v > 0 for v in values.values())
