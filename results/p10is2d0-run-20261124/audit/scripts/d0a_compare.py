# ruff: noqa
"""Audit D0 #2: compare my recomputation (audit_d0_out) with the implementer's run (P10IS2D0-run-20261124). Stdlib only; read-only on both.

Compared:
  1. 96 counted passes + 24 reproduction passes: greedy sequences (exact), 1,000 item scores (|diff| <= 1e-6); also the stored pass mean.
  2. records/readings.json per cell: every pass s, G, share differing; T, (i), (ii), (iii), residual, values-first terms, interaction, shares, G units,
     standard errors; append point; second-capability block; counterfactual RET for c and g(1); registered scale; words.
  3. records/stats.json (and stats/S__*.json): read statistics against mine (means, medians, p5, p95; n; gates).
Tolerances: items 1e-6 (ADR 8.4); derived readings from item scores 1e-9 absolute (both sides average the same 1,000 floats); read statistics 1e-6
(float32 reads). Every difference over its tolerance is listed with both values; maxima are printed for every class.

Usage: python3 -I d0a_compare.py -> audit_d0_out/compare_<UTC>.json
"""
import glob
import json
import math
import time
from pathlib import Path

MINE = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit_d0_out")
IMPL = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2D0-run-20261124")
RES = "auditor_results_20261125T071351Z.json"
CELLS = [(r, o) for r in range(3) for o in ("AB", "BA")]
STORE = {"M1": "M1", "append": "app", "final": "fin"}
TOL_ITEM, TOL_DER, TOL_STAT = 1e-6, 1e-9, 1e-6

diffs = []
maxima = {}
counts = {}


def note(cls, d):
    maxima[cls] = max(maxima.get(cls, 0.0), d)
    counts[cls] = counts.get(cls, 0) + 1


def cmpnum(cls, where, mine, theirs, tol):
    if mine is None or theirs is None:
        if mine is not None or theirs is not None:
            diffs.append({"class": cls, "where": where, "mine": mine, "theirs": theirs, "why": "one side missing"})
        return
    if isinstance(mine, bool) or isinstance(theirs, bool):
        if mine != theirs:
            diffs.append({"class": cls, "where": where, "mine": mine, "theirs": theirs})
        return
    d = abs(mine - theirs)
    if not math.isfinite(d):
        diffs.append({"class": cls, "where": where, "mine": mine, "theirs": theirs, "why": "nonfinite"})
        return
    note(cls, d)
    if d > tol:
        diffs.append({"class": cls, "where": where, "mine": mine, "theirs": theirs, "diff": d})


def cmp_pass(where, mine, theirs):
    if len(mine["items"]) != len(theirs["items"]) or len(theirs["items"]) != 1000:
        diffs.append({"class": "pass", "where": where, "why": "item count", "mine": len(mine["items"]), "theirs": len(theirs["items"])})
        return 0
    nseq = sum(1 for a, b in zip(mine["sequences"], theirs["sequences"]) if a != b)
    counts["sequences"] = counts.get("sequences", 0) + 1000
    if nseq:
        bad = [i for i, (a, b) in enumerate(zip(mine["sequences"], theirs["sequences"])) if a != b]
        diffs.append({"class": "sequence", "where": where, "count": nseq, "first_items": bad[:10]})
    for i, (a, b) in enumerate(zip(mine["items"], theirs["items"])):
        d = abs(a - b)
        note("item", d)
        if d > TOL_ITEM:
            diffs.append({"class": "item", "where": where, "item": i, "mine": a, "theirs": b, "diff": d})
    cmpnum("pass_mean", where, sum(mine["items"]) / 1000 if "mean" not in mine else mine["mean"], theirs["mean"], TOL_DER)
    return nseq


def main():
    seq_diff_total = 0
    # 1. passes
    pass_pairs = 0
    for r, o in CELLS:
        for f in sorted(glob.glob(str(IMPL / "passes" / f"P__{r}__{o}__*.json"))):
            t = json.loads(Path(f).read_text())
            store, cond, role = t["store"], t["cond"], t["role"]
            mc = "reg" if store == "M1" else cond
            mp = MINE / "passes" / f"r{r}_{o}__{role}__{STORE[store]}__{mc}.json"
            m = json.loads(mp.read_text())
            seq_diff_total += cmp_pass(f"counted r{r}{o} {role} {store} {cond}", m, t)
            pass_pairs += 1
        g = json.loads((MINE / "gate" / f"gate_r{r}_{o}.json").read_text())["reproduction"]
        for lab, (store, role) in {"M1_first": ("M1", "first"), "app_first": ("append", "first"), "fin_first": ("final", "first"), "fin_second": ("final", "second")}.items():
            t = json.loads((IMPL / "gate_passes" / f"G__{r}__{o}__{store}__{role}.json").read_text())
            seq_diff_total += cmp_pass(f"repro r{r}{o} {role} {store}", {"items": g[lab]["items"], "sequences": g[lab]["sequences"], "mean": g[lab]["mean_mine"]}, t)
            pass_pairs += 1
    # 2. readings
    mine = json.loads((MINE / RES).read_text())
    rd = json.loads((IMPL / "records" / "readings.json").read_text())
    reg = json.loads(Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121/registry.json").read_text())
    for r, o in CELLS:
        M = mine["cells"][f"r{r}|{o}"]
        T = rd["cells"][f"r{r}/{o}"]
        f, s = o[0], o[1]
        pan = {"first": "E_" + f, "second": "E_" + s}
        for k, tv in T["passes"].items():
            role, store, cond = k.split("|")
            mk = f"{pan[role]}|{STORE[store]}__{'reg' if store == 'M1' else cond}"
            mv = M["passes"][mk]
            w = f"r{r}{o} pass {k}"
            cmpnum("derived", w + " s", mv["s"], tv["s"], TOL_DER)
            cmpnum("derived", w + " G", mv["G"], tv["G"], TOL_DER)
            cmpnum("derived", w + " differs", mv["share_differs_from_ref"], tv["differs_from_reference"], 1e-12)
        D, TD = M["decomposition_first"], T["decomposition"]
        mp = {"T": "T", "i": "i_slot_displacement", "ii": "ii_softmax_renormalisation", "iii": "iii_stage2_values",
              "values_first_values": "values_alone_b1_minus_g1", "values_first_competition": "competition_given_values_g1_minus_a"}
        for tk, mk in mp.items():
            w = f"r{r}{o} first {tk}"
            cmpnum("derived", w, D[mk]["mean"], TD[tk], TOL_DER)
            cmpnum("derived", w + " contrast mean", D[mk]["mean"], TD["contrasts"][tk]["mean"], TOL_DER)
            cmpnum("derived", w + " se", D[mk]["se"], TD["contrasts"][tk]["se"], TOL_DER)
            cmpnum("derived", w + " G units", D[mk]["G_units"], TD["G_units"][tk], TOL_DER)
        cmpnum("derived", f"r{r}{o} first interaction", D["interaction_iii_minus_values_alone"]["mean"], TD["interaction"], TOL_DER)
        cmpnum("derived", f"r{r}{o} first interaction G", D["interaction_iii_minus_values_alone"]["G_units"], TD["G_units"]["interaction"], TOL_DER)
        cmpnum("derived", f"r{r}{o} first residual (F-T)", D["iv_residual_F_minus_T"], TD["residual"], TOL_DER)
        sh = {"i": D["i_slot_displacement"]["share_of_T"], "ii": D["ii_softmax_renormalisation"]["share_of_T"], "iii": D["iii_stage2_values"]["share_of_T"],
              "competition_path": D["i_plus_ii"]["share_of_T"], "values_path": D["iii_stage2_values"]["share_of_T"],
              "competition_values_first": D["competition_given_values_g1_minus_a"]["share_of_T"], "values_values_first": D["values_alone_b1_minus_g1"]["share_of_T"]}
        for k, v in sh.items():
            cmpnum("derived", f"r{r}{o} first share {k}", v, TD["shares"][k], TOL_DER)
        for k in ("competition_path", "values_path", "competition_values_first", "values_values_first"):
            cmpnum("cutoff", f"r{r}{o} share {k} >= 2/3", sh[k] >= 2 / 3, TD["shares"][k] >= 2 / 3, 0)
        A, TA = M["append_point"], T["append_point"]
        cmpnum("derived", f"r{r}{o} append i", A["i_app"]["mean"], TA["i"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append ii", A["ii_app"]["mean"], TA["ii"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append i se", A["i_app"]["se"], TA["contrasts"]["i"]["se"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append ii se", A["ii_app"]["se"], TA["contrasts"]["ii"]["se"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append T (i+ii)", A["i_plus_ii_app"], TA["T"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append T se", A["M1_minus_a_app"]["se"], TA["contrasts"]["T"]["se"], TOL_DER)
        cmpnum("derived", f"r{r}{o} competition final-minus-append", A["i_plus_ii_final_minus_append"], TA["competition_final_minus_append"], TOL_DER)
        cmpnum("derived", f"r{r}{o} append iii", 0.0, TA["iii"], 0.0)
        S2, TS = M["decomposition_second"], T["second_capability_effect_of_stage1_rows"]
        mp2 = {"T": "T2_b2_minus_a", "i": "i_b2_minus_d2", "ii": "ii_d2_minus_e2", "iii": "iii_e2_minus_a", "values_first_values": "values_alone_b2_minus_g2",
               "values_first_competition": "given_values_g2_minus_a"}
        for tk, mk in mp2.items():
            cmpnum("derived", f"r{r}{o} second {tk}", S2[mk]["mean"], TS[tk], TOL_DER)
            cmpnum("derived", f"r{r}{o} second {tk} se", S2[mk]["se"], TS["contrasts"][tk]["se"], TOL_DER)
        cmpnum("derived", f"r{r}{o} second interaction", S2["interaction"], TS["interaction"], TOL_DER)
        cmpnum("derived", f"r{r}{o} second a-e1", S2["a_minus_e1_stage2_off"]["mean"], TS["stage2_switched_off_trained_keys"]["s_a_minus_s_e1"], TOL_DER)
        cmpnum("derived", f"r{r}{o} second a-e1 se", S2["a_minus_e1_stage2_off"]["se"], TS["stage2_switched_off_trained_keys"]["contrast_a_minus_e1"]["se"], TOL_DER)
        for x, tx in (("fin__c", "c"), ("fin__g1", "g1")):
            mc, tc = M["counterfactual_ret_arithmetic"][x], T["counterfactual_ret"][tx]
            w = f"r{r}{o} cfRET {tx}"
            cmpnum("derived", w + " F", mc["F_cf"], tc["F"], TOL_DER)
            cmpnum("derived", w + " rho", mc["rho_cf"], tc["rho"], TOL_DER)
            cmpnum("derived", w + " second cost c", mc["second_cost_s_a_minus_s_c"], tc["second_capability_cost_vs_c"], TOL_DER)
            cmpnum("derived", w + " G_second(c)", mc["G_second_under_c"], tc["G_second_under_c"], TOL_DER)
            cmpnum("derived", w + " G_second(a)", mc["G_second_under_a"], tc["G_second_a"], TOL_DER)
            cmpnum("derived", w + " cost g2", mc["auditor_extra_second_cost_s_a_minus_s_g2"], tc["second_capability_cost_vs_g2"], TOL_DER)
            wm = mc["word"]
            wt = tc["word"].replace("COUNTERFACTUAL RET ARITHMETIC: ", "")
            if wm != wt:
                diffs.append({"class": "word", "where": w, "mine": wm, "theirs": tc["word"]})
        # registered scale (both taken from the registry)
        for role, cap in (("first", f), ("second", s)):
            for arm, v in T["registered_scale"][role].items():
                if arm in ("S0", "TEACHER"):
                    mv = reg[f"{arm}|-|-|s:E_{cap}"]
                elif arm in ("M1_registered", "M-append_registered"):
                    mv = reg[f"{arm.split('_')[0]}|{o}|{r}|s:E_{cap}"]
                elif arm in ("M-sep", "D-sep", "M-joint", "E-table"):
                    mv = reg[f"{arm}|-|{r}|s:E_{cap}"]
                else:
                    mv = reg[f"{arm}|{o}|{r}|s:E_{cap}"]
                cmpnum("registered_scale", f"r{r}{o} {role} {arm}", mv, v, 0.0)
    # words
    sm = mine["summary"]
    for a, b, w in ((sm["path_order_word"], rd["words"]["path_order"], "path order word"), (sm["values_first_word"], rd["words"]["values_first_order"], "values-first word"),
                    (sm["cells_with_T_le_0"], rd["words"]["cells_with_nonpositive_T"], "cells T<=0")):
        if a != b:
            diffs.append({"class": "word", "where": w, "mine": a, "theirs": b})
    final_mine = sm["path_order_word"] + (" ORDER-DEPENDENT" if sm["ORDER_DEPENDENT"] else "")
    if final_mine != rd["words"]["final"]:
        diffs.append({"class": "word", "where": "final word", "mine": final_mine, "theirs": rd["words"]["final"]})
    # 3. stats
    st = json.loads((IMPL / "records" / "stats.json").read_text())
    stat_unmatched = []
    for r, o in CELLS:
        ms = json.loads((MINE / "stats" / f"stats_r{r}_{o}.json").read_text())
        ts = st[f"r{r}/{o}"]
        for mw, tw, p in (("append_first", "append|first", "1"), ("final_first", "final|first", "1"), ("final_second", "final|second", "2")):
            q = "2" if p == "1" else "1"
            T = ts[tw]
            cmpnum("stat_gate", f"r{r}{o} {tw} gates", 0.0, max(abs(a - b) for a, b in zip(ms[mw]["g1"] + ms[mw]["g2"], T["gates"])), 0.0)
            fmap = {"n_p": f"n{p}", "mass_p": f"m{p}", "displaced_weight": "displaced_ref_weight", "top_kept": "ref_top_row_kept", "rel_a": "rel[a]", "rel_c": "rel[c]",
                    "rel_d": f"rel[d{p}]", "rel_e": f"rel[e{p}]", "rel_g": f"rel[g{p}]", "other_part": f"norm_e{q}_over_ref"}
            for kind_m, kind_t in (("word", "words"), ("marker", "markers")):
                for tk, tv in T[kind_t].items():
                    if tk == "displaced":
                        mv = ms[mw][kind_m][f"n{p}"]
                        for sk, msk in (("mean", "mean"), ("median", "median_linear"), ("p5", "p05_linear"), ("p95", "p95_linear")):
                            cmpnum("stat", f"r{r}{o} {tw} {kind_t} displaced {sk} (= 8 - n_p)", 8 - mv[msk], tv[sk], TOL_STAT)
                        continue
                    if tk not in fmap:
                        stat_unmatched.append(f"{tw}/{kind_t}/{tk}")
                        continue
                    mv = ms[mw][kind_m][fmap[tk]]
                    cmpnum("stat_n", f"r{r}{o} {tw} {kind_t} {tk} n", mv["n"], tv["n"], 0)
                    if tv.get("undefined"):
                        diffs.append({"class": "stat", "where": f"r{r}{o} {tw} {kind_t} {tk}", "why": "undefined count nonzero on their side", "theirs": tv["undefined"]})
                    for sk, msk in (("mean", "mean"), ("median", "median_linear"), ("p5", "p05_linear"), ("p95", "p95_linear")):
                        cmpnum("stat", f"r{r}{o} {tw} {kind_t} {tk} {sk}", mv[msk], tv[sk], TOL_STAT)
            if ms[mw]["G_cap_S_p_is_top_n_of_T8_violations"]:
                diffs.append({"class": "stat", "where": f"r{r}{o} {mw}", "why": "my tie-claim violations", "mine": ms[mw]["G_cap_S_p_is_top_n_of_T8_violations"]})
    out = {"utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "pass_pairs_compared": pass_pairs, "sequence_mismatches_total": seq_diff_total, "maxima": maxima,
           "counts": counts, "stat_keys_unmatched": sorted(set(stat_unmatched)), "differences": len(diffs), "difference_list": diffs,
           "verdict": "RECOMPUTATION AGREES" if not diffs else "RECOMPUTATION DIFFERS"}
    p = MINE / f"compare_{out['utc']}.json"
    with open(p, "x") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "difference_list"}, indent=1))
    for d in diffs[:60]:
        print("DIFF", json.dumps(d)[:300])
    print("written", p)


if __name__ == "__main__":
    main()
