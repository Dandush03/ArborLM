# ruff: noqa
"""Independent auditor's library for P10-S1 attempt 2 (ADR-0021 rev 5).

Written from the ADR text only. Does not import arborlm or studies.*. Plain python3, stdlib only.
Reads raw records: cells/<label>/train.json and cells/<label>/eval/u*/eval.json, baselines/*.json,
and the frozen plan (for the frozen cost table and the U_P / U_L values, which are frozen inputs).
"""

import functools
import glob
import json
import math
import os

RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117"
PLAN = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/studies/p10s1/freeze/plan.json"

PANELS = ("A", "B")
G2_TESTS = 40
ALPHA = 0.001
P_CHANCE = 1.0 / 32.0
U_P_ROW = {2048: 8192, 8192: 8192, 32768: 16384}  # frozen (plan row_u_p), section 10.1 item 1 / 25.15
U_L = {(8192, 1024): 393216, (32768, 4096): 786432}  # frozen (plan u_l), section 25.15 extended search
REF_CELL = {2048: (2048, 4096), 8192: (8192, 16384), 32768: (32768, 32768)}  # section 8.1 REF
STEPS = {  # section 5.1
    "C1": (8192, 1024, 4096, "1K->4K"),
    "N1": (2048, 1024, 4096, "1K->4K"),
    "C2": (32768, 4096, 16384, "4K->16K"),
    "N2": (8192, 4096, 16384, "4K->16K"),
}
MC_GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)  # section 5.4


# ---------------------------------------------------------------- chance and information (section 7.1, G2)
@functools.lru_cache(maxsize=None)
def chance_interval(n):
    """Exact binomial central interval of level 1 - 0.001/40 around 1/32: equal tail mass 0.001/40/2 each side.
    low = smallest k with P(X<=k) > tail; high = largest k with P(X>=k) > tail."""
    tail = ALPHA / G2_TESTS / 2.0
    lp, lq = math.log(P_CHANCE), math.log1p(-P_CHANCE)
    lg = math.lgamma(n + 1)
    pmf = [math.exp(lg - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq) for k in range(n + 1)]
    c, low = 0.0, None
    for k in range(n + 1):
        c += pmf[k]
        if c > tail:
            low = k
            break
    c, high = 0.0, None
    for k in range(n, -1, -1):
        c += pmf[k]
        if c > tail:
            high = k
            break
    return low, high


def in_chance(correct, n):
    lo, hi = chance_interval(n)
    return lo <= correct <= hi


def fano(a):
    e = 1.0 - a
    h2 = 0.0 if e <= 0.0 or e >= 1.0 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h2 - e * math.log2(31)


def bits(useful, n):
    """i = 5 - h2(e) - e log2 31, e = 1 - a_use; 0 at or below the upper end of the chance interval (section 7.1)."""
    if useful <= chance_interval(n)[1]:
        return 0.0
    return fano(useful / n)


I_FLOOR = fano(0.25)  # 0.473 bits per fact (section 8.2)


# ---------------------------------------------------------------- records
def load_cells(include_ivf=True):
    """{(kind, arm, facts, slots, draw, init): cell} with cell = {'meta':..., 'snap': {u: {panel: rec}}}; F-OQ-IVF is a separate entry."""
    cells = {}
    for d in sorted(glob.glob(os.path.join(RUN, "cells", "*"))):
        t = json.load(open(os.path.join(d, "train.json")))
        evals = {}
        for p in sorted(glob.glob(os.path.join(d, "eval", "u*", "eval.json"))):
            e = json.load(open(p))
            evals[int(e["update"])] = e
        reads = ["main"] + (["ivf"] if t["arm"] == "F-OQ" else [])
        for rd in reads:
            arm = "F-OQ-IVF" if rd == "ivf" else t["arm"]
            snap = {u: {pn: e["reads"][rd]["panels"][pn] for pn in PANELS} for u, e in evals.items() if rd in e["reads"]}
            sec = {u: e["reads"][rd].get("secondary") for u, e in evals.items() if rd in e["reads"]}
            ivfm = {u: e["reads"][rd].get("ivf_measured") or e["reads"][rd].get("work") for u, e in evals.items() if rd in e["reads"]}
            key = (t["kind_of_cell"], arm, t["facts"], t["slots"], t["draw"], t["init_seed"])
            cells[key] = {"label": os.path.basename(d), "meta": t, "snap": snap, "secondary": sec, "work": ivfm, "evals_identity": {u: e.get("identity") for u, e in evals.items()}}
    return cells


def P(cells, arm, facts, slots, draw):
    """The registered (kind P) cell of an arm in a replicate."""
    return cells[("P", arm, facts, slots, draw, 2100 + draw)]


# ---------------------------------------------------------------- per-view quantities
class View:
    def __init__(self, cell, panel, memory=True):
        self.cell, self.panel, self.memory = cell, panel, memory
        self.recs = {u: cell["snap"][u][panel] for u in cell["snap"]}
        self.ups = sorted(self.recs)
        self.run = cell["meta"]["run_updates"]
        self.u_p = cell["meta"]["u_p"]
        self.n = self.recs[self.ups[-1]]["n"]

    def i(self, u):
        r = self.recs[u]
        return bits(r["useful"], r["n"])

    def a_use(self, u):
        r = self.recs[u]
        return r["useful"] / r["n"]

    def acc(self, u):
        r = self.recs[u]
        return r["correct"] / r["n"]

    def i_star(self, limit):
        el = [u for u in self.ups if u <= limit]
        return max(self.i(u) for u in el)

    def gain(self):
        return self.i_star(self.run) - self.i_star(self.run // 2)

    def plateaued(self):
        return self.gain() <= 0.10 and self.i_star(self.run // 2) >= I_FLOOR

    def loaded(self):
        return self.plateaued() and self.i_star(self.run) <= 4.0

    def dep(self, u):
        """None if DEP does not apply (not a memory cell, or a_use < 0.25); else (passes, reasons). Integer arithmetic for the thresholds."""
        r = self.recs[u]
        n = r["n"]
        if not self.memory or 4 * r["useful"] < n:
            return None
        why = []
        lo, hi = chance_interval(n)
        if r.get("disabled_correct") is None or not (lo <= r["disabled_correct"] <= hi):
            why.append(f"disabled {r.get('disabled_correct')} outside [{lo},{hi}]")
        if r.get("shuffled_correct") is not None and not (lo <= r["shuffled_correct"] <= hi):
            why.append(f"shuffled {r['shuffled_correct']} outside [{lo},{hi}]")
        if 20 * r["useful"] < 19 * r["correct"]:
            why.append(f"a_use {r['useful']}/{n}={r['useful']/n:.4f} < 0.95 x raw {r['correct']}/{n}={r['correct']/n:.4f} (ratio {r['useful']/max(1,r['correct']):.4f})")
        return (not why, why)

    def dep_failures(self):
        out = []
        for u in self.ups:
            d = self.dep(u)
            if d is not None and not d[0]:
                out.append((u, d[1]))
        return out

    def leakage(self):
        out = []
        for u in self.ups:
            r = self.recs[u]
            if r.get("unseen_n", 0) > 0 and not in_chance(r["unseen_correct"], r["unseen_n"]):
                out.append((u, r["unseen_correct"], r["unseen_n"]))
        return out


def mc_entry(cost, arm_s, n_s, arm_l, n_l, u_p, run_s, run_l, claim):
    """Section 5.4 MC readout, implemented from the text. Returns (u_small, u_large, mult, annotation) or ('MC-SHORT', ...).
    claim: which role's advantage would be claimed ('large' on the capacity line; 'small' = arm in the dense labels where small=arm, large=D-OQ)."""
    cs, cl = cost[arm_s][str(n_s)], cost[arm_l][str(n_l)]
    r = {m: cl[m] / cs[m] for m in ("cpu", "madds")}
    def snap(mult, cheaper_run):
        for g in MC_GRID:
            if g >= mult:
                u = int(round(u_p * g))
                return u if u <= cheaper_run else None
        return None
    if all(x >= 1.0 for x in r.values()):  # larger role costlier: larger at U_P, smaller at matched snapshot
        m = max(r.values()); u = snap(m, run_s)
        return (u, u_p, m, None)
    if all(x <= 1.0 for x in r.values()):
        m = max(1 / x for x in r.values()); u = snap(m, run_l)
        return (u_p, u, m, None)
    m = max(max(x, 1 / x) for x in r.values())
    if claim == "large":
        u = snap(m, run_s); return (u, u_p, m, "MC-AMBIGUOUS")
    u = snap(m, run_l); return (u_p, u, m, "MC-AMBIGUOUS")


def load_plan():
    return json.load(open(PLAN))
