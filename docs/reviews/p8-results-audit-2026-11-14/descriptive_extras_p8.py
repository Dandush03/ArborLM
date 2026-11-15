"""Descriptive extras (auditor, Claude Opus 5.5; not Astra validation, not human approval):
per-case training summaries (clipping, lambda range, g_R norm range, wall seconds) from train.json
and hard-trace temporal reuse (actual and null mean) from sim.json. Enters no class.
Usage: python -I descriptive_extras_p8.py TRAIN_RUN SIM_RUN"""
import json, sys
from collections import defaultdict
from pathlib import Path
T, S = Path(sys.argv[1]), Path(sys.argv[2])
acc = defaultdict(lambda: defaultdict(list))
for c in sorted((T / "cells").iterdir()):
    case = c.name[-3:]
    s = json.loads((c / "train.json").read_text())["summary"]
    acc[case]["clipped"].append(s["clipped_updates"])
    for k, v in s.get("lambda", {}).items():
        acc[case][f"lam_{k}_max"].append(v["max"]); acc[case][f"lam_{k}_zero"].append(v["zero_events"])
    for k, v in s.get("g_r_norm", {}).items():
        acc[case][f"gR_{k}_min"].append(v["min"])
    acc[case]["preclip_max"].append(s["pre_clip_gradient_norm"]["max"])
    sp = S / "cells" / c.name / "sim.json"
    if sp.is_file():
        r = json.loads(sp.read_text())
        for p in ("A", "B"):
            tr = r["panels"][p]["temporal_reuse"]
            acc[case][f"reuse_actual_{p}"].append(tr["actual"]["value"])
            acc[case][f"reuse_null_{p}"].append(sum(tr[f"null_{i}"]["value"] for i in (1, 2, 3)) / 3)
out = {c: {k: {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "n": len(v)} for k, v in d.items()} for c, d in sorted(acc.items())}
print(json.dumps(out, indent=1))
