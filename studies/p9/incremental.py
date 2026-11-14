# ruff: noqa: E501
"""P9 Lane D (package I5): phase A and phase B arms, replay, fresh optimizer at V1, and the Lane D
measurements.

Specification: ADR-0017 section 8.5 (incremental; 16,384 slots; A and B are 4,096 disjoint facts each).
STUB: signatures only. Training itself is ``train.train_cell`` driven through ``train.TrainJob``; this
module builds the jobs and measures. Phase A is the D1 cells; phase B the D2 cells (six trained arms
plus the joint bound; exact retrieval by append is ``controls.exact_retrieval``).

Arms (``Cell.lane_d_arm``): ``phaseA`` (D1: flat, learned tree, dense), ``sequential`` (all addition
parameters train, from V1), ``memory_only`` (flat only: keys and values train, projections and gate
frozen), ``replay`` (flat and dense: B's E exposures plus one replayed A context per B context,
``core.contexts_per_update``; updates = ``core.updates``; compared only with each other and the
bound), ``joint`` (flat from initialization on A u B, ``LANE_D_JOINT_FACTS`` facts). Every phase-B arm
starts from V1's parameters with a FRESH optimizer state (ADR 8.5); V1 also stores the optimizer state
for the restoration test only.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .core import Cell
from .data import StudyData
from .train import TrainJob

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone


def phase_a_job(
    cell: Cell, data: StudyData, backbone: "Backbone", run_dir: Path, exposure: int, mode: str
) -> TrainJob:
    """TrainJob of a D1 cell: E exposures of set A from initialization; V1 = the snapshot at U."""
    raise NotImplementedError


def phase_b_job(
    cell: Cell,
    data: StudyData,
    backbone: "Backbone",
    run_dir: Path,
    v1_snapshot: Path,
    exposure: int,
    mode: str,
) -> TrainJob:
    """TrainJob of a D2 cell from ``v1_snapshot`` (V1 of the D1 cell named by ``cell.depends_on``):
    model parameters only, fresh optimizer (``restore_optimizer=False``); memory-only sets
    ``trainable_groups=("keys", "values")``; replay adds set-A contexts; joint (no dependency) starts
    from initialization on A then B ids."""
    raise NotImplementedError


def v1_snapshot_path(run_dir: Path, d1_label: str, exposure: int) -> Path:
    """Snapshot directory of V1: the D1 cell's snapshot at ``core.updates(d1, exposure)``."""
    raise NotImplementedError


@dataclass
class LaneDMeasurement:
    """Accuracy after a phase on a primary panel. ``a_acc`` and ``b_acc`` are accuracies on the A and B
    facts; ``a0_acc`` is accuracy on A after phase A (the cell's own D1); ``changed_slots`` and
    ``changed_bytes`` count key and value rows that differ between V1 and V2 (0 for dense: its changed
    parameters are counted instead); ``support_overlap`` is the overlap of the minimal supports of A and
    B facts (``evaluate.minimal_supports``)."""

    label: str
    panel: str
    a_acc: float
    b_acc: float
    a0_acc: float | None
    changed_slots: int
    changed_bytes: int
    support_overlap: float | None
    updates: int
    examples: int
    logical_lookup_work: int


def changed_between(v1_snapshot: Path, v2_snapshot: Path) -> tuple[int, int]:
    """``(slots, bytes)`` whose key or value rows differ between V1 and V2 (parameters for dense)."""
    raise NotImplementedError


def measure_arm(
    cell: Cell, run_dir: Path, data: StudyData, experiments_root: Path, exposure: int
) -> list[LaneDMeasurement]:
    """Measure one D2 cell on panels A and B for sets A and B (evaluation cached as in ``evaluate``)."""
    raise NotImplementedError


def forgetting(a0_acc: float, a_acc: float) -> float:
    """a_A^0 - a_A."""
    raise NotImplementedError


def logical_lookup_work(arch: str, slots: int, queries: int) -> int:
    """Logical key products over ``queries`` (``core.logical_key_products``); logical work only."""
    raise NotImplementedError


def lane_d_gate(a0_accuracies: dict[str, float]) -> dict[str, bool]:
    """Per D1 label: phase-A accuracy >= ``core.LANE_D_A0_MIN`` (else the arm is NOT_EVALUATED)."""
    raise NotImplementedError


def replay_contexts(data: StudyData, update: int) -> "Tensor":
    """``[16, 64] int64`` replayed set-A contexts of 1-based ``update`` (pure function of the update)."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.incremental {phase-a,phase-b,measure} ...``."""
    raise NotImplementedError


__all__ = [
    "LaneDMeasurement",
    "changed_between",
    "forgetting",
    "lane_d_gate",
    "logical_lookup_work",
    "main",
    "measure_arm",
    "phase_a_job",
    "phase_b_job",
    "replay_contexts",
    "v1_snapshot_path",
]
