"""P8 training worker, 60-cell stage driver, gates and rehearsal (ADR-0015 sections 4, 10, 11).

``python -m arborlm.p8_train <subcommand>``: ``cell`` (one cell), ``stage`` (all 60, supervised),
``restore-check``, ``p5-invariance``, ``rehearsal``. Training rows only: no validation or evaluation
data is opened by any subcommand. Run directories are created under ``--experiments-root`` and never
delete or modify anything that exists there.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import json
import os
import random
import resource
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
import torch

from . import p8_core as core
from .io import canonical_json, file_sha256, read_json, sha256, write_json
from .p8_core import Cell

DRY_PREFIX_SUFFIX = "D"


# --- environment ---------------------------------------------------------------------------------
def configure() -> None:
    """P5's deterministic single-thread CPU configuration (idempotent in one process)."""
    from .engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:  # the inter-op thread count can be set only once per process
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


def peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def utc_now() -> str:
    from .records import utc_now as now

    return now()


# --- freeze binding ------------------------------------------------------------------------------
class FreezeError(ValueError):
    """The working tree does not equal the freeze commit: the stage does not start."""


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(core.repo_root()), *args])


def verify_freeze(commit: str) -> dict[str, Any]:
    """The hashes of every ``src/arborlm`` file, the config and the spec at ``commit`` equal the
    working tree's (so no source, config or spec edit exists since the freeze)."""
    try:
        full = _git("rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    except subprocess.CalledProcessError as exc:
        raise FreezeError(f"freeze commit {commit!r} does not exist") from exc
    listed = _git("ls-tree", "-r", "--name-only", full, "--", "src/arborlm").decode().split("\n")
    frozen = {
        name: sha256(_git("show", f"{full}:{name}"))
        for name in sorted(n for n in listed if n.endswith(".py"))
    }
    current = core.source_hashes()
    problems = []
    if frozen != current:
        problems.append(
            "src/arborlm differs: "
            + ", ".join(
                sorted(k for k in frozen.keys() | current.keys() if frozen.get(k) != current.get(k))
            )
        )
    for name in (str(core.DEFAULT_CONFIG), core.SPEC, "uv.lock", "pyproject.toml"):
        try:
            committed = sha256(_git("show", f"{full}:{name}"))
        except subprocess.CalledProcessError:
            problems.append(f"{name} is missing at the freeze commit")
            continue
        path = core.repo_root() / name
        if not path.is_file() or committed != file_sha256(path):
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise FreezeError("; ".join(problems))
    return {
        "freeze_commit": full,
        "head": _git("rev-parse", "HEAD").decode().strip(),
        "source_files": len(current),
        **core.code_identity(),
    }


# --- training core (shared by the worker, restore-check and the gates) ----------------------------
def _gate_value(model: Any) -> float | None:
    return float(model.addition.gate.detach()) if model.addition is not None else None


def advance(
    model: Any,
    optimizer: Any,
    rows: torch.Tensor,
    cell: Any,
    objective: tuple[str, ...],
    first: int,
    last: int,
    *,
    tracker: Any = None,
    on_step: Callable[[dict[str, Any]], None] | None = None,
    on_checkpoint: Callable[[int], None] | None = None,
) -> list[dict[str, Any]]:
    """Updates ``first..last`` (1-based, inclusive) exactly as P5: batch ``rows[o:o+8]`` with
    ``o = ((step - 1) * 8) mod 2048``."""
    from .p8_objective import train_step_p8

    records = []
    for step in range(first, last + 1):
        offset = core.batch_offset(step)
        batch = rows[offset : offset + core.BATCH]
        record = train_step_p8(
            model,
            optimizer,
            batch,
            step,
            objective,
            tracker=tracker,
            reach=step in core.REACH_UPDATES,
        )
        record["order_offset_for_update"] = offset
        record["gate"] = _gate_value(model)
        if on_step is not None:
            on_step(record)
        records.append(record)
        if on_checkpoint is not None and step in core.CHECKPOINT_STEPS:
            on_checkpoint(step)
    return records


def summarize(records: list[dict[str, Any]], objective: tuple[str, ...]) -> dict[str, Any]:
    def stats(values: list[float]) -> dict[str, float | int | None]:
        return {
            "count": len(values),
            "mean": sum(values) / len(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    out: dict[str, Any] = {
        "updates": len(records),
        "loss_first": records[0]["loss"] if records else None,
        "loss_last": records[-1]["loss"] if records else None,
        "pre_clip_gradient_norm": stats([r["pre_clip_gradient_norm"] for r in records]),
        "clipped_updates": sum(1 for r in records if r["clipped"]),
        "router_nonzero_gradient_updates": sum(
            1 for r in records if (r["router_gradient_norm"] or 0.0) > 0
        ),
    }
    if objective:
        out["lambda"] = {
            name: {
                **stats([r["lam"][name] for r in records]),
                "zero_events": sum(1 for r in records if r["lambda_zero_event"][name]),
            }
            for name in objective
        }
        out["g_l_theta_norm"] = stats([r["g_l_theta_norm"] for r in records])
        out["g_r_norm"] = {
            name: stats([r["g_r_norm"][name] for r in records]) for name in objective
        }
        out["regularizer_first_last"] = {
            name: [records[0]["regularizer"][name], records[-1]["regularizer"][name]]
            for name in objective
        }
    out["param_change_l2"] = {
        key: stats([r["param_change_l2"][key] for r in records]) for key in ("theta_r", "other")
    }
    out["reach"] = [
        {
            k: v
            for k, v in r.items()
            if k.startswith("reach_")
            or k in ("cumulative_hard_selected_slots", "diagnostics", "lam", "regularizer")
        }
        | {"step": r["step"]}
        for r in records
        if r["step"] in core.REACH_UPDATES
    ]
    return out


class StepLog:
    """Append-only per-update JSONL log (flushed every update, fsynced at close)."""

    def __init__(self, path: Path, dry_run: bool) -> None:
        self.stream = path.open("xb")
        self.dry_run = dry_run

    def __call__(self, record: dict[str, Any]) -> None:
        self.stream.write(canonical_json({**record, "dry_run": self.dry_run}))
        self.stream.flush()

    def close(self) -> None:
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def load_inputs(
    cell: Any, experiments_root: Path, dry_run: bool
) -> tuple[Any, dict[str, Any], torch.Tensor, dict[str, str]]:
    """Backbone, provenance, parent-ordered training rows and data hashes."""
    if dry_run:
        backbone = core.synthetic_backbone(cell)
        provenance: dict[str, Any] = {"synthetic": True}
        train, order, hashes = core.synthetic_training(cell)
    else:
        backbone, provenance = core.load_backbone(cell, experiments_root)
        train, order, hashes = core.load_training(cell, experiments_root)
    return backbone, provenance, core.ordered_rows(train, order), hashes


def monitor_batch(rows: torch.Tensor) -> torch.Tensor:
    return rows[core.batch_offset(1) : core.batch_offset(1) + core.BATCH]


def train_cell(
    cell: Cell, run_dir: Path, experiments_root: Path, *, dry_run: bool, data_dir: Path | None
) -> dict[str, Any]:
    """Train one registered cell for 512 updates, checkpointing at 0, 256 and 512."""
    from . import p8_checkpoint as ckpt
    from .p4_model import backbone_digest
    from .p5_model import optimizer_for, optimizer_names, state_digest
    from .p8_objective import ReachTracker, proxy_values
    from .pilot_model import Memory

    started = time.monotonic()
    configure()
    folder = run_dir / "cells" / cell.label
    folder.mkdir(parents=True, exist_ok=False)
    identity_before = core.code_identity()
    backbone, provenance, rows, hashes = load_inputs(cell, experiments_root, dry_run)
    model = core.build_model(cell, backbone)
    frozen_before = backbone_digest(model.backbone)
    optimizer = optimizer_for(model)
    names = optimizer_names(model, optimizer)
    objective = cell.objective
    identity = {
        **identity_before,
        "cell": cell.fields(),
        "case": cell.case,
        "objective": list(objective),
        "backbone_sha256": frozen_before,
        "order_sha256": hashes.get("order_sha256"),
        "dataset_manifest_sha256": hashes.get("dataset_manifest_sha256"),
        "parent_state_sha256": provenance.get("parent", {}).get("checkpoint_state_sha256"),
        "dry_run": dry_run,
    }
    memory = model.addition
    assert isinstance(memory, Memory)
    gate_initial = float(memory.gate.detach())
    keys_initial = memory.keys.detach().clone()
    router_initial = memory.router.detach().clone() if cell.variant == core.LEARNED else None
    fixed_router = memory.router.detach().clone() if cell.variant == core.FIXED else None

    def frozen_check() -> None:
        if backbone_digest(model.backbone) != frozen_before:
            raise ValueError("P8 frozen backbone or mask changed")
        if fixed_router is not None and not torch.equal(fixed_router, memory.router):
            raise ValueError("P8 fixed router buffer changed")
        optimizer_names(model, optimizer)

    frozen_check()
    digests: dict[str, str] = {}
    files: dict[str, str] = {}
    monitor = monitor_batch(rows)
    proxy: dict[str, dict[str, float]] = {}

    def checkpoint(step: int) -> None:
        frozen_check()
        path = ckpt.step_path(folder, step)
        files[f"step-{step:04d}"] = ckpt.save(path, model, optimizer, step, identity)
        digests[f"step-{step:04d}"] = state_digest(model)
        proxy[str(step)] = proxy_values(model, monitor)

    checkpoint(0)
    tracker = ReachTracker()
    log = StepLog(folder / "steps.jsonl", dry_run)
    train_start = time.monotonic()
    try:
        records = advance(
            model,
            optimizer,
            rows,
            cell,
            objective,
            1,
            core.STEPS,
            tracker=tracker,
            on_step=log,
            on_checkpoint=checkpoint,
        )
    finally:
        log.close()
    train_seconds = time.monotonic() - train_start
    frozen_after = backbone_digest(model.backbone)
    if frozen_after != frozen_before:
        raise ValueError("P8 backbone digest changed during training")
    identity_after = core.code_identity()
    if identity_after != identity_before:
        raise ValueError("P8 source, spec or config changed during the cell")
    if not all(bool(p.isfinite().all()) for p in model.parameters()):
        raise ValueError("P8 non-finite parameter after training")
    record = {
        "schema": "P8-cell-v1",
        "study": core.STUDY,
        "dry_run": dry_run,
        "status": "completed",
        "cell": cell.fields(),
        "label": cell.label,
        "index": cell.index,
        "case": cell.case,
        "variant": cell.variant,
        "objective": list(objective),
        "baseline_case": core.CASE_BASELINE.get(cell.case),
        "steps": core.STEPS,
        "batch": core.BATCH,
        "constants": {
            "beta": core.BETA,
            "alpha": core.ALPHA,
            "group": core.GROUP,
            "window": core.WINDOW,
        },
        "seeds": {"init": cell.seed, "python_and_torch": cell.seed},
        "optimizer_parameter_names": names,
        "parameters_trainable": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "backbone_sha256_before": frozen_before,
        "backbone_sha256_after": frozen_after,
        "state_digests": digests,
        "checkpoint_file_sha256": files,
        "checkpoint_files": {k: f"cells/{cell.label}/{k}.pt" for k in files},
        "identity": identity,
        "provenance": provenance,
        "data": hashes,
        "summary": summarize(records, objective),
        "proxy_monitor_batch_offset": core.batch_offset(1),
        "proxy_values": proxy,
        "gate": {"initial": gate_initial, "final": float(memory.gate.detach())},
        "key_movement_l2": float(torch.linalg.vector_norm(memory.keys.detach() - keys_initial)),
        "router_movement_l2": (
            None
            if router_initial is None
            else float(torch.linalg.vector_norm(memory.router.detach() - router_initial))
        ),
        "training_seconds": train_seconds,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_bytes": peak_rss_bytes(),
        "extra_backward_passes_per_update": len(objective),
        "data_dir_argument": None if data_dir is None else str(data_dir),
        "utc_end": utc_now(),
    }
    write_json(folder / "train.json", record)
    return record


# --- stage driver --------------------------------------------------------------------------------
@dataclass
class Running:
    cell: Cell
    process: subprocess.Popen[bytes]
    started: float
    peak_rss: int = 0


@dataclass
class StageSettings:
    workers: int = core.WORKERS
    cell_cap: float = core.TRAIN_CELL_CAP
    stage_cap: float = core.TRAIN_STAGE_CAP
    rss_worker: int = core.RSS_WORKER
    rss_aggregate: int = core.RSS_AGGREGATE
    poll: float = 0.2
    continue_after_failure: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    # tests only: replaces the real worker command (label, run directory) -> argv
    worker_command: Callable[[str, Path], list[str]] | None = None


def _tree_rss(process: psutil.Process) -> int:
    total = 0
    try:
        procs = [process, *process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0
    for proc in procs:
        try:
            total += int(proc.memory_info().rss)
        except psutil.NoSuchProcess:
            continue
    return total


def _kill(process: subprocess.Popen[bytes]) -> None:
    try:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    process.wait()


def run_stage(
    run: Path,
    labels: list[str],
    experiments_root: Path,
    data_dir: Path,
    *,
    dry_run: bool,
    settings: StageSettings,
    header: dict[str, Any],
) -> dict[str, Any]:
    """Run the cells as supervised subprocesses (up to ``settings.workers`` at once). A failed or
    killed cell is recorded as failed; no cell is rerun or silently skipped. After the first failure
    (or a stage-cap or aggregate-RSS breach) no new cell is launched unless
    ``continue_after_failure``; unlaunched cells are recorded as ``unexecuted``. The stage is
    ``completed`` only if all given cells completed."""
    (run / "cells").mkdir(exist_ok=True)
    rows: dict[str, dict[str, Any]] = {
        label: {
            "label": label,
            "index": core.parse_label(label).index,
            "status": "unexecuted",
            "dry_run": dry_run,
        }
        for label in labels
    }
    manifest: dict[str, Any] = {
        **header,
        "dry_run": dry_run,
        "settings": {
            "workers": settings.workers,
            "cell_cap_seconds": settings.cell_cap,
            "stage_cap_seconds": settings.stage_cap,
            "rss_worker_bytes": settings.rss_worker,
            "rss_aggregate_bytes": settings.rss_aggregate,
            "continue_after_failure": settings.continue_after_failure,
            **settings.extra,
        },
        "cells": list(rows.values()),
        "status": "running",
        "reason": None,
        "peak_aggregate_rss_bytes": 0,
    }

    def persist() -> None:
        manifest["cells"] = [rows[label] for label in labels]
        write_json(run / "manifest.json", manifest)

    persist()
    pending = list(labels)
    running: list[Running] = []
    stage_start = time.monotonic()
    stop_reason: str | None = None
    failed = False
    while True:
        elapsed = time.monotonic() - stage_start
        if stop_reason is None and elapsed > settings.stage_cap:
            stop_reason = f"stage cap of {settings.stage_cap:.0f} s exceeded"
        while (
            stop_reason is None
            and (not failed or settings.continue_after_failure)
            and pending
            and len(running) < settings.workers
        ):
            label = pending.pop(0)
            cell = core.parse_label(label)
            folder = run / "supervision"
            folder.mkdir(exist_ok=True)
            out = (folder / f"{label}.stdout.log").open("xb")
            err = (folder / f"{label}.stderr.log").open("xb")
            argv = (
                settings.worker_command(label, run)
                if settings.worker_command is not None
                else [
                    sys.executable,
                    "-m",
                    "arborlm.p8_train",
                    "cell",
                    "--experiments-root",
                    str(experiments_root),
                    "--data-dir",
                    str(data_dir),
                    "--run-dir",
                    str(run),
                    "--label",
                    label,
                    *(["--dry-run"] if dry_run else []),
                ]
            )
            process = subprocess.Popen(
                argv,
                cwd=core.repo_root(),
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
            out.close()
            err.close()
            running.append(Running(cell, process, time.monotonic()))
            rows[label].update(status="running", pid=process.pid, argv=argv)
            persist()
        aggregate = 0
        for item in list(running):
            label = item.cell.label
            try:
                rss = _tree_rss(psutil.Process(item.process.pid))
            except psutil.NoSuchProcess:
                rss = 0
            item.peak_rss = max(item.peak_rss, rss)
            aggregate += rss
            code = item.process.poll()
            reason: str | None = None
            if code is None:
                if rss > settings.rss_worker:
                    reason = f"worker RSS {rss} exceeded {settings.rss_worker}"
                elif time.monotonic() - item.started > settings.cell_cap:
                    reason = f"cell cap of {settings.cell_cap:.0f} s exceeded"
                if reason is not None:
                    _kill(item.process)
            else:
                if code != 0:
                    reason = f"worker exited with code {code}"
            if code is None and reason is None:
                continue
            wall = time.monotonic() - item.started
            running.remove(item)
            record_path = run / "cells" / label / "train.json"
            row = rows[label]
            row.update(
                wall_seconds=wall,
                supervisor_peak_rss_bytes=item.peak_rss,
                exit_code=item.process.returncode,
            )
            if reason is None and record_path.is_file():
                done = read_json(record_path)
                row.update(
                    status="completed",
                    state_digests=done["state_digests"],
                    backbone_sha256_before=done["backbone_sha256_before"],
                    backbone_sha256_after=done["backbone_sha256_after"],
                    checkpoint_file_sha256=done["checkpoint_file_sha256"],
                    identity_source_sha256=done["identity"]["source_sha256"],
                    training_seconds=done["training_seconds"],
                    worker_peak_rss_bytes=done["peak_rss_bytes"],
                    train_json_sha256=file_sha256(record_path),
                )
                if (
                    done["backbone_sha256_before"] != done["backbone_sha256_after"]
                    or done["identity"]["source_sha256"] != header["code_identity"]["source_sha256"]
                ):
                    row.update(status="failed", reason="backbone or source identity mismatch")
                    failed = True
            else:
                row.update(status="failed", reason=reason or "no train.json written")
                failed = True
            persist()
        manifest["peak_aggregate_rss_bytes"] = max(manifest["peak_aggregate_rss_bytes"], aggregate)
        if aggregate > settings.rss_aggregate and stop_reason is None:
            stop_reason = f"aggregate RSS {aggregate} exceeded {settings.rss_aggregate}"
            for item in list(running):
                _kill(item.process)
                rows[item.cell.label].update(
                    status="failed",
                    reason="killed: aggregate RSS limit",
                    wall_seconds=time.monotonic() - item.started,
                    supervisor_peak_rss_bytes=item.peak_rss,
                )
                running.remove(item)
                failed = True
            persist()
        if stop_reason is not None and running and stop_reason.startswith("stage cap"):
            for item in list(running):
                _kill(item.process)
                rows[item.cell.label].update(
                    status="failed",
                    reason="killed: stage cap",
                    wall_seconds=time.monotonic() - item.started,
                    supervisor_peak_rss_bytes=item.peak_rss,
                )
                running.remove(item)
                failed = True
            persist()
        can_launch = stop_reason is None and (not failed or settings.continue_after_failure)
        if not running and (not pending or not can_launch):
            break
        time.sleep(settings.poll)
    statuses = [rows[label]["status"] for label in labels]
    manifest["status"] = "completed" if all(s == "completed" for s in statuses) else "INCOMPLETE"
    manifest["reason"] = stop_reason or (
        None if manifest["status"] == "completed" else "a cell failed or was not executed"
    )
    manifest["counts"] = {
        s: statuses.count(s) for s in ("completed", "failed", "unexecuted", "running")
    }
    manifest["denominator"] = len(labels)
    manifest["stage_wall_seconds"] = time.monotonic() - stage_start
    manifest["utc_end"] = utc_now()
    persist()
    return manifest


def stage_header(kind: str, dry_run: bool, freeze: dict[str, Any] | None) -> dict[str, Any]:
    env = core.environment_record()
    return {
        "schema": "P8-train-stage-v1",
        "study": core.STUDY,
        "kind": kind,
        "spec_reference": core.SPEC,
        "astra_review": "NOT_PERFORMED",
        "freeze": freeze,
        "code_identity": core.code_identity(),
        "source_files_sha256": core.source_hashes(),
        "constants": {
            "beta": core.BETA,
            "alpha": core.ALPHA,
            "group": core.GROUP,
            "window": core.WINDOW,
        },
        "utc_start": utc_now(),
        "argv": sys.argv,
        "environment": {k: v for k, v in env.items() if k != "packages"}
        | {"packages": {k: v for k, v in env["packages"].items() if k in ("torch", "psutil")}},
        "dry_run": dry_run,
    }


def _new_run(root: Path, prefix: str, dry_run: bool) -> Path:
    from .records import allocate_run

    return allocate_run(root, prefix=prefix + (DRY_PREFIX_SUFFIX if dry_run else ""))


def cmd_cell(args: argparse.Namespace) -> int:
    cell = core.parse_label(args.label)
    record = train_cell(
        cell,
        Path(args.run_dir),
        Path(args.experiments_root),
        dry_run=args.dry_run,
        data_dir=Path(args.data_dir),
    )
    print(json.dumps({"label": cell.label, "status": record["status"]}))
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    if args.continue_after_failure and not args.dry_run:
        print("refused: --continue-after-failure is allowed only with --dry-run", file=sys.stderr)
        return 2
    freeze = None
    if not args.dry_run:
        if not args.freeze_commit:
            print("refused: --freeze-commit is required for a registered stage", file=sys.stderr)
            return 2
        freeze = verify_freeze(args.freeze_commit)
    labels = core.all_labels()
    if args.labels:
        if not args.dry_run:
            print("refused: --labels is allowed only with --dry-run", file=sys.stderr)
            return 2
        labels = args.labels.split(",")
    root = Path(args.experiments_root)
    run = _new_run(root, core.STAGE_PREFIX, args.dry_run)
    settings = StageSettings(
        workers=args.workers, continue_after_failure=args.continue_after_failure
    )
    if not args.dry_run and (args.workers > core.WORKERS):
        print("refused: more than four workers", file=sys.stderr)
        return 2
    manifest = run_stage(
        run,
        labels,
        root,
        Path(args.data_dir),
        dry_run=args.dry_run,
        settings=settings,
        header={**stage_header("train", args.dry_run, freeze), "run_id": run.name},
    )
    print(json.dumps({"run": str(run), "status": manifest["status"], "counts": manifest["counts"]}))
    return 0 if manifest["status"] == "completed" else 1


# --- gates ---------------------------------------------------------------------------------------
def restore_check(label: str, run: Path, experiments_root: Path) -> dict[str, Any]:
    """ADR section 10.5 for one cell: restore the mid checkpoint (with optimizer state), train to
    the final step and compare state digests. Reads the stage's files; modifies nothing."""
    from . import p8_checkpoint as ckpt
    from .p5_model import state_digest

    configure()
    started = time.monotonic()
    mid, final_step = core.CHECKPOINT_STEPS[1], core.CHECKPOINT_STEPS[2]
    cell = core.parse_label(label)
    folder = run / "cells" / cell.label
    done = read_json(folder / "train.json")
    dry_run = bool(done["dry_run"])
    backbone, _, rows, _ = load_inputs(cell, experiments_root, dry_run)
    model, optimizer, meta = ckpt.restore(
        ckpt.step_path(folder, mid),
        cell,
        backbone,
        expected_sha256=done["checkpoint_file_sha256"][f"step-{mid:04d}"],
    )
    assert optimizer is not None
    if meta["step"] != mid:
        raise ValueError("not the mid-training checkpoint")
    advance(model, optimizer, rows, cell, cell.objective, mid + 1, final_step)
    final = state_digest(model)
    recorded = done["state_digests"][f"step-{final_step:04d}"]
    reference = ckpt.restore(
        ckpt.step_path(folder, final_step),
        cell,
        backbone,
        expected_sha256=done["checkpoint_file_sha256"][f"step-{final_step:04d}"],
    )[2]["state_digest"]
    return {
        "schema": "P8-restore-check-v1",
        "dry_run": dry_run,
        "label": cell.label,
        "restored_from": f"step-{mid:04d}.pt",
        "restored_step_digest": meta["state_digest"],
        "restored_run_final_digest": final,
        "recorded_final_digest": recorded,
        "checkpoint_final_digest": reference,
        "seconds": time.monotonic() - started,
        "passed": final == recorded == reference,
    }


def cmd_restore_check(args: argparse.Namespace) -> int:
    result = restore_check(args.label, Path(args.run_dir), Path(args.experiments_root))
    out = _new_run(Path(args.experiments_root), core.RESTORE_PREFIX, result["dry_run"])
    write_json(out / "result.json", result)
    print(json.dumps({**result, "run": str(out)}))
    return 0 if result["passed"] else 1


def cmd_restore_worker(args: argparse.Namespace) -> int:
    result = restore_check(args.label, Path(args.run_dir), Path(args.experiments_root))
    write_json(Path(args.out), result)
    return 0 if result["passed"] else 1


RESTORE_GATE_LABELS = [f"b101-o301-s601-{case}" for case in core.CASES]


def supervise_commands(
    commands: dict[str, list[str]], logs: Path, settings: StageSettings
) -> dict[str, dict[str, Any]]:
    """Run each command as a supervised subprocess (workers at once, per-worker RSS and wall caps,
    aggregate RSS cap, stage cap). Returns per-label status, reason, seconds and peak RSS."""
    logs.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict[str, Any]] = {
        label: {"status": "unexecuted", "reason": None} for label in commands
    }
    pending = list(commands)
    running: dict[str, Running] = {}
    start = time.monotonic()
    peak_aggregate = 0
    while pending or running:
        while pending and len(running) < settings.workers:
            label = pending.pop(0)
            with (
                (logs / f"{label}.stdout.log").open("xb") as o,
                (logs / f"{label}.stderr.log").open("xb") as e,
            ):
                process = subprocess.Popen(
                    commands[label],
                    cwd=core.repo_root(),
                    stdout=o,
                    stderr=e,
                    start_new_session=True,
                )
            running[label] = Running(core.parse_label(label), process, time.monotonic())
            out[label]["status"] = "running"
        aggregate = 0
        for label, item in list(running.items()):
            try:
                rss = _tree_rss(psutil.Process(item.process.pid))
            except psutil.NoSuchProcess:
                rss = 0
            item.peak_rss = max(item.peak_rss, rss)
            aggregate += rss
            code = item.process.poll()
            reason = None
            if code is None:
                if rss > settings.rss_worker:
                    reason = f"worker RSS {rss} exceeded {settings.rss_worker}"
                elif time.monotonic() - item.started > settings.cell_cap:
                    reason = f"cap of {settings.cell_cap:.0f} s exceeded"
                elif time.monotonic() - start > settings.stage_cap:
                    reason = "stage cap exceeded"
                if reason is None:
                    continue
                _kill(item.process)
            elif code != 0:
                reason = f"worker exited with code {code}"
            out[label].update(
                status="failed" if reason else "exited",
                reason=reason,
                seconds=time.monotonic() - item.started,
                peak_rss_bytes=item.peak_rss,
                exit_code=item.process.returncode,
            )
            del running[label]
        peak_aggregate = max(peak_aggregate, aggregate)
        if aggregate > settings.rss_aggregate:
            for label, item in list(running.items()):
                _kill(item.process)
                out[label].update(status="failed", reason="killed: aggregate RSS limit")
                del running[label]
            pending.clear()
        if running or pending:
            time.sleep(settings.poll)
    out["_peak_aggregate_rss_bytes"] = {"value": peak_aggregate}
    return out


def cmd_restore_gate(args: argparse.Namespace) -> int:
    """ADR section 10.5 at run time: the restore check on the ten cells b101-o301-s601-C01..C10 of a
    training run, as supervised subprocesses. Writes ``<run>/restore_gate.json``; modifies no
    checkpoint or other stage file."""
    run = Path(args.run_dir)
    target = run / "restore_gate.json"
    if target.exists():
        print("refused: restore_gate.json already exists", file=sys.stderr)
        return 2
    folder = run / "restore_gate"
    folder.mkdir()
    commands = {
        label: [
            sys.executable,
            "-m",
            "arborlm.p8_train",
            "restore-worker",
            "--experiments-root",
            args.experiments_root,
            "--data-dir",
            args.data_dir,
            "--run-dir",
            str(run),
            "--label",
            label,
            "--out",
            str(folder / f"{label}.json"),
        ]
        for label in RESTORE_GATE_LABELS
    }
    supervised = supervise_commands(commands, folder / "logs", StageSettings(poll=0.2))
    peak = supervised.pop("_peak_aggregate_rss_bytes")["value"]
    cells_out = {}
    for label in RESTORE_GATE_LABELS:
        entry = dict(supervised[label])
        path = folder / f"{label}.json"
        detail = read_json(path) if path.is_file() else None
        entry["result"] = detail
        entry["recorded_final_digest"] = detail and detail["recorded_final_digest"]
        entry["restored_retrained_final_digest"] = detail and detail["restored_run_final_digest"]
        entry["seconds"] = entry.get("seconds")
        entry["passed"] = bool(
            detail and detail["passed"] and entry["status"] == "exited" and entry["exit_code"] == 0
        )
        cells_out[label] = entry
    passed = all(c["passed"] for c in cells_out.values())
    write_json(
        target,
        {
            "schema": "P8-restore-gate-v1",
            "gate": "ADR-0015 section 10 item 5 (run time)",
            "run": run.name,
            "cells": cells_out,
            "peak_aggregate_rss_bytes": peak,
            "passed": passed,
            "utc": utc_now(),
        },
    )
    print(json.dumps({"restore_gate": str(target), "passed": passed}))
    return 0 if passed else 1


def cmd_p5_invariance(args: argparse.Namespace) -> int:
    """ADR section 10.3: the P8 standard path with P5's cell b101-o301 flat seed 501 reproduces P5's
    step-512 state. P5 recorded checkpoint *file* hashes only, so the comparison restores the local
    P5 step-512 checkpoint with P5's own code and compares state digests; the P5-format file hash is
    compared as extra evidence. Training rows only."""
    from . import p5_checkpoint as p5ckpt
    from .p4_model import backbone_digest
    from .p5_config import FLAT
    from .p5_config import Cell as P5Cell
    from .p5_model import Model, optimizer_for, optimizer_names, state_digest

    configure()
    root = Path(args.experiments_root)
    cell = P5Cell(101, 301, 501, FLAT)
    quality = core.p5_quality_dir(root)
    row = next(c for c in read_json(quality / "cells.json") if c["label"] == cell.label)
    folder = quality / "cells" / row["run_id"]
    p5_manifest = read_json(folder / "manifest.json")
    p5_result = read_json(folder / "result.json")
    committed = read_json(core.repo_root() / core.P5_RESULTS / cell.label / "result.json")
    committed_file = committed["checkpoint_state_sha256"]["checkpoint-512"]
    state_file = folder / "checkpoint-512" / "state.pt"
    if (
        file_sha256(state_file) != committed_file
        or read_json(folder / "checkpoint-512" / "index.json")["state_sha256"] != committed_file
        or p5_result["checkpoint_state_sha256"]["checkpoint-512"] != committed_file
    ):
        raise ValueError("P5 checkpoint-512 file differs from the committed P5 record")
    backbone, provenance = core.load_backbone(cell, root)
    train, order, hashes = core.load_training(cell, root)
    rows = core.ordered_rows(train, order)
    random.seed(cell.seed)
    torch.default_generator.manual_seed(cell.seed)
    model = Model(cell, backbone)
    optimizer = optimizer_for(model)
    if backbone_digest(model.backbone) != p5_manifest["checkpoint_identity"]["backbone_sha256"]:
        raise ValueError("P5 backbone digest differs from the P8 extraction")
    started = time.monotonic()
    records = advance(model, optimizer, rows, cell, (), 1, core.STEPS)
    seconds = time.monotonic() - started
    p8_digest = state_digest(model)
    p5_model = Model(cell, backbone)
    p5_opt = optimizer_for(p5_model)
    optimizer_names(p5_model, p5_opt)
    counters = p5ckpt.restore(
        folder / "checkpoint-512", p5_model, p5_opt, p5_manifest["checkpoint_identity"]
    )
    p5_digest = state_digest(p5_model)
    tensors_equal = all(
        torch.equal(a, b)
        for (_, a), (_, b) in zip(
            sorted(model.state_dict().items()), sorted(p5_model.state_dict().items()), strict=True
        )
    )
    out = _new_run(root, core.INVARIANCE_PREFIX, False)
    p5ckpt_hash: str | None = None
    try:
        p5ckpt_hash = p5ckpt.save(
            out / "p8-replay-checkpoint-512",
            model,
            optimizer,
            core.STEPS,
            p5_manifest["checkpoint_identity"],
        )
    except Exception as exc:  # informational only
        p5ckpt_hash = f"not produced: {type(exc).__name__}: {exc}"
    recorded_file = p5_result["checkpoint_state_sha256"]["checkpoint-512"]
    result = {
        "schema": "P8-p5-invariance-v1",
        "dry_run": False,
        "gate": "ADR-0015 section 10 item 3 (invariance of the standard path)",
        "p5_cell": cell.label,
        "p5_run_id": row["run_id"],
        "p8_step_512_state_digest": p8_digest,
        "p5_checkpoint_512_state_digest": p5_digest,
        "all_state_tensors_bitwise_equal": tensors_equal,
        "p5_restore_counters": counters,
        "p5_checkpoint_512_file_verified_against_committed_record": committed_file,
        "p5_recorded_checkpoint_512_file_sha256": recorded_file,
        "p8_replay_in_p5_format_file_sha256": p5ckpt_hash,
        "file_hash_equal_informational": p5ckpt_hash == recorded_file,
        "training_seconds": seconds,
        "final_loss": records[-1]["loss"],
        "data": hashes,
        "parent": provenance["parent"]["run_id"],
        "passed": p8_digest == p5_digest and tensors_equal,
        "validation_data_opened": False,
    }
    write_json(out / "result.json", result)
    print(json.dumps({**result, "run": str(out)}, indent=2))
    return 0 if result["passed"] else 1


def project_makespan(durations: list[float], workers: int) -> float:
    """Greedy in-order scheduling of the durations onto ``workers``."""
    free = [0.0] * workers
    for duration in durations:
        index = free.index(min(free))
        free[index] += duration
    return max(free)


def cmd_rehearsal(args: argparse.Namespace) -> int:
    """ADR section 10.8: synthetic full-size rehearsal. Runs ``--per-case`` cells of every case
    type on a synthetic parent and synthetic bytes in a dry-run stage, then projects 60 cells."""
    root = Path(args.experiments_root)
    run = _new_run(root, core.REHEARSAL_PREFIX, True)
    wanted = []
    for case in core.CASES:
        wanted += [c.label for c in core.cells() if c.case == case][: args.per_case]
    labels = sorted(wanted, key=lambda lab: core.parse_label(lab).index)
    manifest = run_stage(
        run,
        labels,
        root,
        Path(args.data_dir),
        dry_run=True,
        settings=StageSettings(workers=args.workers),
        header={**stage_header("rehearsal", True, None), "run_id": run.name},
    )
    by_case: dict[str, list[float]] = {c: [] for c in core.CASES}
    rss: list[int] = []
    for row in manifest["cells"]:
        if row["status"] == "completed":
            by_case[core.parse_label(row["label"]).case].append(row["wall_seconds"])
            rss.append(row["supervisor_peak_rss_bytes"])
    if any(not v for v in by_case.values()):
        summary: dict[str, Any] = {"passed": False, "reason": "a case type did not complete"}
    else:
        mean = {case: sum(v) / len(v) for case, v in by_case.items()}
        durations = [mean[c.case] for c in core.cells()]
        projected = project_makespan(durations, core.WORKERS)
        summary = {
            "seconds_per_cell_by_case": mean,
            "seconds_per_cell_group": {
                "flat_standard": mean["C01"],
                "fixed_tree_standard": mean["C02"],
                "learned_tree_standard": mean["C03"],
                "flat_regularized": sum(mean[c] for c in ("C04", "C06", "C08")) / 3,
                "tree_regularized": sum(mean[c] for c in ("C05", "C07", "C09", "C10")) / 4,
            },
            "projected_stage_seconds_4_workers": projected,
            "projected_over_cap": projected / core.TRAIN_STAGE_CAP,
            "worst_cell_over_cap": max(max(v) for v in by_case.values()) / core.TRAIN_CELL_CAP,
            "peak_worker_rss_bytes": max(rss),
            "worker_rss_over_cap": max(rss) / core.RSS_WORKER,
            "peak_aggregate_rss_bytes": manifest["peak_aggregate_rss_bytes"],
            "aggregate_rss_over_cap": manifest["peak_aggregate_rss_bytes"] / core.RSS_AGGREGATE,
            "label": "measured on this machine (synthetic parent and bytes); projection analytical",
            "passed": projected <= core.REHEARSAL_MAX_FRACTION * core.TRAIN_STAGE_CAP
            and max(max(v) for v in by_case.values())
            <= core.REHEARSAL_MAX_FRACTION * core.TRAIN_CELL_CAP
            and max(rss) <= core.RSS_WORKER,
        }
    result = {"schema": "P8-rehearsal-v1", "dry_run": True, "stage": manifest["status"], **summary}
    write_json(run / "result.json", result)
    print(json.dumps({**result, "run": str(run)}, indent=2))
    return 0 if result.get("passed") else 1


# --- CLI -----------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m arborlm.p8_train", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--experiments-root", required=True)
        p.add_argument("--data-dir", required=True)

    cell = sub.add_parser("cell", help="train one cell")
    common(cell)
    cell.add_argument("--run-dir", required=True)
    cell.add_argument("--label", required=True)
    cell.add_argument("--dry-run", action="store_true")
    cell.set_defaults(func=cmd_cell)

    stage = sub.add_parser("stage", help="train all 60 cells under supervision")
    common(stage)
    stage.add_argument("--freeze-commit")
    stage.add_argument("--dry-run", action="store_true")
    stage.add_argument("--workers", type=int, default=core.WORKERS)
    stage.add_argument("--labels", help="comma-separated labels (dry run only)")
    stage.add_argument("--continue-after-failure", action="store_true")
    stage.set_defaults(func=cmd_stage)

    restore = sub.add_parser("restore-check", help="ADR 10.5 restore-and-compare for one cell")
    common(restore)
    restore.add_argument("--run-dir", required=True)
    restore.add_argument("--label", required=True)
    restore.set_defaults(func=cmd_restore_check)

    worker = sub.add_parser("restore-worker", help="internal: one restore check, JSON to --out")
    common(worker)
    worker.add_argument("--run-dir", required=True)
    worker.add_argument("--label", required=True)
    worker.add_argument("--out", required=True)
    worker.set_defaults(func=cmd_restore_worker)

    gate = sub.add_parser("restore-gate", help="ADR 10.5 on cells b101-o301-s601-C01..C10")
    common(gate)
    gate.add_argument("--run-dir", required=True)
    gate.set_defaults(func=cmd_restore_gate)

    inv = sub.add_parser("p5-invariance", help="ADR 10.3 reproduce P5 b101-o301 flat s501")
    common(inv)
    inv.set_defaults(func=cmd_p5_invariance)

    rehearsal = sub.add_parser("rehearsal", help="ADR 10.8 synthetic full-size rehearsal")
    common(rehearsal)
    rehearsal.add_argument("--per-case", type=int, default=1)
    rehearsal.add_argument("--workers", type=int, default=core.WORKERS)
    rehearsal.set_defaults(func=cmd_rehearsal)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
