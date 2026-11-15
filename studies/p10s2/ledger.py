# ruff: noqa: E501
"""The study ledger of charged hours (ADR-0022 section 13.2 and the lead's ruling of 2026-11-15 on the three implementation audits).

ONE append-only ledger for the whole study, at a fixed path outside every run directory (``<repository>/experiments/P10S2/ledger.jsonl``, git-ignored), used by the fetch step, the data-generation step,
calibration, the pre-freeze gates stage, the rehearsal, the freeze, every registered stage, the recomputation, the analysis and the report. Every stage charges it (``charge(stage, seconds)`` or the
``measure`` context) and reads it (``remaining()``); P, the hours already charged, is never ignored because it is the same file in every stage.

Charged hours are the sum of wall-clock hours over all S2 processes: k parallel workers running for t hours charge k * t. The cap is 36 charged hours; the lead may raise it once, at the rehearsal's
headroom check only, to at most 72; the raise is an entry of this ledger, refused once any registered seed has been drawn (``budget.record_raise`` recomputes its amount from the rehearsal record).

``measure`` writes a start marker (marked ``registered`` for a stage that draws a registered seed) before the stage does anything, and an end entry whether the stage completes or raises. A start marker with
no end entry (the process was killed) is charged the wall time elapsed since its start, so a killed process is not free. Every number here is a charge in hours (measured wall time), never a result.
"""

import json
import os
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import core

STAGE_KINDS = (
    "fetch", "datagen", "calibration", "pilot", "gates-rehearsal", "rehearsal", "gates-registered", "train", "evaluate", "timing", "recompute", "analysis", "report", "freeze", "audit-other",
)  # fmt: skip
STUDY_LEDGER = Path("experiments/P10S2/ledger.jsonl")


class LedgerRefused(RuntimeError):
    """A stage that would take the charged total over the cap is not started."""


def study_ledger_path() -> Path:
    """The single study ledger (``core.ROOT`` is read at call time, so a clone or a test repository has its own)."""
    return core.ROOT / STUDY_LEDGER


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Ledger:
    """The study ledger when ``path`` is None; any other path is for tests of the mechanism."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else study_ledger_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # --- reading ---------------------------------------------------------------------------------------------------------------------------------
    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(ln) for ln in self.path.read_text().splitlines() if ln.strip()]

    def _unfinished(self, entries: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        ended = {e["run_id"] for e in entries if e.get("run_id") and e["status"] != "started"}
        return [e for e in entries if e["status"] == "started" and e.get("run_id") not in ended]

    def unfinished(self) -> list[dict[str, Any]]:
        """Start markers with no end entry (a killed process)."""
        return self._unfinished(self.entries())

    def total_hours(self, *, exclude_run: str | None = None) -> float:
        es = self.entries()
        done = sum(float(e["charged_hours"]) for e in es if e["status"] != "started")
        now = time.time()
        orphan = sum(int(e["workers"]) * max(0.0, now - float(e["t_start"])) / 3600.0 for e in self._unfinished(es) if e.get("run_id") != exclude_run)
        return done + orphan

    def by_kind(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for e in self.entries():
            if e["status"] != "started" and e["kind"] != "cap-raise":
                out[e["kind"]] = out.get(e["kind"], 0.0) + float(e["charged_hours"])
        return out

    def registered_observed(self) -> bool:
        """True once any process marked ``registered`` has started (its start marker counts: a process killed after drawing a seed has still drawn it)."""
        return any(bool(e.get("registered")) for e in self.entries())

    def cap_raise_entry(self) -> dict[str, Any] | None:
        raises = [e for e in self.entries() if e["kind"] == "cap-raise"]
        return raises[-1] if raises else None

    def cap_hours(self) -> float:
        """36 hours unless a raise is recorded in this ledger."""
        e = self.cap_raise_entry()
        base = float(core.CFG["budget"]["cap_hours"])
        if e is None:
            return base
        new = float(e["new_cap_hours"])
        if new > float(core.CFG["budget"]["cap_ceiling_hours"]):
            raise LedgerRefused("the recorded cap is above the ceiling")
        return new

    def remaining(self, cap_hours: float | None = None, *, exclude_run: str | None = None) -> float:
        """Hours left under the cap in force (or under ``cap_hours``) after every charge of every stage, P included."""
        return (self.cap_hours() if cap_hours is None else cap_hours) - self.total_hours(exclude_run=exclude_run)

    # --- writing ---------------------------------------------------------------------------------------------------------------------------------
    def _append(self, entry: dict[str, Any]) -> None:
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(entry, sort_keys=True) + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)

    def record(self, kind: str, wall_seconds: float, *, workers: int = 1, process: str = "", registered: bool = False, status: str = "completed", note: str = "", run_id: str | None = None, t_start: float = 0.0) -> dict[str, Any]:
        """One process's charge: ``workers`` x ``wall_seconds`` / 3600 hours."""
        if kind not in STAGE_KINDS:
            raise ValueError(f"unknown ledger kind {kind!r}")
        if workers < 1 or wall_seconds < 0:
            raise ValueError("workers >= 1 and wall_seconds >= 0 are required")
        charged = 0.0 if status == "started" else workers * wall_seconds / 3600.0
        entry = {"kind": kind, "process": process, "workers": workers, "wall_seconds": wall_seconds, "charged_hours": charged, "registered": registered, "status": status, "note": note, "at": _utc(), "run_id": run_id, "t_start": t_start}
        self._append(entry)
        return entry

    def charge(self, stage: str, seconds: float | None = None, **kw: Any) -> Any:
        """``charge(stage, seconds)`` writes one charge of ``seconds`` wall seconds now. ``charge(stage)`` with no seconds returns the ``measure`` context (kept so a block can be charged by its wall time)."""
        if seconds is None:
            return self.measure(stage, **kw)
        return self.record(stage, seconds, **kw)

    @contextmanager
    def measure(self, kind: str, *, workers: int = 1, process: str = "", registered: bool = False) -> Iterator[str]:
        """Charge the wall time of the enclosed block; a start marker is written first and the end entry whether the block completes or raises. Yields the run id."""
        rid = uuid.uuid4().hex
        t0, w0 = time.perf_counter(), time.time()
        self.record(kind, 0.0, workers=workers, process=process, registered=registered, status="started", run_id=rid, t_start=w0)
        status = "completed"
        try:
            yield rid
        except BaseException:
            status = "failed"
            raise
        finally:
            self.record(kind, time.perf_counter() - t0, workers=workers, process=process, registered=registered, status=status, run_id=rid, t_start=w0)

    def refuse_if_over(self, projected_hours: float, cap_hours: float | None = None, what: str = "stage") -> None:
        """A stage that would exceed the cap in force is not started (section 16 stop rules); the total includes everything charged by every stage."""
        cap = self.cap_hours() if cap_hours is None else cap_hours
        total = self.total_hours()
        if total + projected_hours > cap:
            raise LedgerRefused(f"refused: {what} projects {projected_hours:.3f} h on {total:.3f} h already charged, over the cap of {cap:.1f} h")

    def append_cap_raise(self, new_cap_hours: float, detail: dict[str, Any]) -> dict[str, Any]:
        """The raise as a ledger entry (``budget.record_raise`` validates and calls this)."""
        entry = {"kind": "cap-raise", "process": "cap raise at the rehearsal's headroom check", "workers": 1, "wall_seconds": 0.0, "charged_hours": 0.0, "registered": False, "status": "completed", "note": "", "at": _utc(), "run_id": None, "t_start": 0.0, "new_cap_hours": new_cap_hours, "detail": detail}
        self._append(entry)
        return entry

    def summary(self, cap_hours: float | None = None) -> dict[str, Any]:
        cap = self.cap_hours() if cap_hours is None else cap_hours
        t = self.total_hours()
        return {"charged_hours": t, "cap_hours": cap, "remaining_hours": cap - t, "by_kind": self.by_kind(), "processes": len([e for e in self.entries() if e["status"] != "started" and e["kind"] != "cap-raise"]), "unfinished": len(self.unfinished())}


def sum_charged(entries: Sequence[dict[str, Any]], kinds: Sequence[str] | None = None) -> float:
    return sum(float(e["charged_hours"]) for e in entries if e["status"] != "started" and (kinds is None or e["kind"] in kinds))
