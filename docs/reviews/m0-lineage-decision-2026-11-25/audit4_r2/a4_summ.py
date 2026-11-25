# ruff: noqa
"""Audit 4 (R2): summarise a4_shortcuts JSON. Usage: python3 -I a4_summ.py IN.json [threshold_to_list] [--app]
Per lineage: per level the largest non-(P) effect over shapes and rules (per-shape max), the rule and shape; the lineage-level combined effect
(sum over shapes of share x best non-(P) effect in that shape); (P) rules listed separately; rules with exceptions listed.
--app: use accuracy among applicable items for open answers too (default: a rule's None counts as wrong)."""
import json
import sys

d = json.load(open(sys.argv[1]))
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
APP = "--app" in sys.argv


def eff(v, at):
    if at == "yn":
        return v["effect"]
    return v["acc_app"] if APP else v["acc_all"]


rows = []
for lid, lv_rows in sorted(d["lineages"].items()):
    per_level = []
    comb = []
    plist = {}
    errs = {}
    for lv in sorted(lv_rows, key=int):
        best = (0.0, "-", "-")
        c = 0.0
        for sh, ent in lv_rows[lv].items():
            at = ent["answer_type"]
            bsh = 0.0
            for hn, v in ent["rules"].items():
                if v["nerr"]:
                    errs[hn] = errs.get(hn, 0) + v["nerr"]
                e = eff(v, at)
                if v["P"]:
                    plist.setdefault(hn, []).append((int(lv), sh, round(e, 2)))
                    continue
                if e > best[0]:
                    best = (e, hn, sh)
                bsh = max(bsh, e)
            c += ent["share"] * bsh
        per_level.append(best)
        comb.append(c)
    mx = max(b[0] for b in per_level)
    rows.append((lid, mx, per_level, comb, plist, errs))

bins = {"<=0.10": 0, "0.10-0.15": 0, "0.15-0.25": 0, ">0.25": 0}
for lid, mx, per_level, comb, plist, errs in rows:
    k = "<=0.10" if mx <= 0.10 else "0.10-0.15" if mx <= 0.15 else "0.15-0.25" if mx <= 0.25 else ">0.25"
    bins[k] += 1
    print(f"{lid}: max per-shape effect {mx:.3f}  [{k}]   per level: " + " ".join(f"{b[0]:.2f}" for b in per_level) + "   combined: " + " ".join(f"{c:.2f}" for c in comb))
    if mx > thr:
        seen = set()
        for lv, b in enumerate(per_level):
            if b[0] > thr and (b[1], b[2]) not in seen:
                seen.add((b[1], b[2]))
                print(f"     L{lv} top: {b[1]} on shape {b[2]}")
        # every rule above thr at any level
        allr = {}
        for lv in d["lineages"][lid]:
            for sh, ent in d["lineages"][lid][lv].items():
                for hn, v in ent["rules"].items():
                    e = eff(v, ent["answer_type"])
                    if not v["P"] and e > thr:
                        allr.setdefault((hn, sh), {})[int(lv)] = e
        for (hn, sh), m in sorted(allr.items(), key=lambda x: -max(x[1].values())):
            print(f"       {hn} [{sh}]: " + " ".join(f"L{k}={m[k]:.2f}" for k in sorted(m)))
    for hn, l in plist.items():
        mxp = max(x[2] for x in l)
        if mxp > thr:
            print(f"     (P) {hn}: max {mxp:.2f}")
    for hn, n in errs.items():
        print(f"     rule raised on {n} items: {hn}")
print("distribution of max per-shape effect (non-(P) rules, mode included):", bins)
