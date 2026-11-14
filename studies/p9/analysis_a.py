# ruff: noqa: E501
"""P9 Lane A analysis (package I6): capacity classes, annotations and the ladder report.

Specification: ADR-0017 section 6.1 (I_acc), 8.1 (gates G1-G4, TASK_CEILING_FAIL), 8.2 (capacity: steps,
beats dense, dependence, plateau, the six classes with first-match precedence, the four annotations,
the ladder report), 10 (analysis dependencies: capacity classes need A1/A2 at all sizes including B102
and A8; annotations need A4 with A1 at 4K, A10, A7, A3). STUB: signatures only.

Inputs are the ``core.EvalIndex`` of evaluation records keyed ``(label, update, stream)``: for a cell
the matched-exposure snapshot is ``core.updates(cell, E)`` (and ``U/2`` for the plateau rule), read on
``core.PANEL_STREAM['A']`` and ``['B']`` separately. The class of each panel is computed on its own and
disagreement gives NOT REPLICATED (order 1). Every function is a pure function of its inputs so that
synthetic inputs can trigger every class (required test). Thresholds are ``core`` constants; none is
chosen here.
"""

from dataclasses import dataclass

from .core import ClassResult, EvalIndex

CAPACITY_CLASSES = (
    "NOT REPLICATED",
    "CAPACITY_NOT_SUPPORTED",
    "CAPACITY_POSITIVE",
    "CAPACITY_PARTIAL",
    "UNDERTRAINED",
    "INTERMEDIATE",
)
TREE_CLASSES = ("TREE_AHEAD", "TREE_COMPETITIVE", "TREE_BEHIND")


@dataclass(frozen=True)
class StepResult:
    """One size step N -> 4N for one panel: ``supported`` (accuracy >= 0.25 at both sizes in every cell
    of the step; I ratio >= 3.0 in both B101 seeds and >= 2.5 in the B102 replicate where one exists;
    a ratio with I_N = 0 is +inf), ``failing`` (in both seeds ratio < 2.0 or accuracy < 0.25 at the
    larger size), ``larger_plateaued``, and the ratios used."""

    slots_from: int
    slots_to: int
    supported: bool
    failing: bool
    larger_plateaued: bool
    ratios: dict[str, float]
    accuracies: dict[str, float]


def information_ratio(i_small: float, i_large: float) -> float:
    """I_4N / I_N with I_N = 0 giving +inf (and 0/0 giving 0)."""
    raise NotImplementedError


def plateaued(i_half: float, i_full: float) -> bool:
    """I(U) - I(U/2) <= 0.05 I(U) with I already floored by ``core.information_bits`` (a cell at chance
    at both snapshots has plateaued)."""
    raise NotImplementedError


def step_result(
    index: EvalIndex,
    arch: str,
    slots_from: int,
    panel: str,
    exposure: int,
    *,
    optimizer: str = "adamw",
) -> StepResult:
    """Evaluate one step for ``arch`` in {flat, learned_tree} (A1/A2) or the row-lazy arm (A10,
    ``optimizer='lazy'``; two B101 seeds only, no replicate)."""
    raise NotImplementedError


def beats_dense(index: EvalIndex, arch: str, slots: int, panel: str, exposure: int) -> bool:
    """I >= 1.10 x the matched dense adapter's (A8), both seeds, at ``slots``."""
    raise NotImplementedError


def dependence_holds(index: EvalIndex, arch: str, slots: int, panel: str, exposure: int) -> bool:
    """Value permutation and disabling give chance accuracy (``core.chance_interval``) and at least 90%
    of correctly answered facts have a minimal support."""
    raise NotImplementedError


def classify_capacity_panel(index: EvalIndex, arch: str, panel: str, exposure: int) -> str:
    """The first matching class of ADR 8.2 for one panel, orders 2-6 (order 1 is the panel rule)."""
    raise NotImplementedError


def classify_capacity(index: EvalIndex, arch: str, exposure: int) -> ClassResult:
    """Capacity class of ``arch`` (flat or learned_tree) with annotations: NOT REPLICATED if the panels
    disagree, else the class; TASK_CEILING_FAIL sizes make dependent steps NOT_EVALUATED (and
    CAPACITY_POSITIVE impossible if 65,536 fails; Lanes B-D NOT_EVALUATED if 16,384 fails)."""
    raise NotImplementedError


def empty_slot_effect(index: EvalIndex, panel: str, exposure: int) -> bool:
    """EMPTY-SLOT-EFFECT: at 2,048 fixed facts (A4 with A1 at 4K) I_acc per fact rises by more than 25%
    from 4K to 64K."""
    raise NotImplementedError


def optimizer_annotation(
    index: EvalIndex, arch_step: tuple[int, int], panel: str, exposure: int
) -> str:
    """OPTIMIZER-DEPENDENT if a step supported under AdamW is not supported in A10 and the row-lazy
    accuracy at the smaller size of the step is >= 0.25 in both seeds; otherwise OPTIMIZER-ARM
    UNINFORMATIVE; 'OPTIMIZER-DEPENDENT: not assessed' when A10 is absent."""
    raise NotImplementedError


def key_width_limited(index: EvalIndex, panel: str, exposure: int) -> str:
    """KEY-WIDTH-LIMITED if key-32 R0 supports 16K -> 64K (two B101 seeds) and key-16 R0 does not;
    'not assessed' if A7 at 65,536 is absent."""
    raise NotImplementedError


def tree_comparison(index: EvalIndex, exposure: int) -> ClassResult:
    """D03: TREE_AHEAD if tree I_acc >= 1.03 x flat at 16K in both seeds and both panels,
    TREE_COMPETITIVE if >= 0.97, else TREE_BEHIND, with logical key products beside it and the fixed
    tree (A3) reported beside it."""
    raise NotImplementedError


def ladder_report(
    index: EvalIndex, panel: str, exposure: int
) -> dict[str, dict[str, float | None]]:
    """Per size, in Fano bits per fact with sign: exact - R2, R2 - R1, R1 - R0a, R0a - R0, and tree
    oracle branch - tree R0, with frozen-hidden probes beside R0; a gap is material at >= 0.5 bits.
    At 4,096 slots only exact - R2 and R2 - R1 (R0a is not run). Never enters a class."""
    raise NotImplementedError


def task_gates(index: EvalIndex, calibration: dict[str, object]) -> dict[str, str]:
    """G1-G4 outcomes per size from the calibration and generator reports; TASK_CEILING_FAIL sizes."""
    raise NotImplementedError


def analyze(index: EvalIndex, exposure: int, calibration: dict[str, object]) -> list[ClassResult]:
    """All Lane A results: flat and learned-tree capacity classes with annotations, tree comparison,
    ladder report (as a ClassResult with class 'LADDER_REPORT') and gates."""
    raise NotImplementedError
