"""Watchdog-bound local P2 suite, cell runner and compact evidence export."""

from __future__ import annotations

import argparse
import math
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .p2_config import (
    BATCH,
    CELL_SECONDS,
    CHECKPOINT_STEPS,
    CONDITIONS,
    CONTROL,
    FAMILY,
    JOINT_ATOL,
    PARENT_SPEC,
    SCHEMA,
    SPEC,
    STEPS,
    SUITE_SECONDS,
    TRAIN_TARGETS,
    VAL_TARGETS,
    Cell,
    cells,
    config_hash,
    load_config,
    validate_config,
)
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import RSS_BYTES, supervise

if TYPE_CHECKING:
    from torch import Tensor
    from torch.optim import AdamW

    from .p2_model import FollowupModel
    from .pilot_model import PilotModel

P1_COMMIT = "0b0555c86a8690122a2ba9d07f62235c4b1b384c"
DATA_APPROVAL = "docs/decisions/ADR-0004-real-data-pilot-prerequisite.md"
DEFAULT_CONFIG = Path("configs/p2_optimization_followup.toml")
DEFAULT_RESULTS = Path("results/p2-2026-11-12")


def _fields(**extra: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "question_id": FAMILY,
        "hypothesis": "exploratory sensitivity to controlled optimization inputs",
        "authorized_spec_reference": SPEC,
        "parent_spec_reference": PARENT_SPEC,
        "human_local_data_approval": DATA_APPROVAL,
        "reviewer_override": "human-authorized Codex reviewer per ADR-0003",
        **extra,
    }


def _update(run: Path, **fields: Any) -> None:
    manifest = read_json(run / "manifest.json")
    manifest.update(fields)
    write_json(run / "manifest.json", manifest)


def _prepare(run: Path, config: dict[str, Any]) -> dict[str, Any]:
    write_json(run / "config.resolved.json", config)
    source = record_source(run, Path.cwd(), spec=SPEC)
    environment = record_environment(run, family=FAMILY)
    _update(
        run,
        code_commit=source["code_commit"],
        dirty=source["dirty"],
        source_sha256=source["archive"]["sha256"],
        lock_sha256=source["lock_sha256"],
        spec_sha256=source["spec_sha256"],
        config_sha256=config_hash(config),
        parent_spec_sha256=source["archive_file_sha256"][PARENT_SPEC],
        data_approval_sha256=source["archive_file_sha256"][DATA_APPROVAL],
        environment=environment,
        metrics_not_measured={
            "matched_compute": "control bypasses retrieval",
            "physical_io": "RAM-only; logical lookup work is not physical I/O",
            "inference_latency": "fixed-length objective only",
        },
    )
    runtime_supported()
    return source


def _verify_original_sources(source: dict[str, Any]) -> None:
    """Check the archived P1 source set and old protocol against the pinned Git tree."""
    root = Path(source["git_root"])
    listing = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            P1_COMMIT,
            "--",
            "src/arborlm",
            PARENT_SPEC,
            DATA_APPROVAL,
        ],
    )
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw)
        original = subprocess.check_output(["git", "-C", str(root), "show", f"{P1_COMMIT}:{name}"])
        if source["archive_file_sha256"].get(name) != sha256(original):
            raise ValueError(f"original P1 source/spec differs: {name}")


def _shared(run: Path) -> dict[str, str]:
    manifest = read_json(run / "manifest.json")
    return {
        key: manifest[key]
        for key in (
            "source_sha256",
            "lock_sha256",
            "spec_sha256",
            "config_sha256",
            "parent_spec_sha256",
            "data_approval_sha256",
        )
    }


def _optimizer(model: FollowupModel) -> AdamW:
    from torch import nn

    from .engine import optimizer_for

    return optimizer_for(nn.ParameterList(p for p in model.parameters() if p.requires_grad))


def _tensor_bytes_hash(model: FollowupModel) -> str:
    # NumPy is not installed. Serialization preserves dtype/shape and tensor bytes.
    import io

    import torch

    data = io.BytesIO()
    torch.save(model.memory_state.state_dict(), data)
    return sha256(data.getvalue())


def _training_step(
    model: FollowupModel,
    optimizer: AdamW,
    batch: Tensor,
    step: int,
) -> tuple[float, float, float | None]:
    import torch
    from torch import nn

    from .pilot_metrics import loss_for

    optimizer.zero_grad(set_to_none=True)
    logits, lookup = model(batch[:, :-1])
    loss = loss_for(logits, batch[:, 1:], "mean")
    if not math.isfinite(loss.item()):
        raise ValueError(f"non-finite P2 training loss at step {step}")
    loss.backward()  # type: ignore[no-untyped-call]
    params = [p for p in model.parameters() if p.requires_grad]
    if any(p.grad is None for p in params):
        raise ValueError(f"missing trainable gradient at step {step}")
    router_grad = None
    if model.cell.condition == CONTROL:
        if lookup is not None or any(p.grad is not None for p in model.memory_state.parameters()):
            raise ValueError("control memory was active during training")
    else:
        router = model.memory_state.router
        if (
            lookup is None
            or lookup.branch_ids is None
            or lookup.route_scores is None
            or router.grad is None
            or not bool(lookup.route_scores.isfinite().all())
        ):
            raise ValueError(f"missing/non-finite routing state at step {step}")
        router_grad = float(torch.linalg.vector_norm(router.grad))
        if not math.isfinite(router_grad):
            raise ValueError(f"non-finite router gradient at step {step}")
    norm = nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
    optimizer.step()
    if not all(bool(p.isfinite().all()) for p in params):
        raise ValueError(f"non-finite P2 parameter after step {step}")
    return loss.item(), norm.item(), router_grad


def _evaluate(model: FollowupModel, validation: Tensor, *, memory_enabled: bool) -> dict[str, Any]:
    from .pilot_metrics import evaluate

    # FollowupModel uses the P1 forward and implements the same evaluation interface.
    metrics = evaluate(cast("PilotModel", model), validation)
    if metrics["target_tokens"] != VAL_TARGETS or not math.isfinite(metrics["nll"]):
        raise ValueError("wrong P2 validation count or non-finite loss")
    routing = metrics["retrieval"]
    if memory_enabled:
        if (
            routing is None
            or routing["queries"] != VAL_TARGETS
            or routing["router"] is None
            or not math.isfinite(routing["router"]["normalized_top1_entropy"])
            or not math.isfinite(routing["router"]["mean_normalized_query_router_entropy"])
        ):
            raise ValueError("missing/non-finite P2 evaluation routing evidence")
    elif routing is not None:
        raise ValueError("bypassed memory generated routing evidence")
    return metrics


def _permutation(run: Path, condition: str, permutation: tuple[Tensor, int]) -> dict[str, Any]:
    ids, seed = permutation
    path = run / f"permutation-{condition}.json"
    write_json(
        path,
        {
            "condition": condition,
            "generator_seed": seed,
            "direction": "new slot i receives original row permutation_ids[i]",
            "permutation_ids": ids.tolist(),
        },
    )
    return {"file": path.name, "sha256": file_sha256(path), "generator_seed": seed}


def _diagnostics(
    run: Path,
    cell: Cell,
    checkpoint: Path,
    checkpoint_hash: str,
    identity: dict[str, Any],
    validation: Tensor,
    final: dict[str, Any],
) -> dict[str, Any]:
    from .p2_checkpoint import restore
    from .p2_model import FollowupModel, intervene

    index_hash = file_sha256(checkpoint / "index.json")
    original = final["nll"]
    results = {}
    for condition in CONDITIONS if cell.condition != CONTROL else ("enabled",):
        model = FollowupModel(cell)
        optimizer = _optimizer(model)
        if restore(checkpoint, model, optimizer, identity) != (STEPS, STEPS * BATCH, TRAIN_TARGETS):
            raise ValueError("P2 final checkpoint counters differ")
        perm = intervene(model, condition)
        perm_record = _permutation(run, condition, perm) if perm is not None else None
        metrics = _evaluate(model, validation, memory_enabled=not model.bypass)
        nll = metrics["nll"]
        unchanged = (
            file_sha256(checkpoint / "state.pt") == checkpoint_hash
            and file_sha256(checkpoint / "index.json") == index_hash
        )
        correct = (
            struct.pack("!d", nll) == struct.pack("!d", original)
            if condition == "enabled"
            else math.isclose(nll, original, rel_tol=0, abs_tol=JOINT_ATOL)
            if condition == "joint_within_branch"
            else None
        )
        result = {
            **metrics,
            "condition": condition,
            "training_target_tokens": 0,
            "parent_checkpoint_state_sha256": checkpoint_hash,
            "parent_checkpoint_index_sha256": index_hash,
            "parent_final_nll": original,
            "delta_from_parent_final_nll": nll - original,
            "checkpoint_unchanged": unchanged,
            "invariance_passed": correct,
            "permutation": perm_record,
        }
        append_event(run, {"event": "intervention_evaluation", **result})
        results[condition] = result
        if not unchanged or correct is False:
            raise ValueError(f"P2 intervention correctness failed: {condition}")
    return results


def _cell(run: Path, suite: Path, cell: Cell) -> None:
    import torch

    from .engine import configure_cpu
    from .p2_checkpoint import save
    from .p2_data import load_frozen, order_ids
    from .p2_model import FollowupModel

    config = validate_config(read_json(suite / "config.resolved.json"))
    _prepare(run, config)
    shared = _shared(suite)
    if _shared(run) != shared:
        raise ValueError("P2 cell source/config/spec does not match frozen suite")
    suite_manifest = read_json(suite / "manifest.json")
    dataset_hash = suite_manifest["dataset_manifest_sha256"]
    train, validation, dataset = load_frozen(suite / "frozen-data", dataset_hash)
    write_json(run / "dataset_manifest.json", dataset)
    configure_cpu()
    ids = order_ids(cell.order)
    order_path = run / "order.json"
    write_json(
        order_path,
        {
            "generator_seed": cell.order,
            "rank_interval": [0, ids.numel()],
            "ranked_train_row_ids": ids.tolist(),
        },
    )
    order_hash = file_sha256(order_path)
    if order_hash != suite_manifest["order_sha256"][str(cell.order)]:
        raise ValueError("P2 cell order differs from the registered suite order")
    batches = train[ids]
    model = FollowupModel(cell)
    optimizer = _optimizer(model)
    stored = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if stored != 225793 or trainable != (27392 if cell.condition == CONTROL else 225793):
        raise ValueError("P2 stored/trainable parameter count mismatch")
    control = cell.condition == CONTROL
    frozen_before = _tensor_bytes_hash(model) if control else None
    router_initial = model.memory_state.router.detach().clone()
    identity = {
        **shared,
        "cell": cell.fields(),
        "dataset_manifest_sha256": dataset_hash,
        "order_sha256": order_hash,
    }
    _update(
        run,
        dataset_manifest_sha256=dataset_hash,
        order_sha256=order_hash,
        checkpoint_identity=identity,
        model={
            "parameters_stored": stored,
            "parameters_trainable": trainable,
            "parameters_used": 27392 if control else None,
            "parameters_used_note": "control bypasses all memory"
            if control
            else "learned retrieval touches a query-dependent subset; see logical work metrics",
            "memory_bypassed": control,
            "memory_frozen": control,
        },
        seeds={
            **cell.fields(),
            "global_python_torch_runtime": 42,
            "component_generator_offsets": [1000, 2000, 3000, 4000, 5000],
        },
    )
    initial = _evaluate(model, validation, memory_enabled=not control)
    append_event(run, {"event": "evaluation", "completed_step": 0, **initial})
    start = time.monotonic()
    checkpoints: dict[str, str] = {}
    router_nonzero = 0
    train_tokens = 0
    for step in range(1, STEPS + 1):
        left = (step - 1) * BATCH
        batch = batches[left : left + BATCH]
        loss, gradient, router_gradient = _training_step(model, optimizer, batch, step)
        router_nonzero += int(router_gradient is not None and router_gradient > 0)
        train_tokens += batch[:, 1:].numel()
        append_event(
            run,
            {
                "event": "train_step",
                "completed_step": step,
                "next_order_cursor": step * BATCH,
                "pre_update_loss": loss,
                "loss_units": "nats_per_byte",
                "pre_clip_gradient_norm": gradient,
                "pre_clip_router_gradient_norm": router_gradient,
                "target_tokens_cumulative": train_tokens,
            },
        )
        if step in CHECKPOINT_STEPS:
            name = f"checkpoint-{step}"
            checkpoints[name] = save(run / name, model, optimizer, step, identity)
    training_seconds = time.monotonic() - start
    if train_tokens != TRAIN_TARGETS:
        raise ValueError("incorrect P2 training target count")
    final = _evaluate(model, validation, memory_enabled=not control)
    append_event(run, {"event": "evaluation", "completed_step": STEPS, **final})
    frozen_after = _tensor_bytes_hash(model) if control else None
    if control and frozen_after != frozen_before:
        raise ValueError("control memory changed")
    movement = (
        None
        if control
        else float(torch.linalg.vector_norm(model.memory_state.router.detach() - router_initial))
    )
    if movement is not None and not math.isfinite(movement):
        raise ValueError("non-finite learned router movement")
    # Release the training model/optimizer before creating evaluation-only restorations.
    del model, optimizer
    final_name = f"checkpoint-{STEPS}"
    interventions = _diagnostics(
        run, cell, run / final_name, checkpoints[final_name], identity, validation, final
    )
    if _shared(run) != _shared(suite):
        raise ValueError("P2 shared identity changed during cell")
    current = _source_unchanged(run, shared["source_sha256"])
    if not current:
        raise ValueError("P2 source changed during cell")
    write_json(
        run / "result.json",
        {
            "outcome": "completed",
            "cell": cell.fields(),
            "completed_steps": STEPS,
            "training_target_tokens": train_tokens,
            "training_loop_seconds": training_seconds,
            "training_target_tokens_per_second": train_tokens / training_seconds,
            "initial": initial,
            "final": final,
            "interventions": interventions,
            "learned_router_movement_l2": movement,
            "learned_router_nonzero_gradient_steps": None if control else router_nonzero,
            "frozen_control_memory_initial_sha256": frozen_before,
            "frozen_control_memory_final_sha256": frozen_after,
            "checkpoint_state_sha256": checkpoints,
        },
    )


def _source_unchanged(run: Path, expected: str) -> bool:
    # Recheck the archived source allowlist without rewriting the original evidence.
    with tempfile.TemporaryDirectory(prefix=".verify-source-", dir=run) as stage:
        snapshot = record_source(Path(stage), Path.cwd(), spec=SPEC)
        return str(snapshot["archive"]["sha256"]) == expected


def _label(cell: Cell) -> str:
    tag = "control" if cell.condition == CONTROL else f"m{cell.memory}"
    return f"b{cell.backbone}-o{cell.order}-{tag}"


CELL_EXPORT = (
    "config.resolved.json",
    "manifest.json",
    "source.json",
    "environment.json",
    "dataset_manifest.json",
    "order.json",
    "metrics.jsonl",
    "result.json",
    "terminal.json",
    "stdout.log",
    "stderr.log",
    "permutation-values_permuted.json",
    "permutation-joint_within_branch.json",
    "checkpoint-128/index.json",
    "checkpoint-256/index.json",
)
SUITE_EXPORT = (
    "config.resolved.json",
    "manifest.json",
    "source.json",
    "environment.json",
    "cells.json",
    "metrics.jsonl",
    "result.json",
    "terminal.json",
    "stdout.log",
    "stderr.log",
    "frozen-data/dataset_manifest.json",
    "order-301.json",
    "order-302.json",
    "order-303.json",
)


def _export(run: Path, destination: Path, names: tuple[str, ...]) -> None:
    from .checkpoint import _publish_exclusive

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".p2-export-", dir=destination.parent) as stage:
        temporary = Path(stage) / "bundle"
        temporary.mkdir()
        for name in names:
            source = run / name
            if source.is_file():
                target = temporary / name
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(target, source.read_bytes())
        _publish_exclusive(temporary, destination)


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    from .p2_analysis import describe

    path = run / "cells.json"
    status = read_json(path) if path.exists() else _status()
    completed = all(item["status"] == "completed" for item in status) and reason is None
    for item in status:
        if item["status"] == "running":
            item.update(status="interrupted", reason=reason)
        elif item["status"] == "unexecuted":
            item["reason"] = reason
    totals = sum(item.get("training_target_tokens", 0) for item in status)
    report = {
        "outcome": "completed" if completed else "failed",
        "cells": status,
        "reason": reason,
        "total_completed_training_targets": totals,
        "parent_promotion_gate": "failed_unchanged",
    }
    if completed:
        if totals != 4718592:
            raise ValueError("incorrect P2 suite token count")
        controls = {
            (item["backbone"], item["order"]): item["final_nll"]
            for item in status
            if item["condition"] == CONTROL
        }
        rows = [
            {
                "backbone": item["backbone"],
                "memory": item["memory"],
                "order": item["order"],
                **item["condition_nlls"],
                "control": controls[item["backbone"], item["order"]],
            }
            for item in status
            if item["condition"] != CONTROL
        ]
        report["descriptive_analysis"] = describe(rows)
    return report


def _status() -> list[dict[str, Any]]:
    return [
        {**cell.fields(), "label": _label(cell), "status": "unexecuted", "run_id": None}
        for cell in cells()
    ]


def _suite(run: Path, config_path: Path, data: Path, export: Path) -> None:
    import torch

    from .p2_config import ORDERS
    from .p2_data import freeze, order_ids

    status = _status()
    write_json(run / "cells.json", status)
    try:
        if export.exists():
            raise FileExistsError(f"refuse to overwrite prior P2 compact export: {export}")
        export.mkdir(parents=True)
        config = load_config(config_path)
        source = _prepare(run, config)
        _verify_original_sources(source)
        dataset = run / "frozen-data"
        dataset.mkdir()
        manifest = freeze(dataset, data)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        order_hashes = {}
        for seed in ORDERS:
            ids = order_ids(seed)
            path = run / f"order-{seed}.json"
            write_json(
                path,
                {
                    "generator_seed": seed,
                    "rank_interval": [0, ids.numel()],
                    "ranked_train_row_ids": ids.tolist(),
                },
            )
            order_hashes[str(seed)] = file_sha256(path)
        _update(
            run,
            dataset_manifest_sha256=sha256(canonical_json(manifest)),
            order_sha256=order_hashes,
            output_results=str(export),
            reporting_pauses_seconds=0.0,
            reporting_pause_method="no in-suite pauses",
        )
        print(
            canonical_json({"event": "suite_started", "suite": str(run), "results": str(export)})
            .decode()
            .strip(),
            flush=True,
        )
        for cell, item in zip(cells(), status, strict=True):
            label = _label(cell)

            def worker(child: Path) -> list[str]:
                item.update(run_id=child.name, status="running")
                write_json(run / "cells.json", status)
                return [
                    sys.executable,
                    "-m",
                    "arborlm.optimization_followup",
                    "_cell",
                    str(child),
                    str(run),
                    str(cell.backbone),
                    str(cell.memory),
                    str(cell.order),
                    cell.condition,
                ]

            child, ok = supervise(
                run / "cells",
                "p2_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CELL_SECONDS,
                rss_bytes=RSS_BYTES,
                worker_argv=worker,
                manifest_fields=_fields(parent_run_id=run.name, **cell.fields()),
                run_prefix="P2",
            )
            terminal = read_json(child / "terminal.json")
            item.update(status=terminal["status"], reason=terminal["reason"])
            if ok:
                result = read_json(child / "result.json")
                item.update(
                    training_target_tokens=result["training_target_tokens"],
                    initial_nll=result["initial"]["nll"],
                    final_nll=result["final"]["nll"],
                    condition_nlls={
                        name: values["nll"] for name, values in result["interventions"].items()
                    },
                    wall_seconds=terminal["process_wall_seconds"],
                    peak_rss_bytes=terminal["peak_process_tree_rss_bytes"],
                )
            _export(child, export / label, CELL_EXPORT)
            item["compact_export"] = str(export / label)
            write_json(run / "cells.json", status)
            event = {"event": "cell_finished", **item}
            append_event(run, event)
            print(canonical_json(event).decode().strip(), flush=True)
            if not ok:
                raise RuntimeError(f"P2 cell {label} failed; see {child / 'terminal.json'}")
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        raise
    write_json(run / "result.json", _summary(run))


def _follow_stdout(path: Path, stop: threading.Event) -> None:
    position = 0
    while True:
        if path.exists():
            with path.open("rb") as stream:
                stream.seek(position)
                while line := stream.readline():
                    if not line.endswith(b"\n"):
                        break
                    position = stream.tell()
                    print(line.decode().rstrip(), flush=True)
        if stop.wait(0.1):
            # Worker has exited and flushed all progress lines. Drain any final writes.
            if path.exists():
                with path.open("rb") as stream:
                    stream.seek(position)
                    for line in stream:
                        print(line.decode().rstrip(), flush=True)
            return


def launch(config: Path, data: Path, output: Path, export: Path) -> tuple[Path, bool]:
    if export.exists():
        raise FileExistsError(f"refuse to overwrite prior P2 compact export: {export}")
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
            "arborlm.optimization_followup",
            "_suite",
            str(run),
            str(config),
            str(data),
            str(export),
        ]

    try:
        run, ok = supervise(
            output,
            "p2_suite",
            [],
            requested_argv=sys.argv,
            process_seconds=SUITE_SECONDS,
            rss_bytes=RSS_BYTES,
            worker_argv=worker,
            manifest_fields=_fields(),
            run_prefix="P2",
            nested_workers=True,
        )
    finally:
        stop.set()
        if reporter is not None:
            reporter.join()
    if not ok and not (run / "result.json").exists():
        write_json(run / "result.json", _summary(run, read_json(run / "terminal.json")["reason"]))
    # Preserve an interrupted active child's partial logs if the suite worker did not export them.
    for item in read_json(run / "result.json")["cells"]:
        if item.get("run_id") and not (export / item["label"]).exists():
            child = run / "cells" / item["run_id"]
            if child.is_dir():
                _export(child, export / item["label"], CELL_EXPORT)
    _export(run, export / "suite", SUITE_EXPORT)
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
            raise ValueError("missing supervising P2 watchdog record")
        if args.operation == "_suite":
            _suite(args.run, *map(Path, args.arguments))
        else:
            suite, b, m, o, condition = args.arguments
            _cell(args.run, Path(suite), Cell(int(b), int(m), int(o), condition))
        return 0
    parser = argparse.ArgumentParser(description="Run the preregistered P2 CPU follow-up")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    run, ok = launch(
        args.config.resolve(),
        args.data_dir.resolve(),
        args.output_root.resolve(),
        args.results_root.resolve(),
    )
    print(
        f"{'Recorded' if ok else 'Failed'} P2 suite: {run}",
        file=sys.stdout if ok else sys.stderr,
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
