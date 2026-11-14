"""Independent reconstruction of the P7-B stream B panel (validation ranks 2560..3071) and the panel
confirmation file (gate (a), schema ``p7b-panel-confirmation-v1``).

Auditor role (Claude Opus 5.5). Written from the registered recipe (``arborlm-pilot-v1``, as recorded
in pilot_data.RECIPE / p2_data / p5_data, read but not imported): every row's exact UTF-8 bytes are
cut into 65-byte chunks at stride 65 from offset 0 (a trailing remainder is dropped); a chunk's rank
key is sha256("arborlm-pilot-v1:{split}:{row}:{offset}") then row, then offset; within a split only
the lowest-ranked copy of identical chunk contents is kept; a validation chunk whose contents equal
any train chunk is excluded; the ranked train pool is the first 4,096 train chunks; ranks 0..2559 of
the validation ranking are the P1..P5 panels (blocks of 512); the new panel is ranks 2560..3071.
No ``arborlm`` import. Standard library only, except reading the parquet files needs ``pyarrow``
(run with ``uv run --locked --extra pilot python -I``). Independent engineering evidence; not Astra
validation and not human approval.

Modes:
  real      (after the freeze, once the implementer's panel stage has run): reads the pinned local
            WikiText-2 train and validation parquet files after verifying their SHA-256.
  synthetic (validation only): reads a JSON file {"train": [...], "validation": [...]} of strings.

Usage: see AUDIT.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TOOL = "independent_panel.py (auditor role, Claude Opus 5.5) v1"
CHUNK = 65
PINNED = {  # fetch_wikitext.FILES (pinned revision b08601e04326c79dfdd32d625aee71d232d685c3)
    "train-00000-of-00001.parquet": ("e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7", 6_357_543),
    "validation-00000-of-00001.parquet": ("204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c", 657_209),
}
REGISTERED_PANELS = {  # ADR-0010 section 4 / p2..p5 data modules
    "P1": "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200",
    "P2": "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2",
    "P3": "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0",
    "P4": "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f",
    "P5": "d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98",
}
P1_TRAIN_SHA256 = "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
P5_FIRST_2560_SELECTION_SHA256 = "4c0aaff5a64c30b64ec6e530b3a85fa4a0e75e66069a1a072425bf4eab8fe2cb"
P5_TRAIN_SELECTION_SHA256 = "9543109e906b81af2e04e34b0094388e126a1d9f073e6cc6dd75487bd6aba5ad"
P5_VALIDATION_ELIGIBLE = 16407  # results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def ranked_chunks(rows: list[str], split: str, excluded: set[str] | None) -> tuple[list[tuple], set[str], dict]:
    """[(rank_hex, row, offset, payload, chunk_digest)] sorted, one per distinct content; the set of
    every distinct chunk digest of the split (after exclusion); and counters."""
    best: dict[str, tuple] = {}
    n_chunks = n_excluded = 0
    for r, text in enumerate(rows):
        if not isinstance(text, str):
            raise SystemExit(f"non-string row {split}:{r}")
        data = text.encode("utf-8")
        for off in range(0, len(data) // CHUNK * CHUNK, CHUNK):
            payload = data[off : off + CHUNK]
            n_chunks += 1
            digest = h(payload)
            if excluded is not None and digest in excluded:
                n_excluded += 1
                continue
            key = (h(f"arborlm-pilot-v1:{split}:{r}:{off}".encode()), r, off)
            cur = best.get(digest)
            if cur is None or key < cur[:3]:
                best[digest] = (*key, payload, digest)
    ranked = sorted(best.values(), key=lambda c: c[:3])
    return ranked, set(best), {"rows": len(rows), "full_chunks": n_chunks,
                               "excluded_cross_split": n_excluded, "eligible_unique_chunks": len(ranked)}


def selection_json(rows: list[tuple]) -> bytes:
    """The P2/P5 'selected.json' canonical form (sorted keys, compact, trailing newline)."""
    items = [{"rank": i, "row": c[1], "byte_offset": c[2], "rank_sha256": c[0], "chunk_sha256": c[4]}
             for i, c in enumerate(rows)]
    return (json.dumps(items, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def parquet_rows(path: Path) -> list[str]:
    from pyarrow import parquet  # only dependency outside the standard library

    out: list[str] = []
    with parquet.ParquetFile(path) as fh:
        for batch in fh.iter_batches(columns=["text"], use_threads=False):
            out.extend(batch.column(0).to_pylist())
    return out


def reconstruct(train_rows, val_rows, *, panel_size, train_pool, registered, real: bool) -> dict:
    train_ranked, train_digests, train_counts = ranked_chunks(train_rows, "train", None)
    if len(train_ranked) < train_pool:
        raise SystemExit("too few train chunks")
    pool = train_ranked[:train_pool]
    val_ranked, _, val_counts = ranked_chunks(val_rows, "validation", train_digests)
    need = 6 * panel_size
    if len(val_ranked) < need:
        raise SystemExit(f"only {len(val_ranked)} eligible validation chunks, need {need}")
    earlier = val_ranked[: 5 * panel_size]
    panel = val_ranked[5 * panel_size : need]
    earlier_hashes = {f"P{n + 1}": h(b"".join(c[3] for c in earlier[n * panel_size : (n + 1) * panel_size]))
                      for n in range(5)}
    cal = pool[4 * panel_size : 5 * panel_size]  # training-pool ranks 2048..2559 when panel_size = 512
    panel_digests = [c[4] for c in panel]
    pset = set(panel_digests)
    overlap = {
        "with_P1_to_P5_panels": len(pset & {c[4] for c in earlier}),
        "with_calibration_stream": len(pset & {c[4] for c in cal}),
        "with_full_training_pool": len(pset & train_digests),
        "duplicates_within_panel": len(panel_digests) - len(pset),
    }
    checks = {
        "earlier_panels_equal_registered": earlier_hashes == registered,
        "zero_overlap": not any(overlap.values()),
        "panel_rows": len(panel) == panel_size,
        "every_row_65_bytes": all(len(c[3]) == CHUNK for c in panel),
    }
    extra = {}
    if real:  # registered identities apply to the real files only (attempt 1 applied them always)
        extra = {
            "train_pool_sha256": h(b"".join(c[3] for c in pool)),
            "train_pool_equals_P1": h(b"".join(c[3] for c in pool)) == P1_TRAIN_SHA256,
            "first_2560_selection_sha256": h(selection_json(earlier)),
            "first_2560_selection_equals_P5": h(selection_json(earlier)) == P5_FIRST_2560_SELECTION_SHA256,
            "train_selection_equals_P5": h(selection_json(pool)) == P5_TRAIN_SELECTION_SHA256,
            "validation_eligible_equals_P5_manifest": val_counts["eligible_unique_chunks"] == P5_VALIDATION_ELIGIBLE,
        }
        checks.update({k: v for k, v in extra.items() if isinstance(v, bool)})
    return {
        "ranks": [5 * panel_size, need],
        "panel_sha256": h(b"".join(c[3] for c in panel)),
        "row_sha256": panel_digests,
        "rows_detail": [{"rank": 5 * panel_size + i, "row": c[1], "byte_offset": c[2], "rank_sha256": c[0]}
                        for i, c in enumerate(panel)],
        "earlier_panels": earlier_hashes,
        "overlap": overlap,
        "checks": checks,
        "extra": extra,
        "counts": {"train": train_counts, "validation": val_counts},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("real", "synthetic"), required=True)
    ap.add_argument("--data-dir", type=Path, default=Path("data/wikitext2"))
    ap.add_argument("--synthetic-rows", type=Path, help="synthetic mode: JSON {train: [...], validation: [...]}")
    ap.add_argument("--panel-size", type=int, default=512, help="synthetic mode only")
    ap.add_argument("--train-pool", type=int, default=4096, help="synthetic mode only")
    ap.add_argument("--panel-record", type=Path, required=True, help="the implementer's panel_record.json")
    ap.add_argument("--panel-run-id", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--detail", type=Path, required=True)
    args = ap.parse_args()
    inputs: dict = {}
    if args.mode == "real":
        if args.panel_size != 512 or args.train_pool != 4096:
            raise SystemExit("real mode uses the registered sizes")
        rows = {}
        for name, split in (("train-00000-of-00001.parquet", "train"),
                            ("validation-00000-of-00001.parquet", "validation")):
            path = args.data_dir / name
            digest, size = PINNED[name]
            if path.stat().st_size != size or file_sha256(path) != digest:
                raise SystemExit(f"pinned file mismatch: {name}")
            inputs[name] = {"sha256": digest, "bytes": size}
            rows[split] = parquet_rows(path)
        registered = REGISTERED_PANELS
    else:
        data = json.loads(args.synthetic_rows.read_text())
        rows = {"train": data["train"], "validation": data["validation"]}
        registered = data.get("registered_earlier")  # synthetic: supplied by the validation harness
        inputs["synthetic_rows_sha256"] = file_sha256(args.synthetic_rows)
    mine = reconstruct(rows["train"], rows["validation"], panel_size=args.panel_size,
                       train_pool=args.train_pool, registered=registered,
                       real=args.mode == "real")
    record_path = args.panel_record.resolve()
    theirs = json.loads(record_path.read_text())
    comparison = {
        "panel_sha256_equal": mine["panel_sha256"] == theirs.get("panel_sha256"),
        "row_sha256_equal": mine["row_sha256"] == theirs.get("row_sha256"),
        "ranks_equal": mine["ranks"] == theirs.get("ranks"),
        "rows_detail_equal": [(d["rank"], d["row"], d["byte_offset"], d["rank_sha256"]) for d in mine["rows_detail"]]
        == [(d["rank"], d["row"], d["byte_offset"], d["rank_sha256"]) for d in theirs.get("rows_detail", [])],
        "earlier_equal": mine["earlier_panels"] == {k: v["sha256"] for k, v in theirs.get("earlier_panels", {}).items()},
    }
    agree = all(mine["checks"].values()) and all(comparison.values())
    tool_sha = file_sha256(Path(__file__))
    confirmation = {
        "schema": "p7b-panel-confirmation-v1",
        "verdict": "AGREE" if agree else "DISAGREE",
        "tool": f"{TOOL}; sha256 {tool_sha}",
        "tool_sha256": tool_sha,
        "panel_stage_run_id": args.panel_run_id,
        "panel_record_sha256": file_sha256(record_path),
        "ranks": mine["ranks"],
        "panel_sha256": mine["panel_sha256"],
        "row_sha256": mine["row_sha256"],
        "earlier_panels_reproduced": mine["earlier_panels"],
        "overlap": mine["overlap"],
        "checks": mine["checks"],
        "comparison_with_implementer": comparison,
        "mode": args.mode,
        "label": "independent engineering evidence; not Astra validation; not human approval",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(confirmation, indent=1, sort_keys=True) + "\n")
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_text(json.dumps({"inputs": inputs, "python": sys.version, **mine,
                                       "comparison": comparison}, indent=1, sort_keys=True) + "\n")
    print(f"{confirmation['verdict']}: mode {args.mode}, ranks {mine['ranks']}, checks {mine['checks']}, "
          f"comparison {comparison}")
    return 0 if agree else 2


if __name__ == "__main__":
    sys.exit(main())
