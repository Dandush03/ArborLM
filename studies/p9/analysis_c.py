# ruff: noqa: E501
"""P9 Lane C analysis (package I6): the Lane C gate, locality classes, the hierarchy rule, and the
synthetic-trace classes.

Specification: ADR-0017 section 3 (Lane C gate: the 4K -> 16K capacity step supported for the
architecture concerned, and its B1 cell with alpha_u = 0.25, alpha_c = 0 UTILIZATION_PRESERVED or
IMPROVED against its dose-zero 16K cell; otherwise H17-LOC NOT EVALUATED, descriptive only), 8.4
(locality classes over all four primary settings, both tie rules, both seeds, both panels; first match
wins; hierarchy advantage), 9 (synthetic part and the D09 sweep). STUB: signatures only.

Inputs: ``core.EvalIndex`` for quality and utilization, and the ``core.SimRecord`` lists written by
``sim.simulate_cell`` for locality. Comparison: E of the case against E of the reference, each under
its own optimized co-access layout fitted on its calibration stream (layout key ``coaccess@R``);
identity, frequency, random-partition and branch-constrained layouts and the oracle bound are reported
as controls and enter no class. References: locality reference = the dose-zero flat 16K cell;
utilization reference of a locality cell = the cell with alpha_u = 0.25, alpha_c = 0 of the same
architecture. Pages per query and cross-query reuse are reported separately for every locality cell.
"""

from collections.abc import Mapping, Sequence

from .core import Cell, ClassResult, EvalIndex, SimRecord

LOCALITY_CLASSES = (
    "NOT REPLICATED",
    "COLLAPSED / QUALITY_FAILED",
    "DEGENERATE",
    "LOCALITY_POSITIVE",
    "CONCENTRATION_ONLY",
    "WORSE",
    "NO DIFFERENCE",
    "INTERMEDIATE",
)
SYNTHETIC_EXPECTED = {
    "popularity_only": "NO DIFFERENCE",
    "clusters_random_sharing": "NO DIFFERENCE",
    "clusters_aligned_sharing": "LOCALITY_POSITIVE",
    "collapsed_single_set": "DEGENERATE",
    "working_set_below_cache": "DEGENERATE",
    "incomplete_input": "INCOMPLETE",
}

SimIndex = Mapping[str, Sequence[SimRecord]]  # cell label -> its simulation records


def lane_c_gate(index: EvalIndex, arch: str, exposure: int) -> dict[str, object]:
    """Gate to interpretation for ``arch``: the 4K -> 16K step supported (analysis_a step rule) and the
    B1 alpha_u = 0.25, alpha_c = 0 cell UTILIZATION_PRESERVED or IMPROVED. Returns ``{"passed", ...}``."""
    raise NotImplementedError


def e_ratio_case_vs_reference(
    case: Sequence[SimRecord],
    reference: Sequence[SimRecord],
    *,
    rows: int,
    rho: float,
    tie: str,
    stream: str,
) -> float | None:
    """E(case) / E(reference) for one primary setting, each under its own co-access layout; None when
    either E is undefined."""
    raise NotImplementedError


def raw_miss_ratio(
    case: Sequence[SimRecord],
    reference: Sequence[SimRecord],
    *,
    rows: int,
    rho: float,
    tie: str,
    stream: str,
) -> float | None:
    """Actual-miss ratio case / reference (used by CONCENTRATION_ONLY)."""
    raise NotImplementedError


def classify_locality_panel(
    index: EvalIndex, sims: SimIndex, case: Cell, panel: str, exposure: int
) -> str:
    """Rules 2-6 of ADR 8.4 for one panel over all four settings and both ties: COLLAPSED /
    QUALITY_FAILED (utilization COLLAPSED or I ratio to the locality reference < 0.97) before
    DEGENERATE (any primary setting degenerate for the case or its reference), LOCALITY_POSITIVE
    (E ratio <= 0.80 and the cell UTILIZATION_PRESERVED or IMPROVED), CONCENTRATION_ONLY (raw miss
    ratio <= 0.80 and E ratio > 0.90), WORSE (>= 1.10) / NO DIFFERENCE (in (0.90, 1.10)) / INTERMEDIATE."""
    raise NotImplementedError


def classify_locality(
    index: EvalIndex, sims: SimIndex, case_group: list[Cell], exposure: int
) -> ClassResult:
    """Class of one C1 case (both seeds) with the controls, pages per query, cross-query reuse and the
    ratio of cache size to U* reported in ``details``; NOT_EVALUATED if the gate fails (descriptive)."""
    raise NotImplementedError


def hierarchy_advantage(flat: ClassResult, tree: ClassResult) -> bool:
    """A hierarchy advantage needs the tree case LOCALITY_POSITIVE against the flat case with the same
    doses (ADR 8.4)."""
    raise NotImplementedError


def classify_planted(kind: str, result_class: str) -> bool:
    """Synthetic part (ADR 9): True when the class produced for the planted trace of ``kind`` equals
    ``SYNTHETIC_EXPECTED[kind]`` (every class must be exercised by a required test)."""
    raise NotImplementedError


def d09_sweep(sims: SimIndex) -> list[dict[str, object]]:
    """Descriptive table of rho in {1/16, 1/4, 1} x R in {2, 8, 32}; settings outside the primary four
    and all rho = 1 are labelled descriptive."""
    raise NotImplementedError


def analyze(index: EvalIndex, sims: SimIndex, exposure: int) -> list[ClassResult]:
    """All C1 classes (flat and learned tree, alpha_c in {0.05, 0.25}) plus hierarchy advantages, the
    D09 sweep and the key-traffic identity as descriptive entries."""
    raise NotImplementedError
