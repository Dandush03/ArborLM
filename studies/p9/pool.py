# ruff: noqa: E501
"""P9 job manager (package I6): immutable task ids, stage manifests, worker semaphores, RSS and time
limits, failed records kept, and the dependent-cell stop rule in every stage.

Specification: ADR-0017 section 8.6 (study status; "A failed cell stops the launch of cells that depend
on it, in every stage, enforced by the job manager and tested -- the P8 deviation. Other lanes
continue. Nothing is re-run with changed settings."), 11 (resources: per-worker 3 GiB, aggregate
24 GiB, two to four training workers, four simulation workers). STUB: signatures only.

Model: a stage is a list of ``Task`` (one per cell and stage). A task is launched only when every task
it depends on has status ``completed``; a task whose dependency failed, was killed or was itself
skipped gets status ``skipped_dependency`` and is never launched; unrelated tasks (other lanes) run on.
Failed records are kept (``failed_path``), never overwritten or retried with changed settings.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .core import Cell, Identity, StageManifest

POLL_SECONDS = 0.1
GROUPS = ("train", "evaluate", "simulate", "analyze")


@dataclass(frozen=True)
class Task:
    """One immutable unit of work. ``task_id`` is ``task_id(stage, label, identity)``; ``depends_on``
    are labels of tasks of the SAME stage (training dependencies) and ``after`` are task ids of
    earlier stages that must be completed (for example the evaluation of a cell needs its training
    task). ``group`` selects the worker semaphore."""

    task_id: str
    stage: str
    label: str
    argv: tuple[str, ...]
    depends_on: tuple[str, ...]
    after: tuple[str, ...]
    group: str
    result_path: Path
    failed_path: Path
    log_path: Path


@dataclass
class TaskOutcome:
    label: str
    task_id: str
    status: str  # completed | failed | killed_rss | killed_cap | not_started | skipped_dependency
    returncode: int | None
    seconds: float
    peak_rss_bytes: int
    reason: str | None = None


@dataclass
class PoolResult:
    outcomes: list[TaskOutcome] = field(default_factory=list)
    wall_seconds: float = 0.0
    peak_aggregate_rss_bytes: int = 0
    cap_hit: bool = False

    @property
    def all_completed(self) -> bool:
        raise NotImplementedError


def task_id(stage: str, label: str, identity: Identity) -> str:
    """Immutable id: SHA-256 of the canonical JSON of ``(stage, label, identity)``."""
    raise NotImplementedError


def plan_stage(
    stage: str,
    cells: Sequence[Cell],
    run_dir: Path,
    identity: Identity,
    *,
    argv_for: Mapping[str, Sequence[str]],
    previous_stage_ids: Mapping[str, str] | None = None,
) -> list[Task]:
    """Build the tasks of ``stage`` for ``cells`` (labels from ``core``); ``depends_on`` is
    ``Cell.depends_on`` restricted to the cells in the plan; ``after`` comes from
    ``previous_stage_ids`` (label -> task id of the same cell's previous stage)."""
    raise NotImplementedError


def skipped_for_dependency(tasks: Sequence[Task], not_completed: Collection[str]) -> set[str]:
    """Labels that must not be launched because they (transitively, through ``depends_on``) depend on a
    label in ``not_completed`` (failed, killed, not started or skipped). Pure function; the stop rule
    of ADR 8.6, used by every stage and unit-tested on a synthetic dependency graph."""
    raise NotImplementedError


def run_stage(
    tasks: Sequence[Task],
    *,
    workers: Mapping[str, int],
    stage_cap_seconds: float,
    rss_worker_bytes: int,
    rss_aggregate_bytes: int,
    poll: float = POLL_SECONDS,
    env: Mapping[str, str] | None = None,
) -> PoolResult:
    """Run the tasks with at most ``workers[group]`` concurrent subprocesses per group. Launch a task
    only when its dependencies completed; kill a worker whose process-tree RSS exceeds the per-worker
    cap, the largest worker if the aggregate cap is exceeded, and everything at the stage cap; record
    every outcome (including ``skipped_dependency`` and ``not_started``)."""
    raise NotImplementedError


def build_manifest(
    stage: str,
    run_dir: Path,
    mode: str,
    identity: Identity,
    tasks: Sequence[Task],
    result: PoolResult,
    *,
    started_utc: str,
    finished_utc: str | None,
    workers: int,
    caps: Mapping[str, float],
) -> StageManifest:
    """The ``core.StageManifest`` of a stage: per-task records with result hashes, ``status`` COMPLETE
    only when every task completed, INCOMPLETE otherwise (the denominator is never reduced),
    ``skipped_for_dependency`` listing the labels never launched."""
    raise NotImplementedError


def write_manifest(run_dir: Path, manifest: StageManifest) -> Path:
    """Write ``<run>/manifest.json`` through ``core.write_record`` (kind ``stage_manifest``)."""
    raise NotImplementedError


def peak_rss_bytes() -> int:
    """Peak resident set size of this process in bytes."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
