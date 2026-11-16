# ruff: noqa: E501
"""P8 Panel A and Panel B: validation ranks [3072, 3584) and [3584, 4096) (ADR-0015 section 6).

The recipe is P2/P5/P7-B's, unchanged (see ``p7b_panel``): every full 65-byte chunk of the pinned
validation file is ranked by ``sha256("arborlm-pilot-v1:validation:{row}:{offset}")`` (then row,
offset); chunks whose digest occurs among the train candidates are excluded; among equal chunks the
lowest rank is kept. Ranking does not depend on how many candidates are requested, so selecting the
first 4,096 gives the same ranks 0..3071 as earlier and the new panels are ``[3072:3584]`` and
``[3584:4096]``. That is not assumed: the six earlier panels (P1..P5 and P7-B stream B, blocks of 512)
are re-hashed and must reproduce their recorded SHA-256 values, or the proof stops.

The proof also shows zero exact-chunk overlap of each new panel with every earlier panel, with the
other new panel, with the calibration stream (training ranks 2048..2559) and with the complete
4,096-chunk training candidate pool (and with every train chunk in the file).

This module reads raw data and runs no model. ``reconstruct_from_rows`` takes iterables of text so a
test can use a tiny synthetic corpus; ``reconstruct_from_data_dir`` reads the pinned parquet files.

CLI: ``python -m arborlm.p8_panel prove --data-dir D --out OUT [--repo R] [--compare AUDITOR.json]``.
``--out`` is a directory that receives ``panel_record.json`` (hashes only), ``panel_A.bytes`` and
``panel_B.bytes`` (the raw panel bytes; local, hash-checked against the record on every load) and, with
``--compare``, ``panel_comparison.json``.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7b_core as core
from .io import atomic_write, canonical_json, file_sha256, read_json, sha256, write_json
from .p2_data import _selection
from .pilot_data import CHUNK_BYTES, Candidate, select

SCHEMA_PANEL = "P8-panel-v1"
SCHEMA_COMPARISON = "p8-panel-comparison-v1"
TRAIN_RANKED = 4096  # the frozen training pool of ranked chunks
BLOCK = 512
EARLIER_NAMES = ("P1", "P2", "P3", "P4", "P5", "P7B_streamB")
PANEL_RANKS = {"panel_A": (3072, 3584), "panel_B": (3584, 4096)}  # zero-based, half-open
TOTAL_RANKED = 4096
CAL_RANKS = (2048, 2560)  # training-pool ranks (calibration stream)
PROOF_CAP_SECONDS = 600.0
# P7-B stream B (validation ranks 2560..3071), recorded in the P7-B panel record
P7B_STREAM_B_SHA256 = "4e2c9d971ee5a1e689cba50db79fd2de500f8098de239411e5b12b9ebd240731"
EARLIER_SHA256 = {**core.PRIOR_PANEL_SHA256, "P7B_streamB": P7B_STREAM_B_SHA256}
RECORDED_IN = {
    "P1": "src/arborlm/p2_data.py P1_VALIDATION_SHA256",
    "P2": "src/arborlm/p3_data.py P2_VALIDATION_SHA256",
    "P3": "src/arborlm/p4_data.py P3_VALIDATION_SHA256",
    "P4": "src/arborlm/p4_data.py P4_VALIDATION_SHA256",
    "P5": "src/arborlm/p5_data.py P5_VALIDATION_SHA256",
    "P7B_streamB": "results/p7b-2026-11-13/panel/*/panel_record.json panel_sha256",
}


@dataclass
class PanelResult:
    panel_bytes: dict[str, bytes]
    record: dict[str, Any]


def _bytes(rows: list[Candidate]) -> bytes:
    return b"".join(chunk.payload for chunk in rows)


def _selection_global(rows: list[Candidate], lo: int) -> bytes:
    return canonical_json(
        [
            {
                "rank": lo + i,
                "row": c.row,
                "byte_offset": c.offset,
                "rank_sha256": c.rank,
                "chunk_sha256": sha256(c.payload),
            }
            for i, c in enumerate(rows)
        ]
    )


def _name(label: str, lo: int, hi: int) -> str:
    return f"{label}_ranks_{lo}_{hi - 1}"


def reconstruct_from_rows(
    train_rows: Iterable[str],
    validation_rows: Iterable[str],
    *,
    train_ranked: int = TRAIN_RANKED,
    block: int = BLOCK,
    expected_earlier: dict[str, str] | None = None,
    registered_train_hash: str | None = None,
    registered_p5_manifest: dict[str, Any] | None = None,
    registered_p7b_record: dict[str, Any] | None = None,
) -> PanelResult:
    """Rank, deduplicate and exclude exactly as P5/P7-B did, take the first ``8 * block`` ranked
    validation candidates, check the six earlier panels against their registered hashes and every
    overlap condition, and return both new panels and a record of every check. Raises
    ``StopError`` on any failed check (the study stops; no other window is substituted)."""
    expected = expected_earlier if expected_earlier is not None else EARLIER_SHA256
    n_earlier = len(EARLIER_NAMES)
    total = (n_earlier + len(PANEL_RANKS)) * block
    train, full_train, train_counts = select(train_rows, "train", train_ranked)
    validation, _, val_counts = select(validation_rows, "validation", total, excluded=full_train)
    if len(validation) != total:
        raise core.StopError("fewer ranked validation candidates than the panels need")
    earlier = validation[: n_earlier * block]
    checks: dict[str, Any] = {}
    earlier_record: dict[str, Any] = {}
    for n, name in enumerate(EARLIER_NAMES):
        rows = earlier[n * block : (n + 1) * block]
        digest = sha256(_bytes(rows))
        earlier_record[name] = {
            "ranks": [n * block, (n + 1) * block],
            "recorded_in": RECORDED_IN[name],
            "recorded_sha256": expected[name],
            "sha256": digest,
            "reproduced": digest == expected[name],
        }
    checks["all_six_earlier_reproduced"] = all(v["reproduced"] for v in earlier_record.values())

    cal = train[4 * block : 5 * block]  # training ranks 2048..2559 when block = 512
    panel_ranks = {
        name: ((n_earlier + i) * block, (n_earlier + i + 1) * block)
        for i, name in enumerate(PANEL_RANKS)
    }
    pool = {sha256(c.payload) for c in train}
    sets: dict[str, set[str]] = {
        _name("earlier_validation", 0, n_earlier * block): {sha256(c.payload) for c in earlier},
        _name("calibration_stream_train", 4 * block, 5 * block): {sha256(c.payload) for c in cal},
        _name("training_candidate_pool_train", 0, train_ranked): pool,
        "every_train_chunk_in_file": set(full_train),
    }
    for n, name in enumerate(EARLIER_NAMES):
        lo, hi = n * block, (n + 1) * block
        sets[_name(f"earlier_{name}", lo, hi)] = {sha256(c.payload) for c in validation[lo:hi]}
    panels: dict[str, Any] = {}
    payloads: dict[str, bytes] = {}
    digests: dict[str, list[str]] = {}
    new_rows: dict[str, list[Candidate]] = {}
    for name, (lo, hi) in panel_ranks.items():
        rows = validation[lo:hi]
        new_rows[name] = rows
        digests[name] = [sha256(c.payload) for c in rows]
        payloads[name] = _bytes(rows)
    for name, (lo, hi) in panel_ranks.items():
        rows, d = new_rows[name], digests[name]
        other = next(k for k in panel_ranks if k != name)
        overlap = {k: len(set(d) & s) for k, s in sets.items()}
        overlap["other_new_panel"] = len(set(d) & set(digests[other]))
        panels[name] = {
            "ranks": [lo, hi],
            "ranks_inclusive": [lo, hi - 1],
            "rows": len(rows),
            "bytes": len(payloads[name]),
            "panel_sha256": sha256(payloads[name]),
            "row_sha256_list_sha256": sha256(("\n".join(d) + "\n").encode()),
            "selection_sha256_global_rank": sha256(_selection_global(rows, lo)),
            "selection_sha256_local_rank": sha256(_selection(rows)),
            "duplicates_within_panel": len(d) - len(set(d)),
            "overlap": overlap,
            "first_rows_detail": [
                {
                    "rank": lo + i,
                    "row": c.row,
                    "byte_offset": c.offset,
                    "rank_sha256": c.rank,
                    "chunk_sha256": d[i],
                }
                for i, c in enumerate(rows[:3])
            ],
            "row_sha256": d,
            "rows_detail": [
                {
                    "rank": lo + i,
                    "row": c.row,
                    "byte_offset": c.offset,
                    "rank_sha256": c.rank,
                    "chunk_sha256": d[i],
                }
                for i, c in enumerate(rows)
            ],
        }
    checks["zero_exact_overlap"] = all(
        p["duplicates_within_panel"] == 0
        and not any(p["overlap"].values())
        and p["rows"] == block
        and p["bytes"] == block * CHUNK_BYTES
        for p in panels.values()
    )
    checks["panels_have_full_chunks"] = all(
        len(c.payload) == CHUNK_BYTES for rows in new_rows.values() for c in rows
    )
    checks["at_least_4096_eligible"] = val_counts["eligible_unique_chunks"] >= total
    train_hash = sha256(_bytes(train))
    if registered_train_hash is not None:
        checks["train_pool_reproduced"] = train_hash == registered_train_hash
    selection_sha = sha256(_selection(validation[:2560]))
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
    if registered_p7b_record is not None:
        b = validation[2560:3072]
        detail = [
            {
                "rank": 2560 + i,
                "row": c.row,
                "byte_offset": c.offset,
                "rank_sha256": c.rank,
                "chunk_sha256": sha256(c.payload),
            }
            for i, c in enumerate(b)
        ]
        checks["p7b_stream_b_rows_detail_equal"] = detail == registered_p7b_record["rows_detail"]
    if not all(isinstance(v, bool) and v for v in checks.values()):
        failed = [k for k, v in checks.items() if v is not True]
        raise core.StopError(f"P8 panel reconstruction failed its checks: {failed}")
    record: dict[str, Any] = {
        "schema": SCHEMA_PANEL,
        "panels": {name: {k: v for k, v in p.items()} for name, p in panels.items()},
        "earlier_panels": earlier_record,
        "calibration_stream": {
            "split": "training pool",
            "ranks": [4 * block, 5 * block],
            "rows": len(cal),
            "sha256": sha256(_bytes(cal)),
        },
        "train_pool_sha256": train_hash,
        "selection_first_2560_sha256": selection_sha,
        "train_selection_sha256": train_selection_sha,
        "validation_eligible_candidates": val_counts["eligible_unique_chunks"],
        "counts": {"train": train_counts, "validation": val_counts},
        "checks": checks,
        "chunk_bytes": CHUNK_BYTES,
        "recipe": (
            "arborlm-pilot-v1: rank sha256('arborlm-pilot-v1:validation:{row}:{offset}'), exclude "
            "chunks whose digest is a train candidate, keep the lowest rank per digest; ranks "
            "0..3071 are P1..P5 and P7-B stream B (blocks of 512), ranks 3072..3583 are Panel A, "
            "3584..4095 are Panel B"
        ),
        "python": sys.version.split()[0],
    }
    return PanelResult(payloads, record)


def _p7b_record_path(repo: Path) -> Path:
    found = sorted((repo / core.DEFAULT_RESULTS / "panel").glob("*/panel_record.json"))
    if len(found) != 1:
        raise core.StopError(f"expected exactly one P7-B panel record, found {len(found)}")
    return found[0]


def reconstruct_from_data_dir(data_dir: Path, repo: Path | None = None) -> PanelResult:
    """Read the pinned local WikiText-2 files (acquisition manifest and both parquet files verified
    against their pinned SHA-256 first) and reconstruct the panels."""
    from .fetch_wikitext import DOWNLOAD_FILES, FILES, REVISION
    from .p2_data import P1_TRAIN_SHA256
    from .pilot_data import _rows

    repo = repo or Path.cwd()
    manifest_path = data_dir / "manifest.json"
    acquisition = read_json(manifest_path)
    if (
        acquisition["dataset_revision"] != REVISION
        or acquisition["selected_files"] != list(DOWNLOAD_FILES)
        or acquisition["deferred_test"]["acquired"]
        or acquisition["deferred_test"]["inspected"]
    ):
        raise core.StopError("unexpected acquisition provenance")
    inputs: dict[str, Any] = {"manifest.json": {"sha256": file_sha256(manifest_path)}}
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
        inputs[name] = {"sha256": digest, "bytes": expected["bytes"], "matches_pinned": True}
    p5_path = repo / core.P5_RESULTS / "b101-o301-baseline" / "dataset_manifest.json"
    p7b_path = _p7b_record_path(repo)
    p7b = read_json(p7b_path)
    if p7b["panel_sha256"] != P7B_STREAM_B_SHA256:
        raise core.StopError("the P7-B panel record does not carry the registered stream B hash")
    result = reconstruct_from_rows(
        _rows(data_dir / DOWNLOAD_FILES[0]),
        _rows(data_dir / DOWNLOAD_FILES[1]),
        registered_train_hash=P1_TRAIN_SHA256,
        registered_p5_manifest=read_json(p5_path),
        registered_p7b_record=p7b,
    )
    result.record["inputs"] = inputs
    result.record["identity_crosschecks"] = {
        "P5_manifest_sha256": file_sha256(p5_path),
        "P7B_panel_record_sha256": file_sha256(p7b_path),
    }
    return result


# --- loading for the evaluation stage -------------------------------------------------------------
def _tensor(raw: bytes, rows: int) -> Tensor:
    if len(raw) != rows * CHUNK_BYTES:
        raise core.StopError("panel bytes have an unexpected length")
    return torch.frombuffer(bytearray(raw), dtype=torch.uint8).long().reshape(rows, CHUNK_BYTES)


def verify_panel_bytes(raw: bytes, name: str, record: dict[str, Any]) -> Tensor:
    """The 512 x 65 int64 tensor the models take (the shape ``p5_data.load_frozen`` returns), after
    checking the whole-panel and per-row SHA-256 against the frozen record."""
    entry = record["panels"][name]
    if sha256(raw) != entry["panel_sha256"]:
        raise core.StopError(f"{name} bytes differ from the frozen SHA-256")
    rows = int(entry["rows"])
    tensor = _tensor(raw, rows)
    per_row = [sha256(raw[i * CHUNK_BYTES : (i + 1) * CHUNK_BYTES]) for i in range(rows)]
    if per_row != entry["row_sha256"]:
        raise core.StopError(f"{name} rows differ from the frozen per-row SHA-256 list")
    return tensor


def panel_tensors(
    data_dir: Path,
    record: dict[str, Any],
    *,
    cache_dir: Path | None = None,
    repo: Path | None = None,
) -> tuple[Tensor, Tensor]:
    """(Panel A, Panel B) as int64 ``[512, 65]`` tensors, verified against the frozen ``record``.
    With ``cache_dir`` holding ``panel_A.bytes`` / ``panel_B.bytes`` (written by ``prove``) those are
    read; otherwise the panels are rebuilt from the pinned data (slow). Either way the hashes are
    checked against ``record`` before anything is returned."""
    names = tuple(PANEL_RANKS)
    if cache_dir is not None and all((cache_dir / f"{n}.bytes").is_file() for n in names):
        raws = {n: (cache_dir / f"{n}.bytes").read_bytes() for n in names}
    else:
        raws = reconstruct_from_data_dir(data_dir, repo).panel_bytes
    a, b = (verify_panel_bytes(raws[n], n, record) for n in names)
    return a, b


def calibration_tensor(
    data_dir: Path, record: dict[str, Any] | None = None, *, repo: Path | None = None
) -> Tensor:
    """Training-pool ranks 2048..2559 as int64 ``[512, 65]`` (as ``p7b_workers.
    calibration_slice_real``), verified against ``record['calibration_stream']`` when given."""
    from .fetch_wikitext import DOWNLOAD_FILES
    from .p2_data import P1_TRAIN_SHA256
    from .pilot_data import _rows

    train, _, _ = select(_rows(data_dir / DOWNLOAD_FILES[0]), "train", TRAIN_RANKED)
    if sha256(_bytes(train)) != P1_TRAIN_SHA256:
        raise core.StopError("the training pool differs from P1's registered hash")
    raw = _bytes(train[CAL_RANKS[0] : CAL_RANKS[1]])
    if record is not None and sha256(raw) != record["calibration_stream"]["sha256"]:
        raise core.StopError("calibration bytes differ from the frozen SHA-256")
    return _tensor(raw, CAL_RANKS[1] - CAL_RANKS[0])


def calibration_from_train(train: Tensor) -> Tensor:
    """The same slice from an already loaded 4,096 x 65 training tensor."""
    if tuple(train.shape) != (TRAIN_RANKED, CHUNK_BYTES):
        raise ValueError("the frozen training pool does not hold 4,096 ranked chunks")
    return train[CAL_RANKS[0] : CAL_RANKS[1]]


# --- comparison with the auditor's independent tool ------------------------------------------------
COMPARED_PANEL_FIELDS = (
    "ranks",
    "ranks_inclusive",
    "rows",
    "bytes",
    "panel_sha256",
    "row_sha256_list_sha256",
    "selection_sha256_global_rank",
    "selection_sha256_local_rank",
    "duplicates_within_panel",
    "overlap",
    "first_rows_detail",
)


def compare_with_auditor(record: dict[str, Any], auditor: dict[str, Any]) -> dict[str, Any]:
    """Byte-for-byte comparison of every field both documents carry. Never raises; the result lists
    each compared field and every difference."""
    diffs: list[dict[str, Any]] = []
    compared = 0

    def check(where: str, mine: Any, theirs: Any) -> None:
        nonlocal compared
        compared += 1
        if canonical_json(mine) != canonical_json(theirs):
            diffs.append({"field": where, "implementation": mine, "auditor": theirs})

    for name in PANEL_RANKS:
        mine, theirs = record["panels"][name], auditor["new_panels"][name]
        for field in COMPARED_PANEL_FIELDS:
            check(f"{name}.{field}", mine[field], theirs[field])
    for name in EARLIER_NAMES:
        check(
            f"earlier.{name}.sha256",
            record["earlier_panels"][name]["sha256"],
            auditor["earlier_panels"][name]["sha256"],
        )
        check(
            f"earlier.{name}.recorded_sha256",
            record["earlier_panels"][name]["recorded_sha256"],
            auditor["earlier_panels"][name]["recorded_sha256"],
        )
        check(f"earlier.{name}.reproduced", True, auditor["earlier_panels"][name]["reproduced"])
    for key in (
        "manifest.json",
        "train-00000-of-00001.parquet",
        "validation-00000-of-00001.parquet",
    ):
        check(
            f"inputs.{key}.sha256",
            record["inputs"][key]["sha256"],
            auditor["inputs"][key]["sha256"],
        )
    for split in ("train", "validation"):  # every count the auditor reports (it omits the
        for key, theirs in auditor["counts"][split].items():  # request-dependent not_selected)
            check(f"counts.{split}.{key}", record["counts"][split][key], theirs)
    check(
        "validation_eligible_candidates",
        record["validation_eligible_candidates"],
        auditor["validation_eligible_candidates"],
    )
    check(
        "zero_exact_overlap", record["checks"]["zero_exact_overlap"], auditor["zero_exact_overlap"]
    )
    cross = auditor.get("identity_crosschecks", {})
    for key, mine in record.get("identity_crosschecks", {}).items():
        if key in cross:
            check(f"identity_crosschecks.{key}", mine, cross[key])
    return {
        "schema": SCHEMA_COMPARISON,
        "fields_compared": compared,
        "differences": diffs,
        "verdict": "AGREE" if not diffs else "DISAGREE",
        "auditor_tool": auditor.get("tool"),
        "auditor_tool_sha256": auditor.get("tool_sha256"),
        "label": "self-check of byte-for-byte agreement; not independent review, not Astra validation",
    }


def prove(
    data_dir: Path, out: Path, repo: Path | None = None, compare: Path | None = None
) -> dict[str, Any]:
    started = time.monotonic()
    result = reconstruct_from_data_dir(data_dir, repo)
    out.mkdir(parents=True, exist_ok=True)
    for name, raw in result.panel_bytes.items():
        atomic_write(out / f"{name}.bytes", raw)
    record = dict(result.record)
    record["seconds"] = time.monotonic() - started
    record["cap_seconds"] = PROOF_CAP_SECONDS
    write_json(out / "panel_record.json", record)
    summary: dict[str, Any] = {
        "record": str(out / "panel_record.json"),
        "record_sha256": file_sha256(out / "panel_record.json"),
        "panel_A_sha256": record["panels"]["panel_A"]["panel_sha256"],
        "panel_B_sha256": record["panels"]["panel_B"]["panel_sha256"],
        "seconds": record["seconds"],
    }
    if compare is not None:
        comparison = compare_with_auditor(record, read_json(compare))
        comparison["auditor_json_sha256"] = file_sha256(compare)
        comparison["record_sha256"] = summary["record_sha256"]
        write_json(out / "panel_comparison.json", comparison)
        summary["comparison"] = {k: comparison[k] for k in ("verdict", "fields_compared")}
        summary["differences"] = comparison["differences"]
    return summary


def main(argv: list[str] | None = None) -> int:
    import json

    parser = argparse.ArgumentParser(prog="python -m arborlm.p8_panel")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prove", help="reconstruct Panels A and B and prove the overlap conditions")
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--repo", type=Path, default=None)
    p.add_argument("--compare", type=Path, default=None, help="auditor's panel_confirmation JSON")
    args = parser.parse_args(argv)
    try:
        summary = prove(args.data_dir, args.out, args.repo, args.compare)
    except core.StopError as exc:
        print(f"P8 panel STOP: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary.get("comparison", {}).get("verdict") == "DISAGREE":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
