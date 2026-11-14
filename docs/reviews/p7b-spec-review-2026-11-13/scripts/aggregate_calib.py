"""P7-B spec review, part B aggregation: summaries of outputs/calib_coaccess.json (calibration-only).

Standard library only. Usage (repo root):
  .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/aggregate_calib.py
Writes outputs/aggregate_calib.json and prints a compact table.
All quantities are on the CALIBRATION stream (in-sample or split-half) or on a reviewer-generated null
of the calibration stream. None is an ADR-0014 registered outcome on the evaluation stream.
"""

from __future__ import annotations

import json
import math
import statistics as st

OUT = "docs/reviews/p7b-spec-review-2026-11-13/outputs"
KINDS = ("flat", "fixed_tree", "learned_tree")
TREES = KINDS[1:]
SET = ("R2C32", "R8C8")


def pair(lb):
    b, o, *k, s = lb.split("-")
    return (b, o, s)


def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"mean": st.fmean(xs), "sd": st.stdev(xs) if len(xs) > 1 else 0.0, "min": min(xs), "max": max(xs), "n": len(xs)}


def ols_slope(x, y):
    mx, my = st.fmean(x), st.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    res = [c - my - b * (a - mx) for a, c in zip(x, y)]
    se = math.sqrt(sum(r * r for r in res) / (len(x) - 2) / sxx)
    return b, se


def compare(vals_t, vals_f, pairs_t, pairs_f):
    """ADR-0014 style classification applied to calibration-stream analogues (NOT the registered test)."""
    mt, mf = st.fmean(vals_t.values()), st.fmean(vals_f.values())
    rho = mt / mf
    lower = sum(vals_t[p] < vals_f[p] for p in vals_f)
    higher = sum(vals_t[p] > vals_f[p] for p in vals_f)
    par = {}
    for p in vals_f:
        par.setdefault(p[:2], []).append((vals_t[p], vals_f[p]))
    pl = sum(st.fmean(a for a, _ in v) < st.fmean(b for _, b in v) for v in par.values())
    ph = sum(st.fmean(a for a, _ in v) > st.fmean(b for _, b in v) for v in par.values())
    if rho <= 0.8 and lower >= 22 and pl >= 8:
        cls = "ADVANTAGE"
    elif rho >= 1.25 and higher >= 22 and ph >= 8:
        cls = "FLAT BETTER"
    elif 0.9 <= rho <= 1.1:
        cls = "EQUIVALENT"
    else:
        cls = "MARGINAL"
    return {"rho": rho, "tree_lower_pairs": lower, "tree_lower_parents": pl, "tree_higher_pairs": higher,
            "tree_higher_parents": ph, "class_if_registered_rule_applied": cls}


def main():
    D = json.load(open(f"{OUT}/calib_coaccess.json"))
    P = D["per_checkpoint"]
    assert D["eval_files_read"] == [] and D["n"] == 81
    by = {K: [r for r in P if r["kind"] == K] for K in KINDS}
    A = {"files_read_count": len(D["files_read"]), "eval_files_read": D["eval_files_read"], "wall_seconds": D["wall_seconds"]}

    # ---- sparsity
    sp = {}
    for K in KINDS:
        rs = by[K]
        sp[K] = {}
        for w in ("aff_W8", "aff_W0", "aff_W8_null", "aff_W0_null"):
            sp[K][w] = {k: summ([r[w][k] for r in rs]) for k in (
                "frac_of_all_pairs", "frac_of_used_pairs", "mean_degree_used", "frac_pairs_value_1",
                "frac_pairs_value_le2", "mass_share_top1pct_pairs", "mass_share_top10pct_pairs",
                "same_branch_mass_share", "used_slots")}
        sp[K]["tv_W8_actual_vs_null"] = summ([r["aff_W8_tv_actual_vs_null"] for r in rs])
        sp[K]["tv_W0_actual_vs_null"] = summ([r["aff_W0_tv_actual_vs_null"] for r in rs])
        sp[K]["calib_eff_slots"] = summ([r["calib_eff_slots"] for r in rs])
        sp[K]["within_page_mass_W8"] = {k: summ([r["within_page_mass_W8"].get(k) for r in rs])
                                        for k in rs[0]["within_page_mass_W8"]}
    A["sparsity"] = sp

    # ---- in-sample calibration quantities
    ins = {}
    for K in KINDS:
        rs = by[K]
        x = {}
        for s in SET:
            g = lambda r, key: r["insample"][key]
            m = lambda r, st_, L: r["insample"][f"{st_}|{L}|{s}"]
            d = {}
            lays = ["FREQ", "COAX", "COAX0", "COAXnullfit", "RPCOAX"] + (["BCOAX", "BCOAX0", "BFREQ", "BCOAX_idorder"] if K != "flat" else [])
            for L in lays:
                d[f"m_actual_{L}"] = summ([m(r, "actual", L) for r in rs])
                d[f"G_{L}=m(act,L)/m(act,FREQ)"] = summ([m(r, "actual", L) / m(r, "actual", "FREQ") for r in rs])
                d[f"Ecal_{L}=m(act,L)/m(null,FREQ)"] = summ([m(r, "actual", L) / m(r, "null", "FREQ") for r in rs])
            for L in ["COAX", "COAXnullfit", "RPCOAX"] + (["BCOAX", "BFREQ"] if K != "flat" else []):
                d[f"null_ratio_{L}=m(null,L)/m(null,FREQ)"] = summ([m(r, "null", L) / m(r, "null", "FREQ") for r in rs])
            d["m_null_FREQ"] = summ([m(r, "null", "FREQ") for r in rs])
            d["pages_reversed_COAX/COAX"] = summ([m(r, "actual", "COAX_pages_reversed") / m(r, "actual", "COAX") for r in rs])
            d["pages_reversed_FREQ/FREQ"] = summ([m(r, "actual", "FREQ_pages_reversed") / m(r, "actual", "FREQ") for r in rs])
            d["rows_reversed_COAX/COAX (must be 1)"] = summ([m(r, "actual", "COAX_rows_reversed") / m(r, "actual", "COAX") for r in rs])
            d["desc/asc COAX"] = summ([m(r, "actual_desc", "COAX") / m(r, "actual", "COAX") for r in rs])
            d["desc/asc FREQ"] = summ([m(r, "actual_desc", "FREQ") / m(r, "actual", "FREQ") for r in rs])
            if K != "flat":
                d["BC=m(BCOAX)/m(COAX)"] = summ([m(r, "actual", "BCOAX") / m(r, "actual", "COAX") for r in rs])
                d["pages_reversed_BCOAX/BCOAX"] = summ([m(r, "actual", "BCOAX_pages_reversed") / m(r, "actual", "BCOAX") for r in rs])
                d["BCOAX_idorder/BCOAX"] = summ([m(r, "actual", "BCOAX_idorder") / m(r, "actual", "BCOAX") for r in rs])
                d["desc/asc BCOAX"] = summ([m(r, "actual_desc", "BCOAX") / m(r, "actual", "BCOAX") for r in rs])
            x[s] = d
        x["eviction_age"] = {k: summ([r["eviction_age_queries"][k]["median"] for r in rs]) for k in rs[0]["eviction_age_queries"]}
        x["eviction_age_frac_le_8"] = {k: summ([r["eviction_age_queries"][k]["frac_le_8"] for r in rs]) for k in rs[0]["eviction_age_queries"]}
        x["greedy_ties"] = {k: summ([r["greedy_tie_stats"][k]["score_and_f_ties"] for r in rs]) for k in rs[0]["greedy_tie_stats"]}
        x["invariants"] = {"R1_coax_equals_freq": all(r["R1_coax_equals_freq"] for r in rs),
                           "zeroA_coax_equals_freq_R8": all(r["zeroA_coax_equals_freq_R8"] for r in rs),
                           "branch_membership_ok": all(r.get("branch_membership_ok", True) for r in rs)}
        ins[K] = x
    A["insample"] = ins

    # ---- calibration-stream analogues of the registered comparisons (in-sample; NOT the registered test)
    an = {}
    for s in SET:
        an[s] = {}
        f_by = {pair(r["label"]): r for r in by["flat"]}
        for K in TREES:
            t_by = {pair(r["label"]): r for r in by[K]}
            E = lambda r, L: r["insample"][f"actual|{L}|{s}"] / r["insample"][f"null|FREQ|{s}"]
            En = lambda r, L: r["insample"][f"null|{L}|{s}"] / r["insample"][f"null|FREQ|{s}"]
            an[s][K] = {
                "HB_cal": compare({p: E(t_by[p], "BCOAX") for p in t_by}, {p: E(f_by[p], "COAX") for p in f_by}, None, None),
                "HU_cal": compare({p: E(t_by[p], "COAX") for p in t_by}, {p: E(f_by[p], "COAX") for p in f_by}, None, None),
                "UTIL_cal(HB layouts)": compare({p: En(t_by[p], "BCOAX") for p in t_by}, {p: En(f_by[p], "COAX") for p in f_by}, None, None),
                "UTIL_cal(HU layouts)": compare({p: En(t_by[p], "COAX") for p in t_by}, {p: En(f_by[p], "COAX") for p in f_by}, None, None),
                "FREQ_vs_FREQ_cal": compare({p: E(t_by[p], "FREQ") for p in t_by}, {p: E(f_by[p], "FREQ") for p in f_by}, None, None),
                "nullfit_control_cal": compare({p: E(t_by[p], "COAXnullfit") for p in t_by}, {p: E(f_by[p], "COAXnullfit") for p in f_by}, None, None),
            }
    A["calibration_analogues_in_sample"] = an

    # ---- residual utilization trend of in-sample E (calibration) on log calibration eff slots
    tr = {}
    for s in SET:
        tr[s] = {}
        for L in ("FREQ", "COAX"):
            xs = [math.log(r["calib_eff_slots"]) for r in P]
            ys = [r["insample"][f"actual|{L}|{s}"] / r["insample"][f"null|FREQ|{s}"] for r in P]
            b, se = ols_slope(xs, ys)
            tr[s][f"pooled_E_{L}"] = {"slope_per_ln_eff": b, "se": se}
            for K in KINDS:
                xs = [math.log(r["calib_eff_slots"]) for r in by[K]]
                ys = [r["insample"][f"actual|{L}|{s}"] / r["insample"][f"null|FREQ|{s}"] for r in by[K]]
                b, se = ols_slope(xs, ys)
                tr[s][f"{K}_E_{L}"] = {"slope_per_ln_eff": b, "se": se}
        # trend of the null ratio of BCOAX (popularity penalty of the branch constraint) for trees
        for K in TREES:
            xs = [math.log(r["calib_eff_slots"]) for r in by[K]]
            ys = [r["insample"][f"null|BCOAX|{s}"] / r["insample"][f"null|FREQ|{s}"] for r in by[K]]
            b, se = ols_slope(xs, ys)
            tr[s][f"{K}_nullratio_BCOAX"] = {"slope_per_ln_eff": b, "se": se}
    A["trend_calibration"] = tr

    # ---- split-half transfer, layout lottery, local search
    sh = {}
    for K in KINDS:
        rs = by[K]
        lays = ["FREQ", "COAX", "COAX_LS"] + (["BFREQ", "BCOAX", "BCOAX_LS"] if K != "flat" else [])
        x = {}
        for s in SET:
            R = s.split("C")[0][1:]
            d = {}
            for L in lays:
                pen, lot, ins_ = [], [], []
                for r in rs:
                    m = lambda fit, ev: r["split"][f"m|{L}|fit{fit}|eval{ev}|{s}"]
                    # out-of-sample / in-sample on the same evaluation half, both directions
                    pen += [m("A", "B") / m("B", "B"), m("B", "A") / m("A", "A")]
                    lot.append(abs(math.log(m("A", "B") / m("B", "B"))) )
                    lot.append(abs(math.log(m("B", "A") / m("A", "A"))))
                d[f"{L}: out/in-sample"] = summ(pen)
                d[f"{L}: |log out/in|"] = summ(lot)
            # cross-fitted (honest) co-access gain vs FREQ and LS gain, per checkpoint averaged over directions
            def cross(r, L):
                return 0.5 * (r["split"][f"m|{L}|fitA|evalB|{s}"] + r["split"][f"m|{L}|fitB|evalA|{s}"])
            def insm(r, L):
                return 0.5 * (r["split"][f"m|{L}|fitA|evalA|{s}"] + r["split"][f"m|{L}|fitB|evalB|{s}"])
            d["cross G_COAX"] = summ([cross(r, "COAX") / cross(r, "FREQ") for r in rs])
            d["insample-half G_COAX"] = summ([insm(r, "COAX") / insm(r, "FREQ") for r in rs])
            d["cross LS/greedy COAX"] = summ([cross(r, "COAX_LS") / cross(r, "COAX") for r in rs])
            d["insample LS/greedy COAX"] = summ([insm(r, "COAX_LS") / insm(r, "COAX") for r in rs])
            d["wpm LS/greedy COAX (fit half)"] = summ([r["split"][f"wpm_fit|COAX_LS|A|R{R}"] / r["split"][f"wpm_fit|COAX|A|R{R}"] for r in rs])
            if K != "flat":
                d["cross G_BCOAX"] = summ([cross(r, "BCOAX") / cross(r, "FREQ") for r in rs])
                d["cross BC"] = summ([cross(r, "BCOAX") / cross(r, "COAX") for r in rs])
                d["cross LS/greedy BCOAX"] = summ([cross(r, "BCOAX_LS") / cross(r, "BCOAX") for r in rs])
                d["insample LS/greedy BCOAX"] = summ([insm(r, "BCOAX_LS") / insm(r, "BCOAX") for r in rs])
                d["cross BC with LS (BCOAX_LS/COAX_LS)"] = summ([cross(r, "BCOAX_LS") / cross(r, "COAX_LS") for r in rs])
                d["wpm LS/greedy BCOAX (fit half)"] = summ([r["split"][f"wpm_fit|BCOAX_LS|A|R{R}"] / r["split"][f"wpm_fit|BCOAX|A|R{R}"] for r in rs])
            x[s] = d
        x["ls_swaps"] = {k: summ([r["local_search"][k]["swaps"] for r in rs]) for k in rs[0]["local_search"]}
        x["ls_passes_max"] = max(v["passes"] for r in rs for v in r["local_search"].values())
        sh[K] = x
    A["split_half"] = sh

    # ---- cross-fitted analogue of HB with greedy vs with LS (split-half; NOT the registered test)
    cf = {}
    for s in SET:
        cf[s] = {}
        f_by = {pair(r["label"]): r for r in by["flat"]}
        for K in TREES:
            t_by = {pair(r["label"]): r for r in by[K]}
            c = lambda r, L: 0.5 * (r["split"][f"m|{L}|fitA|evalB|{s}"] + r["split"][f"m|{L}|fitB|evalA|{s}"])
            # normalise by the cross-fitted FREQ of the same checkpoint (no half-stream null available)
            cf[s][K] = {
                "G-ratio greedy: (BCOAX/FREQ)_tree / (COAX/FREQ)_flat": compare({p: c(t_by[p], "BCOAX") / c(t_by[p], "FREQ") for p in t_by}, {p: c(f_by[p], "COAX") / c(f_by[p], "FREQ") for p in f_by}, None, None),
                "G-ratio LS: (BCOAX_LS/FREQ)_tree / (COAX_LS/FREQ)_flat": compare({p: c(t_by[p], "BCOAX_LS") / c(t_by[p], "FREQ") for p in t_by}, {p: c(f_by[p], "COAX_LS") / c(f_by[p], "FREQ") for p in f_by}, None, None),
            }
    A["cross_fitted_gain_analogues"] = cf

    A["timing_seconds_per_checkpoint"] = {k: summ([r[k] for r in P]) for k in ("sec_affinity_W8", "sec_affinity_W0", "sec_greedy_layouts", "sec_split_half", "seconds")}
    with open(f"{OUT}/aggregate_calib.json", "w") as fh:
        json.dump(A, fh, indent=1, sort_keys=True)

    def pr(title, d, nd=3):
        def fmt(v):
            if isinstance(v, dict) and "mean" in v:
                return f"{v['mean']:.{nd}f} [{v['min']:.{nd}f},{v['max']:.{nd}f}] sd {v['sd']:.{nd}f}"
            if isinstance(v, float):
                return f"{v:.{nd}f}"
            return json.dumps(v)
        print(f"-- {title}")
        for k, v in d.items():
            print(f"   {k}: {fmt(v)}")
    for K in KINDS:
        print(f"===== {K}")
        for w in ("aff_W8", "aff_W0", "aff_W8_null"):
            pr(f"sparsity {w}", sp[K][w], 4)
        pr("tv / eff", {"tv_W8": sp[K]["tv_W8_actual_vs_null"], "tv_W0": sp[K]["tv_W0_actual_vs_null"], "eff": sp[K]["calib_eff_slots"]}, 3)
        for s in SET:
            pr(f"in-sample {s}", ins[K][s])
            pr(f"split-half {s}", sh[K][s])
        pr("eviction age median (queries)", ins[K]["eviction_age"], 2)
        pr("eviction age frac <= 8", ins[K]["eviction_age_frac_le_8"], 3)
        pr("greedy (score,f) ties", ins[K]["greedy_ties"], 1)
        print("   invariants", ins[K]["invariants"], "ls max passes", sh[K]["ls_passes_max"])
    print("===== calibration in-sample analogues (NOT registered tests)")
    for s in SET:
        for K in TREES:
            for k, v in an[s][K].items():
                print(f"   {s} {K} {k}: rho {v['rho']:.3f} lower {v['tree_lower_pairs']}/27 par {v['tree_lower_parents']}/9 higher {v['tree_higher_pairs']} -> {v['class_if_registered_rule_applied']}")
    print("===== cross-fitted gain analogues")
    for s in SET:
        for K in TREES:
            for k, v in cf[s][K].items():
                print(f"   {s} {K} {k}: rho {v['rho']:.3f} lower {v['tree_lower_pairs']}/27 par {v['tree_lower_parents']}/9 -> {v['class_if_registered_rule_applied']}")
    print("===== trends (slope of E per ln eff slots, calibration)")
    for s in SET:
        for k, v in tr[s].items():
            print(f"   {s} {k}: {v['slope_per_ln_eff']:+.4f} (se {v['se']:.4f})")
    pr("timing", A["timing_seconds_per_checkpoint"], 2)


if __name__ == "__main__":
    main()
