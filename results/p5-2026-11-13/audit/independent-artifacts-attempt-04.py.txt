#!/usr/bin/env python3
"""Read-only P5 artifact integrity checker; never calls a model forward."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

import torch

EXPECTED_ARCHIVE = "6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e"
BACKBONES, ORDERS, SEEDS = (101, 102, 103), (301, 302, 303), (501, 502, 503)
BASELINE, FLAT, FIXED, LEARNED, DENSE = (
    "baseline",
    "flat",
    "fixed_tree",
    "learned_tree",
    "dense",
)
VARIANTS = (FLAT, FIXED, LEARNED, DENSE)
EXPECTED_ADDITION = {BASELINE: 0, FLAT: 198145, FIXED: 198145, LEARNED: 198401, DENSE: 198401}
EXPECTED_CHECKPOINTS = {
    BASELINE: (0,),
    FLAT: (0, 256, 512),
    FIXED: (0, 256, 512),
    LEARNED: (0, 256, 512),
    DENSE: (0, 256, 512),
}
SOURCE_FILES_EXPECTED = 95
OPTIMIZER_OPTIONS = {
    "lr": 0.003,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0,
    "amsgrad": False,
    "maximize": False,
    "foreach": False,
    "capturable": False,
    "differentiable": False,
    "fused": False,
    "decoupled_weight_decay": True,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def same_tensor(left: torch.Tensor, right: torch.Tensor) -> bool:
    if left.shape != right.shape or left.dtype != right.dtype:
        return False
    left_bytes = left.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
    right_bytes = right.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
    return torch.equal(left_bytes, right_bytes)


def same_value(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return (
            isinstance(left, torch.Tensor)
            and isinstance(right, torch.Tensor)
            and same_tensor(left, right)
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(same_value(left[key], right[key]) for key in left)
        )
    if isinstance(left, list | tuple) or isinstance(right, list | tuple):
        return (
            isinstance(left, list | tuple)
            and isinstance(right, list | tuple)
            and len(left) == len(right)
            and all(same_value(a, b) for a, b in zip(left, right, strict=True))
        )
    return type(left) is type(right) and left == right


def independent_backbone_digest(model_state: dict[str, torch.Tensor]) -> str:
    tensors = {
        name.removeprefix("backbone."): tensor
        for name, tensor in model_state.items()
        if name.startswith("backbone.")
    }
    tensors["mask"] = torch.full((64, 64), -math.inf, dtype=torch.float32, device="cpu").triu(1)
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        metadata = {
            "name": name,
            "shape": list(tensor.shape),
            "dtype": str(tensor.dtype),
        }
        encoded = (json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n").encode()
        digest.update(encoded)
        tensor_bytes = tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
        digest.update(bytes(tensor_bytes.tolist()))
    return digest.hexdigest()


def cells_from_results(root: Path, errors: list[str]) -> dict[tuple[int, int, int, str], Path]:
    found = {}
    expected = {(b, o, 0, BASELINE) for b in BACKBONES for o in ORDERS} | {
        (b, o, seed, v) for b in BACKBONES for o in ORDERS for seed in SEEDS for v in VARIANTS
    }
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not (path / "manifest.json").is_file():
            continue
        manifest = read_json(path / "manifest.json")
        cell = manifest.get("seeds")
        if not isinstance(cell, dict):
            continue
        key = (cell["backbone"], cell["order"], cell["seed"], cell["variant"])
        if key not in expected or key in found:
            errors.append(f"unexpected/duplicate result directory {path}")
        found[key] = path
    if found.keys() != expected:
        errors.append(
            f"registered cell inventory mismatch: expected {len(expected)}, found {len(found)}"
        )
    return found


def raw_cells_from_compact(
    compact_cells: dict[tuple[int, int, int, str], Path], quality_suite: Path, errors: list[str]
) -> dict[tuple[int, int, int, str], Path]:
    rows = read_json(quality_suite / "cells.json")
    by_label = {row["label"]: row for row in rows}
    raw_cells = {}
    for key, compact in compact_cells.items():
        row = by_label.get(compact.name)
        if row is None or not row.get("run_id"):
            errors.append(f"missing raw-cell mapping for {compact.name}")
            continue
        raw = quality_suite / "cells" / row["run_id"]
        if not raw.is_dir():
            errors.append(f"raw quality cell missing for {compact.name}: {raw}")
            continue
        raw_cells[key] = raw
    if raw_cells.keys() != compact_cells.keys():
        errors.append("raw/compact cell mapping is incomplete")
    return raw_cells


def compare_json_files(paths: list[Path], label: str, errors: list[str]) -> str | None:
    hashes = {sha256(path) for path in paths if path.is_file()}
    if len(hashes) != 1 or len(paths) != len([path for path in paths if path.is_file()]):
        errors.append(f"{label} differs or is missing across result cells")
        return None
    return next(iter(hashes))


def validate_source_and_inputs(
    cells: dict[tuple[int, int, int, str], Path], suite: Path, errors: list[str]
) -> dict[str, Any]:
    source_hashes, source_maps, configs, environments, data_manifests = set(), [], [], [], []
    suite_source_map = read_json(suite / "source.json")["archive_file_sha256"]
    frozen_source_map = read_json(
        Path("results/p5-preflight-2026-11-13/execution-freeze/source.json")
    )["archive_file_sha256"]
    if suite_source_map != frozen_source_map:
        errors.append("suite source file map differs from committed execution-freeze map")
    for key, path in cells.items():
        source = read_json(path / "source.json")
        manifest = read_json(path / "manifest.json")
        archive_hash = source["archive"]["sha256"]
        source_hashes.add(archive_hash)
        source_maps.append(source["archive_file_sha256"])
        configs.append(sha256(path / "config.resolved.json"))
        environments.append(sha256(path / "environment.json"))
        data_manifests.append(sha256(path / "dataset_manifest.json"))
        if (
            archive_hash != EXPECTED_ARCHIVE
            or len(source["archive_file_sha256"]) != SOURCE_FILES_EXPECTED
        ):
            errors.append(f"source archive identity or file map size mismatch: {key}")
        if manifest["source_sha256"] != archive_hash:
            errors.append(f"source identity mismatch: {key}")
        if source["archive_file_sha256"] != suite_source_map:
            errors.append(f"source file map differs from suite frozen map: {key}")
    if len(source_hashes) != 1 or source_hashes != {EXPECTED_ARCHIVE}:
        errors.append("source archive hashes are not identical across all 117 cells")
    canonical_map = (
        json.dumps(source_maps[0], sort_keys=True, separators=(",", ":")) if source_maps else ""
    )
    if any(
        json.dumps(value, sort_keys=True, separators=(",", ":")) != canonical_map
        for value in source_maps
    ):
        errors.append("source archive file maps differ across P5 cells")
    config_hash = compare_json_files(
        [path / "config.resolved.json" for path in cells.values()], "resolved config", errors
    )
    environment_hash = compare_json_files(
        [path / "environment.json" for path in cells.values()], "environment", errors
    )
    data_hash = compare_json_files(
        [path / "dataset_manifest.json" for path in cells.values()], "dataset manifest", errors
    )
    suite_manifest = read_json(suite / "manifest.json")
    if suite_manifest.get("source_sha256") != EXPECTED_ARCHIVE:
        errors.append("suite source archive does not match frozen SHA-256")
    archive_path = suite / "source.tar"
    if not archive_path.is_file() or sha256(archive_path) != EXPECTED_ARCHIVE:
        errors.append("suite frozen source.tar hash mismatch")
    if suite_manifest.get("dataset_manifest_sha256") is None:
        errors.append("suite has no dataset manifest identity")
    frozen_dir = suite / "frozen-data"
    frozen_manifest_path = frozen_dir / "dataset_manifest.json"
    if frozen_manifest_path.is_file():
        frozen_manifest = read_json(frozen_manifest_path)
        canonical = (
            json.dumps(frozen_manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        )
        if hashlib.sha256(canonical).hexdigest() != suite_manifest.get("dataset_manifest_sha256"):
            errors.append("frozen dataset manifest does not match suite identity")
        for name, expected_hash in frozen_manifest.get("checksums_sha256", {}).items():
            path = frozen_dir / name
            if not path.is_file() or sha256(path) != expected_hash:
                errors.append(f"frozen dataset file hash mismatch: {name}")
    else:
        errors.append("frozen dataset manifest missing from suite")
    if configs and len(set(configs)) != 1:
        errors.append("resolved config hashes differ")
    if environments and len(set(environments)) != 1:
        errors.append("environment hashes differ")
    if data_manifests and len(set(data_manifests)) != 1:
        errors.append("dataset manifest hashes differ")
    return {
        "source_sha256": next(iter(source_hashes)) if len(source_hashes) == 1 else None,
        "source_file_map_entries": len(source_maps[0]) if source_maps else 0,
        "source_file_map_identical": bool(source_maps)
        and all(value == source_maps[0] for value in source_maps),
        "config_sha256": config_hash,
        "environment_sha256": environment_hash,
        "dataset_manifest_sha256": data_hash,
    }


def checkpoint_dirs(cell_dir: Path, variant: str) -> dict[int, Path]:
    return {step: cell_dir / f"checkpoint-{step}" for step in EXPECTED_CHECKPOINTS[variant]}


def inspect_snapshot(
    cell: tuple[int, int, int, str],
    cell_dir: Path,
    step: int,
    path: Path,
    errors: list[str],
) -> dict[str, Any] | None:
    if not (path / "state.pt").is_file() or not (path / "index.json").is_file():
        errors.append(f"missing snapshot state/index: {cell}/{step}")
        return None
    index = read_json(path / "index.json")
    state_hash = sha256(path / "state.pt")
    if index.get("state_sha256") != state_hash:
        errors.append(f"snapshot index hash mismatch: {cell}/{step}")
    result = read_json(cell_dir / "result.json")
    if result["checkpoint_state_sha256"].get(path.name) != state_hash:
        errors.append(f"result checkpoint hash mismatch: {cell}/{step}")
    state = torch.load(path / "state.pt", weights_only=True, map_location="cpu")
    model = state["model"]
    flags = state["requires_grad"]
    variant = cell[3]
    if any(not bool(torch.isfinite(tensor).all()) for tensor in model.values()):
        errors.append(f"non-finite model tensor: {cell}/{step}")
    if state["counters"] != {
        "additional_step": step,
        "absolute_order_cursor": step * 8,
        "next_cyclic_order_cursor": step * 8 % 2048,
        "additional_targets": step * 512,
    }:
        errors.append(f"snapshot counter mismatch: {cell}/{step}")
    param_count = sum(t.numel() for name, t in model.items() if name in flags)
    trainable_count = sum(t.numel() for name, t in model.items() if flags.get(name) is True)
    frozen_count = sum(t.numel() for name, t in model.items() if name.startswith("backbone."))
    if (
        frozen_count != 27392
        or trainable_count != EXPECTED_ADDITION[variant]
        or param_count != 27392 + EXPECTED_ADDITION[variant]
    ):
        errors.append(f"snapshot parameter counts mismatch: {cell}/{step}")
    if any(flags.get(name) is not False for name in flags if name.startswith("backbone.")):
        errors.append(f"backbone requires_grad flags changed: {cell}/{step}")
    expected_addition_names = {
        FLAT: {"addition.keys", "addition.values", "addition.wq", "addition.wo", "addition.gate"},
        FIXED: {"addition.keys", "addition.values", "addition.wq", "addition.wo", "addition.gate"},
        LEARNED: {
            "addition.keys",
            "addition.values",
            "addition.wq",
            "addition.wo",
            "addition.gate",
            "addition.router",
        },
        DENSE: {"addition.w1", "addition.w2", "addition.gate"},
        BASELINE: set(),
    }[variant]
    actual_trainable = {name for name, value in flags.items() if value is True}
    expected_flag_names = set(model) - ({"addition.router"} if variant == FIXED else set())
    if set(flags) != expected_flag_names:
        errors.append(f"requires_grad name inventory mismatch: {cell}/{step}")
    if actual_trainable != expected_addition_names:
        errors.append(f"trainable parameter names mismatch: {cell}/{step}")
    expected_shapes = {
        FLAT: {
            "addition.keys": (4096, 16),
            "addition.values": (4096, 32),
            "addition.wq": (16, 32),
            "addition.wo": (32, 32),
            "addition.gate": (),
        },
        FIXED: {
            "addition.keys": (4096, 16),
            "addition.values": (4096, 32),
            "addition.wq": (16, 32),
            "addition.wo": (32, 32),
            "addition.gate": (),
            "addition.router": (16, 16),
        },
        LEARNED: {
            "addition.keys": (4096, 16),
            "addition.values": (4096, 32),
            "addition.wq": (16, 32),
            "addition.wo": (32, 32),
            "addition.gate": (),
            "addition.router": (16, 16),
        },
        DENSE: {"addition.w1": (3100, 32), "addition.w2": (32, 3100), "addition.gate": ()},
    }
    for name, shape in expected_shapes.get(variant, {}).items():
        if (
            name not in model
            or tuple(model[name].shape) != shape
            or model[name].dtype != torch.float32
        ):
            errors.append(f"addition tensor shape/dtype mismatch: {cell}/{step}/{name}")
    if variant == FIXED:
        router = model.get("addition.router")
        if router is None or "addition.router" in flags:
            errors.append(f"fixed router buffer/flag missing: {cell}/{step}")
    if (state["bypass"] is True) != (variant == BASELINE):
        errors.append(f"snapshot bypass flag mismatch: {cell}/{step}")
    optimizer = state["optimizer"]
    if variant == BASELINE:
        if optimizer is not None or state["optimizer_parameter_names"]:
            errors.append(f"baseline optimizer exists: {cell}/{step}")
    else:
        if not isinstance(optimizer, dict) or len(optimizer["param_groups"]) != 1:
            errors.append(f"optimizer group count mismatch: {cell}/{step}")
        else:
            group = optimizer["param_groups"][0]
            options = {name: value for name, value in group.items() if name != "params"}
            if options != OPTIMIZER_OPTIONS:
                errors.append(f"optimizer options mismatch: {cell}/{step}")
            if len(group["params"]) != len(expected_addition_names) or len(
                set(group["params"])
            ) != len(group["params"]):
                errors.append(f"optimizer membership length/uniqueness mismatch: {cell}/{step}")
            optimizer_names = state["optimizer_parameter_names"]
            if optimizer_names != [name for name in flags if flags[name]]:
                errors.append(f"optimizer ordered names mismatch: {cell}/{step}")
            optim_states = optimizer["state"]
            normalized_state_ids = {int(parameter_id) for parameter_id in optim_states}
            expected_state_ids = set(group["params"]) if step > 0 else set()
            if normalized_state_ids != expected_state_ids:
                errors.append(f"optimizer state ID set mismatch: {cell}/{step}")
            if step == 0 and optim_states:
                errors.append(f"step-zero optimizer moments are not empty: {cell}")
            if step > 0:
                if len(optim_states) != len(expected_addition_names):
                    errors.append(f"optimizer state count mismatch: {cell}/{step}")
                for parameter_id, parameter_name in zip(
                    group["params"], optimizer_names, strict=True
                ):
                    moment = optim_states.get(parameter_id, optim_states.get(str(parameter_id)))
                    if moment is None or set(moment) != {"step", "exp_avg", "exp_avg_sq"}:
                        errors.append(f"AdamW moment fields missing: {cell}/{step}/{parameter_id}")
                        continue
                    if (
                        moment["step"].shape != torch.Size([])
                        or moment["step"].dtype != torch.float32
                        or float(moment["step"].item()) != float(step)
                    ):
                        errors.append(f"AdamW step clock mismatch: {cell}/{step}/{parameter_id}")
                    if any(
                        tuple(moment[name].shape) != tuple(model[parameter_name].shape)
                        or moment[name].dtype != model[parameter_name].dtype
                        for name in ("exp_avg", "exp_avg_sq")
                    ):
                        errors.append(
                            f"AdamW moment shape mismatch: {cell}/{step}/{parameter_name}"
                        )
                    if (
                        not torch.isfinite(moment["exp_avg"]).all()
                        or not torch.isfinite(moment["exp_avg_sq"]).all()
                    ):
                        errors.append(f"non-finite AdamW moments: {cell}/{step}/{parameter_id}")
    identity = state["identity"]
    if identity["cell"] != {
        "backbone": cell[0],
        "order": cell[1],
        "seed": cell[2],
        "variant": variant,
    }:
        errors.append(f"checkpoint cell identity mismatch: {cell}/{step}")
    if sha256(cell_dir / "order.json") != identity["order_sha256"]:
        errors.append(f"checkpoint order identity mismatch: {cell}/{step}")
    if identity["backbone_sha256"] != independent_backbone_digest(model):
        errors.append(f"frozen backbone+causal-mask digest mismatch: {cell}/{step}")
    return state


def inspect_all_snapshots(
    cells: dict[tuple[int, int, int, str], Path], errors: list[str]
) -> tuple[dict[tuple[int, int, int, str, int], dict[str, Any]], dict[str, Any]]:
    states, count = {}, 0
    for cell, cell_dir in cells.items():
        for step, path in checkpoint_dirs(cell_dir, cell[3]).items():
            state = inspect_snapshot(cell, cell_dir, step, path, errors)
            if state is not None:
                states[(*cell, step)] = state
                count += 1
    if count != 333:
        errors.append(f"actual snapshot count mismatch: expected 333, found {count}")
    for cell in cells:
        for step in EXPECTED_CHECKPOINTS[cell[3]][1:]:
            before = states.get((*cell, 0))
            after = states.get((*cell, step))
            if before is None or after is None:
                continue
            for name, tensor in before["model"].items():
                if name.startswith("backbone.") and not same_tensor(tensor, after["model"][name]):
                    errors.append(f"frozen backbone tensor changed: {cell}/{step}/{name}")
                if (
                    cell[3] == FIXED
                    and name == "addition.router"
                    and not same_tensor(tensor, after["model"][name])
                ):
                    errors.append(f"fixed router buffer changed: {cell}/{step}")
    return states, {"actual_snapshots_checked": count}


def check_shared_initializations(
    states: dict[tuple[int, int, int, str, int], dict[str, Any]], errors: list[str]
) -> dict[str, int]:
    groups = 0
    common = ("addition.keys", "addition.values", "addition.wq", "addition.wo", "addition.gate")
    canonical: dict[tuple[int, str, str], torch.Tensor] = {}
    canonical_rng: dict[tuple[int, str], tuple[torch.Tensor, object]] = {}
    for b in BACKBONES:
        for o in ORDERS:
            for seed in SEEDS:
                flat = states[b, o, seed, FLAT, 0]["model"]
                fixed = states[b, o, seed, FIXED, 0]["model"]
                learned = states[b, o, seed, LEARNED, 0]["model"]
                for name in common:
                    if not same_tensor(flat[name], fixed[name]) or not same_tensor(
                        flat[name], learned[name]
                    ):
                        errors.append(f"fresh A/B/C init mismatch: {(b, o, seed)}/{name}")
                if not same_tensor(fixed["addition.router"], learned["addition.router"]):
                    errors.append(f"fixed/learned router init mismatch: {(b, o, seed)}")
                for variant, names in (
                    (FLAT, common),
                    (FIXED, common + ("addition.router",)),
                    (LEARNED, common + ("addition.router",)),
                    (DENSE, ("addition.w1", "addition.w2", "addition.gate")),
                ):
                    model_state = states[b, o, seed, variant, 0]["model"]
                    for name in names:
                        key = (seed, variant, name)
                        if key not in canonical:
                            canonical[key] = model_state[name]
                        elif not same_tensor(canonical[key], model_state[name]):
                            errors.append(
                                "fresh seed initialization differs across parents: "
                                f"{(b, o, seed, variant, name)}"
                            )
                rng = states[b, o, seed, FLAT, 0]["torch_rng"]
                py_rng = states[b, o, seed, FLAT, 0]["python_rng"]
                if seed not in canonical_rng:
                    canonical_rng[seed] = (rng, py_rng)
                elif (
                    not same_tensor(canonical_rng[seed][0], rng) or canonical_rng[seed][1] != py_rng
                ):
                    errors.append(f"step-zero RNG differs across parents for seed {seed}")
                for variant in (FLAT, FIXED, LEARNED, DENSE):
                    if not same_tensor(rng, states[b, o, seed, variant, 0]["torch_rng"]):
                        errors.append(
                            f"step-zero Torch RNG differs across variants: {(b, o, seed)}"
                        )
                    if py_rng != states[b, o, seed, variant, 0]["python_rng"]:
                        errors.append(
                            f"step-zero Python RNG differs across variants: {(b, o, seed)}"
                        )
                    baseline_backbone = states[b, o, 0, BASELINE, 0]["model"]
                    trained_backbone = states[b, o, seed, variant, 0]["model"]
                    if any(
                        not same_tensor(baseline_backbone[name], tensor)
                        for name, tensor in trained_backbone.items()
                        if name.startswith("backbone.")
                    ):
                        errors.append(
                            "trainable addition backbone differs from P5 baseline: "
                            f"{(b, o, seed, variant)}"
                        )
                groups += 1
    for cell in [cell for cell in states if cell[-1] in (256, 512)]:
        state = states[cell]
        initial_key = (*cell[:-1], 0)
        if not same_tensor(states[initial_key]["torch_rng"], state["torch_rng"]):
            errors.append(f"training changed saved Torch RNG: {cell}")
    return {"seeded_initialization_groups_checked": groups}


def check_parent_hashes(
    cells: dict[tuple[int, int, int, str], Path],
    states: dict[tuple[int, int, int, str, int], dict[str, Any]],
    errors: list[str],
) -> dict[str, int]:
    parents: dict[tuple[int, int], dict[str, Any]] = {}
    for (b, o, _seed, _variant), path in cells.items():
        provenance = read_json(path / "parent_provenance.json")
        parent = provenance
        key = (b, o)
        if key in parents and parents[key] != parent:
            errors.append(f"parent provenance differs among paired cells: {key}")
        parents[key] = parent
        for prefix, name in (
            ("checkpoint_state_sha256", "state.pt"),
            ("checkpoint_index_sha256", "index.json"),
        ):
            actual_path = Path(parent["checkpoint_path"]) / name
            if not actual_path.is_file() or sha256(actual_path) != parent[prefix]:
                errors.append(f"physical P4 parent hash mismatch: {key}/{name}")
        upstream = parent.get("upstream_p3", {})
        for prefix, name in (
            ("checkpoint_state_sha256", "state.pt"),
            ("checkpoint_index_sha256", "index.json"),
        ):
            actual_path = Path(upstream.get("checkpoint_path", "")) / name
            if not actual_path.is_file() or sha256(actual_path) != upstream.get(prefix):
                errors.append(f"physical P3 parent hash mismatch: {key}/{name}")
    if len(parents) != 9:
        errors.append(f"parent count mismatch: expected 9, found {len(parents)}")
    for (b, o), provenance in parents.items():
        p4_state = torch.load(
            Path(provenance["checkpoint_path"]) / "state.pt",
            weights_only=True,
            map_location="cpu",
        )
        p4_model = p4_state.get("model", {})
        p5_model = states[b, o, 0, BASELINE, 0]["model"]
        for name, tensor in p5_model.items():
            if name.startswith("backbone.") and (
                name not in p4_model or not same_tensor(tensor, p4_model[name])
            ):
                errors.append(f"P5 frozen baseline differs from actual P4 parent: {(b, o)}/{name}")
    return {"physical_parent_pairs_checked": len(parents)}


def check_permutations(cells: dict[tuple[int, int, int, str], Path], errors: list[str]) -> int:
    checked = 0
    for cell, directory in cells.items():
        b, o, seed, variant = cell
        if variant not in (FLAT, FIXED, LEARNED):
            continue
        index = (b - 101) * 9 + (o - 301) * 3 + (seed - 501)
        for condition, offset in (("values_permuted", 60000), ("joint_within_branch", 70000)):
            path = directory / f"permutation-{condition}.json"
            evidence = read_json(path)
            generator_seed = offset + index
            generator = torch.Generator(device="cpu").manual_seed(generator_seed)
            if condition == "values_permuted" or variant == FLAT:
                ids = torch.randperm(4096, generator=generator, device="cpu")
            else:
                ids = torch.cat(
                    [
                        branch * 256 + torch.randperm(256, generator=generator, device="cpu")
                        for branch in range(16)
                    ]
                )
            if (
                evidence.get("condition") != condition
                or evidence.get("generator_seed") != generator_seed
                or evidence.get("permutation_ids") != ids.tolist()
            ):
                errors.append(f"registered permutation mismatch: {cell}/{condition}")
            recorded = read_json(directory / "result.json")["interventions"][condition][
                "permutation"
            ]
            if recorded.get("file") != path.name or recorded.get("sha256") != sha256(path):
                errors.append(f"permutation result evidence hash mismatch: {cell}/{condition}")
            checked += 1
    return checked


def compare_raw_compact(
    cells: dict[tuple[int, int, int, str], Path],
    results: Path,
    quality_suite: Path,
    errors: list[str],
) -> dict[str, int]:
    cell_files = [
        "manifest.json",
        "terminal.json",
        "result.json",
        "source.json",
        "environment.json",
        "config.resolved.json",
        "dataset_manifest.json",
        "order.json",
        "parent_provenance.json",
        "metrics.jsonl",
        "permutation-values_permuted.json",
        "permutation-joint_within_branch.json",
        "checkpoint-0/index.json",
        "checkpoint-256/index.json",
        "checkpoint-512/index.json",
    ]
    quality_rows = read_json(quality_suite / "cells.json")
    by_label = {row["label"]: row for row in quality_rows}
    comparisons = 0
    raw_quality = quality_suite
    for cell, compact in cells.items():
        label = compact.name
        row = by_label.get(label)
        if row is None:
            errors.append(f"missing quality status mapping for {label}")
            continue
        raw = raw_quality / "cells" / row["run_id"]
        raw_archive = raw / "source.tar"
        if not raw_archive.is_file() or sha256(raw_archive) != EXPECTED_ARCHIVE:
            errors.append(f"raw cell source.tar differs from frozen archive: {label}")
        if not (raw / "source.diff").is_file() or (raw / "source.diff").read_bytes() != b"":
            errors.append(f"raw cell source.diff missing or nonempty: {label}")
        for name in cell_files:
            if cell[3] not in (FLAT, FIXED, LEARNED) and name.startswith("permutation-"):
                continue
            if (
                name in {"checkpoint-256/index.json", "checkpoint-512/index.json"}
                and cell[3] == BASELINE
            ):
                continue
            raw_file, compact_file = raw / name, compact / name
            if not raw_file.is_file() or not compact_file.is_file():
                errors.append(f"raw/compact evidence file missing: {label}/{name}")
            elif sha256(raw_file) != sha256(compact_file):
                errors.append(f"raw/compact evidence differs: {label}/{name}")
            else:
                comparisons += 1
    quality_export = results / "quality-suite"
    for name in (
        "config.resolved.json",
        "source.json",
        "environment.json",
        "cells.json",
        "metrics.jsonl",
        "result.json",
        "parent_provenance.json",
        "baselines.json",
        "frozen-data/dataset_manifest.json",
    ):
        a, b = raw_quality / name, quality_export / name
        if not a.is_file() or not b.is_file() or sha256(a) != sha256(b):
            errors.append(f"raw/compact quality-suite evidence differs or missing: {name}")
        else:
            comparisons += 1
    return {"raw_compact_files_compared": comparisons}


def compare_timing_raw_compact(suite: Path, results: Path, errors: list[str]) -> dict[str, int]:
    status_path = suite / "timing-status.json"
    if not status_path.is_file():
        errors.append("timing status file is missing")
        return {"timing_raw_compact_files_compared": 0}
    rows = read_json(status_path)["workers"]
    files = (
        "manifest.json",
        "terminal.json",
        "result.json",
        "source.json",
        "environment.json",
        "config.resolved.json",
        "dataset_manifest.json",
        "metrics.jsonl",
        "timing_inputs.json",
        "quality_checkpoint_provenance.json",
    )
    comparisons = 0
    source_maps = []
    frozen_source_map = read_json(
        Path("results/p5-preflight-2026-11-13/execution-freeze/source.json")
    )["archive_file_sha256"]
    for row in rows:
        if row.get("status") != "completed" or not row.get("run_id"):
            errors.append(f"timing worker incomplete in status file: {row.get('label')}")
            continue
        raw = suite / "timing-workers" / row["run_id"]
        compact = results / "timing" / row["label"]
        if not raw.is_dir() or not compact.is_dir():
            errors.append(f"raw/compact timing worker folder missing: {row['label']}")
            continue
        for name in files:
            a, b = raw / name, compact / name
            if not a.is_file() or not b.is_file() or sha256(a) != sha256(b):
                errors.append(
                    f"raw/compact timing evidence differs or missing: {row['label']}/{name}"
                )
            else:
                comparisons += 1
        source = read_json(raw / "source.json")
        source_maps.append(source["archive_file_sha256"])
        timing_archive = raw / "source.tar"
        if not timing_archive.is_file() or sha256(timing_archive) != EXPECTED_ARCHIVE:
            errors.append(f"timing source.tar differs from frozen archive: {row['label']}")
        if (
            source["archive"]["sha256"] != EXPECTED_ARCHIVE
            or len(source_maps[-1]) != SOURCE_FILES_EXPECTED
        ):
            errors.append(f"timing worker source identity/file map mismatch: {row['label']}")
        if source_maps[-1] != frozen_source_map:
            errors.append(f"timing source map differs from frozen source map: {row['label']}")
        if (raw / "source.diff").read_bytes() != b"":
            errors.append(f"timing worker source.diff is nonempty: {row['label']}")
        report = read_json(raw / "result.json")
        if report.get("training_targets") != 0 or report.get("scientific_evaluation_targets") != 0:
            errors.append(
                f"timing worker contains training/scientific evaluation targets: {row['label']}"
            )
        if report.get("state_and_rng_unchanged") is not True:
            errors.append(f"timing worker state/RNG preservation flag missing: {row['label']}")
        for variant, evidence in report["quality_checkpoint_provenance"].items():
            for key, filename in (("state_sha256", "state.pt"), ("index_sha256", "index.json")):
                target = Path(evidence["path"]) / filename
                if not target.is_file() or sha256(target) != evidence[key]:
                    errors.append(
                        f"timing changed P5 quality checkpoint: {row['label']}/{variant}/{filename}"
                    )
            parent = evidence["checkpoint_identity"]["parent"]
            for parent_record in (parent, parent["upstream_p3"]):
                for key, filename in (
                    ("checkpoint_state_sha256", "state.pt"),
                    ("checkpoint_index_sha256", "index.json"),
                ):
                    target = Path(parent_record["checkpoint_path"]) / filename
                    if not target.is_file() or sha256(target) != parent_record[key]:
                        errors.append(
                            f"timing changed parent checkpoint: {row['label']}/{filename}"
                        )
    if len(rows) != 36 or len(source_maps) != 36:
        errors.append(f"timing raw/compact worker count mismatch: {len(rows)}")
    if source_maps and any(value != source_maps[0] for value in source_maps):
        errors.append("timing source file maps differ between workers")
    for name in (
        "result.json",
        "timing-status.json",
        "metrics.jsonl",
        "expected_ack.json",
        "terminal.json",
    ):
        a, b = suite / name, results / "suite" / name
        if not a.is_file() or not b.is_file() or sha256(a) != sha256(b):
            errors.append(f"raw/compact suite timing evidence differs or missing: {name}")
        else:
            comparisons += 1
    return {"timing_raw_compact_files_compared": comparisons}


def audit_operand_traces(results: Path, errors: list[str]) -> int:
    checked = 0
    trained_workers = 0
    for result_path in sorted((results / "timing").glob("*/result.json")):
        report = read_json(result_path)
        if report.get("seed") == 0:
            continue
        trained_workers += 1
        for variant in (FLAT, FIXED, LEARNED):
            if variant not in report.get("traces", {}):
                errors.append(f"missing memory operand traces: {result_path}/{variant}")
                continue
            for size_label in ("8", "1"):
                for batch_index, trace in enumerate(report["traces"][variant][size_label]):
                    n = int(size_label) * 64
                    events = trace["operators"]

                    def matching(
                        operation: str | tuple[str, ...], input_shape: list[int]
                    ) -> list[dict[str, Any]]:
                        names = (operation,) if isinstance(operation, str) else operation
                        return [
                            event
                            for event in events
                            if event["operator"] in names
                            and event["args"]
                            and event["args"][0].get("shape") == input_shape
                        ]

                    value_gathers = matching("aten.index.Tensor", [4096, 32])
                    if (
                        trace.get("queries") != n
                        or trace.get("validated") is not True
                        or trace.get("selected_values_per_query") != 8
                        or len(value_gathers) != 1
                        or value_gathers[0]["args"][1][0].get("shape") != [n, 8]
                        or value_gathers[0]["result"].get("shape") != [n, 8, 32]
                    ):
                        errors.append(
                            "invalid traced value gather: "
                            f"{result_path}/{variant}/{size_label}/{batch_index}"
                        )
                        continue
                    expected_summary = (
                        (4096, 0, 4096 * 16, 0) if variant == FLAT else (512, 16, 512 * 16, 16 * 16)
                    )
                    actual_summary = (
                        trace.get("key_dot_products_per_query"),
                        trace.get("router_dot_products_per_query"),
                        trace.get("candidate_key_elements_per_query"),
                        trace.get("router_elements_per_query"),
                    )
                    if actual_summary != expected_summary:
                        errors.append(
                            "operand-derived logical-work summary mismatch: "
                            f"{result_path}/{variant}/{size_label}/{batch_index}"
                        )
                    if variant == FLAT:
                        score_topk = [
                            event
                            for event in events
                            if event["operator"] == "aten.topk.default"
                            and event["args"][0].get("shape") == [n, 4096]
                            and event["args"][1] == 9
                            and [part.get("shape") for part in event["result"]] == [[n, 9], [n, 9]]
                        ]
                        top_gathers = [
                            event
                            for event in events
                            if event["operator"] == "aten.gather.default"
                            and event["args"][0].get("shape") == [n, 4096]
                            and event["args"][2].get("shape") == [n, 8]
                            and event["result"].get("shape") == [n, 8]
                        ]
                        if len(score_topk) != 1 or len(top_gathers) != 1:
                            errors.append(
                                "invalid flat top-8 score selection operands: "
                                f"{result_path}/{size_label}/{batch_index}"
                            )
                        score = matching(("aten.mm.default", "aten.matmul.default"), [n, 16])
                        key_norm = matching("aten.linalg_vector_norm.default", [4096, 16])
                        if (
                            len(score) != 1
                            or score[0]["args"][1].get("shape") != [16, 4096]
                            or score[0]["result"].get("shape") != [n, 4096]
                            or len(key_norm) != 1
                            or trace.get("candidate_union") != 4096
                            or trace.get("router_dot_products_per_query") != 0
                        ):
                            errors.append(
                                "invalid flat score/key operands: "
                                f"{result_path}/{size_label}/{batch_index}"
                            )
                    else:
                        top_gathers = [
                            event
                            for event in events
                            if event["operator"] == "aten.gather.default"
                            and event["args"][0].get("shape") == [n, 512]
                            and event["args"][2].get("shape") == [n, 8]
                            and event["result"].get("shape") == [n, 8]
                        ]
                        branch_topk = [
                            event
                            for event in events
                            if event["operator"] == "aten.topk.default"
                            and (
                                (
                                    event["args"][0].get("shape") == [n, 16]
                                    and event["args"][1] == 3
                                    and event["result"][0].get("shape") == [n, 3]
                                )
                                or (
                                    event["args"][0].get("shape") == [n, 512]
                                    and event["args"][1] == 9
                                    and event["result"][0].get("shape") == [n, 9]
                                )
                            )
                        ]
                        if len(top_gathers) != 2 or len(branch_topk) != 2:
                            errors.append(
                                "invalid tree top-8 score selection operands: "
                                f"{result_path}/{variant}/{size_label}/{batch_index}"
                            )
                        route = matching(("aten.mm.default", "aten.matmul.default"), [n, 16])
                        score = matching("aten.bmm.default", [n, 512, 16])
                        route_norm = matching("aten.linalg_vector_norm.default", [16, 16])
                        key_norm = matching("aten.linalg_vector_norm.default", [n, 512, 16])
                        key_gathers = matching("aten.index.Tensor", [4096, 16])
                        if (
                            len(route) != 1
                            or route[0]["args"][1].get("shape") != [16, 16]
                            or route[0]["result"].get("shape") != [n, 16]
                            or len(score) != 1
                            or score[0]["args"][1].get("shape") != [n, 16, 1]
                            or score[0]["result"].get("shape") != [n, 512, 1]
                            or len(route_norm) != 1
                            or len(key_norm) != 1
                            or len(key_gathers) != 1
                            or key_gathers[0]["args"][1][0].get("shape") != [n, 512]
                            or key_gathers[0]["result"].get("shape") != [n, 512, 16]
                            or trace.get("router_dot_products_per_query") != 16
                        ):
                            errors.append(
                                "invalid tree route/candidate operands: "
                                f"{result_path}/{variant}/{size_label}/{batch_index}"
                            )
                    checked += 1
    if trained_workers != 27:
        errors.append(f"operand trace worker count mismatch: expected 27, found {trained_workers}")
    if checked != 27 * 3 * 2 * 4:
        errors.append(f"operand trace count mismatch: expected 648, found {checked}")
    return checked


def exact_restore_examples(cells: dict[tuple[int, int, int, str], Path], errors: list[str]) -> int:
    """Load representative snapshots into modules; deliberately never calls forward."""
    from arborlm.p2_config import CONTROL as P2_CONTROL
    from arborlm.p2_config import Cell as P2Cell
    from arborlm.p2_model import FollowupModel
    from arborlm.p4_model import Backbone
    from arborlm.p5_checkpoint import restore
    from arborlm.p5_config import Cell as P5Cell
    from arborlm.p5_model import Model, optimizer_for

    chosen = [
        (101, 301, 0, BASELINE, 0),
        (101, 301, 501, FLAT, 512),
        (101, 301, 501, FIXED, 512),
        (101, 301, 501, LEARNED, 256),
        (101, 301, 501, DENSE, 512),
    ]
    python_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    count = 0
    try:
        for b, o, seed, variant, step in chosen:
            identity_key = (b, o, seed, variant)
            path = cells[identity_key] / f"checkpoint-{step}"
            snapshot = torch.load(path / "state.pt", weights_only=True, map_location="cpu")
            base = FollowupModel(P2Cell(b, 201, o, P2_CONTROL))
            backbone = Backbone(base)
            state = snapshot["model"]
            prefix = "backbone."
            backbone.load_state_dict(
                {
                    name.removeprefix(prefix): tensor
                    for name, tensor in state.items()
                    if name.startswith(prefix)
                },
                strict=True,
            )
            model = Model(P5Cell(b, o, seed, variant), backbone)
            optimizer = optimizer_for(model)
            counters = restore(path, model, optimizer, snapshot["identity"])
            if counters != snapshot["counters"]:
                errors.append(
                    f"representative strict restore counters differ: {identity_key}/{step}"
                )
            loaded = model.state_dict()
            for name, tensor in state.items():
                if name not in loaded or not same_tensor(tensor, loaded[name]):
                    errors.append(
                        "representative strict restore tensor differs: "
                        f"{identity_key}/{step}/{name}"
                    )
            if optimizer is not None and not same_value(
                optimizer.state_dict(), snapshot["optimizer"]
            ):
                errors.append(f"representative optimizer restore differs: {identity_key}/{step}")
            count += 1
    except Exception as exc:  # audit should report restore failure and continue finalization
        errors.append(f"representative strict restore failed: {type(exc).__name__}: {exc}")
    finally:
        random.setstate(python_rng)
        torch.set_rng_state(torch_rng)
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/p5-2026-11-13"))
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("experiments/P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be"),
    )
    args = parser.parse_args()
    errors: list[str] = []
    compact_cells = cells_from_results(args.results, errors)
    quality_suite = (
        args.suite / "quality" / "P5QUALITY-20261113T125206040450Z-aa1f203f012e4112bf137cd09944bb92"
    )
    raw_cells = raw_cells_from_compact(compact_cells, quality_suite, errors)
    identities = validate_source_and_inputs(compact_cells, quality_suite, errors)
    states, checkpoint_counts = inspect_all_snapshots(raw_cells, errors)
    init_counts = check_shared_initializations(states, errors)
    parent_counts = check_parent_hashes(raw_cells, states, errors)
    permutation_count = check_permutations(raw_cells, errors)
    compact_counts = compare_raw_compact(compact_cells, args.results, quality_suite, errors)
    timing_compact_counts = compare_timing_raw_compact(args.suite, args.results, errors)
    restore_count = exact_restore_examples(raw_cells, errors)
    trace_count = audit_operand_traces(args.results, errors)
    output = {
        "audit": "P5 artifact integrity; no forwards",
        "source_and_inputs": identities,
        "snapshots": checkpoint_counts,
        "initialization": init_counts,
        "parents": parent_counts,
        "permutations_checked": permutation_count,
        "raw_compact": compact_counts,
        "timing_raw_compact": timing_compact_counts,
        "representative_no_forward_restores": restore_count,
        "operator_operand_traces_checked": trace_count,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
