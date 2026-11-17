"""Strict ADR-0007 registry and cell identities."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import pilot_config
from .config import _validate
from .io import canonical_json, sha256

SPEC = "docs/decisions/ADR-0007-controlled-optimization-followup.md"
FAMILY = "P2_OPTIMIZATION_FOLLOWUP"
SCHEMA = 1
PARENT_SPEC = pilot_config.SPEC
BACKBONES = (101, 102, 103)
MEMORIES = (201, 202, 203)
ORDERS = (301, 302, 303)
CONTROL_MEMORY = 201
CONDITIONS = ("enabled", "disabled", "values_permuted", "joint_within_branch")
CONTROL, LEARNED = "disabled_throughout", "learned_tree"
VAL_START, VAL_END, TRAIN_SEEN, TRAIN_RANKED = 512, 1024, 2048, 4096
BATCH, STEPS, CONTEXT = 8, 256, 64
CHECKPOINT_STEPS = (128, 256)
CELL_SECONDS, SUITE_SECONDS = 300, 1800
TRAIN_TARGETS, VAL_TARGETS = 131072, 32768
JOINT_ATOL, ADDITIVE_ATOL, THRESHOLD = 1e-6, 1e-12, 0.005

_REGISTERED = {
    "schema_version": 1,
    "experiment_family": "P2_OPTIMIZATION_FOLLOWUP",
    "spec_reference": "docs/decisions/ADR-0007-controlled-optimization-followup.md",
    "parent_spec_reference": "docs/decisions/ADR-0005-ram-pilot-spec.md",
    "backbone_seeds": [101, 102, 103],
    "memory_seeds": [201, 202, 203],
    "order_seeds": [301, 302, 303],
    "cell_order": "backbone-order-control-first-memory-ascending",
    "data": {
        "selection": "arborlm-pilot-v1",
        "validation_rank_interval": [512, 1024],
        "train_rank_interval": [0, 2048],
        "train_ranked_chunks": 4096,
        "batch_order": "torch-cpu-randperm-2048",
    },
    "model": {
        "architecture": "adr0005-small-learned-tree",
        "control": "memory-bypassed-and-frozen-throughout",
        "control_memory_seed": 201,
    },
    "train": {
        "execution": "adr0005-cpu-float32-adamw",
        "batch_size": 8,
        "steps": 256,
        "checkpoint_steps": [128, 256],
        "eval_steps": [0, 256],
    },
    "diagnostic": {
        "conditions": ["enabled", "disabled", "values_permuted", "joint_within_branch"],
        "value_seed_offset": 20000,
        "joint_seed_offset": 30000,
        "joint_absolute_tolerance": 1e-06,
        "joint_relative_tolerance": 0.0,
    },
    "limits": {
        "cell_seconds": 300,
        "suite_seconds": 1800,
        "rss_bytes": 2147483648,
        "poll_seconds": 0.1,
    },
    "analysis": {
        "mean_dependence_threshold": 0.005,
        "consistent_sign_cells": 22,
        "heterogeneous_min_cells": 3,
        "factor_sensitivity_threshold": 0.005,
        "additive_identity_absolute_tolerance": 1e-12,
    },
}


@dataclass(frozen=True)
class Cell:
    backbone: int
    memory: int
    order: int
    condition: str

    def __post_init__(self) -> None:
        if (
            self.backbone not in BACKBONES
            or self.memory not in MEMORIES
            or self.order not in ORDERS
            or self.condition not in (CONTROL, LEARNED)
            or (self.condition == CONTROL and self.memory != CONTROL_MEMORY)
        ):
            raise ValueError("unregistered P2 cell")

    @property
    def index(self) -> int:
        if self.condition != LEARNED:
            raise ValueError("intervention index applies only to learned cells")
        return (self.backbone - 101) * 9 + (self.order - 301) * 3 + (self.memory - 201)

    def fields(self) -> dict[str, Any]:
        return asdict(self)


def cells() -> list[Cell]:
    return [
        cell
        for b in BACKBONES
        for o in ORDERS
        for cell in [
            Cell(b, CONTROL_MEMORY, o, CONTROL),
            *(Cell(b, m, o, LEARNED) for m in MEMORIES),
        ]
    ]


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    _validate(config, _REGISTERED, "P2 config")
    return config


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return validate_config(tomllib.load(file))


def config_hash(config: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_config(config)))
