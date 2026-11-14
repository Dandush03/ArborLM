# ruff: noqa: E501
"""P9I training (ADR-0017 Part I, sections I.4, I.5 and 6.3): alphabet-only cross-entropy at answer
sites, matched updates U for every cell, optimizer groups, snapshots with optimizer state, the training
diagnostics of ADR-0017 section 6.3, and the modes ``registered``, ``calibration`` and ``rehearsal``.

Loss: cross-entropy over the 32 alphabet symbols (bytes 0x40-0x5F) at the eight answer sites of each
context, for every arm. Scoring (``evaluate``) is the most probable alphabet symbol, ties wrong: loss and
scoring use the same output set. Not comparable with P4-P8 / ADR-0017's 256-way loss.

Optimizer: ONE AdamW (lr 0.003, betas (0.9, 0.999), eps 1e-8, no weight decay, built by
``arborlm.engine.optimizer_for`` exactly as P9's ``adamw`` cells; ADR-0017 section 5.1) over ALL trainable
parameters of every arm (key and value tables, projections, gate, interface parameters, dense adapters, the
BB block-0 attention). No row-lazy optimizer exists in Part I. One
gradient clip at 1.0 over all trainable parameters together, before any step.

Definitions fixed here where the ADR leaves a measurement open (as P9's ``train``; reported):

* per-update groups ``keys_selected`` / ``keys_candidate`` / ``keys_untouched`` are defined by the
  answer-site queries of the update's batch (hard top-8 / top-64 minus top-8 / all other rows). The
  per-row movement split uses the row's actual task gradient (non-zero row).
* movement of a row on an update = the L2 norm of the row's change; ``had gradient`` = non-zero gradient row.
* ``dead_slots`` = slots never hard-selected at an answer site in updates 1..u; snapshot diagnostics are
  computed on the update's own batch with the post-update parameters (no gradient, no state change).

Rehearsal mode writes nothing but binary parameter and optimizer files and ONE record,
``rehearsal.json``, through ``write_rehearsal_record`` (whitelist: time, memory, finiteness, shapes,
counts, identity). No loss or accuracy is stored, returned, printed or raised in an exception message in
any mode (there is no progress display).

Imported from P9 and called, not copied: ``optimizer_state_bytes``, ``rng_state``,
``restore_rng``, the answer-site margin helpers. Copied with changes (P9's versions are bound to P9's
``Cell`` / ``P9Model`` / ``Objective`` / record schema): the trainer step, the snapshot writer and
loader (the loader must not demand a frozen block 0 for the BB arms), the rehearsal validator
(study code P9I), the restoration check.
"""

import json
import math
import os
import resource
import sys
import tempfile
import time
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import psutil
import torch
from torch import nn
from torch.nn import functional as F
from torch.optim import Optimizer

from arborlm.engine import optimizer_for as _adamw_for
from arborlm.io import file_sha256
from studies.p9.data import StudyData, TrainingStream, identifier_lut
from studies.p9.data import training_stream_for as _p9_training_stream_for
from studies.p9.objective import (
    answer_site_margins,
    answer_site_rows,
    answer_site_selected,
    soft_mass_outside_top8,
)
from studies.p9.train import optimizer_state_bytes, restore_rng, rng_state

from . import core
from .core import Cell
from .model import GROUPS, P9IModel, build_model, parameter_report, set_trainable

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

MODES = ("registered", "calibration", "rehearsal")
MARGIN_QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
MARGIN_KEYS = ("q00", "q05", "q25", "q50", "q75", "q95", "q100")
VOCAB = 256
SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
ALPHABET_INDEX = torch.tensor(core.ALPHABET, dtype=torch.int64)
NORM_GROUPS = ("keys_selected", "keys_candidate", "keys_untouched", "values", "projections", "interface", "dense", "backbone_attention")


# --- losses -----------------------------------------------------------------------------------------------
def alphabet_loss(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Mean cross-entropy over the 32 alphabet symbols at the answer sites: ``logits [B, 63, 256]``
    against ``tokens[:, 1:][:, sites]`` (alphabet bytes, mapped to 0..31). Scalar float32."""
    if tokens.ndim != 2 or tokens.shape[1] != core.CONTEXT_BYTES:
        raise ValueError("expected tokens [B, 64]")
    inside = logits[:, SITES][..., ALPHABET_INDEX]  # [B, 8, 32]
    targets = tokens[:, 1:][:, SITES] - core.ALPHABET_BASE
    if bool(((targets < 0) | (targets >= core.ALPHABET_SIZE)).any()):
        raise ValueError("an answer target lies outside the alphabet")
    return F.cross_entropy(inside.reshape(-1, core.ALPHABET_SIZE), targets.reshape(-1))


def answer_site_loss_256(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Descriptive only: 256-way cross-entropy at the answer sites (ADR-0017's / P4-P8's loss)."""
    targets = tokens[:, 1:][:, SITES]
    return F.cross_entropy(logits[:, SITES].reshape(-1, VOCAB), targets.reshape(-1))


# --- data of a cell (P9's schedule on the first ``facts`` facts) ---------------------------------------------------
def training_stream_for(data: StudyData, facts: int) -> TrainingStream:
    """The training schedule over facts ``0 .. facts-1`` of the main world: exactly what P9's
    ``data.training_stream_for`` returns for a non-Lane-D cell with that many facts (called through a
    stand-in cell so that no private P9 helper is imported)."""
    stand_in = SimpleNamespace(is_lane_d=False, facts=facts)
    return _p9_training_stream_for(data, cast(Any, stand_in))


def fact_lut_for(data: StudyData, facts: int) -> "Tensor":
    """R2 slot table of the first ``facts`` facts (``data.identifier_lut``)."""
    return identifier_lut(data.facts, torch.arange(facts))


# --- optimizers -----------------------------------------------------------------------------------------------
def build_optimizers(model: P9IModel) -> list[Optimizer]:
    """One AdamW over all trainable parameters (a one-element list, so snapshots and restoration keep
    their list form)."""
    named = model.trainable()
    if not named:
        raise ValueError("no trainable parameters")
    return [_adamw_for(nn.ParameterList(p for _, p in named))]


# --- job ----------------------------------------------------------------------------------------------------------
@dataclass
class TrainJob:
    """Inputs of one cell's training run. ``updates`` is U (matched across cells); ``snapshots`` the update
    counts at which a snapshot is written (default ``(U,)``; the calibration uses
    ``core.CALIBRATION_SNAPSHOTS``). ``init_snapshot`` starts from a snapshot directory (with
    ``restore_optimizer``: optimizer, trackers, movement and counter too). ``max_updates`` caps the run
    (rehearsal)."""

    cell: Cell
    updates: int
    mode: str
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    init_seed: int
    r1_seed: int
    fact_lut: "Tensor | None" = None
    snapshots: Collection[int] | None = None
    init_snapshot: Path | None = None
    restore_optimizer: bool = False
    max_updates: int | None = None


# --- rehearsal whitelist validator (copy of P9's with the study code P9I) -------------------------------------------
class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key or value outside the whitelist."""


FORBIDDEN_WORDS = ("loss", "acc", "nll", "perplex", "entropy", "margin", "correct", "bits")
REHEARSAL_RECORD_KEYS = frozenset(
    {
        "kind", "schema", "study", "label", "mode", "stage", "identity", "updates", "wall_seconds",
        "seconds_per_update", "peak_rss_bytes", "sampled_rss_bytes", "load_average", "loss_finite",
        "parameters_finite", "gradients_finite", "shapes", "parameter_counts", "trainable_parameters",
        "stored_parameters", "optimizer_state_bytes", "trainable_backbone_parameters",
    }
)  # fmt: skip


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: object) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)


def _clean_name(name: object) -> bool:
    return isinstance(name, str) and not any(w in name.lower() for w in FORBIDDEN_WORDS)


def _valid_shapes(v: object) -> bool:
    return (
        isinstance(v, dict)
        and all(_clean_name(k) for k in v)
        and all(isinstance(s, list) and all(_is_int(d) for d in s) for s in v.values())
    )


def _valid_counts(v: object) -> bool:
    return isinstance(v, dict) and all(_clean_name(k) and _is_int(c) for k, c in v.items())


def _valid_identity(v: object) -> bool:
    return isinstance(v, dict) and all(_clean_name(k) and isinstance(s, str) for k, s in v.items())


_REHEARSAL_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "kind": lambda v: v == "rehearsal",
    "schema": lambda v: v == core.SCHEMA and _is_int(v),
    "study": lambda v: v == core.STUDY,
    "label": lambda v: isinstance(v, str),
    "mode": lambda v: v == "rehearsal",
    "stage": lambda v: isinstance(v, str),
    "identity": _valid_identity,
    "updates": _is_int,
    "wall_seconds": _is_number,
    "seconds_per_update": _is_number,
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
}
if set(_REHEARSAL_VALIDATORS) != set(REHEARSAL_RECORD_KEYS):
    raise ImportError("rehearsal validators must cover exactly REHEARSAL_RECORD_KEYS")


def validate_rehearsal_record(record: dict[str, Any]) -> None:
    """Raise unless every key is whitelisted and every value has the whitelisted type and shape
    (finiteness keys are booleans; nested names must not look like a loss, accuracy, entropy or margin)."""
    for key, value in record.items():
        if key not in REHEARSAL_RECORD_KEYS:
            raise RehearsalRecordError(f"key not allowed in a rehearsal record: {key!r}")
        if not _REHEARSAL_VALIDATORS[key](value):
            raise RehearsalRecordError(f"value of {key!r} is not of the whitelisted form")
    for key in ("kind", "schema", "study", "mode"):
        if key not in record:
            raise RehearsalRecordError(f"rehearsal record lacks {key!r}")


def write_rehearsal_record(path: Path, record: dict[str, Any]) -> None:
    """The only writer of rehearsal-mode records."""
    validate_rehearsal_record(record)
    core.write_record(path, record)


# --- snapshots ----------------------------------------------------------------------------------------------------
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


def save_snapshot(
    out_dir: Path,
    update: int,
    model: P9IModel,
    optimizers: list[Optimizer],
    extra: dict[str, Any],
    *,
    write_json: bool = True,
) -> dict[str, str]:
    """Write ``model.pt`` (the whole state, including the BB block-0 attention), ``optimizer.pt``,
    ``movement.pt`` and ``snapshot.json`` into ``<out_dir>/snapshots/uNNNNNNN``; returns the file hashes.
    ``write_json=False`` (the rehearsal path) writes only the binary files."""
    folder = out_dir / "snapshots" / core.snapshot_stem(update)
    model_hash = _publish(folder / "model.pt", {"update": update, "label": extra.get("label"), "model": model.state_dict()})
    optimizer_hash = _publish(
        folder / "optimizer.pt",
        {"update": update, "optimizers": [o.state_dict() for o in optimizers], "rng": extra["rng"], "trackers": extra["trackers"]},
    )
    movement_hash = _publish(folder / "movement.pt", dict(extra["movement"]))
    hashes = {"model_sha256": model_hash, "optimizer_sha256": optimizer_hash, "movement_sha256": movement_hash}
    if write_json:
        diag = extra["diagnostics"]
        record = {
            **core.envelope("snapshot"),
            "label": extra["label"],
            "update": update,
            **hashes,
            "margin_8_9_quantiles": diag["margin_8_9_quantiles"],
            "soft_mass_outside_top8": diag["soft_mass_outside_top8"],
            "dead_slots": diag["dead_slots"],
            "keys_entered_top64_after_0": diag["keys_entered_top64_after_0"],
        }
        core.write_record(folder / "snapshot.json", record)
    return hashes


def load_snapshot(snapshot_dir: Path, model: P9IModel, optimizers: list[Optimizer] | None = None) -> dict[str, Any]:
    """Load a snapshot into ``model`` (and ``optimizers``); returns ``update`` (and, with optimizers,
    ``rng``, ``trackers``, ``movement``). The state must have the model's keys, shapes, dtypes and finite
    values; every backbone tensor that is frozen in this model must equal the live frozen one (the BB
    attention tensors are the trained ones and are not compared)."""
    payload = torch.load(snapshot_dir / "model.pt", weights_only=True, map_location="cpu")
    tensors = payload["model"]
    expected = model.state_dict()
    if tensors.keys() != expected.keys():
        raise ValueError("snapshot model keys differ from the model's")
    live = dict(model.named_parameters())
    for name, tensor in expected.items():
        saved = tensors[name]
        if saved.shape != tensor.shape or saved.dtype != tensor.dtype:
            raise ValueError(f"snapshot tensor {name} has a different shape or dtype")
        if not bool(torch.isfinite(saved).all()):
            raise ValueError(f"snapshot tensor {name} is not finite")
        trainable = name in live and live[name].requires_grad
        if name.startswith("backbone.") and not trainable and not torch.equal(saved, tensor):
            raise ValueError("snapshot backbone differs from the live frozen backbone")
    model.load_state_dict(tensors, strict=True)
    if optimizers is None:
        return {"update": int(payload["update"])}
    state = torch.load(snapshot_dir / "optimizer.pt", weights_only=True, map_location="cpu")
    if len(state["optimizers"]) != len(optimizers):
        raise ValueError("snapshot optimizer count differs")
    for optimizer, saved_state in zip(optimizers, state["optimizers"], strict=True):
        optimizer.load_state_dict(saved_state)
    movement = torch.load(snapshot_dir / "movement.pt", weights_only=True, map_location="cpu")
    return {"update": int(payload["update"]), "rng": state["rng"], "trackers": state["trackers"], "movement": movement}


# --- the training step with the ADR 6.3 instrumentation ---------------------------------------------------------------
def _zero_groups() -> dict[str, float]:
    return {g: 0.0 for g in NORM_GROUPS}


class Trainer:
    """One cell's optimization state and its step. ``step(tokens)`` runs one update on ``tokens [16, 64]``
    and returns the per-update record: forward, alphabet loss at answer sites, backward, per-group
    gradient norms, clip at 1.0, optimizer steps, per-group and per-row bookkeeping."""

    def __init__(self, cell: Cell, model: P9IModel, optimizers: list[Optimizer]) -> None:
        self.cell = cell
        self.model = model
        self.optimizers = optimizers
        self.update = 0
        self.named = model.trainable()
        self.params = [p for _, p in self.named]
        self.group = {name: model.group_of(name) for name, _ in self.named}
        self.slots = model.slots
        self.has_table = {leaf: any(n.endswith("." + leaf) for n, _ in self.named) for leaf in ("keys", "values")}
        n = self.slots
        self.movement: dict[str, Tensor] = {}
        if self.has_table["keys"]:
            self.movement["key_with"] = torch.zeros(n)
            self.movement["key_without"] = torch.zeros(n)
        if self.has_table["values"]:
            self.movement["value_with"] = torch.zeros(n)
            self.movement["value_without"] = torch.zeros(n)
        self.ever_selected = torch.zeros(n, dtype=torch.bool)
        self.ever_top64 = torch.zeros(n, dtype=torch.bool)
        self.top64_at_zero: Tensor | None = None
        self.all_finite = {"loss": True, "gradients": True, "parameters": True}

    # -- state --------------------------------------------------------------------------------------------------
    def tracker_state(self) -> dict[str, Any]:
        return {
            "ever_selected": self.ever_selected.clone(),
            "ever_top64": self.ever_top64.clone(),
            "top64_at_zero": None if self.top64_at_zero is None else self.top64_at_zero.clone(),
            "update": self.update,
        }

    def load_state(self, extra: dict[str, Any]) -> None:
        trackers = extra["trackers"]
        self.ever_selected = trackers["ever_selected"].clone()
        self.ever_top64 = trackers["ever_top64"].clone()
        zero = trackers["top64_at_zero"]
        self.top64_at_zero = None if zero is None else zero.clone()
        if set(extra["movement"]) != set(self.movement):
            raise ValueError("snapshot movement tables do not match this model")
        self.movement = {k: v.clone() for k, v in extra["movement"].items()}
        self.update = int(extra["update"])
        restore_rng(extra["rng"])

    def snapshot_extra(self, tokens: "Tensor") -> dict[str, Any]:
        return {
            "label": self.cell.label,
            "rng": rng_state(),
            "trackers": self.tracker_state(),
            "movement": self.movement,
            "diagnostics": self.snapshot_diagnostics(tokens),
        }

    # -- bookkeeping -----------------------------------------------------------------------------------------------
    def _masks(self, selection: Any) -> tuple["Tensor", "Tensor", "Tensor"] | None:
        if selection is None or selection.candidate_ids is None:
            return None
        n = self.slots
        chosen = torch.zeros(n, dtype=torch.bool)
        chosen[answer_site_selected(selection).reshape(-1)] = True
        candidate = torch.zeros(n, dtype=torch.bool)
        candidate[answer_site_rows(selection)[1].reshape(-1)] = True
        candidate &= ~chosen
        return chosen, candidate, ~(chosen | candidate)

    def _group_norms(self, grads: Iterable["Tensor | None"], masks: tuple["Tensor", "Tensor", "Tensor"] | None) -> dict[str, float]:
        squares = _zero_groups()
        for (name, _), g in zip(self.named, grads, strict=True):
            if g is None:
                continue
            group = self.group[name]
            if group == "keys":
                rows = g.pow(2).sum(-1)
                if masks is None:
                    squares["keys_untouched"] += float(rows.sum())
                else:
                    squares["keys_selected"] += float(rows[masks[0]].sum())
                    squares["keys_candidate"] += float(rows[masks[1]].sum())
                    squares["keys_untouched"] += float(rows[masks[2]].sum())
            else:
                squares[group] += float(g.pow(2).sum())
        return {k: math.sqrt(v) for k, v in squares.items()}

    def snapshot_diagnostics(self, tokens: "Tensor") -> dict[str, Any]:
        """ADR 6.3 per-snapshot measurements on ``tokens`` (the update's own batch), no gradient."""
        diag: dict[str, Any] = {"margin_8_9_quantiles": {}, "soft_mass_outside_top8": 0.0, "dead_slots": 0, "keys_entered_top64_after_0": 0}
        if not self.has_table["values"]:
            return diag
        diag["dead_slots"] = int(self.slots - int(self.ever_selected.sum()))
        if self.top64_at_zero is not None:
            diag["keys_entered_top64_after_0"] = int((self.ever_top64 & ~self.top64_at_zero).sum())
        if self.model.spec.rung == "R2":
            return diag
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                _, selection = self.model(tokens[:, :-1])
                if selection is not None:
                    margins = answer_site_margins(selection)
                    q = torch.quantile(margins, torch.tensor(MARGIN_QUANTILES))
                    diag["margin_8_9_quantiles"] = {
                        **{k: float(v) for k, v in zip(MARGIN_KEYS, q, strict=True)},
                        "mean": float(margins.mean()),
                    }
                    diag["soft_mass_outside_top8"] = soft_mass_outside_top8(selection)
        finally:
            self.model.train(was_training)
        return diag

    # -- one update ----------------------------------------------------------------------------------------------------
    def step(self, tokens: "Tensor") -> dict[str, Any]:
        update = self.update + 1
        self.model.train()
        for optimizer in self.optimizers:
            optimizer.zero_grad(set_to_none=True)
        logits, selection = self.model(tokens[:, :-1])
        loss = alphabet_loss(logits, tokens)
        if not bool(torch.isfinite(loss)):
            self.all_finite["loss"] = False
            raise ValueError(f"non-finite task loss at update {update}")
        with torch.no_grad():
            loss256 = float(answer_site_loss_256(logits, tokens))
        masks = self._masks(selection)
        if selection is not None and selection.candidate_ids is not None:
            self._track(masks, first=self.top64_at_zero is None)
        elif selection is not None:  # R2: one dedicated slot per fact, no candidates
            self.ever_selected[selection.selected[selection.selected >= 0]] = True
        grads = torch.autograd.grad(loss, self.params, allow_unused=True)
        for p, g in zip(self.params, grads, strict=True):
            p.grad = torch.zeros_like(p) if g is None else g
        norms = self._group_norms(grads, masks)
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
        change = self._change(grads, before, masks)
        self.update = update
        return {
            "update": update,
            "task_loss": float(loss),
            "answer_loss_256": loss256,
            "grad_norm": norms,
            "param_change_norm": change,
            "clip_total_norm": float(clip),
        }

    def _track(self, masks: tuple["Tensor", "Tensor", "Tensor"] | None, *, first: bool) -> None:
        if masks is None:
            return
        chosen, candidate, _ = masks
        top64 = chosen | candidate
        if first:
            self.top64_at_zero = top64.clone()
        self.ever_selected |= chosen
        self.ever_top64 |= top64

    def _change(self, task_grads: Iterable["Tensor | None"], before: list["Tensor"], masks: tuple["Tensor", "Tensor", "Tensor"] | None) -> dict[str, float]:
        squares = _zero_groups()
        for (name, p), old, task_grad in zip(self.named, before, list(task_grads), strict=True):
            delta = p.detach() - old
            group = self.group[name]
            leaf = name.rsplit(".", 1)[-1]
            if group in ("keys", "values") and leaf in ("keys", "values"):
                rows = delta.pow(2).sum(-1)
                had = torch.zeros(self.slots, dtype=torch.bool) if task_grad is None else (task_grad != 0).any(dim=-1)
                moved = rows.sqrt()
                prefix = "key" if leaf == "keys" else "value"
                self.movement[f"{prefix}_with"] += moved * had
                self.movement[f"{prefix}_without"] += moved * ~had
                if leaf == "keys" and masks is not None:
                    squares["keys_selected"] += float(rows[masks[0]].sum())
                    squares["keys_candidate"] += float(rows[masks[1]].sum())
                    squares["keys_untouched"] += float(rows[masks[2]].sum())
                elif leaf == "keys":
                    squares["keys_untouched"] += float(rows.sum())
                else:
                    squares["values"] += float(rows.sum())
            else:
                squares[group] += float(delta.pow(2).sum())
        return {k: math.sqrt(v) for k, v in squares.items()}


# --- the cell run -----------------------------------------------------------------------------------------------------------
@dataclass
class Executed:
    """A finished (or in-memory) run: the record plus the live state."""

    record: dict[str, Any]
    model: P9IModel
    optimizers: list[Optimizer]
    trainer: Trainer
    updates: list[dict[str, Any]] = field(default_factory=list)


def peak_rss() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


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
    cell, mode = job.cell, job.mode
    rehearsal = mode == "rehearsal"
    started = time.monotonic()
    model = build_model(cell.arm, cell.slots, job.init_seed, job.backbone, fact_lut=job.fact_lut, r1_seed=job.r1_seed)
    optimizers = build_optimizers(model)
    trainer = Trainer(cell, model, optimizers)
    if job.init_snapshot is not None:
        extra = load_snapshot(job.init_snapshot, model, optimizers if job.restore_optimizer else None)
        if job.restore_optimizer:
            trainer.load_state(extra)
    start = trainer.update
    last = job.updates if job.max_updates is None else min(job.updates, job.max_updates)
    marks = snapshot_marks(job, start, last)
    report = parameter_report(model)
    job.out_dir.mkdir(parents=True, exist_ok=True)
    log = None if rehearsal else (job.out_dir / "updates.jsonl").open("x", encoding="utf-8")
    sampled_rss = 0
    process = psutil.Process()
    contexts = 0
    snapshot_hashes: dict[str, str] = {}
    kept: list[dict[str, Any]] = []
    status, reason = "completed", None
    try:
        for update in range(start + 1, last + 1):
            tokens = job.stream.batch(update).tokens
            record = trainer.step(tokens)
            contexts += int(tokens.shape[0])
            sampled_rss = max(sampled_rss, int(process.memory_info().rss))
            if log is not None:
                log.write(json.dumps(record, allow_nan=False, sort_keys=True) + "\n")
                log.flush()
                kept.append(record)
            if update in marks:
                extra = trainer.snapshot_extra(tokens)
                hashes = save_snapshot(job.out_dir, update, trainer.model, optimizers, extra, write_json=not rehearsal)
                snapshot_hashes[str(update)] = hashes["model_sha256"]
    except Exception as exc:
        status, reason = "failed", type(exc).__name__ + ": " + str(exc)
        if not rehearsal:
            _write_train_record(job, trainer, optimizers, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start)
        raise
    finally:
        if log is not None:
            log.flush()
            os.fsync(log.fileno())
            log.close()
    record_out = _write_train_record(job, trainer, optimizers, report, started, contexts, sampled_rss, marks, snapshot_hashes, status, reason, last, start)
    return Executed(record_out, model, optimizers, trainer, kept)


def _write_train_record(
    job: TrainJob,
    trainer: Trainer,
    optimizers: list[Optimizer],
    report: Any,
    started: float,
    contexts: int,
    sampled_rss: int,
    marks: list[int],
    snapshot_hashes: dict[str, str],
    status: str,
    reason: str | None,
    last: int,
    start: int,
) -> dict[str, Any]:
    cell = job.cell
    wall = time.monotonic() - started
    done = trainer.update - start
    exposures = job.stream.exposures(trainer.update)
    identity = dict(core.code_identity())
    record: dict[str, Any] = {
        **core.envelope("train"),
        "label": cell.label,
        "block": cell.block,
        "arm": cell.arm,
        "slots": cell.slots,
        "facts": int(job.stream.facts.shape[0]),
        "parent": list(cell.parent),
        "seed": cell.seed,
        "init_seed": job.init_seed,
        "mode": job.mode,
        "matched_updates": job.updates,
        "run_updates": last,
        "snapshots": marks,
        "examples": contexts,
        "tokens": contexts * core.INPUT_LENGTH,
        "answer_site_exposures": contexts * core.ANSWER_SITES_PER_CONTEXT,
        "unique_facts": int((exposures > 0).sum()),
        "exposure_per_fact_min": int(exposures.min()),
        "exposure_per_fact_max": int(exposures.max()),
        "exposure_per_fact_mean": float(exposures.float().mean()),
        "trainable_parameters": report.trainable,
        "trainable_backbone_parameters": report.trainable_backbone,
        "stored_parameters": report.stored,
        "parameters_by_group": dict(report.by_group),
        "interface_extra_parameters": report.interface_extra,
        "dense_hidden": report.dense_hidden,
        "optimizer_state_bytes": optimizer_state_bytes(optimizers),
        "wall_seconds": wall,
        "peak_rss_bytes": peak_rss(),
        "update_log": "" if job.mode == "rehearsal" else "updates.jsonl",
        "snapshot_sha256": snapshot_hashes,
        "identity": identity,
        "status": status,
        "reason": reason,
    }
    if job.mode == "rehearsal":
        rehearsal = {
            **core.envelope("rehearsal"),
            "label": cell.label,
            "mode": "rehearsal",
            "stage": "rehearse",
            "identity": identity,
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
            "parameter_counts": dict(report.by_group),
            "trainable_parameters": report.trainable,
            "stored_parameters": report.stored,
            "optimizer_state_bytes": record["optimizer_state_bytes"],
            "trainable_backbone_parameters": report.trainable_backbone,
        }
        write_rehearsal_record(job.out_dir / "rehearsal.json", rehearsal)
    else:
        core.write_record(job.out_dir / "train.json", record)
    return record


def train_cell(job: TrainJob) -> dict[str, Any]:
    """Train one cell for ``job.updates`` updates (or up to ``max_updates``), writing ``updates.jsonl``,
    the snapshots and ``train.json`` (rehearsal: binary snapshots and ``rehearsal.json`` only). Constant
    learning rate, so a snapshot is a valid shorter run. Deterministic on CPU/FP32 (G4). On a failure
    ``train.json`` is written with status ``failed`` (not in rehearsal mode) and the exception re-raised."""
    return run_job(job).record


# --- gates --------------------------------------------------------------------------------------------------------------
def _state_tensors(run: Executed) -> dict[str, "Tensor"]:
    out = {f"param:{n}": p.detach() for n, p in run.model.named_parameters()}
    names = {id(p): n for n, p in run.model.named_parameters()}
    for i, optimizer in enumerate(run.optimizers):
        for param, state in optimizer.state.items():
            for k, v in state.items():
                if torch.is_tensor(v):
                    out[f"optim{i}:{names[id(param)]}:{k}"] = v
    for k, v in run.trainer.movement.items():
        out[f"movement:{k}"] = v
    for k in ("ever_selected", "ever_top64"):
        out[f"tracker:{k}"] = getattr(run.trainer, k)
    if run.trainer.top64_at_zero is not None:
        out["tracker:top64_at_zero"] = run.trainer.top64_at_zero
    return out


def checkpoint_restoration_check(job: TrainJob, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot, restore
    (model, optimizer, RNG, trackers, movement) and continue; every tensor must be bit-identical. Runs in
    ``<out_dir>/restore_check/{straight,first,resumed}``."""
    root = job.out_dir / "restore_check"

    def sub(name: str, **kw: Any) -> TrainJob:
        return TrainJob(**{**job.__dict__, "out_dir": root / name, **kw})

    total = 2 * split_update
    straight = run_job(sub("straight", updates=total, max_updates=total, snapshots=()))
    first = run_job(sub("first", updates=total, max_updates=split_update, snapshots=(split_update,)))
    folder = root / "first" / "snapshots" / core.snapshot_stem(split_update)
    del first
    resumed = run_job(
        sub("resumed", updates=total, max_updates=total, snapshots=(), init_snapshot=folder, restore_optimizer=True)
    )
    a, b = _state_tensors(straight), _state_tensors(resumed)
    mismatches = sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k]))
    return {
        "identical": not mismatches,
        "mismatches": mismatches,
        "split_update": split_update,
        "updates": total,
        "tensors_compared": len(a),
        "resumed_from_update": split_update,
    }


def gradient_reach(model: P9IModel, tokens: "Tensor") -> dict[str, Any]:
    """One backward pass of the alphabet loss on ``tokens [B, 64]``. Returns ``reached`` (every trainable
    parameter name -> it received a finite, non-zero gradient), ``trainable`` (the names) and ``stray``
    (parameters that are not trainable yet carry a gradient: must be empty)."""
    model.zero_grad(set_to_none=True)
    logits, _ = model(tokens[:, :-1])
    alphabet_loss(logits, tokens).backward()  # type: ignore[no-untyped-call]
    reached: dict[str, bool] = {}
    stray: list[str] = []
    for name, p in model.named_parameters():
        if p.requires_grad:
            reached[name] = p.grad is not None and bool(p.grad.isfinite().all()) and bool((p.grad != 0).any())
        elif p.grad is not None:
            stray.append(name)
    model.zero_grad(set_to_none=True)
    return {"reached": reached, "trainable": sorted(reached), "stray": stray}


def configure() -> None:
    """Single-thread deterministic CPU (``arborlm.engine.configure_cpu``), tolerant of a second call."""
    from arborlm.engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:  # the inter-op thread count can be set once per process
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


__all__ = [
    "GROUPS",
    "MODES",
    "Executed",
    "RehearsalRecordError",
    "TrainJob",
    "Trainer",
    "alphabet_loss",
    "build_optimizers",
    "checkpoint_restoration_check",
    "gradient_reach",
    "load_snapshot",
    "run_job",
    "save_snapshot",
    "set_trainable",
    "train_cell",
    "validate_rehearsal_record",
    "write_rehearsal_record",
]
