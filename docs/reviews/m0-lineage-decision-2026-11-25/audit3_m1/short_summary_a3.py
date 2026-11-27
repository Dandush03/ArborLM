# ruff: noqa
"""Audit 3 of M1: summarise short_n1000.json. For each lineage: per level the rule with the largest (rate - held-out base), its rate, base and 95% half-width;
and every rule that ever exceeds base by >= 0.05 (display only, not a threshold) with its per-level differences."""
import json
import sys

d = json.load(open(sys.argv[1]))
for lid in sorted(d):
    lv = d[lid]
    rows = []
    for L in sorted(lv, key=int):
        r = lv[L]
        cand = {k: v for k, v in r["minus_base"].items()}
        k = max(cand, key=cand.get)
        rows.append(f"L{L}:{k.split('[')[0]} {r['rates'][k]:.3f}-{r['base_heldout_mode']:.3f}={cand[k]:+.3f}(+-{r['halfwidth95'][k]:.3f})")
    print(lid)
    print("   best:", " | ".join(rows))
    names = sorted({k for L in lv for k in lv[L]["minus_base"]})
    for k in names:
        diffs = [lv[L]["minus_base"].get(k) for L in sorted(lv, key=int)]
        if any(x is not None and abs(x) >= 0.05 for x in diffs):
            print(f"   {k}: " + " ".join("  -  " if x is None else f"{x:+.3f}" for x in diffs))
    print("   base:", " ".join(f"{lv[L]['base_heldout_mode']:.3f}" for L in sorted(lv, key=int)), " echoed-anywhere:", " ".join(f"{lv[L]['answer_echoed_anywhere']:.2f}" for L in sorted(lv, key=int)))
