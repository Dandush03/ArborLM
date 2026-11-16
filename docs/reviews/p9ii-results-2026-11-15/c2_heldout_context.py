"""P9-II results audit, part C2 (descriptive): held-out-template ratios and the fact-independent share of the un-centred query at the
readout, per arm at 4,096 and 16,384 (4U). Context for why A5-C fails condition 4 while its Panel A accuracy is 0.97-1.00.

Usage: python3 -I docs/reviews/p9ii-results-2026-11-15/c2_heldout_context.py <raw-run-dir>
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

RAW = Path(sys.argv[1])
for stage, n, ro in ((1, 4096, 8192), (2, 16384, 32768)):
    for arm in ("A0", "A1", "A4", "A5-C", "A5-D"):
        rows = []
        for d in sorted((RAW / "cells").glob(f"S{stage}-{arm}-n{n}-d*")):
            if d.name.split(f"-n{n}-")[0] != f"S{stage}-{arm}":
                continue
            e = json.loads((d / "eval" / f"u{ro:07d}" / "eval.json").read_text())
            a = e["panels"]["A"]["accuracy"]
            rows.append((d.name[-6:], a, e["secondary"]["H1"]["accuracy"] / a, e["secondary"]["H2"]["accuracy"] / a,
                         e["probe"]["fact_independent_share"], e["probe"].get("centred_query", {}).get("mean_cosine_different")))
        if not rows:
            continue
        good = [r for r in rows if r[1] > 0.5]
        print(f"S{stage} {arm}: cells {len(rows)}, with Panel A > 0.5: {len(good)}; fact-independent share (un-centred) median "
              f"{statistics.median(r[4] for r in rows):.3f}; min(H1/A, H2/A) per cell with A > 0.5: "
              f"{sorted(round(min(r[2], r[3]), 3) for r in good)}")
        if arm in ("A0", "A5-C"):
            for r in rows:
                print(f"    {r[0]}: A {r[1]:.4f} H1/A {r[2]:.3f} H2/A {r[3]:.3f} fact-indep {r[4]:.3f}"
                      + (f" centred mean cos {r[5]:.4f}" if r[5] is not None else ""))
