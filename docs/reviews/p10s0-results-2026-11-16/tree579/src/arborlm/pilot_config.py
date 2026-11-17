"""Strict versioned configuration for the registered P1 RAM screen."""

import tomllib
from pathlib import Path
from typing import Any

from .config import _validate
from .io import canonical_json, sha256

SPEC = "docs/decisions/ADR-0005-ram-pilot-spec.md"
DATA_APPROVAL = "docs/decisions/ADR-0004-real-data-pilot-prerequisite.md"
FAMILY = "P1_SCREEN"
SCHEMA = 1
VARIANTS = (
    "dense_small",
    "dense_parameter_matched",
    "flat",
    "product_key",
    "fixed_tree",
    "learned_tree",
)
SEEDS = (42, 43, 44)
STEPS, BATCH_SIZE, TRAIN_ROWS, VAL_ROWS = 256, 8, 4096, 512
CHECKPOINT_STEPS = (128, 256)
RUN_SECONDS, SUITE_SECONDS = 300, 1800
_REGISTERED = {
    "schema_version": 1,
    "experiment_family": "P1_SCREEN",
    "spec_reference": "docs/decisions/ADR-0005-ram-pilot-spec.md",
    "variant_order": [
        "dense_small",
        "dense_parameter_matched",
        "flat",
        "product_key",
        "fixed_tree",
        "learned_tree",
    ],
    "seed_order": [42, 43, 44],
    "data": {
        "recipe": "arborlm-pilot-v1",
        "tokenizer": "utf8-bytes-v1",
        "chunk_bytes": 65,
        "train_chunks": 4096,
        "validation_chunks": 512,
        "deduplicate_full_train": True,
    },
    "model": {
        "version": "p1-dense-memory-v1",
        "backbone_reference": "E0-exact-block",
        "width": 32,
        "blocks": 2,
        "heads": 4,
        "vocab_size": 256,
        "context": 64,
        "ffn_width": 64,
        "matched_ffn_width": 1588,
        "memory_after_block": 0,
        "slots": 4096,
        "key_dim": 16,
        "value_dim": 32,
        "retrieved_values": 8,
        "temperature": 0.2,
        "normalize_eps": 1e-08,
        "gate_init": -2.0,
        "branches": 16,
        "visited_branches": 2,
        "product_keys_per_side": 64,
        "product_gap_fallback": 1e-05,
        "memory_seed_offsets": [1000, 2000, 3000, 4000, 5000],
    },
    "train": {
        "execution_reference": "E0-deterministic-CPU-float32-AdamW-clip",
        "steps": 256,
        "batch_size": 8,
        "checkpoint_steps": [128, 256],
        "eval_steps": [0, 256],
        "row_order": "fixed-ranked-cyclic",
        "optimizer_learning_rate": 0.003,
    },
    "limits": {
        "run_seconds": 300,
        "suite_seconds": 1800,
        "rss_bytes": 2147483648,
        "poll_seconds": 0.1,
    },
}


def validate_pilot_config(config: dict[str, Any]) -> dict[str, Any]:
    _validate(config, _REGISTERED, "pilot config")
    return config


def load_pilot_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return validate_pilot_config(tomllib.load(file))


def pilot_config_hash(config: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_pilot_config(config)))
