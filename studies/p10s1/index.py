# ruff: noqa: E501
"""P10S1 conventional retrieval without training (ADR-0021 section 5.5): the inverted-file index (k-means into N/256 centroids, 10 Lloyd iterations, seeded k-means++,
lists visited in order of score until at least 512 candidates are collected), F-OQ-IVF (F-OQ's trained keys read through it), KNN-W (exhaustive nearest neighbour over
the frozen model's states, no oracle, no learning) and KNN-W-IVF.

Choices the ADR leaves to the implementer (reported): clustering is Euclidean k-means on the unit-normalized points (the trained keys are scored by cosine);
centroids are scored by cosine (L2-normalized centroids); an empty cluster keeps its previous centroid; ``K`` counted for F-OQ-IVF is N/256 centroid scores plus the
number of candidate keys collected (the candidates are scored, the others are not, even though the evaluation masks a full score matrix).
"""

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS, stable_top
from studies.p9 import controls
from studies.p9.data import Stream, StudyData, restrict_stream
from studies.p9.model import AdditionSpec, ScalableMemory

from . import core
from .model import S1Memory

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

DIST_CHUNK = 8192
SOFT_TOP = 64


# --- k-means ----------------------------------------------------------------------------------------------------------------------
def _assign(points: "Tensor", centroids: "Tensor") -> "Tensor":
    """Nearest centroid (Euclidean) of every point, in row blocks."""
    c2 = (centroids * centroids).sum(1)
    out = torch.empty(points.shape[0], dtype=torch.int64)
    for start in range(0, points.shape[0], DIST_CHUNK):
        block = points[start : start + DIST_CHUNK]
        d2 = (block * block).sum(1, keepdim=True) - 2.0 * block @ centroids.T + c2[None, :]
        out[start : start + DIST_CHUNK] = d2.argmin(1)
    return out


def kmeans_plus_plus(points: "Tensor", k: int, seed: int) -> "Tensor":
    """Seeded k-means++ initialization: the first centre uniform, each next one drawn with probability proportional to the squared distance to the nearest chosen."""
    n = int(points.shape[0])
    if not 1 <= k <= n:
        raise ValueError("k must lie in 1..n")
    gen = torch.Generator().manual_seed(seed)
    first = int(torch.randint(0, n, (1,), generator=gen))
    chosen = [first]
    d2 = ((points - points[first]) ** 2).sum(1)
    for _ in range(1, k):
        total = float(d2.sum())
        if total <= 0.0:
            weights = torch.ones(n)
        else:
            weights = d2.clamp_min(0.0)
        nxt = int(torch.multinomial(weights, 1, generator=gen))
        chosen.append(nxt)
        d2 = torch.minimum(d2, ((points - points[nxt]) ** 2).sum(1))
    return points[torch.tensor(chosen)].clone()


@dataclass
class IVFIndex:
    """The inverted-file index of one set of keys: ``centroids [k, d]`` (as clustered), ``unit [k, d]`` (L2-normalized, scored by cosine), ``assign [n]`` the list of every
    key, ``sizes [k]`` the list lengths."""

    centroids: "Tensor"
    unit: "Tensor"
    assign: "Tensor"
    sizes: "Tensor"
    seed: int

    @property
    def lists(self) -> int:
        return int(self.centroids.shape[0])

    def sha256(self) -> str:
        h = hashlib.sha256()
        for t in (self.centroids, self.assign):
            c = t.detach().contiguous()
            h.update(repr((tuple(c.shape), str(c.dtype))).encode())
            h.update(_bytes(c))
        return h.hexdigest()


def _bytes(t: "Tensor") -> bytes:
    import ctypes

    return ctypes.string_at(t.data_ptr(), t.numel() * t.element_size()) if t.numel() else b""


def build_index(points: "Tensor", seed: int, lists: int | None = None, iterations: int = core.LLOYD_ITERATIONS) -> IVFIndex:
    """k-means of the unit-normalized ``points [n, d]`` into ``lists`` (default n / 256, at least 1) centroids: seeded k-means++, ``iterations`` Lloyd iterations (an empty
    cluster keeps its centroid). Deterministic in (points, seed)."""
    pts = F.normalize(points.detach().to(torch.float32), dim=-1, eps=EPS)
    n = int(pts.shape[0])
    k = max(1, n // core.IVF_LIST_TARGET) if lists is None else lists
    centroids = kmeans_plus_plus(pts, min(k, n), seed)
    for _ in range(iterations):
        assign = _assign(pts, centroids)
        sums = torch.zeros_like(centroids).index_add_(0, assign, pts)
        counts = torch.bincount(assign, minlength=centroids.shape[0])
        nonempty = counts > 0
        centroids = torch.where(nonempty[:, None], sums / counts.clamp_min(1)[:, None].to(sums.dtype), centroids)
    assign = _assign(pts, centroids)
    sizes = torch.bincount(assign, minlength=centroids.shape[0])
    return IVFIndex(centroids, F.normalize(centroids, dim=-1, eps=EPS), assign, sizes, seed)


def candidate_mask(index: IVFIndex, queries: "Tensor", minimum: int = core.IVF_CANDIDATES) -> "tuple[Tensor, Tensor]":
    """For unit ``queries [Q, d]``: the candidate mask ``[Q, n]`` (keys of the lists visited in descending centroid score until at least ``minimum`` keys are collected; all
    lists if the index holds fewer) and the number of candidates ``[Q]``."""
    scores = queries @ index.unit.T  # [Q, k]
    order = scores.argsort(dim=1, descending=True, stable=True)
    sizes = index.sizes[order]
    cum = sizes.cumsum(1)
    reached = cum >= minimum
    need = torch.where(reached.any(1), reached.to(torch.int64).argmax(1), torch.full((queries.shape[0],), index.lists - 1, dtype=torch.int64))
    rank = torch.empty_like(order)
    rank.scatter_(1, order, torch.arange(index.lists).expand(queries.shape[0], -1).contiguous())
    visited = rank <= need[:, None]
    mask = visited.gather(1, index.assign[None, :].expand(queries.shape[0], -1))
    return mask, cum.gather(1, need[:, None]).squeeze(1)


# --- F-OQ-IVF -----------------------------------------------------------------------------------------------------------------------
class IVFMemory(S1Memory):
    """F-OQ's trained memory read through the index: the 8 best keys of the visited lists' candidates by cosine, weights as F-OQ's (softmax of cosine / 0.2). Nothing is trained.
    ``candidate_counts`` and ``recall`` are measured per query during the reads."""

    def __init__(self, source: ScalableMemory, index: IVFIndex) -> None:
        spec = source.spec
        super().__init__(AdditionSpec("flat", spec.slots, core.KEY_WIDTH, "R1", 0, 0), source.seed, r1_seed=source.r1_seed)
        self.load_state_dict(source.state_dict(), strict=True)
        self.index = index
        self.candidate_counts: list[Tensor] = []
        self.recall_sum = 0.0
        self.recall_queries = 0

    def reset_measures(self) -> None:
        self.candidate_counts = []
        self.recall_sum = 0.0
        self.recall_queries = 0

    def _top_flat(self, q: "Tensor") -> "tuple[Tensor, Tensor]":
        keys = self.keys
        normalized = F.normalize(keys, dim=-1, eps=EPS)
        rows = self._rows(self.spec.slots)
        values, ids = [], []
        for start in range(0, q.shape[0], rows):
            block = q[start : start + rows]
            scores = (block @ normalized.T) / core.TEMPERATURE
            mask, counts = candidate_mask(self.index, block)
            v, i = stable_top(scores.masked_fill(~mask, -torch.inf), SOFT_TOP)
            with torch.no_grad():
                _, exhaustive = stable_top(scores, core.TOP)
                hit = (i[:, : core.TOP, None] == exhaustive[:, None, :]).any(1).float().sum(1) / core.TOP
            self.recall_sum += float(hit.sum())
            self.recall_queries += int(block.shape[0])
            self.candidate_counts.append(counts.clone())
            self.counters.key_scores += int(block.shape[0]) * self.index.lists + int(counts.sum())
            self.counters.topk_comparisons += int(counts.sum())
            values.append(v)
            ids.append(i)
        return torch.cat(values), torch.cat(ids)

    def measured(self) -> dict[str, float]:
        """Mean and 99th percentile of the candidates per query, recall of the exhaustive top-8, mean measured W per query."""
        counts = torch.cat(self.candidate_counts).float() if self.candidate_counts else torch.zeros(1)
        k_mean = self.index.lists + float(counts.mean())
        return {
            "queries": float(counts.numel()), "lists": float(self.index.lists), "candidates_mean": float(counts.mean()), "candidates_p99": float(torch.quantile(counts, 0.99)),
            "K_mean": k_mean, "V": float(core.TOP), "W_mean": core.KEY_WIDTH * k_mean + core.HIDDEN_WIDTH * core.TOP + core.HIDDEN_WIDTH**2,
            "W_p99": core.KEY_WIDTH * (self.index.lists + float(torch.quantile(counts, 0.99))) + core.HIDDEN_WIDTH * core.TOP + core.HIDDEN_WIDTH**2,
            "recall_of_exhaustive_top8": self.recall_sum / max(1, self.recall_queries),
        }


# --- KNN-W ----------------------------------------------------------------------------------------------------------------------------
def window_features(backbone: "Backbone", tokens: "Tensor") -> "Tensor":
    """``[C, 8, 224]`` the seven frozen states of every record (positions 8r .. 8r + 6 after block 0, as the W7 window at the answer site 8r + 6)."""
    h = controls.insertion_hidden(backbone, tokens[:, : core.INPUT_LENGTH].contiguous())
    rows = [h[:, core.RECORD_BYTES * r : core.RECORD_BYTES * r + core.RECORDS_PER_CONTEXT - 1].reshape(h.shape[0], -1) for r in range(core.RECORDS_PER_CONTEXT)]
    return torch.stack(rows, dim=1)


@torch.no_grad()
def knn_keys(backbone: "Backbone", data: StudyData, facts: int, stream_batches: "list[tuple[Tensor, Tensor]]") -> "tuple[Tensor, Tensor]":
    """One stored key per fact: the 224-wide window of its record at its first training occurrence, the mean stored key subtracted, unit-normalized. ``stream_batches`` is the
    first epoch of the training stream as (tokens, fact_ids) pairs. Returns the keys ``[facts, 224]`` and the subtracted mean ``[224]``. Every fact must occur."""
    raw = torch.zeros(facts, 224)
    seen = torch.zeros(facts, dtype=torch.bool)
    for tokens, ids in stream_batches:
        feats = window_features(backbone, tokens)
        flat_ids = ids.reshape(-1)
        keep = (flat_ids < facts) & ~seen[flat_ids.clamp_max(facts - 1)]
        sel = flat_ids[keep]
        raw[sel] = feats.reshape(-1, 224)[keep]
        seen[sel] = True
    if not bool(seen.all()):
        raise ValueError("a fact never occurs in the first training epoch")
    mean = raw.mean(0)
    return F.normalize(raw - mean, dim=-1, eps=EPS), mean


def first_epoch(stream: "object") -> "list[tuple[Tensor, Tensor]]":
    """The first epoch of a ``TrainingStream`` as (tokens, fact_ids) batches (every fact exactly once)."""
    upe = int(getattr(stream, "updates_per_epoch"))
    out = []
    for u in range(1, upe + 1):
        b = stream.batch(u)  # type: ignore[attr-defined]
        out.append((b.tokens, b.fact_ids))
    return out


@torch.no_grad()
def knn_predict(keys: "Tensor", answers: "Tensor", queries: "Tensor", index: IVFIndex | None = None, chunk: int = 512) -> "tuple[Tensor, Tensor]":
    """Nearest stored key by cosine (exhaustive, or among the candidates of ``index``), ties counted wrong. Returns the predicted symbol ``[Q]`` (-1 on a tie) and the
    number of keys scored per query ``[Q]``."""
    pred = torch.empty(queries.shape[0], dtype=torch.int64)
    scored = torch.empty(queries.shape[0], dtype=torch.int64)
    for start in range(0, queries.shape[0], chunk):
        q = queries[start : start + chunk]
        s = q @ keys.T
        if index is None:
            n_scored = torch.full((q.shape[0],), keys.shape[0], dtype=torch.int64)
        else:
            mask, counts = candidate_mask(index, q)
            s = s.masked_fill(~mask, -torch.inf)
            n_scored = counts + index.lists
        best = s.max(1)
        ties = (s == best.values[:, None]).sum(1) > 1
        p = answers[best.indices]
        pred[start : start + chunk] = torch.where(ties, torch.full_like(p, -1), p)
        scored[start : start + chunk] = n_scored
    return pred, scored


def knn_panel(backbone: "Backbone", data: StudyData, facts: int, keys: "Tensor", mean: "Tensor", panel: str, index: IVFIndex | None) -> dict[str, float | int]:
    """KNN-W (or KNN-W-IVF) on a panel restricted to ``facts``: correct answer sites on trained facts, the unseen-control correct count, and keys scored per query."""
    stream = restrict_stream(data.streams[core.PANEL_STREAM[panel]], data.facts, facts)
    correct = n = u_correct = u_n = 0
    scored_total = 0
    answers_all = data.facts.answer
    stored = answers_all[:facts]
    for start in range(0, stream.tokens.shape[0], 256):
        tok = stream.tokens[start : start + 256]
        ids = stream.fact_ids[start : start + 256].reshape(-1)
        feats = F.normalize(window_features(backbone, tok).reshape(-1, 224) - mean, dim=-1, eps=EPS)
        pred, scored = knn_predict(keys, stored, feats, index)
        truth = answers_all[ids]
        trained = ids < facts
        ok = pred == truth
        correct += int(ok[trained].sum())
        n += int(trained.sum())
        u_correct += int(ok[~trained].sum())
        u_n += int((~trained).sum())
        scored_total += int(scored[trained].sum())
    return {"correct": correct, "n": n, "unseen_correct": u_correct, "unseen_n": u_n, "keys_scored_per_query": scored_total / max(1, n)}


def knn_costs(facts: int, index: IVFIndex | None, keys_scored_mean: float) -> dict[str, float]:
    """Storage of 224 values per fact and 224 x keys-scored multiply-adds per query (printed beside the result, section 5.5)."""
    return {"stored_values": float(224 * facts), "stored_values_per_fact": 224.0, "madds_per_query": 224.0 * keys_scored_mean, "lists": float(0 if index is None else index.lists)}


def exact_dictionary(data: StudyData, facts: int, panel: str) -> dict[str, float | int]:
    """DICT: hash table from the identifier bytes to the answer symbol (one probe, 25 bits per fact): accuracy on trained facts of the panel."""
    stream = restrict_stream(data.streams[core.PANEL_STREAM[panel]], data.facts, facts)
    scores = controls.exact_retrieval(data.facts, stream, torch.arange(facts))
    trained = stream.fact_ids.reshape(-1) < facts
    return {"correct": int(scores.correct[trained].sum()), "n": int(trained.sum()), "probes_per_query": 1, "bits_per_fact": 25}


__all__ = ["IVFIndex", "IVFMemory", "Stream", "build_index", "candidate_mask", "knn_keys", "knn_panel", "knn_predict"]
