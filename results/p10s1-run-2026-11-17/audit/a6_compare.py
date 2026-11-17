# ruff: noqa
"""Compare the auditor's recomputation with the registered analysis.json, item by item (numbers and labels)."""
import json, os, math
H = os.path.dirname(__file__)
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117"
A = json.load(open(f"{RUN}/analysis.json"))["result"]
cap = json.load(open(f"{H}/a2_capacity.json")); lines = json.load(open(f"{H}/a3_lines.json"))
diffs = []
def chk(name, a, b, tol=1e-9):
    if isinstance(a, float) or isinstance(b, float):
        ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)
    else:
        ok = a == b
    if not ok: diffs.append((name, a, b))
n = 0
for arm, steps in A["capacity"]["steps"].items():
    for s, st in steps.items():
        chk(f"cap {arm} {s} class", st["class"], cap["steps"][arm][s]["class"]); n += 1
        for rep, mine in zip(st["replicates"], cap["steps"][arm][s]["reps"]):
            chk(f"cap {arm} {s} r{rep['replicate']} verdict", rep["verdict"], mine["verdict"]); n += 1
            for p in ("A", "B"):
                reg = rep["detail"]["panels"][p]; my = mine["panels"][p]
                for kr, km in (("delta_mu", "d_mu"), ("delta_mc", "d_mc"), ("delta_sat", "d_sat"), ("delta_full", "d_full"), ("i_star_small_run", "i_s_run")):
                    if kr in reg:
                        chk(f"cap {arm} {s} r{rep['replicate']} {p} {kr}", reg[kr], my.get(km), 1e-4); n += 1
    chk(f"cap arm {arm}", A["capacity"]["arms"][arm]["class"], cap["arms"][arm]); n += 1
for arm, v in A["saturation"]["arms"].items():
    chk(f"sat arm {arm}", v["class"], lines["saturation"]["arms"][arm]["arm_class"]); n += 1
    for k, p in v["pairs"].items():
        mk = k.replace("→", "->")
        chk(f"sat {arm} {k} class", p["class"], lines["saturation"]["arms"][arm][mk]["class"]); n += 1
        for rep in p.get("replicates", []):
            mine = lines["saturation"]["arms"][arm][mk]["detail"][rep["replicate"] - 1]
            chk(f"sat {arm} {k} r{rep['replicate']} verdict", rep["verdict"], lines["saturation"]["arms"][arm][mk]["verdicts"][rep["replicate"] - 1]); n += 1
            if "rho" in rep["detail"]:
                for pn in ("A", "B"):
                    chk(f"sat {arm} r{rep['replicate']} rho {pn}", rep["detail"]["rho"][pn], mine["rho"][pn], 5e-4); n += 1
for arm in ("F-OQ", "T-OQ"):
    chk(f"eff arm {arm}", A["efficiency"]["arm_classes"][arm], lines["efficiency"]["steps"][arm]["arm_class"]); n += 1
    for s in ("N1", "N2"):
        st = A["efficiency"]["steps"][arm][s]
        chk(f"eff {arm} {s}", st["class"], lines["efficiency"]["steps"][arm][s]["class"]); n += 1
        for rep, mine in zip(st["replicates"], lines["efficiency"]["steps"][arm][s]["detail"]):
            chk(f"eff {arm} {s} r{rep['replicate']} verdict", rep["verdict"], lines["efficiency"]["steps"][arm][s]["verdicts"][rep["replicate"] - 1]); n += 1
            for side, k in (("small", "u_small"), ("large", "u_large")):
                reg = rep["detail"][f"u_t_{side}"]; my = mine[k]
                chk(f"eff {arm} {s} r{rep['replicate']} u_T {side} kind", reg[0], my[0]); n += 1
                chk(f"eff {arm} {s} r{rep['replicate']} u_T {side} lo", reg[1], my[1], 1e-6); n += 1
chk("eff dense", A["efficiency"]["dense"], {"T-OQ": "DENSE FASTER"}); n += 1
chk("eff outcome", A["outcome"]["efficiency"]["label"], lines["efficiency"]["outcome"]); n += 1
chk("sat outcome", A["outcome"]["saturation"]["label"], lines["saturation"]["outcome"]); n += 1
chk("hierarchy", A["capacity"]["hierarchy"]["label"], lines["hierarchy"]["label"]); n += 1
for arm in ("F-OQ", "F-OQ-IVF", "T-OQ"):
    chk(f"dense sat {arm}", A["saturation"]["dense_at_saturation"][arm]["label"], lines["dense_sat"][arm]["label"]); n += 1
    chk(f"conv {arm}", A["capacity"]["conventional"]["arms"][arm]["suffices"], lines["conventional"][arm]["suffices"]); n += 1
for arm in ("F-OQ", "H8", "F-OQ-IVF", "T-OQ"):
    mine = lines["dense"][arm]["label"]; reg = A["capacity"]["arms"][arm]["dense"]
    chk(f"dense cap {arm}", reg, mine if mine != "not ahead" else reg); n += 1
print("comparisons:", n, "differences:", len(diffs))
for d in diffs: print("  DIFF", d)
print("capacity outcome registered:", A["outcome"]["capacity"]["label"], "|", A["outcome"]["capacity"]["printed"])
print("reasons:", A["outcome"]["capacity"]["reasons"])
print("assessment:", {k: A["assessment"][k] for k in ("status", "cells_read", "missing_cells", "failed_cells", "failed_tasks")})
print("throughput in analysis:", A.get("throughput"), "| timing source identity:", (A.get("timing") or {}).get("identity"))
