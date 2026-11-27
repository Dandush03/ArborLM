# ruff: noqa
"""Audit 3 (R2): per LINEAGE-level counts that are saturated (distinct < 0.9 x draws) or below 14,340 (core) / 1,000 (reserve), readings A and B, with Chao1.
Usage: python3 -I a3_cap_tight.py a3_capacity.json"""
import json, sys
d = json.load(open(sys.argv[1]))
for lid, res in sorted(d["lineages"].items()):
    for lv in range(7):
        row = res[str(lv)]
        for k in "AB":
            x = row[k]
            need = 14340 if 1 <= lv <= 5 else 1000
            if x["distinct"] < 0.9 * row["draws"] or x["distinct"] < need:
                print(f"{lid} L{lv} reading {k}: distinct {x['distinct']} of {row['draws']} draws, chao1 ~{x['chao1']:.0f}, need {need}{'  BELOW' if x['distinct'] < need else ''}")
