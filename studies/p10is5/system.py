# ruff: noqa: E501
"""P10IS5 machine records (ADR-0028 sections 3.1 EC3, 6 hygiene, 8 quiet rule): everything is read through system tools that need no administrator access, through ONE injectable ``Run`` function so that
the parsers and the rules are tested on canned output. A command that cannot be read is printed NOT READABLE (EC3 wear counters) or NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS (hygiene), and the study continues on the
counter rule. Parsers are pure functions of text. No command here writes anything, except ``add_exclusion`` (``tmutil addexclusion <dir>`` without ``-p``, which R0 runs on the study's own ``.noindex`` directory).
"""

import math
import os
import plistlib
import re
import subprocess
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import core

Run = Callable[[Sequence[str]], tuple[int, str, str]]
Clock = Callable[[], float]
Sleep = Callable[[float], None]


def run_command(argv: Sequence[str], timeout: float = 60.0) -> tuple[int, str, str]:
    """(returncode, stdout, stderr); an unusable command or a timeout is returncode 127 / 124, never an exception (the caller prints NOT READABLE)."""
    try:
        p = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    except FileNotFoundError:
        return 127, "", f"{argv[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{argv[0]}: timeout after {timeout} s"
    return p.returncode, p.stdout, p.stderr


def run_bytes(argv: Sequence[str], timeout: float = 60.0) -> tuple[int, bytes]:
    try:
        p = subprocess.run(list(argv), capture_output=True, timeout=timeout, check=False)  # noqa: S603
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, b""
    return p.returncode, p.stdout


# --- parsers (pure) ----------------------------------------------------------------------------------------------------------------------------
def parse_loadavg(text: str) -> tuple[float, float, float]:
    """``sysctl -n vm.loadavg``: ``{ 4.28 6.18 5.11 }``."""
    m = re.search(r"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", text)
    if not m:
        raise ValueError(f"not a load average: {text!r}")
    return float(m[1]), float(m[2]), float(m[3])


def parse_boottime(text: str) -> int:
    m = re.search(r"sec\s*=\s*(\d+)", text)
    if not m:
        raise ValueError(f"not a boot time: {text!r}")
    return int(m[1])


def parse_hid_idle_seconds(text: str) -> float | None:
    """``ioreg -c IOHIDSystem``: ``"HIDIdleTime" = 13387188164083`` (nanoseconds)."""
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', text)
    return None if not m else int(m[1]) / 1e9


def parse_on_ac(text: str) -> bool | None:
    """``pmset -g batt``."""
    if "AC Power" in text:
        return True
    if "Battery Power" in text:
        return False
    return None


def parse_low_power(text: str) -> bool | None:
    """``pmset -g``: ``lowpowermode 1`` or ``powermode 1`` (a power mode that is not 0 is low or high; only low is a failure, ``lowpowermode 1``)."""
    m = re.search(r"^\s*lowpowermode\s+(\d)", text, flags=re.M)
    if m:
        return m[1] == "1"
    m = re.search(r"^\s*powermode\s+(\d)", text, flags=re.M)
    return None if not m else m[1] == "1"


def parse_thermal_warning(text: str) -> bool | None:
    """``pmset -g therm``: a warning is recorded when a level line does not say ``No thermal warning level`` or the CPU speed limit is below 100."""
    if not text.strip():
        return None
    limit = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", text)
    if limit and int(limit[1]) < 100:
        return True
    if re.search(r"Thermal warning level[^\n]*:\s*[1-9]", text, flags=re.I):
        return True
    return False


def parse_df_k(text: str) -> dict[str, Any]:
    """``df -k <path>``: device, total, used, available in KiB."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError(f"not df output: {text!r}")
    f = lines[-1].split()
    return {"device": f[0], "total_bytes": int(f[1]) * 1024, "used_bytes": int(f[2]) * 1024, "free_bytes": int(f[3]) * 1024}


def parse_smart_status(text: str) -> str | None:
    """``diskutil info disk0``: ``SMART Status: Verified``."""
    m = re.search(r"SMART Status:\s*(.+)", text)
    return None if not m else m[1].strip()


def _walk_bsd(node: Mapping[str, Any]) -> Iterable[str]:
    if node.get("BSD Name"):
        yield str(node["BSD Name"])
    for c in node.get("IORegistryEntryChildren", []) or []:
        yield from _walk_bsd(c)


def parse_driver_stats(plist: bytes, bsd_name: str = "disk0") -> dict[str, int] | None:
    """``ioreg -a -r -c IOBlockStorageDriver -l``: the Statistics of the driver whose subtree holds ``bsd_name`` (read and write bytes and operations since boot)."""
    if not plist:
        return None
    for node in plistlib.loads(plist):
        if bsd_name in set(_walk_bsd(node)):
            s = node.get("Statistics") or {}
            return {"read_bytes": int(s["Bytes (Read)"]), "write_bytes": int(s["Bytes (Write)"]), "read_ops": int(s["Operations (Read)"]), "write_ops": int(s["Operations (Write)"])}
    return None


def parse_volume_stats(plist: bytes, bsd_name: str) -> dict[str, int] | None:
    """``ioreg -a -r -c AppleAPFSVolume -l``: the APFS volume's ``Bytes read from block device`` (system-wide cross-check, printed only)."""
    if not plist:
        return None
    for v in plistlib.loads(plist):
        if v.get("BSD Name") == bsd_name:
            s = v.get("Statistics") or {}
            return {"read_blockdev": int(s.get("Bytes read from block device", -1)), "written_blockdev": int(s.get("Bytes written to block device", -1)), "read_by_user": int(s.get("Bytes read by user", -1))}
    return None


def parse_ps(text: str) -> list[tuple[int, str]]:
    """``ps -Ao pid,command``."""
    out = []
    for line in text.splitlines()[1:]:
        m = re.match(r"\s*(\d+)\s+(.*)$", line)
        if m:
            out.append((int(m[1]), m[2]))
    return out


PROCESS_RULE = (
    "a process is another study's when its command line contains studies/, studies., arborlm or pytest (case-insensitive) and it is not this stage's own process, one of its ancestors (the shell or launcher that started it; "
    "never pid 1) or one of its descendants; every other matching process, including any other shell or session with ArborLM in its command line, counts"
)


def other_study_processes(ps: Sequence[tuple[int, str]], own_pids: Iterable[int], markers: Sequence[str]) -> list[tuple[int, str]]:
    """Section 8: processes, other than the stage's own, whose command line contains a marker (``studies/``, ``arborlm`` or ``pytest``, case-insensitive: the conservative reading). ``own_pids`` is the stage's own
    process, its ancestors (the launcher) and its descendants."""
    own = set(own_pids)
    low = [m.lower() for m in markers]
    return [(pid, cmd) for pid, cmd in ps if pid not in own and any(m in cmd.lower() for m in low)]


def process_family(ps_with_ppid: Sequence[tuple[int, int]], pid: int) -> set[int]:
    """``pid``, its ancestors (the launcher; never pid 1 and below) and its descendants (never the descendants of an ancestor), from (pid, ppid) pairs."""
    parent = dict(ps_with_ppid)
    fam = {pid}
    cur = pid
    while cur in parent and parent[cur] > 1 and parent[cur] not in fam:
        cur = parent[cur]
        fam.add(cur)
    down = {pid}
    changed = True
    while changed:
        changed = False
        for p, pp in ps_with_ppid:
            if pp in down and p not in down:
                down.add(p)
                changed = True
    return fam | down


def parse_ppids(text: str) -> list[tuple[int, int]]:
    out = []
    for line in text.splitlines()[1:]:
        m = re.match(r"\s*(\d+)\s+(\d+)", line)
        if m:
            out.append((int(m[1]), int(m[2])))
    return out


# --- readers (they call ``run``) ----------------------------------------------------------------------------------------------------------------
def read_loadavg(run: Run) -> float:
    rc, out, err = run(["sysctl", "-n", "vm.loadavg"])
    if rc != 0:
        raise core.EngineeringStop("ENVIRONMENT", f"sysctl vm.loadavg: {err.strip()}")
    return parse_loadavg(out)[0]


def read_boottime(run: Run) -> int | None:
    rc, out, _ = run(["sysctl", "-n", "kern.boottime"])
    return parse_boottime(out) if rc == 0 else None


def read_driver(run_b: Callable[[Sequence[str]], tuple[int, bytes]], bsd: str = "disk0") -> dict[str, int] | None:
    rc, out = run_b(["ioreg", "-a", "-r", "-c", "IOBlockStorageDriver", "-l"])
    return parse_driver_stats(out, bsd) if rc == 0 else None


def own_family(run: Run) -> set[int]:
    rc, out, _ = run(["ps", "-Ao", "pid,ppid"])
    me = os.getpid()
    return process_family(parse_ppids(out), me) if rc == 0 else {me}


def read_other_processes(run: Run, markers: Sequence[str]) -> list[tuple[int, str]]:
    rc, out, err = run(["ps", "-Ao", "pid,command"])
    if rc != 0:
        raise core.EngineeringStop("ENVIRONMENT", f"ps: {err.strip()}")
    return other_study_processes(parse_ps(out), own_family(run), markers)


def read_power(run: Run) -> dict[str, Any]:
    rc1, batt, _ = run(["pmset", "-g", "batt"])
    rc2, allp, _ = run(["pmset", "-g"])
    rc3, therm, _ = run(["pmset", "-g", "therm"])
    return {"on_ac": parse_on_ac(batt) if rc1 == 0 else None, "low_power": parse_low_power(allp) if rc2 == 0 else None, "thermal_warning": parse_thermal_warning(therm) if rc3 == 0 else None}


def read_hid_idle(run: Run) -> float | None:
    rc, out, _ = run(["ioreg", "-c", "IOHIDSystem"])
    return parse_hid_idle_seconds(out) if rc == 0 else None


# --- sampling and the quiet rule ---------------------------------------------------------------------------------------------------------------
RATE_KEYS = ("read_bytes", "write_bytes", "read_ops", "write_ops")


def rates(a: Mapping[str, int], b: Mapping[str, int], seconds: float) -> dict[str, float]:
    if seconds <= 0:
        raise ValueError("a rate needs a positive interval")
    return {k: (b[k] - a[k]) / seconds for k in RATE_KEYS}


def sample_activity(run_b: Callable[[Sequence[str]], tuple[int, bytes]], seconds: float, sleep: Sleep, clock: Clock) -> dict[str, float] | None:
    """Mean disk0 driver rates (bytes and operations per second, read and write) over a window of ``seconds``."""
    a = read_driver(run_b)
    t0 = clock()
    sleep(seconds)
    b = read_driver(run_b)
    return None if a is None or b is None else rates(a, b, max(clock() - t0, 1e-9))


def quiet_thresholds(cfg: Mapping[str, Any]) -> dict[str, float]:
    """The ceilings of section 8 from the fixed figures: the load ceiling is R1's idle 95th percentile plus 0.5; the four rate ceilings are R1's 95th percentiles."""
    f, q = cfg["fixed_after_r1_and_m"], cfg["quiet"]
    return {
        "load_ceiling": float(f["load_p95"]) + float(q["load_margin"]), "read_bytes": float(f["read_bytes_per_s_p95"]), "write_bytes": float(f["write_bytes_per_s_p95"]),
        "read_ops": float(f["read_ops_per_s_p95"]), "write_ops": float(f["write_ops_per_s_p95"]),
    }  # fmt: skip


def evaluate_quiet(readings: Mapping[str, Any], thresholds: Mapping[str, float], hid_min: float, boot_time: int | None) -> dict[str, Any]:
    """The quiet rule as a pure function of the readings: every condition is listed with its reading; ``ok`` only if all hold. An unreadable condition fails the rule (the conservative reading)."""
    conds: dict[str, bool] = {}
    load = readings.get("load")
    conds["load"] = load is not None and load <= thresholds["load_ceiling"]
    conds["no_other_study_process"] = readings.get("other_processes") == []
    hid = readings.get("hid_idle_seconds")
    conds["hid_idle"] = hid is not None and hid >= hid_min
    p = readings.get("power") or {}
    conds["ac_power"] = p.get("on_ac") is True
    conds["power_mode_not_low"] = p.get("low_power") is False
    conds["no_thermal_warning"] = p.get("thermal_warning") is False
    act = readings.get("activity")
    conds["disk_activity"] = act is not None and all(act[k] <= thresholds[k] for k in RATE_KEYS)
    conds["boot_time_unchanged"] = boot_time is None or readings.get("boot_time") == boot_time
    return {"ok": all(conds.values()), "conditions": conds, "failed": [k for k, v in conds.items() if not v], "readings": dict(readings), "thresholds": dict(thresholds)}


def read_quiet(run: Run, run_b: Callable[[Sequence[str]], tuple[int, bytes]], cfg: Mapping[str, Any], sleep: Sleep, clock: Clock, boot_time: int | None) -> dict[str, Any]:
    """One reading of the quiet rule: the load average and the other-process list BEFORE the activity window (the window sleeps ``activity_window_seconds``), then idle time, power and boot time."""
    q = cfg["quiet"]
    others = read_other_processes(run, q["process_markers"])
    readings: dict[str, Any] = {"load": read_loadavg(run), "other_processes": [list(x) for x in others], "other_process_count": len(others), "rule": PROCESS_RULE}
    readings["activity"] = sample_activity(run_b, float(q["activity_window_seconds"]), sleep, clock)
    readings["hid_idle_seconds"] = read_hid_idle(run)
    readings["power"] = read_power(run)
    readings["boot_time"] = read_boottime(run)
    rec = evaluate_quiet(readings, quiet_thresholds(cfg), float(q["hid_idle_min_seconds"]), boot_time)
    rec["utc"] = core.utc_stamp()
    return rec


def wait_for_quiet(read: Callable[[], dict[str, Any]], *, retry_interval: float, deadline: float, sleep: Sleep, clock: Clock) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Retry ``read`` every ``retry_interval`` seconds for at most ``deadline`` seconds (a deadline on every wait). Returns (the quiet record or None, every reading made). None means PAUSED — MACHINE NOT QUIET."""
    t0 = clock()
    history: list[dict[str, Any]] = []
    while True:
        rec = read()
        history.append(rec)
        if rec["ok"]:
            return rec, history
        if clock() - t0 + retry_interval > deadline:
            return None, history
        sleep(retry_interval)


# --- R1's idle window --------------------------------------------------------------------------------------------------------------------------
def idle_conditions_hold(run: Run, markers: Sequence[str], hid_min: float) -> dict[str, Any]:
    """The conditions that must hold at every one of the sixty samples of the idle window: no other study's process, idle time at least 600 s, AC power, power mode not low, no thermal warning."""
    others = read_other_processes(run, markers)
    hid = read_hid_idle(run)
    p = read_power(run)
    ok = not others and hid is not None and hid >= hid_min and p["on_ac"] is True and p["low_power"] is False and p["thermal_warning"] is False
    return {"ok": ok, "other_processes": [list(x) for x in others], "hid_idle_seconds": hid, "power": p}


def take_idle_window(run: Run, run_b: Callable[[Sequence[str]], tuple[int, bytes]], cfg: Mapping[str, Any], sleep: Sleep, clock: Clock) -> dict[str, Any]:
    """One attempt at the idle window: sixty samples every ``idle_interval_seconds`` (the 1-minute load average, and the disk0 driver's rates over each interval). If any sample finds another study's process
    alive or a condition failing, the window is discarded (``discarded`` lists the failing sample); the caller retakes it from the start."""
    q = cfg["quiet"]
    n, step = int(q["idle_samples"]), float(q["idle_interval_seconds"])
    prev = read_driver(run_b)
    if prev is None:
        raise core.EngineeringStop("NO DRIVER COUNTER", "the disk0 driver's statistics cannot be read")
    loads: list[float] = []
    rate_rows: list[dict[str, float]] = []
    samples: list[dict[str, Any]] = []
    for i in range(n):
        t0 = clock()
        sleep(step)
        cur = read_driver(run_b)
        if cur is None:
            raise core.EngineeringStop("NO DRIVER COUNTER", "the disk0 driver's statistics cannot be read")
        cond = idle_conditions_hold(run, q["process_markers"], float(q["hid_idle_min_seconds"]))
        load = read_loadavg(run)
        samples.append({"i": i, "load": load, **cond})
        if not cond["ok"]:
            return {"discarded": True, "failed_sample": i, "samples": samples}
        loads.append(load)
        rate_rows.append(rates(prev, cur, max(clock() - t0, 1e-9)))
        prev = cur
    return {"discarded": False, "samples": samples, "loads": loads, "rate_rows": rate_rows}


def idle_figures(window: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The 95th percentiles (nearest rank) of the window's loads and four rates: what the lead writes into the config as ``[fixed_after_r1_and_m]``."""
    q = float(cfg["quiet"]["percentile"])
    rows = window["rate_rows"]
    return {
        "load_p95": core.nearest_rank(window["loads"], q), "read_bytes_per_s_p95": core.nearest_rank([r["read_bytes"] for r in rows], q), "write_bytes_per_s_p95": core.nearest_rank([r["write_bytes"] for r in rows], q),
        "read_ops_per_s_p95": core.nearest_rank([r["read_ops"] for r in rows], q), "write_ops_per_s_p95": core.nearest_rank([r["write_ops"] for r in rows], q),
        "load_ceiling": core.nearest_rank(window["loads"], q) + float(cfg["quiet"]["load_margin"]), "samples": len(window["loads"]),
    }  # fmt: skip


def idle_baseline(run: Run, run_b: Callable[[Sequence[str]], tuple[int, bytes]], cfg: Mapping[str, Any], sleep: Sleep, clock: Clock) -> dict[str, Any]:
    """Section 8: the idle window is taken first and only when the machine is idle; a discarded window is retaken from the start, retried every 10 minutes for at most 6 hours; then R1 is PAUSED (no idle baseline)
    with the readings recorded, and is rescheduled."""
    q = cfg["quiet"]
    t0 = clock()
    attempts: list[dict[str, Any]] = []
    while True:
        w = take_idle_window(run, run_b, cfg, sleep, clock)
        attempts.append({k: w[k] for k in ("discarded", "failed_sample") if k in w} | {"failing": w["samples"][-1] if w["discarded"] else None})
        if not w["discarded"]:
            fig = idle_figures(w, cfg)
            own = w["loads"][-1] <= fig["load_ceiling"]  # R1's own check uses the rule on its own idle window
            return {"status": "MEASURED", "figures": fig, "own_check_passed": own, "loads": w["loads"], "rate_rows": w["rate_rows"], "attempts": attempts}
        if clock() - t0 + float(q["retry_interval_seconds"]) > float(q["retry_deadline_seconds"]):
            return {"status": "PAUSED — NO IDLE BASELINE", "attempts": attempts}
        sleep(float(q["retry_interval_seconds"]))


# --- EC3 and hygiene -----------------------------------------------------------------------------------------------------------------------------
def ec3_record(run: Run, run_b: Callable[[Sequence[str]], tuple[int, bytes]], where: Path, label: str) -> dict[str, Any]:
    """Before and after every stage that writes: SMART status (must read ``Verified``), free space, the disk0 driver's bytes written since boot. Lifetime bytes written, percentage used and temperature cannot be read
    without administrator access or a tool install: they are printed NOT READABLE and that does not make the part NOT EVALUABLE. A status other than ``Verified`` is PAUSED (``health_ok`` False)."""
    rc, out, _ = run(["diskutil", "info", "disk0"])
    smart = parse_smart_status(out) if rc == 0 else None
    rc2, df, _ = run(["df", "-k", str(where)])
    try:
        free = parse_df_k(df) if rc2 == 0 else None
    except ValueError:
        free = None
    drv = read_driver(run_b)
    return {
        **core.envelope("ec3"), "label": label, "utc": core.utc_stamp(), "smart_status": smart or core.NOT_READABLE, "health_ok": smart == "Verified", "free": free or core.NOT_READABLE, "driver_since_boot": drv or core.NOT_READABLE,
        "lifetime_bytes_written": core.NOT_READABLE, "percentage_used": core.NOT_READABLE, "temperature": core.NOT_READABLE,
    }  # fmt: skip


def hygiene_record(run: Run, directory: Path, *, file_exists: bool, add_exclusion: bool = False) -> dict[str, Any]:
    """The hygiene checks of section 6, each printed; a command that needs administrator access is NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS. Spotlight indexing of the directory, or a snapshot while a file exists,
    are recorded with their consequence (``blocks_e1``: Spotlight indexes the directory -> PAUSED before E1; ``store_retained_by_snapshot``: recorded, not a stop for reads)."""
    out: dict[str, Any] = {**core.envelope("hygiene"), "directory": str(directory), "utc": core.utc_stamp()}

    def cmd(argv: Sequence[str]) -> dict[str, Any]:
        rc, so, se = run(argv)
        text = (so + se).strip()
        if rc != 0 and re.search(r"(?i)(privilege|permission|not permitted|requires? (admin|root|sudo)|must be root|operation not permitted)", text):
            return {"argv": list(argv), "status": core.NOT_CHECKABLE, "output": text[:500]}
        if rc != 0:
            return {"argv": list(argv), "status": core.NOT_READABLE, "returncode": rc, "output": text[:500]}
        # stdout only is the answer: ``mdfind`` always prints a locale line on stderr, which is recorded raw beside it and is never read as a listing
        return {"argv": list(argv), "status": "READ", "output": so.strip()[:2000], "stderr": se.strip()[:500]}

    snaps = [cmd(["tmutil", "listlocalsnapshots", "/"]), cmd(["tmutil", "listlocalsnapshots", "/System/Volumes/Data"])]
    out["local_snapshots"] = snaps
    present = any(s["status"] == "READ" and re.search(r"com\.apple\.TimeMachine\.\d", s["output"]) for s in snaps)
    out["snapshot_present"] = present
    out["store_retained_by_snapshot"] = bool(present and file_exists)
    out["apfs_snapshots"] = cmd(["diskutil", "apfs", "listSnapshots", "disk3s5"])
    out["time_machine_destinations"] = cmd(["tmutil", "destinationinfo"])
    out["time_machine_excluded"] = cmd(["tmutil", "isexcluded", str(directory)])
    if add_exclusion:
        out["time_machine_add_exclusion"] = cmd(["tmutil", "addexclusion", str(directory)])
        out["time_machine_excluded_after"] = cmd(["tmutil", "isexcluded", str(directory)])
        after = out["time_machine_excluded_after"]
        out["exclusion_not_set"] = not (after["status"] == "READ" and "[Excluded]" in after["output"])
    sp = cmd(["mdutil", "-s", str(directory)])
    out["spotlight_status"] = sp
    mdf = cmd(["mdfind", "-onlyin", str(directory), "."])
    out["spotlight_listing"] = mdf
    # ``mdutil -s`` printing "unknown indexing state" is NOT indexed (its raw text is recorded); only "Indexing enabled" or a listing of files on stdout counts as indexed
    indexed = (sp["status"] == "READ" and "Indexing enabled" in (sp["output"] + sp.get("stderr", ""))) or (mdf["status"] == "READ" and bool(mdf["output"].strip()))
    out["spotlight_indexes_directory"] = bool(indexed)
    out["noindex_suffix"] = directory.name.endswith(".noindex")
    out["blocks_e1"] = bool(indexed)
    return out


def finite(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def time_now() -> float:
    return time.monotonic()
