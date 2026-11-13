"""ADR-0010 registry and fixed P5 budgets."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import _validate
from .io import canonical_json, sha256
from .p2_config import BACKBONES, ORDERS

SPEC = "docs/decisions/ADR-0010-hierarchical-memory-ablation.md"
PARENT_SPEC = "docs/decisions/ADR-0009-frozen-backbone-capacity.md"
PARENT_SUITE = "P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd"
PARENT_FREEZE = "812b3fd02d81124b0665cc96d1364a32e40d403d"
PARENT_ARCHIVE = "18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0"
PARENT_RESULTS = Path("results/p4-2026-11-12")
FAMILY = "P5_HIERARCHY_ABLATION"
SCHEMA = 1
BASELINE, FLAT, FIXED, LEARNED, DENSE = "baseline", "flat", "fixed_tree", "learned_tree", "dense"
MEMORIES = (FLAT, FIXED, LEARNED)
VARIANTS = (*MEMORIES, DENSE)
SEEDS = (501, 502, 503)
CHECKPOINT_STEPS = (0, 256, 512)
STEPS, BATCH, CONTEXT, CYCLE_ROWS = 512, 8, 64, 2048
VAL_TARGETS, TRAIN_TARGETS, TOTAL_TARGETS = 32768, 262144, 28311552
FROZEN_PARAMETERS = 27392
ADDITION_PARAMETERS = {BASELINE: 0, FLAT: 198145, FIXED: 198145, LEARNED: 198401, DENSE: 198401}
CONDITIONS = ("enabled", "disabled", "values_permuted", "joint_within_branch")
CELL_SECONDS, QUALITY_SECONDS, TIMING_SECONDS, SUITE_SECONDS = 300, 1800, 600, 2400
THRESHOLD, TOLERANCE, JOINT_ATOL = 0.005, -0.005, 1e-6

_REGISTERED = {
    "schema_version": 1,
    "experiment_family": "P5_HIERARCHY_ABLATION",
    "spec_reference": "docs/decisions/ADR-0010-hierarchical-memory-ablation.md",
    "parent_spec_reference": "docs/decisions/ADR-0009-frozen-backbone-capacity.md",
    "parent_suite": "P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd",
    "parent_freeze": "812b3fd02d81124b0665cc96d1364a32e40d403d",
    "parent_archive": "18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0",
    "backbones": [101, 102, 103],
    "orders": [301, 302, 303],
    "addition_seeds": [501, 502, 503],
    "variant_order": ["flat", "fixed_tree", "learned_tree", "dense"],
    "baseline_seed": 0,
    "model": {
        "backbone_parameters": 27392,
        "flat_parameters": 198145,
        "tree_router_scalars": 256,
        "dense_parameters": 198401,
        "dense_width": 3100,
        "gate": -2.0,
        "init_std": 0.02,
        "component_seed_offsets": [1000, 2000, 3000, 4000, 5000],
        "memory": "unchanged-adr0005",
    },
    "data": {
        "train_ranks": [0, 2048],
        "validation_ranks": [2048, 2560],
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
        "value_seed_offset": 60000,
        "joint_seed_offset": 70000,
        "joint_absolute_tolerance": 1e-06,
        "joint_relative_tolerance": 0.0,
    },
    "timing": {
        "batch_sizes": [8, 1],
        "scopes": ["lookup_score_select", "addition_forward", "model_forward"],
        "rounds": 8,
        "warmups": 2,
        "calls": 10,
        "median_resolution_ratio": 100,
        "round_median_ratio_limit": 1.25,
    },
    "analysis": {
        "effect_threshold": 0.005,
        "dense_tolerance": -0.005,
        "min_cells": 22,
        "min_parents": 8,
        "score_work_max_ratio": 0.25,
        "addition_time_max_ratio": 0.8,
        "model_time_max_ratio": 1.05,
        "identity_absolute_tolerance": 1e-12,
    },
    "limits": {
        "cell_seconds": 300,
        "quality_seconds": 1800,
        "timing_seconds": 600,
        "combined_seconds": 2400,
        "timing_quartet_seconds": 45,
        "timing_baseline_seconds": 15,
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
            or self.variant not in (BASELINE, *VARIANTS)
            or self.seed not in ((0,) if self.variant == BASELINE else SEEDS)
        ):
            raise ValueError("unregistered P5 cell")

    @property
    def parent_label(self) -> str:
        return f"b{self.backbone}-o{self.order}-baseline"

    @property
    def label(self) -> str:
        suffix = self.variant if self.variant == BASELINE else f"{self.variant}-s{self.seed}"
        return f"b{self.backbone}-o{self.order}-{suffix}"

    @property
    def index(self) -> int:
        if self.variant == BASELINE:
            raise ValueError("P5 baseline has no seed index")
        return (self.backbone - 101) * 9 + (self.order - 301) * 3 + (self.seed - 501)

    def fields(self) -> dict[str, Any]:
        return asdict(self)


def rotate(items: tuple[str, ...], shift: int) -> tuple[str, ...]:
    shift %= len(items)
    return items[shift:] + items[:shift]


def cells() -> list[Cell]:
    result = []
    for b in BACKBONES:
        for o in ORDERS:
            result.append(Cell(b, o, 0, BASELINE))
            for seed in SEEDS:
                index = Cell(b, o, seed, FLAT).index
                result.extend(Cell(b, o, seed, v) for v in rotate(VARIANTS, index))
    return result


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, _REGISTERED, "P5 config")
    return data


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return validate_config(tomllib.load(stream))


def config_hash(data: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_config(data)))


def batch_offset(step: int) -> int:
    if not 1 <= step <= STEPS:
        raise ValueError("invalid P5 update")
    return ((step - 1) * BATCH) % CYCLE_ROWS


def counters(step: int) -> dict[str, int]:
    if not 0 <= step <= STEPS:
        raise ValueError("invalid P5 checkpoint step")
    return {
        "additional_step": step,
        "absolute_order_cursor": step * BATCH,
        "next_cyclic_order_cursor": step * BATCH % CYCLE_ROWS,
        "additional_targets": step * BATCH * CONTEXT,
    }
