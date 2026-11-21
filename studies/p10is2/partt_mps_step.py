# ruff: noqa: E501
"""P10-I-S2 Part T, gate G4-MPS: the optimiser-step comparison (ruling 43; audit 8, finding 3).

The amended G4-MPS (ruling 39) compares losses and the gradient at identical parameters, so it no longer
covers gradient clipping or the AdamW step on MPS. This module restores that coverage without the
conditioning that made the old 20-update parameter figure meaningless: CPU and the device are given the
SAME parameters, the SAME gradients (the CPU's, copied) and, where a step needs one, the SAME AdamW state,
and take one ``clip_grad_norm_`` plus ``AdamW.step`` each. The two updates (new parameters minus old) are
compared tensor by tensor with the already registered gradient tolerance, relative, with the exact-zero
clause (``compare_gradients``). No new tolerance is introduced: the figure is
``gates.mps_gradient_relative_tolerance`` (1e-3, ruling 39, ADR-0025 addendum ``g4-mps-amendment``),
applied to the relative norm difference of the two UPDATES (relative to the step size, not to the
parameter norm).

Three steps per tensor set: (1) a fresh optimiser on the CPU gradient of batch 0; (2) the optimiser state
left by step 1 on CPU, copied to the device, and the CPU gradient of batch 1; (3) the same carried state and
the batch-0 gradient scaled to four times ``clip_norm`` (clipping is active).

Clipping is also compared DIRECTLY (ruling 43 as amended in ``ADR-0025-addendum-part-t-rulings-12.md``): ``clipped_gradients``
returns the gradients after ``clip_grad_norm_`` for the batch-0 gradient scaled to 0.5, 1.01 and 4 times
``clip_norm`` (inactive, barely active, active) on CPU and on the device, compared with the same registered
tolerance and the exact-zero clause. The update comparison alone cannot see a wrong clip when the gradient
dwarfs the carried state (Adam's step is then nearly scale-free; on the real cell the key and value
gradients are exactly zero at update 1), the clipped gradients themselves can.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import torch

StepFn = Callable[..., list[list[torch.Tensor]]]


def step_updates(
    params0: Sequence[torch.Tensor],
    grads: Sequence[Sequence[torch.Tensor]],
    dev: torch.device,
    *,
    lr: float,
    weight_decay: float,
    clip: float,
    state_from_cpu: bool = True,
) -> list[list[torch.Tensor]]:
    """The updates of the three steps on ``dev`` (float64 CPU tensors, one list per step, one tensor per
    parameter). ``grads`` holds the gradients of steps 1 and 2 (CPU tensors); step 3 reuses ``grads[0]``
    scaled to four times ``clip``. Step 2's AdamW state is the CPU optimiser's state after step 1
    (``state_from_cpu``), so the state is identical on both devices."""

    def leaves(values: Sequence[torch.Tensor], where: torch.device = dev) -> list[torch.Tensor]:
        return [v.detach().clone().to(where).requires_grad_(True) for v in values]

    def run(q: list[torch.Tensor], g: Sequence[torch.Tensor], opt: torch.optim.AdamW) -> list[torch.Tensor]:
        before = [p.detach().cpu().double().clone() for p in q]
        for p, gi in zip(q, g, strict=True):
            p.grad = gi.detach().clone().to(dev)
        torch.nn.utils.clip_grad_norm_(q, clip)
        opt.step()
        return [p.detach().cpu().double() - b for p, b in zip(q, before, strict=True)]

    out: list[list[torch.Tensor]] = []
    q1 = leaves(params0)
    opt1 = torch.optim.AdamW(q1, lr=lr, weight_decay=weight_decay)
    out.append(run(q1, grads[0], opt1))
    # step 2: parameters and optimiser state after step 1, taken from the CPU reference so both devices start from the same state
    cpu_q = leaves(params0, torch.device("cpu"))
    cpu_opt = torch.optim.AdamW(cpu_q, lr=lr, weight_decay=weight_decay)
    for p, gi in zip(cpu_q, grads[0], strict=True):
        p.grad = gi.detach().clone()
    torch.nn.utils.clip_grad_norm_(cpu_q, clip)
    cpu_opt.step()
    after1 = [p.detach().cpu().clone() for p in cpu_q]
    q2 = leaves(after1)  # on the device under test
    opt2 = torch.optim.AdamW(q2, lr=lr, weight_decay=weight_decay)
    if state_from_cpu:
        opt2.load_state_dict(copy.deepcopy(cpu_opt.state_dict()))  # a copy: loading on the same device would otherwise share (and step in place) the moment tensors
    out.append(run(q2, grads[1], opt2))
    # step 3: clipping active
    norm = float(torch.stack([(g.double() ** 2).sum() for g in grads[0]]).sum().sqrt())
    scale = (4.0 * clip / norm) if norm > 0.0 else 1.0
    q3 = leaves(params0)
    opt3 = torch.optim.AdamW(q3, lr=lr, weight_decay=weight_decay)
    if state_from_cpu:
        opt3.load_state_dict(copy.deepcopy(cpu_opt.state_dict()))  # the carried state of step 1, so the clip factor does not cancel in a first step
    out.append(run(q3, [g * scale for g in grads[0]], opt3))
    return out


CLIP_CASES = (0.5, 1.01, 4.0)  # the batch-0 gradient's norm as a multiple of clip_norm: inactive, barely active, active


def clipped_gradients(grads: Sequence[Sequence[torch.Tensor]], dev: torch.device, *, clip: float) -> list[list[torch.Tensor]]:
    """The gradients AFTER ``clip_grad_norm_`` on ``dev`` (float64 CPU tensors), for the batch-0 gradient scaled to each of ``CLIP_CASES`` times ``clip``: one list per case, one tensor per parameter."""
    norm = float(torch.stack([(g.double() ** 2).sum() for g in grads[0]]).sum().sqrt())
    out: list[list[torch.Tensor]] = []
    for mult in CLIP_CASES:
        scale = (mult * clip / norm) if norm > 0.0 else 1.0
        q = [g.detach().clone().to(dev).requires_grad_(True) for g in grads[0]]
        for p, g in zip(q, grads[0], strict=True):
            p.grad = (g * scale).detach().clone().to(dev)
        torch.nn.utils.clip_grad_norm_(q, clip)
        out.append([p.grad.detach().cpu().double().clone() for p in q if p.grad is not None])
    return out


def compare_steps(
    params0: Sequence[torch.Tensor],
    grads: Sequence[Sequence[torch.Tensor]],
    names: Sequence[str],
    t: Mapping[str, Any],
    dev: torch.device,
    *,
    lr: float,
    weight_decay: float,
    clip: float,
    other_step: StepFn | None = None,
    device_clip: float | None = None,
) -> dict[str, Any]:
    """CPU against ``dev`` (or against ``other_step``, which a test replaces to plant a divergence; ``device_clip``
    plants a wrong clip norm on the device side only, ``1e30`` being a missing clip): the three updates and the
    clipped gradients of ``CLIP_CASES``, each compared with ``compare_gradients`` (relative,
    ``mps_gradient_relative_tolerance``, exact-zero clause). ``passed`` is both conditions."""
    from .partt_gates import compare_gradients

    kw: dict[str, Any] = {"lr": lr, "weight_decay": weight_decay, "clip": clip}
    dkw = {**kw, "clip": clip if device_clip is None else device_clip}
    ref = step_updates(params0, grads, torch.device("cpu"), **kw)
    got = (other_step or step_updates)(params0, grads, dev, **dkw)
    res = compare_gradients(ref, got, names, t)
    cgrad = compare_gradients(clipped_gradients(grads, torch.device("cpu"), clip=clip), clipped_gradients(grads, dev, clip=dkw["clip"]), names, t)
    res["clipped_gradient_agreement"] = {**cgrad, "cases_times_clip_norm": list(CLIP_CASES)}
    res["update_passed"] = bool(res["passed"])
    res["passed"] = bool(res["passed"] and cgrad["passed"])
    res["steps"] = ["fresh optimiser, batch-0 gradient", "optimiser state of step 1 copied, batch-1 gradient", "carried state, clipping active (gradient at 4 x clip_norm)"]
    res["clip_norm"] = clip
    res["lr"] = lr
    return res
