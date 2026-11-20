# ruff: noqa: E501
"""P10IS1 condition of the machine (ADR-0024 addendum A3.3): the SAME reading at every baseline sample and at every quiet-stage reading. Nothing here reads a seed or data.

Conditions (each reading anew): no process of any ArborLM study's stage other than the caller's own process FAMILY (its ancestors AND its descendants, so a keep-awake watcher started by the stage is never "another
study's process": P10-I-S5's defect); mains power; not Low Power Mode; no thermal warning (any line of ``pmset -g therm`` other than the three "No ... has been recorded" lines); ``HIDIdleTime`` (nanoseconds, from
``ioreg -c IOHIDSystem``) at least 600 s; no virtual machine by the ``vm_markers`` list; the application and Claude Code presences RECORDED (and, in the closed condition, absent; at a stage, equal to the baseline's).
A condition that cannot be read FAILS (fail closed).
"""

import contextlib
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

STUDY_STAGE_RE = re.compile(r"(?<![\w.])studies\.(?:p9[\w]*|p10[\w]+)(?:\.stages|\.[a-z_]+)?(?![\w])")
THERM_OK_RE = re.compile(r"^\s*(?:Note:\s*)?No .+ has been recorded\s*$")
HID_RE = re.compile(r'"HIDIdleTime"\s*=\s*(\d+)')
TOOL_SHELL_MARK = "shell-snapshots/snapshot-"  # a tool call of ANY Claude session runs as `/bin/zsh -c source ~/.claude/shell-snapshots/snapshot-zsh-... && eval ...` (seen on the live process table, 2026-11-20)
SILENCE_FAILURES = ("CLAUDE TOOL-CALL SHELL ACTIVE", "CLAUDE PROCESS SET CHANGED")  # the failures that mean the lead was not silent (a stage discard with one of them is PAUSED — NOT SILENT)
POWER_RE = re.compile(r"^\s*(low)?powermode\s+(\d+)\s*$", re.MULTILINE)
CONDITIONS = ("open", "closed")

Row = tuple[int, int, str]  # (pid, ppid, full command line)


# --- readers of the real machine ---------------------------------------------------------------------------------------------------------------------
def ps_table() -> list[Row]:
    """A light listing (``ps -Ao pid=,ppid=,command=``) with the parent of each process; the sampler's own call adds a little load, which the stages do not have (its CPU seconds are recorded)."""
    out = subprocess.run(["ps", "-Ao", "pid=,ppid=,command="], capture_output=True, text=True, check=True, timeout=30).stdout  # noqa: S607
    rows: list[Row] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def family(table: Sequence[Row], pid: int) -> set[int]:
    """``pid``, every ancestor of it and every descendant of it."""
    parent = {p: pp for p, pp, _ in table}
    kids: dict[int, list[int]] = {}
    for p, pp, _ in table:
        kids.setdefault(pp, []).append(p)
    own = {pid}
    cur, seen = pid, set()
    while cur in parent and parent[cur] not in seen and parent[cur] > 0:
        seen.add(parent[cur])
        own.add(parent[cur])
        cur = parent[cur]
    stack = [pid]
    while stack:
        for k in kids.get(stack.pop(), []):
            if k not in own:
                own.add(k)
                stack.append(k)
    return own


def parse_therm(text: str) -> list[str]:
    """The thermal warnings: every non-blank line of ``pmset -g therm`` other than a "No ... has been recorded" line."""
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not THERM_OK_RE.match(ln)]


def parse_hid_idle_ns(text: str) -> int:
    """``HIDIdleTime`` in nanoseconds (the smallest of several if the listing has more than one: the most recent input)."""
    vals = [int(m) for m in HID_RE.findall(text)]
    if not vals:
        raise ValueError("ioreg output without HIDIdleTime")
    return min(vals)


def _run(args: Sequence[str]) -> str:
    return subprocess.run(list(args), capture_output=True, text=True, check=False, timeout=30).stdout


def parse_power(batt: str, full: str) -> dict[str, Any]:
    """Mains power and Low Power Mode from the text of ``pmset -g batt`` and ``pmset -g``. This Mac prints ``powermode 0`` (1 is Low Power Mode), older ones ``lowpowermode 0``: BOTH spellings are read, and if neither
    is present, or the power source line is missing, the setting is unreadable and ``ValueError`` is raised (a refusal, never a pass)."""
    if "Now drawing from" not in batt:
        raise ValueError("pmset -g batt without a power source line")
    flags = [(m.group(1) or "", int(m.group(2))) for m in POWER_RE.finditer(full)]
    if not flags:
        raise ValueError("pmset -g prints neither 'powermode' nor 'lowpowermode': Low Power Mode is unreadable")
    return {"mains": "AC Power" in batt, "low_power_mode": any(v == 1 for _, v in flags), "power_settings": {(k or "") + "powermode": v for k, v in flags}, "raw": batt.splitlines()[:2]}


def real_power() -> dict[str, Any]:
    return parse_power(_run(["pmset", "-g", "batt"]), _run(["pmset", "-g"]))


def real_top() -> list[dict[str, Any]]:
    """The ten processes with the highest CPU share (``ps -Aro pid,pcpu,comm``): recorded, never a condition."""
    lines = _run(["ps", "-Aro", "pid,pcpu,comm"]).splitlines()[1:11]
    out = []
    for ln in lines:
        parts = ln.strip().split(None, 2)
        if len(parts) == 3:
            out.append({"pid": int(parts[0]), "pcpu": float(parts[1]), "comm": parts[2]})
    return out


def real_boot() -> int:
    m = re.search(r"sec\s*=\s*(\d+)", _run(["sysctl", "-n", "kern.boottime"]))
    if not m:
        raise ValueError("kern.boottime unreadable")
    return int(m.group(1))


def own_cpu_seconds() -> float:
    t = os.times()
    return float(t.user + t.system + t.children_user + t.children_system)


@dataclass
class Probe:
    """Every reader of the machine, replaceable by a test (synthetic process tables, loads, clocks)."""

    load: Callable[[], tuple[float, float]] = lambda: (os.getloadavg()[0], os.getloadavg()[1])
    table: Callable[[], list[Row]] = ps_table
    power: Callable[[], dict[str, Any]] = real_power
    therm: Callable[[], list[str]] = lambda: parse_therm(_run(["pmset", "-g", "therm"]))
    hid_ns: Callable[[], int] = lambda: parse_hid_idle_ns(_run(["ioreg", "-c", "IOHIDSystem"]))
    boot: Callable[[], int] = real_boot
    cpu: Callable[[], float] = own_cpu_seconds
    top: Callable[[], list[dict[str, Any]]] = real_top
    pid: int = field(default_factory=os.getpid)
    own: set[int] | None = None  # a fixed own set (a test); None: the process family of ``pid`` from the table
    allow: re.Pattern[str] | None = None  # TEST-ONLY allowance: a study command line matching it is not counted (the real path has none: a ``pytest`` of another study must be seen)


def compiled(cfg_quiet: Mapping[str, Any]) -> dict[str, list[re.Pattern[str]]]:
    return {
        "vm": [re.compile(p) for p in cfg_quiet["vm_markers"]],  # case-sensitive: every marker is anchored to a path component, a bundle or a bundle id (N1)
        "app": [re.compile(p) for p in cfg_quiet["app_markers"]],
        "cli": [re.compile(p) for p in cfg_quiet["cli_markers"]],
    }


def read_conditions(probe: Probe, q: Mapping[str, Any], *, condition: str, expect: tuple[bool, bool] | None = None) -> dict[str, Any]:
    """One reading of the condition of the machine (A3.3). ``condition`` is "open" or "closed" (the baseline's); ``expect`` = (application present, Claude Code present) of the baseline: a stage requires both to
    be equal to it (a baseline sample passes None and records them). ``failed`` names every condition that did not hold; an unreadable one fails."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition is 'open' or 'closed', not {condition!r}")
    failed: list[str] = []
    r: dict[str, Any] = {}
    pats = compiled(q)
    try:
        table = probe.table()
        own = probe.own if probe.own is not None else family(table, probe.pid)
        r["other_study_processes"] = [f"{p}: {c[:160]}" for p, _, c in table if p not in own and STUDY_STAGE_RE.search(c) and not (probe.allow and probe.allow.search(c))]
        r["tool_shells"] = [f"{p}: {c[:120]}" for p, _, c in table if p not in own and TOOL_SHELL_MARK in c]
        r["vm_processes"] = [f"{p}: {c[:160]}" for p, _, c in table if p not in own and any(x.search(c) for x in pats["vm"])]
        r["app_present"] = any(x.search(c) for _, _, c in table for x in pats["app"])
        r["cli_present"] = any(x.search(c) for _, _, c in table for x in pats["cli"])
        r["claude_pids"] = sorted(p for p, _, c in table if any(x.search(c) for x in pats["app"] + pats["cli"]))
        r["own_family"] = sorted(own)
    except Exception as exc:  # noqa: BLE001 - fail closed
        failed.append("PROCESS TABLE UNREADABLE")
        r.update(other_study_processes=[], vm_processes=[], tool_shells=[], claude_pids=[], app_present=None, cli_present=None, error_table=str(exc)[:200])
    if r.get("other_study_processes"):
        failed.append("OTHER STUDY PROCESS ALIVE")
    if r.get("vm_processes"):
        failed.append("VIRTUAL MACHINE PRESENT")
    if r.get("tool_shells"):
        failed.append("CLAUDE TOOL-CALL SHELL ACTIVE")  # the lead is not silent: a tool call of any Claude session outside the caller's own process chain
    try:
        pw = probe.power()
        r["mains"], r["low_power_mode"] = bool(pw.get("mains")), bool(pw.get("low_power_mode"))
        if not r["mains"]:
            failed.append("NOT ON MAINS POWER")
        if r["low_power_mode"]:
            failed.append("LOW POWER MODE")
    except Exception:  # noqa: BLE001
        failed.append("POWER UNREADABLE")
    try:
        r["thermal_lines"] = list(probe.therm())
        if r["thermal_lines"]:
            failed.append("THERMAL WARNING")
    except Exception:  # noqa: BLE001
        failed.append("THERMAL UNREADABLE")
    try:
        ns = int(probe.hid_ns())
        r["hid_idle_seconds"] = ns / 1e9
        if ns < int(q["hid_idle_min_seconds"]) * 10**9:  # exact, in nanoseconds
            failed.append("IDLE TIME UNDER THE MINIMUM")
    except Exception:  # noqa: BLE001
        failed.append("IDLE TIME UNREADABLE")
    try:
        r["boot"] = int(probe.boot())
    except Exception:  # noqa: BLE001
        r["boot"] = None
        failed.append("BOOT TIME UNREADABLE")
    if r.get("app_present") is not None:
        if condition == "closed":
            if r["app_present"]:
                failed.append("APPLICATION PRESENT (CLOSED CONDITION)")
            if r["cli_present"]:
                failed.append("CLAUDE CODE PRESENT (CLOSED CONDITION)")
        if expect is not None and (bool(r["app_present"]), bool(r["cli_present"])) != (bool(expect[0]), bool(expect[1])):
            failed.append("APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S")
    r["failed"] = failed
    return r


@contextlib.contextmanager
def keep_awake(*, pid: int | None = None) -> Iterator[int | None]:
    """A power assertion against idle sleep, ``caffeinate -i -w <pid>``, started as a CHILD of the calling process: it lies inside the stage's own process family (its descendants are counted as the stage's own), and
    its command line names no study. It ends with the caller or here. Off macOS (no ``caffeinate``): nothing."""
    exe = shutil.which("caffeinate")
    proc = subprocess.Popen([exe, "-i", "-w", str(pid or os.getpid())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if exe else None  # noqa: S603
    try:
        yield proc.pid if proc else None
    finally:
        if proc is not None:
            proc.terminate()
            with contextlib.suppress(Exception):
                proc.wait(timeout=10)
