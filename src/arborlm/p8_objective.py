"""P8 differentiable locality proxy and the matched-pressure training step (ADR-0015 sections 3-4).

The functions below are pure and dtype-agnostic (they run in float64 for ``gradcheck``). Queries are
context-major: index = r * T + t, the same order as the model's ``reshape(-1, 16)``.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import math
from dataclasses import dataclass, field
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch.optim import AdamW

from .p5_config import LEARNED
from .p5_model import Model, insertion_hidden, normalized_query, optimizer_names
from .p8_core import (
    ALPHA,
    BETA,
    GROUP,
    LAMBDA_FLOOR,
    REG_CO,
    REG_CONC,
    REG_TEMP,
    REGULARIZERS,
    SLOTS,
    SOFT_TOP,
    TOP,
    WINDOW,
)
from .pilot_metrics import loss_for
from .pilot_model import EPS, PER_BRANCH, TEMP, Memory, stable_top

THETA = ("addition.keys", "addition.wq", "addition.router")
CLIP_NORM = 1.0
CONC_FLOOR = 1e-30


# --- candidate scores and soft inclusion ---------------------------------------------------------
def candidate_scores(memory: Memory, q: Tensor) -> tuple[Tensor, Tensor]:
    """Differentiable selection scores of ``Memory.lookup`` (same operations, same order).

    flat: scores [Q, 4096], ids = arange; tree: scores [Q, 512] over the two visited branches with
    the log-softmax prior included, ids the slot IDs (branch choice and ids are hard). The hard
    top-8 of these scores equals ``Lookup.selected`` of the real lookup."""
    if memory.variant == "flat":
        scores = (q @ F.normalize(memory.keys, dim=-1, eps=EPS).T) / TEMP
        ids = torch.arange(memory.keys.shape[0], device=q.device).expand(q.shape[0], -1)
        return scores, ids
    routes = (q @ F.normalize(memory.router, dim=-1, eps=EPS).T) / TEMP
    _, branch_ids = stable_top(routes, 2)
    ids = (branch_ids[..., None] * PER_BRANCH + torch.arange(PER_BRANCH, device=q.device)).flatten(
        1
    )
    local = F.normalize(memory.keys[ids], dim=-1, eps=EPS)
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    prior = routes.log_softmax(-1).gather(-1, branch_ids)
    scores = scores + prior.repeat_interleave(PER_BRANCH, dim=-1)
    return scores, ids


@dataclass
class Soft:
    """Soft inclusion on each query's ``SOFT_TOP`` highest-scoring candidates (zero elsewhere).

    ``pi`` and ``log_miss`` = log(1 - pi) = -softplus(z) are [Q, SOFT_TOP]; ``ids`` are the slot
    IDs of those candidates; ``gap`` is the 8th-9th score gap per query."""

    pi: Tensor
    ids: Tensor
    log_miss: Tensor
    gap: Tensor


def soft_inclusion(
    scores: Tensor,
    ids: Tensor,
    beta: float = BETA,
    soft_top: int = SOFT_TOP,
) -> Soft:
    """pi = sigmoid((s - tau) / beta) on the ``soft_top`` best candidates, tau = (s(8) + s(9)) / 2
    NOT detached; log(1 - pi) = -softplus((s - tau) / beta) exactly, with no clamp."""
    top, index = scores.topk(soft_top, dim=-1, sorted=True)
    tau = 0.5 * (top[..., TOP - 1] + top[..., TOP])
    z = (top - tau.unsqueeze(-1)) / beta
    return Soft(
        torch.sigmoid(z),
        ids.gather(-1, index),
        -F.softplus(z),
        top[..., TOP - 1] - top[..., TOP],
    )


def to_slots(values: Tensor, ids: Tensor, slots: int = SLOTS) -> Tensor:
    """Scatter per-candidate values into slot space; every other slot is exactly 0."""
    return torch.zeros(values.shape[0], slots, dtype=values.dtype, device=values.device).scatter(
        1, ids, values
    )


# --- the three regularizers ----------------------------------------------------------------------
def r_conc(soft: Soft, slots: int = SLOTS) -> Tensor:
    """Normalized entropy of the batch's soft slot usage; floor ln 8 / ln 4096 = 0.25."""
    usage = to_slots(soft.pi, soft.ids, slots).sum(dim=0)
    u = usage / usage.sum()
    terms = torch.where(u > 0, u * torch.log(u.clamp_min(CONC_FLOOR)), torch.zeros_like(u))
    return -terms.sum() / math.log(slots)


def r_co(soft: Soft, group: int = GROUP, slots: int = SLOTS) -> Tensor:
    """Expected reference groups touched per expected selected slot (minimum 1 / group)."""
    miss = to_slots(soft.log_miss, soft.ids, slots)
    per_group = miss.reshape(miss.shape[0], slots // group, group).sum(-1)
    touched = (1.0 - torch.exp(per_group)).sum(-1)
    return torch.mean(touched / soft.pi.sum(-1))


def r_temp(soft: Soft, rows: int, window: int = WINDOW, slots: int = SLOTS) -> Tensor:
    """Expected fraction of a query's selections not softly selected in the previous ``window``
    positions of the same row, averaged over positions t >= 1."""
    dense = to_slots(soft.pi, soft.ids, slots)
    length = dense.shape[0] // rows
    if rows * length != dense.shape[0] or length < 2:
        raise ValueError("queries must be rows * T with T >= 2")
    cube = dense.reshape(rows, length, slots)
    miss = to_slots(soft.log_miss, soft.ids, slots).reshape(rows, length, slots)
    seen = torch.zeros_like(miss)
    for lag in range(1, min(window, length - 1) + 1):
        seen = seen + F.pad(miss[:, : length - lag], (0, 0, lag, 0))
    new = (cube * torch.exp(seen)).sum(-1) / cube.sum(-1)
    return new[:, 1:].mean()


def regularizer_values(
    soft: Soft, rows: int, names: tuple[str, ...] = REGULARIZERS
) -> dict[str, Tensor]:
    out: dict[str, Tensor] = {}
    for name in names:
        if name == REG_CONC:
            out[name] = r_conc(soft)
        elif name == REG_CO:
            out[name] = r_co(soft)
        elif name == REG_TEMP:
            out[name] = r_temp(soft, rows)
        else:
            raise ValueError(f"unknown regularizer {name!r}")
    return out


def proxy_inputs(model: Model, tokens: Tensor) -> tuple[Tensor, Tensor, Soft]:
    """(scores, ids, soft) from the model's insertion hidden state; q keeps its graph to ``wq``."""
    memory = model.addition
    if not isinstance(memory, Memory):
        raise ValueError("P8 proxy requires a memory addition")
    with torch.no_grad():
        h = insertion_hidden(model, tokens)
    q = normalized_query(memory, h)
    scores, ids = candidate_scores(memory, q)
    return scores, ids, soft_inclusion(scores, ids)


def diagnostics(model: Model, batch: Tensor) -> dict[str, Any]:
    """Proxy diagnostics under no_grad: all three R values, mean 8th-9th gap, mean pi mass outside
    the top 8. Reads the model only; consumes no RNG and touches no gradient."""
    with torch.no_grad():
        _, _, soft = proxy_inputs(model, batch[:, :-1])
        values = regularizer_values(soft, batch.shape[0])
        return {
            "regularizer_all": {k: float(v) for k, v in values.items()},
            "mean_gap_8_9": float(soft.gap.mean()),
            "mean_pi_mass_outside_top8": float((soft.pi[:, TOP:].sum(-1)).mean()),
            "mean_pi_mass_total": float(soft.pi.sum(-1).mean()),
        }


def proxy_values(model: Model, batch: Tensor) -> dict[str, float]:
    result: dict[str, float] = diagnostics(model, batch)["regularizer_all"]
    return result


# --- training step -------------------------------------------------------------------------------
@dataclass
class ReachTracker:
    """Cumulative distinct hard-selected slots across training updates."""

    seen: Tensor = field(default_factory=lambda: torch.zeros(SLOTS, dtype=torch.bool))

    def update(self, selected: Tensor) -> int:
        self.seen[selected.reshape(-1)] = True
        return int(self.seen.sum())


def _grad_or_zero(grad: Tensor | None, like: Tensor) -> Tensor:
    return torch.zeros_like(like) if grad is None else grad


def _norm(tensors: list[Tensor]) -> float:
    return float(torch.linalg.vector_norm(torch.cat([t.reshape(-1) for t in tensors])))


def train_step_p8(
    model: Model,
    optimizer: AdamW,
    batch: Tensor,
    step: int,
    objective_names: tuple[str, ...],
    *,
    alpha: float = ALPHA,
    tracker: ReachTracker | None = None,
    reach: bool = False,
) -> dict[str, Any]:
    """One P8 update. With no objective this is operation-for-operation P5's ``train_step``
    (zero_grad, forward, mean loss, backward, optimizer-membership and routing checks, clip, step).
    With regularizers: L's gradient is kept; each R's gradient is taken on Theta_r = {keys, wq,
    router if trainable} by a separate backward through a separate graph; lambda_k = alpha *
    ||g_L|Theta_r|| / ||g_Rk|| (a constant of the step; 0 if ||g_Rk|| < 1e-12 or a norm is
    non-finite); then g = g_L + sum_k lambda_k g_Rk, clipped and stepped as in P5."""
    optimizer.zero_grad(set_to_none=True)
    logits, lookup = model(batch[:, :-1])
    loss = loss_for(logits, batch[:, 1:], "mean")
    if not math.isfinite(loss.item()):
        raise ValueError(f"P8 non-finite loss at step {step}")
    loss.backward()  # type: ignore[no-untyped-call]
    names = optimizer_names(model, optimizer)
    named = dict(model.named_parameters())
    params = [named[name] for name in names]
    if not params or any(p.grad is None for p in params):
        raise ValueError(f"P8 missing addition gradients at step {step}")
    router_norm = None
    if model.cell.variant == LEARNED and isinstance(model.addition, Memory):
        router = model.addition.router
        if (
            router.grad is None
            or lookup is None
            or lookup.branch_ids is None
            or lookup.route_scores is None
            or not bool(lookup.route_scores.isfinite().all())
        ):
            raise ValueError(f"P8 missing or invalid routing at step {step}")
        router_norm = float(torch.linalg.vector_norm(router.grad))
        if not math.isfinite(router_norm):
            raise ValueError(f"P8 non-finite router gradient norm at step {step}")
    elif model.cell.variant in ("flat", "fixed_tree"):
        if (
            lookup is None
            or (lookup.branch_ids is None) != (model.cell.variant == "flat")
            or (lookup.route_scores is None) != (model.cell.variant == "flat")
            or (lookup.route_scores is not None and not bool(lookup.route_scores.isfinite().all()))
        ):
            raise ValueError("P8 retrieval structure mismatch")
    elif lookup is not None:
        raise ValueError("P8 dense addition returned retrieval")

    record: dict[str, Any] = {
        "step": step,
        "loss": loss.item(),
        "router_gradient_norm": router_norm,
        "objective": list(objective_names),
    }
    hard = lookup.selected if lookup is not None else None
    if tracker is not None and hard is not None:
        record["cumulative_hard_selected_slots"] = tracker.update(hard)
    memory = model.addition
    keys_grad = named["addition.keys"].grad if "addition.keys" in named else None
    if reach and keys_grad is not None:
        record["reach_g_l_key_rows"] = int((keys_grad.abs().sum(-1) > 0).sum())
        record["reach_batch_hard_selected"] = int(hard.unique().numel()) if hard is not None else 0

    if reach and isinstance(memory, Memory):
        record["diagnostics"] = diagnostics(model, batch)

    if objective_names:
        if not isinstance(memory, Memory) or hard is None:
            raise ValueError("P8 regularizers require a memory addition")
        theta = [(n, named[n]) for n in THETA if n in named and named[n].requires_grad]
        theta_params = [p for _, p in theta]
        g_l_all = _norm([_grad_or_zero(p.grad, p) for p in params])
        g_l_theta = _norm([_grad_or_zero(p.grad, p) for p in theta_params])
        scores, ids, soft = proxy_inputs(model, batch[:, :-1])
        selection_consistent = bool(torch.equal(stable_top(scores.detach(), TOP, ids)[1], hard))
        if not selection_consistent:
            raise ValueError(f"P8 proxy top-8 differs from the lookup's selection at step {step}")
        values = regularizer_values(soft, batch.shape[0], objective_names)
        record.update(
            selection_consistent=selection_consistent,
            g_l_norm=g_l_all,
            g_l_theta_norm=g_l_theta,
            regularizer={k: float(v) for k, v in values.items()},
            lam={},
            g_r_norm={},
            lambda_zero_event={},
            lambda_zero_reason={},
        )
        pulls: list[tuple[float, list[Tensor]]] = []
        last = len(objective_names) - 1
        for i, name in enumerate(objective_names):
            raw = torch.autograd.grad(
                values[name], theta_params, retain_graph=i < last, allow_unused=True
            )
            grads = [_grad_or_zero(g, p) for g, p in zip(raw, theta_params, strict=True)]
            g_r = _norm(grads)
            ok = math.isfinite(g_l_theta) and math.isfinite(g_r) and g_r >= LAMBDA_FLOOR
            lam = alpha * g_l_theta / g_r if ok else 0.0
            record["g_r_norm"][name] = g_r
            record["lam"][name] = lam
            record["lambda_zero_event"][name] = not ok
            record["lambda_zero_reason"][name] = (
                None if ok else ("non-finite norm" if not math.isfinite(g_r) else "g_r below floor")
            )
            if reach:
                keys_index = [n for n, _ in theta].index("addition.keys")
                rows = grads[keys_index].norm(dim=-1) > LAMBDA_FLOOR
                reached = int(rows.sum())
                outside = int((rows & ~torch.isin(torch.arange(SLOTS), hard.unique())).sum())
                record.setdefault("reach_g_r_key_rows", {})[name] = reached
                record.setdefault("reach_g_r_not_hard_selected", {})[name] = outside
            if lam != 0.0:
                pulls.append((lam, grads))
        for lam, grads in pulls:
            for p, g in zip(theta_params, grads, strict=True):
                assert p.grad is not None
                p.grad.add_(g, alpha=lam)
    norm = nn.utils.clip_grad_norm_(params, CLIP_NORM, error_if_nonfinite=True)
    before = [p.detach().clone() for p in params]
    optimizer.step()
    with torch.no_grad():
        moved = {n: p.detach() - b for n, p, b in zip(names, params, before, strict=True)}
    on_theta = [n for n in names if n in THETA]
    off_theta = [n for n in names if n not in THETA]
    record["param_change_l2"] = {
        "theta_r": _norm([moved[n] for n in on_theta]) if on_theta else 0.0,
        "other": _norm([moved[n] for n in off_theta]) if off_theta else 0.0,
    }
    if not all(bool(p.isfinite().all()) for p in params):
        raise ValueError(f"P8 non-finite parameter at step {step}")
    record["pre_clip_gradient_norm"] = norm.item()
    record["clipped"] = bool(norm.item() > CLIP_NORM)
    return record


__all__ = [
    "ReachTracker",
    "candidate_scores",
    "proxy_inputs",
    "proxy_values",
    "r_co",
    "r_conc",
    "r_temp",
    "regularizer_values",
    "Soft",
    "diagnostics",
    "soft_inclusion",
    "to_slots",
    "train_step_p8",
]
