"""Watchdog-bound ADR-0009 matrix and compact per-cell evidence."""

from __future__ import annotations

import argparse
import math
import random
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .longer_training import IDENTITY_FIELDS, _bitwise_nll, _isolated_rng
from .optimization_followup import (
    CELL_EXPORT,
    DATA_APPROVAL,
    _export,
    _follow_stdout,
    _optimizer,
    _permutation,
    _source_unchanged,
    _update,
)
from .p4_config import (
    BASELINE,
    BATCH,
    CELL_SECONDS,
    CHECKPOINT_STEPS,
    CONDITIONS,
    DENSE,
    FAMILY,
    JOINT_ATOL,
    MEMORY,
    PARENT_FREEZE,
    PARENT_RESULTS,
    PARENT_SPEC,
    PARENT_SUITE,
    SCHEMA,
    SPEC,
    STEPS,
    SUITE_SECONDS,
    TOTAL_TARGETS,
    TRAIN_TARGETS,
    Cell,
    batch_offset,
    cells,
    config_hash,
    counters,
    load_config,
    validate_config,
)
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import RSS_BYTES, supervise

if TYPE_CHECKING:
    from torch import Tensor

    from .p4_model import FrozenModel

DEFAULT_CONFIG = Path("configs/p4_frozen_capacity.toml")
DEFAULT_RESULTS = Path("results/p4-2026-11-12")
CELL_FILES = tuple(name for name in CELL_EXPORT if not name.startswith("checkpoint-")) + (
    "checkpoint-0/index.json",
    "checkpoint-256/index.json",
    "checkpoint-512/index.json",
    "parent_provenance.json",
)
SUPERVISOR_FILES = ("manifest.json", "terminal.json", "stdout.log", "stderr.log")
SUITE_FILES = (
    "config.resolved.json",
    "source.json",
    "environment.json",
    "cells.json",
    "metrics.jsonl",
    "result.json",
    "frozen-data/dataset_manifest.json",
    "parent_provenance.json",
    "baselines.json",
)
HYPOTHESIS = "useful hierarchical memory capacity on a frozen backbone at the registered budget"


def _fields(**extra: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "question_id": FAMILY,
        "hypothesis": HYPOTHESIS,
        "hypothesis_null_reason": None,
        "authorized_spec_reference": SPEC,
        "parent_spec_reference": PARENT_SPEC,
        "parent_suite_id": PARENT_SUITE,
        "parent_source_freeze": PARENT_FREEZE,
        "human_local_data_approval": DATA_APPROVAL,
        "reviewer_override": "human-authorized Codex reviewer per ADR-0003",
        **extra,
    }


def _prepare(run: Path, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    write_json(run / "config.resolved.json", config)
    source = record_source(run, Path.cwd(), spec=SPEC)
    environment = record_environment(run, family=FAMILY)
    _update(
        run,
        code_commit=source["code_commit"],
        dirty=source["dirty"],
        source_sha256=source["archive"]["sha256"],
        spec_sha256=source["spec_sha256"],
        parent_spec_sha256=source["archive_file_sha256"][PARENT_SPEC],
        data_approval_sha256=source["archive_file_sha256"][DATA_APPROVAL],
        lock_sha256=source["lock_sha256"],
        config_sha256=config_hash(config),
        environment=environment,
        metrics_not_measured={
            "FLOPs": "analytical work units are reported separately",
            "inference_latency": "fixed-length validation only",
            "physical_io": "RAM-only",
            "matched_active_compute": "only trainable parameters and update budget are matched",
        },
    )
    runtime_supported()
    return source, environment


def _shared(run: Path) -> dict[str, str]:
    manifest = read_json(run / "manifest.json")
    return {name: manifest[name] for name in IDENTITY_FIELDS}


def _interventions(
    run: Path,
    model: FrozenModel,
    path: Path,
    digest: str,
    identity: dict[str, Any],
    validation: Tensor,
    reference: float,
    baseline: float,
) -> dict[str, Any]:
    from .p4_checkpoint import restore
    from .p4_model import FrozenModel, evaluate, intervene, optimizer_for

    cell = model.cell
    tags = (
        ("enabled",)
        if cell.variant == BASELINE
        else ("enabled", "disabled")
        if cell.variant == DENSE
        else CONDITIONS
    )
    index_hash = file_sha256(path / "index.json")
    step = 0 if cell.variant == BASELINE else STEPS
    result = {}
    with _isolated_rng():
        for tag in tags:
            clone = FrozenModel(cell, model.backbone)
            if restore(path, clone, optimizer_for(clone), identity) != counters(step):
                raise ValueError("P4 intervention checkpoint counters mismatch")
            permutation = intervene(clone, tag)
            evidence = _permutation(run, tag, permutation) if permutation is not None else None
            metrics = evaluate(clone, validation)
            nll = metrics["nll"]
            passed = (
                _bitwise_nll(nll, reference)
                if tag == "enabled"
                else _bitwise_nll(nll, baseline)
                if tag == "disabled"
                else math.isclose(nll, reference, rel_tol=0, abs_tol=JOINT_ATOL)
                if tag == "joint_within_branch"
                else None
            )
            unchanged = (
                file_sha256(path / "state.pt") == digest
                and file_sha256(path / "index.json") == index_hash
            )
            record = {
                **metrics,
                "condition": tag,
                "panel": "P4_scientific",
                "additional_step": step,
                "training_target_tokens": 0,
                "reference_nll": reference,
                "paired_baseline_nll": baseline,
                "invariance_passed": passed,
                "checkpoint_unchanged": unchanged,
                "checkpoint_state_sha256": digest,
                "checkpoint_index_sha256": index_hash,
                "permutation": evidence,
            }
            append_event(run, {"event": "intervention_evaluation", **record})
            if not unchanged or passed is False:
                raise ValueError(f"P4 intervention integrity failure: {tag}")
            result[tag] = record
    return result


def _cell(run: Path, suite: Path, parent_suite: Path, cell: Cell) -> None:
    import torch

    from .engine import configure_cpu
    from .optimization_followup import _evaluate as evaluate_p3
    from .p2_model import FollowupModel
    from .p3_checkpoint import restore as restore_p3
    from .p4_checkpoint import save
    from .p4_data import load_frozen
    from .p4_model import (
        FrozenModel,
        backbone_digest,
        evaluate,
        optimizer_for,
        optimizer_names,
        train_step,
    )
    from .p4_parent import verify_parent
    from .pilot_model import Memory

    config = validate_config(read_json(suite / "config.resolved.json"))
    _, environment = _prepare(run, config)
    shared = _shared(suite)
    if _shared(run) != shared:
        raise ValueError("P4 source/config/spec does not match frozen suite")
    manifest = read_json(suite / "manifest.json")
    data_hash = manifest["dataset_manifest_sha256"]
    train, prior, validation, data_manifest = load_frozen(suite / "frozen-data", data_hash)
    write_json(run / "dataset_manifest.json", data_manifest)
    mapping = read_json(suite / "parent_provenance.json")
    if sha256(canonical_json(mapping)) != manifest["parent_provenance_sha256"]:
        raise ValueError("P4 frozen parent map changed")
    expected = mapping[cell.parent_label]
    parent = verify_parent(parent_suite, PARENT_RESULTS, expected["record"], environment)
    if parent.provenance != expected["provenance"]:
        raise ValueError("P4 actual parent does not match suite preflight")
    write_json(run / "parent_provenance.json", parent.provenance)
    order_file = run / "order.json"
    atomic_write(order_file, parent.order_file.read_bytes())
    order_hash = file_sha256(order_file)
    if order_hash != parent.identity["order_sha256"]:
        raise ValueError("P4 order differs from verified parent")
    configure_cpu()
    with _isolated_rng():
        original = FollowupModel(parent.cell)
        parent_opt = _optimizer(original)
        restored = restore_p3(parent.checkpoint, original, parent_opt, parent.identity)
        if restored["completed_step"] != 1024 or not original.bypass:
            raise ValueError("P4 must extract the final bypassed P3 parent")
        if cell.variant == BASELINE:
            integrity = evaluate_p3(original, prior, memory_enabled=False)
            passed = _bitwise_nll(integrity["nll"], parent.final_nll)
            append_event(
                run,
                {
                    "event": "parent_restore_integrity",
                    "panel": "P3_integrity_only",
                    "excluded_from_scientific_analysis": True,
                    "training_target_tokens": 0,
                    "recorded_parent_nll": parent.final_nll,
                    "bitwise_passed": passed,
                    **integrity,
                },
            )
            if not passed:
                raise ValueError("P4 P3-parent NLL did not replay bitwise")
        random.seed(cell.seed)
        torch.default_generator.manual_seed(cell.seed)
        model = FrozenModel(cell, original)
    del original, parent_opt
    random.seed(cell.seed)
    torch.default_generator.manual_seed(cell.seed)
    frozen_hash = backbone_digest(model.backbone)
    baseline_record = read_json(suite / "baselines.json").get(cell.parent_label)
    if cell.variant != BASELINE and (
        baseline_record is None
        or baseline_record["backbone_sha256"] != frozen_hash
        or baseline_record["parent_checkpoint_state_sha256"]
        != parent.provenance["checkpoint_state_sha256"]
    ):
        raise ValueError("P4 trainable cell does not match its verified frozen baseline")
    optimizer = optimizer_for(model)
    names = optimizer_names(model, optimizer)
    identity = {
        **shared,
        "cell": cell.fields(),
        "backbone_sha256": frozen_hash,
        "dataset_manifest_sha256": data_hash,
        "order_sha256": order_hash,
        "parent": parent.provenance,
    }
    backbone_count = sum(p.numel() for p in model.backbone.parameters())
    stored = sum(p.numel() for p in model.parameters())
    _update(
        run,
        parent_run_id=parent.provenance["run_id"],
        checkpoint_identity=identity,
        dataset_manifest_sha256=data_hash,
        order_sha256=order_hash,
        seeds=cell.fields(),
        model={
            "parameters_stored": stored,
            "parameters_frozen": backbone_count,
            "parameters_trainable": stored - backbone_count,
            "frozen_backbone_sha256": frozen_hash,
            "optimizer_parameter_names": names,
            "optimizer_parameter_tensor_count": len(names),
            "optimizer_parameter_count": stored - backbone_count,
            "logical_work": (
                {
                    "router_dot_products_per_query": 16,
                    "key_dot_products_per_query": 512,
                    "selected_value_elements_per_query": 256,
                }
                if cell.variant == MEMORY
                else {"dense_3100_wide_matrix_multiplies_per_query": 2}
                if cell.variant == DENSE
                else None
            ),
        },
    )

    def frozen_check() -> None:
        if backbone_digest(model.backbone) != frozen_hash:
            raise ValueError("P4 frozen backbone or mask changed")
        optimizer_names(model, optimizer)
        parent.check_unchanged()

    def reference(step: int, event: str) -> dict[str, Any]:
        outcome = evaluate(model, validation)
        append_event(
            run,
            {
                "event": event,
                "additional_step": step,
                "panel": "P4_scientific",
                "training_target_tokens": 0,
                **outcome,
            },
        )
        return outcome

    frozen_check()
    snapshots = {}
    path = run / "checkpoint-0"
    snapshots[path.name] = save(path, model, optimizer, 0, identity)
    train_seconds = 0.0
    tokens = 0
    initial = None
    gate_initial = float(model.addition.gate.detach()) if model.addition is not None else None
    router_initial = (
        model.addition.router.detach().clone() if isinstance(model.addition, Memory) else None
    )
    nonzero_router = 0
    if optimizer is not None:
        initial = reference(0, "initial_evaluation")
        ordered = train[torch.tensor(parent.order_ids, dtype=torch.int64, device="cpu")]
        start = time.monotonic()
        for step in range(1, STEPS + 1):
            offset = batch_offset(step)
            batch = ordered[offset : offset + BATCH]
            loss, gradient, router_gradient = train_step(model, optimizer, batch, step)
            nonzero_router += int(router_gradient is not None and router_gradient > 0)
            tokens += batch[:, 1:].numel()
            counts = counters(step)
            if counts["additional_targets"] != tokens:
                raise ValueError("P4 wrong training token count")
            append_event(
                run,
                {
                    "event": "train_step",
                    **counts,
                    "order_offset_for_update": offset,
                    "pre_update_loss": loss,
                    "loss_units": "nats_per_byte",
                    "pre_clip_gradient_norm": gradient,
                    "pre_clip_router_gradient_norm": router_gradient,
                    "gate": float(model.addition.gate.detach())
                    if model.addition is not None
                    else None,
                },
            )
            if step in CHECKPOINT_STEPS:
                frozen_check()
                path = run / f"checkpoint-{step}"
                snapshots[path.name] = save(path, model, optimizer, step, identity)
        train_seconds = time.monotonic() - start
        if tokens != TRAIN_TARGETS:
            raise ValueError("P4 wrong final training budget")
    final = reference(0 if optimizer is None else STEPS, "final_evaluation")
    baseline_nll = final["nll"] if optimizer is None else baseline_record["nll"]
    interventions = _interventions(
        run,
        model,
        path,
        snapshots[path.name],
        identity,
        validation,
        final["nll"],
        baseline_nll,
    )
    frozen_check()
    if _shared(suite) != shared or not _source_unchanged(run, shared["source_sha256"]):
        raise ValueError("P4 source archive changed during cell")
    final_gate = float(model.addition.gate.detach()) if model.addition is not None else None
    router_movement = (
        float(torch.linalg.vector_norm(model.addition.router.detach() - router_initial))
        if isinstance(model.addition, Memory) and router_initial is not None
        else None
    )
    if router_movement is not None and not math.isfinite(router_movement):
        raise ValueError("P4 non-finite router movement")
    write_json(
        run / "result.json",
        {
            "outcome": "completed",
            "cell": cell.fields(),
            "initial": initial,
            "final": final,
            "interventions": interventions,
            "additional_training_targets": tokens,
            "completed_steps": 0 if optimizer is None else STEPS,
            "checkpoint_state_sha256": snapshots,
            "backbone_sha256": frozen_hash,
            "parent_checkpoint_unchanged": True,
            "gate_initial": gate_initial,
            "gate_final": final_gate,
            "gate_movement": final_gate - gate_initial
            if final_gate is not None and gate_initial is not None
            else None,
            "router_movement_l2": router_movement,
            "router_nonzero_gradient_steps": nonzero_router if cell.variant == MEMORY else None,
            "training_seconds_including_logs_and_saves": train_seconds,
        },
    )


def _status() -> list[dict[str, Any]]:
    return [
        {**cell.fields(), "label": cell.label, "status": "unexecuted", "run_id": None}
        for cell in cells()
    ]


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    from .p4_analysis import describe

    path = run / "cells.json"
    rows = read_json(path) if path.exists() else _status()
    complete = reason is None and all(row["status"] == "completed" for row in rows)
    for row in rows:
        if row["status"] == "running":
            row.update(status="interrupted", reason=reason)
        elif row["status"] == "unexecuted":
            row["reason"] = reason
    counts = {
        key: sum(row.get(key, 0) for row in rows)
        for key in (
            "additional_training_targets",
            "snapshots",
            "scientific_evaluations",
            "integrity_evaluations",
        )
    }
    result = {
        "outcome": "completed" if complete else "failed",
        "cells": rows,
        "counts": counts,
        "reason": reason,
        "P1_P2_P3_outcomes": "unchanged",
    }
    if complete:
        if tuple(counts.values()) != (TOTAL_TARGETS, 171, 288, 9):
            raise ValueError("P4 suite registered accounting mismatch")
        result["descriptive_analysis"] = describe(rows)
    return result


def _suite(run: Path, config_path: Path, data: Path, parent_suite: Path, export: Path) -> None:
    from .p4_data import freeze
    from .p4_parent import verify_parent, verify_suite

    status = _status()
    write_json(run / "cells.json", status)
    try:
        export.mkdir(parents=True, exist_ok=False)
        config = load_config(config_path)
        source, environment = _prepare(run, config)
        records = verify_suite(parent_suite, PARENT_RESULTS, source)
        mapping = {}
        for key, record in records.items():
            parent = verify_parent(parent_suite, PARENT_RESULTS, record, environment)
            mapping[f"b{key[0]}-o{key[1]}-control"] = {
                "record": record,
                "provenance": parent.provenance,
            }
        write_json(run / "parent_provenance.json", mapping)
        dataset = run / "frozen-data"
        dataset.mkdir()
        manifest = freeze(dataset, data)
        _update(
            run,
            dataset_manifest_sha256=sha256(canonical_json(manifest)),
            parent_provenance_sha256=sha256(canonical_json(mapping)),
            parent_suite_path=str(parent_suite),
            output_results=str(export),
            reporting_pauses_seconds=0.0,
            reporting_pause_method="no in-suite pauses",
            supervisor_finalization_after_worker="final manifest, terminal and closed logs; "
            "partial bundle recovery only if needed",
        )
        baselines: dict[str, Any] = {}
        write_json(run / "baselines.json", baselines)
        print(
            canonical_json({"event": "suite_started", "suite": str(run), "results": str(export)})
            .decode()
            .strip(),
            flush=True,
        )
        for cell, row in zip(cells(), status, strict=True):

            def worker(child: Path) -> list[str]:
                row.update(run_id=child.name, status="running")
                write_json(run / "cells.json", status)
                return [
                    sys.executable,
                    "-m",
                    "arborlm.frozen_capacity",
                    "_cell",
                    str(child),
                    str(run),
                    str(parent_suite),
                    str(cell.backbone),
                    str(cell.order),
                    str(cell.seed),
                    cell.variant,
                ]

            child, ok = supervise(
                run / "cells",
                "p4_capacity_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CELL_SECONDS,
                rss_bytes=RSS_BYTES,
                worker_argv=worker,
                manifest_fields=_fields(parent_p4_suite_id=run.name, **cell.fields()),
                run_prefix="P4CAP",
            )
            terminal = read_json(child / "terminal.json")
            row.update(status=terminal["status"], reason=terminal["reason"])
            if ok:
                result = read_json(child / "result.json")
                final_nll = result["final"]["nll"]
                if cell.variant == BASELINE:
                    baselines[cell.parent_label] = {
                        "nll": final_nll,
                        "backbone_sha256": result["backbone_sha256"],
                        "parent_checkpoint_state_sha256": mapping[cell.parent_label]["provenance"][
                            "checkpoint_state_sha256"
                        ],
                    }
                    write_json(run / "baselines.json", baselines)
                row.update(
                    final_nll=final_nll,
                    initial_nll=result["initial"]["nll"] if result["initial"] is not None else None,
                    interventions={
                        tag: metrics["nll"] for tag, metrics in result["interventions"].items()
                    },
                    additional_training_targets=result["additional_training_targets"],
                    snapshots=len(result["checkpoint_state_sha256"]),
                    scientific_evaluations=1
                    + int(result["initial"] is not None)
                    + len(result["interventions"]),
                    integrity_evaluations=int(cell.variant == BASELINE),
                    wall_seconds=terminal["process_wall_seconds"],
                    peak_rss_bytes=terminal["peak_process_tree_rss_bytes"],
                )
            _export(child, export / cell.label, CELL_FILES)
            row["compact_export"] = str(export / cell.label)
            write_json(run / "cells.json", status)
            event = {"event": "cell_finished", **row}
            append_event(run, event)
            print(canonical_json(event).decode().strip(), flush=True)
            if not ok:
                raise RuntimeError(f"P4 cell {cell.label} failed; see {child / 'terminal.json'}")
        for record in records.values():
            verify_parent(parent_suite, PARENT_RESULTS, record, environment).check_unchanged()
        if not _source_unchanged(run, _shared(run)["source_sha256"]):
            raise ValueError("P4 suite source archive changed")
        write_json(run / "result.json", _summary(run))
        _export(run, export / "suite", SUITE_FILES)
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        if export.is_dir() and not (export / "suite").exists():
            _export(run, export / "suite", SUITE_FILES)
        raise


def launch(
    config: Path, data: Path, output: Path, parent_suite: Path, export: Path
) -> tuple[Path, bool]:
    parent_suite = parent_suite.resolve()
    if output.resolve().is_relative_to(parent_suite) or export.resolve().is_relative_to(
        parent_suite
    ):
        raise ValueError("P4 must not write outputs inside the registered parent suite")
    if export.exists():
        raise FileExistsError(f"refuse to overwrite prior P4 compact export: {export}")
    stop = threading.Event()
    reporter: threading.Thread | None = None

    def worker(run: Path) -> list[str]:
        nonlocal reporter
        reporter = threading.Thread(target=_follow_stdout, args=(run / "stdout.log", stop))
        reporter.start()
        print(
            canonical_json({"event": "suite_allocated", "suite": str(run)}).decode().strip(),
            flush=True,
        )
        return [
            sys.executable,
            "-m",
            "arborlm.frozen_capacity",
            "_suite",
            str(run),
            str(config),
            str(data),
            str(parent_suite),
            str(export),
        ]

    try:
        run, ok = supervise(
            output,
            "p4_capacity_suite",
            [],
            requested_argv=sys.argv,
            process_seconds=SUITE_SECONDS,
            rss_bytes=RSS_BYTES,
            worker_argv=worker,
            manifest_fields=_fields(),
            run_prefix="P4CAP",
            nested_workers=True,
        )
    finally:
        stop.set()
        if reporter is not None:
            reporter.join()
    if not ok and not (run / "result.json").exists():
        write_json(run / "result.json", _summary(run, read_json(run / "terminal.json")["reason"]))
    # After watchdog finalization, preserve terminal and any interrupted cell's evidence.
    for row in read_json(run / "result.json")["cells"]:
        if row.get("run_id") and not (export / row["label"]).exists():
            child = run / "cells" / row["run_id"]
            if child.is_dir():
                _export(child, export / row["label"], CELL_FILES)
    suite_export = export / "suite"
    if not suite_export.exists():
        _export(run, suite_export, SUITE_FILES + SUPERVISOR_FILES)
    else:
        for name in SUPERVISOR_FILES:
            atomic_write(suite_export / name, (run / name).read_bytes())
    return run, ok


def main() -> int:
    if sys.argv[1:2] in (["_suite"], ["_cell"]):
        parser = argparse.ArgumentParser()
        parser.add_argument("operation", choices=("_suite", "_cell"))
        parser.add_argument("run", type=Path)
        parser.add_argument("arguments", nargs="+")
        args = parser.parse_args()
        running = read_json(args.run / "manifest.json")
        if running["status"] != "running" or running["experiment_family"] != FAMILY:
            raise ValueError("missing supervising P4 watchdog record")
        if args.operation == "_suite":
            _suite(args.run, *map(Path, args.arguments))
        else:
            suite, parent, b, o, seed, variant = args.arguments
            _cell(args.run, Path(suite), Path(parent), Cell(int(b), int(o), int(seed), variant))
        return 0
    parser = argparse.ArgumentParser(description="Run ADR-0009 frozen-backbone capacity")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--parent-suite", type=Path, default=Path("experiments") / PARENT_SUITE)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    run, ok = launch(
        args.config.resolve(),
        args.data_dir.resolve(),
        args.output_root.resolve(),
        args.parent_suite.resolve(),
        args.results_root.resolve(),
    )
    print(
        f"{'Recorded' if ok else 'Failed'} P4 capacity suite: {run}",
        file=sys.stdout if ok else sys.stderr,
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
