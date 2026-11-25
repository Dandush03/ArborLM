# ruff: noqa
"""Audit 4 (C1), step 5b: tables from s5_v2.json: (1) every F.* closed form, in-shape rate per level; (2) every S/M rule or MF-in-shape
above 0.25 inside its shape at any level (rate range over levels, share of level); (3) per-lineage maxima. Usage: python3 s5b_tables.py s5_v2.json"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
print("== (1) closed forms F.* (in-shape rate L0..L6; share of level in brackets at max)")
for lid, per in d.items():
    rows = defaultdict(dict)
    for lv in map(str, range(7)):
        for k, v in per[lv]["rules"].items():
            if "|F." in k:
                rows[k][lv] = (v["rate_in_shape"], v.get("share_of_level"))
    for k, r in sorted(rows.items()):
        print(f"{lid:28s} {k:45s} " + " ".join(f"{r.get(str(l), ('-',))[0]}" for l in range(7)) + f"  max share {max(x[1] for x in r.values()):.3f}")
print("\n== (2) S/M/MF in-shape > 0.25 (levels where > 0.25: rate)")
for lid, per in d.items():
    rows = defaultdict(dict)
    for lv in map(str, range(7)):
        for k, v in per[lv]["rules"].items():
            if ("|S." in k or "|M." in k or "MF_in_shape" in k) and v["rate_in_shape"] > 0.25 and v["n_shape"] >= 20:
                rows[k][lv] = (v["rate_in_shape"], v.get("share_of_level"), v["n_shape"])
    for k, r in sorted(rows.items()):
        print(f"{lid:28s} {k:45s} " + " ".join(f"L{l}:{x[0]:.2f}(n{x[2]})" for l, x in sorted(r.items())))
