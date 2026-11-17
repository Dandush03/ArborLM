# ruff: noqa: E501
"""P9I models (ADR-0017 Part I, section I.3): arms N, W7, E7, A4, A4E, R1, R2 on the flat memory of
section 5, read at the answer sites only; the dense controls D plain and D7 (answer sites only); and
block BB (BB, BB-D, BB-0), in which the block-0 attention of the backbone (qkv and output projection,
4,224 parameters) is the only trainable backbone part.

One model class, ``P9IModel``, subclasses ``studies.p9.model.P9Model`` so that P9's cached evaluation
(``build_cache``, ``logits_with``, ``minimal_supports``) runs on it unchanged. It overrides ``select``
and ``memory_delta`` only. The memory is P9's ``ScalableMemory`` (flat, top 8, temperature 0.2, cosine
keys, key width 16, ``wo``, gate), subclassed once to change the query. No P9 code is edited or patched.

Arms (all read at input position ``8r + 6`` of record r; "window" is positions t-6 .. t):

====  =========================================================  =====================================
arm   query at the answer site t                                 extra parameters over arm N
====  =========================================================  =====================================
N     ``W h_t`` (``W`` 16 x 32); identical to P9's R0a           0
W7    ``W [h_{t-6}; ...; h_t]`` (``W`` 16 x 224)                 3,072
E7    as W7 on ``e`` = token + position embedding (no block)     3,072
A4    4 heads x 8, bias-free q, k, v (32 x 32 each), query from  3,072
      ``h_t``, keys and values over the causal prefix, scores
      scaled by 1/sqrt(8), no layer norm, no output projection;
      its 32-wide output goes through ``W`` (16 x 32)
A4E   A4 on ``e``                                                3,072
R1    fixed random unit code per fact (P9's rung)                - (no query projection)
R2    one dedicated slot per fact (P9's rung)                    - (no keys, no query projection)
D     P4/P5 adapter on ``h_t`` at answer sites, hidden width     -
      matched to arm N
D7    the adapter on ``[h_{t-6}; ...; h_t]``, hidden width       -
      matched to arm W7 within 0.1% (786 / 3,090 / 12,306)
BB    arm N with block-0 attention trainable                     4,224 backbone parameters
BB-D  D plain with block-0 attention trainable                   4,224 backbone parameters
BB-0  no addition, block-0 attention trainable                   4,224 backbone parameters
====  =========================================================  =====================================

Initialization (``N(0, 0.02)`` from generators ``seed + k``, as P9): keys +1000, values +2000, ``wq``
+3000, ``wo`` +4000 (arm N, R1 and R2 therefore equal P9's R0a / R1 / R2 at the same seed); W7 and E7
draw ``wq`` as a 16 x 224 matrix with the same generator seed (+3000); A4 and A4E draw q, k, v from
+6000 / +7000 / +8000; the dense adapters draw ``w1`` from +3000 and ``w2`` from +4000. Choices the ADR
leaves open (reported): the ``wq`` initialization of W7 / E7 as a fresh 16 x 224 draw rather than N's
16 x 32 draw embedded in it; the A4 attention scale is applied to the unnormalised scores like the
backbone's.

The training groups used by the optimizers and the diagnostics are ``keys``, ``values``,
``projections`` (``wq``, ``wo``, memory ``gate``), ``interface`` (A4 / A4E q, k, v), ``dense`` (the
adapters) and ``backbone_attention`` (BB arms).
"""

import math
from collections.abc import Collection
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import torch
from torch import nn
from torch.nn import functional as F

from arborlm.pilot_model import EPS, _matrix
from studies.p9.model import AdditionSpec, P9Model, ScalableMemory, Selection

from . import core

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

WIDTH = core.HIDDEN_WIDTH
SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
WINDOW_OFFSETS = torch.arange(-(core.WINDOW - 1), 1, dtype=torch.int64)  # -6 .. 0
IDENTIFIER_OFFSETS = (1, 2, 3, 4, 5)  # positions 8r + 1 .. 8r + 5 of a record
ATTENTION_PARAMETER_NAMES = ("qkv.weight", "qkv.bias", "attn_out.weight", "attn_out.bias")
GROUPS = ("keys", "values", "projections", "interface", "dense", "backbone_attention")
_LEAF_GROUP = {
    "keys": "keys",
    "values": "values",
    "wq": "projections",
    "wo": "projections",
    "gate": "projections",
    "attn_q": "interface",
    "attn_k": "interface",
    "attn_v": "interface",
}


# --- the interface memory ---------------------------------------------------------------------------------
class IMemory(ScalableMemory):
    """P9's flat memory of the R0a rung with the query of ``arm`` in {N, W7, E7, A4, A4E}. ``select(x,
    tokens)`` takes ``x`` = the insertion-point hidden state (N, W7, A4) or the embedding (E7, A4E); the
    caller (``P9IModel``) chooses. Arm N does not override anything: it is P9's R0a memory."""

    def __init__(self, arm: str, slots: int, seed: int) -> None:
        if arm not in core.INTERFACE_ARMS:
            raise ValueError(f"not an interface arm: {arm!r}")
        super().__init__(AdditionSpec("flat", slots, core.KEY_WIDTH, "R0a", 0, 0), seed)
        self.arm = arm
        if arm in ("W7", "E7"):
            self.wq = nn.Parameter(_matrix(seed + 3000, core.KEY_WIDTH, WIDTH * core.WINDOW))
        if arm in ("A4", "A4E"):
            self.attn_q = nn.Parameter(_matrix(seed + 6000, WIDTH, WIDTH))
            self.attn_k = nn.Parameter(_matrix(seed + 7000, WIDTH, WIDTH))
            self.attn_v = nn.Parameter(_matrix(seed + 8000, WIDTH, WIDTH))

    @staticmethod
    def window(x: "Tensor", positions: "Tensor") -> "Tensor":
        """``[B, P, 7 * 32]`` features ``[x_{t-6}; ...; x_t]`` (oldest first) at ``positions``."""
        index = positions[:, None] + WINDOW_OFFSETS[None, :]
        if int(index.min()) < 0:
            raise ValueError("a window reaches before position 0")
        gathered = x[:, index]  # [B, P, 7, 32]
        return gathered.reshape(x.shape[0], positions.numel(), -1)

    def attend(self, x: "Tensor", positions: "Tensor") -> tuple["Tensor", "Tensor"]:
        """One causal attention layer, 4 heads x 8, bias-free, no layer norm, no output projection:
        queries at ``positions`` from ``x_t``, keys and values over ``x_0 .. x_t``. Returns the
        ``[B, P, 32]`` output and the ``[B, 4, P, T]`` attention weights."""
        b, t, _ = x.shape
        p = positions.numel()
        heads, width = core.HEADS, core.HEAD_WIDTH
        q = F.linear(x[:, positions], self.attn_q).reshape(b, p, heads, width).permute(0, 2, 1, 3)
        k = F.linear(x, self.attn_k).reshape(b, t, heads, width).permute(0, 2, 1, 3)
        v = F.linear(x, self.attn_v).reshape(b, t, heads, width).permute(0, 2, 1, 3)
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(width)
        future = torch.arange(t)[None, :] > positions[:, None]  # [P, T]
        mask = torch.zeros(p, t).masked_fill(future, -torch.inf)
        weights = (scores + mask).softmax(dim=-1)
        out = (weights @ v).permute(0, 2, 1, 3).reshape(b, p, heads * width)
        return out, weights

    def _features(self, x: "Tensor", positions: "Tensor") -> "Tensor":
        if self.arm in ("W7", "E7"):
            return self.window(x, positions)
        if self.arm in ("A4", "A4E"):
            return self.attend(x, positions)[0]
        return x[:, positions]

    def _query(self, h_pre: "Tensor", tokens: "Tensor", positions: "Tensor") -> "Tensor":
        if self.arm == "N":
            return super()._query(h_pre, tokens, positions)
        features = self._features(h_pre, positions)
        return F.normalize(F.linear(features, self.wq), dim=-1, eps=EPS).reshape(-1, self.spec.key_width)


# --- dense controls --------------------------------------------------------------------------------------------
class IDense(nn.Module):
    """The P4/P5 dense adapter at answer sites only: ``sigmoid(gate) * w2(gelu_exact(w1(f)))`` where
    ``f`` is ``h_t`` (``window`` 1: D plain, BB-D) or ``[h_{t-6}; ...; h_t]`` (``window`` 7: D7). Bias-free
    ``w1 [hidden, 32 * window]`` and ``w2 [32, hidden]``, gate init -2.0. The output is zero at every
    other position. For ``window`` 1 the parameters equal P9's ``DenseAdapter`` at the same seed."""

    def __init__(self, hidden: int, seed: int, window: int) -> None:
        super().__init__()
        self.window = window
        self.w1 = nn.Parameter(_matrix(seed + 3000, hidden, WIDTH * window))
        self.w2 = nn.Parameter(_matrix(seed + 4000, WIDTH, hidden))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32))

    def delta(self, h_pre: "Tensor") -> "Tensor":
        """``[B, 63, 32]``: the adapter's output at the answer sites, zero elsewhere."""
        positions = SITES[SITES < h_pre.shape[1]]
        features = IMemory.window(h_pre, positions) if self.window > 1 else h_pre[:, positions]
        out = self.gate.sigmoid() * F.linear(F.gelu(F.linear(features, self.w1), approximate="none"), self.w2)
        full = h_pre.new_zeros(h_pre.shape)
        return full.index_copy(1, positions, out)


class NoAddition(nn.Module):
    """BB-0: nothing is added (the trained attention is the only trainable part)."""

    def delta(self, h_pre: "Tensor") -> "Tensor":
        return torch.zeros_like(h_pre)


# --- the model -----------------------------------------------------------------------------------------------------
Addition = IMemory | ScalableMemory | IDense | NoAddition


def _spec_for(arm: str, slots: int) -> AdditionSpec:
    if arm in ("D", "BB-D"):
        return AdditionSpec("dense", slots, core.KEY_WIDTH, "R0", 0, core.dense_plain_hidden_width(slots))
    if arm == "D7":
        return AdditionSpec("dense", slots, core.KEY_WIDTH, "R0", 0, core.d7_hidden_width(slots))
    if arm == "BB-0":  # no addition; the dense arch marks "no key table"; hidden is a placeholder
        return AdditionSpec("dense", slots, core.KEY_WIDTH, "R0", 0, 1)
    rung = {"R1": "R1", "R2": "R2"}.get(arm, "R0a")
    return AdditionSpec("flat", slots, core.KEY_WIDTH, rung, 0, 0)


class P9IModel(P9Model):
    """Frozen P4 backbone (a deep copy) plus the arm's addition. For the BB arms the block-0 attention of
    the copy is trainable; nothing else of the backbone ever is."""

    addition: Any  # IMemory | ScalableMemory | IDense | NoAddition

    def __init__(
        self,
        arm: str,
        slots: int,
        seed: int,
        backbone: "Backbone",
        *,
        fact_lut: "Tensor | None" = None,
        r1_seed: int | None = None,
    ) -> None:
        if arm not in core.ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        spec = _spec_for(arm, slots)
        addition: Addition
        if arm in core.INTERFACE_ARMS:
            addition = IMemory(arm, slots, seed)
        elif arm == "BB":
            addition = IMemory("N", slots, seed)
        elif arm in ("R1", "R2"):
            if arm == "R2" and fact_lut is None:
                raise ValueError("R2 needs the fact lookup table (data.identifier_lut)")
            addition = ScalableMemory(spec, seed, fact_lut=fact_lut, r1_seed=r1_seed)
        elif arm in ("D", "BB-D"):
            addition = IDense(spec.hidden, seed, 1)
        elif arm == "D7":
            addition = IDense(spec.hidden, seed, core.WINDOW)
        else:
            addition = NoAddition()
        super().__init__(spec, backbone, cast(Any, addition))
        self.arm = arm
        self.slots = slots
        if arm in core.BB_ARMS:
            self._train_block0_attention()

    # -- parameters ------------------------------------------------------------------------------------------
    def _train_block0_attention(self) -> None:
        block = self.backbone.blocks[0]
        for name in ATTENTION_PARAMETER_NAMES:
            module_name, leaf = name.split(".")
            getattr(block, module_name).get_parameter(leaf).requires_grad_(True)

    def group_of(self, name: str) -> str:
        """Group of a parameter name of this model (``named_parameters`` naming)."""
        if name.startswith("backbone."):
            return "backbone_attention"
        leaf = name.rsplit(".", 1)[-1]
        if isinstance(self.addition, IDense):
            return "dense"
        return _LEAF_GROUP[leaf]

    def trainable(self) -> list[tuple[str, nn.Parameter]]:
        return [(n, p) for n, p in self.named_parameters() if p.requires_grad]

    def trainable_groups(self) -> dict[str, list[tuple[str, nn.Parameter]]]:
        groups: dict[str, list[tuple[str, nn.Parameter]]] = {g: [] for g in GROUPS}
        for name, p in self.trainable():
            groups[self.group_of(name)].append((name, p))
        return groups

    # -- forward ---------------------------------------------------------------------------------------------
    def embedding(self, tokens: "Tensor") -> "Tensor":
        """``[B, T, 32]`` token plus position embedding (``e``; no block)."""
        self._check_tokens(tokens)
        bb = self.backbone
        return cast("Tensor", bb.token(tokens) + bb.position(torch.arange(tokens.shape[1], device="cpu")))

    def reads_embedding(self) -> bool:
        return self.arm in ("E7", "A4E")

    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection | None:
        """The answer-site read's selection; None for the dense arms and BB-0."""
        if not isinstance(self.addition, ScalableMemory):
            return None
        x = self.embedding(tokens) if self.reads_embedding() else h_pre
        return self.addition.select(x, tokens)

    def memory_delta(
        self,
        h_pre: "Tensor",
        selection: Selection | None,
        *,
        knockout: "Tensor | None" = None,
        values: "Tensor | None" = None,
        disabled: bool = False,
    ) -> "Tensor":
        if disabled:
            return torch.zeros_like(h_pre)
        if isinstance(self.addition, IDense | NoAddition):
            return self.addition.delta(h_pre)
        if selection is None:
            raise ValueError("a memory arm needs its selection")
        return cast("Tensor", self.addition.delta(selection, knockout=knockout, values=values))

    # -- diagnostics -----------------------------------------------------------------------------------------
    def answer_queries(self, h_pre: "Tensor", tokens: "Tensor") -> "Tensor | None":
        """``[B, 8, 16]`` unit queries at the answer sites (R1: the fixed codes); None for R2, dense arms
        and BB-0."""
        mem = self.addition
        if not isinstance(mem, ScalableMemory) or self.spec.rung == "R2":
            return None
        x = self.embedding(tokens) if self.reads_embedding() else h_pre
        q = mem._query(x, tokens, SITES)
        return q.reshape(tokens.shape[0], SITES.numel(), -1)

    def answer_attention(self, h_pre: "Tensor", tokens: "Tensor") -> "Tensor | None":
        """``[B, 4, 8, T]`` attention weights of the answer sites for A4, A4E (the interface layer) and
        the BB arms (block 0 of the backbone, re-computed from its attention parameters); else None."""
        mem = self.addition
        if isinstance(mem, IMemory) and mem.arm in ("A4", "A4E"):
            x = self.embedding(tokens) if self.reads_embedding() else h_pre
            return mem.attend(x, SITES)[1]
        if self.arm in core.BB_ARMS:
            return block0_attention(self.backbone, tokens)[:, :, SITES]
        return None


def block0_attention(backbone: "Backbone", tokens: "Tensor") -> "Tensor":
    """``[B, 4, T, T]`` attention weights of block 0 (the operations of ``arborlm.model.Block``)."""
    t = tokens.shape[1]
    h = backbone.token(tokens) + backbone.position(torch.arange(t, device="cpu"))
    block = cast(Any, backbone.blocks[0])
    b = h.shape[0]
    q, k, _ = block.qkv(block.attn_norm(h)).reshape(b, t, 3, 4, 8).permute(2, 0, 3, 1, 4).unbind(0)
    scores = (q @ k.transpose(-2, -1)) / math.sqrt(8)
    return cast("Tensor", (scores + backbone.mask[:t, :t]).softmax(dim=-1))


def identifier_attention_mass(weights: "Tensor") -> "Tensor":
    """``[B, 4, 8]`` attention mass of each head at each answer site on the five identifier positions
    of its own record (positions 8r+1 .. 8r+5), from ``[B, 4, 8, T]`` weights."""
    rows = []
    for r in range(core.RECORDS_PER_CONTEXT):
        cols = [core.RECORD_BYTES * r + o for o in IDENTIFIER_OFFSETS]
        rows.append(weights[:, :, r, cols].sum(-1))
    return torch.stack(rows, dim=-1)


# --- construction and counts ---------------------------------------------------------------------------------------
def build_model(
    arm: str,
    slots: int,
    seed: int,
    backbone: "Backbone",
    *,
    fact_lut: "Tensor | None" = None,
    r1_seed: int | None = None,
    seed_rng: bool = True,
) -> P9IModel:
    """Model of ``arm`` at ``slots`` with initialization seed ``seed`` on a verified (or synthetic)
    frozen backbone. ``seed_rng`` seeds Python's and torch's global generators with the init seed as P9
    does (no parameter initialization depends on them)."""
    if seed_rng:
        import random

        random.seed(seed)
        torch.default_generator.manual_seed(seed)
    return P9IModel(arm, slots, seed, backbone, fact_lut=fact_lut, r1_seed=r1_seed)


def set_trainable(model: P9IModel, groups: Collection[str]) -> None:
    """Freeze every parameter outside ``groups`` (never unfreezes one)."""
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise ValueError(f"unknown parameter groups: {sorted(unknown)}")
    for name, p in model.named_parameters():
        if p.requires_grad and model.group_of(name) not in groups:
            p.requires_grad_(False)


@dataclass(frozen=True)
class ParameterReport:
    """Measured counts of one model. ``frozen_backbone`` counts backbone parameters with no gradient,
    ``trainable_backbone`` the block-0 attention parameters of the BB arms (4,224)."""

    arm: str
    slots: int
    frozen_backbone: int
    trainable_backbone: int
    trainable: int
    stored: int
    by_group: dict[str, int]
    interface_extra: int  # trainable addition parameters beyond arm N's (W7/E7/A4/A4E), else 0
    dense_hidden: int  # hidden width of the dense adapter, else 0


def parameter_report(model: P9IModel) -> ParameterReport:
    bb = [(n, p) for n, p in model.named_parameters() if n.startswith("backbone.")]
    trainable_bb = sum(p.numel() for _, p in bb if p.requires_grad)
    frozen_bb = sum(p.numel() for _, p in bb if not p.requires_grad)
    by_group = {g: sum(p.numel() for _, p in items) for g, items in model.trainable_groups().items()}
    addition_params = sum(p.numel() for p in model.addition.parameters())
    extra = 0
    if model.arm in ("W7", "E7"):
        extra = model.addition.wq.numel() - core.KEY_WIDTH * WIDTH
    elif model.arm in ("A4", "A4E"):
        extra = by_group["interface"]
    hidden = model.addition.w1.shape[0] if isinstance(model.addition, IDense) else 0
    return ParameterReport(
        arm=model.arm,
        slots=model.slots,
        frozen_backbone=frozen_bb,
        trainable_backbone=trainable_bb,
        trainable=sum(by_group.values()),
        stored=frozen_bb + trainable_bb + addition_params,
        by_group=by_group,
        interface_extra=extra,
        dense_hidden=hidden,
    )


def no_memory_logits(backbone: "Backbone", tokens: "Tensor") -> "Tensor":
    """``[B, T, 256]`` logits of the frozen backbone with nothing added (the no-memory baseline)."""
    from studies.p9 import controls

    return controls.logits_from_hidden(backbone, controls.insertion_hidden(backbone, tokens))


# --- gate G4: identities (section I.9) -------------------------------------------------------------------------------
def n_against_p9_r0a(backbone: "Backbone", slots: int, seed: int, tokens: "Tensor") -> dict[str, Any]:
    """Arm N against ADR-0017's R0a model with equal parameters and inputs (``tokens [B, T <= 64]``).
    P9's R0a already reads at the answer sites only, so no restriction is needed and the whole logit
    tensor (every position) is compared; also the selection, the scores, the insertion-point hidden state
    and the memory read vector (the delta). Every comparison is ``torch.equal`` (bit for bit)."""
    from studies.p9.model import build_model_from_spec

    theirs = build_model_from_spec(_spec_for("N", slots), seed, backbone)
    mine = build_model("N", slots, seed, backbone, seed_rng=False)
    theirs.eval()
    mine.eval()
    same_parameters = all(
        torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in mine.named_parameters() if n.startswith("addition.")
    )
    with torch.no_grad():
        h_t, h_m = theirs.embed_block0(tokens), mine.embed_block0(tokens)
        sel_t, sel_m = theirs.select(h_t, tokens), mine.select(h_m, tokens)
        if sel_t is None or sel_m is None:
            raise ValueError("expected a memory selection from both models")
        delta_t, delta_m = theirs.memory_delta(h_t, sel_t), mine.memory_delta(h_m, sel_m)
        logits_t, _ = theirs(tokens)
        logits_m, _ = mine(tokens)
    sites = [p for p in core.ANSWER_SITE_POSITIONS if p < tokens.shape[1]]
    return {
        "same_parameters": same_parameters,
        "hidden_identical": bool(torch.equal(h_t, h_m)),
        "selection_identical": bool(torch.equal(sel_t.selected, sel_m.selected) and torch.equal(sel_t.positions, sel_m.positions)),
        "scores_identical": bool(torch.equal(sel_t.scores, sel_m.scores)),
        "read_vector_identical": bool(torch.equal(delta_t, delta_m)),
        "logits_identical": bool(torch.equal(logits_t, logits_m)),
        "answer_site_logits_identical": bool(torch.equal(logits_t[:, sites], logits_m[:, sites])),
        "max_abs_logit_difference": float((logits_t - logits_m).abs().max()),
        "read_positions": [int(p) for p in sel_m.positions],
    }


def initial_identities(backbone: "Backbone", slots: int, seed: int, tokens: "Tensor") -> dict[str, bool]:
    """At initialization (same seed, same inputs): BB's forward equals N's, BB-D's equals D plain's and
    BB-0's equals the no-memory baseline, bit for bit."""
    def logits(arm: str) -> "Tensor":
        net = build_model(arm, slots, seed, backbone, seed_rng=False)
        net.eval()
        with torch.no_grad():
            out: Tensor = net(tokens)[0]
        return out

    with torch.no_grad():
        baseline = no_memory_logits(backbone, tokens)
    return {
        "bb_equals_n": bool(torch.equal(logits("BB"), logits("N"))),
        "bb_d_equals_d": bool(torch.equal(logits("BB-D"), logits("D"))),
        "bb_0_equals_no_memory": bool(torch.equal(logits("BB-0"), baseline)),
    }
