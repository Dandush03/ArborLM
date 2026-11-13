"""Watchdog-bound ADR-0010 matrix and compact per-cell evidence."""

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
    _permutation,
    _source_unchanged,
    _update,
)
from .p3_checkpoint import bitwise_equal
from .p5_clock import SuiteRSS
from .p5_config import (
    BASELINE,
    BATCH,
    CELL_SECONDS,
    CHECKPOINT_STEPS,
    CONDITIONS,
    DENSE,
    FAMILY,
    FIXED,
    JOINT_ATOL,
    LEARNED,
    MEMORIES,
    PARENT_FREEZE,
    PARENT_RESULTS,
    PARENT_SPEC,
    PARENT_SUITE,
    QUALITY_SECONDS,
    SCHEMA,
    SPEC,
    STEPS,
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

    from .p5_model import Model

DEFAULT_CONFIG = Path("configs/p5_hierarchy_ablation.toml")
DEFAULT_RESULTS = Path("results/p5-2026-11-13")
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
HYPOTHESIS = "useful hierarchical memory quality, routing and score-work trade-off"


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
            "decode_latency": "fixed-context RAM timing is a separate registered stage",
            "physical_io": "RAM-only",
            "matched_active_compute": "update budget matched; A/B have 256 fewer "
            "trainable parameters than C/D",
        },
    )
    runtime_supported()
    return source, environment


def _shared(run: Path) -> dict[str, str]:
    manifest = read_json(run / "manifest.json")
    return {name: manifest[name] for name in IDENTITY_FIELDS}


def _interventions(
    run: Path,
    model: Model,
    path: Path,
    digest: str,
    identity: dict[str, Any],
    validation: Tensor,
    reference: float,
    baseline: float,
) -> dict[str, Any]:
    from .p5_checkpoint import restore
    from .p5_model import Model, evaluate, intervene, optimizer_for

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
            clone = Model(cell, model.backbone)
            if restore(path, clone, optimizer_for(clone), identity) != counters(step):
                raise ValueError("P5 intervention checkpoint counters mismatch")
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
                "panel": "P5_scientific",
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
                raise ValueError(f"P5 intervention integrity failure: {tag}")
            result[tag] = record
    return result


def _cell(run: Path, suite: Path, parent_suite: Path, cell: Cell) -> None:
    import torch

    from .engine import configure_cpu
    from .p5_checkpoint import save
    from .p5_data import load_frozen
    from .p5_model import (
        Model,
        backbone_digest,
        evaluate,
        logical_work,
        optimizer_for,
        optimizer_names,
        train_step,
    )
    from .p5_parent import extract_verified, verify_parent
    from .pilot_model import Memory

    config = validate_config(read_json(suite / "config.resolved.json"))
    _, environment = _prepare(run, config)
    shared = _shared(suite)
    if _shared(run) != shared:
        raise ValueError("P5 source/config/spec does not match frozen suite")
    manifest = read_json(suite / "manifest.json")
    data_hash = manifest["dataset_manifest_sha256"]
    train, prior, validation, data_manifest = load_frozen(suite / "frozen-data", data_hash)
    write_json(run / "dataset_manifest.json", data_manifest)
    mapping = read_json(suite / "parent_provenance.json")
    if sha256(canonical_json(mapping)) != manifest["parent_provenance_sha256"]:
        raise ValueError("P5 frozen parent map changed")
    expected = mapping[cell.parent_label]
    parent = verify_parent(parent_suite, PARENT_RESULTS, expected["record"], environment)
    if parent.provenance != expected["provenance"]:
        raise ValueError("P5 actual parent does not match suite preflight")
    write_json(run / "parent_provenance.json", parent.provenance)
    order_file = run / "order.json"
    atomic_write(order_file, parent.order_file.read_bytes())
    order_hash = file_sha256(order_file)
    if order_hash != parent.identity["order_sha256"]:
        raise ValueError("P5 order differs from verified parent")
    configure_cpu()
    backbone = extract_verified(parent)
    random.seed(cell.seed)
    torch.default_generator.manual_seed(cell.seed)
    model = Model(cell, backbone)
    if cell.variant == BASELINE:
        integrity = evaluate(model, prior)
        passed = _bitwise_nll(integrity["nll"], parent.final_nll)
        append_event(
            run,
            {
                "event": "parent_restore_integrity",
                "panel": "P4_integrity_only",
                "excluded_from_scientific_analysis": True,
                "training_target_tokens": 0,
                "recorded_parent_nll": parent.final_nll,
                "bitwise_passed": passed,
                **integrity,
            },
        )
        if not passed:
            raise ValueError("P5 P4-parent NLL did not replay bitwise")
    frozen_hash = backbone_digest(model.backbone)
    baseline_record = read_json(suite / "baselines.json").get(cell.parent_label)
    if cell.variant != BASELINE and (
        baseline_record is None
        or baseline_record["backbone_sha256"] != frozen_hash
        or baseline_record["parent_checkpoint_state_sha256"]
        != parent.provenance["checkpoint_state_sha256"]
    ):
        raise ValueError("P5 trainable cell does not match its verified frozen baseline")
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
            "logical_work": logical_work(cell.variant),
            "parameter_bytes": sum(p.numel() * p.element_size() for p in model.parameters()),
            "buffer_bytes": sum(p.numel() * p.element_size() for p in model.buffers()),
            "frozen_backbone_buffer_bytes": sum(
                p.numel() * p.element_size() for p in model.backbone.buffers()
            ),
            "fixed_router_buffer_scalars": 256 if cell.variant == FIXED else 0,
        },
    )

    fixed_router = (
        model.addition.router.detach().clone()
        if cell.variant == FIXED and isinstance(model.addition, Memory)
        else None
    )

    def frozen_check() -> None:
        if backbone_digest(model.backbone) != frozen_hash:
            raise ValueError("P5 frozen backbone or mask changed")
        if fixed_router is not None and (
            not isinstance(model.addition, Memory)
            or not bitwise_equal(fixed_router, model.addition.router)
        ):
            raise ValueError("P5 fixed router buffer changed")
        optimizer_names(model, optimizer)
        parent.check_unchanged()

    def reference(step: int, event: str) -> dict[str, Any]:
        outcome = evaluate(model, validation)
        append_event(
            run,
            {
                "event": event,
                "additional_step": step,
                "panel": "P5_scientific",
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
        model.addition.router.detach().clone()
        if cell.variant in (FIXED, LEARNED) and isinstance(model.addition, Memory)
        else None
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
                raise ValueError("P5 wrong training token count")
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
            raise ValueError("P5 wrong final training budget")
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
        raise ValueError("P5 source archive changed during cell")
    final_gate = float(model.addition.gate.detach()) if model.addition is not None else None
    router_movement = (
        float(torch.linalg.vector_norm(model.addition.router.detach() - router_initial))
        if router_initial is not None and isinstance(model.addition, Memory)
        else None
    )
    if router_movement is not None and not math.isfinite(router_movement):
        raise ValueError("P5 non-finite router movement")
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
            "router_nonzero_gradient_steps": nonzero_router if cell.variant == LEARNED else None,
            "training_seconds_including_logs_and_saves": train_seconds,
            "optimizer_state_tensor_bytes": sum(
                value.numel() * value.element_size()
                for state in optimizer.state.values()
                for value in state.values()
                if isinstance(value, torch.Tensor)
            )
            if optimizer is not None
            else 0,
        },
    )


def _status() -> list[dict[str, Any]]:
    return [
        {**cell.fields(), "label": cell.label, "status": "unexecuted", "run_id": None}
        for cell in cells()
    ]


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    from .p5_analysis import describe

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
        "P1_P2_P3_P4_outcomes": "unchanged",
    }
    if complete:
        if tuple(counts.values()) != (TOTAL_TARGETS, 333, 612, 9):
            raise ValueError("P5 suite registered accounting mismatch")
        result["descriptive_analysis"] = describe(rows)
    return result


def _quality_suite(
    run: Path, config_path: Path, data: Path, parent_suite: Path, export: Path
) -> None:
    from .p5_data import freeze
    from .p5_parent import verify_parent, verify_suite

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
            mapping[f"b{key[0]}-o{key[1]}-baseline"] = {
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
                    "arborlm.hierarchy_ablation",
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
                "p5_quality_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CELL_SECONDS,
                rss_bytes=RSS_BYTES,
                worker_argv=worker,
                manifest_fields=_fields(parent_p5_suite_id=run.name, **cell.fields()),
                run_prefix="P5HIER",
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
                raise RuntimeError(f"P5 cell {cell.label} failed; see {child / 'terminal.json'}")
        for record in records.values():
            verify_parent(parent_suite, PARENT_RESULTS, record, environment).check_unchanged()
        if not _source_unchanged(run, _shared(run)["source_sha256"]):
            raise ValueError("P5 suite source archive changed")
        write_json(run / "result.json", _summary(run))
        _export(run, export / "quality-suite", SUITE_FILES)
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        if export.is_dir() and not (export / "quality-suite").exists():
            _export(run, export / "quality-suite", SUITE_FILES)
        raise


def _timing_models(
    quality: Path,
    parent_suite: Path,
    b: int,
    o: int,
    seed: int,
    environment: dict[str, Any],
) -> tuple[dict[str, Model], dict[str, Any]]:
    from .p5_checkpoint import restore
    from .p5_config import VARIANTS
    from .p5_model import Model, optimizer_for
    from .p5_parent import extract_verified, verify_parent

    bundle = read_json(quality / "parent_provenance.json")
    mapping = bundle[f"b{b}-o{o}-baseline"]
    parent = verify_parent(parent_suite, PARENT_RESULTS, mapping["record"], environment)
    if parent.provenance != mapping["provenance"]:
        raise ValueError("P5 timing parent differs from quality parent")
    quality_manifest = read_json(quality / "manifest.json")
    if sha256(canonical_json(bundle)) != quality_manifest["parent_provenance_sha256"]:
        raise ValueError("P5 timing parent map identity mismatch")
    backbone = extract_verified(parent)
    models: dict[str, Model] = {}
    evidence = {}
    result = read_json(quality / "result.json")
    if result["outcome"] != "completed":
        raise ValueError("P5 timing requires complete quality stage")
    by_label = {row["label"]: row for row in result["cells"]}
    for variant in (BASELINE,) if seed == 0 else VARIANTS:
        cell = Cell(b, o, seed, variant)
        row = by_label[cell.label]
        run_id = row["run_id"]
        if (
            any(row[key] != value for key, value in cell.fields().items())
            or row["status"] != "completed"
            or Path(run_id).name != run_id
            or not run_id.startswith("P5HIER-")
        ):
            raise ValueError("P5 timing quality cell identity mismatch")
        folder = quality / "cells" / run_id
        manifest = read_json(folder / "manifest.json")
        identity = manifest["checkpoint_identity"]
        step = 0 if seed == 0 else STEPS
        path = folder / f"checkpoint-{step}"
        digest = file_sha256(path / "state.pt")
        index = file_sha256(path / "index.json")
        compact = Path(row["compact_export"])
        for name in ("manifest.json", "result.json", f"checkpoint-{step}/index.json"):
            if file_sha256(folder / name) != file_sha256(compact / name):
                raise ValueError(f"P5 timing original and compact quality evidence differ: {name}")
        if (
            identity["parent"] != parent.provenance
            or identity["cell"] != cell.fields()
            or identity["dataset_manifest_sha256"] != quality_manifest["dataset_manifest_sha256"]
            or identity["order_sha256"] != parent.identity["order_sha256"]
            or any(identity[k] != v for k, v in _shared(quality).items())
            or digest != read_json(folder / "result.json")["checkpoint_state_sha256"][path.name]
        ):
            raise ValueError("P5 timing checkpoint identity mismatch")
        model = Model(cell, backbone)
        optimizer = optimizer_for(model)
        if restore(path, model, optimizer, identity) != counters(step):
            raise ValueError("P5 timing checkpoint cursor mismatch")
        models[variant] = model
        evidence[variant] = {
            "path": str(path),
            "state_sha256": digest,
            "index_sha256": index,
            "checkpoint_identity": identity,
            "quality_run_id": run_id,
        }
    parent.check_unchanged()
    return models, evidence


def _timing_worker(
    run: Path,
    quality: Path,
    parent_suite: Path,
    b: int,
    o: int,
    seed: int,
) -> None:
    import gc
    import tracemalloc

    import psutil
    import torch

    from .engine import configure_cpu
    from .p5_data import load_frozen
    from .p5_model import state_digest
    from .p5_timing import CALLS, ROUNDS, inputs_from_rows, run_schedule, schedule, trace_memory

    config = validate_config(read_json(quality / "config.resolved.json"))
    _, environment = _prepare(run, config)
    if _shared(run) != _shared(quality):
        raise ValueError("P5 timing source/config/spec differs from quality stage")
    dataset_hash = read_json(quality / "manifest.json")["dataset_manifest_sha256"]
    train, _, _, dataset = load_frozen(quality / "frozen-data", dataset_hash)
    write_json(run / "dataset_manifest.json", dataset)
    configure_cpu()
    models, evidence = _timing_models(quality, parent_suite, b, o, seed, environment)
    write_json(run / "quality_checkpoint_provenance.json", evidence)
    index = Cell(b, o, seed, BASELINE if seed == 0 else MEMORIES[0]).index if seed else 0
    inputs = inputs_from_rows(train)
    input_bytes = bytes(train[:32, :64].to(torch.uint8).contiguous().reshape(-1).tolist())
    input_record = {
        "input_ranks": list(range(32)),
        "time_steps": 64,
        "labels": False,
        "sha256": sha256(input_bytes),
        "workload_starts": [0, 8, 16, 24],
    }
    write_json(run / "timing_inputs.json", input_record)
    before = {v: state_digest(model) for v, model in models.items()}
    python_rng, torch_rng = random.getstate(), torch.get_rng_state()
    modes = {v: model.training for v, model in models.items()}
    gc_before = gc.isenabled()
    traced = {}
    process = psutil.Process()
    rss_before = process.memory_info().rss
    trace_start = time.monotonic()
    # Separate untimed trace probe. tracemalloc measures Python allocations only.
    tracemalloc.start()
    try:
        for variant, model in models.items():
            if variant not in MEMORIES:
                continue
            workloads = {}
            for size, batches in inputs.items():
                records = []
                for batch_id, x in enumerate(batches):
                    record = trace_memory(model, x)
                    append_event(
                        run,
                        {
                            "event": "operand_trace",
                            "batch_size": size,
                            "input_index": batch_id,
                            **record,
                        },
                    )
                    records.append(record)
                workloads[str(size)] = records
            traced[variant] = workloads
        current_python_bytes, peak_python_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    trace_seconds = time.monotonic() - trace_start
    rss_after_probes = process.memory_info().rss
    timing_start = time.monotonic()
    timing = run_schedule(
        models,
        inputs,
        index,
        on_block=lambda row: append_event(run, {"event": "timing_block", **row}),
    )
    timing_seconds = time.monotonic() - timing_start
    if (
        any(
            state_digest(model) != before[v] or model.training != modes[v]
            for v, model in models.items()
        )
        or random.getstate() != python_rng
        or not torch.equal(torch_rng, torch.get_rng_state())
        or gc.isenabled() != gc_before
    ):
        raise ValueError("P5 timing changed model, RNG, mode or GC state")
    for record in evidence.values():
        path = Path(record["path"])
        if (
            file_sha256(path / "state.pt") != record["state_sha256"]
            or file_sha256(path / "index.json") != record["index_sha256"]
        ):
            raise ValueError("P5 timing changed quality checkpoint")
        parent = record["checkpoint_identity"]["parent"]
        for provenance in (parent, parent["upstream_p3"]):
            original = Path(provenance["checkpoint_path"])
            if (
                file_sha256(original / "state.pt") != provenance["checkpoint_state_sha256"]
                or file_sha256(original / "index.json") != provenance["checkpoint_index_sha256"]
            ):
                raise ValueError("P5 timing changed parent checkpoint")
    if not _source_unchanged(run, _shared(quality)["source_sha256"]):
        raise ValueError("P5 timing source archive changed")
    counts = timing["call_counts"]
    calls = counts["warmups"] + counts["timed"]
    expected_measurements = {
        (block.batch_size, block.scope, block.variant) for block in schedule(index, tuple(models))
    }
    measurements = timing["records"]
    if (
        calls != (192 if seed == 0 else 2112)
        or len(measurements) != len(expected_measurements)
        or {(row["batch_size"], row["scope"], row["variant"]) for row in measurements}
        != expected_measurements
        or any(
            len(row["durations_ns"]) != ROUNDS * CALLS or len(row["round_medians_ns"]) != ROUNDS
            for row in measurements
        )
    ):
        raise ValueError("P5 timing worker call or measurement matrix mismatch")
    write_json(
        run / "result.json",
        {
            "outcome": "completed",
            "backbone": b,
            "order": o,
            "seed": seed,
            "timing": timing,
            "traces": traced,
            "timing_inputs": input_record,
            "timing_scope_calls": calls,
            "training_targets": 0,
            "scientific_evaluation_targets": 0,
            "quality_checkpoint_provenance": evidence,
            "state_and_rng_unchanged": True,
            "probe_counts": {
                "insertion_hidden": 24 if seed else 0,
                "memory_addition_forward": 24 if seed else 0,
            },
            "trace_seconds_including_evidence": trace_seconds,
            "timing_seconds_including_preparation_and_logs": timing_seconds,
            "rss_bytes_before_probes": rss_before,
            "rss_bytes_after_probes": rss_after_probes,
            "rss_bytes_after_timing": process.memory_info().rss,
            "python_tracemalloc_probe_current_bytes": current_python_bytes,
            "python_tracemalloc_probe_peak_bytes": peak_python_bytes,
            "allocation_note": "tracemalloc covers Python probe allocations only, "
            "not PyTorch tensors",
        },
    )


def _emit(value: dict[str, Any]) -> None:
    print(canonical_json(value).decode().strip(), flush=True)


def _finalize_stage(run: Path, export: Path, files: tuple[str, ...]) -> None:
    if not export.exists():
        _export(run, export, files + SUPERVISOR_FILES)
    else:
        for name in SUPERVISOR_FILES:
            atomic_write(export / name, (run / name).read_bytes())


def _timing_stage(
    root: Path,
    quality: Path,
    parent_suite: Path,
    export: Path,
    quality_seconds: float,
    rss: SuiteRSS,
    *,
    timing_start: float,
) -> bool:
    from .p2_config import BACKBONES, ORDERS
    from .p5_analysis import describe
    from .p5_clock import ActiveClock, wait_for_ack
    from .p5_config import SEEDS

    clock = ActiveClock(quality_seconds)
    clock.timing_start = timing_start
    rows: list[dict[str, Any]] = [
        {
            "backbone": b,
            "order": o,
            "seed": seed,
            "label": f"b{b}-o{o}-" + ("baseline" if seed == 0 else f"s{seed}"),
            "status": "unexecuted",
            "run_id": None,
        }
        for b in BACKBONES
        for o in ORDERS
        for seed in (0, *SEEDS)
    ]
    target = export / "timing"
    target.mkdir()
    (root / "metrics.jsonl").touch()
    used: set[str] = set()
    completed = []
    reason: str | None = None

    def terminal_payload() -> dict[str, Any]:
        return {
            "status": "completed" if reason is None else "failed",
            "reason": reason,
            "accounting": clock.snapshot(),
            "supervisor_finalization_after_workers": True,
            "peak_suite_process_tree_rss_bytes": rss.peak,
            "rss_limit_exceeded": rss.breached,
        }

    def persist() -> None:
        write_json(root / "timing-status.json", {"workers": rows, "accounting": clock.snapshot()})

    persist()
    try:
        gate = wait_for_ack(root, root.name, quality.name, used, clock, announce=_emit)
        append_event(root, {"event": "quality_stage_reporting_acknowledged", **gate})
        persist()
        for row in rows:
            b, o, seed = (row[name] for name in ("backbone", "order", "seed"))

            def command(child: Path) -> list[str]:
                row.update(status="running", run_id=child.name)
                persist()
                return [
                    sys.executable,
                    "-m",
                    "arborlm.hierarchy_ablation",
                    "_timing_worker",
                    str(child),
                    str(quality),
                    str(parent_suite),
                    str(b),
                    str(o),
                    str(seed),
                ]

            if rss.breached:
                raise RuntimeError("P5 suite process-tree RSS limit exceeded")
            child, ok = supervise(
                root / "timing-workers",
                "p5_timing_worker",
                [],
                requested_argv=sys.argv,
                worker_argv=command,
                process_seconds=clock.worker_budget(15 if seed == 0 else 45),
                rss_bytes=RSS_BYTES,
                manifest_fields=_fields(
                    parent_p5_suite_id=root.name,
                    quality_stage_run_id=quality.name,
                    backbone=b,
                    order=o,
                    seed=seed,
                ),
                run_prefix="P5TIME",
            )
            terminal = read_json(child / "terminal.json")
            row.update(
                status=terminal["status"],
                reason=terminal["reason"],
                wall_seconds=terminal["process_wall_seconds"],
                peak_rss_bytes=terminal["peak_process_tree_rss_bytes"],
            )
            if ok:
                report = read_json(child / "result.json")
                completed.append(report)
                row["timing_scope_calls"] = report["timing_scope_calls"]
            _export(
                child,
                target / row["label"],
                CELL_FILES
                + (
                    "timing_inputs.json",
                    "quality_checkpoint_provenance.json",
                ),
            )
            row["compact_export"] = str(target / row["label"])
            if clock.remaining() <= 0:
                row.update(status="failed", reason="P5 timing or combined worker deadline exceeded")
                ok = False
            persist()
            event = {"event": "timing_worker_finished", **row, "accounting": clock.snapshot()}
            append_event(root, event)
            _emit(event)
            if not ok:
                raise RuntimeError(f"P5 timing worker {row['label']} failed: {row['reason']}")
            ack = wait_for_ack(root, root.name, child.name, used, clock, announce=_emit)
            append_event(root, {"event": "reporting_acknowledged", **ack})
            persist()
        if rss.breached:
            raise RuntimeError("P5 suite process-tree RSS limit exceeded")
        if sum(worker["timing_scope_calls"] for worker in completed) != 58752:
            raise ValueError("P5 timing scope call total mismatch")
        quality_rows = read_json(quality / "result.json")["cells"]
        analysis = describe(quality_rows, completed)
        clock.worker_budget(float("inf"))
        report = {
            "outcome": "completed",
            "quality_stage": str(quality),
            "timing_workers": rows,
            "timing_scope_calls": 58752,
            "accounting": clock.snapshot(),
            "descriptive_analysis": analysis,
        }
        write_json(root / "result.json", report)
        clock.worker_budget(float("inf"))
        _export(
            root,
            export / "suite",
            (
                "result.json",
                "timing-status.json",
                "metrics.jsonl",
                "expected_ack.json",
            ),
        )
        clock.worker_budget(float("inf"))
        # The first terminal staging write is charged; its public copy is only
        # promoted after checking the active-clock deadline.
        write_json(root / ".terminal-staged.json", terminal_payload())
        clock.worker_budget(float("inf"))
    except BaseException as exc:
        reason = str(exc)
        for row in rows:
            if row["status"] == "running":
                row.update(status="interrupted", reason=reason)
            elif row["status"] == "unexecuted":
                row["reason"] = reason
        persist()
        report = {
            "outcome": "failed",
            "quality_stage": str(quality),
            "timing_workers": rows,
            "accounting": clock.snapshot(),
            "reason": reason,
        }
        write_json(root / "result.json", report)
        if not (export / "suite").exists():
            _export(
                root,
                export / "suite",
                (
                    "result.json",
                    "timing-status.json",
                    "metrics.jsonl",
                    "expected_ack.json",
                ),
            )
        else:
            for name in ("result.json", "timing-status.json", "metrics.jsonl", "expected_ack.json"):
                if (root / name).is_file():
                    atomic_write(export / "suite" / name, (root / name).read_bytes())
        _emit({"event": "timing_stage_failed", "suite": str(root), "reason": reason})
    finally:
        (root / ".terminal-staged.json").unlink(missing_ok=True)
        write_json(root / "terminal.json", terminal_payload())
        atomic_write(export / "suite" / "terminal.json", (root / "terminal.json").read_bytes())
        if reason is None and (clock.remaining() <= 0 or rss.breached):
            reason = "P5 timing/combined deadline or RSS limit exceeded in finalization"
            report = read_json(root / "result.json")
            report.update(outcome="failed", reason=reason, accounting=clock.snapshot())
            report.pop("descriptive_analysis", None)
            write_json(root / "result.json", report)
            atomic_write(export / "suite" / "result.json", (root / "result.json").read_bytes())
            write_json(root / "terminal.json", terminal_payload())
            atomic_write(export / "suite" / "terminal.json", (root / "terminal.json").read_bytes())
    return reason is None


def _launch(
    config: Path,
    data: Path,
    output: Path,
    parent: Path,
    export: Path,
    rss: SuiteRSS,
) -> tuple[Path, bool]:
    from .records import allocate_run

    if any(path.resolve().is_relative_to(parent.resolve()) for path in (output, export)):
        raise ValueError("P5 outputs must not be inside the parent suite")
    if export.exists():
        raise FileExistsError(f"refuse to overwrite prior P5 compact export: {export}")
    quality_started = time.monotonic()
    root = allocate_run(output, prefix="P5HIER")
    _emit({"event": "suite_allocated", "suite": str(root)})
    stop = threading.Event()
    reporter: threading.Thread | None = None

    def command(run: Path) -> list[str]:
        nonlocal reporter
        reporter = threading.Thread(target=_follow_stdout, args=(run / "stdout.log", stop))
        reporter.start()
        return [
            sys.executable,
            "-m",
            "arborlm.hierarchy_ablation",
            "_quality_suite",
            str(run),
            str(config),
            str(data),
            str(parent),
            str(export),
        ]

    try:
        quality, ok = supervise(
            root / "quality",
            "p5_quality_stage",
            [],
            requested_argv=sys.argv,
            process_seconds=QUALITY_SECONDS - (time.monotonic() - quality_started),
            rss_bytes=RSS_BYTES,
            worker_argv=command,
            manifest_fields=_fields(parent_p5_suite_id=root.name),
            run_prefix="P5QUALITY",
            nested_workers=True,
        )
    finally:
        stop.set()
        if reporter is not None:
            reporter.join()
    terminal = read_json(quality / "terminal.json")
    if not (quality / "result.json").exists():
        write_json(quality / "result.json", _summary(quality, terminal["reason"]))
    result = read_json(quality / "result.json")
    for row in result["cells"]:
        if row.get("run_id") and not (export / row["label"]).exists():
            child = quality / "cells" / row["run_id"]
            if child.is_dir():
                _export(child, export / row["label"], CELL_FILES)
    _finalize_stage(quality, export / "quality-suite", SUITE_FILES)
    timing_start = time.monotonic()
    quality_seconds = timing_start - quality_started
    if not ok or quality_seconds > QUALITY_SECONDS or rss.breached:
        reason = (
            "P5 suite process-tree RSS limit exceeded"
            if rss.breached
            else "P5 quality stage wall-time limit exceeded"
            if quality_seconds > QUALITY_SECONDS
            else terminal["reason"]
        )
        write_json(
            root / "terminal.json",
            {
                "status": "failed",
                "stage": "quality",
                "reason": reason,
                "quality_stage_wall_seconds": quality_seconds,
                "quality_supervised_worker_seconds": terminal["process_wall_seconds"],
                "peak_suite_process_tree_rss_bytes": rss.peak,
                "timing": "unexecuted",
            },
        )
        _export(root, export / "suite", ("terminal.json",))
        return root, False
    _emit(
        {
            "event": "quality_stage_finished",
            "suite": str(root),
            "quality_run": str(quality),
            "export": str(export / "quality-suite"),
            "timing_starts_after_ack": True,
            "quality_supervised_worker_seconds": terminal["process_wall_seconds"],
            "quality_stage_wall_seconds": quality_seconds,
        }
    )
    return root, _timing_stage(
        root, quality, parent, export, quality_seconds, rss, timing_start=timing_start
    )


def launch(config: Path, data: Path, output: Path, parent: Path, export: Path) -> tuple[Path, bool]:
    with SuiteRSS() as rss:
        return _launch(config, data, output, parent, export, rss)


def main() -> int:
    if sys.argv[1:2] in (["_quality_suite"], ["_cell"], ["_timing_worker"]):
        operation, path, *worker_args = sys.argv[1:]
        run = Path(path)
        running = read_json(run / "manifest.json")
        if running["status"] != "running" or running["experiment_family"] != FAMILY:
            raise ValueError("missing P5 watchdog record")
        if operation == "_quality_suite":
            config, data, parent, export = map(Path, worker_args)
            _quality_suite(run, config, data, parent, export)
        elif operation == "_cell":
            suite, parent_path, b, o, seed, variant = worker_args
            _cell(run, Path(suite), Path(parent_path), Cell(int(b), int(o), int(seed), variant))
        else:
            quality, parent_path, b, o, seed = worker_args
            _timing_worker(run, Path(quality), Path(parent_path), int(b), int(o), int(seed))
        return 0
    parser = argparse.ArgumentParser(description="Run the registered P5 hierarchy ablation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--parent-suite", type=Path, default=Path("experiments") / PARENT_SUITE)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    run, ok = launch(
        *(
            path.resolve()
            for path in (
                args.config,
                args.data_dir,
                args.output_root,
                args.parent_suite,
                args.results_root,
            )
        )
    )
    print(f"{'Recorded' if ok else 'Failed'} P5: {run}", file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
