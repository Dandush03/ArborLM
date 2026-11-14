"""P7-B study driver (ADR-0014): ``panel``, ``layouts``, ``trace-b``, ``simulate``, ``analyze``,
``loader-smoke``, ``dry-run`` and ``budget``.

    uv run --locked --extra pilot python -m arborlm.p7b_study \\
        {panel|layouts|trace-b|simulate|analyze|loader-smoke|dry-run|budget}

Registered sequence (ADR-0014 section 15, clarification 5): panel proof -> layouts -> auditor
reproduces layout hashes -> stream B traces -> stream-B identity manifest committed -> simulate
stream A -> simulate stream B -> auditor's independent check on both -> analyze both, once.

``trace-b`` is the only stage that runs a model. ``loader-smoke`` restores one real parent/seed and
replays the unmodified models' recorded NLL; it computes and writes no trace of any stream.
``dry-run`` and ``budget`` use synthetic data only and refuse to write under ``experiments/`` or
``results/``. Nothing here trains, downloads or edits an earlier study's record.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import contextlib
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from . import p6_common as common
from . import p7b_core as core
from . import p7b_gates as gates
from . import p7b_stage as stages
from .io import canonical_json, file_sha256, read_json, sha256, write_json
from .p6_common import Pair, pair_label, pairs
from .records import runtime_supported

SMOKE_PAIR: Pair = (101, 301, 501)
DRY_PAIRS, DRY_CONTEXTS = 2, 8
STAGES_BY_STREAM = {"A": "simulate-a", "B": "simulate-b"}


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


class Options:
    """Resolved command-line options shared by the stages."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.data_dir: Path = args.data_dir
        self.parent_suite: Path | None = args.parent_suite
        self.output_root: Path = args.output_root
        self.results_root: Path = args.results_root
        self.p5_results: Path = args.p5_results
        self.supersede: str | None = args.supersede
        self.reason: str | None = args.reason
        self.panel_run: str | None = getattr(args, "panel_run", None)
        self.layout_run: str | None = getattr(args, "layout_run", None)
        self.trace_b_run: str | None = getattr(args, "trace_b_run", None)
        self.simulate_run_a: str | None = getattr(args, "simulate_run_a", None)
        self.simulate_run_b: str | None = getattr(args, "simulate_run_b", None)
        self.panel_confirmation: Path | None = getattr(args, "panel_confirmation", None)
        self.layout_confirmation: Path | None = getattr(args, "layout_confirmation", None)
        self.resim_confirmation_a: Path | None = getattr(args, "resim_confirmation_a", None)
        self.resim_confirmation_b: Path | None = getattr(args, "resim_confirmation_b", None)
        self.stream: str | None = getattr(args, "stream", None)
        # synthetic / dry-run state (None, False for a registered run)
        self.dry_run = False
        self.synthetic = False
        self.pair_list: list[Pair] = pairs()
        self.contexts = core.CONTEXTS
        self.repo: Path = Path.cwd()
        self.identity_path: Path | None = None
        self.reference_dir: Path | None = None
        self.selection: list[str] | None = None
        if (self.supersede is None) != (not self.reason):
            raise SystemExit("--supersede and --reason must be given together")

    def checkpoints(self) -> list[tuple[Pair, str]]:
        return [(p, k) for p in self.pair_list for k in core.KINDS]

    def labels(self) -> list[str]:
        return [core.cell_label(p, k) for p, k in self.checkpoints()]

    def identity(self) -> core.Identity:
        if self.identity_path is None:
            return core.load_identity(self.repo)
        return core.load_identity(self.repo, self.identity_path, self.labels())

    def job_identity(self) -> dict[str, Any]:
        return {
            "repo": str(self.repo),
            "identity": None if self.identity_path is None else str(self.identity_path),
            "labels": self.labels() if self.synthetic else None,
            "synthetic": self.synthetic,
        }

    def arguments(self) -> dict[str, Any]:
        def text(value: Path | None) -> str | None:
            return None if value is None else str(value)

        return {
            "data_dir": str(self.data_dir),
            "parent_suite": text(self.parent_suite),
            "output_root": str(self.output_root),
            "results_root": str(self.results_root),
            "p5_results": str(self.p5_results),
            "supersede": self.supersede,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "synthetic": self.synthetic,
            "checkpoints": len(self.checkpoints()),
            "contexts": self.contexts,
            "stream": self.stream,
            "panel_confirmation": text(self.panel_confirmation),
            "layout_confirmation": text(self.layout_confirmation),
            "resim_confirmation_a": text(self.resim_confirmation_a),
            "resim_confirmation_b": text(self.resim_confirmation_b),
        }


def _worker_argv(kind: str, child: Path, job: Path) -> list[str]:
    return [sys.executable, "-m", "arborlm.p7b_study", "_worker", kind, str(child), str(job)]


def _write_job(context: stages.StageContext, name: str, job: dict[str, Any]) -> Path:
    jobs = context.run / "jobs"
    jobs.mkdir(exist_ok=True)
    path = jobs / f"{name}.json"
    write_json(path, job)
    return path


def _seconds(result: dict[str, Any], key: str = "active_seconds") -> float:
    return float(result.get(key) or 0.0)


# --------------------------------------------------------------------------------------------------
# panel
# --------------------------------------------------------------------------------------------------
def synthetic_panel(opt: Options) -> Any:
    """A tiny stand-in reconstruction (dry run only). The 'registered' hashes are derived from the
    same function, so this exercises the machinery and is NOT independent evidence."""
    from .p7b_panel import EARLIER_PANELS, TRAIN_RANKED, _bytes, reconstruct_from_rows
    from .p7b_synth import synthetic_corpus
    from .pilot_data import select

    size = opt.contexts
    train_rows, val_rows = synthetic_corpus(1, 400), synthetic_corpus(2, 240)
    train_ranked = min(TRAIN_RANKED, 8 * size)
    _, full_train, _ = select(train_rows, "train", train_ranked)
    validation, _, _ = select(val_rows, "validation", EARLIER_PANELS * size, excluded=full_train)
    expected = {
        name: sha256(_bytes(validation[n * size : (n + 1) * size]))
        for n, name in enumerate(("P1", "P2", "P3", "P4", "P5"))
    }
    return reconstruct_from_rows(
        train_rows,
        val_rows,
        train_ranked=train_ranked,
        panel_size=size,
        expected_earlier=expected,
    )


def run_panel(opt: Options) -> tuple[int, Path]:
    from .p7b_panel import reconstruct_from_data_dir

    context = stages.open_stage(
        "panel",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=opt.dry_run,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
    )
    budget = stages.Budget(core.TRACE_B_CAP)
    status, reason = "failed", None
    result: dict[str, Any] = {"stage": "panel"}
    try:
        res = synthetic_panel(opt) if opt.synthetic else reconstruct_from_data_dir(opt.data_dir)
        (context.run / "panel_b.bytes").write_bytes(res.panel_bytes)
        write_json(context.compact / "panel_record.json", res.record)
        write_json(context.run / "panel_record.json", res.record)
        result.update(
            panel_sha256=res.record["panel_sha256"],
            panel_record_sha256=file_sha256(context.compact / "panel_record.json"),
            ranks=res.record["ranks"],
            checks=res.record["checks"],
            overlap=res.record["overlap"],
            panel_bytes_file="panel_b.bytes",
            active_seconds=budget.elapsed(),
        )
        status = "completed"
        if budget.remaining() < 0:
            status, reason = "failed", "panel reconstruction exceeded its cap"
    except Exception as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        result["error"] = reason
    finally:
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-B panel {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# layouts
# --------------------------------------------------------------------------------------------------
def assemble_hash_table(
    context: stages.StageContext,
    done: dict[str, dict[str, Any]],
    labels: list[str],
    identity_sha: str,
) -> Path:
    """Write the layout hash table (the record the auditor reproduces and the simulation checks)."""
    table = {lb: done[lb]["hash_table"] for lb in labels if lb in done}
    payload = {
        "schema": "P7B-layout-hash-table-v1",
        "study": core.STUDY,
        "complete": len(table) == len(labels),
        "identity_manifest_sha256": identity_sha,
        "partitions": next(iter(done.values()))["partitions"] if done else None,
        "hash_method": "ADR-0014 section 4 Exactness (canonical hash)",
        "layouts": table,
        "layout_files": {lb: done[lb]["layout_file"] for lb in labels if lb in done},
        "overall_sha256": sha256(canonical_json(table)),
    }
    path = context.compact / "layout_hash_table.json"
    write_json(path, payload)
    write_json(context.run / "layout_hash_table.json", payload)
    return path


def run_layouts(opt: Options) -> tuple[int, Path]:
    identity = opt.identity()
    labels = opt.labels()
    linkage = {
        "identity_manifest": str(identity.path),
        "identity_manifest_sha256": identity.file_sha256,
        "identity_overall_sha256": identity.data["overall_hash"]["sha256"],
        "reads": "calibration trace files only (roles calibration.*)",
    }
    context = stages.open_stage(
        "layouts",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=opt.dry_run,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        linkage=linkage,
    )
    layout_dir = context.run / "layouts"
    done: dict[str, dict[str, Any]] = {}
    outcome: stages.WorkerOutcome | None = None
    status, reason = "failed", None

    def keep(label: str, _child: Path, result: dict[str, Any]) -> None:
        if result.get("outcome") == "completed":
            done[label] = result

    def argv_for(label: str, child: Path) -> list[str]:
        job = _write_job(
            context,
            label,
            {**opt.job_identity(), "label": label, "layout_dir": str(layout_dir)},
        )
        return _worker_argv("layouts", child, job)

    try:
        outcome = stages.run_workers(
            context,
            [(lb, {}) for lb in labels],
            argv_for=argv_for,
            cap_seconds=core.LAYOUT_CAP,
            after_worker=keep,
        )
        status, reason = outcome.status, outcome.reason
        if status == "completed" and sorted(done) != sorted(labels):
            status, reason = "failed", "not every checkpoint produced a layout record"
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        table_path = assemble_hash_table(context, done, labels, identity.file_sha256)
        result = {
            "stage": "layouts",
            "checkpoints_expected": len(labels),
            "checkpoints_completed": len(done),
            "unexecuted_or_failed": [lb for lb in labels if lb not in done],
            "layout_hash_table": "layout_hash_table.json",
            "layout_hash_table_sha256": file_sha256(table_path),
            "active_seconds": outcome.active_seconds if outcome else None,
            "peak_rss_bytes": outcome.peak_rss_bytes if outcome else None,
            "cap_seconds": core.LAYOUT_CAP,
            "workers": outcome.rows if outcome else [],
        }
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-B layouts {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# trace-b
# --------------------------------------------------------------------------------------------------
def assemble_stream_b_manifest(
    context: stages.StageContext,
    done: dict[str, dict[str, Any]],
    labels: list[str],
    bindings: dict[str, Any],
) -> Path:
    """The stream-B identity manifest: trace file hashes, per-slot count hashes and null stream
    hashes per checkpoint. Written under the results root, to be committed before any simulation."""
    entries: dict[str, Any] = {}
    for label in labels:
        rec = done.get(label)
        if rec is None:
            continue
        files = rec["files"]["stream_b"]
        entries[label] = {
            "selected_sha256": files["selected"]["sha256"],
            "branches_sha256": None if files["branches"] is None else files["branches"]["sha256"],
            "counts_sha256": rec["counts_sha256"],
            "unique_selected_slots": rec["unique_selected_slots"],
            "null_streams": rec["nulls"],
            "regeneration_byte_identical_to_identity_manifest": rec["regeneration"][
                "byte_identical_to_identity_manifest"
            ],
            "replay_bitwise_equal": rec["replay"]["bitwise_equal"],
            "loss_computed_on_stream_b": rec["loss_computed_on_stream_b"],
        }
    payload = {
        "schema": "P7B-stream-b-identity-manifest-v1",
        "study": core.STUDY,
        "complete": len(entries) == len(labels),
        "bindings": bindings,
        "checkpoints": entries,
        "overall_sha256": sha256(canonical_json(entries)),
    }
    path = context.compact / "stream_b_identity_manifest.json"
    write_json(path, payload)
    write_json(context.run / "stream_b_identity_manifest.json", payload)
    return path


def run_trace_b(opt: Options) -> tuple[int, Path]:
    identity = opt.identity()
    dry = opt.dry_run
    panel_compact, panel_link = stages.upstream_linkage(
        opt.results_root, "panel", opt.panel_run, dry_run=dry
    )
    layout_compact, layout_link = stages.upstream_linkage(
        opt.results_root, "layouts", opt.layout_run, dry_run=dry
    )
    panel_record = read_json(panel_compact / "panel_record.json")
    registered = (
        {}
        if not opt.synthetic
        else {
            "ranks": (panel_record["ranks"][0], panel_record["ranks"][1]),
            "rows": panel_record["rows"],
            "earlier": {k: v["sha256"] for k, v in panel_record["earlier_panels"].items()},
        }
    )
    gate_panel = gates.check_panel_confirmation(
        opt.panel_confirmation,
        panel_record_path=panel_compact / "panel_record.json",
        panel_run_id=panel_compact.name,
        dry_run=dry,
        **registered,
    )
    gate_layout = gates.check_layout_confirmation(
        opt.layout_confirmation,
        hash_table_path=layout_compact / "layout_hash_table.json",
        layout_run_id=layout_compact.name,
        labels=opt.labels(),
        dry_run=dry,
    )
    panel_result = read_json(panel_compact / "result.json")
    cap = max(0.0, core.TRACE_B_CAP - _seconds(panel_result))
    linkage = {
        "panel": panel_link,
        "layouts": layout_link,
        "panel_confirmation": gate_panel,
        "layout_confirmation": gate_layout,
        "panel_active_seconds": _seconds(panel_result),
        "identity_manifest_sha256": identity.file_sha256,
    }
    context = stages.open_stage(
        "trace-b",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=dry,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        cap_seconds=cap,
        linkage=linkage,
    )
    traces = context.run / "traces"
    checkpoints = context.compact / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    labels = opt.labels()
    done: dict[str, dict[str, Any]] = {}
    outcome: stages.WorkerOutcome | None = None
    status, reason = "failed", None

    def keep(_label: str, _child: Path, result: dict[str, Any]) -> None:
        for record in result.get("records", []):
            write_json(checkpoints / f"{record['label']}.json", record)
            done[record["label"]] = record

    def argv_for(label: str, child: Path) -> list[str]:
        pair = next(p for p in opt.pair_list if pair_label(p) == label)
        job = _write_job(
            context,
            label,
            {
                **opt.job_identity(),
                "pair": list(pair),
                "traces_dir": str(traces),
                "panel_bytes": str(opt.output_root / panel_compact.name / "panel_b.bytes"),
                "panel_record": str(panel_compact / "panel_record.json"),
                "parent_suite": None if opt.parent_suite is None else str(opt.parent_suite),
                "output_root": str(opt.output_root.resolve()),
                "p5_results": str(opt.p5_results),
                "data_dir": str(opt.data_dir),
                "contexts": opt.contexts,
            },
        )
        return _worker_argv("trace-b", child, job)

    try:
        outcome = stages.run_workers(
            context,
            [(pair_label(p), {"pair": list(p)}) for p in opt.pair_list],
            argv_for=argv_for,
            cap_seconds=cap,
            after_worker=keep,
        )
        status, reason = outcome.status, outcome.reason
        if status == "completed" and sorted(done) != sorted(labels):
            status, reason = "failed", "not every checkpoint produced a stream B trace record"
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        manifest_path = assemble_stream_b_manifest(
            context,
            done,
            labels,
            {
                "panel_record_sha256": file_sha256(panel_compact / "panel_record.json"),
                "panel_sha256": panel_result.get("panel_sha256"),
                "identity_manifest_sha256": identity.file_sha256,
                "layout_hash_table_sha256": file_sha256(layout_compact / "layout_hash_table.json"),
                "panel_confirmation_sha256": gate_panel["sha256"],
                "layout_confirmation_sha256": gate_layout["sha256"],
            },
        )
        result = {
            "stage": "trace-b",
            "checkpoints_expected": len(labels),
            "checkpoints_completed": len(done),
            "unexecuted_or_failed": [lb for lb in labels if lb not in done],
            "stream_b_identity_manifest": "stream_b_identity_manifest.json",
            "stream_b_identity_manifest_sha256": file_sha256(manifest_path),
            "active_seconds": outcome.active_seconds if outcome else None,
            "peak_rss_bytes": outcome.peak_rss_bytes if outcome else None,
            "cap_seconds": cap,
            "workers": outcome.rows if outcome else [],
            "trace_directory": "traces",
        }
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-B trace-b {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# simulate
# --------------------------------------------------------------------------------------------------
def verify_stream_b_manifest(
    trace_compact: Path, layout_compact: Path, identity_sha: str, *, dry_run: bool
) -> dict[str, Any]:
    """ADR-0014 section 7a: the stream-B identity manifest is written and committed before any
    simulation of either stream. Refuses unless it is tracked by Git and unmodified relative to
    HEAD, complete, bound to the layout table and identity manifest of this study, and equal to the
    manifest the trace-b stage recorded in its own result. Returns the record for the linkage
    (including its SHA-256). A dry run uses the labelled stand-in for the Git check only."""
    path = trace_compact / core.STREAM_B_MANIFEST
    git_check = core.tracked_and_clean(path, dry_run=dry_run)
    digest = file_sha256(path)
    manifest = read_json(path)
    problems = []
    if manifest.get("schema") != "P7B-stream-b-identity-manifest-v1" or not manifest.get(
        "complete"
    ):
        problems.append("the manifest is not a complete stream-B identity manifest")
    if read_json(trace_compact / "result.json").get("stream_b_identity_manifest_sha256") != digest:
        problems.append("it differs from the manifest the trace-b stage recorded in its result")
    bindings = manifest.get("bindings", {})
    if bindings.get("layout_hash_table_sha256") != file_sha256(
        layout_compact / "layout_hash_table.json"
    ):
        problems.append("it is bound to a different layout hash table")
    if bindings.get("identity_manifest_sha256") != identity_sha:
        problems.append("it is bound to a different trace identity manifest")
    if problems:
        raise core.GateError("refused: stream-B identity manifest: " + "; ".join(problems))
    return {"file": str(path), "sha256": digest, **git_check}


def run_simulate(opt: Options, stream: str) -> tuple[int, Path]:
    if stream not in STAGES_BY_STREAM:
        raise SystemExit("--stream must be A or B")
    stage = STAGES_BY_STREAM[stream]
    identity = opt.identity()
    dry = opt.dry_run
    layout_compact, layout_link = stages.upstream_linkage(
        opt.results_root, "layouts", opt.layout_run, dry_run=dry
    )
    trace_compact, trace_link = stages.upstream_linkage(
        opt.results_root, "trace-b", opt.trace_b_run, dry_run=dry
    )
    stream_b_manifest = verify_stream_b_manifest(
        trace_compact, layout_compact, identity.file_sha256, dry_run=dry
    )
    gate_layout = gates.check_layout_confirmation(
        opt.layout_confirmation,
        hash_table_path=layout_compact / "layout_hash_table.json",
        layout_run_id=layout_compact.name,
        labels=opt.labels(),
        dry_run=dry,
    )
    # The layout confirmation must be the same one trace-b was started on (hashes, not HEAD).
    trace_manifest = read_json(trace_compact / "manifest.json")
    if trace_manifest["linkage"]["layouts"]["run_id"] != layout_compact.name:
        raise core.GateError("refused: trace-b was started on a different layouts run")
    linkage = {
        "layouts": layout_link,
        "trace_b": trace_link,
        "layout_confirmation": gate_layout,
        "stream_b_identity_manifest": stream_b_manifest,
        "identity_manifest_sha256": identity.file_sha256,
        "stream": stream,
        "order": "once stream A starts, stream B is simulated unconditionally; nothing computed on "
        "one stream is an input to the other",
    }
    context = stages.open_stage(
        stage,
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=dry,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        cap_seconds=core.SIM_CAP,
        linkage=linkage,
    )
    labels = opt.labels()
    status, reason = "failed", None
    outcome: stages.WorkerOutcome | None = None
    layout_dir = opt.output_root / layout_compact.name / "layouts"
    trace_dir = opt.output_root / trace_compact.name / "traces"

    def reference_for(label: str) -> str | None:
        if stream != "A":
            return None
        if opt.reference_dir is not None:
            return str(opt.reference_dir / f"{label}.result.json")
        return str(core.p7a_simulation_path(opt.repo, label))

    def argv_for(label: str, child: Path) -> list[str]:
        job = _write_job(
            context,
            label,
            {
                **opt.job_identity(),
                "label": label,
                "stream": stream,
                "hash_table": str(layout_compact / "layout_hash_table.json"),
                "layout_worker_record": str(layout_compact / "workers" / f"{label}.result.json"),
                "layout_dir": str(layout_dir),
                "trace_b_dir": str(trace_dir),
                "trace_b_record_dir": str(trace_compact / "checkpoints"),
                "stream_b_manifest": stream_b_manifest["file"],
                "stream_b_manifest_sha256": stream_b_manifest["sha256"],
                "reference": reference_for(label),
                "p5_results": str(opt.p5_results),
            },
        )
        return _worker_argv("simulate", child, job)

    try:
        outcome = stages.run_workers(
            context,
            [(lb, {}) for lb in labels],
            argv_for=argv_for,
            cap_seconds=core.SIM_CAP,
        )
        status, reason = outcome.status, outcome.reason
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        rows = outcome.rows if outcome else []
        result = {
            "stage": stage,
            "stream": stream,
            "checkpoints_expected": len(labels),
            "checkpoints_completed": sum(1 for r in rows if r.get("outcome") == "completed"),
            "active_seconds": outcome.active_seconds if outcome else None,
            "peak_rss_bytes": outcome.peak_rss_bytes if outcome else None,
            "cap_seconds": core.SIM_CAP,
            "workers": rows,
            "note": "no analysis output is produced before both streams are simulated",
        }
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-B {stage} {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# analyze
# --------------------------------------------------------------------------------------------------
def load_simulation_records(compact: Path, labels: list[str]) -> dict[str, dict[str, Any]]:
    """Per-checkpoint simulation results of a simulate run; a missing, failed or partial worker
    output is simply absent (the analysis then reports INCOMPLETE)."""
    records: dict[str, dict[str, Any]] = {}
    for label in labels:
        path = compact / "workers" / f"{label}.result.json"
        try:
            data = read_json(path)
        except (OSError, ValueError):
            continue
        if data.get("outcome") == "completed" and data.get("record", {}).get("complete"):
            records[label] = data
    return records


def load_layout_records(compact: Path, labels: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for label in labels:
        try:
            data = read_json(compact / "workers" / f"{label}.result.json")
        except (OSError, ValueError):
            continue
        if data.get("outcome") == "completed":
            out[label] = data
    return out


def load_nll(p5_results: Path, labels: list[str]) -> tuple[dict[str, float] | None, list[str]]:
    nll: dict[str, float] = {}
    missing: list[str] = []
    for label in labels:
        try:
            nll[label] = float(read_json(p5_results / label / "result.json")["final"]["nll"])
        except (OSError, ValueError, KeyError):
            missing.append(label)
    return (nll or None), missing


def run_analyze(opt: Options) -> tuple[int, Path]:
    from .p7b_analysis import analyze_streams

    dry = opt.dry_run
    sim_a, link_a = stages.upstream_linkage(
        opt.results_root, "simulate-a", opt.simulate_run_a, dry_run=dry
    )
    sim_b, link_b = stages.upstream_linkage(
        opt.results_root, "simulate-b", opt.simulate_run_b, dry_run=dry
    )
    labels = opt.labels()
    for compact in (sim_a, sim_b):
        stage_result = read_json(compact / "result.json")
        if stage_result.get("checkpoints_completed") != len(labels):
            raise core.GateError(f"refused: {compact.name} did not simulate every checkpoint")
    manifest_a, manifest_b = (read_json(c / "manifest.json") for c in (sim_a, sim_b))
    for key in ("layouts", "trace_b"):
        if manifest_a["linkage"][key]["run_id"] != manifest_b["linkage"][key]["run_id"]:
            raise core.GateError(f"refused: the two streams were simulated on different {key} runs")
    selection = opt.selection
    checks = {}
    for stream, compact, option in (
        ("A", sim_a, opt.resim_confirmation_a),
        ("B", sim_b, opt.resim_confirmation_b),
    ):
        wanted = selection if selection is not None else core.independent_selection()
        checks[stream] = gates.check_resim_confirmation(
            option,
            stream=stream,
            simulate_run_id=compact.name,
            record_sha256={
                lb: file_sha256(compact / "workers" / f"{lb}.result.json")
                for lb in wanted
                if (compact / "workers" / f"{lb}.result.json").is_file()
            },
            expected_selection=selection,
            dry_run=dry,
        )
    layout_compact = opt.results_root / "layouts" / manifest_a["linkage"]["layouts"]["run_id"]
    linkage = {
        "simulate_a": link_a,
        "simulate_b": link_b,
        "resim_confirmation_a": checks["A"],
        "resim_confirmation_b": checks["B"],
        "layouts_run_id": layout_compact.name,
        "trace_b_run_id": manifest_a["linkage"]["trace_b"]["run_id"],
    }
    context = stages.open_stage(
        "analyze",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=dry,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        cap_seconds=core.ANALYSIS_CAP,
        linkage=linkage,
    )
    budget = stages.Budget(core.ANALYSIS_CAP)
    status, reason = "failed", None
    result: dict[str, Any] = {"stage": "analyze"}
    try:
        records = {
            "A": load_simulation_records(sim_a, labels),
            "B": load_simulation_records(sim_b, labels),
        }
        nll, nll_missing = load_nll(opt.p5_results, labels)
        analysis = analyze_streams(
            records,
            expected=opt.checkpoints(),
            nll=nll,
            layout_records=load_layout_records(layout_compact, labels),
        )
        analysis["p5_nll_missing_labels"] = nll_missing
        write_json(context.compact / "analysis.json", analysis)
        write_json(context.run / "analysis.json", analysis)
        result.update(
            streams={k: v["status"] for k, v in analysis["streams"].items()},
            decision_classes={
                k: v["decision_class"] for k, v in analysis["combined"]["tree_kinds"].items()
            },
            recommendation_row=analysis["combined"]["recommendation"]["row"],
            analysis_seconds=budget.elapsed(),
            analysis_sha256=file_sha256(context.compact / "analysis.json"),
        )
        status = "completed"
        if budget.remaining() < 0:
            status, reason = "failed", "analysis exceeded its cap"
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-B analyze {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# loader-smoke
# --------------------------------------------------------------------------------------------------
def loader_smoke(opt: Options, pair: Pair = SMOKE_PAIR) -> dict[str, Any]:
    """Restore one real parent/seed with P6's loader (locate, hash verification, strict restore) and
    replay the unmodified models' recorded P5 NLL bitwise on the P5 panel. No trace of any stream is
    computed or written; the only scratch folder is a temporary one outside experiments/ and
    results/."""
    from .p5_model import evaluate, state_digest
    from .p7a_trace import bitwise_equal, configure_deterministic_cpu

    configure_deterministic_cpu()
    assert opt.parent_suite is not None
    repo = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="p7b-loader-smoke-") as scratch:
        run = Path(scratch).resolve()
        for protected in (repo / "experiments", repo / "results"):
            if run.is_relative_to(protected):
                raise SystemExit(
                    "loader-smoke scratch folder must be outside experiments/ results/"
                )
        started = time.perf_counter()
        source = common.load_real_cell(
            pair,
            p5_suite=opt.parent_suite.resolve(),
            output_root=opt.output_root.resolve(),
            p5_results=opt.p5_results.resolve(),
            data_dir=opt.data_dir.resolve(),
            run=run,
        )
        loaded = time.perf_counter()
        replays: dict[str, Any] = {}
        for kind in core.KINDS:
            t0 = time.perf_counter()
            digest_before = state_digest(source.models[kind])
            replay = evaluate(source.models[kind], source.panel, source.expected_targets)
            recorded = source.recorded[kind]["nll"]
            replays[kind] = {
                "recorded_nll": recorded,
                "replayed_nll": replay["nll"],
                "bitwise_equal": bitwise_equal(replay["nll"], recorded),
                "state_digest_unchanged": state_digest(source.models[kind]) == digest_before,
                "replay_seconds": time.perf_counter() - t0,
            }
        files_ok = source.files_unchanged()
        finished = time.perf_counter()
    return {
        "command": "loader-smoke",
        "study": core.STUDY,
        "spec": core.SPEC,
        "pair": list(pair),
        "load_seconds": loaded - started,
        "replay_seconds_total": finished - loaded,
        "wall_seconds": finished - started,
        "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
        "replays": replays,
        "all_replays_bitwise_equal": all(r["bitwise_equal"] for r in replays.values()),
        "checkpoint_files_unchanged": files_ok,
        "traces_computed_or_written": False,
        "note": "locate, hash verification, strict restore and unmodified bitwise NLL replay on "
        "the P5 panel only; no trace of any stream, no layout, simulation or analysis; nothing "
        "written under results/ or experiments/",
    }


# --------------------------------------------------------------------------------------------------
# dry-run
# --------------------------------------------------------------------------------------------------
def _listing(*roots: Path) -> dict[str, list[str]]:
    return {str(r): sorted(p.name for p in r.iterdir()) if r.is_dir() else [] for r in roots}


STAND_IN = core.STAND_IN_TOOL
STAND_IN_SHA = core.STAND_IN_TOOL_SHA256


def stand_in_confirmations(opt: Options, root: Path) -> None:
    """Confirmation files for the dry run, written from the implementer's own records. They exercise
    the gates only and are labelled as stand-ins everywhere."""
    panel_compact = next((opt.results_root / "panel").glob("*"))
    record = read_json(panel_compact / "panel_record.json")
    write_json(
        root / "panel_confirmation_stand_in.json",
        {
            "schema": core.SCHEMA_PANEL_CONFIRMATION,
            "verdict": "AGREE",
            "tool": STAND_IN,
            "tool_sha256": STAND_IN_SHA,
            "panel_stage_run_id": panel_compact.name,
            "panel_record_sha256": file_sha256(panel_compact / "panel_record.json"),
            "ranks": record["ranks"],
            "panel_sha256": record["panel_sha256"],
            "row_sha256": record["row_sha256"],
            "earlier_panels_reproduced": {
                k: v["sha256"] for k, v in record["earlier_panels"].items()
            },
            "overlap": {
                "with_P1_to_P5_panels": 0,
                "with_calibration_stream": 0,
                "with_full_training_pool": 0,
                "duplicates_within_panel": 0,
            },
        },
    )
    opt.panel_confirmation = root / "panel_confirmation_stand_in.json"


def stand_in_layout_confirmation(opt: Options, root: Path) -> None:
    layout_compact = next((opt.results_root / "layouts").glob("*"))
    table = read_json(layout_compact / "layout_hash_table.json")
    checkpoints: dict[str, Any] = {}
    for label in opt.labels():
        _, kind = core.parse_label(label)
        checkpoints[label] = {
            f"R{rows}": {
                name: table["layouts"][label][core.layout_key(name, rows)]
                for name in core.required_confirmation_layouts(kind)
            }
            for rows in (2, 8)
        }
    write_json(
        root / "layout_confirmation_stand_in.json",
        {
            "schema": core.SCHEMA_LAYOUT_CONFIRMATION,
            "verdict": "AGREE",
            "tool": STAND_IN,
            "tool_sha256": STAND_IN_SHA,
            "layout_stage_run_id": layout_compact.name,
            "layout_hash_table_sha256": file_sha256(layout_compact / "layout_hash_table.json"),
            "rows": [2, 8],
            "checkpoints": checkpoints,
        },
    )
    opt.layout_confirmation = root / "layout_confirmation_stand_in.json"


def stand_in_resim(opt: Options, root: Path, stream: str) -> None:
    compact = next((opt.results_root / STAGES_BY_STREAM[stream]).glob("*"))
    labels = opt.labels()
    layouts = [core.L_FREQ, core.L_COAX, core.L_BCOAX, *core.L_PCOAX]
    path = root / f"resim_confirmation_{stream}_stand_in.json"
    write_json(
        path,
        {
            "schema": core.SCHEMA_RESIM_CONFIRMATION,
            "verdict": "AGREE",
            "tool": STAND_IN,
            "tool_sha256": STAND_IN_SHA,
            "stream": stream,
            "simulate_stage_run_id": compact.name,
            "selection": labels,
            "settings": [{"R": r, "C": c} for r, c in core.CRITERION_SETTINGS],
            "tie_rules": list(core.TIES),
            "streams_compared": ["actual", "null_1", "null_2", "null_3"],
            "layouts_compared": layouts,
            "record_sha256": {
                lb: file_sha256(compact / "workers" / f"{lb}.result.json") for lb in labels
            },
            "checkpoints": {lb: {"differences": [], "integrity_problems": []} for lb in labels},
        },
    )
    if stream == "A":
        opt.resim_confirmation_a = path
    else:
        opt.resim_confirmation_b = path


def dry_run(args: argparse.Namespace, keep: Path | None = None, pair_count: int = DRY_PAIRS) -> int:
    """All stages on small synthetic data in a temporary directory (or in ``keep``, for tests,
    which then survives). Refuses to write under experiments/ or results/ and verifies that both
    are unchanged afterwards."""
    from .p7b_synth import build_identity, write_references

    repo = Path.cwd().resolve()
    before = _listing(repo / "experiments", repo / "results")
    summary: dict[str, Any] = {"label": "dry run on synthetic data; stand-in confirmation files"}
    code = 0
    with contextlib.ExitStack() as stack:
        if keep is None:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="p7b-dry-run-")))
        else:
            root = keep
        stages.registered_roots_refused(root)
        args.output_root, args.results_root = root / "experiments", root / "results"
        args.supersede = args.reason = None
        opt = Options(args)
        opt.dry_run = opt.synthetic = True
        opt.pair_list, opt.contexts = pairs()[:pair_count], DRY_CONTEXTS
        opt.repo = root
        opt.parent_suite = opt.parent_suite or root / "none"
        opt.p5_results = root / "p5-none"
        # The git-based source checks of the stages run in the repository; only the data is
        # synthetic. Shared files live in ``root`` and are addressed by absolute path.
        identity, kept = build_identity(root, opt.pair_list, opt.contexts)
        opt.identity_path = identity.path
        opt.reference_dir = write_references(root, identity, kept)
        opt.selection = opt.labels()
        sequence: list[tuple[str, Any]] = [
            ("panel", lambda: run_panel(opt)),
            ("layouts", lambda: run_layouts(opt)),
        ]
        for name, step in sequence:
            code = step()[0]
            summary[name] = code
            if code:
                break
        if code == 0:
            stand_in_confirmations(opt, root)
            stand_in_layout_confirmation(opt, root)
            for name, step in (
                ("trace-b", lambda: run_trace_b(opt)),
                ("simulate-a", lambda: run_simulate(opt, "A")),
                ("simulate-b", lambda: run_simulate(opt, "B")),
            ):
                code = step()[0]
                summary[name] = code
                if code:
                    break
        if code == 0:
            stand_in_resim(opt, root, "A")
            stand_in_resim(opt, root, "B")
            code = run_analyze(opt)[0]
            summary["analyze"] = code
            analysis = read_json(next((opt.results_root / "analyze").glob("*/analysis.json")))
            summary["streams"] = {k: v["status"] for k, v in analysis["streams"].items()}
            summary["analysis_missing"] = {
                k: len(v["missing_or_failed"]) for k, v in analysis["streams"].items()
            }
        summary["scratch_deleted"] = keep is None
    after = _listing(repo / "experiments", repo / "results")
    summary["experiments_and_results_unchanged"] = before == after
    print(canonical_json(summary).decode().strip())
    return 0 if code == 0 and before == after else 1


# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="P7-B co-access layout equivalence (ADR-0014)")
    parser.add_argument(
        "command",
        choices=(
            "panel",
            "layouts",
            "trace-b",
            "simulate",
            "analyze",
            "loader-smoke",
            "dry-run",
            "budget",
        ),
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data/wikitext2"))
    parser.add_argument("--parent-suite", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--results-root", type=Path, default=core.DEFAULT_RESULTS)
    parser.add_argument("--p5-results", type=Path, default=core.P5_RESULTS)
    parser.add_argument("--supersede", help="run ID of an earlier run of the same stage")
    parser.add_argument("--reason", help="recorded reason for a deliberate rerun")
    parser.add_argument("--stream", choices=("A", "B"), help="simulate: the evaluation stream")
    parser.add_argument("--panel-run", help="trace-b: panel run ID (default: the one completed)")
    parser.add_argument("--layout-run", help="trace-b, simulate: layouts run ID")
    parser.add_argument("--trace-b-run", help="simulate: trace-b run ID")
    parser.add_argument("--simulate-run-a", help="analyze: simulate-a run ID")
    parser.add_argument("--simulate-run-b", help="analyze: simulate-b run ID")
    parser.add_argument("--panel-confirmation", type=Path, help="trace-b: gate (a) file")
    parser.add_argument("--layout-confirmation", type=Path, help="trace-b, simulate: gate (b) file")
    parser.add_argument(
        "--resim-confirmation-a", type=Path, help="analyze: gate (c) file, stream A"
    )
    parser.add_argument(
        "--resim-confirmation-b", type=Path, help="analyze: gate (c) file, stream B"
    )
    parser.add_argument("--replay-seconds", type=float, help="budget: measured seconds per replay")
    parser.add_argument("--load-seconds", type=float, help="budget: measured seconds per pair load")
    return parser


def main() -> int:
    if sys.argv[1:2] == ["_worker"]:
        from . import p7b_workers as workers

        kind, rest = sys.argv[2], sys.argv[3:]
        table = {
            "layouts": workers.layouts_worker,
            "trace-b": workers.trace_b_worker,
            "simulate": workers.simulate_worker,
        }
        return table[kind](rest)
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "budget":
        from .p7b_budget import budget

        return budget(args)
    if args.command == "dry-run":
        return dry_run(args)
    runtime_supported()
    opt = Options(args)
    if args.command == "loader-smoke":
        if opt.parent_suite is None:
            parser.error("loader-smoke requires --parent-suite")
        report = loader_smoke(opt)
        print(canonical_json(report).decode().strip(), flush=True)
        ok = report["all_replays_bitwise_equal"] and report["checkpoint_files_unchanged"]
        return 0 if ok else 1
    if args.command == "panel":
        return run_panel(opt)[0]
    if args.command == "layouts":
        return run_layouts(opt)[0]
    if args.command == "trace-b":
        if opt.parent_suite is None:
            parser.error("trace-b requires --parent-suite")
        return run_trace_b(opt)[0]
    if args.command == "simulate":
        if opt.stream is None:
            parser.error("simulate requires --stream A or B")
        return run_simulate(opt, opt.stream)[0]
    return run_analyze(opt)[0]


if __name__ == "__main__":
    sys.exit(main())
