"""Independent float64 exhaustive routing reference for P6-Q (ADR-0011 section 4.3).

Written by the auditor role from the scoring rule stated in ADR-0011 section 4.1,
without reusing the frozen pilot implementation. It scores every one of the
4,096 memory slots directly in float64 and selects the top 8 with ties broken by
ascending slot ID.

Rule (all arithmetic in float64, after converting the float32 inputs):

* ``normalize(x) = x / max(||x||_2, 1e-8)`` row-wise, applied to keys and router rows.
* ``cos_i = <q, normalize(key_i)> / 0.2``; ``q`` is used exactly as given.
* ``route_b = <q, normalize(router_b)> / 0.2`` for all 16 branches.
* Slot ``i`` belongs to branch ``i // 256``.
* ``use_prior=True``: ``score_i = cos_i + log_softmax(route)[i // 256]``.
* ``use_prior=False``: ``score_i = cos_i``.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["exhaustive_reference"]

_DIM = 16
_BRANCHES = 16
_SLOTS_PER_BRANCH = 256
_SLOTS = _BRANCHES * _SLOTS_PER_BRANCH
_TOP = 8
_TEMPERATURE = 0.2
_NORM_EPS = 1e-8


def _check(name: str, value: object, shape: tuple[int | None, ...]) -> Tensor:
    if not isinstance(value, Tensor):
        raise TypeError(f"{name} must be a torch.Tensor, got {type(value).__name__}")
    if value.dtype != torch.float32:
        raise TypeError(f"{name} must be float32, got {value.dtype}")
    if value.dim() != len(shape) or any(
        want is not None and got != want for got, want in zip(value.shape, shape, strict=True)
    ):
        expected = "[" + ", ".join("N" if want is None else str(want) for want in shape) + "]"
        raise ValueError(f"{name} must have shape {expected}, got {list(value.shape)}")
    if not bool(torch.isfinite(value).all()):
        raise ValueError(f"{name} contains non-finite values")
    return value


def _unit_rows(matrix: Tensor) -> Tensor:
    """Row-wise x / max(||x||_2, eps) in float64."""
    norms = torch.sqrt((matrix * matrix).sum(dim=1, keepdim=True))
    return matrix / torch.clamp(norms, min=_NORM_EPS)


def _log_softmax_rows(logits: Tensor) -> Tensor:
    """Row-wise log-softmax in float64 via a max-shifted log-sum-exp."""
    shift = logits.max(dim=1, keepdim=True).values
    shifted = logits - shift
    return shifted - torch.log(torch.exp(shifted).sum(dim=1, keepdim=True))


def exhaustive_reference(
    q: Tensor, keys: Tensor, router: Tensor, *, use_prior: bool
) -> tuple[Tensor, Tensor, Tensor]:
    """Independent float64 scoring of all 4,096 slots for float32 inputs q [N,16] (already normalized queries), raw keys [4096,16], raw router [16,16].
    Returns (scores [N,4096] float64, selected_ids [N,8] int64 ordered by descending score then ascending slot ID, boundary_gap [N] float64 = 8th minus 9th score)."""  # noqa: E501
    if not isinstance(use_prior, bool):
        raise TypeError("use_prior must be a bool")
    _check("q", q, (None, _DIM))
    _check("keys", keys, (_SLOTS, _DIM))
    _check("router", router, (_BRANCHES, _DIM))

    with torch.no_grad():
        # .to(float64) on a float32 tensor always allocates new storage, so the
        # caller's tensors are never written to.
        q64 = q.detach().to(dtype=torch.float64)
        keys64 = keys.detach().to(dtype=torch.float64, device=q.device)
        router64 = router.detach().to(dtype=torch.float64, device=q.device)

        scores = (q64 @ _unit_rows(keys64).T) / _TEMPERATURE
        if use_prior:
            routes = (q64 @ _unit_rows(router64).T) / _TEMPERATURE
            prior = _log_softmax_rows(routes)
            branch_of_slot = torch.arange(_SLOTS, device=q.device) // _SLOTS_PER_BRANCH
            scores = scores + prior[:, branch_of_slot]

        # Columns are slot IDs in ascending order. A stable descending sort keeps
        # equal scores in their original (ascending-ID) order.
        ordered_scores, order = torch.sort(scores, dim=1, descending=True, stable=True)
        selected_ids = order[:, :_TOP].to(dtype=torch.int64).contiguous()
        boundary_gap = (ordered_scores[:, _TOP - 1] - ordered_scores[:, _TOP]).contiguous()

    if not bool(torch.isfinite(scores).all()):
        raise FloatingPointError("non-finite reference score")
    assert scores.dtype == torch.float64 and boundary_gap.dtype == torch.float64
    return scores, selected_ids, boundary_gap
