# ruff: noqa: E501
"""P10IS0 task runner and stage manifests (ADR-0023 sections 10, 12, 14), the design of ``studies/p10ir/runner.py`` in this study's own file: resumable.

A stage is a list of tasks (one per cell label; the items of a cell are run in one process so that its draw is generated once). A task whose ``result`` file exists is COMPLETE and is not run again.
A stop on a resource cap (the stage's wall-clock cap, the 3 GiB per-worker or the 18 GiB aggregate memory guard; the worker count itself is ``ladder.worker_count``) leaves the stage PAUSED: the unfinished tasks are listed ``killed_cap``,
``killed_rss`` or ``not_started`` and the next invocation runs only them (inside a task a finished read or gate is not recomputed: ``items.run_item``). A task that exits with an error is FAILED: its
record is kept and it is not re-run. The stage manifest records PAUSED or COMPLETE (or FAILED) and keeps one history entry per invocation. No shell is involved: argument lists only. Every wait has a
deadline (the stage cap). A worker's refusal on an identity or precondition check (exit 75) is PAUSED — IDENTITY: no failed record, and the next invocation runs the task again."""

import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from arborlm.io import write_json

from . import core

COMPLETED, FAILED, KILLED_CAP, KILLED_RSS, NOT_STARTED = "completed", "failed", "killed_cap", "killed_rss", "not_started"
PAUSED_IDENTITY = "paused_identity"
IDENTITY_EXIT = 75  # a worker that refuses on an identity or precondition check (a dirty tree, a frozen file that differs, no Decision 2) exits with this code (EX_TEMPFAIL): PAUSED — IDENTITY, not FAILED
PAUSED_STATUSES = (KILLED_CAP, KILLED_RSS, NOT_STARTED, PAUSED_IDENTITY)
POLL = 0.2


@dataclass(frozen=True)
class Task:
    label: str
    argv: tuple[str, ...]
    result_path: Path
    failed_path: Path
    log_path: Path


def _tree_rss(proc: psutil.Process) -> int:
    try:
        return int(sum(p.memory_info().rss for p in [proc, *proc.children(recursive=True)]))
    except psutil.Error:
        return 0


def _kill(popen: "subprocess.Popen[bytes]") -> None:
    try:
        parent = psutil.Process(popen.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.Error:
        pass
    popen.wait(timeout=30)


def run_tasks(tasks: Sequence[Task], *, workers: int, cap_seconds: float, rss_worker_bytes: int, rss_aggregate_bytes: int, env: dict[str, str] | None = None, poll: float = POLL) -> tuple[dict[str, dict[str, Any]], float]:
    """Run the tasks in subprocesses, at most ``workers`` at once, until all are done or ``cap_seconds`` of wall clock pass (then every running task is killed: ``killed_cap``, the rest ``not_started``).
    Returns (label -> outcome, wall seconds). A task with a result file is ``completed`` without running; one with a failed record is ``failed`` without running."""
    import os

    begun = time.monotonic()
    out: dict[str, dict[str, Any]] = {}
    pending = []
    for t in tasks:
        if t.result_path.is_file():
            out[t.label] = {"status": COMPLETED, "seconds": 0.0, "skipped": "result exists", "peak_rss_bytes": 0}
        elif t.failed_path.is_file():
            out[t.label] = {"status": FAILED, "seconds": 0.0, "reason": "refused: a failed record exists; it is kept and the task is not re-run", "peak_rss_bytes": 0}
        else:
            pending.append(t)
    running: dict[str, tuple[Task, subprocess.Popen[bytes], psutil.Process, float, int]] = {}
    environment = {**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})}
    while pending or running:
        if time.monotonic() - begun > cap_seconds:
            for label, (task, popen, _, t0, peak) in list(running.items()):
                _kill(popen)
                out[label] = {"status": KILLED_CAP, "seconds": time.monotonic() - t0, "reason": f"stage cap of {cap_seconds:.0f} s reached", "peak_rss_bytes": peak}
                running.pop(label)
            for t in pending:
                out[t.label] = {"status": NOT_STARTED, "seconds": 0.0, "reason": "stage cap reached", "peak_rss_bytes": 0}
            pending = []
            break
        while pending and len(running) < workers:
            t = pending.pop(0)
            t.log_path.parent.mkdir(parents=True, exist_ok=True)
            with t.log_path.open("ab") as log:
                popen = subprocess.Popen(list(t.argv), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=environment)  # noqa: S603 - argument list, no shell
            running[t.label] = (t, popen, psutil.Process(popen.pid), time.monotonic(), 0)
        aggregate = 0
        for label in list(running):
            task, popen, proc, t0, peak = running[label]
            rss = _tree_rss(proc)
            peak = max(peak, rss)
            running[label] = (task, popen, proc, t0, peak)
            code = popen.poll()
            if code == IDENTITY_EXIT:
                out[label] = {"status": PAUSED_IDENTITY, "seconds": time.monotonic() - t0, "returncode": code, "peak_rss_bytes": peak, "reason": "PAUSED — IDENTITY: the worker refused on an identity or precondition check; restore the file or the state bit for bit and run the stage again (no failed record is kept)"}
                running.pop(label)
                continue
            if code is not None:
                ok = code == 0 and task.result_path.is_file()
                out[label] = {"status": COMPLETED if ok else FAILED, "seconds": time.monotonic() - t0, "returncode": code, "peak_rss_bytes": peak}
                if not ok:
                    out[label]["reason"] = f"exit status {code}" if code != 0 else "exit status 0 but no result file"
                    write_json(task.failed_path, {"label": label, "status": FAILED, "reason": out[label]["reason"], "returncode": code, "log": str(task.log_path), "utc": datetime.now(UTC).isoformat(), "note": "failed record kept; the task is not re-run"})
                running.pop(label)
                continue
            if rss > rss_worker_bytes:
                _kill(popen)
                out[label] = {"status": KILLED_RSS, "seconds": time.monotonic() - t0, "reason": f"process-tree RSS {rss} above the per-worker guard {rss_worker_bytes}", "peak_rss_bytes": peak}
                running.pop(label)
                continue
            aggregate += rss
        if aggregate > rss_aggregate_bytes and running:
            label = max(running, key=lambda k: running[k][4])
            task, popen, _, t0, peak = running.pop(label)
            _kill(popen)
            out[label] = {"status": KILLED_RSS, "seconds": time.monotonic() - t0, "reason": f"aggregate RSS {aggregate} above the guard {rss_aggregate_bytes}; the largest worker was stopped", "peak_rss_bytes": peak}
        if running or pending:
            time.sleep(poll)
    return out, time.monotonic() - begun


def stage_status(outcomes: dict[str, dict[str, Any]]) -> str:
    """COMPLETE when every task completed; FAILED if any failed (kept, not re-run); PAUSED if the only unfinished tasks stopped on a resource cap or on an identity refusal (PAUSED — IDENTITY)."""
    statuses = [o["status"] for o in outcomes.values()]
    if statuses and all(s == COMPLETED for s in statuses):
        return "COMPLETE"
    if any(s == FAILED for s in statuses):
        return "FAILED"
    return "PAUSED"


def manifest_path(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "manifest.json"


def read_manifest(run_dir: Path, stage: str) -> dict[str, Any] | None:
    p = manifest_path(run_dir, stage)
    return core.read_record(p, "stage_manifest") if p.is_file() else None


def write_manifest(run_dir: Path, stage: str, mode: str, outcomes: dict[str, dict[str, Any]], seconds: float, *, identity: dict[str, Any], started: str, caps: dict[str, float], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """The stage manifest: ``status`` COMPLETE, PAUSED or FAILED, the latest outcome of every task, and one ``history`` entry per invocation. A COMPLETE manifest is never rewritten."""
    prior = read_manifest(run_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        raise RuntimeError(f"{manifest_path(run_dir, stage)} is COMPLETE; a completed stage is never rewritten")
    tasks = dict(prior["tasks"]) if prior else {}
    tasks.update(outcomes)
    history = list(prior["history"]) if prior else []
    history.append({"started_utc": started, "finished_utc": datetime.now(UTC).isoformat(), "charged_seconds": seconds, "outcomes": {k: v["status"] for k, v in outcomes.items()}, "caps": caps})
    status = stage_status(tasks)
    record = {**core.envelope("stage_manifest"), "stage": stage, "mode": mode, "status": status, "tasks": tasks, "history": history, "charged_seconds": float(sum(h["charged_seconds"] for h in history)), "identity": identity, **(extra or {})}
    core.write_record(manifest_path(run_dir, stage), record, overwrite=True)
    return record


Worker = Callable[[Sequence[str]], int]
