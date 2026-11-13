"""Read-only summary of retained P5 timing records (no new measurement)."""
import json, statistics
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[4] / "results/p5-2026-11-13/timing"
acc = defaultdict(list)
for f in sorted(root.glob("*/result.json")):
    d = json.loads(f.read_text())
    for r in d["timing"]["records"]:
        acc[(r["variant"], r["scope"], r["batch_size"])].append((f.parent.name, r["median_ns"], r["p10_ns"], r["p90_ns"]))
out = {"note": "Derived only from retained P5 result.json files. NOT the same measurement as operator_profile.json: different weights, queries, process and workers.",
       "source": str(root.relative_to(root.parents[2])), "workers_found": len(list(root.glob('*/result.json'))), "cells": []}
for (v, s, b), rows in sorted(acc.items()):
    out["cells"].append({"variant": v, "scope": s, "batch_size": b, "n_workers": len(rows),
        "median_across_workers_of_median_ns": statistics.median(x[1] for x in rows),
        "min_worker_median_ns": min(x[1] for x in rows), "max_worker_median_ns": max(x[1] for x in rows),
        "median_across_workers_of_p10_ns": statistics.median(x[2] for x in rows),
        "median_across_workers_of_p90_ns": statistics.median(x[3] for x in rows)})
Path(__file__).with_name("p5_retained_timing_summary.json").write_text(json.dumps(out, indent=1))
for c in out["cells"]:
    print(c["variant"], c["scope"], c["batch_size"], c["n_workers"], c["median_across_workers_of_median_ns"])
