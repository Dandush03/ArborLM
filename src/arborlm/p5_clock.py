"""P5 timing budget and explicit, single-use reporting acknowledgements."""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .p5_config import SUITE_SECONDS, TIMING_SECONDS
from .watchdog import POLL_SECONDS


@dataclass
class ActiveClock:
    quality_seconds: float
    now: Callable[[], float] = time.monotonic
    timing_start: float = field(init=False)
    external_wait_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.timing_start = self.now()

    def snapshot(self) -> dict[str, float]:
        wall = self.now() - self.timing_start
        active = wall - self.external_wait_seconds
        return {
            "quality_worker_seconds": self.quality_seconds,
            "quality_stage_wall_seconds": self.quality_seconds,
            "timing_stage_wall_seconds": wall,
            "external_reporting_wait_seconds": self.external_wait_seconds,
            "timing_worker_active_seconds": active,
            "combined_worker_active_seconds": self.quality_seconds + active,
        }

    def remaining(self) -> float:
        values = self.snapshot()
        return min(
            TIMING_SECONDS - values["timing_worker_active_seconds"],
            SUITE_SECONDS - values["combined_worker_active_seconds"],
        )

    def worker_budget(self, ceiling: float) -> float:
        remaining = self.remaining()
        if remaining <= 0:
            raise TimeoutError("P5 timing or combined worker deadline exceeded")
        return min(ceiling, remaining)

    def exclude_wait(self, elapsed: float) -> None:
        if elapsed < 0:
            raise ValueError("nonmonotonic reporting wait")
        self.external_wait_seconds += elapsed


def _validated_ack(value: object, suite: str, worker: str, used: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != {
        "suite_id",
        "worker_id",
        "commit",
        "push_completed",
    }:
        raise ValueError("P5 malformed reporting acknowledgement")
    commit = value["commit"]
    if (
        value["suite_id"] != suite
        or value["worker_id"] != worker
        or worker in used
        or value["push_completed"] is not True
        or not isinstance(commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
    ):
        raise ValueError("P5 mismatched/reused reporting acknowledgement")
    return value


def wait_for_ack(
    run: Path,
    suite: str,
    worker: str,
    used: set[str],
    clock: ActiveClock,
    *,
    announce: Callable[[dict[str, Any]], None],
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Call only after the worker is reaped and its compact bundle is finalized."""
    clock.worker_budget(float("inf"))
    inbox = run / "report-acks"
    inbox.mkdir(exist_ok=True)
    ack = inbox / f"{worker}.json"
    if ack.exists():
        raise ValueError("P5 acknowledgement arrived before its worker request")
    expected = {
        "event": "timing_ack_required",
        "suite_id": suite,
        "worker_id": worker,
        "ack_path": str(ack),
        "accounting": clock.snapshot(),
    }
    write_json(run / "expected_ack.json", expected)
    # Previous files are retained as evidence. New unexpected IDs are not accepted.
    if any(path.name != f"{worker}.json" and path.stem not in used for path in inbox.iterdir()):
        raise ValueError("P5 out-of-order acknowledgement file")
    announce(expected)
    clock.worker_budget(float("inf"))
    start = clock.now()
    while not ack.is_file():
        if any(path.name != f"{worker}.json" and path.stem not in used for path in inbox.iterdir()):
            raise ValueError("P5 out-of-order acknowledgement file")
        sleep(POLL_SECONDS)
    elapsed = clock.now() - start
    if any(path.name != f"{worker}.json" and path.stem not in used for path in inbox.iterdir()):
        raise ValueError("P5 out-of-order acknowledgement file")
    value = _validated_ack(read_json(ack), suite, worker, used)
    clock.exclude_wait(elapsed)
    used.add(worker)
    record = {**value, "external_wait_seconds": elapsed, "accounting": clock.snapshot()}
    write_json(run / "expected_ack.json", {"acknowledged": record})
    return record


class SuiteRSS:
    """Sample the P5 supervisor plus all descendants, including stage packaging."""

    def __init__(self) -> None:
        import threading

        self.stop = threading.Event()
        self.peak = 0
        self.breached = False
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        import os
        import signal

        import psutil

        from .watchdog import RSS_BYTES, _rss

        process = psutil.Process()
        while not self.stop.is_set():
            self.peak = max(self.peak, _rss(process))
            if self.peak > RSS_BYTES:
                self.breached = True
                # Workers own process groups. The existing supervisor traps SIGINT,
                # terminates its active child tree, and finalizes evidence.
                os.kill(os.getpid(), signal.SIGINT)
                return
            self.stop.wait(POLL_SECONDS)

    def __enter__(self) -> "SuiteRSS":
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop.set()
        self.thread.join()
