# ruff: noqa: E501
"""P10S1 training (ADR-0021 sections 4, 5.4, 7.3): the alphabet loss at answer sites for every arm, ONE AdamW (lr 0.003, no weight decay; D-OQ's rate is the calibrated one) with
one gradient clip at 1.0, a constant rate, snapshots at the registered updates (a snapshot is a valid shorter run, gate G4), the cumulative movement of value rows on updates
with and without their own gradient (section 7.3), process CPU seconds per snapshot (section 5.4), and the modes ``registered``, ``calibration`` and ``rehearsal``.

The step is P9-I's ``Trainer.step`` operation for operation (forward, ``alphabet_loss``, ``autograd.grad``, clip, ``optimizer.step``), so F-OQ and R2 reproduce P9-I's R1 and R2
training step bit for bit; the extra bookkeeping (row movement, logs) only reads tensors. Rehearsal mode writes one whitelisted record (time, memory, finiteness, shapes,
counts, identity): no loss or accuracy is stored, returned, printed or raised in any exception message.

Imported from P9 and P9-I and called, not copied: ``alphabet_loss``, ``training_stream_for``, ``fact_lut_for``, ``optimizer_state_bytes``, ``rng_state``, ``restore_rng``.
"""

import json
import math
import os
import resource
import sys
import tempfile
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
import torch
from torch import nn
from torch.optim import AdamW, Optimizer

from arborlm.engine import optimizer_for as _adamw_for
from arborlm.io import file_sha256
from studies.p9.data import Batch, StudyData, TrainingStream
from studies.p9.train import optimizer_state_bytes, restore_rng, rng_state
from studies.p9i.train import alphabet_loss, fact_lut_for, training_stream_for

from . import core
from .model import GROUPS, P10S1Model, build_model, parameter_report

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

MODES = ("registered", "calibration", "rehearsal")
LOG_EVERY = 64
__all__ = ["fact_lut_for", "training_stream_for"]


def peak_rss() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def build_optimizers(model: P10S1Model, lr: float = core.LEARNING_RATE) -> list[Optimizer]:
    """One AdamW over the trainable parameters (a one-element list, so snapshots keep their list form). At lr 0.003 this is ``arborlm.engine.optimizer_for`` itself (P9-I's
    optimizer); another rate (D-OQ, chosen in calibration) differs in the rate only."""
    named = model.trainable()
    if not named:
        raise ValueError("no trainable parameters")
    params = nn.ParameterList(p for _, p in named)
    if lr == core.LEARNING_RATE:
        return [_adamw_for(params)]
    return [AdamW(params.parameters(), lr=lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0, amsgrad=False, foreach=False, fused=False)]


# --- job ----------------------------------------------------------------------------------------------------------------------------
@dataclass
class TrainJob:
    """Inputs of one cell's run. ``snapshots`` are the update counts at which a snapshot is written; ``optimizer_marks`` those that also keep the optimizer state (default
    the last); ``max_updates`` caps the run (rehearsal, gates, calibration read-outs)."""

    cell: core.Cell
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    r1_seed: int
    hash_seed: int
    mode: str
    updates: int
    snapshots: Collection[int] | None = None
    optimizer_marks: Collection[int] | None = None
    init_snapshot: Path | None = None
    max_updates: int | None = None
    fact_lut: "Tensor | None" = None
    log_every: int = LOG_EVERY
    extra: dict[str, Any] = field(default_factory=dict)


def job_model(job: TrainJob, *, seed_rng: bool = True) -> P10S1Model:
    c = job.cell
    return build_model(c.arm, c.slots, c.init_seed, job.backbone, fact_lut=job.fact_lut, r1_seed=job.r1_seed, hash_seed=job.hash_seed, seed_rng=seed_rng)


# --- rehearsal whitelist validator ----------------------------------------------------------------------------------------------------
class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key or value outside the whitelist."""


FORBIDDEN_WORDS = ("loss", "acc", "nll", "perplex", "entropy", "margin", "correct", "bits")
REHEARSAL_RECORD_KEYS = frozenset(
    {
        "kind", "schema", "study", "label", "mode", "stage", "arm", "slots", "facts", "identity", "environment", "updates", "wall_seconds", "cpu_seconds", "seconds_per_update",
        "cpu_seconds_per_update", "evaluation_wall_seconds", "evaluation_cpu_seconds", "evaluation_snapshots", "peak_rss_bytes", "sampled_rss_bytes", "load_average", "loss_finite",
        "parameters_finite", "gradients_finite", "shapes", "parameter_counts", "trainable_parameters", "stored_parameters", "optimizer_state_bytes", "trainable_backbone_parameters",
        "seed_set", "index_build_seconds", "work_counters", "item",
    }
)  # fmt: skip


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: object) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)


def _clean_name(name: object) -> bool:
    return isinstance(name, str) and not any(w in name.lower() for w in FORBIDDEN_WORDS)


def _valid_shapes(v: object) -> bool:
    return isinstance(v, dict) and all(_clean_name(k) for k in v) and all(isinstance(s, list) and all(_is_int(d) for d in s) for s in v.values())


def _valid_counts(v: object) -> bool:
    return isinstance(v, dict) and all(_clean_name(k) and _is_int(c) for k, c in v.items())


def _valid_identity(v: object) -> bool:
    return isinstance(v, dict) and all(_clean_name(k) and isinstance(s, str) for k, s in v.items())


def _valid_plain(v: object) -> bool:
    if isinstance(v, dict):
        return all(_clean_name(k) and _valid_plain(x) for k, x in v.items())
    if isinstance(v, list):
        return all(_valid_plain(x) for x in v)
    return v is None or isinstance(v, str | bool | int) or _is_number(v)


def _valid_work(v: object) -> bool:
    return isinstance(v, dict) and all(isinstance(k, str) and _is_number(x) for k, x in v.items())


_REHEARSAL_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "kind": lambda v: v == "rehearsal",
    "schema": lambda v: v == core.SCHEMA and _is_int(v),
    "study": lambda v: v == core.STUDY,
    "label": lambda v: isinstance(v, str),
    "mode": lambda v: v == "rehearsal",
    "stage": lambda v: isinstance(v, str),
    "arm": lambda v: v in core.ARMS,
    "slots": lambda v: v in core.SLOT_COUNTS,
    "facts": _is_int,
    "identity": _valid_identity,
    "environment": _valid_plain,
    "updates": _is_int,
    "wall_seconds": _is_number,
    "cpu_seconds": _is_number,
    "seconds_per_update": _is_number,
    "cpu_seconds_per_update": _is_number,
    "evaluation_wall_seconds": _is_number,
    "evaluation_cpu_seconds": _is_number,
    "evaluation_snapshots": _is_int,
    "peak_rss_bytes": _is_int,
    "sampled_rss_bytes": _is_int,
    "load_average": lambda v: isinstance(v, list | tuple) and all(_is_number(x) for x in v),
    "loss_finite": lambda v: isinstance(v, bool),
    "parameters_finite": lambda v: isinstance(v, bool),
    "gradients_finite": lambda v: isinstance(v, bool),
    "shapes": _valid_shapes,
    "parameter_counts": _valid_counts,
    "trainable_parameters": _is_int,
    "stored_parameters": _is_int,
    "optimizer_state_bytes": _is_int,
    "trainable_backbone_parameters": _is_int,
    "seed_set": lambda v: isinstance(v, str),
    "index_build_seconds": _is_number,
    "work_counters": _valid_work,
    "item": lambda v: isinstance(v, str),
}
if set(_REHEARSAL_VALIDATORS) != set(REHEARSAL_RECORD_KEYS):
    raise ImportError("rehearsal validators must cover exactly REHEARSAL_RECORD_KEYS")


def validate_rehearsal_record(record: dict[str, Any]) -> None:
    """Raise unless every key is whitelisted and every value has the whitelisted type and shape."""
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


# --- snapshots ----------------------------------------------------------------------------------------------------------------------
def _publish(path: Path, payload: Any) -> str:
    """Write ``payload`` atomically (temp file, fsync, exclusive link); refuse to overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return file_sha256(path)


def save_snapshot(out_dir: Path, update: int, model: P10S1Model, optimizers: list[Optimizer], extra: dict[str, Any], *, keep_optimizer: bool = True, write_json: bool = True) -> dict[str, str]:
    """``model.pt`` (the whole state), ``optimizer.pt`` (optimizer, RNG and trainer state; only when ``keep_optimizer``) and ``snapshot.json`` into
    ``<out_dir>/snapshots/uNNNNNNN``; returns the file hashes."""
    folder = out_dir / "snapshots" / core.snapshot_stem(update)
    hashes = {"model_sha256": _publish(folder / "model.pt", {"update": update, "label": extra.get("label"), "model": model.state_dict()})}
    if keep_optimizer:
        hashes["optimizer_sha256"] = _publish(folder / "optimizer.pt", {"update": update, "optimizers": [o.state_dict() for o in optimizers], "rng": extra["rng"], "trainer": extra["trainer"]})
    if write_json:
        core.write_record(folder / "snapshot.json", {**core.envelope("snapshot"), "label": extra["label"], "update": update, **hashes})
    return hashes


def load_model_state(snapshot_dir: Path, model: P10S1Model) -> int:
    """Load a snapshot's model state (keys, shapes, dtypes and finiteness checked; every backbone tensor must equal the live frozen one)."""
    payload = torch.load(snapshot_dir / "model.pt", weights_only=True, map_location="cpu")
    tensors, expected = payload["model"], model.state_dict()
    if tensors.keys() != expected.keys():
        raise ValueError("snapshot model keys differ from the model's")
    for name, tensor in expected.items():
        saved = tensors[name]
        if saved.shape != tensor.shape or saved.dtype != tensor.dtype:
            raise ValueError(f"snapshot tensor {name} has a different shape or dtype")
        if saved.is_floating_point() and not bool(torch.isfinite(saved).all()):
            raise ValueError(f"snapshot tensor {name} is not finite")
        if name.startswith("backbone.") and not torch.equal(saved, tensor):
            raise ValueError("snapshot backbone differs from the live frozen backbone")
    model.load_state_dict(tensors, strict=True)
    return int(payload["update"])


# --- the trainer ----------------------------------------------------------------------------------------------------------------------
def _zero() -> dict[str, float]:
    return dict.fromkeys(GROUPS, 0.0)


class Trainer:
    """One cell's optimization state and its step. ``step(batch)`` runs one update (P9-I's step) and returns the per-update record."""

    def __init__(self, job: TrainJob, model: P10S1Model) -> None:
        self.job, self.cell, self.model = job, job.cell, model
        self.update = 0
        self.optimizers = build_optimizers(model, job.cell.lr)
        self.named = model.trainable()
        self.params = [p for _, p in self.named]
        self.group = {name: model.group_of(name) for name, _ in self.named}
        self.values_index = next((i for i, (n, _) in enumerate(self.named) if n.endswith(".values")), None)
        self.move_with = 0.0  # cumulative movement of value rows on updates in which the row had its own gradient
        self.move_without = 0.0  # ... and on updates in which it had none
        self.rows_with_grad_updates = 0
        self.all_finite = {"loss": True, "gradients": True, "parameters": True}

    # -- state ----------------------------------------------------------------------------------------------------------------------
    def trainer_state(self) -> dict[str, Any]:
        return {"update": self.update, "move_with": self.move_with, "move_without": self.move_without, "rows_with_grad_updates": self.rows_with_grad_updates}

    def snapshot_extra(self) -> dict[str, Any]:
        return {"label": self.cell.label, "rng": rng_state(), "trainer": self.trainer_state()}

    def resume(self, snapshot_dir: Path) -> None:
        """Restore model, optimizer, RNG and trainer state from a snapshot directory."""
        update = load_model_state(snapshot_dir, self.model)
        self.update = update
        state = torch.load(snapshot_dir / "optimizer.pt", weights_only=True, map_location="cpu")
        if len(state["optimizers"]) != len(self.optimizers):
            raise ValueError("snapshot optimizer count differs")
        for optimizer, saved in zip(self.optimizers, state["optimizers"], strict=True):
            optimizer.load_state_dict(saved)
        t = state["trainer"]
        self.move_with, self.move_without, self.rows_with_grad_updates = float(t["move_with"]), float(t["move_without"]), int(t["rows_with_grad_updates"])
        restore_rng(state["rng"])

    # -- one update -------------------------------------------------------------------------------------------------------------------
    def step(self, batch: Batch) -> dict[str, Any]:
        began = time.monotonic()
        update = self.update + 1
        tokens = batch.tokens
        self.model.train()
        for optimizer in self.optimizers:
            optimizer.zero_grad(set_to_none=True)
        logits, _ = self.model(tokens[:, :-1])
        loss = alphabet_loss(logits, tokens)
        if not bool(torch.isfinite(loss)):
            self.all_finite["loss"] = False
            raise ValueError(f"non-finite task loss at update {update}")
        grads = torch.autograd.grad(loss, self.params, allow_unused=True)
        for p, g in zip(self.params, grads, strict=True):
            p.grad = torch.zeros_like(p) if g is None else g
        norms = self._group_norms(grads)
        clip = nn.utils.clip_grad_norm_(self.params, core.CLIP_NORM, error_if_nonfinite=False)
        if not bool(torch.isfinite(clip)):
            self.all_finite["gradients"] = False
            raise ValueError(f"non-finite gradient norm at update {update}")
        before = self.params[self.values_index].detach().clone() if self.values_index is not None else None
        for optimizer in self.optimizers:
            optimizer.step()
        if not all(bool(p.isfinite().all()) for p in self.params):
            self.all_finite["parameters"] = False
            raise ValueError(f"non-finite parameter at update {update}")
        if before is not None and self.values_index is not None:
            self._track_rows(grads[self.values_index], before)
        self.update = update
        return {"update": update, "task_loss": loss.detach().item(), "grad_norm": norms, "clip_total_norm": float(clip), "seconds": time.monotonic() - began}

    def _track_rows(self, grad: "Tensor | None", before: "Tensor") -> None:
        """Row movement (section 7.3): the L2 displacement of every value row this update, summed over rows that had a gradient in this update and over rows that had none."""
        after = self.params[self.values_index].detach()  # type: ignore[index]
        moved = (after - before).norm(dim=1)
        has = (grad != 0).any(dim=1) if grad is not None else torch.zeros(moved.shape[0], dtype=torch.bool)
        self.move_with += float(moved[has].sum())
        self.move_without += float(moved[~has].sum())
        self.rows_with_grad_updates += int(has.sum())

    def _group_norms(self, grads: "tuple[Tensor | None, ...]") -> dict[str, float]:
        squares = _zero()
        for (name, _), g in zip(self.named, grads, strict=True):
            if g is not None:
                squares[self.group[name]] += float(g.pow(2).sum())
        return {k: math.sqrt(v) for k, v in squares.items()}

    def movement(self) -> dict[str, float]:
        total = self.move_with + self.move_without
        return {"with_own_gradient": self.move_with, "without_own_gradient": self.move_without, "total": total, "share_without": self.move_without / total if total > 0 else 0.0, "row_updates_with_gradient": float(self.rows_with_grad_updates)}


# --- the cell run ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Executed:
    """A finished (or in-memory) run: the record plus the live state."""

    record: dict[str, Any]
    model: P10S1Model
    trainer: Trainer
    updates: list[dict[str, Any]] = field(default_factory=list)


def check_job_seeds(job: TrainJob) -> None:
    if job.mode not in MODES:
        raise ValueError(f"unknown mode {job.mode!r}")
    core.check_seed_set(job.mode, job.data.seeds.name)


def snapshot_marks(job: TrainJob, start: int, last: int) -> list[int]:
    marks = sorted(set(job.snapshots)) if job.snapshots is not None else [job.updates]
    return [m for m in marks if start < m <= last]


def run_job(job: TrainJob) -> Executed:
    """Run a job and return the live state. ``train_cell`` is this plus its record on disk."""
    check_job_seeds(job)
    mode = job.mode
    rehearsal = mode == "rehearsal"
    started, cpu_started = time.monotonic(), time.process_time()
    model = job_model(job)
    trainer = Trainer(job, model)
    if job.init_snapshot is not None:
        trainer.resume(job.init_snapshot)
    start = trainer.update
    last = job.updates if job.max_updates is None else min(job.updates, job.max_updates)
    marks = snapshot_marks(job, start, last)
    keep_opt = set(job.optimizer_marks) if job.optimizer_marks is not None else {last}
    report = parameter_report(model)
    job.out_dir.mkdir(parents=True, exist_ok=True)
    update_log = None if rehearsal else (job.out_dir / "updates.jsonl").open("x", encoding="utf-8")
    sampled_rss, contexts = 0, 0
    snapshot_hashes: dict[str, str] = {}
    meta: dict[str, dict[str, Any]] = {}
    kept: list[dict[str, Any]] = []
    status, reason = "completed", None
    process = psutil.Process()
    try:
        for update in range(start + 1, last + 1):
            batch = job.stream.batch(update)
            record = trainer.step(batch)
            contexts += int(batch.tokens.shape[0])
            if update % job.log_every == 0 or update in marks:
                sampled_rss = max(sampled_rss, int(process.memory_info().rss))
            if update_log is not None and (update % job.log_every == 0 or update == last):
                update_log.write(core.json_line(record) + "\n")
                update_log.flush()
                kept.append(record)
            if update in marks:
                hashes = save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), keep_optimizer=update in keep_opt, write_json=not rehearsal)
                snapshot_hashes[str(update)] = hashes["model_sha256"]
                meta[str(update)] = {"cpu_seconds": time.process_time() - cpu_started, "wall_seconds": time.monotonic() - started, "movement": trainer.movement(), "peak_rss_bytes": peak_rss()}
    except Exception as exc:
        status, reason = "failed", type(exc).__name__ + ": " + str(exc)
        if not rehearsal:
            _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, meta, status, reason, last, start, cpu_started)
        raise
    finally:
        if update_log is not None:
            update_log.flush()
            os.fsync(update_log.fileno())
            update_log.close()
    record_out = _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, meta, status, reason, last, start, cpu_started)
    return Executed(record_out, model, trainer, kept)


def _write_train_record(job: TrainJob, trainer: Trainer, report: Any, started: float, contexts: int, sampled_rss: int, marks: list[int], snapshot_hashes: dict[str, str], meta: dict[str, dict[str, Any]], status: str, reason: str | None, last: int, start: int, cpu_started: float) -> dict[str, Any]:
    cell = job.cell
    wall = time.monotonic() - started
    cpu = time.process_time() - cpu_started
    done = trainer.update - start
    facts = int(job.stream.facts.shape[0])
    exposures = job.stream.exposures(trainer.update)
    identity = core.code_identity()
    counters = trainer.model.counters.per_query()
    record: dict[str, Any] = {
        **core.envelope("train"),
        "label": cell.label, "kind_of_cell": cell.kind, "arm": cell.arm, "facts": facts, "slots": cell.slots, "draw": cell.draw, "init_seed": cell.init_seed, "u_p": cell.u_p,
        "learning_rate": cell.lr, "mode": job.mode, "run_updates_registered": cell.run_updates, "matched_updates": job.updates, "run_updates": last, "snapshots": marks,
        "examples": contexts, "answer_site_exposures": contexts * core.ANSWER_SITES_PER_CONTEXT, "unique_facts": int((exposures > 0).sum()),
        "exposure_per_fact_min": int(exposures.min()), "exposure_per_fact_max": int(exposures.max()), "exposure_per_fact_mean": float(exposures.float().mean()),
        "exposure_per_fact_analytical": core.exposures_per_fact(trainer.update, facts),
        "trainable_parameters": report.trainable, "trainable_backbone_parameters": report.trainable_backbone, "stored_parameters": report.stored, "parameters_by_group": dict(report.by_group),
        "dense_hidden": report.dense_hidden, "work_per_query_counted_in_training": counters,
        "snapshot_meta": meta, "cpu_seconds": cpu, "wall_seconds": wall, "peak_rss_bytes": peak_rss(), "sampled_rss_bytes": sampled_rss,
        "movement": trainer.movement(), "optimizer_state_bytes": optimizer_state_bytes(trainer.optimizers),
        "update_log": "" if job.mode == "rehearsal" else "updates.jsonl", "snapshot_sha256": snapshot_hashes, "identity": identity, "environment": core.environment(),
        "status": status, "reason": reason, "seed_set": job.data.seeds.name, "cost_label": "measured process CPU seconds of this run (descriptive; the MC readout uses the frozen rehearsal multipliers)",
        **job.extra,
    }  # fmt: skip
    if job.mode == "rehearsal":
        rehearsal = {
            **core.envelope("rehearsal"), "label": cell.label, "mode": "rehearsal", "stage": "rehearse", "arm": cell.arm, "slots": cell.slots, "facts": facts, "identity": identity,
            "environment": record["environment"], "updates": done, "wall_seconds": wall, "cpu_seconds": cpu, "seconds_per_update": wall / done if done else 0.0,
            "cpu_seconds_per_update": cpu / done if done else 0.0, "peak_rss_bytes": record["peak_rss_bytes"], "sampled_rss_bytes": sampled_rss, "load_average": list(os.getloadavg()),
            "loss_finite": trainer.all_finite["loss"], "parameters_finite": trainer.all_finite["parameters"], "gradients_finite": trainer.all_finite["gradients"],
            "shapes": {n: list(p.shape) for n, p in trainer.named}, "parameter_counts": dict(report.by_group), "trainable_parameters": report.trainable, "stored_parameters": report.stored,
            "optimizer_state_bytes": record["optimizer_state_bytes"], "trainable_backbone_parameters": report.trainable_backbone, "seed_set": job.data.seeds.name,
            "work_counters": {k: float(v) for k, v in counters.items()},
        }  # fmt: skip
        write_rehearsal_record(job.out_dir / "rehearsal.json", rehearsal)
    else:
        core.write_record(job.out_dir / "train.json", core.jsonable(record))
    return record


def train_cell(job: TrainJob) -> dict[str, Any]:
    """Train one cell for ``job.updates`` updates (or up to ``max_updates``), writing ``updates.jsonl`` (every 64 updates), the snapshots and ``train.json`` (rehearsal: binary
    snapshots and ``rehearsal.json`` only). Constant learning rate. Deterministic on CPU/FP32 (G4). On a failure ``train.json`` is written with status ``failed`` (not in rehearsal
    mode) and the exception re-raised."""
    return run_job(job).record


# --- gates: restoration and gradient reach ------------------------------------------------------------------------------------------
def _state_tensors(run: Executed) -> "dict[str, Tensor]":
    model = run.model
    out = {f"param:{n}": p.detach() for n, p in model.named_parameters()}
    out.update({f"buffer:{n}": b for n, b in model.addition.named_buffers()})
    names = {id(p): n for n, p in model.named_parameters()}
    for i, optimizer in enumerate(run.trainer.optimizers):
        for param, state in optimizer.state.items():
            for k, v in state.items():
                if torch.is_tensor(v):
                    out[f"optim{i}:{names[id(param)]}:{k}"] = v
    out["trainer:movement"] = torch.tensor([run.trainer.move_with, run.trainer.move_without, float(run.trainer.rows_with_grad_updates)], dtype=torch.float64)
    return out


def checkpoint_restoration_check(job: TrainJob, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot, restore (model, optimizer, RNG, trainer state) and continue; every tensor must
    be bit-identical. Runs in ``<out_dir>/restore_check/{straight,first,resumed}``."""
    root = job.out_dir / "restore_check"

    def sub(name: str, **kw: Any) -> TrainJob:
        return TrainJob(**{**job.__dict__, "out_dir": root / name, **kw})

    total = 2 * split_update
    straight = run_job(sub("straight", updates=job.updates, max_updates=total, snapshots=()))
    run_job(sub("first", updates=job.updates, max_updates=split_update, snapshots=(split_update,), optimizer_marks=(split_update,)))
    folder = root / "first" / "snapshots" / core.snapshot_stem(split_update)
    resumed = run_job(sub("resumed", updates=job.updates, max_updates=total, snapshots=(), init_snapshot=folder))
    a, b = _state_tensors(straight), _state_tensors(resumed)
    mismatches = sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k]))
    return {"identical": not mismatches, "mismatches": mismatches, "split_update": split_update, "updates": total, "tensors_compared": len(a), "resumed_from_update": split_update}


def gradient_reach(job: TrainJob, tokens: "Tensor") -> dict[str, Any]:
    """One backward pass of the training loss on ``tokens [B, 64]``, through the same loss function the trainer uses. Returns ``reached`` (every trainable parameter -> it received a
    finite non-zero gradient), ``stray`` (parameters that are not trainable yet carry a gradient: must be empty), ``buffer_gradients`` and the gradient of the value table (for the
    per-row checks of H8 and R2)."""
    model = job_model(job, seed_rng=False)
    model.zero_grad(set_to_none=True)
    logits, _ = model(tokens[:, :-1])
    loss = alphabet_loss(logits, tokens)
    loss.backward()  # type: ignore[no-untyped-call]
    reached: dict[str, bool] = {}
    stray: list[str] = []
    for name, p in model.named_parameters():
        if p.requires_grad:
            reached[name] = p.grad is not None and bool(p.grad.isfinite().all()) and bool((p.grad != 0).any())
        elif p.grad is not None:
            stray.append(name)
    values = dict(model.named_parameters()).get("addition.values")
    rows = None if values is None or values.grad is None else (values.grad != 0).any(dim=1).nonzero().squeeze(1)
    buffer_gradients = [n for n, b in model.addition.named_buffers() if b.grad is not None or b.requires_grad]
    return {"reached": reached, "trainable": sorted(reached), "stray": stray, "buffer_gradients": buffer_gradients, "value_rows_with_gradient": None if rows is None else rows.tolist()}


def configure() -> None:
    """Single-thread deterministic CPU (``arborlm.engine.configure_cpu``), tolerant of a second call."""
    from arborlm.engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:  # the inter-op thread count can be set once per process
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


def lines_of(path: Path) -> list[dict[str, Any]]:
    """The records of a JSONL log; ``jsonable``'s string markers are left as they are."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
