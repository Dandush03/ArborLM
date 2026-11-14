# ruff: noqa: E501
"""P9 Lane D analysis (package I6): incremental classes.

Specification: ADR-0017 section 8.1 (Lane D G2 family of 4 tests), 8.5 (classes for flat sequential,
flat memory-only and learned tree sequential, each against dense sequential; replay and exact
retrieval reported beside them and entering no class). STUB: signatures only.

With ``a_A`` and ``a_B`` the accuracy on A and B after phase B and ``a_A0`` the accuracy on A after phase
A: classes need ``a_A0 >= 0.5`` (else NOT_EVALUATED); first match wins, per primary panel, both seeds:
1 NOT REPLICATED (panels disagree); 2 NO_NEW_CAPABILITY (a_B < 0.5 x the joint bound's accuracy on B);
3 FORGETTING (a_A < 0.70 a_A0); 4 INCREMENTAL_POSITIVE (a_B >= 0.9 x the bound on B, a_A >= 0.90 a_A0, and
the arm's forgetting a_A0 - a_A at least 0.10 smaller than dense sequential's, whose own a_A0 must be
>= 0.5 else NOT_EVALUATED); 5 INTERMEDIATE. NO ADVANTAGE OVER DENSE is an annotation printed when dense
sequential's forgetting is <= 0.10. Lane D is NOT_EVALUATED if 16,384 slots is TASK_CEILING_FAIL.
"""

from .core import ClassResult, EvalIndex

INCREMENTAL_CLASSES = (
    "NOT REPLICATED",
    "NO_NEW_CAPABILITY",
    "FORGETTING",
    "INCREMENTAL_POSITIVE",
    "INTERMEDIATE",
)
CLASSED_ARMS = (
    ("flat", "sequential"),
    ("flat", "memory_only"),
    ("learned_tree", "sequential"),
)


def phase_accuracies(index: EvalIndex, label: str, exposure: int, panel: str) -> dict[str, float]:
    """``{"a_A", "a_B"}`` of a D2 cell on ``panel`` and ``{"a_A0"}`` of its D1 cell, read from the
    evaluation records of the lane_d streams at the phase-end snapshots."""
    raise NotImplementedError


def lane_d_g2(index: EvalIndex, panel: str) -> dict[str, object]:
    """No-memory baseline on sets A and B per primary panel against the 4-test interval
    (``core.chance_interval(4096, core.G2_TESTS_LANE_D)``)."""
    raise NotImplementedError


def classify_arm_panel(index: EvalIndex, arch: str, arm: str, panel: str, exposure: int) -> str:
    """Classes 2-5 for one panel and one classed arm, with seeds combined (both seeds must satisfy a
    rule)."""
    raise NotImplementedError


def classify_arm(index: EvalIndex, arch: str, arm: str, exposure: int) -> ClassResult:
    """Class with the NO ADVANTAGE OVER DENSE annotation; replay, exact retrieval and the joint bound
    in ``details`` beside the class (no class of their own)."""
    raise NotImplementedError


def analyze(index: EvalIndex, exposure: int) -> list[ClassResult]:
    """All Lane D results for the three classed arms."""
    raise NotImplementedError
