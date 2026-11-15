"""Re-check (auditor): stream key sets of the 55 registered P8 sim.json, by kind, and the kinds of the
five supplement cells read from their eval.json only (no simulation). Stdlib only."""
import collections
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sim_run = root / "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
eval_run = root / "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
five = [f"b10{b}-o30{b}-s60{s}-{c}" for b in (1, 2, 3) for s in (1, 2) for c in ("C04", "C05")]
seen = collections.Counter()
n = 0
for cell in sorted((sim_run / "cells").iterdir()):
    p = cell / "sim.json"
    if not p.is_file():
        print("NO sim.json:", cell.name)
        continue
    rec = json.loads(p.read_text())
    n += 1
    for panel, pr in rec["panels"].items():
        st = pr["streams"]
        kind = pr.get("kind") or rec.get("kind") or rec.get("variant")
        sig = (
            str(kind),
            tuple(sorted(st)),
            tuple(sorted(st["order_shuffled"])),
            tuple(tuple(sorted(st[s])) for s in ("null_1", "null_2", "null_3")),
            tuple(sorted(st["actual"])),
            tuple(sorted(pr["temporal_reuse"])),
        )
        seen[sig] += 1
print("registered sim.json read:", n)
for sig, c in seen.items():
    print(c, "panels:", json.dumps(sig))
print("--- eval kinds of failed (no sim.json) cells")
for cell in sorted((eval_run / "cells").iterdir()):
    if not (sim_run / "cells" / cell.name / "sim.json").is_file():
        ev = json.loads((cell / "eval.json").read_text())
        ks = {k: ev[k] for k in ev if k in ("kind", "variant", "case")}
        print(cell.name, ks)
