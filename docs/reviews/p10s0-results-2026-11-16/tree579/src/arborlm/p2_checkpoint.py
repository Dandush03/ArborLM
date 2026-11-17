"""Separate P2 atomic checkpoint schema with strict run and order identity."""

import hashlib
import random
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW

from .checkpoint import _dict_with_fields, _same_tensor, _validate_optimizer, publish_state
from .io import read_json
from .p2_config import BATCH, CHECKPOINT_STEPS, CONTEXT, FAMILY, SCHEMA, SPEC
from .p2_model import FollowupModel
from .pilot_checkpoint import components

# Full-model slot/router metadata is identical to P1; P2 adds bypass/freeze identity.
_FIELDS = {
    "family",
    "schema_version",
    "spec_reference",
    "identity",
    "components",
    "model",
    "optimizer",
    "python_rng",
    "torch_rng",
    "completed_step",
    "next_order_cursor",
    "train_tokens",
    "requires_grad",
    "bypass",
}


def _validate_identity(model: FollowupModel, identity: dict[str, Any]) -> None:
    if identity["cell"] != model.cell.fields():
        raise ValueError("P2 checkpoint factor identity mismatch")


def save(
    path: Path,
    model: FollowupModel,
    optimizer: AdamW,
    step: int,
    identity: dict[str, Any],
) -> str:
    _validate_identity(model, identity)
    if step not in CHECKPOINT_STEPS:
        raise ValueError("unregistered P2 checkpoint step")
    return publish_state(
        path,
        {
            "family": FAMILY,
            "schema_version": SCHEMA,
            "spec_reference": SPEC,
            "identity": identity,
            "components": components("learned_tree"),
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "python_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "completed_step": step,
            "next_order_cursor": step * BATCH,
            "train_tokens": step * BATCH * CONTEXT,
            "requires_grad": {name: p.requires_grad for name, p in model.named_parameters()},
            "bypass": model.bypass,
        },
        schema=SCHEMA,
    )


def restore(
    path: Path,
    model: FollowupModel,
    optimizer: AdamW,
    identity: dict[str, Any],
) -> tuple[int, int, int]:
    _validate_identity(model, identity)
    index = _dict_with_fields(
        read_json(path / "index.json"), {"schema_version", "state_sha256"}, "P2 checkpoint index"
    )
    if type(index["schema_version"]) is not int or index["schema_version"] != SCHEMA:
        raise ValueError("unknown P2 checkpoint index version")
    with (path / "state.pt").open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("P2 checkpoint checksum mismatch")
        stream.seek(0)
        state = _dict_with_fields(
            torch.load(stream, map_location="cpu", weights_only=True), _FIELDS, "P2 checkpoint"
        )
    flags = {name: p.requires_grad for name, p in model.named_parameters()}
    if (
        state["family"] != FAMILY
        or type(state["schema_version"]) is not int
        or state["schema_version"] != SCHEMA
        or state["spec_reference"] != SPEC
        or state["identity"] != identity
        or state["components"] != components("learned_tree")
        or state["requires_grad"] != flags
        or state["bypass"] is not model.bypass
    ):
        raise ValueError(
            "P2 checkpoint condition/schema/config/data/order/source identity mismatch"
        )
    step, cursor, tokens = (
        state["completed_step"],
        state["next_order_cursor"],
        state["train_tokens"],
    )
    if (
        type(step) is not int
        or step not in CHECKPOINT_STEPS
        or type(cursor) is not int
        or cursor != step * BATCH
        or type(tokens) is not int
        or tokens != cursor * CONTEXT
    ):
        raise ValueError("P2 checkpoint counter mismatch")
    expected = model.state_dict()
    tensors = _dict_with_fields(state["model"], set(expected), "P2 model")
    for name, value in expected.items():
        if not _same_tensor(tensors[name], value):
            raise ValueError(f"P2 invalid model tensor: {name}")
        if not flags[name] and not torch.equal(tensors[name], value):
            raise ValueError(f"P2 frozen model tensor mutated: {name}")
    trainable = nn.ParameterList(p for p in model.parameters() if p.requires_grad)
    _validate_optimizer(state["optimizer"], trainable, optimizer, step)
    random.Random(0).setstate(state["python_rng"])
    if not _same_tensor(state["torch_rng"], torch.get_rng_state()):
        raise ValueError("invalid P2 torch RNG")
    torch.Generator(device="cpu").set_state(state["torch_rng"])
    model.load_state_dict(tensors, strict=True)
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    return step, cursor, tokens
