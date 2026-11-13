"""Verify the nine exact P3 parent controls before extracting their backbones."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnose_memory import _same_environment
from .io import canonical_json, file_sha256, read_json, sha256
from .optimization_followup import DATA_APPROVAL
from .p2_config import BACKBONES, CONTROL, ORDERS, Cell
from .p2_data import P1_TRAIN_SHA256
from .p3_config import FAMILY as P3_FAMILY
from .p3_config import config_hash, validate_config
from .p3_parent import SHARED_KEYS, _same_files
from .p4_config import PARENT_ARCHIVE, PARENT_FREEZE, PARENT_SPEC, PARENT_SUITE
from .p4_data import P3_VALIDATION_SHA256


@dataclass(frozen=True)
class Parent:
    checkpoint: Path
    cell: Cell
    identity: dict[str, Any]
    final_nll: float
    order_ids: list[int]
    order_file: Path
    provenance: dict[str, Any]

    def check_unchanged(self) -> None:
        if (
            file_sha256(self.checkpoint / "state.pt") != self.provenance["checkpoint_state_sha256"]
            or file_sha256(self.checkpoint / "index.json")
            != self.provenance["checkpoint_index_sha256"]
        ):
            raise ValueError("P4 parent checkpoint/index changed")


def map_parents(records: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    expected = {(b, o) for b in BACKBONES for o in ORDERS}
    mapped = {}
    run_ids = set()
    for record in records:
        if record["condition"] != CONTROL:
            continue
        key = (record["backbone"], record["order"])
        run_id = record["run_id"]
        if (
            key not in expected
            or key in mapped
            or record["memory"] != 201
            or record["status"] != "completed"
            or record["label"] != f"b{key[0]}-o{key[1]}-control"
            or not isinstance(run_id, str)
            or not run_id.startswith("P3LT-")
            or Path(run_id).name != run_id
            or run_id in run_ids
        ):
            raise ValueError("invalid or duplicate P3 control mapping")
        mapped[key] = record
        run_ids.add(run_id)
    if mapped.keys() != expected:
        raise ValueError("P4 requires all nine P3 controls")
    return mapped


def verify_suite(
    suite: Path, compact: Path, source: dict[str, Any]
) -> dict[tuple[int, int], dict[str, Any]]:
    if suite.name != PARENT_SUITE:
        raise ValueError("P4 requires the exact registered P3 suite")
    _same_files(
        suite,
        compact / "suite",
        (
            "manifest.json",
            "result.json",
            "source.json",
            "config.resolved.json",
            "cells.json",
            "frozen-data/dataset_manifest.json",
            "parent_provenance.json",
        ),
    )
    parent = read_json(suite / "manifest.json")
    original = read_json(suite / "source.json")
    if (
        parent["run_id"] != PARENT_SUITE
        or parent["code_commit"] != PARENT_FREEZE
        or parent["experiment_family"] != P3_FAMILY
        or parent["status"] != "completed"
        or parent["authorized_spec_reference"] != PARENT_SPEC
        or parent["source_sha256"] != PARENT_ARCHIVE
        or file_sha256(suite / "source.tar") != PARENT_ARCHIVE
        or original["code_commit"] != PARENT_FREEZE
        or original["archive"]["sha256"] != PARENT_ARCHIVE
        or original["lock_sha256"] != parent["lock_sha256"]
        or original["spec_sha256"] != parent["spec_sha256"]
    ):
        raise ValueError("P4 P3 suite/source identity mismatch")
    old = original["archive_file_sha256"]
    new = source["archive_file_sha256"]
    required = {
        "src/arborlm/p3_checkpoint.py",
        "src/arborlm/p2_model.py",
        "src/arborlm/pilot_model.py",
        "configs/p3_longer_training.toml",
        "uv.lock",
        PARENT_SPEC,
        DATA_APPROVAL,
    }
    if not required <= old.keys():
        raise ValueError("P3 source identity missing necessary records")
    for name, digest in old.items():
        if (
            name.startswith(("src/arborlm/", "configs/", "docs/decisions/"))
            or name in ("pyproject.toml", "uv.lock", ".python-version")
        ) and new.get(name) != digest:
            raise ValueError(f"frozen P3 source/config/spec/lock changed: {name}")
    config = validate_config(read_json(suite / "config.resolved.json"))
    dataset_path = suite / "frozen-data"
    dataset = read_json(dataset_path / "dataset_manifest.json")
    result = read_json(suite / "result.json")
    if (
        config_hash(config) != parent["config_sha256"]
        or sha256(canonical_json(dataset)) != parent["dataset_manifest_sha256"]
        or file_sha256(dataset_path / "train.bytes") != P1_TRAIN_SHA256
        or file_sha256(dataset_path / "validation.bytes") != P3_VALIDATION_SHA256
        or result["outcome"] != "completed"
        or result["cells"] != read_json(suite / "cells.json")
    ):
        raise ValueError("P4 P3 suite config/data/results identity mismatch")
    return map_parents(result["cells"])


def verify_parent(
    suite: Path,
    compact: Path,
    record: dict[str, Any],
    environment: dict[str, Any],
) -> Parent:
    cell = Cell(record["backbone"], 201, record["order"], CONTROL)
    label = f"b{cell.backbone}-o{cell.order}-control"
    run_id = record["run_id"]
    if (
        not isinstance(run_id, str)
        or not run_id.startswith("P3LT-")
        or Path(run_id).name != run_id
        or record["label"] != label
        or record["condition"] != CONTROL
        or record["memory"] != 201
    ):
        raise ValueError("wrong P4 parent mapping")
    directory = suite / "cells" / run_id
    hashes = _same_files(
        directory,
        compact / label,
        (
            "manifest.json",
            "result.json",
            "source.json",
            "config.resolved.json",
            "dataset_manifest.json",
            "checkpoint-1024/index.json",
            "order.json",
            "parent_provenance.json",
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
        or manifest["experiment_family"] != P3_FAMILY
        or manifest["status"] != "completed"
        or manifest["authorized_spec_reference"] != PARENT_SPEC
        or any(manifest[key] != value for key, value in cell.fields().items())
        or any(manifest[key] != suite_manifest[key] for key in SHARED_KEYS)
        or manifest["source_sha256"] != PARENT_ARCHIVE
        or source["archive"]["sha256"] != PARENT_ARCHIVE
        or file_sha256(directory / "source.tar") != PARENT_ARCHIVE
        or not _same_environment(environment, manifest["environment"])
    ):
        raise ValueError("P4 parent manifest/source/environment mismatch")
    order_file = directory / "order.json"
    order = read_json(order_file)
    ids = order["ranked_train_row_ids"]
    order_hash = hashes["order.json"]
    identity = {
        **{key: manifest[key] for key in SHARED_KEYS},
        "cell": cell.fields(),
        "order_sha256": order_hash,
        "parent": read_json(directory / "parent_provenance.json"),
    }
    if (
        identity != manifest["checkpoint_identity"]
        or order_hash != manifest["order_sha256"]
        or order_hash != identity["parent"]["checkpoint_identity"]["order_sha256"]
        or order["generator_seed"] != cell.order
        or order["rank_interval"] != [0, 2048]
        or any(type(idx) is not int for idx in ids)
        or sorted(ids) != list(range(2048))
        or config_hash(validate_config(read_json(directory / "config.resolved.json")))
        != manifest["config_sha256"]
        or sha256(canonical_json(read_json(directory / "dataset_manifest.json")))
        != manifest["dataset_manifest_sha256"]
    ):
        raise ValueError("P4 parent checkpoint identity/order mismatch")
    checkpoint = directory / "checkpoint-1024"
    state_hash = file_sha256(checkpoint / "state.pt")
    result = read_json(directory / "result.json")
    endpoint = result["durations"]["1024"]
    final_nll = endpoint["reference"]["nll"]
    if (
        result["outcome"] != "completed"
        or result["cell"] != cell.fields()
        or result["lifetime_training_targets"] != 524288
        or endpoint["completed_step"] != 1024
        or endpoint["reference"]["target_tokens"] != 32768
        or not math.isfinite(final_nll)
        or final_nll != record["durations"]["1024"]["enabled"]
        or state_hash != read_json(checkpoint / "index.json")["state_sha256"]
        or state_hash != result["checkpoint_state_sha256"]["checkpoint-1024"]
        or state_hash != endpoint["checkpoint_state_sha256"]
        or hashes["checkpoint-1024/index.json"] != endpoint["checkpoint_index_sha256"]
    ):
        raise ValueError("P4 parent checkpoint/result hash mismatch")
    return Parent(
        checkpoint,
        cell,
        identity,
        final_nll,
        ids,
        order_file,
        {
            "suite_id": PARENT_SUITE,
            "run_id": run_id,
            "code_commit": manifest["code_commit"],
            "checkpoint_state_sha256": state_hash,
            "checkpoint_index_sha256": hashes["checkpoint-1024/index.json"],
            "source_archive_sha256": PARENT_ARCHIVE,
            "checkpoint_path": str(checkpoint),
            "checkpoint_identity": identity,
            "record_hashes": hashes,
            "original_P3_panel_nll": final_nll,
            "historical_steps": 1024,
            "historical_targets": 524288,
        },
    )
