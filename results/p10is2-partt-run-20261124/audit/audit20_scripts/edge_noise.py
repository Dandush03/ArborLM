# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 20, descriptive only (enters no rule): sampling standard error of G_second(M-append) per cell, from the
1,000 item scores, ignoring the (shared) S0 and teacher terms; and the paired M-append minus M1-other-order item
differences are NOT used. Also the calibration ladder differences recomputed from the unit means.
Usage: python3 -I edge_noise.py <run_dir> <calibration_json>"""
import json
import math
import statistics
import sys

RUN, CAL = sys.argv[1], sys.argv[2]
items = json.load(open(f"{RUN}/item_records.json"))["items"]
reg = json.load(open(f"{RUN}/registry.json"))
P = {"A": "E_A", "B": "E_B"}
den = {c: reg[f"TEACHER|-|-|s:{p}"] - reg[f"S0|-|-|s:{p}"] for c, p in P.items()}
second = {"AB": "B", "BA": "A"}
for r in (0, 1, 2):
    for o in ("AB", "BA"):
        c = second[o]
        x = items[f"M-append|{o}|{r}|s:{P[c]}"]["items"]
        se = statistics.stdev(x) / math.sqrt(len(x)) / den[c]
        g = (math.fsum(x) / len(x) - reg[f"S0|-|-|s:{P[c]}"]) / den[c]
        print(f"{r}{o}: G_second={g:.4f}  SE(G)~{se:.4f}  (G-0.5)/SE={(g - 0.5) / se:+.2f}")
first = {"AB": "A", "BA": "B"}
for arm in ("M1", "M-seq"):
    for r in (0, 1, 2):
        for o in ("AB", "BA"):
            c = first[o] if arm == "M1" else second[o]
            x = items[f"{arm}|{o}|{r}|s:{P[c]}"]["items"]
            se = statistics.stdev(x) / math.sqrt(len(x)) / den[c]
            g = (math.fsum(x) / len(x) - reg[f"S0|-|-|s:{P[c]}"]) / den[c]
            print(f"{arm} {'G_first' if arm == 'M1' else 'G_second'} {r}{o}: G={g:.4f}  SE(G)~{se:.4f}  (G-0.5)/SE={(g - 0.5) / se:+.2f}")
cal = json.load(open(CAL))
u = cal["units"]
for name, key in (("lora/A", "ladder-lora-A"), ("lora/B", "ladder-lora-B"), ("store/A", "ladder-store-A"), ("store/B", "ladder-store-B")):
    m = u[key]["means"]
    diffs = {k: m[str(2 * int(k))] - m[k] for k in ("1000", "2000", "4000")}
    rec = {k: cal["ladder_differences"][k][name] for k in diffs}
    print(name, {k: round(v, 4) for k, v in diffs.items()}, "matches record:", all(abs(diffs[k] - rec[k]) < 1e-12 for k in diffs))
ok = [k for k in ("1000", "2000", "4000") if all(cal["ladder_differences"][k][n] < 0.01 for n in ("lora/A", "lora/B", "store/A", "store/B"))]
print("u values meeting the convergence rule:", ok, "-> U =", int(ok[0]) if ok else 8000, "NOT CONVERGED AT U" if not ok else "")
