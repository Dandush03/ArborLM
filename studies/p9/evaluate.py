# ruff: noqa: E501
"""P9 evaluation (package I3): cached selections and weights, accuracy, I_acc with the chance floor,
log-loss gain, seven-position knock-outs, minimal supports, U*, specificity, group ablation, value
permutation and disabling, usage statistics, the LEAKAGE check and trace export.

Specification: ADR-0017 section 6.1 (knowledge), 6.2 (useful slots), 6.3 (per-snapshot optimization
quantities), 7 (soft against hard usage), 8.1 (LEAKAGE), 8.4 (traces). STUB: signatures only.

Cached evaluation (budget requirement): one forward per (snapshot, stream) builds a ``ReadCache``
(``h_pre`` after the first block, the selections and the read weights). Value permutation, disabling,
knock-outs and group ablations reuse it through ``P9Model.memory_delta`` / ``P9Model.finish`` and need
no further key scoring.

Everything is computed per snapshot and per stream; ``evaluate_snapshot`` returns ``core.EvalRecord``.
Accuracy uses ``core.score_answer_sites`` (most probable symbol within the alphabet, ties wrong) and
``core.information_bits`` (I_acc with the chance floor at the G2 interval for the stream's fact count).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .core import AnswerScores, Cell, EvalRecord, Trace
from .data import Stream, StudyData
from .model import P9Model, Selection

if TYPE_CHECKING:
    from torch import Tensor


@dataclass
class ReadCache:
    """One forward over a stream. ``tokens [C, 64] int64``; ``h_pre [C, 63, 32] float32``;
    ``selection`` covers all C contexts (``selected [C, P, 8]``, ``scores [C, P, 8]``, candidate
    fields as ``model.Selection``); ``logits_answer [C, 8, 256] float32`` the logits at the answer
    sites of the unmodified model; ``stream`` is the stream evaluated."""

    stream: Stream
    tokens: "Tensor"
    h_pre: "Tensor"
    selection: Selection | None
    logits_answer: "Tensor"


def build_cache(model: P9Model, stream: Stream, *, batch_contexts: int = 64) -> ReadCache:
    """Run ``model`` once over ``stream`` (no gradients, CPU, FP32) and cache the reads."""
    raise NotImplementedError


def score_cache(cache: ReadCache, table_answers: "Tensor") -> AnswerScores:
    """``AnswerScores`` over the ``C * 8`` answer sites of the cache (context, record order);
    ``table_answers [C * 8] int64`` are the answer symbol indices (``Stream.answer_targets``)."""
    raise NotImplementedError


def logits_with(
    model: P9Model,
    cache: ReadCache,
    *,
    knockout: "Tensor | None" = None,
    values: "Tensor | None" = None,
    disabled: bool = False,
    batch_contexts: int = 64,
) -> "Tensor":
    """``[C, 8, 256]`` answer-site logits with an intervention applied to the cached reads: ``knockout
    [C, P, 8] bool`` removes those slots' values from the weighted sum (selections and weights as
    cached), ``values [N, 32]`` replaces the value table, ``disabled`` removes the memory."""
    raise NotImplementedError


def permute_values(model: P9Model, seed: int) -> "Tensor":
    """``[N, 32]`` value table permuted over slots with a seeded generator (value permutation,
    ADR 5.6; accuracy must fall to chance)."""
    raise NotImplementedError


@dataclass
class SupportResult:
    """Minimal supports (ADR 6.2). ``length [C * 8] int64`` shortest-prefix size (0 when none, i.e.
    the fact is answered incorrectly or no prefix breaks it); ``has_support [C * 8] bool``; ``slots``
    the support slot ids per fact (ragged list of int lists); ``useful`` the sorted ids of useful slots
    (their count is U*); ``removing_site_read_stays_correct [C * 8] bool``."""

    length: "Tensor"
    has_support: "Tensor"
    slots: list[list[int]]
    useful: list[int]
    removing_site_read_stays_correct: "Tensor"


def minimal_supports(
    model: P9Model, cache: ReadCache, nomem: AnswerScores, scores: AnswerScores
) -> SupportResult:
    """For every correctly answered fact: candidates are the union of slots selected at the record's
    seven input positions ordered by summed weight; the minimal support is the shortest prefix whose
    knock-out (values removed at the answer site and the six earlier positions, wherever those slots
    are selected) makes p_f <= max(2/32, p_f_nomem + 0.02) (``core.SUPPORT_P_*``)."""
    raise NotImplementedError


def specificity(
    model: P9Model, cache: ReadCache, supports: SupportResult, scores: AnswerScores, *, seed: int
) -> dict[str, Any]:
    """The two conditions for interpreting U* (ADR 6.2): (1) knocking out 8 slots drawn from other
    facts' minimal supports, excluding every slot selected in the fact's own record, changes p_f by
    less than 0.05 on at least 95% of facts; (2) zeroing the values of one of 64 contiguous slot
    groups at all positions, selections kept, leaves facts whose minimal support avoids the group
    within 0.02 accuracy. Returns ``{"condition_1", "condition_2", "interpretable", ...details}``."""
    raise NotImplementedError


def usage_statistics(cache: ReadCache, supports: SupportResult | None) -> dict[str, Any]:
    """Distinct selected slots, entropy-effective slots (hard top-8 at answer sites and soft from pi),
    hot-64 share, dead slots, weight entropy of each read, facts per slot, soft mass outside the top 8
    and the 8th-9th margin distribution (ADR 6.2, 6.3, 7). Hard entropies use answer-site selections."""
    raise NotImplementedError


def first_entering_top64(model_at_0: P9Model, model: P9Model, stream: Stream) -> int:
    """Count of keys that enter any query's top 64 after update 0 (ADR 6.2 revival count)."""
    raise NotImplementedError


def accuracy_by_neighbour(
    scores: AnswerScores, has_neighbour: "Tensor"
) -> tuple[float | None, float | None]:
    """Accuracy of facts with and without a two-symbol neighbour (ADR 4.1)."""
    raise NotImplementedError


def evaluate_snapshot(
    cell: Cell,
    run_dir: Path,
    update: int,
    stream: Stream,
    data: StudyData,
    model: P9Model,
    *,
    nomem: AnswerScores,
    interventions: bool,
    write_traces: bool,
    seed: int,
) -> EvalRecord:
    """Evaluate one snapshot on one stream and write ``core.eval_path`` (and the per-fact distribution
    file). ``interventions`` runs value permutation, disabling, supports and specificity (done only
    at the matched-exposure and fixed-compute snapshots, per the budget). ``write_traces`` exports the
    answer-site and all-position traces for ``panel_a``, ``panel_b`` and ``calibration``."""
    raise NotImplementedError


def export_traces(
    cell: Cell,
    update: int,
    cache: ReadCache,
    run_dir: Path,
    *,
    kinds: tuple[str, ...] = ("answer", "all"),
) -> dict[str, tuple[Path, str]]:
    """Write ``core.Trace`` files (``core.trace_path``) for ``kinds`` and return ``kind -> (path,
    sha256)``. Answer-site traces hold queries at positions 8r+6 only; all-position traces hold all 63."""
    raise NotImplementedError


def trace_from_cache(cell: Cell, update: int, cache: ReadCache, kind: str) -> Trace:
    """In-memory trace (``core.Trace``) of a cache; ``cluster`` is -1 for unseen facts."""
    raise NotImplementedError


def leakage_flag(unseen_correct: int, unseen_facts: int) -> bool:
    """LEAKAGE (ADR 8.1): unseen-fact accuracy outside the G2 interval (tests = 8)."""
    raise NotImplementedError


def evaluate_cell(
    cell: Cell, run_dir: Path, data: StudyData, experiments_root: Path, exposure: int
) -> list[EvalRecord]:
    """All snapshots of the cell on the panels it needs, with the intervention schedule above. The
    worker entry used by the evaluate stage; one record file per (snapshot, stream)."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.evaluate {cell,stage} ...``."""
    raise NotImplementedError
