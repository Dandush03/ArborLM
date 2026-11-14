"""Aggregate calib_partitions.json (calibration stream only). Auditor's own code, stdlib only.

Usage: .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/rereview/scripts/aggregate_partitions.py
"""

import itertools
import json
import math
import statistics as st

OUT = "docs/reviews/p7b-spec-review-2026-11-13/rereview/outputs"
D = json.load(open(f"{OUT}/calib_partitions.json"))
assert D["eval_files_read"] == [] and not any("eval_" in x for x in D["files_read"])
CK = D["per_checkpoint"]
KINDS = ("flat", "fixed_tree", "learned_tree")
SET = ("R2C32", "R8C8")
TIE = ("asc", "desc")
REG = [f"P{i}" for i in range(1, 6)]
EXTRA = [f"X{s}" for s in range(91701, 91721)]
PROF = [f"M{s}" for s in range(91801, 91806)]


def parse(lb):
    b, o, *k, s = lb.split("-")
    return f"{b}-{o}", s, "-".join(k)


by = {}
for r in CK:
    par, seed, kind = parse(r["label"])
    by[(kind, par, seed)] = r
pairs = sorted({(p, s) for (_, p, s) in by})
assert len(pairs) == 27


def m(r, stream, lay, key, tie):
    return r["m"][f"{stream}|{lay}|{key}"][tie]


def ratio_counts(a, b):
    """a, b: dict pair->value. ratio of means, cells a<b, parents a<b."""
    ra = st.fmean(a.values()) / st.fmean(b.values())
    cells = sum(1 for k in a if a[k] < b[k])
    pars = sorted({p for p, _ in a})
    pa = sum(1 for p in pars if st.fmean(a[k] for k in a if k[0] == p) < st.fmean(b[k] for k in b if k[0] == p))
    return ra, cells, pa


res = {}
lines = []
P = lines.append
P("All quantities: calibration stream, in-sample (fit on all 512 contexts, warm 256, count 256), "
  "same-query affinity, greedy + registered refinement. NOT registered outcomes.")

# --- refinement
mx = max(v["passes"] for r in CK for v in r["refine"].values() if v)
nc = sum(1 for r in CK for v in r["refine"].values() if v and not v["converged"])
tot = sum(1 for r in CK for v in r["refine"].values() if v)
P(f"\nRefinement: {tot} layouts (R=2 and R=8), max passes used {mx}, not converged within 12: {nc}")
sw = {}
for r in CK:
    for k, v in r["refine"].items():
        if v:
            n = k.split("|")[0]
            n = "Pi" if n.startswith("P") else "Xi" if n.startswith("X") else "Mi" if n.startswith("M") else n
            sw.setdefault((n, k.split("|")[1]), []).append(v["swaps"])
for k, v in sorted(sw.items()):
    P(f"  swaps {k}: mean {st.fmean(v):.1f} max {max(v)}")
# refinement gain in misses: COAX vs COAXg
for key in SET:
    for kind in KINDS:
        g = [m(by[(kind, p, s)], "actual", "COAX", key, "asc") / m(by[(kind, p, s)], "actual", "COAXg", key, "asc") for p, s in pairs]
        P(f"  m(COAX refined)/m(greedy) {key} {kind}: {st.fmean(g):.4f} [{min(g):.3f},{max(g):.3f}]")

# --- PART analogue and partition spread (trees)
for key in SET:
    for tie in TIE:
        for kind in ("fixed_tree", "learned_tree"):
            rr = {k: by[(kind,) + k] for k in pairs}
            mB = {k: m(rr[k], "actual", "B", key, tie) for k in pairs}
            mPi = {pn: {k: m(rr[k], "actual", pn, key, tie) for k in pairs} for pn in REG}
            mP = {k: st.fmean(mPi[pn][k] for pn in REG) for k in pairs}
            r1, c1, p1 = ratio_counts(mB, mP)
            per = {pn: st.fmean(mB.values()) / st.fmean(mPi[pn].values()) for pn in REG}
            sd = [st.stdev([mPi[pn][k] for pn in REG]) for k in pairs]
            cv = [st.stdev([mPi[pn][k] for pn in REG]) / mP[k] for k in pairs]
            rng = [(max(mPi[pn][k] for pn in REG) - min(mPi[pn][k] for pn in REG)) / mP[k] for k in pairs]
            below_all = sum(1 for k in pairs if all(mB[k] < mPi[pn][k] for pn in REG))
            jensen = st.fmean(st.fmean(mB[k] / mPi[pn][k] for pn in REG) for k in pairs)
            cl1 = r1 <= 0.80 and c1 >= 22 and p1 >= 8
            cl2 = all(v <= 0.80 for v in per.values())
            # profile-matched partitions
            mM = {k: st.fmean(m(rr[k], "actual", pn, key, tie) for pn in PROF) for k in pairs}
            rM, cM, pM = ratio_counts(mB, mM)
            perM = [st.fmean(mB.values()) / st.fmean(m(rr[k], "actual", pn, key, tie) for k in pairs) for pn in PROF]
            cvM = [st.stdev([m(rr[k], "actual", pn, key, tie) for pn in PROF]) / mM[k] for k in pairs]
            # popularity cost and exploited structure (reviewer null, 1 replicate)
            def pc(lay):
                return st.fmean(m(rr[k], "null", lay, key, tie) / m(rr[k], "null", "FREQ", key, tie) for k in pairs)
            def ex(lays):
                return {k: st.fmean(m(rr[k], "actual", l, key, tie) for l in lays) / st.fmean(m(rr[k], "null", l, key, tie) for l in lays) for k in pairs}
            exB, exP, exM = ex(["B"]), ex(REG), ex(PROF)
            rexP = ratio_counts(exB, exP)
            rexM = ratio_counts(exB, exM)
            d = {"ratio_mB_meanmP": r1, "cells": c1, "parents": p1, "per_partition": per,
                 "min_per": min(per.values()), "max_per": max(per.values()),
                 "jensen_mean_of_ratios": jensen, "cv_mean": st.fmean(cv), "cv_median": st.median(cv),
                 "cv_max": max(cv), "sd_mean": st.fmean(sd), "range_over_mean_mean": st.fmean(rng),
                 "range_over_mean_max": max(rng), "cells_below_all_five": below_all,
                 "clause1": cl1, "clause2": cl2, "profile_ratio": rM, "profile_cells": cM,
                 "profile_parents": pM, "profile_per": perM, "profile_cv_mean": st.fmean(cvM),
                 "popcost_B": pc("B"), "popcost_Pmean": st.fmean(pc(pn) for pn in REG),
                 "popcost_Mmean": st.fmean(pc(pn) for pn in PROF),
                 "exploited_B_over_P": rexP, "exploited_B_over_M": rexM}
            res[f"PART|{key}|{tie}|{kind}"] = d

P("\nPART analogue (trees): m_B = L-BCOAX, m_P = mean of 5 registered partition layouts")
P("key tie kind | mean mB/mean mP  cells parents | per-partition min..max | Jensen | CV across 5 (mean/median/max) | range/mean (mean/max) | below all 5 | clause1 clause2")
for k, d in res.items():
    if k.startswith("PART"):
        P(f"{k[5:]:28s} | {d['ratio_mB_meanmP']:.3f} {d['cells']:2d}/27 {d['parents']}/9 | "
          f"{d['min_per']:.3f}..{d['max_per']:.3f} | {d['jensen_mean_of_ratios']:.3f} | "
          f"{d['cv_mean']:.3f}/{d['cv_median']:.3f}/{d['cv_max']:.3f} | {d['range_over_mean_mean']:.3f}/{d['range_over_mean_max']:.3f} | "
          f"{d['cells_below_all_five']:2d} | {d['clause1']} {d['clause2']}")
P("\nStronger nulls (trees): profile-matched partitions (branch popularity profile kept, membership scrambled in 16-rank bins), and 'exploited structure' m(actual,L)/m(null,L)")
P("key tie kind | mB/mean mM cells parents | per-M min..max | CV(M) | pop.cost B / P / M | exploited B/P (ratio, cells, parents) | exploited B/M")
for k, d in res.items():
    if k.startswith("PART"):
        e1, e2 = d["exploited_B_over_P"], d["exploited_B_over_M"]
        P(f"{k[5:]:28s} | {d['profile_ratio']:.3f} {d['profile_cells']:2d}/27 {d['profile_parents']}/9 | "
          f"{min(d['profile_per']):.3f}..{max(d['profile_per']):.3f} | {d['profile_cv_mean']:.3f} | "
          f"{d['popcost_B']:.3f} / {d['popcost_Pmean']:.3f} / {d['popcost_Mmean']:.3f} | "
          f"{e1[0]:.3f} {e1[1]}/27 {e1[2]}/9 | {e2[0]:.3f} {e2[1]}/27 {e2[2]}/9")

# --- operating characteristics over 25 random partitions (5 registered + 20 reviewer)
P("\nOperating characteristics, trees: all C(25,5) = 53,130 five-subsets of 25 random partitions")
P("key tie kind | per-partition aggregate ratio over 25: mean, SD, min, max | P(clause1) P(clause2) P(disagree) | subset-mean ratio: min..max")
for key in SET:
    for tie in TIE:
        for kind in ("fixed_tree", "learned_tree"):
            rr = {k: by[(kind,) + k] for k in pairs}
            pool = REG + EXTRA
            mB = [m(rr[k], "actual", "B", key, tie) for k in pairs]
            M = {pn: [m(rr[k], "actual", pn, key, tie) for k in pairs] for pn in pool}
            mBbar = st.fmean(mB)
            agg = {pn: mBbar / st.fmean(M[pn]) for pn in pool}
            n1 = n2 = dis = 0
            lo, hi = 9, 0
            pars = sorted({p for p, _ in pairs})
            pidx = {p: [i for i, (pp, _) in enumerate(pairs) if pp == p] for p in pars}
            for sub in itertools.combinations(pool, 5):
                mp = [st.fmean(M[pn][i] for pn in sub) for i in range(27)]
                r = mBbar / st.fmean(mp)
                lo, hi = min(lo, r), max(hi, r)
                cells = sum(1 for i in range(27) if mB[i] < mp[i])
                pp = sum(1 for p in pars if st.fmean(mB[i] for i in pidx[p]) < st.fmean(mp[i] for i in pidx[p]))
                c1 = r <= 0.8 and cells >= 22 and pp >= 8
                c2 = all(agg[pn] <= 0.8 for pn in sub)
                n1 += c1
                n2 += c2
                dis += c1 != c2
            N = math.comb(25, 5)
            v = list(agg.values())
            res[f"OC|{key}|{tie}|{kind}"] = {"agg_mean": st.fmean(v), "agg_sd": st.stdev(v), "agg_min": min(v),
                                             "agg_max": max(v), "p_clause1": n1 / N, "p_clause2": n2 / N,
                                             "p_disagree": dis / N, "subset_min": lo, "subset_max": hi}
            d = res[f"OC|{key}|{tie}|{kind}"]
            P(f"{key} {tie} {kind:12s} | {d['agg_mean']:.3f} {d['agg_sd']:.4f} {d['agg_min']:.3f} {d['agg_max']:.3f} | "
              f"{d['p_clause1']:.3f} {d['p_clause2']:.3f} {d['p_disagree']:.3f} | {lo:.3f}..{hi:.3f}")

# --- flat: partition layouts against L-COAX
P("\nFlat checkpoints: m(partition)/m(L-COAX), ratio of means, per registered partition and CV across five")
for key in SET:
    for tie in TIE:
        rr = {k: by[("flat",) + k] for k in pairs}
        c = st.fmean(m(rr[k], "actual", "COAX", key, tie) for k in pairs)
        per = [st.fmean(m(rr[k], "actual", pn, key, tie) for k in pairs) / c for pn in REG]
        cv = st.fmean(st.stdev([m(rr[k], "actual", pn, key, tie) for pn in REG]) / st.fmean(m(rr[k], "actual", pn, key, tie) for pn in REG) for k in pairs)
        P(f"  {key} {tie}: per-partition {', '.join(f'{x:.3f}' for x in per)}; CV mean {cv:.3f}")
        res[f"FLATP|{key}|{tie}"] = {"per": per, "cv_mean": cv}

# --- HB / HU analogues with raw and utilization-adjusted ratio
def ols(rows):
    """rows: (E, x, tree). OLS E = a + b x + d tree. Returns a, b, d, se_b."""
    n = len(rows)
    X = [(1.0, x, t) for _, x, t in rows]
    y = [e for e, _, _ in rows]
    XtX = [[sum(X[k][i] * X[k][j] for k in range(n)) for j in range(3)] for i in range(3)]
    Xty = [sum(X[k][i] * y[k] for k in range(n)) for i in range(3)]
    # 3x3 inverse
    a = XtX
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    inv = [[0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            mnr = [[a[r][c] for c in range(3) if c != i] for r in range(3) if r != j]
            inv[i][j] = (-1) ** (i + j) * (mnr[0][0] * mnr[1][1] - mnr[0][1] * mnr[1][0]) / det
    beta = [sum(inv[i][j] * Xty[j] for j in range(3)) for i in range(3)]
    resid = [y[k] - sum(beta[i] * X[k][i] for i in range(3)) for k in range(n)]
    s2 = sum(r * r for r in resid) / (n - 3)
    return beta[0], beta[1], beta[2], math.sqrt(s2 * inv[1][1])


def classify(rho, rad, cells, pars):
    if rho <= 0.80 and rad <= 0.80 and cells[0] >= 22 and pars[0] >= 8:
        return "TREE MATERIALLY BETTER"
    if rho >= 1.25 and rad >= 1.25 and cells[1] >= 22 and pars[1] >= 8:
        return "FLAT MATERIALLY BETTER"
    if 0.90 <= rho <= 1.10 and 0.90 <= rad <= 1.10:
        return "WITHIN 10%"
    return "INTERMEDIATE"


P("\nHB/HU calibration analogues (E = m(actual, L)/m(reviewer null, L-FREQ), x = ln calibration effective slots)")
P("comp key tie kind | rho cells(tree<) parents | b (SE) | a+b*xbar | rho_adj | per-arch slope flat / tree | class")
for comp, tl in (("HB", "B"), ("HU", "COAX")):
    for key in SET:
        for tie in TIE:
            for kind in ("fixed_tree", "learned_tree"):
                Et, Ef, rows = {}, {}, []
                slope = {}
                for k in pairs:
                    for kd, lay, dst in ((kind, tl, Et), ("flat", "COAX", Ef)):
                        r = by[(kd,) + k]
                        e = m(r, "actual", lay, key, tie) / m(r, "null", "FREQ", key, tie)
                        dst[k] = e
                        rows.append((e, math.log(r["eff_slots"]), 1 if kd != "flat" else 0))
                rho = st.fmean(Et.values()) / st.fmean(Ef.values())
                ct = sum(1 for k in pairs if Et[k] < Ef[k])
                cf = sum(1 for k in pairs if Ef[k] < Et[k])
                pars = sorted({p for p, _ in pairs})
                pt = sum(1 for p in pars if st.fmean(Et[k] for k in pairs if k[0] == p) < st.fmean(Ef[k] for k in pairs if k[0] == p))
                pf = sum(1 for p in pars if st.fmean(Ef[k] for k in pairs if k[0] == p) < st.fmean(Et[k] for k in pairs if k[0] == p))
                a, b, dd, seb = ols(rows)
                xbar = st.fmean(x for _, x, _ in rows)
                den = a + b * xbar
                rad = (den + dd) / den
                for t in (0, 1):
                    sub = [(e, x) for e, x, tt in rows if tt == t]
                    mx_ = st.fmean(x for _, x in sub)
                    me = st.fmean(e for e, _ in sub)
                    slope[t] = sum((x - mx_) * (e - me) for e, x in sub) / sum((x - mx_) ** 2 for _, x in sub)
                cls = classify(rho, rad, (ct, cf), (pt, pf))
                res[f"{comp}|{key}|{tie}|{kind}"] = {"rho": rho, "rho_adj": rad, "b": b, "se_b": seb, "den": den,
                                                     "slope_flat": slope[0], "slope_tree": slope[1],
                                                     "tree_lower_cells": ct, "tree_lower_parents": pt, "class": cls}
                P(f"{comp} {key} {tie} {kind:12s} | {rho:.3f} {ct:2d}/27 {pt}/9 | {b:+.3f} ({seb:.3f}) | {den:.3f} | "
                  f"{rad:.3f} | {slope[0]:+.3f} / {slope[1]:+.3f} | {cls}")

json.dump(res, open(f"{OUT}/aggregate_partitions.json", "w"), indent=1, sort_keys=True)
open(f"{OUT}/aggregate_partitions.log", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
