# ruff: noqa: E501
"""P10IR reads and measurements (ADR-0029 sections 6 and 7). Nothing here trains, tunes or writes a checkpoint. Every read and every fact-level pass runs under ``torch.no_grad()`` (the checkpoint's keys and router are Parameters: with autograd on, each chunk's graph would stay alive until the pass returned).

* **One tree path** (``tree_path``): the router's ``v`` best branches, the prior on or off in the selection of the top 8, on or off in the weights. T0 (v = 2, both on), T1, T1w, T3 and T2
  (v = N/256) and the sweep Tv are this function. It repeats ``arborlm``'s and P9's operations of ``ScalableMemory._top_tree`` one for one (same chunking at v = 2, same normalisation of the gathered
  keys, same tie rule through ``stable_top`` with the slot ids), so that T0 equals ``S1Memory._top_tree`` bit for bit (gate 2, review finding R3-1); ``TreeReadMemory(verify=True)`` checks that on every
  query it serves.
* **Flat reads**: F0 is P10-S1's unmodified flat read; I256@512 is P10-S1's ``evaluate.ivf_model`` (called, not copied); I64@c is ``IVFBudgetMemory``, P10-S1's ``IVFMemory`` with another minimum candidate
  count and an index of N/64 lists built by P10-S1's ``build_index``.
* **End-task measures** go through P10-S1's own ``evaluate.panel_counts`` (a_use, raw accuracy, its derangement) and ``core.bits_per_fact`` (i): called, not re-derived.
* **New measurements** (section 7): candidate recall CR8 and CR1 over all trained facts, selection overlap SR8, recovered attention mass AM_C and AM_S, the prior effects, testability. E8 and E1 are the top 8
  and top 1 of cos / 0.2 against ``F.normalize(keys, eps=EPS)`` without priors by ``stable_top`` (ties to the lower slot id), on the same checkpoint's keys.
"""

import contextlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS, stable_top
from studies.p10s1 import core as s1core
from studies.p10s1 import evaluate as s1eval
from studies.p10s1 import index as s1index
from studies.p10s1.model import P10S1Model, S1Memory

from . import core

if TYPE_CHECKING:
    from torch import Tensor

    from studies.p9.data import StudyData

TEMP = s1core.TEMPERATURE
TOP = s1core.TOP
SOFT_TOP = s1index.SOFT_TOP
FACT_CHUNK = 1024


# --- the reads of a tree checkpoint (names and parameters) ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TreeReadSpec:
    """``visits`` is the number of branches visited (None: every branch, v = N/256)."""

    name: str
    visits: int | None
    prior_select: bool
    prior_weight: bool

    def v(self, branches: int) -> int:
        return branches if self.visits is None else self.visits


def tree_read_specs(slots: int, cfg: Mapping[str, Any] | None = None) -> list[TreeReadSpec]:
    """T0, T1, T1w, T3, T2 and the sweep reads that are not aliases of them: v = 2 is T0 / T1 and v = N/256 is T3 / T2, so neither is read twice. v > N/256 is not here: it is a NOT APPLICABLE
    item of the plan (``stages.plan_items``)."""
    c = cfg or core.load_config()
    branches = slots // int(c["reads"]["branch_size"])
    out = [
        TreeReadSpec("T0", int(c["reads"]["visit_registered"]), True, True), TreeReadSpec("T1", int(c["reads"]["visit_registered"]), False, False),
        TreeReadSpec("T1w", int(c["reads"]["visit_registered"]), True, False), TreeReadSpec("T3", None, True, True), TreeReadSpec("T2", None, False, False),
    ]  # fmt: skip
    for v in core.feasible_visits(slots, cfg):
        if v in (int(c["reads"]["visit_registered"]), branches):
            continue
        out += [TreeReadSpec(core.tv_name(v, "on"), v, True, True), TreeReadSpec(core.tv_name(v, "off"), v, False, False)]
    return out


# --- the one tree path ----------------------------------------------------------------------------------------------------------------------------------
@dataclass
class TreeOut:
    values: "Tensor"  # [R, 64] the scores the weights are the softmax of (first 8), in selection order
    ids: "Tensor"  # [R, 64] slot ids in selection order (score, then slot id)
    branch_ids: "Tensor"  # [R, v] the branches visited, in route order
    routes: "Tensor"  # [R, N/256]


@torch.no_grad()
def tree_path(keys: "Tensor", router: "Tensor", q: "Tensor", v: int, prior_select: bool, prior_weight: bool, *, per: int, chunk_elements: int) -> TreeOut:
    """The router's ``v`` best branches (ties to the lower branch id), every key of them scored cos(q, key) / 0.2, the prior (the log-softmax over all branches of the branch's route score, one constant per
    branch) added to the selection scores if ``prior_select`` and to the weight scores if ``prior_weight``; the top 64 by score with ties to the lower slot id (``stable_top`` with ids), whose first
    8 are the read's slots and whose weights are the softmax of their weight scores. With both priors on and v = 2 this is ``ScalableMemory._top_tree`` operation for operation."""
    kw = int(keys.shape[1])
    routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
    _, branch_ids = stable_top(routes, v)
    arange = torch.arange(per, device="cpu")
    rows = max(1, chunk_elements // max(1, v * per * kw))
    values, ids = [], []
    for start in range(0, q.shape[0], rows):
        end = start + rows
        indices = (branch_ids[start:end, :, None] * per + arange).flatten(1)
        local = F.normalize(keys[indices], dim=-1, eps=EPS)
        cos = torch.bmm(local, q[start:end].unsqueeze(-1)).squeeze(-1) / TEMP
        prior = routes[start:end].log_softmax(-1).gather(-1, branch_ids[start:end])
        with_prior = cos + prior.repeat_interleave(per, dim=-1)
        select_scores = with_prior if prior_select else cos
        weight_scores = with_prior if prior_weight else cos
        by_id = indices.argsort(dim=-1)  # what ``stable_top(scores, count, ids)`` does, kept open so that the weight scores can follow the selection
        sel_sorted = select_scores.gather(-1, by_id)
        ids_sorted = indices.gather(-1, by_id)
        weight_sorted = weight_scores.gather(-1, by_id)
        _, order = stable_top(sel_sorted, SOFT_TOP)
        values.append(weight_sorted.gather(-1, order))
        ids.append(ids_sorted.gather(-1, order))
    return TreeOut(torch.cat(values), torch.cat(ids), branch_ids, routes)


@torch.no_grad()
def exhaustive_top(keys: "Tensor", q: "Tensor", count: int, chunk_elements: int) -> "tuple[Tensor, Tensor]":
    """The flat read: top ``count`` of cos / 0.2 against ``F.normalize(keys, eps=EPS)`` by ``stable_top`` (ties to the lower slot id), as ``ScalableMemory._top_flat``."""
    normalized = F.normalize(keys, dim=-1, eps=EPS)
    rows = max(1, chunk_elements // max(1, int(keys.shape[0])))
    values, ids = [], []
    for start in range(0, q.shape[0], rows):
        v, i = stable_top((q[start : start + rows] @ normalized.T) / TEMP, count)
        values.append(v)
        ids.append(i)
    return torch.cat(values), torch.cat(ids)


@torch.no_grad()
def independent_flat(keys: "Tensor", router: "Tensor", q: "Tensor", with_prior: bool, *, per: int, chunk_elements: int) -> "tuple[Tensor, Tensor]":
    """The extra gate read of section 11 gate 4: ``q @ keys.T`` over all keys with (T3) or without (T2) the per-key prior of its branch; top 64 by ``stable_top`` (ties to the lower slot id)."""
    normalized = F.normalize(keys, dim=-1, eps=EPS)
    routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
    prior = routes.log_softmax(-1).repeat_interleave(per, dim=-1)
    rows = max(1, chunk_elements // max(1, int(keys.shape[0])))
    values, ids = [], []
    for start in range(0, q.shape[0], rows):
        scores = (q[start : start + rows] @ normalized.T) / TEMP
        if with_prior:
            scores = scores + prior[start : start + rows]
        v, i = stable_top(scores, SOFT_TOP)
        values.append(v)
        ids.append(i)
    return torch.cat(values), torch.cat(ids)


# --- memories that serve a read through P10-S1's model ----------------------------------------------------------------------------------------------------
class TreeReadMemory(S1Memory):
    """The trained tree memory read by ``tree_path`` with the settings of ``read``. Nothing is trained. With ``verify`` every query is also served by ``S1Memory._top_tree`` and the first 8 slot ids and
    scores must equal it bit for bit (gate 2, R3-1): ``checked`` and ``mismatched`` count queries."""

    def __init__(self, source: S1Memory, read: TreeReadSpec, *, verify: bool = False) -> None:
        super().__init__(source.spec, source.seed, r1_seed=source.r1_seed)
        self.load_state_dict(source.state_dict(), strict=True)
        self.read, self.verify = read, verify
        self.checked = self.mismatched = 0

    def _top_tree(self, q: "Tensor") -> "tuple[Tensor, Tensor, Tensor, Tensor]":
        v = self.read.v(self.spec.branches)
        out = tree_path(cast("Tensor", self.keys), cast("Tensor", self.router), q, v, self.read.prior_select, self.read.prior_weight, per=self.spec.per_branch, chunk_elements=int(self.chunk_elements))
        self.counters.key_scores += int(q.shape[0]) * (self.spec.branches + v * self.spec.per_branch)
        self.counters.topk_comparisons += int(q.shape[0]) * (self.spec.branches + v * self.spec.per_branch)
        if self.verify:
            saved = (self.counters.key_scores, self.counters.topk_comparisons)
            ref_values, ref_ids, _, _ = S1Memory._top_tree(self, q)
            self.counters.key_scores, self.counters.topk_comparisons = saved
            same = (ref_ids[:, :TOP] == out.ids[:, :TOP]).all(1) & (ref_values[:, :TOP] == out.values[:, :TOP]).all(1)
            self.checked += int(q.shape[0])
            self.mismatched += int((~same).sum())
        return out.values, out.ids, out.branch_ids, out.routes


class IVFBudgetMemory(s1index.IVFMemory):
    """P10-S1's ``IVFMemory`` with ``minimum`` candidates instead of 512 (``candidate_mask(..., minimum)``); the rest of ``_top_flat`` is P10-S1's, line for line."""

    def __init__(self, source: Any, index: s1index.IVFIndex, minimum: int) -> None:
        super().__init__(source, index)
        self.minimum = minimum

    def _top_flat(self, q: "Tensor") -> "tuple[Tensor, Tensor]":
        keys = self.keys
        normalized = F.normalize(keys, dim=-1, eps=EPS)
        rows = self._rows(self.spec.slots)
        values, ids = [], []
        for start in range(0, q.shape[0], rows):
            block = q[start : start + rows]
            scores = (block @ normalized.T) / TEMP
            mask, counts = s1index.candidate_mask(self.index, block, self.minimum)
            v, i = stable_top(scores.masked_fill(~mask, -torch.inf), SOFT_TOP)
            with torch.no_grad():
                _, exhaustive = stable_top(scores, TOP)
                hit = (i[:, :TOP, None] == exhaustive[:, None, :]).any(1).float().sum(1) / TOP
            self.recall_sum += float(hit.sum())
            self.recall_queries += int(block.shape[0])
            self.candidate_counts.append(counts.clone())
            self.counters.key_scores += int(block.shape[0]) * self.index.lists + int(counts.sum())
            self.counters.topk_comparisons += int(counts.sum())
            values.append(v)
            ids.append(i)
        return torch.cat(values), torch.cat(ids)


@contextlib.contextmanager
def swapped_addition(model: P10S1Model, memory: Any) -> Iterator[None]:
    """``model`` with ``memory`` as its addition for the duration (the backbone, the output head and the gate are the checkpoint's)."""
    old = model.addition
    model.addition = memory
    try:
        yield
    finally:
        model.addition = old


# --- end-task counts through P10-S1's own functions --------------------------------------------------------------------------------------------------------------
def read_counts(model: P10S1Model, data: "StudyData", facts: int, seeds: Any) -> dict[str, Any]:
    """The counts of the model's current read on Panels A and B: ``evaluate.panel_counts`` with P10-S1's derangement (mask seed 0) under ``evaluate.eval_chunking``; i by ``core.bits_per_fact``. The work of
    Panel A is counted; an index memory's measured candidates are returned under ``measured`` (with P10-S1's recall quantity, which a gate consumes and no record keeps)."""
    pi = s1eval._deranged(data, facts, s1core.mask_seed(seeds, 0))
    panels: dict[str, Any] = {}
    out: dict[str, Any] = {}
    with s1eval.eval_chunking(model):
        for panel in s1core.PANELS:
            stream = s1eval.stream_for(data, facts, s1core.PANEL_STREAM[panel])
            model.counters.reset()
            if isinstance(model.addition, s1index.IVFMemory):
                model.addition.reset_measures()
            counts = s1eval.panel_counts(model, data, facts, stream, pi=pi, tables=None)
            n, useful = int(counts["n"]), int(counts["useful"])
            panels[panel] = {
                "n": n, "correct": int(counts["correct"]), "useful": useful, "disabled_correct": int(counts["disabled_correct"]), "swap_correct": int(counts["swap_correct"]),
                "unseen_n": int(counts["unseen_n"]), "unseen_correct": int(counts["unseen_correct"]),
                "i": s1core.bits_per_fact(useful, n), "a_use": useful / n if n else float("nan"), "accuracy": int(counts["correct"]) / n if n else float("nan"),
            }  # fmt: skip
            if panel == "A":
                out["work"] = model.counters.per_query()
                if isinstance(model.addition, s1index.IVFMemory):
                    out["measured"] = model.addition.measured()
    out["panels"] = panels
    return out


# --- fact-level measures (section 7) ----------------------------------------------------------------------------------------------------------------------------
def _stats_from(selected: "Tensor", in_c: "Tensor", e_ids: "Tensor", w_e: "Tensor") -> dict[str, "Tensor"]:
    """Per fact: CR8 = |C ∩ E8| / 8, CR1 = [E1 ∈ C], SR8 = |S ∩ E8| / 8, AM_C = sum of w_E over C ∩ E8, AM_S = sum of w_E over S ∩ E8."""
    s_in_e = (selected[:, :, None] == e_ids[:, None, :]).any(1)  # [R, 8]: which E8 slots the read selected
    return {
        "cr8": in_c.float().mean(1), "cr1": in_c[:, 0].float(), "sr8": (selected[:, :, None] == e_ids[:, None, :]).any(-1).float().mean(1),
        "am_c": (in_c.float() * w_e).sum(1), "am_s": (s_in_e.float() * w_e).sum(1),
    }  # fmt: skip


def _pair_stats(a_ids: "Tensor", a_w: "Tensor", b_ids: "Tensor", b_w: "Tensor") -> dict[str, "Tensor"]:
    """Between two reads of the same facts: whether the selected sets differ, and the total-variation distance of the weights over the union of the two selected sets (weight zero outside each)."""
    match = a_ids[:, :, None] == b_ids[:, None, :]  # [R, 8, 8]
    equal = match.any(-1).all(-1)
    w_b_at_a = (match.float() * b_w[:, None, :]).sum(-1)
    b_only = (~match.any(1)).float()
    tv = 0.5 * ((a_w - w_b_at_a).abs().sum(1) + (b_w * b_only).sum(1))
    return {"changed": (~equal).float(), "tv": tv}


def _mean(parts: Sequence["Tensor"]) -> float:
    return float(torch.cat(list(parts)).to(torch.float64).mean()) if parts else float("nan")  # float64: the per-fact values are integer counts over 8 (or 0/1), exact in float32; the mean is not taken in float32


def _weights(values: "Tensor") -> "Tensor":
    return values[:, :TOP].softmax(-1)


@torch.no_grad()
def tree_fact_pass(source: S1Memory, codes: "Tensor", specs: Sequence[TreeReadSpec], *, chunk_elements: int, chunk: int = FACT_CHUNK) -> dict[str, dict[str, Any]]:
    """CR8, CR1, SR8, AM_C, AM_S of every read of ``specs`` over all trained facts (each once), the share of facts whose eight slots span both branches (T0), and the pair statistics T0 against T1, T1w and
    T3, and T3 against T2. ``source`` is the checkpoint's T-OQ memory; ``codes [F, 16]`` the facts' oracle codes."""
    keys, router, per, branches = cast("Tensor", source.keys), cast("Tensor", source.router), source.spec.per_branch, source.spec.branches
    acc: dict[str, dict[str, list[Tensor]]] = {s.name: {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "span")} for s in specs}
    pair_names = [("T1", "T0"), ("T1w", "T0"), ("T3", "T0"), ("T2", "T3")]
    pairs: dict[str, dict[str, list[Tensor]]] = {a: {"changed": [], "tv": []} for a, _ in pair_names}
    have = {s.name for s in specs}
    for start in range(0, codes.shape[0], chunk):
        q = codes[start : start + chunk]
        e_vals, e_ids = exhaustive_top(keys, q, TOP, chunk_elements)
        w_e = e_vals.softmax(-1)
        outs: dict[str, TreeOut] = {}
        for s in specs:
            out = tree_path(keys, router, q, s.v(branches), s.prior_select, s.prior_weight, per=per, chunk_elements=chunk_elements)
            outs[s.name] = out
            in_c = (e_ids[:, :, None] // per == out.branch_ids[:, None, :]).any(-1)
            st = _stats_from(out.ids[:, :TOP], in_c, e_ids, w_e)
            for k, val in st.items():
                acc[s.name][k].append(val)
            sel_branch = out.ids[:, :TOP] // per
            acc[s.name]["span"].append((sel_branch.min(1).values != sel_branch.max(1).values).float())
        for a, b in pair_names:
            if a in have and b in have:
                st2 = _pair_stats(outs[a].ids[:, :TOP], _weights(outs[a].values), outs[b].ids[:, :TOP], _weights(outs[b].values))
                for k, val in st2.items():
                    pairs[a][k].append(val)
    result: dict[str, dict[str, Any]] = {}
    for s in specs:
        facts = {k: _mean(v) for k, v in acc[s.name].items() if k != "span"}
        facts["share_span_both"] = _mean(acc[s.name]["span"])
        entry: dict[str, Any] = {"facts": facts, "facts_n": int(codes.shape[0])}
        if s.name in pairs and pairs[s.name]["changed"]:
            against = dict(pair_names)[s.name]
            entry["pair"] = {"against": against, "share_selected_changed": _mean(pairs[s.name]["changed"]), "tv_mean": _mean(pairs[s.name]["tv"])}
        result[s.name] = entry
    return result


@torch.no_grad()
def flat_fact_pass(source: S1Memory, codes: "Tensor", indexes: Mapping[str, tuple[s1index.IVFIndex, int]], *, chunk: int = FACT_CHUNK) -> dict[str, dict[str, Any]]:
    """The same measures for F0 (C is every key) and for each named index read (``indexes[name] = (index, minimum candidates)``): C is the mask of the lists visited; the candidate counts are measured per
    fact (mean and 99th percentile)."""
    keys = cast("Tensor", source.keys)
    normalized = F.normalize(keys, dim=-1, eps=EPS)
    names = ["F0", *indexes]
    acc: dict[str, dict[str, list[Tensor]]] = {n: {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s")} for n in names}
    counts_acc: dict[str, list[Tensor]] = {n: [] for n in indexes}
    for start in range(0, codes.shape[0], chunk):
        q = codes[start : start + chunk]
        scores = (q @ normalized.T) / TEMP
        e_vals, e_ids = stable_top(scores, TOP)
        w_e = e_vals.softmax(-1)
        _, f0_ids = stable_top(scores, SOFT_TOP)
        st = _stats_from(f0_ids[:, :TOP], torch.ones_like(e_ids, dtype=torch.bool), e_ids, w_e)
        for k, val in st.items():
            acc["F0"][k].append(val)
        for name, (idx, minimum) in indexes.items():
            mask, counts = s1index.candidate_mask(idx, q, minimum)
            counts_acc[name].append(counts)
            v, i = stable_top(scores.masked_fill(~mask, -torch.inf), SOFT_TOP)
            st = _stats_from(i[:, :TOP], mask.gather(1, e_ids), e_ids, w_e)
            for k, val in st.items():
                acc[name][k].append(val)
    out: dict[str, dict[str, Any]] = {}
    for n in names:
        entry: dict[str, Any] = {"facts": {k: _mean(v) for k, v in acc[n].items()}, "facts_n": int(codes.shape[0])}
        if n in counts_acc:
            c = torch.cat(counts_acc[n]).to(torch.float64)
            entry["candidates_facts"] = {"mean": float(c.mean()), "p99": float(torch.quantile(c, 0.99))}
        out[n] = entry
    return out


# --- records ----------------------------------------------------------------------------------------------------------------------------------------------------------
def read_record(stage: str, cell: str, update: int, read: str, counts: Mapping[str, Any], *, facts: Mapping[str, Any] | None = None, extra: Mapping[str, Any] | None = None, seconds: float = 0.0) -> dict[str, Any]:
    """The record of one read of one checkpoint. The sealed recall quantity of P10-S1's index read is never stored: it is dropped here before anything is written."""
    rec: dict[str, Any] = {**core.envelope("read"), "stage": stage, "cell": cell, "update": update, "read": read, "panels": counts["panels"], "work": counts["work"], "seconds": seconds}
    measured = dict(counts.get("measured") or {})
    measured.pop("recall_of_exhaustive_top8", None)
    if measured:
        rec["candidates"] = {"mean": measured["candidates_mean"], "p99": measured["candidates_p99"]}
    if facts is not None:
        rec["facts"] = dict(facts.get("facts", {}))
        rec["facts_n"] = facts.get("facts_n")
        if "pair" in facts:
            rec["pair"] = dict(facts["pair"])
        if "candidates_facts" in facts:
            rec["candidates_facts"] = dict(facts["candidates_facts"])
    rec.update(extra or {})
    return rec


Emit = Callable[[str, dict[str, Any]], None]
