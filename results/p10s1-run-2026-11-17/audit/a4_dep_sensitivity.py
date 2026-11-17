# ruff: noqa
"""DEP: where it fails, why, and how much the capacity outcome depends on the registered reading of 'every snapshot up to the run length' (ruling 22 (g)).
Descriptive sensitivity only; the registered rule is ruling 22 (g). Not a re-analysis under a new rule."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import PANELS, STEPS, U_P_ROW, View, load_cells, load_plan, P, chance_interval

cells = load_cells()
plan = load_plan()
R5 = range(1, 6)

# 1. census of every DEP evaluation on registered memory cells
tot = collections.Counter()
fails = []
window = []
for k, c in sorted(cells.items()):
    if k[0] != "P" or k[1] in ("D-OQ",):
        continue
    for p in PANELS:
        v = View(c, p)
        for u in v.ups:
            d = v.dep(u)
            if d is None:
                continue
            tot[k[1]] += 1
            r = v.recs[u]
            if not d[0]:
                n = r["n"]; p0 = r["disabled_correct"] / n
                exp_extra = (n - r["useful"]) * p0
                fails.append((k[1], k[2], k[3], k[4], p, u, r["useful"], r["correct"], n, round(r["useful"] / n, 4), round(r["useful"] / r["correct"], 4), r["correct"] - r["useful"], round(exp_extra, 1), d[1]))
            a = r["useful"] / r["n"]
            if a < 0.45:
                window.append((round(a, 3), round(r["useful"] / r["correct"], 4), d[0]))
print("DEP evaluations (a_use >= 0.25) on registered memory cells, per arm:", dict(tot))
print("DEP failures:", len(fails), "  all from the 0.95 x raw condition:", all(all('0.95' in w for w in f[-1]) for f in fails))
print("(arm, facts, slots, draw, panel, update, useful, correct, n, a_use, useful/correct, correct-useful, (n-useful)*disabled_rate)")
for f in fails:
    print("  ", f[:-1])
print("updates at which DEP failed:", collections.Counter(f[5] for f in fails), " U_P/x:", collections.Counter(f"{U_P_ROW[f[1]]//f[5]}" for f in fails))
# pass/fail as a function of a_use near the floor
bins = collections.defaultdict(lambda: [0, 0])
for a, ratio, ok in window:
    b = round(int(a * 20) / 20, 2)
    bins[b][0 if ok else 1] += 1
print("a_use bin (lower edge, width 0.05): [DEP passes, DEP fails]:", dict(sorted(bins.items())))
mx = max(f[9] for f in fails)
print("largest a_use at a failure:", mx)

# 2. sensitivity: capacity step verdicts with DEP read (a) at every snapshot (registered, ruling 22 (g)); (b) only at the snapshots whose values enter the verdict; (c) not at all
cap = json.load(open(os.path.join(os.path.dirname(__file__), "a2_capacity.json")))
mc = {k: v["mine"] for k, v in cap["mc_check"].items()}

def read_snaps(view, role, s, arm):
    up = U_P_ROW[STEPS[s][0]]
    base = "F-OQ" if arm == "F-OQ-IVF" else arm
    m = mc[f"cap|{base}|{s}"]
    out = {up, m[0] if role == "S" else m[1]}
    for lim in ([view.run, view.run // 2] if role == "S" else [view.run]):
        el = [u for u in view.ups if u <= lim]
        out.add(max(el, key=lambda u: (view.i(u), -u)))
    return out

def verdict(arm, s, r, p, mode):
    f, ns, nl, _ = STEPS[s]
    up = U_P_ROW[f]
    S, L = View(P(cells, arm, f, ns, r), p), View(P(cells, arm, f, nl, r), p)
    base = "F-OQ" if arm == "F-OQ-IVF" else arm
    m = mc[f"cap|{base}|{s}"]
    if mode != "none":
        for v, role in ((S, "S"), (L, "L")):
            snaps = v.ups if mode == "all" else read_snaps(v, role, s, arm)
            if any(v.dep(u) is not None and not v.dep(u)[0] for u in snaps):
                return "DEPENDENCE_FAILED"
    i_s_up, i_l_up = S.i(up), L.i(up)
    i_s_run, i_s_half, i_l_run = S.i_star(S.run), S.i_star(S.run // 2), L.i_star(L.run)
    d_mu, d_sat, d_full = i_l_up - i_s_up, i_l_up - i_s_run, i_l_run - i_s_run
    d_mc = L.i(m[1]) - S.i(m[0])
    if i_s_up >= 4.5: return "CEILING"
    if d_mu >= 0.5 and d_mc >= 0.5 and d_sat >= 0.5 and S.loaded() and d_sat - 2 * (i_s_run - i_s_half) >= 0.5 and L.a_use(up) >= 0.5: return "CAPACITY"
    if d_mu >= 0.5: return "GAIN WITHIN BUDGET ONLY"
    if d_mu <= -0.5 and d_full <= -0.5: return "REVERSED"
    if d_mu <= -0.5: return "BEHIND WITHIN BUDGET"
    if abs(d_mu) < 0.25 and abs(d_full) < 0.25 and S.plateaued() and L.plateaued(): return "NULL" if S.loaded() else "FLAT, NOT LOADED"
    return "UNRESOLVED"

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
    floor = all(View(P(cells, arm, 32768, 16384, r), p).a_use(16384) >= 0.80 for r in R5 for p in PANELS)
    if all(has.values()) and not any(c == "REVERSED" for c in sc.values()) and floor: return "CAPACITY_SUPPORTED"
    if any(has.values()): return "CAPACITY_ONE_TRANSITION"
    if any(all(sc[s] == "NOT LOADED" for s in ss) for ss in trans.values()): return "NOT_TESTED_BY_LOAD"
    if all(any(sc[s] in ("NO GAIN", "REVERSED") for s in ss) for ss in trans.values()): return "CAPACITY_NOT_SUPPORTED"
    return "INTERMEDIATE"

for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
    floor = [(r, p, round(View(P(cells, arm, 32768, 16384, r), p).a_use(16384), 4)) for r in R5 for p in PANELS]
    print(f"\n{arm}: a_use at 32K/16K at U_P (section 8.4 row 3 floor 0.80):", min(x[2] for x in floor))
    for mode in ("all", "read", "none"):
        sc = {}
        for s in STEPS:
            vs = []
            for r in R5:
                pv = {p: verdict(arm, s, r, p, mode) for p in PANELS}
                vs.append(pv["A"] if pv["A"] == pv["B"] else "PANEL-DISAGREE")
            sc[s] = (step_class(vs), vs)
        print(f"  DEP mode {mode:4s}: arm class {arm_class(arm, {s: v[0] for s, v in sc.items()}):24s}", {s: v[0] for s, v in sc.items()})
