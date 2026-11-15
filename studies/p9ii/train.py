# ruff: noqa: E501
"""P9II training (ADR-0019 sections 3, 4, 5 and 8.1): the alphabet loss at answer sites for every arm, the auxiliary losses of A1, A1-S, A2
and A5-D, the schedules of A2 and A4, the centre of A5-C, ONE AdamW (lr 0.003) with one gradient clip at 1.0, matched updates, snapshots
with optimizer state, the per-update log and the per-cell diagnostics every 64 updates, and the modes ``registered``, ``calibration`` and
``rehearsal``.

Loss. Every arm: cross-entropy over the 32 alphabet symbols at the eight answer sites of each context (``studies.p9i.train.alphabet_loss``,
imported). A1 and A1-S add ``lambda * L_addr``; A5-D adds ``mu * L_div``; A2's phase 1 is ``L_addr`` alone (the query projection and the keys train;
values, output projection and gate are frozen), phase 2 the answer loss alone with everything trainable, and the AdamW state is reset at the
switch (a fresh optimizer: moments zero, bias-correction counters restarted). No backbone parameter is trainable in any arm.

Decisions the ADR leaves open (reported): A4's k(t) uses t = the number of updates already taken (the first update reads k_0); A5-C's batch mean
of z is committed to m after the optimizer step, so a forward uses the m of the previous update; the diagnostics' gradient norms of the answer
loss and of the auxiliary loss are taken on the update's own batch with the post-update parameters in a separate backward pass (no state change).

Rehearsal mode writes nothing but binary parameter and optimizer files and ONE record, ``rehearsal.json``, through ``write_rehearsal_record``
(whitelist: time, memory, finiteness, shapes, counts, identity). No loss or accuracy is stored, returned, printed or raised in an exception
message in any mode (there is no progress display); the probes run in rehearsal mode (their cost is part of what is measured) and are discarded.

Imported from P9 and P9-I and called, not copied: ``alphabet_loss``, ``training_stream_for``, ``fact_lut_for``, ``optimizer_state_bytes``,
``rng_state``, ``restore_rng``. Copied with changes (their versions are bound to P9-I's ``Cell``, ``P9IModel`` and record schema): the trainer step,
the snapshot writer and loader, the rehearsal validator (study code P9II), the restoration check.
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
from typing import TYPE_CHECKING, Any, cast

import psutil
import torch
from torch import nn
from torch.optim import Optimizer

from arborlm.engine import optimizer_for as _adamw_for
from arborlm.io import file_sha256
from studies.p9.data import Batch, StudyData, TrainingStream
from studies.p9.train import optimizer_state_bytes, restore_rng, rng_state
from studies.p9i.train import alphabet_loss, fact_lut_for, training_stream_for

from . import core
from .diagnostics import ProbeSet, build_probe, probe_measures, probe_reads
from .model import (
    GROUPS,
    IIMemory,
    P9IIModel,
    a1s_targets,
    address_loss,
    build_model,
    diversity_loss,
    parameter_report,
    set_a2_phase,
    target_injection,
    trainable_counts,
)

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

MODES = ("registered", "calibration", "rehearsal")
AUX_ARMS = ("A1", "A2", "A1-S", "A5-D")
TARGET_ARMS = core.TARGET_ARMS
REHEARSAL_PHASES = ("pre", "post", "k0", "mid", "k8", "main")
__all__ = ["fact_lut_for", "training_stream_for"]


def peak_rss() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


# --- optimizer ----------------------------------------------------------------------------------------------------------
def build_optimizers(model: P9IIModel) -> list[Optimizer]:
    """One AdamW over the parameters that are trainable now (a one-element list, so snapshots keep their list form). For A2 this is called
    again at the switch: the new optimizer is the reset of every moment and counter."""
    named = model.trainable()
    if not named:
        raise ValueError("no trainable parameters")
    return [_adamw_for(nn.ParameterList(p for _, p in named))]


# --- job --------------------------------------------------------------------------------------------------------------------
@dataclass
class TrainJob:
    """Inputs of one cell's training run. ``updates`` is the cell's total number of updates (stage multiplier included); ``unit`` is U (8,192;
    the DRY stage passes a tiny one: it scales U_pre); ``snapshots`` the update counts at which a snapshot is written (the readouts);
    ``rehearsal_phase`` forces one phase of A2 or A4 for the rehearsal; ``max_updates`` caps the run (rehearsal)."""

    cell: core.Cell
    hyper: core.Hyper
    updates: int
    mode: str
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    init_seed: int
    r1_seed: int
    target_seed: int
    stream_seed: int
    unit: int = core.UPDATES
    stage: int = 1
    snapshots: Collection[int] | None = None
    init_snapshot: Path | None = None
    max_updates: int | None = None
    diag_every: int = core.DIAG_EVERY
    rehearsal_phase: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# --- rehearsal whitelist validator (copy of P9-I's with the study code P9II) ---------------------------------------------------
class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key or value outside the whitelist."""


FORBIDDEN_WORDS = ("loss", "acc", "nll", "perplex", "entropy", "margin", "correct", "bits")
REHEARSAL_RECORD_KEYS = frozenset(
    {
        "kind", "schema", "study", "label", "mode", "stage", "arm", "slots", "phase", "identity", "environment", "updates", "wall_seconds",
        "seconds_per_update", "evaluation_wall_seconds", "peak_rss_bytes", "sampled_rss_bytes", "load_average", "loss_finite",
        "parameters_finite", "gradients_finite", "shapes", "parameter_counts", "trainable_parameters", "stored_parameters",
        "optimizer_state_bytes", "trainable_backbone_parameters", "seed_set",
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
    """Nested plain JSON whose names are clean (the environment record)."""
    if isinstance(v, dict):
        return all(_clean_name(k) and _valid_plain(x) for k, x in v.items())
    if isinstance(v, list):
        return all(_valid_plain(x) for x in v)
    return v is None or isinstance(v, str | bool | int) or _is_number(v)


_REHEARSAL_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "kind": lambda v: v in ("rehearsal",),
    "schema": lambda v: v == core.SCHEMA and _is_int(v),
    "study": lambda v: v == core.STUDY,
    "label": lambda v: isinstance(v, str),
    "mode": lambda v: v == "rehearsal",
    "stage": lambda v: isinstance(v, str),
    "arm": lambda v: v in core.ARMS,
    "slots": lambda v: v in core.SLOTS_BY_SIZE,
    "phase": lambda v: v in REHEARSAL_PHASES,
    "identity": _valid_identity,
    "environment": _valid_plain,
    "updates": _is_int,
    "wall_seconds": _is_number,
    "seconds_per_update": _is_number,
    "evaluation_wall_seconds": _is_number,
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


# --- snapshots ---------------------------------------------------------------------------------------------------------------
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


def save_snapshot(out_dir: Path, update: int, model: P9IIModel, optimizers: list[Optimizer], extra: dict[str, Any], *, write_json: bool = True) -> dict[str, str]:
    """``model.pt`` (the whole state, buffers such as A5-C's m included), ``optimizer.pt`` (optimizer, RNG and trainer state) and
    ``snapshot.json`` into ``<out_dir>/snapshots/uNNNNNNN``; returns the file hashes."""
    folder = out_dir / "snapshots" / core.snapshot_stem(update)
    model_hash = _publish(folder / "model.pt", {"update": update, "label": extra.get("label"), "model": model.state_dict()})
    optimizer_hash = _publish(folder / "optimizer.pt", {"update": update, "optimizers": [o.state_dict() for o in optimizers], "rng": extra["rng"], "trainer": extra["trainer"]})
    hashes = {"model_sha256": model_hash, "optimizer_sha256": optimizer_hash}
    if write_json:
        core.write_record(folder / "snapshot.json", {**core.envelope("snapshot"), "label": extra["label"], "update": update, **hashes})
    return hashes


def load_model_state(snapshot_dir: Path, model: P9IIModel) -> int:
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


# --- the trainer ------------------------------------------------------------------------------------------------------------------
def _zero() -> dict[str, float]:
    return dict.fromkeys(GROUPS, 0.0)


class Trainer:
    """One cell's optimization state and its step. ``step(batch)`` runs one update: forward, the arm's loss, backward, per-group gradient norms,
    clip at 1.0, the optimizer step, and the per-update record."""

    def __init__(self, job: TrainJob, model: P9IIModel, probe: ProbeSet) -> None:
        cell = job.cell
        self.job, self.cell, self.model, self.probe = job, cell, model, probe
        self.hyper = job.hyper
        self.arm = cell.arm
        self.slots = cell.slots
        schedule = core.schedule_for(cell.arm, job.stage, job.hyper, cell.slots, job.unit) if cell.arm in core.SCHEDULED_ARMS else core.Schedule(job.updates, None, None, None)
        self.schedule = schedule
        self.phase_override = job.rehearsal_phase
        self.update = 0
        self.phase = 1
        self.all_finite = {"loss": True, "gradients": True, "parameters": True}
        facts = int(job.stream.facts.shape[0])
        self.injection = target_injection(facts, cell.slots, job.target_seed) if cell.arm in TARGET_ARMS else None
        self.anchor: dict[str, Tensor] = {}
        self.seconds_since_record = 0.0
        self.updates_since_record = 0
        self.optimizers: list[Optimizer] = []
        self.configure_phase(self.phase_at(1))

    # -- phases and the read width ------------------------------------------------------------------------------------------------
    def phase_at(self, update: int) -> int:
        """A2: 1 for updates 1..U_pre (L_addr only), 2 afterwards. Every other arm: 1 throughout (a single phase)."""
        if self.arm != "A2":
            return 1
        if self.phase_override == "pre":
            return 1
        if self.phase_override == "post":
            return 2
        return 1 if update <= cast(int, self.schedule.u_pre) else 2

    def read_k(self, t: int) -> int:
        """A4's read width for the update that follows ``t`` updates taken (rehearsal phases fix it)."""
        if self.arm != "A4":
            return core.STANDARD_K
        k0, t_anneal = cast(int, self.schedule.k0), cast(int, self.schedule.t_anneal)
        if self.phase_override == "k0":
            return k0
        if self.phase_override == "mid":
            return core.k_schedule(t_anneal // 2, k0, t_anneal)
        if self.phase_override == "k8":
            return core.STANDARD_K
        return core.k_schedule(t, k0, t_anneal)

    def configure_phase(self, phase: int) -> None:
        """Set the trainable set of ``phase`` and build a fresh optimizer over it (A2's switch: moments zero, counters restarted)."""
        self.phase = phase
        if self.arm == "A2":
            set_a2_phase(self.model, phase)
        self.optimizers = build_optimizers(self.model)
        self.named = self.model.trainable()
        self.params = [p for _, p in self.named]
        self.group = {name: self.model.group_of(name) for name, _ in self.named}

    # -- state --------------------------------------------------------------------------------------------------------------------
    def trainer_state(self) -> dict[str, Any]:
        return {"update": self.update, "phase": self.phase, "anchor": {k: v.clone() for k, v in self.anchor.items()}}

    def snapshot_extra(self) -> dict[str, Any]:
        return {"label": self.cell.label, "rng": rng_state(), "trainer": self.trainer_state()}

    def resume(self, snapshot_dir: Path) -> None:
        """Restore model, optimizer, RNG and trainer state from a snapshot directory (the phase is set before the optimizer state loads)."""
        update = load_model_state(snapshot_dir, self.model)
        self.update = update
        self.configure_phase(self.phase_at(max(update, 1)))  # the phase of the last update taken; a switch due next happens inside step
        state = torch.load(snapshot_dir / "optimizer.pt", weights_only=True, map_location="cpu")
        if len(state["optimizers"]) != len(self.optimizers):
            raise ValueError("snapshot optimizer count differs")
        for optimizer, saved in zip(self.optimizers, state["optimizers"], strict=True):
            optimizer.load_state_dict(saved)
        self.anchor = {k: v.clone() for k, v in state["trainer"]["anchor"].items()}
        restore_rng(state["rng"])

    # -- losses -------------------------------------------------------------------------------------------------------------------
    def targets_for(self, fact_ids: "Tensor", update: int) -> "Tensor | None":
        if self.arm in ("A1", "A2"):
            return cast("Tensor", self.injection)[fact_ids.reshape(-1)]
        if self.arm == "A1-S":
            return a1s_targets(self.job.stream_seed, update, self.slots, int(fact_ids.numel()))
        return None

    def compute_losses(self, tokens: "Tensor", fact_ids: "Tensor", update: int, phase: int) -> tuple["Tensor", dict[str, "Tensor"]]:
        """The loss the arm trains on at ``update`` and its parts: ``answer``, and ``addr`` / ``div`` where the arm has them. The one function the
        step, the gates' gradient-reach test and the diagnostics all call."""
        memory = self.model.addition
        iimemory = memory if isinstance(memory, IIMemory) else None
        if iimemory is not None:
            iimemory.keep_query = self.arm in AUX_ARMS
        try:
            logits, _ = self.model(tokens[:, :-1])
        finally:
            if iimemory is not None:
                iimemory.keep_query = False
        answer = alphabet_loss(logits, tokens)
        parts: dict[str, Tensor] = {"answer": answer}
        if self.arm in ("A1", "A2", "A1-S"):
            q = cast(IIMemory, iimemory).last_query
            targets = self.targets_for(fact_ids, update)
            parts["addr"] = address_loss(cast("Tensor", q), cast(IIMemory, iimemory).keys, cast("Tensor", targets))
        elif self.arm == "A5-D":
            parts["div"] = diversity_loss(cast("Tensor", cast(IIMemory, iimemory).last_query))
        if self.arm in ("A1", "A1-S"):
            total = answer + self.hyper.lambda_ * parts["addr"]
        elif self.arm == "A2":
            total = parts["addr"] if phase == 1 else answer
        elif self.arm == "A5-D":
            total = answer + self.hyper.mu * parts["div"]
        else:
            total = answer
        return total, parts

    # -- one update ------------------------------------------------------------------------------------------------------------------
    def step(self, batch: Batch) -> dict[str, Any]:
        began = time.monotonic()
        update = self.update + 1
        if self.phase_at(update) != self.phase:
            self.configure_phase(self.phase_at(update))  # A2's switch: trainable set changes, AdamW moments and counters reset
        phase = self.phase
        k = self.read_k(self.update)
        self.model.set_read_k(k)
        self.model.train()
        for optimizer in self.optimizers:
            optimizer.zero_grad(set_to_none=True)
        try:
            loss, parts = self.compute_losses(batch.tokens, batch.fact_ids, update, phase)
        finally:
            self.model.set_read_k(core.STANDARD_K)
        for v in (loss, *parts.values()):
            if not bool(torch.isfinite(v)):
                self.all_finite["loss"] = False
                raise ValueError(f"non-finite loss at update {update}")
        grads = torch.autograd.grad(loss, self.params, allow_unused=True)
        for p, g in zip(self.params, grads, strict=True):
            p.grad = torch.zeros_like(p) if g is None else g
        norms = self._group_norms(grads)
        clip = nn.utils.clip_grad_norm_(self.params, core.CLIP_NORM, error_if_nonfinite=False)
        if not bool(torch.isfinite(clip)):
            self.all_finite["gradients"] = False
            raise ValueError(f"non-finite gradient norm at update {update}")
        before = [p.detach().clone() for p in self.params]
        for optimizer in self.optimizers:
            optimizer.step()
        if not all(bool(p.isfinite().all()) for p in self.params):
            self.all_finite["parameters"] = False
            raise ValueError(f"non-finite parameter at update {update}")
        if isinstance(self.model.addition, IIMemory):
            self.model.addition.commit_centre()
        change = self._change(before)
        self.update = update
        seconds = time.monotonic() - began
        self.seconds_since_record += seconds
        self.updates_since_record += 1
        record: dict[str, Any] = {
            "update": update,
            "phase": phase,
            "read_k": k,
            "task_loss": float(parts["answer"].detach()),
            "address_loss": float(parts["addr"].detach()) if "addr" in parts else None,
            "diversity_loss": float(parts["div"].detach()) if "div" in parts else None,
            "grad_norm": norms,
            "param_change_norm": change,
            "clip_total_norm": float(clip),
            "clip_factor": min(1.0, core.CLIP_NORM / (float(clip) + 1e-6)),
            "seconds": seconds,
            "rss_bytes": int(psutil.Process().memory_info().rss),
        }
        return record

    def _group_norms(self, grads: "tuple[Tensor | None, ...]") -> dict[str, float]:
        squares = _zero()
        for (name, _), g in zip(self.named, grads, strict=True):
            if g is not None:
                squares[self.group[name]] += float(g.pow(2).sum())
        return {k: math.sqrt(v) for k, v in squares.items()}

    def _change(self, before: "list[Tensor]") -> dict[str, float]:
        squares = _zero()
        for (name, p), old in zip(self.named, before, strict=True):
            squares[self.group[name]] += float((p.detach() - old).pow(2).sum())
        return {k: math.sqrt(v) for k, v in squares.items()}

    # -- diagnostics (section 8.1; every ``diag_every`` updates) -----------------------------------------------------------------------
    def loss_gradient_norms(self, batch: Batch) -> dict[str, dict[str, float]]:
        """Gradient norms by parameter group of the answer loss alone and of the auxiliary loss alone, on this batch with the current parameters
        (eval mode, separate backward passes; no parameter, optimizer or buffer changes)."""
        was = self.model.training
        self.model.eval()
        out: dict[str, dict[str, float]] = {}
        try:
            self.model.set_read_k(self.read_k(self.update))
            for which in ("answer", "addr", "div"):
                if which != "answer" and not (which == "addr" and self.arm in ("A1", "A2", "A1-S")) and not (which == "div" and self.arm == "A5-D"):
                    continue
                _, parts = self.compute_losses(batch.tokens, batch.fact_ids, self.update, self.phase)
                params = self.params if which == "answer" else [p for n, p in self.named if self.group[n] in ("wq", "keys")]
                names = [n for n, _ in self.named] if which == "answer" else [n for n, _ in self.named if self.group[n] in ("wq", "keys")]
                if not params:
                    continue
                grads = torch.autograd.grad(parts[which], params, allow_unused=True)
                squares = _zero()
                for name, g in zip(names, grads, strict=True):
                    if g is not None:
                        squares[self.group[name]] += float(g.pow(2).sum())
                out[which] = {k: math.sqrt(v) for k, v in squares.items()}
        finally:
            self.model.set_read_k(core.STANDARD_K)
            self.model.train(was)
        return out

    def movement_since_record(self) -> dict[str, float]:
        """Actual displacement (L2 norm) of each group since the previous record; the anchors are refreshed."""
        squares = _zero()
        current = {n: p.detach().clone() for n, p in self.named}
        for name, p in current.items():
            if name in self.anchor:
                squares[self.group[name]] += float((p - self.anchor[name]).pow(2).sum())
        self.anchor = current
        return {k: math.sqrt(v) for k, v in squares.items()}

    def diagnose(self, batch: Batch) -> dict[str, Any]:
        """The record of section 8.1 at the current update."""
        reads = probe_reads(self.model, self.probe)
        keys = getattr(self.model.addition, "keys", None)
        targets = None
        if self.injection is not None:
            targets = self.injection[self.probe.fact]
        measures = probe_measures(reads, self.probe, keys=None if keys is None else keys.detach(), targets=targets, read_k=self.read_k(self.update), centred_arm=self.arm == "A5-C")
        per = self.seconds_since_record / max(1, self.updates_since_record)
        self.seconds_since_record, self.updates_since_record = 0.0, 0
        record: dict[str, Any] = {
            "update": self.update,
            "phase": self.phase,
            "arm": self.arm,
            "mean_update_seconds": per,
            "peak_rss_bytes": peak_rss(),
            "gradient_norms_by_loss": self.loss_gradient_norms(batch),
            "movement_since_previous_record": self.movement_since_record(),
            **measures,
        }
        return record


# --- the cell run -------------------------------------------------------------------------------------------------------------------
@dataclass
class Executed:
    """A finished (or in-memory) run: the record plus the live state."""

    record: dict[str, Any]
    model: P9IIModel
    trainer: Trainer
    updates: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


def check_job_seeds(job: TrainJob) -> None:
    if job.mode not in MODES:
        raise ValueError(f"unknown mode {job.mode!r}")
    core.check_seed_set(job.mode, job.data.seeds.name)


def snapshot_marks(job: TrainJob, start: int, last: int) -> list[int]:
    marks = sorted(set(job.snapshots)) if job.snapshots is not None else [job.updates]
    return [m for m in marks if start < m <= last]


def initial_centre_rows(model: P9IIModel, stream: TrainingStream) -> "Tensor":
    """z at initialization over the first 16 training batches: ``[16 * 128, 16]`` (A5-C's m is initialised to its mean)."""
    rows = []
    with torch.no_grad():
        was = model.training
        model.eval()
        for u in range(1, core.CENTRE_INIT_BATCHES + 1):
            tokens = stream.batch(u).tokens
            z = model.answer_z(model.embed_block0(tokens[:, : core.INPUT_LENGTH]), tokens)
            rows.append(cast("Tensor", z).reshape(-1, core.KEY_WIDTH))
        model.train(was)
    return torch.cat(rows)


def run_job(job: TrainJob) -> Executed:
    """Run a job and return the live state. ``train_cell`` is this plus its record on disk."""
    check_job_seeds(job)
    cell, mode = job.cell, job.mode
    rehearsal = mode == "rehearsal"
    started = time.monotonic()
    model = build_model(cell.arm, cell.slots, job.init_seed, job.backbone, r1_seed=job.r1_seed)
    facts = int(job.stream.facts.shape[0])
    probe = build_probe(job.data, facts)
    trainer = Trainer(job, model, probe)
    if job.init_snapshot is not None:
        trainer.resume(job.init_snapshot)
    elif cell.arm == "A5-C":
        cast(IIMemory, model.addition).init_centre(initial_centre_rows(model, job.stream))
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
                hashes = save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), write_json=not rehearsal)
                snapshot_hashes[str(update)] = hashes["model_sha256"]
    except Exception as exc:
        status, reason = "failed", type(exc).__name__ + ": " + str(exc)
        if not rehearsal:
            _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start)
        raise
    finally:
        for log in (update_log, diag_log):
            if log is not None:
                log.flush()
                os.fsync(log.fileno())
                log.close()
    record_out = _write_train_record(job, trainer, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start)
    return Executed(record_out, model, trainer, kept, kept_diag)


def _write_train_record(job: TrainJob, trainer: Trainer, report: dict[str, Any], started: float, contexts: int, sampled_rss: int, marks: list[int], snapshot_hashes: dict[str, str], status: str, reason: str | None, last: int, start: int) -> dict[str, Any]:
    cell = job.cell
    wall = time.monotonic() - started
    done = trainer.update - start
    exposures = job.stream.exposures(trainer.update)
    identity = core.code_identity()
    schedule = trainer.schedule
    record: dict[str, Any] = {
        **core.envelope("train"),
        "label": cell.label,
        "arm": cell.arm,
        "stage": cell.stage,
        "slots": cell.slots,
        "draw": cell.draw,
        "seed_index": cell.seed_index,
        "facts": int(job.stream.facts.shape[0]),
        "init_seed": job.init_seed,
        "target_seed": job.target_seed,
        "stream_seed": job.stream_seed,
        "mode": job.mode,
        "unit_updates": job.unit,
        "matched_updates": job.updates,
        "run_updates": last,
        "snapshots": marks,
        "hyper": job.hyper.as_json(),
        "schedule": {"total": schedule.total, "u_pre": schedule.u_pre, "t_anneal": schedule.t_anneal, "k0": schedule.k0},
        "examples": contexts,
        "answer_site_exposures": contexts * core.ANSWER_SITES_PER_CONTEXT,
        "unique_facts": int((exposures > 0).sum()),
        "exposure_per_fact_min": int(exposures.min()),
        "exposure_per_fact_max": int(exposures.max()),
        "exposure_per_fact_mean": float(exposures.float().mean()),
        "exposure_per_fact_analytical": core.exposures_per_fact(trainer.update, int(job.stream.facts.shape[0])),
        "trainable_parameters": report["trainable"],
        "trainable_parameters_by_phase": {"1": report["trainable"]} if cell.arm != "A2" else {"1": _a2_count(trainer, 1), "2": _a2_count(trainer, 2)},
        "trainable_backbone_parameters": report["trainable_backbone"],
        "stored_parameters": report["stored"],
        "parameters_by_group": dict(report["by_group"]),
        "optimizer_state_bytes": optimizer_state_bytes(trainer.optimizers),
        "wall_seconds": wall,
        "peak_rss_bytes": peak_rss(),
        "update_log": "" if job.mode == "rehearsal" else "updates.jsonl",
        "diagnostics_log": "" if job.mode == "rehearsal" else "diagnostics.jsonl",
        "snapshot_sha256": snapshot_hashes,
        "identity": identity,
        "environment": core.environment(),
        "status": status,
        "reason": reason,
        "seed_set": job.data.seeds.name,
        **job.extra,
    }
    if job.mode == "rehearsal":
        rehearsal = {
            **core.envelope("rehearsal"),
            "label": cell.label,
            "mode": "rehearsal",
            "stage": "rehearse",
            "arm": cell.arm,
            "slots": cell.slots,
            "phase": job.rehearsal_phase or "main",
            "identity": identity,
            "environment": record["environment"],
            "updates": done,
            "wall_seconds": wall,
            "seconds_per_update": wall / done if done else 0.0,
            "peak_rss_bytes": record["peak_rss_bytes"],
            "sampled_rss_bytes": sampled_rss,
            "load_average": list(os.getloadavg()),
            "loss_finite": trainer.all_finite["loss"],
            "parameters_finite": trainer.all_finite["parameters"],
            "gradients_finite": trainer.all_finite["gradients"],
            "shapes": {n: list(p.shape) for n, p in trainer.named},
            "parameter_counts": dict(report["by_group"]),
            "trainable_parameters": report["trainable"],
            "stored_parameters": report["stored"],
            "optimizer_state_bytes": record["optimizer_state_bytes"],
            "trainable_backbone_parameters": report["trainable_backbone"],
            "seed_set": job.data.seeds.name,
        }
        write_rehearsal_record(job.out_dir / "rehearsal.json", rehearsal)
    else:
        core.write_record(job.out_dir / "train.json", core.jsonable(record))
    return record


def _a2_count(trainer: Trainer, phase: int) -> int:
    saved = [(p, p.requires_grad) for p in trainer.model.addition.parameters()]
    try:
        set_a2_phase(trainer.model, phase)
        return sum(trainable_counts(trainer.model).values())
    finally:
        for p, flag in saved:
            p.requires_grad_(flag)


def train_cell(job: TrainJob) -> dict[str, Any]:
    """Train one cell for ``job.updates`` updates (or up to ``max_updates``), writing ``updates.jsonl``, ``diagnostics.jsonl``, the snapshots and
    ``train.json`` (rehearsal: binary snapshots and ``rehearsal.json`` only). Constant learning rate. Deterministic on CPU/FP32 (G4). On a
    failure ``train.json`` is written with status ``failed`` (not in rehearsal mode) and the exception re-raised."""
    return run_job(job).record


# --- gates: restoration and gradient reach -------------------------------------------------------------------------------------------
def _state_tensors(run: Executed) -> dict[str, "Tensor"]:
    model = run.model
    out = {f"param:{n}": p.detach() for n, p in model.named_parameters()}
    out.update({f"buffer:{n}": b for n, b in model.addition.named_buffers()})
    names = {id(p): n for n, p in model.named_parameters()}
    for i, optimizer in enumerate(run.trainer.optimizers):
        for param, state in optimizer.state.items():
            for k, v in state.items():
                if torch.is_tensor(v):
                    out[f"optim{i}:{names[id(param)]}:{k}"] = v
    for k, v in run.trainer.anchor.items():
        out[f"anchor:{k}"] = v
    return out


def checkpoint_restoration_check(job: TrainJob, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot, restore (model, optimizer, RNG, trainer state) and
    continue; every tensor must be bit-identical. Runs in ``<out_dir>/restore_check/{straight,first,resumed}``. A2's switch, A5-C's m and A4's
    schedule are all inside the compared state."""
    root = job.out_dir / "restore_check"

    def sub(name: str, **kw: Any) -> TrainJob:
        return TrainJob(**{**job.__dict__, "out_dir": root / name, **kw})

    total = 2 * split_update
    straight = run_job(sub("straight", updates=job.updates, max_updates=total, snapshots=()))
    run_job(sub("first", updates=job.updates, max_updates=split_update, snapshots=(split_update,)))
    folder = root / "first" / "snapshots" / core.snapshot_stem(split_update)
    resumed = run_job(sub("resumed", updates=job.updates, max_updates=total, snapshots=(), init_snapshot=folder))
    a, b = _state_tensors(straight), _state_tensors(resumed)
    mismatches = sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k]))
    return {"identical": not mismatches, "mismatches": mismatches, "split_update": split_update, "updates": total, "tensors_compared": len(a), "resumed_from_update": split_update}


def gradient_reach(job: TrainJob, tokens: "Tensor", fact_ids: "Tensor", which: str = "training", *, phase: int | None = None, update: int = 1) -> dict[str, Any]:
    """One backward pass of ``which`` in {training, answer, addr, div} on ``tokens [B, 64]`` with their fact ids, through the same loss function
    the trainer uses. Returns ``reached`` (every trainable parameter -> it received a finite non-zero gradient), ``trainable``, ``stray``
    (parameters that are not trainable yet carry a gradient: must be empty) and ``buffer_gradients`` (buffers with a gradient: must be empty)."""
    model = build_model(job.cell.arm, job.cell.slots, job.init_seed, job.backbone, r1_seed=job.r1_seed, seed_rng=False)
    probe = build_probe(job.data, int(job.stream.facts.shape[0]))
    trainer = Trainer(job, model, probe)
    if job.cell.arm == "A5-C":
        cast(IIMemory, model.addition).init_centre(initial_centre_rows(model, job.stream))
    chosen = trainer.phase if phase is None else phase
    if job.cell.arm == "A2":
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


def configure() -> None:
    """Single-thread deterministic CPU (``arborlm.engine.configure_cpu``), tolerant of a second call."""
    from arborlm.engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:  # the inter-op thread count can be set once per process
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


def lines_of(path: Path) -> list[dict[str, Any]]:
    """The records of a JSONL log (updates or diagnostics); ``jsonable``'s string markers are left as they are."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
