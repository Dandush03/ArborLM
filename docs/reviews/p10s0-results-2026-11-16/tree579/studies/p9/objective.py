# ruff: noqa: E501
"""P9 objectives (package I2): soft inclusion, the global usage floor with the b-free gradient, the
co-access term, and the absolute coefficients.

Specification: ADR-0017 section 7 (D07, D08). The coefficients are fixed by ``core.lambda_u`` and
``core.lambda_c`` (no measurement, no cap, no adaptation) and are re-exported here; the doses are
``core.ALPHA_U_DOSES`` and ``core.ALPHA_C_DOSES``.

Queries: the usage floor and the co-access term use the answer-site queries only (ADR 7: "u_bar_t is
the batch-normalized pi usage at answer sites only"; the co-access term follows the same convention by
the lead's clarification 15.1 item 3). A ``Selection`` read at all 63 positions (R0) is therefore first
restricted with ``answer_site_rows``.

Gradient of the usage floor (ADR 7, auditor RECHECK W7, CONFIRM F4): with u_t = (1 - b) u_{t-1} +
b u_bar_t, u_{t-1} detached, the applied gradient is lam_u * (dR_glob/du at u_t) * d u_bar_t / d theta,
**without** the factor b. It is implemented as the loss ``lam_u * <g_t, u_bar_t>`` with ``g_t`` the
detached ``dR_glob/du`` at u_t, so autograd supplies ``d u_bar_t / d theta`` (including the batch
normalization) and no factor b appears. ``g_t = (ln u_t + 1) / ln N`` where the hinge is active (and 0
where u_t = 0, the 0 ln 0 = 0 convention; ``u_t >= b u_bar_t`` so it is finite wherever the gradient of
``u_bar`` is non-zero).

Additions to the stub (reported): ``SoftInclusion`` and ``soft_inclusion_full`` return the exact
``log(1 - pi) = -softplus(z)`` that ADR-0015's R_co needs (``log1p(-pi)`` would be -inf when pi rounds
to 1); ``coaccess_term`` takes it as an optional fourth argument; ``UsageStats`` keeps the soft and hard
usage averages for the entropy diagnostics of every memory cell.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from arborlm.p8_objective import Soft
from arborlm.p8_objective import r_co as _p8_r_co

from . import core
from .core import Cell, lambda_c, lambda_u
from .model import Selection

if TYPE_CHECKING:
    from torch import Tensor

__all__ = [
    "Objective",
    "ObjectiveResult",
    "SoftInclusion",
    "UsageFloor",
    "UsageStats",
    "answer_site_margins",
    "answer_site_rows",
    "answer_site_selected",
    "coaccess_term",
    "lambda_c",
    "lambda_u",
    "slot_usage",
    "soft_inclusion",
    "soft_inclusion_full",
    "soft_mass_outside_top8",
    "usage_entropy",
    "usage_floor_gradient_weights",
]

TOP = core.TOP
TINY = 1e-300


def _answer_columns(selection: Selection) -> list[int]:
    positions = selection.positions.tolist()
    try:
        return [positions.index(p) for p in core.ANSWER_SITE_POSITIONS]
    except ValueError as exc:
        raise ValueError("the selection does not cover every answer site") from exc


def answer_site_rows(selection: Selection) -> tuple["Tensor", "Tensor"]:
    """Restrict a selection to answer-site queries: returns ``(candidate_scores [Q, 64] float32,
    candidate_ids [Q, 64] int64)`` with ``Q = B * 8`` queries in (context, record) order."""
    if selection.candidate_scores is None or selection.candidate_ids is None:
        raise ValueError("this rung has no candidate scores (R2 reads one dedicated slot)")
    cols = _answer_columns(selection)
    scores = selection.candidate_scores[:, cols]
    ids = selection.candidate_ids[:, cols]
    return scores.reshape(-1, scores.shape[-1]), ids.reshape(-1, ids.shape[-1])


def answer_site_selected(selection: Selection) -> "Tensor":
    """``[B * 8, 8] int64`` hard top-8 slot ids of the answer-site queries (context, record order)."""
    cols = _answer_columns(selection)
    chosen = selection.selected[:, cols]
    return chosen.reshape(-1, chosen.shape[-1])


@dataclass
class SoftInclusion:
    """``pi`` and ``log_miss = log(1 - pi) = -softplus(z)`` ``[Q, 64]``; ``gap`` the 8th-9th score
    margin per query ``[Q]``."""

    pi: "Tensor"
    log_miss: "Tensor"
    gap: "Tensor"


def soft_inclusion_full(candidate_scores: "Tensor") -> SoftInclusion:
    """pi_s = sigmoid((score_s - tau) / 0.25) on a query's top-64 candidates, tau the midpoint of the
    8th and 9th scores, not detached (ADR 7, as ADR-0015 rev. 3; the same arithmetic as
    ``arborlm.p8_objective.soft_inclusion``)."""
    tau = 0.5 * (candidate_scores[..., TOP - 1] + candidate_scores[..., TOP])
    z = (candidate_scores - tau.unsqueeze(-1)) / core.BETA_SOFT
    return SoftInclusion(
        pi=torch.sigmoid(z),
        log_miss=-F.softplus(z),
        gap=candidate_scores[..., TOP - 1] - candidate_scores[..., TOP],
    )


def soft_inclusion(candidate_scores: "Tensor") -> "Tensor":
    """pi_s = sigmoid((score_s - tau) / 0.25) on a query's top-64 candidates, tau the midpoint of the
    8th and 9th scores, not detached (ADR 7, as ADR-0015 rev. 3). ``[Q, 64] -> [Q, 64]`` float32."""
    return soft_inclusion_full(candidate_scores).pi


def slot_usage(pi: "Tensor", candidate_ids: "Tensor", slots: int) -> "Tensor":
    """u_bar_t: batch-normalized soft usage, ``[slots] float32`` summing to 1, scattered from ``pi``
    ``[Q, 64]`` over ``candidate_ids [Q, 64]`` (differentiable in ``pi``)."""
    usage = pi.new_zeros(slots).index_add(0, candidate_ids.reshape(-1), pi.reshape(-1))
    return usage / usage.sum()


def usage_entropy(u: "Tensor") -> "Tensor":
    """H(u) = -sum u ln u with 0 ln 0 = 0 (scalar, float64 accumulation, returned in ``u``'s dtype)."""
    d = u.double()
    terms = torch.where(d > 0, d * torch.log(d.clamp_min(TINY)), torch.zeros_like(d))
    return (-terms.sum()).to(u.dtype)


def usage_floor_gradient_weights(u_detached: "Tensor", slots: int, facts: int) -> "Tensor":
    """g_t = dR_glob/du at the detached u_t, ``[slots] float32``, for R_glob = max(0, ln M - H(u)) /
    ln N with M = ``core.usage_floor_support(slots, facts)``; finite on every slot where u_t > 0 and
    zero when the hinge is inactive; no epsilon is added (ADR 7)."""
    log_m = math.log(core.usage_floor_support(slots, facts))
    log_n = math.log(slots)
    u = u_detached.detach().double()
    if not bool(log_m - usage_entropy(u) > 0):
        return torch.zeros(slots, dtype=torch.float32)
    g = torch.where(u > 0, (torch.log(u.clamp_min(TINY)) + 1.0) / log_n, torch.zeros_like(u))
    return g.to(torch.float32)


def _check_state(state: dict[str, Any], keys: tuple[str, ...]) -> None:
    if set(state) != set(keys):
        raise ValueError(f"objective state must have exactly the keys {keys}")


class UsageFloor:
    """Global usage floor state: the moving average u_t = (1 - b) u_{t-1} + b u_bar_t with b = 128 / F
    (``core.usage_ema_rate``); u_{t-1} detached; u_0 = the first batch's u_bar (so u_1 = u_bar_1). The
    state is part of the training state and must be saved in and restored from every snapshot
    (``state_dict``)."""

    def __init__(self, slots: int, facts: int) -> None:
        self.slots = slots
        self.facts = facts
        self.b = core.usage_ema_rate(facts)
        self.log_m = math.log(core.usage_floor_support(slots, facts))
        self.log_n = math.log(slots)
        self.u: Tensor | None = None
        self.updates = 0

    def advance(self, u_bar: "Tensor") -> "Tensor":
        """Advance the average with the detached ``u_bar``; returns the new detached u_t."""
        batch = u_bar.detach()
        previous = batch if self.u is None else self.u
        self.u = (1.0 - self.b) * previous + self.b * batch
        self.updates += 1
        return self.u

    def r_glob(self, u: "Tensor") -> float:
        """R_glob(u) = max(0, ln M - H(u)) / ln N."""
        return max(0.0, self.log_m - float(usage_entropy(u))) / self.log_n

    def penalty(self, u_bar: "Tensor", lam: float) -> tuple["Tensor", dict[str, float | bool]]:
        """Advance the average with the detached value of ``u_bar`` and return the scalar loss term
        ``lam * <g_t, u_bar>`` (the applied gradient is lam * g_t * d u_bar / d theta, without the
        factor b) and diagnostics: ``hinge_active``, ``entropy_soft`` (H(u_t)), ``r_glob``."""
        u_t = self.advance(u_bar)
        entropy = float(usage_entropy(u_t))
        g = usage_floor_gradient_weights(u_t, self.slots, self.facts)
        term = lam * (g * u_bar).sum()
        return term, {
            "hinge_active": self.log_m - entropy > 0,
            "entropy_soft": entropy,
            "r_glob": max(0.0, self.log_m - entropy) / self.log_n,
        }

    def peek_weights(self, u_bar: "Tensor") -> "Tensor":
        """g at the current average (or, before any update, at ``u_bar``) without advancing it."""
        return usage_floor_gradient_weights(
            u_bar.detach() if self.u is None else self.u, self.slots, self.facts
        )

    def state_dict(self) -> dict[str, Any]:
        return {"u": None if self.u is None else self.u.clone(), "updates": self.updates}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        _check_state(state, ("u", "updates"))
        self.u = None if state["u"] is None else state["u"].clone()
        self.updates = int(state["updates"])


def coaccess_term(
    pi: "Tensor", candidate_ids: "Tensor", slots: int, log_miss: "Tensor | None" = None
) -> "Tensor":
    """R_co of ADR-0015 (expected number of 8-slot identifier groups touched per selected slot;
    group = slot id // 8, ``core.CO_GROUP``), scalar; its best value is ``core.CO_BEST`` = 1/8. It calls
    ``arborlm.p8_objective.r_co`` unchanged. ``log_miss`` is ``log(1 - pi)`` (pass the exact
    ``SoftInclusion.log_miss``; without it ``log1p(-pi)`` is used, which is -inf where pi rounds to 1)."""
    miss = torch.log1p(-pi) if log_miss is None else log_miss
    soft = Soft(pi=pi, ids=candidate_ids, log_miss=miss, gap=torch.zeros_like(pi[..., 0]))
    return _p8_r_co(soft, group=core.CO_GROUP, slots=slots)


def answer_site_margins(selection: Selection) -> "Tensor":
    """``[B * 8]`` 8th minus 9th candidate score at the answer sites (detached)."""
    scores, _ = answer_site_rows(selection)
    return (scores[:, TOP - 1] - scores[:, TOP]).detach()


def soft_mass_outside_top8(selection: Selection) -> float:
    """Mean over answer-site queries of the soft inclusion mass on candidates 9..64."""
    scores, _ = answer_site_rows(selection)
    with torch.no_grad():
        pi = soft_inclusion_full(scores).pi
        return float(pi[:, TOP:].sum(-1).mean())


class UsageStats:
    """Diagnostic soft and hard usage averages (same rate b and first-batch start as the floor), kept for
    every memory cell. ``update`` returns (H of the soft average, H of the hard average)."""

    def __init__(self, slots: int, facts: int) -> None:
        self.slots = slots
        self.b = core.usage_ema_rate(facts)
        self.soft: Tensor | None = None
        self.hard: Tensor | None = None

    def _advance(self, previous: "Tensor | None", batch: "Tensor") -> "Tensor":
        base = batch if previous is None else previous
        return (1.0 - self.b) * base + self.b * batch

    def update(
        self, pi: "Tensor", candidate_ids: "Tensor", selected: "Tensor"
    ) -> tuple[float, float]:
        with torch.no_grad():
            soft_batch = slot_usage(pi.detach(), candidate_ids, self.slots)
            counts = torch.zeros(self.slots, dtype=torch.float32).index_add(
                0, selected.reshape(-1), torch.ones(selected.numel(), dtype=torch.float32)
            )
            hard_batch = counts / counts.sum()
            self.soft = self._advance(self.soft, soft_batch)
            self.hard = self._advance(self.hard, hard_batch)
            return float(usage_entropy(self.soft)), float(usage_entropy(self.hard))

    def state_dict(self) -> dict[str, Any]:
        return {
            "soft": None if self.soft is None else self.soft.clone(),
            "hard": None if self.hard is None else self.hard.clone(),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        _check_state(state, ("soft", "hard"))
        self.soft = None if state["soft"] is None else state["soft"].clone()
        self.hard = None if state["hard"] is None else state["hard"].clone()


@dataclass
class ObjectiveResult:
    """``total`` is task + lambda_u * usage term + lambda_c * (R_co - 1/8); parts are detached floats
    for logging; ``diagnostics`` holds hinge flags and soft/hard entropies (UpdateRecord fields).

    ``usage_penalty`` is the **value** lambda_u * R_glob(u_t) (what the term costs); the loss tensor
    added to ``total`` is lambda_u * <g_t, u_bar_t>, whose value is not R_glob but whose gradient is
    the applied one. ``coaccess_penalty`` is lambda_c * (R_co - 1/8)."""

    total: "Tensor"
    task: float
    usage_penalty: float
    coaccess_penalty: float
    diagnostics: dict[str, float | bool | None]


class Objective:
    """The cell's objective: answer-site cross-entropy plus the usage and co-access terms with the
    absolute coefficients of the cell (``core.lambda_u_for``, ``core.lambda_c_for``). Cells with
    alpha_u = alpha_c = 0 add nothing to the loss; every memory cell still advances the diagnostic
    ``UsageStats`` (a few vector operations per update)."""

    def __init__(self, cell: Cell) -> None:
        self.cell = cell
        self.lambda_u = core.lambda_u_for(cell)
        self.lambda_c = core.lambda_c_for(cell)
        self.has_usage = cell.alpha_u > 0
        self.has_coaccess = cell.alpha_c > 0
        memory = cell.arch != "dense" and cell.rung != "R2"
        self.floor = UsageFloor(cell.slots, cell.facts) if self.has_usage else None
        self.stats = UsageStats(cell.slots, cell.facts) if memory else None
        self.last_terms: dict[str, Tensor] = {}
        self.last_diagnostics: dict[str, float | bool | None] = self._blank()

    @property
    def active(self) -> bool:
        return self.has_usage or self.has_coaccess

    @staticmethod
    def _blank() -> dict[str, float | bool | None]:
        return {
            "hinge_usage_active": False,
            "hinge_coaccess_active": False,
            "usage_entropy_soft": None,
            "usage_entropy_hard": None,
            "r_glob": None,
            "r_co": None,
        }

    def __call__(self, task_loss: "Tensor", selection: Selection | None) -> ObjectiveResult:
        self.last_terms = {}
        diag = self._blank()
        usage_value = coaccess_value = 0.0
        total = task_loss
        if (
            selection is not None
            and selection.candidate_scores is not None
            and self.stats is not None
        ):
            scores, ids = answer_site_rows(selection)
            soft = soft_inclusion_full(scores)
            soft_h, hard_h = self.stats.update(soft.pi, ids, answer_site_selected(selection))
            diag["usage_entropy_soft"], diag["usage_entropy_hard"] = soft_h, hard_h
            if self.floor is not None:
                u_bar = slot_usage(soft.pi, ids, self.cell.slots)
                term, info = self.floor.penalty(u_bar, self.lambda_u)
                self.last_terms["usage"] = term
                total = total + term
                diag["hinge_usage_active"] = bool(info["hinge_active"])
                diag["r_glob"] = float(info["r_glob"])
                usage_value = self.lambda_u * float(info["r_glob"])
            if self.has_coaccess:
                r_co = coaccess_term(soft.pi, ids, self.cell.slots, soft.log_miss)
                term = self.lambda_c * (r_co - core.CO_BEST)
                self.last_terms["coaccess"] = term
                total = total + term
                diag["r_co"] = float(r_co)
                diag["hinge_coaccess_active"] = float(r_co) > core.CO_BEST
                coaccess_value = float(term)
        elif self.active:
            raise ValueError("a regularized cell needs a memory selection with candidates")
        self.last_diagnostics = diag
        return ObjectiveResult(
            total=total,
            task=float(task_loss.detach()),
            usage_penalty=usage_value,
            coaccess_penalty=coaccess_value,
            diagnostics=diag,
        )

    def regularizer_losses(self, selection: Selection) -> dict[str, "Tensor"]:
        """The individual regularizer loss tensors (for the per-group gradient norms of ADR 6.3),
        keyed ``usage`` and ``coaccess``, without advancing the moving average a second time. After
        ``__call__`` these are the very tensors added to its total (same graph); without a preceding
        call they are rebuilt from ``selection`` against the current state."""
        if self.last_terms:
            return dict(self.last_terms)
        terms: dict[str, Tensor] = {}
        if not self.active:
            return terms
        scores, ids = answer_site_rows(selection)
        soft = soft_inclusion_full(scores)
        if self.floor is not None:
            u_bar = slot_usage(soft.pi, ids, self.cell.slots)
            g = self.floor.peek_weights(u_bar)
            terms["usage"] = self.lambda_u * (g * u_bar).sum()
        if self.has_coaccess:
            r_co = coaccess_term(soft.pi, ids, self.cell.slots, soft.log_miss)
            terms["coaccess"] = self.lambda_c * (r_co - core.CO_BEST)
        return terms

    def state_dict(self) -> dict[str, Any]:
        return {
            "floor": None if self.floor is None else self.floor.state_dict(),
            "stats": None if self.stats is None else self.stats.state_dict(),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        _check_state(state, ("floor", "stats"))
        if (state["floor"] is None) != (self.floor is None) or (state["stats"] is None) != (
            self.stats is None
        ):
            raise ValueError("objective state does not match this cell's objective")
        if self.floor is not None:
            self.floor.load_state_dict(state["floor"])
        if self.stats is not None:
            self.stats.load_state_dict(state["stats"])
        self.last_terms = {}
