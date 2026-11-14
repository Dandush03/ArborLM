"""P7-B stream B panel: validation ranks 2560..3071 under the existing recipe (ADR-0014 section 7a).

The recipe is P2/P5's: every full 65-byte chunk of the pinned local validation file is ranked by
``sha256("arborlm-pilot-v1:validation:{row}:{offset}")`` (then row, offset); a chunk whose digest
occurs among the train candidates is excluded; among equal chunks the lowest rank is kept. P5
required exactly the first 2,560 ranked candidates and sliced ``[2048:]``. Ranking does not depend
on how many candidates are requested, so selecting the first 3,072 gives the same ranks 0..2559 and
the new panel is ``[2560:3072]``. That claim is not assumed: the five earlier panels (ranks 0..2559
in blocks of 512) are re-hashed and must reproduce the recorded P1..P5 SHA-256 values, or the stage
stops.

This module reads raw data and runs no model. ``reconstruct_from_rows`` takes iterables of text so a
test can use a tiny synthetic corpus; ``reconstruct_from_data_dir`` reads the pinned parquet files.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7b_core as core
from .io import file_sha256, read_json, sha256
from .p2_data import _selection
from .pilot_data import CHUNK_BYTES, Candidate, select

TRAIN_RANKED = 4096  # the frozen training pool of ranked chunks (P2_CONFIG TRAIN_RANKED)
PANEL_SIZE = 512
EARLIER_PANELS = 5


@dataclass
class PanelResult:
    panel_bytes: bytes
    record: dict[str, Any]


def _bytes(rows: list[Candidate]) -> bytes:
    return b"".join(chunk.payload for chunk in rows)


def reconstruct_from_rows(
    train_rows: Iterable[str],
    validation_rows: Iterable[str],
    *,
    train_ranked: int = TRAIN_RANKED,
    panel_size: int = PANEL_SIZE,
    expected_earlier: dict[str, str] | None = None,
    registered_train_hash: str | None = None,
    registered_p5_manifest: dict[str, Any] | None = None,
) -> PanelResult:
    """Rank, deduplicate and exclude exactly as P5 did, take the first ``6 * panel_size`` ranked
    validation candidates, check the five earlier panels against their registered hashes and the
    overlap conditions, and return the new panel and a record of every check.

    ``expected_earlier`` defaults to the registered P1..P5 hashes (ADR-0010 section 4).
    ``registered_p5_manifest`` (P5's published ``dataset_manifest.json``), when given, adds three
    checks that ranks 0..2559 are exactly P5's: the SHA-256 of the canonical selection list of the
    first 2,560 ranked candidates, the same for the 4,096 train candidates, and the candidate
    counts of the validation file."""
    expected = expected_earlier if expected_earlier is not None else core.PRIOR_PANEL_SHA256
    train, full_train, train_counts = select(train_rows, "train", train_ranked)
    total = (EARLIER_PANELS + 1) * panel_size
    validation, _, val_counts = select(validation_rows, "validation", total, excluded=full_train)
    if len(validation) != total:
        raise core.StopError("fewer ranked validation candidates than the panel needs")
    earlier = validation[: EARLIER_PANELS * panel_size]
    panel_rows = validation[EARLIER_PANELS * panel_size : total]
    checks: dict[str, Any] = {}
    # 1. The recorded P1..P5 panels are reproduced from the same file with the same recipe.
    earlier_record: dict[str, Any] = {}
    for n, name in enumerate(("P1", "P2", "P3", "P4", "P5")):
        block = earlier[n * panel_size : (n + 1) * panel_size]
        digest = sha256(_bytes(block))
        earlier_record[name] = {
            "ranks": [n * panel_size, (n + 1) * panel_size],
            "sha256": digest,
            "registered_sha256": expected[name],
            "match": digest == expected[name],
        }
    checks["earlier_panels_reproduced"] = all(v["match"] for v in earlier_record.values())
    # 2. Overlap checks (exact chunk content).
    panel_digests = [sha256(chunk.payload) for chunk in panel_rows]
    earlier_digests = {sha256(chunk.payload) for chunk in earlier}
    calibration = train[4 * panel_size : 5 * panel_size]
    calibration_digests = {sha256(chunk.payload) for chunk in calibration}
    overlap = {
        "duplicates_within_panel": len(panel_digests) - len(set(panel_digests)),
        "with_P1_to_P5_panels": len(set(panel_digests) & earlier_digests),
        "with_calibration_stream": len(set(panel_digests) & calibration_digests),
        "with_full_training_candidate_pool": len(set(panel_digests) & full_train),
    }
    checks["zero_overlap"] = all(v == 0 for v in overlap.values())
    checks["panel_rows"] = len(panel_rows) == panel_size
    checks["panel_rows_have_full_chunks"] = all(len(c.payload) == CHUNK_BYTES for c in panel_rows)
    # 3. Registered training hash (when the registered hash is supplied; P1 train identity).
    train_hash = sha256(_bytes(train))
    if registered_train_hash is not None:
        checks["train_pool_reproduced"] = train_hash == registered_train_hash
    selection_sha = sha256(_selection(validation[: EARLIER_PANELS * panel_size]))
    train_selection_sha = sha256(_selection(train))
    if registered_p5_manifest is not None:
        sums = registered_p5_manifest["checksums_sha256"]
        checks["first_2560_selection_equals_p5_frozen"] = (
            selection_sha == sums["validation_first_2560.selected.json"]
        )
        checks["train_selection_equals_p5_frozen"] = (
            train_selection_sha == sums["train.selected.json"]
        )
        recorded = registered_p5_manifest["counts"]["validation"]
        checks["validation_candidate_counts_equal_p5"] = all(
            val_counts[k] == recorded[k]
            for k in (
                "rows",
                "remainder_bytes",
                "full_chunks",
                "excluded_cross_split",
                "duplicates_after_cross_split",
                "eligible_unique_chunks",
            )
        )
    if not all(isinstance(v, bool) and v for v in checks.values()):
        failed = [k for k, v in checks.items() if v is not True]
        raise core.StopError(f"stream B panel reconstruction failed its checks: {failed}")
    payload = _bytes(panel_rows)
    record: dict[str, Any] = {
        "schema": core.SCHEMA_PANEL,
        "ranks": [EARLIER_PANELS * panel_size, total],
        "rank_origin": "zero-based; the half-open range [2560, 3072) = ranks 2560..3071",
        "rows": panel_size,
        "chunk_bytes": CHUNK_BYTES,
        "panel_sha256": sha256(payload),
        "row_sha256": panel_digests,
        "rows_detail": [
            {
                "rank": EARLIER_PANELS * panel_size + n,
                "row": c.row,
                "byte_offset": c.offset,
                "rank_sha256": c.rank,
                "chunk_sha256": panel_digests[n],
            }
            for n, c in enumerate(panel_rows)
        ],
        "earlier_panels": earlier_record,
        "calibration_stream": {
            "split": "training pool",
            "ranks": [4 * panel_size, 5 * panel_size],
            "sha256": sha256(_bytes(calibration)),
        },
        "train_pool_sha256": train_hash,
        "selection_first_2560_sha256": selection_sha,
        "train_selection_sha256": train_selection_sha,
        "overlap": overlap,
        "checks": checks,
        "counts": {"train": train_counts, "validation": val_counts},
        "recipe": (
            "arborlm-pilot-v1: rank sha256('arborlm-pilot-v1:validation:{row}:{offset}'), "
            "exclude chunks whose digest is a train candidate, keep the lowest rank per digest; "
            "ranks 0..2559 are P1..P5 (blocks of 512), ranks 2560..3071 are stream B"
        ),
        "python": sys.version.split()[0],
    }
    return PanelResult(payload, record)


def reconstruct_from_data_dir(data_dir: Path, repo: Path | None = None) -> PanelResult:
    """Read the pinned local WikiText-2 files (acquisition manifest and both parquet files are
    verified against their pinned SHA-256 first) and reconstruct the panel."""
    from .fetch_wikitext import DOWNLOAD_FILES, FILES, REVISION
    from .p2_data import P1_TRAIN_SHA256

    repo = repo or Path.cwd()
    from .pilot_data import _rows

    manifest_path = data_dir / "manifest.json"
    acquisition = read_json(manifest_path)
    if (
        acquisition["dataset_revision"] != REVISION
        or acquisition["selected_files"] != list(DOWNLOAD_FILES)
        or acquisition["deferred_test"]["acquired"]
        or acquisition["deferred_test"]["inspected"]
    ):
        raise core.StopError("unexpected acquisition provenance")
    inputs: dict[str, Any] = {"acquisition_manifest_sha256": file_sha256(manifest_path)}
    for name in DOWNLOAD_FILES:
        expected = FILES[name]
        entry = acquisition["files"][name]
        path = data_dir / name
        digest = file_sha256(path)
        if (
            (entry["sha256"], entry["bytes"]) != (expected["sha256"], expected["bytes"])
            or path.stat().st_size != expected["bytes"]
            or digest != expected["sha256"]
        ):
            raise core.StopError(f"pinned acquisition file mismatch: {name}")
        inputs[name] = {"sha256": digest, "bytes": expected["bytes"]}
    p5_manifest = read_json(repo / core.P5_RESULTS / "b101-o301-baseline" / "dataset_manifest.json")
    result = reconstruct_from_rows(
        _rows(data_dir / DOWNLOAD_FILES[0]),
        _rows(data_dir / DOWNLOAD_FILES[1]),
        registered_train_hash=P1_TRAIN_SHA256,
        registered_p5_manifest=p5_manifest,
    )
    result.record["p5_dataset_manifest_sha256"] = file_sha256(
        repo / core.P5_RESULTS / "b101-o301-baseline" / "dataset_manifest.json"
    )
    result.record["inputs"] = inputs
    return result


def panel_tensor(panel_bytes: bytes, record: dict[str, Any]) -> Tensor:
    """The 512 x 65 byte panel as the int64 tensor the models take, after re-checking its hash."""
    if sha256(panel_bytes) != record["panel_sha256"]:
        raise core.StopError("stream B panel bytes differ from the recorded SHA-256")
    rows = record["rows"]
    if len(panel_bytes) != rows * CHUNK_BYTES:
        raise core.StopError("stream B panel has an unexpected length")
    per_row = [sha256(panel_bytes[i * CHUNK_BYTES : (i + 1) * CHUNK_BYTES]) for i in range(rows)]
    if per_row != record["row_sha256"]:
        raise core.StopError("stream B panel rows differ from the recorded per-row SHA-256 list")
    return torch.frombuffer(bytearray(panel_bytes), dtype=torch.uint8).long().reshape(rows, -1)
