"""P2 local data freeze and training-order identity."""

from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from .fetch_wikitext import DOWNLOAD_FILES, FILES, REVISION
from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .p2_config import ORDERS, TRAIN_RANKED, TRAIN_SEEN, VAL_END, VAL_START
from .pilot_data import CHUNK_BYTES, RECIPE, TOKENIZER, Candidate, _rows, select

P1_TRAIN_SHA256 = "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
P1_VALIDATION_SHA256 = "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200"
P1_TOKENIZER_SHA256 = "575b06a29bd215e2cce3100a13140ffe72bb542be55fd2c8b5f9d4cdef59d770"
PANEL_RECIPE = {
    "parent_recipe": RECIPE,
    "eligible_validation_ranks": [0, VAL_END],
    "measured_validation_ranks": [VAL_START, VAL_END],
    "training_ranked": TRAIN_RANKED,
    "training_seen_ranks": [0, TRAIN_SEEN],
    "limitation": "previously unevaluated panel from the same split; near duplicates and shared "
    "articles remain possible; not independent corpus evidence",
}


def _rows_bytes(rows: list[Candidate]) -> bytes:
    return b"".join(chunk.payload for chunk in rows)


def _selection(rows: list[Candidate]) -> bytes:
    return canonical_json(
        [
            {
                "rank": i,
                "row": chunk.row,
                "byte_offset": chunk.offset,
                "rank_sha256": chunk.rank,
                "chunk_sha256": sha256(chunk.payload),
            }
            for i, chunk in enumerate(rows)
        ]
    )


def panel(
    validation: list[Candidate], full_train: set[str]
) -> tuple[list[Candidate], list[Candidate]]:
    if len(validation) != VAL_END:
        raise ValueError("expected exact registered ranked validation window")
    prior, panel = validation[:VAL_START], validation[VAL_START:]
    prior_hashes = {sha256(chunk.payload) for chunk in prior}
    panel_hashes = {sha256(chunk.payload) for chunk in panel}
    if len(panel_hashes) != VAL_END - VAL_START or panel_hashes & (prior_hashes | full_train):
        raise ValueError("P2 panel overlaps P1 or the full train candidate set")
    return prior, panel


def freeze(directory: Path, source: Path) -> dict[str, Any]:
    acquisition_bytes = (source / "manifest.json").read_bytes()
    acquisition = read_json(source / "manifest.json")
    if (
        acquisition["dataset_revision"] != REVISION
        or acquisition["selected_files"] != list(DOWNLOAD_FILES)
        or acquisition["deferred_test"]["acquired"]
        or acquisition["deferred_test"]["inspected"]
    ):
        raise ValueError("unexpected acquisition provenance")
    for name in DOWNLOAD_FILES:
        expected = FILES[name]
        path = source / name
        entry = acquisition["files"][name]
        if (entry["sha256"], entry["bytes"]) != (expected["sha256"], expected["bytes"]) or (
            path.stat().st_size != expected["bytes"] or file_sha256(path) != expected["sha256"]
        ):
            raise ValueError(f"pinned acquisition file mismatch: {name}")
    readme = (source / "README.upstream.md").read_bytes()
    if sha256(readme) != acquisition["publisher_readme"]["sha256"]:
        raise ValueError("publisher README checksum mismatch")
    train, full_train, train_counts = select(
        _rows(source / DOWNLOAD_FILES[0]), "train", TRAIN_RANKED
    )
    validation, _, val_counts = select(
        _rows(source / DOWNLOAD_FILES[1]), "validation", VAL_END, excluded=full_train
    )
    prior, measured = panel(validation, full_train)
    files = {
        "train.bytes": _rows_bytes(train),
        "validation.bytes": _rows_bytes(measured),
        "validation_first_1024.selected.json": _selection(validation),
        "train.selected.json": _selection(train),
        "tokenizer.json": canonical_json(TOKENIZER),
        "recipe.json": canonical_json(PANEL_RECIPE),
        "acquisition.json": acquisition_bytes,
        "README.upstream.md": readme,
    }
    if (
        sha256(files["train.bytes"]) != P1_TRAIN_SHA256
        or sha256(_rows_bytes(prior)) != P1_VALIDATION_SHA256
        or sha256(files["tokenizer.json"]) != P1_TOKENIZER_SHA256
    ):
        raise ValueError("P1 train/validation/tokenizer identity mismatch")
    checksums = {name: sha256(data) for name, data in files.items()}
    manifest = {
        "dataset_revision": REVISION,
        "source_splits": {name: FILES[name] for name in DOWNLOAD_FILES},
        "publisher": acquisition["publisher"],
        "publisher_license_note": "Publisher card front matter and body differ; local use only "
        "approved by ADR-0004. No publication rights inferred.",
        "p1_validation_bytes_sha256": P1_VALIDATION_SHA256,
        "exact_overlap_with_full_train": 0,
        "exact_overlap_with_p1_panel": 0,
        "counts": {"train": train_counts, "validation": val_counts},
        "measured_ranks": [VAL_START, VAL_END],
        "checksums_sha256": checksums,
        "limitation": PANEL_RECIPE["limitation"],
    }
    for name, data in files.items():
        atomic_write(directory / name, data)
    write_json(directory / "dataset_manifest.json", manifest)
    return manifest


def load_frozen(directory: Path, expected_sha256: str) -> tuple[Tensor, Tensor, dict[str, Any]]:
    manifest = read_json(directory / "dataset_manifest.json")
    if sha256(canonical_json(manifest)) != expected_sha256 or (
        manifest["checksums_sha256"]["train.bytes"] != P1_TRAIN_SHA256
        or manifest["p1_validation_bytes_sha256"] != P1_VALIDATION_SHA256
        or manifest["checksums_sha256"]["tokenizer.json"] != P1_TOKENIZER_SHA256
        or manifest["dataset_revision"] != REVISION
    ):
        raise ValueError("P2 frozen dataset manifest mismatch")
    for name, digest in manifest["checksums_sha256"].items():
        if file_sha256(directory / name) != digest:
            raise ValueError(f"P2 frozen dataset file mismatch: {name}")
    train = (directory / "train.bytes").read_bytes()
    validation = (directory / "validation.bytes").read_bytes()
    if (
        len(train) != TRAIN_RANKED * CHUNK_BYTES
        or len(validation) != (VAL_END - VAL_START) * CHUNK_BYTES
    ):
        raise ValueError("P2 dataset has incorrect row counts")

    def tensor(data: bytes) -> Tensor:
        return torch.frombuffer(bytearray(data), dtype=torch.uint8).long().reshape(-1, CHUNK_BYTES)

    return tensor(train), tensor(validation), manifest


def order_ids(seed: int) -> Tensor:
    if seed not in ORDERS:
        raise ValueError("unregistered order seed")
    return torch.randperm(
        TRAIN_SEEN, generator=torch.Generator(device="cpu").manual_seed(seed), device="cpu"
    )
