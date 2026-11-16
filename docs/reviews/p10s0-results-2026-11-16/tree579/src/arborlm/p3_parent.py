"""Read-only verification of the exact registered P2 suite and cell evidence."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnose_memory import _same_environment
from .io import canonical_json, file_sha256, read_json, sha256
from .optimization_followup import DATA_APPROVAL, _label
from .p2_config import FAMILY as P2_FAMILY
from .p2_config import Cell, cells
from .p2_config import config_hash as p2_config_hash
from .p2_config import validate_config as p2_validate_config
from .p2_data import P1_TRAIN_SHA256
from .p3_config import PARENT_ARCHIVE, PARENT_FREEZE, PARENT_SPEC, PARENT_SUITE, START
from .p3_data import P2_VALIDATION_SHA256

SHARED_KEYS = (
    "source_sha256",
    "lock_sha256",
    "spec_sha256",
    "config_sha256",
    "parent_spec_sha256",
    "data_approval_sha256",
    "dataset_manifest_sha256",
)


@dataclass(frozen=True)
class Parent:
    checkpoint: Path
    identity: dict[str, Any]
    final_nll: float
    order_ids: list[int]
    order_file: Path
    inherited_router_movement: float | None
    provenance: dict[str, Any]

    def check_unchanged(self) -> None:
        if (
            file_sha256(self.checkpoint / "state.pt") != self.provenance["checkpoint_state_sha256"]
            or file_sha256(self.checkpoint / "index.json")
            != self.provenance["checkpoint_index_sha256"]
        ):
            raise ValueError("P2 parent checkpoint/index changed")


def map_cells(records: list[dict[str, Any]]) -> dict[Cell, dict[str, Any]]:
    mapped = {}
    run_ids = set()
    for record in records:
        cell = Cell(record["backbone"], record["memory"], record["order"], record["condition"])
        run_id = record["run_id"]
        if (
            cell in mapped
            or not isinstance(run_id, str)
            or not run_id.startswith("P2-")
            or Path(run_id).name != run_id
            or run_id in run_ids
            or record["label"] != _label(cell)
            or record["status"] != "completed"
        ):
            raise ValueError("invalid or duplicate P2 cell mapping")
        mapped[cell] = record
        run_ids.add(run_id)
    if set(mapped) != set(cells()):
        raise ValueError("P3 requires every completed P2 parent")
    return mapped


def _same_files(local: Path, compact: Path, names: tuple[str, ...]) -> dict[str, str]:
    hashes = {}
    for name in names:
        actual = file_sha256(local / name)
        if actual != file_sha256(compact / name):
            raise ValueError(f"P2 parent differs from committed compact record: {name}")
        hashes[name] = actual
    return hashes


def verify_suite(
    suite: Path, review_root: Path, source: dict[str, Any]
) -> dict[Cell, dict[str, Any]]:
    if suite.name != PARENT_SUITE:
        raise ValueError("P3 must use the exact registered P2 suite")
    _same_files(
        suite,
        review_root / "suite",
        (
            "manifest.json",
            "result.json",
            "source.json",
            "config.resolved.json",
            "cells.json",
            "frozen-data/dataset_manifest.json",
            "order-301.json",
            "order-302.json",
            "order-303.json",
        ),
    )
    parent = read_json(suite / "manifest.json")
    if (
        parent["run_id"] != PARENT_SUITE
        or parent["code_commit"] != PARENT_FREEZE
        or parent["experiment_family"] != P2_FAMILY
        or parent["status"] != "completed"
        or parent["source_sha256"] != PARENT_ARCHIVE
        or parent["authorized_spec_reference"] != PARENT_SPEC
        or file_sha256(suite / "source.tar") != PARENT_ARCHIVE
    ):
        raise ValueError("P2 suite identity mismatch")
    original = read_json(suite / "source.json")
    if (
        original["archive"]["sha256"] != PARENT_ARCHIVE
        or original["code_commit"] != PARENT_FREEZE
        or original["lock_sha256"] != parent["lock_sha256"]
        or original["spec_sha256"] != parent["spec_sha256"]
    ):
        raise ValueError("P2 source record identity mismatch")
    # All old package files, configs, specs, and lock are frozen; new P3 paths are allowed.
    current = source["archive_file_sha256"]
    frozen = original["archive_file_sha256"]
    required = {
        "src/arborlm/p2_model.py",
        "src/arborlm/p2_checkpoint.py",
        "src/arborlm/optimization_followup.py",
        "configs/p2_optimization_followup.toml",
        "uv.lock",
        PARENT_SPEC,
        DATA_APPROVAL,
    }
    if not required <= frozen.keys():
        raise ValueError("P2 source record missing required files")
    for name, digest in frozen.items():
        if (
            name.startswith(("src/arborlm/", "configs/", "docs/decisions/"))
            or name in ("pyproject.toml", "uv.lock", ".python-version")
        ) and current.get(name) != digest:
            raise ValueError(f"P2 source/config/spec/lock changed: {name}")
    config = p2_validate_config(read_json(suite / "config.resolved.json"))
    dataset_path = suite / "frozen-data"
    dataset = read_json(dataset_path / "dataset_manifest.json")
    if (
        p2_config_hash(config) != parent["config_sha256"]
        or sha256(canonical_json(dataset)) != parent["dataset_manifest_sha256"]
        or dataset["checksums_sha256"]["train.bytes"] != P1_TRAIN_SHA256
        or dataset["checksums_sha256"]["validation.bytes"] != P2_VALIDATION_SHA256
        or file_sha256(dataset_path / "train.bytes") != P1_TRAIN_SHA256
        or file_sha256(dataset_path / "validation.bytes") != P2_VALIDATION_SHA256
    ):
        raise ValueError("P2 suite config/data identity mismatch")
    return map_cells(read_json(suite / "cells.json"))


def verify_cell(
    suite: Path,
    review_root: Path,
    record: dict[str, Any],
    cell: Cell,
    environment: dict[str, Any],
) -> Parent:
    if any(record[key] != value for key, value in cell.fields().items()):
        raise ValueError("wrong P2 factor mapping")
    run_id = record["run_id"]
    if not isinstance(run_id, str) or not run_id.startswith("P2-") or Path(run_id).name != run_id:
        raise ValueError("invalid P2 parent run ID")
    directory = suite / "cells" / run_id
    hashes = _same_files(
        directory,
        review_root / _label(cell),
        (
            "manifest.json",
            "result.json",
            "source.json",
            "config.resolved.json",
            "dataset_manifest.json",
            "checkpoint-256/index.json",
            "order.json",
        ),
    )
    manifest, suite_manifest = (
        read_json(directory / "manifest.json"),
        read_json(suite / "manifest.json"),
    )
    source = read_json(directory / "source.json")
    if (
        manifest["run_id"] != run_id
        or manifest["parent_run_id"] != PARENT_SUITE
        or manifest["status"] != "completed"
        or manifest["experiment_family"] != P2_FAMILY
        or manifest["authorized_spec_reference"] != PARENT_SPEC
        or any(manifest[key] != value for key, value in cell.fields().items())
        or any(manifest[key] != suite_manifest[key] for key in SHARED_KEYS)
        or manifest["source_sha256"] != PARENT_ARCHIVE
        or source["archive"]["sha256"] != PARENT_ARCHIVE
        or file_sha256(directory / "source.tar") != PARENT_ARCHIVE
    ):
        raise ValueError("P2 cell manifest/source identity mismatch")
    if not _same_environment(environment, manifest["environment"]):
        raise ValueError("P3 numerical environment differs from the P2 parent")
    order_file = directory / "order.json"
    order_hash = hashes["order.json"]
    order = read_json(order_file)
    ids = order["ranked_train_row_ids"]
    if (
        order_hash != manifest["order_sha256"]
        or order_hash != suite_manifest["order_sha256"][str(cell.order)]
        or order_hash != file_sha256(suite / f"order-{cell.order}.json")
        or order["generator_seed"] != cell.order
        or order["rank_interval"] != [0, 2048]
        or any(type(idx) is not int for idx in ids)
        or sorted(ids) != list(range(2048))
    ):
        raise ValueError("P2 parent order mismatch")
    identity = {
        **{key: manifest[key] for key in SHARED_KEYS},
        "order_sha256": order_hash,
        "cell": cell.fields(),
    }
    if (
        manifest["checkpoint_identity"] != identity
        or sha256(canonical_json(read_json(directory / "dataset_manifest.json")))
        != identity["dataset_manifest_sha256"]
        or p2_config_hash(p2_validate_config(read_json(directory / "config.resolved.json")))
        != identity["config_sha256"]
    ):
        raise ValueError("P2 parent checkpoint config/data identity mismatch")
    result = read_json(directory / "result.json")
    if (
        result["outcome"] != "completed"
        or result["cell"] != cell.fields()
        or result["completed_steps"] != START
        or result["training_target_tokens"] != 131072
        or result["final"]["target_tokens"] != 32768
        or not math.isfinite(result["final"]["nll"])
        or result["final"]["nll"] != record["final_nll"]
    ):
        raise ValueError("P2 result identity/count mismatch")
    checkpoint = directory / "checkpoint-256"
    state_hash = file_sha256(checkpoint / "state.pt")
    index = read_json(checkpoint / "index.json")
    if (
        index["state_sha256"] != state_hash
        or result["checkpoint_state_sha256"]["checkpoint-256"] != state_hash
    ):
        raise ValueError("P2 parent checkpoint state hash mismatch")
    return Parent(
        checkpoint,
        identity,
        float(result["final"]["nll"]),
        ids,
        order_file,
        result["learned_router_movement_l2"],
        {
            "suite_id": PARENT_SUITE,
            "run_id": run_id,
            "code_commit": manifest["code_commit"],
            "source_archive_sha256": PARENT_ARCHIVE,
            "checkpoint_state_sha256": state_hash,
            "checkpoint_index_sha256": hashes["checkpoint-256/index.json"],
            "record_hashes": hashes,
            "checkpoint_identity": identity,
            "checkpoint_path": str(checkpoint),
            "original_P2_panel_nll": result["final"]["nll"],
        },
    )
