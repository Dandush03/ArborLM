# ruff: noqa: E501
"""P9 Lane B analysis (package I6): utilization classes and the optimization annotations.

Specification: ADR-0017 section 6.3 (REGULARIZER-DRIVEN MOVEMENT), 7 (SOFT-USAGE ONLY), 8.3 (the
utilization classes; first match wins). STUB: signatures only.

Reference of a case: the dose-zero 16K cell of the same architecture and seed for B1 cells; the B1 cell
with alpha_u = 0.25, alpha_c = 0 of the same architecture and seed for C1 cells (``reference_label``).
Every rule is evaluated per seed against the reference of the same seed and must hold in both seeds
and both panels; seeds that disagree give INTERMEDIATE; panels that disagree give NOT REPLICATED.
Lane B classes need dose-zero 16K accuracy >= 0.25 in both seeds, else NOT_EVALUATED. If U* is NOT
INTERPRETABLE for the case or its reference, COLLAPSED is decided by the I ratio alone and
ENTROPY_INFLATION, IMPROVED and PRESERVED become INTERMEDIATE. Entropy-effective slots here come from
hard top-8 selections at answer sites (``EvalRecord.usage['entropy_effective_hard']``).

Movement inputs: ``EvalRecord.usage['key_movement_without_task_grad']`` (cumulative key movement on
updates where the row had no task gradient, summed over rows) and ``['key_movement_share_without']``.
"""

from .core import Cell, ClassResult, EvalIndex

UTILIZATION_CLASSES = (
    "NOT REPLICATED",
    "COLLAPSED",
    "ENTROPY_INFLATION",
    "UTILIZATION_IMPROVED",
    "UTILIZATION_PRESERVED",
    "NO DIFFERENCE / INTERMEDIATE",
)


def reference_label(cell: Cell) -> str:
    """Label of the reference cell of a B1 or C1 cell (same architecture, parent and seed)."""
    raise NotImplementedError


def lane_b_evaluable(index: EvalIndex, exposure: int) -> dict[str, bool]:
    """Per architecture: dose-zero 16K accuracy >= 0.25 in both seeds (else Lane B is NOT_EVALUATED)."""
    raise NotImplementedError


def utilization_ratios(index: EvalIndex, case: Cell, panel: str, exposure: int) -> dict[str, float]:
    """Per-seed ratios against the reference: I, U*, entropy-effective slots (hard), mean minimal
    support length, and the accuracy drop; keyed ``<name>_s1701`` / ``<name>_s1702``."""
    raise NotImplementedError


def classify_utilization_panel(index: EvalIndex, case: Cell, panel: str, exposure: int) -> str:
    """Rules 2-6 of ADR 8.3 for one panel: COLLAPSED (U* ratio < 0.80 or I ratio < 0.90),
    ENTROPY_INFLATION (eff ratio >= 1.25, I ratio < 1.03, U* ratio < 1.03), UTILIZATION_IMPROVED (I and
    U* ratios >= 1.05 and support-length ratio <= 1.10), UTILIZATION_PRESERVED (I ratio >= 0.97, drop
    <= 0.02, U* ratio >= 0.97), else NO DIFFERENCE / INTERMEDIATE."""
    raise NotImplementedError


def soft_usage_only(index: EvalIndex, case: Cell, panel: str, exposure: int) -> bool:
    """SOFT-USAGE ONLY: soft H(u) >= ln M while the hard entropy-effective-slot ratio to the reference
    is below 1.05 (ADR 7)."""
    raise NotImplementedError


def regularizer_driven_movement(index: EvalIndex, case: Cell, exposure: int) -> bool:
    """REGULARIZER-DRIVEN MOVEMENT: in both seeds the cell's cumulative key movement on updates where
    the row had no task gradient exceeds 1.5 x that of its reference (``core.REGULARIZER_MOVEMENT_RATIO``)."""
    raise NotImplementedError


def classify_utilization(index: EvalIndex, case_group: list[Cell], exposure: int) -> ClassResult:
    """Class of one case (both seeds of one architecture and dose) with annotations SOFT-USAGE ONLY and
    REGULARIZER-DRIVEN MOVEMENT; ``case_group`` holds the two seed cells."""
    raise NotImplementedError


def analyze(index: EvalIndex, exposure: int) -> list[ClassResult]:
    """All B1 classes (flat and learned tree, alpha_u in {0.25, 1}); C1 cells are classed against
    their own reference in ``analysis_c`` using ``classify_utilization``."""
    raise NotImplementedError
