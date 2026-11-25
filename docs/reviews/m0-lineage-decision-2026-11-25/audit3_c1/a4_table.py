# ruff: noqa
"""Audit 3 (C1), step 4: print the shortcut / formula table from a3's JSON.  python a4_table.py a3_shortcuts_gen7.json"""
import json, sys

d = json.load(open(sys.argv[1]))
print("## Generic rules per level L0..L6 (2-fold CV; open answers, chance 0)")
print("lineage | MF L0..L6 | MF|shape L0..L6 | BEST generic L0..L6 | any-literal oracle L1-L5 max | distinct keys L3")
for lid in sorted(d):
    p = d[lid]
    f = lambda k: " ".join(f"{p[str(l)][k]:.2f}" for l in range(7))
    print(f"{lid} | {f('MF_cv')} | {f('MF_shape_cv')} | {f('BEST_generic_cv')} | {max(p[str(l)]['oracle_any_literal'] for l in range(1,6)):.2f} | {p['3']['distinct_keys']}")
print()
print("## Shape-specific rules (S.* shortcut, F.* closed formula): rate inside the shape per level L0..L6 [share of level at L3]; MF inside shape at L3")
for lid in sorted(d):
    p = d[lid]
    keys = sorted({k for l in range(7) for k in p[str(l)]["S"]})
    for k in keys:
        rates = []
        for l in range(7):
            c = p[str(l)]["S"].get(k)
            rates.append(f"{c['rate_in_shape']:.2f}" if c else "  - ")
        c3 = p["3"]["S"].get(k) or next(p[str(l)]["S"][k] for l in range(7) if k in p[str(l)]["S"])
        print(f"{lid} | {k} | {' '.join(rates)} | share {c3['share_of_level']:.2f} | MFshape {c3['mf_in_shape_cv']:.2f}")
