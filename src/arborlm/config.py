"""Validate the single approved E0 configuration before execution."""

import tomllib
from pathlib import Path
from typing import Any

from .io import canonical_json, sha256

SPEC = "docs/decisions/ADR-0003-e0-approved-spec.md"
SCHEMA = 1
# Kept independently of the CLI input: modifying the input cannot redefine E0.
_APPROVED = {
    "schema_version": 1,
    "experiment_family": "E0",
    "question_id": "G0",
    "spec_reference": "docs/decisions/ADR-0003-e0-approved-spec.md",
    "data": {
        "generator": "sha256-cycle8-v1",
        "tokenizer": "integer-identity-v1",
        "vocab_size": 16,
        "motif_length": 8,
        "row_length": 33,
        "train_seed": 101,
        "validation_seed": 202,
        "train_rows": 256,
        "validation_rows": 64,
        "packing": False,
    },
    "model": {
        "architecture": "dense-causal-pre-layernorm",
        "blocks": 2,
        "width": 32,
        "heads": 4,
        "head_width": 8,
        "ffn_width": 64,
        "context_length": 32,
        "position_embedding": "learned-absolute",
        "layer_norm_epsilon": 1e-05,
        "qkv_projection": "combined-biased",
        "attention": "explicit-scaled-dot-product-causal-diagonal",
        "activation": "gelu-exact",
        "tied_output": True,
        "output_bias": False,
        "dropout": 0.0,
        "init_mean": 0.0,
        "init_std": 0.02,
        "bias_init": 0.0,
        "norm_scale_init": 1.0,
        "parameters": 18688,
    },
    "training": {
        "device": "cpu",
        "dtype": "float32",
        "torch_seed": 42,
        "python_seed": 42,
        "threads": 1,
        "interop_threads": 1,
        "deterministic_algorithms": True,
        "deterministic_warn_only": False,
        "steps": 32,
        "batch_size": 8,
        "accumulation": 1,
        "row_order": "cyclic",
        "workers": 0,
        "objective": "mean-next-token-cross-entropy",
        "optimizer": "AdamW",
        "learning_rate": 0.003,
        "betas": [0.9, 0.999],
        "epsilon": 1e-08,
        "weight_decay": 0.0,
        "amsgrad": False,
        "foreach": False,
        "fused": False,
        "gradient_clip_norm": 1.0,
        "error_if_nonfinite_gradients": True,
        "zero_grad_set_to_none": True,
        "mixed_precision": False,
        "compile": False,
        "scheduler": False,
        "checkpoint_steps": [16, 32],
    },
    "evaluation": {
        "steps": [0, 32],
        "batch_size": 8,
        "reduction": "sum-cross-entropy-divided-by-valid-targets",
        "nll_units": "nats_per_target_token",
    },
    "limits": {
        "process_seconds": 300,
        "smoke_seconds": 1500,
        "rss_bytes": 2147483648,
        "poll_seconds": 0.1,
    },
}


def _validate(actual: object, expected: object, location: str) -> None:
    if type(actual) is not type(expected):
        raise ValueError(f"{location}: unsupported value type")
    if isinstance(expected, dict) and isinstance(actual, dict):
        if actual.keys() != expected.keys():
            extra = sorted(actual.keys() - expected.keys())
            missing = sorted(expected.keys() - actual.keys())
            raise ValueError(f"{location}: unknown fields {extra}, missing fields {missing}")
        for key, value in expected.items():
            _validate(actual[key], value, f"{location}.{key}")
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            raise ValueError(f"{location}: unsupported list length")
        for index, (item, reference) in enumerate(zip(actual, expected, strict=True)):
            _validate(item, reference, f"{location}[{index}]")
    elif actual != expected:
        raise ValueError(f"{location}: expected {expected!r}; got {actual!r}")


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, _APPROVED, "config")
    return data


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return validate_config(tomllib.load(file))


def config_hash(config: dict[str, Any]) -> str:
    return sha256(canonical_json(validate_config(config)))
