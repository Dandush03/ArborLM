"""P7-B spec review, part A: what the PUBLISHED P7-A records say about the proposed E normalization.

Auditor role (Claude Opus 5.5). Standard library only; no arborlm import; no P7-A analysis code reused.
Reads only: results/p7a-2026-11-13/simulate/<run>/workers/*.result.json (published per-checkpoint
records) and results/p5-2026-11-13/<label>/result.json (published P5 effective slots / NLL).
Reads NO trace file (neither calibration nor evaluation).

Quantities computed are all P7-A layouts (L-FREQ, L-BFREQ, L-ID) already published. No co-access layout
exists here and none of ADR-0014's registered outcomes (E under L-COAX/L-BCOAX, rho of HB/HU/UTIL, BC,
co-access gain) is computed.

  E_FREQ(c) = m_c(actual, L-FREQ) / mean_s m_c(FM_s, L-FREQ)   (the P7-A "actual/FM" ratio)
  E_BFREQ(c) = m_c(actual, L-FREQ-branch) / mean_s m_c(FM_s, L-FREQ)  (trees; published-derived)

Usage (repo root):  python3 -I docs/reviews/p7b-spec-review-2026-11-13/scripts/published_ratio.py
Independent engineering evidence; not Astra validation; not human approval.
"""

from __future__ import annotations

import glob
import json
import math
import os
import statistics as st
import sys

RES = "results/p7a-2026-11-13/simulate/P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b/workers"
P5 = "results/p5-2026-11-13"
FM = ("freq_matched_1", "freq_matched_2", "freq_matched_3")
KINDS = ("flat", "fixed_tree", "learned_tree")
WARM_Q = 16384
SETTINGS = [(2, 32), (8, 8)]
GRID = [(r, c) for r in (1, 2, 8, 32, 128, 512) for c in (8, 16, 32, 64, 128)]


def parse(label):
    b, o, *k, s = label.split("-")
    return (int(b[1:]), int(o[1:]), int(s[1:])), "-".join(k)


def cap(rec, stream, layout, R, C):
    e = rec["streams"][stream][f"{layout}|R{R}"]["by_c"][str(C)]
    return (e["misses_warm"] - e["first_touch_warm"]) / WARM_Q


def ols(x, y):
    mx, my = st.fmean(x), st.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    b = sxy / sxx
    a = my - b * mx
    res = [yy - a - b * xx for xx, yy in zip(x, y)]
    ss_tot = sum((yy - my) ** 2 for yy in y)
    r2 = 1 - sum(r * r for r in res) / ss_tot if ss_tot > 0 else None
    # slope standard error
    se = math.sqrt(sum(r * r for r in res) / (len(x) - 2) / sxx) if len(x) > 2 else None
    return {"intercept": a, "slope": b, "slope_se": se, "r2": r2}


def ancova(groups):
    """common slope, separate intercepts; groups: {K: [(x,y)]}"""
    sxx = sxy = 0.0
    means = {}
    for K, pts in groups.items():
        mx = st.fmean(p[0] for p in pts)
        my = st.fmean(p[1] for p in pts)
        means[K] = (mx, my)
        sxx += sum((p[0] - mx) ** 2 for p in pts)
        sxy += sum((p[0] - mx) * (p[1] - my) for p in pts)
    b = sxy / sxx
    return b, {K: means[K][1] - b * means[K][0] for K in groups}, means


def main():
    recs = {}
    for p in sorted(glob.glob(f"{RES}/*.result.json")):
        d = json.load(open(p))
        recs[d["label"]] = d["record"]
    assert len(recs) == 81
    eff, nll = {}, {}
    for lb in recs:
        f = json.load(open(f"{P5}/{lb}/result.json"))["final"]
        eff[lb] = f["retrieval"]["effective_selected_slots"]
        nll[lb] = f["nll"]
    by = {K: sorted([lb for lb in recs if parse(lb)[1] == K], key=lambda x: parse(x)[0]) for K in KINDS}
    pair_of = {lb: parse(lb)[0] for lb in recs}
    out = {"inputs": {"sim_workers": RES, "p5": P5, "traces_read": "none"}, "settings": {}}

    for R, C in SETTINGS + [g for g in GRID if g not in SETTINGS]:
        key = f"R{R}C{C}"
        S = {"per_checkpoint": {}}
        ok = True
        for lb, rec in recs.items():
            mact = cap(rec, "actual", "L-FREQ", R, C)
            mnull = st.fmean(cap(rec, s, "L-FREQ", R, C) for s in FM)
            row = {"kind": parse(lb)[1], "eff": eff[lb], "m_act_FREQ": mact, "m_null_FREQ": mnull,
                   "m_act_ID": cap(rec, "actual", "L-ID", R, C)}
            row["E_FREQ"] = mact / mnull if mnull > 0 else None
            if parse(lb)[1] != "flat":
                mb = cap(rec, "actual", "L-BFREQ", R, C)
                row["m_act_BFREQ"] = mb
                row["E_BFREQ"] = mb / mnull if mnull > 0 else None
            S["per_checkpoint"][lb] = row
            if mnull <= 0:
                ok = False
        pc = S["per_checkpoint"]
        S["null_mean"] = {K: st.fmean(pc[lb]["m_null_FREQ"] for lb in by[K]) for K in KINDS}
        S["null_min"] = {K: min(pc[lb]["m_null_FREQ"] for lb in by[K]) for K in KINDS}
        S["null_floor_violations_0.005"] = {K: sum(pc[lb]["m_null_FREQ"] < 0.005 for lb in by[K]) for K in KINDS}
        S["nondegenerate_by_ADR14_floors"] = {
            K: (S["null_mean"]["flat"] >= 0.05 and S["null_mean"][K] >= 0.01
                and all(pc[lb]["m_null_FREQ"] >= 0.005 for lb in by["flat"] + by[K]))
            for K in KINDS[1:]}
        if not ok or (R, C) not in SETTINGS:
            out["settings"][key] = {k: v for k, v in S.items() if k != "per_checkpoint"}
            continue
        E = {K: [pc[lb]["E_FREQ"] for lb in by[K]] for K in KINDS}
        S["E_FREQ_mean"] = {K: st.fmean(E[K]) for K in KINDS}
        S["E_FREQ_sd"] = {K: st.stdev(E[K]) for K in KINDS}
        S["E_FREQ_minmax"] = {K: [min(E[K]), max(E[K])] for K in KINDS}
        # rho under L-FREQ for both sides (NOT a registered comparison; shows the baseline offset)
        S["rho_FREQ_vs_FREQ"] = {K: S["E_FREQ_mean"][K] / S["E_FREQ_mean"]["flat"] for K in KINDS[1:]}
        # alternative aggregates
        S["rho_alt"] = {}
        for K in KINDS[1:]:
            num_t = sum(pc[lb]["m_act_FREQ"] for lb in by[K]) / sum(pc[lb]["m_null_FREQ"] for lb in by[K])
            num_f = sum(pc[lb]["m_act_FREQ"] for lb in by["flat"]) / sum(pc[lb]["m_null_FREQ"] for lb in by["flat"])
            gm = lambda xs: math.exp(st.fmean(math.log(x) for x in xs))
            S["rho_alt"][K] = {"ratio_of_mean_E": S["rho_FREQ_vs_FREQ"][K],
                               "ratio_of_pooled_ratios": num_t / num_f,
                               "ratio_of_geometric_means": gm(E[K]) / gm(E["flat"])}
        # pair counts (tree E strictly lower than paired flat E) and parents
        S["pairs_tree_lower_FREQ"] = {}
        S["paired_log_ratio"] = {}
        for K in KINDS[1:]:
            fl = {pair_of[lb]: pc[lb]["E_FREQ"] for lb in by["flat"]}
            tr = {pair_of[lb]: pc[lb]["E_FREQ"] for lb in by[K]}
            lr = [math.log(tr[p] / fl[p]) for p in fl]
            par = {}
            for p in fl:
                par.setdefault(p[:2], []).append((tr[p], fl[p]))
            S["pairs_tree_lower_FREQ"][K] = {
                "pairs": sum(tr[p] < fl[p] for p in fl),
                "parents": sum(st.fmean(a for a, _ in v) < st.fmean(b for _, b in v) for v in par.values())}
            S["paired_log_ratio"][K] = {"mean": st.fmean(lr), "sd": st.stdev(lr),
                                         "se_naive": st.stdev(lr) / math.sqrt(len(lr))}
        # residual trend of E_FREQ with utilization
        S["trend"] = {}
        for K in KINDS:
            x = [math.log(pc[lb]["eff"]) for lb in by[K]]
            y = [pc[lb]["E_FREQ"] for lb in by[K]]
            S["trend"][K] = {"E_on_log_eff": ols(x, y),
                             "E_on_nullm": ols([pc[lb]["m_null_FREQ"] for lb in by[K]], y)}
        X = [math.log(pc[lb]["eff"]) for lb in recs]
        Y = [pc[lb]["E_FREQ"] for lb in recs]
        S["trend"]["pooled"] = {"E_on_log_eff": ols(X, Y),
                                "E_on_nullm": ols([pc[lb]["m_null_FREQ"] for lb in recs], Y)}
        b, inter, means = ancova({K: [(math.log(pc[lb]["eff"]), pc[lb]["E_FREQ"]) for lb in by[K]] for K in KINDS})
        xbar = st.fmean(X)
        adj = {K: inter[K] + b * xbar for K in KINDS}
        S["trend"]["ancova_common_slope"] = b
        S["trend"]["adjusted_mean_E_at_pooled_mean_log_eff"] = adj
        S["trend"]["adjusted_rho"] = {K: adj[K] / adj["flat"] for K in KINDS[1:]}
        # predicted rho from utilization alone: pooled fit (no arch term) evaluated at each arch's mean log eff
        pf = S["trend"]["pooled"]["E_on_log_eff"]
        pred = {K: pf["intercept"] + pf["slope"] * means[K][0] for K in KINDS}
        S["trend"]["rho_predicted_by_pooled_utilization_fit"] = {K: pred[K] / pred["flat"] for K in KINDS[1:]}
        # E_BFREQ for trees vs E_FREQ flat (published-derived; NOT a registered P7-B quantity)
        S["E_BFREQ_mean"] = {K: st.fmean(pc[lb]["E_BFREQ"] for lb in by[K]) for K in KINDS[1:]}
        S["rho_treeBFREQ_vs_flatFREQ"] = {K: S["E_BFREQ_mean"][K] / S["E_FREQ_mean"]["flat"] for K in KINDS[1:]}
        S["pairs_treeBFREQ_lower_than_flatFREQ"] = {}
        for K in KINDS[1:]:
            fl = {pair_of[lb]: pc[lb]["E_FREQ"] for lb in by["flat"]}
            tr = {pair_of[lb]: pc[lb]["E_BFREQ"] for lb in by[K]}
            par = {}
            for p in fl:
                par.setdefault(p[:2], []).append((tr[p], fl[p]))
            S["pairs_treeBFREQ_lower_than_flatFREQ"][K] = {
                "pairs": sum(tr[p] < fl[p] for p in fl),
                "parents": sum(st.fmean(a for a, _ in v) < st.fmean(b for _, b in v) for v in par.values())}
        out["settings"][key] = S
    out["eff_slots_range"] = {K: [min(eff[lb] for lb in by[K]), st.fmean(eff[lb] for lb in by[K]), max(eff[lb] for lb in by[K])] for K in KINDS}
    os.makedirs("docs/reviews/p7b-spec-review-2026-11-13/outputs", exist_ok=True)
    with open("docs/reviews/p7b-spec-review-2026-11-13/outputs/published_ratio.json", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    # compact print
    for key in ("R2C32", "R8C8"):
        S = out["settings"][key]
        print(f"== {key}")
        for k in ("null_mean", "null_min", "null_floor_violations_0.005", "nondegenerate_by_ADR14_floors",
                  "E_FREQ_mean", "E_FREQ_sd", "E_FREQ_minmax", "rho_FREQ_vs_FREQ", "rho_alt",
                  "pairs_tree_lower_FREQ", "paired_log_ratio", "E_BFREQ_mean", "rho_treeBFREQ_vs_flatFREQ",
                  "pairs_treeBFREQ_lower_than_flatFREQ"):
            print(" ", k, json.dumps(S[k]))
        for K in KINDS + ("pooled",):
            t = S["trend"][K]["E_on_log_eff"]
            print(f"  trend {K}: slope {t['slope']:+.4f} (se {t['slope_se']:.4f}) per ln(eff), r2 {t['r2']:.3f}")
        print("  ancova slope", round(S["trend"]["ancova_common_slope"], 4), "adjusted rho",
              json.dumps(S["trend"]["adjusted_rho"]), "rho predicted by utilization alone",
              json.dumps(S["trend"]["rho_predicted_by_pooled_utilization_fit"]))
    print("== non-degeneracy over the grid (ADR-0014 floors, L-FREQ null)")
    for key, S in out["settings"].items():
        print(f"  {key}: null_mean {json.dumps({k: round(v, 4) for k, v in S['null_mean'].items()})} "
              f"min {json.dumps({k: round(v, 4) for k, v in S['null_min'].items()})} nondeg {json.dumps(S['nondegenerate_by_ADR14_floors'])}")
    print("eff slots", json.dumps(out["eff_slots_range"]))


if __name__ == "__main__":
    sys.exit(main())
