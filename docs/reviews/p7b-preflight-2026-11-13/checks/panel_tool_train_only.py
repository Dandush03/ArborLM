"""Partial real-data check of tools/independent_panel.py WITHOUT opening the validation file: read
only the pinned TRAIN parquet with the tool's own reader and ranking, and confirm that the ranked
train pool reproduces the registered P1 train hash and P5's frozen train selection hash, and the
P5 manifest's train counters. Auditor role. Run with `uv run --locked --extra pilot python -I`.
"""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "docs/reviews/p7b-preflight-2026-11-13/tools"))
import independent_panel as P  # noqa: E402


def main() -> int:
    t0 = time.monotonic()
    name = "train-00000-of-00001.parquet"
    path = REPO / "data/wikitext2" / name
    digest, size = P.PINNED[name]
    assert path.stat().st_size == size and P.file_sha256(path) == digest, "pinned train file mismatch"
    rows = P.parquet_rows(path)
    ranked, digests, counts = P.ranked_chunks(rows, "train", None)
    pool = ranked[:4096]
    p5 = json.loads((REPO / "results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json").read_text())
    rec = p5["counts"]["train"]
    out = {
        "train_rows": counts["rows"],
        "train_full_chunks": counts["full_chunks"],
        "train_eligible_unique": counts["eligible_unique_chunks"],
        "p5_manifest_train_counts": {k: rec[k] for k in ("rows", "full_chunks", "eligible_unique_chunks")},
        "counts_equal_p5": (counts["rows"], counts["full_chunks"], counts["eligible_unique_chunks"])
        == (rec["rows"], rec["full_chunks"], rec["eligible_unique_chunks"]),
        "train_pool_sha256_equals_P1": P.h(b"".join(c[3] for c in pool)) == P.P1_TRAIN_SHA256,
        "train_selection_equals_P5_frozen": P.h(P.selection_json(pool)) == P.P5_TRAIN_SELECTION_SHA256,
        "seconds": time.monotonic() - t0,
        "validation_file_opened": False,
    }
    print(json.dumps(out, indent=1))
    ok = out["counts_equal_p5"] and out["train_pool_sha256_equals_P1"] and out["train_selection_equals_P5_frozen"]
    print("TRAIN-ONLY REAL CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
