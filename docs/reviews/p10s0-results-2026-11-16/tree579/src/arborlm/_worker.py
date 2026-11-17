"""Internal worker: execute an E0 operation under the parent watchdog."""

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

from .config import config_hash, load_config, validate_config
from .io import file_sha256, read_json, write_json
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import supervise

ABSENT = {
    "flops": "no approved FLOP estimator for E0",
    "prefill_decode_ttft": "E0 only trains/evaluates fixed-length targets",
    "accelerator_memory": "CPU-only run",
    "physical_nvme": "not applicable to resident E0",
    "routing": "not applicable to dense E0",
}


def _update(run: Path, **values: Any) -> None:
    current = read_json(run / "manifest.json")
    current.update(values)
    write_json(run / "manifest.json", current)


def _prepare(run: Path, config: dict[str, Any]) -> None:
    write_json(run / "config.resolved.json", config)
    source = record_source(run, Path.cwd())
    environment = record_environment(run)
    _update(
        run,
        code_commit=source["code_commit"],
        dirty=source["dirty"],
        source_sha256=source["archive"]["sha256"],
        lock_sha256=source["lock_sha256"],
        spec_sha256=source["spec_sha256"],
        environment=environment,
        config_sha256=config_hash(config),
        seeds={"torch": 42, "python": 42, "train_data": 101, "validation_data": 202},
        metrics_not_measured=ABSENT,
    )
    runtime_supported()


def _link(run: Path, checkpoint: Path) -> Path:
    parent = checkpoint.parent
    _update(
        run, parent_run_id=parent.name, parent_run_directory=str(parent), checkpoint=str(checkpoint)
    )
    return parent


def _run_model(args: argparse.Namespace, run: Path) -> None:
    parent: Path | None = None
    checkpoint = args.checkpoint if args.operation == "eval" else args.resume
    if checkpoint is not None:
        parent = _link(run, checkpoint)
    config = (
        validate_config(read_json(checkpoint.parent / "config.resolved.json"))
        if args.operation == "eval"
        else load_config(args.config)
    )
    _prepare(run, config)

    from .checkpoint import read_checkpoint, restore_checkpoint, save_checkpoint
    from .data import generate_dataset
    from .engine import (
        BATCH_SIZE,
        CHECKPOINT_STEPS,
        CONTEXT,
        STEPS,
        configure_cpu,
        evaluate,
        optimizer_for,
        train_step,
    )
    from .model import PARAMETERS, DenseBaseline, active_parameters

    data = generate_dataset()
    data.record(run)
    checksums = data.checksums()
    if parent is not None:
        data.record(parent, verify_existing=True)
        if config_hash(validate_config(read_json(parent / "config.resolved.json"))) != config_hash(
            config
        ):
            raise ValueError("parent run config mismatch")
    identity = {"config_sha256": config_hash(config), "dataset_checksums_sha256": checksums}
    _update(run, dataset_checksums_sha256=checksums)

    configure_cpu()
    model = DenseBaseline()
    optimizer = optimizer_for(model)
    total = sum(param.numel() for param in model.parameters())
    trainable = sum(param.numel() for param in model.parameters() if param.requires_grad)
    if total != PARAMETERS or trainable != PARAMETERS:
        raise AssertionError(f"parameter count differs from approved model: {total}/{trainable}")
    _update(
        run,
        model={
            "kind": "dense_baseline",
            "parameters_total": total,
            "parameters_trainable": trainable,
            "parameters_active_per_example_estimate": active_parameters(CONTEXT),
            "active_parameter_method": "unique weights participating in a single forward; all "
            "tied token embedding/output weights and only the position rows in context",
        },
    )
    step = cursor = tokens = 0
    if checkpoint is not None:
        state = read_checkpoint(checkpoint, model, optimizer, identity)
        step, cursor, tokens = restore_checkpoint(state, model, optimizer)
        _update(run, parent_checkpoint_sha256=file_sha256(checkpoint / "state.pt"))

    def record_eval() -> dict[str, Any]:
        measurements = evaluate(model, data.validation)
        append_event(
            run,
            {
                "event": "evaluation",
                "completed_step": step,
                "nll_unit": "nats_per_target_token",
                **measurements,
            },
        )
        return measurements

    final_eval: dict[str, Any] | None
    if args.operation == "eval":
        if step != STEPS:
            raise ValueError("E0 eval requires a final step-32 checkpoint")
        final_eval = record_eval()
        result = {
            "outcome": "completed",
            "steps_this_process": 0,
            "train_tokens_this_process": 0,
            "completed_step": step,
            "train_tokens_cumulative": tokens,
            "next_row": cursor,
            "evaluation": {"final": final_eval},
            "evaluation_tokens_this_process": final_eval["tokens"],
        }
    else:
        if step not in (0, CHECKPOINT_STEPS[0]) or (args.stop_after is not None and step != 0):
            raise ValueError("E0 resume requires the step-16 checkpoint; stop-after is fresh only")
        target = args.stop_after or STEPS
        initial_eval = record_eval() if step == 0 else None
        checkpoints: dict[str, str] = {}
        start_step, start_tokens = step, tokens
        start = time.monotonic()
        while step < target:
            rows = [data.train[(cursor + offset) % len(data.train)] for offset in range(BATCH_SIZE)]
            loss, grad = train_step(model, optimizer, rows)
            step += 1
            cursor = (cursor + BATCH_SIZE) % len(data.train)
            tokens += BATCH_SIZE * CONTEXT
            append_event(
                run,
                {
                    "event": "train_step",
                    "completed_step": step,
                    "pre_update_loss": loss,
                    "loss_unit": "nats_per_target_token",
                    "pre_clip_gradient_norm": grad,
                    "target_tokens_cumulative": tokens,
                    "next_row": cursor,
                },
            )
            if step in CHECKPOINT_STEPS:
                name = f"checkpoint-{step:02d}"
                checkpoints[name] = save_checkpoint(run / name, model, optimizer, step, identity)
        elapsed = time.monotonic() - start
        final_eval = record_eval() if step == STEPS else None
        result = {
            "outcome": "completed" if step == STEPS else "registered_stop",
            "completed_step": step,
            "next_row": cursor,
            "steps_this_process": step - start_step,
            "train_tokens_this_process": tokens - start_tokens,
            "train_tokens_cumulative": tokens,
            "train_loop_seconds": elapsed,
            "train_target_tokens_per_second": (tokens - start_tokens) / elapsed,
            "train_loop_method": "monotonic clock, including logs and checkpoint writes",
            "evaluation": {"initial": initial_eval, "final": final_eval},
            "evaluation_tokens_this_process": sum(
                entry["tokens"] for entry in (initial_eval, final_eval) if entry is not None
            ),
            "checkpoint_state_sha256": checkpoints,
        }
    write_json(run / "result.json", result)


def _bitwise_equal(left: Any, right: Any) -> bool:
    import torch

    if type(left) is not type(right):
        return False
    if isinstance(left, torch.Tensor):
        return bool(
            left.shape == right.shape
            and left.dtype == right.dtype
            and left.device == right.device
            and torch.equal(
                left.contiguous().reshape(-1).view(torch.uint8),
                right.contiguous().reshape(-1).view(torch.uint8),
            )
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _bitwise_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list | tuple):
        return len(left) == len(right) and all(
            _bitwise_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float):
        return struct.pack("!d", left) == struct.pack("!d", right)
    return bool(left == right)


def _losses(run: Path) -> list[tuple[int, float]]:
    events = [json.loads(line) for line in (run / "metrics.jsonl").read_text().splitlines()]
    return [
        (event["completed_step"], event["pre_update_loss"])
        for event in events
        if event["event"] == "train_step"
    ]


def _final_state(run: Path, config: dict[str, Any]) -> dict[str, Any]:
    from .checkpoint import read_checkpoint
    from .data import generate_dataset
    from .engine import optimizer_for
    from .model import DenseBaseline

    model = DenseBaseline()
    return read_checkpoint(
        run / "checkpoint-32",
        model,
        optimizer_for(model),
        {
            "config_sha256": config_hash(config),
            "dataset_checksums_sha256": generate_dataset().checksums(),
        },
    )


def _child_records_valid(children: tuple[Path, ...]) -> bool:
    artifact_names = {
        "config.resolved.json",
        "manifest.json",
        "train.json",
        "validation.json",
        "tokenizer.json",
        "generator.json",
        "dataset_manifest.json",
        "metrics.jsonl",
        "stdout.log",
        "stderr.log",
        "source.json",
        "source.diff",
        "source.tar",
        "environment.json",
        "result.json",
        "terminal.json",
    }
    metadata_names = {
        "schema_version",
        "run_id",
        "operation",
        "experiment_family",
        "question_id",
        "authorized_spec_reference",
        "authorized_result_review",
        "astra_spec_review",
        "astra_result_review",
        "human_merge_approval",
        "human_publication_approval",
        "argv",
        "requested_argv",
        "cwd",
        "limits",
        "environment",
        "code_commit",
        "dirty",
        "source_sha256",
        "lock_sha256",
        "seeds",
        "model",
        "dataset_checksums_sha256",
        "created_utc",
        "finished_utc",
        "status",
    }
    if len(set(children)) != 5:
        return False
    for child in children:
        if any(not (child / name).is_file() for name in artifact_names):
            return False
        record = read_json(child / "manifest.json")
        if not metadata_names <= record.keys() or record["run_id"] != child.name:
            return False
        source = read_json(child / "source.json")
        for item in ("archive", "patch"):
            if file_sha256(child / source[item]["file"]) != source[item]["sha256"]:
                return False
    a, b, reload, stop, resume = children
    return (
        all(
            read_json(child / "terminal.json")["status"] == "completed"
            for child in (a, b, reload, resume)
        )
        and read_json(stop / "terminal.json")["status"] == "interrupted"
        and read_json(resume / "manifest.json")["parent_run_id"] == stop.name
        and read_json(reload / "manifest.json")["parent_run_id"] == a.name
    )


def _run_smoke(run: Path, path: Path) -> None:
    config = load_config(path)
    _prepare(run, config)
    children: dict[str, str] = {}

    def launch(name: str, operation: str, *argv: str) -> Path:
        child, ok = supervise(run / "children", operation, list(argv), requested_argv=sys.argv)
        children[name] = child.name
        _update(run, children=children)
        append_event(
            run, {"event": "child_finished", "name": name, "child_run_id": child.name, "ok": ok}
        )
        if not ok:
            raise RuntimeError(f"{name} failed; see {child / 'terminal.json'}")
        return child

    a = launch("fresh_a", "train", "--config", str(path))
    b = launch("fresh_b", "train", "--config", str(path))
    reloaded = launch("reload", "eval", "--checkpoint", str(a / "checkpoint-32"))
    stopped = launch("registered_stop", "train", "--config", str(path), "--stop-after", "16")
    resumed = launch(
        "resume", "train", "--config", str(path), "--resume", str(stopped / "checkpoint-16")
    )

    from .data import generate_dataset
    from .engine import configure_cpu

    configure_cpu()
    generate_dataset().record(run)
    loss_a, loss_b, loss_stop, loss_resume = map(_losses, (a, b, stopped, resumed))
    final_a, final_b, final_resume = (_final_state(child, config) for child in (a, b, resumed))
    results = [read_json(child / "result.json") for child in (a, b, reloaded, stopped, resumed)]
    eval_a, eval_b, eval_reloaded, _, eval_resume = (entry["evaluation"] for entry in results)
    gates = {
        "run_records": _child_records_valid((a, b, reloaded, stopped, resumed)),
        "fresh_repeat_steps": [step for step, _ in loss_a] == list(range(1, 33)),
        "fresh_repeat_losses": _bitwise_equal(loss_a, loss_b),
        "fresh_repeat_model": _bitwise_equal(final_a["model"], final_b["model"]),
        "fresh_repeat_optimizer": _bitwise_equal(final_a["optimizer"], final_b["optimizer"]),
        "fresh_repeat_eval_nll": _bitwise_equal(eval_a["final"]["nll"], eval_b["final"]["nll"]),
        "reload_eval_nll": _bitwise_equal(eval_a["final"]["nll"], eval_reloaded["final"]["nll"]),
        "resume_prefix_losses": _bitwise_equal(loss_a[:16], loss_stop),
        "resume_suffix_losses": _bitwise_equal(loss_a[16:], loss_resume),
        "resume_final_model_optimizer_rng_counters": _bitwise_equal(final_a, final_resume),
        "resume_eval_nll": _bitwise_equal(eval_a["final"]["nll"], eval_resume["final"]["nll"]),
    }
    for name, passed in gates.items():
        append_event(run, {"event": "gate", "gate": name, "passed": passed})
    passed = all(gates.values())
    write_json(
        run / "result.json",
        {
            "outcome": "completed" if passed else "failed",
            "gates": gates,
            "children": children,
            "fresh_a_evaluation": eval_a,
            "reference_equivalence": "bitwise comparison in this numerical environment only",
        },
    )
    if not passed:
        raise RuntimeError("one or more registered E0 equivalence checks failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("train", "eval", "smoke"))
    parser.add_argument("run", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--stop-after", type=int, choices=(16,))
    args = parser.parse_args()
    if args.operation == "smoke":
        _run_smoke(args.run, args.config)
    else:
        _run_model(args, args.run)


if __name__ == "__main__":
    main()
