"""P7-A stage orchestration: manifests citing ADR-0013, rerun guards, supervised workers, caps.

Each registered stage (trace, simulate, analyze) allocates a fresh run directory under
``--output-root``, a compact mirror under ``--results-root/<stage>/<run id>``, a manifest and a
terminal record. A second non-dry-run run of the same stage is refused unless ``--supersede`` and
``--reason`` are given and recorded. Manifests state spec ADR-0013 and study P7-A; none of the E0
infrastructure-validation template text is used (worker manifests override it).

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from . import p7a_core as core
from .io import read_json, sha256, write_json
from .p5_clock import SuiteRSS
from .p6_stage import StageContext, check_rerun, finish_stage, git_head
from .records import allocate_run, record_environment, record_source, utc_now
from .watchdog import RSS_BYTES, supervise

STAGE_PREFIX = {"trace": "P7AT", "simulate": "P7AS", "analyze": "P7AA"}
WORKER_PREFIX = {"trace": "P7ATW", "simulate": "P7ASW"}
STAGE_CAP = {
    "trace": core.TRACE_CAP,
    "simulate": core.SIM_CAP,
    "analyze": core.SIM_CAP,
}
HUMAN_APPROVAL = (
    "ADR-0013 section 14: human approval of 2026-11-13 ('Approve as drafted'), revision 2 with the "
    "pre-outcome clarifications, as amended by section 14 items 8 to 14 (clarification 2 withdrawn)"
)
SEED_RECORD = {
    "checkpoints": "restored, not re-seeded; no training",
    "L-RAND": list(core.RAND_SEEDS),
    "order_shuffle": core.ORDER_SHUFFLE_SEED,
    "context_shuffle": core.CONTEXT_SHUFFLE_SEED,
    "frequency_matched_replicates": list(core.FM_SEEDS),
    "frequency_matched_generator": "exact count-preserving null; random.Random(replicate_seed * "
    "1000 + cell_index) (ADR-0013 section 14 item 8)",
    "bootstrap": core.BOOTSTRAP_SEED,
    "bootstrap_resamples": core.BOOTSTRAP_RESAMPLES,
    "independent_simulator_selection": 91501,
}


def registered_roots_refused(*paths: Path) -> None:
    """A dry run must never write under the registered experiments/ or results/ trees."""
    repo = Path.cwd().resolve()
    for path in paths:
        resolved = path.resolve()
        for protected in (repo / "experiments", repo / "results"):
            if resolved == protected or resolved.is_relative_to(protected):
                raise ValueError(
                    f"a dry run may not write under {protected}: {resolved} is inside it"
                )


# Untracked files are hashed (name and content) only under these trees: code, tests, configs and
# the decision records. Anything else untracked (docs/reviews/, a scratch area, outputs/) may appear
# or change while a stage runs without failing it.
GUARDED_UNTRACKED = (b"src/", b"tests/", b"configs/", b"docs/decisions/")


def tracked_state_sha256(repo: Path | None = None) -> str:
    """Hash used by the end-of-stage check (ADR-0013 section 14 clarification 6, audit minor 5).

    Covered: every content, mode, deletion or rename difference of a *tracked* file from HEAD
    (staged or not, ``git diff HEAD --binary``); and the names and contents of untracked files under
    ``src/``, ``tests/``, ``configs/`` and ``docs/decisions/`` (so an uncommitted edit of
    ``src/arborlm/p7a_*.py``, an uncommitted test, or a new source file is detected). The p7a
    sources and the specification are also hashed separately by ``verify_frozen``.

    Not covered: untracked files elsewhere, which may be created, edited or deleted during a stage
    without failing it (for example ``docs/reviews/`` and a scratch folder); git-ignored paths
    (``results/``, ``experiments/``, ``data/``, which stages write into); the content of a
    tracked file is covered only through git's view of it. Nothing may be created inside a tracked
    file's path, and the independent simulator's ``--out`` is written between stages, as the
    runbook states.
    """
    import subprocess

    root = repo or Path.cwd()

    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)

    diff = git("diff", "HEAD", "--binary", "--no-ext-diff")
    untracked = [
        n for n in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if n
    ]
    parts = [diff]
    for name in sorted(untracked):
        if name.startswith(GUARDED_UNTRACKED):
            path = root / name.decode()
            content = path.read_bytes() if path.is_file() else b""
            parts.append(name + b"\0" + sha256(content).encode())
    return sha256(b"\0".join(parts))


def environment_details(run: Path) -> dict[str, Any]:
    import platform

    env = record_environment(run, family=core.FAMILY)
    return {
        **{k: v for k, v in env.items() if k != "packages"},
        "torch": torch.__version__,
        "packages": {k: v for k, v in env["packages"].items() if k in ("torch", "psutil")},
        "threads": {
            "intra_op": torch.get_num_threads(),
            "inter_op": torch.get_num_interop_threads(),
        },
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "platform": platform.platform(),
    }


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
    cap_seconds: float | None = None,
    linkage: dict[str, Any] | None = None,
) -> StageContext:
    if dry_run:
        registered_roots_refused(output_root, results_root)
    superseded = check_rerun(results_root, stage, supersede, supersede_reason, dry_run=dry_run)
    run = allocate_run(output_root, prefix=STAGE_PREFIX[stage] + ("D" if dry_run else ""))
    compact = results_root / stage / run.name
    compact.mkdir(parents=True, exist_ok=False)  # never overwrites
    source = record_source(run, Path.cwd(), spec=core.SPEC)
    head, dirty = git_head()
    cap = cap_seconds if cap_seconds is not None else STAGE_CAP[stage]
    manifest = {
        "schema_version": 1,
        "experiment_family": core.FAMILY,
        "study": core.STUDY,
        "spec_reference": core.SPEC,
        "spec_sha256": source["spec_sha256"],
        "human_approval": HUMAN_APPROVAL,
        "purpose": (
            "trace-driven storage-page locality simulation on the frozen P5 memories; counts under "
            "a page model, not device measurements"
        ),
        "stage": stage,
        "run_id": run.name,
        "dry_run": dry_run,
        "command": argv,
        "arguments": arguments,
        "git_head": head,
        "git_dirty": dirty,
        "tracked_state_sha256": tracked_state_sha256(),
        "source_archive_sha256": source["archive"]["sha256"],
        "p7a_source_sha256": core.source_hashes(),
        "lock_sha256": source["lock_sha256"],
        "environment": environment_details(run),
        "seeds": SEED_RECORD,
        "supersedes": superseded,
        "linkage": linkage or {},
        "known_limits": list(core.KNOWN_LIMITS),
        "caps": {
            "stage_seconds": cap,
            "trace_seconds": core.TRACE_CAP,
            "simulation_and_analysis_seconds": core.SIM_CAP,
            "combined_seconds": core.COMBINED_CAP,
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


def verify_frozen(context: StageContext) -> str | None:
    """Re-check at stage end: p7a sources, the spec and the tracked-file state are unchanged.
    Returns a reason string on a difference, else None."""
    manifest = context.manifest
    if core.source_hashes() != manifest["p7a_source_sha256"]:
        return "a src/arborlm/p7a_*.py file changed while the stage ran"
    if core.spec_sha256() != manifest["spec_sha256"]:
        return "the ADR-0013 specification file changed while the stage ran"
    if tracked_state_sha256() != manifest["tracked_state_sha256"]:
        return "a version-controlled file changed while the stage ran"
    return None


def finish(context: StageContext, status: str, reason: str | None, result: dict[str, Any]) -> str:
    """Close a stage after the end-of-stage frozen-source check; a difference turns the stage
    into ``failed``. Returns the final status."""
    problem = verify_frozen(context)
    context.manifest["frozen_check_at_end"] = {
        "p7a_sources_unchanged": core.source_hashes() == context.manifest["p7a_source_sha256"],
        "spec_unchanged": core.spec_sha256() == context.manifest["spec_sha256"],
        "problem": problem,
        "p7a_source_sha256": core.source_hashes(),
        "spec_sha256": core.spec_sha256(),
    }
    if problem is not None:
        status, reason = "failed", f"{reason + '; ' if reason else ''}{problem}"
    finish_stage(context, status, reason, result)
    return status


class Budget:
    """Active worker time of one stage."""

    def __init__(self, cap_seconds: float, now: Callable[[], float] = time.monotonic) -> None:
        self.cap, self.now, self.start = cap_seconds, now, now()

    def elapsed(self) -> float:
        return float(self.now() - self.start)

    def remaining(self) -> float:
        return self.cap - self.elapsed()


@dataclass
class WorkerOutcome:
    rows: list[dict[str, Any]]
    status: str
    reason: str | None
    peak_rss_bytes: int
    active_seconds: float


def run_workers(
    context: StageContext,
    items: list[tuple[str, dict[str, Any]]],
    *,
    argv_for: Callable[[str, Path], list[str]],
    cap_seconds: float,
    slack: float = 0.0,
    after_worker: Callable[[str, Path, dict[str, Any]], None] | None = None,
) -> WorkerOutcome:
    """One supervised subprocess per item, in order, under the stage cap. The first failure or a
    cap breach stops the stage; remaining items are recorded as ``unexecuted``. Partial worker
    output is copied to the compact mirror whether or not the worker finished."""
    budget = Budget(cap_seconds)
    workers = context.compact / "workers"
    workers.mkdir(exist_ok=True)
    rows: list[dict[str, Any]] = [
        {"label": label, "status": "unexecuted", "run_id": None, **extra} for label, extra in items
    ]

    def persist() -> None:
        payload = {"workers": rows, "elapsed_seconds": budget.elapsed(), "cap_seconds": cap_seconds}
        write_json(context.run / "workers.json", payload)
        write_json(context.compact / "workers.json", payload)

    persist()
    reason: str | None = None
    with SuiteRSS() as rss:
        try:
            for row in rows:
                if rss.breached:
                    raise RuntimeError("process-tree RSS limit exceeded")
                remaining = budget.remaining()
                if remaining <= 0:
                    raise TimeoutError(f"stage cap of {cap_seconds:.0f} s exhausted before start")
                label = str(row["label"])

                def command(
                    child: Path, row: dict[str, Any] = row, label: str = label
                ) -> list[str]:
                    row.update(status="running", run_id=child.name)
                    persist()
                    return argv_for(label, child)

                child, ok = supervise(
                    context.run / "workers",
                    f"p7a_{context.stage}_worker",
                    [],
                    requested_argv=sys.argv,
                    process_seconds=remaining + slack,
                    rss_bytes=RSS_BYTES,
                    worker_argv=command,
                    manifest_fields={
                        # Override the E0 template text: this is P7-A under ADR-0013.
                        "experiment_family": core.FAMILY,
                        "question_id": core.STUDY,
                        "hypothesis": (
                            "storage-page locality of the existing P5 memories (ADR-0013 "
                            "predictions P7-H1 to P7-H4)"
                        ),
                        "hypothesis_null_reason": None,
                        "authorized_spec_reference": core.SPEC,
                        "spec_sha256": context.manifest["spec_sha256"],
                        "p7a_stage_run_id": context.run.name,
                        "label": label,
                        "dry_run": context.manifest["dry_run"],
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
                for name in ("terminal.json", "manifest.json", "result.json", "partial.json"):
                    if (child / name).is_file():
                        stem = name.replace(".json", "")
                        shutil.copyfile(child / name, workers / f"{label}.{stem}.json")
                result: dict[str, Any] = {}
                if (child / "result.json").is_file():
                    result = read_json(child / "result.json")
                    row["outcome"] = result.get("outcome")
                    if result.get("gate"):
                        row["gate"] = result["gate"]
                persist()
                if after_worker is not None and result:
                    after_worker(label, child, result)  # partial records are kept on failure too
                if not ok:
                    reason = f"worker {label} failed: {terminal['reason']}" + (
                        f" [{result['gate']}: {result.get('message')}]"
                        if result.get("gate")
                        else ""
                    )
                    break
            if reason is None and rss.breached:
                reason = "process-tree RSS limit exceeded"
        except TimeoutError as exc:
            reason = f"stage wall-time cap: {exc}"
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
        peak = rss.peak
    persist()
    return WorkerOutcome(
        rows, "completed" if reason is None else "failed", reason, peak, budget.elapsed()
    )


def completed_stage_dirs(results_root: Path, stage: str, *, dry_run: bool) -> list[Path]:
    from .p6_stage import completed_runs

    return completed_runs(results_root, stage, dry_run=dry_run)
