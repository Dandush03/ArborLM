# ruff: noqa: E501
"""P10IS5 device layer (ADR-0028 sections 5.1, 6, 7; rulings 2, 13): the per-process counter, the read discipline, the one ledgered write function, the uncached build, the whole-file cold check.

``F_RDAHEAD`` 45, ``F_NOCACHE`` 48 and ``F_FULLFSYNC`` 51 are ``fcntl`` commands on macOS (the constants are the device config's). The counter is ``proc_pid_rusage(getpid(), RUSAGE_INFO_V2)`` through ``ctypes`` on
``/usr/lib/libSystem.B.dylib``: ``ri_diskio_bytesread``, ``ri_diskio_byteswritten``, ``ri_phys_footprint``; a non-zero return is an environment error. Not ``getrusage`` and not ``psutil``. Standard library only.

Every study write of a benchmark file goes through ``WriteLedger.write``: it adds to a persisted ledger and refuses (``WriteBudgetExceeded``, PAUSED) a write that would pass the cap, before the write is made.
"""

import ctypes
import fcntl
import hashlib
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from arborlm.io import read_json, write_json

from . import core, layout
from .core import EngineeringStop, Paused, WriteBudgetExceeded

F_RDAHEAD, F_NOCACHE, F_FULLFSYNC = 45, 48, 51
PAGE = layout.PAGE
MIB = 1 << 20
RUSAGE_INFO_V2 = 2


class RUsageInfoV2(ctypes.Structure):
    _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [
        (n, ctypes.c_uint64)
        for n in (
            "ri_user_time ri_system_time ri_pkg_idle_wkups ri_interrupt_wkups ri_pageins ri_wired_size ri_resident_size ri_phys_footprint ri_proc_start_abstime ri_proc_exit_abstime "
            "ri_child_user_time ri_child_system_time ri_child_pkg_idle_wkups ri_child_interrupt_wkups ri_child_pageins ri_child_elapsed_abstime ri_diskio_bytesread ri_diskio_byteswritten"
        ).split()
    ]  # fmt: skip


@dataclass(frozen=True)
class IOSnapshot:
    bytes_read: int
    bytes_written: int
    phys_footprint: int = 0


class Counter(Protocol):
    def read(self) -> IOSnapshot: ...


class ProcCounter:
    """The per-process physical counter of this process (all its threads), read through ``proc_pid_rusage``. A non-zero return is an environment error (ENGINEERING STOP)."""

    def __init__(self) -> None:
        self._libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)

    def read(self) -> IOSnapshot:
        r = RUsageInfoV2()
        rc = self._libc.proc_pid_rusage(os.getpid(), RUSAGE_INFO_V2, ctypes.byref(r))
        if rc != 0:
            raise EngineeringStop("NO PHYSICAL COUNTER", f"proc_pid_rusage returned {rc}, errno {ctypes.get_errno()}")
        return IOSnapshot(int(r.ri_diskio_bytesread), int(r.ri_diskio_byteswritten), int(r.ri_phys_footprint))


# --- descriptors: the read discipline (section 7, items 1 and 2) ---------------------------------------------------------------------------------
def open_uncached_read(path: Path | str) -> int:
    """A read descriptor with ``F_RDAHEAD`` 0 and ``F_NOCACHE`` 1. Every read of the file or the rehearsal file by any part of the study uses one."""
    fd = os.open(path, os.O_RDONLY)
    try:
        fcntl.fcntl(fd, F_RDAHEAD, 0)
        fcntl.fcntl(fd, F_NOCACHE, 1)
    except OSError:
        os.close(fd)
        raise
    return fd


def open_cached_read(path: Path | str) -> int:
    """A descriptor WITHOUT ``F_NOCACHE``: only for R1's control file (positive control, pollution control, harness figure and its warm-up)."""
    return os.open(path, os.O_RDONLY)


def open_uncached_write(path: Path | str, *, create: bool = True, exclusive: bool = True) -> int:
    flags = os.O_WRONLY | (os.O_CREAT if create else 0) | (os.O_EXCL if create and exclusive else 0)
    fd = os.open(path, flags, 0o600)
    try:
        fcntl.fcntl(fd, F_NOCACHE, 1)
    except OSError:
        os.close(fd)
        raise
    return fd


def counter_rule(counter_bytes: int, pages: int, written_bytes: int = 0) -> str:
    """Section 7: counter bytes read must equal 16,384 x pages requested. Below: STORE PAGES CACHED. Above (or any bytes written during the pass): COUNTER CONTAMINATED. Else OK."""
    predicted = PAGE * pages
    if counter_bytes < predicted:
        return core.STORE_PAGES_CACHED
    if counter_bytes > predicted or written_bytes != 0:
        return core.COUNTER_CONTAMINATED
    return "OK"


# --- the write ledger (section 6) ----------------------------------------------------------------------------------------------------------------
class WriteLedger:
    """The study's own bytes written, over every stage and attempt (failed ones included), in one JSON file under the run directory. ``begin`` reserves a stretch of writes against the cap (persisted before
    the first write of the stretch); ``write`` is THE function every benchmark-file write goes through: it checks the write against the reservation and refuses a write that would pass the cap before it is made.
    ``settle`` charges the larger of the logical bytes and the process's own ``ri_diskio_byteswritten`` delta (the larger is charged; the extra goes in as its own entry)."""

    def __init__(self, path: Path, cap_bytes: int) -> None:
        if cap_bytes <= 0:
            raise ValueError("the write cap must be positive")
        self.path, self.cap_bytes = path, int(cap_bytes)
        self._reserved_left = 0
        self._open_label: str | None = None

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != core.STUDY or data.get("kind") != "write_ledger":
            raise ValueError(f"not a P10IS5 write ledger: {self.path}")
        return list(data["entries"])

    def total(self) -> int:
        return int(sum(int(e["bytes"]) for e in self.entries()))

    def remaining(self) -> int:
        return max(0, self.cap_bytes - self.total())

    def _append(self, label: str, nbytes: int, note: str) -> None:
        entries = self.entries()
        entries.append({"label": label, "bytes": int(nbytes), "note": note, "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {**core.envelope("write_ledger"), "cap_bytes": self.cap_bytes, "entries": entries})

    def begin(self, label: str, nbytes: int) -> None:
        """Reserve ``nbytes`` of writes. Refused (PAUSED — WRITE BUDGET, nothing charged) when the total would pass the cap."""
        if nbytes < 0:
            raise ValueError("negative write")
        if self._reserved_left:
            raise RuntimeError("a reservation is still open")
        if self.total() + nbytes > self.cap_bytes:
            raise WriteBudgetExceeded(f"{label}: {nbytes} B on top of {self.total()} B would pass the cap of {self.cap_bytes} B")
        self._append(label, nbytes, "reserved before the writes")
        self._reserved_left, self._open_label = int(nbytes), label

    def write(self, fd: int, data: bytes, offset: int) -> int:
        """The one write function. The bytes are taken from the open reservation; a write larger than what is left is refused before it is made."""
        if len(data) > self._reserved_left:
            raise WriteBudgetExceeded(f"{self._open_label}: a write of {len(data)} B exceeds the {self._reserved_left} B reserved")
        n = os.pwrite(fd, data, offset)
        if n != len(data):
            raise EngineeringStop("SHORT WRITE", f"{n} of {len(data)} bytes")
        self._reserved_left -= n
        return n

    def end(self) -> int:
        """Close the reservation; returns the reserved bytes that were not written (they stay charged: nothing is credited back)."""
        left, self._reserved_left, self._open_label = self._reserved_left, 0, None
        return left

    def settle(self, label: str, logical: int, observed: int) -> int:
        """Charge the larger of ``logical`` and ``observed`` (the reservation already charged ``logical``); returns the extra charged."""
        extra = max(0, int(observed) - int(logical))
        if extra:
            self._append(label, extra, f"observed process bytes written ({observed}) above the logical bytes ({logical})")
        return extra


def free_space(path: Path) -> int:
    return int(shutil.disk_usage(path).free)


def require_free_space(path: Path, minimum: int) -> int:
    free = free_space(path)
    if free < minimum:
        raise Paused("PAUSED — FREE SPACE", f"{free} B free, at least {minimum} B required")
    return free


# --- reads with the counter ---------------------------------------------------------------------------------------------------------------------
PRead = Callable[[int, int, int], bytes]


@dataclass
class ScanResult:
    nbytes: int
    pages: int
    counter_bytes: int
    written_bytes: int
    status: str
    sha256: str


def uncached_scan(path: Path, offset: int, nbytes: int, counter: Counter, *, request_bytes: int = MIB, pread: PRead = os.pread, on_block: Callable[[int, bytes], None] | None = None) -> ScanResult:
    """Read ``nbytes`` from ``offset`` once, uncached, in ``request_bytes`` requests, and check the counter rule over the whole read. The hash is of the bytes read, in order. Nothing is printed or written inside."""
    if offset % PAGE or nbytes % PAGE or request_bytes % PAGE:
        raise ValueError("whole pages at page offsets only")
    fd = open_uncached_read(path)
    h = hashlib.sha256()
    try:
        a = counter.read()
        pos = 0
        while pos < nbytes:
            n = min(request_bytes, nbytes - pos)
            b = pread(fd, n, offset + pos)
            if len(b) != n:
                raise EngineeringStop("SHORT READ", f"{len(b)} of {n} bytes at offset {offset + pos}")
            h.update(b)
            if on_block is not None:
                on_block(offset + pos, b)
            pos += n
        z = counter.read()
    finally:
        os.close(fd)
    cb, wb = z.bytes_read - a.bytes_read, z.bytes_written - a.bytes_written
    return ScanResult(nbytes, nbytes // PAGE, cb, wb, counter_rule(cb, nbytes // PAGE, wb), h.hexdigest())


class StoreNotCold(Paused):
    """A whole-file uncached read counted fewer bytes than the file holds (or a verification read did): PAUSED — STORE NOT COLD."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(core.STORE_NOT_COLD, detail)


# --- the uncached build (section 7 item 1, ruling 13) ---------------------------------------------------------------------------------------------
def manifest_path(path: Path) -> Path:
    return path.with_name(path.name + ".build.json")


def tile_digest(contents_seed: int, first: int, count: int) -> str:
    """SHA-256 of tiles ``first .. first+count-1`` regenerated from the seed."""
    h = hashlib.sha256()
    for t in range(first, first + count):
        h.update(layout.tile_bytes(contents_seed, t))
    return h.hexdigest()


def build_file(path: Path, tiles: int, contents_seed: int, ledger: WriteLedger, counter: Counter, *, chunk_bytes: int, resume: bool = False, pread: PRead = os.pread, label: str | None = None, min_free: int = 0) -> dict[str, Any]:
    """Write ``tiles`` tiles to ``path`` on a ``F_NOCACHE`` descriptor in 1 MiB ``pwrite`` calls through ``ledger.write``, closing each chunk after ``F_FULLFSYNC``, then verify the chunk by an uncached read against
    the regenerated SHA-256 and the counter rule. A manifest beside the file lists the verified chunks; with ``resume`` the build continues at the first unverified chunk (rewritten bytes are charged again).
    Without ``resume`` an existing file is refused. A verification read below the counter rule is STORE NOT COLD (PAUSED); a hash difference is ENGINEERING STOP (DATA MISMATCH)."""
    label = label or path.name
    size = tiles * layout.TILE_BYTES
    if chunk_bytes % layout.TILE_BYTES:
        raise ValueError("a chunk is a whole number of tiles")
    tiles_per_chunk = chunk_bytes // layout.TILE_BYTES
    n_chunks = -(-tiles // tiles_per_chunk)
    mpath = manifest_path(path)
    verified: list[dict[str, Any]] = []
    if path.exists() or mpath.exists():
        if not resume:
            raise core.StageRefused(f"refused: {path} exists; a file is built once (a rebuild deletes it first, charged to the write budget)")
        if mpath.is_file():
            m = read_json(mpath)
            if m.get("tiles") != tiles or m.get("seed") != contents_seed:
                raise core.StageRefused(f"refused: the build manifest of {path} is for another geometry or seed")
            verified = list(m["verified_chunks"])
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"path": str(path), "tiles": tiles, "bytes": size, "chunks": n_chunks, "resumed_from_chunk": len(verified), "chunk_reports": []}
    for ci in range(len(verified), n_chunks):
        first = ci * tiles_per_chunk
        count = min(tiles_per_chunk, tiles - first)
        cbytes = count * layout.TILE_BYTES
        if min_free:
            require_free_space(path.parent, min_free)
        ledger.begin(f"{label}#chunk{ci}", cbytes)
        c0 = counter.read()
        h = hashlib.sha256()
        fd = open_uncached_write(path, create=not path.exists(), exclusive=False)
        try:
            for t in range(first, first + count):
                data = layout.tile_bytes(contents_seed, t)
                h.update(data)
                ledger.write(fd, data, t * layout.TILE_BYTES)
            fcntl.fcntl(fd, F_FULLFSYNC)
        finally:
            os.close(fd)
            ledger.end()
        c1 = counter.read()
        extra = ledger.settle(f"{label}#chunk{ci}", cbytes, c1.bytes_written - c0.bytes_written)
        scan = uncached_scan(path, first * layout.TILE_BYTES, cbytes, counter, pread=pread)
        entry = {"chunk": ci, "bytes": cbytes, "sha256": h.hexdigest(), "verify_counter_bytes": scan.counter_bytes, "verify_status": scan.status, "observed_extra_written": extra}
        report["chunk_reports"].append(entry)
        if scan.sha256 != h.hexdigest():
            raise EngineeringStop("DATA MISMATCH", f"{path} chunk {ci}: the bytes read back differ from the regenerated bytes")
        if scan.status != "OK":
            raise StoreNotCold(f"{path} chunk {ci}: verification read counted {scan.counter_bytes} B for {cbytes} B ({scan.status})")
        verified.append({"chunk": ci, "sha256": h.hexdigest()})
        write_json(mpath, {"tiles": tiles, "seed": contents_seed, "verified_chunks": verified})
    if path.stat().st_size != size:
        raise EngineeringStop("FILE SIZE", f"{path} is {path.stat().st_size} B, expected {size} B")
    report["complete"] = True
    return report


def delete_built_file(path: Path) -> dict[str, Any]:
    """Unlink the file and its manifest, check its absence and record the free space (the snapshot check is the caller's)."""
    for p in (path, manifest_path(path)):
        if p.exists():
            p.unlink()
    return {"path": str(path), "absent": not path.exists() and not manifest_path(path).exists(), "free_bytes": free_space(path.parent)}


# --- the cold check (section 7 item 7) ----------------------------------------------------------------------------------------------------------
def cold_check(path: Path, tiles: int, contents_seed: int, counter: Counter, *, pread: PRead = os.pread, tile_hashes: Mapping[int, str] | None = None) -> dict[str, Any]:
    """The whole file read once, uncached, in 1 MiB requests, against the counter: counter bytes must equal the file size. A short count is STORE NOT COLD (the caller deletes and rebuilds once); a count above is
    COUNTER CONTAMINATED. The bytes are also compared, tile by tile, with the regenerated tiles (a difference is ENGINEERING STOP (DATA MISMATCH)). The check reads every page once and equally."""
    size = tiles * layout.TILE_BYTES
    hashes: dict[int, str] = {}

    def on_block(off: int, b: bytes) -> None:
        hashes[off // layout.TILE_BYTES] = hashlib.sha256(b).hexdigest()

    scan = uncached_scan(path, 0, size, counter, pread=pread, on_block=on_block)
    bad = [t for t in sorted(hashes) if hashes[t] != (tile_hashes[t] if tile_hashes is not None else layout.tile_sha256(contents_seed, t))]
    if bad:
        raise EngineeringStop("DATA MISMATCH", f"{path}: tiles {bad[:5]} differ from the regenerated tiles")
    return {
        "path": str(path), "tiles": tiles, "bytes": size, "counter_bytes": scan.counter_bytes, "written_bytes": scan.written_bytes, "status": scan.status, "cold": scan.status == "OK",
        "verdict": "COLD" if scan.status == "OK" else core.STORE_NOT_COLD if scan.status == core.STORE_PAGES_CACHED else core.COUNTER_CONTAMINATED,
    }  # fmt: skip


def hold_cold(path: Path, tiles: int, contents_seed: int, counter: Counter, rebuild: Callable[[], None], wait: Callable[[], None], *, pread: PRead = os.pread) -> dict[str, Any]:
    """Section 7 item 7: a first short count is PAUSED — STORE NOT COLD: the file is rebuilt once (``rebuild``, charged by the caller's ledger), the 10-minute ``wait`` is taken, and the file is checked again. A second
    short count is ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD. Returns the record; raises nothing for the two registered outcomes (the caller maps them)."""
    first = cold_check(path, tiles, contents_seed, counter, pread=pread)
    rec: dict[str, Any] = {"first": first, "rebuilt": False, "second": None, "outcome": "COLD"}
    if first["cold"]:
        return rec
    rec["outcome"] = core.STORE_NOT_COLD
    rebuild()
    wait()
    rec["rebuilt"] = True
    second = cold_check(path, tiles, contents_seed, counter, pread=pread)
    rec["second"] = second
    rec["outcome"] = "COLD" if second["cold"] else f"{core.ENG_NOT_EVALUABLE} — {core.STORE_CANNOT_BE_HELD_COLD}"
    return rec


def pages_requested(requests: Sequence[layout.Request]) -> int:
    return sum(r.pages for r in requests)
