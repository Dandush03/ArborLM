# ruff: noqa: E501
"""P9 training (package I2): answer-site loss, AdamW and row-lazy Adam, the training loop, snapshots
with optimizer state, the instrumentation of ADR 6.3, and the modes ``registered``, ``calibration``
and ``rehearsal``.

Specification: ADR-0017 section 5.1 (loss at answer sites only; AdamW lr 0.003, no weight decay, clip
1.0), 5.5 (batch of 16 contexts, constant learning rate, snapshots), 5.6 (row-lazy Adam on the key and
value tables only, lr 0.012; projections, gate and router use AdamW), 6.3 (per-update and per-row
instrumentation), 12 step 5 (rehearsal writes only through a whitelist validator).

Disk layout (``core.cell_dir`` and ``core.snapshot_dir``): ``train.json`` (``core.TrainRecord``),
``updates.jsonl`` (one ``core.UpdateRecord`` per update), and per snapshot ``model.pt``,
``optimizer.pt`` (optimizer state, objective state, update counter, RNG state, trackers),
``movement.pt`` (``key_with``, ``key_without``, ``value_with``, ``value_without``: ``[N] float32``
cumulative parameter movement on updates where the row did / did not have a task gradient) and
``snapshot.json`` (``core.SnapshotRecord``).

Modes: ``registered`` (the run; needs a freeze, enforced by the job manager), ``calibration`` and
``rehearsal`` (rehearsal-namespace data only). In ``rehearsal`` mode nothing but binary parameter and
optimizer files and ONE record, ``rehearsal.json``, written by ``write_rehearsal_record`` (allowed keys:
``core.REHEARSAL_RECORD_KEYS``: time, RSS, finiteness, shapes), reaches the disk; no loss or accuracy is
stored, returned in a record, printed or raised in an exception message in any mode (there is no
progress display).

Definitions fixed here where the ADR leaves a measurement open (reported to the lead):

* per-update parameter groups ``keys_selected`` / ``keys_candidate`` / ``keys_untouched`` are defined by
  the answer-site queries of the update's batch (hard top-8 / top-64 minus top-8 / all other rows). Under
  R0 a row selected only at a non-answer position is "untouched" by this definition although it may carry
  a task gradient; the per-row movement split uses the row's actual task gradient instead.
* movement of a row on an update = the L2 norm of the row's change; "had a task gradient" = the row of the
  task-loss gradient (before any regularizer and before clipping) has a non-zero entry.
* ``dead_slots`` = slots never hard-selected at an answer site in updates 1..u; ``keys_entered_top64_after_0``
  = slots that appeared in an answer-site top-64 in updates 1..u but not in the answer-site top-64 of the
  first batch evaluated at the initial parameters (update 0).
* snapshot diagnostics are computed on the update's own training batch with the post-update parameters
  (no gradient, no state change); ``margin_8_9_quantiles`` has keys ``q00 q05 q25 q50 q75 q95 q100 mean``.
* ``examples`` = training contexts, ``tokens`` = contexts x 63 input tokens.
"""

import argparse
import json
import math
import os
import random
import resource
import sys
import tempfile
import time
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import psutil
import torch
from torch import nn
from torch.nn import functional as F
from torch.optim import Optimizer

from arborlm.engine import optimizer_for as _adamw_for
from arborlm.io import file_sha256

from . import core
from .core import Cell, TrainRecord, UpdateRecord
from .data import StudyData, TrainingStream
from .model import (
    PARAMETER_GROUP_NAMES,
    P9Model,
    Selection,
    build_model,
    parameter_counts,
    set_trainable,
    trainable_groups,
)
from .objective import (
    Objective,
    answer_site_margins,
    answer_site_rows,
    answer_site_selected,
    soft_mass_outside_top8,
)

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

MODES = ("registered", "calibration", "rehearsal")
MARGIN_QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
MARGIN_KEYS = ("q00", "q05", "q25", "q50", "q75", "q95", "q100")
VOCAB = 256
SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)


# --- losses ----------------------------------------------------------------------------------------------
def answer_site_loss(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Mean cross-entropy at answer sites only (ADR 5.1, every arm): ``logits [B, 63, 256]`` against
    targets ``tokens[:, 1:]`` at input positions 8r+6 (target byte 8r+7), scalar float32."""
    if tokens.ndim != 2 or tokens.shape[1] != core.CONTEXT_BYTES:
        raise ValueError("expected tokens [B, 64]")
    targets = tokens[:, 1:][:, SITES]
    return F.cross_entropy(logits[:, SITES].reshape(-1, VOCAB), targets.reshape(-1))


def all_position_loss(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Mean cross-entropy over all 63 targets; descriptive only, never optimized."""
    return F.cross_entropy(logits.reshape(-1, VOCAB), tokens[:, 1:].reshape(-1))


# --- row-lazy Adam -----------------------------------------------------------------------------------------
class RowLazyAdam(Optimizer):
    """Adam with per-row moments for 2-D tables: a row is updated only on updates where its gradient
    is non-zero, with bias correction by the row's own update count (ADR 5.6). Used for ``keys`` and
    ``values`` of A10 at learning rate ``core.LAZY_LEARNING_RATE``; betas and eps as AdamW. The update of
    a row is torch Adam's (no weight decay): ``m = b1 m + (1-b1) g``, ``v = b2 v + (1-b2) g^2``,
    ``p -= (lr / (1 - b1^t)) m / (sqrt(v) / sqrt(1 - b2^t) + eps)`` with t the row's own count."""

    def __init__(
        self,
        params: Iterable["torch.nn.Parameter"],
        lr: float,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ) -> None:
        super().__init__(params, {"lr": lr, "betas": betas, "eps": eps})
        for group in self.param_groups:
            for p in group["params"]:
                if p.ndim != 2:
                    raise ValueError("RowLazyAdam handles 2-D tables only")

    def step(self, closure: Callable[[], float] | None = None) -> float | None:  # type: ignore[override]
        loss = None
        if closure is not None:
            with torch.enable_grad():  # type: ignore[no-untyped-call]
                loss = closure()
        with torch.no_grad():
            self._step()
        return loss

    def _step(self) -> None:
        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            lr, eps = group["lr"], group["eps"]
            for p in group["params"]:
                grad = p.grad
                if grad is None:
                    continue
                state = self.state[p]
                if not state:
                    state["row_step"] = torch.zeros(p.shape[0], dtype=torch.int64)
                    state["exp_avg"] = torch.zeros_like(p)
                    state["exp_avg_sq"] = torch.zeros_like(p)
                rows = (grad != 0).any(dim=1).nonzero().squeeze(1)
                if rows.numel() == 0:
                    continue
                g = grad.index_select(0, rows)
                m = state["exp_avg"].index_select(0, rows).mul_(beta1).add_(g, alpha=1.0 - beta1)
                v = (
                    state["exp_avg_sq"]
                    .index_select(0, rows)
                    .mul_(beta2)
                    .addcmul_(g, g, value=1.0 - beta2)
                )
                steps = state["row_step"].index_select(0, rows) + 1
                state["exp_avg"].index_copy_(0, rows, m)
                state["exp_avg_sq"].index_copy_(0, rows, v)
                state["row_step"].index_copy_(0, rows, steps)
                t = steps.to(torch.float64)
                bias1 = 1.0 - torch.pow(torch.tensor(beta1, dtype=torch.float64), t)
                bias2 = 1.0 - torch.pow(torch.tensor(beta2, dtype=torch.float64), t)
                step_size = (lr / bias1).to(torch.float32).unsqueeze(1)
                denom = (v.sqrt() / bias2.sqrt().to(torch.float32).unsqueeze(1)).add_(eps)
                update = p.index_select(0, rows).addcdiv_(m * step_size, denom, value=-1.0)
                p.index_copy_(0, rows, update)


def _trainable(model: P9Model) -> list[tuple[str, nn.Parameter]]:
    return [(n, p) for n, p in model.named_parameters() if p.requires_grad]


def build_optimizer(model: P9Model, cell: Cell) -> list[Optimizer]:
    """Optimizers of the cell: one AdamW over all trainable parameters (lr 0.003, betas (0.9, 0.999),
    eps 1e-8, weight decay 0) for ``adamw`` cells; for ``lazy`` cells a ``RowLazyAdam`` over keys and
    values plus an AdamW over the remaining trainable parameters. Gradient clipping at 1.0 is applied
    over all trainable parameters together by the loop, before any step. The AdamW is built by
    ``arborlm.engine.optimizer_for`` exactly as P5's (``p5_model.optimizer_for``)."""
    named = _trainable(model)
    if not named:
        raise ValueError("no trainable parameters")
    if cell.optimizer == "adamw":
        return [_adamw_for(nn.ParameterList(p for _, p in named))]
    if model.spec.arch == "dense":
        raise ValueError("the row-lazy optimizer is defined for key and value tables only")
    tables = [p for n, p in named if n.rsplit(".", 1)[-1] in core.LAZY_TABLES]
    rest = [p for n, p in named if n.rsplit(".", 1)[-1] not in core.LAZY_TABLES]
    optimizers: list[Optimizer] = [
        RowLazyAdam(tables, lr=core.LAZY_LEARNING_RATE, betas=core.BETAS, eps=core.ADAM_EPS)
    ]
    if rest:
        optimizers.append(_adamw_for(nn.ParameterList(rest)))
    return optimizers


def optimizer_state_bytes(optimizers: Collection[Optimizer]) -> int:
    total = 0
    for optimizer in optimizers:
        for state in optimizer.state.values():
            total += sum(t.numel() * t.element_size() for t in state.values() if torch.is_tensor(t))
    return total


# --- job ---------------------------------------------------------------------------------------------------
@dataclass
class TrainJob:
    """Inputs of one cell's training run.

    ``stream`` comes from ``data.training_stream_for`` (Lane D phase B arms pass the B stream).
    ``init_snapshot`` (a snapshot directory) starts from its model parameters and, if
    ``restore_optimizer`` is True, its optimizer and objective state, trackers, movement and update
    counter (the checkpoint-restoration test); False gives the fresh optimizer of every Lane D phase-B
    arm (ADR 8.5). ``trainable_groups`` restricts training (``("keys", "values")`` for memory-only).
    ``max_updates`` caps the run (rehearsal): it is the absolute index of the last update.
    ``out_dir`` is ``core.cell_dir(run_dir, cell.label)``.

    Additions to the stub: ``init_seed`` / ``r1_seed`` / ``branch_seed`` (None = ``cell.seed`` and the
    registered ``core.DATA_SEEDS`` values) for rehearsal-namespace runs.
    """

    cell: Cell
    exposure: int
    mode: str
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    init_snapshot: Path | None = None
    restore_optimizer: bool = False
    trainable_groups: Collection[str] | None = None
    max_updates: int | None = None
    snapshot_updates: Collection[int] | None = None
    fact_lut: "Tensor | None" = None
    init_seed: int | None = None
    r1_seed: int | None = None
    branch_seed: int | None = None


# --- rehearsal whitelist validator ----------------------------------------------------------------------------
class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key outside ``core.REHEARSAL_RECORD_KEYS``."""


_FORBIDDEN_WORDS = ("loss", "acc", "nll", "perplex", "entropy", "margin", "correct", "bits")


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: object) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)


def _clean_name(name: object) -> bool:
    return isinstance(name, str) and not any(w in name.lower() for w in _FORBIDDEN_WORDS)


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
}
if set(_REHEARSAL_VALIDATORS) != set(core.REHEARSAL_RECORD_KEYS):
    raise ImportError("rehearsal validators must cover exactly core.REHEARSAL_RECORD_KEYS")


def validate_rehearsal_record(record: dict[str, Any]) -> None:
    """Raise ``RehearsalRecordError`` unless every key is whitelisted and every value has the type and
    shape of its whitelist entry (finiteness keys must be booleans; nested names must not look like a
    loss, accuracy, entropy or margin)."""
    for key, value in record.items():
        if key not in core.REHEARSAL_RECORD_KEYS:
            raise RehearsalRecordError(f"key not allowed in a rehearsal record: {key!r}")
        if not _REHEARSAL_VALIDATORS[key](value):
            raise RehearsalRecordError(f"value of {key!r} is not of the whitelisted form")
    for key in ("kind", "schema", "study", "mode"):
        if key not in record:
            raise RehearsalRecordError(f"rehearsal record lacks {key!r}")


def write_rehearsal_record(path: Path, record: dict[str, Any]) -> None:
    """The only writer of rehearsal-mode records: refuses any key outside the whitelist (time, RSS,
    finiteness, shapes) and any non-finite-flag value that looks like a loss or accuracy."""
    validate_rehearsal_record(record)
    core.write_record(path, record)


# --- snapshots -----------------------------------------------------------------------------------------------
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


def rng_state() -> dict[str, Any]:
    return {"python": random.getstate(), "torch": torch.get_rng_state()}


def restore_rng(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])


def save_snapshot(
    out_dir: Path,
    update: int,
    model: P9Model,
    optimizers: list[Optimizer],
    extra: dict[str, Any],
    *,
    write_json: bool = True,
) -> dict[str, str]:
    """Write ``model.pt``, ``optimizer.pt``, ``movement.pt`` (from ``extra``) and ``snapshot.json`` of
    update ``update`` into ``<out_dir>/snapshots/uNNNNNNN``; returns the file hashes. ``out_dir`` is the
    cell directory. ``extra`` carries ``objective`` (state), ``rng``, ``trackers``, ``movement`` (the
    accumulators) and ``diagnostics`` (the ``SnapshotRecord`` measurements). ``write_json=False`` (the
    rehearsal path) writes only the binary files."""
    folder = out_dir / "snapshots" / core.snapshot_stem(update)
    model_hash = _publish(
        folder / "model.pt",
        {"update": update, "label": extra.get("label"), "model": model.state_dict()},
    )
    optimizer_hash = _publish(
        folder / "optimizer.pt",
        {
            "update": update,
            "optimizers": [o.state_dict() for o in optimizers],
            "objective": extra["objective"],
            "rng": extra["rng"],
            "trackers": extra["trackers"],
        },
    )
    movement_hash = _publish(folder / "movement.pt", dict(extra["movement"]))
    hashes = {
        "model_sha256": model_hash,
        "optimizer_sha256": optimizer_hash,
        "movement_sha256": movement_hash,
    }
    if write_json:
        diag = extra["diagnostics"]
        record = {
            **core.envelope("snapshot"),
            "label": extra["label"],
            "update": update,
            **hashes,
            "margin_8_9_quantiles": diag["margin_8_9_quantiles"],
            "soft_mass_outside_top8": diag["soft_mass_outside_top8"],
            "hinge_active": diag["hinge_active"],
            "dead_slots": diag["dead_slots"],
            "keys_entered_top64_after_0": diag["keys_entered_top64_after_0"],
        }
        core.write_record(folder / "snapshot.json", record)
    return hashes


def load_snapshot(
    snapshot_dir: Path,
    model: P9Model,
    optimizers: list[Optimizer] | None = None,
) -> dict[str, Any]:
    """Load a snapshot into ``model`` (and ``optimizers`` when given); returns the ``extra`` payload
    (``update`` only for a model-only load; with ``optimizers`` also ``objective``, ``rng``,
    ``trackers`` and ``movement``). Used by evaluation (model only) and by the restoration test
    (bit-identical continuation). The model state must have the model's keys and shapes, finite
    values and a backbone equal to the live frozen backbone."""
    payload = torch.load(snapshot_dir / "model.pt", weights_only=True, map_location="cpu")
    tensors = payload["model"]
    expected = model.state_dict()
    if tensors.keys() != expected.keys():
        raise ValueError("snapshot model keys differ from the model's")
    for name, tensor in expected.items():
        saved = tensors[name]
        if saved.shape != tensor.shape or saved.dtype != tensor.dtype:
            raise ValueError(f"snapshot tensor {name} has a different shape or dtype")
        if not bool(torch.isfinite(saved).all()):
            raise ValueError(f"snapshot tensor {name} is not finite")
        if name.startswith("backbone.") and not torch.equal(saved, tensor):
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
    return {
        "update": int(payload["update"]),
        "objective": state["objective"],
        "rng": state["rng"],
        "trackers": state["trackers"],
        "movement": movement,
    }


# --- the training step with ADR 6.3 instrumentation ------------------------------------------------------------
def _zero_groups() -> dict[str, float]:
    return {g: 0.0 for g in core.PARAM_GROUPS}


class Trainer:
    """One cell's optimization state and its step. ``step(tokens)`` runs one update on ``tokens
    [B, 64] int64`` (B = 16, or 32 with replay) and returns the ``UpdateRecord`` of ADR 6.3. The step
    is: forward, task loss at answer sites, objective terms, gradients of the task loss and of each
    regularizer term separately (``autograd.grad`` on the one graph), summed into ``.grad``, clipped
    together at 1.0, stepped by the optimizers, then the per-group and per-row bookkeeping."""

    def __init__(
        self,
        cell: Cell,
        model: P9Model,
        optimizers: list[Optimizer],
        objective: Objective,
    ) -> None:
        self.cell = cell
        self.model = model
        self.optimizers = optimizers
        self.objective = objective
        self.update = 0
        self.named = _trainable(model)
        self.params = [p for _, p in self.named]
        self.group = {name: g for g, items in trainable_groups(model).items() for name, _ in items}
        self.has_keys = "addition.keys" in dict(self.named)
        self.has_values = "addition.values" in dict(self.named)
        n = model.spec.slots
        self.slots = n
        self.movement: dict[str, Tensor] = {}
        if model.spec.arch != "dense":
            if self.has_keys:
                self.movement["key_with"] = torch.zeros(n)
                self.movement["key_without"] = torch.zeros(n)
            if self.has_values:
                self.movement["value_with"] = torch.zeros(n)
                self.movement["value_without"] = torch.zeros(n)
        self.ever_selected = torch.zeros(n, dtype=torch.bool)
        self.ever_top64 = torch.zeros(n, dtype=torch.bool)
        self.top64_at_zero: Tensor | None = None
        self.all_finite = {"loss": True, "gradients": True, "parameters": True}

    # -- state ------------------------------------------------------------------------------------------
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
        self.objective.load_state_dict(extra["objective"])
        restore_rng(extra["rng"])

    def snapshot_extra(self, tokens: "Tensor") -> dict[str, Any]:
        return {
            "label": self.cell.label,
            "objective": self.objective.state_dict(),
            "rng": rng_state(),
            "trackers": self.tracker_state(),
            "movement": self.movement,
            "diagnostics": self.snapshot_diagnostics(tokens),
        }

    # -- bookkeeping -------------------------------------------------------------------------------------
    def _masks(self, selection: Selection | None) -> tuple["Tensor", "Tensor", "Tensor"] | None:
        if selection is None or selection.candidate_ids is None:
            return None
        n = self.slots
        chosen = torch.zeros(n, dtype=torch.bool)
        chosen[answer_site_selected(selection).reshape(-1)] = True
        candidate = torch.zeros(n, dtype=torch.bool)
        candidate[answer_site_rows(selection)[1].reshape(-1)] = True
        candidate &= ~chosen
        return chosen, candidate, ~(chosen | candidate)

    def _group_norms(
        self,
        grads: Iterable["Tensor | None"],
        masks: tuple["Tensor", "Tensor", "Tensor"] | None,
    ) -> dict[str, float]:
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
        """ADR 6.3 per-snapshot measurements on ``tokens`` (the update's own batch), no gradient, no
        state change."""
        n = self.slots
        diag: dict[str, Any] = {
            "margin_8_9_quantiles": {},
            "soft_mass_outside_top8": 0.0,
            "hinge_active": {
                "usage": bool(self.objective.last_diagnostics["hinge_usage_active"]),
                "coaccess": bool(self.objective.last_diagnostics["hinge_coaccess_active"]),
            },
            "dead_slots": 0,
            "keys_entered_top64_after_0": 0,
        }
        if self.model.spec.arch == "dense":
            return diag
        diag["dead_slots"] = int(n - int(self.ever_selected.sum()))
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

    # -- one update --------------------------------------------------------------------------------------
    def step(self, tokens: "Tensor") -> UpdateRecord:
        update = self.update + 1
        self.model.train()
        for optimizer in self.optimizers:
            optimizer.zero_grad(set_to_none=True)
        logits, selection = self.model(tokens[:, :-1])
        task = answer_site_loss(logits, tokens)
        if not bool(torch.isfinite(task)):
            self.all_finite["loss"] = False
            raise ValueError(f"non-finite task loss at update {update}")
        with torch.no_grad():
            all_loss = float(all_position_loss(logits, tokens))
        result = self.objective(task, selection)
        terms = list(self.objective.last_terms.items())
        masks = self._masks(selection)
        if selection is not None and selection.candidate_ids is not None:
            self._track(selection, masks, first=self.top64_at_zero is None)
        elif selection is not None:  # R2: one dedicated slot per fact, no candidates
            self.ever_selected[selection.selected[selection.selected >= 0]] = True

        params = self.params
        task_grads = torch.autograd.grad(task, params, retain_graph=bool(terms), allow_unused=True)
        term_grads: dict[str, tuple[Tensor | None, ...]] = {}
        for i, (name, term) in enumerate(terms):
            term_grads[name] = torch.autograd.grad(
                term, params, retain_graph=i < len(terms) - 1, allow_unused=True
            )
        for k, p in enumerate(params):
            g = task_grads[k]
            total = torch.zeros_like(p) if g is None else g
            if term_grads:
                total = total.clone()
                for grads in term_grads.values():
                    if grads[k] is not None:
                        total.add_(cast("Tensor", grads[k]))
            p.grad = total
        record_norms = {
            "task": self._group_norms(task_grads, masks),
            "usage": self._group_norms(term_grads.get("usage", [None] * len(params)), masks),
            "coaccess": self._group_norms(term_grads.get("coaccess", [None] * len(params)), masks),
        }
        clip = nn.utils.clip_grad_norm_(params, core.CLIP_NORM, error_if_nonfinite=False)
        if not bool(torch.isfinite(clip)):
            self.all_finite["gradients"] = False
            raise ValueError(f"non-finite gradient norm at update {update}")
        before = [p.detach().clone() for p in params]
        for optimizer in self.optimizers:
            optimizer.step()
        if not all(bool(p.isfinite().all()) for p in params):
            self.all_finite["parameters"] = False
            raise ValueError(f"non-finite parameter at update {update}")
        change = self._change(task_grads, before, masks)
        self.update = update
        diag = result.diagnostics
        return UpdateRecord(
            update=update,
            task_loss=result.task,
            all_position_loss=all_loss,
            usage_penalty=result.usage_penalty,
            coaccess_penalty=result.coaccess_penalty,
            grad_norm_task=record_norms["task"],
            grad_norm_usage=record_norms["usage"],
            grad_norm_coaccess=record_norms["coaccess"],
            param_change_norm=change,
            clip_total_norm=float(clip),
            hinge_usage_active=bool(diag["hinge_usage_active"]),
            hinge_coaccess_active=bool(diag["hinge_coaccess_active"]),
            usage_entropy_soft=cast("float | None", diag["usage_entropy_soft"]),
            usage_entropy_hard=cast("float | None", diag["usage_entropy_hard"]),
        )

    def _track(
        self,
        selection: Selection,
        masks: tuple["Tensor", "Tensor", "Tensor"] | None,
        *,
        first: bool,
    ) -> None:
        if masks is None:
            return
        chosen, candidate, _ = masks
        top64 = chosen | candidate
        if first:
            self.top64_at_zero = top64.clone()
        self.ever_selected |= chosen
        self.ever_top64 |= top64

    def _change(
        self,
        task_grads: Iterable["Tensor | None"],
        before: list["Tensor"],
        masks: tuple["Tensor", "Tensor", "Tensor"] | None,
    ) -> dict[str, float]:
        squares = _zero_groups()
        grads = list(task_grads)
        for (name, p), old, task_grad in zip(self.named, before, grads, strict=True):
            delta = p.detach() - old
            group = self.group[name]
            leaf = name.rsplit(".", 1)[-1]
            if leaf in ("keys", "values"):
                rows = delta.pow(2).sum(-1)
                had = (
                    torch.zeros(self.slots, dtype=torch.bool)
                    if task_grad is None
                    else (task_grad != 0).any(dim=-1)
                )
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


# --- the cell run --------------------------------------------------------------------------------------------------
@dataclass
class Executed:
    """A finished (or in-memory) run: the record plus the live state, for the restoration check."""

    record: TrainRecord
    model: P9Model
    optimizers: list[Optimizer]
    trainer: Trainer
    objective: Objective
    updates: list[UpdateRecord] = field(default_factory=list)


def _peak_rss() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _check_seeds(job: TrainJob) -> None:
    if job.mode not in MODES:
        raise ValueError(f"unknown mode {job.mode!r}")
    seeds = getattr(job.data, "seeds", None)
    name = getattr(seeds, "name", None)
    if name is None:
        return
    if (job.mode == "registered") != (name == "registered"):
        raise ValueError(f"mode {job.mode!r} cannot use the {name!r} seed set")


def _batch_tokens(stream: TrainingStream, update: int) -> "Tensor":
    batch = stream.batch(update)
    if getattr(batch, "replay_tokens", None) is not None:
        return torch.cat([batch.tokens, cast("Tensor", batch.replay_tokens)])
    return batch.tokens


def run_job(job: TrainJob) -> Executed:
    """Run a job and return the live state. ``train_cell`` is this plus its record."""
    _check_seeds(job)
    cell, mode = job.cell, job.mode
    rehearsal = mode == "rehearsal"
    started = time.monotonic()
    model = build_model(
        cell,
        job.backbone,
        fact_lut=job.fact_lut,
        init_seed=job.init_seed,
        r1_seed=job.r1_seed,
        branch_seed=job.branch_seed,
    )
    if job.trainable_groups is not None:
        set_trainable(model, job.trainable_groups)
    optimizers = build_optimizer(model, cell)
    objective = Objective(cell)
    trainer = Trainer(cell, model, optimizers, objective)
    if job.init_snapshot is not None:
        extra = load_snapshot(
            job.init_snapshot, model, optimizers if job.restore_optimizer else None
        )
        if job.restore_optimizer:
            trainer.load_state(extra)
    start = trainer.update
    last = core.run_updates(cell, job.exposure)
    if job.max_updates is not None:
        last = min(last, job.max_updates)
    marks = (
        sorted(set(job.snapshot_updates))
        if job.snapshot_updates is not None
        else list(core.snapshots(cell, job.exposure))
    )
    marks = [m for m in marks if start < m <= last]
    counts = parameter_counts(model)
    job.out_dir.mkdir(parents=True, exist_ok=True)
    log = None if rehearsal else (job.out_dir / "updates.jsonl").open("x", encoding="utf-8")
    kept: list[UpdateRecord] = []
    sampled_rss = 0
    process = psutil.Process()
    contexts = 0
    snapshot_hashes: dict[str, str] = {}
    status, reason = "completed", None
    try:
        for update in range(start + 1, last + 1):
            tokens = _batch_tokens(job.stream, update)
            update_record = trainer.step(tokens)
            contexts += int(tokens.shape[0])
            sampled_rss = max(sampled_rss, int(process.memory_info().rss))
            if log is not None:
                log.write(json.dumps(update_record, allow_nan=False, sort_keys=True) + "\n")
                log.flush()
                kept.append(update_record)
            if update in marks:
                extra = trainer.snapshot_extra(tokens)
                hashes = save_snapshot(
                    job.out_dir, update, trainer.model, optimizers, extra, write_json=not rehearsal
                )
                snapshot_hashes[str(update)] = hashes["model_sha256"]
    except Exception as exc:
        status, reason = "failed", type(exc).__name__ + ": " + str(exc)
        if not rehearsal:
            _write_train_record(
                job,
                trainer,
                optimizers,
                counts,
                started,
                contexts,
                sampled_rss,
                marks,
                snapshot_hashes,
                status,
                reason,
                last,
                start,
            )
        raise
    finally:
        if log is not None:
            log.flush()
            os.fsync(log.fileno())
            log.close()
    record = _write_train_record(
        job,
        trainer,
        optimizers,
        counts,
        started,
        contexts,
        sampled_rss,
        marks,
        snapshot_hashes,
        status,
        reason,
        last,
        start,
    )
    return Executed(record, model, optimizers, trainer, objective, kept)


def _write_train_record(
    job: TrainJob,
    trainer: Trainer,
    optimizers: list[Optimizer],
    counts: Any,
    started: float,
    contexts: int,
    sampled_rss: int,
    marks: list[int],
    snapshot_hashes: dict[str, str],
    status: str,
    reason: str | None,
    last: int,
    start: int,
) -> TrainRecord:
    cell = job.cell
    wall = time.monotonic() - started
    done = trainer.update - start
    exposures = job.stream.exposures(trainer.update)
    unique = int((exposures > 0).sum())
    lo, hi = int(exposures.min()), int(exposures.max())
    record = cast(
        TrainRecord,
        dict(
            **core.envelope("train"),
            label=cell.label,
            index=cell.index,
            block=cell.block,
            mode=job.mode,
            exposure=job.exposure,
            matched_updates=core.updates(cell, job.exposure),
            run_updates=core.run_updates(cell, job.exposure) if job.max_updates is None else last,
            snapshots=marks,
            examples=contexts,
            tokens=contexts * core.INPUT_LENGTH,
            unique_facts=unique,
            exposure_per_fact_min=lo,
            exposure_per_fact_max=hi,
            trainable_parameters=counts.trainable,
            stored_parameters=counts.stored,
            initialized_slots=counts.initialized_slots,
            optimizer_state_bytes=optimizer_state_bytes(optimizers),
            lambda_u=core.lambda_u_for(cell),
            lambda_c=core.lambda_c_for(cell),
            wall_seconds=wall,
            peak_rss_bytes=_peak_rss(),
            update_log="" if job.mode == "rehearsal" else "updates.jsonl",
            snapshot_sha256=snapshot_hashes,
            identity=core.code_identity(),
            status=status,
            reason=reason,
        ),
    )
    if job.mode == "rehearsal":
        rehearsal = {
            **core.envelope("rehearsal"),
            "label": cell.label,
            "mode": "rehearsal",
            "stage": "rehearse",
            "identity": dict(record["identity"]),
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
            "parameter_counts": dict(counts.by_group),
            "trainable_parameters": counts.trainable,
            "stored_parameters": counts.stored,
            "optimizer_state_bytes": record["optimizer_state_bytes"],
        }
        write_rehearsal_record(job.out_dir / "rehearsal.json", rehearsal)
    else:
        core.write_record(job.out_dir / "train.json", record)
    return record


def train_cell(job: TrainJob) -> TrainRecord:
    """Train one cell for ``core.run_updates`` updates (or up to ``max_updates``), writing
    ``updates.jsonl``, the snapshots of ``core.snapshots`` (or ``snapshot_updates``) and ``train.json``
    (rehearsal: binary snapshots and ``rehearsal.json`` only). Constant learning rate, so a snapshot is
    a valid shorter run. Deterministic on CPU/FP32 (G4). On a failure ``train.json`` is written with
    status ``failed`` (not in rehearsal mode) and the exception is re-raised."""
    return run_job(job).record


# --- gates ---------------------------------------------------------------------------------------------------------
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
    for name, state in (("floor", run.objective.floor), ("stats", run.objective.stats)):
        if state is not None:
            for k, v in state.state_dict().items():
                if torch.is_tensor(v):
                    out[f"objective:{name}:{k}"] = v
    return out


def checkpoint_restoration_check(job: TrainJob, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot,
    restore (model, optimizer, objective, RNG) and continue; the parameters must be bit-identical.
    Runs in ``<out_dir>/restore_check/{straight,first,resumed}``. Returns ``identical`` and the list of
    mismatching tensors (names only)."""
    root = job.out_dir / "restore_check"

    def sub(name: str, **kw: Any) -> TrainJob:
        values = {**job.__dict__, "out_dir": root / name, **kw}
        return TrainJob(**values)

    total = 2 * split_update
    straight = run_job(sub("straight", max_updates=total, snapshot_updates=()))
    first = run_job(sub("first", max_updates=split_update, snapshot_updates=(split_update,)))
    folder = root / "first" / "snapshots" / core.snapshot_stem(split_update)
    del first
    resumed = run_job(
        sub(
            "resumed",
            max_updates=total,
            snapshot_updates=(),
            init_snapshot=folder,
            restore_optimizer=True,
        )
    )
    a, b = _state_tensors(straight), _state_tensors(resumed)
    mismatches = sorted(
        k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k])
    )
    return {
        "identical": not mismatches,
        "mismatches": mismatches,
        "split_update": split_update,
        "updates": total,
        "tensors_compared": len(a),
        "resumed_from_update": split_update,
    }


def gradient_reach(model: P9Model, tokens: "Tensor") -> dict[str, bool]:
    """ENGINEERING_FAIL check (ADR 8.6): one backward pass reaches every trainable parameter group
    (a regularizer being inactive is not a failure and is not tested here). ``tokens [B, 64] int64``.
    Returns one entry per group that has trainable parameters: True when every parameter of the group
    received a finite, non-zero gradient from the answer-site loss."""
    model.zero_grad(set_to_none=True)
    logits, _ = model(tokens[:, :-1])
    answer_site_loss(logits, tokens).backward()  # type: ignore[no-untyped-call]
    reached: dict[str, bool] = {}
    for group, items in trainable_groups(model).items():
        if not items:
            continue
        reached[group] = all(
            p.grad is not None and bool(p.grad.isfinite().all()) and bool((p.grad != 0).any())
            for _, p in items
        )
    model.zero_grad(set_to_none=True)
    return reached


# --- command line ---------------------------------------------------------------------------------------------------
def _configure() -> None:
    from arborlm.engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:  # the inter-op thread count can be set once per process
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


def prepare_job(args: argparse.Namespace) -> TrainJob:
    """Load the verified backbone, generate the data draw and build the cell's job. Needs the
    git-ignored ``experiments/`` and the package-I1 data module."""
    from arborlm import p8_core

    from . import data as data_mod

    cell = core.parse_label(args.label)
    root = Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()
    seeds = (
        core.registered_seeds() if args.mode == "registered" else core.rehearsal_seeds(args.draw)
    )
    backbone, _ = p8_core.load_backbone(cell, root)
    study = data_mod.build_study_data(seeds, core.load_trained_corpus(root))
    stream = data_mod.training_stream_for(study, cell)
    lut = None
    if cell.rung == "R2":
        lut = data_mod.identifier_lut(study.facts, data_mod.facts_of(study, cell))
    out_dir = core.cell_dir(Path(args.run_dir), cell.label)
    return TrainJob(
        cell=cell,
        exposure=args.exposure,
        mode=args.mode,
        data=study,
        stream=stream,
        backbone=backbone,
        out_dir=out_dir,
        max_updates=args.max_updates,
        fact_lut=lut,
        init_seed=None if args.mode == "registered" else seeds.facts,
        r1_seed=seeds.r1_codes,
        branch_seed=seeds.branch_hash,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m studies.p9.train", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("cell", "restore-check", "rehearsal"):
        p = sub.add_parser(name)
        p.add_argument("--label", required=True)
        p.add_argument("--run-dir", required=True)
        p.add_argument("--experiments-root", default=None)
        p.add_argument("--exposure", type=int, default=core.DEFAULT_EXPOSURE)
        p.add_argument(
            "--mode", choices=MODES, default="rehearsal" if name == "rehearsal" else "calibration"
        )
        p.add_argument("--draw", type=int, default=0, help="rehearsal seed draw")
        p.add_argument("--max-updates", type=int, default=None)
        if name == "restore-check":
            p.add_argument("--split", type=int, required=True)
    sub.add_parser("stage")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.train {cell,stage,restore-check,rehearsal} ...``.
    ``stage`` belongs to the job manager (``studies.p9.pool``) and is refused here. Output is a single
    line of non-loss, non-accuracy facts (status, record path; for ``rehearsal`` the whitelisted record)."""
    args = _parser().parse_args(argv)
    if args.command == "stage":
        print("stage runs belong to studies.p9.pool", file=sys.stderr)
        return 2
    _configure()
    if args.command == "rehearsal":
        args.mode = "rehearsal"
    job = prepare_job(args)
    if args.command == "restore-check":
        result = checkpoint_restoration_check(job, args.split)
        print(
            json.dumps(
                {"restoration_identical": result["identical"], "mismatches": result["mismatches"]}
            )
        )
        return 0 if result["identical"] else 1
    record = train_cell(job)
    if args.mode == "rehearsal":
        print((job.out_dir / "rehearsal.json").read_text(encoding="utf-8"))
    else:
        print(
            json.dumps(
                {
                    "label": record["label"],
                    "status": record["status"],
                    "record": str(job.out_dir / "train.json"),
                }
            )
        )
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "MODES",
    "PARAMETER_GROUP_NAMES",
    "Executed",
    "RehearsalRecordError",
    "RowLazyAdam",
    "TrainJob",
    "Trainer",
    "all_position_loss",
    "answer_site_loss",
    "build_optimizer",
    "checkpoint_restoration_check",
    "gradient_reach",
    "load_snapshot",
    "main",
    "optimizer_state_bytes",
    "run_job",
    "save_snapshot",
    "train_cell",
    "validate_rehearsal_record",
    "write_rehearsal_record",
]
