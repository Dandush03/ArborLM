"""Registered per-update rates against the rehearsal's alone and busy rates; other studies' ledger entries overlapping the run.
Usage: python3 -I timing.py <run dir> <projection.json> <experiments dir>"""
import json, sys, statistics, collections, glob
from pathlib import Path
run, proj, exp = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
ra, rb = proj["rates_alone"], proj["rates_busy"]
grp = collections.defaultdict(list)
for c in sorted((run / "cells").iterdir()):
    t = json.loads((c / "train.json").read_text())
    blk, arm, ct = t["block"], t["arm"], t["celltype"].replace("/", "")
    reh = f"REH-{arm}-{ct}-main" if arm != "A2" else f"REH-A2-{ct}-post"
    grp[reh].append(t["wall_seconds"] / t["run_updates"])
print(f"{'rehearsal item':26s} {'n':>3s} {'run s/upd':>10s} {'alone':>8s} {'busy':>8s} {'run/busy':>8s} {'run/alone':>9s}")
for k, v in sorted(grp.items()):
    a = ra.get(k, {}).get("seconds_per_update"); b = rb.get(k, {}).get("seconds_per_update")
    m = statistics.median(v)
    print(f"{k:26s} {len(v):3d} {m:10.5f} {a or float('nan'):8.5f} {b or float('nan'):8.5f} {m/b if b else float('nan'):8.3f} {m/a if a else float('nan'):9.3f}")
t0, t1 = "2026-11-15T22:28:00", "2026-11-16T04:31:00"
for lp in sorted(exp.glob("*ledger*.json")):
    if "P10S0" in lp.name: continue
    try: L = json.loads(lp.read_text())
    except Exception: continue
    ov = [e for e in L.get("entries", []) if t0 <= e.get("utc", "")[:19] <= t1]
    if ov:
        print(lp.name, len(ov), "entries ending inside the run window:", [(e["stage"], round(e["seconds"]), e["utc"][:19]) for e in ov][:12])
