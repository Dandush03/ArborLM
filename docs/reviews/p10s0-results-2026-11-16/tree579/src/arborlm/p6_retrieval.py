"""P6-E inference-only retrieval variants (ADR-0011 section 3.2).

Every variant is a wrapper constructed from a restored ``pilot_model.Memory``. F0 and T0 are the
unmodified reference ``Memory`` and have no wrapper here. A wrapper exposes ``lookup(q)`` and
``forward(h)`` with the reference return contract, builds its caches once at construction, binds
them to a hash of the source tensors, never mutates the wrapped module and refuses to run when
gradients are enabled or when the wrapped module is in training mode.

Status: SPEC: HUMAN-APPROVED (ADR-0011); implementation self-checked only, not independently
audited, not Astra validated.
"""

import ctypes
import hashlib
import time
from typing import Any, Literal

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .p5_config import FIXED, FLAT, LEARNED
from .p5_model import Model
from .pilot_model import (
    BRANCHES,
    EPS,
    PER_BRANCH,
    TEMP,
    TOP,
    Lookup,
    Memory,
    PilotModel,
    stable_top,
)

GUARD_DELTA = 1e-4
FLAT_VARIANTS = ("F1", "F2")
TREE_VARIANTS = ("T1", "T2", "T3", "T4", "T5")
ALL_VARIANTS = (*FLAT_VARIANTS, *TREE_VARIANTS)
VISIT = 2
Binding = Literal["hash", "fingerprint"]


def variants_for(kind: str) -> tuple[str, ...]:
    """Registered non-reference variants applicable to a memory kind."""
    if kind == FLAT:
        return FLAT_VARIANTS
    if kind in (FIXED, LEARNED):
        return TREE_VARIANTS
    raise ValueError("unknown memory kind")


def bit_equal(a: Tensor, b: Tensor) -> bool:
    """Bitwise equality of two tensors (float tensors compared by bit pattern)."""
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    a, b = a.contiguous(), b.contiguous()
    if a.dtype.is_floating_point:
        width = {torch.float32: torch.int32, torch.float64: torch.int64}[a.dtype]
        return bool(torch.equal(a.view(width), b.view(width)))
    return bool(torch.equal(a, b))


def tensors_digest(tensors: dict[str, Tensor]) -> str:
    """SHA-256 over names, shapes, dtypes and raw bytes of float32/int64 tensors."""
    digest = hashlib.sha256()
    for name in sorted(tensors):
        tensor = tensors[name].detach().contiguous()
        digest.update(f"{name}|{list(tensor.shape)}|{tensor.dtype}|".encode())
        if tensor.device.type != "cpu":
            raise ValueError("P6 variants are CPU-only")
        digest.update(ctypes.string_at(tensor.data_ptr(), tensor.nbytes))
    return digest.hexdigest()


def _version(tensor: Tensor) -> int:
    try:
        return int(tensor._version)
    except RuntimeError:  # inference tensors do not track versions
        return -1


def first_occurrence_top(scores: Tensor, count: int) -> tuple[Tensor, Tensor]:
    """``count`` successive first-occurrence maxima along the last dimension.

    On ascending-ID input the first occurrence is the lowest ID, so equal scores come out in
    ascending-ID order, which is the registered tie rule. Returns values and positions.
    """
    work = scores.clone()
    values = scores.new_empty((scores.shape[0], count))
    positions = torch.empty((scores.shape[0], count), dtype=torch.int64)
    for rank in range(count):
        best, where = work.max(dim=-1)
        values[:, rank] = best
        positions[:, rank] = where
        work.scatter_(-1, where[:, None], -torch.inf)
    return values, positions


def reference_arithmetic_t2(
    q: Tensor, routes: Tensor, branch_ids: Tensor, normalized_keys: Tensor
) -> tuple[Tensor, Tensor]:
    """T2 arithmetic for given queries: ID-ordered candidates, no per-query ID sort.

    Returns the selected scores and selected slot IDs in the reference order (descending score,
    then ascending slot ID).
    """
    ordered = branch_ids.sort(dim=-1).values
    ids = (ordered[..., None] * PER_BRANCH + torch.arange(PER_BRANCH, device="cpu")).flatten(1)
    local = normalized_keys[ids]
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    prior = routes.log_softmax(-1).gather(-1, ordered)
    scores = scores + prior.repeat_interleave(PER_BRANCH, dim=-1)
    values, positions = stable_top(scores, TOP)
    return values, ids.gather(-1, positions)


class FastMemory(Memory):
    """Base class: read-only wrapper around a restored ``Memory``.

    ``Memory.__init__`` is deliberately not called: the wrapper owns no parameters and no
    buffers, only plain cache tensors. The wrapped module is held in an unregistered tuple so
    that ``wrapper.train()``/``wrapper.eval()`` can never change the wrapped module's mode.
    """

    variant_id: str
    applies_to: tuple[str, ...]
    caches: dict[str, Tensor]

    def __init__(self, source: Memory, variant_id: str, *, binding: Binding = "hash") -> None:
        nn.Module.__init__(self)
        if source.variant not in self.applies_to:
            raise ValueError(f"{variant_id} does not apply to {source.variant}")
        self.variant = source.variant
        self.variant_id = variant_id
        self._source = (source,)
        self.binding = binding
        self.fallback_log: list[tuple[int, int]] = []
        self.caches = {}
        self._bound_names = ("keys",) if self.variant == FLAT else ("keys", "router")
        build_start = time.perf_counter_ns()
        with torch.no_grad():
            self._build(source)
        self.build_ns = time.perf_counter_ns() - build_start
        bind_start = time.perf_counter_ns()
        self._digest = tensors_digest(self._bound())
        self._fingerprint = self._current_fingerprint()
        self.bind_ns = time.perf_counter_ns() - bind_start
        self.eval()

    # -- subclass hooks -------------------------------------------------------------------
    def _build(self, source: Memory) -> None:
        raise NotImplementedError

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        raise NotImplementedError

    # -- source binding -------------------------------------------------------------------
    @property
    def source(self) -> Memory:
        return self._source[0]

    def _bound(self) -> dict[str, Tensor]:
        return {name: getattr(self.source, name).detach() for name in self._bound_names}

    def _current_fingerprint(self) -> tuple[tuple[int, int, tuple[int, ...]], ...]:
        """O(1) check: storage address, in-place version counter and shape of each source."""
        tensors = (getattr(self.source, name) for name in self._bound_names)
        return tuple((t.data_ptr(), _version(t), tuple(t.shape)) for t in tensors)

    def verify_source(self) -> None:
        """Full hash check of the bound source tensors."""
        if tensors_digest(self._bound()) != self._digest:
            raise RuntimeError("source tensors changed after the cache was built")

    def _guard(self) -> None:
        if torch.is_grad_enabled():
            raise RuntimeError("P6 retrieval variants are inference-only: gradients are enabled")
        if self.training or self.source.training:
            raise RuntimeError("P6 retrieval variants refuse to run in training mode")
        if self.binding == "hash":
            self.verify_source()
        elif self._current_fingerprint() != self._fingerprint:
            raise RuntimeError("source tensors changed after the cache was built")

    # -- read-only views of the wrapped module's tensors (for P5 helper functions) ------------
    def __getattr__(self, name: str) -> Any:
        try:
            return super().__getattr__(name)
        except AttributeError:
            if name in ("wq", "wo", "values", "gate") and "_source" in self.__dict__:
                return getattr(self.__dict__["_source"][0], name)
            raise

    # -- reference contract ---------------------------------------------------------------
    @property
    def persistent_extra_bytes(self) -> int:
        return sum(t.nbytes for t in self.caches.values())

    def reset_log(self) -> None:
        self.fallback_log.clear()

    def fallback_fraction(self) -> float | None:
        queries = sum(n for n, _ in self.fallback_log)
        if not self.fallback_log or queries == 0:
            return None
        return sum(f for _, f in self.fallback_log) / queries

    def lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        self._guard()
        return self._lookup(q)

    def forward(self, h: Tensor) -> tuple[Tensor, Lookup]:
        self._guard()
        src = self.source
        q = F.normalize(F.linear(h, src.wq), dim=-1, eps=EPS).reshape(-1, 16)
        scores, lookup = self._lookup(q)
        combined = (scores.softmax(-1)[..., None] * src.values[lookup.selected]).sum(dim=-2)
        return h + src.gate.sigmoid() * F.linear(combined.reshape(h.shape), src.wo), lookup


# ---------------------------------------------------------------------------------------------
# Flat variants
# ---------------------------------------------------------------------------------------------
class _FlatMemory(FastMemory):
    applies_to = (FLAT,)

    def _build(self, source: Memory) -> None:
        # Same operation as the reference, executed once at load instead of on every call.
        self.caches["normalized_keys"] = F.normalize(source.keys, dim=-1, eps=EPS).detach()

    def _scores(self, q: Tensor) -> Tensor:
        return (q @ self.caches["normalized_keys"].T) / TEMP


class F1(_FlatMemory):
    """Normalized key matrix computed once at load. Nothing else changes."""

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        weights, selected = stable_top(self._scores(q), TOP)
        return weights, Lookup(selected, None)


class F2(_FlatMemory):
    """F1 plus the exact selection kernel: nine successive first-occurrence maxima.

    The first eight are the selection. The ninth feeds the reference's registered tie-safety
    check (strictly descending among the nine); rows that fail it use the reference's stable
    argsort, exactly as ``stable_top`` does.
    """

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        scores = self._scores(q)
        top, positions = first_occurrence_top(scores, TOP + 1)
        safe = (top[:, :-1] > top[:, 1:]).all(dim=-1)
        selected = positions[:, :TOP].contiguous()
        if not bool(safe.all()):
            selected[~safe] = scores[~safe].argsort(dim=-1, descending=True, stable=True)[:, :TOP]
        self.fallback_log.append((int(q.shape[0]), int((~safe).sum())))
        return scores.gather(-1, selected), Lookup(selected, None)


# ---------------------------------------------------------------------------------------------
# Tree variants
# ---------------------------------------------------------------------------------------------
class _TreeMemory(FastMemory):
    applies_to = (FIXED, LEARNED)

    def _build(self, source: Memory) -> None:
        self.caches["normalized_keys"] = F.normalize(source.keys, dim=-1, eps=EPS).detach()
        self.caches["normalized_router"] = F.normalize(source.router, dim=-1, eps=EPS).detach()
        self.caches["slot_offsets"] = torch.arange(PER_BRANCH, device="cpu")

    @property
    def _nk(self) -> Tensor:
        return self.caches["normalized_keys"]

    @property
    def _blocks(self) -> Tensor:
        """The normalized key table viewed as 16 branch blocks of 256 x 16 (no copy)."""
        return self._nk.view(BRANCHES, PER_BRANCH, 16)

    def _route(self, q: Tensor) -> tuple[Tensor, Tensor]:
        routes = (q @ self.caches["normalized_router"].T) / TEMP
        _, branch_ids = stable_top(routes, VISIT)
        return routes, branch_ids

    def _rank_order_candidates(self, branch_ids: Tensor) -> Tensor:
        """Candidate IDs in the reference's order: visited branches in route-rank order."""
        offsets = self.caches["slot_offsets"]
        return (branch_ids[..., None] * PER_BRANCH + offsets).flatten(1)

    def _id_order(self, branch_ids: Tensor) -> tuple[Tensor, Tensor]:
        """Visited branches sorted by branch ID and the matching ascending slot IDs."""
        ordered = branch_ids.sort(dim=-1).values
        ids = (ordered[..., None] * PER_BRANCH + self.caches["slot_offsets"]).flatten(1)
        return ordered, ids

    @staticmethod
    def _with_prior(contraction: Tensor, routes: Tensor, branches: Tensor) -> Tensor:
        prior = routes.log_softmax(-1).gather(-1, branches)
        return contraction + prior.repeat_interleave(PER_BRANCH, dim=-1)

    @staticmethod
    def _result(
        values: Tensor, selected: Tensor, candidates: Tensor, branch_ids: Tensor, routes: Tensor
    ) -> tuple[Tensor, Lookup]:
        return values, Lookup(selected, candidates, branch_ids=branch_ids, route_scores=routes)


class T1(_TreeMemory):
    """Normalized key table and router computed once; candidates gathered from the table.

    Scoring, prior and selection are the reference code path (rank-ordered candidates,
    ``stable_top`` with IDs, which sorts them per query).
    """

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        routes, branch_ids = self._route(q)
        indices = self._rank_order_candidates(branch_ids)
        local = self._nk[indices]
        scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
        scores = self._with_prior(scores, routes, branch_ids)
        values, selected = stable_top(scores, TOP, indices)
        return self._result(values, selected, indices, branch_ids, routes)


class T2(_TreeMemory):
    """T1 with candidate lists built in ascending slot-ID order (branches sorted by ID).

    The per-query sort of 512 candidate IDs is unnecessary, so selection is ``stable_top`` on
    ID-ordered scores. Returned ``candidate_ids`` and ``branch_ids`` keep the reference's
    rank order; only the internal computation is ID-ordered.
    """

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        routes, branch_ids = self._route(q)
        values, selected = reference_arithmetic_t2(q, routes, branch_ids, self._nk)
        candidates = self._rank_order_candidates(branch_ids)
        return self._result(values, selected, candidates, branch_ids, routes)


class _GuardedTree(_TreeMemory):
    """T3, T4, T5: fast scoring plus a guard band around near-ties.

    Any query whose fast scores have an adjacent gap below ``GUARD_DELTA`` among the top nine
    candidates is recomputed with T2 arithmetic. The per-call fallback count is logged.
    """

    selection: Literal["topk", "maxima"] = "topk"

    def _contract(self, q: Tensor, ordered: Tensor) -> Tensor:
        """Raw cosine products /TEMP for ID-ordered candidates, shape [N, 512]."""
        raise NotImplementedError

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        routes, branch_ids = self._route(q)
        ordered, ids = self._id_order(branch_ids)
        scores = self._with_prior(self._contract(q, ordered), routes, ordered)
        if self.selection == "topk":
            top, positions = scores.topk(TOP + 1, sorted=True)
        else:
            top, positions = first_occurrence_top(scores, TOP + 1)
        flagged = ((top[:, :-1] - top[:, 1:]) < GUARD_DELTA).any(dim=-1)
        values = top[:, :TOP]
        selected = ids.gather(-1, positions[:, :TOP])
        if bool(flagged.any()):
            fixed_values, fixed_selected = reference_arithmetic_t2(
                q[flagged], routes[flagged], branch_ids[flagged], self._nk
            )
            values = values.clone()
            values[flagged] = fixed_values
            selected[flagged] = fixed_selected
        self.fallback_log.append((int(q.shape[0]), int(flagged.sum())))
        return self._result(
            values.contiguous(),
            selected,
            self._rank_order_candidates(branch_ids),
            branch_ids,
            routes,
        )


class T3(_GuardedTree):
    """T2 with the contraction expressed on branch blocks (keys viewed as 16 x 256 x 16)."""

    def _contract(self, q: Tensor, ordered: Tensor) -> Tensor:
        n = q.shape[0]
        blocks = self._blocks[ordered.reshape(-1)]  # [2N, 256, 16]
        per_block_query = q.repeat_interleave(VISIT, dim=0).unsqueeze(-1)  # [2N, 16, 1]
        return torch.bmm(blocks, per_block_query).reshape(n, VISIT * PER_BRANCH) / TEMP


class _BlockScored(_GuardedTree):
    """Scoring without gathering candidate keys: one dense product per visited branch block."""

    def _contract(self, q: Tensor, ordered: Tensor) -> Tensor:
        n = q.shape[0]
        flat = ordered.reshape(-1)  # slot s = 2 * query + position in ID order
        by_branch = flat.argsort(stable=True)
        counts = torch.bincount(flat, minlength=BRANCHES).tolist()
        out = q.new_empty((n * VISIT, PER_BRANCH))
        start = 0
        for branch, count in enumerate(counts):
            if count:
                rows = by_branch[start : start + count]
                queries = torch.div(rows, VISIT, rounding_mode="floor")
                out[rows] = q[queries] @ self._blocks[branch].T
                start += count
        return out.reshape(n, VISIT * PER_BRANCH) / TEMP


class T4(_BlockScored):
    """T2 semantics scored per branch block (queries grouped by visited branch), top-9 kernel."""

    selection = "topk"


class T5(_BlockScored):
    """T4 scoring plus nine successive first-occurrence maxima in place of ``topk(9)``."""

    selection = "maxima"


REGISTRY: dict[str, type[FastMemory]] = {
    "F1": F1,
    "F2": F2,
    "T1": T1,
    "T2": T2,
    "T3": T3,
    "T4": T4,
    "T5": T5,
}


def build_memory_variant(
    memory: Memory, variant_id: str, *, binding: Binding = "hash"
) -> FastMemory:
    if variant_id not in REGISTRY:
        raise ValueError(f"unregistered P6-E variant {variant_id}")
    return REGISTRY[variant_id](memory, variant_id, binding=binding)


# ---------------------------------------------------------------------------------------------
# Full model whose addition is the variant
# ---------------------------------------------------------------------------------------------
class VariantModel(nn.Module):
    """A full P5 model whose memory addition is a variant, sharing the source backbone.

    The source model is held unregistered so that ``train()``/``eval()`` on this object never
    touches the source model's backbone. It exposes the attributes used by the P5 timing
    scopes (``addition``, ``memory``, ``cell``, token/position/blocks/final_norm/mask).
    """

    def __init__(self, source: Model, addition: FastMemory) -> None:
        super().__init__()
        if source.addition is not addition.source:
            raise ValueError("variant addition does not wrap the source model's memory")
        self._model = (source,)
        self.cell = source.cell
        self.addition = addition
        self.bypass = False
        self.eval()

    def forward(self, tokens: Tensor) -> tuple[Tensor, Lookup | None]:
        if self._model[0].training:
            raise RuntimeError("P6 retrieval variants refuse to run in training mode")
        return PilotModel.forward(self, tokens)  # type: ignore[arg-type]

    @property
    def token(self) -> nn.Embedding:
        return self._model[0].token

    @property
    def position(self) -> nn.Embedding:
        return self._model[0].position

    @property
    def blocks(self) -> nn.ModuleList:
        return self._model[0].blocks

    @property
    def final_norm(self) -> nn.LayerNorm:
        return self._model[0].final_norm

    @property
    def mask(self) -> Tensor:
        return self._model[0].mask

    @property
    def memory(self) -> FastMemory:
        return self.addition


def build_variant_model(
    model: Model, variant_id: str, *, binding: Binding = "hash"
) -> VariantModel:
    memory = model.addition
    if not isinstance(memory, Memory):
        raise ValueError("P6 variants require a memory model")
    return VariantModel(model, build_memory_variant(memory, variant_id, binding=binding))


__all__ = [
    "ALL_VARIANTS",
    "FLAT_VARIANTS",
    "GUARD_DELTA",
    "REGISTRY",
    "TREE_VARIANTS",
    "FastMemory",
    "VariantModel",
    "bit_equal",
    "build_memory_variant",
    "build_variant_model",
    "first_occurrence_top",
    "reference_arithmetic_t2",
    "tensors_digest",
    "variants_for",
]
