"""Frozen P3 backbone and registered, separately trained P4 additions."""

import copy
import hashlib
import math
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch.optim import AdamW

from .engine import optimizer_for as adamw_for
from .io import canonical_json
from .longer_training import _isolated_rng
from .p2_model import FollowupModel
from .p4_config import (
    ADDITION_PARAMETERS,
    BASELINE,
    BATCH,
    CONDITIONS,
    DENSE,
    FROZEN_PARAMETERS,
    MEMORY,
    VAL_TARGETS,
    Cell,
)
from .pilot_metrics import RetrievalCounts, loss_for
from .pilot_model import BRANCHES, PER_BRANCH, SLOTS, Memory, PilotModel, _matrix


class Backbone(nn.Module):
    mask: Tensor

    def __init__(self, parent: FollowupModel) -> None:
        super().__init__()
        # Copy existing components without calling any initializer.
        self.token = copy.deepcopy(parent.token)
        self.position = copy.deepcopy(parent.position)
        self.blocks = copy.deepcopy(parent.blocks)
        self.final_norm = copy.deepcopy(parent.final_norm)
        self.register_buffer("mask", parent.mask.detach().clone(), persistent=False)
        self.requires_grad_(False)
        self.zero_grad(set_to_none=True)


def extract(parent: FollowupModel) -> Backbone:
    if not parent.bypass:
        raise ValueError("P4 requires a bypassed control parent")
    return Backbone(parent)


def backbone_digest(backbone: Backbone) -> str:
    """Canonical names, shapes, dtypes, and contiguous tensor bytes."""
    digest = hashlib.sha256()
    tensors = sorted([*backbone.named_parameters(), *backbone.named_buffers()])
    for name, tensor in tensors:
        digest.update(
            canonical_json(
                {
                    "name": name,
                    "shape": list(tensor.shape),
                    "dtype": str(tensor.dtype),
                }
            )
        )
        raw = tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
        digest.update(bytes(raw.tolist()))
    return digest.hexdigest()


class DenseAdapter(nn.Module):
    def __init__(self, seed: int) -> None:
        super().__init__()
        self.w1 = nn.Parameter(_matrix(seed + 3000, 3100, 32))
        self.w2 = nn.Parameter(_matrix(seed + 4000, 32, 3100))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32, device="cpu"))

    def forward(self, h: Tensor) -> tuple[Tensor, None]:
        return h + self.gate.sigmoid() * F.linear(
            F.gelu(F.linear(h, self.w1), approximate="none"), self.w2
        ), None


class FrozenModel(nn.Module):
    forward = PilotModel.forward

    def __init__(self, cell: Cell, parent: FollowupModel | Backbone) -> None:
        super().__init__()
        self.cell = cell
        self.backbone = (
            extract(parent) if isinstance(parent, FollowupModel) else copy.deepcopy(parent)
        )
        self.addition: Memory | DenseAdapter | None
        if cell.variant == MEMORY:
            self.addition = Memory("learned_tree", cell.seed)
        elif cell.variant == DENSE:
            self.addition = DenseAdapter(cell.seed)
        else:
            self.addition = None
        self.bypass = cell.variant == BASELINE

    @property
    def token(self) -> nn.Embedding:
        return self.backbone.token

    @property
    def position(self) -> nn.Embedding:
        return self.backbone.position

    @property
    def blocks(self) -> nn.ModuleList:
        return self.backbone.blocks

    @property
    def final_norm(self) -> nn.LayerNorm:
        return self.backbone.final_norm

    @property
    def mask(self) -> Tensor:
        return self.backbone.mask

    @property
    def memory(self) -> Memory | DenseAdapter | None:
        # The original forward uses this hook for either addition. Evaluation
        # explicitly distinguishes dense addition from sparse routing.
        return None if self.bypass else self.addition


def optimizer_names(model: FrozenModel, optimizer: AdamW | None) -> list[str]:
    named = dict(model.named_parameters())
    trainable = [(name, p) for name, p in named.items() if p.requires_grad]
    stored = sum(p.numel() for p in named.values())
    frozen = sum(p.numel() for p in model.backbone.parameters())
    expected_trainable = 0 if model.cell.variant == BASELINE else ADDITION_PARAMETERS
    if (
        frozen != FROZEN_PARAMETERS
        or stored != frozen + expected_trainable
        or sum(p.numel() for _, p in trainable) != expected_trainable
        or any(p.requires_grad or p.grad is not None for p in model.backbone.parameters())
        or any(not name.startswith("addition.") for name, _ in trainable)
    ):
        raise ValueError("P4 backbone freeze or parameter count mismatch")
    if optimizer is None:
        if trainable:
            raise ValueError("P4 trainable cell missing optimizer")
    else:
        actual = [id(p) for group in optimizer.param_groups for p in group["params"]]
        if (
            not trainable
            or actual != [id(p) for _, p in trainable]
            or len(set(actual)) != len(actual)
        ):
            raise ValueError("P4 optimizer membership or order mismatch")
    return [name for name, _ in trainable]


def optimizer_for(model: FrozenModel) -> AdamW | None:
    optimizer = (
        None
        if model.cell.variant == BASELINE
        else adamw_for(nn.ParameterList(p for p in model.parameters() if p.requires_grad))
    )
    optimizer_names(model, optimizer)
    return optimizer


def train_step(
    model: FrozenModel,
    optimizer: AdamW,
    batch: Tensor,
    step: int,
) -> tuple[float, float, float | None]:
    optimizer.zero_grad(set_to_none=True)
    logits, lookup = model(batch[:, :-1])
    loss = loss_for(logits, batch[:, 1:], "mean")
    if not math.isfinite(loss.item()):
        raise ValueError(f"P4 non-finite loss at step {step}")
    loss.backward()  # type: ignore[no-untyped-call]
    names = optimizer_names(model, optimizer)
    params = [dict(model.named_parameters())[name] for name in names]
    if not params or any(p.grad is None for p in params):
        raise ValueError(f"P4 missing addition gradients at step {step}")
    router_norm = None
    if isinstance(model.addition, Memory):
        router = model.addition.router
        if (
            router.grad is None
            or lookup is None
            or lookup.branch_ids is None
            or lookup.route_scores is None
            or not bool(lookup.route_scores.isfinite().all())
        ):
            raise ValueError(f"P4 missing or invalid routing at step {step}")
        router_norm = float(torch.linalg.vector_norm(router.grad))
    elif lookup is not None:
        raise ValueError("P4 dense addition returned retrieval")
    norm = nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
    optimizer.step()
    if not all(bool(p.isfinite().all()) for p in params):
        raise ValueError(f"P4 non-finite parameter at step {step}")
    return loss.item(), norm.item(), router_norm


def evaluate(
    model: FrozenModel,
    data: Tensor,
    expected_targets: int = VAL_TARGETS,
) -> dict[str, Any]:
    tracker = RetrievalCounts("learned_tree") if isinstance(model.memory, Memory) else None
    was_training = model.training
    model.eval()
    total, count = 0.0, 0
    try:
        with _isolated_rng(), torch.no_grad():
            for start in range(0, data.shape[0], BATCH):
                batch = data[start : start + BATCH]
                logits, lookup = model(batch[:, :-1])
                total += float(loss_for(logits, batch[:, 1:], "sum"))
                count += batch[:, 1:].numel()
                if tracker is not None:
                    if (
                        lookup is None
                        or lookup.branch_ids is None
                        or lookup.route_scores is None
                        or not bool(lookup.route_scores.isfinite().all())
                    ):
                        raise ValueError("P4 missing or invalid evaluation routing")
                    tracker.update(lookup)
                elif lookup is not None:
                    raise ValueError("P4 non-memory evaluation returned retrieval")
    finally:
        model.train(was_training)
    if count != expected_targets or count <= 0 or not math.isfinite(total):
        raise ValueError("P4 wrong validation count or non-finite loss")
    nll = total / count
    try:
        perplexity = math.exp(nll)
    except OverflowError as exc:
        raise ValueError("P4 validation perplexity is non-finite") from exc
    return {
        "nll": nll,
        "nll_units": "nats_per_byte",
        "byte_perplexity": perplexity,
        "target_tokens": count,
        "retrieval": tracker.report() if tracker is not None else None,
    }


def intervene(model: FrozenModel, condition: str) -> tuple[Tensor, int] | None:
    if (
        condition not in CONDITIONS
        or (model.cell.variant == BASELINE and condition != "enabled")
        or (model.cell.variant == DENSE and condition not in ("enabled", "disabled"))
    ):
        raise ValueError("unregistered P4 intervention")
    if condition == "enabled":
        return None
    if condition == "disabled":
        model.bypass = True
        return None
    if not isinstance(model.addition, Memory):
        raise ValueError("P4 permutation requires memory")
    generator = torch.Generator(device="cpu")
    if condition == "values_permuted":
        seed = 40000 + model.cell.index
        ids = torch.randperm(SLOTS, generator=generator.manual_seed(seed), device="cpu")
    else:
        seed = 50000 + model.cell.index
        generator.manual_seed(seed)
        ids = torch.cat(
            [
                branch * PER_BRANCH + torch.randperm(PER_BRANCH, generator=generator, device="cpu")
                for branch in range(BRANCHES)
            ]
        )
    with torch.no_grad():
        if condition == "joint_within_branch":
            model.addition.keys.copy_(model.addition.keys[ids])
        model.addition.values.copy_(model.addition.values[ids])
    return ids, seed
