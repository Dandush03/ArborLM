# ruff: noqa: E501
"""P10IS0 memory and disk accounting and stage 3's quiet-machine rule (ADR-0023 sections 9, 10, 11; coordinator rulings 3 and 4).

* Disk: a stage PAUSES when the run directory reaches 110 GiB or the free space falls below 50 GiB (``check_disk``); the projection is the per-update records at 609 bytes (section 11).
* Memory: the loop streams its records to disk (``adapter.run_segment``), so a worker's memory does not grow with run length; the projection if the records were held in memory (1,144 bytes each) is ``memory_projection_bytes``. The
  worker count is ``ladder.worker_count`` (n = min(6, floor(9 GiB / measured peak)); n < 1 is an engineering stop).
* Stage 3: the quiet condition is read BEFORE the stage's own workers start: the 1-minute load average sampled every 10 s for 60 s, every sample at most 2.0, and no other study's process alive (``quiet_check``). Then six workers alone.
  Up to three attempts within 24 hours; after that PAUSED — MACHINE NOT QUIET (``attempt_decision``). An attempt that fails the condition is kept and never used (ruling 20).
"""

import os
import shutil
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

from . import core


class PlatformMismatch(RuntimeError):
    """The running platform is not the platform of record (ADR-0023 section 10: macOS arm64, torch 2.8.0, one thread, one interop thread, deterministic algorithms)."""


def configure_process() -> None:
    """One thread, one interop thread, deterministic algorithms: set BEFORE the platform check (N6), whatever thread variables the process was started with."""
    import torch

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass  # already set (and parallel work has started) in this process: the check below then verifies it
    torch.use_deterministic_algorithms(True)


def platform_record() -> dict[str, Any]:
    """OS, machine, Python, torch version, threads, interop threads and the deterministic flag (recorded in every stage manifest, train record and the rehearsal record)."""
    import platform
    import sys

    import torch

    return {
        "system": platform.system(), "machine": platform.machine(), "python": sys.version.split()[0], "torch": torch.__version__.split("+")[0], "torch_num_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }  # fmt: skip


def check_platform(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Compare the running platform with the config's ``[platform]`` (call ``configure_process`` first). Returns the record; raises ``PlatformMismatch`` naming every difference."""
    want = (cfg or core.load_config())["platform"]
    rec = platform_record()
    diffs = [f"{k}: {rec[k]!r} != {want[k]!r}" for k in ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms") if rec[k] != want[k]]
    if diffs:
        raise PlatformMismatch("not the platform of record: " + "; ".join(diffs))
    return rec


PAUSED_DISK = "PAUSED — DISK"
PAUSED_NOT_QUIET = "PAUSED — MACHINE NOT QUIET"
OTHER_STUDY_MARKERS = ("studies.p9", "studies.p10", "arborlm.p")  # command lines of another study's compute stage


class DiskPause(RuntimeError):
    """The run directory reached its cap or free space fell below the minimum: PAUSED, resumable; no cell is dropped and no label depends on it."""


def dir_bytes(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                continue
    return total


def check_disk(run_dir: Path, cfg: Mapping[str, Any] | None = None, *, used: int | None = None, free: int | None = None, also: Sequence[Path] = ()) -> dict[str, int]:
    """Raise ``DiskPause`` when the run directory is at 110 GiB or more, or free space is below 50 GiB. ``used`` and ``free`` are injectable for tests."""
    r = (cfg or core.load_config())["resources"]
    u = dir_bytes(run_dir) if used is None and run_dir.exists() else (used or 0)
    u += sum(dir_bytes(d) for d in also if d.exists())  # N4: the sealed directory counts toward the same 110 GiB
    f = min(shutil.disk_usage(d if d.exists() else d.parent).free for d in [run_dir, *also]) if free is None else free  # and free space is checked on both filesystems
    if u >= int(r["disk_cap_bytes"]):
        raise DiskPause(f"the run directory holds {u} bytes, at or above the cap of {r['disk_cap_bytes']}")
    if f < int(r["disk_free_min_bytes"]):
        raise DiskPause(f"free disk space {f} bytes is below the minimum of {r['disk_free_min_bytes']}")
    return {"run_dir_bytes": u, "free_bytes": f}


def check_free(path: Path, cfg: Mapping[str, Any] | None = None, *, free: int | None = None) -> None:
    """The free-space half of the disk rule, cheap enough for a training loop (every 1,024 updates)."""
    r = (cfg or core.load_config())["resources"]
    f = shutil.disk_usage(path if path.exists() else path.parent if path.parent.exists() else Path("/")).free if free is None else free
    if f < int(r["disk_free_min_bytes"]):
        raise DiskPause(f"free disk space {f} bytes is below the minimum of {r['disk_free_min_bytes']}")


def disk_projection_bytes(updates_total: int, cfg: Mapping[str, Any] | None = None) -> int:
    """ANALYTICAL: per-update logs at 609 bytes per update (P10-S0: 19,948,322 bytes for 32,768 updates), plus nothing for snapshots (counted separately by the plan)."""
    return updates_total * int((cfg or core.load_config())["resources"]["disk_bytes_per_update"])


def memory_projection_bytes(updates: int, cfg: Mapping[str, Any] | None = None) -> int:
    """ANALYTICAL: what P10-S0's loop would add per worker if the per-update records were held in memory (1,144 bytes each): 0.56 GiB at 524,288 updates. This study's loop keeps none."""
    return updates * int((cfg or core.load_config())["resources"]["update_record_bytes"])


def other_study_processes(*, exclude_pids: Sequence[int] = ()) -> list[dict[str, Any]]:
    """Processes of another study's compute stage alive on the machine (by command line). Never matches this process or ``exclude_pids``."""
    me = {os.getpid(), *exclude_pids}
    try:
        cur = psutil.Process()
        me |= {p.pid for p in cur.parents()} | {p.pid for p in cur.children(recursive=True)}
    except psutil.Error:
        pass
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
        except psutil.Error:
            continue
        if p.info["pid"] in me:
            continue  # this process, its ancestors and its descendants (its own workers); another study's test suite is another study's process (R13)
        if "python" in cmd and any(m in cmd for m in OTHER_STUDY_MARKERS) and "studies.p10is0" not in cmd:
            out.append({"pid": p.info["pid"], "command": cmd[:400]})
    return out


def quiet_check(
    cfg: Mapping[str, Any] | None = None, *, sampler: Callable[[], float] | None = None, sleep: Callable[[float], None] = time.sleep, others: Callable[[], list[dict[str, Any]]] = other_study_processes
) -> dict[str, Any]:
    """Read BEFORE stage 3's own workers start (so its own load is not counted): the 1-minute load average every ``sample_seconds`` for ``sample_window_seconds`` (a bounded loop: window / interval + 1 samples), every sample at most
    ``quiet_load_max``, and no other study's process alive at the start or the end."""
    t = (cfg or core.load_config())["timing"]
    sample = sampler or (lambda: os.getloadavg()[0])
    n = int(t["sample_window_seconds"]) // int(t["sample_seconds"]) + 1
    samples: list[float] = []
    procs = others()
    for i in range(n):
        samples.append(float(sample()))
        if i < n - 1:
            sleep(float(t["sample_seconds"]))
    procs += others()
    limit = float(t["quiet_load_max"])
    reasons = []
    if any(s > limit for s in samples):
        reasons.append(f"a load-average sample above {limit}")
    if procs:
        reasons.append("another study's process is alive")
    return {"quiet": not reasons, "samples": samples, "max_sample": max(samples), "limit": limit, "other_processes": procs, "reasons": reasons}


def attempt_decision(attempts: Sequence[Mapping[str, Any]], first_started: datetime, now: datetime | None = None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """After the attempts so far (each with ``quiet``): READY (use the first attempt that met the condition: never a failed one, never the least loaded), RETRY (fewer than three attempts and within 24 hours of the first
    attempt's start), or PAUSED — MACHINE NOT QUIET (rescheduled; never run loaded)."""
    t = (cfg or core.load_config())["timing"]
    now = now or datetime.now(UTC)
    for i, a in enumerate(attempts):
        if a.get("quiet"):
            return {"decision": "READY", "use_attempt": i}
    expired = now - first_started > timedelta(hours=float(t["attempt_window_hours"]))
    if len(attempts) >= int(t["attempts"]) or expired:
        return {"decision": PAUSED_NOT_QUIET, "use_attempt": None, "attempts": len(attempts), "window_expired": expired}
    return {"decision": "RETRY", "use_attempt": None, "attempts": len(attempts), "window_expired": False}


def stage3_rates(records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any] | None = None) -> dict[tuple[str, int], float]:
    """Seconds per update by (arm, slots) from the quiet attempt's records, each of at least ``min_updates`` updates; a shorter record is refused (the rehearsal runs at least 8,192 updates per (arm, slot count))."""
    need = int((cfg or core.load_config())["timing"]["min_updates"])
    out: dict[tuple[str, int], float] = {}
    for r in records:
        if int(r["updates"]) < need:
            raise ValueError(f"timing record for {r['arm']} at {r['slots']} slots has {r['updates']} updates, fewer than {need}")
        out[(str(r["arm"]), int(r["slots"]))] = float(r["wall_seconds"]) / int(r["updates"])
    return out
