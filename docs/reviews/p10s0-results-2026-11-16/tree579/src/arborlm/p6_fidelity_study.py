"""P6-Q routing-fidelity study driver (ADR-0011 Part Q), primary panel only.

``run`` evaluates the 54 final P5 tree checkpoints and the 27 shared step-0 tree checkpoints,
one supervised subprocess per checkpoint in a fixed order, under the caps of section 4.6.
``analyze`` computes the registered flags from the 54 final records (step 0 is summarized over
whatever completed). ``loader-smoke`` runs only the real loading path for one cell (locate, hash
verification, strict restore, bitwise replay of the unmodified model's recorded P5 NLL) and
reports wall time and peak RSS; it computes no rule, comparison or fidelity quantity and writes
nothing under ``results/`` or ``experiments/``. Nothing here trains, downloads or touches the
P1-P5 records; checkpoints are only read and hashed.

Budget rule: an item is started only if the remaining active budget is at least the per-checkpoint
cap (60 s), finals included. Otherwise it is recorded as ``unexecuted`` with the reason
``budget`` and a ``budget_exhausted_before_start`` event is logged, so a budget stop is never
confused with a slow or killed cell. When every final completed and the budget ended during
step 0, the suite ends with the distinct status ``completed_finals_step0_partial``.
"""

from __future__ import annotations

import argparse
import resource
import shlex
import struct
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .io import canonical_json, file_sha256, read_json, sha256, write_json
from .longer_training import IDENTITY_FIELDS
from .p2_config import BACKBONES, ORDERS
from .p5_config import (
    FIXED,
    LEARNED,
    PARENT_RESULTS,
    SEEDS,
    VAL_TARGETS,
    Cell,
    counters,
)
from .p5_config import PARENT_SUITE as P4_SUITE
from .p5_data import P5_VALIDATION_SHA256
from .pilot_model import Memory
from .records import (
    allocate_run,
    append_event,
    manifest,
    record_environment,
    record_source,
    runtime_supported,
    utc_now,
)
from .watchdog import RSS_BYTES, supervise

if TYPE_CHECKING:
    from torch import Tensor

    from .p5_model import Model

FAMILY = "P6Q_ROUTING_FIDELITY"
SPEC = "docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md"
SCHEMA = "P6Q-checkpoint-v1"
TOTAL_SECONDS = 1800
CHECKPOINT_SECONDS = 60
FINAL_STEP = 512
INITIAL = "shared_initial"
DEFAULT_P5_RESULTS = Path("results/p5-2026-11-13")
PARTIAL_STEP0 = "completed_finals_step0_partial"
BUDGET_DURING_FINALS = "stopped_budget_during_finals"
COMPLETED_OUTCOMES = ("completed", PARTIAL_STEP0)
EXPORT_FILES = ("result.json", "manifest.json", "terminal.json")
SUITE_EXPORT = ("manifest.json", "result.json", "terminal.json", "source.json", "environment.json")


@dataclass(frozen=True)
class Item:
    cell: Cell
    kind: str
    step: int

    @property
    def label(self) -> str:
        if self.kind == INITIAL:
            return f"b{self.cell.backbone}-o{self.cell.order}-{INITIAL}-s{self.cell.seed}"
        return f"{self.cell.label}-final"

    @property
    def record_kind(self) -> str:
        return "initial" if self.kind == INITIAL else "final"


def items() -> list[Item]:
    """Registered evaluation order: all 54 final tree checkpoints first (parent, then seed
    ascending; fixed, then learned), then the 27 shared step-0 checkpoints (parent, then seed
    ascending). The finals carry the registered flags; step 0 is descriptive."""
    result: list[Item] = []
    for b in BACKBONES:
        for o in ORDERS:
            for seed in SEEDS:
                result.append(Item(Cell(b, o, seed, FIXED), FIXED, FINAL_STEP))
                result.append(Item(Cell(b, o, seed, LEARNED), LEARNED, FINAL_STEP))
    for b in BACKBONES:
        for o in ORDERS:
            for seed in SEEDS:
                result.append(Item(Cell(b, o, seed, FIXED), INITIAL, 0))
    return result


def quality_directory(parent_suite: Path) -> Path:
    found = sorted((parent_suite / "quality").glob("P5QUALITY-*"))
    if len(found) != 1 or not found[0].is_dir():
        raise ValueError("expected exactly one P5 quality stage under the parent suite")
    return found[0]


# ---------------------------------------------------------------------------------------------
# Locating and verifying recorded P5 evidence
# ---------------------------------------------------------------------------------------------


@dataclass
class Evidence:
    folder: Path
    identity: dict[str, Any]
    result: dict[str, Any]
    state_sha256: dict[str, str]


def locate(quality: Path, p5_results: Path, cell: Cell) -> Evidence:
    """Find a P5 cell's original record folder and check it against the compact export."""
    summary = read_json(quality / "result.json")
    if summary["outcome"] != "completed":
        raise ValueError("P5 quality stage did not complete")
    rows = [row for row in summary["cells"] if row["label"] == cell.label]
    if len(rows) != 1:
        raise ValueError(f"P5 cell not found exactly once: {cell.label}")
    row = rows[0]
    run_id = row["run_id"]
    if (
        any(row[key] != value for key, value in cell.fields().items())
        or row["status"] != "completed"
        or Path(run_id).name != run_id
        or not run_id.startswith("P5HIER-")
    ):
        raise ValueError("P5 quality cell identity mismatch")
    folder = quality / "cells" / run_id
    compact = p5_results / cell.label
    for name in (
        "manifest.json",
        "result.json",
        "checkpoint-0/index.json",
        "checkpoint-512/index.json",
    ):
        if file_sha256(folder / name) != file_sha256(compact / name):
            raise ValueError(f"P5 original and compact evidence differ: {cell.label}/{name}")
    result = read_json(folder / "result.json")
    if result["outcome"] != "completed" or result["cell"] != cell.fields():
        raise ValueError("P5 recorded cell did not complete")
    return Evidence(
        folder,
        read_json(folder / "manifest.json")["checkpoint_identity"],
        result,
        result["checkpoint_state_sha256"],
    )


def verify_hashes(quality: Path, p5_results: Path) -> dict[str, str]:
    """Hash every checkpoint the study reads and compare with the P5 records."""
    seen: dict[str, str] = {}
    for item in items():
        evidence = locate(quality, p5_results, item.cell)
        peers = [item.cell]
        if item.kind == INITIAL:
            peers.append(Cell(item.cell.backbone, item.cell.order, item.cell.seed, LEARNED))
        for peer in peers:
            ev = evidence if peer == item.cell else locate(quality, p5_results, peer)
            for step in (0, FINAL_STEP):
                name = f"checkpoint-{step}"
                path = ev.folder / name / "state.pt"
                digest = file_sha256(path)
                if digest != ev.state_sha256[name]:
                    raise ValueError(f"checkpoint hash differs from the P5 record: {path}")
                seen[str(path)] = digest
    return seen


# ---------------------------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------------------------


def _restore(
    quality: Path,
    p5_results: Path,
    cell: Cell,
    step: int,
    backbone: Any,
    shared: dict[str, str],
    dataset_hash: str,
    order_sha256: str,
    parent_provenance: dict[str, Any],
) -> tuple[Model, Evidence]:
    from .p5_checkpoint import restore
    from .p5_model import Model, optimizer_for

    evidence = locate(quality, p5_results, cell)
    identity = evidence.identity
    path = evidence.folder / f"checkpoint-{step}"
    digest = file_sha256(path / "state.pt")
    if (
        identity["parent"] != parent_provenance
        or identity["cell"] != cell.fields()
        or identity["dataset_manifest_sha256"] != dataset_hash
        or identity["order_sha256"] != order_sha256
        or any(identity[key] != value for key, value in shared.items())
        or digest != evidence.state_sha256[path.name]
    ):
        raise ValueError("P6-Q checkpoint identity mismatch")
    model = Model(cell, backbone)
    optimizer = optimizer_for(model)
    if restore(path, model, optimizer, identity) != counters(step):
        raise ValueError("P6-Q checkpoint cursor mismatch")
    return model, evidence


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


@dataclass
class Prepared:
    model: Model
    panel: Tensor
    evidence: Evidence
    recorded: dict[str, Any]
    initial_tensors: tuple[Tensor, Tensor] | None
    shared_initial: dict[str, Any] | None
    hash_paths: dict[str, Path]
    hashes_before: dict[str, str]
    parent: Any


def prepare(
    run: Path,
    quality: Path,
    p4_suite: Path,
    data_dir: Path,
    p5_results: Path,
    item: Item,
) -> Prepared:
    """Load, verify and restore everything needed for one checkpoint (no P6-Q measurement)."""
    from .engine import configure_cpu
    from .p3_checkpoint import bitwise_equal
    from .p5_config import validate_config
    from .p5_data import load_frozen
    from .p5_parent import extract_verified, verify_parent

    runtime_supported()
    environment = record_environment(run, family=FAMILY)
    configure_cpu()
    validate_config(read_json(quality / "config.resolved.json"))
    quality_manifest = read_json(quality / "manifest.json")
    shared = {name: quality_manifest[name] for name in IDENTITY_FIELDS}
    dataset_hash = quality_manifest["dataset_manifest_sha256"]
    _, _, panel, dataset = load_frozen(quality / "frozen-data", dataset_hash)
    if file_sha256(data_dir / "manifest.json") != dataset["checksums_sha256"]["acquisition.json"]:
        raise ValueError("local WikiText-2 acquisition manifest differs from the frozen panel's")
    bundle = read_json(quality / "parent_provenance.json")
    if sha256(canonical_json(bundle)) != quality_manifest["parent_provenance_sha256"]:
        raise ValueError("P5 parent map identity mismatch")
    mapping = bundle[item.cell.parent_label]
    parent = verify_parent(p4_suite, PARENT_RESULTS, mapping["record"], environment)
    if parent.provenance != mapping["provenance"]:
        raise ValueError("P5 parent differs from the recorded parent")
    backbone = extract_verified(parent)
    order_sha256 = parent.identity["order_sha256"]

    def restore_cell(cell: Cell, step: int) -> tuple[Model, Evidence]:
        return _restore(
            quality,
            p5_results,
            cell,
            step,
            backbone,
            shared,
            dataset_hash,
            order_sha256,
            parent.provenance,
        )

    model, evidence = restore_cell(item.cell, item.step)
    recorded = evidence.result["final" if item.step == FINAL_STEP else "initial"]
    hash_paths = {
        f"checkpoint-{step}": evidence.folder / f"checkpoint-{step}" / "state.pt"
        for step in (0, FINAL_STEP)
    }
    hashes_before = {name: file_sha256(path) for name, path in hash_paths.items()}
    shared_initial: dict[str, Any] | None = None
    initial_tensors: tuple[Tensor, Tensor] | None = None
    if item.kind == INITIAL:
        peer_cell = Cell(item.cell.backbone, item.cell.order, item.cell.seed, LEARNED)
        peer, peer_evidence = restore_cell(peer_cell, 0)
        identical = (
            bitwise_equal(dict(model.state_dict()), dict(peer.state_dict()))
            and canonical_json(peer_evidence.result["initial"]) == canonical_json(recorded)
            and model.bypass is peer.bypass
        )
        if not identical:
            raise ValueError("fixed and learned step-0 checkpoints are not identical")
        shared_initial = {
            "fixed_learned_state_and_recorded_metrics_identical": True,
            "learned_peer": peer_cell.label,
            "learned_state_sha256": peer_evidence.state_sha256["checkpoint-0"],
        }
    else:
        init_model, _ = restore_cell(item.cell, 0)
        init_memory = init_model.addition
        if not isinstance(init_memory, Memory):
            raise ValueError("P6-Q requires a tree memory")
        initial_tensors = (init_memory.keys.detach().clone(), init_memory.values.detach().clone())
        del init_model
    return Prepared(
        model,
        panel,
        evidence,
        recorded,
        initial_tensors,
        shared_initial,
        hash_paths,
        hashes_before,
        parent,
    )


def _measure(
    run: Path,
    quality: Path,
    p4_suite: Path,
    data_dir: Path,
    p5_results: Path,
    item: Item,
) -> dict[str, Any]:
    from .p6_fidelity import SCHEMA as FIDELITY_SCHEMA
    from .p6_fidelity import evaluate_checkpoint, load_reference, write_array

    if FIDELITY_SCHEMA != SCHEMA:
        raise ValueError("record schema mismatch")
    started = time.monotonic()
    ready = prepare(run, quality, p4_suite, data_dir, p5_results, item)
    prepared_seconds = time.monotonic() - started
    fragment, arrays = evaluate_checkpoint(
        ready.model,
        ready.panel,
        recorded_nll=ready.recorded["nll"],
        recorded_retrieval=ready.recorded["retrieval"],
        initial_tensors=ready.initial_tensors,
        reference=load_reference(),
        expected_targets=VAL_TARGETS,
    )
    array_dir = run / "arrays"
    array_dir.mkdir(mode=0o700)
    array_record = {name: write_array(array_dir, name, tensor) for name, tensor in arrays.items()}
    hashes_after = {name: file_sha256(path) for name, path in ready.hash_paths.items()}
    if hashes_after != ready.hashes_before or any(
        hashes_after[name] != ready.evidence.state_sha256[name] for name in hashes_after
    ):
        raise ValueError("a P5 checkpoint changed during the P6-Q evaluation")
    ready.parent.check_unchanged()
    return {
        "schema": SCHEMA,
        "outcome": "completed",
        "label": item.label,
        "kind": item.record_kind,
        "cell": item.cell.fields(),
        "step": item.step,
        "panel": {
            "ranks": [2048, 2560],
            "sha256": P5_VALIDATION_SHA256,
            "queries": VAL_TARGETS,
        },
        "checkpoint": {
            "state_sha256_before": ready.hashes_before,
            "state_sha256_after": hashes_after,
            "recorded_state_sha256": ready.evidence.state_sha256,
            "p5_quality_run_id": ready.evidence.folder.name,
        },
        "shared_initial": ready.shared_initial,
        "resources": {
            "prepare_wall_seconds": prepared_seconds,
            "worker_wall_seconds": time.monotonic() - started,
            "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
        },
        "arrays": array_record,
        **fragment,
    }


def _worker(argv: list[str]) -> int:
    from .p6_fidelity import GateViolation

    run_path, quality, p4_suite, data_dir, p5_results, b, o, seed, kind, step = argv
    run = Path(run_path)
    running = read_json(run / "manifest.json")
    if running["status"] != "running" or running["experiment_family"] != FAMILY:
        raise ValueError("missing P6-Q watchdog record")
    variant = FIXED if kind == INITIAL else kind
    item = Item(Cell(int(b), int(o), int(seed), variant), kind, int(step))
    try:
        record = _measure(
            run, Path(quality), Path(p4_suite), Path(data_dir), Path(p5_results), item
        )
    except GateViolation as exc:
        write_json(
            run / "result.json",
            {
                "schema": SCHEMA,
                "outcome": "gate_violation",
                "label": item.label,
                "gate": exc.gate,
                "message": exc.message,
                "details": exc.details,
            },
        )
        print(f"P6-Q gate violation: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write_json(
            run / "result.json",
            {
                "schema": SCHEMA,
                "outcome": "error",
                "label": item.label,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
    write_json(run / "result.json", record)
    return 0


# ---------------------------------------------------------------------------------------------
# Suite
# ---------------------------------------------------------------------------------------------


def _export(source: Path, destination: Path, names: tuple[str, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for name in names:
        if (source / name).exists():
            write_json(destination / name, read_json(source / name))


def _bitwise(first: float, second: float) -> bool:
    return struct.pack("!d", first) == struct.pack("!d", second)


def _preflight() -> dict[str, Any]:
    """Synthetic check that the auditor's reference and the frozen tree rule are callable."""
    import torch

    from .p6_fidelity import load_reference
    from .pilot_model import tree_candidates

    reference = load_reference()
    generator = torch.Generator().manual_seed(0)
    keys = torch.randn(4096, 16, generator=generator) * 0.02
    router = torch.randn(16, 16, generator=generator) * 0.02
    q = torch.nn.functional.normalize(torch.randn(64, 16, generator=generator), dim=-1)
    routes = (q @ torch.nn.functional.normalize(router, dim=-1, eps=1e-8).T) / 0.2
    _, ids, _ = reference(q, keys, router, use_prior=True)
    _, selected, _, _ = tree_candidates(q, keys, routes, visit=16, use_prior=True)
    return {"synthetic_queries": 64, "frozen_equals_reference": bool(torch.equal(ids, selected))}


def _worker_argv(
    item: Item, quality: Path, p4_suite: Path, data_dir: Path, p5_results: Path
) -> Callable[[Path], list[str]]:
    def argv(child_run: Path) -> list[str]:
        return [
            sys.executable,
            "-m",
            "arborlm.p6_fidelity_study",
            "_cell",
            str(child_run),
            str(quality),
            str(p4_suite),
            str(data_dir),
            str(p5_results),
            str(item.cell.backbone),
            str(item.cell.order),
            str(item.cell.seed),
            item.kind,
            str(item.step),
        ]

    return argv


def run_study(args: argparse.Namespace) -> int:
    root = args.output_root.resolve()
    results_root = args.results_root.resolve()
    parent_suite = args.parent_suite.resolve()
    data_dir = args.data_dir.resolve()
    p5_results = args.p5_results.resolve()
    p4_suite = (args.p4_suite or parent_suite.parent / P4_SUITE).resolve()
    if results_root.exists() and any(results_root.iterdir()):
        raise SystemExit(f"refusing to overwrite existing results root: {results_root}")
    quality = quality_directory(parent_suite)
    run = allocate_run(root, prefix="P6Q")
    cwd = Path.cwd()
    source = record_source(run, cwd, spec=SPEC)
    environment = record_environment(run, family=FAMILY)
    git_root = Path(source["git_root"])
    p6_sources = {
        path.relative_to(git_root).as_posix(): file_sha256(path)
        for path in sorted((git_root / "src" / "arborlm").glob("p6_*.py"))
    }
    from .p6_fidelity import KNOWN_LIMITS

    started = utc_now()
    wall_start = time.monotonic()
    running = manifest(
        run,
        "p6q_suite",
        experiment_family=FAMILY,
        question_id="P6-Q",
        hypothesis="routing fidelity of top-2 branch search against exhaustive search",
        hypothesis_null_reason=None,
        authorized_spec_reference=SPEC,
        spec_sha256=source["spec_sha256"],
        p6_source_sha256=p6_sources,
        cwd=str(cwd),
        argv=[sys.executable, "-m", "arborlm.p6_fidelity_study", *sys.argv[1:]],
        requested_argv=sys.argv,
        command=shlex.join(sys.argv),
        code_commit=source["code_commit"],
        dirty=source["dirty"],
        source_sha256=source["archive"]["sha256"],
        lock_sha256=source["lock_sha256"],
        environment=environment,
        parent_suite=str(parent_suite),
        p4_suite=str(p4_suite),
        p5_results=str(p5_results),
        data_dir=str(data_dir),
        results_root=str(results_root),
        limits={
            "total_active_worker_seconds": TOTAL_SECONDS,
            "checkpoint_seconds": CHECKPOINT_SECONDS,
            "rss_bytes": RSS_BYTES,
        },
        panel="P5 primary panel only (ranks 2048-2560); replication panel not approved",
        known_limits=list(KNOWN_LIMITS),
        started_utc=started,
    )
    write_json(run / "manifest.json", running)
    (run / "metrics.jsonl").touch()
    status: list[dict[str, Any]] = []
    active = 0.0
    outcome, reason = "completed", None
    stop_kind: str | None = None  # None, "budget" or "failure"
    try:
        preflight = _preflight()
        append_event(run, {"event": "preflight", **preflight})
        if preflight.get("frozen_equals_reference") is not True:
            raise ValueError(
                "P6-Q stop: the frozen tree rule and the independent reference disagree in the "
                "preflight on synthetic tensors"
            )
        hashes = verify_hashes(quality, p5_results)
        write_json(run / "checkpoint_hashes_before.json", hashes)
        for item in items():
            if stop_kind is not None:
                status.append(
                    {
                        "label": item.label,
                        "status": "unexecuted",
                        "reason": f"stage stopped earlier ({stop_kind})",
                    }
                )
                continue
            remaining = TOTAL_SECONDS - active
            if remaining < CHECKPOINT_SECONDS:
                stop_kind = "budget"
                reason = (
                    f"budget: {remaining:.1f} s of the {TOTAL_SECONDS} s total remain, below the "
                    f"{CHECKPOINT_SECONDS} s per-checkpoint cap, before {item.label}"
                )
                outcome = PARTIAL_STEP0 if item.record_kind == "initial" else BUDGET_DURING_FINALS
                append_event(
                    run,
                    {
                        "event": "budget_exhausted_before_start",
                        "label": item.label,
                        "kind": item.record_kind,
                        "remaining_seconds": remaining,
                        "per_checkpoint_cap_seconds": CHECKPOINT_SECONDS,
                        "terminal_status": outcome,
                    },
                )
                status.append({"label": item.label, "status": "unexecuted", "reason": "budget"})
                continue
            child, ok = supervise(
                run / "cells",
                "_p6q_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CHECKPOINT_SECONDS,
                rss_bytes=RSS_BYTES,
                worker_argv=_worker_argv(item, quality, p4_suite, data_dir, p5_results),
                manifest_fields={
                    "experiment_family": FAMILY,
                    "question_id": "P6-Q",
                    "authorized_spec_reference": SPEC,
                    "label": item.label,
                    "cell": item.cell.fields(),
                    "step": item.step,
                    "code_commit": source["code_commit"],
                    "dirty": source["dirty"],
                    "spec_sha256": source["spec_sha256"],
                    "parent_suite_run": run.name,
                },
                run_prefix="P6QCELL",
            )
            terminal = read_json(child / "terminal.json")
            active += float(terminal["process_wall_seconds"])
            row = {
                "label": item.label,
                "status": terminal["status"],
                "reason": terminal["reason"],
                "run_id": child.name,
                "wall_seconds": terminal["process_wall_seconds"],
                "peak_rss_bytes": terminal["peak_process_tree_rss_bytes"],
                "active_seconds_cumulative": active,
                "started_with_remaining_seconds": remaining,
            }
            _export(child, results_root / "cells" / item.label, EXPORT_FILES)
            status.append(row)
            write_json(run / "cells.json", status)
            append_event(run, {"event": "checkpoint_finished", **row})
            print(canonical_json(row).decode().strip(), flush=True)
            if not ok:
                result = (
                    read_json(child / "result.json") if (child / "result.json").exists() else {}
                )
                outcome, stop_kind = "stopped", "failure"
                reason = f"{item.label}: {terminal['reason']}" + (
                    f" [{result.get('gate')}]" if result.get("gate") else ""
                )
        if outcome in COMPLETED_OUTCOMES:
            after = verify_hashes(quality, p5_results)
            if after != hashes:
                raise ValueError("a P5 checkpoint changed during the P6-Q study")
            write_json(run / "checkpoint_hashes_after.json", after)
    except BaseException as exc:
        outcome, reason = "stopped", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        finals = [r for r in status if r["label"].endswith("-final")]
        step0 = [r for r in status if not r["label"].endswith("-final")]
        finished = {
            "outcome": outcome,
            "reason": reason,
            "cells": status,
            "active_worker_seconds": active,
            "suite_wall_seconds": time.monotonic() - wall_start,
            "checkpoints_total": len(items()),
            "checkpoints_completed": sum(1 for row in status if row.get("status") == "completed"),
            "finals_completed": sum(1 for r in finals if r.get("status") == "completed"),
            "step0_completed": sum(1 for r in step0 if r.get("status") == "completed"),
            "step0_unexecuted": sum(1 for r in step0 if r.get("status") == "unexecuted"),
        }
        write_json(run / "result.json", finished)
        terminal_suite = {
            "status": outcome if outcome in COMPLETED_OUTCOMES else "failed",
            "outcome": outcome,
            "reason": reason,
            "finished_utc": utc_now(),
            "active_worker_seconds": active,
        }
        write_json(run / "terminal.json", terminal_suite)
        current = read_json(run / "manifest.json")
        current.update(terminal_suite)
        write_json(run / "manifest.json", current)
        write_json(run / "cells.json", status)
        if not (results_root / "suite").exists():
            _export(run, results_root / "suite", SUITE_EXPORT)
    done = outcome in COMPLETED_OUTCOMES
    print(f"P6-Q {outcome}: {run}", file=sys.stdout if done else sys.stderr)
    return 0 if done else 1


def analyze_study(args: argparse.Namespace) -> int:
    from .p6_fidelity_analysis import analyze

    results_root = args.results_root.resolve()
    records: list[dict[str, Any]] = []
    for path in sorted((results_root / "cells").glob("*/")):
        if (path / "result.json").is_file():
            records.append(read_json(path / "result.json"))
            continue
        # A cell killed by the watchdog leaves no result.json: keep it visible, never crash.
        terminal = read_json(path / "terminal.json") if (path / "terminal.json").is_file() else None
        records.append(
            {
                "label": path.name,
                "outcome": "no_result_json",
                "terminal": terminal,
                "files": sorted(p.name for p in path.iterdir()),
            }
        )
    statuses: dict[str, dict[str, Any]] = {}
    suite: dict[str, Any] | None = None
    suite_result = results_root / "suite" / "result.json"
    if suite_result.is_file():
        data = read_json(suite_result)
        statuses = {row["label"]: row for row in data.get("cells", [])}
        suite = {
            name: data.get(name)
            for name in (
                "outcome",
                "reason",
                "active_worker_seconds",
                "checkpoints_total",
                "checkpoints_completed",
                "finals_completed",
                "step0_completed",
                "step0_unexecuted",
            )
        }
    out = results_root / "analysis.json"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    write_json(out, analyze(records, statuses, suite))
    print(f"wrote {out}")
    return 0


def resolve_item(cell_label: str, step: str) -> Item:
    """The registered item for a cell label such as ``b101-o301-fixed_tree-s501``."""
    found = [i for i in items() if i.cell.label == cell_label and i.record_kind == step]
    if len(found) != 1:
        raise SystemExit(f"no registered {step} item for cell {cell_label!r}")
    return found[0]


def loader_smoke(args: argparse.Namespace) -> dict[str, Any]:
    """Real loading path for one registered item and the unmodified bitwise replay. Nothing else.

    Runs ``prepare`` (locate, hash verification, parent verification, strict restore) and the
    unmodified-model replay of the recorded P5 NLL. It never imports the rule, reference or
    measurement code, and writes only into a temporary folder outside ``results/`` and
    ``experiments/``.
    """
    from .p5_model import evaluate

    item = resolve_item(args.cell, args.step)
    parent_suite = args.parent_suite.resolve()
    quality = quality_directory(parent_suite)
    p4_suite = (args.p4_suite or parent_suite.parent / P4_SUITE).resolve()
    repo = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="p6q-loader-smoke-") as scratch:
        run = Path(scratch).resolve()
        for protected in (repo / "experiments", repo / "results"):
            if run.is_relative_to(protected):
                raise SystemExit(
                    "loader-smoke scratch folder must be outside experiments/ results/"
                )
        started = time.perf_counter()
        ready = prepare(
            run, quality, p4_suite, args.data_dir.resolve(), args.p5_results.resolve(), item
        )
        prepared = time.perf_counter()
        replay = evaluate(ready.model, ready.panel, VAL_TARGETS)
        replayed = time.perf_counter()
        hashes_after = {name: file_sha256(path) for name, path in ready.hash_paths.items()}
        ready.parent.check_unchanged()
    bitwise = _bitwise(replay["nll"], ready.recorded["nll"])
    return {
        "command": "loader-smoke",
        "study": "P6-Q",
        "label": item.label,
        "step": item.step,
        "prepare_seconds": prepared - started,
        "replay_seconds": replayed - prepared,
        "wall_seconds": replayed - started,
        "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
        "recorded_nll": ready.recorded["nll"],
        "replayed_nll": replay["nll"],
        "replay_bitwise_equal": bitwise,
        "checkpoint_files_unchanged": hashes_after == ready.hashes_before,
        "p6_quantities_computed": False,
        "note": "locate, hash verification, strict restore and unmodified bitwise replay only; no "
        "rule substitution, reference, recall or fidelity quantity; nothing written under "
        "results/ or experiments/",
    }


def main() -> int:
    if sys.argv[1:2] == ["_cell"]:
        return _worker(sys.argv[2:])
    parser = argparse.ArgumentParser(description="P6-Q routing-fidelity study (primary panel)")
    parser.add_argument("command", choices=("run", "analyze", "loader-smoke"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/wikitext2"))
    parser.add_argument("--parent-suite", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--results-root", type=Path)
    parser.add_argument("--p4-suite", type=Path)
    parser.add_argument("--p5-results", type=Path, default=DEFAULT_P5_RESULTS)
    parser.add_argument("--cell", help="loader-smoke: cell label, e.g. b101-o301-fixed_tree-s501")
    parser.add_argument("--step", choices=("final", "initial"), help="loader-smoke: checkpoint")
    args = parser.parse_args()
    if args.command == "loader-smoke":
        if args.parent_suite is None or args.cell is None or args.step is None:
            parser.error("loader-smoke requires --parent-suite, --cell and --step")
        runtime_supported()
        report = loader_smoke(args)
        print(canonical_json(report).decode().strip(), flush=True)
        ok = report["replay_bitwise_equal"] and report["checkpoint_files_unchanged"]
        return 0 if ok else 1
    if args.results_root is None:
        parser.error(f"{args.command} requires --results-root")
    if args.command == "analyze":
        return analyze_study(args)
    if args.parent_suite is None:
        parser.error("run requires --parent-suite")
    runtime_supported()
    return run_study(args)


if __name__ == "__main__":
    sys.exit(main())
