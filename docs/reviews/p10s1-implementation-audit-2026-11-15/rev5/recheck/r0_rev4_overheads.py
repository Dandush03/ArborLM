"""Recheck script r0 (Claude Opus 5.5 auditor; P10-S1 rev-5 fix recheck; not Astra review).
Per-task non-training wall time in revision 4's calibration (read only): task seconds (pool manifest) minus the
run's training wall_seconds (train.json), against its number of evaluated snapshots. Fit overhead = a + b * snapshots
by least squares (my own code). a ~ start-up per task, b ~ evaluation seconds per snapshot (six workers, revision 4 sizes).
  python3 -I r0_rev4_overheads.py <rev-4 run dir>
"""
import json, sys
from pathlib import Path
D = Path(sys.argv[1])
m = json.loads((D / "calibrate" / "manifest.json").read_text())
rows = []
for t in m["tasks"]:
    tr = D / "cells" / t["label"] / "train.json"
    if t["status"] != "completed" or not tr.is_file():
        continue
    w = json.loads(tr.read_text())
    n = len(list((D / "cells" / t["label"] / "eval").glob("u*")))
    rows.append((t["label"], w["arm"], w["slots"], n, t["seconds"] - w["wall_seconds"], w["wall_seconds"]))
n = len(rows)
xs = [r[3] for r in rows]; ys = [r[4] for r in rows]
mx, my = sum(xs) / n, sum(ys) / n
b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(1e-12, sum((x - mx) ** 2 for x in xs))
a = my - b * mx
print(f"tasks {n}; overhead min {min(ys):.1f} s, median {sorted(ys)[n//2]:.1f} s, max {max(ys):.1f} s; snapshots min {min(xs)} max {max(xs)}")
print(f"fit: overhead = {a:.2f} s + {b:.2f} s * snapshots")
by = {}
for r in rows:
    by.setdefault((r[1], r[2]), []).append(r[4] / max(1, r[3]))
for k, v in sorted(by.items()):
    print(f"  {k}: overhead per snapshot median {sorted(v)[len(v)//2]:.2f} s over {len(v)} tasks")
