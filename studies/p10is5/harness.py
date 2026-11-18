# ruff: noqa: E501
"""P10IS5 read harness (ADR-0028 section 5.1, section 7, ruling 6, 8, 9): one pass is one process issuing every read of the pass from k threads.

k ``threading.Thread``s, each with its own descriptor (opened with the discipline BEFORE the first snapshot), started and parked on a ``threading.Barrier``; snapshot; release; each thread runs its list with
``t0 = perf_counter_ns(); b = os.pread(fd, n, off); t1 = perf_counter_ns()`` and keeps (t0, t1, b); join; snapshot. A short read is an environment error. Nothing is printed or written between the two snapshots (output is held in
memory), nothing but the one file is opened between them, and the hashing of the bytes happens after the last snapshot. ``sys.getswitchinterval()`` is recorded and not changed.
Every figure is the host-visible cost through this harness, not the drive's service time.
"""

import hashlib
import os
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core, layout
from .core import EngineeringStop
from .device import PRead, counter_rule, open_cached_read, open_uncached_read
from .layout import PAGE, Request


@dataclass
class PassResult:
    """The raw outcome of one pass: per-request times and thread (in request order), both counter snapshots, the wall time and the bytes read (kept in memory for the parity hash after the last snapshot)."""

    k: int
    s: int
    n_requests: int
    pages: int
    t0_ns: list[int]
    t1_ns: list[int]
    thread: list[int]
    counter_start: Any
    counter_end: Any
    wall_ns: int
    switch_interval: float
    data: list[bytes] = field(repr=False)
    cross_start: dict[str, Any] | None = None
    cross_end: dict[str, Any] | None = None

    @property
    def latencies_ns(self) -> list[int]:
        return [b - a for a, b in zip(self.t0_ns, self.t1_ns, strict=True)]

    @property
    def counter_bytes(self) -> int:
        return int(self.counter_end.bytes_read - self.counter_start.bytes_read)

    @property
    def written_bytes(self) -> int:
        return int(self.counter_end.bytes_written - self.counter_start.bytes_written)

    @property
    def pages_per_second(self) -> float:
        return self.pages / (self.wall_ns / 1e9)

    def max_in_flight(self) -> int:
        """The largest number of requests whose (t0, t1) intervals overlap (descriptive; the host-side number of outstanding reads)."""
        ev = sorted([(a, 1) for a in self.t0_ns] + [(b, -1) for b in self.t1_ns], key=lambda e: (e[0], e[1]))
        cur = best = 0
        for _, d in ev:
            cur += d
            best = max(best, cur)
        return best


def run_pass(
    path: str | os.PathLike[str],
    requests: Sequence[Request],
    k: int,
    counter: Any,
    *,
    uncached: bool = True,
    pread: PRead = os.pread,
    cross_check: Callable[[], dict[str, Any]] | None = None,
    clock: Callable[[], int] = time.perf_counter_ns,
    opener: Callable[[Any, bool], int] | None = None,
) -> PassResult:
    """Run one pass: ``requests`` dealt to ``k`` threads by their ``thread`` field, one closed loop per thread. ``uncached`` False opens the descriptors without ``F_NOCACHE`` (only R1's control file).
    ``cross_check`` is called OUTSIDE the two snapshots (before the first, after the second) for the system-wide ioreg figures, which are printed and never charged."""
    if k < 1 or not requests:
        raise ValueError("a pass needs at least one thread and one request")
    lists = layout.thread_lists(requests, k)
    fds = [opener(path, uncached) if opener else (open_uncached_read(path) if uncached else open_cached_read(path)) for _ in range(k)]
    n = len(requests)
    t0 = [0] * n
    t1 = [0] * n
    got: list[bytes] = [b""] * n
    errors: list[BaseException] = []
    barrier = threading.Barrier(k + 1)

    def worker(j: int) -> None:
        fd, mine = fds[j], lists[j]
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            return
        try:
            for r in mine:
                a = clock()
                b = pread(fd, r.length, r.offset)
                z = clock()
                t0[r.index], t1[r.index], got[r.index] = a, z, b
        except BaseException as e:  # noqa: BLE001 - re-raised in the caller after the join
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(j,), daemon=True) for j in range(k)]
    try:
        for t in threads:
            t.start()
        cross_start = cross_check() if cross_check else None
        c0 = counter.read()
        w0 = clock()
        barrier.wait()
        for t in threads:
            t.join()
        c1 = counter.read()
        cross_end = cross_check() if cross_check else None
    except BaseException:
        barrier.abort()
        raise
    finally:
        for fd in fds:
            os.close(fd)
    if errors:
        raise EngineeringStop("READ ERROR", repr(errors[0]))
    w1 = max(t1)  # section 5.1: the wall time runs from the release of the start barrier to the last thread's last return
    for r, b in zip(requests, got, strict=True):
        if len(b) != r.length:
            raise EngineeringStop("SHORT READ", f"request {r.index}: {len(b)} of {r.length} bytes at offset {r.offset}")
    return PassResult(k, requests[0].pages if len({r.pages for r in requests}) == 1 else 0, n, sum(r.pages for r in requests), t0, t1, [r.thread for r in requests], c0, c1, w1 - w0, sys.getswitchinterval(), got, cross_start, cross_end)


def parity_ok(requests: Sequence[Request], data: Sequence[bytes], expected: Sequence[Sequence[str]]) -> tuple[bool, int]:
    """Ruling 8, after the pass's last snapshot: the SHA-256 of every page read equals the expected hash written by stage P. Returns (all equal, number of pages that differ)."""
    bad = 0
    for r, b, want in zip(requests, data, expected, strict=True):
        got = layout.page_hashes(b)
        bad += sum(1 for x, y in zip(got, want, strict=True) if x != y) + abs(len(got) - len(want))
    return bad == 0, bad


def pass_record(
    stage: str, repeat: int, k: int, s: int, attempt: int, requests: Sequence[Request], res: PassResult, *, parity: tuple[bool, int] | None, block: str, role: str, predicted_override: int | None = None
) -> dict[str, Any]:
    """The pass's record: requests (index, thread, offset, length), per-request times, counter snapshots (process; the system-wide cross-checks are inside ``cross``), page hashes' verdict, the counter rule's status."""
    predicted = predicted_override if predicted_override is not None else PAGE * sum(r.pages for r in requests)
    status = counter_rule(res.counter_bytes, sum(r.pages for r in requests), res.written_bytes)
    return {
        **core.envelope("pass"), "key": core.pass_key(stage, repeat, k, s, attempt), "stage": stage, "repeat": repeat, "k": k, "s": s, "attempt": attempt, "block": block, "role": role, "requests": len(requests),
        "pages": res.pages, "predicted_bytes": predicted, "counter_bytes": res.counter_bytes, "written_bytes": res.written_bytes, "counter_status": status, "counter_start": vars_of(res.counter_start), "counter_end": vars_of(res.counter_end),
        "wall_ns": res.wall_ns, "pages_per_second": res.pages_per_second, "latency_ns": res.latencies_ns, "t0_ns": res.t0_ns, "thread": res.thread, "max_in_flight": res.max_in_flight(),
        "switch_interval": res.switch_interval, "parity_ok": None if parity is None else parity[0], "parity_bad_pages": None if parity is None else parity[1], "cross_start": res.cross_start, "cross_end": res.cross_end,
        "request_list": [[r.index, r.thread, r.offset, r.length] for r in requests],
    }  # fmt: skip


def vars_of(snap: Any) -> dict[str, int]:
    return {"bytes_read": int(snap.bytes_read), "bytes_written": int(snap.bytes_written), "phys_footprint": int(getattr(snap, "phys_footprint", 0))}


def expected_digest(hashes: Sequence[Sequence[str]]) -> str:
    h = hashlib.sha256()
    for row in hashes:
        for x in row:
            h.update(x.encode())
    return h.hexdigest()
