# ruff: noqa: E501
"""The charged-time ledger (ADR-0022 section 13.2).

Charged hours are the sum of wall-clock hours over all S2 processes: k parallel workers running for t hours charge k * t. The data-generation step, calibration, pilot, rehearsal and the registered run
are all charged. So are the second gates stage on registered seeds and the independent recomputation of every score: "all S2 processes" has no exception. The cap is 36 charged hours; the lead may raise
it once, at the rehearsal's headroom check only, to at most 72 (``budget``). A stage whose projected charge would take the total over the cap is not started.

The ledger is an append-only JSON-lines file; an entry is written even when the process fails. ``registered`` marks a process that observes a registered replicate seed (the cap-raise mechanism of
``budget`` refuses after any such entry).
"""

import json
import os
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE_KINDS = (
    "datagen", "calibration", "pilot", "rehearsal", "gates-rehearsal", "gates-registered", "train", "evaluate", "timing", "recompute", "analysis", "report", "audit-other",
)  # fmt: skip


class LedgerRefused(RuntimeError):
    """A stage that would take the charged total over the cap is not started."""


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(ln) for ln in self.path.read_text().splitlines() if ln.strip()]

    def _append(self, entry: dict[str, Any]) -> None:
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(entry, sort_keys=True) + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)

    def record(self, kind: str, wall_seconds: float, *, workers: int = 1, process: str = "", registered: bool = False, status: str = "completed", note: str = "") -> dict[str, Any]:
        """One process's charge: ``workers`` x ``wall_seconds`` / 3600 hours."""
        if kind not in STAGE_KINDS:
            raise ValueError(f"unknown ledger kind {kind!r}")
        if workers < 1 or wall_seconds < 0:
            raise ValueError("workers >= 1 and wall_seconds >= 0 are required")
        entry = {"kind": kind, "process": process, "workers": workers, "wall_seconds": wall_seconds, "charged_hours": workers * wall_seconds / 3600.0, "registered": registered, "status": status, "note": note, "at": _utc()}
        self._append(entry)
        return entry

    @contextmanager
    def charge(self, kind: str, *, workers: int = 1, process: str = "", registered: bool = False) -> Iterator[None]:
        """Charge the wall time of the enclosed block; the entry is written whether the block completes or raises."""
        t0 = time.perf_counter()
        status = "completed"
        try:
            yield
        except BaseException:
            status = "failed"
            raise
        finally:
            self.record(kind, time.perf_counter() - t0, workers=workers, process=process, registered=registered, status=status)

    def total_hours(self) -> float:
        return sum(float(e["charged_hours"]) for e in self.entries())

    def by_kind(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for e in self.entries():
            out[e["kind"]] = out.get(e["kind"], 0.0) + float(e["charged_hours"])
        return out

    def registered_observed(self) -> bool:
        return any(bool(e.get("registered")) for e in self.entries())

    def refuse_if_over(self, projected_hours: float, cap_hours: float, what: str) -> None:
        """A stage that would exceed the cap is not started (section 16 stop rules)."""
        total = self.total_hours()
        if total + projected_hours > cap_hours:
            raise LedgerRefused(f"refused: {what} projects {projected_hours:.3f} h on {total:.3f} h already charged, over the cap of {cap_hours:.1f} h")

    def summary(self, cap_hours: float) -> dict[str, Any]:
        t = self.total_hours()
        return {"charged_hours": t, "cap_hours": cap_hours, "remaining_hours": cap_hours - t, "by_kind": self.by_kind(), "processes": len(self.entries())}


def sum_charged(entries: Sequence[dict[str, Any]], kinds: Sequence[str] | None = None) -> float:
    return sum(float(e["charged_hours"]) for e in entries if kinds is None or e["kind"] in kinds)
