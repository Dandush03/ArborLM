# ruff: noqa: E501
"""P10IS5 stage R0, the device record (ADR-0028 sections 3.1 EC3, 6, 8): EC3 before and after, the machine fingerprint, the hygiene checks, the counters readable, and the third review's three probes repeated under the
platform of record (at most 64 MiB written in all: 32 + 16 + 8 = 56 MiB, every byte through the write ledger). It runs on a shared machine. Probe pages are chosen by fixed arithmetic (no seed).

The probes record what the process counter, the APFS volume and the disk0 driver counted; none is a label. Cached reads (the buffered write of probe 2, the cached pair of probe 1) happen only on R0's own probe files.
"""

import fcntl
import os
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import blocks, core, device, harness, layout, system
from .device import F_FULLFSYNC, MIB, PAGE
from .layout import Request

PROBE_A_BYTES, PROBE_B_BYTES, PROBE_C_BYTES = 32 * MIB, 16 * MIB, 8 * MIB


def _pages_requests(pages: list[int], nbytes: int = PAGE) -> list[Request]:
    return [Request(j, 0, p // layout.TILE_PAGES, p % layout.TILE_PAGES, p * PAGE, nbytes) for j, p in enumerate(pages)]


def _write_probe(path: Path, nbytes: int, ledger: device.WriteLedger, counter: device.Counter, *, nocache: bool) -> dict[str, Any]:
    """A probe file of random bytes (``os.urandom``: probes need no reproducible content), written in 1 MiB ``pwrite`` calls through the ledger; ``nocache`` False is probe 2's buffered write."""
    ledger.begin(path.name, nbytes)
    c0 = counter.read()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if nocache:
            fcntl.fcntl(fd, device.F_NOCACHE, 1)
        for off in range(0, nbytes, MIB):
            ledger.write(fd, os.urandom(MIB), off)
        fcntl.fcntl(fd, F_FULLFSYNC)
    finally:
        os.close(fd)
        ledger.end()
    c1 = counter.read()
    ledger.settle(path.name, nbytes, c1.bytes_written - c0.bytes_written)
    return {"logical_bytes": nbytes, "process_bytes_written": c1.bytes_written - c0.bytes_written, "process_bytes_read": c1.bytes_read - c0.bytes_read, "nocache": nocache}


def _pass(path: Path, reqs: list[Request], deps: blocks.Deps, *, uncached: bool, predicted: int) -> dict[str, Any]:
    res = harness.run_pass(path, reqs, 1, deps.counter, uncached=uncached, pread=deps.pread, cross_check=deps.cross_check, opener=deps.opener)
    return {"requests": len(reqs), "counter_bytes": res.counter_bytes, "predicted_bytes": predicted, "ratio": None if predicted == 0 else res.counter_bytes / predicted, "median_ns": core.median(res.latencies_ns), "wall_ns": res.wall_ns, "cross_start": res.cross_start, "cross_end": res.cross_end}


def probe_a(dirpath: Path, ledger: device.WriteLedger, deps: blocks.Deps) -> dict[str, Any]:
    """Probe 1 (32 MiB, ``F_NOCACHE`` build): uncached reads of 512 pages (B) and again (B2); cached reads of 512 other pages twice (C: the second counts 0); an uncached read of those cached pages (D: ``F_NOCACHE``
    does not bypass cached pages); 4 KiB uncached reads at the start of 256 fresh pages (E: a whole page is counted)."""
    path = dirpath / "probe_a.bin"
    out: dict[str, Any] = {"write": _write_probe(path, PROBE_A_BYTES, ledger, deps.counter, nocache=True)}
    try:
        n = PROBE_A_BYTES // PAGE  # 2,048
        group = {name: [p for p in range(n) if p % 8 == r] for name, r in (("B", 0), ("C", 1), ("E", 2))}  # 256 pages each: fixed arithmetic, no seed
        b = _pass(path, _pages_requests(group["B"]), deps, uncached=True, predicted=len(group["B"]) * PAGE)
        out["B_cold_nocache"], out["B2_repeat_nocache"] = b, _pass(path, _pages_requests(group["B"]), deps, uncached=True, predicted=len(group["B"]) * PAGE)
        out["C1_cached_first"] = _pass(path, _pages_requests(group["C"]), deps, uncached=False, predicted=len(group["C"]) * PAGE)
        out["C2_cached_second"] = _pass(path, _pages_requests(group["C"]), deps, uncached=False, predicted=len(group["C"]) * PAGE)
        out["D_nocache_of_cached_pages"] = _pass(path, _pages_requests(group["C"]), deps, uncached=True, predicted=len(group["C"]) * PAGE)
        out["E_nocache_4KiB_reads"] = _pass(path, _pages_requests(group["E"], 4096), deps, uncached=True, predicted=len(group["E"]) * PAGE)
    finally:
        out["delete"] = device.delete_built_file(path)
    return out


def probe_b(dirpath: Path, ledger: device.WriteLedger, deps: blocks.Deps) -> dict[str, Any]:
    """Probe 2 (16 MiB, BUFFERED write, no ``F_NOCACHE``, then ``F_FULLFSYNC``): is the file cache-resident, so that a later uncached read is served from cache (it was, in the third review)? The process's own
    ``ri_phys_footprint`` is read as well."""
    path = dirpath / "probe_b.bin"
    out: dict[str, Any] = {"write": _write_probe(path, PROBE_B_BYTES, ledger, deps.counter, nocache=False)}
    try:
        pages = [p for p in range(PROBE_B_BYTES // PAGE) if p % 4 == 0]  # 256 pages
        out["nocache_read_after_buffered_write"] = _pass(path, _pages_requests(pages), deps, uncached=True, predicted=len(pages) * PAGE)
        out["phys_footprint"] = deps.counter.read().phys_footprint
    finally:
        out["delete"] = device.delete_built_file(path)
    return out


def probe_c(dirpath: Path, ledger: device.WriteLedger, deps: blocks.Deps) -> dict[str, Any]:
    """Probe 3 (8 MiB, ``F_NOCACHE`` build; repeats probe 2 part ii): 4 KiB uncached reads, then a 16 KiB uncached re-read of the same pages (does a sub-page read leave the page cached?), and a control on fresh pages."""
    path = dirpath / "probe_c.bin"
    out: dict[str, Any] = {"write": _write_probe(path, PROBE_C_BYTES, ledger, deps.counter, nocache=True)}
    try:
        n = PROBE_C_BYTES // PAGE  # 512
        g = [p for p in range(n) if p % 4 == 0]  # 128 pages
        h = [p for p in range(n) if p % 4 == 1]  # 128 fresh pages
        out["ii_nocache_4KiB_reads"] = _pass(path, _pages_requests(g, 4096), deps, uncached=True, predicted=len(g) * PAGE)
        out["ii_nocache_16KiB_reread_same_pages"] = _pass(path, _pages_requests(g), deps, uncached=True, predicted=len(g) * PAGE)
        out["control_nocache_16KiB_fresh_pages"] = _pass(path, _pages_requests(h), deps, uncached=True, predicted=len(h) * PAGE)
    finally:
        out["delete"] = device.delete_built_file(path)
    return out


def fingerprint(run: system.Run) -> dict[str, Any]:
    """The machine fingerprint (printed, not compared)."""
    rec: dict[str, Any] = {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version()}
    for name, argv in (("hw_model", ["sysctl", "-n", "hw.model"]), ("hw_memsize", ["sysctl", "-n", "hw.memsize"]), ("hw_pagesize", ["sysctl", "-n", "hw.pagesize"]), ("boot_time", ["sysctl", "-n", "kern.boottime"]), ("sw_vers", ["sw_vers"])):
        rc, out, _ = run(argv)
        rec[name] = out.strip() if rc == 0 else core.NOT_READABLE
    rc, out, _ = run(["diskutil", "info", "disk0"])
    rec["disk0_model"] = next((ln.split(":", 1)[1].strip() for ln in out.splitlines() if "Device / Media Name" in ln), core.NOT_READABLE) if rc == 0 else core.NOT_READABLE
    return rec


def run_r0(cfg: Mapping[str, Any], data_dir: Path, run_dir: Path, deps: blocks.Deps, ledger: device.WriteLedger, plat_problems: list[str]) -> dict[str, Any]:
    """R0: the order of checks of ruling 14 (EC3, free space, hygiene) then the counters and the three probes. A drive health warning or Spotlight indexing of the directory is PAUSED (raised after the record is written)."""
    b = cfg["budget"]
    data_dir.mkdir(parents=True, exist_ok=True)
    ec3_before = system.ec3_record(deps.run, deps.run_b, data_dir, "R0 before")
    free = device.require_free_space(data_dir, int(b["free_space_min_bytes"]))
    hyg = system.hygiene_record(deps.run, data_dir, file_exists=False, add_exclusion=True)
    counters: dict[str, Any] = {}
    try:
        snap = deps.counter.read()
        counters["process"] = {"bytes_read": snap.bytes_read, "bytes_written": snap.bytes_written, "phys_footprint": snap.phys_footprint, "readable": True}
    except core.EngineeringStop as e:
        counters["process"] = {"readable": False, "error": str(e)}
    counters["disk0_driver"] = system.read_driver(deps.run_b) or core.NOT_READABLE
    if int(b["probe_bytes"]) < PROBE_A_BYTES + PROBE_B_BYTES + PROBE_C_BYTES:
        raise core.EngineeringStop("CONFIG", "the probe budget is below the three probes")
    probes = {} if hyg["blocks_e1"] or not counters["process"]["readable"] else {"probe_1": probe_a(data_dir, ledger, deps), "probe_2": probe_b(data_dir, ledger, deps), "probe_3": probe_c(data_dir, ledger, deps)}
    ec3_after = system.ec3_record(deps.run, deps.run_b, data_dir, "R0 after")
    rec = {
        **core.envelope("r0"), "utc": core.utc_stamp(), "platform_problems": plat_problems, "platform_of_record": not plat_problems, "fingerprint": fingerprint(deps.run), "ec3_before": ec3_before, "ec3_after": ec3_after, "free_bytes": free, "hygiene": hyg,
        "counters": counters, "probes": probes, "probe_bytes_written": ledger.total(), "ledger_cap_bytes": ledger.cap_bytes,
    }  # fmt: skip
    core.write_record(run_dir / "r0" / "r0.json", rec, overwrite=True)
    for e in (ec3_before, ec3_after):
        if not e["health_ok"]:
            raise core.Paused("PAUSED — DRIVE HEALTH", f"SMART status {e['smart_status']}: goes to the human lead")
    if hyg["blocks_e1"]:
        raise core.Paused("PAUSED — SPOTLIGHT INDEXES THE DIRECTORY", str(data_dir))
    return rec
