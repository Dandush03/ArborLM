# ruff: noqa: E501
"""P9 models (package I2): the scalable memory (sizes, key widths, constant-candidate tree, ladder rungs
R0/R0a/R1/R2/oracle branch), the parameter-matched dense adapter, and the wrapper around the frozen
backbone.

Specification: ADR-0017 section 5.1 (common; at 4,096 slots and key width 16 the new forward must
reproduce the P5 ``Memory`` forward exactly), 5.2 (size scaling), 5.3 (addressing ladder), 5.4 (key
width), 5.6 (dense adapter). STUB: signatures only.

Forward decomposition (so that ``evaluate`` can cache selections and re-run only the upper block for
knock-outs, ADR 6.2 and the budget's "cached evaluation"): ``tokens [B, 63] int64`` ->
``embed_block0`` -> ``h_pre [B, 63, 32]`` (after the first frozen block, where the memory is inserted)
-> ``select`` -> ``Selection`` -> ``memory_delta`` ``[B, 63, 32]`` (gate * wo(sum_k softmax(score_k) *
value_k), zero at positions with no read) -> ``finish`` (``h_pre + delta`` through the second frozen
block, final norm and the tied output) -> logits ``[B, 63, 256]`` float32. ``forward`` composes them.

Read positions: R0 and the oracle branch read at all 63 input positions; R0a, R1 and R2 read at the
answer sites only (``core.ANSWER_SITE_POSITIONS``); the dense adapter acts at all positions.
All tensors are CPU float32 (indices int64).
"""

from collections.abc import Collection
from dataclasses import dataclass
from typing import TYPE_CHECKING

from torch import nn

from .core import Cell

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone


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

    @classmethod
    def from_cell(cls, cell: Cell) -> "AdditionSpec":
        """Spec of ``cell`` (dense: ``core.dense_hidden_width(slots)``; trees: ``core.BRANCHES``)."""
        raise NotImplementedError

    @property
    def read_positions(self) -> tuple[int, ...]:
        """Input positions at which the memory reads (63 positions, or the 8 answer sites)."""
        raise NotImplementedError


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
    """

    positions: "Tensor"
    selected: "Tensor"
    scores: "Tensor"
    candidate_ids: "Tensor | None"
    candidate_scores: "Tensor | None"
    branches: "Tensor | None"
    route_scores: "Tensor | None"

    def weights(self) -> "Tensor":
        """``[B, P, 8]`` softmax of ``scores``."""
        raise NotImplementedError


class ScalableMemory(nn.Module):
    """Top-8, temperature 0.2, cosine keys, learned query projection, output projection and gate
    (ADR 5.1), at any registered size and key width.

    Parameters (names are the contract for ``trainable_groups``): ``keys [N, kw]``, ``values [N, 32]``,
    ``wq [kw, 32]``, ``wo [32, 32]``, ``gate []`` (init -2.0), ``router [branches, kw]`` (a Parameter
    for the learned tree, a buffer for the fixed tree and the oracle branch). Initialization is
    ``N(0, 0.02)`` from generators seeded ``seed + 1000 / 2000 / 3000 / 4000 / 5000`` (keys, values,
    wq, wo, router) exactly as ``arborlm.pilot_model._matrix``, so the 4,096 / 16 shapes are
    identical to P5's. The tree visits the two best branches of ``route_scores`` and scores their
    2 x 256 candidates (ADR 5.2); the oracle branch uses a seeded hash of the identifier instead of
    the router; R1 replaces the query by a fixed unit code per fact (seeded hash of the identifier,
    seed ``core.DATA_SEEDS['r1_codes']``); R2 selects one dedicated slot per fact with weight 1.
    """

    def __init__(
        self,
        spec: AdditionSpec,
        seed: int,
        *,
        fact_lut: "Tensor | None" = None,
        r1_seed: int = 0,
        branch_seed: int = 0,
    ) -> None:
        raise NotImplementedError

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection:
        """Selection at the rung's read positions. ``h_pre [B, 63, 32]``, ``tokens [B, 63] int64`` (the
        identifier bytes at positions 8r+1..8r+5 give the oracle codes, branches and R2 slots)."""
        raise NotImplementedError

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
        raise NotImplementedError


class DenseAdapter(nn.Module):
    """Parameter-matched dense adapter (ADR 5.6, core.OPEN_CHOICES c08): the structure of
    ``arborlm.p4_model.DenseAdapter`` with a variable hidden width ``h = core.dense_hidden_width(slots)``:
    ``h + sigmoid(gate) * w2(gelu_exact(w1(h)))`` with bias-free ``w1 [h, 32]``, ``w2 [32, h]``,
    ``gate []`` init -2.0, ``N(0, 0.02)`` from generators seeded ``seed + 3000`` and ``seed + 4000``
    (``_matrix``). Trainable count ``64 h + 1`` equals the flat key-16 memory of the same size."""

    def __init__(self, hidden: int, seed: int) -> None:
        raise NotImplementedError

    def delta(self, h_pre: "Tensor") -> "Tensor":
        """``[B, 63, 32]`` addition at all positions."""
        raise NotImplementedError


class P9Model(nn.Module):
    """Frozen P4 backbone plus one addition. The backbone is a deep copy with ``requires_grad`` False."""

    spec: AdditionSpec
    backbone: "Backbone"
    addition: ScalableMemory | DenseAdapter

    def embed_block0(self, tokens: "Tensor") -> "Tensor":
        """``[B, 63, 32]``: token + position embeddings through the first block."""
        raise NotImplementedError

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection | None:
        """The memory's reads (None for the dense adapter)."""
        raise NotImplementedError

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
        raise NotImplementedError

    def finish(self, h_pre: "Tensor", delta: "Tensor") -> "Tensor":
        """``[B, 63, 256]`` float32 logits from ``h_pre + delta``."""
        raise NotImplementedError

    def forward(self, tokens: "Tensor") -> tuple["Tensor", Selection | None]:
        """``tokens [B, 63] int64`` (input bytes 0..62) -> logits ``[B, 63, 256]`` and the selection."""
        raise NotImplementedError


def build_model(
    cell: Cell, backbone: "Backbone", *, fact_lut: "Tensor | None" = None, seed_rng: bool = True
) -> P9Model:
    """Model of ``cell`` on a verified frozen backbone (``arborlm.p8_core.load_backbone``). ``fact_lut``
    (``data.identifier_lut``) is required for the R2 rung. Trainable parameters follow the rung
    (ADR 5.3 'Trained' column); the fixed tree's and the oracle branch's router is frozen."""
    raise NotImplementedError


def build_model_from_spec(
    spec: AdditionSpec,
    seed: int,
    backbone: "Backbone",
    *,
    fact_lut: "Tensor | None" = None,
    r1_seed: int = 0,
    branch_seed: int = 0,
) -> P9Model:
    """As ``build_model`` from a bare spec (used by the P5 invariance check at 4,096 / 16)."""
    raise NotImplementedError


PARAMETER_GROUP_NAMES = ("keys", "values", "router", "projections", "dense")


def trainable_groups(model: P9Model) -> dict[str, list[tuple[str, "nn.Parameter"]]]:
    """Trainable parameters by group: keys; values; router; projections (wq, wo, gate); dense."""
    raise NotImplementedError


def set_trainable(model: P9Model, groups: Collection[str]) -> None:
    """Freeze every addition parameter outside ``groups`` (Lane D memory-only: keys and values train,
    projections and gate frozen, ADR 8.5)."""
    raise NotImplementedError


@dataclass(frozen=True)
class ParameterCounts:
    frozen_backbone: int  # 27,392
    trainable: int
    stored: int  # backbone + addition
    initialized_slots: int  # N for memories, 0 for dense
    by_group: dict[str, int]


def parameter_counts(model: P9Model) -> ParameterCounts:
    """Counts reported for every cell (ADR 6.3). For R0/R0a the trainable count equals
    ``core.memory_parameters`` (198,145 flat / 198,401 learned tree at 4,096 slots, key 16)."""
    raise NotImplementedError


def p5_forward_invariance(
    backbone: "Backbone", variant: str, seed: int, tokens: "Tensor"
) -> dict[str, object]:
    """Gate G4: build the 4,096-slot, key-16, R0 model of ``variant`` in {flat, fixed_tree,
    learned_tree} and the P5 ``arborlm.p5_model.Model`` with the same seed; return the maximum absolute
    logit difference (must be exactly 0.0) and whether selections are identical on ``tokens``
    (``[B, T <= 64] int64``)."""
    raise NotImplementedError
