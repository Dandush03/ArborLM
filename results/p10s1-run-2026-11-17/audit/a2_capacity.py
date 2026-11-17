# ruff: noqa
"""Task 2a: capacity line, recomputed from raw counts by the text of ADR-0021 sections 8.1-8.4, 8.7 and ruling 22 (g)."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import PANELS, STEPS, U_P_ROW, REF_CELL, View, load_cells, load_plan, mc_entry, P

plan = load_plan()
cost = plan["frozen"]["cost"]
cells = load_cells()
ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")
out = {"steps": {}, "arms": {}, "dep_detail": [], "mc_check": {}}


def ref_ok(r, facts):
    f, n = REF_CELL[facts]
    c = P(cells, "R2", f, n, r)
    vs = [View(c, p) for p in PANELS]
    return all(v.a_use(v.u_p) >= 0.95 for v in vs), [round(v.a_use(v.u_p), 5) for v in vs]


# MC entries: recompute from the frozen cost table and compare with the frozen plan
for arm in ("F-OQ", "T-OQ", "H8"):
    for s, (f, ns, nl, tr) in STEPS.items():
        up = U_P_ROW[f]
        run_s = P(cells, arm, f, ns, 1)["meta"]["run_updates"]; run_l = P(cells, arm, f, nl, 1)["meta"]["run_updates"]
        mine = mc_entry(cost, arm, ns, arm, nl, up, run_s, run_l, "large")
        fz = plan["frozen"]["mc"][f"cap|{arm}|{s}"]
        same = (mine[0], mine[1]) == (fz["small_update"], fz["large_update"]) and (mine[3] == fz["annotation"])
        out["mc_check"][f"cap|{arm}|{s}"] = {"mine": mine, "frozen": [fz["small_update"], fz["large_update"], fz["multiplier"], fz["annotation"]], "same": same}

def mc_for(arm, s):
    base = "F-OQ" if arm == "F-OQ-IVF" else arm
    e = out["mc_check"][f"cap|{base}|{s}"]["mine"]
    return e[0], e[1]


def panel_verdict(arm, s, r, p):
    f, ns, nl, tr = STEPS[s]
    up = U_P_ROW[f]
    cs, cl = P(cells, arm, f, ns, r), P(cells, arm, f, nl, r)
    S, L = View(cs, p), View(cl, p)
    ok, refv = ref_ok(r, f)
    leak = [v.leakage() for v in (View(cs, "A"), View(cs, "B"), View(cl, "A"), View(cl, "B"))]
    d = {"ref": refv}
    if not ok or any(leak):
        return ("NOT_EVALUATED", d)
    u_s_mc, u_l_mc = mc_for(arm, s)
    i_s_up, i_l_up = S.i(up), L.i(up)
    i_s_run, i_s_half, i_l_run = S.i_star(S.run), S.i_star(S.run // 2), L.i_star(L.run)
    d_mu, d_sat, d_full = i_l_up - i_s_up, i_l_up - i_s_run, i_l_run - i_s_run
    d_mc = L.i(u_l_mc) - S.i(u_s_mc) if (u_s_mc and u_l_mc) else None
    d.update(i_s_up=i_s_up, i_l_up=i_l_up, i_s_run=i_s_run, i_s_half=i_s_half, i_l_run=i_l_run, d_mu=d_mu, d_mc=d_mc, d_sat=d_sat, d_full=d_full,
             mc=(u_s_mc, u_l_mc), loaded=S.loaded(), p_s=S.plateaued(), p_l=L.plateaued(), a_l_up=L.a_use(up), gain_s=S.gain())
    fs, fl = S.dep_failures(), L.dep_failures()
    if fs or fl:
        d["dep_fail_small"], d["dep_fail_large"] = fs, fl
        return ("DEPENDENCE_FAILED", d)
    if i_s_up >= 4.5:
        return ("CEILING", d)
    if (d_mu >= 0.5 and d_mc is not None and d_mc >= 0.5 and d_sat >= 0.5 and S.loaded()
            and d_sat - 2 * (i_s_run - i_s_half) >= 0.5 and L.a_use(up) >= 0.5):
        return ("CAPACITY", d)
    if d_mu >= 0.5:
        return ("GAIN WITHIN BUDGET ONLY", d)
    if d_mu <= -0.5 and d_full <= -0.5:
        return ("REVERSED", d)
    if d_mu <= -0.5:
        return ("BEHIND WITHIN BUDGET", d)
    if abs(d_mu) < 0.25 and abs(d_full) < 0.25 and S.plateaued() and L.plateaued():
        return ("NULL" if S.loaded() else "FLAT, NOT LOADED", d)
    return ("UNRESOLVED", d)


def step_class(v):
    c = collections.Counter(v)
    if c["NOT_EVALUATED"] >= 2: return "NOT_EVALUATED"
    if c["DEPENDENCE_FAILED"] >= 2: return "DEPENDENCE_FAILED"
    if c["PANEL-DISAGREE"] >= 2: return "NOT REPLICATED"
    if c["CAPACITY"] == 5: return "CAPACITY STEP"
    if c["CAPACITY"] + c["GAIN WITHIN BUDGET ONLY"] == 5: return "GAIN WITHIN BUDGET"
    if c["CEILING"] + c["FLAT, NOT LOADED"] >= 4: return "NOT LOADED"
    if c["REVERSED"] >= 4: return "REVERSED"
    if c["NULL"] + c["REVERSED"] >= 4: return "NO GAIN"
    return "MIXED"


def arm_class(arm, sc):
    trans = {"1K->4K": ["C1", "N1"], "4K->16K": ["C2", "N2"]}
    if any(all(sc[s] == "NOT_EVALUATED" for s in ss) for ss in trans.values()): return "NOT_EVALUATED"
    if any(c == "DEPENDENCE_FAILED" for c in sc.values()): return "DEPENDENCE_FAILED"
    has = {t: any(sc[s] == "CAPACITY STEP" for s in ss) for t, ss in trans.items()}
    floor = all(View(P(cells, arm, 32768, 16384, r), p).a_use(16384) >= 0.80 for r in range(1, 6) for p in PANELS)
    if all(has.values()) and not any(c == "REVERSED" for c in sc.values()) and floor: return "CAPACITY_SUPPORTED"
    if any(has.values()): return "CAPACITY_ONE_TRANSITION"
    if any(all(sc[s] == "NOT LOADED" for s in ss) for ss in trans.values()): return "NOT_TESTED_BY_LOAD"
    if all(any(sc[s] in ("NO GAIN", "REVERSED") for s in ss) for ss in trans.values()): return "CAPACITY_NOT_SUPPORTED"
    return "INTERMEDIATE"


def r(x):
    return None if x is None else (round(x, 4) if isinstance(x, float) else x)


for arm in ARMS:
    out["steps"][arm] = {}
    for s in STEPS:
        verdicts, reps = [], []
        for rep in range(1, 6):
            pv = {p: panel_verdict(arm, s, rep, p) for p in PANELS}
            vs = {p: pv[p][0] for p in PANELS}
            v = vs["A"] if vs["A"] == vs["B"] else "PANEL-DISAGREE"
            verdicts.append(v)
            reps.append({"rep": rep, "verdict": v, "panels": {p: {"v": pv[p][0], **{k: (r(x) if not isinstance(x, (list, tuple)) else x) for k, x in pv[p][1].items()}} for p in PANELS}})
        out["steps"][arm][s] = {"class": step_class(verdicts), "verdicts": verdicts, "reps": reps}
    sc = {s: out["steps"][arm][s]["class"] for s in STEPS}
    out["arms"][arm] = arm_class(arm, sc)

json.dump(out, open(os.path.join(os.path.dirname(__file__), "a2_capacity.json"), "w"), indent=1, default=str)
print("MC check (frozen vs mine):", all(v["same"] for v in out["mc_check"].values()), {k: v for k, v in out["mc_check"].items() if not v["same"]})
for arm in ARMS:
    print(f"\n== {arm}: ARM CLASS {out['arms'][arm]}")
    for s in STEPS:
        st = out["steps"][arm][s]
        print(f"  {s}: {st['class']:22s} {st['verdicts']}")
        for rp in st["reps"]:
            for p in PANELS:
                d = rp["panels"][p]
                extra = ""
                if d["v"] == "DEPENDENCE_FAILED":
                    extra = f" depfail small={d.get('dep_fail_small')} large={d.get('dep_fail_large')}"
                print(f"     r{rp['rep']} {p}: {d['v']:24s} i_s(UP)={d.get('i_s_up')} i_l(UP)={d.get('i_l_up')} dMU={d.get('d_mu')} dMC={d.get('d_mc')} dSAT={d.get('d_sat')} dFULL={d.get('d_full')} i*s(run)={d.get('i_s_run')} i*s(half)={d.get('i_s_half')} gain_s={d.get('gain_s')} loaded={d.get('loaded')} pS={d.get('p_s')} pL={d.get('p_l')} aL(UP)={d.get('a_l_up')}{extra}")
