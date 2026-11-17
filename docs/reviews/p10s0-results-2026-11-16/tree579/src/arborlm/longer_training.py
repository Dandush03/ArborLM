"""Run the bounded ADR-0008 continuation with immutable P2 parents."""

from __future__ import annotations

import argparse
import math
import random
import struct
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .optimization_followup import (
    CELL_EXPORT,
    DATA_APPROVAL,
    SUITE_EXPORT,
    _evaluate,
    _export,
    _follow_stdout,
    _label,
    _optimizer,
    _permutation,
    _source_unchanged,
    _tensor_bytes_hash,
    _training_step,
    _update,
)
from .p2_config import CONDITIONS, CONTROL, JOINT_ATOL, Cell, cells
from .p3_config import (
    ADDITIONAL_TARGETS,
    BATCH,
    CELL_SECONDS,
    DURATIONS,
    END,
    FAMILY,
    LIFETIME_TARGETS,
    PARENT_FREEZE,
    PARENT_RESULTS,
    PARENT_SPEC,
    PARENT_SUITE,
    SCHEMA,
    SPEC,
    START,
    SUITE_SECONDS,
    batch_offset,
    config_hash,
    counters,
    load_config,
    validate_config,
)
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import RSS_BYTES, supervise

if TYPE_CHECKING:
    from torch import Tensor

    from .p2_model import FollowupModel

DEFAULT_CONFIG = Path("configs/p3_longer_training.toml")
DEFAULT_RESULTS = Path("results/p3-lt-2026-11-12")
CELL_FILES = CELL_EXPORT + (
    "checkpoint-512/index.json",
    "checkpoint-1024/index.json",
    "parent_provenance.json",
    "duration_status.json",
)
SUITE_FILES = SUITE_EXPORT + ("parent_provenance.json",)
SUITE_SUPERVISOR_FILES = ("manifest.json", "terminal.json", "stdout.log", "stderr.log")
SUITE_WORKER_FILES = tuple(name for name in SUITE_FILES if name not in SUITE_SUPERVISOR_FILES)
IDENTITY_FIELDS = (
    "source_sha256",
    "spec_sha256",
    "parent_spec_sha256",
    "config_sha256",
    "lock_sha256",
    "data_approval_sha256",
)


def _fields(**extra: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "question_id": FAMILY,
        "hypothesis": "longer optimization on fixed examples and memory dependence",
        "authorized_spec_reference": SPEC,
        "parent_spec_reference": PARENT_SPEC,
        "parent_p2_suite_id": PARENT_SUITE,
        "parent_p2_source_freeze": PARENT_FREEZE,
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
        config_sha256=config_hash(config),
        lock_sha256=source["lock_sha256"],
        data_approval_sha256=source["archive_file_sha256"][DATA_APPROVAL],
        environment=environment,
        metrics_not_measured={
            "matched_compute": "control bypasses retrieval",
            "physical_io": "RAM-only; logical lookup work is not physical I/O",
            "inference_latency": "fixed-length objective only",
        },
    )
    runtime_supported()
    return source, environment


def _shared(run: Path) -> dict[str, str]:
    manifest = read_json(run / "manifest.json")
    return {key: manifest[key] for key in IDENTITY_FIELDS}


@contextmanager
def _isolated_rng() -> Iterator[None]:
    import torch

    state = random.getstate()
    try:
        with torch.random.fork_rng(devices=[]):
            yield
    finally:
        random.setstate(state)


def _bitwise_nll(first: float, second: float) -> bool:
    return struct.pack("!d", first) == struct.pack("!d", second)


def _duration(
    run: Path,
    cell: Cell,
    checkpoint: Path,
    checkpoint_hash: str,
    identity: dict[str, Any],
    validation: Tensor,
    model: FollowupModel,
    step: int,
) -> dict[str, Any]:
    from .p2_model import FollowupModel, intervene
    from .p3_checkpoint import restore

    control = cell.condition == CONTROL
    index_hash = file_sha256(checkpoint / "index.json")
    initial_permutations: dict[str, dict[str, Any]] = {}
    with _isolated_rng():
        # The reference comes from the live state immediately after the atomic checkpoint.
        reference = _evaluate(model, validation, memory_enabled=not control)
        append_event(
            run,
            {
                "event": "duration_reference",
                "global_step": step,
                "panel": "P3_scientific",
                "training_target_tokens": 0,
                "checkpoint_state_sha256": checkpoint_hash,
                "checkpoint_index_sha256": index_hash,
                **reference,
            },
        )
        conditions: dict[str, Any] = {}
        for condition in CONDITIONS if not control else ("enabled",):
            clone = FollowupModel(cell)
            clone_optimizer = _optimizer(clone)
            if restore(checkpoint, clone, clone_optimizer, identity) != counters(step):
                raise ValueError("P3 checkpoint duration mismatch during intervention")
            permutation = intervene(clone, condition)
            if permutation is not None:
                # Recompute and verify the same artifact at each duration without overwriting it.
                ids, seed = permutation
                file = run / f"permutation-{condition}.json"
                if not file.exists():
                    initial_permutations[condition] = _permutation(run, condition, permutation)
                else:
                    stored = read_json(file)
                    if (
                        stored["generator_seed"] != seed
                        or stored["permutation_ids"] != ids.tolist()
                    ):
                        raise ValueError("P3 intervention permutation changed across durations")
                    initial_permutations[condition] = {
                        "file": file.name,
                        "sha256": file_sha256(file),
                        "generator_seed": seed,
                    }
            measured = _evaluate(clone, validation, memory_enabled=not clone.bypass)
            nll, baseline = measured["nll"], reference["nll"]
            unchanged = (
                file_sha256(checkpoint / "state.pt") == checkpoint_hash
                and file_sha256(checkpoint / "index.json") == index_hash
            )
            invariant = (
                _bitwise_nll(nll, baseline)
                if condition == "enabled"
                else math.isclose(nll, baseline, abs_tol=JOINT_ATOL, rel_tol=0)
                if condition == "joint_within_branch"
                else None
            )
            result = {
                **measured,
                "global_step": step,
                "condition": condition,
                "panel": "P3_scientific",
                "training_target_tokens": 0,
                "parent_checkpoint_state_sha256": checkpoint_hash,
                "parent_checkpoint_index_sha256": index_hash,
                "parent_p2_checkpoint_state_sha256": identity["parent"]["checkpoint_state_sha256"],
                "reference_nll": baseline,
                "delta_from_reference_nll": nll - baseline,
                "checkpoint_unchanged": unchanged,
                "invariance_passed": invariant,
                "permutation": initial_permutations.get(condition),
            }
            append_event(run, {"event": "duration_intervention", **result})
            if not unchanged or invariant is False:
                raise ValueError(f"P3 intervention correctness failed at {step}: {condition}")
            conditions[condition] = result
    return {
        "reference": reference,
        "interventions": conditions,
        "checkpoint_state_sha256": checkpoint_hash,
        "checkpoint_index_sha256": index_hash,
    }


def _cell(run: Path, suite: Path, parent_suite: Path, cell: Cell) -> None:
    import torch

    from .engine import configure_cpu
    from .p2_model import FollowupModel
    from .p3_checkpoint import convert, save
    from .p3_data import load_frozen
    from .p3_parent import verify_cell

    config = validate_config(read_json(suite / "config.resolved.json"))
    _, environment = _prepare(run, config)
    shared = _shared(suite)
    if _shared(run) != shared:
        raise ValueError("P3 source/config/spec does not match frozen suite")
    suite_manifest = read_json(suite / "manifest.json")
    dataset_hash = suite_manifest["dataset_manifest_sha256"]
    train, prior, validation, dataset = load_frozen(suite / "frozen-data", dataset_hash)
    write_json(run / "dataset_manifest.json", dataset)
    parent_bundle = read_json(suite / "parent_provenance.json")
    if sha256(canonical_json(parent_bundle)) != suite_manifest["parent_provenance_sha256"]:
        raise ValueError("P3 parent map changed after suite preflight")
    expected_parent = parent_bundle[_label(cell)]
    parent = verify_cell(
        parent_suite,
        PARENT_RESULTS,
        {
            **cell.fields(),
            "run_id": expected_parent["run_id"],
            "final_nll": expected_parent["original_P2_panel_nll"],
        },
        cell,
        environment,
    )
    if parent.provenance != expected_parent:
        raise ValueError("P3 parent no longer matches suite preflight")
    write_json(run / "parent_provenance.json", parent.provenance)
    order_file = run / "order.json"
    atomic_write(order_file, parent.order_file.read_bytes())
    order_hash = file_sha256(order_file)
    if order_hash != parent.identity["order_sha256"]:
        raise ValueError("P3 order copy differs from parent")
    identity = {
        **shared,
        "cell": cell.fields(),
        "dataset_manifest_sha256": dataset_hash,
        "order_sha256": order_hash,
        "parent": parent.provenance,
    }
    configure_cpu()
    model = FollowupModel(cell)
    optimizer = _optimizer(model)
    control = cell.condition == CONTROL
    stored = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if stored != 225793 or trainable != (27392 if control else 225793):
        raise ValueError("P3 stored/trainable parameter count mismatch")
    _update(
        run,
        dataset_manifest_sha256=dataset_hash,
        order_sha256=order_hash,
        checkpoint_identity=identity,
        parent_p2_run_id=parent.provenance["run_id"],
        parent_p2_checkpoint_state_sha256=parent.provenance["checkpoint_state_sha256"],
        model={
            "parameters_stored": stored,
            "parameters_trainable": trainable,
            "parameters_used": 27392 if control else None,
            "memory_bypassed": control,
            "memory_frozen": control,
        },
        seeds=cell.fields(),
        resumed_rng=True,
    )
    ordered = train[torch.tensor(parent.order_ids, dtype=torch.int64, device="cpu")]
    start_path = run / f"checkpoint-{START}"
    checkpoint_hash = convert(
        parent.checkpoint, parent.identity, start_path, model, optimizer, identity
    )
    parent.check_unchanged()
    checkpoints = {start_path.name: checkpoint_hash}
    restored_router = model.memory_state.router.detach().clone()
    frozen_before = _tensor_bytes_hash(model) if control else None
    with _isolated_rng():
        engineering = _evaluate(model, prior, memory_enabled=not control)
    integrity_passed = _bitwise_nll(engineering["nll"], parent.final_nll)
    engineering.update(
        event="parent_restore_integrity",
        panel="P2_integrity_only",
        global_step=START,
        recorded_parent_nll=parent.final_nll,
        bitwise_passed=integrity_passed,
        excluded_from_scientific_analysis=True,
        training_target_tokens=0,
        original_parent_state_sha256=parent.provenance["checkpoint_state_sha256"],
    )
    append_event(run, engineering)
    if not integrity_passed:
        raise ValueError("P3 restore did not replay original P2-panel result bitwise")
    durations = {}
    train_seconds = 0.0
    router_nonzero = 0
    additional_targets = 0

    def duration(step: int, path: Path, digest: str) -> None:
        if control and _tensor_bytes_hash(model) != frozen_before:
            raise ValueError("P3 frozen control memory changed")
        movement = (
            None
            if control
            else float(
                torch.linalg.vector_norm(model.memory_state.router.detach() - restored_router)
            )
        )
        if movement is not None and not math.isfinite(movement):
            raise ValueError("P3 non-finite router movement")
        value = _duration(run, cell, path, digest, identity, validation, model, step)
        parent.check_unchanged()
        evidence = {
            **value,
            **counters(step),
            "zero_new_training_conversion": step == START,
            "learned_router_movement_l2_from_restored_P2": movement,
            "inherited_P2_router_movement_l2": parent.inherited_router_movement,
            "nonzero_router_gradient_updates_since_P2": None if control else router_nonzero,
            "frozen_control_memory_sha256": frozen_before,
        }
        durations[str(step)] = evidence
        append_event(
            run,
            {
                "event": "duration_complete",
                "global_step": step,
                **counters(step),
                "zero_new_training_conversion": step == START,
                "checkpoint_state_sha256": digest,
                "learned_router_movement_l2_from_restored_P2": movement,
                "inherited_P2_router_movement_l2": parent.inherited_router_movement,
                "nonzero_router_gradient_updates_since_P2": None if control else router_nonzero,
                "frozen_control_memory_sha256": frozen_before,
                "parent_checkpoint_unchanged": True,
            },
        )
        write_json(run / "duration_status.json", durations)

    duration(START, start_path, checkpoint_hash)
    phase_start = time.monotonic()
    for step in range(START + 1, END + 1):
        offset = batch_offset(step)
        batch = ordered[offset : offset + BATCH]
        loss, gradient, router_gradient = _training_step(model, optimizer, batch, step)
        router_nonzero += int(router_gradient is not None and router_gradient > 0)
        additional_targets += batch[:, 1:].numel()
        step_counters = counters(step)
        if additional_targets != step_counters["additional_targets"]:
            raise ValueError("P3 training target count mismatch")
        append_event(
            run,
            {
                "event": "train_step",
                "global_step": step,
                "order_offset_for_update": offset,
                "pre_update_loss": loss,
                "loss_units": "nats_per_byte",
                "pre_clip_gradient_norm": gradient,
                "pre_clip_router_gradient_norm": router_gradient,
                **step_counters,
            },
        )
        if step in DURATIONS:
            checkpoint = run / f"checkpoint-{step}"
            digest = save(checkpoint, model, optimizer, step, identity)
            checkpoints[checkpoint.name] = digest
            train_seconds += time.monotonic() - phase_start
            duration(step, checkpoint, digest)
            phase_start = time.monotonic()
    if additional_targets != ADDITIONAL_TARGETS or _shared(run) != _shared(suite):
        raise ValueError("P3 terminal training budget or source identity mismatch")
    if not _source_unchanged(run, shared["source_sha256"]):
        raise ValueError("P3 source archive changed during execution")
    parent.check_unchanged()
    write_json(
        run / "result.json",
        {
            "outcome": "completed",
            "cell": cell.fields(),
            "durations": durations,
            "parent_restore_integrity": engineering,
            "checkpoint_state_sha256": checkpoints,
            "original_parent_checkpoint_unchanged": True,
            "additional_training_targets": additional_targets,
            "lifetime_training_targets": LIFETIME_TARGETS,
            "training_loop_seconds_including_logs_and_saves": train_seconds,
            "additional_training_targets_per_second": additional_targets / train_seconds,
        },
    )


def _status() -> list[dict[str, Any]]:
    return [
        {**cell.fields(), "label": _label(cell), "status": "unexecuted", "run_id": None}
        for cell in cells()
    ]


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    from .p3_analysis import describe

    path = run / "cells.json"
    status = read_json(path) if path.exists() else _status()
    complete = reason is None and all(row["status"] == "completed" for row in status)
    for row in status:
        if row["status"] == "running":
            row.update(status="interrupted", reason=reason)
        elif row["status"] == "unexecuted":
            row["reason"] = reason
    additional = sum(row.get("additional_training_targets", 0) for row in status)
    lifetime = sum(row.get("lifetime_training_targets", 0) for row in status)
    report = {
        "outcome": "completed" if complete else "failed",
        "cells": status,
        "reason": reason,
        "total_completed_additional_training_targets": additional,
        "total_completed_lifetime_training_targets": lifetime,
        "parent_promotion_gate": "failed_unchanged",
    }
    if complete:
        if (additional, lifetime) != (14155776, 18874368):
            raise ValueError("P3 suite training target count mismatch")
        report["descriptive_analysis"] = describe(status)
    return report


def _suite(run: Path, config_path: Path, data: Path, parent_suite: Path, export: Path) -> None:
    from .p3_data import freeze
    from .p3_parent import verify_cell, verify_suite

    status = _status()
    write_json(run / "cells.json", status)
    try:
        export.mkdir(parents=True, exist_ok=False)
        config = load_config(config_path)
        source, environment = _prepare(run, config)
        records = verify_suite(parent_suite, PARENT_RESULTS, source)
        parents = {
            _label(cell): verify_cell(
                parent_suite, PARENT_RESULTS, records[cell], cell, environment
            )
            for cell in cells()
        }
        parent_bundle = {label: parent.provenance for label, parent in parents.items()}
        write_json(run / "parent_provenance.json", parent_bundle)
        dataset = run / "frozen-data"
        dataset.mkdir()
        manifest = freeze(dataset, data)
        _update(
            run,
            dataset_manifest_sha256=sha256(canonical_json(manifest)),
            parent_provenance_sha256=sha256(canonical_json(parent_bundle)),
            parent_p2_suite=str(parent_suite),
            output_results=str(export),
            reporting_pauses_seconds=0.0,
            reporting_pause_method="no in-suite pauses",
            supervisor_finalization_after_worker="final manifest, terminal status and closed "
            "stdout/stderr; partial bundle recovery only after a watchdog kill",
        )
        print(
            canonical_json({"event": "suite_started", "suite": str(run), "results": str(export)})
            .decode()
            .strip(),
            flush=True,
        )
        for cell, row in zip(cells(), status, strict=True):
            label = _label(cell)

            def worker(child: Path) -> list[str]:
                row.update(run_id=child.name, status="running")
                write_json(run / "cells.json", status)
                return [
                    sys.executable,
                    "-m",
                    "arborlm.longer_training",
                    "_cell",
                    str(child),
                    str(run),
                    str(parent_suite),
                    str(cell.backbone),
                    str(cell.memory),
                    str(cell.order),
                    cell.condition,
                ]

            child, ok = supervise(
                run / "cells",
                "p3_lt_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CELL_SECONDS,
                rss_bytes=RSS_BYTES,
                worker_argv=worker,
                manifest_fields=_fields(
                    parent_run_id=run.name,
                    parent_p2_run_id=parents[label].provenance["run_id"],
                    **cell.fields(),
                ),
                run_prefix="P3LT",
            )
            terminal = read_json(child / "terminal.json")
            row.update(status=terminal["status"], reason=terminal["reason"])
            if ok:
                result = read_json(child / "result.json")
                duration_nlls = {
                    step: {
                        condition: value["nll"]
                        for condition, value in block["interventions"].items()
                    }
                    for step, block in result["durations"].items()
                }
                effects = {
                    step: {
                        "enabled_nll": values["enabled"],
                        "D": values["disabled"] - values["enabled"]
                        if "disabled" in values
                        else None,
                        "P": values["values_permuted"] - values["enabled"]
                        if "values_permuted" in values
                        else None,
                    }
                    for step, values in duration_nlls.items()
                }
                row.update(
                    durations=duration_nlls,
                    per_duration_progress=effects,
                    additional_training_targets=result["additional_training_targets"],
                    lifetime_training_targets=result["lifetime_training_targets"],
                    wall_seconds=terminal["process_wall_seconds"],
                    peak_rss_bytes=terminal["peak_process_tree_rss_bytes"],
                )
            _export(child, export / label, CELL_FILES)
            row["compact_export"] = str(export / label)
            write_json(run / "cells.json", status)
            event = {"event": "cell_finished", **row}
            append_event(run, event)
            print(canonical_json(event).decode().strip(), flush=True)
            if not ok:
                raise RuntimeError(f"P3 cell {label} failed; see {child / 'terminal.json'}")
        for parent in parents.values():
            parent.check_unchanged()
        if not _source_unchanged(run, _shared(run)["source_sha256"]):
            raise ValueError("P3 suite source archive changed during execution")
        write_json(run / "result.json", _summary(run))
        _export(run, export / "suite", SUITE_WORKER_FILES)
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        # Normal failures package their partial suite under the worker cap. A hard
        # watchdog kill may prevent this; the outer supervisor then recovers it.
        if export.is_dir() and not (export / "suite").exists():
            _export(run, export / "suite", SUITE_WORKER_FILES)
        raise


def launch(
    config: Path, data: Path, output: Path, parent_suite: Path, export: Path
) -> tuple[Path, bool]:
    parent_suite = parent_suite.resolve()
    if output.resolve().is_relative_to(parent_suite) or export.resolve().is_relative_to(
        parent_suite
    ):
        raise ValueError("P3 must not write outputs inside the registered parent suite")
    if export.exists():
        raise FileExistsError(f"refuse to overwrite prior P3 compact export: {export}")
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
            "arborlm.longer_training",
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
            "p3_lt_suite",
            [],
            requested_argv=sys.argv,
            process_seconds=SUITE_SECONDS,
            rss_bytes=RSS_BYTES,
            worker_argv=worker,
            manifest_fields=_fields(),
            run_prefix="P3LT",
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
        _export(run, suite_export, SUITE_FILES)
    else:
        for name in SUITE_SUPERVISOR_FILES:
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
            raise ValueError("missing supervising P3 watchdog record")
        if args.operation == "_suite":
            _suite(args.run, *map(Path, args.arguments))
        else:
            suite, parent, b, m, o, condition = args.arguments
            _cell(args.run, Path(suite), Path(parent), Cell(int(b), int(m), int(o), condition))
        return 0
    parser = argparse.ArgumentParser(description="Run ADR-0008 bounded longer training")
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
        f"{'Recorded' if ok else 'Failed'} P3-LT suite: {run}",
        file=sys.stdout if ok else sys.stderr,
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
