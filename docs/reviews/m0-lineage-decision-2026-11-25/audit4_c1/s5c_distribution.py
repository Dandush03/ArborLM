# ruff: noqa
"""Audit 4 (C1), step 5c: distribution of the per-lineage maximum (over levels L0-L6, and over core levels L1-L5) of the level-wide
battery effect, EFF_S (cheap) and EFF_SM (cheap + partial-trace mutations); closed forms (F) reported separately. Usage: python3 s5c_distribution.py s5_v2.json"""
import json, sys
d = json.load(open(sys.argv[1]))
for key in ("EFF_S", "EFF_SM", "EFF_F"):
    for lvls, lab in ((range(7), "L0-L6"), (range(1, 6), "L1-L5")):
        mx = {lid: max(per[str(l)][key] for l in lvls) for lid, per in d.items()}
        b = {"<=0.10": [], "(0.10,0.15]": [], "(0.15,0.25]": [], ">0.25": []}
        for lid, v in sorted(mx.items(), key=lambda kv: kv[1]):
            k = "<=0.10" if v <= 0.10 else ("(0.10,0.15]" if v <= 0.15 else ("(0.15,0.25]" if v <= 0.25 else ">0.25"))
            b[k].append(f"{lid.replace('C1.', '')} {v:.3f}")
        print(f"== {key} {lab}: " + "; ".join(f"{k} {len(v)}" for k, v in b.items()))
        for k, v in b.items():
            if k != "<=0.10":
                print("   ", k, ", ".join(v))
