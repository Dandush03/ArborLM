"""Read-only verification of registered P4 baselines and their P3 linkage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .diagnose_memory import _same_environment
from .io import canonical_json, file_sha256, read_json, sha256
from .longer_training import IDENTITY_FIELDS
from .p2_config import BACKBONES, CONTROL, ORDERS
from .p2_config import Cell as P3Cell
from .p2_data import P1_TRAIN_SHA256
from .p3_parent import _same_files
from .p4_config import FAMILY as P4_FAMILY
from .p4_config import PARENT_RESULTS as P3_RESULTS
from .p4_config import PARENT_SUITE as P3_SUITE
from .p4_config import Cell as P4Cell
from .p4_config import config_hash, validate_config
from .p4_data import P4_VALIDATION_SHA256
from .p5_config import BASELINE, PARENT_ARCHIVE, PARENT_FREEZE, PARENT_SPEC, PARENT_SUITE

if TYPE_CHECKING:
    from .p4_model import Backbone

SHARED = (*IDENTITY_FIELDS, "dataset_manifest_sha256")


@dataclass(frozen=True)
class Parent:
    checkpoint: Path
    cell: P4Cell
    identity: dict[str, Any]
    final_nll: float
    order_ids: list[int]
    order_file: Path
    provenance: dict[str, Any]

    def check_unchanged(self) -> None:
        for tag, name in (("state", "state.pt"), ("index", "index.json")):
            if file_sha256(self.checkpoint / name) != self.provenance[f"checkpoint_{tag}_sha256"]:
                raise ValueError("P5 P4 parent changed")
            upstream = self.provenance["upstream_p3"]
            if (
                file_sha256(Path(upstream["checkpoint_path"]) / name)
                != upstream[f"checkpoint_{tag}_sha256"]
            ):
                raise ValueError("P5 upstream P3 parent changed")


def map_parents(records: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    expected = {(b, o) for b in BACKBONES for o in ORDERS}
    mapped = {}
    run_ids = set()
    for record in records:
        if record["variant"] != BASELINE:
            continue
        key = (record["backbone"], record["order"])
        run_id = record["run_id"]
        if (
            key not in expected
            or key in mapped
            or record["seed"] != 0
            or record["status"] != "completed"
            or record["label"] != f"b{key[0]}-o{key[1]}-baseline"
            or not isinstance(run_id, str)
            or not run_id.startswith("P4CAP-")
            or Path(run_id).name != run_id
            or run_id in run_ids
        ):
            raise ValueError("invalid or duplicate P5 parent mapping")
        mapped[key] = record
        run_ids.add(run_id)
    if mapped.keys() != expected:
        raise ValueError("P5 requires all nine P4 baseline parents")
    return mapped


def verify_suite(
    suite: Path, compact: Path, source: dict[str, Any]
) -> dict[tuple[int, int], dict[str, Any]]:
    if suite.name != PARENT_SUITE:
        raise ValueError("P5 requires the exact registered P4 suite")
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
            "baselines.json",
        ),
    )
    manifest = read_json(suite / "manifest.json")
    original = read_json(suite / "source.json")
    if (
        manifest["run_id"] != PARENT_SUITE
        or manifest["code_commit"] != PARENT_FREEZE
        or manifest["experiment_family"] != P4_FAMILY
        or manifest["status"] != "completed"
        or manifest["authorized_spec_reference"] != PARENT_SPEC
        or manifest["source_sha256"] != PARENT_ARCHIVE
        or file_sha256(suite / "source.tar") != PARENT_ARCHIVE
        or original["code_commit"] != PARENT_FREEZE
        or original["archive"]["sha256"] != PARENT_ARCHIVE
        or original["lock_sha256"] != manifest["lock_sha256"]
        or original["spec_sha256"] != manifest["spec_sha256"]
    ):
        raise ValueError("P5 P4 source/suite identity mismatch")
    frozen = original["archive_file_sha256"]
    required = {
        "src/arborlm/p4_checkpoint.py",
        "src/arborlm/p4_model.py",
        "src/arborlm/pilot_model.py",
        "configs/p4_frozen_capacity.toml",
        "uv.lock",
        PARENT_SPEC,
    }
    if not required <= frozen.keys():
        raise ValueError("P5 P4 source record missing necessary files")
    for name, digest in frozen.items():
        if (
            name.startswith(("src/arborlm/", "configs/", "docs/decisions/"))
            or name in ("pyproject.toml", "uv.lock", ".python-version")
        ) and source["archive_file_sha256"].get(name) != digest:
            raise ValueError(f"P5 immutable source/config/spec/lock changed: {name}")
    dataset = suite / "frozen-data"
    result = read_json(suite / "result.json")
    if (
        result["outcome"] != "completed"
        or result["cells"] != read_json(suite / "cells.json")
        or config_hash(validate_config(read_json(suite / "config.resolved.json")))
        != manifest["config_sha256"]
        or sha256(canonical_json(read_json(dataset / "dataset_manifest.json")))
        != manifest["dataset_manifest_sha256"]
        or file_sha256(dataset / "train.bytes") != P1_TRAIN_SHA256
        or file_sha256(dataset / "validation.bytes") != P4_VALIDATION_SHA256
    ):
        raise ValueError("P5 P4 config/data/results identity mismatch")
    return map_parents(result["cells"])


def verify_parent(
    suite: Path, compact: Path, record: dict[str, Any], environment: dict[str, Any]
) -> Parent:
    from .p4_parent import verify_parent as verify_p3

    b, o = record["backbone"], record["order"]
    cell = P4Cell(b, o, 0, BASELINE)
    label = f"b{b}-o{o}-baseline"
    run_id = record["run_id"]
    if (
        not isinstance(run_id, str)
        or not run_id.startswith("P4CAP-")
        or Path(run_id).name != run_id
        or record["label"] != label
        or any(record[k] != v for k, v in cell.fields().items())
    ):
        raise ValueError("wrong P5 P4 parent mapping")
    folder = suite / "cells" / run_id
    hashes = _same_files(
        folder,
        compact / label,
        (
            "manifest.json",
            "result.json",
            "source.json",
            "config.resolved.json",
            "dataset_manifest.json",
            "checkpoint-0/index.json",
            "order.json",
            "parent_provenance.json",
        ),
    )
    manifest = read_json(folder / "manifest.json")
    original = read_json(folder / "source.json")
    suite_manifest = read_json(suite / "manifest.json")
    if (
        manifest["run_id"] != run_id
        or manifest["parent_p4_suite_id"] != PARENT_SUITE
        or manifest["experiment_family"] != P4_FAMILY
        or manifest["status"] != "completed"
        or manifest["authorized_spec_reference"] != PARENT_SPEC
        or any(manifest[key] != value for key, value in cell.fields().items())
        or any(manifest[key] != suite_manifest[key] for key in SHARED)
        or original["archive"]["sha256"] != PARENT_ARCHIVE
        or file_sha256(folder / "source.tar") != PARENT_ARCHIVE
        or not _same_environment(environment, manifest["environment"])
    ):
        raise ValueError("P5 parent source/environment mismatch")
    order_file = folder / "order.json"
    order = read_json(order_file)
    ids = order["ranked_train_row_ids"]
    order_hash = hashes["order.json"]
    upstream = read_json(folder / "parent_provenance.json")
    p3_suite = (suite.parent / P3_SUITE).resolve()
    p3_record = next(
        (
            row
            for row in read_json(p3_suite / "cells.json")
            if row["backbone"] == b and row["order"] == o and row["condition"] == CONTROL
        ),
        None,
    )
    if (
        p3_record is None
        or verify_p3(p3_suite, P3_RESULTS, p3_record, environment).provenance != upstream
    ):
        raise ValueError("P5 upstream P3 parent mismatch")
    backbone_hash = manifest["model"]["frozen_backbone_sha256"]
    identity = {
        **{key: manifest[key] for key in SHARED},
        "cell": cell.fields(),
        "order_sha256": order_hash,
        "parent": upstream,
        "backbone_sha256": backbone_hash,
    }
    if (
        identity != manifest["checkpoint_identity"]
        or order_hash != manifest["order_sha256"]
        or order_hash != upstream["checkpoint_identity"]["order_sha256"]
        or order["generator_seed"] != o
        or order["rank_interval"] != [0, 2048]
        or any(type(idx) is not int for idx in ids)
        or sorted(ids) != list(range(2048))
        or config_hash(validate_config(read_json(folder / "config.resolved.json")))
        != manifest["config_sha256"]
        or sha256(canonical_json(read_json(folder / "dataset_manifest.json")))
        != manifest["dataset_manifest_sha256"]
    ):
        raise ValueError("P5 parent checkpoint config/data/order mismatch")
    result = read_json(folder / "result.json")
    checkpoint = folder / "checkpoint-0"
    state_hash = file_sha256(checkpoint / "state.pt")
    final = result["final"]["nll"]
    if (
        result["outcome"] != "completed"
        or result["cell"] != cell.fields()
        or result["additional_training_targets"] != 0
        or result["completed_steps"] != 0
        or result["backbone_sha256"] != backbone_hash
        or result["final"]["target_tokens"] != 32768
        or not math.isfinite(final)
        or final != record["final_nll"]
        or state_hash != read_json(checkpoint / "index.json")["state_sha256"]
        or state_hash != result["checkpoint_state_sha256"]["checkpoint-0"]
    ):
        raise ValueError("P5 parent checkpoint/result hash mismatch")
    return Parent(
        checkpoint,
        cell,
        identity,
        final,
        ids,
        order_file,
        {
            "suite_id": PARENT_SUITE,
            "run_id": run_id,
            "code_commit": manifest["code_commit"],
            "checkpoint_state_sha256": state_hash,
            "checkpoint_index_sha256": hashes["checkpoint-0/index.json"],
            "checkpoint_path": str(checkpoint),
            "record_hashes": hashes,
            "checkpoint_identity": identity,
            "source_archive_sha256": PARENT_ARCHIVE,
            "backbone_sha256": backbone_hash,
            "original_P4_panel_nll": final,
            "upstream_p3": upstream,
            "upstream_historical_steps": 1024,
            "upstream_historical_targets": 524288,
        },
    )


def extract_verified(parent: Parent) -> Backbone:
    from .longer_training import _isolated_rng
    from .optimization_followup import _optimizer
    from .p2_model import FollowupModel
    from .p3_checkpoint import restore as restore_p3
    from .p4_checkpoint import restore as restore_p4
    from .p4_config import counters as p4_counters
    from .p4_model import FrozenModel, backbone_digest

    with _isolated_rng():
        parent.check_unchanged()
        upstream = parent.provenance["upstream_p3"]
        p3 = FollowupModel(P3Cell(parent.cell.backbone, 201, parent.cell.order, CONTROL))
        loaded = restore_p3(
            Path(upstream["checkpoint_path"]), p3, _optimizer(p3), upstream["checkpoint_identity"]
        )
        if loaded["completed_step"] != 1024 or not p3.bypass:
            raise ValueError("P5 upstream checkpoint not final P3 control")
        model = FrozenModel(parent.cell, p3)
        if restore_p4(parent.checkpoint, model, None, parent.identity) != p4_counters(0):
            raise ValueError("P5 original P4 checkpoint is not a frozen baseline")
        if backbone_digest(model.backbone) != parent.provenance["backbone_sha256"]:
            raise ValueError("P5 extracted backbone digest differs")
        parent.check_unchanged()
        return model.backbone
