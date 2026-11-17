"""Freeze the approved train/validation chunks; no test split is accessed."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fetch_wikitext import DOWNLOAD_FILES, FILES, REVISION
from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .pilot_config import TRAIN_ROWS, VAL_ROWS

CHUNK_BYTES = 65
RECIPE = {
    "version": "arborlm-pilot-v1",
    "encoding": "exact UTF-8 bytes per row; no normalization, separators, or special tokens",
    "chunk_bytes": CHUNK_BYTES,
    "stride_bytes": CHUNK_BYTES,
    "index_origin": 0,
    "rank": "sha256(UTF-8 arborlm-pilot-v1:{split}:{row_index}:{byte_offset}), then row/offset",
    "duplicates": "keep lowest rank per split; exclude validation against all train candidates",
    "sample_sizes": {"train": TRAIN_ROWS, "validation": VAL_ROWS},
}
TOKENIZER = {"version": "utf8-bytes-v1", "ids": list(range(256)), "padding": False}


@dataclass(frozen=True)
class Candidate:
    rank: str
    row: int
    offset: int
    payload: bytes


def select(
    rows: Iterable[str],
    split: str,
    count: int,
    *,
    excluded: set[str] | None = None,
) -> tuple[list[Candidate], set[str], dict[str, int]]:
    by_digest: dict[str, Candidate] = {}
    counts = dict.fromkeys(
        (
            "rows",
            "remainder_bytes",
            "full_chunks",
            "excluded_cross_split",
            "duplicates_after_cross_split",
            "eligible_unique_chunks",
            "not_selected_after_ranking",
        ),
        0,
    )
    for row, text in enumerate(rows):
        counts["rows"] += 1
        if not isinstance(text, str):
            raise ValueError(f"non-string text field at {split}:{row}")
        encoded = text.encode("utf-8")
        counts["remainder_bytes"] += len(encoded) % CHUNK_BYTES
        for offset in range(0, len(encoded) - CHUNK_BYTES + 1, CHUNK_BYTES):
            payload = encoded[offset : offset + CHUNK_BYTES]
            digest = sha256(payload)
            counts["full_chunks"] += 1
            if excluded is not None and digest in excluded:
                counts["excluded_cross_split"] += 1
                continue
            candidate = Candidate(
                sha256(f"arborlm-pilot-v1:{split}:{row}:{offset}".encode()), row, offset, payload
            )
            existing = by_digest.get(digest)
            if existing is not None:
                counts["duplicates_after_cross_split"] += 1
            if existing is None or _sort_key(candidate) < _sort_key(existing):
                by_digest[digest] = candidate
    ranked = sorted(by_digest.values(), key=_sort_key)
    if len(ranked) < count:
        raise ValueError(f"insufficient unique {split} chunks: {len(ranked)} < {count}")
    counts["eligible_unique_chunks"] = len(ranked)
    counts["not_selected_after_ranking"] = len(ranked) - count
    return ranked[:count], set(by_digest), counts


def _sort_key(chunk: Candidate) -> tuple[str, int, int]:
    return chunk.rank, chunk.row, chunk.offset


def _rows(path: Path) -> Iterator[str]:
    from pyarrow import parquet

    with parquet.ParquetFile(path) as file:
        for batch in file.iter_batches(columns=["text"], use_threads=False):
            yield from batch.column(0).to_pylist()


def freeze_dataset(directory: Path, source: Path) -> dict[str, Any]:
    acquisition = read_json(source / "manifest.json")
    if acquisition["dataset_revision"] != REVISION or acquisition["selected_files"] != list(
        DOWNLOAD_FILES
    ):
        raise ValueError("dataset acquisition identity mismatch")
    if acquisition["deferred_test"]["acquired"] or acquisition["deferred_test"]["inspected"]:
        raise ValueError("unexpected test split in acquisition record")
    for name in DOWNLOAD_FILES:
        expected = FILES[name]
        path = source / name
        if path.stat().st_size != expected["bytes"] or file_sha256(path) != expected["sha256"]:
            raise ValueError(f"pinned dataset integrity check failed: {name}")
    readme = (source / "README.upstream.md").read_bytes()
    if sha256(readme) != acquisition["publisher_readme"]["sha256"]:
        raise ValueError("publisher card checksum mismatch")
    atomic_write(directory / "README.upstream.md", readme)
    write_json(directory / "acquisition.json", acquisition)

    train, full_train_hashes, train_counts = select(
        _rows(source / DOWNLOAD_FILES[0]), "train", TRAIN_ROWS
    )
    validation, _, val_counts = select(
        _rows(source / DOWNLOAD_FILES[1]), "validation", VAL_ROWS, excluded=full_train_hashes
    )
    files = {
        "recipe.json": canonical_json(RECIPE),
        "tokenizer.json": canonical_json(TOKENIZER),
    }
    for split, chunks in (("train", train), ("validation", validation)):
        files[f"{split}.bytes"] = b"".join(chunk.payload for chunk in chunks)
        files[f"{split}.selected.json"] = canonical_json(
            [
                {
                    "row": chunk.row,
                    "byte_offset": chunk.offset,
                    "rank_sha256": chunk.rank,
                    "chunk_sha256": sha256(chunk.payload),
                }
                for chunk in chunks
            ]
        )
    for name, contents in files.items():
        atomic_write(directory / name, contents)
    manifest = {
        "dataset_revision": REVISION,
        "publisher": acquisition["publisher"],
        "publisher_license_note": (
            "Pinned card front matter lists CC-BY-SA-3.0/GFDL and its body refers to "
            "CC BY-SA 4.0; discrepancy unresolved. Local use only was approved."
        ),
        "source_splits": {name: FILES[name] for name in DOWNLOAD_FILES},
        "counts": {"train": train_counts, "validation": val_counts},
        "checksums_sha256": {
            **{name: sha256(content) for name, content in files.items()},
            "README.upstream.md": sha256(readme),
            "acquisition.json": file_sha256(directory / "acquisition.json"),
        },
        "limitation": (
            "exact chunk deduplication does not exclude near duplicates or shared articles"
        ),
    }
    write_json(directory / "dataset_manifest.json", manifest)
    return manifest


def load_frozen(directory: Path) -> tuple[bytes, bytes, dict[str, Any]]:
    manifest = read_json(directory / "dataset_manifest.json")
    names = {
        "recipe.json",
        "tokenizer.json",
        "train.bytes",
        "validation.bytes",
        "train.selected.json",
        "validation.selected.json",
        "README.upstream.md",
        "acquisition.json",
    }
    if manifest["dataset_revision"] != REVISION or manifest["checksums_sha256"].keys() != names:
        raise ValueError("frozen dataset manifest mismatch")
    files = {name: (directory / name).read_bytes() for name in names}
    if any(sha256(data) != manifest["checksums_sha256"][name] for name, data in files.items()):
        raise ValueError("frozen dataset checksum mismatch")
    if (
        files["recipe.json"] != canonical_json(RECIPE)
        or files["tokenizer.json"] != canonical_json(TOKENIZER)
        or len(files["train.bytes"]) != CHUNK_BYTES * TRAIN_ROWS
        or len(files["validation.bytes"]) != CHUNK_BYTES * VAL_ROWS
    ):
        raise ValueError("frozen tokenizer/recipe/data mismatch")
    return files["train.bytes"], files["validation.bytes"], manifest
