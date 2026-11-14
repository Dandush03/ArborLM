"""Independent recomputation of the P7-B registered classifications, outcomes, decisions and main
descriptive results from the per-checkpoint simulation records (ADR-0014 sections 2, 4-11, 15).

Auditor role (Claude Opus 5.5). Python standard library only. No ``arborlm`` import and no reuse of
``p7b_analysis.py`` or any implementer summary script; every rule below is written from the ADR text.
The implementation's ``analysis.json`` is read only at the end, to compare against.
Independent engineering/mathematical evidence; not Astra validation; not human approval.

Usage (from the repository root):
    .venv/bin/python -I docs/reviews/p7b-results-audit-2026-11-13/recompute_p7b.py \
        --repo . --out docs/reviews/p7b-results-audit-2026-11-13/recompute_p7b.json

Quantities (my reading of the ADR, stated so a reader can check it):
  m          = (misses_warm - first_touch_warm) / 16384   warm capacity misses per counted query
               (counted half = last 256 contexts x 64 queries).
  E_c(L)     = m(actual, L) / mean_k m(null_k, L-FREQ), same R, C and tie rule.
  S_c(L)     = m(actual, L) / mean_k m(null_k, L).
  G_c(L)     = m(actual, L) / m(actual, L-FREQ).
  pop cost   = mean_k m(null_k, L) / mean_k m(null_k, L-FREQ).
  x          = ln(effective slots) of the stream analysed (record evaluation_counts.effective_slots;
               cross-checked against my own count of the trace files).
  rho        = mean E over 27 tree cells / mean E over 27 flat cells.
  rho_adj    = (a + b xbar + d) / (a + b xbar), OLS of E on [1, x, tree] over the 54 cells, solved
               exactly in rational arithmetic with x = Fraction(float).
Every ratio of counts is computed exactly with fractions.Fraction and converted to float only for
reporting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
import sys
import time
from fractions import Fraction
from pathlib import Path

RUNS = {
    "layouts": "results/p7b-2026-11-13/layouts/P7BL-20261114T013707250613Z-31637f68420b415ebc73f333bb21993b",
    "panel": "results/p7b-2026-11-13/panel/P7BP-20261114T013656010347Z-9433b10446e5458885b6cb83f8d1a915",
    "trace-b": "results/p7b-2026-11-13/trace-b/P7BT-20261114T015044654616Z-c8ecc1e86e434a6b9ec1b76f6b5f23ae",
    "simulate-a": "results/p7b-2026-11-13/simulate-a/P7BSA-20261114T015358875869Z-b5028326a722484bbbb49ec1c8518d57",
    "simulate-b": "results/p7b-2026-11-13/simulate-b/P7BSB-20261114T021416466847Z-5a15dae8e51147ce9a888613aced4527",
    "analyze": "results/p7b-2026-11-13/analyze/P7BA-20261114T024054852573Z-72ade53e0ef74ddf893e0d30f8cd3044",
}
P7A_SIM = "results/p7a-2026-11-13/simulate/P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b/workers"
IDENTITY = "docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json"
TRACE_A_DIR = "experiments/P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e/traces"
TRACE_B_DIR = "experiments/P7BT-20261114T015044654616Z-c8ecc1e86e434a6b9ec1b76f6b5f23ae/traces"
P5 = "results/p5-2026-11-13"

KINDS = ("flat", "fixed_tree", "learned_tree")
TREES = ("fixed_tree", "learned_tree")
RS = (1, 2, 8, 32, 128, 512)
CS = (8, 16, 32, 64, 128)
TIES = ("asc", "desc")
SETTINGS = {"primary": (2, 32), "confirmation": (8, 8)}
NULLS = ("null_1", "null_2", "null_3")
PARTS = tuple(f"L-PCOAX-{i}" for i in range(1, 6))
RANDS = ("L-RAND-91101", "L-RAND-91102", "L-RAND-91103")
WARM_Q = 16384
QUERIES = 32768
ROWS_PER_QUERY = 8
PART_SEEDS = {91601: "ae626b43df264708466a8afc9c2b5434c3db053e7b57f27800b9674192b16487",
              91602: "0d310a05d82ef6eba8cc5adbeba16a88d74a5221353eb0208c1e755f3230e9f3",
              91603: "55cbff61076689e78f030d374b741aa28f448484694f51d3f65dbc56db183af5",
              91604: "98142918ba5f6ef34e6b9d3efc1f27a7c5ea9fd821bfb2b862641145af6f25a2",
              91605: "8d55366cd4d23a08e651161638e0b0cc34dbee0ad13764e3181ffa2b5db26a0c"}
CAPS = {"layouts": 2700.0, "panel+trace-b": 600.0, "simulate-a": 5400.0, "simulate-b": 5400.0,
        "analyze": 600.0, "total": 14700.0}
RSS_CAP = 2 * 1024 ** 3

TMB, FMB, W10, INTER, TRD, DEG = ("TREE MATERIALLY BETTER", "FLAT MATERIALLY BETTER", "WITHIN 10%",
                                  "INTERMEDIATE", "TIE-RULE DEPENDENT", "DEGENERATE")
RBB, NB = "REAL BRANCHES BETTER", "NOT BETTER"


def fl(x):
    return None if x is None else float(x)


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def mean(xs):
    xs = list(xs)
    return sum(xs, Fraction(0)) / len(xs) if xs and isinstance(xs[0], Fraction) else (
        sum(xs) / len(xs) if xs else None)


# ------------------------------------------------------------------------------------------------
# record access
# ------------------------------------------------------------------------------------------------
class Stream:
    def __init__(self, repo: Path, name: str):
        self.name = name
        run = repo / RUNS["simulate-a" if name == "A" else "simulate-b"]
        self.run = run
        self.results = {}
        self.outcomes = {}
        for p in sorted((run / "workers").glob("*.result.json")):
            d = json.loads(p.read_text())
            self.results[d["label"]] = d
        self.labels = sorted(self.results, key=lambda lb: self.results[lb]["cell_index"])
        self.kind = {lb: self.results[lb]["kind"] for lb in self.labels}
        self.pair = {lb: tuple(self.results[lb]["pair"]) for lb in self.labels}
        self.eff = {lb: self.results[lb]["record"]["evaluation_counts"]["effective_slots"]
                    for lb in self.labels}
        self.ent = {lb: self.results[lb]["record"]["evaluation_counts"]["entropy_nats"]
                    for lb in self.labels}

    def by_kind(self, kind):
        return [lb for lb in self.labels if self.kind[lb] == kind]

    def entry(self, lb, stream, layout, R, C, tie):
        st = self.results[lb]["record"]["streams"].get(stream, {})
        e = st.get(f"{layout}|R{R}")
        if e is None:
            return None
        return e["by_c"].get(str(C), {}).get(tie)

    def mint(self, lb, stream, layout, R, C, tie):
        """Integer warm capacity misses (None if not simulated). L-RAND = sum over 3 perms / 3."""
        if layout == "L-RAND":
            vals = [self.mint(lb, stream, r, R, C, tie) for r in RANDS]
            return None if None in vals else Fraction(sum(vals), 3)
        e = self.entry(lb, stream, layout, R, C, tie)
        if e is None:
            return None
        return e["misses_warm"] - e["first_touch_warm"]

    def m(self, lb, stream, layout, R, C, tie):
        v = self.mint(lb, stream, layout, R, C, tie)
        return None if v is None else Fraction(v) / WARM_Q

    def mnull(self, lb, layout, R, C, tie):
        vals = [self.m(lb, s, layout, R, C, tie) for s in NULLS]
        return None if None in vals else sum(vals, Fraction(0)) / 3

    def E(self, lb, layout, R, C, tie, num="actual"):
        n = self.m(lb, num, layout, R, C, tie)
        d = self.mnull(lb, "L-FREQ", R, C, tie)
        if n is None or d is None or d == 0:
            return None
        return n / d

    def S(self, lb, layout, R, C, tie):
        n = self.m(lb, "actual", layout, R, C, tie)
        d = self.mnull(lb, layout, R, C, tie)
        if n is None or d is None or d == 0:
            return None
        return n / d

    def G(self, lb, layout, R, C, tie):
        n = self.m(lb, "actual", layout, R, C, tie)
        d = self.m(lb, "actual", "L-FREQ", R, C, tie)
        if n is None or d is None or d == 0:
            return None
        return n / d


# ------------------------------------------------------------------------------------------------
# OLS, exact
# ------------------------------------------------------------------------------------------------
def solve3(M, v):
    M = [row[:] + [v[i]] for i, row in enumerate(M)]
    n = 3
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [M[r][k] - f * M[c][k] for k in range(n + 1)]
    return [M[i][n] / M[i][i] for i in range(n)]


def ols(rows):
    """rows: list of (E, x, t) Fractions. Returns a, b, d, xbar."""
    X = [(Fraction(1), x, t) for _, x, t in rows]
    y = [e for e, _, _ in rows]
    XtX = [[sum((X[k][i] * X[k][j] for k in range(len(X))), Fraction(0)) for j in range(3)]
           for i in range(3)]
    Xty = [sum((X[k][i] * y[k] for k in range(len(X))), Fraction(0)) for i in range(3)]
    a, b, d = solve3(XtX, Xty)
    xbar = sum((x for _, x, _ in rows), Fraction(0)) / len(rows)
    return a, b, d, xbar


def slope_only(pts):
    """Simple OLS slope and SE for (x, y) floats; descriptive per-architecture slopes."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    b = sxy / sxx
    a = my - b * mx
    res = sum((p[1] - a - b * p[0]) ** 2 for p in pts)
    se = math.sqrt(res / (n - 2) / sxx)
    return a, b, se


# ------------------------------------------------------------------------------------------------
# registered comparison (ADR section 7)
# ------------------------------------------------------------------------------------------------
def pairs_of(st: Stream, K: str):
    flat = {st.pair[lb]: lb for lb in st.by_kind("flat")}
    return [(lb, flat[st.pair[lb]]) for lb in st.by_kind(K)]


def compare(st: Stream, K, Lt, Lf, R, C, tie, num="actual", xsrc="eff"):
    prs = pairs_of(st, K)
    out = {"R": R, "C": C, "tie": tie, "tree_layout": Lt, "flat_layout": Lf, "numerator": num}
    den_t = [st.mnull(t, "L-FREQ", R, C, tie) for t, _ in prs]
    den_f = [st.mnull(f, "L-FREQ", R, C, tie) for _, f in prs]
    num_t = [st.m(t, num, Lt, R, C, tie) for t, _ in prs]
    num_f = [st.m(f, num, Lf, R, C, tie) for _, f in prs]
    if None in den_t + den_f + num_t + num_f:
        out["status"] = "NOT SIMULATED"
        out["class"] = None
        return out
    nd = {"flat_denominator_mean": mean(den_f), "tree_denominator_mean": mean(den_t),
          "min_denominator": min(den_t + den_f), "flat_numerator_mean": mean(num_f),
          "tree_numerator_mean": mean(num_t)}
    ok = (nd["flat_denominator_mean"] >= Fraction(5, 100) and nd["tree_denominator_mean"] >= Fraction(1, 100)
          and nd["min_denominator"] >= Fraction(5, 1000) and nd["flat_numerator_mean"] >= Fraction(1, 100)
          and nd["tree_numerator_mean"] >= Fraction(1, 100))
    out["non_degeneracy"] = nd
    out["status"] = "NON-DEGENERATE" if ok else "DEGENERATE"
    if any(d == 0 for d in den_t + den_f):
        out["class"] = DEG
        return out
    Et = [n / d for n, d in zip(num_t, den_t)]
    Ef = [n / d for n, d in zip(num_f, den_f)]
    mt, mf = mean(Et), mean(Ef)
    rho = mt / mf if mf != 0 else None
    xs = {lb: Fraction(math.log(st.eff[lb])) if xsrc == "eff" else Fraction(st.ent[lb]) for lb in st.labels}
    rows = [(e, xs[t], Fraction(1)) for e, (t, _) in zip(Et, prs)] + \
           [(e, xs[f], Fraction(0)) for e, (_, f) in zip(Ef, prs)]
    a, b, d, xbar = ols(rows)
    base = a + b * xbar
    rho_adj = (base + d) / base if base > 0 else None
    cells_t = sum(1 for x, y in zip(Et, Ef) if x < y)
    cells_f = sum(1 for x, y in zip(Et, Ef) if x > y)
    ties_ = sum(1 for x, y in zip(Et, Ef) if x == y)
    parents = sorted({st.pair[t][:2] for t, _ in prs})
    pt = pf = 0
    for p in parents:
        idx = [i for i, (t, _) in enumerate(prs) if st.pair[t][:2] == p]
        a_t = mean([Et[i] for i in idx])
        a_f = mean([Ef[i] for i in idx])
        pt += a_t < a_f
        pf += a_t > a_f
    fav_t = cells_t >= 22 and pt >= 8
    fav_f = cells_f >= 22 and pf >= 8
    if not ok:
        cls = DEG
    elif rho_adj is None:
        cls = INTER
    elif rho <= Fraction(8, 10) and rho_adj <= Fraction(8, 10) and fav_t:
        cls = TMB
    elif rho >= Fraction(125, 100) and rho_adj >= Fraction(125, 100) and fav_f:
        cls = FMB
    elif Fraction(9, 10) <= rho <= Fraction(11, 10) and Fraction(9, 10) <= rho_adj <= Fraction(11, 10):
        cls = W10
    else:
        cls = INTER
    # unadjusted / adjusted distance to boundaries
    out.update({
        "E_tree_mean": mt, "E_flat_mean": mf, "rho": rho, "rho_adj": rho_adj,
        "a": a, "b": b, "d": d, "x_mean": xbar, "level_at_mean_utilization": base,
        "cells_tree_lower": cells_t, "cells_flat_lower": cells_f, "cells_tied": ties_,
        "parents_tree_lower": pt, "parents_flat_lower": pf, "parents_total": len(parents),
        "counts_favour_tree": fav_t, "counts_favour_flat": fav_f, "class": cls,
        "E_tree": Et, "E_flat": Ef,
    })
    # descriptive: per-architecture slopes and separate-slope ratios
    pts_t = [(float(xs[t]), float(e)) for e, (t, _) in zip(Et, prs)]
    pts_f = [(float(xs[f]), float(e)) for e, (_, f) in zip(Ef, prs)]
    at_, bt_, set_ = slope_only(pts_t)
    af_, bf_, sef_ = slope_only(pts_f)
    xb = float(xbar)
    mxt = sum(p[0] for p in pts_t) / 27
    mxf = sum(p[0] for p in pts_f) / 27
    out["separate_slopes"] = {
        "tree_slope": bt_, "tree_se": set_, "flat_slope": bf_, "flat_se": sef_,
        "z_difference": (bt_ - bf_) / math.sqrt(set_ ** 2 + sef_ ** 2),
        "ratio_at_pooled_xbar": (at_ + bt_ * xb) / (af_ + bf_ * xb),
        "ratio_at_flat_mean_x": (at_ + bt_ * mxf) / (af_ + bf_ * mxf),
        "ratio_at_tree_mean_x": (at_ + bt_ * mxt) / (af_ + bf_ * mxt),
    }
    return out


def combine_ties(by_tie):
    cl = [by_tie[t]["class"] for t in TIES]
    if any(c == DEG or by_tie[t]["status"] == "DEGENERATE" for c, t in zip(cl, TIES)):
        return DEG
    if cl[0] == cl[1]:
        return cl[0]
    return TRD


def part_k(st: Stream, K, R, C, tie):
    labs = st.by_kind(K)
    out = {"R": R, "C": C, "tie": tie}
    dens = {L: [st.mnull(lb, L, R, C, tie) for lb in labs] for L in ("L-BCOAX",) + PARTS}
    degenerate = False
    out["null_denominators"] = {}
    for L, v in dens.items():
        dg = min(v) < Fraction(5, 1000) or mean(v) < Fraction(1, 100)
        out["null_denominators"][L] = {"mean": mean(v), "min": min(v), "degenerate": dg}
        degenerate |= dg
    out["status"] = "DEGENERATE" if degenerate else "NON-DEGENERATE"
    SB = [st.S(lb, "L-BCOAX", R, C, tie) for lb in labs]
    SPi = {L: [st.S(lb, L, R, C, tie) for lb in labs] for L in PARTS}
    SP = [sum((SPi[L][i] for L in PARTS), Fraction(0)) / 5 for i in range(len(labs))]
    msb, msp = mean(SB), mean(SP)
    cells = sum(1 for b, p in zip(SB, SP) if b < p)
    tied = sum(1 for b, p in zip(SB, SP) if b == p)
    parents = sorted({st.pair[lb][:2] for lb in labs})
    pl = 0
    for p in parents:
        idx = [i for i, lb in enumerate(labs) if st.pair[lb][:2] == p]
        pl += mean([SB[i] for i in idx]) < mean([SP[i] for i in idx])
    agg = msb <= Fraction(8, 10) * msp and cells >= 22 and pl >= 8
    every = []
    for L in PARTS:
        ms = mean(SPi[L])
        every.append({"layout": L, "mean_S": ms, "ratio": msb / ms, "clause": msb <= Fraction(8, 10) * ms})
    better = (not degenerate) and agg and all(e["clause"] for e in every)
    # raw misses
    mB = [st.m(lb, "actual", "L-BCOAX", R, C, tie) for lb in labs]
    mPi = {L: [st.m(lb, "actual", L, R, C, tie) for lb in labs] for L in PARTS}
    mP = [sum((mPi[L][i] for L in PARTS), Fraction(0)) / 5 for i in range(len(labs))]
    spread = []
    lower_all = 0
    for i in range(len(labs)):
        vals = [SPi[L][i] for L in PARTS]
        spread.append((max(vals) - min(vals)) / (sum(vals, Fraction(0)) / 5))
        lower_all += all(SB[i] < v for v in vals)
    out.update({
        "mean_S_B": msb, "mean_S_P": msp, "aggregate_ratio": msb / msp, "cells_strictly_lower": cells,
        "cells_tied": tied, "parents_strictly_lower": pl, "parents_total": len(parents),
        "aggregate_holds": agg, "every_partition": every, "better": better,
        "raw_ratio": mean(mB) / mean(mP),
        "raw_per_partition": [mean(mB) / mean(mPi[L]) for L in PARTS],
        "per_cell_spread_mean": mean(spread), "cells_S_B_lower_than_all_five": lower_all,
        "partition_ratio_min": min(e["ratio"] for e in every),
        "partition_ratio_max": max(e["ratio"] for e in every),
    })
    return out


def outcome(hb, part, rho_primary_asc):
    hp, hc = hb["primary"], hb["confirmation"]
    pp, pc = part["primary"], part["confirmation"]
    if hp == DEG:
        return "UNRESOLVED"
    if hp == TMB and hc == TMB and pp == RBB and pc == RBB:
        return "HIERARCHY-SPECIFIC ADVANTAGE"
    if hp == TMB and hc == TMB:
        return "ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC"
    if hp == TMB:
        return "NOT ROBUST"
    if hp == FMB:
        return "FLAT CO-ACCESS BETTER"
    if hp == W10:
        return "WITHIN 10% OF FLAT CO-ACCESS"
    return "INTERMEDIATE (tree-favouring)" if rho_primary_asc < 1 else "INTERMEDIATE (flat-favouring)"


def pairing(a, b):
    if a == b and a != "UNRESOLVED":
        return f"{a}, REPLICATED"
    if a == b == "UNRESOLVED":
        return "UNRESOLVED ON BOTH STREAMS"
    if a == "UNRESOLVED" or b == "UNRESOLVED":
        return f"{b if a == 'UNRESOLVED' else a}, SINGLE-STREAM"
    return "NOT REPLICATED"


def decision_class(a, b):
    nset = {"WITHIN 10% OF FLAT CO-ACCESS", "FLAT CO-ACCESS BETTER", "ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC"}
    if a == b == "HIERARCHY-SPECIFIC ADVANTAGE":
        return "S"
    if a == b == "UNRESOLVED":
        return "U"
    if a in nset and b in nset:
        return "N"
    return "I"


def recommendation(classes):
    if "S" in classes:
        return 1, "At least one tree kind in S"
    if all(c == "N" for c in classes):
        return 2, "Both tree kinds in N"
    if all(c == "U" for c in classes):
        return 3, "Both tree kinds in U"
    return 4, "Anything else"


# ------------------------------------------------------------------------------------------------
# descriptive
# ------------------------------------------------------------------------------------------------
def agg_ratio(st, kind, f_num, f_den):
    """mean of per-checkpoint ratios and ratio of means; skip if any piece missing or den 0."""
    labs = st.by_kind(kind)
    nums = [f_num(lb) for lb in labs]
    dens = [f_den(lb) for lb in labs]
    if None in nums or None in dens:
        return None
    rom = mean(nums) / mean(dens) if mean(dens) != 0 else None
    mor = mean([n / d for n, d in zip(nums, dens)]) if all(d != 0 for d in dens) else None
    return {"mean_of_ratios": mor, "ratio_of_means": rom}


def descriptive(st: Stream, repo: Path, layout_workers: dict, p5nll: dict):
    D = {}
    crit = list(SETTINGS.items())
    # co-access gain, popularity cost, decomposition at criterion settings, both ties
    G, PC, DEC = {}, {}, {}
    for kind in KINDS:
        lays = ["L-COAX", "L-NCOAX", "L-COAX8", "L-COAXg", *PARTS]
        if kind != "flat":
            lays += ["L-BCOAX", "L-BFREQ", "L-BCOAX8", "L-BCOAXg"]
        for _, (R, C) in crit:
            for tie in TIES:
                for L in lays:
                    r = agg_ratio(st, kind, lambda lb: st.m(lb, "actual", L, R, C, tie),
                                  lambda lb: st.m(lb, "actual", "L-FREQ", R, C, tie))
                    if r:
                        G[f"{kind}|{L}|R{R}|C{C}|{tie}"] = r
                for L in ["L-COAX", *PARTS] + (["L-BCOAX"] if kind != "flat" else []):
                    r = agg_ratio(st, kind, lambda lb: st.mnull(lb, L, R, C, tie),
                                  lambda lb: st.mnull(lb, "L-FREQ", R, C, tie))
                    if r:
                        PC[f"{kind}|{L}|R{R}|C{C}|{tie}"] = r
                for L in ["L-FREQ", "L-COAX"] + (["L-BCOAX", "L-BFREQ"] if kind != "flat" else []):
                    labs = st.by_kind(kind)
                    nf = [st.mnull(lb, "L-FREQ", R, C, tie) for lb in labs]
                    nl = [st.mnull(lb, L, R, C, tie) for lb in labs]
                    al = [st.m(lb, "actual", L, R, C, tie) for lb in labs]
                    if None in nf + al:
                        continue
                    DEC[f"{kind}|{L}|R{R}|C{C}|{tie}"] = {
                        "mean_null_LFREQ": mean(nf),
                        "mean_null_L": None if None in nl else mean(nl),
                        "mean_actual_L": mean(al),
                        "mean_E": mean([a / b for a, b in zip(al, nf)]),
                        "mean_S": None if None in nl else mean([a / b for a, b in zip(al, nl)]),
                        "mean_popularity_cost": None if None in nl else mean([b / a for a, b in zip(nf, nl)]),
                    }
    D["co_access_gain"] = G
    D["popularity_cost"] = PC
    D["decomposition"] = DEC
    # BC_K and partition counterpart
    BC = {}
    for K in TREES:
        for _, (R, C) in crit:
            for tie in TIES:
                labs = st.by_kind(K)
                mb = [st.m(lb, "actual", "L-BCOAX", R, C, tie) for lb in labs]
                mc = [st.m(lb, "actual", "L-COAX", R, C, tie) for lb in labs]
                mp = [sum((st.m(lb, "actual", L, R, C, tie) for L in PARTS), Fraction(0)) / 5 for lb in labs]
                BC[f"{K}|R{R}|C{C}|{tie}"] = {
                    "BC_ratio_of_means": mean(mb) / mean(mc), "BC_mean_of_ratios": mean([a / b for a, b in zip(mb, mc)]),
                    "partition_ratio_of_means": mean(mp) / mean(mc),
                    "partition_mean_of_ratios": mean([a / b for a, b in zip(mp, mc)])}
    D["BC_K"] = BC
    # NCOAX band
    nco = []
    for kind in KINDS:
        for _, (R, C) in crit:
            for tie in TIES:
                labs = st.by_kind(kind)
                g = [st.G(lb, "L-NCOAX", R, C, tie) for lb in labs]
                mg = mean(g)
                nco.append({"kind": kind, "R": R, "C": C, "tie": tie, "G_mean_of_ratios": mg,
                            "within_band": Fraction(97, 100) <= mg <= Fraction(103, 100)})
    D["ncoax_control"] = {"rows": nco, "flagged": not all(r["within_band"] for r in nco)}
    # flat partition layouts vs flat L-COAX
    FP = {}
    for L in PARTS:
        for _, (R, C) in crit:
            for tie in TIES:
                labs = st.by_kind("flat")
                FP[f"{L}|R{R}|C{C}|{tie}"] = {
                    "raw_ratio_vs_flat_coax": mean([st.m(lb, "actual", L, R, C, tie) for lb in labs]) /
                    mean([st.m(lb, "actual", "L-COAX", R, C, tie) for lb in labs]),
                    "exploited_ratio_vs_flat_coax": mean([st.S(lb, L, R, C, tie) for lb in labs]) /
                    mean([st.S(lb, "L-COAX", R, C, tie) for lb in labs])}
    D["flat_partition_layouts"] = FP
    # utilization
    D["utilization"] = {k: {"mean_effective_slots": mean([st.eff[lb] for lb in st.by_kind(k)]),
                            "mean_entropy_nats": mean([st.ent[lb] for lb in st.by_kind(k)]),
                            "mean_unique_selected_slots": mean([st.results[lb]["record"]["evaluation_counts"]["unique_selected_slots"] for lb in st.by_kind(k)])}
                        for k in KINDS}
    # sensitivity: W=8 and greedy-only HB/HU at criterion settings (asc only: desc not simulated)
    SENS = {}
    for K in TREES:
        for sname, (R, C) in crit:
            for var, lt, lf in (("A8", "L-BCOAX8", "L-COAX8"), ("greedy", "L-BCOAXg", "L-COAXg"),
                                ("HU_A8", "L-COAX8", "L-COAX8"), ("HU_greedy", "L-COAXg", "L-COAXg"),
                                ("order_shuffled", "L-BCOAX", "L-COAX")):
                for tie in TIES:
                    num = "order_shuffled" if var == "order_shuffled" else "actual"
                    r = compare(st, K, lt, lf, R, C, tie, num=num)
                    SENS[f"{K}|{sname}|{var}|{tie}"] = slim(r)
    D["sensitivity"] = SENS
    # robustness grid (asc; both at criterion settings handled in registered)
    GRID = {}
    for K in TREES:
        for R in RS:
            for C in CS:
                cell = {}
                for var, lt, lf, num in (("HB", "L-BCOAX", "L-COAX", "actual"), ("HU", "L-COAX", "L-COAX", "actual"),
                                         ("HB_A8", "L-BCOAX8", "L-COAX8", "actual"),
                                         ("HB_greedy", "L-BCOAXg", "L-COAXg", "actual"),
                                         ("HB_order_shuffled", "L-BCOAX", "L-COAX", "order_shuffled")):
                    cell[var] = slim(compare(st, K, lt, lf, R, C, "asc", num=num))
                GRID[f"{K}|R{R}|C{C}"] = cell
    D["robustness_grid_asc"] = GRID
    # pages and misses at criterion settings (+ per context quantiles)
    PM = {}
    for kind in KINDS:
        lays = ["L-FREQ", "L-COAX", "L-NCOAX", *PARTS] + (["L-BCOAX", "L-BFREQ"] if kind != "flat" else [])
        for _, (R, C) in crit:
            for tie in TIES:
                for L in lays:
                    labs = st.by_kind(kind)
                    es = [st.entry(lb, "actual", L, R, C, tie) for lb in labs]
                    if None in es:
                        continue
                    stats = [st.results[lb]["record"]["streams"]["actual"][f"{L}|R{R}"]["stats"] for lb in labs]
                    m_ = [Fraction(e["misses_warm"] - e["first_touch_warm"], WARM_Q) for e in es]
                    PM[f"{kind}|{L}|R{R}|C{C}|{tie}"] = {
                        "warm_capacity_misses_per_query": mean(m_),
                        "first_touch_misses_per_query_whole_stream": mean([Fraction(e["first_touch_all"], QUERIES) for e in es]),
                        "first_touch_warm_per_counted_query": mean([Fraction(e["first_touch_warm"], WARM_Q) for e in es]),
                        "cold_misses_per_query_whole_stream": mean([Fraction(e["misses_all"], QUERIES) for e in es]),
                        "cached_amplification_warm_capacity_misses": mean(m_) * R / ROWS_PER_QUERY,
                        "cached_amplification_all_warm_misses": mean([Fraction(e["misses_warm"], WARM_Q) for e in es]) * R / ROWS_PER_QUERY,
                        "mean_distinct_pages_per_query": mean([Fraction(s["pages_sum"], QUERIES) for s in stats]),
                        "uncached_read_amplification": mean([Fraction(s["pages_sum"], QUERIES) for s in stats]) * R / ROWS_PER_QUERY,
                        "per_context_quantiles_mean": [mean([Fraction(e["ctx_q"][i]) for e in es]) for i in range(7)],
                        "mean_effective_slots": mean([st.eff[lb] for lb in labs]),
                    }
    D["pages_and_misses"] = PM
    # calibration transfer (asc; criterion settings + L-FREQ etc)
    CT = {}
    for kind in KINDS:
        lays = ["L-FREQ", "L-COAX", "L-NCOAX", *PARTS] + (["L-BCOAX", "L-BFREQ"] if kind != "flat" else [])
        for _, (R, C) in crit:
            for L in lays:
                labs = st.by_kind(kind)
                cal = []
                for lb in labs:
                    e = layout_workers[lb]["calibration_transfer"][f"{L}|R{R}"]["by_c"][str(C)]["asc"]
                    cal.append(Fraction(e["misses_warm"] - e["first_touch_warm"], WARM_Q))
                ev = [st.m(lb, "actual", L, R, C, "asc") for lb in labs]
                CT[f"{kind}|{L}|R{R}|C{C}"] = {"mean_m_calibration": mean(cal), "mean_m_evaluation": mean(ev),
                                               "evaluation_over_calibration": mean(ev) / mean(cal),
                                               "mean_of_ratios": mean([a / b for a, b in zip(ev, cal)])}
    D["calibration_transfer"] = CT
    # quality vs misses
    Q = {"per_kind_mean_nll": {k: mean([p5nll[lb] for lb in st.by_kind(k)]) for k in KINDS}}
    for K in TREES:
        prs = pairs_of(st, K)
        dn = [p5nll[t] - p5nll[f] for t, f in prs]
        Q[f"{K}|paired_nll"] = {"mean_tree_minus_flat": mean(dn),
                                "cells_abs_within_0.005": sum(1 for x in dn if abs(x) <= 0.005),
                                "cells_tree_not_worse_by_more_than_0.005": sum(1 for x in dn if x <= 0.005),
                                "max_abs": max(abs(x) for x in dn)}
        for sname, (R, C) in crit:
            for tie in TIES:
                dE = [float(st.E(t, "L-BCOAX", R, C, tie) - st.E(f, "L-COAX", R, C, tie)) for t, f in prs]
                Q[f"{K}|{sname}|{tie}|paired_E_diff_HB"] = {
                    "mean": sum(dE) / 27, "cells_tree_lower": sum(1 for x in dE if x < 0),
                    "pearson_dNLL_vs_dE": pearson(dn, dE)}
    for kind in KINDS:
        for sname, (R, C) in crit:
            for tie in TIES:
                for L in ["L-COAX", "L-FREQ"] + (["L-BCOAX"] if kind != "flat" else []):
                    labs = st.by_kind(kind)
                    Q[f"{kind}|{L}|{sname}|{tie}|corr_E_NLL"] = pearson(
                        [float(st.E(lb, L, R, C, tie)) for lb in labs], [p5nll[lb] for lb in labs])
    D["quality_vs_misses"] = Q
    return D


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def slim(r):
    keep = ("status", "class", "rho", "rho_adj", "b", "cells_tree_lower", "parents_tree_lower",
            "cells_flat_lower", "parents_flat_lower", "E_tree_mean", "E_flat_mean")
    o = {k: r.get(k) for k in keep if k in r}
    if "non_degeneracy" in r:
        o["non_degeneracy"] = r["non_degeneracy"]
    return o


# ------------------------------------------------------------------------------------------------
# integrity
# ------------------------------------------------------------------------------------------------
def integrity(repo: Path, streams: dict, layout_workers: dict, recompute_traces: bool):
    I = {}
    ident = json.loads((repo / IDENTITY).read_text())
    id_by = {c["label"]: c for c in ident["checkpoints"]}
    bman_path = repo / RUNS["trace-b"] / "stream_b_identity_manifest.json"
    bman = json.loads(bman_path.read_text())
    bman_sha = sha_file(bman_path)
    I["stream_b_manifest_file_sha256"] = bman_sha
    trace_b_result = json.loads((repo / RUNS["trace-b"] / "result.json").read_text())
    I["stream_b_manifest_sha_in_trace_b_result_matches"] = trace_b_result["stream_b_identity_manifest_sha256"] == bman_sha
    hash_table_path = repo / RUNS["layouts"] / "layout_hash_table.json"
    ht_sha = sha_file(hash_table_path)
    ht = json.loads(hash_table_path.read_text())
    I["layout_hash_table_sha256"] = ht_sha
    problems = []
    src_hashes = set()
    spec_hashes = set()
    for S, st in streams.items():
        n_comp = sum(1 for lb in st.labels if st.results[lb]["outcome"] == "completed" and st.results[lb]["record"]["complete"])
        I[f"{S}_completed"] = n_comp
        I[f"{S}_kinds"] = {k: len(st.by_kind(k)) for k in KINDS}
        res = json.loads((st.run / "result.json").read_text())
        I[f"{S}_stage_result_checkpoints_completed"] = res["checkpoints_completed"]
        for lb in st.labels:
            d = st.results[lb]
            src_hashes.add(json.dumps(d["p7b_source_sha256"], sort_keys=True))
            spec_hashes.add(d["spec_sha256"])
            if d["stream"] != S:
                problems.append(f"{S} {lb}: stream field {d['stream']}")
            if d["queries"] != QUERIES:
                problems.append(f"{S} {lb}: queries {d['queries']}")
            if d["stream_b_manifest_sha256"] != bman_sha:
                problems.append(f"{S} {lb}: stream_b_manifest_sha256 differs from file")
            lb_bind = d["layout_binding"]
            if lb_bind["hash_table_sha256"] != ht_sha:
                problems.append(f"{S} {lb}: layout hash table sha differs")
            if lb_bind["layout_file_sha256"] != ht["layout_files"][lb]["sha256"]:
                problems.append(f"{S} {lb}: layout file sha differs from hash table")
            if lb_bind["layout_file_sha256"] != layout_workers[lb]["layout_file"]["sha256"]:
                problems.append(f"{S} {lb}: layout file sha differs from layout worker")
            # null stream hashes
            if S == "A":
                p7a = id_by[lb]["simulation"]["frequency_matched"]
                for i, ns in enumerate(d["null_streams"]):
                    if ns["stream_sha256"] != p7a[f"freq_matched_{i + 1}"]["stream_sha256"]:
                        problems.append(f"A {lb}: null {i + 1} hash differs from P7-A")
                    if ns["replicate_seed"] != 91301 + i or ns["generator_seed"] != (91301 + i) * 1000 + d["cell_index"]:
                        problems.append(f"A {lb}: null seeds {ns}")
            else:
                bm = bman["checkpoints"][lb]
                for i, ns in enumerate(d["null_streams"]):
                    if ns["stream_sha256"] != bm["null_streams"][i]["stream_sha256"]:
                        problems.append(f"B {lb}: null {i + 1} hash differs from stream-B manifest")
                    if ns["replicate_seed"] != 91321 + i or ns["generator_seed"] != (91321 + i) * 1000 + d["cell_index"]:
                        problems.append(f"B {lb}: null seeds {ns}")
                if d["trace"]["files"]["selected"]["sha256"] != bm["selected_sha256"]:
                    problems.append(f"B {lb}: selected trace sha differs from manifest")
                br = d["trace"]["files"].get("branches")
                if (br or {}).get("sha256") != bm.get("branches_sha256"):
                    problems.append(f"B {lb}: branches sha differs from manifest")
                if d["counts_identity"].get("counts_sha256") != bm["counts_sha256"]:
                    problems.append(f"B {lb}: counts sha differs from manifest")
                if d["record"]["evaluation_counts"]["counts_sha256"] != bm["counts_sha256"]:
                    problems.append(f"B {lb}: record counts sha differs from manifest")
                if bm.get("loss_computed_on_stream_b") is not False:
                    problems.append(f"B {lb}: loss_computed_on_stream_b not false")
            # R = 1 invariants, first-touch independence, monotonicity, misses <= touches
            for sname, lays in d["record"]["streams"].items():
                r1 = {k: v for k, v in lays.items() if k.endswith("|R1")}
                ps = {v["stats"]["pages_sum"] for v in r1.values()}
                if len(ps) > 1:
                    problems.append(f"{S} {lb} {sname}: R1 pages_sum differs across layouts {ps}")
                hs = {json.dumps(v["stats"]["hist"]) for v in r1.values()}
                if len(hs) > 1:
                    problems.append(f"{S} {lb} {sname}: R1 histogram differs across layouts")
                c8 = {v["by_c"]["8"]["asc"]["misses_warm"] - v["by_c"]["8"]["asc"]["first_touch_warm"] for v in r1.values() if "8" in v["by_c"]}
                if len(c8) > 1:
                    problems.append(f"{S} {lb} {sname}: R1 C8 capacity misses differ {c8}")
                ft = {(v["by_c"][c][t]["first_touch_all"], v["by_c"][c][t]["first_touch_warm"]) for v in r1.values() for c in v["by_c"] for t in v["by_c"][c]}
                if len(ft) > 1:
                    problems.append(f"{S} {lb} {sname}: R1 first-touch differs")
                for key, v in lays.items():
                    R = int(key.split("|R")[1])
                    fts = {(v["by_c"][c][t]["first_touch_all"], v["by_c"][c][t]["first_touch_warm"]) for c in v["by_c"] for t in v["by_c"][c]}
                    if len(fts) > 1:
                        problems.append(f"{S} {lb} {sname} {key}: first-touch depends on C or tie")
                    if list(fts)[0][0] != v["stats"]["distinct_stream"]:
                        problems.append(f"{S} {lb} {sname} {key}: first_touch_all != distinct pages in stream")
                    prev = None
                    for c in sorted(v["by_c"], key=int):
                        e = v["by_c"][c]["asc"]
                        if e["misses_all"] > v["stats"]["pages_sum"]:
                            problems.append(f"{S} {lb} {sname} {key} C{c}: misses exceed touches")
                        if e["misses_warm"] > e["misses_all"] or e["first_touch_warm"] > e["misses_warm"]:
                            problems.append(f"{S} {lb} {sname} {key} C{c}: count ordering")
                        cap = e["misses_warm"] - e["first_touch_warm"]
                        if prev is not None and cap > prev:
                            problems.append(f"{S} {lb} {sname} {key} C{c}: capacity misses increase with C ({prev}->{cap})")
                        prev = cap
                        # with C pages of R rows, a query needing p<=C pages... ceiling: a page can only be
                        # missed if touched; capacity >= distinct pages of the busiest query is required
                    if max(i for i, h in enumerate(v["stats"]["hist"]) if h) + 1 > min(int(c) for c in v["by_c"]):
                        problems.append(f"{S} {lb} {sname} {key}: a query touches more pages than smallest C")
                    if sum(v["stats"]["hist"]) != QUERIES:
                        problems.append(f"{S} {lb} {sname} {key}: histogram total {sum(v['stats']['hist'])}")
                    if sum((i + 1) * h for i, h in enumerate(v["stats"]["hist"])) != v["stats"]["pages_sum"]:
                        problems.append(f"{S} {lb} {sname} {key}: hist vs pages_sum")
            if not d["r1_invariants"]["all_identical"]:
                problems.append(f"{S} {lb}: record says R1 invariants not identical")
    I["distinct_p7b_source_hash_sets_across_sim_workers"] = len(src_hashes)
    I["distinct_spec_sha256_across_sim_workers"] = sorted(spec_hashes)
    # stage manifests: spec hash and sources consistent across stages
    stage_spec, stage_src = {}, set()
    for stg, path in RUNS.items():
        man = json.loads((repo / path / "manifest.json").read_text())
        stage_spec[stg] = (man.get("frozen_check_at_end", {}).get("spec_sha256"),
                           man.get("frozen_check_at_end", {}).get("spec_unchanged"),
                           man.get("frozen_check_at_end", {}).get("p7b_sources_unchanged"))
        stage_src.add(json.dumps(man.get("p7b_source_sha256"), sort_keys=True))
    I["stage_spec_and_frozen_checks"] = stage_spec
    I["distinct_p7b_source_hash_sets_across_stage_manifests"] = len(stage_src)
    I["stage_and_worker_sources_identical"] = stage_src == src_hashes
    spec_now = sha_file(repo / "docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md")
    I["spec_sha256_of_ADR_file_now"] = spec_now
    # P7-A reproduction on stream A
    stA = streams["A"]
    n_cmp = n_diff = 0
    for lb in stA.labels:
        p7a = json.loads((repo / P7A_SIM / f"{lb}.result.json").read_text())["record"]["streams"]
        mapping = {"actual": "actual", "freq_matched_1": "null_1", "freq_matched_2": "null_2",
                   "freq_matched_3": "null_3", "order_shuffled": "order_shuffled"}
        for s7a, sb in mapping.items():
            for key, v in p7a[s7a].items():
                for c, e in v["by_c"].items():
                    mine = stA.results[lb]["record"]["streams"][sb].get(key, {}).get("by_c", {}).get(c, {}).get("asc")
                    n_cmp += 1
                    if mine is None or any(mine[f] != e[f] for f in ("misses_all", "misses_warm", "first_touch_all", "first_touch_warm")):
                        n_diff += 1
                        if n_diff <= 20:
                            problems.append(f"A {lb} {s7a} {key} C{c}: differs from P7-A")
    I["p7a_reproduction"] = {"configurations_compared": n_cmp, "differences": n_diff}
    # partitions registered hashes
    ph = {}
    for seed, want in PART_SEEDS.items():
        lst = list(range(4096))
        random.Random(seed).shuffle(lst)
        got = hashlib.sha256(b"".join(struct.pack("<H", v) for v in lst)).hexdigest()
        ph[seed] = got == want
    I["partition_hashes_match_registered"] = ph
    # traces: hashes and effective slots from the raw files
    if recompute_traces:
        tr = {"A": [], "B": []}
        for S, st in streams.items():
            base = repo / (TRACE_A_DIR if S == "A" else TRACE_B_DIR)
            fname = "eval_selected.int16.bin" if S == "A" else "streamB_selected.int16.bin"
            for lb in st.labels:
                p = base / lb / fname
                data = p.read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                vals = struct.unpack(f"<{len(data) // 2}h", data)
                counts = [0] * 4096
                for v in vals:
                    counts[v] += 1
                tot = sum(counts)
                ent = -sum(c / tot * math.log(c / tot) for c in counts if c)
                rec = st.results[lb]
                ok_sha = sha == rec["trace"]["files"]["selected"]["sha256"]
                diff_eff = abs(math.exp(ent) - st.eff[lb])
                tr[S].append({"label": lb, "sha_matches_record": ok_sha, "entropy_mine": ent,
                              "entropy_record": st.ent[lb], "abs_diff_effective_slots": diff_eff,
                              "unique_mine": sum(1 for c in counts if c),
                              "unique_record": rec["record"]["evaluation_counts"]["unique_selected_slots"],
                              "rows": len(vals)})
                if not ok_sha:
                    problems.append(f"{S} {lb}: trace sha differs from record")
                if diff_eff > 1e-9 * st.eff[lb]:
                    problems.append(f"{S} {lb}: effective slots differ {math.exp(ent)} vs {st.eff[lb]}")
                if tr[S][-1]["unique_mine"] != tr[S][-1]["unique_record"]:
                    problems.append(f"{S} {lb}: unique slots differ")
                if S == "A":
                    idf = [f for f in id_by[lb]["files"] if f.get("relpath", "").endswith("eval_selected.int16.bin")]
                    if not idf or idf[0]["recorded_sha256"] != sha:
                        problems.append(f"A {lb}: trace sha differs from identity manifest")
        I["trace_check"] = {S: {"checkpoints": len(v), "all_sha_match": all(x["sha_matches_record"] for x in v),
                                "max_abs_diff_effective_slots": max(x["abs_diff_effective_slots"] for x in v),
                                "max_abs_diff_entropy": max(abs(x["entropy_mine"] - x["entropy_record"]) for x in v)}
                            for S, v in tr.items()}
    I["problems"] = problems
    return I


def resources(repo: Path):
    out = {}
    tot = 0.0
    peak = 0
    for stg in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze"):
        res = json.loads((repo / RUNS[stg] / "result.json").read_text())
        man = json.loads((repo / RUNS[stg] / "manifest.json").read_text())
        act = res.get("active_seconds", res.get("analysis_seconds"))
        workers = res.get("workers") or []
        wsum = sum(w.get("wall_seconds") or 0 for w in workers)
        wpk = max([w.get("peak_rss_bytes") or 0 for w in workers] + [0])
        out[stg] = {"active_seconds": act, "stage_wall_seconds": man.get("wall_seconds"),
                    "sum_worker_wall_seconds": wsum, "workers": len(workers),
                    "stage_peak_rss_bytes": res.get("peak_rss_bytes"), "max_worker_peak_rss_bytes": wpk,
                    "cap_seconds_in_manifest": man["caps"]["stage_seconds"],
                    "start_utc": man.get("start_utc"), "end_utc": man.get("end_utc"), "status": res.get("status")}
        tot += act or 0
        peak = max(peak, res.get("peak_rss_bytes") or 0, wpk)
    out["checks"] = {
        "layouts_within_2700": out["layouts"]["active_seconds"] <= CAPS["layouts"],
        "panel_plus_trace_b_within_600": out["panel"]["active_seconds"] + out["trace-b"]["active_seconds"] <= CAPS["panel+trace-b"],
        "simulate_a_within_5400": out["simulate-a"]["active_seconds"] <= CAPS["simulate-a"],
        "simulate_b_within_5400": out["simulate-b"]["active_seconds"] <= CAPS["simulate-b"],
        "analyze_within_600": out["analyze"]["active_seconds"] <= CAPS["analyze"],
        "study_total_seconds": tot, "study_total_within_14700": tot <= CAPS["total"],
        "max_recorded_rss_bytes": peak, "rss_within_2GiB": peak <= RSS_CAP,
    }
    return out


def split_half(layout_workers, labels_by_kind):
    out = {}
    for kind, labs in labels_by_kind.items():
        keys = sorted(layout_workers[labs[0]]["split_half"])
        for key in keys:
            f01 = [Fraction(layout_workers[lb]["split_half"][key]["capacity_misses_fit_0"], layout_workers[lb]["split_half"][key]["counted_queries"]) for lb in labs]
            f10 = [Fraction(layout_workers[lb]["split_half"][key]["capacity_misses_fit_1"], layout_workers[lb]["split_half"][key]["counted_queries"]) for lb in labs]
            rel_mean = [abs(a - b) / ((a + b) / 2) if a + b else Fraction(0) for a, b in zip(f01, f10)]
            rel_min = [abs(a - b) / min(a, b) if min(a, b) else None for a, b in zip(f01, f10)]
            out[f"{kind}|{key}"] = {"mean_m_fit0_score1": mean(f01), "mean_m_fit1_score0": mean(f10),
                                    "mean_rel_diff_over_pair_mean": mean(rel_mean), "max_rel_diff_over_pair_mean": max(rel_mean),
                                    "mean_rel_diff_over_min": mean([x for x in rel_min if x is not None]),
                                    "max_rel_diff_over_min": max(x for x in rel_min if x is not None)}
    return out


# ------------------------------------------------------------------------------------------------
# comparison with analysis.json
# ------------------------------------------------------------------------------------------------
class Cmp:
    def __init__(self):
        self.n = 0
        self.diffs = []
        self.max_rel = 0.0

    def num(self, where, mine, theirs, tol=1e-9):
        self.n += 1
        if mine is None or theirs is None:
            if not (mine is None and theirs is None):
                self.diffs.append({"where": where, "mine": fl(mine) if not isinstance(mine, str) else mine, "theirs": theirs})
            return
        m, t = float(mine), float(theirs)
        rel = abs(m - t) / max(abs(t), 1e-300) if t != 0 else abs(m)
        self.max_rel = max(self.max_rel, rel)
        if rel > tol:
            self.diffs.append({"where": where, "mine": m, "theirs": t, "rel": rel})

    def eq(self, where, mine, theirs):
        self.n += 1
        if mine != theirs:
            self.diffs.append({"where": where, "mine": mine, "theirs": theirs})


def compare_with_analysis(an, REG, DESC, SPLIT, cmpr: Cmp):
    for S in ("A", "B"):
        ps = an["per_stream"][S]["tree_kinds"]
        for K in TREES:
            mine = REG[S][K]
            th = ps[K]
            cmpr.eq(f"{S}/{K}/outcome", mine["outcome"], th["outcome"])
            cmpr.num(f"{S}/{K}/primary_rho_asc", mine["primary_rho_ascending"], th["primary_rho_ascending"])
            for comp in ("HB", "HU", "PART"):
                for sname in SETTINGS:
                    cmpr.eq(f"{S}/{K}/{comp}/{sname}/class", mine[comp][sname], th[comp][sname])
            for sname in SETTINGS:
                for comp in ("HB", "HU"):
                    for tie in TIES:
                        m = mine["detail"][comp][sname][tie]
                        t = th["settings"][sname][comp]["by_tie"][tie]
                        w = f"{S}/{K}/{comp}/{sname}/{tie}"
                        cmpr.eq(w + "/class", m["class"], t["class"])
                        cmpr.eq(w + "/status", m["status"], t["status"])
                        cmpr.num(w + "/rho", m["rho"], t["rho"])
                        if "rho_exact" in t:
                            cmpr.eq(w + "/rho_exact", str(m["rho"]), t["rho_exact"])
                        cmpr.num(w + "/rho_adj", m["rho_adj"], t["rho_adj"])
                        adj = t["adjustment"]
                        for k in ("a", "b", "d", "x_mean", "level_at_mean_utilization"):
                            cmpr.num(w + "/" + k, m[k], adj[k])
                        cmpr.num(w + "/E_tree_mean", m["E_tree_mean"], t["E_tree_mean"])
                        cmpr.num(w + "/E_flat_mean", m["E_flat_mean"], t["E_flat_mean"])
                        cmpr.eq(w + "/cells_tree_lower", m["cells_tree_lower"], t["counts_favour_tree"]["cells_strictly_lower"])
                        cmpr.eq(w + "/parents_tree_lower", m["parents_tree_lower"], t["counts_favour_tree"]["parents_strictly_lower"])
                        cmpr.eq(w + "/cells_flat_lower", m["cells_flat_lower"], t["counts_favour_flat"]["cells_strictly_lower"])
                        cmpr.eq(w + "/parents_flat_lower", m["parents_flat_lower"], t["counts_favour_flat"]["parents_strictly_lower"])
                        cmpr.eq(w + "/cells_tied", m["cells_tied"], t["counts_favour_tree"]["cells_tied"])
                        for k, v in m["non_degeneracy"].items():
                            cmpr.num(w + "/nd/" + k, v, t["non_degeneracy"][k])
                for tie in TIES:
                    m = mine["detail"]["PART"][sname][tie]
                    t = th["settings"][sname]["PART"]["by_tie"][tie]
                    w = f"{S}/{K}/PART/{sname}/{tie}"
                    cmpr.eq(w + "/better", m["better"], t["better"])
                    cmpr.eq(w + "/status", m["status"], t["status"])
                    cmpr.num(w + "/ratio", m["aggregate_ratio"], t["aggregate"]["ratio"])
                    cmpr.num(w + "/mean_S_B", m["mean_S_B"], t["aggregate"]["mean_S_B"])
                    cmpr.num(w + "/mean_S_P", m["mean_S_P"], t["aggregate"]["mean_S_P"])
                    cmpr.eq(w + "/cells", m["cells_strictly_lower"], t["aggregate"]["cells_strictly_lower"])
                    cmpr.eq(w + "/parents", m["parents_strictly_lower"], t["aggregate"]["parents_strictly_lower"])
                    for i, e in enumerate(m["every_partition"]):
                        cmpr.num(w + f"/part{i + 1}/ratio", e["ratio"], t["every_partition"][i]["ratio"])
                        cmpr.num(w + f"/part{i + 1}/mean_S", e["mean_S"], t["every_partition"][i]["mean_S"])
                    cmpr.num(w + "/raw", m["raw_ratio"], t["raw_misses_descriptive"]["mean_m_B_over_mean_m_P"])
                    for i, v in enumerate(m["raw_per_partition"]):
                        cmpr.num(w + f"/raw_part{i + 1}", v, t["raw_misses_descriptive"]["per_partition_ratio"][i])
                    cmpr.num(w + "/spread", m["per_cell_spread_mean"], t["spread"]["per_cell_spread_mean"])
                    cmpr.eq(w + "/lower_all_five", m["cells_S_B_lower_than_all_five"], t["spread"]["cells_S_B_lower_than_all_five"])
                    for L, v in m["null_denominators"].items():
                        cmpr.num(w + f"/nullden/{L}/mean", v["mean"], t["null_denominators"][L]["mean"])
                        cmpr.num(w + f"/nullden/{L}/min", v["min"], t["null_denominators"][L]["min"])
        # combined
    for K in TREES:
        th = an["combined"]["tree_kinds"][K]
        cmpr.eq(f"combined/{K}/outcome_A", REG["combined"][K]["A"], th["outcome_A"])
        cmpr.eq(f"combined/{K}/outcome_B", REG["combined"][K]["B"], th["outcome_B"])
        cmpr.eq(f"combined/{K}/pairing", REG["combined"][K]["pairing"], th["pairing"]["description"])
        cmpr.eq(f"combined/{K}/decision", REG["combined"][K]["decision_class"], th["decision_class"])
    cmpr.eq("combined/recommendation_row", REG["combined"]["recommendation_row"], an["combined"]["recommendation"]["row"])
    # descriptive
    for S in ("A", "B"):
        d, t = DESC[S], an["descriptive"][S]
        for k, v in d["co_access_gain"].items():
            if k in t["co_access_gain"]:
                cmpr.num(f"{S}/G/{k}/mor", v["mean_of_ratios"], t["co_access_gain"][k]["mean_of_ratios"])
                cmpr.num(f"{S}/G/{k}/rom", v["ratio_of_means"], t["co_access_gain"][k]["ratio_of_means"])
            else:
                cmpr.diffs.append({"where": f"{S}/G/{k}", "note": "not present in analysis.json"})
        for k, v in d["popularity_cost"].items():
            if k in t["popularity_cost"]:
                cmpr.num(f"{S}/PC/{k}/mor", v["mean_of_ratios"], t["popularity_cost"][k]["mean_of_ratios"])
                cmpr.num(f"{S}/PC/{k}/rom", v["ratio_of_means"], t["popularity_cost"][k]["ratio_of_means"])
            else:
                cmpr.diffs.append({"where": f"{S}/PC/{k}", "note": "not present in analysis.json"})
        for k, v in d["BC_K"].items():
            cmpr.num(f"{S}/BC/{k}", v["BC_ratio_of_means"], t["BC_K"][k]["BC"])
            cmpr.num(f"{S}/BCpart/{k}", v["partition_ratio_of_means"], t["BC_K"][k]["five_partition_counterpart"])
        for r in d["ncoax_control"]["rows"]:
            tr = [x for x in t["ncoax_control"]["rows"] if x["kind"] == r["kind"] and x["R"] == r["R"] and x["tie"] == r["tie"]][0]
            cmpr.num(f"{S}/NCOAX/{r['kind']}/R{r['R']}/{r['tie']}", r["G_mean_of_ratios"], tr["G_mean_of_ratios"])
            cmpr.eq(f"{S}/NCOAX/{r['kind']}/R{r['R']}/{r['tie']}/band", r["within_band"], tr["within_band"])
        cmpr.eq(f"{S}/NCOAX/flagged", d["ncoax_control"]["flagged"], an["ncoax_control_flagged"][S])
        for k, v in d["flat_partition_layouts"].items():
            for kk in v:
                cmpr.num(f"{S}/FP/{k}/{kk}", v[kk], t["flat_partition_layouts"][k][kk])
        for k, v in d["utilization"].items():
            for kk in v:
                cmpr.num(f"{S}/U/{k}/{kk}", v[kk], t["utilization"][k][kk])
        for k, v in d["calibration_transfer"].items():
            tk = t["calibration_transfer"].get(k)
            if tk is None:
                cmpr.diffs.append({"where": f"{S}/CT/{k}", "note": "not in analysis"})
                continue
            for kk in ("mean_m_calibration", "mean_m_evaluation", "evaluation_over_calibration"):
                cmpr.num(f"{S}/CT/{k}/{kk}", v[kk], tk[kk])
        for k, v in d["pages_and_misses"].items():
            kind, L, R, C, tie = k.split("|")
            if tie != "asc":
                continue
            tk = t["pages_and_misses"].get(f"{kind}|{L}|{R}")
            if tk is None:
                cmpr.diffs.append({"where": f"{S}/PM/{k}", "note": "not in analysis"})
                continue
            bc = tk["by_c"][C[1:]]
            for kk in ("warm_capacity_misses_per_query", "first_touch_misses_per_query_whole_stream",
                       "cold_misses_per_query_whole_stream", "cached_amplification_warm_capacity_misses",
                       "cached_amplification_all_warm_misses"):
                cmpr.num(f"{S}/PM/{k}/{kk}", v[kk], bc[kk])
            for i in range(7):
                cmpr.num(f"{S}/PM/{k}/q{i}", v["per_context_quantiles_mean"][i], bc["per_context_capacity_misses_quantiles_mean_over_checkpoints"][i])
            cmpr.num(f"{S}/PM/{k}/pages", v["mean_distinct_pages_per_query"], tk["mean_distinct_pages_per_query"])
            cmpr.num(f"{S}/PM/{k}/uncached", v["uncached_read_amplification"], tk["uncached_read_amplification"])
        # robustness grid
        for K in TREES:
            for e in t["robustness_grid"][K]:
                mine = d["robustness_grid_asc"][f"{K}|R{e['R']}|C{e['C']}"]
                for var in ("HB", "HU", "HB_A8", "HB_greedy", "HB_order_shuffled"):
                    if var not in e:
                        continue
                    w = f"{S}/grid/{K}/R{e['R']}C{e['C']}/{var}"
                    cmpr.eq(w + "/status", mine[var]["status"], e[var]["status"])
                    if e[var]["status"] == "NON-DEGENERATE" or mine[var]["status"] == "NON-DEGENERATE":
                        crit = {(2, 32): "primary", (8, 8): "confirmation"}.get((e["R"], e["C"]))
                        mine_cls = mine[var]["class"]
                        if crit and var in ("HB", "HU"):
                            mine_cls = REG[S][K][var][crit]  # both tie rules at the criterion settings
                        cmpr.eq(w + "/class", mine_cls, e[var]["class"])
                        cmpr.num(w + "/rho", mine[var].get("rho"), e[var].get("rho"))
                        cmpr.num(w + "/rho_adj", mine[var].get("rho_adj"), e[var].get("rho_adj"))
                        cmpr.eq(w + "/cells", mine[var].get("cells_tree_lower"), e[var].get("cells_tree_lower"))
                        cmpr.eq(w + "/parents", mine[var].get("parents_tree_lower"), e[var].get("parents_tree_lower"))
        # quality
        q = t["quality_vs_misses"]
        for k in KINDS:
            cmpr.num(f"{S}/Q/{k}/mean_nll", d["quality_vs_misses"]["per_kind_mean_nll"][k], q["per_kind"][k]["mean_nll"])
        for K in TREES:
            mp = d["quality_vs_misses"][f"{K}|paired_nll"]
            tp = q["paired_tree_minus_flat"][K]
            cmpr.num(f"{S}/Q/{K}/mean_diff", mp["mean_tree_minus_flat"], tp["mean_difference_nats_per_byte"])
            cmpr.eq(f"{S}/Q/{K}/within", mp["cells_abs_within_0.005"], tp["cells_absolute_difference_within_0.005"])
    # split half
    for k, v in SPLIT.items():
        t = an["split_half_stability"].get(k)
        if t is None:
            cmpr.diffs.append({"where": f"split/{k}", "note": "not in analysis"})
            continue
        cmpr.num(f"split/{k}/f01", v["mean_m_fit0_score1"], t["mean_m_fit0_score1"])
        cmpr.num(f"split/{k}/f10", v["mean_m_fit1_score0"], t["mean_m_fit1_score0"])
        cmpr.num(f"split/{k}/relmean", v["mean_rel_diff_over_pair_mean"], t["mean_relative_difference_between_directions"])
        cmpr.num(f"split/{k}/relmax", v["max_rel_diff_over_pair_mean"], t["max_relative_difference_between_directions"])


# ------------------------------------------------------------------------------------------------
def to_json(x):
    if isinstance(x, Fraction):
        return float(x)
    if isinstance(x, dict):
        return {str(k): to_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_json(v) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-traces", action="store_true")
    args = ap.parse_args()
    t0 = time.monotonic()
    repo = args.repo.resolve()
    streams = {S: Stream(repo, S) for S in ("A", "B")}
    lw = {}
    for p in sorted((repo / RUNS["layouts"] / "workers").glob("*.result.json")):
        d = json.loads(p.read_text())
        lw[d["label"]] = d
    p5nll = {lb: json.loads((repo / P5 / lb / "result.json").read_text())["final"]["nll"] for lb in streams["A"].labels}

    REG = {}
    for S, st in streams.items():
        REG[S] = {}
        for K in TREES:
            det = {"HB": {}, "HU": {}, "PART": {}}
            cls = {"HB": {}, "HU": {}, "PART": {}}
            for sname, (R, C) in SETTINGS.items():
                for comp, lt in (("HB", "L-BCOAX"), ("HU", "L-COAX")):
                    bt = {tie: compare(st, K, lt, "L-COAX", R, C, tie) for tie in TIES}
                    det[comp][sname] = bt
                    cls[comp][sname] = combine_ties(bt)
                pt = {tie: part_k(st, K, R, C, tie) for tie in TIES}
                det["PART"][sname] = pt
                if any(pt[t]["status"] == "DEGENERATE" for t in TIES):
                    cls["PART"][sname] = DEG
                elif all(pt[t]["better"] for t in TIES):
                    cls["PART"][sname] = RBB
                else:
                    cls["PART"][sname] = NB
            rho_pa = det["HB"]["primary"]["asc"]["rho"]
            REG[S][K] = {**cls, "detail": det, "primary_rho_ascending": rho_pa,
                         "outcome": outcome(cls["HB"], cls["PART"], rho_pa)}
    comb = {}
    for K in TREES:
        a, b = REG["A"][K]["outcome"], REG["B"][K]["outcome"]
        pr = pairing(a, b)
        comb[K] = {"A": a, "B": b, "pairing": pr if pr != "NOT REPLICATED" else "NOT REPLICATED",
                   "decision_class": decision_class(a, b)}
    row, rtext = recommendation([comb[K]["decision_class"] for K in TREES])
    comb["recommendation_row"] = row
    comb["recommendation_condition"] = rtext
    REG["combined"] = comb

    # sensitivity of x choice (entropy_nats vs ln(effective_slots))
    XS = {}
    for S, st in streams.items():
        for K in TREES:
            for sname, (R, C) in SETTINGS.items():
                for tie in TIES:
                    r = compare(st, K, "L-BCOAX", "L-COAX", R, C, tie, xsrc="ent")
                    XS[f"{S}|{K}|{sname}|{tie}"] = float(r["rho_adj"])

    DESC = {S: descriptive(st, repo, lw, p5nll) for S, st in streams.items()}
    labels_by_kind = {k: streams["A"].by_kind(k) for k in KINDS}
    SPLIT = split_half(lw, labels_by_kind)
    INTEG = integrity(repo, streams, lw, not args.skip_traces)
    RES = resources(repo)

    an = json.loads((repo / RUNS["analyze"] / "analysis.json").read_text())
    cmpr = Cmp()
    compare_with_analysis(an, REG, DESC, SPLIT, cmpr)

    # strip big per-cell lists to a compact per-cell table
    percell = {}
    for S, st in streams.items():
        for K in TREES:
            for sname in SETTINGS:
                for tie in TIES:
                    r = REG[S][K]["detail"]["HB"][sname][tie]
                    prs = pairs_of(st, K)
                    percell[f"{S}|{K}|HB|{sname}|{tie}"] = [
                        {"tree": t, "flat": f, "E_tree": float(et), "E_flat": float(ef)}
                        for (t, f), et, ef in zip(prs, r.pop("E_tree"), r.pop("E_flat"))]
                    r2 = REG[S][K]["detail"]["HU"][sname][tie]
                    r2.pop("E_tree", None)
                    r2.pop("E_flat", None)
    # per-checkpoint E table (criterion settings) for every stream/layout/tie
    perE = {}
    for S, st in streams.items():
        for lb in st.labels:
            row_ = {"kind": st.kind[lb], "effective_slots": st.eff[lb]}
            lays = ["L-ID", "L-RAND", "L-FREQ", "L-COAX", "L-NCOAX", "L-COAX8", "L-COAXg", *PARTS]
            if st.kind[lb] != "flat":
                lays += ["L-BFREQ", "L-BCOAX", "L-BCOAX8", "L-BCOAXg"]
            for sname, (R, C) in SETTINGS.items():
                for tie in TIES:
                    for L in lays:
                        e = st.E(lb, L, R, C, tie)
                        if e is not None:
                            row_[f"E|{L}|{sname}|{tie}"] = float(e)
                            row_[f"m|{L}|{sname}|{tie}"] = float(st.m(lb, "actual", L, R, C, tie))
                    row_[f"den|{sname}|{tie}"] = float(st.mnull(lb, "L-FREQ", R, C, tie))
            perE[f"{S}|{lb}"] = row_
    # m for every R, C, tie, layout, stream (counts form) is available in the records; here a count
    out = {
        "schema": "p7b-results-recompute-v1",
        "label": "independent engineering/mathematical evidence by the auditor role (Claude Opus 5.5); not Astra validation; not human approval",
        "python": sys.version,
        "tool_sha256": sha_file(Path(__file__)),
        "analysis_sha256": sha_file(repo / RUNS["analyze"] / "analysis.json"),
        "registered": to_json(REG),
        "x_source_sensitivity_rho_adj_with_entropy_nats": XS,
        "per_cell_HB": percell,
        "per_checkpoint_E_criterion_settings": perE,
        "descriptive": to_json(DESC),
        "split_half": to_json(SPLIT),
        "integrity": to_json(INTEG),
        "resources": RES,
        "comparison_with_analysis": {"values_compared": cmpr.n, "differences": cmpr.diffs[:400],
                                     "n_differences": len(cmpr.diffs), "max_relative_difference": cmpr.max_rel},
        "seconds": time.monotonic() - t0,
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"compared {cmpr.n} values; {len(cmpr.diffs)} differences; max rel {cmpr.max_rel:.3g}; "
          f"integrity problems {len(INTEG['problems'])}; {out['seconds']:.1f} s")
    for K in TREES:
        print(K, REG["A"][K]["HB"], REG["A"][K]["PART"], REG["A"][K]["outcome"], "|",
              REG["B"][K]["HB"], REG["B"][K]["PART"], REG["B"][K]["outcome"], "|", comb[K])
    print("recommendation row", row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
