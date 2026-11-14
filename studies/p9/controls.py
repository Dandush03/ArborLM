# ruff: noqa: E501
"""P9 controls that involve no trained memory (package I1): exact retrieval, the no-memory baseline,
frozen-hidden probes, the answer probability attainable through the frozen final layers, and the G2
chance report.

Specification: ADR-0017 section 5.6 (controls), 8.1 (G2), 12 step 4 (calibration: allowed contents).
STUB: signatures only. All scores are ``core.AnswerScores`` computed by ``core.score_answer_sites``
so that "most probable symbol within the alphabet, ties counted wrong" is implemented once.

Shapes: ``Q`` is the number of answer-site queries of a stream (8 per context, in (context, record)
order); logits are ``[Q, 256] float32``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from .core import AnswerScores, ChanceInterval
from .data import FactTable, Stream

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone


def answer_site_logits_no_memory(
    backbone: "Backbone", stream: Stream, *, batch_contexts: int = 64
) -> "Tensor":
    """Frozen backbone with no addition, ``[Q, 256] float32`` logits at every answer site of
    ``stream`` in (context, record) order. CPU, FP32, no gradients (ADR 5.1)."""
    raise NotImplementedError


def evaluate_no_memory(
    backbone: "Backbone", table: FactTable, stream: Stream, *, batch_contexts: int = 64
) -> AnswerScores:
    """No-memory baseline on ``stream`` (ADR 5.6): scores against the facts' answers."""
    raise NotImplementedError


def exact_retrieval(table: FactTable, stream: Stream, known_ids: "Tensor") -> AnswerScores:
    """Dictionary lookup of ``known_ids`` (``[K] int64`` facts in the dictionary): probability 1 on
    the stored answer, so exactly 1.0 accuracy on trained facts; unseen facts get symbol index 0
    (core.OPEN_CHOICES c10), so their accuracy is exactly the count of chance matches (ADR 4.6
    check 4, D01). Also the append-only "exact retrieval" arm of Lane D (ADR 8.5)."""
    raise NotImplementedError


@dataclass
class ProbeResult:
    """A frozen-hidden probe (ADR 5.6): no memory involved. ``accuracy`` is over the facts of the
    evaluation stream; ``scores`` is None for probes that give only a hard prediction."""

    name: str
    facts: int
    correct: int
    accuracy: float
    scores: AnswerScores | None


def nearest_stored_state_probe(
    backbone: "Backbone", table: FactTable, train: Stream, evaluate: Stream
) -> ProbeResult:
    """Predict, for each answer site of ``evaluate``, the answer stored with the nearest (cosine)
    frozen answer-site hidden state of ``train`` (hidden state after the first block, ``[32]``)."""
    raise NotImplementedError


def linear_probe_per_position(
    backbone: "Backbone", table: FactTable, train: Stream, evaluate: Stream, *, seed: int
) -> list[ProbeResult]:
    """One 32-way linear probe per identifier position (five), trained on the frozen hidden states
    at the answer site (closed form or a fixed small number of full-batch steps; no memory)."""
    raise NotImplementedError


def attainable_answer_probability(
    backbone: "Backbone", stream: Stream, *, max_norm: float | None = None
) -> dict[str, float]:
    """Largest probability of the correct symbol reachable through the frozen upper block and output
    layers by an additive change to the answer-site hidden state (linear algebra on frozen weights;
    ADR 12 step 4). Returns summary statistics (``mean``, ``median``, ``min``, ``max`` over
    answer sites) for the calibration record."""
    raise NotImplementedError


class G2Test(TypedDict):
    name: str
    facts: int
    correct: int
    interval: tuple[int, int]
    inside: bool


class G2Report(TypedDict):
    tests: int
    level: float
    results: list[G2Test]
    passed: bool


def g2_report(counts: Mapping[str, tuple[int, int]], tests: int) -> G2Report:
    """Gate G2 (ADR 8.1): ``counts`` maps a test name to ``(correct, facts)`` (the no-memory baseline
    on the 2,048-, 8,192- and 32,768-fact sets and the unseen set, per panel; Lane D sets A and B with
    ``tests = core.G2_TESTS_LANE_D``). Each must lie inside ``core.chance_interval(facts, tests)``."""
    raise NotImplementedError


def unseen_leakage(correct: int, facts: int, tests: int = 8) -> bool:
    """LEAKAGE flag (ADR 8.1): the unseen-fact accuracy of a trained cell lies outside the interval."""
    raise NotImplementedError


def chance_intervals_for_registered_sets() -> dict[str, ChanceInterval]:
    """The G2 intervals for 2,048 / 8,192 / 32,768 facts (tests = 8) and 4,096 (tests = 4)."""
    raise NotImplementedError
