"""Independent recomputation of P6-E from raw worker records (auditor role).

Standard library only. Does not import arborlm. Reads:
  results/p6-e-2026-11-13/{equivalence,screen,confirm,analysis}/<run>/...
  experiments/P6E{EQ,SCR,CON}-*/workers/<run>/metrics.jsonl   (per-block raw durations, local)
  results/p5-2026-11-13/timing/*/result.json                    (P5 context)
Writes recompute_p6e.json next to this file.

Rules implemented from ADR-0011 sections 3.3, 3.4, 3.6 and clarifications 20-21 only.
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import statistics as st
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RES = os.path.join(ROOT, "results", "p6-e-2026-11-13")
EXP = os.path.join(ROOT, "experiments")
P5 = os.path.join(ROOT, "results", "p5-2026-11-13")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recompute_p6e.json")

BACKBONES = (101, 102, 103)
ORDERS = (301, 302, 303)
SEEDS = (501, 502, 503)
PAIRS = [(b, o, s) for b in BACKBONES for o in ORDERS for s in SEEDS]
PARENTS = [(b, o) for b in BACKBONES for o in ORDERS]
KINDS = ("fixed_tree", "learned_tree")
SCOPES = ("lookup_score_select", "addition_forward", "model_forward")
WORKLOADS = ("W8", "W1", "Wtok")
ROUNDS, CALLS = 8, 10
SCORE_TOL, LOGIT_TOL, NLL_TOL = 1e-5, 1e-4, 1e-6


def load(path):
    with open(path) as fh:
        return json.load(fh)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def one(pattern):
    hits = sorted(glob.glob(pattern))
    assert len(hits) == 1, (pattern, hits)
    return hits[0]


def label(p):
    return f"b{p[0]}-o{p[1]}-s{p[2]}"


def gmean(xs):
    xs = list(xs)
    return math.exp(math.fsum(math.log(x) for x in xs) / len(xs))


def nearest_rank(sorted_xs, p):
    return sorted_xs[math.ceil(len(sorted_xs) * p) - 1]


def parse_ts(run_id):
    # e.g. P6CNW-20261113T175808203465Z-<hex>
    t = run_id.split("-")[1]
    return datetime.strptime(t, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- stage folders
stage_dir = {s: one(os.path.join(RES, s, "*")) for s in ("equivalence", "screen", "confirm", "analysis")}
ana = load(os.path.join(stage_dir["analysis"], "result.json"))
out: dict = {"inputs": {s: os.path.relpath(d, ROOT) for s, d in stage_dir.items()}}
discrepancies: list[str] = []


def disc(msg):
    discrepancies.append(msg)


# --------------------------------------------------------------------------- (a) timing records
def own_summary(rec):
    d = rec["durations_ns"]
    assert len(d) == ROUNDS * CALLS, len(d)
    rows = [d[i * CALLS:(i + 1) * CALLS] for i in range(ROUNDS)]
    rm = [st.median(r) for r in rows]
    med = st.median(d)
    srt = sorted(d)
    ratio = max(rm) / min(rm)
    res = rec["resolution_ns"]
    crit = {"positive": min(d) > 0, "median>=100res": med >= 100 * res, "rounds<=1.25": ratio <= 1.25}
    return {
        "median": med, "round_medians": rm, "ratio": ratio, "usable": all(crit.values()), "crit": crit,
        "p10": nearest_rank(srt, 0.1), "p50": nearest_rank(srt, 0.5), "p90": nearest_rank(srt, 0.9),
        "p95": nearest_rank(srt, 0.95), "min": srt[0], "max": srt[-1],
    }


timing = {}  # stage -> pair -> (workload, scope, entity) -> own summary (+ stored)
worker_meta = {}
record_mismatch = []
metrics_mismatch = []
for stage in ("screen", "confirm"):
    wj = load(os.path.join(stage_dir[stage], "workers.json"))
    timing[stage] = {}
    worker_meta[stage] = {}
    for w in wj["workers"]:
        p = tuple(w["pair"])
        rec = load(os.path.join(stage_dir[stage], "workers", f"{label(p)}.json"))
        assert rec["outcome"] == "completed" and tuple(rec["pair"]) == p
        start = parse_ts(w["run_id"])
        worker_meta[stage][p] = {"run_id": w["run_id"], "start_utc": start.isoformat(),
                                 "wall_seconds": w["wall_seconds"], "peak_rss_bytes": w["peak_rss_bytes"],
                                 "status": w["status"]}
        table = {}
        for r in rec["timing"]["records"]:
            key = (r["workload"], r["scope"], r["entity"])
            mine = own_summary(r)
            ok = (mine["median"] == r["median_ns"] and mine["round_medians"] == r["round_medians_ns"]
                  and mine["usable"] == r["usable"] and abs(mine["ratio"] - r["round_median_ratio"]) == 0
                  and mine["p10"] == r["p10_ns"] and mine["p50"] == r["p50_ns"] and mine["p90"] == r["p90_ns"]
                  and mine["p95"] == r["p95_ns"] and mine["min"] == r["min_ns"] and mine["max"] == r["max_ns"])
            if not ok:
                record_mismatch.append([stage, label(p), *key])
            mine["stored_usable"] = r["usable"]
            table[key] = mine
            table[key]["_durations"] = r["durations_ns"]
        timing[stage][p] = table
        # cross-check against the local per-block log, which also gives the block order in time
        exp_stage = {"screen": "P6ESCR", "confirm": "P6ECON"}[stage]
        mpath = os.path.join(EXP, os.path.basename(stage_dir[stage]), "workers", w["run_id"], "metrics.jsonl")
        assert os.path.basename(stage_dir[stage]).startswith(exp_stage)
        blocks = []
        if os.path.exists(mpath):
            with open(mpath) as fh:
                for line in fh:
                    ev = json.loads(line)
                    if ev.get("event") == "timing_block":
                        blocks.append(ev)
        rebuilt = {}
        for i, b in enumerate(blocks):
            k = (b["workload"], b["scope"], b["entity"])
            rebuilt.setdefault(k, []).append((b["round"], i, b["durations_ns"]))
        for k, v in table.items():
            rows = rebuilt.get(k)
            if rows is None or [x for _, _, d in rows for x in d] != v["_durations"] or \
                    [r for r, _, _ in rows] != list(range(ROUNDS)):
                metrics_mismatch.append([stage, label(p), *k])
            else:
                v["_block_index"] = [i for _, i, _ in rows]
                v["_blocks_total"] = len(blocks)
out["a_records"] = {
    "records_checked": {s: sum(len(t) for t in timing[s].values()) for s in timing},
    "stored_vs_recomputed_mismatches": record_mismatch,
    "raw_metrics_jsonl_vs_record_mismatches": metrics_mismatch,
}

# --------------------------------------------------------------------------- (b) equivalence
eq_res = load(os.path.join(stage_dir["equivalence"], "result.json"))
eq = {}
eq_fail = []
eq_detail = {}
for p in PAIRS:
    rec = load(os.path.join(stage_dir["equivalence"], "workers", f"{label(p)}.json"))
    assert rec["outcome"] == "completed"
    mf = rec["mismatch_file"]
    if mf["records"] != 0 or mf["sha256"] != hashlib.sha256(b"").hexdigest():
        eq_fail.append(["mismatch_file_nonempty", label(p)])
    for kind, ck in rec["checkpoints"].items():
        for v, vr in ck["variants"].items():
            scopes = vr["scopes"]
            classes = {}
            for sname in ("a_panel", "b_w1", "b_w8", "c_fixtures"):
                if sname not in scopes:
                    classes[sname] = "NOT_EQUIVALENT"
                    continue
                s = scopes[sname]
                same_sel = s["selected_mismatch_queries"] == 0
                ids = s["branch_ids_equal"] and s["candidate_ids_equal"]
                tie_bad = sname == "c_fixtures" and s["tie_rule_violations_variant"] > 0
                strict = (same_sel and ids and s["selected_scores_bitwise"] and s["route_scores_bitwise"]
                          and s["logits_bitwise"] in (True, None) and s["nll_bitwise"] in (True, None))
                lg, nl = s["max_abs_logit_diff"], s["nll_abs_diff"]
                bounded = (same_sel and ids and s["max_abs_score_diff"] <= SCORE_TOL
                           and (lg is None or lg <= LOGIT_TOL) and (nl is None or nl <= NLL_TOL))
                c = "NOT_EQUIVALENT" if tie_bad else ("STRICT" if strict else ("BOUNDED" if bounded else "NOT_EQUIVALENT"))
                classes[sname] = c
                if c != vr["scope_classes"][sname]:
                    eq_fail.append(["scope_class_differs", label(p), kind, v, sname, c, vr["scope_classes"][sname]])
            rank = {"STRICT": 0, "BOUNDED": 1, "NOT_EQUIVALENT": 2}
            worst = max(classes.values(), key=rank.get)
            if worst != vr["class"]:
                eq_fail.append(["class_differs", label(p), kind, v, worst, vr["class"]])
            d = eq_detail.setdefault(v, {"classes": [], "max_score": 0.0, "max_logit": 0.0, "max_nll": 0.0,
                                         "sel_mismatch": 0, "tie_viol_var": 0, "tie_viol_ref": 0,
                                         "fb_q": 0, "fb_flag": 0, "fb_fwd_q": 0, "fb_fwd_flag": 0,
                                         "fb_fix_q": 0, "fb_fix_flag": 0, "fb_frac_per_ckpt": [],
                                         "nll_bitwise_all": True, "logits_bitwise_all": True,
                                         "exact_tie_queries_fixtures": 0, "wtok_selected_mismatch": 0,
                                         "wtok_ids_equal_all": True, "integrity_ok": True, "state_ok": True,
                                         "files_ok": True, "checkpoints": 0})
            d["checkpoints"] += 1
            d["classes"].append(worst)
            d["integrity_ok"] &= ck["integrity"]["bitwise_equal"] and ck["integrity"]["replayed_nll"] == ck["integrity"]["recorded_final_nll"]
            d["state_ok"] &= ck["model_state_and_rng_unchanged"]
            d["files_ok"] &= ck["checkpoint_files_unchanged_before_and_after"]
            for sname, s in scopes.items():
                d["max_score"] = max(d["max_score"], s["max_abs_score_diff"] or 0.0)
                d["max_logit"] = max(d["max_logit"], s["max_abs_logit_diff"] or 0.0)
                d["max_nll"] = max(d["max_nll"], s["nll_abs_diff"] or 0.0)
                d["sel_mismatch"] += s["selected_mismatch_queries"]
                d["tie_viol_var"] += s["tie_rule_violations_variant"]
                d["tie_viol_ref"] += s["tie_rule_violations_reference"]
                if s["nll_bitwise"] is False:
                    d["nll_bitwise_all"] = False
                if s["logits_bitwise"] is False:
                    d["logits_bitwise_all"] = False
                g = s.get("guard_fallback_lookup")
                if g and sname == "c_fixtures":
                    d["fb_fix_q"] += g["queries"]; d["fb_fix_flag"] += g["flagged_queries"]
                    d["exact_tie_queries_fixtures"] += s["queries_with_exact_ties_in_reference_top9"]
                elif g and g["queries"]:
                    assert sum(n for n, _ in g["per_call"]) == g["queries"]
                    assert sum(f for _, f in g["per_call"]) == g["flagged_queries"]
                    d["fb_q"] += g["queries"]; d["fb_flag"] += g["flagged_queries"]
                    if sname == "a_panel":
                        d["fb_frac_per_ckpt"].append(g["flagged_queries"] / g["queries"])
                gf = s.get("guard_fallback_forward")
                if gf and gf["queries"]:
                    d["fb_fwd_q"] += gf["queries"]; d["fb_fwd_flag"] += gf["flagged_queries"]
            wt = vr.get("descriptive_wtok")
            if wt:
                d["wtok_selected_mismatch"] += wt["selected_mismatch_queries"]
                d["wtok_ids_equal_all"] &= wt["branch_ids_equal"] and wt["candidate_ids_equal"]
eq_summary = {}
for v, d in sorted(eq_detail.items()):
    counts = {c: d["classes"].count(c) for c in ("STRICT", "BOUNDED", "NOT_EQUIVALENT")}
    expected = 27 if v.startswith("F") else 54
    passes = d["checkpoints"] == expected and counts["NOT_EQUIVALENT"] == 0
    fr = d["fb_frac_per_ckpt"]
    eq_summary[v] = {
        "checkpoints": d["checkpoints"], "counts": counts, "EQ": passes,
        "max_abs_selected_score_diff": d["max_score"], "max_abs_logit_diff": d["max_logit"],
        "max_abs_panel_nll_diff": d["max_nll"], "selected_mismatch_queries_total": d["sel_mismatch"],
        "tie_rule_violations_variant": d["tie_viol_var"], "tie_rule_violations_reference": d["tie_viol_ref"],
        "panel_nll_bitwise_all": d["nll_bitwise_all"], "logits_bitwise_all": d["logits_bitwise_all"],
        "guard_fallback_lookup_a_b": {"queries": d["fb_q"], "flagged": d["fb_flag"],
                                      "fraction": d["fb_flag"] / d["fb_q"] if d["fb_q"] else None},
        "guard_fallback_forward_a_b": {"queries": d["fb_fwd_q"], "flagged": d["fb_fwd_flag"],
                                       "fraction": d["fb_fwd_flag"] / d["fb_fwd_q"] if d["fb_fwd_q"] else None},
        "guard_fallback_panel_per_checkpoint": ({"min": min(fr), "median": st.median(fr), "max": max(fr)} if fr and d["fb_q"] else None),
        "guard_fallback_fixtures": {"queries": d["fb_fix_q"], "flagged": d["fb_fix_flag"]},
        "fixture_queries_with_exact_ties_in_reference_top9": d["exact_tie_queries_fixtures"],
        "wtok_descriptive_selected_mismatch": d["wtok_selected_mismatch"],
        "wtok_ids_equal_all": d["wtok_ids_equal_all"],
        "integrity_replay_bitwise_all": d["integrity_ok"], "state_rng_unchanged_all": d["state_ok"],
        "checkpoint_files_unchanged_all": d["files_ok"],
    }
    g = eq_res["gate"][v]
    if g["counts"] != counts or g["EQ"] != passes:
        disc(f"equivalence gate for {v}: stage result {g['counts']}/{g['EQ']} vs mine {counts}/{passes}")
    a = ana["analysis"]["equivalence"][v]
    if a["counts"] != counts or a["EQ"] != passes:
        disc(f"analysis equivalence for {v}: {a['counts']}/{a['EQ']} vs mine {counts}/{passes}")
out["b_equivalence"] = {"per_variant": eq_summary, "classification_disagreements": eq_fail,
                        "E-H1_T1_T2_STRICT_everywhere": all(eq_summary[v]["counts"]["STRICT"] == 54 for v in ("T1", "T2")),
                        "E-H2_T3_T4_T5_F2_at_least_BOUNDED": all(eq_summary[v]["EQ"] for v in ("T3", "T4", "T5", "F2"))}

# --------------------------------------------------------------------------- (c) selection
scr = timing["screen"]
sel_tree = {}
for kind in KINDS:
    table = {}
    for v in ("T1", "T2", "T3", "T4", "T5"):
        ratios = [scr[p][("W8", "addition_forward", f"{kind}:{v}")]["median"] /
                  scr[p][("W8", "addition_forward", f"{kind}:T0")]["median"] for p in PAIRS]
        all_usable = all(scr[p][("W8", "addition_forward", f"{kind}:{x}")]["usable"] for p in PAIRS for x in (v, "T0"))
        table[v] = {"gm_ratio_to_T0": gmean(ratios), "all_usable": all_usable,
                    "n_pairs_both_usable": sum(scr[p][("W8", "addition_forward", f"{kind}:{v}")]["usable"] and
                                               scr[p][("W8", "addition_forward", f"{kind}:T0")]["usable"] for p in PAIRS)}
    eligible = [v for v in table if eq_summary[v]["EQ"]]
    chosen = min(eligible, key=lambda v: (table[v]["gm_ratio_to_T0"], v))
    sel_tree[kind] = {"selected": chosen, "table": table}
flat_table = {}
for v in ("F0", "F1", "F2"):
    meds = [scr[p][("W8", "addition_forward", f"flat:{v}")]["median"] for p in PAIRS]
    flat_table[v] = {"median_of_worker_medians_ns": st.median(meds),
                     "gm_ratio_to_F0": gmean(m / scr[p][("W8", "addition_forward", "flat:F0")]["median"]
                                             for m, p in zip(meds, PAIRS))}
flat_elig = [v for v in flat_table if v == "F0" or eq_summary[v]["EQ"]]
comparator = min(flat_elig, key=lambda v: (flat_table[v]["median_of_worker_medians_ns"], v))
selection = load(os.path.join(stage_dir["screen"], "selection.json"))
for kind in KINDS:
    if selection["tree"][kind]["selected"] != sel_tree[kind]["selected"]:
        disc(f"selection {kind}: stored {selection['tree'][kind]['selected']} vs mine {sel_tree[kind]['selected']}")
    for v, t in sel_tree[kind]["table"].items():
        s = selection["tree"][kind]["table"][v]
        if abs(s["geometric_mean_ratio_to_T0"] - t["gm_ratio_to_T0"]) > 1e-12 or s["all_usable"] != t["all_usable"]:
            disc(f"selection table {kind}/{v}: stored {s} vs mine {t}")
if selection["flat"]["comparator"] != comparator:
    disc(f"flat comparator stored {selection['flat']['comparator']} vs mine {comparator}")
for v, t in flat_table.items():
    if selection["flat"]["table"][v]["median_of_worker_medians_ns"] != t["median_of_worker_medians_ns"]:
        disc(f"flat table {v}: stored {selection['flat']['table'][v]} vs mine {t}")
# linkage
con_spec = load(os.path.join(stage_dir["confirm"], "stage-spec.json"))
scr_spec = load(os.path.join(stage_dir["screen"], "stage-spec.json"))
eq_spec = load(os.path.join(stage_dir["equivalence"], "stage-spec.json"))
link = {
    "confirm.evidence.equivalence_run == eq run": con_spec["evidence"]["equivalence_run"] == os.path.basename(stage_dir["equivalence"]),
    "confirm.evidence.screen_run == screen run": con_spec["evidence"]["screen_run"] == os.path.basename(stage_dir["screen"]),
    "confirm.equivalence_result_sha256 == sha(eq result.json)": con_spec["evidence"]["equivalence_result_sha256"] == sha(os.path.join(stage_dir["equivalence"], "result.json")),
    "confirm.screen_result_sha256 == sha(screen result.json)": con_spec["evidence"]["screen_result_sha256"] == sha(os.path.join(stage_dir["screen"], "result.json")),
    "confirm.selection_sha256 == sha(selection.json)": con_spec["evidence"]["selection_sha256"] == sha(os.path.join(stage_dir["screen"], "selection.json")),
    "screen.equivalence_result_sha256 == sha(eq result.json)": scr_spec["evidence"]["equivalence_result_sha256"] == sha(os.path.join(stage_dir["equivalence"], "result.json")),
    "results copies equal experiments copies": all(
        sha(os.path.join(stage_dir[s], f)) == sha(os.path.join(EXP, os.path.basename(stage_dir[s]), f))
        for s, f in (("equivalence", "result.json"), ("screen", "result.json"), ("screen", "selection.json"),
                     ("confirm", "result.json"), ("analysis", "result.json"))),
    "confirm plan == {T0, selected} x kinds, {F0, comparator}": con_spec["plan"] == {
        "fixed_tree": ["T0", sel_tree["fixed_tree"]["selected"]], "learned_tree": ["T0", sel_tree["learned_tree"]["selected"]],
        "flat": ["F0", comparator]},
    "confirm workers timed exactly the planned entities": all(
        sorted({k[2] for k in timing["confirm"][p]}) == sorted(
            [f"fixed_tree:T0", f"fixed_tree:{sel_tree['fixed_tree']['selected']}", f"learned_tree:T0",
             f"learned_tree:{sel_tree['learned_tree']['selected']}", "flat:F0", f"flat:{comparator}"])
        for p in PAIRS),
    "confirm workers 27 and each has 48 records": len(timing["confirm"]) == 27 and all(len(t) == 48 for t in timing["confirm"].values()),
    "screen workers 27 and each has 120 records": len(timing["screen"]) == 27 and all(len(t) == 120 for t in timing["screen"].values()),
    "all three stage specs share source archive sha": len({x["source"]["source_archive_sha256"] for x in (eq_spec, scr_spec, con_spec)}) == 1,
    "analysis inputs name these runs": ana["inputs"]["confirm_run"] == os.path.basename(stage_dir["confirm"]) and
        ana["inputs"]["screen_run"] == os.path.basename(stage_dir["screen"]) and
        ana["inputs"]["equivalence_run"] == os.path.basename(stage_dir["equivalence"]),
    "no supersede args": all(x["args"]["supersede"] is None for x in (eq_spec, scr_spec, con_spec)),
    "only one run directory per stage in results": all(len(glob.glob(os.path.join(RES, s, "*"))) == 1 for s in ("equivalence", "screen", "confirm", "analysis")),
    "only one run directory per stage in experiments": {s: len(glob.glob(os.path.join(EXP, s + "-*"))) for s in ("P6EEQ", "P6ESCR", "P6ECON", "P6EANA")},
}
out["c_selection"] = {"tree": sel_tree, "flat": {"comparator": comparator, "table": flat_table}, "linkage": link}

# --------------------------------------------------------------------------- (d)/(e) criteria and ratios
con = timing["confirm"]


def ratio_block(stage_t, workload, scope, top, bottom):
    rows = []
    for p in PAIRS:
        t, b = stage_t[p][(workload, scope, top)], stage_t[p][(workload, scope, bottom)]
        rows.append({"pair": list(p), "ratio": t["median"] / b["median"], "top_usable": t["usable"],
                     "bottom_usable": b["usable"]})
    ratios = [r["ratio"] for r in rows]
    parents = {f"b{b}-o{o}": gmean(r["ratio"] for r in rows if tuple(r["pair"][:2]) == (b, o)) for b, o in PARENTS}
    usable = [r["top_usable"] and r["bottom_usable"] for r in rows]
    us = [r["ratio"] for r, u in zip(rows, usable) if u]
    return {"gm": gmean(ratios), "min": min(ratios), "max": max(ratios), "median": st.median(ratios),
            "parents": parents, "ratios": ratios, "usable": usable, "n_usable_pairs": sum(usable),
            "all_usable": all(usable), "gm_usable_only": gmean(us) if us else None, "ratios_usable_only": us,
            "parents_usable_only": {f"b{b}-o{o}": (gmean(r["ratio"] for r, u in zip(rows, usable) if u and tuple(r["pair"][:2]) == (b, o))
                                                   if any(u and tuple(r["pair"][:2]) == (b, o) for r, u in zip(rows, usable)) else None)
                                    for b, o in PARENTS}}


def clauses(block, gm_lim, cell_cmp, cell_lim, cell_req, par_req, use_usable=False):
    ratios = block["ratios_usable_only"] if use_usable else block["ratios"]
    gm = block["gm_usable_only"] if use_usable else block["gm"]
    parents = [x for x in (block["parents_usable_only"] if use_usable else block["parents"]).values() if x is not None]
    f = (lambda x: x < cell_lim) if cell_cmp == "<" else (lambda x: x <= cell_lim)
    c = sum(f(x) for x in ratios)
    pc = sum(f(x) for x in parents)
    return {"gm": gm, "gm_ok": gm is not None and gm <= gm_lim, "cells": c, "cells_of": len(ratios), "cells_req": cell_req,
            "cells_ok": c >= cell_req, "parents": pc, "parents_of": len(parents), "parents_req": par_req,
            "parents_ok": pc >= par_req}


def criteria(kind, v, flat_ref, use_usable=False):
    res = {}
    a_t0 = ratio_block(con, "W8", "addition_forward", f"{kind}:{v}", f"{kind}:T0")
    a_fl = ratio_block(con, "W8", "addition_forward", f"{kind}:{v}", f"flat:{flat_ref}")
    m_fl = ratio_block(con, "W8", "model_forward", f"{kind}:{v}", f"flat:{flat_ref}")
    sp = clauses(a_t0, 0.50, "<", 1.0, 26, 9, use_usable)
    par_a = clauses(a_fl, 1.00, "<=", 1.0, 22, 8, use_usable)
    par_m = clauses(m_fl, 1.05, "<=", 1.05, 22, 8, use_usable)
    pr_a = clauses(a_fl, 0.80, "<", 1.0, 22, 8, use_usable)
    pr_m = clauses(m_fl, 1.05, "<=", 1.05, 22, 8, use_usable)

    def ok(*cs):
        return all(c["gm_ok"] and c["cells_ok"] and c["parents_ok"] for c in cs)

    def verdict(reliable, *cs):
        if use_usable:
            return "DESCRIPTIVE_PASS" if ok(*cs) else "DESCRIPTIVE_FAIL"
        return "INCONCLUSIVE" if not reliable else ("PASS" if ok(*cs) else "FAIL")
    res["SP"] = {"addition_forward_vs_T0": sp, "reliable_all_27": a_t0["all_usable"], "usable_pairs": a_t0["n_usable_pairs"],
                 "clauses_met_pointwise": ok(sp), "verdict": verdict(a_t0["all_usable"], sp)}
    rel = a_fl["all_usable"] and m_fl["all_usable"]
    res["PAR"] = {"addition_forward": par_a, "model_forward": par_m, "reliable": rel,
                  "usable_pairs": [a_fl["n_usable_pairs"], m_fl["n_usable_pairs"]],
                  "clauses_met_pointwise": ok(par_a, par_m), "verdict": verdict(rel, par_a, par_m)}
    res["PR"] = {"addition_forward": pr_a, "model_forward": pr_m, "reliable": rel,
                 "usable_pairs": [a_fl["n_usable_pairs"], m_fl["n_usable_pairs"]],
                 "clauses_met_pointwise": ok(pr_a, pr_m), "verdict": verdict(rel, pr_a, pr_m)}
    res["_blocks"] = {"add_vs_T0": a_t0, "add_vs_flat": a_fl, "fwd_vs_flat": m_fl}
    return res


crit = {}
sens = {}
for kind in KINDS:
    v = sel_tree[kind]["selected"]
    crit[kind] = {"variant": v, "flat_comparator": comparator, "EQ": eq_summary[v]["EQ"],
                  "registered": criteria(kind, v, comparator),
                  "versus_F0_weaker": criteria(kind, v, "F0")}
    sens[kind] = {"vs_comparator": criteria(kind, v, comparator, use_usable=True),
                  "vs_F0": criteria(kind, v, "F0", use_usable=True)}
    # compare with analysis
    ac = ana["analysis"]["criteria"][kind]
    reg = crit[kind]["registered"]
    for name in ("SP", "PAR", "PR"):
        if ac[name]["status"] != reg[name]["verdict"]:
            disc(f"{kind} {name}: analysis {ac[name]['status']} vs mine {reg[name]['verdict']}")
        if ana["analysis"]["verdicts"][kind][name] != reg[name]["verdict"]:
            disc(f"{kind} verdicts.{name}: analysis {ana['analysis']['verdicts'][kind][name]} vs mine {reg[name]['verdict']}")
    pairs_ana = {
        ("PAR", "addition_forward"): reg["_blocks"]["add_vs_flat"], ("PAR", "model_forward"): reg["_blocks"]["fwd_vs_flat"],
        ("PR", "addition_forward"): reg["_blocks"]["add_vs_flat"], ("PR", "model_forward"): reg["_blocks"]["fwd_vs_flat"],
        ("SP", "addition_forward"): reg["_blocks"]["add_vs_T0"],
    }
    for (name, scope), blk in pairs_ana.items():
        a = ac[name][scope]
        if abs(a["geometric_mean"]["value"] - blk["gm"]) > 1e-12:
            disc(f"{kind} {name}/{scope} gm analysis {a['geometric_mean']['value']} vs mine {blk['gm']}")
        mine_clause = reg[name][scope if name != "SP" else "addition_forward_vs_T0"]
        if a["cells"]["count"] != mine_clause["cells"] or a["parents"]["count"] != mine_clause["parents"]:
            disc(f"{kind} {name}/{scope} counts analysis {a['cells']['count']}/{a['parents']['count']} vs mine {mine_clause['cells']}/{mine_clause['parents']}")
        if a["geometric_mean"]["pass"] != mine_clause["gm_ok"] or a["cells"]["pass"] != mine_clause["cells_ok"] or a["parents"]["pass"] != mine_clause["parents_ok"]:
            disc(f"{kind} {name}/{scope} clause pass flags differ: analysis gm/cells/parents "
                 f"{a['geometric_mean']['pass']}/{a['cells']['pass']}/{a['parents']['pass']} vs mine "
                 f"{mine_clause['gm_ok']}/{mine_clause['cells_ok']}/{mine_clause['parents_ok']}")
        if [r["usable"] for r in a["ratios"]] != blk["usable"]:
            disc(f"{kind} {name}/{scope} per-pair usable flags differ")
        if any(abs(r["ratio"] - x) > 1e-15 for r, x in zip(a["ratios"], blk["ratios"])):
            disc(f"{kind} {name}/{scope} per-pair ratios differ")
    # weaker F0 comparison
    w = ac["versus_F0_weaker_comparison"]
    for name in ("PAR", "PR"):
        for scope, key in (("addition_forward", "add_vs_flat"), ("model_forward", "fwd_vs_flat")):
            if abs(w[name][scope]["geometric_mean"]["value"] - crit[kind]["versus_F0_weaker"]["_blocks"][key]["gm"]) > 1e-12:
                disc(f"{kind} vs F0 {name}/{scope} gm differs")
        if w[name].get("status") != crit[kind]["versus_F0_weaker"][name]["verdict"]:
            disc(f"{kind} vs F0 {name} status analysis {w[name].get('status')} vs mine {crit[kind]['versus_F0_weaker'][name]['verdict']}")


def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if not k.startswith("_")}
    return d


def compact_criteria(c):
    o = {}
    for name in ("SP", "PAR", "PR"):
        x = c[name]
        o[name] = strip({k: v for k, v in x.items()})
    return o


out["d_criteria"] = {k: {"variant": c["variant"], "flat_comparator": c["flat_comparator"], "EQ": c["EQ"],
                         "registered_vs_comparator": compact_criteria(c["registered"]),
                         "versus_F0_weaker": compact_criteria(c["versus_F0_weaker"]),
                         "per_pair_add_vs_T0": c["registered"]["_blocks"]["add_vs_T0"]["ratios"],
                         "per_pair_add_vs_flat": c["registered"]["_blocks"]["add_vs_flat"]["ratios"],
                         "per_pair_fwd_vs_flat": c["registered"]["_blocks"]["fwd_vs_flat"]["ratios"],
                         "parents_add_vs_T0": c["registered"]["_blocks"]["add_vs_T0"]["parents"],
                         "parents_add_vs_flat": c["registered"]["_blocks"]["add_vs_flat"]["parents"],
                         "parents_fwd_vs_flat": c["registered"]["_blocks"]["fwd_vs_flat"]["parents"]}
                     for k, c in crit.items()}


def hyp(name):
    per = {k: crit[k]["registered"][name]["verdict"] for k in KINDS}
    if any(v == "PASS" and crit[k]["EQ"] for k, v in per.items()):
        return {"per_kind": per, "holds": True}
    if any(v in ("INCONCLUSIVE", "INCOMPLETE") for v in per.values()):
        return {"per_kind": per, "holds": None, "status": "UNDECIDED"}
    return {"per_kind": per, "holds": False}


out["d_hypotheses"] = {"E-H3(SP)": hyp("SP"), "E-H4(PR)": hyp("PR")}
for h, k in (("E-H3", "E-H3(SP)"), ("E-H4", "E-H4(PR)")):
    if ana["analysis"]["hypotheses"][h]["holds"] != out["d_hypotheses"][k]["holds"]:
        disc(f"{h} holds analysis {ana['analysis']['hypotheses'][h]['holds']} vs mine {out['d_hypotheses'][k]['holds']}")

# (e) descriptive ratios: every scope/workload for the confirm entities, plus screen
desc = {}
for stage_name, stage_t, pairs_list in (("confirm", con, None), ("screen", scr, None)):
    ents = sorted({k[2] for k in stage_t[PAIRS[0]]})
    for e in ents:
        kind, v = e.split(":")
        refs = {"T0": f"{kind}:T0"} if kind != "flat" else {"F0": "flat:F0"}
        if kind != "flat":
            refs.update({"flat_comparator": f"flat:{comparator}", "F0": "flat:F0"})
        if v in ("T0", "F0") and kind != "flat":
            refs = {"flat_comparator": f"flat:{comparator}", "F0": "flat:F0"}
        if v == "F0":
            continue
        for wl in WORKLOADS:
            for sc in SCOPES:
                if (wl, sc, e) not in stage_t[PAIRS[0]]:
                    continue
                for rn, ref in refs.items():
                    if ref == e:
                        continue
                    b = ratio_block(stage_t, wl, sc, e, ref)
                    desc[f"{stage_name}/{e}/{wl}/{sc}/over_{rn}"] = {
                        "gm": b["gm"], "min": b["min"], "max": b["max"], "all_usable": b["all_usable"],
                        "n_usable_pairs": b["n_usable_pairs"], "gm_usable_only": b["gm_usable_only"],
                        "parents": b["parents"],
                        "cells_lt1": sum(x < 1 for x in b["ratios"])}
out["e_descriptive_ratios"] = desc
# compare with analysis descriptive (ratio to the variant's own reference: T0 for trees, F0 for flat)
for sect, stg in (("confirm_descriptive", "confirm"), ("screen_descriptive", "screen")):
    for key, a in ana[sect].items():
        e, wl, sc = key.split("/")
        kind = e.split(":")[0]
        rn = "F0" if kind == "flat" else "T0"
        mine = desc.get(f"{stg}/{e}/{wl}/{sc}/over_{rn}")
        if mine is None or abs(mine["gm"] - a["geometric_mean_ratio_to_reference"]) > 1e-12 or mine["all_usable"] != a["all_usable"]:
            disc(f"{sect} {key}: analysis {a} vs mine {mine and (mine['gm'], mine['all_usable'])}")

# --------------------------------------------------------------------------- (f) reliability
rel = {}
for stage_name, stage_t in (("screen", scr), ("confirm", con)):
    recs = []
    for p in PAIRS:
        for (wl, sc, e), m in stage_t[p].items():
            rm = m["round_medians"]
            imax, imin = rm.index(max(rm)), rm.index(min(rm))
            recs.append({"pair": label(p), "workload": wl, "scope": sc, "entity": e, "ratio": m["ratio"],
                         "usable": m["usable"], "crit": m["crit"], "median_ns": m["median"],
                         "round_of_max": imax, "round_of_min": imin,
                         "block_index_of_max": m.get("_block_index", [None] * 8)[imax],
                         "block_index_of_min": m.get("_block_index", [None] * 8)[imin],
                         "blocks_total": m.get("_blocks_total")})
    un = [r for r in recs if not r["usable"]]
    ratios = sorted(r["ratio"] for r in recs)

    def q(xs, p):
        return xs[min(len(xs) - 1, max(0, math.ceil(len(xs) * p) - 1))]

    def count_by(key, rows):
        c = {}
        for r in rows:
            c[r[key]] = c.get(r[key], 0) + 1
        return dict(sorted(c.items()))
    by_worker = count_by("pair", un)
    tot_worker = count_by("pair", recs)
    starts = {label(p): worker_meta[stage_name][p]["start_utc"] for p in PAIRS}
    worker_rows = []
    for p in PAIRS:
        L = label(p)
        wr = [r["ratio"] for r in recs if r["pair"] == L]
        worker_rows.append({"pair": L, "start_utc": starts[L], "unusable": by_worker.get(L, 0), "records": tot_worker[L],
                            "median_round_ratio": st.median(wr), "max_round_ratio": max(wr)})
    # time ordering: workers ran sequentially; split into thirds by start time
    order = sorted(worker_rows, key=lambda r: r["start_utc"])
    thirds = [order[i * 9:(i + 1) * 9] for i in range(3)]
    ent_rows = {}
    for r in recs:
        ent_rows.setdefault(r["entity"], []).append(r)
    by_entity = {e: {"records": len(rs), "unusable": sum(not r["usable"] for r in rs),
                     "median_round_ratio": st.median(r["ratio"] for r in rs),
                     "p90_round_ratio": q(sorted(r["ratio"] for r in rs), 0.9)} for e, rs in sorted(ent_rows.items())}
    # position of the outlying round within the worker's block sequence
    pos = [r["block_index_of_max"] / r["blocks_total"] for r in un if r["block_index_of_max"] is not None]
    rel[stage_name] = {
        "records": len(recs), "unusable": len(un), "fraction_unusable": len(un) / len(recs),
        "failed_criterion_counts": {k: sum(not r["crit"][k] for r in recs) for k in ("positive", "median>=100res", "rounds<=1.25")},
        "round_median_ratio_quantiles": {str(p): q(ratios, p) for p in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)},
        "ratio_histogram": {"<=1.05": sum(x <= 1.05 for x in ratios), "1.05-1.10": sum(1.05 < x <= 1.10 for x in ratios),
                            "1.10-1.25": sum(1.10 < x <= 1.25 for x in ratios), "1.25-1.50": sum(1.25 < x <= 1.5 for x in ratios),
                            ">1.50": sum(x > 1.5 for x in ratios)},
        "unusable_by_workload": count_by("workload", un), "records_by_workload": count_by("workload", recs),
        "unusable_by_scope": count_by("scope", un),
        "unusable_by_workload_scope": count_by("ws", [dict(r, ws=f"{r['workload']}/{r['scope']}") for r in un]),
        "by_entity": by_entity,
        "workers": worker_rows,
        "workers_with_any_unusable": sum(1 for r in worker_rows if r["unusable"]),
        "unusable_by_start_third": [sum(r["unusable"] for r in t) for t in thirds],
        "start_third_bounds": [[t[0]["start_utc"], t[-1]["start_utc"]] for t in thirds],
        "round_of_max_hist_unusable": count_by("round_of_max", un),
        "round_of_min_hist_unusable": count_by("round_of_min", un),
        "outlier_round_relative_position_in_worker_unusable": {"n": len(pos), "quantiles": {str(p): q(sorted(pos), p) for p in (0.1, 0.5, 0.9)} if pos else None},
        "unusable_records": [{k: r[k] for k in ("pair", "workload", "scope", "entity", "ratio", "round_of_max", "round_of_min")} for r in un],
    }
# P5 comparison
p5_recs = []
for f in sorted(glob.glob(os.path.join(P5, "timing", "*", "result.json"))):
    w = load(f)
    for r in w["timing"]["records"]:
        d = r["durations_ns"]
        rm = [st.median(d[i * 10:(i + 1) * 10]) for i in range(8)]
        p5_recs.append({"worker": os.path.basename(os.path.dirname(f)), "bs": r["batch_size"], "scope": r["scope"],
                        "variant": r["variant"], "ratio": max(rm) / min(rm), "median": st.median(d),
                        "usable": min(d) > 0 and st.median(d) >= 100 * r["resolution_ns"] and max(rm) / min(rm) <= 1.25,
                        "stored_usable": r["usable"]})
p5r = sorted(r["ratio"] for r in p5_recs)
rel["P5"] = {"records": len(p5_recs), "unusable": sum(not r["usable"] for r in p5_recs),
             "stored_unusable": sum(not r["stored_usable"] for r in p5_recs),
             "round_median_ratio_quantiles": {str(p): p5r[min(len(p5r) - 1, max(0, math.ceil(len(p5r) * p) - 1))] for p in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)},
             "unusable_records": [r for r in p5_recs if not r["usable"]]}
out["f_reliability"] = rel

# --------------------------------------------------------------------------- (g) sensitivity (NOT registered)
out["g_sensitivity_NOT_REGISTERED"] = {
    "label": "Descriptive sensitivity only: clauses recomputed over pairs where both records are usable. NOT a registered result and NOT a substitute verdict.",
    "per_kind": {k: {ref: {name: {"usable_pairs": s[name]["usable_pairs"],
                                  **{sc: s[name][sc] for sc in s[name] if sc in ("addition_forward", "model_forward", "addition_forward_vs_T0")},
                                  "all_clauses_met_on_usable_subset": s[name]["clauses_met_pointwise"]}
                           for name in ("SP", "PAR", "PR")}
                     for ref, s in sens[k].items()} for k in KINDS},
}

# round-matched ratios (entities are interleaved within each round, so round r of numerator and
# denominator ran close together in time). Descriptive only; NOT a registered statistic.
rm_out = {}
for kind in KINDS:
    v = sel_tree[kind]["selected"]
    for sc in ("addition_forward", "model_forward"):
        for ref in (f"flat:{comparator}", f"{kind}:T0", "flat:F0"):
            rr = []
            for p in PAIRS:
                a = con[p][("W8", sc, f"{kind}:{v}")]["round_medians"]
                b = con[p][("W8", sc, ref)]["round_medians"]
                rr.extend(x / y for x, y in zip(a, b))
            srt = sorted(rr)
            rm_out[f"{kind}:{v}/W8/{sc}/over_{ref}"] = {
                "round_pairs": len(rr), "lt_1": sum(x < 1 for x in rr), "le_0.80": sum(x <= 0.80 for x in rr),
                "le_0.50": sum(x <= 0.50 for x in rr), "min": srt[0], "median": st.median(rr), "max": srt[-1]}
    for wl in ("W1",):
        for sc in ("addition_forward", "model_forward"):
            rr = []
            for p in PAIRS:
                a = con[p][(wl, sc, f"{kind}:{v}")]["round_medians"]
                b = con[p][(wl, sc, f"flat:{comparator}")]["round_medians"]
                rr.extend(x / y for x, y in zip(a, b))
            rm_out[f"{kind}:{v}/{wl}/{sc}/over_flat:{comparator}"] = {"round_pairs": len(rr), "lt_1": sum(x < 1 for x in rr),
                                                                   "min": min(rr), "median": st.median(rr), "max": max(rr)}
out["g_round_matched_NOT_REGISTERED"] = rm_out

# --------------------------------------------------------------------------- (h) absolute medians and P5 comparison
absm = {}
for stage_name, stage_t in (("confirm", con), ("screen", scr)):
    for key in sorted(stage_t[PAIRS[0]]):
        meds = [stage_t[p][key]["median"] / 1000 for p in PAIRS]
        absm[f"{stage_name}/{key[2]}/{key[0]}/{key[1]}"] = {"median_us": st.median(meds), "min_us": min(meds), "max_us": max(meds)}
p5_abs = {}
for r in p5_recs:
    if r["worker"].endswith("baseline"):
        continue
    p5_abs.setdefault((r["variant"], r["bs"], r["scope"]), []).append(r["median"] / 1000)
p5_abs = {f"{v}/bs{bs}/{sc}": {"median_us": st.median(x), "min_us": min(x), "max_us": max(x), "n": len(x)} for (v, bs, sc), x in sorted(p5_abs.items())}
comp = {}
for kind_p6, p5v in (("fixed_tree:T0", "fixed_tree"), ("learned_tree:T0", "learned_tree"), ("flat:F0", "flat")):
    for wl, bs in (("W8", 8), ("W1", 1)):
        for sc in SCOPES:
            a = absm.get(f"confirm/{kind_p6}/{wl}/{sc}")
            b = p5_abs.get(f"{p5v}/bs{bs}/{sc}")
            if a and b:
                comp[f"{kind_p6} vs P5 {p5v} {wl}/{sc}"] = {"p6_confirm_median_us": a["median_us"], "p5_median_us": b["median_us"],
                                                             "p6_over_p5": a["median_us"] / b["median_us"]}
# reference tree/flat ratio in P6 (T0/F0) vs P5 (tree/flat) per pair
p5_pair = {}
for r in p5_recs:
    if r["worker"].endswith("baseline"):
        continue
    p5_pair[(r["worker"], r["bs"], r["scope"], r["variant"])] = r["median"]
ref_ratio = {}
for kind in KINDS:
    for wl, bs in (("W8", 8), ("W1", 1)):
        for sc in ("addition_forward", "model_forward"):
            p6 = [con[p][(wl, sc, f"{kind}:T0")]["median"] / con[p][(wl, sc, "flat:F0")]["median"] for p in PAIRS]
            p5 = [p5_pair[(label(p), bs, sc, kind)] / p5_pair[(label(p), bs, sc, "flat")] for p in PAIRS]
            ref_ratio[f"{kind}/{wl}/{sc}"] = {"P6_confirm_T0_over_F0_gm": gmean(p6), "P5_tree_over_flat_gm": gmean(p5)}
out["h_absolute"] = {"p6": absm, "p5": p5_abs, "p6_reference_vs_p5": comp, "reference_ratio_T0_over_F0_vs_P5": ref_ratio}

# --------------------------------------------------------------------------- (i) memory, construction, first call, caps
mem = {}
for stage_name in ("confirm", "screen"):
    recs = {p: load(os.path.join(stage_dir[stage_name], "workers", f"{label(p)}.json")) for p in PAIRS}
    agg = {}
    for fld in ("persistent_extra_bytes", "construction_ns", "binding_hash_ns", "first_call_after_load_ns"):
        for e in recs[PAIRS[0]][fld]:
            xs = [recs[p][fld][e] for p in PAIRS]
            agg[f"{fld}/{e}"] = {"median": st.median(xs), "min": min(xs), "max": max(xs)}
    for e in recs[PAIRS[0]]["memory_profile"]:
        for fld in ("allocated_bytes_per_call", "peak_live_bytes_per_call"):
            xs = [recs[p]["memory_profile"][e][fld] for p in PAIRS]
            agg[f"memory_profile/{e}/{fld}"] = {"median": st.median(xs), "min": min(xs), "max": max(xs)}
    for pt in ("before_load", "after_load", "after_cache_construction", "after_timing"):
        xs = [recs[p]["rss_bytes"][pt] for p in PAIRS]
        agg[f"rss/{pt}"] = {"median": st.median(xs), "min": min(xs), "max": max(xs)}
    gf = {}
    for e in recs[PAIRS[0]]["guard_fallback"]:
        qq = sum(recs[p]["guard_fallback"][e]["queries"] for p in PAIRS)
        ff = sum(recs[p]["guard_fallback"][e]["fallback_queries"] for p in PAIRS)
        per = [recs[p]["guard_fallback"][e]["fraction"] for p in PAIRS if recs[p]["guard_fallback"][e]["fraction"] is not None]
        gf[e] = {"queries": qq, "fallback": ff, "fraction": ff / qq if qq else None,
                 "per_worker_min": min(per) if per else None, "per_worker_max": max(per) if per else None}
    mem[stage_name] = {"aggregates": agg, "guard_fallback_timed": gf}
    # fallback rate per worker vs speed ratio
    if stage_name == "confirm":
        corr = {}
        for kind in KINDS:
            v = sel_tree[kind]["selected"]
            xs = [recs[p]["guard_fallback"][f"{kind}:{v}"]["fraction"] for p in PAIRS]
            ys = [con[p][("W8", "addition_forward", f"{kind}:{v}")]["median"] / con[p][("W8", "addition_forward", f"{kind}:T0")]["median"] for p in PAIRS]
            corr[kind] = {"pearson_fallback_fraction_vs_W8_add_ratio_to_T0": st.correlation(xs, ys),
                          "fallback_fraction_range": [min(xs), max(xs)]}
        mem[stage_name]["fallback_vs_speed"] = corr
caps = {}
for stage_name, stage_cap, worker_cap in (("equivalence", 1200, None), ("screen", 1200, 90), ("confirm", 600, 45)):
    wj = load(os.path.join(stage_dir[stage_name], "workers.json"))
    rs = load(os.path.join(stage_dir[stage_name], "result.json"))
    walls = [w["wall_seconds"] for w in wj["workers"]]
    caps[stage_name] = {"active_worker_seconds_sum": math.fsum(walls), "stage_cap_s": stage_cap,
                        "max_worker_wall_s": max(walls), "worker_cap_s": worker_cap,
                        "peak_worker_rss_bytes": max(w["peak_rss_bytes"] for w in wj["workers"]),
                        "peak_stage_process_tree_rss_bytes": rs.get("peak_stage_process_tree_rss_bytes"),
                        "stage_wall_seconds": rs.get("stage_wall_seconds"), "elapsed": wj.get("elapsed"),
                        "all_completed": all(w["status"] == "completed" for w in wj["workers"]), "workers": len(walls)}
caps["combined_active_worker_seconds"] = math.fsum(caps[s]["active_worker_seconds_sum"] for s in ("equivalence", "screen", "confirm"))
caps["combined_cap_s"] = 3000
mem["caps"] = caps
out["i_memory_and_resources"] = mem

# --------------------------------------------------------------------------- (j) integrity
integ = {}
p5_nll = {}
p5_hash = {}
for p in PAIRS:
    for kind in ("flat", "fixed_tree", "learned_tree"):
        r = load(os.path.join(P5, f"b{p[0]}-o{p[1]}-{kind}-s{p[2]}", "result.json"))
        p5_nll[(p, kind)] = r["final"]["nll"] if isinstance(r["final"], dict) and "nll" in r["final"] else None
        p5_hash[(p, kind)] = r.get("checkpoint_state_sha256")
for stage_name in ("equivalence", "screen", "confirm"):
    bad = []
    for p in PAIRS:
        rec = load(os.path.join(stage_dir[stage_name], "workers", f"{label(p)}.json"))
        sr = rec["source_recheck_at_worker_end"]
        if not (sr["archive_unchanged"] and sr["p6_sources_unchanged"]):
            bad.append([label(p), "source_recheck"])
        for kind, ev in rec["checkpoint_evidence"].items():
            if p5_nll[(p, kind)] is not None and ev["recorded_final_nll"] != p5_nll[(p, kind)]:
                bad.append([label(p), kind, "recorded_final_nll != P5 record", ev["recorded_final_nll"], p5_nll[(p, kind)]])
            h = p5_hash[(p, kind)]
            hv = h.get("checkpoint-512") if isinstance(h, dict) else h
            if hv is not None and ev["state_sha256"] != hv:
                bad.append([label(p), kind, "state_sha256 != P5 record"])
        if stage_name == "equivalence":
            for kind, ck in rec["checkpoints"].items():
                if not (ck["integrity"]["bitwise_equal"] and ck["checkpoint_files_unchanged_before_and_after"] and ck["model_state_and_rng_unchanged"]):
                    bad.append([label(p), kind, "integrity"])
        else:
            if not (rec["checkpoint_files_unchanged"] and rec["state_and_rng_unchanged"]):
                bad.append([label(p), "files/state"])
            for kind, x in rec["integrity_replay_before_timing"].items():
                if not (x["bitwise_equal"] and x["replayed_nll"] == x["recorded_final_nll"]):
                    bad.append([label(p), kind, "replay"])
            if rec.get("dry_run") or rec.get("synthetic"):
                bad.append([label(p), "dry_run/synthetic"])
    integ[stage_name] = {"workers": 27, "problems": bad}
meta = {}
for mf in sorted(glob.glob(os.path.join(RES, "*", "*", "manifest.json")) + glob.glob(os.path.join(RES, "*", "*", "workers", "*.manifest.json"))
                 + glob.glob(os.path.join(ROOT, "results", "p6-q-2026-11-13", "**", "manifest.json"), recursive=True)):
    m = load(mf)
    k = (m.get("authorized_spec_reference"), m.get("question_id"), m.get("hypothesis_null_reason"), m.get("experiment_family"),
         m.get("astra_result_review"), m.get("authorized_result_review"))
    meta.setdefault(json.dumps(k), []).append(os.path.relpath(mf, ROOT))
integ["manifest_metadata_variants"] = {k: {"count": len(v), "example": v[0]} for k, v in meta.items()}
integ["p5_reference_fields_found"] = {"final_nll": sum(v is not None for v in p5_nll.values()),
                                      "state_sha": sum(v is not None for v in p5_hash.values())}
out["j_integrity"] = integ

out["discrepancies_with_implementation_analysis"] = discrepancies
out["environment"] = {"python": sys.version, "argv": sys.argv, "cwd": os.getcwd()}
with open(OUT, "w") as fh:
    json.dump(out, fh, indent=1, sort_keys=True, default=str)

# --------------------------------------------------------------------------- console summary
print("records checked", out["a_records"]["records_checked"], "mismatches", len(record_mismatch), "metrics mismatches", len(metrics_mismatch))
print("EQ", {v: (s["counts"], s["EQ"]) for v, s in eq_summary.items()}, "classification disagreements", len(eq_fail))
print("selection", {k: sel_tree[k]["selected"] for k in KINDS}, "comparator", comparator)
print("linkage", link)
for k in KINDS:
    r = crit[k]["registered"]
    print(k, {n: (r[n]["verdict"], r[n]["clauses_met_pointwise"]) for n in ("SP", "PAR", "PR")})
print("reliability", {s: (rel[s]["records"], rel[s]["unusable"]) for s in rel})
print("hypotheses", out["d_hypotheses"])
print("discrepancies", len(discrepancies))
for d in discrepancies:
    print("  -", d)
