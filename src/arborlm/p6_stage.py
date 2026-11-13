"""Stage orchestration shared by the P6-E equivalence, T-screen and T-confirm stages.

A stage owns a fresh run directory under ``--output-root`` (never overwritten), a compact
mirror under ``--results-root``, a manifest, a terminal record and one supervised subprocess
worker per parent/seed. Wall-time and RSS caps are enforced with the existing watchdog; a breach
stops the stage and preserves partial and unexecuted records.

Status: SPEC: HUMAN-APPROVED (ADR-0011); implementation self-checked only.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from .io import file_sha256, read_json, write_json
from .p5_clock import SuiteRSS
from .p6_common import FAMILY, KNOWN_LIMITS, SPEC, Pair, StageBudget, pair_label
from .records import allocate_run, record_environment, record_source, utc_now
from .watchdog import RSS_BYTES, supervise

STAGES = {
    # name: (run prefix, stage cap seconds, per-worker cap seconds or None)
    "equivalence": ("P6EEQ", 1200.0, None),
    "screen": ("P6ESCR", 1200.0, 90.0),
    "confirm": ("P6ECON", 600.0, 45.0),
    "analysis": ("P6EANA", 0.0, None),
}
WORKER_PREFIX = {"equivalence": "P6EQW", "screen": "P6SCW", "confirm": "P6CNW"}
SEED_NOTE = {
    "P5_checkpoints": "restored, not re-seeded",
    "fixture_seed": 91001,
    "torch_default_seed_configure_cpu": 42,
    "note": "no training; fixture and synthetic-fixture seeds are implementer choices",
}


def p6_source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {f"src/arborlm/{p.name}": file_sha256(p) for p in sorted(root.glob("p6_*.py"))}


def source_expectations(context: "StageContext") -> dict[str, Any]:
    """What every worker of the stage must still see at its end (archive and p6 source hashes)."""
    return {
        "source_archive_sha256": context.manifest["source_archive_sha256"],
        "p6_source_sha256": context.manifest["p6_source_sha256"],
    }


def verify_source_unchanged(run: Path, expected: dict[str, Any]) -> dict[str, Any]:
    """Re-hash the source archive allowlist and the p6 modules; stop on any difference.

    Same technique as the earlier studies: the archive is rebuilt in a scratch folder inside the
    worker's run folder, so no recorded evidence is rewritten.
    """
    with tempfile.TemporaryDirectory(prefix=".verify-source-", dir=run) as scratch:
        snapshot = record_source(Path(scratch), Path.cwd(), spec=SPEC)
    archive = str(snapshot["archive"]["sha256"])
    p6 = p6_source_hashes()
    if archive != expected["source_archive_sha256"] or p6 != expected["p6_source_sha256"]:
        raise ValueError("P6 stop: the source archive or a p6 module changed during the worker")
    return {"archive_sha256": archive, "p6_sources_unchanged": True, "archive_unchanged": True}


def git_head() -> tuple[str, bool]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    return head, dirty


def environment_details(run: Path) -> dict[str, Any]:
    env = record_environment(run, family=FAMILY)
    clock = time.get_clock_info("perf_counter")
    # Packages list is already in ``env``; thread and clock facts are what P6 timing needs.
    return {
        **{k: v for k, v in env.items() if k != "packages"},
        "torch": torch.__version__,
        "torch_packages": {k: v for k, v in env["packages"].items() if k in ("torch", "psutil")},
        "torch_config_show": torch.__config__.show(),
        "torch_parallel_info": torch.__config__.parallel_info(),
        "threads": {
            "intra_op": torch.get_num_threads(),
            "inter_op": torch.get_num_interop_threads(),
        },
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "clock": {
            "implementation": clock.implementation,
            "resolution_ns": clock.resolution * 1e9,
            "monotonic": clock.monotonic,
            "adjustable": clock.adjustable,
        },
        "platform": platform.platform(),
    }


@dataclass
class StageContext:
    stage: str
    run: Path
    compact: Path
    manifest: dict[str, Any]
    started: float = field(default_factory=time.monotonic)

    def write_manifest(self) -> None:
        write_json(self.run / "manifest.json", self.manifest)
        write_json(self.compact / "manifest.json", self.manifest)


def prior_runs(results_root: Path, stage: str) -> list[str]:
    """Names of earlier non-dry-run runs of ``stage`` (completed, failed or unreadable)."""
    found = []
    for directory in sorted((results_root / stage).glob("*")):
        if not directory.is_dir():
            continue
        try:
            dry = bool(read_json(directory / "manifest.json").get("dry_run"))
        except (OSError, ValueError):
            dry = False  # an unreadable run still counts as a run
        if not dry:
            found.append(directory.name)
    return found


def check_rerun(
    results_root: Path,
    stage: str,
    supersede: str | None,
    reason: str | None,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    """Single registered invocation per stage: a second non-dry-run run needs a recorded reason."""
    if dry_run:
        if supersede is not None:
            raise ValueError("--supersede is not meaningful for a dry run")
        return None
    existing = prior_runs(results_root, stage)
    if supersede is None:
        if existing:
            raise ValueError(
                f"refusing to run {stage} again: earlier run(s) {existing} exist under "
                f"{results_root / stage}; a deliberate rerun needs "
                "--supersede <run-id> --reason <text>"
            )
        return None
    if not reason or not reason.strip():
        raise ValueError("--supersede requires a non-empty --reason")
    if supersede not in existing:
        raise ValueError(f"--supersede {supersede!r} is not an earlier {stage} run: {existing}")
    return {"run_id": supersede, "reason": reason, "earlier_runs": existing}


def open_stage(
    stage: str,
    *,
    output_root: Path,
    results_root: Path,
    argv: list[str],
    arguments: dict[str, Any],
    dry_run: bool = False,
    supersede: str | None = None,
    supersede_reason: str | None = None,
) -> StageContext:
    prefix, cap, worker_cap = STAGES[stage]
    superseded = check_rerun(results_root, stage, supersede, supersede_reason, dry_run=dry_run)
    run = allocate_run(output_root, prefix=prefix + ("D" if dry_run else ""))
    compact = results_root / stage / run.name
    compact.mkdir(parents=True, exist_ok=False)  # refuses to overwrite
    source = record_source(run, Path.cwd(), spec=SPEC)
    head, dirty = git_head()
    manifest = {
        "schema_version": 1,
        "experiment_family": FAMILY,
        "stage": stage,
        "run_id": run.name,
        "dry_run": dry_run,
        "command": argv,
        "arguments": arguments,
        "git_head": head,
        "git_dirty": dirty,
        "source_archive_sha256": source["archive"]["sha256"],
        "p6_source_sha256": p6_source_hashes(),
        "spec_reference": SPEC,
        "spec_sha256": source["spec_sha256"],
        "lock_sha256": source["lock_sha256"],
        "environment": environment_details(run),
        "seeds": SEED_NOTE,
        "supersedes": superseded,
        "known_limits": list(KNOWN_LIMITS),
        "caps": {
            "stage_seconds": cap,
            "worker_seconds": worker_cap,
            "rss_bytes": RSS_BYTES,
        },
        "start_utc": utc_now(),
        "end_utc": None,
        "status": "running",
        "reason": None,
        "astra_review": "NOT_PERFORMED",
    }
    context = StageContext(stage, run, compact, manifest)
    context.write_manifest()
    return context


def finish_stage(
    context: StageContext, status: str, reason: str | None, result: dict[str, Any]
) -> None:
    context.manifest.update(
        end_utc=utc_now(),
        status=status,
        reason=reason,
        wall_seconds=time.monotonic() - context.started,
    )
    write_json(context.run / "result.json", {**result, "status": status, "reason": reason})
    write_json(context.compact / "result.json", {**result, "status": status, "reason": reason})
    write_json(context.run / "terminal.json", {"status": status, "reason": reason})
    context.write_manifest()


@dataclass
class WorkerOutcome:
    rows: list[dict[str, Any]]
    status: str
    reason: str | None
    peak_rss_bytes: int
    wall_seconds: float


def run_worker_stage(
    context: StageContext,
    pair_list: list[Pair],
    *,
    argv_for: Callable[[Pair, Path], list[str]],
    cap_seconds: float | None = None,
    worker_cap_seconds: float | None = None,
    after_worker: Callable[[Pair, Path], None] | None = None,
) -> WorkerOutcome:
    """Run one supervised worker per pair, sequentially, under the stage caps."""
    _, cap, worker_cap = STAGES[context.stage]
    budget = StageBudget(cap_seconds or cap, worker_cap_seconds or worker_cap)
    workers_dir = context.compact / "workers"
    workers_dir.mkdir(exist_ok=True)
    rows: list[dict[str, Any]] = [
        {"label": pair_label(p), "pair": list(p), "status": "unexecuted", "run_id": None}
        for p in pair_list
    ]

    def persist() -> None:
        write_json(context.run / "workers.json", {"workers": rows, "elapsed": budget.elapsed()})
        write_json(context.compact / "workers.json", {"workers": rows, "elapsed": budget.elapsed()})

    persist()
    reason: str | None = None
    with SuiteRSS() as rss:
        try:
            for row, pair in zip(rows, pair_list, strict=True):
                if rss.breached:
                    raise RuntimeError("P6 stage process-tree RSS limit exceeded")
                seconds = budget.worker_budget()

                def command(child: Path, row: dict[str, Any] = row, pair: Pair = pair) -> list[str]:
                    row.update(status="running", run_id=child.name)
                    persist()
                    return argv_for(pair, child)

                child, ok = supervise(
                    context.run / "workers",
                    f"p6_{context.stage}_worker",
                    [],
                    requested_argv=sys.argv,
                    process_seconds=seconds,
                    rss_bytes=RSS_BYTES,
                    worker_argv=command,
                    manifest_fields={
                        "p6_stage_run_id": context.run.name,
                        "pair": list(pair),
                        "experiment_family": FAMILY,
                    },
                    run_prefix=WORKER_PREFIX[context.stage],
                )
                terminal = read_json(child / "terminal.json")
                row.update(
                    status=terminal["status"],
                    reason=terminal["reason"],
                    wall_seconds=terminal["process_wall_seconds"],
                    peak_rss_bytes=terminal["peak_process_tree_rss_bytes"],
                )
                shutil.copyfile(
                    child / "terminal.json", workers_dir / f"{row['label']}.terminal.json"
                )
                shutil.copyfile(
                    child / "manifest.json", workers_dir / f"{row['label']}.manifest.json"
                )
                if (child / "result.json").is_file():
                    shutil.copyfile(child / "result.json", workers_dir / f"{row['label']}.json")
                persist()
                if not ok:
                    reason = f"worker {row['label']} failed: {terminal['reason']}"
                    break
                if after_worker is not None:
                    after_worker(pair, child)
            if reason is None and rss.breached:
                reason = "P6 stage process-tree RSS limit exceeded"
        except TimeoutError as exc:
            reason = f"P6 stage wall-time cap exhausted: {exc}"
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
        peak = rss.peak
    return WorkerOutcome(
        rows, "completed" if reason is None else "failed", reason, peak, budget.elapsed()
    )


def completed_runs(results_root: Path, stage: str, *, dry_run: bool = False) -> list[Path]:
    found = []
    for result in sorted((results_root / stage).glob("*/result.json")):
        data = read_json(result)
        manifest = read_json(result.parent / "manifest.json")
        if data.get("status") == "completed" and bool(manifest.get("dry_run")) == dry_run:
            found.append(result.parent)
    return found


def require_completed(
    results_root: Path, stage: str, run_id: str | None = None, *, dry_run: bool = False
) -> Path:
    """The compact directory of the completed run of ``stage`` that a later stage consumes."""
    if run_id is not None:
        target = results_root / stage / run_id
        if (
            not (target / "result.json").is_file()
            or read_json(target / "result.json").get("status") != "completed"
        ):
            raise ValueError(f"{stage} run {run_id} is not a completed stage")
        if (
            not (target / "manifest.json").is_file()
            or bool(read_json(target / "manifest.json").get("dry_run")) != dry_run
        ):
            raise ValueError(
                f"{stage} run {run_id} has a different dry_run flag than requested "
                f"(dry_run={dry_run}): a registered stage never consumes a dry-run record"
            )
        return target
    found = completed_runs(results_root, stage, dry_run=dry_run)
    if len(found) != 1:
        raise ValueError(
            f"expected exactly one completed {stage} run under {results_root / stage}, "
            f"found {len(found)}; pass the run ID explicitly"
        )
    return found[0]
