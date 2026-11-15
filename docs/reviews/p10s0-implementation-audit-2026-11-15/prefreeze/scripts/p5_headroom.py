# Headroom rule (ADR-0020 10.4 reading A + rulings M6/N4): charged + 2*(remaining projected stages + reserve) <= cap.
# Inputs: ledger now; my recomputed projection (p3 output); generation and gates measurements from the records. Reserve = (cap_analysis+cap_report)/2 = 60 s if A,R <= 30 s.
import json, sys, math
from pathlib import Path
E = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
P = json.loads(Path(sys.argv[1]).read_text())["with_overhead_max"]
led = json.loads((E / "P10S0-ledger.json").read_text())
C0 = sum(e["seconds"] for e in led["entries"])
gen_meas = 33.44888391700806; gen_cap = max(60, 2 * gen_meas)
G_task, G_ledger, G_json, Pd = 39.755301958008204, 39.76153733301908, 38.72354562499095, 3.1943115839967504
gates_meas = G_task + 12 * Pd
gates_i1 = (G_task - Pd) + 13 * Pd * 1.6
RES = (60 + 60) / 2
Q1, Q1c = P["q1:full"]["total_s"], P["q1:cut3"]["total_s"]
WX = {c: P[f"wx:{c}"]["total_s"] for c in ("A5-D", "A1")}; PR = {c: P[f"probe:{c}"]["total_s"] for c in ("A5-D", "A1")}
out = {"C0_charged_now_s": C0, "gen_15_at_measured_s": 15 * gen_meas, "gen_15_at_cap_s": 15 * gen_cap, "gates_measured_G_plus_12P_s": gates_meas, "gates_with_I1_ratio_s": gates_i1, "reserve_s": RES,
       "Q1_full_h": Q1 / 3600, "Q1_cut3_h": Q1c / 3600, "WX_h": {k: v / 3600 for k, v in WX.items()}, "PR_h": {k: v / 3600 for k, v in PR.items()}}
def h(x): return round(x / 3600, 4)
scen = {"nominal (gen and gates at measured)": C0 + 15 * gen_meas + gates_meas, "gen at measured, gates with I1 x1.6 per draw": C0 + 15 * gen_meas + gates_i1, "gen at its cap (66.9 s x 15), gates at its cap": C0 + 15 * gen_cap + 2 * gates_meas}
tab = {}
for sname, Cq in scen.items():
    row = {"charged_at_Q1_start_h": h(Cq)}
    for cap_h in (16, 21, 22):
        cap = cap_h * 3600
        pre_full = Cq + 2 * (Q1 + RES); pre_cut = Cq + 2 * (Q1c + RES)
        d = {"pre_full_need_h": h(pre_full), "pre_decision": "full" if pre_full <= cap else ("cut3" if pre_cut <= cap else "stop"), "pre_cut3_need_h": h(pre_cut)}
        q1_used = Q1 if d["pre_decision"] == "full" else Q1c
        for s in (1.0, 1.1, 1.25, 1.5):
            Cpost = Cq + s * q1_used
            for c in ("A5-D", "A1"):
                both = Cpost + 2 * (WX[c] + PR[c] + RES); wxo = Cpost + 2 * (WX[c] + RES)
                d[f"post s={s} {c}"] = {"need_both_h": h(both), "margin_both_s": round(cap - both, 1), "decision": "WX+probe" if both <= cap else ("WX only (cut 1)" if wxo <= cap else "neither (cuts 1,2)")}
        for c in ("A5-D", "A1"):
            d[f"max Q1 slowdown keeping WX+probe {c}"] = round((cap - Cq - 2 * (WX[c] + PR[c] + RES)) / q1_used, 4)
            d[f"max Q1 slowdown keeping WX {c}"] = round((cap - Cq - 2 * (WX[c] + RES)) / q1_used, 4)
        row[f"cap {cap_h} h"] = d
    for c in ("A5-D", "A1"):
        row[f"smallest cap (h, real) for WX+probe {c} after Q1 full at projection"] = h(Cq + Q1 + 2 * (WX[c] + PR[c] + RES))
    row["smallest cap (h, real) for Q1 full before Q1"] = h(Cq + 2 * (Q1 + RES))
    tab[sname] = row
out["scenarios"] = tab
json.dump(out, sys.stdout, indent=1)
