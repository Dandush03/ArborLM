# ruff: noqa
"""Audit 4 (R1): the top heuristics per shape (by the largest of eff / anti over levels), with fired and accuracy per level.
usage: python top_heur4.py <k> <rows.jsonl ...> [--only substr]"""
import json, sys
from collections import defaultdict
k = int(sys.argv[1]); files = [a for a in sys.argv[2:] if not a.startswith("--")]
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
files = [f for f in files if f != only]
rows = defaultdict(lambda: defaultdict(dict))
for f in files:
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            if only and only not in r["lineage"]:
                continue
            rows[r["lineage"]][r["heuristic"]][r["level"]] = r
for lid in sorted(rows):
    hs = rows[lid]
    score = {h: max(max(r["eff"], r["anti"] if r["anti"] is not None else -9) for r in lv.values()) for h, lv in hs.items()}
    print(lid)
    for h in sorted(score, key=lambda h: -score[h])[:k]:
        lv = hs[h]
        print(f"   {h:42s} best {score[h]:+.3f} | " + " ".join(f"L{l}:{lv[l]['eff']:+.2f}/{(lv[l]['anti'] if lv[l]['anti'] is not None else 0):+.2f} f{lv[l]['fired']} a{lv[l]['acc_fired'] if lv[l]['acc_fired'] is not None else '-'}" for l in sorted(lv)))
