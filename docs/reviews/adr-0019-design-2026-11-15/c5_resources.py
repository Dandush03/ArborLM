"""C5 (auditor, Opus 5.5) -- resource recomputation from the P9-I registered run's raw train records (attempt 2,
six workers, single-threaded) and the ledger; then the draft's ADR-0019 projection redone with those numbers.
Usage: c5_resources.py <P9-I run dir> <experiments/P9I-ledger.json>
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

run = Path(sys.argv[1])
per = defaultdict(list)
rss = []
for cell in sorted((run / "cells").iterdir()):
    t = json.loads((cell / "train.json").read_text())
    per[(t["arm"], t["slots"])].append(t["wall_seconds"] / t["run_updates"])
    rss.append(t["peak_rss_bytes"])
print("== P9-I attempt 2: seconds per update (wall, six concurrent single-thread workers), by arm and size")
for k in sorted(per, key=lambda x: (x[1], x[0])):
    v = per[k]
    print(f"  {k[0]:5s} {k[1]:6d}: n={len(v)} min {min(v):.4f} median {statistics.median(v):.4f} max {max(v):.4f}")
print(f"  peak RSS over all cells: {max(rss) / 2**30:.3f} GiB")
mem = {s: [x for (a, sz), v in per.items() if sz == s and a in ("W7", "N", "R1", "A4", "E7", "A4E", "D7") for x in v] for s in (4096, 16384, 65536)}
spu = {s: max(v) for s, v in mem.items()}
print("  max s/update over memory and dense arms (used below):", {s: round(x, 4) for s, x in spu.items()})

ledger = json.loads(Path(sys.argv[2]).read_text())
print("\n== ledger entries (stage, seconds)")
entries = ledger if isinstance(ledger, list) else ledger.get("entries", ledger)
try:
    for e in entries:
        print("  ", {k: e[k] for k in e if k in ("run", "stage", "mode", "charged_seconds", "seconds", "wall_seconds")})
except Exception as exc:  # keep going; ledger schema is not essential
    print("  could not parse ledger:", exc)

U = 8192
W = 6
print("\n== ADR-0019 draft projection recomputed (training only; no probes, no evaluation, no A4 dense phase)")
blocks = [
    ("calibration", 26, U, 4096),
    ("stage1", 128, U, 4096),
    ("stage2 (max)", 40, 4 * U, 16384),
    ("stage3", 8, U, 65536),
]
tot_sum = tot_make = 0.0
for name, cells, upd, size in blocks:
    per_cell = upd * spu[size]
    summed = cells * per_cell
    rounds = -(-cells // W)
    makespan = rounds * per_cell
    tot_sum += summed
    tot_make += makespan
    print(f"  {name:13s}: {cells:3d} cells x {upd} upd x {spu[size]:.4f} s = {per_cell:7.1f} s/cell; summed {summed / 3600:5.2f} h; "
          f"six workers: {rounds} rounds, makespan {makespan / 3600:5.2f} h")
print(f"  total summed {tot_sum / 3600:.2f} h; total makespan with six workers {tot_make / 3600:.2f} h")
reh = tot_make - blocks[0][1] * 0  # a full-size rehearsal of the full registered matrix costs the same makespan
print(f"  if the rehearsal is the full registered matrix at full U: rehearsal ~ {(tot_make - 26 * 0) / 3600 - (-(-26 // W)) * U * spu[4096] / 3600:.2f} h")
run_make = tot_make - (-(-26 // W)) * U * spu[4096]
cal_make = (-(-26 // W)) * U * spu[4096]
print(f"  registered stages makespan {run_make / 3600:.2f} h; calibration {cal_make / 3600:.2f} h")
print(f"  2x headroom on the registered stages alone needs {2 * run_make / 3600:.2f} h of caps; + calibration + a full rehearsal "
      f"= {(2 * run_make + cal_make + run_make) / 3600:.2f} h against the 4 h cap")
