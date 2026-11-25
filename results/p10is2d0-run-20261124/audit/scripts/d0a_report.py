# ruff: noqa
"""Audit D0: my readings (ADR-0035 sections 5.2, 5.3, 6, 7) from my own per-pass files. Stdlib only. Writes NEW files:
  audit_d0_out/auditor_results_<UTC>.json, audit_d0_out/auditor_report_<UTC>.txt, audit_d0_out/auditor_sha256_<UTC>.txt
Registered numbers used (taken from records, not recomputed here): S0 and teacher scores (G denominators), the registered M1 / M-append scores (F and
APPEND COST), and the comparator arms of section 12.

Usage: python3 -I d0a_report.py
"""
import hashlib
import json
import math
import time
from pathlib import Path

OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit_d0_out")
RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
CELLS = [(r, o) for r in range(3) for o in ("AB", "BA")]
PANEL = {"A": "E_A", "B": "E_B"}
FIRST = ["M1__reg", "app__a", "app__d1", "fin__a", "fin__b1", "fin__c", "fin__d1", "fin__e1", "fin__g1"]
SECOND = ["fin__a", "fin__b2", "fin__c", "fin__d2", "fin__e2", "fin__g2", "fin__e1"]
ORACLE = "ORACLE LINE (Part T): every pass is under the oracle route; task identity is given by rule, not learned."
TAG = "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL. AUDITOR'S INDEPENDENT RECOMPUTATION; not Astra validation, not human approval."


def fmean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs)


def contrast(x, y):
    """Paired per-item difference x - y: mean and standard error sd/sqrt(n), sd with n - 1."""
    d = [a - b for a, b in zip(x, y)]
    n = len(d)
    m = fmean(d)
    sd = math.sqrt(math.fsum((v - m) ** 2 for v in d) / (n - 1))
    return {"mean": m, "se": sd / math.sqrt(n)}


def main():
    reg = json.loads((RUN / "registry.json").read_text())
    s0 = {c: reg[f"S0|-|-|s:{PANEL[c]}"] for c in "AB"}
    te = {c: reg[f"TEACHER|-|-|s:{PANEL[c]}"] for c in "AB"}
    den = {c: te[c] - s0[c] for c in "AB"}

    def G(s, c):
        return (s - s0[c]) / den[c] if den[c] >= 0.30 else None

    missing, cells = [], {}
    for r, o in CELLS:
        f, s = o[0], o[1]
        P = {}
        for panel, names in (("first", FIRST), ("second", SECOND)):
            for n in names:
                p = OUT / "passes" / f"r{r}_{o}__{panel}__{n}.json"
                if not Path(str(p) + ".done").exists():
                    missing.append(p.name)
                    continue
                P[(panel, n)] = json.loads(p.read_text())
        st = OUT / "stats" / f"stats_r{r}_{o}.json"
        stats = json.loads(st.read_text()) if Path(str(st) + ".done").exists() else None
        if stats is None:
            missing.append(st.name)
        cells[(r, o)] = (P, stats)
    if missing:
        print("INCOMPLETE; missing:", missing)
        return

    res = {"tag": TAG, "oracle_line": ORACLE, "denominators": den, "s0": s0, "teacher": te, "cells": {}}
    words = {}
    for (r, o), (P, stats) in cells.items():
        f, sc = o[0], o[1]
        I = {k: v["items"] for k, v in P.items()}
        S = {k: fmean(v) for k, v in I.items()}
        seq = {k: v["sequences"] for k, v in P.items()}
        ref1, ref2 = seq[("first", "M1__reg")], seq[("second", "fin__a")]
        passes = {}
        for (panel, n), v in I.items():
            cap = f if panel == "first" else sc
            ref = ref1 if panel == "first" else ref2
            passes[f"{PANEL[cap]}|{n}"] = {"s": S[(panel, n)], "G": G(S[(panel, n)], cap),
                                          "share_differs_from_ref": fmean([1.0 if a != b else 0.0 for a, b in zip(seq[(panel, n)], ref)]),
                                          "ref": "M1 on E_first" if panel == "first" else "a on E_second"}
        x1 = lambda n: I[("first", n)]
        x2 = lambda n: I[("second", n)]
        F_reg = reg[f"M1|{o}|{r}|s:{PANEL[f]}"] - reg[f"M-append|{o}|{r}|s:{PANEL[f]}"]
        T = contrast(x1("fin__b1"), x1("fin__a"))
        t = T["mean"]
        terms = {
            "T": T,
            "i_slot_displacement": contrast(x1("fin__b1"), x1("fin__d1")),
            "ii_softmax_renormalisation": contrast(x1("fin__d1"), x1("fin__e1")),
            "iii_stage2_values": contrast(x1("fin__e1"), x1("fin__a")),
            "values_alone_b1_minus_g1": contrast(x1("fin__b1"), x1("fin__g1")),
            "competition_given_values_g1_minus_a": contrast(x1("fin__g1"), x1("fin__a")),
        }
        comp_path = terms["i_slot_displacement"]["mean"] + terms["ii_softmax_renormalisation"]["mean"]
        inter = terms["iii_stage2_values"]["mean"] - terms["values_alone_b1_minus_g1"]["mean"]
        dec1 = {k: {**v, "G_units": v["mean"] / den[f], "share_of_T": v["mean"] / t} for k, v in terms.items()}
        dec1["i_plus_ii"] = {"mean": comp_path, "G_units": comp_path / den[f], "share_of_T": comp_path / t}
        dec1["interaction_iii_minus_values_alone"] = {"mean": inter, "G_units": inter / den[f], "share_of_T": inter / t,
                                                      "paired": contrast([a - b - (c - d) for a, b, c, d in zip(x1("fin__e1"), x1("fin__a"), x1("fin__b1"), x1("fin__g1"))], [0.0] * 1000)}
        dec1["registered_F"] = F_reg
        dec1["iv_residual_F_minus_T"] = F_reg - t
        dec1["path_sum_minus_T"] = (terms["i_slot_displacement"]["mean"] + terms["ii_softmax_renormalisation"]["mean"] + terms["iii_stage2_values"]["mean"]) - t
        app = {"i_app": contrast(x1("M1__reg"), x1("app__d1")), "ii_app": contrast(x1("app__d1"), x1("app__a")),
               "M1_minus_a_app": contrast(x1("M1__reg"), x1("app__a"))}
        ia = app["i_app"]["mean"] + app["ii_app"]["mean"]
        app["i_plus_ii_app"] = ia
        app["i_plus_ii_final_minus_append"] = comp_path - ia
        app["G_units"] = {k: (v["mean"] if isinstance(v, dict) else v) / den[f] for k, v in app.items() if k != "G_units"}
        app["registered_append_cost_G"] = (reg[f"M-append@append|{o}|{r}|s:{PANEL[f]}"] - reg[f"M1|{o}|{r}|s:{PANEL[f]}"]) / den[f] if f"M-append@append|{o}|{r}|s:{PANEL[f]}" in reg else None
        app["mine_append_cost_G_a_app_minus_M1"] = (S[("first", "app__a")] - S[("first", "M1__reg")]) / den[f]
        T2 = contrast(x2("fin__b2"), x2("fin__a"))
        t2 = T2["mean"]
        terms2 = {"T2_b2_minus_a": T2, "i_b2_minus_d2": contrast(x2("fin__b2"), x2("fin__d2")), "ii_d2_minus_e2": contrast(x2("fin__d2"), x2("fin__e2")),
                  "iii_e2_minus_a": contrast(x2("fin__e2"), x2("fin__a")), "values_alone_b2_minus_g2": contrast(x2("fin__b2"), x2("fin__g2")),
                  "given_values_g2_minus_a": contrast(x2("fin__g2"), x2("fin__a")), "a_minus_e1_stage2_off": contrast(x2("fin__a"), x2("fin__e1")),
                  "a_minus_c_second_cost": contrast(x2("fin__a"), x2("fin__c"))}
        dec2 = {k: {**v, "G_units": v["mean"] / den[sc], "share_of_T2": (v["mean"] / t2) if t2 != 0 else None} for k, v in terms2.items()}
        dec2["interaction"] = terms2["iii_e2_minus_a"]["mean"] - terms2["values_alone_b2_minus_g2"]["mean"]
        gm1 = G(S[("first", "M1__reg")], f)
        evaluable = gm1 is not None and gm1 >= 0.50
        cf = {}
        for x in ("fin__c", "fin__g1"):
            Fx = S[("first", "M1__reg")] - S[("first", x)]
            rho = G(S[("first", x)], f) / gm1 if evaluable else None
            cf[x] = {"F_cf": Fx, "rho_cf": rho, "evaluable_G_first_M1": gm1,
                     "word": ("HOLDS" if (Fx <= 0.03 and rho >= 0.90) else "DOES NOT HOLD") if evaluable else "NOT EVALUABLE: FIRST NOT ACQUIRED",
                     "second_cost_s_a_minus_s_c": terms2["a_minus_c_second_cost"]["mean"], "G_second_under_c": G(S[("second", "fin__c")], sc),
                     "G_second_under_a": G(S[("second", "fin__a")], sc),
                     "auditor_extra_second_cost_s_a_minus_s_g2": S[("second", "fin__a")] - S[("second", "fin__g2")]}
        words[(r, o)] = {"T": t, "comp_path_share": comp_path / t, "values_path_share": terms["iii_stage2_values"]["mean"] / t,
                         "comp_vfirst_share": terms["competition_given_values_g1_minus_a"]["mean"] / t, "values_vfirst_share": terms["values_alone_b1_minus_g1"]["mean"] / t,
                         "interaction": inter, "abs_inter_ge_T_over_3": abs(inter) >= t / 3}
        # comparators, registered (taken from records)
        comp = {}
        for arm in ("M-append", "M1", "M-seq", "M-ii", "D-append", "D-seq", "D1"):
            for c in "AB":
                k = f"{arm}|{o}|{r}|s:{PANEL[c]}"
                if k in reg:
                    comp[k] = reg[k]
        for arm in ("M-sep", "D-sep", "M-joint", "D-joint", "E-table"):
            for c in "AB":
                k = f"{arm}|-|{r}|s:{PANEL[c]}"
                if k in reg:
                    comp[k] = reg[k]
        res["cells"][f"r{r}|{o}"] = {"first": f, "second": sc, "passes": passes, "decomposition_first": dec1, "append_point": app, "decomposition_second": dec2,
                                    "counterfactual_ret_arithmetic": cf, "shares": words[(r, o)], "read_statistics": stats, "registered_comparators": comp}

    def word(cshare, vshare):
        nc = sum(1 for k in words if words[k][cshare] >= 2 / 3)
        nv = sum(1 for k in words if words[k][vshare] >= 2 / 3)
        w = "COMPETITION-LARGER" if nc >= 5 else ("VALUES-LARGER" if nv >= 5 else "MIXED")
        if nc >= 5 and nv >= 5:
            w = "BOTH-CRITERIA-MET (ambiguous)"
        return w, nc, nv

    wp, ncp, nvp = word("comp_path_share", "values_path_share")
    wv, ncv, nvv = word("comp_vfirst_share", "values_vfirst_share")
    od = any(words[k]["abs_inter_ge_T_over_3"] for k in words) or wp != wv
    neg_T = [f"r{r}|{o}" for (r, o) in words if words[(r, o)]["T"] <= 0]
    res["summary"] = {"path_order_word": wp, "path_order_cells_comp_ge_2_3": ncp, "path_order_cells_values_ge_2_3": nvp,
                      "values_first_word": wv, "values_first_cells_comp_ge_2_3": ncv, "values_first_cells_values_ge_2_3": nvv,
                      "ORDER_DEPENDENT": od, "cells_with_T_le_0": neg_T}
    res["utc"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    # text report
    L = [TAG, ORACLE, ""]
    L.append(f"Denominators (teacher - S0, registered): E_A {den['A']:.6f}  E_B {den['B']:.6f}")
    for key, c in res["cells"].items():
        L.append("")
        L.append(f"=== cell {key} (first {c['first']}, second {c['second']}) ===   {TAG.split(';')[0]}")
        L.append("pass                          s            G         share_differs")
        for pk, pv in sorted(c["passes"].items()):
            L.append(f"  {pk:26s} {pv['s']:.9f}  {pv['G']:+.6f}  {pv['share_differs_from_ref']:.3f}")
        d = c["decomposition_first"]
        L.append("first capability, final store (s units; G units; share of T; paired SE in s):")
        for k in ("T", "i_slot_displacement", "ii_softmax_renormalisation", "iii_stage2_values", "i_plus_ii", "values_alone_b1_minus_g1", "competition_given_values_g1_minus_a", "interaction_iii_minus_values_alone"):
            v = d[k]
            se = v.get("se", v.get("paired", {}).get("se"))
            L.append(f"  {k:40s} {v['mean']:+.6f}  G {v['G_units']:+.6f}  share {v['share_of_T']:+.4f}  se {se if se is None else f'{se:.6f}'}")
        L.append(f"  registered F {d['registered_F']:+.9f}  (iv) F - T {d['iv_residual_F_minus_T']:+.3e}  path sum - T {d['path_sum_minus_T']:+.3e}")
        a = c["append_point"]
        L.append(f"append point: (i) {a['i_app']['mean']:+.6f} se {a['i_app']['se']:.6f}; (ii) {a['ii_app']['mean']:+.6f} se {a['ii_app']['se']:.6f}; (i)+(ii) {a['i_plus_ii_app']:+.6f}; final-minus-append (i)+(ii) {a['i_plus_ii_final_minus_append']:+.6f}")
        L.append(f"   APPEND COST in G: mine {a['mine_append_cost_G_a_app_minus_M1']:+.6f}  registered-record-derived {a['registered_append_cost_G'] if a['registered_append_cost_G'] is None else format(a['registered_append_cost_G'], '+.6f')}")
        d2 = c["decomposition_second"]
        L.append("second capability (effect of stage-1 rows on the second capability's read; not a retention loss):")
        for k, v in d2.items():
            if isinstance(v, dict):
                sh = v["share_of_T2"]
                L.append(f"  {k:32s} {v['mean']:+.6f}  G {v['G_units']:+.6f}  share {sh if sh is None else f'{sh:+.4f}'}  se {v['se']:.6f}")
        L.append(f"  interaction (iii2 - values alone) {d2['interaction']:+.6f}")
        for x, v in c["counterfactual_ret_arithmetic"].items():
            rho = v["rho_cf"]
            L.append(f"COUNTERFACTUAL RET ARITHMETIC [{x}]: {v['word']}  F_cf {v['F_cf']:+.6f}  rho_cf {rho if rho is None else f'{rho:.4f}'}  | second cost s[a]-s[c] {v['second_cost_s_a_minus_s_c']:+.6f}  G_second(c) {v['G_second_under_c']:+.6f}  G_second(a) {v['G_second_under_a']:+.6f}  (extra: s[a]-s[g2] {v['auditor_extra_second_cost_s_a_minus_s_g2']:+.6f})  -- not RET")
        L.append("registered comparators (from registry.json, not recomputed): " + "; ".join(f"{k} {v:.4f}" for k, v in c["registered_comparators"].items()))
        stt = c["read_statistics"]
        for where in ("append_first", "final_first", "final_second"):
            for kind in ("word", "marker"):
                L.append(f"  read stats {where}/{kind}: " + "; ".join(f"{k} mean {v['mean']:.4f} med {v['median_linear']:.4f} p5 {v['p05_linear']:.4f} p95 {v['p95_linear']:.4f}" for k, v in stt[where][kind].items()))
            L.append(f"  read stats {where}: g1 {stt[where]['g1']} g2 {stt[where]['g2']} tie-claim violations {stt[where]['G_cap_S_p_is_top_n_of_T8_violations']}")
    L.append("")
    sm = res["summary"]
    L.append(f"SUMMARY (path order): {sm['path_order_word']}  (cells with (i)+(ii) >= 2/3 T: {sm['path_order_cells_comp_ge_2_3']}; with (iii) >= 2/3 T: {sm['path_order_cells_values_ge_2_3']})")
    L.append(f"SUMMARY (values first): {sm['values_first_word']}  (competition-given-values >= 2/3 T: {sm['values_first_cells_comp_ge_2_3']}; values alone >= 2/3 T: {sm['values_first_cells_values_ge_2_3']})")
    L.append(f"ORDER-DEPENDENT: {sm['ORDER_DEPENDENT']}   cells with T <= 0: {sm['cells_with_T_le_0']}")
    L.append("per cell shares: " + "; ".join(f"r{r}|{o}: T {w['T']:+.5f} path comp {w['comp_path_share']:+.3f} vals {w['values_path_share']:+.3f} | vfirst comp {w['comp_vfirst_share']:+.3f} vals {w['values_vfirst_share']:+.3f} inter {w['interaction']:+.5f}" for (r, o), w in words.items()))
    L.append(TAG)
    jp = OUT / f"auditor_results_{res['utc']}.json"
    tp = OUT / f"auditor_report_{res['utc']}.txt"
    with open(jp, "x") as fh:
        json.dump(res, fh, indent=1)
    with open(tp, "x") as fh:
        fh.write("\n".join(L) + "\n")
    hp = OUT / f"auditor_sha256_{res['utc']}.txt"
    lines = []
    for p in [jp, tp] + sorted((OUT / "passes").glob("*.json")) + sorted((OUT / "stats").glob("*.json")) + sorted((OUT / "gate").glob("*.json")):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p}")
    with open(hp, "x") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(L))
    print("written", jp, tp, hp)


if __name__ == "__main__":
    main()
