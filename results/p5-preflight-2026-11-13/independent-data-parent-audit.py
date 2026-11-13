"""Independent P5 data and parent audit; no ArborLM imports or model forwards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from pyarrow import parquet

ROOT = Path.cwd()
DATA = ROOT / "data/wikitext2"
P3 = ROOT / "experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d"
P4 = ROOT / "experiments/P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd"
P3_RESULTS = ROOT / "results/p3-lt-2026-11-12"
P4_RESULTS = ROOT / "results/p4-2026-11-12"
P5_RANGE = (2048, 2560)
PANEL_SHA = {
    (0, 512): "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200",
    (512, 1024): "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2",
    (1024, 1536): "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0",
    (1536, 2048): "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f",
}
EXPECTED_FILES = {
    "train-00000-of-00001.parquet": {
        "bytes": 6357543,
        "sha256": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    },
    "validation-00000-of-00001.parquet": {
        "bytes": 657209,
        "sha256": "204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c",
    },
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_rows(path: Path):
    with parquet.ParquetFile(path) as file:
        for batch in file.iter_batches(columns=["text"], use_threads=False):
            yield from batch.column(0).to_pylist()


def selected_rows(split: str, path: Path, excluded: set[str] | None = None):
    by_chunk: dict[str, dict[str, Any]] = {}
    counts = {
        "rows": 0,
        "full_chunks": 0,
        "excluded_cross_split": 0,
        "duplicates_after_cross_split": 0,
        "remainder_bytes": 0,
    }
    for row_index, text in enumerate(read_rows(path)):
        counts["rows"] += 1
        if not isinstance(text, str):
            raise ValueError(f"non-string parquet text at {split}:{row_index}")
        payload_row = text.encode("utf-8")
        counts["remainder_bytes"] += len(payload_row) % 65
        for offset in range(0, len(payload_row) - 64, 65):
            payload = payload_row[offset : offset + 65]
            payload_sha = sha_bytes(payload)
            counts["full_chunks"] += 1
            if excluded is not None and payload_sha in excluded:
                counts["excluded_cross_split"] += 1
                continue
            candidate = {
                "row": row_index,
                "byte_offset": offset,
                "rank_sha256": sha_bytes(f"arborlm-pilot-v1:{split}:{row_index}:{offset}".encode()),
                "chunk_sha256": payload_sha,
                "payload": payload,
            }
            previous = by_chunk.get(payload_sha)
            if previous is not None:
                counts["duplicates_after_cross_split"] += 1
            if previous is None or (candidate["rank_sha256"], row_index, offset) < (
                previous["rank_sha256"],
                previous["row"],
                previous["byte_offset"],
            ):
                by_chunk[payload_sha] = candidate
    ranked = sorted(
        by_chunk.values(),
        key=lambda item: (item["rank_sha256"], item["row"], item["byte_offset"]),
    )
    return ranked, set(by_chunk), counts


def selection_bytes(items: list[dict[str, Any]]) -> bytes:
    return canonical_json(
        [
            {
                "row": item["row"],
                "byte_offset": item["byte_offset"],
                "rank_sha256": item["rank_sha256"],
                "chunk_sha256": item["chunk_sha256"],
            }
            for item in items
        ]
    )


def panel_bytes(items: list[dict[str, Any]]) -> bytes:
    return b"".join(item["payload"] for item in items)


def scan_panel_ranges() -> dict[str, Any]:
    """Find existing JSON declarations of evaluation/validation rank ranges."""
    ranges: list[dict[str, Any]] = []
    keys = {
        "scientific_panel_ranks",
        "validation_ranks",
        "measured_ranks",
        "validation_range",
        "panel_ranks",
    }
    for base in (ROOT / "experiments", ROOT / "results"):
        for path in base.rglob("*.json"):
            if path.name.endswith(".selected.json"):
                continue
            try:
                obj = read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            stack = [("", obj)]
            while stack:
                key, value = stack.pop()
                if isinstance(value, dict):
                    stack.extend((name, child) for name, child in value.items())
                elif isinstance(value, list):
                    if key in keys and len(value) == 2 and all(type(x) is int for x in value):
                        ranges.append(
                            {
                                "file": str(path.relative_to(ROOT)),
                                "key": key,
                                "range": value,
                            }
                        )
                    else:
                        stack.extend((key, child) for child in value)
    overlaps = [
        record
        for record in ranges
        if record["range"][0] < P5_RANGE[1] and record["range"][1] > P5_RANGE[0]
    ]
    return {"declared_ranges_found": ranges, "overlapping_range_records": overlaps}


def tensor_bytes(tensor: torch.Tensor) -> bytes:
    return bytes(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist())


def tensor_map_digest(tensors: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        digest.update(
            canonical_json({"name": name, "shape": list(tensor.shape), "dtype": str(tensor.dtype)})
        )
        digest.update(tensor_bytes(tensor))
    return digest.hexdigest()


def parent_audit() -> dict[str, Any]:
    p3_rows = read_json(P3 / "cells.json")
    p4_rows = read_json(P4 / "cells.json")
    p3_map = {
        (row["backbone"], row["order"]): row
        for row in p3_rows
        if row.get("condition") == "disabled_throughout" and row.get("memory") == 201
    }
    p4_map = {
        (row["backbone"], row["order"]): row
        for row in p4_rows
        if row.get("variant") == "baseline" and row.get("seed") == 0
    }
    issues: list[str] = []
    if len(p3_map) != 9 or len(p4_map) != 9 or set(p3_map) != set(p4_map):
        issues.append("parent maps are not the exact 9 B×O combinations")
    records: list[dict[str, Any]] = []
    environment_fingerprints: set[str] = set()
    for key in sorted(p4_map):
        p3_row, p4_row = p3_map[key], p4_map[key]
        label = f"b{key[0]}-o{key[1]}"
        p3_dir = P3 / "cells" / p3_row["run_id"]
        p4_dir = P4 / "cells" / p4_row["run_id"]
        compact_p3 = P3_RESULTS / f"b{key[0]}-o{key[1]}-control"
        compact_p4 = P4_RESULTS / f"b{key[0]}-o{key[1]}-baseline"
        p3_state_path = p3_dir / "checkpoint-1024/state.pt"
        p3_index_path = p3_dir / "checkpoint-1024/index.json"
        p4_state_path = p4_dir / "checkpoint-0/state.pt"
        p4_index_path = p4_dir / "checkpoint-0/index.json"
        p3_index, p4_index = read_json(p3_index_path), read_json(p4_index_path)
        p4_provenance = read_json(p4_dir / "parent_provenance.json")
        p3_result = read_json(p3_dir / "result.json")
        p4_result = read_json(p4_dir / "result.json")
        p3_state_sha, p3_index_sha = sha_file(p3_state_path), sha_file(p3_index_path)
        p4_state_sha, p4_index_sha = sha_file(p4_state_path), sha_file(p4_index_path)
        if p3_index["state_sha256"] != p3_state_sha:
            issues.append(f"{label}: actual P3 state/index mismatch")
        if p4_index["state_sha256"] != p4_state_sha:
            issues.append(f"{label}: actual P4 state/index mismatch")
        if (compact_p3 / "checkpoint-1024/index.json").read_bytes() != p3_index_path.read_bytes():
            issues.append(f"{label}: P3 compact index differs")
        if (compact_p4 / "checkpoint-0/index.json").read_bytes() != p4_index_path.read_bytes():
            issues.append(f"{label}: P4 compact index differs")
        if (
            p3_result["checkpoint_state_sha256"].get("checkpoint-1024") != p3_state_sha
            or p3_result["durations"]["1024"].get("checkpoint_index_sha256") != p3_index_sha
        ):
            issues.append(f"{label}: P3 result checkpoint hashes")
        p4_parent = p4_provenance
        if (
            p4_parent["checkpoint_state_sha256"] != p3_state_sha
            or p4_parent["checkpoint_index_sha256"] != p3_index_sha
            or p4_parent["run_id"] != p3_row["run_id"]
            or p4_parent["suite_id"] != P3.name
        ):
            issues.append(f"{label}: P4→P3 parent provenance")
        if p4_result["checkpoint_state_sha256"].get("checkpoint-0") != p4_state_sha:
            issues.append(f"{label}: P4 result state hash")
        if p4_row["status"] != "completed" or p4_row["additional_training_targets"] != 0:
            issues.append(f"{label}: P4 baseline status/budget")

        p3_state = torch.load(p3_state_path, map_location="cpu", weights_only=True)
        p4_state = torch.load(p4_state_path, map_location="cpu", weights_only=True)
        p3_backbone = {
            name: tensor
            for name, tensor in p3_state["model"].items()
            if not name.startswith("memory_state.")
        }
        p4_backbone = {
            name.removeprefix("backbone."): tensor
            for name, tensor in p4_state["model"].items()
            if name.startswith("backbone.")
        }
        if set(p3_backbone) != set(p4_backbone) or any(
            tensor_bytes(p3_backbone[name]) != tensor_bytes(p4_backbone[name])
            for name in p3_backbone
        ):
            issues.append(f"{label}: P4 baseline tensors differ from P3 backbone")
        p4_flags = p4_state["requires_grad"]
        if any(p4_flags.values()) or p4_state["optimizer"] is not None:
            issues.append(f"{label}: P4 baseline has trainable parameters or optimizer")
        numel = sum(tensor.numel() for tensor in p4_backbone.values())
        if numel != 27392:
            issues.append(f"{label}: P4 frozen parameter count {numel}")
        digest_tensors = dict(p4_backbone)
        digest_tensors["mask"] = torch.full((64, 64), -torch.inf, dtype=torch.float32).triu(1)
        digest = tensor_map_digest(digest_tensors)
        if digest != p4_result["backbone_sha256"]:
            issues.append(f"{label}: canonical P4 backbone digest")

        p3_env = read_json(p3_dir / "environment.json")
        p4_env = read_json(p4_dir / "environment.json")

        def numerical(env: dict[str, Any]) -> dict[str, Any]:
            return {
                **{
                    field: env.get(field)
                    for field in (
                        "os",
                        "architecture",
                        "cpu",
                        "python",
                        "python_implementation",
                        "accelerator",
                    )
                },
                "torch": env.get("packages", {}).get("torch"),
            }

        if numerical(p3_env) != numerical(p4_env):
            issues.append(f"{label}: P3/P4 numerical environment differs")
        environment_fingerprints.add(sha_bytes(canonical_json(numerical(p4_env))))
        records.append(
            {
                "label": label,
                "p3_run_id": p3_row["run_id"],
                "p3_state_sha256": p3_state_sha,
                "p3_index_sha256": p3_index_sha,
                "p4_run_id": p4_row["run_id"],
                "p4_state_sha256": p4_state_sha,
                "p4_index_sha256": p4_index_sha,
                "p4_backbone_sha256": digest,
                "backbone_parameters": numel,
                "p3_p4_tensor_bytes_equal": True,
            }
        )
    if len(environment_fingerprints) != 1:
        issues.append("P4 parent numerical environments differ across cells")
    return {
        "parents_verified": len(records),
        "environment_fingerprints": sorted(environment_fingerprints),
        "parents": records,
        "issues": issues,
    }


def main() -> None:
    manifest = read_json(DATA / "manifest.json")
    file_checks: dict[str, Any] = {}
    for name, expected in EXPECTED_FILES.items():
        path = DATA / name
        actual = {"bytes": path.stat().st_size, "sha256": sha_file(path)}
        file_checks[name] = {"actual": actual, "expected": expected}
        if actual != expected or manifest["files"][name]["sha256"] != expected["sha256"]:
            raise RuntimeError(f"pinned file integrity mismatch: {name}")
    train, train_hashes, train_counts = selected_rows(
        "train", DATA / "train-00000-of-00001.parquet"
    )
    validation, _, validation_counts = selected_rows(
        "validation", DATA / "validation-00000-of-00001.parquet", train_hashes
    )
    if len(train) < 4096 or len(validation) < P5_RANGE[1]:
        raise RuntimeError("insufficient selected candidates")
    train_selected = train[:4096]
    first2560 = validation[: P5_RANGE[1]]
    panel_records: dict[str, Any] = {}
    for start, end in ((0, 512), (512, 1024), (1024, 1536), (1536, 2048), P5_RANGE):
        selected = first2560[start:end]
        panel_digest = sha_bytes(panel_bytes(selected))
        expected = PANEL_SHA.get((start, end))
        if expected is not None and panel_digest != expected:
            raise RuntimeError(f"prior panel hash mismatch for {start}:{end}")
        panel_records[f"{start}:{end}"] = {
            "rows": len(selected),
            "sha256": panel_digest,
            "matches_registered_prior": expected is None or panel_digest == expected,
            "selected_ids": [
                {k: item[k] for k in ("row", "byte_offset", "rank_sha256", "chunk_sha256")}
                for item in selected
            ],
        }
    p4_frozen = P4 / "frozen-data"
    selected_file = p4_frozen / "validation_first_2048.selected.json"
    independent_old_ids = json.loads(selection_bytes(validation[:2048]))
    recorded_old_ids = read_json(selected_file)
    p4_selection_matches = len(recorded_old_ids) == 2048 and all(
        {key: row[key] for key in independent_old_ids[0]} == independent_old_ids[index]
        and row.get("rank") == index
        for index, row in enumerate(recorded_old_ids)
    )
    if not p4_selection_matches:
        raise RuntimeError("independent first-2048 validation IDs differ from P4 frozen selection")
    p4_data_manifest = read_json(p4_frozen / "dataset_manifest.json")
    if (
        sha_file(selected_file)
        != p4_data_manifest["checksums_sha256"]["validation_first_2048.selected.json"]
    ):
        raise RuntimeError("P4 first-2048 selected ID file hash mismatch")
    p5_selected = validation[P5_RANGE[0] : P5_RANGE[1]]
    p5_hashes = {item["chunk_sha256"] for item in p5_selected}
    previous_hashes = {item["chunk_sha256"] for item in validation[: P5_RANGE[0]]}
    train_selected_hashes = {item["chunk_sha256"] for item in train_selected}
    overlap_previous = len(p5_hashes & previous_hashes)
    overlap_full_train = len(p5_hashes & train_hashes)
    if overlap_previous or overlap_full_train:
        raise RuntimeError("P5 panel exact overlap detected")
    range_scan = scan_panel_ranges()
    if range_scan["overlapping_range_records"]:
        raise RuntimeError("existing result records declare overlapping P5 rank interval")
    parent_results = parent_audit()
    if parent_results["issues"]:
        raise RuntimeError(f"parent audit issues: {parent_results['issues']}")
    p5_sel_bytes = selection_bytes(p5_selected)
    output = {
        "status": "PASS",
        "audit_scope": (
            "read-only raw data and parent identity; no ArborLM import, model forward, "
            "training, or evaluation"
        ),
        "data_files": file_checks,
        "train_counts": train_counts,
        "validation_counts": validation_counts,
        "train_first4096_bytes_sha256": sha_bytes(panel_bytes(train_selected)),
        "train_first4096_ids_sha256": sha_bytes(selection_bytes(train_selected)),
        "train_selected_4096_matches_registered": sha_bytes(panel_bytes(train_selected))
        == "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07",
        "prior_and_p5_validation_panels": panel_records,
        "p4_first2048_selected_ids_match": p4_selection_matches,
        "p5_panel_range": list(P5_RANGE),
        "p5_panel_rows": len(p5_selected),
        "p5_panel_bytes_sha256": sha_bytes(panel_bytes(p5_selected)),
        "p5_panel_ids_sha256": sha_bytes(p5_sel_bytes),
        "exact_overlap_with_prior_panels": overlap_previous,
        "exact_overlap_with_full_train_candidates": overlap_full_train,
        "exact_overlap_with_first4096_train_selection": len(p5_hashes & train_selected_hashes),
        "prior_use_rank_scan": range_scan,
        "parent_audit": parent_results,
        "model_forwards": 0,
        "training_updates": 0,
        "model_evaluations": 0,
    }
    if not output["train_selected_4096_matches_registered"]:
        raise RuntimeError("train selection hash mismatch")
    path = ROOT / "results/p5-preflight-2026-11-13/independent-data-parent-audit.json"
    path.write_bytes(canonical_json(output))
    print(json.dumps(output, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
