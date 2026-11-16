"""ADR-0009 registry and fixed P4 budgets."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import _validate
from .io import canonical_json, sha256
from .p2_config import BACKBONES, ORDERS

SPEC = "docs/decisions/ADR-0009-frozen-backbone-capacity.md"
PARENT_SPEC = "docs/decisions/ADR-0008-bounded-longer-training.md"
PARENT_SUITE = "P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d"
PARENT_FREEZE = "861c137a7fcccf27e3371ca2217fd7d956753ca9"
PARENT_ARCHIVE = "7be7aaccde57383961e530b64bdc6902df3f3b690af2857f68db0c5f96ad75a0"
PARENT_RESULTS = Path("results/p3-lt-2026-11-12")
FAMILY = "P4_FROZEN_CAPACITY"
SCHEMA = 1
BASELINE, MEMORY, DENSE = "baseline", "memory", "dense"
SEEDS = (401, 402, 403)
CHECKPOINT_STEPS = (0, 256, 512)
STEPS, BATCH, CONTEXT, CYCLE_ROWS = 512, 8, 64, 2048
VAL_TARGETS, TRAIN_TARGETS, TOTAL_TARGETS = 32768, 262144, 14155776
FROZEN_PARAMETERS, ADDITION_PARAMETERS = 27392, 198401
CONDITIONS = ("enabled", "disabled", "values_permuted", "joint_within_branch")
CELL_SECONDS, SUITE_SECONDS = 300, 1800
THRESHOLD, TOLERANCE, JOINT_ATOL = 0.005, -0.005, 1e-6
_REGISTERED = {
    "schema_version": 1,
    "experiment_family": "P4_FROZEN_CAPACITY",
    "spec_reference": "docs/decisions/ADR-0009-frozen-backbone-capacity.md",
    "parent_spec_reference": "docs/decisions/ADR-0008-bounded-longer-training.md",
    "parent_suite": "P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d",
    "parent_freeze": "861c137a7fcccf27e3371ca2217fd7d956753ca9",
    "parent_archive": "7be7aaccde57383961e530b64bdc6902df3f3b690af2857f68db0c5f96ad75a0",
    "backbones": [101, 102, 103],
    "orders": [301, 302, 303],
    "addition_seeds": [401, 402, 403],
    "baseline_seed": 0,
    "model": {
        "backbone_parameters": 27392,
        "addition_parameters": 198401,
        "dense_width": 3100,
        "memory": "unchanged-adr0005-learned-tree",
        "gate": -2.0,
        "init_std": 0.02,
        "component_seed_offsets": [1000, 2000, 3000, 4000, 5000],
    },
    "data": {
        "train_ranks": [0, 2048],
        "validation_ranks": [1536, 2048],
        "order": "exact-parent-two-cycles",
    },
    "training": {
        "steps": 512,
        "batch": 8,
        "context": 64,
        "optimizer": "fresh-adr0005-AdamW-only-addition",
        "checkpoint_steps": [0, 256, 512],
        "evaluation_steps": [0, 512],
    },
    "intervention": {
        "value_seed_offset": 40000,
        "joint_seed_offset": 50000,
        "joint_absolute_tolerance": 1e-06,
        "joint_relative_tolerance": 0.0,
    },
    "analysis": {
        "effect_threshold": 0.005,
        "dense_tolerance": -0.005,
        "min_cells": 22,
        "min_parents": 8,
        "identity_absolute_tolerance": 1e-12,
    },
    "limits": {
        "cell_seconds": 300,
        "suite_seconds": 1800,
        "rss_bytes": 2147483648,
        "poll_seconds": 0.1,
    },
}


@dataclass(frozen=True)
class Cell:
    backbone: int
    order: int
    seed: int
    variant: str

    def __post_init__(self) -> None:
        if (
            self.backbone not in BACKBONES
            or self.order not in ORDERS
            or self.variant not in (BASELINE, MEMORY, DENSE)
            or self.seed not in ((0,) if self.variant == BASELINE else SEEDS)
        ):
            raise ValueError("unregistered P4 cell")

    @property
    def parent_label(self) -> str:
        return f"b{self.backbone}-o{self.order}-control"

    @property
    def label(self) -> str:
        suffix = self.variant if self.variant == BASELINE else f"{self.variant}-s{self.seed}"
        return f"b{self.backbone}-o{self.order}-{suffix}"

    @property
    def index(self) -> int:
        if self.variant != MEMORY:
            raise ValueError("only P4 memory cells have a permutation index")
        return (self.backbone - 101) * 9 + (self.order - 301) * 3 + (self.seed - 401)

    def fields(self) -> dict[str, Any]:
        return asdict(self)


def cells() -> list[Cell]:
    return [
        cell
        for b in BACKBONES
        for o in ORDERS
        for cell in [
            Cell(b, o, 0, BASELINE),
            *(Cell(b, o, seed, variant) for seed in SEEDS for variant in (MEMORY, DENSE)),
        ]
    ]


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, _REGISTERED, "P4 config")
    return data


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return validate_config(tomllib.load(stream))


def config_hash(data: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_config(data)))


def batch_offset(step: int) -> int:
    if not 1 <= step <= STEPS:
        raise ValueError("invalid P4 update")
    return ((step - 1) * BATCH) % CYCLE_ROWS


def counters(step: int) -> dict[str, int]:
    if not 0 <= step <= STEPS:
        raise ValueError("invalid P4 checkpoint step")
    return {
        "additional_step": step,
        "absolute_order_cursor": step * BATCH,
        "next_cyclic_order_cursor": step * BATCH % CYCLE_ROWS,
        "additional_targets": step * BATCH * CONTEXT,
    }
