# ruff: noqa: E501
"""P10S0 training. The trainer is ``studies.p9ii.train.Trainer`` itself (the same losses, schedules, AdamW at 0.003, clip 1.0, diagnostics every 64 updates), called and not copied;
what is written here is the cell run around it: S0's seed-set check, S0's model builder (WX), S0's record envelope (study code P10S0), snapshots, the whitelisted rehearsal record, and
the restoration and gradient-reach gates for S0's arms. No loss or accuracy is stored, returned, printed or raised in an exception message in rehearsal mode.

Cells are identified by ``core.Cell``; ``core.Cell.p9ii_cell()`` gives the ``studies.p9ii`` cell the trainer needs (base arm; the stage whose schedule multiplier applies to A2's U_pre).
"""

import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
import torch

from studies.p9.data import StudyData, TrainingStream
from studies.p9.train import optimizer_state_bytes
from studies.p9i.train import training_stream_for
from studies.p9ii import train as p9iitrain
from studies.p9ii.diagnostics import build_probe
from studies.p9ii.model import parameter_report, set_a2_phase
from studies.p9ii.train import Trainer, build_optimizers, load_model_state, peak_rss, save_snapshot
from studies.p9ii.train import TrainJob as P9IIJob

from . import core
from .model import build_model

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

configure = p9iitrain.configure
lines_of = p9iitrain.lines_of
REHEARSAL_PHASES = ("pre", "post", "main")


@dataclass
class Job:
    """One cell's training run. ``unit`` is U (8,192; the DRY stage and tests pass a tiny one); ``snapshots`` the update counts at which a snapshot is written (the readouts);
    ``rehearsal_phase`` forces one phase of A2 ('pre' or 'post'); ``max_updates`` caps the run (rehearsal, gates)."""

    cell: core.Cell
    mode: str
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    init_seed: int
    r1_seed: int
    target_seed: int
    hyper: core.Hyper = core.HYPER
    unit: int = core.UPDATES
    snapshots: tuple[int, ...] | None = None
    init_snapshot: Path | None = None
    max_updates: int | None = None
    diag_every: int = core.DIAG_EVERY
    rehearsal_phase: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    whitelist_only: bool | None = None  # write only the whitelisted rehearsal record (default: when mode is 'rehearsal'); the DRY rehearsal sets it on a test seed set

    @property
    def is_rehearsal(self) -> bool:
        return self.mode == "rehearsal" if self.whitelist_only is None else self.whitelist_only

    @property
    def updates(self) -> int:
        return self.cell.ct.updates(self.unit)

    def to_p9ii(self) -> P9IIJob:
        """The ``studies.p9ii`` job the trainer is built from. ``mode`` is the trainer's own and is not read by ``Trainer``; the seed-set check is S0's (``check_job``)."""
        return P9IIJob(
            cell=self.cell.p9ii_cell(), hyper=self.hyper, updates=self.updates, mode="calibration", data=self.data, stream=self.stream, backbone=self.backbone, out_dir=self.out_dir,
            init_seed=self.init_seed, r1_seed=self.r1_seed, target_seed=self.target_seed, stream_seed=0, unit=self.unit, stage=self.cell.ct.stage, snapshots=self.snapshots,
            init_snapshot=self.init_snapshot, max_updates=self.max_updates, diag_every=self.diag_every, rehearsal_phase=self.rehearsal_phase, extra=dict(self.extra),
        )  # fmt: skip


def check_job(job: Job) -> None:
    core.check_seed_set(job.mode, job.data.seeds.name)
    if job.cell.base in core.SUPERVISED and job.cell.celltype == "8K/4K":
        raise ValueError("A1 and A2 are not run at 8K/4K: no target injection (ADR-0020 section 5.1)")
    if job.rehearsal_phase is not None and (job.rehearsal_phase not in REHEARSAL_PHASES or (job.rehearsal_phase != "main" and job.cell.base != "A2")):
        raise ValueError(f"unknown or misplaced rehearsal phase {job.rehearsal_phase!r}")


# --- rehearsal whitelist validator (time, memory, shapes, counts, identity; no loss or accuracy) -----------------------------------------------------
class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key or value outside the whitelist."""


REHEARSAL_RECORD_KEYS = frozenset(
    {
        "kind", "schema", "study", "label", "mode", "block", "arm", "celltype", "slots", "facts", "phase", "identity", "environment", "updates", "wall_seconds", "seconds_per_update",
        "evaluation_wall_seconds", "peak_rss_bytes", "sampled_rss_bytes", "load_average", "busy_processes", "loss_finite", "parameters_finite", "gradients_finite", "shapes", "parameter_counts",
        "trainable_parameters", "stored_parameters", "optimizer_state_bytes", "trainable_backbone_parameters", "seed_set",
    }
)  # fmt: skip
_is_int, _is_number = p9iitrain._is_int, p9iitrain._is_number
_REHEARSAL_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "kind": lambda v: v == "rehearsal",
    "schema": lambda v: v == core.SCHEMA and _is_int(v),
    "study": lambda v: v == core.STUDY,
    "label": lambda v: isinstance(v, str),
    "mode": lambda v: v in ("rehearsal", "dry"),
    "block": lambda v: v in ("Q1", "WX", "PR", "PC"),
    "arm": lambda v: v in core.ARMS,
    "celltype": lambda v: v in core.CELLTYPES,
    "slots": lambda v: v in (4096, 16384, 65536),
    "facts": lambda v: _is_int(v) and v > 0,
    "phase": lambda v: v in REHEARSAL_PHASES,
    "identity": p9iitrain._valid_identity,
    "environment": p9iitrain._valid_plain,
    "updates": _is_int,
    "wall_seconds": _is_number,
    "seconds_per_update": _is_number,
    "evaluation_wall_seconds": _is_number,
    "peak_rss_bytes": _is_int,
    "sampled_rss_bytes": _is_int,
    "load_average": lambda v: isinstance(v, list | tuple) and all(_is_number(x) for x in v),
    "busy_processes": _is_int,
    "loss_finite": lambda v: isinstance(v, bool),
    "parameters_finite": lambda v: isinstance(v, bool),
    "gradients_finite": lambda v: isinstance(v, bool),
    "shapes": p9iitrain._valid_shapes,
    "parameter_counts": p9iitrain._valid_counts,
    "trainable_parameters": _is_int,
    "stored_parameters": _is_int,
    "optimizer_state_bytes": _is_int,
    "trainable_backbone_parameters": _is_int,
    "seed_set": lambda v: isinstance(v, str),
}
if set(_REHEARSAL_VALIDATORS) != set(REHEARSAL_RECORD_KEYS):
    raise ImportError("rehearsal validators must cover exactly REHEARSAL_RECORD_KEYS")


def validate_rehearsal_record(record: dict[str, Any]) -> None:
    for key, value in record.items():
        if key not in REHEARSAL_RECORD_KEYS:
            raise RehearsalRecordError(f"key not allowed in a rehearsal record: {key!r}")
        if not _REHEARSAL_VALIDATORS[key](value):
            raise RehearsalRecordError(f"value of {key!r} is not of the whitelisted form")
    for key in ("kind", "schema", "study", "mode"):
        if key not in record:
            raise RehearsalRecordError(f"rehearsal record lacks {key!r}")


def write_rehearsal_record(path: Path, record: dict[str, Any]) -> None:
    """The only writer of rehearsal-mode records (the kind is ``rehearsal``)."""
    validate_rehearsal_record(record)
    core.write_record(path, record)


# --- the cell run -----------------------------------------------------------------------------------------------------------------------------------
@dataclass
class Executed:
    record: dict[str, Any]
    model: Any
    trainer: Trainer
    updates: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


def snapshot_marks(job: Job, start: int, last: int) -> list[int]:
    marks = sorted(set(job.snapshots)) if job.snapshots is not None else [job.updates]
    return [m for m in marks if start < m <= last]


def run_job(job: Job) -> Executed:
    """Run a job and return the live state. ``train_cell`` is this plus its record on disk. Same loop as ``studies.p9ii.train.run_job`` (update log, diagnostics every
    ``diag_every`` updates, snapshots at the marks), with S0's checks and records."""
    check_job(job)
    cell = job.cell
    rehearsal = job.is_rehearsal
    started, cpu_started = time.monotonic(), time.process_time()
    model = build_model(cell.arm, cell.slots, job.init_seed, job.backbone, r1_seed=job.r1_seed)
    facts = int(job.stream.facts.shape[0])
    probe = build_probe(job.data, facts)
    trainer = Trainer(job.to_p9ii(), model, probe)
    if job.init_snapshot is not None:
        trainer.resume(job.init_snapshot)
    start = trainer.update
    last = job.updates if job.max_updates is None else min(job.updates, job.max_updates)
    marks = snapshot_marks(job, start, last)
    report = parameter_report(model)
    job.out_dir.mkdir(parents=True, exist_ok=True)
    update_log = None if rehearsal else (job.out_dir / "updates.jsonl").open("x", encoding="utf-8")
    diag_log = None if rehearsal else (job.out_dir / "diagnostics.jsonl").open("x", encoding="utf-8")
    sampled_rss, contexts = 0, 0
    snapshot_hashes: dict[str, str] = {}
    kept: list[dict[str, Any]] = []
    kept_diag: list[dict[str, Any]] = []
    status, reason = "completed", None
    process = psutil.Process()
    if not trainer.anchor:
        trainer.anchor = {n: p.detach().clone() for n, p in trainer.named}
    try:
        for update in range(start + 1, last + 1):
            batch = job.stream.batch(update)
            record = trainer.step(batch)
            contexts += int(batch.tokens.shape[0])
            sampled_rss = max(sampled_rss, int(process.memory_info().rss))
            if update_log is not None:
                update_log.write(core.json_line(record) + "\n")
                update_log.flush()
                kept.append(record)
            if update % job.diag_every == 0:
                diag = trainer.diagnose(batch)
                if diag_log is not None:
                    diag_log.write(core.json_line(diag) + "\n")
                    diag_log.flush()
                    kept_diag.append(diag)
            if update in marks:
                hashes = save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), write_json=False)
                snapshot_hashes[str(update)] = hashes["model_sha256"]
                if not rehearsal:
                    folder = job.out_dir / "snapshots" / core.snapshot_stem(update)
                    core.write_record(folder / "snapshot.json", {**core.envelope("snapshot"), "label": cell.label, "update": update, **hashes})
    except Exception as exc:
        status, reason = "failed", type(exc).__name__ + ": " + str(exc)
        if not rehearsal:
            _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start, cpu_started)
        raise
    finally:
        for log in (update_log, diag_log):
            if log is not None:
                log.flush()
                os.fsync(log.fileno())
                log.close()
    record_out = _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start, cpu_started)
    return Executed(record_out, model, trainer, kept, kept_diag)


def _write_train_record(job: Job, trainer: Trainer, report: dict[str, Any], started: float, contexts: int, sampled_rss: int, marks: list[int], snapshot_hashes: dict[str, str], status: str, reason: str | None, last: int, start: int, cpu_started: float) -> dict[str, Any]:
    cell = job.cell
    wall = time.monotonic() - started
    done = trainer.update - start
    exposures = job.stream.exposures(trainer.update)
    identity = core.code_identity()
    schedule = trainer.schedule
    by_phase = {"1": p9iitrain._a2_count(trainer, 1), "2": p9iitrain._a2_count(trainer, 2)} if cell.base == "A2" else {"1": report["trainable"]}
    record: dict[str, Any] = {
        **core.envelope("train"),
        "label": cell.label, "arm": cell.arm, "block": cell.block, "celltype": cell.celltype, "slots": cell.slots, "draw": cell.draw, "seed_index": cell.seed_index,
        "facts": int(job.stream.facts.shape[0]), "init_seed": job.init_seed, "target_seed": job.target_seed, "mode": job.mode, "unit_updates": job.unit,
        "matched_updates": job.updates, "run_updates": last, "snapshots": marks, "hyper": job.hyper.as_json(),
        "schedule": {"total": schedule.total, "u_pre": schedule.u_pre},
        "examples": contexts, "answer_site_exposures": contexts * core.ANSWER_SITES_PER_CONTEXT,
        "unique_facts": int((exposures > 0).sum()), "exposure_per_fact_min": int(exposures.min()), "exposure_per_fact_max": int(exposures.max()),
        "exposure_per_fact_mean": float(exposures.float().mean()), "exposure_per_fact_analytical": core.exposures_per_fact(trainer.update, int(job.stream.facts.shape[0])),
        "trainable_parameters": max(by_phase.values()),
        "trainable_parameters_label": "the largest trainable set over the phases (A2: phase 2, everything in the addition); the count of each phase is in trainable_parameters_by_phase",
        "trainable_parameters_by_phase": by_phase, "trainable_backbone_parameters": report["trainable_backbone"], "stored_parameters": report["stored"],
        "parameters_by_group": dict(report["by_group"]),
        "cpu_seconds": time.process_time() - cpu_started,
        "cost": {"cpu_seconds_label": "measured process CPU seconds of this run (descriptive; no efficiency claim; never a speedup)", **core.analytical_cost(cell.arm, cell.slots, trainer.update)},
        "optimizer_state_bytes": optimizer_state_bytes(trainer.optimizers), "wall_seconds": wall, "peak_rss_bytes": peak_rss(),
        "update_log": "" if job.is_rehearsal else "updates.jsonl", "diagnostics_log": "" if job.is_rehearsal else "diagnostics.jsonl",
        "snapshot_sha256": snapshot_hashes, "identity": identity, "environment": core.environment(), "status": status, "reason": reason, "seed_set": job.data.seeds.name, **job.extra,
    }  # fmt: skip
    if job.is_rehearsal:
        rehearsal = {
            **core.envelope("rehearsal"), "label": cell.label, "mode": "rehearsal" if job.mode == "rehearsal" else "dry", "block": cell.block, "arm": cell.arm, "celltype": cell.celltype, "slots": cell.slots, "facts": cell.facts,
            "phase": job.rehearsal_phase or "main", "identity": identity, "environment": record["environment"], "updates": done, "wall_seconds": wall,
            "seconds_per_update": wall / done if done else 0.0, "peak_rss_bytes": record["peak_rss_bytes"], "sampled_rss_bytes": sampled_rss, "load_average": list(os.getloadavg()),
            "busy_processes": int(job.extra.get("busy_processes", 0)), "loss_finite": trainer.all_finite["loss"], "parameters_finite": trainer.all_finite["parameters"],
            "gradients_finite": trainer.all_finite["gradients"], "shapes": {n: list(p.shape) for n, p in trainer.named}, "parameter_counts": dict(report["by_group"]),
            "trainable_parameters": report["trainable"], "stored_parameters": report["stored"], "optimizer_state_bytes": record["optimizer_state_bytes"],
            "trainable_backbone_parameters": report["trainable_backbone"], "seed_set": job.data.seeds.name,
        }  # fmt: skip
        write_rehearsal_record(job.out_dir / "rehearsal.json", rehearsal)
    else:
        core.write_record(job.out_dir / "train.json", core.jsonable(record))
    return record


def train_cell(job: Job) -> dict[str, Any]:
    """Train one cell for ``job.updates`` updates (or up to ``max_updates``). Constant learning rate; deterministic on CPU/FP32. On a failure ``train.json`` is written with status
    ``failed`` (not in rehearsal mode) and the exception re-raised; a failed cell is kept and not re-run."""
    return run_job(job).record


# --- gates: restoration and gradient reach -------------------------------------------------------------------------------------------------------------
def checkpoint_restoration_check(job: Job, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot, restore (model, optimizer, RNG, trainer state) and continue; every tensor must be
    bit-identical (``studies.p9ii.train``'s comparison over parameters, buffers, optimizer state and anchors)."""
    root = job.out_dir / "restore_check"

    def sub(name: str, **kw: Any) -> Job:
        return Job(**{**job.__dict__, "out_dir": root / name, **kw})

    total = 2 * split_update
    straight = run_job(sub("straight", max_updates=total, snapshots=()))
    run_job(sub("first", max_updates=split_update, snapshots=(split_update,)))
    folder = root / "first" / "snapshots" / core.snapshot_stem(split_update)
    resumed = run_job(sub("resumed", max_updates=total, snapshots=(), init_snapshot=folder))
    a, b = p9iitrain._state_tensors(straight), p9iitrain._state_tensors(resumed)  # type: ignore[arg-type]
    mismatches = sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k]))
    return {"identical": not mismatches, "mismatches": mismatches, "split_update": split_update, "updates": total, "tensors_compared": len(a), "resumed_from_update": split_update}


def gradient_reach(job: Job, tokens: "Tensor", fact_ids: "Tensor", which: str = "training", *, phase: int | None = None, update: int = 1) -> dict[str, Any]:
    """One backward pass of ``which`` in {training, answer, addr, div} through the same loss function the trainer uses (``Trainer.compute_losses``). Returns ``reached``,
    ``trainable``, ``stray`` and ``buffer_gradients`` as ``studies.p9ii.train.gradient_reach`` does."""
    model = build_model(job.cell.arm, job.cell.slots, job.init_seed, job.backbone, r1_seed=job.r1_seed, seed_rng=False)
    probe = build_probe(job.data, int(job.stream.facts.shape[0]))
    trainer = Trainer(job.to_p9ii(), model, probe)
    chosen = trainer.phase if phase is None else phase
    if job.cell.base == "A2":
        set_a2_phase(model, chosen)
    model.zero_grad(set_to_none=True)
    total, parts = trainer.compute_losses(tokens, fact_ids, update, chosen)
    loss = total if which == "training" else parts[which]
    loss.backward()  # type: ignore[no-untyped-call]
    reached: dict[str, bool] = {}
    stray: list[str] = []
    for name, p in model.named_parameters():
        if p.requires_grad:
            reached[name] = p.grad is not None and bool(p.grad.isfinite().all()) and bool((p.grad != 0).any())
        elif p.grad is not None:
            stray.append(name)
    buffer_gradients = [n for n, b in model.addition.named_buffers() if b.grad is not None or b.requires_grad]
    return {"reached": reached, "trainable": sorted(reached), "stray": stray, "buffer_gradients": buffer_gradients}


def finite_loss_log(updates: list[dict[str, Any]]) -> bool:
    return all(math.isfinite(float(r["task_loss"])) for r in updates)


__all__ = ["Executed", "Job", "build_optimizers", "check_job", "load_model_state", "peak_rss", "run_job", "train_cell", "training_stream_for"]
