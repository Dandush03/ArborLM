"""C7 - recount of the rev 1 matrix (section 10), parameter matching (5.6) and budget (RESOURCE_BUDGET.md).

Pure arithmetic from the numbers printed in the design documents and the benchmark output
benchmark/indicative_update_timing_run1.jsonl (read, not re-run).
"""

import json
import math
import sys
from pathlib import Path

# --- 1. matrix: (block, configurations, cells as listed) --------------------------------------------
BLOCKS = [("A1", 3, 9), ("A2", 3, 9), ("A3", 1, 2), ("A4", 2, 4), ("A5", 6, 12), ("A6", 1, 2), ("A7", 4, 8),
          ("A8", 5, 10), ("A9", 3, 6), ("B1", 10, 20), ("C1", 4, 8), ("D1", 3, 6), ("D2", 6, 12)]
# --- 2. cells by size, from the block definitions -----------------------------------------------------
# (size, block, cells, kind) kind: flat | tree | dense | r2 ; updates per cell
CELLS = [
    (4096, "A1", 3, "flat", 2048), (16384, "A1", 3, "flat", 2048), (65536, "A1", 3, "flat", 8192),
    (4096, "A2", 3, "tree", 2048), (16384, "A2", 3, "tree", 2048), (65536, "A2", 3, "tree", 8192),
    (16384, "A3", 2, "tree", 2048),
    (16384, "A4", 2, "flat", 2048), (65536, "A4", 2, "flat", 2048),
    (4096, "A5", 4, "flat", 2048), (16384, "A5", 4, "flat", 2048), (65536, "A5", 4, "flat", 8192),
    (16384, "A6", 2, "tree", 2048),
    (16384, "A7", 4, "flat", 2048), (65536, "A7", 4, "flat", 8192),
    (4096, "A8", 2, "dense", 2048), (16384, "A8", 4, "dense", 2048), (65536, "A8", 4, "dense", 8192),
    (16384, "A9", 6, "mixed", None),
    (16384, "B1", 10, "flat", 2048), (16384, "B1", 10, "tree", 2048),
    (16384, "C1", 4, "flat", 2048), (16384, "C1", 4, "tree", 2048),
    (16384, "D1", 6, "mixed", 1024), (16384, "D2", 10, "mixed", 1024), (16384, "D2", 2, "flat", 2048),
]
ALLOW = {4096: {"flat": 0.013, "dense": 0.013, "tree": 0.10}, 16384: {"flat": 0.04, "dense": 0.04, "tree": 0.10},
         65536: {"flat": 0.13, "dense": 0.13, "tree": 0.10}}


def params(n: int, key: int = 16, tree: bool = False) -> int:
    branches = n // 256
    return n * key + n * 32 + key * 32 + 32 * 32 + 1 + (branches * key if tree else 0)


def main(root: Path) -> None:
    total = sum(c for _, _, c in BLOCKS)
    print(json.dumps({"listed_total": total, "listed_ok": total == 108}))
    by_size: dict[int, int] = {}
    for size, _, cells, _, _ in CELLS:
        by_size[size] = by_size.get(size, 0) + cells
    print(json.dumps({"cells_by_size": by_size, "sum": sum(by_size.values())}))
    # serial training hours with the budget's own allowance; A9 has no update count in rev 1 (assume 2048)
    hours: dict[int, float] = {}
    for size, block, cells, kind, updates in CELLS:
        u = updates or 2048
        k = "flat" if kind in ("mixed", "r2") else kind
        if kind == "mixed":
            k = "tree"  # conservative
        hours[size] = hours.get(size, 0.0) + cells * u * ALLOW[size][k] / 3600
    print(json.dumps({"serial_training_hours_by_size_auditor": {k: round(v, 2) for k, v in hours.items()},
                      "total": round(sum(hours.values()), 2), "budget_says": {"65536": 5.25, "16384": 3.5, "4096": 0.4}}))
    # A9 has no updates / exposures / classes in rev 1
    print(json.dumps({"A9_family2_updates_specified": False, "A9_thresholds_specified": False}))
    # --- parameter matching
    for n in (4096, 16384, 65536):
        for key in (16, 32):
            p = params(n, key)
            width = (p - 1) / 64
            print(json.dumps({"slots": n, "key_width": key, "flat_params": p, "tree_params": params(n, key, True),
                              "dense_hidden_width_to_match_flat": round(width, 1),
                              "dense_MACs_per_token": 2 * 32 * round(width),
                              "flat_key_MACs_per_token": n * key, "tree_key_MACs_per_token": (n // 256 + 512) * key}))
    # --- benchmark file
    bench = root / "docs/reviews/adr-0017-design-2026-11-14/benchmark/indicative_update_timing_run1.jsonl"
    rows = [json.loads(x) for x in bench.read_text().splitlines() if x.strip()]
    for r in rows:
        flops = 3 * 2 * r["positions"] * r["slots"] * 16 if r["kind"] == "flat" else None
        print(json.dumps({**r, "approx_flat_score_flops_fwd_bwd": flops,
                          "approx_GFLOP_per_s": round(flops / r["s_per_update"] / 1e9, 1) if flops else None}))
    # --- evaluation cost at 65,536 slots if evaluated as full forwards (no cached selection)
    facts = 32768
    positions = facts // 8 * 64
    score_flops = 2 * positions * 65536 * 16
    gflops = 75.0  # forward-only throughput assumed equal to the benchmark's fwd+bwd effective rate
    per_forward_s = score_flops / (gflops * 1e9)
    forwards = 3 + 1 + 2 + 4 + 2 * 64  # panels A,B,same; unseen; calibration(2x); permuted+disabled x2; 64 groups x2
    print(json.dumps({"eval_positions_per_panel_64K": positions, "score_GFLOP_per_full_panel_forward": round(score_flops / 1e9, 1),
                      "seconds_per_full_forward_at_75_GFLOPs": round(per_forward_s, 1),
                      "full_forwards_per_snapshot_if_uncached": forwards,
                      "minutes_per_snapshot_uncached": round(forwards * per_forward_s / 60, 1),
                      "snapshots_64K_matched_cells": 18 * 3,
                      "hours_64K_eval_uncached": round(18 * 3 * forwards * per_forward_s / 3600, 1),
                      "budget_eval_allowance_hours_total": 2.7}))
    # --- P7-B co-access code reuse at larger N (p7b_layout.pair_affinity: dense int32 n x n; int16 layout blobs)
    for n in (4096, 16384, 65536):
        print(json.dumps({"distinct_slots_n": n, "pair_affinity_dense_int32_GiB": round(n * n * 4 / 2**30, 2),
                          "int16_layout_serialization_ok": n - 1 <= 32767}))
    print(json.dumps({"python": sys.version.split()[0]}))
    _ = math


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
