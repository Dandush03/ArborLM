"""Bounded, sequential P1_SCREEN orchestration and guarded training worker."""

import argparse
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

from .io import canonical_json, read_json, sha256, write_json
from .pilot_config import (
    BATCH_SIZE,
    CHECKPOINT_STEPS,
    DATA_APPROVAL,
    FAMILY,
    RUN_SECONDS,
    SCHEMA,
    SEEDS,
    SPEC,
    STEPS,
    SUITE_SECONDS,
    TRAIN_ROWS,
    VAL_ROWS,
    VARIANTS,
    load_pilot_config,
    pilot_config_hash,
    validate_pilot_config,
)
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import supervise


def _fields(**extra: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "question_id": FAMILY,
        "hypothesis": None,
        "hypothesis_null_reason": "bounded preregistered screen, not a general H1–H5 validation",
        "authorized_spec_reference": SPEC,
        "human_local_data_approval": DATA_APPROVAL,
        "reviewer_override": "human-authorized Codex reviewer per ADR-0003",
        **extra,
    }


def _update(run: Path, **fields: Any) -> None:
    record = read_json(run / "manifest.json")
    record.update(fields)
    write_json(run / "manifest.json", record)


def _prepare(run: Path, config: dict[str, Any]) -> str:
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
        data_approval_sha256=source["archive_file_sha256"][DATA_APPROVAL],
        environment=environment,
        config_sha256=pilot_config_hash(config),
        metrics_not_measured={
            "flops": "lookup work is analytical; actual FLOPs are not measured or matched",
            "ttft_decode": "fixed-length objective only",
            "accelerator_memory": "CPU only",
            "physical_io": "RAM-only model; logical lookup counts are not physical I/O",
            "reasoning": "byte prediction on this validation split only",
        },
    )
    runtime_supported()
    return str(source["spec_sha256"])


def _cells() -> list[dict[str, Any]]:
    return [
        {"variant": variant, "seed": seed, "status": "unexecuted", "run_id": None}
        for seed in SEEDS
        for variant in VARIANTS
    ]


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    cells = read_json(run / "cells.json") if (run / "cells.json").exists() else _cells()
    for cell in cells:
        if cell["status"] == "running":
            cell["status"] = "interrupted"
        if cell["status"] == "unexecuted" and reason is not None:
            cell["reason"] = reason
    return {
        "outcome": "completed" if all(c["status"] == "completed" for c in cells) else "failed",
        "cells": cells,
        "reason": reason,
    }


def _suite(run: Path, config_path: Path, source_dir: Path) -> None:
    from .pilot_data import freeze_dataset

    cells = _cells()
    write_json(run / "cells.json", cells)
    try:
        config = load_pilot_config(config_path)
        _prepare(run, config)
        data_dir = run / "frozen-data"
        data_dir.mkdir()
        dataset = freeze_dataset(data_dir, source_dir)
        dataset_hash = sha256(canonical_json(dataset))
        _update(run, dataset_manifest_sha256=dataset_hash, frozen_dataset="frozen-data")
        for cell in cells:
            variant, seed = cell["variant"], cell["seed"]

            def child_argv(child: Path) -> list[str]:
                cell.update(run_id=child.name, status="running")
                write_json(run / "cells.json", cells)
                return [
                    sys.executable,
                    "-m",
                    "arborlm.pilot",
                    "cell",
                    str(child),
                    str(run),
                    variant,
                    str(seed),
                    dataset_hash,
                ]

            child, ok = supervise(
                run / "cells",
                "pilot_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=RUN_SECONDS,
                worker_argv=child_argv,
                run_prefix="P1",
                manifest_fields=_fields(variant=variant, seed=seed, parent_run_id=run.name),
            )
            terminal = read_json(child / "terminal.json")
            cell.update(status=terminal["status"], reason=terminal["reason"])
            if ok:
                result = read_json(child / "result.json")
                if (
                    result["training_target_tokens"] != STEPS * BATCH_SIZE * 64
                    or result["initial"]["target_tokens"] != VAL_ROWS * 64
                    or result["final"]["target_tokens"] != VAL_ROWS * 64
                ):
                    cell.update(status="failed", reason="incorrect token budget")
                    ok = False
            write_json(run / "cells.json", cells)
            append_event(run, {"event": "cell_finished", **cell})
            if not ok:
                raise RuntimeError(f"{variant}/{seed} failed; see {child / 'terminal.json'}")
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        raise
    write_json(run / "result.json", _summary(run))


def _cell(run: Path, suite: Path, variant: str, seed: int, expected_dataset_hash: str) -> None:
    import torch
    from torch import nn

    from .engine import configure_cpu, optimizer_for
    from .pilot_checkpoint import components, save
    from .pilot_data import CHUNK_BYTES, load_frozen
    from .pilot_metrics import evaluate, loss_for
    from .pilot_model import CONTEXT, COUNTS, PilotModel

    config = validate_pilot_config(read_json(suite / "config.resolved.json"))
    spec_hash = _prepare(run, config)
    parent = read_json(suite / "manifest.json")
    if parent["spec_sha256"] != spec_hash:
        raise ValueError("suite/cell registered spec changed")
    train_bytes, val_bytes, dataset = load_frozen(suite / "frozen-data")
    dataset_hash = sha256(canonical_json(dataset))
    if dataset_hash != expected_dataset_hash:
        raise ValueError("suite/cell frozen dataset hash mismatch")
    write_json(run / "dataset_manifest.json", dataset)
    _update(
        run,
        dataset_manifest_sha256=dataset_hash,
        frozen_dataset_path=str(suite / "frozen-data"),
        seeds={"python": seed, "torch": seed},
    )
    identity = {
        "variant": variant,
        "seed": seed,
        "config_sha256": pilot_config_hash(config),
        "spec_sha256": spec_hash,
        "dataset_manifest_sha256": dataset_hash,
    }
    configure_cpu()
    torch.default_generator.manual_seed(seed)
    random.seed(seed)
    model = PilotModel(variant, seed)
    optimizer = optimizer_for(model)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    stored_buffer = 256 if variant == "fixed_tree" else 0
    if (
        trainable != COUNTS[variant]
        or sum(b.numel() for name, b in model.named_buffers() if name != "mask") != stored_buffer
    ):
        raise ValueError("registered parameter/buffer counts differ")
    _update(
        run,
        model={
            "variant": variant,
            "parameters_trainable": trainable,
            "parameters_total": sum(p.numel() for p in model.parameters()),
            "stored_nontrainable_router_scalars": stored_buffer,
            "stored_model_scalars_excluding_mask": trainable + stored_buffer,
            "components": components(variant),
            "dense_routing": "not_applicable" if model.memory is None else None,
        },
    )
    train = torch.frombuffer(bytearray(train_bytes), dtype=torch.uint8).long().view(-1, CHUNK_BYTES)
    validation = (
        torch.frombuffer(bytearray(val_bytes), dtype=torch.uint8).long().view(-1, CHUNK_BYTES)
    )
    memory = model.memory
    router = memory.router if memory is not None and variant.endswith("_tree") else None
    router_initial = router.detach().clone() if router is not None else None

    def evaluation(step: int) -> dict[str, Any]:
        result = evaluate(model, validation)
        if result["target_tokens"] != VAL_ROWS * CONTEXT:
            raise ValueError("incorrect pilot validation token count")
        append_event(run, {"event": "evaluation", "completed_step": step, **result})
        return result

    initial = evaluation(0)
    checkpoints: dict[str, str] = {}
    train_fallbacks = 0
    router_nonzero_steps = 0
    start = time.monotonic()
    for step in range(1, STEPS + 1):
        start_row = (step - 1) * BATCH_SIZE % TRAIN_ROWS
        batch = train[start_row : start_row + BATCH_SIZE]
        optimizer.zero_grad(set_to_none=True)
        logits, lookup = model(batch[:, :-1])
        loss = loss_for(logits, batch[:, 1:], "mean")
        if not math.isfinite(loss.item()):
            raise ValueError(f"non-finite training loss at step {step}")
        loss.backward()  # type: ignore[no-untyped-call]  # PyTorch stub
        router_grad = None
        if variant == "learned_tree":
            if router is None or router.grad is None:
                raise ValueError("learned router missing gradient tensor")
            router_grad = float(torch.linalg.vector_norm(router.grad))
            if not math.isfinite(router_grad):
                raise ValueError("non-finite learned router gradient")
            router_nonzero_steps += int(router_grad > 0)
        pre_clip = nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        if not all(bool(p.isfinite().all()) for p in model.parameters()):
            raise ValueError(f"non-finite parameter after step {step}")
        fallbacks = (
            int(lookup.exhaustive_queries.sum())
            if lookup is not None and lookup.exhaustive_queries is not None
            else None
        )
        if fallbacks is not None:
            train_fallbacks += fallbacks
        append_event(
            run,
            {
                "event": "train_step",
                "completed_step": step,
                "pre_update_loss": loss.item(),
                "loss_unit": "nats_per_byte",
                "pre_clip_gradient_norm": pre_clip.item(),
                "pre_clip_router_gradient_norm": router_grad,
                "target_tokens_cumulative": step * BATCH_SIZE * CONTEXT,
                "next_row": step * BATCH_SIZE % TRAIN_ROWS,
                "product_key_fallback_queries": fallbacks,
            },
        )
        if step in CHECKPOINT_STEPS:
            name = f"checkpoint-{step}"
            checkpoints[name] = save(run / name, model, optimizer, step, identity)
    elapsed = time.monotonic() - start
    final = evaluation(STEPS)
    if variant == "fixed_tree" and (
        router is None or router_initial is None or not torch.equal(router, router_initial)
    ):
        raise ValueError("fixed router mutated")
    movement = None
    if variant == "learned_tree" and router is not None and router_initial is not None:
        movement = float(torch.linalg.vector_norm(router.detach() - router_initial))
        if not math.isfinite(movement):
            raise ValueError("non-finite learned router movement")
    train_tokens = STEPS * BATCH_SIZE * CONTEXT
    write_json(
        run / "result.json",
        {
            "outcome": "completed",
            "completed_steps": STEPS,
            "training_target_tokens": train_tokens,
            "initial": initial,
            "final": final,
            "train_loop_seconds": elapsed,
            "training_target_tokens_per_second": train_tokens / elapsed,
            "checkpoint_state_sha256": checkpoints,
            "learned_router_movement_l2": movement,
            "learned_router_nonzero_gradient_steps": router_nonzero_steps
            if variant == "learned_tree"
            else None,
            "product_key_training_fallback_queries": train_fallbacks
            if variant == "product_key"
            else None,
            "product_key_training_fallback_fraction": train_fallbacks / train_tokens
            if variant == "product_key"
            else None,
            "product_key_training_candidate_sums_histogram": {
                "64": train_tokens - train_fallbacks,
                "4096": train_fallbacks,
            }
            if variant == "product_key"
            else None,
        },
    )


def launch(config: Path, source: Path, output: Path, requested: list[str]) -> tuple[Path, bool]:
    run, ok = supervise(
        output,
        "pilot_suite",
        [],
        requested_argv=requested,
        process_seconds=SUITE_SECONDS,
        worker_argv=lambda run: [
            sys.executable,
            "-m",
            "arborlm.pilot",
            "suite",
            str(run),
            str(config),
            str(source),
        ],
        run_prefix="P1",
        manifest_fields=_fields(),
        nested_workers=True,
    )
    if not ok and not (run / "result.json").exists():
        terminal = read_json(run / "terminal.json")
        write_json(run / "result.json", _summary(run, terminal["reason"]))
    return run, ok


def main() -> None:
    # Workers must be launched by the watchdog, which creates the running record.
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("suite", "cell"))
    parser.add_argument("run", type=Path)
    parser.add_argument("arguments", nargs="+")
    args = parser.parse_args()
    if not (args.run / "manifest.json").is_file():
        raise ValueError("missing supervising watchdog run record")
    if args.operation == "suite":
        _suite(args.run, *map(Path, args.arguments))
    else:
        suite, variant, seed, expected = args.arguments
        _cell(args.run, Path(suite), variant, int(seed), expected)


if __name__ == "__main__":
    main()
