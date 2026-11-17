"""Audit script a2 (Claude Opus 5.5 auditor; P10-S1 revision 5 implementation audit; not Astra review).

My own implementations of the revision-5 rules (ADR-0021 sections 5.4, 8.2, 8.5, 8.7, 8.10, 10.1), written from the
ADR text, compared with studies.p10s1.classes / calibrate on constructed and random synthetic records; plus the
plateau floor recomputed on revision 4's raw calibration records (calibration draws; already observed; read only).

  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root> <revision-4 calibration run dir>
"""

import glob
import json
import math
import os
import random
import sys

ROOT, REV4 = sys.argv[1], sys.argv[2]
sys.path.insert(0, ROOT)
from studies.p10s1 import calibrate as K  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import core  # noqa: E402

out, fails = [], []


def check(name, ok, detail=""):
    out.append(f"{'OK  ' if ok else 'FAIL'} {name}{(': ' + str(detail)) if detail != '' else ''}")
    if not ok:
        fails.append(name)


# ---------------- my primitives ----------------
def log_binom_pmf(k, n, p):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log(1 - p)


def my_chance(n, alpha=0.001 / 40, p=1 / 32):
    pm = [math.exp(log_binom_pmf(k, n, p)) for k in range(0, int(n * p * 4) + 200)]
    cdf, s = [], 0.0
    for x in pm:
        s += x
        cdf.append(s)
    lo = next(k for k in range(len(cdf)) if cdf[k] > alpha / 2)  # P(X <= lo - 1) <= alpha/2
    hi = next(k for k in range(len(cdf)) if 1 - cdf[k] <= alpha / 2)  # P(X > hi) <= alpha/2
    return lo, hi


CH = {}
for n in (2048, 8192, 32768):
    CH[n] = my_chance(n)
check("chance intervals [34,100] [192,325] [894,1159] (mine)", CH == {2048: (34, 100), 8192: (192, 325), 32768: (894, 1159)}, CH)
for n in (2048, 8192, 32768):
    iv = core.chance_interval(n)
    check(f"code chance interval n={n}", (iv.low, iv.high) == CH[n], (iv.low, iv.high))


def fano(a):
    e = 1 - a
    if e <= 0:
        return 5.0
    h = -(e * math.log2(e) + (1 - e) * math.log2(1 - e)) if 0 < e < 1 else 0.0
    return 5 - h - e * math.log2(31)


def my_i(useful, n):
    if n not in CH:
        CH[n] = my_chance(n)  # attempt 2: attempt 1 failed with KeyError at n = 131,072 (my own defect; kept as a2_rules.attempt1.out)
    return 0.0 if useful <= CH[n][1] else fano(useful / n)


FLOOR = fano(0.25)
check(f"plateau floor = i(0.25) = {FLOOR:.4f} (ADR 0.473)", abs(FLOOR - 0.473) < 5e-4 and abs(core.PLATEAU_FLOOR_I - FLOOR) < 1e-12, core.PLATEAU_FLOOR_I)
for a, v in ((0.5, 1.523), (0.8, 3.287), (0.9, 4.036), (0.95, 4.466)):
    check(f"i({a}) = {fano(a):.3f} (ADR {v})", abs(fano(a) - v) < 1e-3)

EPS = 1e-12


def istar(series, limit):
    return max(v for u, v in series.items() if u <= limit)


def my_plateaued(series, run):
    return istar(series, run) - istar(series, run // 2) <= 0.10 + EPS and istar(series, run // 2) >= FLOOR - EPS


def my_loaded(series, run):
    return my_plateaued(series, run) and istar(series, run) <= 4.0 + EPS


# ---------------- B. plateau floor on revision 4's raw curves ----------------
rows = []
code_mismatch = 0
for path in sorted(glob.glob(os.path.join(REV4, "cells", "CAL_F-OQ_*_y65536"))):
    label = os.path.basename(path)
    f = int(label.split("_f")[1].split("_")[0])
    n = int(label.split("_n")[1].split("_")[0])
    for panel in ("A", "B"):
        series, obs = {}, {}
        for ev in glob.glob(os.path.join(path, "eval", "u*", "eval.json")):
            d = json.load(open(ev))
            pa = d["reads"]["main"]["panels"][panel]
            u = int(os.path.basename(os.path.dirname(ev))[1:])
            series[u] = my_i(pa["useful"], pa["n"])
            obs[u] = C.PanelObs(n=pa["n"], correct=pa["correct"], useful=pa["useful"], disabled=pa.get("disabled_correct"), shuffled=pa.get("shuffled_correct"), swap=pa.get("swap_correct"))
        for run in (1024, 2048, 4096, 8192, 16384, 32768, 65536):
            if run not in series or run // 2 not in series:
                continue
            nofloor = istar(series, run) - istar(series, run // 2) <= 0.10 + EPS and istar(series, run) <= 4.0 + EPS
            withfloor = my_loaded(series, run)
            v = C.View({u: o for u, o in obs.items() if u <= run}, run, 8192)
            if v.loaded() != withfloor:
                code_mismatch += 1
            rows.append((f"{f}/{n}", label.split("_d")[1][0], panel, run, round(istar(series, run // 2), 3), round(istar(series, run), 3), nofloor, withfloor))
early = [r for r in rows if r[3] <= 8192 and r[6]]
early_floor = [r for r in rows if r[3] <= 8192 and r[7]]
out.append(f"     revision-4 F-OQ curves: {len(rows)} (cell, draw, panel, run) views read")
out.append(f"     'loaded' by the revision-4 rule (no floor) at run <= 8,192: {len(early)} views, e.g. {early[:3]}")
check("with the floor, no revision-4 view is loaded at run lengths 1,024-8,192 (ADR 8.2 / fact 14)", not early_floor, early_floor[:5])
check("code View.loaded equals my rule on every revision-4 view", code_mismatch == 0, code_mismatch)
for r in rows:
    if r[7]:
        out.append(f"     loaded with the floor: {r}")
changed_at_65536 = [r for r in rows if r[3] == 65536 and r[6] != r[7]]
check("the floor changes no view's status at 65,536 (where revision 4's runs ended)", not changed_at_65536, changed_at_65536)


# ---------------- C. load search ----------------
def mk_obs(i_target_a, n=8192):
    useful = int(round(i_target_a * n))
    return C.PanelObs(n=n, correct=useful, useful=useful, disabled=n // 32, shuffled=n // 32)


def views_from(a_by_u, n=8192):
    return {(d, p): C.View({u: mk_obs(a, n) for u, a in a_by_u.items()}, max(a_by_u), 8192) for d in (1, 2) for p in ("A", "B")}


def my_pass(a_by_u, U, n=8192):
    s = {u: my_i(int(round(a * n)), n) for u, a in a_by_u.items() if u <= U}
    return U in s and U // 2 in s and my_loaded(s, U)


def my_ul(a_by_u, cands):
    for k in range(1, len(cands)):
        if my_pass(a_by_u, cands[k - 1]) and my_pass(a_by_u, cands[k]):
            return cands[k]
    return None


cands = core.load_candidates("8K/1K")  # 65,536 ... 262,144
grid = sorted({512 * 2**k for k in range(10)} | set(cands) | {c // 2 for c in cands})
grid = [u for u in grid if u <= 262144]


def curve(points):  # a_use that rises then holds; points: list of (update, a) breakpoints, step function
    out_ = {}
    for u in grid:
        out_[u] = max([a for uu, a in points if uu <= u] + [0.0])
    return out_


cases = {
    "passes at the first two candidates": curve([(512, 0.2), (16384, 0.5), (32768, 0.6), (131072, 0.75)]),
    "first pass alone (rises after the first candidate)": curve([(512, 0.2), (16384, 0.5), (32768, 0.6), (98304, 0.65), (131072, 0.7), (196608, 0.75), (262144, 0.8)]),
    "two consecutive passes from the first": curve([(512, 0.2), (16384, 0.5), (32768, 0.6)]),
    "pass-fail-pass-pass": curve([(512, 0.2), (16384, 0.5), (32768, 0.6), (98304, 0.7)]),
    "above 4.0 bits (a 0.92) everywhere late": curve([(512, 0.2), (16384, 0.6), (32768, 0.92)]),
    "flat below the DEP floor": curve([(512, 0.05), (1024, 0.20)]),
    "never flat": {u: min(0.89, 0.1 + 0.1 * math.log2(u / 512)) for u in grid},
}
for name, a in cases.items():
    mine = my_ul(a, list(cands))
    code = K.arm_u_l(views_from(a), list(cands))
    check(f"U_L [{name}] mine={mine} code={code}", mine == code)
# attempt 3: attempt 2 expected 196,608 here; that was my error (the consecutive pair is 196,608 and 262,144, so U_L is 262,144); kept in a2_rules.attempt2.out
check("pass-fail-pass-pass gives the later candidate of the consecutive pair (196,608 and 262,144 -> 262,144)", my_ul(cases["pass-fail-pass-pass"], list(cands)) == 262144, my_ul(cases["pass-fail-pass-pass"], list(cands)))
check("a first pass alone gives no U_L", my_ul(cases["first pass alone (rises after the first candidate)"], list(cands)) is None and K.arm_u_l(views_from(cases["first pass alone (rises after the first candidate)"]), list(cands)) is None)
short = views_from(cases["two consecutive passes from the first"])
short.pop((2, "B"))
check("a failed / missing run (three views) gives no U_L", K.arm_u_l(short, list(cands)) is None and K.arm_u_l(None, list(cands)) is None)
o = K.cell_outcome(None, 131072)
check("F-OQ none -> NOT LOADED WITHIN ITS CEILING, RETURN_TO_LEAD (even with a T-OQ U_L)", o["action"] == K.RETURN_TO_LEAD and o["u_l"] is None)
o = K.cell_outcome(131072, None)
check("F-OQ only -> F-OQ's, T-OQ PREDICTED NOT LOADED", o["action"] == K.GRID_STANDS and o["u_l"] == 131072 and o["toq_predicted_not_loaded"])
o = K.cell_outcome(98304, 196608)
check("both -> the larger", o["u_l"] == 196608)
o = K.saturation_cell_outcome(None)
check("2K/256 none -> not run, no return", o["action"] == K.GRID_STANDS and o["runs"] is False and "256 NOT MEASURED" in o["status"])
try:
    K.plan_values({"returns_to_lead": ["x"]})
    check("plan_values refuses an open return", False)
except K.TieNeedsLead:
    check("plan_values refuses an open return (nothing proceeds as NOT TESTED automatically)", True)

# ---------------- D. row U_P ----------------
def row(fa, ra):
    f = {(u, d, p): fa[u] for u in fa for d in (1, 2) for p in "AB"}
    r = {(u, d, p): ra[u] for u in ra for d in (1, 2) for p in "AB"}
    return K.row_u_p(f, r, [8192, 16384, 32768])


check("row U_P 8,192", row({8192: .9, 16384: .95, 32768: .99}, {8192: .95, 16384: 1, 32768: 1})["u_p"] == 8192)
check("row U_P 16,384 (R2 short at 8,192)", row({8192: .95, 16384: .95, 32768: .99}, {8192: .949, 16384: .96, 32768: 1})["u_p"] == 16384)
check("row U_P 32,768", row({8192: .5, 16384: .89, 32768: .9}, {8192: 1, 16384: 1, 32768: 1})["u_p"] == 32768)
check("row U_P none -> return", row({8192: .5, 16384: .6, 32768: .89}, {8192: 1, 16384: 1, 32768: 1})["action"] == K.RETURN_TO_LEAD)


# ---------------- E. dense rate ----------------
def my_select(readout, walk, diverged):
    live = {r: v for r, v in readout.items() if r not in diverged}
    if not live:
        return "RETURN", None
    best = max(live.values())
    best_rate = min(r for r, v in live.items() if v == best)
    others = [v for r, v in live.items() if r != best_rate]
    if best_rate == 0.1 and (not others or best - max(others) > 0.02 + EPS):
        return "RETURN", None
    cont = sorted(r for r, v in live.items() if best - v < 0.02 - EPS)
    if len(cont) == 1:
        return "OK", cont[0]
    for u in sorted(walk[cont[0]], reverse=True):
        vals = {r: walk[r][u] for r in cont}
        top = max(vals.values())
        cont = sorted(r for r, v in vals.items() if top - v < 0.02 - EPS)
        if len(cont) == 1:
            return "OK", cont[0]
    return "OK", min(cont)


R = (0.001, 0.003, 0.01, 0.03, 0.1)
walk_u = [4096, 2048, 1024, 512]
dcases = {
    "plain maximum 0.03": ({0.001: .1, 0.003: .4, 0.01: .8, 0.03: .95, 0.1: .5}, None, ()),
    "tie 0.01/0.03 separated at U/2": ({0.001: .1, 0.003: .4, 0.01: .94, 0.03: .95, 0.1: .5}, {0.01: {4096: .7, 2048: .5, 1024: .3, 512: .1}, 0.03: {4096: .9, 2048: .6, 1024: .3, 512: .1}}, ()),
    "tie never separated -> smaller": ({0.001: .1, 0.003: .4, 0.01: .94, 0.03: .95, 0.1: .5}, {0.01: {u: .5 for u in walk_u}, 0.03: {u: .51 for u in walk_u}}, ()),
    "0.1 best by > 0.02 -> return": ({0.001: .1, 0.003: .4, 0.01: .8, 0.03: .9, 0.1: .95}, None, ()),
    "0.1 tied, wins the walk -> EDGE": ({0.001: .1, 0.003: .4, 0.01: .8, 0.03: .94, 0.1: .95}, {0.03: {4096: .5, 2048: .4, 1024: .2, 512: .1}, 0.1: {4096: .8, 2048: .6, 1024: .3, 512: .1}}, ()),
    "0.1 diverged, 0.03 best": ({0.001: .1, 0.003: .4, 0.01: .8, 0.03: .9, 0.1: .0}, None, (0.1,)),
    "every rate diverged": ({r: 0 for r in R}, None, R),
    "0.1 ahead by exactly 0.02 (boundary)": ({0.001: .1, 0.003: .4, 0.01: .8, 0.03: 0.93, 0.1: 0.95}, None, ()),
}
for name, (ro, wk, dv) in dcases.items():
    mine = my_select(ro, wk or {}, set(dv))
    try:
        code = K.select_dense_rate(ro, wk, 8192, dv)
        cr = ("RETURN", None) if code["action"] == K.RETURN_TO_LEAD else ("OK", code["rate"])
        edge = code.get("edge")
    except K.TieNeedsLead as exc:
        cr, edge = ("TIE", str(exc)), None
    check(f"dense [{name}] mine={mine} code={cr} edge={edge}", mine == cr)
code = K.select_dense_rate(dcases["0.1 ahead by exactly 0.02 (boundary)"][0], None, 8192, ())
out.append(f"     boundary: 0.1 at 0.95 vs 0.03 at 0.93 -> code action {code['action']}, rate {code['rate']}, edge {code.get('edge')}, decided_by {code.get('decided_by')}")

# ---------------- F. matched compute comparator (ADR 5.4) ----------------
def my_mc(cs, cl, u_p, run_s, run_l, claim):
    grid_ = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
    r = {m: cl[m] / cs[m] for m in ("cpu", "madds")}
    if all(x >= 1 - EPS for x in r.values()):  # larger costlier or equal
        mult, cheap, run = max(r.values()), "small", run_s
    elif all(x <= 1 + EPS for x in r.values()):
        mult, cheap, run = max(1 / x for x in r.values()), "large", run_l
    else:
        mult = max(max(x, 1 / x) for x in r.values())
        cheap, run = ("small", run_s) if claim == "large" else ("large", run_l)
    g = next((x for x in grid_ if x >= mult - EPS), None)
    if g is None or u_p * g > run:
        return ("MC-SHORT", cheap)
    return ("OK", cheap, int(u_p * g))


mcs = [
    ({"cpu": 1, "madds": 1}, {"cpu": 1.6, "madds": 1.7}, "large"),
    ({"cpu": 1, "madds": 1}, {"cpu": 0.9, "madds": 1.2}, "large"),
    ({"cpu": 1, "madds": 1}, {"cpu": 0.9, "madds": 1.2}, "small"),
    ({"cpu": 1, "madds": 1}, {"cpu": 0.5, "madds": 5.1}, "small"),
    ({"cpu": 1, "madds": 1}, {"cpu": 1.0, "madds": 1.0}, "large"),
    ({"cpu": 1, "madds": 1}, {"cpu": 1.0, "madds": 0.8}, "large"),
    ({"cpu": 1, "madds": 1}, {"cpu": 7.0, "madds": 7.0}, "large"),
]
for cs, cl, claim in mcs:
    e = C.mc_pair(cs, cl, 8192, 49152, 49152, claim)
    mine = my_mc(cs, cl, 8192, 49152, 49152, claim)
    code = (e.status, e.cheaper) if e.status != "OK" else ("OK", e.cheaper, e.small_update if e.cheaper == "small" else e.large_update)
    check(f"MC {cs}->{cl} claim={claim}: mine={mine} code={code} annot={e.annotation}", mine == code)
e = C.mc_pair({"cpu": 1, "madds": 1}, {"cpu": 0.5, "madds": 5.1}, 8192, 49152, 30000, "small")
check("comparator reading beyond the other cell's run -> MC-SHORT", e.status == C.MC_SHORT, e)

# ---------------- G. dense at saturation (ADR 8.5) ----------------
def sat_cell(d, r, st, cost):
    return C.SatDenseCell("8K/1K", [{"A": (d, r), "B": (d, r)} for _ in range(5)], [{"A": st, "B": st} for _ in range(5)], cost)


cases_g = {
    "DENSE HOLDS MORE": ([sat_cell(-0.3, 0.8, C.PLATEAUED, True)], C.DENSE_HOLDS_MORE, []),
    "STORE HOLDS MORE": ([sat_cell(0.5, 1.2, C.PLATEAUED, True)], C.STORE_HOLDS_MORE, []),
    "SAME (ratio short)": ([sat_cell(0.1, 1.05, C.PLATEAUED, True)], C.SAME_AT_SATURATION, []),
    "SAME + DENSE STILL RISING": ([sat_cell(0.5, 1.2, C.RISING, True)], C.SAME_AT_SATURATION, [C.DENSE_STILL_RISING]),
    "SAME + DENSE NOT LEARNED": ([sat_cell(0.5, 1.2, C.FLAT_BELOW_FLOOR, True)], C.SAME_AT_SATURATION, [C.DENSE_NOT_LEARNED]),
    "SAME + NOT ESTABLISHED (cost)": ([sat_cell(0.5, 1.2, C.PLATEAUED, False)], C.SAME_AT_SATURATION, [C.DENSE_NOT_ESTABLISHED]),
}
for name, (cells, lab, sub) in cases_g.items():
    g = C.dense_at_saturation(cells)
    check(f"dense at saturation [{name}] -> {g['label']} {g['sublabels']}", g["label"] == lab and g["sublabels"] == sub)
both = C.dense_at_saturation([sat_cell(0.5, 1.2, C.RISING, False)])
ratio_fail_cost_fail = C.dense_at_saturation([sat_cell(0.1, 1.05, C.PLATEAUED, False)])
out.append(f"     two conditions fail (plateau, cost; ratio holds): sublabels {both['sublabels']} (ADR prints a sub-label only when row 2 fails ONLY because of one condition)")
out.append(f"     ratio fails AND cost fails: label {ratio_fail_cost_fail['label']}, sublabels {ratio_fail_cost_fail['sublabels']}")

# ---------------- H. saturation line (ADR 8.10) ----------------
def side(a_by_u, facts, slots, dep_ok=True):
    def ob(a):
        u_ = int(round(a * facts))
        return C.PanelObs(n=facts, correct=u_, useful=u_, disabled=(facts // 32 if dep_ok else u_), shuffled=facts // 32)
    run = max(a_by_u)
    return C.SatSide({p: C.View({u: ob(a) for u, a in a_by_u.items()}, run, 8192) for p in "AB"}, facts, slots)


flat = lambda a: {16384: a * 0.9, 32768: a, 65536: a, 131072: a}  # noqa: E731
small = side(flat(0.60), 8192, 1024)
i_small = fano(0.60)
# large cell: choose a_use so that rho = S(4N)/S(N) = 32768 i_L / (8192 i_S) = 4 i_L / i_S
need_3 = 0.75 * i_small
a_lo, a_hi = 0.0, 1.0
for _ in range(80):
    mid = (a_lo + a_hi) / 2
    a_lo, a_hi = (mid, a_hi) if fano(mid) < need_3 else (a_lo, mid)
large_prop = side(flat(min(1, a_hi + 0.01)), 32768, 4096)
large_sub = side(flat(max(0.3, a_lo - 0.05)), 32768, 4096)
check("pair PROPORTIONAL", C.saturation_pair(small, large_prop, ref_ok=True).verdict == C.PROPORTIONAL)
check("pair SUBPROPORTIONAL", C.saturation_pair(small, large_sub, ref_ok=True).verdict == C.SUBPROPORTIONAL)
check("pair NOT FULL (smaller still rising)", C.saturation_pair(side({16384: .3, 32768: .45, 65536: .6, 131072: .7}, 8192, 1024), large_prop, ref_ok=True).verdict == C.NOT_FULL)
check("pair NOT_EVALUATED", C.saturation_pair(small, large_prop, ref_ok=False).verdict == C.NOT_EVALUATED)
check("pair DEPENDENCE_FAILED", C.saturation_pair(side(flat(0.6), 8192, 1024, dep_ok=False), large_prop, ref_ok=True).verdict == C.DEPENDENCE_FAILED)
# rho exactly 3.0: construct S directly through counts: small 1,024 slots / 8,192 facts, large 4,096 / 32,768 with i_L = 0.75 i_S exactly is not reachable by counts; check the >= with EPS instead
check("rho >= 3.0 uses >= (a ratio of exactly 3.0 is PROPORTIONAL)", C.ge(3.0, core.SATURATION_RATIO) and not C.ge(3.0 - 1e-9, core.SATURATION_RATIO))
pc = C.saturation_pair_class
check("pair classes", [pc([C.NOT_EVALUATED] * 2 + [C.PROPORTIONAL] * 3), pc([C.DEPENDENCE_FAILED] * 2 + [C.PROPORTIONAL] * 3), pc([C.NOT_FULL] * 2 + [C.PROPORTIONAL] * 3), pc([C.PROPORTIONAL] * 5), pc([C.SUBPROPORTIONAL] * 4 + [C.PROPORTIONAL]), pc([C.SUBPROPORTIONAL] * 3 + [C.PROPORTIONAL] * 2)] == [C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_FULL, C.PROPORTIONAL_STEP, C.SUBPROPORTIONAL_STEP, C.MIXED])
ac = C.saturation_arm_class
check("arm classes (F-OQ two pairs)", [ac([C.NOT_FULL, C.NOT_EVALUATED]), ac([C.DEPENDENCE_FAILED, C.PROPORTIONAL_STEP]), ac([C.PROPORTIONAL_STEP, C.SUBPROPORTIONAL_STEP]), ac([C.PROPORTIONAL_STEP, C.PROPORTIONAL_STEP]), ac([C.NOT_FULL, C.PROPORTIONAL_STEP])] == [C.SAT_NOT_MEASURED, C.DEPENDENCE_FAILED, C.SAT_DOES_NOT_SCALE, C.SAT_PROPORTIONAL_ALL_PAIRS, C.INTERMEDIATE])
so = lambda cl, **kw: C.saturation_outcome(cl, engineering_failed=False, incomplete=False, **kw)  # noqa: E731
o3 = so({"F-OQ": C.INTERMEDIATE, "T-OQ": C.SAT_PROPORTIONAL_ALL_PAIRS}, sat256_absent=True)
check("outcome SATURATION-PROPORTIONAL via T-OQ when F-OQ is INTERMEDIATE (2K/256 absent; ruling 6), tagged", o3.label == C.SAT_PROPORTIONAL and core.STORE_ONLY_TAG in o3.printed and C.NOT_MEASURED_256 in o3.printed and C.NOT_FUNDED_16K in o3.printed, o3.printed)
o4 = so({"F-OQ": C.SAT_DOES_NOT_SCALE, "T-OQ": C.SAT_DOES_NOT_SCALE})
check("outcome SATURATION-SUBPROPORTIONAL", o4.label == C.SAT_SUBPROPORTIONAL, o4.printed)
check("SUBPROPORTIONAL printed with a crowding / 'not a property of the store alone' caveat (ADR 8.10, 12)", "crowd" in o4.printed.lower() or "property of the store" in o4.printed.lower(), o4.printed)
o5 = so({"F-OQ": C.SAT_NOT_MEASURED, "T-OQ": C.SAT_NOT_MEASURED})
check("outcome SATURATION NOT MEASURED", o5.label == C.SAT_NOT_MEASURED_OUTCOME)
o6 = so({"F-OQ": C.DEPENDENCE_FAILED, "T-OQ": C.SAT_PROPORTIONAL_ALL_PAIRS * 0 + C.INTERMEDIATE})
check("outcome INCONCLUSIVE with reason DEPENDENCE_FAILED", o6.label == C.SAT_INCONCLUSIVE and "DEPENDENCE_FAILED" in o6.reasons)
o_h8 = so({"F-OQ": C.INTERMEDIATE, "T-OQ": C.INTERMEDIATE, "H8": C.SAT_PROPORTIONAL_ALL_PAIRS})
check("H8 alone never gives SATURATION-PROPORTIONAL", o_h8.label == C.SAT_INCONCLUSIVE)

# ---------------- I. capacity outcome and milestone reading (ADR 8.7) ----------------
def arm(name, cls, dense=C.DENSE_MATCHES, dsat=C.SAME_AT_SATURATION, sub=(), sat=C.SAT_PROPORTIONAL_ALL_PAIRS):
    return C.ArmCapacity(name, cls, dense, ["C1", "C2"], "", dsat, list(sub), sat)


co = lambda arms, **kw: C.capacity_outcome(arms, engineering_failed=False, incomplete=False, **kw)  # noqa: E731
pos = co({"F-OQ": arm("F-OQ", C.CAPACITY_SUPPORTED), "T-OQ": arm("T-OQ", C.CAPACITY_SUPPORTED), "F-OQ-IVF": arm("F-OQ-IVF", C.INTERMEDIATE)})
check("CAPACITY-POSITIVE tagged, with 16,384->65,536 NOT TESTED and the size range", pos.label == C.CAPACITY_POSITIVE and core.STORE_ONLY_TAG in pos.printed and C.NOT_TESTED_16K_65K in pos.printed and C.SIZES_CAPACITY in pos.printed)
check("CAPACITY-POSITIVE printed label carries the saturation outcome with bits per slot (ADR 8.7 printed label)", "SATURATION" in pos.printed and "bits per slot" in pos.printed, pos.printed)
neg_a = co({"F-OQ": arm("F-OQ", C.CAPACITY_NOT_SUPPORTED), "T-OQ": arm("T-OQ", C.CAPACITY_NOT_SUPPORTED)})
check("CAPACITY-NEGATIVE (a)", neg_a.label == C.CAPACITY_NEGATIVE and "(a)" in neg_a.printed and C.NOT_TESTED_16K_65K in neg_a.printed)
neg_b = co({"F-OQ": arm("F-OQ", C.CAPACITY_SUPPORTED, dsat=C.DENSE_HOLDS_MORE), "T-OQ": arm("T-OQ", C.INTERMEDIATE)})
check("DENSE HOLDS MORE AT SATURATION -> CAPACITY-NEGATIVE (b)", neg_b.label == C.CAPACITY_NEGATIVE and "DENSE" in neg_b.printed)
nt = co({"F-OQ": arm("F-OQ", C.NOT_TESTED_BY_LOAD), "T-OQ": arm("T-OQ", C.NOT_TESTED_BY_LOAD)}, every_step_not_loaded=True)
check("CAPACITY NOT TESTED", nt.label == C.CAPACITY_NOT_TESTED and C.NOT_TESTED_16K_65K in nt.printed)
inc = co({"F-OQ": arm("F-OQ", C.DEPENDENCE_FAILED), "T-OQ": arm("T-OQ", C.CAPACITY_NOT_SUPPORTED)})
check("F-OQ DEPENDENCE_FAILED + T-OQ NOT_SUPPORTED -> INCONCLUSIVE, never NEGATIVE", inc.label == C.CAPACITY_INCONCLUSIVE)
# NULL path: NULL in 4 of 5 -> NO GAIN in each transition -> CAPACITY_NOT_SUPPORTED
cls_null = C.capacity_step_class([C.NULL] * 4 + [C.UNRESOLVED])
arm_null = C.capacity_arm_class({"C1": cls_null, "N1": C.NOT_LOADED, "C2": cls_null, "N2": C.NOT_LOADED}, {"1K→4K": ["C1", "N1"], "4K→16K": ["C2", "N2"]}, True)
check("NULL x4 -> NO GAIN -> CAPACITY_NOT_SUPPORTED (null reachable)", cls_null == C.NO_GAIN and arm_null == C.CAPACITY_NOT_SUPPORTED, (cls_null, arm_null))

work = {"T-OQ": C.SUBLINEAR, "F-OQ-IVF": C.SUBLINEAR, "F-OQ": C.LINEAR_KEY_SCORING}


def mr(toq):
    arms = {"F-OQ": arm("F-OQ", C.CAPACITY_SUPPORTED), "T-OQ": toq, "F-OQ-IVF": arm("F-OQ-IVF", C.INTERMEDIATE)}
    o = co(arms)
    return o.label, C.milestone_reading(o, arms, work, C.TREE_COMPETITIVE, "S0 NOT YET DECIDED")


lab, txt = mr(arm("T-OQ", C.CAPACITY_SUPPORTED))
check("storage half supported (all conditions)", txt.startswith("Storage half supported") and core.STORE_ONLY_TAG in txt and C.NOT_TESTED_16K_65K in txt, txt[:120])
lab, txt = mr(arm("T-OQ", C.CAPACITY_SUPPORTED, sat=C.INTERMEDIATE))
check("refused without the saturation class -> 'Capacity steps shown; proportional saturation not shown'", txt.startswith("Capacity steps shown; proportional saturation not shown"), txt[:80])
lab, txt = mr(arm("T-OQ", C.CAPACITY_SUPPORTED, dsat=C.DENSE_HOLDS_MORE))
check("refused with DENSE HOLDS MORE AT SATURATION", not txt.startswith("Storage half"), txt[:80])
lab, txt = mr(arm("T-OQ", C.CAPACITY_SUPPORTED, dense=C.DENSE_NOT_ESTABLISHED + " (MC-SHORT)"))
check("refused with the dense matched-compute reading not established", not txt.startswith("Storage half"), txt[:80])
lab1, txt1 = mr(arm("T-OQ", C.CAPACITY_SUPPORTED, dsat=C.SAME_AT_SATURATION, sub=[C.DENSE_NOT_ESTABLISHED]))
lab2, txt2 = mr(arm("T-OQ", C.CAPACITY_SUPPORTED, dsat=C.SAME_AT_SATURATION, sub=[]))
out.append(f"     milestone, saturation cost condition failing with the ratio holding (sub-label printed): {txt1[:70]!r}")
out.append(f"     milestone, saturation cost condition failing with the ratio also failing (no sub-label):  {txt2[:70]!r}")
check("milestone reading is monotone in the store's saturation ratio (a store that holds MORE is not refused where one that holds the SAME is admitted)", not (txt2.startswith("Storage half") and not txt1.startswith("Storage half")))

# ---------------- J. random cross-check of the capacity panel (rows 1-10 of 8.2) ----------------
def my_capacity(sm, lg, mcu, ref, leak):
    s_i = {u: my_i(o.useful, o.n) for u, o in sm.items()}
    l_i = {u: my_i(o.useful, o.n) for u, o in lg.items()}
    run_s, run_l, up = max(sm), max(lg), 8192
    if not ref or leak:
        return C.NOT_EVALUATED

    def dep(o):
        if o.useful / o.n < 0.25 - EPS:
            return True
        return CH[o.n][0] <= o.disabled <= CH[o.n][1] and CH[o.n][0] <= o.shuffled <= CH[o.n][1] and o.useful / o.n >= 0.95 * o.correct / o.n - EPS

    if not all(dep(o) for o in sm.values()) or not all(dep(o) for o in lg.values()):
        return C.DEPENDENCE_FAILED
    dmu = l_i[up] - s_i[up]
    dsat = l_i[up] - istar(s_i, run_s)
    dfull = istar(l_i, run_l) - istar(s_i, run_s)
    dmc = l_i[mcu[1]] - s_i[mcu[0]]
    loaded = my_loaded(s_i, run_s)
    if s_i[up] >= 4.5 - EPS:
        return C.CEILING
    if dmu >= .5 - EPS and dmc >= .5 - EPS and dsat >= .5 - EPS and loaded and dsat - 2 * (istar(s_i, run_s) - istar(s_i, run_s // 2)) >= .5 - EPS and lg[up].useful / lg[up].n >= .5 - EPS:
        return C.CAPACITY
    if dmu >= .5 - EPS:
        return C.GAIN_ONLY
    if dmu <= -.5 + EPS and dfull <= -.5 + EPS:
        return C.REVERSED
    if dmu <= -.5 + EPS:
        return C.BEHIND
    if abs(dmu) < .25 - EPS and abs(dfull) < .25 - EPS and my_plateaued(s_i, run_s) and my_plateaued(l_i, run_l):
        return C.NULL if loaded else C.FLAT_NOT_LOADED
    return C.UNRESOLVED


rng = random.Random(921777)
counts = {}
mism = 0
for t in range(4000):
    us = [512, 1024, 2048, 4096, 8192, 16384, 24576, 32768, 49152]
    n = 8192

    def series(level, rise):
        a, o = 0.0, {}
        for u in us:
            a = min(1.0, max(a, level * (1 - math.exp(-u / rise)) + rng.uniform(-0.01, 0.01)))
            useful = int(round(a * n))
            corr = min(n, useful + (rng.randint(0, 40) if rng.random() < 0.97 else rng.randint(400, 900)))
            dis = n // 32 if rng.random() < 0.995 else n // 2
            o[u] = C.PanelObs(n=n, correct=corr, useful=useful, disabled=dis, shuffled=n // 32)
        return o

    sm = series(rng.choice([0.3, 0.5, 0.6, 0.7, 0.9, 0.97]), rng.choice([500, 2000, 8000, 30000]))
    lg = series(rng.choice([0.3, 0.6, 0.8, 0.95, 0.99, 1.0]), rng.choice([500, 2000, 8000, 30000]))
    ref, leak = rng.random() > 0.03, rng.random() < 0.02
    mcu = (rng.choice([8192, 16384, 24576]), 8192)
    entry = C.McEntry("OK", mcu[0], mcu[1], 2.0, "small")
    code = C.capacity_panel(C.View(sm, max(sm), 8192), C.View(lg, max(lg), 8192), entry, ref_ok=ref, leakage=leak).verdict
    mine = my_capacity(sm, lg, mcu, ref, leak)
    counts[mine] = counts.get(mine, 0) + 1
    if mine != code:
        mism += 1
check(f"capacity panel: 4,000 random series, my rows 1-10 vs code (verdicts reached {dict(sorted(counts.items()))})", mism == 0, mism)

print("\n".join(out))
print(f"\n{len(fails)} FAIL: {fails}")
