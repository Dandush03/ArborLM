"""Strict P3-LT config and duration/cursor semantics."""

import tomllib
from pathlib import Path
from typing import Any

from .config import _validate
from .io import canonical_json, sha256

FAMILY = "P3_LT"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0008-bounded-longer-training.md"
PARENT_SUITE = "P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7"
PARENT_FREEZE = "fd61cb7a69b8d29484cf8bef0170c1eb168da1fe"
PARENT_ARCHIVE = "6fea4b684a364ef85c8cda6ea1df683f9e7f8332dd4645caf7094b620da02801"
PARENT_SPEC = "docs/decisions/ADR-0007-controlled-optimization-followup.md"
PARENT_RESULTS = Path("results/p2-2026-11-12")
DURATIONS = (256, 512, 1024)
START, MID, END = DURATIONS
BATCH, CONTEXT, CYCLE_ROWS = 8, 64, 2048
VAL_START, VAL_END = 1024, 1536
CELL_SECONDS, SUITE_SECONDS = 300, 1800
ADDITIONAL_TARGETS, LIFETIME_TARGETS = 393216, 524288
THRESHOLD = 0.005
_REGISTERED = {
    "schema_version": 1,
    "experiment_family": "P3_LT",
    "spec_reference": "docs/decisions/ADR-0008-bounded-longer-training.md",
    "parent_spec_reference": "docs/decisions/ADR-0007-controlled-optimization-followup.md",
    "parent_suite_id": "P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7",
    "parent_source_freeze": "fd61cb7a69b8d29484cf8bef0170c1eb168da1fe",
    "parent_source_sha256": "6fea4b684a364ef85c8cda6ea1df683f9e7f8332dd4645caf7094b620da02801",
    "data": {
        "ranked_train": 4096,
        "used_train": 2048,
        "earlier_panels": [[0, 512], [512, 1024]],
        "validation_ranks": [1024, 1536],
        "order": "repeat-exact-parent-order",
    },
    "training": {
        "execution": "strict-P2-restore-and-identical-update",
        "parent_step": 256,
        "final_step": 1024,
        "batch_size": 8,
        "context": 64,
        "checkpoint_steps": [256, 512, 1024],
        "additional_targets_per_cell": 393216,
        "lifetime_targets_per_cell": 524288,
    },
    "evaluation": {
        "scientific_steps": [256, 512, 1024],
        "targets_per_panel": 32768,
        "conditions": ["enabled", "disabled", "values_permuted", "joint_within_branch"],
        "permutation_rule": "reuse-P2-seed-and-order-per-cell",
        "parent_panel_use": "bitwise-restore-integrity-only",
        "joint_absolute_tolerance": 1e-06,
    },
    "analysis": {
        "primary_step": 1024,
        "secondary_step": 512,
        "dependence_threshold": 0.005,
        "joint_positive_cells": 22,
        "additive_identity_absolute_tolerance": 1e-12,
    },
    "limits": {
        "cell_seconds": 300,
        "suite_seconds": 1800,
        "rss_bytes": 2147483648,
        "poll_seconds": 0.1,
    },
}


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    _validate(config, _REGISTERED, "P3 config")
    return config


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return validate_config(tomllib.load(stream))


def config_hash(config: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_config(config)))


def batch_offset(step: int) -> int:
    if not START < step <= END:
        raise ValueError("unregistered P3 update")
    return ((step - 1) * BATCH) % CYCLE_ROWS


def counters(step: int) -> dict[str, int]:
    if not START <= step <= END:
        raise ValueError("unregistered P3 global step")
    rows = step * BATCH
    return {
        "completed_step": step,
        "absolute_order_cursor": rows,
        "next_cyclic_order_cursor": rows % CYCLE_ROWS,
        "cumulative_targets": rows * CONTEXT,
        "additional_targets": (step - START) * BATCH * CONTEXT,
    }
