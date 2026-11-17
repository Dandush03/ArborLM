# ruff: noqa: E501
"""P8 stage worker pool: one subprocess per cell, up to four in parallel, RSS and wall-time guarded.

Used by the evaluation and simulation stages (ADR-0015 section 11: single-threaded deterministic
workers, 2 GiB RSS per worker, 8 GiB aggregate, stage caps). Pure orchestration; no scientific value
is chosen here. A worker that fails or is killed leaves a ``*.failed.json`` record next to where its
result would have been; nothing is ever deleted or re-run with different parameters.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import os
import resource
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
import torch

from . import p8_core as core
from .io import write_json
from .records import utc_now


def peak_rss_bytes() -> int:
    """This process's peak resident set size (macOS reports bytes, Linux kilobytes)."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def determinism() -> dict[str, Any]:
    return {
        "threads_intra_op": torch.get_num_threads(),
        "threads_inter_op": torch.get_num_interop_threads(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "default_dtype": str(torch.get_default_dtype()),
        "device": "cpu",
        "single_thread": torch.get_num_threads() == 1,
    }


def require_freeze(dry_run: bool, freeze_commit: str | None) -> dict[str, Any] | None:
    """Registered stages need ``--freeze-commit`` and the same verification training uses
    (``p8_train.verify_freeze``: src/arborlm, config, spec, uv.lock, pyproject equal to their
    content at that commit). A dry run returns None."""
    if dry_run:
        return None
    from .p7b_core import GateError
    from .p8_train import FreezeError, verify_freeze

    if not freeze_commit:
        raise GateError("refused: a registered stage requires --freeze-commit")
    try:
        return verify_freeze(freeze_commit)
    except FreezeError as exc:
        raise GateError(f"refused: freeze verification failed: {exc}") from exc


@dataclass
class Job:
    label: str
    argv: list[str]
    result_path: Path  # the worker's own result file (eval.json / sim.json)
    failed_path: Path  # written by the pool on failure
    log_path: Path


@dataclass
class JobOutcome:
    label: str
    status: str  # completed | failed | killed_rss | killed_cap | not_started
    returncode: int | None
    seconds: float
    peak_rss_bytes: int
    reason: str | None = None


@dataclass
class PoolResult:
    outcomes: list[JobOutcome] = field(default_factory=list)
    wall_seconds: float = 0.0
    peak_aggregate_rss_bytes: int = 0
    cap_hit: bool = False

    @property
    def all_completed(self) -> bool:
        return bool(self.outcomes) and all(o.status == "completed" for o in self.outcomes)


def _tree_rss(process: psutil.Process) -> int:
    total = 0
    try:
        members = [process, *process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0
    for member in members:
        try:
            total += int(member.memory_info().rss)
        except psutil.NoSuchProcess:
            continue
    return total


def _kill(popen: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(popen.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    popen.wait()


def run_pool(
    jobs: list[Job],
    *,
    workers: int = core.WORKERS,
    cap_seconds: float,
    rss_worker: int = core.RSS_WORKER,
    rss_aggregate: int = core.RSS_AGGREGATE,
    poll: float = core.POLL_SECONDS,
    env: dict[str, str] | None = None,
) -> PoolResult:
    """Run ``jobs`` with at most ``workers`` concurrent subprocesses. Kills a worker whose process-tree
    RSS exceeds ``rss_worker``; kills the largest if the aggregate exceeds ``rss_aggregate``; kills
    everything and stops starting jobs when ``cap_seconds`` of wall time has passed."""
    started = time.monotonic()
    result = PoolResult()
    pending = list(jobs)
    running: dict[str, tuple[Job, subprocess.Popen[bytes], psutil.Process, float, int]] = {}
    environment = {**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})}

    def finish(label: str, status: str, reason: str | None) -> None:
        job, popen, _, begun, peak = running.pop(label)
        outcome = JobOutcome(
            label, status, popen.returncode, time.monotonic() - begun, peak, reason
        )
        result.outcomes.append(outcome)
        if status != "completed":
            write_json(
                job.failed_path,
                {
                    "label": label,
                    "status": status,
                    "reason": reason,
                    "returncode": popen.returncode,
                    "seconds": outcome.seconds,
                    "peak_process_tree_rss_bytes": peak,
                    "utc": utc_now(),
                    "note": "failed record kept; the cell is not re-run with changed parameters",
                },
            )

    while pending or running:
        elapsed = time.monotonic() - started
        if elapsed > cap_seconds and not result.cap_hit:
            result.cap_hit = True
            for label, (_, popen, _, _, _) in list(running.items()):
                _kill(popen)
                finish(label, "killed_cap", f"stage cap of {cap_seconds:.0f} s exceeded")
            for job in pending:
                result.outcomes.append(
                    JobOutcome(job.label, "not_started", None, 0.0, 0, "stage cap")
                )
                write_json(
                    job.failed_path,
                    {"label": job.label, "status": "not_started", "reason": "stage cap exceeded"},
                )
            pending = []
            break
        while pending and len(running) < workers:
            job = pending.pop(0)
            job.log_path.parent.mkdir(parents=True, exist_ok=True)
            with job.log_path.open("wb") as log:
                popen = subprocess.Popen(
                    job.argv,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=environment,
                )
            running[job.label] = (job, popen, psutil.Process(popen.pid), time.monotonic(), 0)
        aggregate = 0
        for label in list(running):
            job, popen, watched, begun, peak = running[label]
            rss = _tree_rss(watched)
            aggregate += rss
            peak = max(peak, rss)
            running[label] = (job, popen, watched, begun, peak)
            code = popen.poll()
            if code is not None:
                ok = code == 0 and job.result_path.is_file()
                finish(
                    label, "completed" if ok else "failed", None if ok else f"exit status {code}"
                )
            elif rss > rss_worker:
                _kill(popen)
                finish(label, "killed_rss", f"process-tree RSS {rss} above {rss_worker}")
        result.peak_aggregate_rss_bytes = max(result.peak_aggregate_rss_bytes, aggregate)
        if aggregate > rss_aggregate and running:
            label = max(running, key=lambda k: running[k][4])
            _kill(running[label][1])
            finish(label, "killed_rss", f"aggregate RSS {aggregate} above {rss_aggregate}")
        time.sleep(poll)
    result.wall_seconds = time.monotonic() - started
    return result
