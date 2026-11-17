"""Frozen P4 backbone and registered P5 additions."""

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
from .p4_model import Backbone, DenseAdapter
from .p4_model import backbone_digest as backbone_digest
from .p5_config import (
    ADDITION_PARAMETERS,
    BASELINE,
    BATCH,
    CONDITIONS,
    DENSE,
    FIXED,
    FLAT,
    FROZEN_PARAMETERS,
    LEARNED,
    MEMORIES,
    VAL_TARGETS,
    Cell,
)
from .pilot_metrics import RetrievalCounts, loss_for
from .pilot_model import BRANCHES, PER_BRANCH, SLOTS, Memory, PilotModel

ADAMW_OPTIONS = {
    "lr": 0.003,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0,
    "amsgrad": False,
    "maximize": False,
    "foreach": False,
    "capturable": False,
    "differentiable": False,
    "fused": False,
    "decoupled_weight_decay": True,
}


class Model(nn.Module):
    forward = PilotModel.forward

    def __init__(self, cell: Cell, parent: Backbone) -> None:
        super().__init__()
        self.cell = cell
        self.backbone = copy.deepcopy(parent)
        self.addition: Memory | DenseAdapter | None
        if cell.variant in MEMORIES:
            self.addition = Memory(cell.variant, cell.seed)
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


def optimizer_names(model: Model, optimizer: AdamW | None) -> list[str]:
    named = dict(model.named_parameters())
    trainable = [(name, p) for name, p in named.items() if p.requires_grad]
    stored = sum(p.numel() for p in named.values())
    frozen = sum(p.numel() for p in model.backbone.parameters())
    expected_trainable = ADDITION_PARAMETERS[model.cell.variant]
    if (
        frozen != FROZEN_PARAMETERS
        or stored != frozen + expected_trainable
        or sum(p.numel() for _, p in trainable) != expected_trainable
        or any(p.requires_grad or p.grad is not None for p in model.backbone.parameters())
        or any(not name.startswith("addition.") for name, _ in trainable)
    ):
        raise ValueError("P5 backbone freeze or parameter count mismatch")
    if optimizer is None:
        if trainable:
            raise ValueError("P5 trainable cell missing optimizer")
    else:
        if type(optimizer) is not AdamW or len(optimizer.param_groups) != 1:
            raise ValueError("P5 optimizer must be AdamW with one parameter group")
        group = optimizer.param_groups[0]
        options = {key: value for key, value in group.items() if key != "params"}
        if options.keys() != ADAMW_OPTIONS.keys() or any(
            type(options[key]) is not type(expected) or options[key] != expected
            for key, expected in ADAMW_OPTIONS.items()
        ):
            raise ValueError("P5 optimizer hyperparameters differ from registered AdamW")
        actual = [id(p) for p in group["params"]]
        if (
            not trainable
            or actual != [id(p) for _, p in trainable]
            or len(set(actual)) != len(actual)
        ):
            raise ValueError("P5 optimizer membership or order mismatch")
    return [name for name, _ in trainable]


def optimizer_for(model: Model) -> AdamW | None:
    optimizer = (
        None
        if model.cell.variant == BASELINE
        else adamw_for(nn.ParameterList(p for p in model.parameters() if p.requires_grad))
    )
    optimizer_names(model, optimizer)
    return optimizer


def train_step(
    model: Model,
    optimizer: AdamW,
    batch: Tensor,
    step: int,
) -> tuple[float, float, float | None]:
    optimizer.zero_grad(set_to_none=True)
    logits, lookup = model(batch[:, :-1])
    loss = loss_for(logits, batch[:, 1:], "mean")
    if not math.isfinite(loss.item()):
        raise ValueError(f"P5 non-finite loss at step {step}")
    loss.backward()  # type: ignore[no-untyped-call]
    names = optimizer_names(model, optimizer)
    params = [dict(model.named_parameters())[name] for name in names]
    if not params or any(p.grad is None for p in params):
        raise ValueError(f"P5 missing addition gradients at step {step}")
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
            raise ValueError(f"P5 missing or invalid routing at step {step}")
        router_norm = float(torch.linalg.vector_norm(router.grad))
        if not math.isfinite(router_norm):
            raise ValueError(f"P5 non-finite router gradient norm at step {step}")
    elif model.cell.variant in (FLAT, FIXED):
        if (
            lookup is None
            or (lookup.branch_ids is None) != (model.cell.variant == FLAT)
            or (lookup.route_scores is None) != (model.cell.variant == FLAT)
            or (lookup.route_scores is not None and not bool(lookup.route_scores.isfinite().all()))
        ):
            raise ValueError("P5 retrieval structure mismatch")
    elif lookup is not None:
        raise ValueError("P5 dense addition returned retrieval")
    norm = nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
    optimizer.step()
    if not all(bool(p.isfinite().all()) for p in params):
        raise ValueError(f"P5 non-finite parameter at step {step}")
    return loss.item(), norm.item(), router_norm


def evaluate(
    model: Model,
    data: Tensor,
    expected_targets: int = VAL_TARGETS,
) -> dict[str, Any]:
    tracker = RetrievalCounts(model.cell.variant) if isinstance(model.memory, Memory) else None
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
                        or (lookup.branch_ids is None) != (model.cell.variant == FLAT)
                        or (lookup.route_scores is None) != (model.cell.variant == FLAT)
                        or (
                            lookup.route_scores is not None
                            and not bool(lookup.route_scores.isfinite().all())
                        )
                    ):
                        raise ValueError("P5 missing or invalid evaluation routing")
                    tracker.update(lookup)
                elif lookup is not None:
                    raise ValueError("P5 non-memory evaluation returned retrieval")
    finally:
        model.train(was_training)
    if count != expected_targets or count <= 0 or not math.isfinite(total):
        raise ValueError("P5 wrong validation count or non-finite loss")
    nll = total / count
    try:
        perplexity = math.exp(nll)
    except OverflowError as exc:
        raise ValueError("P5 validation perplexity is non-finite") from exc
    retrieval = tracker.report() if tracker is not None else None
    if retrieval is not None and tracker is not None:
        observed = tracker.selected.double()
        probabilities = observed[observed > 0] / observed.sum()
        entropy = float(-(probabilities * probabilities.log()).sum())
        retrieval["selected_slot_entropy_normalized"] = entropy / math.log(SLOTS)
        retrieval["effective_selected_slots"] = math.exp(entropy)
    return {
        "nll": nll,
        "nll_units": "nats_per_byte",
        "byte_perplexity": perplexity,
        "target_tokens": count,
        "retrieval": retrieval,
    }


def intervene(model: Model, condition: str) -> tuple[Tensor, int] | None:
    if (
        condition not in CONDITIONS
        or (model.cell.variant == BASELINE and condition != "enabled")
        or (model.cell.variant == DENSE and condition not in ("enabled", "disabled"))
    ):
        raise ValueError("unregistered P5 intervention")
    if condition == "enabled":
        return None
    if condition == "disabled":
        model.bypass = True
        return None
    if not isinstance(model.addition, Memory):
        raise ValueError("P5 permutation requires memory")
    generator = torch.Generator(device="cpu")
    if condition == "values_permuted":
        seed = 60000 + model.cell.index
        ids = torch.randperm(SLOTS, generator=generator.manual_seed(seed), device="cpu")
    else:
        seed = 70000 + model.cell.index
        generator.manual_seed(seed)
        if model.cell.variant == FLAT:
            ids = torch.randperm(SLOTS, generator=generator, device="cpu")
        else:
            ids = torch.cat(
                [
                    branch * PER_BRANCH
                    + torch.randperm(PER_BRANCH, generator=generator, device="cpu")
                    for branch in range(BRANCHES)
                ]
            )
    with torch.no_grad():
        if condition == "joint_within_branch":
            model.addition.keys.copy_(model.addition.keys[ids])
        model.addition.values.copy_(model.addition.values[ids])
    return ids, seed


def insertion_hidden(model: Model, tokens: Tensor) -> Tensor:
    t = tokens.shape[1]
    h = model.token(tokens) + model.position(torch.arange(t, device="cpu"))
    return model.blocks[0](h, model.mask[:t, :t])  # type: ignore[no-any-return]


def normalized_query(memory: Memory, h: Tensor) -> Tensor:
    return F.normalize(F.linear(h, memory.wq), dim=-1, eps=1e-8).reshape(-1, 16)


def logical_work(variant: str) -> dict[str, int | float | None]:
    if variant == BASELINE:
        return {"state_fraction": None, "trainable_fraction": None}
    if variant == DENSE:
        return {
            "dense_matrix_multiplies_per_query": 2,
            "state_fraction": 1.0,
            "trainable_fraction": 1.0,
        }
    tree = variant != FLAT
    dots, router = (512, 16) if tree else (4096, 0)
    consulted = 1537 + 256 + (dots + router) * 16
    state = ADDITION_PARAMETERS[variant] + (256 if variant == FIXED else 0)
    return {
        "key_dot_products": dots,
        "router_dot_products": router,
        "candidate_key_elements": dots * 16,
        "router_elements": router * 16,
        "selected_value_elements": 256,
        "common_elements": 1537,
        "consulted_state_elements": consulted,
        "addition_state_elements": state,
        "state_fraction": consulted / state,
        "trainable_fraction": (consulted - (256 if variant == FIXED else 0))
        / ADDITION_PARAMETERS[variant],
    }


def state_digest(model: Model) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted([*model.named_parameters(), *model.named_buffers()]):
        digest.update(
            canonical_json(
                {
                    "name": name,
                    "shape": list(tensor.shape),
                    "dtype": str(tensor.dtype),
                    "requires_grad": tensor.requires_grad,
                }
            )
        )
        digest.update(bytes(tensor.detach().contiguous().reshape(-1).view(torch.uint8).tolist()))
    digest.update(canonical_json({"bypass": model.bypass}))
    return digest.hexdigest()
