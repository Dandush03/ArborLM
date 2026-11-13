"""Read-only independent integrity and arithmetic audit for the registered P3-LT run."""

import hashlib
import json
import math
import pathlib
import statistics
import struct
import subprocess
from typing import Any

import torch

ROOT = pathlib.Path(__file__).resolve().parents[2]
P3 = ROOT / "experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d"
P2 = ROOT / "experiments/P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7"
P2_EXPORT = ROOT / "results/p2-2026-11-12"
STEPS = (256, 512, 1024)
BACKBONES, MEMORIES, ORDERS = (101, 102, 103), (201, 202, 203), (301, 302, 303)
CONTROL, LEARNED = "disabled_throughout", "learned_tree"


def read(path: pathlib.Path) -> Any:
    return json.loads(path.read_text())


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return (
            left.shape == right.shape
            and left.dtype == right.dtype
            and torch.equal(
                left.contiguous().reshape(-1).view(torch.uint8),
                right.contiguous().reshape(-1).view(torch.uint8),
            )
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, tuple | list) and isinstance(right, tuple | list):
        return (
            type(left) is type(right)
            and len(left) == len(right)
            and all(same(a, b) for a, b in zip(left, right, strict=True))
        )
    return type(left) is type(right) and left == right


def distribution(values: list[float]) -> dict[str, float | int]:
    return {
        "mean": statistics.mean(values),
        "sample_sd": statistics.stdev(values),
        "minimum": min(values),
        "maximum": max(values),
        "positive": sum(value > 0 for value in values),
        "zero": sum(value == 0 for value in values),
        "negative": sum(value < 0 for value in values),
    }


def decompose(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    grand = statistics.mean(row[metric] for row in rows)
    levels = {
        "backbone": BACKBONES,
        "memory": MEMORIES,
        "order": ORDERS,
    }
    marginal = {
        factor: {
            level: statistics.mean(row[metric] for row in rows if row[factor] == level)
            for level in values
        }
        for factor, values in levels.items()
    }
    residuals = []
    for row in rows:
        fitted = grand + sum(marginal[factor][row[factor]] - grand for factor in levels)
        residuals.append((row[metric] - fitted) ** 2)
    return {
        "grand_mean": grand,
        "marginal_means": marginal,
        "marginal_ranges": {
            factor: max(values.values()) - min(values.values())
            for factor, values in marginal.items()
        },
        "interaction_rms": math.sqrt(statistics.mean(residuals)),
    }


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(left, right, rel_tol=0, abs_tol=tolerance)


def main() -> None:
    issues: list[str] = []
    p3_status = read(P3 / "cells.json")
    p2_status = read(P2 / "cells.json")
    p3_manifest = read(P3 / "manifest.json")
    p3_result = read(P3 / "result.json")
    parent_bundle = read(P3 / "parent_provenance.json")
    p2_by_cell = {
        (row["backbone"], row["memory"], row["order"], row["condition"]): row for row in p2_status
    }
    expected = {(b, 201, o, CONTROL) for b in BACKBONES for o in ORDERS} | {
        (b, m, o, LEARNED) for b in BACKBONES for m in MEMORIES for o in ORDERS
    }
    actual = {(row["backbone"], row["memory"], row["order"], row["condition"]) for row in p3_status}
    if (
        len(p3_status) != 36
        or actual != expected
        or any(row["status"] != "completed" for row in p3_status)
    ):
        issues.append("registered 36-cell grid/status")

    source_hashes: set[str] = set()
    head_commits: set[str] = set()
    dirty_count = 0
    empty_patch_count = 0
    counts = {"checkpoints": 0, "train": 0, "references": 0, "interventions": 0, "old_panel": 0}
    total_additional = 0
    total_lifetime = 0
    learned: list[dict[str, Any]] = []
    controls: dict[tuple[int, int], dict[str, dict[str, float]]] = {}

    for row in p3_status:
        cell = (row["backbone"], row["memory"], row["order"], row["condition"])
        parent_row = p2_by_cell[cell]
        label = row["label"]
        run = P3 / "cells" / row["run_id"]
        result = read(run / "result.json")
        manifest = read(run / "manifest.json")
        source = read(run / "source.json")
        terminal = read(run / "terminal.json")
        source_hashes.add(source["archive"]["sha256"])
        head_commits.add(manifest["code_commit"])
        dirty_count += bool(manifest["dirty"])

        if terminal["status"] != "completed" or terminal["returncode"] != 0:
            issues.append(f"{label}: terminal status")
        if (
            source["archive"]["sha256"] != manifest["source_sha256"]
            or digest(run / "source.tar") != manifest["source_sha256"]
        ):
            issues.append(f"{label}: source archive hash")
        patch = run / "source.diff"
        if patch.read_bytes() == b"" and digest(patch) == source["patch"]["sha256"]:
            empty_patch_count += 1
        else:
            issues.append(f"{label}: source diff")
        for key in (
            "source_sha256",
            "spec_sha256",
            "parent_spec_sha256",
            "config_sha256",
            "lock_sha256",
            "data_approval_sha256",
            "dataset_manifest_sha256",
        ):
            if manifest.get(key) != p3_manifest.get(key):
                issues.append(f"{label}: changed {key}")
        if (
            result["additional_training_targets"] != 393216
            or result["lifetime_training_targets"] != 524288
        ):
            issues.append(f"{label}: target totals")
        total_additional += result["additional_training_targets"]
        total_lifetime += result["lifetime_training_targets"]

        events = [json.loads(line) for line in (run / "metrics.jsonl").read_text().splitlines()]
        train = [event for event in events if event.get("event") == "train_step"]
        refs = [event for event in events if event.get("event") == "duration_reference"]
        interventions = [event for event in events if event.get("event") == "duration_intervention"]
        old_panel = [event for event in events if event.get("event") == "parent_restore_integrity"]
        counts["train"] += len(train)
        counts["references"] += len(refs)
        counts["interventions"] += len(interventions)
        counts["old_panel"] += len(old_panel)
        if [event.get("global_step") for event in train] != list(range(257, 1025)):
            issues.append(f"{label}: training steps")
        if any(
            event.get("order_offset_for_update") != (8 * (event["global_step"] - 1)) % 2048
            for event in train
        ):
            issues.append(f"{label}: cyclic order offsets")
        if any(
            (event.get("additional_targets"), event.get("cumulative_targets"))
            != ((event["global_step"] - 256) * 512, event["global_step"] * 512)
            for event in train
        ):
            issues.append(f"{label}: training event counters")
        if [event.get("global_step") for event in refs] != list(STEPS := (256, 512, 1024)):
            issues.append(f"{label}: duration reference steps")
        expected_interventions = 3 if row["condition"] == CONTROL else 12
        if len(interventions) != expected_interventions or len(old_panel) != 1:
            issues.append(f"{label}: diagnostic counts")
        if any(
            event.get("panel") != "P3_scientific"
            or event.get("target_tokens") != 32768
            or event.get("training_target_tokens") != 0
            for event in refs + interventions
        ):
            issues.append(f"{label}: P3 panel targets/training")
        if (
            len(old_panel) != 1
            or old_panel[0].get("panel") != "P2_integrity_only"
            or old_panel[0].get("target_tokens") != 32768
            or old_panel[0].get("training_target_tokens") != 0
            or old_panel[0].get("excluded_from_scientific_analysis") is not True
            or old_panel[0].get("bitwise_passed") is not True
        ):
            issues.append(f"{label}: P2 integrity-only replay")

        p2_run = P2 / "cells" / parent_row["run_id"]
        p2_result = read(p2_run / "result.json")
        p2_state_path = p2_run / "checkpoint-256" / "state.pt"
        p2_index_path = p2_run / "checkpoint-256" / "index.json"
        provenance = parent_bundle[label]
        p2_state = torch.load(p2_state_path, map_location="cpu", weights_only=True)
        if (
            digest(p2_state_path) != provenance["checkpoint_state_sha256"]
            or digest(p2_index_path) != provenance["checkpoint_index_sha256"]
            or digest(p2_state_path) != p2_result["checkpoint_state_sha256"]["checkpoint-256"]
            or result["original_parent_checkpoint_unchanged"] is not True
        ):
            issues.append(f"{label}: P2 parent state/index changed")
        if old_panel and struct.pack("!d", old_panel[0]["nll"]) != struct.pack(
            "!d", p2_result["final"]["nll"]
        ):
            issues.append(f"{label}: old-panel NLL differs from P2")
        p2_export = P2_EXPORT / label
        for name in (
            "result.json",
            "manifest.json",
            "source.json",
            "config.resolved.json",
            "dataset_manifest.json",
            "order.json",
            "checkpoint-256/index.json",
        ):
            if digest(p2_run / name) != digest(p2_export / name):
                issues.append(f"{label}: P2 compact record mismatch {name}")
        p3_identity = manifest["checkpoint_identity"]
        if p3_identity.get("parent") != provenance:
            issues.append(f"{label}: embedded P2 identity")

        for step in STEPS:
            checkpoint = run / f"checkpoint-{step}"
            state_path = checkpoint / "state.pt"
            index = read(checkpoint / "index.json")
            state = torch.load(state_path, map_location="cpu", weights_only=True)
            counts["checkpoints"] += 1
            state_hash = digest(state_path)
            if (
                state_hash != index["state_sha256"]
                or state_hash != result["checkpoint_state_sha256"][f"checkpoint-{step}"]
            ):
                issues.append(f"{label}: checkpoint {step} hash/index")
            expected_counts = {
                "completed_step": step,
                "absolute_order_cursor": step * 8,
                "next_cyclic_order_cursor": (step * 8) % 2048,
                "cumulative_targets": step * 512,
                "additional_targets": (step - 256) * 512,
            }
            if state["counters"] != expected_counts:
                issues.append(f"{label}: checkpoint {step} counters")
            if state["zero_training_conversion"] is not (step == 256):
                issues.append(f"{label}: checkpoint {step} conversion marker")
            clocks = {int(value["step"].item()) for value in state["optimizer"]["state"].values()}
            if clocks != {step}:
                issues.append(f"{label}: AdamW step clocks at {step}")
            if state["identity"] != p3_identity:
                issues.append(f"{label}: checkpoint {step} identity")
            if step == 256:
                for field in (
                    "model",
                    "optimizer",
                    "python_rng",
                    "torch_rng",
                    "requires_grad",
                    "bypass",
                ):
                    if not same(state[field], p2_state[field]):
                        issues.append(f"{label}: P2-to-P3 zero-conversion field {field}")
            if row["condition"] == CONTROL:
                if state["bypass"] is not True:
                    issues.append(f"{label}: control bypass at {step}")
                for name, value in p2_state["model"].items():
                    if name.startswith("memory_state.") and not same(state["model"][name], value):
                        issues.append(f"{label}: frozen control memory changed at {step}")
            elif state["bypass"] is not False:
                issues.append(f"{label}: learned memory bypass at {step}")

        if read(p2_run / "order.json") != read(run / "order.json"):
            issues.append(f"{label}: P2 order changed")
        duration_values = {
            str(step): {
                condition: value["nll"]
                for condition, value in result["durations"][str(step)]["interventions"].items()
            }
            for step in STEPS
        }
        if row["condition"] == CONTROL:
            controls[(row["backbone"], row["order"])] = duration_values
        else:
            learned.append(
                {
                    "backbone": row["backbone"],
                    "memory": row["memory"],
                    "order": row["order"],
                    "durations": duration_values,
                }
            )
            cell_index = (
                (row["backbone"] - 101) * 9 + (row["order"] - 301) * 3 + row["memory"] - 201
            )
            for condition, seed in (
                ("values_permuted", 20000 + cell_index),
                ("joint_within_branch", 30000 + cell_index),
            ):
                p2_perm = read(p2_run / f"permutation-{condition}.json")
                p3_perm_path = run / f"permutation-{condition}.json"
                p3_perm = read(p3_perm_path)
                generator = torch.Generator(device="cpu").manual_seed(seed)
                if condition == "values_permuted":
                    ids = torch.randperm(4096, generator=generator).tolist()
                else:
                    ids = sum(
                        (
                            [
                                branch * 256 + i
                                for i in torch.randperm(256, generator=generator).tolist()
                            ]
                            for branch in range(16)
                        ),
                        [],
                    )
                if (
                    p2_perm["permutation_ids"] != p3_perm["permutation_ids"]
                    or p3_perm["permutation_ids"] != ids
                    or p3_perm["generator_seed"] != seed
                ):
                    issues.append(f"{label}: permutation {condition}")
                for step in STEPS:
                    record = result["durations"][str(step)]["interventions"][condition][
                        "permutation"
                    ]
                    if record["sha256"] != digest(p3_perm_path) or record["generator_seed"] != seed:
                        issues.append(f"{label}: duration permutation {condition} at {step}")

    for order in ORDERS:
        same_order = [row for row in p3_status if row["order"] == order]
        if (
            len(same_order) != 12
            or len(
                {(P3 / "cells" / row["run_id"] / "order.json").read_bytes() for row in same_order}
            )
            != 1
        ):
            issues.append(f"order {order}: cell streams differ")

    data_dir = P3 / "frozen-data"
    data_manifest = read(data_dir / "dataset_manifest.json")
    for name, expected_hash in data_manifest["checksums_sha256"].items():
        if digest(data_dir / name) != expected_hash:
            issues.append(f"dataset checksum {name}")
    data_hashes = {
        name: digest(data_dir / name)
        for name in ("train.bytes", "p2_validation_integrity.bytes", "validation.bytes")
    }
    expected_data = {
        "train.bytes": "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07",
        "p2_validation_integrity.bytes": (
            "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2"
        ),
        "validation.bytes": "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0",
    }
    if data_hashes != expected_data:
        issues.append("train/P2/P3 panel byte identities")
    selection = read(data_dir / "validation_first_1536.selected.json")
    if len(selection) != 1536 or [item["rank"] for item in selection] != list(range(1536)):
        issues.append("P3 validation selection ranks")
    for name, offset in (("p2_validation_integrity.bytes", 512), ("validation.bytes", 1024)):
        raw = (data_dir / name).read_bytes()
        for index in range(512):
            if (
                hashlib.sha256(raw[index * 65 : (index + 1) * 65]).hexdigest()
                != selection[offset + index]["chunk_sha256"]
            ):
                issues.append(f"selected chunk identity {name}:{index}")
    acquisition = read(data_dir / "acquisition.json")
    if acquisition["deferred_test"]["acquired"] or acquisition["deferred_test"]["inspected"]:
        issues.append("deferred test split accessed")

    by_step: dict[str, list[dict[str, Any]]] = {}
    for step in STEPS:
        key = str(step)
        measured = []
        for row in learned:
            nlls = row["durations"][key]
            control_nll = controls[(row["backbone"], row["order"])][key]["enabled"]
            enabled = nlls["enabled"]
            d = nlls["disabled"] - enabled
            p = nlls["values_permuted"] - enabled
            g = control_nll - enabled
            s = control_nll - nlls["disabled"]
            if not math.isclose(g, d + s, rel_tol=0, abs_tol=1e-12):
                issues.append(
                    f"{row['backbone']}/{row['memory']}/{row['order']}: G=D+S step {step}"
                )
            measured.append({**row, **nlls, "control": control_nll, "D": d, "P": p, "G": g, "S": s})
        by_step[key] = measured
        saved = p3_result["descriptive_analysis"]["by_duration"][key]
        for metric in (
            "enabled",
            "disabled",
            "values_permuted",
            "joint_within_branch",
            "D",
            "P",
            "G",
            "S",
        ):
            actual = distribution([row[metric] for row in measured])
            for field, value in actual.items():
                record = saved["learned_paired_metrics"][metric][field]
                if not (close(value, record) if isinstance(value, float) else value == record):
                    issues.append(f"suite summary {key} {metric}.{field}")
        control_summary = distribution(
            [controls[(b, o)][key]["enabled"] for b in BACKBONES for o in ORDERS]
        )
        for field, value in control_summary.items():
            record = saved["unique_control_nll"][field]
            if not (close(value, record) if isinstance(value, float) else value == record):
                issues.append(f"unique control summary {key}.{field}")

    changes: dict[str, list[dict[str, Any]]] = {}
    for step in (512, 1024):
        key = str(step)
        start_map = {(row["backbone"], row["memory"], row["order"]): row for row in by_step["256"]}
        deltas = []
        for row in by_step[key]:
            start = start_map[(row["backbone"], row["memory"], row["order"])]
            deltas.append(
                {
                    **{field: row[field] for field in ("backbone", "memory", "order")},
                    **{
                        field: row[field] - start[field]
                        for field in ("enabled", "D", "P", "G", "S")
                    },
                }
            )
        changes[key] = deltas
        saved = p3_result["descriptive_analysis"]["changes_from_256"][key]
        for metric in ("enabled", "D", "P", "G", "S"):
            actual = distribution([row[metric] for row in deltas])
            for field, value in actual.items():
                record = saved["learned"][metric][field]
                if not (close(value, record) if isinstance(value, float) else value == record):
                    issues.append(f"suite delta summary {key} {metric}.{field}")
        control_delta = [
            controls[(b, o)][key]["enabled"] - controls[(b, o)]["256"]["enabled"]
            for b in BACKBONES
            for o in ORDERS
        ]
        actual = distribution(control_delta)
        for field, value in actual.items():
            record = saved["unique_control"][field]
            if not (close(value, record) if isinstance(value, float) else value == record):
                issues.append(f"suite control delta {key}.{field}")
        if (
            sum(row["D"] > 0 and row["P"] > 0 for row in deltas)
            != saved["both_delta_d_and_p_positive"]
        ):
            issues.append(f"suite positive delta count {key}")
        for metric in ("D", "G"):
            calc = decompose(deltas, metric)
            record = saved["factor_decomposition"][metric]
            if not close(calc["grand_mean"], record["grand_mean"]) or not close(
                calc["interaction_rms"], record["interaction_rms"]
            ):
                issues.append(f"factor decomposition {key} {metric}")
            for factor, value in calc["marginal_ranges"].items():
                if not close(value, record["marginal_ranges"][factor]):
                    issues.append(f"factor range {key} {metric} {factor}")

    endpoint = by_step["1024"]
    end_means = {
        field: statistics.mean(row[field] for row in endpoint)
        for field in ("D", "P", "G", "enabled")
    }
    delta_end = changes["1024"]
    delta_means = {
        field: statistics.mean(row[field] for row in delta_end)
        for field in ("D", "P", "G", "S", "enabled")
    }
    both_delta = sum(row["D"] > 0 and row["P"] > 0 for row in delta_end)
    both_endpoint = sum(row["D"] > 0 and row["P"] > 0 for row in endpoint)
    criteria = {
        "mean_delta_D_at_threshold": delta_means["D"] >= 0.005,
        "mean_delta_P_at_threshold": delta_means["P"] >= 0.005,
        "delta_joint_positive_at_least_22": both_delta >= 22,
        "mean_endpoint_D_at_threshold": end_means["D"] >= 0.005,
        "mean_endpoint_P_at_threshold": end_means["P"] >= 0.005,
        "endpoint_joint_positive_at_least_22": both_endpoint >= 22,
        "endpoint_enabled_mean_strictly_improved": end_means["enabled"]
        < statistics.mean(row["enabled"] for row in by_step["256"]),
        "endpoint_mean_G_nonnegative": end_means["G"] >= 0,
    }
    flags = {
        "duration_increases_dependence": all(list(criteria.values())[:3]),
        "endpoint_dependence": all(list(criteria.values())[3:6]),
        "endpoint_quality_guard": all(list(criteria.values())[6:]),
    }
    recorded = p3_result["descriptive_analysis"]
    if criteria != recorded["criteria"] or flags != recorded["flags"]:
        issues.append("prespecified flag arithmetic")

    freeze = "861c137a7fcccf27e3371ca2217fd7d956753ca9"
    non_results_commits = []
    for commit in head_commits:
        paths = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit], text=True
        ).splitlines()
        if commit != freeze and any(not path.startswith("results/") for path in paths):
            non_results_commits.append((commit, paths))
    if non_results_commits:
        issues.append("post-freeze commit touched non-results files")
    if len(source_hashes) != 1 or next(iter(source_hashes)) != p3_manifest["source_sha256"]:
        issues.append("source archive changed across cells")
    if total_additional != 14_155_776 or total_lifetime != 18_874_368:
        issues.append("suite target totals")
    expected_counts = {
        "checkpoints": 108,
        "train": 27648,
        "references": 108,
        "interventions": 351,
        "old_panel": 36,
    }
    if counts != expected_counts:
        issues.append(f"suite event counts {counts}")

    print(
        json.dumps(
            {
                "issues": issues,
                "cells": len(p3_status),
                "counts": counts,
                "additional_targets": total_additional,
                "lifetime_targets": total_lifetime,
                "source_sha256": sorted(source_hashes),
                "head_commits": len(head_commits),
                "dirty_cells": dirty_count,
                "empty_hash_valid_source_diffs": empty_patch_count,
                "data_sha256": {
                    name: digest(P3 / "frozen-data" / name)
                    for name in ("train.bytes", "p2_validation_integrity.bytes", "validation.bytes")
                },
                "criteria": criteria,
                "flags": flags,
                "means": {
                    "delta_D_1024": delta_means["D"],
                    "delta_P_1024": delta_means["P"],
                    "endpoint_D": end_means["D"],
                    "endpoint_P": end_means["P"],
                    "endpoint_G": end_means["G"],
                    "endpoint_enabled": end_means["enabled"],
                    "enabled_256": statistics.mean(row["enabled"] for row in by_step["256"]),
                },
                "positive_counts": {"delta_both": both_delta, "endpoint_both": both_endpoint},
            },
            indent=2,
        )
    )
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
