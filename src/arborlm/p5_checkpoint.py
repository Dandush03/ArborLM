"""Strict P5 checkpoints with immutable frozen-backbone verification."""

import hashlib
import random
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW

from .checkpoint import _dict_with_fields, _same_tensor, _validate_optimizer, publish_state
from .io import read_json
from .p3_checkpoint import bitwise_equal
from .p5_config import BASELINE, CHECKPOINT_STEPS, DENSE, FAMILY, FIXED, SCHEMA, SPEC, counters
from .p5_model import Model, backbone_digest, optimizer_names
from .pilot_checkpoint import components

FIELDS = {
    "family",
    "schema_version",
    "spec_reference",
    "identity",
    "components",
    "model",
    "optimizer",
    "optimizer_parameter_names",
    "python_rng",
    "torch_rng",
    "counters",
    "requires_grad",
    "bypass",
}


def _components(model: Model) -> dict[str, Any]:
    if model.cell.variant == BASELINE:
        return {"backbone": "P3-extracted-frozen-v1", "addition": None}
    if model.cell.variant == DENSE:
        return {"backbone": "P3-extracted-frozen-v1", "addition": "dense-gelu-3100-v1"}
    return {"backbone": "P3-extracted-frozen-v1", "addition": components(model.cell.variant)}


def _validate(model: Model, identity: dict[str, Any], step: int) -> None:
    if (
        identity["cell"] != model.cell.fields()
        or identity["backbone_sha256"] != backbone_digest(model.backbone)
        or model.bypass is not (model.cell.variant == BASELINE)
        or type(step) is not int
        or step not in CHECKPOINT_STEPS
        or (model.cell.variant == BASELINE and step != 0)
    ):
        raise ValueError("P5 checkpoint cell/step/bypass/frozen-backbone mismatch")


def save(
    path: Path,
    model: Model,
    optimizer: AdamW | None,
    step: int,
    identity: dict[str, Any],
) -> str:
    _validate(model, identity, step)
    return publish_state(
        path,
        {
            "family": FAMILY,
            "schema_version": SCHEMA,
            "spec_reference": SPEC,
            "identity": identity,
            "components": _components(model),
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict() if optimizer else None,
            "optimizer_parameter_names": optimizer_names(model, optimizer),
            "python_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "counters": counters(step),
            "requires_grad": {
                name: param.requires_grad for name, param in model.named_parameters()
            },
            "bypass": model.bypass,
        },
        schema=SCHEMA,
    )


def restore(
    path: Path,
    model: Model,
    optimizer: AdamW | None,
    identity: dict[str, Any],
) -> dict[str, int]:
    index = _dict_with_fields(
        read_json(path / "index.json"), {"schema_version", "state_sha256"}, "P5 checkpoint index"
    )
    if type(index["schema_version"]) is not int or index["schema_version"] != SCHEMA:
        raise ValueError("unknown P5 index schema")
    with (path / "state.pt").open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("P5 checkpoint checksum mismatch")
        stream.seek(0)
        state = _dict_with_fields(
            torch.load(stream, weights_only=True, map_location="cpu"), FIELDS, "P5 checkpoint"
        )
    names = optimizer_names(model, optimizer)
    flags = {name: p.requires_grad for name, p in model.named_parameters()}
    if (
        state["family"] != FAMILY
        or type(state["schema_version"]) is not int
        or state["schema_version"] != SCHEMA
        or state["spec_reference"] != SPEC
        or state["identity"] != identity
        or state["components"] != _components(model)
        or state["optimizer_parameter_names"] != names
        or state["requires_grad"] != flags
        or state["bypass"] is not model.bypass
    ):
        raise ValueError("P5 checkpoint schema/identity/optimizer membership mismatch")
    stored = state["counters"]
    step = stored["additional_step"]
    _validate(model, identity, step)
    if stored != counters(step) or any(type(value) is not int for value in stored.values()):
        raise ValueError("P5 checkpoint counters mismatch")
    expected = model.state_dict()
    tensors = _dict_with_fields(state["model"], set(expected), "P5 model")
    for name, tensor in expected.items():
        if not _same_tensor(tensors[name], tensor):
            raise ValueError(f"P5 invalid model tensor: {name}")
        if (
            name.startswith("backbone.")
            or (model.cell.variant == FIXED and name == "addition.router")
        ) and not bitwise_equal(tensors[name], tensor):
            raise ValueError(f"P5 frozen backbone tensor changed: {name}")
    if optimizer is None:
        if state["optimizer"] is not None:
            raise ValueError("baseline P5 checkpoint contains optimizer")
    elif step == 0:
        if state["optimizer"] != optimizer.state_dict() or state["optimizer"]["state"]:
            raise ValueError("step-zero P5 optimizer is not fresh")
    else:
        _validate_optimizer(
            state["optimizer"],
            nn.ParameterList(p for p in model.parameters() if p.requires_grad),
            optimizer,
            step,
        )
    random.Random(0).setstate(state["python_rng"])
    if not _same_tensor(state["torch_rng"], torch.get_rng_state()):
        raise ValueError("invalid P5 torch RNG")
    torch.Generator(device="cpu").set_state(state["torch_rng"])
    model.load_state_dict(tensors, strict=True)
    if optimizer is not None:
        optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    return counters(step)
