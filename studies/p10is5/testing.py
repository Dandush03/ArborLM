# ruff: noqa: E501
"""Helpers of the P10IS5 tests (module of the package so that pytest does not collect it): fake counters, fake reads that synthesise tile bytes without a device, scripted quiet readings, a tiny geometry, scratch
directories under ``experiments/_scratch/`` that are deleted when the test ends and tally the bytes the tests wrote. Seeds are the registry's unit-test range 937001-937999 only. Self-check only."""

import contextlib
import os
import shutil
import threading
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from . import bench, core, layout
from .device import IOSnapshot

TEST_SEED_CONTENTS = 937001
TEST_SEED_ASSIGN = 937011
TEST_SEED_REQUEST = (937021, 937022, 937023)
TEST_SEED_ORDER = (937031, 937032, 937033)
TALLY = core.repo_root() / "experiments" / "_scratch" / "p10is5_test_bytes_written.log"
PAGE = layout.PAGE


@contextlib.contextmanager
def scratch(name: str) -> Iterator[Path]:
    """A directory under ``experiments/_scratch/`` of the worktree (git-ignored), deleted when the test ends; the bytes found in it at the end are appended to the tally (the tests' own disk writes)."""
    root = core.repo_root() / "experiments" / "_scratch" / "p10is5_tests" / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        TALLY.parent.mkdir(parents=True, exist_ok=True)
        with TALLY.open("a") as f:
            f.write(f"{name}\t{total}\n")
        shutil.rmtree(root, ignore_errors=True)


class FakeIO:
    """A counter and a ``pread`` that synthesise the bytes of tile files from the seed (no device). ``cached_offsets`` reads count 0 bytes (a polluted page); ``corrupt`` flips the first byte of a request;
    ``extra`` adds bytes to the counter of every read (contamination). Thread safe."""

    def __init__(self, contents_seed: int) -> None:
        self.seed = contents_seed
        self.lock = threading.Lock()
        self.read = 0
        self.written = 0
        self.footprint = 1 << 20
        self.cached_offsets: set[int] = set()
        self.corrupt: set[int] = set()
        self.extra = 0
        self._tiles: dict[int, bytes] = {}
        self.reads = 0
        self.modes: dict[int, bool] = {}
        self.model_cache = False
        self.cache: set[tuple[str, int]] = set()
        self.ns: dict[int, str] = {}

    def tile(self, t: int) -> bytes:
        if t not in self._tiles:
            self._tiles[t] = layout.tile_bytes(self.seed, t)
        return self._tiles[t]

    def opener(self, path: Any, uncached: bool = True) -> int:
        fd = os.open(os.devnull, os.O_RDONLY)
        with self.lock:
            self.modes[fd] = uncached
            self.ns[fd] = "control" if "control" in str(path) else "rest"  # two files never share cached pages
        return fd

    def pread(self, fd: int, n: int, off: int) -> bytes:
        t, within = divmod(off, layout.TILE_BYTES)
        b = self.tile(t)[within : within + n]
        with self.lock:
            self.reads += 1
            if self.model_cache:
                # whole pages are counted; pages already cached count 0 (also for F_NOCACHE: probe 1D); only a descriptor without F_NOCACHE adds pages to the cache
                ns = self.ns.get(fd, "rest")
                pages = [(ns, p) for p in range(off // PAGE, (off + n - 1) // PAGE + 1)]
                new = [p for p in pages if p not in self.cache]
                self.read += PAGE * len(new) + self.extra
                if not self.modes.get(fd, True):
                    self.cache.update(pages)
            elif off not in self.cached_offsets:
                self.read += n + self.extra
            if off in self.corrupt:
                b = bytes([b[0] ^ 0xFF]) + b[1:]
        return b

    def counter_read(self) -> IOSnapshot:
        with self.lock:
            return IOSnapshot(self.read, self.written, self.footprint)


class RealFileIO:
    """A fake PHYSICAL counter over REAL file reads (small files in the scratch directory): ``pread`` really reads and counts the bytes it returns, except at ``short_offsets`` (pages 'already cached': they count
    0). Used to test the build, the verification reads and the cold check on a few MiB without the device's counter."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.read = 0
        self.short_offsets: set[int] = set()

    def pread(self, fd: int, n: int, off: int) -> bytes:
        b = os.pread(fd, n, off)
        with self.lock:
            if off not in self.short_offsets:
                self.read += len(b)
        return b

    def counter_read(self) -> IOSnapshot:
        with self.lock:
            return IOSnapshot(self.read, 0, 1 << 20)


class FakeCounter:
    def __init__(self, io: "FakeIO | RealFileIO") -> None:
        self.io = io

    def read(self) -> IOSnapshot:
        return self.io.counter_read()


def devnull_opener(_: Any, uncached: bool = True) -> int:
    return os.open(os.devnull, os.O_RDONLY)


def quiet_record(ok: bool = True, **extra: Any) -> dict[str, Any]:
    return {"ok": ok, "failed": [] if ok else ["load"], "conditions": {}, "readings": {}, **extra}


def scripted_gate(script: Callable[[], dict[str, Any]], *, retries: int = 1) -> bench.QuietGate:
    """A gate whose ``read`` calls ``script``; ``wait`` tries up to ``retries`` times; ``settle`` does nothing."""

    def wait(read: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        hist = []
        for _ in range(retries):
            rec = read()
            hist.append(rec)
            if rec["ok"]:
                return rec, hist
        return None, hist

    return bench.QuietGate(script, wait, lambda: None)


def tiny_geometry(repeats: int = 2, spare: bool = True, usable: int = 30) -> core.Geometry:
    """Sizes 1, 3, 8, 64 at depths 1 and 2; 4, 4, 2, 1 requests from 1 tile each (enough segments); repeats 1..``repeats`` and a spare."""
    return core.Geometry("tiny", 64, usable, (1, 3, 8, 64), (1, 2), (4, 4, 2, 1), (1, 1, 1, 1), repeats, spare)


def tiny_context(run_dir: Path, file_path: Path | None = None, repeats: int = 2, spare: bool = True, stage: str = "E2") -> bench.Context:
    blocks = [{"repeat": i + 1, "role": "regular", "request_order_seed": TEST_SEED_REQUEST[i], "pass_order_seed": TEST_SEED_ORDER[i]} for i in range(repeats)]
    if spare:
        blocks.append({"repeat": repeats + 1, "role": "spare", "request_order_seed": TEST_SEED_REQUEST[2], "pass_order_seed": TEST_SEED_ORDER[2]})
    return bench.Context(stage, tiny_geometry(repeats, spare), TEST_SEED_CONTENTS, TEST_SEED_ASSIGN, tuple(blocks), file_path or run_dir / "x.bin", run_dir, 1 << 32)


def thresholds_for(geometry: core.Geometry, m_t: float = 0.10) -> dict[str, Any]:
    return {
        "m_t": m_t, "timing_spread": False, "label_min_repeats": 4, "valid_min_repeats": 4, "harness_limited_fraction": 0.25, "sizes": list(geometry.sizes), "depths": list(geometry.depths), "grid": [list(c) for c in geometry.cells()],
    }  # fmt: skip


# --- a fake machine for the system tools (canned output as this machine printed it) -------------------------------------------------------------------------
BATT = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=36307043)\t100%; charged; 0:00 remaining present: true\n"
PMSET = " powermode            0\n lowpowermode         0\n"
THERM = "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\n"
HID = '    | | |   "HIDIdleTime" = 13387188164083\n'


def plist_driver(read: int, write: int, rops: int, wops: int) -> bytes:
    import plistlib

    return plistlib.dumps([
        {"Statistics": {"Bytes (Read)": 0, "Bytes (Write)": 0, "Operations (Read)": 0, "Operations (Write)": 0}, "IORegistryEntryChildren": [{"BSD Name": "disk9"}]},
        {"Statistics": {"Bytes (Read)": read, "Bytes (Write)": write, "Operations (Read)": rops, "Operations (Write)": wops}, "IORegistryEntryChildren": [{"BSD Name": "disk0", "IORegistryEntryChildren": [{"BSD Name": "disk0s1"}]}]},
    ])  # fmt: skip


class Clock:
    """A fake clock: ``sleep`` advances it."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


class FakeSystem:
    """Canned ``run`` and ``run_b``; the disk counters advance by fixed rates per second of fake time; ``other_windows`` lists (from, to) fake-time windows in which another study's process is alive."""

    def __init__(self, clk: Clock, other_windows: "Sequence[tuple[float, float]]" = (), load: float = 2.0) -> None:
        self.clk, self.other, self.load = clk, other_windows, load

    def run(self, argv: "Sequence[str]") -> tuple[int, str, str]:
        a = list(argv)
        if a[:2] == ["sysctl", "-n"] and a[2] == "vm.loadavg":
            return 0, f"{{ {self.load + (self.clk.t % 7) / 100:.2f} 1.0 1.0 }}", ""
        if a[:2] == ["sysctl", "-n"]:
            return 0, "{ sec = 5, usec = 1 }", ""
        if a[0] == "ps" and any(x.startswith("pid,ppid") for x in a):
            return 0, "  PID  PPID COMM\n  505   404 python\n  404     1 /usr/bin/caffeinate\n", ""
        if a[0] == "ps":
            busy = any(lo <= self.clk.t < hi for lo, hi in self.other)
            return 0, "  PID COMMAND\n    1 /sbin/launchd\n  404 caffeinate\n" + ("  900 python -m pytest\n" if busy else ""), ""
        if a[:2] == ["pmset", "-g"] and len(a) == 3 and a[2] == "batt":
            return 0, BATT, ""
        if a[:2] == ["pmset", "-g"] and len(a) == 3:
            return 0, THERM, ""
        if a[:2] == ["pmset", "-g"]:
            return 0, PMSET, ""
        if a[0] == "ioreg":
            return 0, HID, ""
        if a[0] == "diskutil":
            return 0, "   SMART Status:              Verified\n", ""
        if a[0] == "df":
            return 0, "Filesystem 1024-blocks Used Available Capacity iused ifree %iused Mounted on\n/dev/disk3s5 3000000000 1000000000 2000000000 33% 1 1 0% /System/Volumes/Data\n", ""
        if a[0] == "mdutil":
            return 0, "Indexing disabled.", ""
        if a[0] in ("tmutil", "mdfind"):
            return 0, "", ""
        return 127, "", "unknown"

    def run_b(self, argv: "Sequence[str]") -> tuple[int, bytes]:
        t = int(self.clk.t)
        return 0, plist_driver(1000 * t, 2000 * t, 10 * t, 20 * t)
