"""Gates, G5 per evaluation, snapshot hashes, data-manifest seed layout. Usage: python3 -I integrity2.py <run dir>"""
import hashlib, json, sys
from pathlib import Path
run = Path(sys.argv[1])
g = json.loads((run / "gates.json").read_text())
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("passed", "ok", "pass") and not isinstance(v, (dict, list)):
                yield p + "/" + k, v
            yield from walk(v, p + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
flags = list(walk(g))
print("gates.json pass/ok flags:", len(flags), "false:", [f for f in flags if f[1] is not True])
print("gates top-level keys:", list(g.keys()))
nev = g5bad = 0
snapbad = []
for c in sorted((run / "cells").iterdir()):
    t = json.loads((c / "train.json").read_text())
    for u, h in t["snapshot_sha256"].items():
        f = c / "snapshots" / f"u{int(u):07d}" / "model.pt"
        if hashlib.sha256(f.read_bytes()).hexdigest() != h:
            snapbad.append((c.name, u))
    for e in (c / "eval").glob("*/eval.json"):
        r = json.loads(e.read_text()); nev += 1
        if not r["g5"]["passed"] or r["g5"]["hash_mismatches"]:
            g5bad += 1
print("evaluations", nev, "G5 failures", g5bad, "snapshot hash mismatches", snapbad)
for dm in sorted((run / "draws").glob("*/data_manifest.json")):
    d = json.loads(dm.read_text())
    name = d["seed_set"]
    base = {"p10s0-reserve-1": 201301, "p10s0-reserve-2": 201401}.get(name) or 200001 + 100 * (int(name.split("-")[-1]) - 1)
    off = {"2048": 0, "8192": 20, "32768": 60}
    bad = []
    for fs, seeds in d["seeds"].items():
        vals = [v for k, v in seeds.items() if isinstance(v, int)] + [x for k, v in seeds.items() if isinstance(v, list) for x in v]
        lo, hi = base + off[fs], base + off[fs] + 19
        if not all(lo <= v <= hi for v in vals) or len(set(vals)) != 20:
            bad.append((fs, min(vals), max(vals), len(set(vals))))
    print(name, "base", base, "G1", d["g1_passed"], "layout ok" if not bad else bad)
