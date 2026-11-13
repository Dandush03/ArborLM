"""Versioned, immutable checkpoints for locally generated E0 state."""

import ctypes
import hashlib
import math
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.optim import AdamW

from .config import SCHEMA, SPEC
from .engine import BATCH_SIZE, CHECKPOINT_STEPS, CONTEXT
from .io import file_sha256, fsync_dir, read_json, write_json
from .model import DenseBaseline

NOT_APPLICABLE = dict.fromkeys(
    ("scheduler", "router", "memory", "index", "layout"), "not_applicable"
)
STATE_FIELDS = {
    "schema_version",
    "spec_reference",
    "identity",
    "model",
    "optimizer",
    "python_rng",
    "torch_rng",
    "completed_step",
    "next_row",
    "train_tokens",
    "components",
}
INDEX_FIELDS = {"schema_version", "state_sha256"}


def _publish_exclusive(stage: Path, destination: Path) -> None:
    """Atomically publish a directory without replacing an existing path."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = libc.renamex_np
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        arguments = (os.fsencode(stage), os.fsencode(destination), 0x00000004)  # RENAME_EXCL
    elif sys.platform == "linux":
        rename = libc.renameat2
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        arguments = (
            -100,
            os.fsencode(stage),
            -100,
            os.fsencode(destination),
            1,
        )  # RENAME_NOREPLACE
    else:
        raise RuntimeError("exclusive checkpoint publication is unsupported on this platform")
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def save_checkpoint(
    destination: Path,
    model: DenseBaseline,
    optimizer: AdamW,
    step: int,
    identity: dict[str, Any],
) -> str:
    if destination.exists():
        raise FileExistsError(destination)
    if step not in CHECKPOINT_STEPS:
        raise ValueError(f"unsupported checkpoint step: {step}")
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        state_path = stage / "state.pt"
        state = {
            "schema_version": SCHEMA,
            "spec_reference": SPEC,
            "identity": identity,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "python_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "completed_step": step,
            "next_row": (step * BATCH_SIZE) % 256,
            "train_tokens": step * BATCH_SIZE * CONTEXT,
            "components": NOT_APPLICABLE,
        }
        with state_path.open("xb") as file:
            torch.save(state, file)
            file.flush()
            os.fsync(file.fileno())
        digest = file_sha256(state_path)
        write_json(stage / "index.json", {"schema_version": SCHEMA, "state_sha256": digest})
        _publish_exclusive(stage, destination)
        fsync_dir(destination.parent)
        return digest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _dict_with_fields(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise ValueError(f"invalid {label} fields")
    return value


def _schema(value: object) -> None:
    if type(value) is not int or value != SCHEMA:
        raise ValueError("unknown checkpoint schema")


def _same_tensor(value: object, reference: Tensor) -> bool:
    return (
        isinstance(value, Tensor)
        and value.layout == reference.layout
        and value.shape == reference.shape
        and value.dtype == reference.dtype
        and value.device == reference.device
        and bool(torch.isfinite(value).all())
    )


def _validate_optimizer(state: object, model: DenseBaseline, optimizer: AdamW, step: int) -> None:
    opt = _dict_with_fields(state, {"state", "param_groups"}, "optimizer")
    if opt["param_groups"] != optimizer.state_dict()["param_groups"]:
        raise ValueError("checkpoint optimizer parameter groups/settings mismatch")
    entries = opt["state"]
    params = list(model.parameters())
    if not isinstance(entries, dict) or set(entries) != set(range(len(params))):
        raise ValueError("checkpoint optimizer entries incomplete")
    for index, reference in enumerate(params):
        entry = _dict_with_fields(entries[index], {"step", "exp_avg", "exp_avg_sq"}, "AdamW state")
        clock = entry["step"]
        if (
            not _same_tensor(clock, torch.zeros((), dtype=torch.float32))
            or not math.isclose(clock.item(), step, rel_tol=0, abs_tol=0)
            or not _same_tensor(entry["exp_avg"], reference)
            or not _same_tensor(entry["exp_avg_sq"], reference)
        ):
            raise ValueError("checkpoint AdamW tensors invalid")


def read_checkpoint(
    directory: Path,
    model: DenseBaseline,
    optimizer: AdamW,
    identity: dict[str, Any],
) -> dict[str, Any]:
    index = _dict_with_fields(read_json(directory / "index.json"), INDEX_FIELDS, "index")
    _schema(index["schema_version"])
    file = directory / "state.pt"
    with file.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("checkpoint state checksum mismatch")
        stream.seek(0)
        # No arbitrary objects are needed even for trusted, locally generated checkpoints.
        state = _dict_with_fields(
            torch.load(stream, map_location="cpu", weights_only=True), STATE_FIELDS, "checkpoint"
        )
    _schema(state["schema_version"])
    if state["identity"] != identity or state["spec_reference"] != SPEC:
        raise ValueError("checkpoint config/data/tokenizer/spec identity mismatch")
    if state["components"] != NOT_APPLICABLE:
        raise ValueError("checkpoint component declarations mismatch")
    step = state["completed_step"]
    if (
        type(step) is not int
        or step not in CHECKPOINT_STEPS
        or type(state["next_row"]) is not int
        or state["next_row"] != (step * BATCH_SIZE) % 256
        or type(state["train_tokens"]) is not int
        or state["train_tokens"] != step * BATCH_SIZE * CONTEXT
    ):
        raise ValueError("checkpoint counters invalid")
    model_state = model.state_dict()
    supplied = _dict_with_fields(state["model"], set(model_state), "model state")
    if any(not _same_tensor(supplied[key], tensor) for key, tensor in model_state.items()):
        raise ValueError("checkpoint model tensor mismatch")
    _validate_optimizer(state["optimizer"], model, optimizer, step)
    random.Random(0).setstate(state["python_rng"])
    if not _same_tensor(state["torch_rng"], torch.get_rng_state()):
        raise ValueError("checkpoint torch RNG tensor mismatch")
    torch.Generator(device="cpu").set_state(state["torch_rng"])
    return state


def restore_checkpoint(
    state: dict[str, Any],
    model: DenseBaseline,
    optimizer: AdamW,
) -> tuple[int, int, int]:
    model.load_state_dict(state["model"], strict=True)
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    return int(state["completed_step"]), int(state["next_row"]), int(state["train_tokens"])
