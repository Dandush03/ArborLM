# ruff: noqa: E501
"""P9 training (package I2): answer-site loss, AdamW and row-lazy Adam, the training loop, snapshots
with optimizer state, the instrumentation of ADR 6.3, and the modes ``registered``, ``calibration``
and ``rehearsal``.

Specification: ADR-0017 section 5.1 (loss at answer sites only; AdamW lr 0.003, no weight decay, clip
1.0), 5.5 (batch of 16 contexts, constant learning rate, snapshots), 5.6 (row-lazy Adam on the key and
value tables only, lr 0.012; projections, gate and router use AdamW), 6.3 (per-update and per-row
instrumentation), 12 step 5 (rehearsal writes only through a whitelist validator). STUB: signatures.

Disk layout (``core.cell_dir`` and ``core.snapshot_dir``): ``train.json`` (``core.TrainRecord``),
``updates.jsonl`` (one ``core.UpdateRecord`` per update), and per snapshot ``model.pt``,
``optimizer.pt`` (optimizer state, objective state, update counter, RNG state), ``movement.pt``
(``key_with``, ``key_without``, ``value_with``, ``value_without``: ``[N] float32`` cumulative
parameter movement on updates where the row did / did not have a task gradient) and
``snapshot.json`` (``core.SnapshotRecord``).

Modes: ``registered`` (the run; needs a freeze), ``calibration`` and ``rehearsal`` (rehearsal-seed
data only; the rehearsal path writes records only through ``write_rehearsal_record`` and must never
write the loss or accuracy of a compared arm anywhere).
"""

from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.optim import Optimizer

from .core import Cell, TrainRecord
from .data import StudyData, TrainingStream
from .model import P9Model

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

MODES = ("registered", "calibration", "rehearsal")


def answer_site_loss(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Mean cross-entropy at answer sites only (ADR 5.1, every arm): ``logits [B, 63, 256]`` against
    targets ``tokens[:, 1:]`` at input positions 8r+6 (target byte 8r+7), scalar float32."""
    raise NotImplementedError


def all_position_loss(logits: "Tensor", tokens: "Tensor") -> "Tensor":
    """Mean cross-entropy over all 63 targets; descriptive only, never optimized."""
    raise NotImplementedError


class RowLazyAdam(Optimizer):
    """Adam with per-row moments for 2-D tables: a row is updated only on updates where its gradient
    is non-zero, with bias correction by the row's own update count (ADR 5.6). Used for ``keys`` and
    ``values`` of A10 at learning rate ``core.LAZY_LEARNING_RATE``; betas and eps as AdamW."""

    def __init__(
        self,
        params: Iterable["torch.nn.Parameter"],
        lr: float,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ) -> None:
        raise NotImplementedError

    def step(self, closure: Callable[[], float] | None = None) -> float | None:  # type: ignore[override]
        raise NotImplementedError


def build_optimizer(model: P9Model, cell: Cell) -> list[Optimizer]:
    """Optimizers of the cell: one AdamW over all trainable parameters (lr 0.003, betas (0.9, 0.999),
    eps 1e-8, weight decay 0) for ``adamw`` cells; for ``lazy`` cells a ``RowLazyAdam`` over keys and
    values plus an AdamW over the remaining trainable parameters. Gradient clipping at 1.0 is applied
    over all trainable parameters together by the loop, before any step."""
    raise NotImplementedError


@dataclass
class TrainJob:
    """Inputs of one cell's training run.

    ``stream`` comes from ``data.training_stream_for`` (Lane D phase B arms pass the B stream).
    ``init_snapshot`` starts from a snapshot's model parameters and, if ``restore_optimizer`` is True,
    its optimizer and objective state and update counter (the checkpoint-restoration test); False
    gives the fresh optimizer of every Lane D phase-B arm (ADR 8.5). ``trainable_groups`` restricts
    training (``("keys", "values")`` for memory-only). ``max_updates`` caps the run (rehearsal).
    ``out_dir`` is ``core.cell_dir(run_dir, cell.label)``.
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


def train_cell(job: TrainJob) -> TrainRecord:
    """Train one cell for ``core.run_updates`` updates (or ``max_updates``), writing ``updates.jsonl``,
    the snapshots of ``core.snapshots`` (or ``snapshot_updates``) and ``train.json``. Constant learning
    rate, so a snapshot is a valid shorter run. Deterministic on CPU/FP32 (G4)."""
    raise NotImplementedError


def save_snapshot(
    out_dir: Path, update: int, model: P9Model, optimizers: list[Optimizer], extra: dict[str, Any]
) -> dict[str, str]:
    """Write ``model.pt``, ``optimizer.pt``, ``movement.pt`` (from ``extra``) and ``snapshot.json`` of
    update ``update``; returns the file hashes. ``extra`` carries the objective state, RNG state and
    the movement accumulators."""
    raise NotImplementedError


def load_snapshot(
    snapshot_dir: Path,
    model: P9Model,
    optimizers: list[Optimizer] | None = None,
) -> dict[str, Any]:
    """Load a snapshot into ``model`` (and ``optimizers`` when given); returns the ``extra`` payload.
    Used by evaluation (model only) and by the restoration test (bit-identical continuation)."""
    raise NotImplementedError


class RehearsalRecordError(ValueError):
    """A rehearsal record contained a key outside ``core.REHEARSAL_RECORD_KEYS``."""


def write_rehearsal_record(path: Path, record: dict[str, Any]) -> None:
    """The only writer of rehearsal-mode records: refuses any key outside the whitelist (time, RSS,
    finiteness, shapes) and any non-finite-flag value that looks like a loss or accuracy."""
    raise NotImplementedError


def checkpoint_restoration_check(job: TrainJob, split_update: int) -> dict[str, Any]:
    """Gate G4: train ``2 * split_update`` updates straight, and train ``split_update``, snapshot,
    restore (model, optimizer, objective, RNG) and continue; the parameters must be bit-identical."""
    raise NotImplementedError


def gradient_reach(model: P9Model, tokens: "Tensor") -> dict[str, bool]:
    """ENGINEERING_FAIL check (ADR 8.6): one backward pass reaches every trainable parameter group
    (a regularizer being inactive is not a failure and is not tested here)."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.train {cell,stage,restore-check,rehearsal} ...``."""
    raise NotImplementedError
