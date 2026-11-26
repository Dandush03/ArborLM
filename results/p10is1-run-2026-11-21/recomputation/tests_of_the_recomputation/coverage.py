# ruff: noqa
"""Which verdicts, classes, labels and MC statuses the comparison runs exercised. Usage: python3 coverage.py <recompute outputs...>"""
import json, sys
from collections import Counter
C = {k: Counter() for k in ("cap_verdict", "cap_step_class", "cap_arm_class", "dense_cell", "dense_sat", "dense_arm", "cap_outcome", "mc_status", "mc_c_mode", "sat_verdict", "sat_pair_class", "sat_arm_class", "sat_outcome", "eff_verdict", "eff_step_class", "eff_arm_class", "dense_speed", "eff_outcome", "sparse", "u_t_kind")}
for f in sys.argv[1:]:
    m = json.load(open(f))
    c = m["capacity"]; C["cap_outcome"][c["outcome"]] += 1
    for arm, a in c["arms"].items():
        C["cap_arm_class"][a["class"]] += 1; C["dense_arm"][a["dense_arm"]] += 1
        for st, s in a["steps_detail"].items():
            C["cap_step_class"][s["class"]] += 1
            for r in s["replicates"]:
                for v in r["panels"].values(): C["cap_verdict"][v] += 1
                for k, v in r["mc"].items(): C["mc_status"][f"{k}:{v[2]}"] += 1
        for v in a["dense_cells"].values():
            C["dense_cell"][v["label"]] += 1
            for r in v["replicates"]:
                for k, st in r["status"].items(): C["mc_status"][f"dense {k}:{st}"] += 1
        for v in a["dense_at_saturation"].values(): C["dense_sat"][v["label"]] += 1
    s = m["saturation"]; C["sat_outcome"][s["outcome"]] += 1
    for a in s["arms"].values():
        C["sat_arm_class"][a["class"]] += 1
        for p in a["pairs"].values():
            C["sat_pair_class"][p["class"]] += 1
            for v in p["verdicts"]: C["sat_verdict"][v] += 1
    e = m["efficiency"]; C["eff_outcome"][e["outcome"]] += 1
    for r in e["readings"].values():
        for a in r.values():
            C["eff_arm_class"][a["class"]] += 1
            for v in a["dense_speed"].values(): C["dense_speed"][v] += 1
            for st in a["steps"].values():
                C["eff_step_class"][st["class"]] += 1
                for rr in st["replicates"]:
                    C["eff_verdict"][rr["verdict"]] += 1; C["u_t_kind"][rr["u_t_small"][0]] += 1; C["u_t_kind"][rr["u_t_large"][0]] += 1
    for t in m["sparse"].values(): C["sparse"][t["label"]] += 1
for k, v in C.items():
    print(f"{k}: {dict(v)}")
