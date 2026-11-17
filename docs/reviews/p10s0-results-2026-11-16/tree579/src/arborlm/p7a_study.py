"""P7-A study driver (ADR-0013): ``trace``, ``simulate``, ``analyze``, ``loader-smoke``,
``dry-run`` and ``budget``.

    uv run --locked --extra pilot python -m arborlm.p7a_study \
        {trace|simulate|analyze|loader-smoke|dry-run|budget}

``trace`` is the only stage that runs a model: for each of the 81 final P5 memory checkpoints
in the registered order it replays the recorded P5 NLL bitwise and writes the evaluation and
calibration traces. ``simulate`` and ``analyze`` are pure integer bookkeeping over those traces.
``loader-smoke`` restores one real parent/seed and replays the unmodified models' recorded NLL;
it computes and writes no trace. ``dry-run`` and ``budget`` use synthetic traces only and refuse
to write under ``experiments/`` or ``results/``.

Nothing here trains, downloads or edits a P1-P6 record. Status: implementation self-checked only.
"""

import argparse
import resource
import shlex
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from . import p6_common as common
from . import p7a_core as core
from . import p7a_stage as stages
from .io import canonical_json, file_sha256, read_json, write_json
from .p6_common import Pair, pair_label, pairs
from .p6_stage import git_head, require_completed
from .records import record_environment, runtime_supported

DEFAULT_RESULTS = Path("results/p7a-2026-11-13")
DRY_PAIRS, DRY_CONTEXTS = 2, 8
SMOKE_PAIR: Pair = (101, 301, 501)


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def calibration_slice(train: Any) -> Any:
    """The calibration stream of a real cell: training-pool ranks 2048-2559 of the frozen pool of
    4,096 ranked chunks (ADR-0013 section 3 and clarification 3); never the evaluation stream."""
    if train.shape[0] != 4096:
        raise ValueError("the frozen training pool does not hold 4,096 ranked chunks")
    return train[core.CAL_START : core.CAL_END]


def _checkpoints(pair_list: list[Pair]) -> list[tuple[Pair, str]]:
    return [(p, k) for p in pair_list for k in core.KINDS]


# --------------------------------------------------------------------------------------------------
# Trace worker (one supervised subprocess per parent/seed pair; its three checkpoints in order)
# --------------------------------------------------------------------------------------------------
def _worker_run(argv_run: str, expected_stage: str) -> Path:
    run = Path(argv_run)
    running = read_json(run / "manifest.json")
    if running["status"] != "running" or running.get("experiment_family") != core.FAMILY:
        raise ValueError("missing P7-A watchdog record")
    if running.get("question_id") != core.STUDY:
        raise ValueError("worker manifest does not cite P7-A")
    _ = expected_stage
    return run


def _trace_worker(argv: list[str]) -> int:
    from .p5_model import evaluate
    from .p7a_trace import GateViolation, configure_deterministic_cpu, trace_checkpoint

    (run_path, traces, parent_suite, output_root, p5_results, data_dir, b, o, s, contexts, syn) = (
        argv
    )
    run = _worker_run(run_path, "trace")
    configure_deterministic_cpu()
    pair: Pair = (int(b), int(o), int(s))
    n_contexts, synthetic = int(contexts), syn == "1"
    started = time.monotonic()
    records: list[dict[str, Any]] = []

    def write(outcome: str, **extra: Any) -> None:
        write_json(
            run / "result.json",
            {
                "schema": core.SCHEMA_TRACE,
                "outcome": outcome,
                "pair": list(pair),
                "records": records,
                "worker_seconds": time.monotonic() - started,
                "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
                **extra,
            },
        )

    try:
        if synthetic:
            source = common.load_synthetic_cell(pair, rows=n_contexts)
            calibration = source.train[16 : 16 + n_contexts]
        else:
            source = common.load_real_cell(
                pair,
                p5_suite=Path(parent_suite),
                output_root=Path(output_root),
                p5_results=Path(p5_results),
                data_dir=Path(data_dir),
                run=run,
            )
            calibration = calibration_slice(source.train)
        # load_real_cell writes P6's environment record into this folder; replace it with P7-A's.
        record_environment(run, family=core.FAMILY)
        for kind in core.KINDS:
            label = core.cell_label(pair, kind)
            if synthetic:
                recorded = evaluate(source.models[kind], source.panel, n_contexts * 64)["retrieval"]
            else:
                recorded = read_json(Path(p5_results) / label / "result.json")["final"]["retrieval"]
                if recorded is None:
                    raise ValueError(f"no recorded retrieval for {label}")
            t0 = time.monotonic()
            record = trace_checkpoint(
                source,
                kind,
                Path(traces) / label,
                contexts=n_contexts,
                calibration=calibration,
                recorded_retrieval=recorded,
            )
            record["seconds"] = time.monotonic() - t0
            records.append(record)
        if not source.files_unchanged():
            raise GateViolation("checkpoint_hash", "a P5 snapshot file changed during the worker")
        write("completed")
    except GateViolation as exc:
        write("gate_violation", gate=exc.gate, message=exc.message, details=exc.details)
        print(f"P7-A gate violation: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write("error", error=f"{type(exc).__name__}: {exc}")
        raise
    return 0


# --------------------------------------------------------------------------------------------------
# Simulation worker (one supervised subprocess per checkpoint; no model, no torch.nn)
# --------------------------------------------------------------------------------------------------
def _sim_worker(argv: list[str]) -> int:
    from .p7a_sim import CapExceeded, simulate_checkpoint
    from .p7a_trace import configure_deterministic_cpu

    run_path, trace_root, record_path, p5_results, syn = argv
    run = _worker_run(run_path, "simulate")
    configure_deterministic_cpu()  # the same single-thread deterministic configuration as P5/P6
    record_environment(run, family=core.FAMILY)
    limit = float(read_json(run / "manifest.json")["limits"]["process_seconds"])
    started = time.monotonic()
    deadline = started + max(limit - 5.0, 1.0)  # self-check first, so the partial is written
    source_before = core.source_hashes()
    trace = read_json(Path(record_path))
    label = trace["label"]
    pair, kind = core.parse_label(label)
    queries = int(trace["queries"])
    synthetic = syn == "1"

    def write(outcome: str, **extra: Any) -> None:
        write_json(
            run / "result.json",
            {
                "schema": core.SCHEMA_SIM,
                "outcome": outcome,
                "label": label,
                "kind": kind,
                "pair": list(pair),
                "cell_index": core.cell_index(pair, kind),
                "queries": queries,
                "worker_seconds": time.monotonic() - started,
                "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
                **extra,
            },
        )

    def progress(info: dict[str, Any]) -> None:
        write_json(run / "partial.json", {"label": label, **info})

    try:
        directory = Path(trace_root) / trace["trace_dir"]
        eval_sel, eval_br = core.read_trace(directory, "eval", trace["files"]["evaluation"])
        cal_sel, cal_br = core.read_trace(directory, "calib", trace["files"]["calibration"])
        recorded = (
            None
            if synthetic
            else read_json(Path(p5_results) / label / "result.json")["final"]["retrieval"]
        )
        core.check_trace(eval_sel, eval_br, kind, recorded=recorded, queries=queries)
        core.check_trace(cal_sel, cal_br, kind, queries=queries)
        record = simulate_checkpoint(
            kind=kind,
            index=core.cell_index(pair, kind),
            eval_selected=eval_sel,
            eval_branches=eval_br,
            calibration_selected=cal_sel,
            deadline=deadline,
            progress=progress,
        )
        if core.source_hashes() != source_before:
            raise ValueError("a p7a source file changed during the worker")
        write(
            "completed",
            trace={
                "run_id": Path(trace_root).parent.name,
                "files": trace["files"],
                "record": Path(record_path).name,
            },
            p7a_source_sha256=source_before,
            spec_sha256=core.spec_sha256(),
            record=record,
        )
    except CapExceeded as exc:
        write(
            "cap_exceeded",
            gate="resource_cap",
            message=str(exc),
            partial=getattr(exc, "partial", None),
        )
        print(f"P7-A cap exceeded: {exc}", file=sys.stderr)
        return 1
    except (core.TraceIntegrityError, core.InvariantError) as exc:
        gate = "trace_integrity" if isinstance(exc, core.TraceIntegrityError) else "invariant"
        write("gate_violation", gate=gate, message=str(exc))
        print(f"P7-A {gate}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write("error", error=f"{type(exc).__name__}: {exc}")
        raise
    return 0


# --------------------------------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------------------------------
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
        self.trace_run: str | None = getattr(args, "trace_run", None)
        self.simulate_run: str | None = getattr(args, "simulate_run", None)
        self.independent_check: Path | None = getattr(args, "independent_check", None)
        self.independent_expected: list[str] | None = None  # None: the registered selection
        self.dry_run = False
        self.pair_list: list[Pair] = pairs()
        self.contexts = core.CONTEXTS
        self.synthetic = False
        if (self.supersede is None) != (not self.reason):
            raise SystemExit("--supersede and --reason must be given together")

    def arguments(self) -> dict[str, Any]:
        return {
            "data_dir": str(self.data_dir),
            "parent_suite": str(self.parent_suite),
            "output_root": str(self.output_root),
            "results_root": str(self.results_root),
            "p5_results": str(self.p5_results),
            "supersede": self.supersede,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "pairs": len(self.pair_list),
            "contexts": self.contexts,
            "synthetic": self.synthetic,
            "independent_check": None
            if self.independent_check is None
            else str(self.independent_check),
        }


def _argv(opt: Options) -> list[str]:
    return [sys.executable, "-m", "arborlm.p7a_study", *sys.argv[1:]]


def run_trace(opt: Options) -> tuple[int, Path]:
    labels = [core.cell_label(p, k) for p, k in _checkpoints(opt.pair_list)]
    context = stages.open_stage(
        "trace",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=opt.dry_run,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
    )
    traces = context.run / "traces"
    status, reason = "failed", None
    outcome: stages.WorkerOutcome | None = None
    checkpoints = context.compact / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    done: dict[str, dict[str, Any]] = {}

    def keep(label: str, _child: Path, result: dict[str, Any]) -> None:
        for record in result.get("records", []):
            write_json(checkpoints / f"{record['label']}.json", record)
            done[record["label"]] = record

    def argv_for(label: str, child: Path) -> list[str]:
        pair = next(p for p in opt.pair_list if pair_label(p) == label)
        return [
            sys.executable,
            "-m",
            "arborlm.p7a_study",
            "_trace",
            str(child),
            str(traces),
            str(opt.parent_suite),
            str(opt.output_root.resolve()),
            str(opt.p5_results),
            str(opt.data_dir),
            *map(str, pair),
            str(opt.contexts),
            "1" if opt.synthetic else "0",
        ]

    try:
        outcome = stages.run_workers(
            context,
            [(pair_label(p), {"pair": list(p)}) for p in opt.pair_list],
            argv_for=argv_for,
            cap_seconds=core.TRACE_CAP,
            after_worker=keep,
        )
        reason = outcome.reason
        status = outcome.status
        if status == "completed" and sorted(done) != sorted(labels):
            status, reason = "failed", "not every registered checkpoint produced a trace record"
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result = {
            "stage": "trace",
            "checkpoints_expected": len(labels),
            "checkpoints_completed": len(done),
            "completed_labels": sorted(done),
            "unexecuted_or_failed": [lb for lb in labels if lb not in done],
            "active_seconds": outcome.active_seconds if outcome else None,
            "peak_rss_bytes": outcome.peak_rss_bytes if outcome else None,
            "workers": outcome.rows if outcome else [],
            "trace_directory": "traces",
            "trace_sha256": {
                lb: {
                    part: {n: e["sha256"] for n, e in rec["files"][part].items() if e}
                    for part in ("evaluation", "calibration")
                }
                for lb, rec in sorted(done.items())
            },
        }
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-A trace {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


def _consumed(results_root: Path, stage: str, run_id: str | None, dry: bool) -> Path:
    return require_completed(results_root, stage, run_id, dry_run=dry)


def run_simulate(opt: Options) -> tuple[int, Path]:
    trace_compact = _consumed(opt.results_root, "trace", opt.trace_run, opt.dry_run)
    trace_result = read_json(trace_compact / "result.json")
    trace_manifest = read_json(trace_compact / "manifest.json")
    expected = [core.cell_label(p, k) for p, k in _checkpoints(opt.pair_list)]
    if sorted(trace_result["completed_labels"]) != sorted(expected):
        raise SystemExit("simulate requires a completed trace stage covering every checkpoint")
    trace_active = float(trace_result.get("active_seconds") or 0.0)
    cap = min(core.SIM_CAP, core.COMBINED_CAP - trace_active)
    trace_run_dir = opt.output_root / trace_compact.name
    linkage = {
        "trace_run_id": trace_compact.name,
        "trace_manifest_sha256": file_sha256(trace_compact / "manifest.json"),
        "trace_result_sha256": file_sha256(trace_compact / "result.json"),
        "trace_p7a_source_sha256": trace_manifest["p7a_source_sha256"],
        "trace_active_seconds": trace_active,
    }
    context = stages.open_stage(
        "simulate",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=opt.dry_run,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        cap_seconds=cap,
        linkage=linkage,
    )
    outcome: stages.WorkerOutcome | None = None
    status, reason = "failed", None
    traces = trace_run_dir / "traces"

    def argv_for(label: str, child: Path) -> list[str]:
        return [
            sys.executable,
            "-m",
            "arborlm.p7a_study",
            "_sim",
            str(child),
            str(traces),
            str(trace_compact / "checkpoints" / f"{label}.json"),
            str(opt.p5_results),
            "1" if opt.synthetic else "0",
        ]

    try:
        outcome = stages.run_workers(
            context,
            [(lb, {}) for lb in expected],
            argv_for=argv_for,
            cap_seconds=cap,
            slack=0.0,
        )
        status, reason = outcome.status, outcome.reason
    except BaseException as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        rows = outcome.rows if outcome else []
        result = {
            "stage": "simulate",
            "checkpoints_expected": len(expected),
            "checkpoints_completed": sum(1 for r in rows if r.get("outcome") == "completed"),
            "active_seconds": outcome.active_seconds if outcome else None,
            "peak_rss_bytes": outcome.peak_rss_bytes if outcome else None,
            "cap_seconds": cap,
            "workers": rows,
            "linkage": linkage,
        }
        final = stages.finish(context, status, reason, result)
    print(
        f"P7-A simulate {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


def load_simulation_records(results_root: Path, run_id: str) -> dict[str, dict[str, Any]]:
    """Per-checkpoint simulation results of a simulate run; a missing, failed or partial worker
    output is returned as a record without ``record.complete`` and never raises."""
    folder = results_root / "simulate" / run_id / "workers"
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.result.json")):
        label = path.name.removesuffix(".result.json")
        try:
            data = read_json(path)
        except (OSError, ValueError):
            continue
        if data.get("outcome") == "completed" and data.get("record", {}).get("complete"):
            records[label] = data
    return records


def check_linkage(
    opt: Options, simulate_compact: Path, records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Analysis linkage: the simulate run points at one completed trace run whose manifest and
    result hashes it recorded; every simulation record cites the same trace files; the p7a sources
    and the spec are identical across the stages."""
    sim_manifest = read_json(simulate_compact / "manifest.json")
    link = sim_manifest["linkage"]
    trace_compact = opt.results_root / "trace" / link["trace_run_id"]
    problems: list[str] = []
    if (
        file_sha256(trace_compact / "manifest.json") != link["trace_manifest_sha256"]
        or file_sha256(trace_compact / "result.json") != link["trace_result_sha256"]
    ):
        problems.append(
            "trace manifest or result differs from the hashes the simulate run recorded"
        )
    trace_manifest = read_json(trace_compact / "manifest.json")
    if trace_manifest["p7a_source_sha256"] != sim_manifest["p7a_source_sha256"]:
        problems.append("p7a sources differ between the trace and simulate stages")
    if trace_manifest["spec_sha256"] != sim_manifest["spec_sha256"]:
        problems.append("spec hash differs between the trace and simulate stages")
    for label, rec in records.items():
        recorded = trace_compact / "checkpoints" / f"{label}.json"
        if not recorded.is_file() or read_json(recorded)["files"] != rec["trace"]["files"]:
            problems.append(
                f"{label}: simulation cites trace files that differ from the trace record"
            )
        if rec.get("p7a_source_sha256") != sim_manifest["p7a_source_sha256"]:
            problems.append(f"{label}: p7a sources differ from the simulate manifest")
    if problems:
        raise ValueError("analysis linkage check failed: " + "; ".join(problems))
    return {**link, "checked_records": len(records)}


def check_frozen_against_simulate(sim_manifest: dict[str, Any]) -> dict[str, Any]:
    """ADR-0013 section 14 item 11: analysis refuses unless the current p7a source hashes, the
    specification hash and the Git HEAD equal those the simulation stage recorded."""
    current = {
        "p7a_source_sha256": core.source_hashes(),
        "spec_sha256": core.spec_sha256(),
        "git_head": git_head()[0],
    }
    problems = [
        f"{name} differs from the simulate stage's"
        for name, value in current.items()
        if value != sim_manifest.get(name)
    ]
    if problems:
        raise ValueError("analysis refused: " + "; ".join(problems))
    return {"checked": list(current), "equal_to_simulate_manifest": True}


def _argv_value(argv: list[Any], flag: str) -> str | None:
    for i, item in enumerate(argv):
        if item == flag and i + 1 < len(argv):
            return str(argv[i + 1])
        if isinstance(item, str) and item.startswith(flag + "="):
            return item.split("=", 1)[1]
    return None


def check_independent_comparison(
    path: Path | None,
    *,
    simulate_run_id: str,
    trace_run_id: str,
    expected_selection: list[str] | None = None,
    allow_small: bool = False,
) -> dict[str, Any]:
    """ADR-0013 section 14 item 12 and clarification 7: the analysis stage requires the summary JSON
    of ``docs/reviews/p7a-preflight-2026-11-13/independent_sim.py`` and refuses unless its verdict
    is AGREE, it used the registered checkpoint selection (the file lists exactly it, was run with
    ``--registered-selection``, and every listed checkpoint reports no difference and no integrity
    problem), it read this simulate run's workers (and this trace run's traces), and its tie rule
    is ascending. Returns a record that includes the file's SHA-256."""
    if path is None:
        raise ValueError(
            "analysis refused: --independent-check <independent_sim.py summary JSON> is required"
        )
    if not path.is_file():
        raise ValueError(f"analysis refused: independent-simulator file not found: {path}")
    try:
        data = read_json(path)
    except ValueError as exc:
        raise ValueError(
            f"analysis refused: independent-simulator file is not JSON: {exc}"
        ) from exc
    expected = core.independent_selection() if expected_selection is None else expected_selection
    argv = data.get("argv") if isinstance(data.get("argv"), list) else []
    problems: list[str] = []
    if data.get("verdict") != "AGREE":
        problems.append(f"verdict is {data.get('verdict')!r}, not 'AGREE'")
    selection = data.get("selection")
    if not isinstance(selection, list) or sorted(selection) != sorted(expected):
        problems.append("selection is not the registered clarification-7 selection")
    if "--registered-selection" not in argv:
        problems.append("it was not run with --registered-selection")
    if "--allow-small" in argv and not allow_small:
        problems.append("it was run with --allow-small (synthetic validation only)")
    if data.get("tie_rule") != "asc":
        problems.append(f"tie rule is {data.get('tie_rule')!r}, not the registered 'asc'")
    workers = _argv_value(argv, "--sim-workers")
    if workers is None or Path(workers).parts[-3:] != ("simulate", simulate_run_id, "workers"):
        problems.append(f"it did not read this simulate run ({simulate_run_id}) workers")
    traces = _argv_value(argv, "--trace-root")
    if traces is None or Path(traces).parts[-2:] != (trace_run_id, "traces"):
        problems.append(f"it did not read this trace run ({trace_run_id}) traces")
    checked = data.get("checkpoints")
    if not isinstance(checked, dict) or sorted(checked) != sorted(expected):
        problems.append("per-checkpoint results do not cover exactly the selection")
    else:
        for label, entry in sorted(checked.items()):
            if entry.get("differences") or entry.get("integrity_problems"):
                problems.append(f"{label}: differences or integrity problems are listed")
    if problems:
        raise ValueError(
            "analysis refused: independent-simulator gate failed: " + "; ".join(problems)
        )
    return {
        "file": str(path),
        "sha256": file_sha256(path),
        "verdict": data["verdict"],
        "tie_rule": data["tie_rule"],
        "checkpoints": len(expected),
        "selection": sorted(expected),
        "simulate_run_id": simulate_run_id,
        "trace_run_id": trace_run_id,
    }


def run_analyze(opt: Options) -> tuple[int, Path]:
    from .p7a_analysis import analyze_records

    sim_compact = _consumed(opt.results_root, "simulate", opt.simulate_run, opt.dry_run)
    sim_result = read_json(sim_compact / "result.json")
    sim_manifest = read_json(sim_compact / "manifest.json")
    frozen = check_frozen_against_simulate(sim_manifest)  # item 11: before anything is opened
    independent = check_independent_comparison(  # item 12
        opt.independent_check,
        simulate_run_id=sim_compact.name,
        trace_run_id=sim_manifest["linkage"]["trace_run_id"],
        expected_selection=opt.independent_expected,
        allow_small=opt.dry_run,
    )
    records = load_simulation_records(opt.results_root, sim_compact.name)
    linkage = {
        "frozen_against_simulate": frozen,
        "independent_simulator_check": independent,
        "independent_check_sha256": independent["sha256"],
        "simulate_run_id": sim_compact.name,
        "simulate_manifest_sha256": file_sha256(sim_compact / "manifest.json"),
        "simulate_result_sha256": file_sha256(sim_compact / "result.json"),
        "simulate_active_seconds": sim_result.get("active_seconds"),
    }
    chain = check_linkage(opt, sim_compact, records)
    linkage["checked"] = chain
    spent = float(sim_result.get("active_seconds") or 0.0) + float(
        chain.get("trace_active_seconds") or 0.0
    )
    cap = max(
        0.0,
        min(
            core.SIM_CAP - float(sim_result.get("active_seconds") or 0.0), core.COMBINED_CAP - spent
        ),
    )
    context = stages.open_stage(
        "analyze",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=sys.argv,
        arguments=opt.arguments(),
        dry_run=opt.dry_run,
        supersede=opt.supersede,
        supersede_reason=opt.reason,
        cap_seconds=cap,
        linkage=linkage,
    )
    budget = stages.Budget(cap)
    status, reason = "failed", None
    result: dict[str, Any] = {"stage": "analyze"}
    expected = _checkpoints(opt.pair_list) if opt.dry_run else None
    try:
        analysis = analyze_records(records, expected)
        write_json(context.compact / "analysis.json", analysis)
        write_json(context.run / "analysis.json", analysis)
        outcomes = {k: v["outcome"] for k, v in analysis["criteria"]["tree_kinds"].items()}
        result.update(
            checkpoints_expected=analysis["checkpoints_expected"],
            checkpoints_complete=analysis["checkpoints_complete"],
            missing_or_failed=analysis["missing_or_failed"],
            outcomes=outcomes,
            analysis_seconds=budget.elapsed(),
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
        f"P7-A analyze {final}: {context.run}",
        file=sys.stdout if final == "completed" else sys.stderr,
    )
    return (0 if final == "completed" else 1), context.run


# --------------------------------------------------------------------------------------------------
# loader-smoke, dry-run, budget
# --------------------------------------------------------------------------------------------------
def loader_smoke(opt: Options, pair: Pair = SMOKE_PAIR) -> dict[str, Any]:
    """Restore one real parent/seed with P6's loader (locate, hash verification, strict restore) and
    replay the unmodified models' recorded P5 NLL bitwise. No trace is computed or written; the
    only scratch folder is a temporary one outside experiments/ and results/."""
    from .p5_model import evaluate, state_digest
    from .p7a_trace import configure_deterministic_cpu

    configure_deterministic_cpu()
    assert opt.parent_suite is not None
    repo = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="p7a-loader-smoke-") as scratch:
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
            from .p7a_trace import bitwise_equal

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
        "p7a_quantities_computed": False,
        "note": "locate, hash verification, strict restore and unmodified bitwise NLL replay only; "
        "no trace, simulation or analysis; nothing written under results/ or experiments/",
    }


def _listing(*roots: Path) -> dict[str, list[str]]:
    return {str(r): sorted(p.name for p in r.iterdir()) if r.is_dir() else [] for r in roots}


def dry_run(args: argparse.Namespace) -> int:
    """All three stages on small synthetic traces in a temporary directory. Refuses to write under
    experiments/ or results/ and verifies that both are unchanged afterwards."""
    repo = Path.cwd().resolve()
    before = _listing(repo / "experiments", repo / "results")
    with tempfile.TemporaryDirectory(prefix="p7a-dry-run-") as scratch:
        root = Path(scratch)
        stages.registered_roots_refused(root)
        args.output_root, args.results_root = root / "experiments", root / "results"
        args.supersede = args.reason = None
        opt = Options(args)
        opt.dry_run, opt.synthetic = True, True
        opt.pair_list, opt.contexts = pairs()[:DRY_PAIRS], DRY_CONTEXTS
        opt.parent_suite = opt.parent_suite or root / "none"
        code, trace_run = run_trace(opt)
        summary: dict[str, Any] = {"trace": code}
        if code == 0:
            code, sim_run = run_simulate(opt)
            summary["simulate"] = code
        if code == 0:
            labels = [core.cell_label(p, k) for p, k in _checkpoints(opt.pair_list)]
            stand_in = root / "independent_check_stand_in.json"
            write_json(
                stand_in,
                {
                    "tool": "dry-run stand-in; NOT produced by independent_sim.py",
                    "argv": [
                        "independent_sim.py",
                        "--registered-selection",
                        "--allow-small",
                        "--trace-root",
                        str(trace_run / "traces"),
                        "--sim-workers",
                        str(opt.results_root / "simulate" / sim_run.name / "workers"),
                    ],
                    "selection": labels,
                    "tie_rule": "asc",
                    "checkpoints": {
                        lb: {"differences": [], "integrity_problems": []} for lb in labels
                    },
                    "verdict": "AGREE",
                },
            )
            opt.independent_check, opt.independent_expected = stand_in, labels
            code, ana_run = run_analyze(opt)
            summary["analyze"] = code
            analysis = read_json(next((opt.results_root / "analyze").glob("*/analysis.json")))
            summary["analysis_outcomes"] = {
                k: v["outcome"] for k, v in analysis["criteria"]["tree_kinds"].items()
            }
            summary["analysis_missing"] = len(analysis["missing_or_failed"])
        summary["scratch_deleted"] = True
    after = _listing(repo / "experiments", repo / "results")
    summary["experiments_and_results_unchanged"] = before == after
    print(canonical_json(summary).decode().strip())
    return 0 if code == 0 and before == after else 1


def budget(args: argparse.Namespace) -> int:
    """The mandatory timed dry run of section 10: the complete per-checkpoint configuration set on
    full-size synthetic traces (one flat, one tree), projected to 81 checkpoints against the
    3,600 s cap. Prints a report; writes nothing."""
    from .p7a_sim import config_count, simulate_checkpoint
    from .p7a_trace import synthetic_trace

    report: dict[str, Any] = {
        "command": "budget",
        "label": "measured wall time on synthetic traces; a projection, not a result",
        "queries": core.QUERIES,
        "cap_seconds": core.SIM_CAP,
    }
    seconds: dict[str, float] = {}
    for kind, index, seed in ((core.FLAT, 0, 7001), ("fixed_tree", 1, 7002)):
        t0 = time.monotonic()
        selected, branches = synthetic_trace(kind, seed)
        calibration, _ = synthetic_trace(kind, seed + 1000)
        made = time.monotonic() - t0
        t1 = time.monotonic()
        record = simulate_checkpoint(
            kind=kind,
            index=index,
            eval_selected=selected,
            eval_branches=branches,
            calibration_selected=calibration,
        )
        elapsed = time.monotonic() - t1
        seconds[kind] = elapsed
        report[kind] = {
            "synthetic_trace_seconds": made,
            "simulation_seconds": elapsed,
            "configurations": config_count(kind),
            "unique_selected_slots": record["evaluation_counts"]["unique_selected_slots"],
            "complete": record["complete"],
        }
    projected = 27 * seconds[core.FLAT] + 54 * seconds["fixed_tree"]
    report["projected_total_seconds_81_checkpoints"] = projected
    report["margin_against_cap"] = core.SIM_CAP / projected
    report["twofold_margin_met"] = core.SIM_CAP / projected >= 2.0
    report["note"] = (
        "in-process, excluding process start-up and trace reading (about a second per checkpoint) "
        "and the analysis stage; synthetic concentration is an implementer's guess"
    )
    report["peak_rss_bytes_ru_maxrss"] = _peak_rss_bytes()
    print(canonical_json(report).decode().strip())
    return 0 if report["twofold_margin_met"] else 1


def main() -> int:
    if sys.argv[1:2] == ["_trace"]:
        return _trace_worker(sys.argv[2:])
    if sys.argv[1:2] == ["_sim"]:
        return _sim_worker(sys.argv[2:])
    parser = argparse.ArgumentParser(description="P7-A storage-page locality study (ADR-0013)")
    parser.add_argument(
        "command", choices=("trace", "simulate", "analyze", "loader-smoke", "dry-run", "budget")
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data/wikitext2"))
    parser.add_argument("--parent-suite", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--p5-results", type=Path, default=core.P5_RESULTS)
    parser.add_argument("--supersede", help="run ID of an earlier run of the same stage")
    parser.add_argument("--reason", help="recorded reason for a deliberate rerun")
    parser.add_argument("--trace-run", help="simulate: trace run ID (default: the one completed)")
    parser.add_argument(
        "--simulate-run", help="analyze: simulate run ID (default: the one completed)"
    )
    parser.add_argument(
        "--independent-check",
        type=Path,
        help="analyze: summary JSON written by independent_sim.py (required; verdict AGREE, "
        "registered selection, this simulate run)",
    )
    args = parser.parse_args()
    if args.command == "budget":
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
    if args.command == "trace":
        if opt.parent_suite is None:
            parser.error("trace requires --parent-suite")
        return run_trace(opt)[0]
    if args.command == "simulate":
        return run_simulate(opt)[0]
    return run_analyze(opt)[0]


_ = (shlex, _argv)  # kept for command-line reproduction helpers

if __name__ == "__main__":
    sys.exit(main())
