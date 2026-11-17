"""P8 checkpoints: one atomic file per step, with optimizer state, RNG state and identity.

Layout: ``<train_run>/cells/<cell.label>/step-0000.pt``, ``step-0256.pt``, ``step-0512.pt``.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import hashlib
import os
import random
import tempfile
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW

from .io import file_sha256, fsync_dir
from .p4_model import Backbone
from .p5_model import (
    Model,
    backbone_digest,
    optimizer_for,
    optimizer_names,
    state_digest,
)
from .p8_core import CHECKPOINT_STEPS, FAMILY, SCHEMA, SPEC, Cell, build_model

__all__ = ["restore", "save", "state_digest", "step_path"]

FIELDS = {
    "family",
    "schema_version",
    "spec_reference",
    "identity",
    "step",
    "model",
    "optimizer",
    "optimizer_parameter_names",
    "python_rng",
    "torch_rng",
    "requires_grad",
    "bypass",
    "state_digest",
    "backbone_sha256",
}
IDENTITY_REQUIRED = ("cell", "backbone_sha256", "source_sha256", "spec_sha256", "config_sha256")


def step_path(cell_dir: Path, step: int) -> Path:
    return cell_dir / f"step-{step:04d}.pt"


def _check_identity(identity: dict[str, Any], cell: Cell, backbone_hash: str) -> None:
    missing = [k for k in IDENTITY_REQUIRED if k not in identity]
    if missing or identity["cell"] != cell.fields() or identity["backbone_sha256"] != backbone_hash:
        raise ValueError(f"P8 checkpoint identity incomplete or mismatched: {missing}")


def save(
    path: Path,
    model: Model,
    optimizer: AdamW | None,
    step: int,
    identity: dict[str, Any],
) -> str:
    """Atomically write the checkpoint; refuse to overwrite. Returns the file's SHA-256."""
    cell = model.cell
    if not isinstance(cell, Cell):
        raise ValueError("P8 checkpoint requires a P8 cell")
    if type(step) is not int or step not in CHECKPOINT_STEPS or optimizer is None:
        raise ValueError("P8 checkpoint step or optimizer invalid")
    digest = backbone_digest(model.backbone)
    _check_identity(identity, cell, digest)
    if model.bypass:
        raise ValueError("P8 model must not bypass the memory")
    if path.exists():
        raise FileExistsError(path)
    state = {
        "family": FAMILY,
        "schema_version": SCHEMA,
        "spec_reference": SPEC,
        "identity": identity,
        "step": step,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "optimizer_parameter_names": optimizer_names(model, optimizer),
        "python_rng": random.getstate(),
        "torch_rng": torch.get_rng_state(),
        "requires_grad": {name: p.requires_grad for name, p in model.named_parameters()},
        "bypass": model.bypass,
        "state_digest": state_digest(model),
        "backbone_sha256": digest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            torch.save(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError(path)
        os.link(temporary, path)  # exclusive publish: fails if the destination exists
        fsync_dir(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return file_sha256(path)


def restore(
    path: Path,
    cell: Cell,
    backbone: Backbone,
    *,
    expected_sha256: str | None = None,
) -> tuple[Model, AdamW | None, dict[str, Any]]:
    """Load a checkpoint into a freshly built model of ``cell`` over ``backbone``; verify identity,
    file hash (if given), backbone digest, optimizer membership and the recorded state digest.
    Restores the Python and torch RNG state. Returns ``(model, optimizer, meta)``."""
    with path.open("rb") as stream:
        file_digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if expected_sha256 is not None and file_digest != expected_sha256:
            raise ValueError("P8 checkpoint file checksum mismatch")
        stream.seek(0)
        state = torch.load(stream, weights_only=True, map_location="cpu")
    if not isinstance(state, dict) or state.keys() != FIELDS:
        raise ValueError("invalid P8 checkpoint fields")
    if (
        state["family"] != FAMILY
        or state["schema_version"] != SCHEMA
        or state["spec_reference"] != SPEC
        or state["step"] not in CHECKPOINT_STEPS
    ):
        raise ValueError("P8 checkpoint family/schema/spec/step mismatch")
    model = build_model(cell, backbone, seed_rng=False)
    optimizer = optimizer_for(model)
    current = backbone_digest(model.backbone)
    _check_identity(state["identity"], cell, current)
    if state["backbone_sha256"] != current:
        raise ValueError("P8 checkpoint backbone digest mismatch")
    names = optimizer_names(model, optimizer)
    flags = {name: p.requires_grad for name, p in model.named_parameters()}
    if (
        state["optimizer_parameter_names"] != names
        or state["requires_grad"] != flags
        or state["bypass"] is not model.bypass
        or optimizer is None
    ):
        raise ValueError("P8 checkpoint optimizer membership or freeze flags mismatch")
    expected = model.state_dict()
    tensors = state["model"]
    if not isinstance(tensors, dict) or tensors.keys() != expected.keys():
        raise ValueError("P8 checkpoint model keys mismatch")
    for name, tensor in expected.items():
        saved = tensors[name]
        if (
            not isinstance(saved, torch.Tensor)
            or saved.shape != tensor.shape
            or saved.dtype != tensor.dtype
            or not bool(torch.isfinite(saved).all())
        ):
            raise ValueError(f"P8 invalid model tensor: {name}")
        frozen = name.startswith("backbone.") or (
            cell.variant == "fixed_tree" and name == "addition.router"
        )
        if frozen and not torch.equal(saved, tensor):
            raise ValueError(f"P8 frozen tensor changed: {name}")
    model.load_state_dict(tensors, strict=True)
    optimizer.load_state_dict(state["optimizer"])
    if state_digest(model) != state["state_digest"]:
        raise ValueError("P8 checkpoint state digest mismatch")
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    meta = {
        "step": state["step"],
        "state_digest": state["state_digest"],
        "file_sha256": file_digest,
        "identity": state["identity"],
    }
    return model, optimizer, meta


def optimizer_params(model: Model) -> list[nn.Parameter]:
    return [p for p in model.parameters() if p.requires_grad]
