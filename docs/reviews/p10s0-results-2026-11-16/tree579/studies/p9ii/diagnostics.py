# ruff: noqa: E501
"""P9II probe set and the measurements of ADR-0019 section 8.1, in tensors (the rules that read them are in ``classes``).

Probe set (section 8.1 after R2 and R4): for the first 256 trained facts, in the order of their first appearance in the draw's
calibration stream restricted to the cell's trained facts, both of their occurrences in that stream: 512 answer sites, 256
probe facts. The calibration stream uses training templates and contexts that are not in training. Panels A and B are untouched.
No rule or action during training reads the probe.

Definitions fixed here where the ADR names a measurement without a formula (all reported, none changes a threshold):

* distinct top-1 slots and the largest top-1 share: over the probe's sites (share = the largest count / number of sites).
* private slot: a slot that is in the top 8 of exactly one probe fact (a fact's top 8 = the union over its occurrences);
  "share of facts with a private slot" = facts holding at least one.
* address stability: the share of probe facts whose top-1 slot is the same at both occurrences.
* mean cosine between queries of different facts: the mean of q_i . q_j over probe-site pairs with different facts, on the
  un-centred normalized query z / |z| (for A5-C the centred query is reported beside it, descriptively).
* effective rank: exp of the entropy of the normalized eigenvalues of the covariance of the un-centred normalized queries;
  total variance: its trace.
* fact-independent share: |mean z|^2 / E|z|^2 on the probe (z un-normalized, un-centred).
* (template, record index) share: the share of the centred normalized query's variance that lies between the groups
  (template index, record index), i.e. SS_between / SS_total after global centring.
* for A4: the soft mass outside the top 8 of the read at the current k(t) (1 - the weight of the best 8 of the softmax
  over the k(t) best slots); 0 at k = 8.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS
from studies.p9 import core as p9core
from studies.p9.data import StudyData, restrict_stream

from . import core
from .model import SITES, P9IIModel

if TYPE_CHECKING:
    from torch import Tensor


@dataclass
class ProbeSet:
    """``tokens [C, 64]`` the contexts that hold probe sites; for each of the S sites: ``ctx`` (row of ``tokens``), ``rec`` (record
    index = answer-site index), ``fact`` (fact id), ``template`` (template index of the context) and ``answer`` (symbol 0..31)."""

    tokens: "Tensor"
    ctx: "Tensor"
    rec: "Tensor"
    fact: "Tensor"
    template: "Tensor"
    answer: "Tensor"
    probe_facts: int

    @property
    def sites(self) -> int:
        return int(self.fact.shape[0])


def build_probe(data: StudyData, facts: int, n_facts: int = core.PROBE_FACTS) -> ProbeSet:
    """The probe set of a cell with ``facts`` trained facts (see the module docstring)."""
    stream = restrict_stream(data.streams["calibration"], data.facts, facts)
    flat = stream.fact_ids.reshape(-1)
    first: list[int] = []
    seen: set[int] = set()
    for value in flat.tolist():
        if value >= facts:
            continue  # an unseen-control fact (or one the cell does not train) is never a probe fact (audit m13)
        if value not in seen:
            seen.add(value)
            first.append(value)
            if len(first) == min(n_facts, facts):
                break
    chosen = torch.tensor(first, dtype=torch.int64)
    if bool((chosen >= facts).any()) or len(set(first)) != len(first):
        raise AssertionError("the probe holds a fact the cell does not train, or a fact twice")
    where = torch.isin(flat, chosen).nonzero().squeeze(1)
    rows, rec = where // core.RECORDS_PER_CONTEXT, where % core.RECORDS_PER_CONTEXT
    contexts, ctx = torch.unique(rows, return_inverse=True)
    return ProbeSet(
        tokens=stream.tokens[contexts],
        ctx=ctx,
        rec=rec,
        fact=flat[where],
        template=stream.template[rows],
        answer=stream.answer_targets()[rows, rec],
        probe_facts=len(first),
    )


@dataclass
class ProbeReads:
    """What the model does on the probe sites (eval mode, no gradient): ``correct [S]`` (ties wrong), ``q`` the actual unit queries
    (None for A7), ``z`` the un-normalized un-centred query (None for A6, A7), ``top8 [S, 8]`` and ``scores8 [S, 8]`` (cos / 0.2)."""

    correct: "Tensor"
    q: "Tensor | None"
    z: "Tensor | None"
    top8: "Tensor | None"
    scores8: "Tensor | None"


@torch.no_grad()
def probe_reads(model: P9IIModel, probe: ProbeSet, chunk: int = 128) -> ProbeReads:
    was = model.training
    model.eval()
    try:
        n = probe.tokens.shape[0]
        logits, qs, zs, tops, scs = [], [], [], [], []
        for start in range(0, n, chunk):
            tok = probe.tokens[start : start + chunk, : core.INPUT_LENGTH].contiguous()
            h = model.embed_block0(tok)
            sel = model.select(h, tok)
            out = model.finish(h, model.memory_delta(h, sel))
            logits.append(out[:, SITES])
            q = model.answer_queries(h, tok)
            if q is not None:
                qs.append(q)
            z = model.answer_z(h, tok)
            if z is not None:
                zs.append(z)
            if sel is not None:
                tops.append(sel.selected[:, :, : core.TOP])
                scs.append(sel.scores[:, :, : core.TOP])
        all_logits = torch.cat(logits)  # [C, 8, 256]
        site_logits = all_logits[probe.ctx, probe.rec]
        correct = p9core.score_answer_sites(site_logits, probe.answer).correct

        def pick(parts: "list[Tensor]") -> "Tensor | None":
            return torch.cat(parts)[probe.ctx, probe.rec] if parts else None

        return ProbeReads(correct, pick(qs), pick(zs), pick(tops), pick(scs))
    finally:
        model.train(was)


# --- measurements on tensors --------------------------------------------------------------------------------------------
def top_slot_statistics(top1: "Tensor", top8: "Tensor", fact: "Tensor", probe_facts: int) -> dict[str, float | int]:
    """Distinct top-1 slots, the largest top-1 share, the share of facts with a private slot and address stability (see the module docstring)."""
    sites = int(top1.shape[0])
    counts = torch.bincount(top1) if sites else torch.zeros(1, dtype=torch.int64)
    distinct = int((counts > 0).sum())
    largest = int(counts.max())
    by_fact: dict[int, set[int]] = {}
    first_top: dict[int, list[int]] = {}
    for site in range(sites):
        f = int(fact[site])
        by_fact.setdefault(f, set()).update(int(s) for s in top8[site])
        first_top.setdefault(f, []).append(int(top1[site]))
    holders: dict[int, int] = {}
    for slots in by_fact.values():
        for s in slots:
            holders[s] = holders.get(s, 0) + 1
    private = sum(1 for slots in by_fact.values() if any(holders[s] == 1 for s in slots))
    pairs = [v for v in first_top.values() if len(v) >= 2]
    stable = sum(1 for v in pairs if v[0] == v[1])
    return {
        "distinct_top1": distinct,
        "largest_top1_share": largest / sites if sites else math.nan,
        "largest_top1_count": largest,
        "private_slot_share": private / max(1, len(by_fact)),
        "address_stability": stable / len(pairs) if pairs else math.nan,
        "sites": sites,
        "probe_facts": probe_facts,
    }


def query_statistics(q: "Tensor", fact: "Tensor", template: "Tensor", rec: "Tensor") -> dict[str, float]:
    """Mean cosine between queries of different facts, effective rank, total variance and the (template, record) share of the variance,
    all on the unit queries ``q [S, d]`` given."""
    q = q.to(torch.float64)
    sims = q @ q.T
    different = fact[:, None] != fact[None, :]
    mean_cos = float(sims[different].mean()) if bool(different.any()) else math.nan
    centred = q - q.mean(0, keepdim=True)
    cov = centred.T @ centred / max(1, q.shape[0])
    eig = torch.linalg.eigvalsh(cov).clamp_min(0.0)
    total = float(eig.sum())
    if total > 0:
        p = eig / eig.sum()
        entropy = -float((p[p > 0] * p[p > 0].log()).sum())
        rank = math.exp(entropy)
    else:
        rank = 0.0
    groups = template.to(torch.int64) * core.RECORDS_PER_CONTEXT + rec
    ss_total = float((centred**2).sum())
    ss_between = 0.0
    for g in torch.unique(groups):
        m = groups == g
        ss_between += float(m.sum()) * float(((centred[m].mean(0)) ** 2).sum())
    return {
        "mean_cosine_different": mean_cos,
        "effective_rank": rank,
        "total_variance": total,
        "template_record_variance_share": ss_between / ss_total if ss_total > 0 else math.nan,
    }


def fact_independent_share(z: "Tensor") -> float:
    """|mean z|^2 / E|z|^2 (the share of the query that is the same vector for every site)."""
    z = z.to(torch.float64)
    denominator = float((z**2).sum(-1).mean())
    return float((z.mean(0) ** 2).sum()) / denominator if denominator > 0 else math.nan


def soft_mass_outside_top8(q: "Tensor", keys: "Tensor", k: int) -> float:
    """1 - the weight of the best 8 slots in the softmax (temperature 0.2) over the ``k`` best slots, averaged over the queries; 0 at k = 8."""
    if k <= core.TOP:
        return 0.0
    scores = (q @ F.normalize(keys, dim=-1, eps=EPS).T) / core.TEMPERATURE
    top = scores.topk(min(k, scores.shape[1]), dim=-1).values
    weights = top.softmax(-1)
    return float(1.0 - weights[:, : core.TOP].sum(-1).mean())


def probe_measures(
    reads: ProbeReads,
    probe: ProbeSet,
    *,
    keys: "Tensor | None" = None,
    targets: "Tensor | None" = None,
    read_k: int = core.TOP,
    centred_arm: bool = False,
) -> dict[str, Any]:
    """Every probe measurement of section 8.1 that the arm has (``targets [S]``: the target slot of each site's fact for an arm with
    one). Values are plain floats and ints (``nan`` where undefined)."""
    out: dict[str, Any] = {"probe_accuracy": float(reads.correct.float().mean()), "probe_sites": probe.sites}
    if reads.top8 is not None and reads.scores8 is not None:
        out.update(top_slot_statistics(reads.top8[:, 0], reads.top8, probe.fact, probe.probe_facts))
        out["cosine_with_top1_key"] = float(reads.scores8[:, 0].mean()) * core.TEMPERATURE
    q_unc = None
    if reads.z is not None:
        out["fact_independent_share"] = fact_independent_share(reads.z)
        q_unc = F.normalize(reads.z, dim=-1, eps=EPS)
    elif reads.q is not None:
        q_unc = reads.q
    if q_unc is not None:
        out.update(query_statistics(q_unc, probe.fact, probe.template, probe.rec))
    if centred_arm and reads.q is not None:
        out["centred_query"] = query_statistics(reads.q, probe.fact, probe.template, probe.rec)
    if targets is not None and reads.top8 is not None and keys is not None and reads.q is not None:
        out["target_top1_recall"] = float((reads.top8[:, 0] == targets).float().mean())
        out["target_top8_recall"] = float((reads.top8 == targets[:, None]).any(-1).float().mean())
        kappa = F.normalize(keys, dim=-1, eps=EPS)[targets]
        out["mean_target_score"] = float((reads.q * kappa).sum(-1).mean())
    if keys is not None and reads.q is not None and read_k > core.TOP:
        out["read_k"] = read_k
        out["soft_mass_outside_top8"] = soft_mass_outside_top8(reads.q, keys, read_k)
    return out
