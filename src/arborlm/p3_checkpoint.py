"""Atomic P3 snapshots and exact zero-update conversion from a P2 parent."""

import hashlib
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW

from .checkpoint import _dict_with_fields, _same_tensor, _validate_optimizer, publish_state
from .io import file_sha256, read_json
from .optimization_followup import _optimizer
from .p2_checkpoint import restore as restore_p2
from .p2_model import FollowupModel
from .p3_config import DURATIONS, FAMILY, SCHEMA, SPEC, START, counters
from .pilot_checkpoint import components

FIELDS = {
    "family",
    "schema_version",
    "spec_reference",
    "identity",
    "components",
    "model",
    "optimizer",
    "python_rng",
    "torch_rng",
    "counters",
    "requires_grad",
    "bypass",
    "zero_training_conversion",
}


def _flags(model: FollowupModel) -> dict[str, bool]:
    return {name: param.requires_grad for name, param in model.named_parameters()}


def save(
    path: Path,
    model: FollowupModel,
    optimizer: AdamW,
    step: int,
    identity: dict[str, Any],
) -> str:
    if step not in DURATIONS or identity["cell"] != model.cell.fields():
        raise ValueError("wrong P3 checkpoint step/cell")
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
            "counters": counters(step),
            "requires_grad": _flags(model),
            "bypass": model.bypass,
            "zero_training_conversion": step == START,
        },
        schema=SCHEMA,
    )


def restore(
    path: Path,
    model: FollowupModel,
    optimizer: AdamW,
    identity: dict[str, Any],
) -> dict[str, int]:
    index = _dict_with_fields(
        read_json(path / "index.json"), {"schema_version", "state_sha256"}, "P3 checkpoint index"
    )
    if type(index["schema_version"]) is not int or index["schema_version"] != SCHEMA:
        raise ValueError("unknown P3 index schema")
    with (path / "state.pt").open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("P3 checkpoint checksum mismatch")
        stream.seek(0)
        state = _dict_with_fields(
            torch.load(stream, weights_only=True, map_location="cpu"), FIELDS, "P3 checkpoint"
        )
    flags = _flags(model)
    if (
        state["family"] != FAMILY
        or type(state["schema_version"]) is not int
        or state["schema_version"] != SCHEMA
        or state["spec_reference"] != SPEC
        or state["identity"] != identity
        or identity["cell"] != model.cell.fields()
        or state["components"] != components("learned_tree")
        or state["requires_grad"] != flags
        or state["bypass"] is not model.bypass
    ):
        raise ValueError(
            "P3 checkpoint schema/cell/config/data/order/source/parent identity mismatch"
        )
    stored = state["counters"]
    step = stored["completed_step"]
    if (
        type(step) is not int
        or step not in DURATIONS
        or stored != counters(step)
        or any(type(value) is not int for value in stored.values())
        or state["zero_training_conversion"] is not (step == START)
    ):
        raise ValueError("P3 checkpoint duration/cursor counters mismatch")
    expected = model.state_dict()
    tensors = _dict_with_fields(state["model"], set(expected), "P3 model")
    for name, value in expected.items():
        if not _same_tensor(tensors[name], value):
            raise ValueError(f"P3 invalid model tensor: {name}")
        if not flags[name] and not bitwise_equal(tensors[name], value):
            raise ValueError(f"P3 frozen model tensor changed: {name}")
    trainable = nn.ParameterList(p for p in model.parameters() if p.requires_grad)
    _validate_optimizer(state["optimizer"], trainable, optimizer, step)
    random.Random(0).setstate(state["python_rng"])
    if not _same_tensor(state["torch_rng"], torch.get_rng_state()):
        raise ValueError("invalid P3 torch RNG")
    torch.Generator(device="cpu").set_state(state["torch_rng"])
    model.load_state_dict(tensors, strict=True)
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    return counters(step)


def bitwise_equal(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(
            bitwise_equal(value, right[key]) for key, value in left.items()
        )
    if type(left) is not type(right):
        return False
    if isinstance(left, torch.Tensor):
        return bool(
            left.shape == right.shape
            and left.dtype == right.dtype
            and torch.equal(
                left.contiguous().reshape(-1).view(torch.uint8),
                right.contiguous().reshape(-1).view(torch.uint8),
            )
        )
    if isinstance(left, list | tuple):
        return len(left) == len(right) and all(
            bitwise_equal(x, y) for x, y in zip(left, right, strict=True)
        )
    return bool(left == right)


def convert(
    parent: Path,
    parent_identity: dict[str, Any],
    path: Path,
    model: FollowupModel,
    optimizer: AdamW,
    identity: dict[str, Any],
) -> str:
    before = (file_sha256(parent / "state.pt"), file_sha256(parent / "index.json"))
    if restore_p2(parent, model, optimizer, parent_identity) != (START, 2048, 131072):
        raise ValueError("P3 requires a final P2 checkpoint")
    python_rng, torch_rng = random.getstate(), torch.get_rng_state()
    digest = save(path, model, optimizer, START, identity)
    clone = FollowupModel(model.cell)
    clone_opt = _optimizer(clone)
    if (
        restore(path, clone, clone_opt, identity) != counters(START)
        or not bitwise_equal(model.state_dict(), clone.state_dict())
        or not bitwise_equal(optimizer.state_dict(), clone_opt.state_dict())
        or not bitwise_equal(python_rng, random.getstate())
        or not bitwise_equal(torch_rng, torch.get_rng_state())
        or before != (file_sha256(parent / "state.pt"), file_sha256(parent / "index.json"))
    ):
        raise ValueError("P3 zero-training conversion did not preserve the P2 parent state")
    return digest
