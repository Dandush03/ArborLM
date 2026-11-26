# ruff: noqa: E501
"""The counterfactual reads of ADR-0035 section 4, over a frozen store.

Notation as in the ADR: S1, S2 the rows of stages 1 and 2 (0-based stage index 0 and 1 here), a_s the cosine, T8(X) the eight largest with ties to the lowest row index, sigma(X) the softmax of a_s / 0.2 over X,
G = T8(S1 u S2), p the protected stage and o the other. Every function takes a ``SparseStore`` and unit queries (M, 16) and returns (M, width). ``read_a``, ``read_e``, ``read_d`` and ``read_g`` take the selection
and sigma(G) from ONE computation (``slot_view``, the same operations as ``SparseStore.read``) and differ in the per-slot weight vector only; ``read_b`` is the unmodified ``SparseStore.read`` on a store that holds
stage p's tensors alone. Positions, addresses, route, decoding and scoring are the registered ones.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import torch
from torch import Tensor

from studies.p10s2 import core
from studies.p10s2.memory import Ablation, CodeBook, MemoryArm, SparseStore
from studies.p10s2.model import LoRAAdapter

CONDITIONS = ("a", "b1", "b2", "c", "d1", "d2", "e1", "e2", "g1", "g2")


@dataclass(frozen=True)
class SlotView:
    order: Tensor  # (M, 8) selected row indices, best first, ties to the lowest row index
    sel: Tensor  # (M, 8) their cosines
    weights: Tensor  # (M, 8) sigma(G)
    stage: Tensor  # (M, 8) stage index of each selected row


def _row_stage(store: SparseStore) -> Tensor:
    return torch.cat([torch.full((r,), k, dtype=torch.long) for k, r in enumerate(store.stage_rows)])


def _row_gate(store: SparseStore) -> Tensor:
    return torch.cat([g.expand(r) for g, r in zip(store.gates, store.stage_rows, strict=True)])


def slot_view(store: SparseStore, q: Tensor) -> SlotView:
    """The registered selection and softmax, operation for operation as ``SparseStore.read`` (kept as written there so that ``read_a`` is bit-identical to it)."""
    keys = torch.cat(list(store.keys), dim=0)
    kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    a = q @ kn.t()
    order = torch.sort(a, dim=-1, descending=True, stable=True).indices[:, : core.TOP]
    sel = torch.gather(a, 1, order)
    w = torch.softmax(sel / core.TEMPERATURE, dim=-1)
    return SlotView(order, sel, w, _row_stage(store)[order])


def _combine(store: SparseStore, view: SlotView, slot_weight: Tensor) -> Tensor:
    values = torch.cat(list(store.values), dim=0)
    return (slot_weight.unsqueeze(-1) * values[view.order]).sum(dim=1)


def read_a(store: SparseStore, q: Tensor) -> Tensor:
    """a: sum over G of sigma(G)_s g_stage(s) V_s, the registered read."""
    view = slot_view(store, q)
    return _combine(store, view, view.weights * _row_gate(store)[view.order])


def read_e(store: SparseStore, q: Tensor, p: int) -> Tensor:
    """e(p): sum over G n Sp of sigma(G)_s g_p V_s: stage o's gate is set to 0, the selection and the softmax stay."""
    view = slot_view(store, q)
    gate = torch.where(_row_stage(store) == p, _row_gate(store), torch.zeros(()))
    return _combine(store, view, view.weights * gate[view.order])


def read_d(store: SparseStore, q: Tensor, p: int) -> Tensor:
    """d(p): K = G n Sp; sum over K of sigma(K)_s g_p V_s, the zero vector if K is empty (the displacement stays; the mass stage o held and stage o's values are gone)."""
    view = slot_view(store, q)
    in_p = view.stage == p
    logits = (view.sel / core.TEMPERATURE).masked_fill(~in_p, float("-inf"))
    w = torch.softmax(logits, dim=-1)
    w = torch.where(in_p.any(dim=1, keepdim=True), w, torch.zeros(()))
    return _combine(store, view, w * store.gates[p])


def single_stage_store(store: SparseStore, p: int) -> SparseStore:
    """A store holding stage p's tensors alone (copies)."""
    return SparseStore.from_state({"width": store.width, "stage_rows": [store.stage_rows[p]], "keys": [store.keys[p].detach()], "values": [store.values[p].detach()], "gates": [store.gates[p].detach()]})


def read_b(store: SparseStore, q: Tensor, p: int) -> Tensor:
    """b(p): the unmodified ``SparseStore.read`` on stage p alone: an oracle bank switch."""
    return single_stage_store(store, p).read(q)


def read_c(store: SparseStore, q: Tensor) -> Tensor:
    """c: b(1) + b(2): each stage read at full weight."""
    return read_b(store, q, 0) + read_b(store, q, 1)


def read_g(store: SparseStore, q: Tensor, p: int) -> Tensor:
    """g(p): b(p) + the part of the registered read that falls on stage o's rows (sum over G n So of sigma(G)_s g_o V_s): competition removed, stage o's values exactly as registered."""
    return read_b(store, q, p) + read_e(store, q, 1 - p)


def condition_reader(store: SparseStore, cond: str) -> Callable[[Tensor], Tensor]:
    """The read function of one condition of section 4 on a store (two stages for every condition but ``a`` on a one-stage store). Single-stage stores for b are built once."""
    if cond not in CONDITIONS:
        raise ValueError(f"unknown condition {cond!r}")
    if cond == "a":
        return lambda q: read_a(store, q)
    kind, p = cond[0], (int(cond[1]) - 1 if len(cond) > 1 else 0)
    if kind == "b":
        alone = single_stage_store(store, p)
        return lambda q: alone.read(q)
    if kind == "c":
        alone0, alone1 = single_stage_store(store, 0), single_stage_store(store, 1)
        return lambda q: alone0.read(q) + alone1.read(q)
    if kind == "d":
        return lambda q: read_d(store, q, p)
    if kind == "e":
        return lambda q: read_e(store, q, p)
    if kind == "g":
        alone_p = single_stage_store(store, p)
        return lambda q: alone_p.read(q) + read_e(store, q, 1 - p)
    raise ValueError(f"unknown condition {cond!r}")  # pragma: no cover


class DiagArm(MemoryArm):
    """A ``MemoryArm`` whose ``prepare`` substitutes the condition's read for ``SparseStore.read``; everything else (queries from the code book, positions, accumulation, route "none") is the registered code."""

    def __init__(self, store: SparseStore, layer: int, codes: CodeBook, cond: str, reader: Callable[[Tensor], Tensor] | None = None) -> None:
        super().__init__(store, layer, codes)
        self.cond = cond
        self.reader = reader if reader is not None else condition_reader(store, cond)

    def prepare(self, reads: Sequence[Sequence[tuple[int, str, int]]], batch: int, length: int, device: torch.device, ablation: Ablation | None = None) -> tuple[Tensor | None, LoRAAdapter | None]:
        if ablation is not None:
            raise ValueError("D0 scores no ablation")
        if not any(reads):
            return None, None
        bi, pi, q = self.queries(reads)
        r = self.reader(q.to(device))
        add = torch.zeros(batch, length, self.store.width, device=device, dtype=r.dtype)
        add = add.index_put((bi.to(device), pi.to(device)), r, accumulate=True)
        return add, None
