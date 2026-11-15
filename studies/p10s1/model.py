# ruff: noqa: E501
"""P10S1 models (ADR-0021 section 3): F-OQ (flat, oracle query), T-OQ (learned tree, oracle query), H8 (hashed exact address), R2 (oracle address) and D-OQ
(parameter-matched dense map of the same code), on the frozen backbone, read at the answer sites only. Evaluation-only reads (F-OQ-IVF) live in ``index``.

New code, no edit of P9 or P9-I and no monkeypatching:

* F-OQ, T-OQ and R2 are P9's ``ScalableMemory`` (flat or learned tree, rung R1 or R2) subclassed once to count work (``S1Memory``); F-OQ and R2 therefore
  reproduce P9-I's R1 and R2 forward and training step bit for bit (gate G4; the unit tests compare them). The counters are plain integers, never tensors,
  so the state dict and the parameter groups are P9-I's.
* H8 is ``ScalableMemory`` at the R2 rung (values, ``wo``, gate; no keys, no query projection) with the selection replaced by 8 distinct slots from a seeded hash
  of the identifier, weights 1/8 (zero scores through the same softmax). Slots are shared between facts.
* D-OQ: the oracle code (the very tensor F-OQ's query is) -> ``w1 [h, 16]`` + ``b1 [h]`` -> exact GELU -> ``w2 [32, h]`` -> sigmoid(gate), gate -2, added at the
  answer site. ``w1``, ``b1`` ~ U(-1/4, 1/4), ``w2`` ~ U(-1/sqrt(h), 1/sqrt(h)) from generators seeded ``seed + 3000``, ``+ 5000``, ``+ 4000``; h from
  ``core.doq_hidden`` so that 49 h + 1 equals F-OQ's parameter count within 0.1% (gate G8).

Every forward takes tokens only: the identity of the queried fact reaches the memory through the identifier bytes of the record being asked (the oracle,
section 3), never through a table (gate G6).
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import torch
from torch import nn
from torch.nn import functional as F

from studies.p9 import model as p9model
from studies.p9.model import AdditionSpec, P9Model, ScalableMemory, Selection

from . import core

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

WIDTH = core.HIDDEN_WIDTH
SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
GROUPS = ("keys", "values", "router", "projections", "dense")
_LEAF_GROUP = {"keys": "keys", "values": "values", "router": "router", "wo": "projections", "gate": "projections"}
_DENSE_LEAVES = ("w1", "b1", "w2", "gate")


def uniform_matrix(seed: int, bound: float, *shape: int) -> "Tensor":
    """``U(-bound, bound)`` from a generator seeded ``seed`` (CPU float32)."""
    gen = torch.Generator(device="cpu").manual_seed(seed)
    return (torch.rand(shape, generator=gen, dtype=torch.float32) * 2.0 - 1.0) * bound


# --- work counters (section 7.4; gate G7) --------------------------------------------------------------------------------------
@dataclass
class WorkCounters:
    """Instrumented counters of the forward: queries, key scores (each 16 wide), value rows read, and top-k comparisons (counted separately, section 7.4 item 1).
    Plain Python integers incremented from the shapes of the tensors the read actually computed."""

    queries: int = 0
    key_scores: int = 0
    value_rows: int = 0
    topk_comparisons: int = 0
    hidden_units: int = 0  # D-OQ: hidden units evaluated

    def reset(self) -> None:
        self.queries = self.key_scores = self.value_rows = self.topk_comparisons = self.hidden_units = 0

    def per_query(self) -> dict[str, float]:
        """K, V and W = 16 K + 32 V + 1,024 per query; for D-OQ the hidden units h and W = 48 h (bias additions h)."""
        q = max(1, self.queries)
        if self.hidden_units:
            h = self.hidden_units / q
            return {"queries": float(self.queries), "K": 0.0, "V": 0.0, "hidden": h, "W": 48.0 * h, "bias_additions": h, "topk_comparisons": 0.0}
        k, v = self.key_scores / q, self.value_rows / q
        return {"queries": float(self.queries), "K": k, "V": v, "topk_comparisons": self.topk_comparisons / q, "W": core.KEY_WIDTH * k + WIDTH * v + WIDTH * WIDTH}


# --- the memories ----------------------------------------------------------------------------------------------------------------
class S1Memory(ScalableMemory):
    """P9's ``ScalableMemory`` with work counters. Flat or learned tree, rung R1 (oracle query) or R2 (oracle address); no parameter, buffer or computation is added."""

    def __init__(self, spec: AdditionSpec, seed: int, *, fact_lut: "Tensor | None" = None, r1_seed: int | None = None) -> None:
        super().__init__(spec, seed, fact_lut=fact_lut, r1_seed=r1_seed)
        self.counters = WorkCounters()

    def _top_flat(self, q: "Tensor") -> "tuple[Tensor, Tensor]":
        out = super()._top_flat(q)
        scores = int(q.shape[0]) * int(cast("Tensor", self.keys).shape[0])
        self.counters.key_scores += scores
        self.counters.topk_comparisons += scores
        return out

    def _top_tree(self, q: "Tensor") -> "tuple[Tensor, Tensor, Tensor, Tensor]":
        values, ids, branch_ids, routes = super()._top_tree(q)
        per_query = int(routes.shape[1]) + int(branch_ids.shape[1]) * self.spec.per_branch  # router scores + candidate keys scored
        self.counters.key_scores += int(q.shape[0]) * per_query
        self.counters.topk_comparisons += int(q.shape[0]) * (int(routes.shape[1]) + int(branch_ids.shape[1]) * self.spec.per_branch)
        return values, ids, branch_ids, routes

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection:
        sel = super().select(h_pre, tokens)
        self.counters.queries += int(sel.selected.shape[0]) * int(sel.selected.shape[1])
        self.counters.value_rows += int(sel.selected.shape[0]) * int(sel.selected.shape[1]) * int(sel.selected.shape[2])
        return sel

    def select_codes(self, codes: "Tensor") -> "tuple[Tensor, Tensor]":
        """Top-8 slot ids ``[n, 8]`` and scores of the unit queries ``codes [n, 16]`` (fact level, no tokens: separability and the index comparisons). Not counted."""
        if self.spec.rung != "R1":
            raise ValueError("select_codes needs an oracle-query memory")
        saved = (self.counters.queries, self.counters.key_scores, self.counters.value_rows, self.counters.topk_comparisons)
        try:
            values, ids = self._top_flat(codes) if self.spec.arch == "flat" else self._top_tree(codes)[:2]
        finally:
            self.counters.queries, self.counters.key_scores, self.counters.value_rows, self.counters.topk_comparisons = saved
        return ids[:, : core.TOP], values[:, : core.TOP]


_M64 = p9model._M64


def h8_slots(seed: int, code: int, slots: int) -> tuple[int, ...]:
    """8 distinct slots from a seeded hash of the identifier code (splitmix64 on Python integers; a repeated slot is redrawn)."""
    out: list[int] = []
    attempt = 0
    base = p9model._mix64((seed ^ 0x2545F4914F6CDD1D) & _M64)
    while len(out) < core.TOP:
        s = p9model._mix64((base + code * 64 + attempt) & _M64) % slots
        attempt += 1
        if s not in out:
            out.append(s)
    return tuple(out)


class H8Memory(S1Memory):
    """Hashed exact address: 8 slots per fact from ``h8_slots`` (shared between facts), weights 1/8. Learned: values, ``wo``, gate. Built on P9's R2 rung (no keys, no
    query projection); the selection is replaced, ``delta`` is P9's."""

    def __init__(self, slots: int, seed: int, hash_seed: int) -> None:
        super().__init__(AdditionSpec("flat", slots, core.KEY_WIDTH, "R2", 0, 0), seed, fact_lut=torch.zeros(1, dtype=torch.int64))
        self.hash_seed = hash_seed
        self._cache: dict[int, tuple[int, ...]] = {}

    def slots_of(self, code: int) -> tuple[int, ...]:
        if code not in self._cache:
            self._cache[code] = h8_slots(self.hash_seed, code, self.spec.slots)
        return self._cache[code]

    def slot_table(self, codes: "Tensor") -> "Tensor":
        """``[..., 8]`` slots of the identifier codes ``codes [...]`` (int64)."""
        flat = codes.reshape(-1).tolist()
        return torch.tensor([self.slots_of(int(c)) for c in flat], dtype=torch.int64).reshape(*codes.shape, core.TOP)

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection:
        b, length, _ = h_pre.shape
        if length < core.INPUT_LENGTH:
            raise ValueError("H8 needs the full 63 input positions")
        positions = torch.tensor(p9model.read_positions_for(self.spec, length), dtype=torch.int64)
        slots = self.slot_table(p9model.identifier_codes(tokens))  # [B, 8, 8]
        self.counters.queries += int(slots.shape[0]) * int(slots.shape[1])
        self.counters.value_rows += int(slots.numel() // core.TOP) * core.TOP
        return Selection(positions=positions, selected=slots, scores=torch.zeros(slots.shape, dtype=torch.float32), candidate_ids=None, candidate_scores=None, branches=None, route_scores=None, length=length)

    def select_codes(self, codes: "Tensor") -> "tuple[Tensor, Tensor]":  # pragma: no cover - H8 has no query code
        raise ValueError("H8 has no query code")


class OracleCodes:
    """The fixed random unit code of a fact (a seeded hash of the identifier, width 16): exactly F-OQ's query, so that D-OQ's input tensor is F-OQ's code tensor."""

    def __init__(self, r1_seed: int, width: int = core.KEY_WIDTH) -> None:
        self.r1_seed, self.width = r1_seed, width
        self._cache: dict[int, list[float]] = {}

    def of_codes(self, ident: "Tensor") -> "Tensor":
        """``[n, width]`` unit codes of identifier codes ``ident [n]`` (int64)."""
        rows = []
        for value in ident.tolist():
            if value not in self._cache:
                self._cache[value] = p9model.unit_code(self.r1_seed, value, self.width)
            rows.append(self._cache[value])
        return torch.tensor(rows, dtype=torch.float32)

    def __call__(self, tokens: "Tensor") -> "Tensor":
        """``[B, 8, width]`` codes of the records' identifiers (positions 8r + 1 .. 8r + 4), as ``ScalableMemory._oracle_codes`` computes them."""
        codes = p9model.identifier_codes(tokens)
        unique, inverse = torch.unique(codes, return_inverse=True)
        return self.of_codes(unique)[inverse]


@dataclass
class CodeRead:
    """What D-OQ's ``select`` returns: the oracle codes ``[B, 8, 16]`` of the records at the answer sites (there is no slot selection)."""

    codes: "Tensor"
    length: int


class DOQDense(nn.Module):
    """D-OQ (section 5.3): code -> ``w1 [h, 16]`` + ``b1`` -> exact GELU -> ``w2 [32, h]`` -> sigmoid(gate), added at the answer sites; zero elsewhere."""

    def __init__(self, hidden: int, seed: int, r1_seed: int) -> None:
        super().__init__()
        self.hidden = hidden
        self.w1 = nn.Parameter(uniform_matrix(seed + 3000, core.DOQ_INIT_BOUND_FANIN, hidden, core.KEY_WIDTH))
        self.b1 = nn.Parameter(uniform_matrix(seed + 5000, core.DOQ_INIT_BOUND_FANIN, hidden))
        self.w2 = nn.Parameter(uniform_matrix(seed + 4000, 1.0 / math.sqrt(hidden), WIDTH, hidden))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32))
        self.codes = OracleCodes(r1_seed)
        self.counters = WorkCounters()

    def delta(self, h_pre: "Tensor", read: CodeRead) -> "Tensor":
        """``[B, 63, 32]`` addition: zero except at the eight answer sites."""
        hidden = F.gelu(F.linear(read.codes, self.w1, self.b1), approximate="none")
        out = self.gate.sigmoid() * F.linear(hidden, self.w2)
        n = int(read.codes.shape[0]) * int(read.codes.shape[1])
        self.counters.queries += n
        self.counters.hidden_units += int(hidden.numel())
        positions = SITES[SITES < h_pre.shape[1]]
        full = h_pre.new_zeros(h_pre.shape)
        return full.index_copy(1, positions, out)


# --- the model --------------------------------------------------------------------------------------------------------------------
Addition = S1Memory | H8Memory | DOQDense


def spec_for(arm: str, slots: int) -> AdditionSpec:
    """The P9 addition spec behind an arm."""
    if arm == "F-OQ":
        return AdditionSpec("flat", slots, core.KEY_WIDTH, "R1", 0, 0)
    if arm == "T-OQ":
        return AdditionSpec("learned_tree", slots, core.KEY_WIDTH, "R1", slots // core.BRANCH_SIZE, 0)
    if arm in ("H8", "R2"):
        return AdditionSpec("flat", slots, core.KEY_WIDTH, "R2", 0, 0)
    if arm == "D-OQ":
        return AdditionSpec("dense", slots, core.KEY_WIDTH, "R1", 0, core.doq_hidden(slots))
    raise ValueError(f"unknown P10S1 arm {arm!r}")


class P10S1Model(P9Model):
    """Frozen P4 backbone (a deep copy) plus the arm's addition; nothing of the backbone is ever trainable."""

    addition: Any  # S1Memory | H8Memory | DOQDense

    def __init__(self, arm: str, slots: int, seed: int, backbone: "Backbone", *, fact_lut: "Tensor | None" = None, r1_seed: int, hash_seed: int | None = None) -> None:
        if arm not in core.ARMS:
            raise ValueError(f"unknown P10S1 arm {arm!r}")
        spec = spec_for(arm, slots)
        addition: Addition
        if arm == "D-OQ":
            addition = DOQDense(spec.hidden, seed, r1_seed)
        elif arm == "H8":
            if hash_seed is None:
                raise ValueError("H8 needs its hash seed (base + 40)")
            addition = H8Memory(slots, seed, hash_seed)
        elif arm == "R2":
            if fact_lut is None:
                raise ValueError("R2 needs the fact lookup table (data.identifier_lut)")
            addition = S1Memory(spec, seed, fact_lut=fact_lut)
        else:
            addition = S1Memory(spec, seed, r1_seed=r1_seed)
        super().__init__(spec, backbone, cast(Any, addition))
        self.arm = arm
        self.slots = slots
        self.r1_seed = r1_seed

    # -- parameters -----------------------------------------------------------------------------------------------------------
    def group_of(self, name: str) -> str:
        leaf = name.rsplit(".", 1)[-1]
        if isinstance(self.addition, DOQDense):
            return "dense"
        return _LEAF_GROUP[leaf]

    def trainable(self) -> list[tuple[str, nn.Parameter]]:
        return [(n, p) for n, p in self.named_parameters() if p.requires_grad]

    def trainable_groups(self) -> dict[str, list[tuple[str, nn.Parameter]]]:
        groups: dict[str, list[tuple[str, nn.Parameter]]] = {g: [] for g in GROUPS}
        for name, p in self.trainable():
            groups[self.group_of(name)].append((name, p))
        return groups

    @property
    def counters(self) -> WorkCounters:
        return cast(WorkCounters, self.addition.counters)

    # -- forward --------------------------------------------------------------------------------------------------------------
    def select(self, h_pre: "Tensor", tokens: "Tensor") -> "Selection | CodeRead | None":  # type: ignore[override]
        if isinstance(self.addition, DOQDense):
            return CodeRead(self.addition.codes(tokens), h_pre.shape[1])
        return cast("Selection", self.addition.select(h_pre, tokens))

    def memory_delta(
        self,
        h_pre: "Tensor",
        selection: "Selection | CodeRead | None",
        *,
        knockout: "Tensor | None" = None,
        values: "Tensor | None" = None,
        disabled: bool = False,
    ) -> "Tensor":
        if disabled:
            return torch.zeros_like(h_pre)
        if isinstance(self.addition, DOQDense):
            if not isinstance(selection, CodeRead):
                raise ValueError("D-OQ needs its code read")
            return self.addition.delta(h_pre, selection)
        if not isinstance(selection, Selection):
            raise ValueError("a memory arm needs its selection")
        return cast("Tensor", self.addition.delta(selection, knockout=knockout, values=values))

    def forward(self, tokens: "Tensor") -> "tuple[Tensor, Selection | CodeRead | None]":  # type: ignore[override]
        h_pre = self.embed_block0(tokens)
        read = self.select(h_pre, tokens)
        return self.finish(h_pre, self.memory_delta(h_pre, read)), read

    def oracle_codes(self, tokens: "Tensor") -> "Tensor":
        """``[B, 8, 16]`` codes of the records at the answer sites (F-OQ, T-OQ and D-OQ's query; the same function for all three)."""
        if isinstance(self.addition, DOQDense):
            return self.addition.codes(tokens)
        if self.arm not in ("F-OQ", "T-OQ"):
            raise ValueError("only F-OQ, T-OQ and D-OQ have an oracle code")
        return cast("Tensor", self.addition._oracle_codes(tokens))


def build_model(
    arm: str,
    slots: int,
    seed: int,
    backbone: "Backbone",
    *,
    fact_lut: "Tensor | None" = None,
    r1_seed: int,
    hash_seed: int | None = None,
    seed_rng: bool = True,
) -> P10S1Model:
    """Model of ``arm`` at ``slots`` with initialization seed ``seed`` on a verified (or synthetic) frozen backbone. ``seed_rng`` seeds Python's and torch's global
    generators with the init seed as P9 does (no parameter initialization depends on them)."""
    if seed_rng:
        import random

        random.seed(seed)
        torch.default_generator.manual_seed(seed)
    return P10S1Model(arm, slots, seed, backbone, fact_lut=fact_lut, r1_seed=r1_seed, hash_seed=hash_seed)


def set_trainable(model: P10S1Model, groups: "list[str] | tuple[str, ...]") -> None:
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise ValueError(f"unknown parameter groups: {sorted(unknown)}")
    for name, p in model.named_parameters():
        if p.requires_grad and not name.startswith("backbone.") and model.group_of(name) not in groups:
            p.requires_grad_(False)


@dataclass(frozen=True)
class ParameterReport:
    arm: str
    slots: int
    frozen_backbone: int
    trainable_backbone: int
    trainable: int
    stored: int
    by_group: dict[str, int]
    dense_hidden: int


def parameter_report(model: P10S1Model) -> ParameterReport:
    bb = [(n, p) for n, p in model.named_parameters() if n.startswith("backbone.")]
    by_group = {g: sum(p.numel() for _, p in items) for g, items in model.trainable_groups().items()}
    addition_params = sum(p.numel() for p in model.addition.parameters())
    return ParameterReport(
        arm=model.arm, slots=model.slots,
        frozen_backbone=sum(p.numel() for _, p in bb if not p.requires_grad),
        trainable_backbone=sum(p.numel() for _, p in bb if p.requires_grad),
        trainable=sum(by_group.values()),
        stored=sum(p.numel() for _, p in bb) + addition_params,
        by_group=by_group,
        dense_hidden=int(model.addition.hidden) if isinstance(model.addition, DOQDense) else 0,
    )  # fmt: skip


def tensor_sha256(t: "Tensor") -> str:
    """sha256 of a tensor's dtype, shape and bytes."""
    import ctypes
    import hashlib

    t = t.detach().contiguous().cpu()
    h = hashlib.sha256(repr((tuple(t.shape), str(t.dtype))).encode())
    h.update(ctypes.string_at(t.data_ptr(), t.numel() * t.element_size()) if t.numel() else b"")
    return h.hexdigest()


def backbone_hashes(backbone: "Backbone") -> dict[str, str]:
    """sha256 of every backbone tensor (parameters and buffers)."""
    return {name: tensor_sha256(t) for name, t in backbone.state_dict().items()}


def no_memory_logits(frozen: "Backbone", tokens: "Tensor") -> "Tensor":
    from studies.p9i.model import no_memory_logits as p9i_no_memory

    return p9i_no_memory(frozen, tokens)


@torch.no_grad()
def g5_check(model: P10S1Model, frozen: "Backbone", tokens: "Tensor", rows: int = 128) -> dict[str, Any]:
    """Backbone identity: every backbone tensor of ``model`` hashes like the frozen backbone's, and with the addition disabled the logits on ``tokens`` ([R, <= 64] corpus
    rows) equal the frozen backbone's bit for bit (in blocks of ``rows``)."""
    was = model.training
    model.eval()
    try:
        before, after = backbone_hashes(frozen), backbone_hashes(model.backbone)
        identical = True
        for start in range(0, tokens.shape[0], rows):
            chunk = tokens[start : start + rows].contiguous()
            h_pre = model.embed_block0(chunk)
            off = model.finish(h_pre, model.memory_delta(h_pre, None, disabled=True))
            identical = identical and bool(torch.equal(off, no_memory_logits(frozen, chunk)))
    finally:
        model.train(was)
    mismatched = sorted(n for n in before if before[n] != after.get(n))
    return {"passed": not mismatched and identical, "hash_mismatches": mismatched, "tensors": len(before), "disabled_logits_identical": identical}


# --- the derangement of facts (section 7.1) -------------------------------------------------------------------------------------------------------
def derangement(answers: "Tensor", seed: int) -> "Tensor":
    """``pi [F]``: a seeded permutation of the facts ``0 .. F-1`` with ``answers[pi[f]] != answers[f]`` for every f (so pi has no fixed point). Start from a seeded random
    permutation and repair every violating position by swapping its image with the image of a seeded position that fixes both; deterministic in ``seed``."""
    n = int(answers.shape[0])
    if n < 2 or int(torch.unique(answers).numel()) < 2:
        raise ValueError("a derangement with different answers needs two facts with different answers")
    gen = torch.Generator().manual_seed(seed)
    pi = torch.randperm(n, generator=gen)
    for _ in range(64):
        bad = (answers[pi] == answers).nonzero().squeeze(1).tolist()
        if not bad:
            return pi
        for i in bad:
            if int(answers[pi[i]]) != int(answers[i]):
                continue
            for _try in range(64 * n):
                j = int(torch.randint(0, n, (1,), generator=gen))
                if answers[pi[j]] != answers[i] and answers[pi[i]] != answers[j]:
                    pi[i], pi[j] = pi[j].clone(), pi[i].clone()
                    break
    raise RuntimeError("could not build a derangement with different answers")


def swapped_tokens(tokens: "Tensor", fact_ids: "Tensor", pi: "Tensor", ident: "Tensor", trained: int) -> "Tensor":
    """``tokens [C, 64]`` with the four free identifier bytes (positions 8r + 1 .. 8r + 4) of every record of a trained fact f replaced by those of ``pi[f]`` (the fifth
    byte, the checksum, is not read by any oracle). ``ident [F, 5]`` is the fact table's identifier symbols. The backbone sees the original tokens; only the oracle's
    read of the fact is replaced (the address swap, section 7.1)."""
    out = tokens.clone()
    ids = fact_ids.clamp_max(trained - 1)
    keep = fact_ids < trained
    partner = pi[ids]  # [C, 8]
    symbols = ident[partner][..., :4] + core.ALPHABET_BASE  # [C, 8, 4]
    for r in range(core.RECORDS_PER_CONTEXT):
        cols = [core.RECORD_BYTES * r + 1 + o for o in range(4)]
        rows = keep[:, r].nonzero().squeeze(1)
        out[rows[:, None], torch.tensor(cols)[None, :]] = symbols[rows, r]
    return out
