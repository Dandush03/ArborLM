# ruff: noqa
"""Tasks 2b-2d and 4: efficiency line (8.8), saturation line (8.10), dense labels (8.5), hierarchy and conventional retrieval (8.5), raw a_use table.
Written from the ADR text; no import of studies.* or arborlm.*."""
import collections, json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import PANELS, STEPS, U_P_ROW, U_L, REF_CELL, View, bits, load_cells, load_plan, mc_entry, P, RUN

plan = load_plan()
cost = plan["frozen"]["cost"]
cells = load_cells()
res = {}
R5 = range(1, 6)


def V(arm, f, n, r, p):
    return View(P(cells, arm, f, n, r), p, memory=(arm != "D-OQ"))


def ref_ok(r, facts):
    f, n = REF_CELL[facts]
    return all(V("R2", f, n, r, p).a_use(U_P_ROW[facts]) >= 0.95 for p in PANELS)


def leak(arm, f, n, r):
    return any(V(arm, f, n, r, p).leakage() for p in PANELS)


print("REF per replicate and row:", {(r, f): ref_ok(r, f) for r in R5 for f in (2048, 8192, 32768)})
print("LEAKAGE anywhere:", [(k, c["label"]) for k, c in cells.items() if k[0] == "P" and any(View(c, p, memory=(k[1] != "D-OQ")).leakage() for p in PANELS)])

# ============================================================== efficiency line (8.8)
IT = 3.0

def u_t(views):
    """min-of-panels interpolation; qualifies if i>=3 on all given panels and DEP passes on them."""
    ups = sorted(set.intersection(*[set(v.ups) for v in views]))
    run = views[0].run
    for k, s in enumerate(ups):
        if all(v.i(s) >= IT for v in views):
            deps = [v.dep(s) for v in views]
            if any(d is not None and not d[0] for d in deps):
                return ("DEPFAIL", run, math.inf, s)
            if k == 0:
                return ("left", 0.0, float(s), s)
            pv = ups[k - 1]
            mp, mh = min(v.i(pv) for v in views), min(v.i(s) for v in views)
            frac = (IT - mp) / (mh - mp)
            x = math.log2(pv) + frac * (math.log2(s) - math.log2(pv))
            return ("exact", 2 ** x, 2 ** x, s)
    return ("right", float(run), math.inf, None)


def eff_verdict(arm, s, r):
    f, ns, nl, _ = STEPS[s]
    if not ref_ok(r, f) or leak(arm, f, ns, r) or leak(arm, f, nl, r):
        return "NOT_EVALUATED", {}
    ys = u_t([V(arm, f, ns, r, p) for p in PANELS])
    xs = u_t([V(arm, f, nl, r, p) for p in PANELS])
    d = {"u_small": ys, "u_large": xs}
    if ys[0] == "DEPFAIL" or xs[0] == "DEPFAIL":
        return "DEPENDENCE_FAILED", d
    cs, cl = cost[arm][str(ns)], cost[arm][str(nl)]
    run_s, run_l = V(arm, f, ns, r, "A").run, V(arm, f, nl, r, "A").run
    ylo, yhi, xlo, xhi = ys[1], ys[2], xs[1], xs[2]
    row4 = ys[0] == "right" and xhi <= run_s / 2 and all(xhi * cl[m] <= 0.8 * run_s * cs[m] for m in ("cpu", "madds"))
    row5 = xhi <= ylo / 2 and all(xhi * cl[m] <= 0.8 * ylo * cs[m] for m in ("cpu", "madds"))
    row6 = xhi <= ylo / 2
    row7 = xlo >= 2 * yhi and math.isfinite(yhi) and (xs[0] != "right" or run_l >= 2 * yhi)
    cens = ys[0] != "exact" or xs[0] != "exact"
    d.update(row4=row4, row5=row5, row6=row6, row7=row7, ratio_updates=(xhi / ylo if ylo > 0 else None),
             cost_ratio={m: (xhi * cl[m]) / (ylo * cs[m]) if ylo > 0 and math.isfinite(xhi) else None for m in ("cpu", "madds")})
    if (ys[0] == "right" and xs[0] == "right") or (cens and not (row4 or row5 or row6 or row7)):
        return "NOT_ASSESSED", d
    if row4: return "REACHED ONLY BY THE LARGER", d
    if row5: return "FASTER", d
    if row6: return "FASTER IN UPDATES ONLY", d
    if row7: return "SLOWER", d
    return "SAME", d


def eff_step_class(v):
    c = collections.Counter(v)
    if c["NOT_EVALUATED"] >= 2: return "NOT_EVALUATED"
    if c["DEPENDENCE_FAILED"] >= 2: return "DEPENDENCE_FAILED"
    if c["NOT_ASSESSED"] >= 2: return "NOT_ASSESSED"
    if c["FASTER"] + c["REACHED ONLY BY THE LARGER"] == 5: return "FASTER STEP"
    if c["FASTER"] + c["FASTER IN UPDATES ONLY"] == 5: return "UPDATES-ONLY STEP"
    if c["SLOWER"] >= 4: return "SLOWER STEP"
    if c["SAME"] >= 4: return "NO DIFFERENCE"
    return "MIXED"


eff = {}
for arm in ("F-OQ", "T-OQ"):
    eff[arm] = {}
    for s in ("N1", "N2"):
        vs = [eff_verdict(arm, s, r) for r in R5]
        eff[arm][s] = {"class": eff_step_class([v[0] for v in vs]), "verdicts": [v[0] for v in vs], "detail": [v[1] for v in vs]}
    cl = {s: eff[arm][s]["class"] for s in ("N1", "N2")}
    # arm class, transitions: N1 in 1K->4K, N2 in 4K->16K
    if any(c in ("NOT_EVALUATED", "NOT_ASSESSED") for c in cl.values()):
        ac = "NOT_EVALUATED"
    elif any(c == "DEPENDENCE_FAILED" for c in cl.values()):
        ac = "DEPENDENCE_FAILED"
    elif all(c == "FASTER STEP" for c in cl.values()):
        ac = "EFFICIENCY_SUPPORTED"
    elif any(c == "FASTER STEP" for c in cl.values()):
        ac = "EFFICIENCY_ONE_TRANSITION"
    elif all(c in ("SLOWER STEP", "NO DIFFERENCE") for c in cl.values()):
        ac = "EFFICIENCY_NOT_SUPPORTED"
    else:
        ac = "INTERMEDIATE"
    eff[arm]["arm_class"] = ac

# DENSE FASTER at the larger cell of each FASTER STEP: two readings (per-panel u_T with "either panel"; both-panel min u_T)
def dense_faster(arm, s, per_panel):
    f, ns, nl, _ = STEPS[s]
    ca, cd = cost[arm][str(nl)], cost["D-OQ"][str(nl)]
    cnt, detail = 0, []
    for r in R5:
        if per_panel:
            pairs = [(u_t([V(arm, f, nl, r, p)]), u_t([V("D-OQ", f, nl, r, p)])) for p in PANELS]
        else:
            pairs = [(u_t([V(arm, f, nl, r, p) for p in PANELS]), u_t([V("D-OQ", f, nl, r, p) for p in PANELS]))]
        ok = any(all(d[2] * cd[m] <= 0.8 * a[1] * ca[m] for m in ("cpu", "madds")) for a, d in pairs)
        cnt += ok
        detail.append([(a[0], round(a[1]), d[0], round(d[2]) if math.isfinite(d[2]) else d[2], {m: round(d[2] * cd[m] / (a[1] * ca[m]), 3) if a[1] > 0 and math.isfinite(d[2]) else None for m in ("cpu", "madds")}) for a, d in pairs])
    return ("DENSE FASTER" if cnt >= 4 else "not DENSE FASTER (sure)"), cnt, detail

for arm in ("F-OQ", "T-OQ"):
    eff[arm]["dense"] = {}
    for s in ("N1", "N2"):
        if eff[arm][s]["class"] == "FASTER STEP":
            eff[arm]["dense"][s] = {"per_panel_either": dense_faster(arm, s, True), "min_of_panels": dense_faster(arm, s, False)}
sup = [a for a in ("F-OQ", "T-OQ") if eff[a]["arm_class"] == "EFFICIENCY_SUPPORTED"]
dfast = {a: any(v["per_panel_either"][0] == "DENSE FASTER" for v in eff[a]["dense"].values()) for a in sup}
if any(not dfast[a] for a in sup):
    eo = "EFFICIENCY-POSITIVE"
elif all(eff[a]["arm_class"] == "EFFICIENCY_NOT_SUPPORTED" for a in ("F-OQ", "T-OQ")) or (sup and all(dfast.values())):
    eo = "EFFICIENCY-NEGATIVE"
else:
    eo = "EFFICIENCY-INCONCLUSIVE"
res["efficiency"] = {"steps": eff, "outcome": eo}

print("\n=== EFFICIENCY")
for arm in ("F-OQ", "T-OQ"):
    print(arm, eff[arm]["arm_class"], {s: (eff[arm][s]["class"], eff[arm][s]["verdicts"]) for s in ("N1", "N2")})
    for s in ("N1", "N2"):
        for r, d in zip(R5, eff[arm][s]["detail"]):
            us, ul = d["u_small"], d["u_large"]
            print(f"   {s} r{r}: u_T small {us[0]} {us[1]:.0f}..{us[2]} (hit {us[3]}), large {ul[0]} {ul[1]:.0f}..{ul[2]} (hit {ul[3]}); ratio u(4N)/u(N)={d.get('ratio_updates') and round(d['ratio_updates'],3)} cost ratios={ {m: (round(x,3) if x else x) for m,x in d.get('cost_ratio',{}).items()} }")
    for s, v in eff[arm]["dense"].items():
        print(f"   DENSE at {s}: per-panel/either: {v['per_panel_either'][0]} ({v['per_panel_either'][1]}/5); min-of-panels: {v['min_of_panels'][0]} ({v['min_of_panels'][1]}/5)")
        for r, det in zip(R5, v["per_panel_either"][2]):
            print(f"       r{r} (arm kind, arm u_T lo, D-OQ kind, D-OQ u_T hi, c_T(D)/c_T(arm)) per panel: {det}")
print("EFFICIENCY OUTCOME:", eo)

# ============================================================== saturation line (8.10)
sat = {}
SATP = {"F-OQ": [((2048, 256), (8192, 1024)), ((8192, 1024), (32768, 4096))], "F-OQ-IVF": [((8192, 1024), (32768, 4096))], "T-OQ": [((8192, 1024), (32768, 4096))], "H8": [((8192, 1024), (32768, 4096))]}
print("\n=== SATURATION")
for arm, pairs in SATP.items():
    pcl = []
    sat[arm] = {}
    for (fs, ns), (fl, nl) in pairs:
        key = f"{ns}->{nl}"
        if ns == 256:
            sat[arm][key] = {"class": "NOT FULL", "note": "2K/256 not run (sat256 false): fixed NOT FULL (section 10.1 item 0b)"}
            pcl.append("NOT FULL"); continue
        verdicts, det = [], []
        for r in R5:
            vs = {p: V(arm, fs, ns, r, p) for p in PANELS}; vl = {p: V(arm, fl, nl, r, p) for p in PANELS}
            if not (ref_ok(r, fs) and ref_ok(r, fl)) or leak(arm, fs, ns, r) or leak(arm, fl, nl, r):
                verdicts.append("NOT_EVALUATED"); det.append({}); continue
            depf = [(p, x.dep_failures()) for p, x in list(vs.items()) + list(vl.items()) if x.dep_failures()]
            full = {("S", p): vs[p].loaded() for p in PANELS} | {("L", p): vl[p].loaded() for p in PANELS}
            S = {p: fs * vs[p].i_star(vs[p].run) for p in PANELS}; Lb = {p: fl * vl[p].i_star(vl[p].run) for p in PANELS}
            rho = {p: Lb[p] / S[p] for p in PANELS}
            dd = {"rho": {p: round(rho[p], 3) for p in PANELS}, "b_small": {p: round(S[p] / ns, 2) for p in PANELS}, "b_large": {p: round(Lb[p] / nl, 2) for p in PANELS},
                  "gain_small": {p: round(vs[p].gain(), 4) for p in PANELS}, "gain_large": {p: round(vl[p].gain(), 4) for p in PANELS},
                  "full": {f"{k[0]}{k[1]}": v for k, v in full.items()}, "istar_small": {p: round(vs[p].i_star(vs[p].run), 4) for p in PANELS}, "istar_large": {p: round(vl[p].i_star(vl[p].run), 4) for p in PANELS},
                  "half_small": {p: round(vs[p].i_star(vs[p].run // 2), 4) for p in PANELS}, "half_large": {p: round(vl[p].i_star(vl[p].run // 2), 4) for p in PANELS}, "depfail": depf}
            if depf: v = "DEPENDENCE_FAILED"
            elif not all(full.values()): v = "NOT FULL"
            elif all(x >= 3.0 for x in rho.values()): v = "PROPORTIONAL"
            else: v = "SUBPROPORTIONAL"
            verdicts.append(v); det.append(dd)
        c = collections.Counter(verdicts)
        cls = ("NOT_EVALUATED" if c["NOT_EVALUATED"] >= 2 else "DEPENDENCE_FAILED" if c["DEPENDENCE_FAILED"] >= 2 else "NOT FULL" if c["NOT FULL"] >= 2
               else "PROPORTIONAL STEP" if c["PROPORTIONAL"] == 5 else "SUBPROPORTIONAL STEP" if c["SUBPROPORTIONAL"] >= 4 else "MIXED")
        sat[arm][key] = {"class": cls, "verdicts": verdicts, "detail": det}
        pcl.append(cls)
        print(f"{arm} {key}: {cls} {verdicts}")
        for r, d in zip(R5, det):
            print(f"    r{r}: rho {d.get('rho')} b {d.get('b_small')} -> {d.get('b_large')} i* small {d.get('istar_small')} (half {d.get('half_small')}, gain {d.get('gain_small')}) large {d.get('istar_large')} (half {d.get('half_large')}, gain {d.get('gain_large')}) full {d.get('full')} dep {d.get('depfail')}")
    if all(x in ("NOT FULL", "NOT_EVALUATED") for x in pcl): ac = "SATURATION_NOT_MEASURED"
    elif "DEPENDENCE_FAILED" in pcl: ac = "DEPENDENCE_FAILED"
    elif "SUBPROPORTIONAL STEP" in pcl: ac = "SATURATION_DOES_NOT_SCALE"
    elif all(x == "PROPORTIONAL STEP" for x in pcl): ac = "SATURATION_PROPORTIONAL_ALL_PAIRS"
    else: ac = "INTERMEDIATE"
    sat[arm]["arm_class"] = ac
    print(f"  {arm} ARM CLASS {ac}")
ac = {a: sat[a]["arm_class"] for a in sat}
if any(ac[a] == "SATURATION_PROPORTIONAL_ALL_PAIRS" for a in ("F-OQ", "T-OQ", "F-OQ-IVF")): so = "SATURATION-PROPORTIONAL"
elif ac["F-OQ"] == ac["T-OQ"] == "SATURATION_DOES_NOT_SCALE": so = "SATURATION-SUBPROPORTIONAL"
elif ac["F-OQ"] == ac["T-OQ"] == "SATURATION_NOT_MEASURED": so = "SATURATION NOT MEASURED"
else: so = "SATURATION-INCONCLUSIVE"
print("SATURATION OUTCOME:", so)
res["saturation"] = {"arms": sat, "outcome": so}

# ============================================================== dense labels (8.5)
print("\n=== DENSE (capacity line) at the larger cell of each CAPACITY STEP")
cap = json.load(open(os.path.join(os.path.dirname(__file__), "a2_capacity.json")))
dense = {}
for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
    csteps = [s for s in STEPS if cap["steps"][arm][s]["class"] == "CAPACITY STEP"]
    lab_any_ahead = False
    info = {}
    for s in csteps:
        f, ns, nl, _ = STEPS[s]
        up = U_P_ROW[f]
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        run_a = V(arm, f, nl, 1, "A").run; run_d = V("D-OQ", f, nl, 1, "A").run
        mc = mc_entry(cost, base, nl, "D-OQ", nl, up, run_a, run_d, "small")
        fz = plan["frozen"]["mc"][f"dense|{base}|{nl//1024 if False else ''}"] if False else plan["frozen"]["mc"][f"dense|{base}|{f//1024}K/{nl//1024}K"]
        rd = {"MU": [], "MC": [], "D-BEST": []}
        for r in R5:
            for name in rd:
                ds = {}
                for p in PANELS:
                    a, d = V(arm, f, nl, r, p), V("D-OQ", f, nl, r, p)
                    if name == "MU": ds[p] = (a.i(up) - d.i(up), d.a_use(up))
                    elif name == "MC": ds[p] = (a.i(mc[0]) - d.i(mc[1]), d.a_use(mc[1]))
                    else: ds[p] = (a.i(up) - d.i_star(d.run), None)
                rd[name].append(ds)
        n_ahead = {name: sum(1 for ds in v if any(x[0] <= -0.25 for x in ds.values())) for name, v in rd.items()}
        lab_any_ahead |= any(x >= 4 for x in n_ahead.values())
        info[s] = {"cell": f"{f}/{nl}", "mc_mine": mc, "mc_frozen": [fz["small_update"], fz["large_update"], fz["annotation"]], "replicates_ahead": n_ahead,
                   "d": {name: [{p: round(x[0], 4) for p, x in ds.items()} for ds in v] for name, v in rd.items()},
                   "dense_a_use": {name: [{p: (round(x[1], 4) if x[1] is not None else None) for p, x in ds.items()} for ds in v] for name, v in rd.items()}}
    dense[arm] = {"capacity_steps": csteps, "label": ("DENSE AHEAD" if lab_any_ahead else ("DENSE NOT READ" if not csteps else "not ahead")), "cells": info}
    print(arm, dense[arm]["label"], "steps", csteps)
    for s, i in info.items():
        print("   ", s, i["cell"], "MC mine", i["mc_mine"], "frozen", i["mc_frozen"], "replicates ahead", i["replicates_ahead"])
        for name in ("MU", "MC", "D-BEST"):
            print("      ", name, "d:", i["d"][name], "D-OQ a_use:", i["dense_a_use"][name])

print("\n=== DENSE AT SATURATION (loaded cells, both at U_L)")
dsat = {}
for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
    per = {}
    ahead_any = False
    for (f, n) in ((8192, 1024), (32768, 4096)):
        rows = []
        for r in R5:
            row = {}
            for p in PANELS:
                a, d = V(arm, f, n, r, p), V("D-OQ", f, n, r, p)
                ia, idd = a.i_star(a.run), d.i_star(d.run)
                row[p] = (round(ia - idd, 4), round(ia / idd, 4) if idd > 0 else None, round(ia, 4), round(idd, 4), round(d.gain(), 4))
            rows.append(row)
        cnt = sum(1 for row in rows if any(x[0] <= -0.25 for x in row.values()))
        ahead_any |= cnt >= 4
        per[f"{f}/{n}"] = {"replicates_dense_ahead": cnt, "rows": rows}
    dsat[arm] = {"label": "DENSE HOLDS MORE AT SATURATION" if ahead_any else "not dense-holds-more", "cells": per}
    print(arm, dsat[arm]["label"])
    for c, v in per.items():
        print(f"   {c}: replicates with d_sat<=-0.25 (either panel) {v['replicates_dense_ahead']}/5; per rep (d_sat, r_sat, i*arm, i*D-OQ, D-OQ last-doubling gain):")
        for r, row in zip(R5, v["rows"]):
            print(f"       r{r} {row}")
res["dense"] = dense
res["dense_sat"] = dsat

# ============================================================== hierarchy, conventional
print("\n=== HIERARCHY T-OQ / F-OQ-IVF on I_use at U_P")
hier = {}
for (f, n) in ((8192, 4096), (32768, 16384)):
    up = U_P_ROW[f]
    rat = []
    for r in R5:
        rr = {}
        for p in PANELS:
            t, v, e = V("T-OQ", f, n, r, p).i(up), V("F-OQ-IVF", f, n, r, p).i(up), V("F-OQ", f, n, r, p).i(up)
            rr[p] = (round(t / v, 4) if v > 0 else math.inf, round(t / e, 4) if e > 0 else math.inf)
        rat.append(rr)
    hier[f"{f}/{n}"] = rat
    print(f"{f}/{n}: (T/IVF, T/exhaustive) per rep:", rat)
def cnt(th, c): return sum(1 for rr in hier[c] if all(rr[p][0] >= th for p in PANELS))
hl = "TREE_AHEAD" if all(cnt(1.03, c) >= 4 for c in hier) else "TREE_COMPETITIVE" if all(cnt(0.97, c) >= 4 for c in hier) else "TREE_BEHIND"
print("HIERARCHY:", hl)
res["hierarchy"] = {"label": hl, "ratios": hier}

print("\n=== CONVENTIONAL RETRIEVAL at 32K/16K (KNN i from raw accuracy)")
conv = {}
for arm in ("F-OQ", "F-OQ-IVF", "T-OQ"):
    c = 0; rows = []
    for r in R5:
        b = json.load(open(f"{RUN}/baselines/d{r}_f32768.json"))
        ia = {p: V(arm, 32768, 16384, r, p).i(16384) for p in PANELS}
        ik = {p: bits(b["panels"][p]["KNN-W"]["correct"], b["panels"][p]["KNN-W"]["n"]) for p in PANELS}
        iv = {p: bits(b["panels"][p]["KNN-W-IVF"]["correct"], b["panels"][p]["KNN-W-IVF"]["n"]) for p in PANELS}
        ok = any(all(k[p] >= ia[p] - 0.25 for p in PANELS) for k in (ik, iv))
        c += ok
        rows.append((round(ia["A"], 3), round(ik["A"], 3), round(iv["A"], 3), b["panels"]["A"]["DICT"]["correct"] / b["panels"]["A"]["DICT"]["n"]))
    conv[arm] = {"suffices": c >= 4, "count": c, "rows(i_arm A, i_KNN A, i_KNN-IVF A, DICT acc)": rows}
    print(arm, conv[arm])
res["conventional"] = conv

# ============================================================== task 4: raw a_use table
print("\n=== TASK 4: a_use (mean over 5 replicates of the mean of panels A and B; [min, max] over replicates and panels)")
tab = {}
cellset = sorted({(k[1], k[2], k[3]) for k in cells if k[0] == "P"}, key=lambda x: (x[0], x[1], x[2]))
for arm, f, n in cellset:
    up = U_P_ROW[f]
    run = P(cells, arm, f, n, 1)["meta"]["run_updates"]
    def stat(fn):
        vals = [fn(V(arm, f, n, r, p)) for r in R5 for p in PANELS]
        means = [(fn(V(arm, f, n, r, "A")) + fn(V(arm, f, n, r, "B"))) / 2 for r in R5]
        return round(sum(means) / 5, 4), round(min(vals), 4), round(max(vals), 4)
    a_up = stat(lambda v: v.a_use(up)); a_run = stat(lambda v: v.a_use(run)); a_max = stat(lambda v: max(v.a_use(u) for v in [v] for u in v.ups))
    i_up = stat(lambda v: v.i(up)); i_run = stat(lambda v: v.i_star(run))
    raw_up = stat(lambda v: v.acc(up))
    tab[f"{arm} {f//1024}K/{n//1024 if n>=1024 else n}{'K' if n>=1024 else ''}"] = {"U_P": up, "U_run": run, "a_use_UP": a_up, "a_use_Urun": a_run, "a_use_max": a_max, "raw_acc_UP": raw_up, "i_UP": i_up, "istar_Urun": i_run}
    print(f"{arm:9s} {f:6d}/{n:6d} U_P={up:6d} U_run={run:7d}  a_use@U_P {a_up}  a_use@U_run {a_run}  max a_use {a_max}  raw@U_P {raw_up}  i@U_P {i_up}  i*@U_run {i_run}")
res["table"] = tab
json.dump(res, open(os.path.join(os.path.dirname(__file__), "a3_lines.json"), "w"), indent=1, default=str)
