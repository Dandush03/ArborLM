# ruff: noqa: E501
"""P9 job manager (package I6): immutable task ids, stage manifests, worker semaphores, RSS and time
limits, failed records kept, and the dependent-cell stop rule in every stage.

Specification: ADR-0017 section 8.6 (study status; "A failed cell stops the launch of cells that depend
on it, in every stage, enforced by the job manager and tested -- the P8 deviation. Other lanes
continue. Nothing is re-run with changed settings."), 11 (resources: per-worker 3 GiB, aggregate
24 GiB, two to four training workers, four simulation workers).

Model: a stage is a list of ``Task`` (one per cell and stage). A task is launched only when every task
it depends on has status ``completed``; a task whose dependency failed, was killed or was itself
skipped gets status ``skipped_dependency`` and is never launched; unrelated tasks (other lanes) run on.
Failed records are kept (``failed_path``), never overwritten or retried with changed settings. A task
whose failed or result file already exists is refused, not re-run.

Workers are subprocesses invoked as ``python -m studies.p9.<module> ...`` from an argument list; no
shell is involved, so there is no word splitting. This module only orchestrates: it chooses no
scientific value. Sampled RSS is the process-tree RSS (as ``arborlm.p8_pool``).

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import argparse
import json
import os
import resource
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from arborlm.io import canonical_json, file_sha256, sha256, write_json

from . import core
from .core import Cell, Identity, StageManifest, TaskRecord

POLL_SECONDS = 0.1
GROUPS = ("train", "evaluate", "simulate", "analyze")
STAGE_GROUP: dict[str, str] = {
    "generate": "analyze",  # integration additions: stages.py drives these through the same manager
    "gates": "train",
    "report": "analyze",
    "calibrate": "train",
    "rehearse": "train",
    "train": "train",
    "incremental": "train",
    "evaluate": "evaluate",
    "simulate": "simulate",
    "analyze": "analyze",
}
TRAINING_STAGES = ("train", "incremental")  # stages whose tasks are cell trainings
TASK_STATUSES = (
    "completed",
    "failed",
    "killed_rss",
    "killed_cap",
    "not_started",
    "skipped_dependency",
)
REGISTERED = "registered"
MODES = (REGISTERED, "calibration", "rehearsal")


class StageRefused(RuntimeError):
    """A stage refused to start (dirty tree, missing or wrong freeze, bad worker count, ...)."""


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
        return bool(self.outcomes) and all(o.status == "completed" for o in self.outcomes)


@dataclass
class WallBudget:
    """The total wall-time cap across stages: each stage is run with ``min(stage cap, remaining)`` and
    charged what it used. ``total_seconds`` is fixed at the second human decision, not here."""

    total_seconds: float
    used_seconds: float = 0.0

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.used_seconds)

    def charge(self, seconds: float) -> None:
        self.used_seconds += max(0.0, seconds)


@dataclass(frozen=True)
class StageCaps:
    """Caps of one stage run (recorded in the manifest)."""

    stage_seconds: float
    rss_worker_bytes: int = core.RSS_WORKER_BYTES
    rss_aggregate_bytes: int = core.RSS_AGGREGATE_BYTES
    total_seconds: float | None = None

    def as_dict(self) -> dict[str, float]:
        out: dict[str, float] = {
            "stage_seconds": float(self.stage_seconds),
            "rss_worker_bytes": float(self.rss_worker_bytes),
            "rss_aggregate_bytes": float(self.rss_aggregate_bytes),
        }
        if self.total_seconds is not None:
            out["total_seconds"] = float(self.total_seconds)
        return out


# --- identity ------------------------------------------------------------------------------------------
def task_id(stage: str, label: str, identity: Identity) -> str:
    """Immutable id: SHA-256 of the canonical JSON of ``(stage, label, identity)``."""
    return sha256(canonical_json([stage, label, dict(identity)]))


def worker_argv(module: str, *args: str, python: str | None = None) -> list[str]:
    """``[python, "-m", "studies.p9.<module>", *args]``: the only worker command shape (no shell)."""
    if not module or not module.replace("_", "").isalnum():
        raise ValueError(f"not a P9 worker module name: {module!r}")
    return [python or sys.executable, "-m", f"studies.p9.{module}", *args]


def validate_worker_argv(argv: Sequence[str]) -> None:
    """Refuse an argument list that is not ``<python> -m studies.p9.<module> ...``."""
    if len(argv) < 3 or argv[1] != "-m" or not argv[2].startswith("studies.p9."):
        raise ValueError(
            f"worker argv must be '<python> -m studies.p9.<module> ...': {list(argv)[:3]}"
        )
    if not all(isinstance(a, str) for a in argv):
        raise ValueError("worker argv must be strings")


def _stage_paths(stage: str, run_dir: Path, label: str) -> tuple[Path, Path, Path]:
    cell = core.cell_dir(run_dir, label)
    result = cell / ("train.json" if stage in TRAINING_STAGES else f"{stage}.json")
    return result, cell / f"{stage}.failed.json", cell / f"{stage}.log"


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
    if stage not in STAGE_GROUP:
        raise ValueError(f"unknown P9 stage {stage!r}")
    labels = [c.label for c in cells]
    if len(set(labels)) != len(labels):
        raise ValueError("a stage plan may name a cell once")
    planned = set(labels)
    tasks: list[Task] = []
    for cell in cells:
        if cell.label not in argv_for:
            raise ValueError(f"no worker command for {cell.label}")
        argv = tuple(argv_for[cell.label])
        validate_worker_argv(argv)
        result, failed, log = _stage_paths(stage, run_dir, cell.label)
        after = (previous_stage_ids or {}).get(cell.label)
        tasks.append(
            Task(
                task_id=task_id(stage, cell.label, identity),
                stage=stage,
                label=cell.label,
                argv=argv,
                depends_on=tuple(d for d in cell.depends_on if d in planned),
                after=(after,) if after else (),
                group=STAGE_GROUP[stage],
                result_path=result,
                failed_path=failed,
                log_path=log,
            )
        )
    return tasks


def skipped_for_dependency(tasks: Sequence[Task], not_completed: Collection[str]) -> set[str]:
    """Labels that must not be launched because they (transitively, through ``depends_on``) depend on a
    label in ``not_completed`` (failed, killed, not started or skipped). Pure function; the stop rule
    of ADR 8.6, used by every stage and unit-tested on a synthetic dependency graph. A dependency that
    names no task of ``tasks`` is only unsatisfied if it is itself in ``not_completed``."""
    bad = set(not_completed)
    deps = {t.label: t.depends_on for t in tasks}
    skipped: set[str] = set()
    changed = True
    while changed:
        changed = False
        for label, parents in deps.items():
            if label in skipped:
                continue
            if any(p in bad or p in skipped for p in parents):
                skipped.add(label)
                changed = True
    return skipped


def peak_rss_bytes() -> int:
    """Peak resident set size of this process in bytes (macOS reports bytes, Linux kilobytes)."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


# --- the run loop ---------------------------------------------------------------------------------------
def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _tree_rss(process: psutil.Process) -> int:
    total = 0
    try:
        members = [process, *process.children(recursive=True)]
    except psutil.Error:
        return 0
    for member in members:
        try:
            total += int(member.memory_info().rss)
        except psutil.Error:
            continue
    return total


def _kill(popen: "subprocess.Popen[bytes]") -> None:
    try:
        os.killpg(popen.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    popen.wait()


@dataclass
class _Running:
    task: Task
    popen: "subprocess.Popen[bytes]"
    watched: psutil.Process
    begun: float
    peak: int = 0
    rss: int = 0


def run_stage(
    tasks: Sequence[Task],
    *,
    workers: Mapping[str, int],
    stage_cap_seconds: float,
    rss_worker_bytes: int,
    rss_aggregate_bytes: int,
    poll: float = POLL_SECONDS,
    env: Mapping[str, str] | None = None,
    completed_ids: Collection[str] = (),
    total_remaining_seconds: float | None = None,
) -> PoolResult:
    """Run the tasks with at most ``workers[group]`` concurrent subprocesses per group. Launch a task
    only when its dependencies completed; kill a worker whose process-tree RSS exceeds the per-worker
    cap, the largest worker if the aggregate cap is exceeded, and everything at the stage cap (or the
    remaining total cap, whichever is smaller); record every outcome (including ``skipped_dependency``
    and ``not_started``). ``completed_ids`` are the ids of earlier-stage tasks known to be completed:
    a task whose ``after`` is not covered is skipped, never launched (fail closed). A task whose
    failed or result file already exists is refused (failed, reason says so), never re-run."""
    labels = [t.label for t in tasks]
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate task labels in a stage")
    for t in tasks:
        if workers.get(t.group, 0) < 1:
            raise ValueError(f"no worker slots configured for group {t.group!r} (task {t.label})")
    cap = (
        stage_cap_seconds
        if total_remaining_seconds is None
        else min(stage_cap_seconds, total_remaining_seconds)
    )
    cap_reason = (
        f"stage cap of {stage_cap_seconds:.0f} s exceeded"
        if total_remaining_seconds is None or stage_cap_seconds <= total_remaining_seconds
        else f"total wall-time cap exceeded (remaining {total_remaining_seconds:.0f} s at stage start)"
    )
    known_done = set(completed_ids)
    started = time.monotonic()
    result = PoolResult()
    pending: list[Task] = list(tasks)
    running: dict[str, _Running] = {}
    done: dict[str, str] = {}  # label -> status
    environment = {**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})}

    def record(
        task: Task,
        status: str,
        reason: str | None,
        *,
        code: int | None = None,
        seconds: float = 0.0,
        peak: int = 0,
        write: bool = True,
    ) -> None:
        done[task.label] = status
        result.outcomes.append(
            TaskOutcome(task.label, task.task_id, status, code, seconds, peak, reason)
        )
        if status != "completed" and write and not task.failed_path.exists():
            task.failed_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(
                task.failed_path,
                {
                    "label": task.label,
                    "task_id": task.task_id,
                    "stage": task.stage,
                    "status": status,
                    "reason": reason,
                    "returncode": code,
                    "seconds": seconds,
                    "peak_process_tree_rss_bytes": peak,
                    "utc": _utc(),
                    "note": "failed record kept; the task is not re-run with changed parameters",
                },
            )

    def finish(label: str, status: str, reason: str | None) -> None:
        run = running.pop(label)
        record(
            run.task,
            status,
            reason,
            code=run.popen.returncode,
            seconds=time.monotonic() - run.begun,
            peak=run.peak,
        )

    def refuse_pending(status: str, reason: str) -> None:
        for task in list(pending):
            pending.remove(task)
            record(task, status, reason)

    while pending or running:
        elapsed = time.monotonic() - started
        if elapsed > cap and not result.cap_hit:
            result.cap_hit = True
            for label in list(running):
                _kill(running[label].popen)
                finish(label, "killed_cap", cap_reason)
            refuse_pending("not_started", "stage cap")
            break

        # unsatisfied upstream stage tasks and refused leftovers
        for task in list(pending):
            missing_after = [a for a in task.after if a not in known_done]
            if missing_after:
                pending.remove(task)
                record(
                    task,
                    "skipped_dependency",
                    f"upstream-stage task not completed: {missing_after[0][:12]}",
                )
            elif task.failed_path.exists() or task.result_path.exists():
                pending.remove(task)
                which = "failed record" if task.failed_path.exists() else "result"
                record(
                    task,
                    "failed",
                    f"refused: a {which} already exists for this task; it is never re-run or overwritten",
                    write=False,
                )

        # the dependent-cell stop rule (ADR 8.6): transitive, applied before every launch
        in_plan = {t.label for t in tasks}
        bad = {label for label, status in done.items() if status != "completed"}
        unknown = {d for t in pending for d in t.depends_on if d not in in_plan and d not in done}
        skip = skipped_for_dependency(tasks, bad | unknown)
        for task in list(pending):
            if task.label in skip:
                pending.remove(task)
                culprit = next(
                    (d for d in task.depends_on if d in bad or d in skip or d in unknown), "?"
                )
                record(task, "skipped_dependency", f"dependency {culprit} did not complete")

        launched = 0
        for task in list(pending):
            if not all(done.get(d) == "completed" for d in task.depends_on):
                continue
            if (
                sum(1 for r in running.values() if r.task.group == task.group)
                >= workers[task.group]
            ):
                continue
            pending.remove(task)
            task.log_path.parent.mkdir(parents=True, exist_ok=True)
            task.result_path.parent.mkdir(parents=True, exist_ok=True)
            with task.log_path.open("wb") as log:
                popen = subprocess.Popen(  # noqa: S603 - argument list, no shell
                    list(task.argv),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=environment,
                )
            running[task.label] = _Running(task, popen, psutil.Process(popen.pid), time.monotonic())
            launched += 1

        aggregate = 0
        for label in list(running):
            run = running[label]
            run.rss = _tree_rss(run.watched)
            run.peak = max(run.peak, run.rss)
            code = run.popen.poll()
            if code is not None:
                ok = code == 0 and run.task.result_path.is_file()
                reason = (
                    None
                    if ok
                    else (
                        f"exit status {code}" if code != 0 else "exit status 0 but no result file"
                    )
                )
                finish(label, "completed" if ok else "failed", reason)
                continue
            if run.rss > rss_worker_bytes:
                _kill(run.popen)
                finish(
                    label,
                    "killed_rss",
                    f"process-tree RSS {run.rss} above per-worker cap {rss_worker_bytes}",
                )
                continue
            aggregate += run.rss
        result.peak_aggregate_rss_bytes = max(result.peak_aggregate_rss_bytes, aggregate)
        if aggregate > rss_aggregate_bytes and running:
            label = max(running, key=lambda k: running[k].rss)
            _kill(running[label].popen)
            finish(
                label,
                "killed_rss",
                f"aggregate RSS {aggregate} above cap {rss_aggregate_bytes}; largest worker killed",
            )

        if (
            pending
            and not running
            and not launched
            and not any(all(done.get(d) == "completed" for d in t.depends_on) for t in pending)
        ):
            # nothing can ever start (dependencies outside the plan that never complete)
            refuse_pending("skipped_dependency", "dependency never completes within this stage")
            break
        if running or pending:
            time.sleep(poll)
    result.wall_seconds = time.monotonic() - started
    return result


# --- manifests --------------------------------------------------------------------------------------------
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
    by_label = {o.label: o for o in result.outcomes}
    records: list[TaskRecord] = []
    for task in tasks:
        outcome = by_label.get(task.label)
        if outcome is None:
            outcome = TaskOutcome(
                task.label, task.task_id, "not_started", None, 0.0, 0, "no outcome recorded"
            )
        path = task.result_path
        completed = outcome.status == "completed" and path.is_file()
        records.append(
            TaskRecord(
                label=task.label,
                task_id=task.task_id,
                status=outcome.status,
                returncode=outcome.returncode,
                seconds=float(outcome.seconds),
                peak_rss_bytes=int(outcome.peak_rss_bytes),
                reason=outcome.reason,
                depends_on=list(task.depends_on),
                result_path=str(path) if completed else None,
                result_sha256=file_sha256(path) if completed else None,
            )
        )
    every_task_completed = bool(records) and all(r["status"] == "completed" for r in records)
    return StageManifest(
        kind="stage_manifest",
        schema=core.SCHEMA,
        study=core.STUDY,
        stage=stage,
        run_id=run_dir.name,
        mode=mode,
        started_utc=started_utc,
        finished_utc=finished_utc,
        identity=identity,
        workers=workers,
        caps=dict(caps),
        tasks=records,
        status="COMPLETE" if every_task_completed else "INCOMPLETE",
        skipped_for_dependency=[r["label"] for r in records if r["status"] == "skipped_dependency"],
    )


def write_manifest(run_dir: Path, manifest: StageManifest) -> Path:
    """Write ``<run>/manifest.json`` through ``core.write_record`` (kind ``stage_manifest``)."""
    path = run_dir / "manifest.json"
    core.write_record(path, dict(manifest))
    return path


# --- preconditions of a registered stage --------------------------------------------------------------------
def _git_text(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)  # noqa: S603, S607
    if done.returncode != 0:
        raise StageRefused(f"git {' '.join(args)} failed: {done.stderr.decode().strip()}")
    return done.stdout.decode().strip()


def _git_ok(repo: Path, *args: str) -> bool:
    return (
        subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False).returncode
        == 0
    )  # noqa: S603, S607


FrozenVerifier = Callable[[Path, str], Mapping[str, Any]]


def _default_verifier(repo: Path, commit: str) -> Mapping[str, Any]:
    return core.frozen_input_check(repo, commit)


def check_preconditions(
    mode: str,
    repo: Path,
    freeze_commit: str | None,
    *,
    verify_frozen: FrozenVerifier = _default_verifier,
) -> dict[str, str] | None:
    """A ``registered`` stage refuses unless: the working tree is clean (no staged, unstaged or
    untracked non-ignored change); ``freeze_commit`` names a commit that is an ancestor of HEAD; the
    P9 package, the config, the specification and every ``tests/test_p9_*.py`` equal their content at
    that commit; and ``core.frozen_input_check`` (src/arborlm, uv.lock, pyproject.toml, P8 digest)
    reports ok. Returns the freeze identity, or None for a calibration or rehearsal stage."""
    if mode not in MODES:
        raise StageRefused(f"unknown mode {mode!r}")
    if mode != REGISTERED:
        return None
    dirty = _git_text(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise StageRefused(
            "refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10])
        )
    if not freeze_commit:
        raise StageRefused("refused: a registered stage requires --freeze-commit")
    if not _git_ok(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}"):
        raise StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = _git_text(repo, "rev-parse", f"{freeze_commit}^{{commit}}")
    if not _git_ok(repo, "merge-base", "--is-ancestor", full, "HEAD"):
        raise StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems: list[str] = []
    for path in ("studies", str(core.DEFAULT_CONFIG), core.SPEC):
        frozen_obj = (
            _git_text(repo, "rev-parse", "--verify", f"{full}:{path}")
            if _git_ok(repo, "cat-file", "-e", f"{full}:{path}")
            else None
        )
        head_obj = (
            _git_text(repo, "rev-parse", "--verify", f"HEAD:{path}")
            if _git_ok(repo, "cat-file", "-e", f"HEAD:{path}")
            else None
        )
        if frozen_obj != head_obj:
            problems.append(f"{path} at HEAD differs from the freeze commit")

    def tests_at(rev: str) -> dict[str, str]:
        listing = (
            _git_text(repo, "ls-tree", rev, "tests/")
            if _git_ok(repo, "cat-file", "-e", f"{rev}:tests")
            else ""
        )
        out: dict[str, str] = {}
        for line in listing.splitlines():
            meta, _, name = line.partition("\t")
            if name.startswith("tests/test_p9_"):
                out[name] = meta.split()[2]
        return out

    if tests_at(full) != tests_at("HEAD"):
        problems.append("the tests/test_p9_*.py files at HEAD differ from the freeze commit")
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    verification = verify_frozen(repo, full)
    if not verification.get("ok"):
        raise StageRefused(
            "refused: frozen inputs do not verify: "
            + "; ".join(map(str, list(verification.get("problems", []))[:5]))
        )
    return {"commit": full, "tree": _git_text(repo, "rev-parse", f"{full}^{{tree}}")}


def validate_workers(mode: str, workers: Mapping[str, int]) -> None:
    """Registered runs use 2-4 training workers and at most four simulation workers (ADR 11)."""
    if mode != REGISTERED:
        return
    low, high = core.TRAINING_WORKERS_RANGE
    train = workers.get("train", 0)
    if not low <= train <= high:
        raise StageRefused(f"refused: {train} training workers; ADR 11 allows {low} to {high}")
    if workers.get("simulate", 0) > core.SIMULATION_WORKERS:
        raise StageRefused(f"refused: more than {core.SIMULATION_WORKERS} simulation workers")


def completed_ids_from(manifests: Sequence[Mapping[str, Any]]) -> set[str]:
    """Task ids with status ``completed`` in earlier stage manifests (the ``after`` check)."""
    return {
        t["task_id"]
        for m in manifests
        for t in m.get("tasks", [])
        if t.get("status") == "completed"
    }


def execute_stage(
    stage: str,
    mode: str,
    cells: Sequence[Cell],
    run_dir: Path,
    identity: Identity,
    *,
    argv_for: Mapping[str, Sequence[str]],
    repo: Path,
    freeze_commit: str | None,
    workers: Mapping[str, int],
    caps: StageCaps,
    previous_stage_ids: Mapping[str, str] | None = None,
    completed_ids: Collection[str] = (),
    budget: WallBudget | None = None,
    env: Mapping[str, str] | None = None,
    poll: float = POLL_SECONDS,
    verify_frozen: FrozenVerifier = _default_verifier,
    manifest_dir: Path | None = None,
) -> tuple[StageManifest, Path]:
    """One stage, end to end: refuse (dirty tree, missing or wrong freeze, wrong worker count, an existing
    manifest) before anything is created; plan; run under the caps; write the manifest (also when tasks
    failed). ``manifest_dir`` (integration addition) is where ``manifest.json`` is written (default
    ``run_dir``): stages that share one cell directory write one manifest each, to ``<run>/<stage>/``."""
    check_preconditions(mode, repo, freeze_commit, verify_frozen=verify_frozen)
    validate_workers(mode, workers)
    tasks = plan_stage(
        stage, cells, run_dir, identity, argv_for=argv_for, previous_stage_ids=previous_stage_ids
    )
    return execute_tasks(
        stage,
        mode,
        tasks,
        run_dir,
        identity,
        workers=workers,
        caps=caps,
        completed_ids=completed_ids,
        budget=budget,
        env=env,
        poll=poll,
        manifest_dir=manifest_dir,
    )


def execute_tasks(
    stage: str,
    mode: str,
    tasks: Sequence[Task],
    run_dir: Path,
    identity: Identity,
    *,
    workers: Mapping[str, int],
    caps: StageCaps,
    completed_ids: Collection[str] = (),
    budget: WallBudget | None = None,
    env: Mapping[str, str] | None = None,
    poll: float = POLL_SECONDS,
    manifest_dir: Path | None = None,
) -> tuple[StageManifest, Path]:
    """Run planned tasks under the caps and write the stage manifest (never over an existing one).
    Preconditions of a registered stage are checked by the caller (``execute_stage`` or ``stages``)."""
    target = (manifest_dir or run_dir) / "manifest.json"
    if target.exists():
        raise StageRefused(f"refused: {target} already exists; a stage is run once and never overwritten")
    run_dir.mkdir(parents=True, exist_ok=True)
    started = _utc()
    result = run_stage(
        tasks,
        workers=workers,
        stage_cap_seconds=caps.stage_seconds,
        rss_worker_bytes=caps.rss_worker_bytes,
        rss_aggregate_bytes=caps.rss_aggregate_bytes,
        poll=poll,
        env=env,
        completed_ids=completed_ids,
        total_remaining_seconds=budget.remaining() if budget is not None else caps.total_seconds,
    )
    if budget is not None:
        budget.charge(result.wall_seconds)
    manifest = build_manifest(
        stage,
        run_dir,
        mode,
        identity,
        tasks,
        result,
        started_utc=started,
        finished_utc=_utc(),
        workers=int(workers.get(STAGE_GROUP[stage], 0)),
        caps=caps.as_dict(),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    core.write_record(target, dict(manifest))
    return manifest, target


# --- command line -------------------------------------------------------------------------------------------
def _plan_listing(stage: str, blocks: Sequence[str] | None) -> list[dict[str, Any]]:
    selected = [c for c in core.cells() if not blocks or c.block in blocks]
    labels = {c.label for c in selected}
    return [
        {
            "label": c.label,
            "block": c.block,
            "depends_on": [d for d in c.depends_on if d in labels],
            "group": STAGE_GROUP[stage],
        }
        for c in selected
    ]


def main(argv: list[str] | None = None) -> int:
    """``python -m studies.p9.pool plan --stage S [--block B ...]`` prints the dependency plan (no
    execution). ``run`` executes a stage: ``--module M --arg A ...`` builds the worker command
    ``python -m studies.p9.M A ...`` for every cell (``{label}`` and ``{run_dir}`` are substituted in
    each ``--arg``); it needs ``--freeze-commit`` for ``--mode registered``."""
    parser = argparse.ArgumentParser(prog="python -m studies.p9.pool")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--stage", required=True, choices=sorted(STAGE_GROUP))
    plan.add_argument("--block", action="append", default=None)
    run = sub.add_parser("run")
    run.add_argument("--stage", required=True, choices=sorted(STAGE_GROUP))
    run.add_argument("--mode", required=True, choices=MODES)
    run.add_argument("--block", action="append", default=None)
    run.add_argument("--module", required=True)
    run.add_argument("--arg", action="append", default=[])
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--freeze-commit", default=None)
    run.add_argument("--train-workers", type=int, default=2)
    run.add_argument("--sim-workers", type=int, default=core.SIMULATION_WORKERS)
    run.add_argument("--stage-cap-seconds", type=float, required=True)
    run.add_argument("--rss-worker-bytes", type=int, default=core.RSS_WORKER_BYTES)
    run.add_argument("--rss-aggregate-bytes", type=int, default=core.RSS_AGGREGATE_BYTES)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "plan":
        print(json.dumps(_plan_listing(args.stage, args.block), indent=1))
        return 0
    selected = [c for c in core.cells() if not args.block or c.block in args.block]
    argv_for = {
        c.label: worker_argv(
            args.module, *[a.format(label=c.label, run_dir=str(args.run_dir)) for a in args.arg]
        )
        for c in selected
    }
    workers = {
        "train": args.train_workers,
        "evaluate": args.train_workers,
        "simulate": args.sim_workers,
        "analyze": 1,
    }
    try:
        manifest, path = execute_stage(
            args.stage,
            args.mode,
            selected,
            args.run_dir,
            core.code_identity(),
            argv_for=argv_for,
            repo=core.repo_root(),
            freeze_commit=args.freeze_commit,
            workers=workers,
            caps=StageCaps(args.stage_cap_seconds, args.rss_worker_bytes, args.rss_aggregate_bytes),
            env={"PYTHONPATH": str(core.repo_root())},
        )
    except StageRefused as exc:
        print(f"P9 stage REFUSED: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"status": manifest["status"], "tasks": len(manifest["tasks"]), "manifest": str(path)},
            indent=1,
        )
    )
    return 0 if manifest["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
