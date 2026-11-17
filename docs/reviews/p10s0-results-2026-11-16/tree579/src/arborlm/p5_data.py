"""Select the P5 panel using the original rank/deduplication recipe."""

from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from .fetch_wikitext import DOWNLOAD_FILES, FILES, REVISION
from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .p2_config import TRAIN_RANKED
from .p2_data import (
    P1_TOKENIZER_SHA256,
    P1_TRAIN_SHA256,
    P1_VALIDATION_SHA256,
    _rows_bytes,
    _selection,
)
from .p3_data import P2_VALIDATION_SHA256
from .p4_data import P4_VALIDATION_SHA256
from .pilot_data import CHUNK_BYTES, RECIPE, TOKENIZER, Candidate, _rows, select

P3_VALIDATION_SHA256 = "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0"

P5_VALIDATION_SHA256 = "d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98"
VAL_START, VAL_END = 2048, 2560
RECIPE_P5 = {
    "parent_recipe": RECIPE,
    "scientific_panel_ranks": [VAL_START, VAL_END],
    "P4_integrity_only_ranks": [1536, VAL_START],
    "limitations": "same corpus split; shared articles and near-duplicates remain possible",
}
FILES_FROZEN = {
    "train.bytes",
    "p4_validation_integrity.bytes",
    "validation.bytes",
    "train.selected.json",
    "validation_first_2560.selected.json",
    "tokenizer.json",
    "recipe.json",
    "acquisition.json",
    "README.upstream.md",
}


def panel(
    validation: list[Candidate], full_train: set[str]
) -> tuple[bytes, bytes, bytes, bytes, bytes]:
    if len(validation) != VAL_END:
        raise ValueError("P5 requires the first 2560 ranked validation candidates")
    hashes = {sha256(row.payload) for row in validation}
    if len(hashes) != VAL_END or hashes & full_train:
        raise ValueError("P5 panel exact overlap with earlier validation or full train")
    return (
        _rows_bytes(validation[:512]),
        _rows_bytes(validation[512:1024]),
        _rows_bytes(validation[1024:1536]),
        _rows_bytes(validation[1536:VAL_START]),
        _rows_bytes(validation[VAL_START:]),
    )


def freeze(directory: Path, source: Path) -> dict[str, Any]:
    acquisition_bytes = (source / "manifest.json").read_bytes()
    acquisition = read_json(source / "manifest.json")
    if (
        acquisition["dataset_revision"] != REVISION
        or acquisition["selected_files"] != list(DOWNLOAD_FILES)
        or acquisition["deferred_test"]["acquired"]
        or acquisition["deferred_test"]["inspected"]
    ):
        raise ValueError("unexpected P5 acquisition provenance")
    for name in DOWNLOAD_FILES:
        entry, expected = acquisition["files"][name], FILES[name]
        path = source / name
        if (entry["sha256"], entry["bytes"]) != (expected["sha256"], expected["bytes"]) or (
            path.stat().st_size != expected["bytes"] or file_sha256(path) != expected["sha256"]
        ):
            raise ValueError(f"pinned P5 acquisition file mismatch: {name}")
    readme = (source / "README.upstream.md").read_bytes()
    if sha256(readme) != acquisition["publisher_readme"]["sha256"]:
        raise ValueError("publisher README checksum mismatch")
    train, full_train, train_counts = select(
        _rows(source / DOWNLOAD_FILES[0]), "train", TRAIN_RANKED
    )
    validation, _, val_counts = select(
        _rows(source / DOWNLOAD_FILES[1]), "validation", VAL_END, excluded=full_train
    )
    p1, p2, p3, p4, p5 = panel(validation, full_train)
    files = {
        "train.bytes": _rows_bytes(train),
        "p4_validation_integrity.bytes": p4,
        "validation.bytes": p5,
        "validation_first_2560.selected.json": _selection(validation),
        "train.selected.json": _selection(train),
        "tokenizer.json": canonical_json(TOKENIZER),
        "recipe.json": canonical_json(RECIPE_P5),
        "acquisition.json": acquisition_bytes,
        "README.upstream.md": readme,
    }
    checksums = {name: sha256(data) for name, data in files.items()}
    prior = [sha256(x) for x in (p1, p2, p3, p4)]
    if prior != [
        P1_VALIDATION_SHA256,
        P2_VALIDATION_SHA256,
        P3_VALIDATION_SHA256,
        P4_VALIDATION_SHA256,
    ] or (
        checksums["train.bytes"] != P1_TRAIN_SHA256
        or checksums["tokenizer.json"] != P1_TOKENIZER_SHA256
        or checksums["validation.bytes"] != P5_VALIDATION_SHA256
    ):
        raise ValueError("P5 prior frozen train/validation/tokenizer identity mismatch")
    manifest = {
        "dataset_revision": REVISION,
        "publisher": acquisition["publisher"],
        "source_splits": {name: FILES[name] for name in DOWNLOAD_FILES},
        "publisher_license_note": "Publisher card front matter and body differ; local use only.",
        "earlier_validation_sha256": prior,
        "exact_overlap_with_earlier_panels": 0,
        "exact_overlap_with_full_train": 0,
        "counts": {"train": train_counts, "validation": val_counts},
        "scientific_panel_ranks": [VAL_START, VAL_END],
        "P4_panel_role": "parent integrity only; excluded from P5 analysis",
        "checksums_sha256": checksums,
        "limitations": RECIPE_P5["limitations"],
    }
    for name, payload in files.items():
        atomic_write(directory / name, payload)
    write_json(directory / "dataset_manifest.json", manifest)
    return manifest


def load_frozen(
    directory: Path, expected_hash: str
) -> tuple[Tensor, Tensor, Tensor, dict[str, Any]]:
    manifest = read_json(directory / "dataset_manifest.json")
    checksums = manifest["checksums_sha256"]
    if (
        sha256(canonical_json(manifest)) != expected_hash
        or checksums.keys() != FILES_FROZEN
        or manifest["dataset_revision"] != REVISION
        or checksums["train.bytes"] != P1_TRAIN_SHA256
        or checksums["validation.bytes"] != P5_VALIDATION_SHA256
        or checksums["p4_validation_integrity.bytes"] != P4_VALIDATION_SHA256
        or checksums["tokenizer.json"] != P1_TOKENIZER_SHA256
        or manifest["earlier_validation_sha256"]
        != [P1_VALIDATION_SHA256, P2_VALIDATION_SHA256, P3_VALIDATION_SHA256, P4_VALIDATION_SHA256]
    ):
        raise ValueError("P5 frozen dataset identity mismatch")
    payloads = {name: (directory / name).read_bytes() for name in FILES_FROZEN}
    if any(sha256(payload) != checksums[name] for name, payload in payloads.items()):
        raise ValueError("P5 frozen dataset checksum mismatch")

    def rows(name: str, count: int) -> Tensor:
        raw = payloads[name]
        if len(raw) != count * CHUNK_BYTES:
            raise ValueError(f"unexpected P5 row count for {name}")
        return (
            torch.frombuffer(bytearray(raw), dtype=torch.uint8).long().reshape(count, CHUNK_BYTES)
        )

    return (
        rows("train.bytes", TRAIN_RANKED),
        rows("p4_validation_integrity.bytes", 512),
        rows("validation.bytes", 512),
        manifest,
    )
