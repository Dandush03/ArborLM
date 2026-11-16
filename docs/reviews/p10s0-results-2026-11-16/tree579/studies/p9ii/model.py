# ruff: noqa: E501
"""P9II models (ADR-0019 section 3 and 4): arms A0, A1, A2, A4, A5-C, A5-D, A1-S (all W7, the seven-position
window query of P9-I), the oracle reference A6 (= P9-I's R1) and the dense control A7 (= P9-I's D7).

The arms differ in the objective and, for A4 and A5-C, in the forward:

====  ==================================================================================================
arm   forward                                                                         objective (trainer)
====  ==================================================================================================
A0    P9-I's W7, the same code path (bit-identical)                                   answer loss
A1    as A0                                                                           answer + lambda * L_addr
A2    as A0                                                                           L_addr only, then answer only
A4    top-k(t) read, softmax(a / 0.2) over the k(t) best slots; k = 8 from T_A on     answer loss
A5-C  z' = z - m, q = z' / |z'|; m an EMA buffer (decay 0.99, no gradient)           answer loss
A5-D  as A0                                                                           answer + mu * L_div
A1-S  as A0                                                                           answer + lambda * L_addr (random targets)
A6    P9-I's R1 (oracle query, reference only)                                         answer loss
A7    P9-I's D7 (parameter-matched dense window)                                      answer loss
====  ==================================================================================================

No backbone parameter is trainable in any arm. No learned arm's forward takes a fact identity (gate G6):
``forward(tokens)`` and ``select(h_pre, tokens)`` are the only entry points the trainer and the evaluation use.
Fact identities enter the study only through the trainer's targets (``target_injection``, ``a1s_targets``).

Imported from P9-I and called, not copied: ``IMemory`` (the W7 query), ``IDense`` (D7), ``P9IModel``. Written here
because their versions cannot do what ADR-0019 needs: the top-k(t) read of A4, the centred query of A5-C, the
address loss, the diversity loss, the target slots, the per-parameter groups, and G5/G6.
"""

import hashlib
import inspect
from typing import TYPE_CHECKING, Any, cast

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS, stable_top
from studies.p9.model import Selection
from studies.p9i.model import IDense, IMemory, P9IModel

from . import core

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
MEMORY_GROUPS = ("wq", "keys", "values", "wo", "gate")
GROUPS = (*MEMORY_GROUPS, "dense")
STANDARD_K = core.STANDARD_K


# --- the memory --------------------------------------------------------------------------------------------------
class IIMemory(IMemory):
    """P9-I's W7 memory (``wq`` 16 x 224) with the three things ADR-0019 adds. For A0, A1, A2, A5-D and A1-S nothing is
    overridden in effect: ``select`` and ``_query`` run P9-I's code, so the forward is bit-identical to W7's.

    * A4: ``read_k`` (set by the trainer from ``core.k_schedule``; 8 everywhere else, including every evaluation) widens the
      read to the ``read_k`` best slots, softmax at temperature 0.2 over them.
    * A5-C: ``centre`` (a 16-vector buffer): z' = z - m before normalization; ``commit_centre`` moves it by the EMA.
    * the trainer's auxiliary losses read ``last_query`` (the normalized queries of the batch, with their graph) when
      ``keep_query`` is set.
    """

    def __init__(self, arm: str, slots: int, seed: int) -> None:
        if arm not in core.LEARNED_ARMS:
            raise ValueError(f"not a learned P9II arm: {arm!r}")
        super().__init__("W7", slots, seed)  # self.arm stays "W7": P9-I's helpers key on it
        self.ii_arm = arm
        self.read_k = STANDARD_K
        self.keep_query = False
        self.last_query: Tensor | None = None
        self._pending_z: Tensor | None = None
        if arm == "A5-C":
            self.register_buffer("centre", torch.zeros(core.KEY_WIDTH))
            self.register_buffer("centre_initialised", torch.zeros((), dtype=torch.int64))

    # -- the query -----------------------------------------------------------------------------------------------
    def window_z(self, h_pre: "Tensor", positions: "Tensor") -> "Tensor":
        """``[B, P, 16]`` un-normalized query z = W [h_{t-6}; ...; h_t] (no centring)."""
        return F.linear(self.window(h_pre, positions), self.wq)

    def _query(self, h_pre: "Tensor", tokens: "Tensor", positions: "Tensor") -> "Tensor":
        if self.ii_arm != "A5-C" and not self.keep_query:
            return super()._query(h_pre, tokens, positions)
        z = F.linear(self._features(h_pre, positions), self.wq)
        if self.ii_arm == "A5-C":
            if self.training:
                self._pending_z = z.detach().reshape(-1, core.KEY_WIDTH).mean(0)
            z = z - cast("Tensor", self.centre)
        q = F.normalize(z, dim=-1, eps=EPS).reshape(-1, self.spec.key_width)
        if self.keep_query:
            self.last_query = q
        return q

    # -- A5-C: the common-mode estimate ------------------------------------------------------------------------------
    @torch.no_grad()
    def init_centre(self, z_rows: "Tensor") -> None:
        """m := the mean of z at initialization over the training batches given (``z_rows [n, 16]``)."""
        if self.ii_arm != "A5-C":
            raise ValueError("only A5-C has a centre")
        cast("Tensor", self.centre).copy_(z_rows.mean(0))
        cast("Tensor", self.centre_initialised).fill_(1)

    @torch.no_grad()
    def commit_centre(self) -> None:
        """m := 0.99 m + 0.01 * (the batch mean of z of the last training forward); no gradient ever reaches m."""
        if self.ii_arm != "A5-C" or self._pending_z is None:
            return
        centre = cast("Tensor", self.centre)
        centre.mul_(core.CENTRE_DECAY).add_(self._pending_z, alpha=1.0 - core.CENTRE_DECAY)
        self._pending_z = None

    # -- the read ------------------------------------------------------------------------------------------------------
    def select(self, h_pre: "Tensor", tokens: "Tensor") -> Selection:
        k = self.read_k if self.ii_arm == "A4" else STANDARD_K
        if k == STANDARD_K:
            return super().select(h_pre, tokens)
        return self._select_wide(h_pre, tokens, min(k, self.spec.slots))

    def _select_wide(self, h_pre: "Tensor", tokens: "Tensor", k: int) -> Selection:
        """The ``k`` best slots of every answer-site query (ties by slot id), scores at temperature 0.2, all N scores computed."""
        b, length, _ = h_pre.shape
        positions = SITES[SITES < length]
        q = self._query(h_pre, tokens, positions)
        normalized = F.normalize(cast("Tensor", self.keys), dim=-1, eps=EPS)
        values, ids = stable_top((q @ normalized.T) / core.TEMPERATURE, k)
        p = positions.numel()
        return Selection(positions, ids.reshape(b, p, k), values.reshape(b, p, k), None, None, None, None, length)

    def delta(self, selection: Selection, *, knockout: "Tensor | None" = None, values: "Tensor | None" = None) -> "Tensor":
        """The read contribution. At k = N (A4's first phase when k_0 = N) the softmax runs over all N scores and is applied
        to the value table by a matrix product over slot order; otherwise P9's ``ScalableMemory.delta``."""
        b, p, k = selection.selected.shape
        if k != self.spec.slots or knockout is not None:
            return super().delta(selection, knockout=knockout, values=values)
        table = self.values if values is None else values
        weights = selection.scores.reshape(-1, k).softmax(-1)
        full = torch.zeros_like(weights).scatter(1, selection.selected.reshape(-1, k), weights)
        out = self.gate.sigmoid() * F.linear((full @ table).reshape(b, p, -1), self.wo)
        positions = selection.positions
        whole = out.new_zeros((b, selection.length, out.shape[-1]))
        return whole.index_copy(1, positions, out)


# --- the model ---------------------------------------------------------------------------------------------------------
class P9IIModel(P9IModel):
    """Frozen backbone (a deep copy, never trainable) plus the arm's addition. ``forward(tokens)`` takes tokens only."""

    ii_arm: str

    def __init__(self, arm: str, slots: int, seed: int, backbone: "Backbone", *, r1_seed: int | None = None) -> None:
        if arm not in core.ARMS:
            raise ValueError(f"unknown P9II arm {arm!r}")
        super().__init__(core.BASE_ARM[arm], slots, seed, backbone, r1_seed=r1_seed)
        if arm in core.LEARNED_ARMS:
            self.addition = IIMemory(arm, slots, seed)
        self.arm = arm
        self.ii_arm = arm
        for p in self.backbone.parameters():
            p.requires_grad_(False)

    def group_of(self, name: str) -> str:
        if isinstance(self.addition, IDense):
            return "dense"
        return name.rsplit(".", 1)[-1]

    def set_read_k(self, k: int) -> None:
        if isinstance(self.addition, IIMemory):
            self.addition.read_k = int(k)

    def answer_z(self, h_pre: "Tensor", tokens: "Tensor") -> "Tensor | None":
        """``[B, 8, 16]`` un-normalized, un-centred query z at the answer sites; None for A6 and A7."""
        if not isinstance(self.addition, IIMemory):
            return None
        return self.addition.window_z(h_pre, SITES[SITES < h_pre.shape[1]])

    def answer_scores(self, h_pre: "Tensor", tokens: "Tensor") -> "Tensor | None":
        """``[B * 8, N]`` cosine scores a_s of every answer-site query against every slot (no temperature); None for A7."""
        q = self.answer_queries(h_pre, tokens)
        keys = getattr(self.addition, "keys", None)
        if q is None or keys is None:
            return None
        return q.reshape(-1, q.shape[-1]) @ F.normalize(keys, dim=-1, eps=EPS).T


def build_model(arm: str, slots: int, seed: int, backbone: "Backbone", *, r1_seed: int | None = None, seed_rng: bool = True) -> P9IIModel:
    """Model of ``arm`` at ``slots`` with initialization seed ``seed``. ``seed_rng`` seeds Python's and torch's global generators
    with the init seed as P9 and P9-I do (no parameter initialization depends on them)."""
    if seed_rng:
        import random

        random.seed(seed)
        torch.default_generator.manual_seed(seed)
    return P9IIModel(arm, slots, seed, backbone, r1_seed=r1_seed)


# --- A2 phases -------------------------------------------------------------------------------------------------------------
A2_PHASE1_FROZEN = ("values", "wo", "gate")


def set_a2_phase(model: P9IIModel, phase: int) -> None:
    """Phase 1: the query projection and the keys train, values, output projection and gate are frozen. Phase 2: everything
    in the addition is trainable (the backbone never is)."""
    if model.ii_arm != "A2" or phase not in (1, 2):
        raise ValueError("A2 has phases 1 and 2")
    for name, p in model.addition.named_parameters():
        p.requires_grad_(phase == 2 or name not in A2_PHASE1_FROZEN)


# --- the auxiliary losses ---------------------------------------------------------------------------------------------------
def target_injection(facts: int, slots: int, seed: int) -> "Tensor":
    """The fixed injection s(f) of the ``facts`` trained facts into the ``slots`` slots, drawn once per cell from ``seed``
    (base + 40 + j): an arbitrary label, not an oracle code."""
    if facts > slots:
        raise ValueError("an injection needs at least as many slots as facts")
    generator = torch.Generator().manual_seed(seed)
    return torch.randperm(slots, generator=generator)[:facts]


def a1s_targets(seed: int, update: int, slots: int, count: int = core.ANSWER_SITES_PER_BATCH) -> "Tensor":
    """A1-S's targets of one update: ``count`` uniform draws over the slots, a pure function of (seed, update), so independent
    of the fact, of the data order and of the initialization, and reproducible from the seed (base + 60 + j)."""
    generator = torch.Generator().manual_seed(core.derive_seed(seed, "a1s", update))
    return torch.randint(0, slots, (count,), generator=generator)


def all_scores(q: "Tensor", keys: "Tensor") -> "Tensor":
    """``[R, N]`` cosine scores of unit queries against every (normalized) key: all N scores."""
    return q @ F.normalize(keys, dim=-1, eps=EPS).T


def address_loss(q: "Tensor", keys: "Tensor", targets: "Tensor", tau: float = core.TAU_ADDR) -> "Tensor":
    """L_addr = mean over answer sites of -log( exp(a_t / tau) / sum_{s=1..N} exp(a_s / tau) ): a supervised InfoNCE with fixed
    proxies. It uses all N scores and has gradients to the query projection (through q) and to the keys only."""
    return F.cross_entropy(all_scores(q, keys) / tau, targets)


def diversity_loss(q: "Tensor") -> "Tensor":
    """L_div = log( mean_{i != j} exp(2 q_i . q_j) ) over the batch's normalized, un-centred queries."""
    n = q.shape[0]
    sims = DIVERSITY * (q @ q.T)
    off = ~torch.eye(n, dtype=torch.bool)
    return torch.logsumexp(sims[off], dim=0) - torch.log(torch.tensor(float(n * (n - 1))))


DIVERSITY = core.DIVERSITY_SCALE


# --- counts -------------------------------------------------------------------------------------------------------------------
def trainable_counts(model: P9IIModel) -> dict[str, int]:
    """Trainable parameters by group at the moment (A2: phase 1 or 2 as set)."""
    out = dict.fromkeys(GROUPS, 0)
    for name, p in model.trainable():
        out[model.group_of(name)] += p.numel()
    return out


def parameter_report(model: P9IIModel) -> dict[str, Any]:
    by_group = trainable_counts(model)
    backbone = [p for n, p in model.named_parameters() if n.startswith("backbone.")]
    addition = sum(p.numel() for p in model.addition.parameters())
    buffers = sum(t.numel() for t in model.addition.buffers())
    return {
        "arm": model.arm,
        "slots": model.slots,
        "trainable": sum(by_group.values()),
        "by_group": by_group,
        "trainable_backbone": sum(p.numel() for p in backbone if p.requires_grad),
        "frozen_backbone": sum(p.numel() for p in backbone if not p.requires_grad),
        "stored": sum(p.numel() for p in backbone) + addition + buffers,
        "buffers": buffers,
    }


# --- G5 and G6 -----------------------------------------------------------------------------------------------------------------
def tensor_sha256(t: "Tensor") -> str:
    return hashlib.sha256(bytes(t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist())).hexdigest()


def backbone_hashes(backbone: "Backbone") -> dict[str, str]:
    """sha256 of every backbone tensor (parameters and buffers)."""
    return {name: tensor_sha256(t) for name, t in backbone.state_dict().items()}


def no_memory_logits(frozen: "Backbone", tokens: "Tensor") -> "Tensor":
    from studies.p9i.model import no_memory_logits as p9i_no_memory

    return p9i_no_memory(frozen, tokens)


@torch.no_grad()
def g5_check(model: P9IIModel, frozen: "Backbone", tokens: "Tensor") -> dict[str, Any]:
    """G5 (backbone identity, section 9): every backbone tensor of ``model`` hashes like the frozen backbone's, and with the addition
    disabled the logits on ``tokens`` ([R, <= 64] corpus rows) equal the frozen backbone's bit for bit."""
    was = model.training
    model.eval()
    try:
        before, after = backbone_hashes(frozen), backbone_hashes(model.backbone)
        h_pre = model.embed_block0(tokens)
        off = model.finish(h_pre, model.memory_delta(h_pre, None, disabled=True))
        identical = bool(torch.equal(off, no_memory_logits(frozen, tokens)))
    finally:
        model.train(was)
    mismatched = sorted(n for n in before if before[n] != after.get(n))
    return {"passed": not mismatched and identical, "hash_mismatches": mismatched, "tensors": len(before), "disabled_logits_identical": identical}


def forward_arguments(model: P9IIModel) -> dict[str, list[str]]:
    """Parameter names of the forward entry points (G6: tokens only, no fact identity)."""
    return {
        "forward": [n for n in inspect.signature(model.forward).parameters],
        "select": [n for n in inspect.signature(model.select).parameters],
    }


@torch.no_grad()
def g6_check(backbone: "Backbone", slots: int, seed: int, tokens: "Tensor", fact_lut_a: "Tensor", fact_lut_b: "Tensor") -> dict[str, Any]:
    """G6 (section 9): no learned arm's forward has a fact-identity input, and with the token inputs fixed, permuting the target slots,
    the R1 codes and the fact-index tables leaves every learned arm's logits bit-identical. ``fact_lut_a`` and ``fact_lut_b`` stand for two
    different fact-index tables (they are offered to the construction path and ignored by every learned arm)."""
    out: dict[str, Any] = {"arms": {}}
    for arm in core.LEARNED_ARMS:
        args = forward_arguments(build_model(arm, slots, seed, backbone, seed_rng=False))
        a = build_model(arm, slots, seed, backbone, r1_seed=101, seed_rng=False)
        b = build_model(arm, slots, seed, backbone, r1_seed=202, seed_rng=False)
        a.eval()
        b.eval()
        same = bool(torch.equal(a(tokens)[0], b(tokens)[0]))
        out["arms"][arm] = {"forward_arguments": args, "tokens_only": args["forward"] == ["tokens"] and args["select"] == ["h_pre", "tokens"], "logits_identical_under_changed_tables": same}
    out["fact_tables_differ"] = bool(not torch.equal(fact_lut_a, fact_lut_b))
    out["passed"] = bool(out["fact_tables_differ"] and all(v["tokens_only"] and v["logits_identical_under_changed_tables"] for v in out["arms"].values()))
    return out
