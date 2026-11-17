# ruff: noqa: E501
"""P9 models (package I2): the scalable memory (sizes, key widths, constant-candidate tree, ladder rungs
R0/R0a/R1/R2/oracle branch), the parameter-matched dense adapter, and the wrapper around the frozen
backbone.

Specification: ADR-0017 section 5.1 (common; at 4,096 slots and key width 16 the new forward must
reproduce the P5 ``Memory`` forward exactly), 5.2 (size scaling), 5.3 (addressing ladder), 5.4 (key
width), 5.6 (dense adapter).

Forward decomposition (so that ``evaluate`` can cache selections and re-run only the upper block for
knock-outs, ADR 6.2 and the budget's "cached evaluation"): ``tokens [B, 63] int64`` ->
``embed_block0`` -> ``h_pre [B, 63, 32]`` (after the first frozen block, where the memory is inserted)
-> ``select`` -> ``Selection`` -> ``memory_delta`` ``[B, 63, 32]`` (gate * wo(sum_k softmax(score_k) *
value_k), zero at positions with no read) -> ``finish`` (``h_pre + delta`` through the second frozen
block, final norm and the tied output) -> logits ``[B, 63, 256]`` float32. ``forward`` composes them.

Read positions: R0 and the oracle branch read at all input positions; R0a, R1 and R2 read at the
answer sites only (``core.ANSWER_SITE_POSITIONS``); the dense adapter acts at all positions.
All tensors are CPU float32 (indices int64).

Which parameters exist (so that "stored", "trainable" and "gradient reach" are literal):

=====  ========================================================  ==================================
rung   tensors created                                           trained
=====  ========================================================  ==================================
R0     keys, values, wq, wo, gate (+ router)                     all (router only for learned_tree)
R0a    as R0                                                     as R0
R1     keys, values, wo, gate (+ router)                         all (no ``wq``: the query is a code)
R2     values, wo, gate                                          all (no keys, no ``wq``, no router)
OB     keys, values, wq, wo, gate (router absent)                all (the branch is a hash)
=====  ========================================================  ==================================

The fixed tree's router is a (non-trained) buffer, as in P5.

Choices the ADR leaves open, all flagged in the package report:

* The identifier code of a record (R1 code, R2 slot, OB branch) is computed from the first four
  identifier symbols (the fifth is their checksum), ``sum(symbol_i * 32**i, i < 4)``, exactly the
  convention of ``data.encode_identifiers``; symbol = ``(byte - 0x40) & 31``.
* OB reads at every position; at position p the branch is the hash of the identifier of the record
  that contains p (record p // 8), read non-causally from the input tokens (positions that precede
  the identifier inside the record included). No label leaks (the answer byte is never an input at or
  before the answer site) but the oracle is not causal. The visited set is the single hashed branch
  (256 candidates, no router prior); the top 64 of those 256 feed the soft inclusion.
* R2 returns ``selected [B, P, 1]`` (one slot, weight 1; -1 for an identifier with no slot, which then
  contributes nothing); other rungs return 8.
"""

import copy
import math
from collections.abc import Collection
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import torch
from torch import nn
from torch.nn import functional as F

from arborlm.pilot_model import EPS, _matrix, stable_top

from . import core
from .core import Cell

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

TEMP = core.TEMPERATURE
TOP = core.TOP
SOFT_TOP = core.SOFT_TOP
WIDTH = core.HIDDEN_WIDTH
VOCAB = 256
SCORE_CHUNK_ELEMENTS = 1 << 24  # float32 elements of one score chunk (64 MiB) before rows are split
ALPHABET_BASE = core.ALPHABET[0]
if core.ALPHABET != tuple(range(ALPHABET_BASE, ALPHABET_BASE + core.ALPHABET_SIZE)) or (
    ALPHABET_BASE % 32
):  # the "& 31" symbol arithmetic needs 32 contiguous bytes
    raise ImportError("P9 alphabet must be 32 contiguous bytes starting on a multiple of 32")

TREE_ARCHS = ("fixed_tree", "learned_tree")
ALL_POSITION_RUNGS = ("R0", "OB")
ANSWER_SITE_RUNGS = ("R0a", "R1", "R2")


def read_positions_for(spec: "AdditionSpec", length: int) -> tuple[int, ...]:
    """Positions (below ``length`` input positions) at which ``spec`` reads memory."""
    if spec.arch == "dense" or spec.rung in ALL_POSITION_RUNGS:
        return tuple(range(length))
    return tuple(p for p in core.ANSWER_SITE_POSITIONS if p < length)


@dataclass(frozen=True)
class AdditionSpec:
    """What is added to the frozen backbone. ``arch`` in core.ARCHS, ``rung`` in core.RUNGS.
    ``branches`` is 0 for flat and dense; ``hidden`` is the dense width (0 otherwise)."""

    arch: str
    slots: int
    key_width: int
    rung: str
    branches: int
    hidden: int

    def __post_init__(self) -> None:
        if self.arch not in core.ARCHS or self.rung not in core.RUNGS:
            raise ValueError(f"unregistered addition: {self.arch}/{self.rung}")
        if self.arch == "dense" and (self.hidden <= 0 or self.branches):
            raise ValueError("dense addition needs a hidden width and no branches")
        if self.arch in TREE_ARCHS and (self.branches <= 0 or self.slots % self.branches):
            raise ValueError("tree addition needs branches dividing the slots")
        if self.arch == "flat" and self.branches:
            raise ValueError("flat addition has no branches")
        if self.rung == "OB" and self.arch not in TREE_ARCHS:
            raise ValueError("the oracle branch needs a tree")
        if self.arch != "dense" and self.hidden:
            raise ValueError("only the dense adapter has a hidden width")

    @classmethod
    def from_cell(cls, cell: Cell) -> "AdditionSpec":
        """Spec of ``cell`` (dense: ``core.dense_hidden_width(slots)``; trees: ``core.BRANCHES``)."""
        if cell.arch == "dense":
            return cls(
                "dense",
                cell.slots,
                cell.key_width,
                cell.rung,
                0,
                core.dense_hidden_width(cell.slots),
            )
        branches = core.BRANCHES[cell.slots] if cell.arch in TREE_ARCHS else 0
        return cls(cell.arch, cell.slots, cell.key_width, cell.rung, branches, 0)

    @property
    def read_positions(self) -> tuple[int, ...]:
        """Input positions at which the memory reads (63 positions, or the 8 answer sites)."""
        return read_positions_for(self, core.INPUT_LENGTH)

    @property
    def per_branch(self) -> int:
        return self.slots // self.branches if self.branches else 0


@dataclass
class Selection:
    """The memory reads of one forward call at ``P`` read positions.

    ``positions [P] int64`` input positions; ``selected [B, P, 8] int64`` selected slot ids;
    ``scores [B, P, 8] float32`` pre-softmax scores (temperature applied; carries gradient; the
    read weights are ``scores.softmax(-1)``); ``candidate_ids [B, P, 64] int64`` and
    ``candidate_scores [B, P, 64] float32`` the 64 highest-scoring candidates in descending score
    order (ties by slot id; for the tree, drawn from the 2 x 256 visited candidates; the soft
    inclusion of ADR 7 is computed on them); ``branches [B, P, 2] int64`` and ``route_scores
    [B, P, branches] float32`` for trees. Candidate fields and ``branches`` are None where the rung
    has no key scoring (R2) or the arch has no tree.

    Additions to the contract (reported): ``length`` is the number of input positions of the call
    (63 in the study); for R2 ``selected`` and ``scores`` have a last dimension of 1 (the dedicated
    slot, -1 for an identifier without a slot; score 0, weight 1); for the oracle branch ``branches``
    is ``[B, P, 1]`` (the hashed branch) and ``route_scores`` is None.
    """

    positions: "Tensor"
    selected: "Tensor"
    scores: "Tensor"
    candidate_ids: "Tensor | None"
    candidate_scores: "Tensor | None"
    branches: "Tensor | None"
    route_scores: "Tensor | None"
    length: int = core.INPUT_LENGTH

    def weights(self) -> "Tensor":
        """``[B, P, 8]`` softmax of ``scores``."""
        return self.scores.softmax(-1)


# --- identifier codes, oracle query codes and hashed branches (deterministic, pure Python hashing) -------
_M64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


def _mix64(x: int) -> int:
    """splitmix64 finalizer on Python integers (exact 64-bit wrap-around, platform independent)."""
    x = (x + _GOLDEN) & _M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & _M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & _M64
    return x ^ (x >> 31)


def unit_code(seed: int, ident: int, width: int) -> list[float]:
    """Fixed random unit vector of ``width`` entries for identifier code ``ident`` under ``seed``:
    Gaussian entries (Box-Muller on splitmix64 uniforms in float64) normalized to length 1."""
    state = _mix64(_mix64(seed & _M64) + ident)
    values: list[float] = []
    for j in range((width + 1) // 2):
        a = _mix64((state + (2 * j + 1) * _GOLDEN) & _M64)
        b = _mix64((state + (2 * j + 2) * _GOLDEN) & _M64)
        u1 = ((a >> 11) + 1) / float(1 << 53)  # in (0, 1]
        u2 = (b >> 11) / float(1 << 53)  # in [0, 1)
        radius = math.sqrt(-2.0 * math.log(u1))
        values.append(radius * math.cos(2.0 * math.pi * u2))
        values.append(radius * math.sin(2.0 * math.pi * u2))
    values = values[:width]
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values]


def branch_of(seed: int, ident: int, branches: int) -> int:
    """Branch of the oracle-branch rung: a seeded hash of the identifier code."""
    return _mix64(_mix64((seed ^ 0x5851F42D4C957F2D) & _M64) + ident) % branches


_ID_INDEX = torch.tensor(
    [[8 * r + 1 + i for i in range(4)] for r in range(core.RECORDS_PER_CONTEXT)], dtype=torch.int64
)
_ID_POWERS = torch.tensor([32**i for i in range(4)], dtype=torch.int64)


def identifier_codes(tokens: "Tensor") -> "Tensor":
    """``[B, 8] int64`` code ``sum(symbol_i * 32**i, i < 4)`` of each record's identifier, read from the
    identifier bytes at input positions 8r+1 .. 8r+4 (symbol = ``(byte - 0x40) & 31``); needs T >= 61."""
    if tokens.ndim != 2 or tokens.shape[1] < core.INPUT_LENGTH - 2:
        raise ValueError("identifier codes need tokens [B, T >= 61]")
    symbols = (tokens[:, _ID_INDEX] - ALPHABET_BASE) & 31
    return (symbols * _ID_POWERS).sum(-1)


class ScalableMemory(nn.Module):
    """Top-8, temperature 0.2, cosine keys, learned query projection, output projection and gate
    (ADR 5.1), at any registered size and key width.

    Parameters (names are the contract for ``trainable_groups``): ``keys [N, kw]``, ``values [N, 32]``,
    ``wq [kw, 32]``, ``wo [32, 32]``, ``gate []`` (init -2.0), ``router [branches, kw]`` (a Parameter
    for the learned tree, a buffer for the fixed tree). Initialization is ``N(0, 0.02)`` from
    generators seeded ``seed + 1000 / 2000 / 3000 / 4000 / 5000`` (keys, values, wq, wo, router)
    exactly as ``arborlm.pilot_model._matrix``, so the 4,096 / 16 shapes are identical to P5's. The
    tree visits the two best branches of ``route_scores`` and scores their 2 x 256 candidates (ADR
    5.2); the oracle branch uses a seeded hash of the identifier instead of the router; R1 replaces the
    query by a fixed unit code per fact (seeded hash of the identifier, seed
    ``core.DATA_SEEDS['r1_codes']``); R2 selects one dedicated slot per fact with weight 1.

    ``chunk_elements`` bounds the score matrix of one chunk (queries are processed in row blocks and
    only the top 64 of each row are kept), so memory stays bounded at 65,536 slots; chunked and
    unchunked results are mathematically identical (selections exactly, values and gradients up to
    float accumulation order in the shared key gradient).
    """

    router: "Tensor | None"
    fact_lut: "Tensor | None"

    def __init__(
        self,
        spec: AdditionSpec,
        seed: int,
        *,
        fact_lut: "Tensor | None" = None,
        r1_seed: int | None = None,
        branch_seed: int | None = None,
    ) -> None:
        super().__init__()
        if spec.arch == "dense":
            raise ValueError("ScalableMemory is not the dense adapter")
        self.spec = spec
        self.seed = seed
        self.r1_seed = core.DATA_SEEDS["r1_codes"] if r1_seed is None else r1_seed
        self.branch_seed = core.DATA_SEEDS["branch_hash"] if branch_seed is None else branch_seed
        self.chunk_elements = SCORE_CHUNK_ELEMENTS
        rung, kw, n = spec.rung, spec.key_width, spec.slots
        self._code_cache: dict[int, list[float]] = {}
        if rung != "R2":
            self.keys = nn.Parameter(_matrix(seed + 1000, n, kw))
        self.values = nn.Parameter(_matrix(seed + 2000, n, WIDTH))
        if rung in ("R0", "R0a", "OB"):
            self.wq = nn.Parameter(_matrix(seed + 3000, kw, WIDTH))
        self.wo = nn.Parameter(_matrix(seed + 4000, WIDTH, WIDTH))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32))
        if spec.arch in TREE_ARCHS and rung not in ("OB", "R2"):
            router = _matrix(seed + 5000, spec.branches, kw)
            if spec.arch == "fixed_tree":
                self.register_buffer("router", router)
            else:
                self.router = nn.Parameter(router)
        else:
            self.register_buffer("router", None)
        if rung == "R2":
            if fact_lut is None:
                raise ValueError("R2 needs the fact lookup table (data.identifier_lut)")
            self.register_buffer("fact_lut", fact_lut.to(torch.int64), persistent=False)
        else:
            self.fact_lut = None

    # --- queries -----------------------------------------------------------------------------------
    def _oracle_codes(self, tokens: "Tensor") -> "Tensor":
        """``[B, 8, kw]`` fixed unit codes of the records' identifiers (R1)."""
        codes = identifier_codes(tokens)
        unique, inverse = torch.unique(codes, return_inverse=True)
        rows = []
        for value in unique.tolist():
            if value not in self._code_cache:
                self._code_cache[value] = unit_code(self.r1_seed, value, self.spec.key_width)
            rows.append(self._code_cache[value])
        table = torch.tensor(rows, dtype=torch.float32)
        return table[inverse]

    def _record_of(self, positions: "Tensor") -> "Tensor":
        return cast(
            "Tensor", (positions // core.RECORD_BYTES).clamp_max(core.RECORDS_PER_CONTEXT - 1)
        )

    def _query(self, h_pre: "Tensor", tokens: "Tensor", positions: "Tensor") -> "Tensor":
        """``[B * P, kw]`` unit queries (row index = context * P + position slot)."""
        kw = self.spec.key_width
        if self.spec.rung == "R1":
            codes = self._oracle_codes(tokens)  # [B, 8, kw] at the answer sites
            return codes.reshape(-1, kw)
        x = h_pre if positions.numel() == h_pre.shape[1] else h_pre[:, positions]
        return F.normalize(F.linear(x, self.wq), dim=-1, eps=EPS).reshape(-1, kw)

    # --- selection ---------------------------------------------------------------------------------
    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection:
        """Selection at the rung's read positions. ``h_pre [B, 63, 32]``, ``tokens [B, 63] int64`` (the
        identifier bytes at positions 8r+1..8r+5 give the oracle codes, branches and R2 slots)."""
        b, length, _ = h_pre.shape
        spec = self.spec
        positions = torch.tensor(read_positions_for(spec, length), dtype=torch.int64)
        p = positions.numel()
        if spec.rung in ("R1", "R2", "OB") and length < core.INPUT_LENGTH:
            raise ValueError("oracle rungs need the full 63 input positions")
        if spec.rung == "R2":
            return self._select_r2(tokens, positions, b)
        q = self._query(h_pre, tokens, positions)
        branches: Tensor | None = None
        routes: Tensor | None = None
        if spec.arch == "flat":
            values, ids = self._top_flat(q)
        elif spec.rung == "OB":
            values, ids, branches = self._top_oracle_branch(q, tokens, positions, b)
        else:
            values, ids, branches, routes = self._top_tree(q)
        v = values.reshape(b, p, SOFT_TOP)
        i = ids.reshape(b, p, SOFT_TOP)
        return Selection(
            positions=positions,
            selected=i[..., :TOP],
            scores=v[..., :TOP],
            candidate_ids=i,
            candidate_scores=v,
            branches=None if branches is None else branches.reshape(b, p, -1),
            route_scores=None if routes is None else routes.reshape(b, p, -1),
            length=length,
        )

    def _rows(self, per_row_elements: int) -> int:
        return max(1, self.chunk_elements // max(1, per_row_elements))

    def _top_flat(self, q: "Tensor") -> tuple["Tensor", "Tensor"]:
        """Top 64 of every query's scores against all keys, ties by slot id (``stable_top``), in row
        blocks so that no more than ``chunk_elements`` scores exist at once."""
        keys = cast("Tensor", self.keys)
        normalized = F.normalize(keys, dim=-1, eps=EPS)
        rows = self._rows(self.spec.slots)
        values, ids = [], []
        for start in range(0, q.shape[0], rows):
            scores = (q[start : start + rows] @ normalized.T) / TEMP
            v, i = stable_top(scores, SOFT_TOP)
            values.append(v)
            ids.append(i)
        return torch.cat(values), torch.cat(ids)

    def _top_tree(self, q: "Tensor") -> tuple["Tensor", "Tensor", "Tensor", "Tensor"]:
        """Constant-candidate tree: the same operations as ``arborlm.pilot_model.tree_candidates``
        (two best branches of ``route_scores``, 2 x 256 candidates, log-softmax prior of the visited
        branches), keeping the top 64 candidates instead of the top 8."""
        spec = self.spec
        keys = cast("Tensor", self.keys)
        router = cast("Tensor", self.router)
        per = spec.per_branch
        routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
        _, branch_ids = stable_top(routes, core.VISIT)
        arange = torch.arange(per, device="cpu")
        rows = self._rows(core.VISIT * per * spec.key_width)
        values, ids = [], []
        for start in range(0, q.shape[0], rows):
            end = start + rows
            indices = (branch_ids[start:end, :, None] * per + arange).flatten(1)
            local = F.normalize(keys[indices], dim=-1, eps=EPS)
            scores = torch.bmm(local, q[start:end].unsqueeze(-1)).squeeze(-1) / TEMP
            prior = routes[start:end].log_softmax(-1).gather(-1, branch_ids[start:end])
            scores = scores + prior.repeat_interleave(per, dim=-1)
            v, i = stable_top(scores, SOFT_TOP, indices)
            values.append(v)
            ids.append(i)
        return torch.cat(values), torch.cat(ids), branch_ids, routes

    def _top_oracle_branch(
        self, q: "Tensor", tokens: "Tensor", positions: "Tensor", b: int
    ) -> tuple["Tensor", "Tensor", "Tensor"]:
        """Tree with the branch given by a seeded hash of the identifier of the record containing the
        position; the 256 slots of that branch are scored (no router, no prior), top 64 kept."""
        spec = self.spec
        keys = cast("Tensor", self.keys)
        per = spec.per_branch
        codes = identifier_codes(tokens)  # [B, 8]
        per_record = torch.tensor(
            [
                [branch_of(self.branch_seed, c, spec.branches) for c in row]
                for row in codes.tolist()
            ],
            dtype=torch.int64,
        )
        branch_ids = per_record[:, self._record_of(positions)].reshape(-1, 1)  # [B * P, 1]
        arange = torch.arange(per, device="cpu")
        rows = self._rows(per * spec.key_width)
        values, ids = [], []
        for start in range(0, q.shape[0], rows):
            end = start + rows
            indices = (branch_ids[start:end, :, None] * per + arange).flatten(1)
            local = F.normalize(keys[indices], dim=-1, eps=EPS)
            scores = torch.bmm(local, q[start:end].unsqueeze(-1)).squeeze(-1) / TEMP
            v, i = stable_top(scores, SOFT_TOP, indices)
            values.append(v)
            ids.append(i)
        return torch.cat(values), torch.cat(ids), branch_ids

    def _select_r2(self, tokens: "Tensor", positions: "Tensor", b: int) -> Selection:
        lut = cast("Tensor", self.fact_lut)
        slots = lut[identifier_codes(tokens)]  # [B, 8], -1 where the identifier has no slot
        selected = slots.reshape(b, -1, 1)
        return Selection(
            positions=positions,
            selected=selected,
            scores=torch.zeros(selected.shape, dtype=torch.float32),
            candidate_ids=None,
            candidate_scores=None,
            branches=None,
            route_scores=None,
            length=tokens.shape[1],
        )

    # --- contribution ------------------------------------------------------------------------------
    def delta(
        self,
        selection: Selection,
        *,
        knockout: "Tensor | None" = None,
        values: "Tensor | None" = None,
    ) -> "Tensor":
        """``[B, 63, 32]`` memory contribution. ``knockout [B, P, 8] bool`` removes those slots'
        values from the weighted sum with selections and weights unchanged (ADR 6.2); ``values
        [N, 32]`` replaces the value table (value permutation)."""
        table = self.values if values is None else values
        b, p, k = selection.selected.shape
        chosen = selection.selected.reshape(-1, k)
        weights = selection.scores.reshape(-1, k).softmax(-1)
        if self.spec.rung == "R2":
            weights = weights * (chosen >= 0).to(weights.dtype)
            chosen = chosen.clamp_min(0)
        if knockout is not None:
            if knockout.shape != selection.selected.shape:
                raise ValueError("knockout must match the selection shape")
            weights = weights.masked_fill(knockout.reshape(-1, k), 0.0)
        combined = (weights[..., None] * table[chosen]).sum(dim=-2)
        out = self.gate.sigmoid() * F.linear(combined.reshape(b, p, -1), self.wo)
        return _to_positions(out, selection)


def _to_positions(x: "Tensor", selection: Selection) -> "Tensor":
    """Scatter ``[B, P, 32]`` read contributions into ``[B, length, 32]`` (zero where nothing is read)."""
    positions = selection.positions
    if positions.numel() == selection.length:
        return x
    full = x.new_zeros((x.shape[0], selection.length, x.shape[-1]))
    return full.index_copy(1, positions, x)


class DenseAdapter(nn.Module):
    """Parameter-matched dense adapter (ADR 5.6, core.OPEN_CHOICES c08): the structure of
    ``arborlm.p4_model.DenseAdapter`` with a variable hidden width ``h = core.dense_hidden_width(slots)``:
    ``h + sigmoid(gate) * w2(gelu_exact(w1(h)))`` with bias-free ``w1 [h, 32]``, ``w2 [32, h]``,
    ``gate []`` init -2.0, ``N(0, 0.02)`` from generators seeded ``seed + 3000`` and ``seed + 4000``
    (``_matrix``). Trainable count ``64 h + 1`` equals the flat key-16 memory of the same size."""

    def __init__(self, hidden: int, seed: int) -> None:
        super().__init__()
        self.w1 = nn.Parameter(_matrix(seed + 3000, hidden, WIDTH))
        self.w2 = nn.Parameter(_matrix(seed + 4000, WIDTH, hidden))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32))

    def delta(self, h_pre: "Tensor") -> "Tensor":
        """``[B, 63, 32]`` addition at all positions."""
        hidden = F.gelu(F.linear(h_pre, self.w1), approximate="none")
        return self.gate.sigmoid() * F.linear(hidden, self.w2)


class P9Model(nn.Module):
    """Frozen P4 backbone plus one addition. The backbone is a deep copy with ``requires_grad`` False."""

    spec: AdditionSpec
    backbone: "Backbone"
    addition: ScalableMemory | DenseAdapter

    def __init__(
        self, spec: AdditionSpec, backbone: "Backbone", addition: ScalableMemory | DenseAdapter
    ) -> None:
        super().__init__()
        self.spec = spec
        self.backbone = copy.deepcopy(backbone)
        self.backbone.requires_grad_(False)
        self.addition = addition

    @staticmethod
    def _check_tokens(tokens: "Tensor") -> None:
        if (
            tokens.ndim != 2
            or tokens.shape[0] == 0
            or not 1 <= tokens.shape[1] <= core.CONTEXT_BYTES
            or tokens.dtype != torch.int64
            or tokens.device.type != "cpu"
        ):
            raise ValueError("expected nonempty CPU int64 [B,T] with 1 <= T <= 64")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("expected byte token IDs")

    def embed_block0(self, tokens: "Tensor") -> "Tensor":
        """``[B, 63, 32]``: token + position embeddings through the first block."""
        self._check_tokens(tokens)
        t = tokens.shape[1]
        bb = self.backbone
        h = bb.token(tokens) + bb.position(torch.arange(t, device="cpu"))
        return cast("Tensor", bb.blocks[0](h, bb.mask[:t, :t]))

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection | None:
        """The memory's reads (None for the dense adapter)."""
        if isinstance(self.addition, DenseAdapter):
            return None
        return self.addition.select(h_pre, tokens)

    def memory_delta(
        self,
        h_pre: "Tensor",
        selection: Selection | None,
        *,
        knockout: "Tensor | None" = None,
        values: "Tensor | None" = None,
        disabled: bool = False,
    ) -> "Tensor":
        """``[B, 63, 32]`` addition; zeros when ``disabled`` (memory disabled, ADR 5.6)."""
        if disabled:
            return torch.zeros_like(h_pre)
        if isinstance(self.addition, DenseAdapter):
            return self.addition.delta(h_pre)
        if selection is None:
            raise ValueError("a memory addition needs its selection")
        return self.addition.delta(selection, knockout=knockout, values=values)

    def finish(self, h_pre: "Tensor", delta: "Tensor") -> "Tensor":
        """``[B, 63, 256]`` float32 logits from ``h_pre + delta``."""
        bb = self.backbone
        t = h_pre.shape[1]
        h = bb.blocks[1](h_pre + delta, bb.mask[:t, :t])
        return F.linear(bb.final_norm(h), bb.token.weight)

    def forward(self, tokens: "Tensor") -> tuple["Tensor", Selection | None]:
        """``tokens [B, 63] int64`` (input bytes 0..62) -> logits ``[B, 63, 256]`` and the selection."""
        h_pre = self.embed_block0(tokens)
        selection = self.select(h_pre, tokens)
        return self.finish(h_pre, self.memory_delta(h_pre, selection)), selection


def build_model(
    cell: Cell,
    backbone: "Backbone",
    *,
    fact_lut: "Tensor | None" = None,
    seed_rng: bool = True,
    init_seed: int | None = None,
    r1_seed: int | None = None,
    branch_seed: int | None = None,
) -> P9Model:
    """Model of ``cell`` on a verified frozen backbone (``arborlm.p8_core.load_backbone``). ``fact_lut``
    (``data.identifier_lut``) is required for the R2 rung. Trainable parameters follow the rung
    (ADR 5.3 'Trained' column); the fixed tree's router is frozen and the oracle branch has none.

    Additions to the stub: ``init_seed`` (default ``cell.seed``) and ``r1_seed`` / ``branch_seed``
    (default the registered ``core.DATA_SEEDS`` values) let rehearsal and calibration use the
    rehearsal namespace. ``seed_rng`` seeds Python's and torch's global generators with the init seed
    as P8 did (no parameter initialization depends on them)."""
    seed = cell.seed if init_seed is None else init_seed
    if seed_rng:
        import random

        random.seed(seed)
        torch.default_generator.manual_seed(seed)
    return build_model_from_spec(
        AdditionSpec.from_cell(cell),
        seed,
        backbone,
        fact_lut=fact_lut,
        r1_seed=r1_seed,
        branch_seed=branch_seed,
    )


def build_model_from_spec(
    spec: AdditionSpec,
    seed: int,
    backbone: "Backbone",
    *,
    fact_lut: "Tensor | None" = None,
    r1_seed: int | None = None,
    branch_seed: int | None = None,
) -> P9Model:
    """As ``build_model`` from a bare spec (used by the P5 invariance check at 4,096 / 16)."""
    addition: ScalableMemory | DenseAdapter
    if spec.arch == "dense":
        addition = DenseAdapter(spec.hidden, seed)
    else:
        addition = ScalableMemory(
            spec, seed, fact_lut=fact_lut, r1_seed=r1_seed, branch_seed=branch_seed
        )
    return P9Model(spec, backbone, addition)


PARAMETER_GROUP_NAMES = ("keys", "values", "router", "projections", "dense")
_GROUP_OF = {
    "keys": "keys",
    "values": "values",
    "router": "router",
    "wq": "projections",
    "wo": "projections",
    "gate": "projections",
}


def _group_for(model: P9Model, name: str) -> str:
    leaf = name.rsplit(".", 1)[-1]
    if isinstance(model.addition, DenseAdapter):
        return "dense"
    return _GROUP_OF[leaf]


def trainable_groups(model: P9Model) -> dict[str, list[tuple[str, "nn.Parameter"]]]:
    """Trainable parameters by group: keys; values; router; projections (wq, wo, gate); dense."""
    groups: dict[str, list[tuple[str, nn.Parameter]]] = {g: [] for g in PARAMETER_GROUP_NAMES}
    for name, p in model.addition.named_parameters():
        if p.requires_grad:
            groups[_group_for(model, name)].append((f"addition.{name}", p))
    return groups


def set_trainable(model: P9Model, groups: Collection[str]) -> None:
    """Freeze every addition parameter outside ``groups`` (Lane D memory-only: keys and values train,
    projections and gate frozen, ADR 8.5). Never unfreezes a parameter the rung leaves frozen."""
    unknown = set(groups) - set(PARAMETER_GROUP_NAMES)
    if unknown:
        raise ValueError(f"unknown parameter groups: {sorted(unknown)}")
    for name, p in model.addition.named_parameters():
        if _group_for(model, name) not in groups:
            p.requires_grad_(False)


@dataclass(frozen=True)
class ParameterCounts:
    frozen_backbone: int  # 27,392
    trainable: int
    stored: int  # backbone + addition
    initialized_slots: int  # N for memories, 0 for dense
    by_group: dict[str, int]


def parameter_counts(model: P9Model) -> ParameterCounts:
    """Counts reported for every cell (ADR 6.3). For R0/R0a the trainable count equals
    ``core.memory_parameters`` (198,145 flat / 198,401 learned tree at 4,096 slots, key 16). ``stored``
    counts the backbone and every persistent addition tensor (parameters and the fixed tree's router
    buffer)."""
    backbone = sum(p.numel() for p in model.backbone.parameters())
    by_group = {g: sum(p.numel() for _, p in items) for g, items in trainable_groups(model).items()}
    addition = sum(p.numel() for p in model.addition.parameters()) + sum(
        t.numel() for n, t in model.addition.named_buffers() if n in model.addition.state_dict()
    )
    return ParameterCounts(
        frozen_backbone=backbone,
        trainable=sum(by_group.values()),
        stored=backbone + addition,
        initialized_slots=0 if isinstance(model.addition, DenseAdapter) else model.spec.slots,
        by_group=by_group,
    )


def p5_forward_invariance(
    backbone: "Backbone", variant: str, seed: int, tokens: "Tensor"
) -> dict[str, object]:
    """Gate G4: build the 4,096-slot, key-16, R0 model of ``variant`` in {flat, fixed_tree,
    learned_tree} and the P5 ``arborlm.p5_model.Model`` with the same seed; return the maximum absolute
    logit difference (must be exactly 0.0) and whether selections are identical on ``tokens``
    (``[B, T <= 64] int64``)."""
    from arborlm.p5_config import MEMORIES
    from arborlm.p5_model import Model

    if variant not in MEMORIES:
        raise ValueError(f"unknown P5 memory variant {variant!r}")
    branches = 0 if variant == "flat" else core.BRANCHES[4096]
    spec = AdditionSpec(variant, 4096, core.KEY_WIDTH, "R0", branches, 0)
    mine = build_model_from_spec(spec, seed, backbone)
    # P5's Model reads only cell.variant and cell.seed (P8 passes its own cell class the same way).
    reference = Model(cast(Any, SimpleNamespace(variant=variant, seed=seed)), backbone)
    mine.eval()
    reference.eval()
    same_parameters = all(
        torch.equal(p, dict(reference.named_parameters())[n])
        for n, p in mine.named_parameters()
        if n.startswith("addition.")
    ) and all(
        torch.equal(t, dict(reference.named_buffers())[n])
        for n, t in mine.named_buffers()
        if n.startswith("addition.") and n in mine.state_dict()
    )
    with torch.no_grad():
        logits, selection = mine(tokens)
        ref_logits, lookup = reference(tokens)
    if selection is None or lookup is None:
        raise ValueError("expected a memory selection from both models")
    flat_selected = selection.selected.reshape(-1, TOP)
    routing = True
    if variant != "flat":
        routing = bool(
            lookup.branch_ids is not None
            and selection.branches is not None
            and torch.equal(lookup.branch_ids, selection.branches.reshape(-1, core.VISIT))
            and lookup.route_scores is not None
            and selection.route_scores is not None
            and torch.equal(
                lookup.route_scores, selection.route_scores.reshape(flat_selected.shape[0], -1)
            )
        )
    return {
        "variant": variant,
        "same_parameters": same_parameters,
        "queries": int(flat_selected.shape[0]),
        "max_abs_logit_difference": float((logits - ref_logits).abs().max()),
        "logits_identical": bool(torch.equal(logits, ref_logits)),
        "selection_identical": bool(torch.equal(lookup.selected, flat_selected)),
        "routing_identical": routing,
        "logit_shape": list(logits.shape),
    }
