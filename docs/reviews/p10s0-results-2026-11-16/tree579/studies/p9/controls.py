# ruff: noqa: E501
"""P9 controls that involve no trained memory (package I1): exact retrieval, the no-memory baseline,
frozen-hidden probes, the answer probability attainable through the frozen final layers, and the G2
chance report.

Specification: ADR-0017 section 5.6 (controls), 8.1 (G2), 12 step 4 (calibration: allowed contents).
All scores are ``core.AnswerScores`` computed by ``core.score_answer_sites`` so that "most probable
symbol within the alphabet, ties counted wrong" is implemented once. Self-checked only: not
independent review, not Astra validation, not human approval.

Shapes: ``Q`` is the number of answer-site queries of a stream (8 per context, in (context, record)
order); logits are ``[Q, 256] float32``.

Frozen backbone. ``load_backbone`` restores B101/B102 exactly as P5 and P8 do (``p8_core.load_backbone``
verifies the parent record, the checkpoint state and the backbone digest against P5's baselines);
``synthetic_backbone`` is a random full-size backbone for unit tests only. The backbone is run
directly (embedding, block 0, block 1, final norm, tied output), not through any P9 model module.
The "hidden state" of the probes is the residual stream after the first block, where the memory is
inserted (``insertion_hidden`` of P5).

Documented methods and their limits:

* **Nearest stored state.** Cosine nearest neighbour among the answer-site hidden states of the
  ``train`` stream; predicts the stored answer. Uses every answer site of ``train`` (with the
  calibration stream, each fact twice). Hard prediction only.
* **Linear probe.** One probe per identifier position (five), 32 classes, predicting the identifier
  symbol from the answer-site hidden state. Closed-form ridge regression on one-hot targets (a least
  squares classifier, not logistic regression), features standardized on the training queries plus an
  intercept (not penalized); ridge strength chosen from a fixed grid by a seeded 80/20 split of the
  training queries, ties to the smaller strength, then refit on all training queries; float64,
  deterministic. A least-squares classifier can understate what a softmax probe extracts.
* **Attainable probability.** See ``attainable_answer_probability``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import torch
from torch.nn import functional as F

from . import core
from .core import AnswerScores, ChanceInterval
from .data import FactTable, Stream, StudyData, encode_identifiers, restrict_stream

if TYPE_CHECKING:
    from arborlm.p4_model import Backbone

_ALPHABET = torch.tensor(core.ALPHABET, dtype=torch.int64)
RIDGE_GRID = (1e-6, 1e-4, 1e-2, 1e0)
PROBE_FIT_FRACTION = 0.8
EXACT_LOGIT_GAP = 1.0e4  # exact retrieval's logit gap: probability 1 on the stored symbol in float32


# --- the frozen backbone ---------------------------------------------------------------------
def load_backbone(
    parent: tuple[int, int] = core.PRIMARY_PARENT, experiments_root: Path | None = None
) -> tuple["Backbone", dict[str, Any]]:
    """The verified frozen backbone of ``parent`` = (backbone, order), (101, 301) or (102, 302), read
    from the git-ignored ``experiments/`` of the main checkout (default) exactly as P8 does. Returns
    the backbone and its provenance record."""
    from arborlm import p8_core

    class _Parent:
        def __init__(self, backbone: int, order: int) -> None:
            self.order = order
            self.parent_label = f"b{backbone}-o{order}-baseline"

    root = experiments_root or core.default_experiments_root()
    return p8_core.load_backbone(_Parent(*parent), root)


def synthetic_backbone(backbone: int = 101, order: int = 301) -> "Backbone":
    """A random full-dimension backbone (27,392 parameters), not a verified parent; tests only."""
    from arborlm.p2_config import CONTROL
    from arborlm.p2_config import Cell as ParentCell
    from arborlm.p2_model import FollowupModel
    from arborlm.p4_model import extract

    return extract(FollowupModel(ParentCell(backbone, 201, order, CONTROL)))


def insertion_hidden(backbone: "Backbone", tokens: torch.Tensor) -> torch.Tensor:
    """``[B, T, 32]`` residual stream after the first frozen block (the memory insertion point) for
    ``tokens [B, T] int64`` (as P5's ``insertion_hidden``)."""
    t = tokens.shape[1]
    h = backbone.token(tokens) + backbone.position(torch.arange(t, device="cpu"))
    return backbone.blocks[0](h, backbone.mask[:t, :t])  # type: ignore[no-any-return]


def logits_from_hidden(backbone: "Backbone", h: torch.Tensor) -> torch.Tensor:
    """``[B, T, 256]`` logits of the frozen upper block, final norm and tied output for the residual
    stream ``h [B, T, 32]`` after block 0 (plus whatever has been added to it)."""
    t = h.shape[1]
    h = backbone.blocks[1](h, backbone.mask[:t, :t])
    return F.linear(backbone.final_norm(h), backbone.token.weight)


def answer_site_hidden(
    backbone: "Backbone", stream: Stream, *, batch_contexts: int = 64
) -> torch.Tensor:
    """``[Q, 32]`` frozen hidden states (after block 0) at every answer site, (context, record) order."""
    sites = list(core.ANSWER_SITE_POSITIONS)
    parts = []
    with torch.no_grad():
        for start in range(0, stream.tokens.shape[0], batch_contexts):
            tokens = stream.tokens[start : start + batch_contexts, : core.INPUT_LENGTH]
            parts.append(insertion_hidden(backbone, tokens)[:, sites].reshape(-1, 32))
    return torch.cat(parts)


def answer_site_logits_no_memory(
    backbone: "Backbone", stream: Stream, *, batch_contexts: int = 64
) -> torch.Tensor:
    """Frozen backbone with no addition, ``[Q, 256] float32`` logits at every answer site of
    ``stream`` in (context, record) order. CPU, FP32, no gradients (ADR 5.1)."""
    sites = list(core.ANSWER_SITE_POSITIONS)
    parts = []
    with torch.no_grad():
        for start in range(0, stream.tokens.shape[0], batch_contexts):
            tokens = stream.tokens[start : start + batch_contexts, : core.INPUT_LENGTH]
            logits = logits_from_hidden(backbone, insertion_hidden(backbone, tokens))
            parts.append(logits[:, sites].reshape(-1, 256).float())
    return torch.cat(parts)


def evaluate_no_memory(
    backbone: "Backbone", table: FactTable, stream: Stream, *, batch_contexts: int = 64
) -> AnswerScores:
    """No-memory baseline on ``stream`` (ADR 5.6): scores against the facts' answers."""
    logits = answer_site_logits_no_memory(backbone, stream, batch_contexts=batch_contexts)
    return core.score_answer_sites(logits, table.answer[stream.fact_ids].reshape(-1))


# --- exact retrieval -----------------------------------------------------------------------------
def exact_retrieval(table: FactTable, stream: Stream, known_ids: torch.Tensor) -> AnswerScores:
    """Dictionary lookup of ``known_ids`` (``[K] int64`` facts in the dictionary): probability 1 on
    the stored answer, so exactly 1.0 accuracy on trained facts; unseen facts get symbol index 0
    (core.OPEN_CHOICES c10), so their accuracy is exactly the count of chance matches (ADR 4.6
    check 4, D01). Also the append-only "exact retrieval" arm of Lane D (ADR 8.5).

    The lookup key is the identifier read from the stream's tokens (not the fact id), so the control
    does not use the stream's bookkeeping."""
    lut = torch.full((32**4,), -1, dtype=torch.int64)
    lut[encode_identifiers(table.ident[known_ids])] = table.answer[known_ids]
    c = stream.tokens.shape[0]
    byte_symbol = torch.full((256,), -1, dtype=torch.int64)
    byte_symbol[_ALPHABET] = torch.arange(core.ALPHABET_SIZE)
    symbols = byte_symbol[stream.tokens.reshape(c, 8, 8)[:, :, 1:6]].reshape(-1, 5)
    stored = lut[encode_identifiers(symbols)]
    predicted = torch.where(stored >= 0, stored, torch.zeros_like(stored))
    logits = torch.full((symbols.shape[0], 256), -EXACT_LOGIT_GAP, dtype=torch.float32)
    logits[torch.arange(symbols.shape[0]), _ALPHABET[predicted]] = 0.0
    return core.score_answer_sites(logits, table.answer[stream.fact_ids].reshape(-1))


# --- frozen-hidden probes ----------------------------------------------------------------------------
@dataclass
class ProbeResult:
    """A frozen-hidden probe (ADR 5.6): no memory involved. ``accuracy`` is over the answer-site
    queries of the evaluation stream; ``scores`` is None for probes that give only a hard prediction;
    ``per_query_correct [Q] bool`` allows splitting by neighbour, unseen or cluster."""

    name: str
    facts: int
    correct: int
    accuracy: float
    scores: AnswerScores | None
    per_query_correct: torch.Tensor | None = None


def _result(name: str, correct: torch.Tensor) -> ProbeResult:
    n = int(correct.numel())
    k = int(correct.sum())
    return ProbeResult(name, n, k, k / n, None, correct)


def nearest_stored_state_probe(
    backbone: "Backbone", table: FactTable, train: Stream, evaluate: Stream
) -> ProbeResult:
    """Predict, for each answer site of ``evaluate``, the answer stored with the nearest (cosine)
    frozen answer-site hidden state of ``train`` (hidden state after the first block, ``[32]``)."""
    stored = F.normalize(answer_site_hidden(backbone, train), dim=-1, eps=1e-8)
    stored_answer = table.answer[train.fact_ids].reshape(-1)
    queries = F.normalize(answer_site_hidden(backbone, evaluate), dim=-1, eps=1e-8)
    truth = table.answer[evaluate.fact_ids].reshape(-1)
    chunks = []
    for start in range(0, queries.shape[0], 1024):
        nearest = (queries[start : start + 1024] @ stored.T).argmax(dim=1)
        chunks.append(stored_answer[nearest])
    return _result("nearest_stored_state", torch.cat(chunks) == truth)


def _ridge(x: torch.Tensor, onehot: torch.Tensor, strength: float) -> torch.Tensor:
    n, d = x.shape
    penalty = torch.eye(d, dtype=torch.float64) * strength * n
    penalty[-1, -1] = 0.0  # the intercept is not penalized
    solution: torch.Tensor = torch.linalg.solve(
        x.T @ x + penalty + 1e-12 * torch.eye(d, dtype=torch.float64), x.T @ onehot
    )
    return solution


def linear_probe_per_position(
    backbone: "Backbone", table: FactTable, train: Stream, evaluate: Stream, *, seed: int
) -> list[ProbeResult]:
    """One 32-way linear probe per identifier position (five), trained on the frozen hidden states
    at the answer site (closed form or a fixed small number of full-batch steps; no memory).
    Target: the identifier symbol at that position. See the module docstring for the method."""
    x_train = answer_site_hidden(backbone, train).double()
    x_eval = answer_site_hidden(backbone, evaluate).double()
    mean, std = x_train.mean(0), x_train.std(0).clamp_min(1e-8)

    def design(x: torch.Tensor) -> torch.Tensor:
        return torch.cat([(x - mean) / std, torch.ones(x.shape[0], 1, dtype=torch.float64)], dim=1)

    d_train, d_eval = design(x_train), design(x_eval)
    ident_train = table.ident[train.fact_ids].reshape(-1, 5)
    ident_eval = table.ident[evaluate.fact_ids].reshape(-1, 5)
    n = d_train.shape[0]
    order = torch.randperm(n, generator=torch.Generator().manual_seed(seed))
    fit, held = order[: int(PROBE_FIT_FRACTION * n)], order[int(PROBE_FIT_FRACTION * n) :]
    results = []
    for position in range(core.IDENTIFIER_LENGTH):
        onehot = F.one_hot(ident_train[:, position], core.ALPHABET_SIZE).double()
        best_strength, best_accuracy = RIDGE_GRID[0], -1.0
        for strength in RIDGE_GRID:
            w = _ridge(d_train[fit], onehot[fit], strength)
            accuracy = float(((d_train[held] @ w).argmax(1) == ident_train[held, position]).double().mean())
            if accuracy > best_accuracy:
                best_strength, best_accuracy = strength, accuracy
        w = _ridge(d_train, onehot, best_strength)
        correct = (d_eval @ w).argmax(1) == ident_eval[:, position]
        results.append(_result(f"linear_probe_position_{position + 1}", correct))
    return results


# --- attainable probability --------------------------------------------------------------------------
def attainable_answer_probability(
    backbone: "Backbone",
    stream: Stream,
    *,
    max_norm: float | None = None,
    iterations: int = 200,
    lr: float = 0.1,
    batch_contexts: int = 256,
) -> dict[str, float]:
    """Largest probability of the correct symbol reachable through the frozen upper block and output
    layers by an additive change to the answer-site hidden state (linear algebra on frozen weights;
    ADR 12 step 4). Returns summary statistics (``mean``, ``median``, ``min``, ``max`` over
    answer sites) for the calibration record.

    Method. For each answer site, a vector ``delta [32]`` is added to the residual stream after block
    0 at that position only, and ``log softmax(logits)[correct byte]`` of the frozen second block, final
    norm and tied output is ascended with a fixed number of Adam steps (``iterations``, step ``lr``,
    ``delta`` starting at 0, no randomness, so the result is deterministic). The sequence is truncated
    at the site, which is exact because attention is causal. One record is perturbed per pass, so
    ``delta`` of one site never changes another site's read. The reported probability of a site is the
    best value over all iterates (the envelope), so it is monotone in ``iterations``. ``max_norm``
    projects ``delta`` onto that Euclidean ball (None: unconstrained).

    Reported keys: ``mean``/``median``/``min``/``max`` of the full 256-way softmax probability;
    ``sigma_*`` the same for the probability renormalized over the alphabet (the best iterate of that
    quantity, not separately optimized); ``baseline_mean`` at ``delta = 0`` (the no-memory value);
    ``fraction_at_least_0.95`` of the full probability; ``queries``, ``iterations``, ``lr`` and
    ``max_norm`` (-1 when None).

    Limits. (1) A non-convex objective ascended by a fixed schedule gives a lower bound on the supremum.
    (2) Only the answer-site hidden state moves; the real memory also changes the hidden states at the
    earlier positions that the site attends to, and it produces ``delta`` from a bounded read, so this
    is neither an upper bound nor an achievable value for a trained memory. (3) Unconstrained, the
    norm of ``delta`` is unbounded and the result is a property of the frozen layers (layer norm and
    tied output), not of any memory; the ``max_norm`` variant shows the dependence on the norm.
    (4) Each site gets its own ``delta`` (an oracle that knows the answer), so it bounds nothing about
    what a memory can learn from the identifier alone."""
    n_contexts = stream.tokens.shape[0]
    targets = stream.answer_targets()  # [C, 8]
    best_full = torch.zeros(n_contexts, 8)
    best_sigma = torch.zeros(n_contexts, 8)
    base_full = torch.zeros(n_contexts, 8)
    norms = torch.zeros(n_contexts, 8)
    for record in range(core.RECORDS_PER_CONTEXT):
        site = core.answer_site_position(record)
        for start in range(0, n_contexts, batch_contexts):
            sl = slice(start, start + batch_contexts)
            tokens = stream.tokens[sl, : site + 1]
            with torch.no_grad():
                h_pre = insertion_hidden(backbone, tokens)
            b = tokens.shape[0]
            rows = torch.arange(b)
            symbol = targets[sl, record]
            byte = _ALPHABET[symbol]
            delta = torch.zeros(b, 32, requires_grad=True)
            optimizer = torch.optim.Adam([delta], lr=lr)
            best_f = torch.zeros(b)
            best_s = torch.zeros(b)
            for step in range(iterations + 1):
                h = torch.cat([h_pre[:, :site], h_pre[:, site : site + 1] + delta[:, None]], dim=1)
                logits = logits_from_hidden(backbone, h)[:, site]
                logp = logits.log_softmax(-1)[rows, byte]
                with torch.no_grad():
                    p_full = logp.exp()
                    p_sigma = logits[:, _ALPHABET].softmax(-1)[rows, symbol]
                    if step == 0:
                        base_full[sl, record] = p_full
                    best_f = torch.maximum(best_f, p_full)
                    best_s = torch.maximum(best_s, p_sigma)
                if step == iterations:
                    break
                optimizer.zero_grad()
                (-logp.sum()).backward()  # type: ignore[no-untyped-call]
                optimizer.step()
                if max_norm is not None:
                    with torch.no_grad():
                        scale = (max_norm / delta.norm(dim=1, keepdim=True).clamp_min(1e-12)).clamp(max=1.0)
                        delta.mul_(scale)
            best_full[sl, record], best_sigma[sl, record] = best_f, best_s
            norms[sl, record] = delta.detach().norm(dim=1)
    full, sigma = best_full.reshape(-1), best_sigma.reshape(-1)
    return {
        "mean": float(full.mean()),
        "median": float(full.median()),
        "min": float(full.min()),
        "max": float(full.max()),
        "sigma_mean": float(sigma.mean()),
        "sigma_median": float(sigma.median()),
        "sigma_min": float(sigma.min()),
        "sigma_max": float(sigma.max()),
        "baseline_mean": float(base_full.mean()),
        "fraction_at_least_0.95": float((full >= 0.95).float().mean()),
        "final_delta_norm_mean": float(norms.mean()),
        "queries": float(full.numel()),
        "iterations": float(iterations),
        "lr": lr,
        "max_norm": -1.0 if max_norm is None else float(max_norm),
    }


# --- G2 ------------------------------------------------------------------------------------------------
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
    results: list[G2Test] = []
    for name, (correct, facts) in counts.items():
        interval = core.chance_interval(facts, tests)
        results.append(
            G2Test(
                name=name,
                facts=facts,
                correct=correct,
                interval=(interval.low, interval.high),
                inside=interval.low <= correct <= interval.high,
            )
        )
    return G2Report(
        tests=tests,
        level=core.g2_level(tests),
        results=results,
        passed=all(r["inside"] for r in results),
    )


def unseen_leakage(correct: int, facts: int, tests: int = 8) -> bool:
    """LEAKAGE flag (ADR 8.1): the unseen-fact accuracy of a trained cell lies outside the interval."""
    interval = core.chance_interval(facts, tests)
    return not interval.low <= correct <= interval.high


def chance_intervals_for_registered_sets() -> dict[str, ChanceInterval]:
    """The G2 intervals for 2,048 / 8,192 / 32,768 facts (tests = 8) and 4,096 (tests = 4)."""
    out = {
        f"facts_{n}": core.chance_interval(n, core.G2_TESTS_PRIMARY)
        for n in core.FACTS_PROPORTIONAL.values()
    }
    out[f"lane_d_facts_{core.LANE_D_FACTS}"] = core.chance_interval(
        core.LANE_D_FACTS, core.G2_TESTS_LANE_D
    )
    return out


# --- the controls record read by analysis_a / analysis_d (integration, package I7) -----------------------
def _counts(scores: AnswerScores, mask: torch.Tensor) -> dict[str, int]:
    return {"correct": int(scores.correct[mask].sum()), "facts": int(mask.sum())}


def proportional_fact_counts() -> list[int]:
    """Distinct proportional-track fact counts of the ACTIVE registry (2,048 / 8,192 / 32,768; scaled in
    the DRY profile), sorted."""
    return sorted(
        {c.facts for c in core.cells_of_block("A1") if c.parent == core.PRIMARY_PARENT}
    )


def no_memory_counts(
    backbone: "Backbone", data: StudyData, panel_stream: str
) -> dict[str, dict[str, int]]:
    """``{"<F>": {correct, facts}, ..., "unseen": {correct, facts}}`` for one primary panel: the
    no-memory baseline on the F-fact sets (the panel restricted to F facts) and on the unseen set (ADR
    8.1 G2). Counts are answer sites, one per fact."""
    out: dict[str, dict[str, int]] = {}
    full = data.streams[panel_stream]
    for facts in proportional_fact_counts():
        stream = restrict_stream(full, data.facts, facts)
        scores = evaluate_no_memory(backbone, data.facts, stream)
        ids = stream.fact_ids.reshape(-1)
        out[str(facts)] = _counts(scores, ids < facts)
        if facts == proportional_fact_counts()[-1]:
            out["unseen"] = _counts(scores, ids >= data.facts.trained)
    return out


def controls_record(
    data: StudyData,
    backbones: Mapping[tuple[int, int], "Backbone"],
    *,
    g1: Mapping[str, Any] | None = None,
    g4: Mapping[str, Any] | None = None,
    probes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``controls`` mapping that ``analysis_a.analyze`` / ``analysis_d.analyze`` read (layout in the
    ``analysis_a`` docstring), measured on the draw ``data`` (no trained memory involved):

    * ``g1`` ``{"passed", "failed_checks"}`` from the generator report; ``g4`` ``{"passed", "defects", ...}``
      as given (None when no report exists: the analysis prints GATES NOT REPORTED);
    * ``no_memory[panel_a|panel_b]`` per fact count and ``unseen`` for the primary parent; Lane D sets
      ``lane_d_<p>_<S>`` (``{correct, facts}``);
    * ``no_memory_replicate`` the same panel entries for parent B102 (reported, read by no rule: ADR 8.1
      does not say which parent the G2 family uses; PENDING LEAD REVIEW);
    * ``exact_accuracy[str(slots)]`` exact retrieval on the trained facts of Panel A at that size and
      ``exact_lane_d`` (append arm);
    * ``probes`` as given (calibration output) and ``g2`` the interval report of the primary family.
    """
    from . import incremental  # lazy: incremental imports train

    primary = backbones[core.PRIMARY_PARENT]
    no_memory: dict[str, Any] = {
        "panel_a": no_memory_counts(primary, data, "panel_a"),
        "panel_b": no_memory_counts(primary, data, "panel_b"),
    }
    for panel in ("a", "b"):
        for which in ("A", "B"):
            name = f"lane_d_{panel}_{which}"
            stream = data.streams[name]
            scores = evaluate_no_memory(primary, data.lane_d, stream)
            no_memory[name] = _counts(scores, torch.ones(scores.correct.shape[0], dtype=torch.bool))
    replicate = backbones.get(core.REPLICATE_PARENT)
    record: dict[str, Any] = {
        "g1": None
        if g1 is None
        else {
            "passed": bool(g1["passed"]),
            "failed_checks": [c["name"] for c in g1.get("checks", []) if not c["passed"]],
        },
        "g4": None if g4 is None else dict(g4),
        "no_memory": no_memory,
        "no_memory_replicate": None
        if replicate is None
        else {
            "panel_a": no_memory_counts(replicate, data, "panel_a"),
            "panel_b": no_memory_counts(replicate, data, "panel_b"),
        },
        "probes": None if probes is None else dict(probes),
    }
    if record["g1"] is None:
        del record["g1"]
    if record["g4"] is None:
        del record["g4"]
    exact: dict[str, float] = {}
    for cell in core.cells_of_block("A1"):
        if cell.parent != core.PRIMARY_PARENT or cell.seed != core.INIT_SEEDS[0]:
            continue
        stream = restrict_stream(data.streams["panel_a"], data.facts, cell.facts)
        scores = exact_retrieval(data.facts, stream, torch.arange(data.facts.trained))
        trained = stream.fact_ids.reshape(-1) < cell.facts
        exact[str(cell.slots)] = float(scores.correct[trained].float().mean())
    record["exact_accuracy"] = exact
    record["exact_lane_d"] = [
        dict(m.__dict__) for m in incremental.exact_append_control(data)
    ]
    primary_counts = {
        f"{panel}/{name}": (v["correct"], v["facts"])
        for panel in ("panel_a", "panel_b")
        for name, v in no_memory[panel].items()
    }
    record["g2"] = {
        "primary": dict(g2_report(primary_counts, core.G2_TESTS_PRIMARY)),
        "lane_d": dict(
            g2_report(
                {n: (v["correct"], v["facts"]) for n, v in no_memory.items() if n.startswith("lane_d")},
                core.G2_TESTS_LANE_D,
            )
        ),
    }
    return record
