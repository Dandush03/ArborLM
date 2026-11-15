# ruff: noqa: E501
"""P9 evaluation (package I3): cached selections and weights, accuracy, I_acc with the chance floor,
log-loss gain, seven-position knock-outs, minimal supports, U*, specificity, group ablation, value
permutation and disabling, usage statistics, the LEAKAGE check and trace export.

Specification: ADR-0017 section 6.1 (knowledge), 6.2 (useful slots), 6.3 (per-snapshot optimization
quantities), 7 (soft against hard usage), 8.1 (LEAKAGE), 8.4 (traces). Self-checked only: not
independent review, not Astra validation, not human approval.

Cached evaluation (budget requirement): one forward per (snapshot, stream) builds a ``ReadCache``
(``h_pre`` after the first block, the selections and the read weights). Value permutation, disabling,
knock-outs and group ablations reuse it through ``P9Model.memory_delta`` and the frozen upper block and
need no further key scoring. ``ReadCache`` is valid only for the model (parameters) it was built from.

Everything is computed per snapshot and per stream; ``evaluate_snapshot`` returns ``core.EvalRecord``.
Accuracy uses ``core.score_answer_sites`` (most probable symbol within the alphabet, ties wrong) and
``core.information_bits`` (I_acc with the chance floor at the G2 interval for the stream's fact count).
Facts are counted per answer-site instance: a stream that holds a fact twice (calibration) counts it
twice. Accuracy, I_acc and every intervention are over trained facts only; the unseen controls of a
panel are scored separately (``unseen_correct``, ``unseen_facts``, ``leakage``).

Complexity (C contexts, F = 8 C answer sites, P read positions, N slots, kw key width, B the cost of
the frozen upper block on one position, about 14 K multiply-adds):

* ``build_cache``: one scoring pass, O(C P N kw) plus top-64 selection. The only pass that scores keys.
* value permutation, disabling: one upper pass each, O(C 63 B).
* group ablation: at most 64 upper passes, each only over the contexts that read a slot of the group.
* minimal supports: round k evaluates prefix k of every still unresolved fact on the record's causal
  prefix only (sequence length 8 r + 7, mean 31.5 positions) and recomputes the memory delta only at
  the record's read positions. At most K_f <= 7 * 8 = 56 rounds per fact (the union of its seven
  positions' selections); a fact leaves the rounds as soon as its prefix breaks it, so the cost is
  O(F (s + 1) 31.5 B) for a mean support length s, and O(F 56 31.5 B) at worst. Batched over facts.
* specificity condition 1: one truncated evaluation per fact; condition 2: the group ablation above.

Readings the ADR leaves open (all PENDING LEAD REVIEW, reported to the lead):

* Specificity condition 1 applied literally (removal "wherever selected" at the record's seven
  positions) cannot do anything: the drawn slots are excluded from every slot selected in the record,
  so the change in p_f is identically zero. ``specificity(..., scope="context")`` (the default) applies
  the removal at every position of the fact's context up to its answer site, which contains the
  literal reading as a special case; ``scope="record"`` gives the literal reading.
* "Every slot selected in the fact's own record" is read as the slots selected at the record's input
  positions 8r .. 8r + 7 (the answer byte's own position included where it is an input).
* Condition 1 is evaluated over every trained answer-site fact of the stream, not only correct facts.
  Condition 2 requires every one of the 64 groups to stay within 0.02, for the facts that have a
  minimal support avoiding that group (those facts are correct at baseline by definition).
* "Share of correct facts that stay correct when the whole answer-site read is removed" removes the
  fact's own answer-site read only (every slot selected at position 8r + 6, one fact at a time).
* Value permutation is a seeded cyclic derangement of the table rows (no slot keeps its own value).
"""

import argparse
import hashlib
import io
import math
import sys
from dataclasses import dataclass, field
from functools import cache as memoize
from pathlib import Path
from typing import Any, cast

import torch
from torch import Tensor
from torch.nn import functional as F

from . import controls, core
from .core import AnswerScores, Cell, EvalRecord, Trace
from .data import (
    FactTable,
    Stream,
    StudyData,
    facts_of,
    identifier_lut,
    neighbour_flags,
    panel_streams,
    restrict_stream,
)
from .model import P9Model, Selection, build_model
from .objective import slot_usage, soft_inclusion_full, usage_entropy
from .train import load_snapshot

VOCAB = 256
TOP = core.TOP
SOFT_TOP = core.SOFT_TOP
SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
TREE_ARCHS = ("fixed_tree", "learned_tree")
TRACE_BLOCKS = (
    "A1",
    "A2",
    "B1",
    "C1",
)  # cells whose traces feed the locality lane (D09); lead to confirm
TRACE_STREAMS = ("panel_a", "panel_b", "calibration")
SPECIFICITY_SCOPE = "context"
SUPPORT_CHUNK = 1024  # facts per upper-block batch (bounds the attention matrices)
MARGIN_KEYS = ("q00", "q05", "q25", "q50", "q75", "q95", "q100")
MARGIN_QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)


# --- small helpers -----------------------------------------------------------------------------------------
def _seed(seed: int, *tags: object) -> int:
    """A 62-bit seed derived from ``seed`` and tags (SHA-256)."""
    text = "|".join([str(seed), "evaluate", *map(str, tags)]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "little") & ((1 << 62) - 1)


@memoize
def _identity() -> core.Identity:
    return core.code_identity()


def _table(data: StudyData, stream: Stream) -> FactTable:
    return data.facts if stream.world == "main" else data.lane_d


def _subset(scores: AnswerScores, mask: Tensor) -> AnswerScores:
    return AnswerScores(
        logp_sigma=scores.logp_sigma[mask],
        p_correct=scores.p_correct[mask],
        correct=scores.correct[mask],
        mass_sigma=scores.mass_sigma[mask],
        answer=scores.answer[mask],
    )


def _rows(sel: Selection, index: Any) -> Selection:
    """The contexts ``index`` of a cached selection (no candidate fields, no route scores)."""
    return Selection(
        positions=sel.positions,
        selected=sel.selected[index],
        scores=sel.scores[index],
        candidate_ids=None,
        candidate_scores=None,
        branches=None if sel.branches is None else sel.branches[index],
        route_scores=None,
        length=sel.length,
    )


def _finish_sites(model: P9Model, h_pre: Tensor, delta: Tensor) -> Tensor:
    """``[B, 8, 256]`` answer-site logits of ``P9Model.finish`` (the same operations, the output
    projection applied to the eight answer sites only; the final norm acts per position)."""
    bb = model.backbone
    t = h_pre.shape[1]
    h = cast(Tensor, bb.blocks[1](h_pre + delta, bb.mask[:t, :t]))
    return F.linear(bb.final_norm(h[:, SITES]), bb.token.weight)


def _score_last(model: P9Model, x: Tensor, answer: Tensor) -> AnswerScores:
    """Scores at the last position of ``x [n, L, 32]`` (the block-1 input of a causal prefix)."""
    bb = model.backbone
    length = x.shape[1]
    h = cast(Tensor, bb.blocks[1](x, bb.mask[:length, :length]))[:, -1]
    return core.score_answer_sites(F.linear(bb.final_norm(h), bb.token.weight), answer)


# --- the read cache ------------------------------------------------------------------------------------------
@dataclass
class ReadCache:
    """One forward over a stream. ``tokens [C, 64] int64``; ``h_pre [C, 63, 32] float32``;
    ``selection`` covers all C contexts (``selected [C, P, 8]``, ``scores [C, P, 8]``, ``branches``
    for trees); ``logits_answer [C, 8, 256] float32`` the logits at the answer sites of the unmodified
    model; ``stream`` is the stream evaluated.

    Additions to the stub (reported): the candidate fields of ``selection`` are None and ``route_scores``
    is dropped (at 65,536 slots they would take about 0.4 GiB per panel); the answer-site candidates
    that the soft usage statistics need are kept in ``site_candidate_ids / site_candidate_scores
    [C, 8, 64]``; ``slots`` is the memory size; ``selection`` is None for the dense adapter."""

    stream: Stream
    tokens: Tensor
    h_pre: Tensor
    selection: Selection | None
    logits_answer: Tensor
    site_candidate_ids: Tensor | None = None
    site_candidate_scores: Tensor | None = None
    slots: int = 0
    _upper: Any = field(default=None, repr=False, compare=False)


def site_columns(selection: Selection) -> list[int]:
    """Columns of ``selection`` that are the eight answer-site positions."""
    positions = selection.positions.tolist()
    return [positions.index(p) for p in core.ANSWER_SITE_POSITIONS]


@torch.no_grad()
def build_cache(model: P9Model, stream: Stream, *, batch_contexts: int = 64) -> ReadCache:
    """Run ``model`` once over ``stream`` (no gradients, CPU, FP32) and cache the reads."""
    was_training = model.training
    model.eval()
    try:
        tokens = stream.tokens
        h_parts, logit_parts = [], []
        selected, scores, branches, cand_ids, cand_scores = [], [], [], [], []
        positions: Tensor | None = None
        for start in range(0, tokens.shape[0], batch_contexts):
            inp = tokens[start : start + batch_contexts, : core.INPUT_LENGTH].contiguous()
            h = model.embed_block0(inp)
            sel = model.select(h, inp)
            logit_parts.append(_finish_sites(model, h, model.memory_delta(h, sel)))
            h_parts.append(h)
            if sel is None:
                continue
            positions = sel.positions
            selected.append(sel.selected)
            scores.append(sel.scores)
            if sel.branches is not None:
                branches.append(sel.branches)
            if sel.candidate_ids is not None and sel.candidate_scores is not None:
                cols = site_columns(sel)
                cand_ids.append(sel.candidate_ids[:, cols])
                cand_scores.append(sel.candidate_scores[:, cols])
    finally:
        model.train(was_training)
    selection: Selection | None = None
    if positions is not None:
        selection = Selection(
            positions=positions,
            selected=torch.cat(selected),
            scores=torch.cat(scores),
            candidate_ids=None,
            candidate_scores=None,
            branches=torch.cat(branches) if branches else None,
            route_scores=None,
            length=core.INPUT_LENGTH,
        )
    return ReadCache(
        stream=stream,
        tokens=tokens,
        h_pre=torch.cat(h_parts),
        selection=selection,
        logits_answer=torch.cat(logit_parts),
        site_candidate_ids=torch.cat(cand_ids) if cand_ids else None,
        site_candidate_scores=torch.cat(cand_scores) if cand_scores else None,
        slots=model.spec.slots,
    )


def score_cache(cache: ReadCache, table_answers: Tensor) -> AnswerScores:
    """``AnswerScores`` over the ``C * 8`` answer sites of the cache (context, record order);
    ``table_answers [C * 8] int64`` are the answer symbol indices (``Stream.answer_targets``)."""
    return core.score_answer_sites(cache.logits_answer.reshape(-1, VOCAB), table_answers)


@torch.no_grad()
def _logits_core(
    model: P9Model,
    cache: ReadCache,
    rows: Tensor | None,
    *,
    knockout: Tensor | None,
    values: Tensor | None,
    disabled: bool,
    batch_contexts: int,
) -> Tensor:
    index = torch.arange(cache.tokens.shape[0]) if rows is None else rows
    parts = []
    for start in range(0, index.shape[0], batch_contexts):
        chunk = index[start : start + batch_contexts]
        h = cache.h_pre[chunk]
        sel = None if cache.selection is None else _rows(cache.selection, chunk)
        ko = None if knockout is None else knockout[chunk]
        delta = model.memory_delta(h, sel, knockout=ko, values=values, disabled=disabled)
        parts.append(_finish_sites(model, h, delta))
    if not parts:
        return torch.zeros((0, core.ANSWER_SITES_PER_CONTEXT, VOCAB))
    return torch.cat(parts)


def logits_with(
    model: P9Model,
    cache: ReadCache,
    *,
    knockout: Tensor | None = None,
    values: Tensor | None = None,
    disabled: bool = False,
    batch_contexts: int = 64,
) -> Tensor:
    """``[C, 8, 256]`` answer-site logits with an intervention applied to the cached reads: ``knockout
    [C, P, 8] bool`` removes those slots' values from the weighted sum (selections and weights as
    cached), ``values [N, 32]`` replaces the value table, ``disabled`` removes the memory."""
    return _logits_core(
        model,
        cache,
        None,
        knockout=knockout,
        values=values,
        disabled=disabled,
        batch_contexts=batch_contexts,
    )


def permute_values(model: P9Model, seed: int) -> Tensor:
    """``[N, 32]`` value table permuted over slots with a seeded generator (value permutation,
    ADR 5.6; accuracy must fall to chance). The permutation is a cyclic derangement: slot ``perm[i]``
    receives the value of slot ``perm[i + 1]``, so no slot keeps its own value."""
    table = getattr(model.addition, "values", None)
    if table is None:
        raise ValueError("the dense adapter has no value table")
    n = int(table.shape[0])
    if n < 2:
        raise ValueError("a permutation needs at least two slots")
    perm = torch.randperm(n, generator=torch.Generator().manual_seed(seed))
    source = table.detach()
    out = torch.empty_like(source)
    out[perm] = source[perm.roll(-1)]
    return out


# --- the upper-block evaluator over cached reads ------------------------------------------------------------
class _Upper:
    """Per-snapshot constants for evaluating one fact at a time on its causal prefix: the unmodified
    block-1 input ``base_x = h_pre + delta`` of every context and the read columns of each record."""

    def __init__(self, model: P9Model, cache: ReadCache) -> None:
        sel = cache.selection
        if sel is None:
            raise ValueError("the dense adapter has no reads to knock out")
        self.model_id = id(model)
        parts = []
        for start in range(0, cache.tokens.shape[0], 64):
            chunk = slice(start, start + 64)
            parts.append(model.memory_delta(cache.h_pre[chunk], _rows(sel, chunk)))
        self.base_x = cache.h_pre + torch.cat(parts)
        pos = sel.positions.tolist()
        rb = core.RECORD_BYTES
        self.record_cols = [
            [i for i, p in enumerate(pos) if rb * r <= p <= rb * r + 6] for r in range(8)
        ]
        self.record_cols_wide = [
            [i for i, p in enumerate(pos) if rb * r <= p <= min(rb * r + 7, core.INPUT_LENGTH - 1)]
            for r in range(8)
        ]
        self.site_local = [
            self.record_cols[r].index(pos.index(core.answer_site_position(r))) for r in range(8)
        ]
        self.positions = sel.positions

    def local(
        self,
        model: P9Model,
        cache: ReadCache,
        ctx: Tensor,
        r: int,
        knockout: Tensor,
        answer: Tensor,
    ) -> AnswerScores:
        """Facts of record ``r`` in contexts ``ctx``: block-1 evaluation on the causal prefix of
        ``8 r + 7`` positions, the memory delta recomputed at the record's read positions with
        ``knockout [n, Pr, 8]`` (over ``record_cols[r]``), everything else as cached."""
        sel = cast(Selection, cache.selection)
        length = core.RECORD_BYTES * r + 7
        cols = torch.tensor(self.record_cols[r], dtype=torch.int64)
        sub = Selection(
            positions=sel.positions[cols],
            selected=sel.selected[ctx[:, None], cols[None, :]],
            scores=sel.scores[ctx[:, None], cols[None, :]],
            candidate_ids=None,
            candidate_scores=None,
            branches=None,
            route_scores=None,
            length=length,
        )
        h = cache.h_pre[ctx, :length]
        delta = model.memory_delta(h, sub, knockout=knockout)
        x = self.base_x[ctx, :length].clone()
        p = sub.positions
        x[:, p] = h[:, p] + delta[:, p]
        return _score_last(model, x, answer)

    def context(
        self,
        model: P9Model,
        cache: ReadCache,
        ctx: Tensor,
        r: int,
        slots: Tensor,
        answer: Tensor,
        *,
        only_record: bool,
    ) -> AnswerScores:
        """Facts of record ``r``: the values of ``slots [n, m]`` removed wherever they are selected at
        positions up to the answer site (``only_record``: only at the record's own read positions)."""
        sel = cast(Selection, cache.selection)
        length = core.RECORD_BYTES * r + 7
        ncols = int((sel.positions < length).sum())
        selected = sel.selected[ctx][:, :ncols]
        ko = (selected[..., None] == slots[:, None, None, :]).any(-1)
        if only_record:
            keep = torch.zeros(ncols, dtype=torch.bool)
            for c in self.record_cols_wide[r]:
                if c < ncols:
                    keep[c] = True
            ko &= keep[None, :, None]
        sub = Selection(
            positions=sel.positions[:ncols],
            selected=selected,
            scores=sel.scores[ctx][:, :ncols],
            candidate_ids=None,
            candidate_scores=None,
            branches=None,
            route_scores=None,
            length=length,
        )
        h = cache.h_pre[ctx, :length]
        x = h + model.memory_delta(h, sub, knockout=ko)
        return _score_last(model, x, answer)


def _upper(model: P9Model, cache: ReadCache) -> _Upper:
    up = cache._upper
    if up is None or up.model_id != id(model):
        up = _Upper(model, cache)
        cache._upper = up
    return cast(_Upper, up)


# --- minimal supports ----------------------------------------------------------------------------------------
@dataclass
class SupportResult:
    """Minimal supports (ADR 6.2). ``length [C * 8] int64`` shortest-prefix size (0 when none, i.e.
    the fact is answered incorrectly or no prefix breaks it); ``has_support [C * 8] bool``; ``slots``
    the support slot ids per fact (ragged list of int lists); ``useful`` the sorted ids of useful slots
    (their count is U*); ``removing_site_read_stays_correct [C * 8] bool`` (the fact is correct and
    stays correct when its own answer-site read is removed). ``searched [C * 8] bool`` marks the facts
    the search ran for."""

    length: Tensor
    has_support: Tensor
    slots: list[list[int]]
    useful: list[int]
    removing_site_read_stays_correct: Tensor
    searched: Tensor | None = None


def _candidates(ids: Tensor, w: Tensor) -> tuple[Tensor, Tensor]:
    """Distinct slots of ``ids [n, Pr, 8]`` ordered by summed weight (``w [n, Pr, 8]``) descending, ties
    by slot id ascending; ``(cand [n, Pr * 8] padded with -2, count [n])``. Ids below 0 are not slots."""
    n, pr, k = ids.shape
    m = pr * k
    flat = ids.reshape(n, m)
    wf = w.reshape(n, m)
    valid = flat >= 0
    eq = (flat[:, :, None] == flat[:, None, :]) & valid[:, :, None] & valid[:, None, :]
    total = (eq.to(wf.dtype) * wf[:, None, :]).sum(-1)
    first = valid & ~torch.tril(eq, diagonal=-1).any(-1)
    big = torch.iinfo(torch.int64).max
    by_id = torch.where(first, flat, torch.full_like(flat, big)).argsort(dim=1, stable=True)
    flat1, total1, first1 = flat.gather(1, by_id), total.gather(1, by_id), first.gather(1, by_id)
    order = torch.where(first1, -total1, torch.full_like(total1, math.inf)).argsort(
        dim=1, stable=True
    )
    count = first.sum(1)
    cand = flat1.gather(1, order)
    cand = torch.where(torch.arange(m)[None, :] < count[:, None], cand, torch.full_like(cand, -2))
    return cand, count


def _support_thresholds(nomem: AnswerScores) -> Tensor:
    return torch.maximum(
        nomem.p_correct + core.SUPPORT_P_MARGIN, torch.tensor(core.SUPPORT_P_ABSOLUTE)
    )


@torch.no_grad()
def minimal_supports(
    model: P9Model,
    cache: ReadCache,
    nomem: AnswerScores,
    scores: AnswerScores,
    *,
    facts: Tensor | None = None,
    chunk: int = SUPPORT_CHUNK,
) -> SupportResult:
    """For every correctly answered fact: candidates are the union of slots selected at the record's
    seven input positions ordered by summed weight; the minimal support is the shortest prefix whose
    knock-out (values removed at the answer site and the six earlier positions, wherever those slots
    are selected) makes p_f <= max(2/32, p_f_nomem + 0.02) (``core.SUPPORT_P_*``) and the fact
    incorrect. The rungs that read only at answer sites have the answer-site read as their only
    position. ``facts [C * 8] bool`` (keyword-only addition) restricts the search to those facts
    (default: every correct fact); a fact it excludes has no support."""
    up = _upper(model, cache)
    sel = cast(Selection, cache.selection)
    q = cache.tokens.shape[0] * core.ANSWER_SITES_PER_CONTEXT
    searched = scores.correct.clone() if facts is None else (scores.correct & facts)
    threshold = _support_thresholds(nomem)
    length = torch.zeros(q, dtype=torch.int64)
    stays = torch.zeros(q, dtype=torch.bool)
    slots: list[list[int]] = [[] for _ in range(q)]
    record_of = torch.arange(q) % core.ANSWER_SITES_PER_CONTEXT
    for r in range(core.RECORDS_PER_CONTEXT):
        cols = torch.tensor(up.record_cols[r], dtype=torch.int64)
        group = (searched & (record_of == r)).nonzero().squeeze(1)
        for start in range(0, group.shape[0], chunk):
            idx = group[start : start + chunk]
            ctx = idx // core.ANSWER_SITES_PER_CONTEXT
            ids = sel.selected[ctx[:, None], cols[None, :]]
            weights = sel.scores[ctx[:, None], cols[None, :]].softmax(-1)
            cand, count = _candidates(ids, weights)
            answer = scores.answer[idx]
            # the whole answer-site read removed, this fact only
            site = torch.zeros(ids.shape, dtype=torch.bool)
            site[:, up.site_local[r]] = True
            stays[idx] = up.local(model, cache, ctx, r, site, answer).correct
            # prefix rounds
            knock = torch.zeros(ids.shape, dtype=torch.bool)
            open_rows = count > 0
            found = torch.zeros(idx.shape[0], dtype=torch.int64)
            for k in range(1, int(count.max()) + 1 if idx.numel() else 1):
                act = (open_rows & (count >= k)).nonzero().squeeze(1)
                if act.numel() == 0:
                    break
                knock[act] |= ids[act] == cand[act, k - 1][:, None, None]
                result = up.local(model, cache, ctx[act], r, knock[act], answer[act])
                broken = ~result.correct & (result.p_correct <= threshold[idx[act]])
                done = act[broken]
                found[done] = k
                open_rows[done] = False
            length[idx] = found
            for row in (found > 0).nonzero().squeeze(1).tolist():
                slots[int(idx[row])] = cand[row, : int(found[row])].tolist()
    useful = sorted({s for fact in slots for s in fact})
    return SupportResult(
        length=length,
        has_support=length > 0,
        slots=slots,
        useful=useful,
        removing_site_read_stays_correct=stays,
        searched=searched,
    )


# --- specificity ---------------------------------------------------------------------------------------------
def _draw_other_slots(pool: Tensor, own: Tensor, generator: torch.Generator, count: int) -> Tensor:
    """For each row, ``count`` distinct slots drawn uniformly from ``pool`` without those in ``own
    [n, k]`` (ids below 0 ignored); rows with too few valid draws are padded with -2."""
    n = own.shape[0]
    m = 8 * count
    draws = pool[torch.randint(0, pool.shape[0], (n, m), generator=generator)]
    bad = (draws[:, :, None] == own[:, None, :]).any(-1)
    dup = torch.tril(draws[:, :, None] == draws[:, None, :], diagonal=-1).any(-1)
    ok = ~(bad | dup)
    rank = ok.cumsum(1)
    take = ok & (rank <= count)
    out = torch.full((n, count), -2, dtype=torch.int64)
    slot = (rank - 1).clamp_min(0)
    rows = torch.arange(n)[:, None].expand(n, m)
    out[rows[take], slot[take]] = draws[take]
    return out


@torch.no_grad()
def specificity(
    model: P9Model,
    cache: ReadCache,
    supports: SupportResult,
    scores: AnswerScores,
    *,
    seed: int,
    facts: Tensor | None = None,
    scope: str = SPECIFICITY_SCOPE,
    chunk: int = SUPPORT_CHUNK,
) -> dict[str, Any]:
    """The two conditions for interpreting U* (ADR 6.2): (1) knocking out 8 slots drawn from other
    facts' minimal supports, excluding every slot selected in the fact's own record, changes p_f by
    less than 0.05 on at least 95% of facts; (2) zeroing the values of one of 64 contiguous slot
    groups at all positions, selections kept, leaves facts whose minimal support avoids the group
    within 0.02 accuracy. Returns ``{"condition_1", "condition_2", "interpretable", ...details}``.
    ``facts`` (default every answer site) are the facts condition 1 is tested on; ``scope`` is
    explained in the module docstring."""
    if scope not in ("context", "record"):
        raise ValueError("scope must be 'context' or 'record'")
    up = _upper(model, cache)
    sel = cast(Selection, cache.selection)
    q = cache.tokens.shape[0] * core.ANSWER_SITES_PER_CONTEXT
    tested = torch.ones(q, dtype=torch.bool) if facts is None else facts
    record_of = torch.arange(q) % core.ANSWER_SITES_PER_CONTEXT
    pool = torch.tensor(supports.useful, dtype=torch.int64)

    # condition 1 -----------------------------------------------------------------------------------
    unchanged = torch.zeros(q, dtype=torch.bool)
    drawn_total = 0
    evaluated = torch.zeros(q, dtype=torch.bool)
    if pool.numel() > 0:
        generator = torch.Generator().manual_seed(_seed(seed, "specificity"))
        for r in range(core.RECORDS_PER_CONTEXT):
            cols_wide = torch.tensor(up.record_cols_wide[r], dtype=torch.int64)
            group = (tested & (record_of == r)).nonzero().squeeze(1)
            for start in range(0, group.shape[0], chunk):
                idx = group[start : start + chunk]
                ctx = idx // core.ANSWER_SITES_PER_CONTEXT
                own = sel.selected[ctx[:, None], cols_wide[None, :]].reshape(idx.shape[0], -1)
                other = _draw_other_slots(pool, own, generator, core.SPECIFICITY_OTHER_SLOTS)
                after = up.context(
                    model, cache, ctx, r, other, scores.answer[idx], only_record=scope == "record"
                )
                change = (after.p_correct - scores.p_correct[idx]).abs()
                unchanged[idx] = change < core.SPECIFICITY_DELTA
                evaluated[idx] = True
                drawn_total += int((other >= 0).sum())
    n_eval = int(evaluated.sum())
    share = float(unchanged[evaluated].float().mean()) if n_eval else 1.0
    condition_1 = share >= core.SPECIFICITY_SHARE

    # condition 2 -----------------------------------------------------------------------------------
    table = cast(Tensor, getattr(model.addition, "values")).detach()
    n_slots = int(table.shape[0])
    groups = core.SPECIFICITY_GROUPS
    size = math.ceil(n_slots / groups)
    selected = sel.selected
    group_of_read = (selected.clamp_min(0) // size).to(torch.int64)
    member = torch.zeros(q, groups, dtype=torch.bool)
    for fact, fact_slots in enumerate(supports.slots):
        if fact_slots:
            member[fact, (torch.tensor(fact_slots) // size).unique()] = True
    has = supports.has_support
    drops: list[float] = []
    counts: list[int] = []
    no_avoider = 0
    for g in range(groups):
        avoiders = has & ~member[:, g]
        counts.append(int(avoiders.sum()))
        if counts[-1] == 0:
            no_avoider += 1
            drops.append(0.0)
            continue
        touched = (group_of_read == g) & (selected >= 0)
        rows = touched.flatten(1).any(1).nonzero().squeeze(1)
        correct = scores.correct.clone()
        if rows.numel():
            ablated = table.clone()
            ablated[g * size : (g + 1) * size] = 0.0
            logits = _logits_core(
                model, cache, rows, knockout=None, values=ablated, disabled=False, batch_contexts=64
            )
            facts_of_rows = (
                rows[:, None] * core.ANSWER_SITES_PER_CONTEXT + torch.arange(8)
            ).reshape(-1)
            correct[facts_of_rows] = core.score_answer_sites(
                logits.reshape(-1, VOCAB), scores.answer[facts_of_rows]
            ).correct
        drops.append(1.0 - float(correct[avoiders].float().mean()))
    max_drop = max(drops) if drops else 0.0
    failing = sum(d > core.SPECIFICITY_GROUP_TOLERANCE for d in drops)
    condition_2 = failing == 0
    return {
        "condition_1": bool(condition_1),
        "condition_2": bool(condition_2),
        "interpretable": bool(condition_1 and condition_2),
        "scope": scope,
        "condition_1_share_unchanged": share,
        "condition_1_threshold_share": core.SPECIFICITY_SHARE,
        "condition_1_delta": core.SPECIFICITY_DELTA,
        "condition_1_facts_tested": n_eval,
        "condition_1_pool_slots": int(pool.numel()),
        "condition_1_mean_slots_drawn": (drawn_total / n_eval) if n_eval else 0.0,
        "condition_1_vacuous": bool(pool.numel() == 0),
        "condition_2_groups": groups,
        "condition_2_group_size": size,
        "condition_2_max_drop": float(max_drop),
        "condition_2_groups_failing": int(failing),
        "condition_2_groups_without_avoiding_facts": int(no_avoider),
        "condition_2_tolerance": core.SPECIFICITY_GROUP_TOLERANCE,
        "condition_2_group_drops": [float(d) for d in drops],
        "condition_2_group_fact_counts": counts,
    }


# --- usage ---------------------------------------------------------------------------------------------------
def _effective(entropy: float) -> float:
    return math.exp(entropy)


def read_weight_entropy(selection: Selection, columns: list[int]) -> Tensor:
    """``[C * len(columns)]`` entropy (nats) of the softmax read weights at ``columns``."""
    w = selection.scores[:, columns].softmax(-1)
    return (-(w * w.clamp_min(1e-30).log()).sum(-1)).reshape(-1)


def _hard_usage(selected: Tensor, slots: int) -> dict[str, float]:
    flat = selected.reshape(-1)
    flat = flat[flat >= 0]
    counts = torch.bincount(flat, minlength=slots)
    total = float(counts.sum())
    distinct = int((counts > 0).sum())
    if total == 0:
        return {"distinct": 0, "entropy": 0.0, "effective": 0.0, "hot64": 0.0}
    u = counts.double() / total
    entropy = float(usage_entropy(u))
    hot = float(counts.topk(min(64, slots)).values.sum()) / total
    return {
        "distinct": distinct,
        "entropy": entropy,
        "effective": _effective(entropy),
        "hot64": hot,
    }


def usage_statistics(
    cache: ReadCache, supports: SupportResult | None = None, *, rows: Tensor | None = None
) -> dict[str, Any]:
    """Distinct selected slots, entropy-effective slots (hard top-8 at answer sites and soft from pi),
    hot-64 share, dead slots, weight entropy of each read, facts per slot, soft mass outside the top 8
    and the 8th-9th margin distribution (ADR 6.2, 6.3, 7). Hard entropies use answer-site selections.
    ``rows [C * 8] bool`` (keyword-only addition) restricts the answer-site statistics to those facts
    (the evaluation passes the trained facts); entropies are in nats."""
    sel = cache.selection
    q = cache.tokens.shape[0] * core.ANSWER_SITES_PER_CONTEXT
    if sel is None:
        return {"slots": 0, "dense": True}
    keep = torch.ones(q, dtype=torch.bool) if rows is None else rows
    cols = site_columns(sel)
    site_sel = sel.selected[:, cols].reshape(q, -1)[keep]
    hard = _hard_usage(site_sel, cache.slots)
    out: dict[str, Any] = {
        "slots": cache.slots,
        "answer_site_queries": int(keep.sum()),
        "distinct": hard["distinct"],
        "dead_slots": int(cache.slots - hard["distinct"]),
        "entropy_hard": hard["entropy"],
        "entropy_effective_hard": hard["effective"],
        "hot64_share": hard["hot64"],
    }
    allpos = _hard_usage(sel.selected, cache.slots)
    out["distinct_all_positions"] = allpos["distinct"]
    out["entropy_effective_hard_all_positions"] = allpos["effective"]
    entropy = read_weight_entropy(sel, cols)[keep]
    out["weight_entropy_mean"] = float(entropy.mean())
    out["weight_entropy_median"] = float(entropy.median())
    # facts per slot: distinct answer-site facts that select the slot
    fact_id = cache.stream.fact_ids.reshape(-1)[keep]
    base = int(cache.stream.fact_ids.max()) + 1
    ids = site_sel
    pair = (ids.clamp_min(0).to(torch.int64) * base + fact_id[:, None]).reshape(-1)
    valid = (ids >= 0).reshape(-1)
    unique_pairs = torch.unique(pair[valid])
    per_slot = torch.bincount(unique_pairs // base, minlength=cache.slots)
    used = per_slot[per_slot > 0].double()
    out["facts_per_slot_mean"] = float(used.mean()) if used.numel() else 0.0
    out["facts_per_slot_median"] = float(used.median()) if used.numel() else 0.0
    out["facts_per_slot_max"] = int(used.max()) if used.numel() else 0
    if supports is not None and supports.useful:
        useful = torch.tensor(supports.useful, dtype=torch.int64)
        member = torch.bincount(
            torch.tensor(
                [s for fact_slots in supports.slots for s in fact_slots], dtype=torch.int64
            ),
            minlength=cache.slots,
        )[useful]
        out["facts_per_useful_slot_mean"] = float(member.double().mean())
    # soft usage and margins at answer sites (needs the candidates; R2 has none)
    if cache.site_candidate_ids is not None and cache.site_candidate_scores is not None:
        cand_ids = cache.site_candidate_ids.reshape(q, -1)[keep]
        cand_scores = cache.site_candidate_scores.reshape(q, -1)[keep]
        inclusion = soft_inclusion_full(cand_scores)
        u = slot_usage(inclusion.pi, cand_ids, cache.slots)
        soft_entropy = float(usage_entropy(u))
        out["entropy_soft"] = soft_entropy
        out["entropy_effective_soft"] = _effective(soft_entropy)
        out["soft_mass_outside_top8"] = float(inclusion.pi[:, TOP:].sum(-1).mean())
        margin = inclusion.gap
        quant = torch.quantile(margin, torch.tensor(MARGIN_QUANTILES))
        out["margin_8_9"] = {
            **{k: float(v) for k, v in zip(MARGIN_KEYS, quant, strict=True)},
            "mean": float(margin.mean()),
        }
    return out


@torch.no_grad()
def first_entering_top64(model_at_0: P9Model, model: P9Model, stream: Stream) -> int:
    """Count of keys that enter any query's top 64 after update 0 (ADR 6.2 revival count): the answer-site
    top-64 candidates of ``model`` on ``stream`` that are in no answer-site top 64 of ``model_at_0``."""
    now = build_cache(model, stream)
    then = build_cache(model_at_0, stream)
    if now.site_candidate_ids is None or then.site_candidate_ids is None:
        return 0
    seen = torch.zeros(now.slots, dtype=torch.bool)
    seen[then.site_candidate_ids.reshape(-1)] = True
    entered = torch.zeros(now.slots, dtype=torch.bool)
    entered[now.site_candidate_ids.reshape(-1)] = True
    return int((entered & ~seen).sum())


def accuracy_by_neighbour(
    scores: AnswerScores, has_neighbour: Tensor
) -> tuple[float | None, float | None]:
    """Accuracy of facts with and without a two-symbol neighbour (ADR 4.1); None for an empty class."""
    correct = scores.correct.float()
    with_n = has_neighbour.bool()
    a = float(correct[with_n].mean()) if bool(with_n.any()) else None
    b = float(correct[~with_n].mean()) if bool((~with_n).any()) else None
    return a, b


# --- traces --------------------------------------------------------------------------------------------------
def trace_from_cache(cell: Cell, update: int, cache: ReadCache, kind: str) -> Trace:
    """In-memory trace (``core.Trace``) of a cache; ``cluster`` is -1 for unseen facts (and for contexts
    that mix clusters: it is the stream's context-level cluster). Rows are in (context, position) order;
    an answer-site trace holds positions 8r+6, an all-position trace every read position."""
    if kind not in core.TRACE_KINDS:
        raise ValueError("unknown trace kind")
    sel = cache.selection
    if sel is None or sel.selected.shape[-1] != TOP:
        raise ValueError("a trace needs a top-8 memory (the dense adapter and R2 have none)")
    cols = site_columns(sel) if kind == "answer" else list(range(sel.positions.shape[0]))
    c = cache.tokens.shape[0]
    stream = cache.stream
    positions = sel.positions[cols]
    ctx = torch.arange(c).repeat_interleave(len(cols))
    pos = positions.repeat(c)
    record = (pos // core.RECORD_BYTES).clamp_max(core.RECORDS_PER_CONTEXT - 1)
    branches = None
    if sel.branches is not None and sel.branches.shape[-1] == core.VISIT:
        branches = sel.branches[:, cols].reshape(-1, core.VISIT)
    return Trace(
        label=cell.label,
        update=update,
        stream=stream.name,
        kind=kind,
        slots=cache.slots,
        selected=sel.selected[:, cols].reshape(-1, TOP).to(torch.int64),
        branches=None if branches is None else branches.to(torch.int64),
        context=ctx,
        position=pos,
        fact=stream.fact_ids[ctx, record],
        cluster=stream.cluster[ctx],
    )


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
    out: dict[str, tuple[Path, str]] = {}
    for kind in kinds:
        path = core.trace_path(run_dir, cell.label, update, cache.stream.name, kind)
        out[kind] = (path, core.write_trace(path, trace_from_cache(cell, update, cache, kind)))
    return out


def leakage_flag(unseen_correct: int, unseen_facts: int) -> bool:
    """LEAKAGE (ADR 8.1): unseen-fact accuracy outside the G2 interval (tests = 8). False when the
    stream has no unseen facts."""
    if unseen_facts <= 0:
        return False
    interval = core.chance_interval(unseen_facts, core.G2_TESTS_PRIMARY)
    return not interval.low <= unseen_correct <= interval.high


# --- one snapshot, one stream ---------------------------------------------------------------------------------
_NEIGHBOURS: dict[tuple[int, int], Tensor] = {}


def _neighbours(table: FactTable, among: int | None) -> Tensor:
    key = (id(table), table.trained if among is None else among)
    if key not in _NEIGHBOURS:
        _NEIGHBOURS[key] = neighbour_flags(table, among=among)
    return _NEIGHBOURS[key]


def _snapshot_extras(cell: Cell, run_dir: Path, update: int) -> dict[str, Any]:
    """Movement split and training-time diagnostics stored next to the snapshot (absent files skipped)."""
    folder = core.snapshot_dir(run_dir, cell.label, update)
    out: dict[str, Any] = {}
    movement = folder / "movement.pt"
    if movement.is_file():
        data = torch.load(movement, weights_only=True, map_location="cpu")
        for table in ("key", "value"):
            if f"{table}_with" not in data:  # the dense adapter has no key or value tables
                continue
            with_g, without_g = (
                float(data[f"{table}_with"].sum()),
                float(data[f"{table}_without"].sum()),
            )
            out[f"{table}_movement_with_task_grad"] = with_g
            out[f"{table}_movement_without_task_grad"] = without_g
            total = with_g + without_g
            out[f"{table}_movement_share_without"] = (without_g / total) if total > 0 else None
    snap = folder / "snapshot.json"
    if snap.is_file():
        record = core.read_record(snap, "snapshot")
        out["dead_slots_training"] = record.get("dead_slots")
        out["keys_entered_top64_after_0"] = record.get("keys_entered_top64_after_0")
    return out


def _accuracy(scores: AnswerScores, mask: Tensor) -> float:
    return float(scores.correct[mask].float().mean())


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
    table = _table(data, stream)
    cache = build_cache(model, stream)
    fact_ids = stream.fact_ids.reshape(-1)
    answers = stream.answer_targets().reshape(-1)
    scores = score_cache(cache, answers)
    trained = fact_ids < table.trained
    unseen = ~trained
    n = int(trained.sum())
    if n == 0:
        raise ValueError("the stream holds no trained facts")
    tests = core.G2_TESTS_LANE_D if stream.name.startswith("lane_d_") else core.G2_TESTS_PRIMARY
    correct = int(scores.correct[trained].sum())
    sub = _subset(scores, trained)
    logloss_bits = core.BITS_PER_FACT + sub.logp_sigma.gather(1, sub.answer[:, None]).squeeze(
        1
    ) / math.log(2.0)
    among = None if cell.is_lane_d else cell.facts
    flags = _neighbours(table, among)[fact_ids][trained]
    with_n, without_n = accuracy_by_neighbour(sub, flags)
    unseen_n = int(unseen.sum())
    unseen_correct = int(scores.correct[unseen].sum())
    dense = cache.selection is None

    permuted: float | None = None
    disabled_acc: float | None = None
    useful: int | None = None
    interpretable: bool | None = None
    spec: dict[str, Any] = {}
    mean_length: float | None = None
    share_support: float | None = None
    share_stay: float | None = None
    supports: SupportResult | None = None
    if interventions:
        off = logits_with(model, cache, disabled=True)
        disabled_acc = _accuracy(core.score_answer_sites(off.reshape(-1, VOCAB), answers), trained)
        if not dense:
            perm = logits_with(
                model, cache, values=permute_values(model, _seed(seed, update, stream.name, "perm"))
            )
            permuted = _accuracy(core.score_answer_sites(perm.reshape(-1, VOCAB), answers), trained)
            supports = minimal_supports(model, cache, nomem, scores, facts=trained)
            spec = specificity(
                model, cache, supports, scores, seed=_seed(seed, update, stream.name), facts=trained
            )
            useful = len(supports.useful)
            interpretable = bool(spec["interpretable"])
            lengths = supports.length[trained & supports.has_support]
            mean_length = float(lengths.double().mean()) if lengths.numel() else None
            ok = trained & scores.correct
            n_ok = int(ok.sum())
            if n_ok:
                share_support = float((supports.has_support & ok).sum()) / n_ok
                share_stay = float((supports.removing_site_read_stays_correct & ok).sum()) / n_ok
            spec = {
                **spec,
                "support_summary": {
                    "facts_correct": n_ok,
                    "facts_with_support": int((supports.has_support & ok).sum()),
                    "length_median": float(lengths.double().median()) if lengths.numel() else None,
                    "length_max": int(lengths.max()) if lengths.numel() else None,
                },
            }
    usage = usage_statistics(cache, supports, rows=trained)
    usage.update(_snapshot_extras(cell, run_dir, update))
    per_fact_median = {
        "p_correct": float(sub.p_correct.median()),
        "logloss_gain_bits": float(logloss_bits.median()),
    }
    usage["per_fact_median"] = per_fact_median

    path = core.eval_path(run_dir, cell.label, update, stream.name)
    per_fact_path = path.with_name(f"{stream.name}.perfact.pt")
    tensors: dict[str, Tensor] = {
        "fact_id": fact_ids.to(torch.int64),
        "trained": trained,
        "correct": scores.correct,
        "p_correct": scores.p_correct,
        "mass_sigma": scores.mass_sigma,
    }
    if not dense:
        tensors["weight_entropy"] = read_weight_entropy(
            cast(Selection, cache.selection), site_columns(cast(Selection, cache.selection))
        )
    if supports is not None:
        tensors["support_length"] = supports.length
        tensors["site_read_removed_stays_correct"] = supports.removing_site_read_stays_correct
    buffer = io.BytesIO()
    torch.save(tensors, buffer)
    per_fact_path.parent.mkdir(parents=True, exist_ok=True)
    from arborlm.io import atomic_write

    atomic_write(per_fact_path, buffer.getvalue())

    record = cast(
        EvalRecord,
        {
            **core.envelope("eval"),
            "label": cell.label,
            "update": update,
            "stream": stream.name,
            "facts": n,
            "correct": correct,
            "accuracy": correct / n,
            "information_bits": float(core.information_bits(correct, n, tests)),
            "logloss_gain_bits": float(logloss_bits.double().sum()),
            "mass_outside_alphabet_mean": float(1.0 - sub.mass_sigma.double().mean()),
            "accuracy_with_neighbour": with_n,
            "accuracy_without_neighbour": without_n,
            "unseen_correct": unseen_correct,
            "unseen_facts": unseen_n,
            "leakage": leakage_flag(unseen_correct, unseen_n),
            "value_permuted_accuracy": permuted,
            "disabled_accuracy": disabled_acc,
            "useful_slots": useful,
            "ustar_interpretable": interpretable,
            "specificity": spec,
            "mean_support_length": mean_length,
            "share_correct_with_support": share_support,
            "share_stay_correct_without_site_read": share_stay,
            "usage": usage,
            "per_fact_file": per_fact_path.relative_to(run_dir).as_posix(),
            "identity": _identity(),
        },
    )
    core.write_record(path, record)
    if write_traces and stream.name in TRACE_STREAMS and not dense and cell.rung != "R2":
        export_traces(cell, update, cache, run_dir)
    return record


# --- one cell --------------------------------------------------------------------------------------------------
def evaluate_cell(
    cell: Cell,
    run_dir: Path,
    data: StudyData,
    experiments_root: Path,
    exposure: int,
    *,
    secondary: bool = False,
    trace_blocks: tuple[str, ...] = TRACE_BLOCKS,
    backbone: Any = None,
) -> list[EvalRecord]:
    """All snapshots of the cell on the panels it needs, with the intervention schedule above. The
    worker entry used by the evaluate stage; one record file per (snapshot, stream).

    Interventions run at the matched-exposure snapshot ``core.updates(cell, exposure)`` and, outside
    Lane D, at the fixed-compute snapshot ``core.fixed_compute_updates(exposure)``; the half-way
    snapshots get knowledge metrics only. Streams: the primary panels A and B (``panel_streams``; the
    four Lane D sets for Lane D cells). Keyword-only additions (reported): ``secondary`` adds the H1, H2
    and mixed-cluster streams (knowledge metrics, at the intervention snapshots); traces (answer-site
    and all-position, panels A and B and the calibration stream) are written at the matched-exposure
    snapshot of cells of ``trace_blocks``. ``backbone`` (integration addition) is a ready frozen backbone
    (the synthetic one of the DRY profile); None loads the verified parent from ``experiments_root``."""
    if backbone is None:
        backbone, _ = controls.load_backbone(cell.parent, experiments_root)
    lut = identifier_lut(data.facts, facts_of(data, cell)) if cell.rung == "R2" else None
    model = build_model(
        cell,
        backbone,
        fact_lut=lut,
        seed_rng=False,
        r1_seed=data.seeds.r1_codes,
        branch_seed=data.seeds.branch_hash,
    )
    matched = core.updates(cell, exposure)
    fixed = None if cell.is_lane_d else core.fixed_compute_updates(exposure)
    seed = data.seeds.permutation_tests
    nomem_cache: dict[str, AnswerScores] = {}

    def nomem_for(stream: Stream) -> AnswerScores:
        if stream.name not in nomem_cache:
            nomem_cache[stream.name] = controls.evaluate_no_memory(
                backbone, _table(data, stream), stream
            )
        return nomem_cache[stream.name]

    records: list[EvalRecord] = []
    for update in core.snapshots(cell, exposure):
        load_snapshot(core.snapshot_dir(run_dir, cell.label, update), model)
        deep = update in (matched, fixed)
        traced = update == matched and cell.block in trace_blocks and cell.arch != "dense"
        streams = [s for panel in core.PANELS for s in panel_streams(data, cell, panel)]
        for stream in streams:
            records.append(
                evaluate_snapshot(
                    cell,
                    run_dir,
                    update,
                    stream,
                    data,
                    model,
                    nomem=nomem_for(stream),
                    interventions=deep,
                    write_traces=traced,
                    seed=seed,
                )
            )
        extra: list[Stream] = []
        if secondary and deep and not cell.is_lane_d:
            extra += [
                restrict_stream(data.streams[n], data.facts, cell.facts)
                for n in ("h1", "h2", "mixed")
            ]
        if traced:
            extra.append(restrict_stream(data.streams["calibration"], data.facts, cell.facts))
        for stream in extra:
            records.append(
                evaluate_snapshot(
                    cell,
                    run_dir,
                    update,
                    stream,
                    data,
                    model,
                    nomem=nomem_for(stream),
                    interventions=False,
                    write_traces=traced and stream.name == "calibration",
                    seed=seed,
                )
            )
    return records


# --- command line -----------------------------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m studies.p9.evaluate", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("cell", "stage"):
        p = sub.add_parser(name)
        p.add_argument("--run-dir", required=True)
        p.add_argument("--exposure", type=int, default=core.DEFAULT_EXPOSURE)
        p.add_argument("--mode", choices=("registered", "calibration"), default="registered")
        p.add_argument("--draw", type=int, default=0, help="rehearsal-namespace draw (calibration)")
        p.add_argument("--experiments-root", default=None)
        p.add_argument("--secondary", action="store_true")
        if name == "cell":
            p.add_argument("--label", required=True)
        else:
            p.add_argument("--labels", nargs="*", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.evaluate {cell,stage} ...``. Prints file counts only,
    never an accuracy. Rehearsal mode is refused: a rehearsal path never writes accuracy (ADR 12 step 5)."""
    args = _parser().parse_args(argv)
    from arborlm.engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:
        torch.set_num_threads(1)
    from .data import build_study_data

    root = Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()
    seeds = (
        core.registered_seeds() if args.mode == "registered" else core.rehearsal_seeds(args.draw)
    )
    data = build_study_data(seeds, core.load_trained_corpus(root))
    labels = [args.label] if args.command == "cell" else (args.labels or core.all_labels())
    total = 0
    for label in labels:
        cell = core.parse_label(label)
        written = evaluate_cell(
            cell, Path(args.run_dir), data, root, args.exposure, secondary=args.secondary
        )
        total += len(written)
        print(f"{label}: {len(written)} records")
    print(f"{total} eval records written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
