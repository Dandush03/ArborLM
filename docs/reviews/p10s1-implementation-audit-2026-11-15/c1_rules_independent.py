"""Auditor's independent implementation of ADR-0021 rev 4 sections 7.1 and 8.2-8.8, written from the ADR text, compared with
studies/p10s1/classes.py on synthetic inputs that cover every row. Nothing here imports the implementer's helpers for the
computation itself (no core.bits_per_fact, no core.chance_interval); studies.p10s1.classes/core are imported ONLY as the objects
under test.

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c1_rules_independent.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import itertools
import json
import math
import random
import sys
from collections import Counter

from studies.p10s1 import classes as C  # object under test
from studies.p10s1 import core as K  # object under test

OUT = {}


# ---------------------------------------------------------------- 7.1 information of a count (own code)
def log_pmf(k, n, p):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def my_interval(n, tests=40, alpha_total=0.001, p=1 / 32):
    """Exact binomial central interval of level 1 - alpha_total/tests: smallest lo with P(X<lo) <= a/2 maximal..., i.e.
    lo = smallest k with P(X <= k) > a/2 ; hi = smallest k with P(X <= k) >= 1 - a/2."""
    a = alpha_total / tests
    cdf = 0.0
    lo = hi = None
    for k in range(n + 1):
        cdf += math.exp(log_pmf(k, n, p))
        if lo is None and cdf > a / 2:
            lo = k
        if hi is None and cdf >= 1 - a / 2:
            hi = k
            break
    return lo, hi


def fano(a):
    e = 1.0 - a
    h2 = 0.0 if e in (0.0, 1.0) else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h2 - e * math.log2(31)


_IV = {}


def iv(n):
    if n not in _IV:
        _IV[n] = my_interval(n)
    return _IV[n]


def my_i(useful, n):
    if n <= 0:
        return 0.0
    if useful <= iv(n)[1]:
        return 0.0
    return fano(useful / n)


def my_chance(c, n):
    lo, hi = iv(n)
    return lo <= c <= hi


# ---------------------------------------------------------------- an observation is a dict of counts
def obs(n, useful, correct, disabled, shuffled, unseen_n=2048, unseen_c=None):
    return dict(n=n, useful=useful, correct=correct, disabled=disabled, shuffled=shuffled, unseen_n=unseen_n, unseen_c=unseen_c if unseen_c is not None else 64)


def my_dep(o, memory=True):
    if not memory:
        return None
    a = o["useful"] / o["n"]
    if a < 0.25:
        return None
    ok = my_chance(o["disabled"], o["n"]) and (o["shuffled"] is None or my_chance(o["shuffled"], o["n"]))
    return ok and a >= 0.95 * (o["correct"] / o["n"]) - 1e-12


def my_leak(o):
    return o["unseen_n"] > 0 and not my_chance(o["unseen_c"], o["unseen_n"])


class Series:
    def __init__(self, obs_by_u, run, u_p):
        self.o, self.run, self.u_p = obs_by_u, run, u_p

    def i(self, u):
        o = self.o[u]
        return my_i(o["useful"], o["n"])

    def a(self, u):
        o = self.o[u]
        return o["useful"] / o["n"]

    def istar(self, lim):
        us = [u for u in self.o if u <= lim]
        best = max(self.i(u) for u in us)
        at = min(u for u in us if self.i(u) == best)
        return best, at


# ---------------------------------------------------------------- 8.2 capacity verdict, one panel (own code, ADR text)
def my_capacity_panel(S, L, mc, ref_ok, leak):
    """mc: None (MC-SHORT/AMBIGUOUS) or (u_small, u_large)."""
    if not ref_ok or leak:
        return "NOT_EVALUATED"
    up = S.u_p
    iS_run, aS_run = S.istar(S.run)
    iS_half, aS_half = S.istar(S.run // 2)
    iL_run, aL_run = L.istar(L.run)
    iL_half, aL_half = L.istar(L.run // 2)
    reads_S = {up, aS_run, aS_half} | ({mc[0]} if mc else set())
    reads_L = {up, aL_run, aL_half} | ({mc[1]} if mc else set())
    if any(my_dep(S.o[u]) is False for u in reads_S) or any(my_dep(L.o[u]) is False for u in reads_L):
        return "DEPENDENCE_FAILED"
    d_mu = L.i(up) - S.i(up)
    d_mc = (L.i(mc[1]) - S.i(mc[0])) if mc else None
    d_sat = L.i(up) - iS_run
    d_full = iL_run - iS_run
    plat_S = iS_run - iS_half <= 0.10 + 1e-12
    plat_L = iL_run - iL_half <= 0.10 + 1e-12
    loaded = plat_S and iS_run <= 4.0 + 1e-12
    g = 0.5 - 1e-12
    if S.i(up) >= 4.5 - 1e-12:
        return "CEILING"
    if d_mu >= g and d_mc is not None and d_mc >= g and d_sat >= g and loaded and d_sat - 2 * (iS_run - iS_half) >= g and L.a(up) >= 0.5 - 1e-12:
        return "CAPACITY"
    if d_mu >= g:
        return "GAIN WITHIN BUDGET ONLY"
    if d_mu <= -g and d_full <= -g:
        return "REVERSED"
    if d_mu <= -g:
        return "BEHIND WITHIN BUDGET"
    if abs(d_mu) < 0.25 - 1e-12 and abs(d_full) < 0.25 - 1e-12 and plat_S and plat_L:
        return "NULL" if loaded else "FLAT, NOT LOADED"
    return "UNRESOLVED"


def my_step_class(v):
    c = Counter(v)
    if c["NOT_EVALUATED"] >= 2:
        return "NOT_EVALUATED"
    if c["DEPENDENCE_FAILED"] >= 2:
        return "DEPENDENCE_FAILED"
    if c["PANEL-DISAGREE"] >= 2:
        return "NOT REPLICATED"
    if c["CAPACITY"] == 5:
        return "CAPACITY STEP"
    if c["CAPACITY"] + c["GAIN WITHIN BUDGET ONLY"] == 5:
        return "GAIN WITHIN BUDGET"
    if c["CEILING"] + c["FLAT, NOT LOADED"] >= 4:
        return "NOT LOADED"
    if c["REVERSED"] >= 4:
        return "REVERSED"
    if c["NULL"] + c["REVERSED"] >= 4:
        return "NO GAIN"
    return "MIXED"


def my_arm_class(steps, trans, a80):
    per = {t: [steps[s] for s in ss] for t, ss in trans.items()}
    if any(all(x == "NOT_EVALUATED" for x in xs) for xs in per.values()):
        return "NOT_EVALUATED"
    if "DEPENDENCE_FAILED" in steps.values():
        return "DEPENDENCE_FAILED"
    has = {t: "CAPACITY STEP" in xs for t, xs in per.items()}
    if all(has.values()) and "REVERSED" not in steps.values() and a80:
        return "CAPACITY_SUPPORTED"
    if any(has.values()):
        return "CAPACITY_ONE_TRANSITION"
    if any(all(x == "NOT LOADED" for x in xs) for xs in per.values()):
        return "NOT_TESTED_BY_LOAD"
    if all(any(x in ("NO GAIN", "REVERSED") for x in xs) for xs in per.values()):
        return "CAPACITY_NOT_SUPPORTED"
    return "INTERMEDIATE"


def my_outcome(arms, eng, inc, directed=False):
    """arms: name -> (class, dense) for F-OQ, F-OQ-IVF, T-OQ (dense in AHEAD/BEATS/MATCHES/NOT READ)."""
    if eng:
        return "S1-ENGINEERING-FAILURE"
    if inc:
        return "S1-INCOMPLETE"
    sup = [a for a in ("F-OQ", "T-OQ", "F-OQ-IVF") if arms[a][0] == "CAPACITY_SUPPORTED"]
    if any(arms[a][1] not in ("DENSE AHEAD", "DENSE NOT READ") for a in sup):
        return "CAPACITY-POSITIVE"
    if arms["F-OQ"][0] == "CAPACITY_NOT_SUPPORTED" and arms["T-OQ"][0] == "CAPACITY_NOT_SUPPORTED":
        return "CAPACITY-NEGATIVE"
    if sup and all(arms[a][1] == "DENSE AHEAD" for a in sup):
        return "CAPACITY-NEGATIVE"
    if directed:
        return "CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET"
    return "CAPACITY-INCONCLUSIVE"


# ---------------------------------------------------------------- generators
N = 8192
LO, HI = iv(N)


def count_for(a):
    return max(0, min(N, round(a * N)))


def rand_obs(rng, a, dep_fail_p=0.05):
    u = count_for(a)
    correct = u if rng.random() > 0.05 else min(N, u + rng.randint(0, N // 8))
    dis = rng.randint(LO, HI) if rng.random() > dep_fail_p else rng.choice([0, HI + 1 + rng.randint(0, 500)])
    sh = rng.randint(LO, HI) if rng.random() > dep_fail_p else HI + 1 + rng.randint(0, 500)
    return obs(N, u, correct, dis, sh)


def rand_series(rng, u_p, run, mode):
    marks = sorted({int(u_p * f) for f in (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1, 2, 4) if u_p * f <= run} | {run // 2, run} | {int(u_p * m) for m in (1.25, 1.5, 2.5, 3, 6) if u_p * m <= run})
    # mode: shape of the curve
    top = {"low": rng.uniform(0.03, 0.5), "mid": rng.uniform(0.5, 0.9), "high": rng.uniform(0.85, 1.0), "any": rng.uniform(0.0, 1.0)}[mode]
    k = rng.uniform(0.3, 3.0)
    out = {}
    for m in marks:
        a = top * (1 - math.exp(-k * m / u_p * (1 + rng.uniform(-0.2, 0.2))))
        if rng.random() < 0.1:
            a = top  # plateau
        if rng.random() < 0.05:
            a *= rng.uniform(0.5, 1.0)  # dip
        out[m] = rand_obs(rng, max(0.0, min(1.0, a)))
    return out


def to_view(series, run, u_p):
    d = {u: C.PanelObs(n=o["n"], correct=o["correct"], useful=o["useful"], disabled=o["disabled"], shuffled=o["shuffled"], unseen_n=o["unseen_n"], unseen_correct=o["unseen_c"]) for u, o in series.items()}
    return C.View(d, run, u_p)


def compare_capacity(trials=60000, seed=921501):
    rng = random.Random(seed)
    u_p = 8192
    mism = []
    cov = Counter()
    for t in range(trials):
        run_s, run_l = rng.choice([(6 * u_p, 4 * u_p), (4 * u_p, 2 * u_p)])
        s = rand_series(rng, u_p, run_s, rng.choice(["low", "mid", "high", "any"]))
        l_ = rand_series(rng, u_p, run_l, rng.choice(["low", "mid", "high", "any"]))
        mc_ok = rng.random() < 0.85
        mc_u = rng.choice([u for u in s if u >= u_p]) if mc_ok else None
        mc = (mc_u, u_p) if mc_ok else None
        ref = rng.random() > 0.03
        leak = rng.random() < 0.02
        mine = my_capacity_panel(Series(s, run_s, u_p), Series(l_, run_l, u_p), mc, ref, leak)
        entry = C.McEntry("OK", mc_u, u_p, 1.5, "small") if mc_ok else C.McEntry(C.MC_SHORT, None, None, 9.0, None)
        theirs = C.capacity_panel(to_view(s, run_s, u_p), to_view(l_, run_l, u_p), entry, ref_ok=ref, leakage=leak).verdict
        cov[mine] += 1
        if mine != theirs:
            mism.append((t, mine, theirs))
    return {"trials": trials, "mismatches": len(mism), "first_mismatches": mism[:10], "coverage": dict(cov)}


def compare_step_class():
    names = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "PANEL-DISAGREE", "CAPACITY", "GAIN WITHIN BUDGET ONLY", "CEILING", "FLAT, NOT LOADED", "REVERSED", "NULL", "BEHIND WITHIN BUDGET", "UNRESOLVED"]
    mism = 0
    cov = Counter()
    for combo in itertools.combinations_with_replacement(names, 5):
        m, t = my_step_class(list(combo)), C.capacity_step_class(list(combo))
        cov[m] += 1
        mism += m != t
    return {"multisets": sum(cov.values()), "mismatches": mism, "coverage": dict(cov)}


def compare_arm_class():
    cls = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "NOT REPLICATED", "CAPACITY STEP", "GAIN WITHIN BUDGET", "NOT LOADED", "REVERSED", "NO GAIN", "MIXED"]
    trans = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}
    mism = 0
    cov = Counter()
    for combo in itertools.product(cls, repeat=4):
        steps = dict(zip(["A1", "B1", "A2", "B2"], combo, strict=True))
        for a80 in (True, False):
            m, t = my_arm_class(steps, trans, a80), C.capacity_arm_class(steps, trans, a80)
            cov[m] += 1
            mism += m != t
    return {"cases": sum(cov.values()), "mismatches": mism, "coverage": dict(cov)}


def compare_outcome():
    classes = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "CAPACITY_SUPPORTED", "CAPACITY_ONE_TRANSITION", "NOT_TESTED_BY_LOAD", "CAPACITY_NOT_SUPPORTED", "INTERMEDIATE"]
    dense = ["DENSE AHEAD", "BEATS DENSE", "DENSE MATCHES", "DENSE NOT READ"]
    mism = []
    cov = Counter()
    neg_wrong = []
    for cf, ct, ci in itertools.product(classes, repeat=3):
        for df, dt, di in itertools.product(dense, repeat=3):
            arms = {"F-OQ": (cf, df), "T-OQ": (ct, dt), "F-OQ-IVF": (ci, di)}
            for eng, inc in ((False, False), (True, False), (False, True)):
                m = my_outcome(arms, eng, inc)
                theirs = C.capacity_outcome({a: C.ArmCapacity(a, c, d) for a, (c, d) in arms.items()}, engineering_failed=eng, incomplete=inc).label
                cov[m] += 1
                if m != theirs:
                    mism.append((arms, eng, inc, m, theirs))
                # 10.2 requirement: no arm SUPPORTED and arms in NOT_EVALUATED/DEP/NTBL/ONE/INTERMEDIATE never NEGATIVE
                if not eng and not inc and all(x[0] in ("NOT_EVALUATED", "DEPENDENCE_FAILED", "NOT_TESTED_BY_LOAD", "CAPACITY_ONE_TRANSITION", "INTERMEDIATE") for x in arms.values()) and theirs == C.CAPACITY_NEGATIVE:
                    neg_wrong.append(arms)
    return {"cases": sum(cov.values()), "mismatches": len(mism), "first": [str(x) for x in mism[:5]], "coverage": dict(cov), "negative_on_unevaluated": len(neg_wrong)}


# ---------------------------------------------------------------- 8.8 efficiency (own code)
def my_ut(views):
    """views: list of Series (panels). Returns (kind, lo, hi, dep_failed)."""
    ups = sorted(set.intersection(*(set(v.o) for v in views)))
    for k, s in enumerate(ups):
        if all(v.i(s) >= 3.0 - 1e-12 for v in views):
            if any(my_dep(v.o[s]) is False for v in views):
                return ("dep", None, None, True)
            if k == 0:
                return ("left", 0.0, float(s), False)
            p = ups[k - 1]
            y0, y1 = min(v.i(p) for v in views), min(v.i(s) for v in views)
            x0, x1 = math.log2(p), math.log2(s)
            x = x0 + (3.0 - y0) / (y1 - y0) * (x1 - x0)
            return ("exact", 2**x, 2**x, False)
    return ("right", float(views[0].run), math.inf, False)


def my_eff_step(us, ul, ref_ok, leak, run_s, run_l, cs, cl):
    """us/ul: (kind, lo, hi, dep). cs/cl: {'cpu','madds'} cost per update."""
    if not ref_ok or leak:
        return "NOT_EVALUATED"
    if us[3] or ul[3]:
        return "DEPENDENCE_FAILED"
    ks, ls, hs = us[0], us[1], us[2]
    kl, ll, hl = ul[0], ul[1], ul[2]
    m = ("cpu", "madds")
    # each condition 'for every value the bounds allow' (worst case)
    r4 = ks == "right" and hl <= run_s / 2 + 1e-9 and all(hl * cl[x] <= 0.8 * run_s * cs[x] + 1e-12 for x in m)
    # u_T(4N) <= u_T(N)/2 for all values: sup(4N) <= inf(N)/2 ; for right-censored small inf is run_s (exclusive)
    half_u = hl <= ls / 2 + 1e-9
    half_c = all(hl * cl[x] <= 0.8 * ls * cs[x] + 1e-12 for x in m)
    r5 = half_u and half_c
    r6 = half_u
    r7 = math.isfinite(hs) and ll >= 2 * hs - 1e-9 and (kl != "right" or run_l >= 2 * hs - 1e-9)
    cens = ks != "exact" or kl != "exact"
    if (ks == "right" and kl == "right") or (cens and not (r4 or r5 or r6 or r7)):
        return "NOT_ASSESSED"
    if r4:
        return "REACHED ONLY BY THE LARGER"
    if r5:
        return "FASTER"
    if r6:
        return "FASTER IN UPDATES ONLY"
    if r7:
        return "SLOWER"
    return "SAME"


def compare_efficiency(trials=40000, seed=921502):
    rng = random.Random(seed)
    u_p = 8192
    mism_ut = 0
    mism = []
    cov = Counter()
    for _ in range(trials):
        run_s, run_l = rng.choice([(6 * u_p, 4 * u_p), (4 * u_p, 2 * u_p)])
        ss = [rand_series(rng, u_p, run_s, rng.choice(["low", "mid", "high", "any"])) for _ in range(2)]
        sl = [rand_series(rng, u_p, run_l, rng.choice(["low", "mid", "high", "any"])) for _ in range(2)]
        my_s = my_ut([Series(x, run_s, u_p) for x in ss])
        my_l = my_ut([Series(x, run_l, u_p) for x in sl])
        th_s = C.u_t([to_view(x, run_s, u_p) for x in ss])
        th_l = C.u_t([to_view(x, run_l, u_p) for x in sl])
        for mine, th in ((my_s, th_s), (my_l, th_l)):
            if mine[3] != th.dep_failed:
                mism_ut += 1
            elif not mine[3] and (mine[0] != th.ut.kind or not math.isclose(mine[1], th.ut.lo, rel_tol=1e-9, abs_tol=1e-9) or not (mine[2] == th.ut.hi or math.isclose(mine[2], th.ut.hi, rel_tol=1e-9))):
                mism_ut += 1
        cs = {"cpu": rng.uniform(0.005, 0.02), "madds": rng.uniform(1e6, 3e6)}
        cl = {"cpu": cs["cpu"] * rng.uniform(0.8, 5.0), "madds": cs["madds"] * rng.uniform(0.9, 5.0)}
        ref, leak = rng.random() > 0.02, rng.random() < 0.01
        if my_s[3] or my_l[3]:
            m = my_eff_step(("x", 0, 0, my_s[3]), ("x", 0, 0, my_l[3]), ref, leak, run_s, run_l, cs, cl)
        else:
            m = my_eff_step(my_s, my_l, ref, leak, run_s, run_l, cs, cl)
        t = C.efficiency_step(th_s, th_l, ref_ok=ref, leakage=leak, run_small=run_s, run_large=run_l, cost_small=cs, cost_large=cl).verdict
        cov[m] += 1
        if m != t:
            mism.append((m, t, my_s, my_l))
    # direct UT grid to reach every verdict row
    grid = Counter()
    gmis = []
    kinds = []
    for kind in ("exact", "left", "right"):
        for v in (512, 1024, 2048, 4096, 8192, 12000, 16384, 24576, 32768, 49152):
            if kind == "exact":
                kinds.append((kind, float(v), float(v)))
            elif kind == "left":
                kinds.append((kind, 0.0, float(v)))
    for run_s, run_l in ((49152, 32768), (32768, 16384)):
        rs = ("right", float(run_s), math.inf)
        rl = ("right", float(run_l), math.inf)
        for a, b in itertools.product(kinds + [rs], kinds + [rl]):
            for cfac in (0.5, 1.0, 3.0):
                cs = {"cpu": 0.01, "madds": 1e6}
                cl = {"cpu": 0.01 * cfac, "madds": 1e6 * cfac}
                m = my_eff_step((*a, False), (*b, False), True, False, run_s, run_l, cs, cl)
                t = C.efficiency_step(C.UTResult(C.UT(*a), False, None, None), C.UTResult(C.UT(*b), False, None, None), ref_ok=True, leakage=False, run_small=run_s, run_large=run_l, cost_small=cs, cost_large=cl).verdict
                grid[m] += 1
                if m != t:
                    gmis.append((a, b, cfac, m, t))
    return {"trials": trials, "u_t_mismatches": mism_ut, "verdict_mismatches": len(mism), "first": [str(x) for x in mism[:5]], "coverage_random": dict(cov), "grid_cases": sum(grid.values()), "grid_mismatches": len(gmis), "grid_first": [str(x) for x in gmis[:5]], "grid_coverage": dict(grid)}


def my_eff_step_class(v):
    c = Counter(v)
    if c["NOT_EVALUATED"] >= 2:
        return "NOT_EVALUATED"
    if c["DEPENDENCE_FAILED"] >= 2:
        return "DEPENDENCE_FAILED"
    if c["NOT_ASSESSED"] >= 2:
        return "NOT_ASSESSED"
    if c["FASTER"] + c["REACHED ONLY BY THE LARGER"] == 5:
        return "FASTER STEP"
    if c["FASTER"] + c["FASTER IN UPDATES ONLY"] == 5:
        return "UPDATES-ONLY STEP"
    if c["SLOWER"] >= 4:
        return "SLOWER STEP"
    if c["SAME"] >= 4:
        return "NO DIFFERENCE"
    return "MIXED"


def my_eff_arm(steps, trans):
    per = {t: [steps[s] for s in ss] for t, ss in trans.items()}
    if any(all(x in ("NOT_EVALUATED", "NOT_ASSESSED") for x in xs) for xs in per.values()):
        return "NOT_EVALUATED"
    if "DEPENDENCE_FAILED" in steps.values():
        return "DEPENDENCE_FAILED"
    f = {t: "FASTER STEP" in xs for t, xs in per.items()}
    if all(f.values()) and "SLOWER STEP" not in steps.values():
        return "EFFICIENCY_SUPPORTED"
    if any(f.values()):
        return "EFFICIENCY_ONE_TRANSITION"
    if all(any(x in ("SLOWER STEP", "NO DIFFERENCE") for x in xs) for xs in per.values()):
        return "EFFICIENCY_NOT_SUPPORTED"
    return "INTERMEDIATE"


def my_eff_outcome(cls, dense):
    sup = [a for a in ("F-OQ", "T-OQ") if cls[a] == "EFFICIENCY_SUPPORTED"]
    if any(dense[a] != "DENSE FASTER" for a in sup):
        return "EFFICIENCY-POSITIVE"
    if all(cls[a] == "EFFICIENCY_NOT_SUPPORTED" for a in ("F-OQ", "T-OQ")):
        return "EFFICIENCY-NEGATIVE"
    if sup and all(dense[a] == "DENSE FASTER" for a in sup):
        return "EFFICIENCY-NEGATIVE"
    return "EFFICIENCY-INCONCLUSIVE"


def compare_eff_classes():
    names = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "NOT_ASSESSED", "REACHED ONLY BY THE LARGER", "FASTER", "FASTER IN UPDATES ONLY", "SLOWER", "SAME"]
    m1 = sum(my_eff_step_class(list(c)) != C.efficiency_step_class(list(c)) for c in itertools.combinations_with_replacement(names, 5))
    cl = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "NOT_ASSESSED", "FASTER STEP", "UPDATES-ONLY STEP", "SLOWER STEP", "NO DIFFERENCE", "MIXED"]
    trans = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}
    m2 = 0
    cov = Counter()
    for combo in itertools.product(cl, repeat=4):
        steps = dict(zip(["A1", "B1", "A2", "B2"], combo, strict=True))
        a, b = my_eff_arm(steps, trans), C.efficiency_arm_class(steps, trans)
        cov[a] += 1
        m2 += a != b
    arms = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "EFFICIENCY_SUPPORTED", "EFFICIENCY_ONE_TRANSITION", "EFFICIENCY_NOT_SUPPORTED", "INTERMEDIATE"]
    dense = ["DENSE FASTER", "DENSE NOT FASTER", "DENSE NOT READ"]
    m3 = 0
    cov3 = Counter()
    for cf, ct, df, dt in itertools.product(arms, arms, dense, dense):
        cls, d = {"F-OQ": cf, "T-OQ": ct}, {"F-OQ": df, "T-OQ": dt}
        a = my_eff_outcome(cls, d)
        b = C.efficiency_outcome(cls, d, engineering_failed=False, incomplete=False).label
        cov3[a] += 1
        m3 += a != b
    return {"step_class_mismatches": m1, "arm_class_mismatches": m2, "arm_coverage": dict(cov), "outcome_mismatches": m3, "outcome_coverage": dict(cov3)}


# ---------------------------------------------------------------- 8.5 dense label (own code)
def my_dense(cells):
    """cells: list of reps; rep: reading -> panel -> (d, r). r None = zero denominator. ADR: DENSE AHEAD d<=-0.25 in >=4 reps in any reading
    at any cell (panel rule: auditor's variants); BEATS: r>=1.10 all 5, MU and MC, both panels, every cell."""
    out = {}
    for rule in ("both", "either", "per-panel"):
        ahead = False
        for reps in cells:
            for rd in ("MU", "MC", "D-BEST"):
                if rule == "both":
                    n = sum(all(rep[rd][p][0] <= -0.25 + 1e-12 for p in "AB") for rep in reps)
                elif rule == "either":
                    n = sum(any(rep[rd][p][0] <= -0.25 + 1e-12 for p in "AB") for rep in reps)
                else:
                    n = max(sum(rep[rd][p][0] <= -0.25 + 1e-12 for rep in reps) for p in "AB")
                ahead = ahead or n >= 4
        beats = all((rep[rd][p][1] is None or rep[rd][p][1] >= 1.10 - 1e-12) for reps in cells for rep in reps for rd in ("MU", "MC") for p in "AB")
        out[rule] = "DENSE AHEAD" if ahead else ("BEATS DENSE" if beats else "DENSE MATCHES")
    return out


def compare_dense(trials=20000, seed=921503):
    rng = random.Random(seed)
    mism = 0
    differs = Counter()
    for _ in range(trials):
        ncell = rng.choice([1, 2])
        cells = []
        for _c in range(ncell):
            reps = []
            for _r in range(5):
                rep = {}
                for rd in ("MU", "MC", "D-BEST"):
                    rep[rd] = {}
                    for p in "AB":
                        d = rng.choice([rng.uniform(-1, 1), -0.25, -0.26, -0.24])
                        r = None if rng.random() < 0.03 else rng.choice([rng.uniform(0.8, 1.5), 1.10, 1.09])
                        rep[rd][p] = (d, r, 0.5)
                reps.append(rep)
            cells.append(reps)
        mine = my_dense([c for c in cells])
        theirs = C.dense_label([C.DenseCell(f"S{k}", c) for k, c in enumerate(cells)])["label"]
        theirs = "BEATS DENSE" if theirs.startswith("BEATS DENSE") else theirs
        mism += mine["both"] != theirs
        for rule in ("either", "per-panel"):
            if mine[rule] != mine["both"]:
                differs[f"{rule} vs both: {mine['both']} -> {mine[rule]}"] += 1
    return {"trials": trials, "mismatches_vs_both_panels_reading": mism, "cases_where_other_panel_readings_differ": dict(differs)}


# ---------------------------------------------------------------- study B ratio (section 8.6): I_use = F * i
def study_b_case():
    a = 0.99
    i = fano(a)
    steps = [(a, a, i, i), (a, a, i, i)]
    rep = {"MU": {"A": steps, "B": steps}, "MC": {"A": steps, "B": steps}}
    theirs = C.study_b_label([rep] * 5, True, [True, True])
    # own: I_use(8K/16K)/I_use(2K/4K) = 8192*i / (2048*i) = 4 >= 3 ; same for 32768/8192
    mine = "KNOWLEDGE SCALES WITH MEMORY" if (8192 * i) / (2048 * i) >= 3 and (32768 * i) / (8192 * i) >= 3 and a >= 0.85 else "NOT ESTABLISHED"
    # the most i ratio reachable with a_use>=0.85 at both cells
    best = fano(1.0) / fano(0.85)
    return {"a_use_everywhere": a, "i": i, "I_use_ratio_per_diagonal_step": 4.0, "auditor": mine, "implementation": theirs["label"], "max_i_ratio_reachable_with_floor_0_85": best}


def main():
    OUT["chance_intervals_own"] = {n: iv(n) for n in (2048, 8192, 32768, 65536)}
    OUT["chance_intervals_impl"] = {n: (K.chance_interval(n).low, K.chance_interval(n).high) for n in (2048, 8192, 32768, 65536)}
    OUT["fano_checkpoints_own"] = {a: round(fano(a), 3) for a in (0.5, 0.758, 0.8, 0.896, 0.9, 0.95, 0.954, 0.958, 0.974)}
    OUT["bits_mismatch_count"] = sum(abs(my_i(u, n) - K.bits_per_fact(u, n)) > 1e-12 for n in (2048, 8192, 32768) for u in range(0, n + 1, 7))
    OUT["capacity_panel"] = compare_capacity()
    OUT["step_class"] = compare_step_class()
    OUT["arm_class"] = compare_arm_class()
    OUT["outcome"] = compare_outcome()
    OUT["efficiency"] = compare_efficiency()
    OUT["efficiency_classes"] = compare_eff_classes()
    OUT["dense_label"] = compare_dense()
    OUT["study_b_ratio"] = study_b_case()
    json.dump(OUT, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
