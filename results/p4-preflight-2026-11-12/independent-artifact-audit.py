"""Read-only integrity audit of registered P4 checkpoints and run records."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch

ROOT = Path.cwd()
DEFAULT_SUITE = ROOT / "experiments/P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd"
P3 = ROOT / "experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d"
P3_COMPACT = ROOT / "results/p3-lt-2026-11-12"
EXPECTED_SOURCE = "18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0"
SOURCE_FREEZE = "812b3fd02d81124b0665cc96d1364a32e40d403d"
EXPECTED_PANEL = "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f"
EXPECTED_TRAIN = "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
EXPECTED_P3_PANEL = "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0"
EXPECTED_P1_PANEL = "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200"
EXPECTED_P2_PANEL = "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2"


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bitwise_equal(left: torch.Tensor, right: torch.Tensor) -> bool:
    return (
        left.shape == right.shape
        and left.dtype == right.dtype
        and torch.equal(
            left.detach().contiguous().reshape(-1).view(torch.uint8),
            right.detach().contiguous().reshape(-1).view(torch.uint8),
        )
    )


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def canonical_backbone_digest(model_state: dict[str, torch.Tensor]) -> str:
    """Hash names, shapes, dtypes and raw bytes, including the nonpersistent mask."""
    tensors = {
        name.removeprefix("backbone."): tensor
        for name, tensor in model_state.items()
        if name.startswith("backbone.")
    }
    tensors["mask"] = torch.full((64, 64), -torch.inf, dtype=torch.float32).triu(1)
    result = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        result.update(
            canonical_json({"name": name, "shape": list(tensor.shape), "dtype": str(tensor.dtype)})
        )
        result.update(
            bytes(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist())
        )
    return result.hexdigest()


def distribution(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def audit(suite: Path, *, allow_partial: bool) -> dict[str, Any]:
    issues: list[str] = []
    rows = read(suite / "cells.json")
    manifest = read(suite / "manifest.json")
    result = read(suite / "result.json") if (suite / "result.json").exists() else {}
    statuses = Counter(row["status"] for row in rows)
    expected_cells = {
        (backbone, order, seed, variant)
        for backbone in (101, 102, 103)
        for order in (301, 302, 303)
        for seed, variant in [
            (0, "baseline"),
            *[(seed, variant) for seed in (401, 402, 403) for variant in ("memory", "dense")],
        ]
    }
    actual_cells = {(row["backbone"], row["order"], row["seed"], row["variant"]) for row in rows}
    if len(rows) != 63 or actual_cells != expected_cells:
        issues.append("registered 63-cell grid")
    if not allow_partial and statuses != Counter({"completed": 63}):
        issues.append(f"suite cell statuses {dict(statuses)}")
    if manifest.get("source_sha256") != EXPECTED_SOURCE:
        issues.append("suite source archive identity")

    accepted = read(ROOT / "results/p4-preflight-2026-11-12/accepted-source-files.json")
    accepted_hashes: dict[str, str] = accepted["sha256"]
    if accepted.get("status") != "PASS" or len(accepted_hashes) != 55:
        issues.append("root accepted-source-files record")

    p3_rows = read(P3 / "cells.json")
    p3_by_label = {
        row["label"]: row for row in p3_rows if row["condition"] == "disabled_throughout"
    }
    p3_source_path = P3 / "cells" / p3_by_label["b101-o301-control"]["run_id"] / "source.json"
    p3_source_hashes = read(p3_source_path)["archive_file_sha256"]
    p3_common = {
        name: value
        for name, value in p3_source_hashes.items()
        if name.startswith(("src/arborlm/", "tests/", "configs/", "docs/decisions/"))
    }
    if len(p3_common) != 55:
        issues.append(f"P3 preserved source subset count {len(p3_common)}")

    data_dir = suite / "frozen-data"
    data_manifest = read(data_dir / "dataset_manifest.json")
    checksums = data_manifest["checksums_sha256"]
    actual_data_hashes = {name: digest(data_dir / name) for name in checksums}
    if actual_data_hashes != checksums:
        issues.append("frozen data checksum map")
    panel_hash = actual_data_hashes.get("validation.bytes")
    if panel_hash != EXPECTED_PANEL:
        issues.append("P4 panel hash")
    if actual_data_hashes.get("train.bytes") != EXPECTED_TRAIN:
        issues.append("P4 training bytes hash")
    if actual_data_hashes.get("p3_validation_integrity.bytes") != EXPECTED_P3_PANEL:
        issues.append("P3 integrity panel hash")
    if data_manifest.get("earlier_validation_sha256") != [
        EXPECTED_P1_PANEL,
        EXPECTED_P2_PANEL,
        EXPECTED_P3_PANEL,
    ]:
        issues.append("prior validation panel hashes")
    selected = read(data_dir / "validation_first_2048.selected.json")
    if len(selected) != 2048 or [row.get("rank") for row in selected] != list(range(2048)):
        issues.append("selected validation ranks")
    p4_bytes = (data_dir / "validation.bytes").read_bytes()
    if len(p4_bytes) != 512 * 65:
        issues.append("P4 panel byte length")
    else:
        for offset in range(512):
            chunk = p4_bytes[offset * 65 : (offset + 1) * 65]
            if hashlib.sha256(chunk).hexdigest() != selected[1536 + offset].get("chunk_sha256"):
                issues.append(f"P4 selected row hash {offset}")
                break
    if (
        data_manifest.get("exact_overlap_with_earlier_panels") != 0
        or data_manifest.get("exact_overlap_with_full_train") != 0
    ):
        issues.append("declared panel disjointness")

    event_counts: Counter[str] = Counter()
    head_counts: Counter[str] = Counter()
    dirty_counts: Counter[str] = Counter()
    archive_maps: list[dict[str, str]] = []
    init_states: dict[tuple[str, int], list[dict[str, torch.Tensor]]] = defaultdict(list)
    parent_state_hashes: dict[str, str] = {}
    backbone_digests: dict[str, str] = {}
    cell_rows: list[dict[str, Any]] = []

    for row in rows:
        if row["status"] != "completed":
            continue
        label = row["label"]
        run = suite / "cells" / row["run_id"]
        compact = ROOT / row["compact_export"]
        cell_result = read(run / "result.json")
        cell_manifest = read(run / "manifest.json")
        source = read(run / "source.json")
        terminal = read(run / "terminal.json")
        if terminal.get("status") != "completed" or terminal.get("returncode") != 0:
            issues.append(f"{label}: terminal status")
        for key in (
            "source_sha256",
            "spec_sha256",
            "config_sha256",
            "lock_sha256",
            "dataset_manifest_sha256",
            "data_approval_sha256",
            "parent_spec_sha256",
        ):
            if cell_manifest.get(key) != manifest.get(key):
                issues.append(f"{label}: shared {key}")
        source_hash = digest(run / "source.tar")
        if (
            source_hash != EXPECTED_SOURCE
            or source_hash != cell_manifest.get("source_sha256")
            or source_hash != source.get("archive", {}).get("sha256")
        ):
            issues.append(f"{label}: source archive bytes/hash")
        patch = run / "source.diff"
        if patch.read_bytes() or digest(patch) != source.get("patch", {}).get("sha256"):
            issues.append(f"{label}: source diff")
        file_hashes = source["archive_file_sha256"]
        archive_maps.append(file_hashes)
        if len(file_hashes) != 82:
            issues.append(f"{label}: source map count {len(file_hashes)}")
        for name, expected in accepted_hashes.items():
            if file_hashes.get(name) != expected:
                issues.append(f"{label}: accepted source file {name}")
        for name, expected in p3_common.items():
            if file_hashes.get(name) != expected:
                issues.append(f"{label}: preserved P3 source file {name}")
        head = cell_manifest.get("code_commit")
        dirty = cell_manifest.get("dirty")
        head_counts[str(head)] += 1
        dirty_counts[str(dirty)] += 1

        parent_label = f"b{row['backbone']}-o{row['order']}-control"
        p3_row = p3_by_label[parent_label]
        p3_run = P3 / "cells" / p3_row["run_id"]
        p3_state_path = p3_run / "checkpoint-1024" / "state.pt"
        p3_index_path = p3_run / "checkpoint-1024" / "index.json"
        parent_state_hash = digest(p3_state_path)
        parent_index_hash = digest(p3_index_path)
        parent = cell_manifest["checkpoint_identity"]["parent"]
        if parent_state_hash != parent.get(
            "checkpoint_state_sha256"
        ) or parent_index_hash != parent.get("checkpoint_index_sha256"):
            issues.append(f"{label}: P3 parent file changed")
        if cell_result.get("parent_checkpoint_unchanged") is not True:
            issues.append(f"{label}: parent unchanged marker")
        parent_state_hashes[label] = parent_state_hash
        p3_state = torch.load(p3_state_path, map_location="cpu", weights_only=True)

        order = run / "order.json"
        if order.read_bytes() != (p3_run / "order.json").read_bytes():
            issues.append(f"{label}: order differs from P3 parent")
        if digest(order) != cell_manifest.get("order_sha256"):
            issues.append(f"{label}: order hash")

        expected_steps = [0] if row["variant"] == "baseline" else [0, 256, 512]
        if len(cell_result.get("checkpoint_state_sha256", {})) != len(expected_steps):
            issues.append(f"{label}: snapshot count in result")
        for step in expected_steps:
            checkpoint = run / f"checkpoint-{step}"
            state_path = checkpoint / "state.pt"
            index_path = checkpoint / "index.json"
            raw = torch.load(state_path, map_location="cpu", weights_only=True)
            state_hash = digest(state_path)
            index = read(index_path)
            if (
                index.get("state_sha256") != state_hash
                or cell_result["checkpoint_state_sha256"].get(f"checkpoint-{step}") != state_hash
            ):
                issues.append(f"{label}: state hash/index step {step}")
            compact_index = compact / f"checkpoint-{step}/index.json"
            if not compact_index.exists() or compact_index.read_bytes() != index_path.read_bytes():
                issues.append(f"{label}: compact checkpoint index step {step}")
            counters = raw["counters"]
            expected_counters = {
                "additional_step": step,
                "absolute_order_cursor": step * 8,
                "next_cyclic_order_cursor": (step * 8) % 2048,
                "additional_targets": step * 512,
            }
            if counters != expected_counters:
                issues.append(f"{label}: checkpoint counters step {step}")
            expected_cell = {
                "backbone": row["backbone"],
                "order": row["order"],
                "seed": row["seed"],
                "variant": row["variant"],
            }
            if raw["identity"].get("cell") != expected_cell:
                issues.append(f"{label}: checkpoint cell identity step {step}")
            if (
                raw["identity"].get("parent", {}).get("checkpoint_state_sha256")
                != parent_state_hash
            ):
                issues.append(f"{label}: P3 parent identity step {step}")
            if raw["bypass"] is not (row["variant"] == "baseline"):
                issues.append(f"{label}: bypass flag step {step}")

            frozen = {
                name.removeprefix("backbone."): tensor
                for name, tensor in raw["model"].items()
                if name.startswith("backbone.")
            }
            parent_backbone = {
                name: tensor
                for name, tensor in p3_state["model"].items()
                if not name.startswith("memory_state.")
            }
            if set(frozen) != set(parent_backbone) or any(
                not bitwise_equal(frozen[name], tensor) for name, tensor in parent_backbone.items()
            ):
                issues.append(f"{label}: frozen backbone tensor bytes step {step}")
            digest_value = canonical_backbone_digest(raw["model"])
            if digest_value != cell_result.get("backbone_sha256"):
                issues.append(f"{label}: canonical backbone/mask digest step {step}")
            backbone_digests[label] = digest_value

            flags = raw["requires_grad"]
            trainable_names = [name for name, flag in flags.items() if flag]
            if any(name.startswith("backbone.") for name in trainable_names):
                issues.append(f"{label}: trainable backbone parameter")
            if row["variant"] == "baseline":
                if (
                    raw["optimizer"] is not None
                    or raw["optimizer_parameter_names"]
                    or trainable_names
                ):
                    issues.append(f"{label}: baseline has optimizer/trainable parameters")
            else:
                if (
                    trainable_names != raw["optimizer_parameter_names"]
                    or len(trainable_names) != len(set(trainable_names))
                    or any(not name.startswith("addition.") for name in trainable_names)
                ):
                    issues.append(f"{label}: optimizer parameter names/order")
                if sum(raw["model"][name].numel() for name in trainable_names) != 198401:
                    issues.append(f"{label}: trainable parameter count")
                opt_state = raw["optimizer"]["state"]
                if step == 0:
                    if opt_state:
                        issues.append(f"{label}: step-zero optimizer is not fresh")
                else:
                    clocks = {int(state["step"].item()) for state in opt_state.values()}
                    if len(opt_state) != len(trainable_names) or clocks != {step}:
                        issues.append(f"{label}: AdamW membership/clocks step {step}")
                if step == 0:
                    init_states[(row["variant"], row["seed"])].append(
                        {
                            name: tensor.detach().clone()
                            for name, tensor in raw["model"].items()
                            if name.startswith("addition.")
                        }
                    )

        event_rows = [
            json.loads(line) for line in (run / "metrics.jsonl").read_text().splitlines() if line
        ]
        per_cell_events = Counter(event["event"] for event in event_rows)
        event_counts.update(per_cell_events)
        expected_interventions = {"baseline": 1, "memory": 4, "dense": 2}[row["variant"]]
        expected_evals = {
            "parent_restore_integrity": int(row["variant"] == "baseline"),
            "initial_evaluation": int(row["variant"] != "baseline"),
            "final_evaluation": 1,
            "intervention_evaluation": expected_interventions,
        }
        for name, count in expected_evals.items():
            if per_cell_events[name] != count:
                issues.append(f"{label}: event count {name}")
        for event in event_rows:
            if event["event"] in (
                "initial_evaluation",
                "final_evaluation",
                "intervention_evaluation",
                "parent_restore_integrity",
            ):
                if (
                    event.get("target_tokens") != 32768
                    or event.get("training_target_tokens", 0) != 0
                ):
                    issues.append(f"{label}: evaluation target count")
            if event["event"] == "intervention_evaluation":
                if (
                    event.get("panel") != "P4_scientific"
                    or event.get("checkpoint_unchanged") is not True
                ):
                    issues.append(f"{label}: intervention panel/checkpoint integrity")
                if event.get("invariance_passed") is False:
                    issues.append(f"{label}: registered intervention invariance")
            if event["event"] == "parent_restore_integrity":
                if (
                    event.get("panel") != "P3_integrity_only"
                    or event.get("excluded_from_scientific_analysis") is not True
                    or event.get("bitwise_passed") is not True
                    or event.get("nll") != parent.get("original_P3_panel_nll")
                ):
                    issues.append(f"{label}: old P3 integrity evaluation")
        train_events = [event for event in event_rows if event["event"] == "train_step"]
        if row["variant"] == "baseline":
            if train_events or row["additional_training_targets"] != 0 or row["snapshots"] != 1:
                issues.append(f"{label}: baseline training/snapshots")
        else:
            if (
                [event.get("additional_step") for event in train_events] != list(range(1, 513))
                or row["additional_training_targets"] != 262144
                or row["snapshots"] != 3
            ):
                issues.append(f"{label}: training steps/targets/snapshots")
            if any(
                event.get("order_offset_for_update") != ((event["additional_step"] - 1) * 8) % 2048
                or event.get("additional_targets") != event["additional_step"] * 512
                for event in train_events
            ):
                issues.append(f"{label}: training order/counters")
        if row["variant"] == "baseline":
            if len(event_rows) != 3:
                issues.append(f"{label}: baseline event total")
        cell_rows.append(row)

    if len(archive_maps) != len(cell_rows):
        issues.append("per-cell source maps missing")
    elif any(source_map != archive_maps[0] for source_map in archive_maps[1:]):
        issues.append("82-entry source maps differ across cells")
    for name, expected_hash in accepted_hashes.items():
        if archive_maps and archive_maps[0].get(name) != expected_hash:
            issues.append(f"accepted source file mismatch {name}")
    p3_common_matches = (
        sum(archive_maps[0].get(name) == expected_hash for name, expected_hash in p3_common.items())
        if archive_maps
        else 0
    )
    if p3_common_matches != 55:
        issues.append(f"P3 preserved file matches {p3_common_matches}/55")
    for key, states in init_states.items():
        first = states[0]
        if any(
            set(candidate) != set(first)
            or any(not bitwise_equal(candidate[name], first[name]) for name in first)
            for candidate in states[1:]
        ):
            issues.append(f"same-seed addition initialization differs {key}")

    for head in head_counts:
        if head == SOURCE_FREEZE:
            continue
        paths = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", head], text=True
        ).splitlines()
        if any(not path.startswith("results/") for path in paths):
            issues.append(f"post-freeze commit touched non-results paths {head}")

    snapshot_count = sum(row.get("snapshots", 0) for row in cell_rows)
    completed = len(cell_rows)
    if completed == 63:
        expected_event_counts = {
            "train_step": 27648,
            "initial_evaluation": 54,
            "final_evaluation": 63,
            "intervention_evaluation": 171,
            "parent_restore_integrity": 9,
        }
        if dict((key, event_counts[key]) for key in expected_event_counts) != expected_event_counts:
            issues.append("suite total event accounting")
        if snapshot_count != 171:
            issues.append(f"suite snapshot count {snapshot_count}")
        if result.get("counts") != {
            "additional_training_targets": 14155776,
            "snapshots": 171,
            "scientific_evaluations": 288,
            "integrity_evaluations": 9,
        }:
            issues.append("suite compact accounting")

    return {
        "status": "PASS" if not issues else "FAIL",
        "suite_id": suite.name,
        "registered_cells": len(rows),
        "completed_cells": completed,
        "status_counts": dict(statuses),
        "source_archive_sha256": manifest.get("source_sha256"),
        "all_82_file_maps_identical": bool(archive_maps)
        and all(m == archive_maps[0] for m in archive_maps),
        "accepted_source_files_expected": len(accepted_hashes),
        "accepted_source_files_match": len(accepted_hashes) == 55
        and bool(archive_maps)
        and all(archive_maps[0].get(n) == h for n, h in accepted_hashes.items()),
        "p3_preserved_source_files_expected": 55,
        "p3_preserved_source_files_match": p3_common_matches,
        "actual_head_counts": dict(head_counts),
        "dirty_flag_counts": dict(dirty_counts),
        "event_counts": {
            name: event_counts[name]
            for name in (
                "train_step",
                "initial_evaluation",
                "final_evaluation",
                "intervention_evaluation",
                "parent_restore_integrity",
            )
        },
        "snapshots": snapshot_count,
        "panel_sha256": panel_hash,
        "new_panel_rows": 512,
        "parent_state_hashes": parent_state_hashes,
        "same_seed_initialization_groups": {
            f"{variant}-seed{seed}": len(states) for (variant, seed), states in init_states.items()
        },
        "issues": issues,
        "model_forwards_by_auditor": 0,
        "training_updates_by_auditor": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    report = audit(args.suite, allow_partial=args.allow_partial)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
