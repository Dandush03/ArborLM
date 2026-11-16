"""Immutable pilot checkpoint with a versioned, variant-specific state contract."""

import hashlib
import random
from pathlib import Path
from typing import Any

import torch
from torch.optim import AdamW

from .checkpoint import _dict_with_fields, _same_tensor, _validate_optimizer, publish_state
from .io import read_json
from .pilot_config import BATCH_SIZE, CHECKPOINT_STEPS, FAMILY, SCHEMA, SPEC, TRAIN_ROWS
from .pilot_model import CONTEXT, PilotModel


def components(variant: str) -> dict[str, Any]:
    memory = not variant.startswith("dense")
    tree = variant.endswith("_tree")
    return {
        "backbone": "pilot-pre-ln-tied-dense-v1",
        "query_output_adapters_gate": "cosine-additive-v1" if memory else None,
        "keys": ("factorized-64x64-v1" if variant == "product_key" else "independent-v1")
        if memory
        else None,
        "values": "direct-32-v1" if memory else None,
        "slot_ids": {"first": 0, "last": 4095} if memory else None,
        "router": ("trainable-v1" if variant == "learned_tree" else "fixed-buffer-v1")
        if tree
        else None,
        "partitions": {
            "branches": 16,
            "slots_per_branch": 256,
            "rule": "slot_id = 256*branch_id + local_id",
        }
        if tree
        else None,
        "storage_layout": None,
        "scheduler": None,
    }


def save(
    path: Path,
    model: PilotModel,
    optimizer: AdamW,
    step: int,
    identity: dict[str, Any],
) -> str:
    if (
        step not in CHECKPOINT_STEPS
        or identity["variant"] != model.variant
        or identity["seed"] != model.seed
    ):
        raise ValueError("invalid pilot checkpoint step or variant")
    return publish_state(
        path,
        {
            "family": FAMILY,
            "schema_version": SCHEMA,
            "spec_reference": SPEC,
            "identity": identity,
            "components": components(model.variant),
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "python_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "completed_step": step,
            "next_row": (step * BATCH_SIZE) % TRAIN_ROWS,
            "train_tokens": step * BATCH_SIZE * CONTEXT,
        },
        schema=SCHEMA,
    )


def restore(
    path: Path,
    model: PilotModel,
    optimizer: AdamW,
    identity: dict[str, Any],
) -> tuple[int, int, int]:
    index = _dict_with_fields(
        read_json(path / "index.json"), {"schema_version", "state_sha256"}, "pilot checkpoint index"
    )
    if type(index["schema_version"]) is not int or index["schema_version"] != SCHEMA:
        raise ValueError("unknown pilot checkpoint index schema")
    with (path / "state.pt").open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("pilot checkpoint checksum mismatch")
        file.seek(0)
        state = _dict_with_fields(
            torch.load(file, weights_only=True, map_location="cpu"),
            {
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
                "next_row",
                "train_tokens",
            },
            "pilot checkpoint state",
        )
    if (
        state["family"] != FAMILY
        or type(state["schema_version"]) is not int
        or state["schema_version"] != SCHEMA
        or state["spec_reference"] != SPEC
        or state["identity"] != identity
        or identity["variant"] != model.variant
        or identity["seed"] != model.seed
        or state["components"] != components(model.variant)
    ):
        raise ValueError("pilot checkpoint variant/config/data/spec mismatch")
    step = state["completed_step"]
    cursor = state["next_row"]
    tokens = state["train_tokens"]
    if (
        type(step) is not int
        or step not in CHECKPOINT_STEPS
        or type(cursor) is not int
        or cursor != (step * BATCH_SIZE) % TRAIN_ROWS
        or type(tokens) is not int
        or tokens != step * BATCH_SIZE * CONTEXT
    ):
        raise ValueError("invalid pilot checkpoint counters")
    expected = model.state_dict()
    model_state = _dict_with_fields(state["model"], set(expected), "pilot model")
    if any(not _same_tensor(model_state[name], target) for name, target in expected.items()):
        raise ValueError("invalid pilot checkpoint model tensors")
    if model.variant == "fixed_tree" and not torch.equal(
        model_state["memory.router"], expected["memory.router"]
    ):
        raise ValueError("fixed router differs from registered initialization")
    _validate_optimizer(state["optimizer"], model, optimizer, step)
    random.Random(0).setstate(state["python_rng"])
    if not _same_tensor(state["torch_rng"], torch.get_rng_state()):
        raise ValueError("invalid pilot checkpoint RNG tensor")
    torch.Generator(device="cpu").set_state(state["torch_rng"])

    model.load_state_dict(model_state, strict=True)
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    return step, cursor, tokens
