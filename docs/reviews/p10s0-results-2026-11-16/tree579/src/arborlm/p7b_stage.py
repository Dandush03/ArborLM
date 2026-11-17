"""P7-B stage orchestration: manifests citing ADR-0014, rerun guards, supervised workers, caps.

Each registered stage allocates a fresh run directory under ``--output-root``, a compact mirror
under ``--results-root/<stage>/<run id>``, a manifest and a terminal record. A second non-dry-run
run of the same stage is refused unless ``--supersede`` and ``--reason`` are given and recorded.

Linkage (ADR-0014 section 15, clarification 2): commits happen between stages by design, so a stage
is bound to its predecessors by the **hash of every ``*.py`` file under ``src/arborlm/`` (all
modules, not only ``p7b_*.py``), the specification hash and the hashes of the upstream stage's
records**, never by the Git HEAD (which is recorded only for information).
Within a stage the source, the specification and the version-controlled tree are re-checked at the
end, exactly as P7-A did.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from . import p7b_core as core
from .io import file_sha256, read_json, write_json
from .p5_clock import SuiteRSS
from .p6_stage import StageContext, check_rerun, finish_stage, git_head, require_completed
from .p7a_stage import Budget, registered_roots_refused, tracked_state_sha256
from .records import allocate_run, record_environment, record_source, utc_now
from .watchdog import RSS_BYTES, supervise

STAGE_PREFIX = {
    "panel": "P7BP",
    "layouts": "P7BL",
    "trace-b": "P7BT",
    "simulate-a": "P7BSA",
    "simulate-b": "P7BSB",
    "analyze": "P7BA",
}
WORKER_PREFIX = {
    "layouts": "P7BLW",
    "trace-b": "P7BTW",
    "simulate-a": "P7BSAW",
    "simulate-b": "P7BSBW",
}
STAGE_CAP = {
    "panel": core.TRACE_B_CAP,
    "layouts": core.LAYOUT_CAP,
    "trace-b": core.TRACE_B_CAP,
    "simulate-a": core.SIM_CAP,
    "simulate-b": core.SIM_CAP,
    "analyze": core.ANALYSIS_CAP,
}
SEED_RECORD = {
    "checkpoints": "restored, not re-seeded; no training",
    "L-RAND": list(core.RAND_SEEDS),
    "partitions": list(core.PARTITION_SEEDS),
    "stream_A_nulls": list(core.STREAM_A_NULL_SEEDS),
    "calibration_nulls": list(core.CAL_NULL_SEEDS),
    "stream_B_nulls": list(core.STREAM_B_NULL_SEEDS),
    "null_generator": "random.Random(replicate_seed * 1000 + cell_index); the exact "
    "count-preserving construction named in ADR-0014 section 3",
    "order_shuffle": 91201,
    "independent_selection": core.INDEPENDENT_SELECTION_SEED,
}
KNOWN_LIMITS = (
    "Every number is a count under a page model; none is a device measurement, latency, "
    "throughput or timing. A page-read count is not a time.",
    "R = 1, 2 and 8 are hypothetical row sizes that relabel bytes per row; they change no "
    "selection and no weight.",
    "Value pages only; keys are assumed in RAM. Simulated page misses are not I/O.",
    "Contexts are unrelated 64-byte teacher-forced windows; stream B comes from the same corpus "
    "split, and so from the same articles, as stream A: fresh in the sense of never having been "
    "evaluated, not an independent corpus.",
    "Greedy fill with bounded swap refinement is a heuristic; a stronger optimizer would probably "
    "help flat memory more (ADR-0014 section 8).",
    "Five predetermined partitions cannot support a statement about partitions in general "
    "(ADR-0014 section 7).",
    "Consistency counts over 27 pairs describe robustness to training randomness only; they are "
    "not significance tests.",
)

__all__ = [
    "Budget",
    "StageContext",
    "WorkerOutcome",
    "finish",
    "open_stage",
    "registered_roots_refused",
    "require_completed",
    "run_workers",
    "upstream_linkage",
]


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
        "human_approval": core.HUMAN_APPROVAL,
        "purpose": (
            "co-access layout equivalence: trace-driven value-page simulation on the frozen P5 "
            "memories, two evaluation streams; counts under a page model, not device measurements"
        ),
        "stage": stage,
        "run_id": run.name,
        "dry_run": dry_run,
        "command": argv,
        "arguments": arguments,
        "git_head_informational": head,
        "git_dirty_informational": dirty,
        "linkage_basis": "hashes of every file under src/arborlm/, specification hash and upstream "
        "record hashes; not the Git HEAD (ADR-0014 section 15, clarification 2)",
        "tracked_state_sha256": tracked_state_sha256(),
        "source_archive_sha256": source["archive"]["sha256"],
        "p7b_source_sha256": core.source_hashes(),
        "package_source_sha256": core.package_hashes(),
        "lock_sha256": source["lock_sha256"],
        "environment": environment_details(run),
        "seeds": SEED_RECORD,
        "supersedes": superseded,
        "linkage": linkage or {},
        "known_limits": list(KNOWN_LIMITS),
        "caps": {
            "stage_seconds": cap,
            "stage_cap_registered": STAGE_CAP[stage],
            "study_total_seconds": core.STUDY_CAP,
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
    """Re-check at stage end: the P7-B sources, the specification and the version-controlled tree
    are unchanged. Returns a reason string on a difference, else None."""
    manifest = context.manifest
    if core.source_hashes() != manifest["p7b_source_sha256"]:
        return "a src/arborlm/p7b_*.py file changed while the stage ran"
    if core.package_hashes() != manifest["package_source_sha256"]:
        return "a src/arborlm/*.py file changed while the stage ran"
    if core.spec_sha256() != manifest["spec_sha256"]:
        return "the ADR-0014 specification file changed while the stage ran"
    if tracked_state_sha256() != manifest["tracked_state_sha256"]:
        return "a version-controlled file changed while the stage ran"
    return None


def finish(context: StageContext, status: str, reason: str | None, result: dict[str, Any]) -> str:
    """Close a stage after the end-of-stage frozen-source check; a difference turns the stage into
    ``failed``. Returns the final status."""
    problem = verify_frozen(context)
    context.manifest["frozen_check_at_end"] = {
        "p7b_sources_unchanged": core.source_hashes() == context.manifest["p7b_source_sha256"],
        "package_sources_unchanged": core.package_hashes()
        == context.manifest["package_source_sha256"],
        "spec_unchanged": core.spec_sha256() == context.manifest["spec_sha256"],
        "problem": problem,
        "p7b_source_sha256": core.source_hashes(),
        "spec_sha256": core.spec_sha256(),
    }
    if problem is not None:
        status, reason = "failed", f"{reason + '; ' if reason else ''}{problem}"
    finish_stage(context, status, reason, result)
    return status


def upstream_linkage(
    results_root: Path, stage: str, run_id: str | None, *, dry_run: bool
) -> tuple[Path, dict[str, Any]]:
    """The completed upstream run a stage consumes, and its binding: manifest and result hashes.
    Refuses unless the upstream hashes of every ``src/arborlm/*.py`` file and the specification hash
    equal the current ones (linkage by hashes, not by Git HEAD)."""
    compact = require_completed(results_root, stage, run_id, dry_run=dry_run)
    manifest = read_json(compact / "manifest.json")
    problems = []
    if manifest["p7b_source_sha256"] != core.source_hashes():
        problems.append("the P7-B sources differ from the upstream stage's")
    if manifest.get("package_source_sha256") != core.package_hashes():
        problems.append("the src/arborlm sources differ from the upstream stage's")
    if manifest["spec_sha256"] != core.spec_sha256():
        problems.append("the specification differs from the upstream stage's")
    if problems:
        raise core.GateError(
            f"refused: upstream {stage} run {compact.name}: " + "; ".join(problems)
        )
    return compact, {
        "run_id": compact.name,
        "manifest_sha256": file_sha256(compact / "manifest.json"),
        "result_sha256": file_sha256(compact / "result.json"),
        "p7b_source_sha256_equal": True,
        "package_source_sha256_equal": True,
        "package_files": len(manifest["package_source_sha256"]),
        "spec_sha256_equal": True,
    }


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
    manifest_extra: dict[str, Any] | None = None,
    after_worker: Callable[[str, Path, dict[str, Any]], None] | None = None,
) -> WorkerOutcome:
    """One supervised subprocess per item, in order, as sequential active worker time under
    ``cap_seconds``. The first failure or a cap breach stops the stage; remaining items are recorded
    as ``unexecuted``. Partial worker output is copied to the compact mirror whether or not the
    worker finished."""
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
                    f"p7b_{context.stage}_worker",
                    [],
                    requested_argv=sys.argv,
                    process_seconds=remaining,
                    rss_bytes=RSS_BYTES,
                    worker_argv=command,
                    manifest_fields={
                        # Replace the E0 template text: this is P7-B under ADR-0014.
                        "experiment_family": core.FAMILY,
                        "question_id": core.STUDY,
                        "hypothesis": (
                            "co-access layout equivalence of the existing P5 memories "
                            "(ADR-0014 H-P7B)"
                        ),
                        "hypothesis_null_reason": None,
                        "authorized_spec_reference": core.SPEC,
                        "spec_sha256": context.manifest["spec_sha256"],
                        "p7b_stage_run_id": context.run.name,
                        "label": label,
                        "dry_run": context.manifest["dry_run"],
                        **(manifest_extra or {}),
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
