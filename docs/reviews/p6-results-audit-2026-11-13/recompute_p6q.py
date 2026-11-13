"""Independent recomputation of P6-Q from compact per-checkpoint records (auditor role).

Standard library only (the raw .bin arrays are read with the `array` module, little-endian
native on the audit machine, after checking their SHA-256). Does not import arborlm.
Reads:
  results/p6-q-2026-11-13/{cells/<label>/result.json, suite/result.json, analysis.json}
  results/p5-2026-11-13/<cell>/result.json                 (P5 registered NLL and T2P concentration)
  experiments/P6Q-*/cells/<run_id>/arrays/*.bin             (raw per-query arrays, sample of 4 checkpoints)
Writes recompute_p6q.json next to this file.

Flag rules are ADR-0011 section 4.4 and clarifications 6-15, 29 only.
"""

from __future__ import annotations

import array
import glob
import hashlib
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RES = os.path.join(ROOT, "results", "p6-q-2026-11-13")
P5 = os.path.join(ROOT, "results", "p5-2026-11-13")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recompute_p6q.json")

BACKBONES = (101, 102, 103)
ORDERS = (301, 302, 303)
SEEDS = (501, 502, 503)
PAIRS = [(b, o, s) for b in BACKBONES for o in ORDERS for s in SEEDS]
PARENTS = [(b, o) for b in BACKBONES for o in ORDERS]
KINDS = ("fixed_tree", "learned_tree")
Q = 32768
SLOTS, BRANCHES, PER_BRANCH, TEMP = 4096, 16, 256, 0.2
# Raw-array sample, fixed before looking at any per-checkpoint value: one fixed and two learned
# finals spanning backbones/orders/seeds, plus the first step-0 checkpoint.
RAW_SAMPLE = ["b101-o301-fixed_tree-s501-final", "b102-o302-learned_tree-s502-final",
              "b103-o303-learned_tree-s503-final", "b101-o301-shared_initial-s501"]


def load(path):
    with open(path) as fh:
        return json.load(fh)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flabel(p, kind):
    return f"b{p[0]}-o{p[1]}-{kind}-s{p[2]}-final"


def ilabel(p):
    return f"b{p[0]}-o{p[1]}-shared_initial-s{p[2]}"


def mean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs)


def parent_means(vals):  # vals: dict pair -> value
    return {f"b{b}-o{o}": mean(vals[(b, o, s)] for s in SEEDS) for b, o in PARENTS}


def dist(xs):
    xs = sorted(xs)
    return {"n": len(xs), "mean": mean(xs), "sd": st.stdev(xs) if len(xs) > 1 else None, "min": xs[0],
            "median": st.median(xs), "max": xs[-1]}


disc: list[str] = []
ana = load(os.path.join(RES, "analysis.json"))
suite = load(os.path.join(RES, "suite", "result.json"))
cells = {}
for d in sorted(glob.glob(os.path.join(RES, "cells", "*"))):
    cells[os.path.basename(d)] = load(os.path.join(d, "result.json"))
out: dict = {"cells_found": len(cells)}

# --------------------------------------------------------------------------- completeness
finals = {(p, k): cells.get(flabel(p, k)) for p in PAIRS for k in KINDS}
missing = [flabel(p, k) for (p, k), c in finals.items() if c is None or c.get("outcome") != "completed"]
inits = {p: cells.get(ilabel(p)) for p in PAIRS}
init_done = [ilabel(p) for p, c in inits.items() if c is not None and c.get("outcome") == "completed"]
init_missing = [ilabel(p) for p, c in inits.items() if c is None or c.get("outcome") != "completed"]
suite_status = {c["label"]: (c["status"], c.get("reason")) for c in suite["cells"]}
out["completeness"] = {"finals_missing_or_incomplete": missing, "step0_completed": len(init_done),
                       "step0_unexecuted": init_missing,
                       "suite_status_of_unexecuted": {x: suite_status.get(x) for x in init_missing},
                       "suite_counts": {s: sum(1 for c in suite["cells"] if c["status"] == s) for s in {c["status"] for c in suite["cells"]}}}
if sorted(init_missing) != sorted(x["label"] for x in ana["step0_unexecuted_or_failed"]):
    disc("step-0 unexecuted list differs from analysis")
flags_status = "INCOMPLETE" if missing else "COMPUTED"


# --------------------------------------------------------------------------- per-cell internal consistency
def cell_checks(c, final=True):
    probs = []
    for rule in ("P", "C"):
        r = c["recall"][rule]
        h = r["histogram"]
        if sum(h) != r["queries"] or r["queries"] != Q:
            probs.append(f"recall {rule} histogram sum")
        ov = sum(k * n for k, n in enumerate(h))
        if ov != r["overlap_sum"]:
            probs.append(f"recall {rule} overlap_sum")
        if r["mean"] != ov / (8 * Q):
            probs.append(f"recall {rule} mean {r['mean']} vs {ov / (8 * Q)}")
        if r["fraction_one"] != h[8] / Q:
            probs.append(f"recall {rule} fraction_one")
        lo = c["lost"][rule]
        if lo["lost_candidates"] != 8 * Q - ov:
            probs.append(f"lost {rule} count vs recall")
        if sum(lo["route_rank_histogram"]) != lo["lost_candidates"]:
            probs.append(f"lost {rule} rank histogram sum")
        lph = lo["lost_per_query_histogram"]
        if sum(lph) != Q or [lph[k] for k in range(9)] != [h[8 - k] for k in range(9)]:
            probs.append(f"lost {rule} per-query histogram is not the mirror of the recall histogram")
        if lo["queries_with_loss"] != Q - h[8]:
            probs.append(f"lost {rule} queries_with_loss")
        if final:
            if lo["lost_trained"] + lo["lost_untrained"] != lo["lost_candidates"]:
                probs.append(f"lost {rule} trained+untrained")
            rt = lo["reference_recall_trained"]
            if rt["reference_slots_total"] != 8 * Q:
                probs.append(f"lost {rule} reference_slots_total")
            pooled = (rt["reference_slots_trained"] - lo["lost_trained"]) / rt["reference_slots_trained"]
            if abs(pooled - rt["recall_pooled"]) > 1e-15:
                probs.append(f"lost {rule} recall_pooled {rt['recall_pooled']} vs {pooled}")
    if c["lost"]["P"]["route_rank_histogram"][0] or c["lost"]["P"]["route_rank_histogram"][1]:
        probs.append("gate iii: lost X16P slot in route rank 1 or 2")
    if abs(c["recall_by_width"]["2"]["mean"] - c["recall"]["P"]["mean"]) > 0 or c["recall_by_width"]["16"]["mean"] != 1.0:
        probs.append("width curve endpoints")
    ws = [c["recall_by_width"][str(k)]["mean"] for k in (2, 3, 4, 6, 8, 12, 16)]
    if any(b < a for a, b in zip(ws, ws[1:])):
        probs.append("width curve not monotone")
    for key, rule in (("restrict", "X16P"), ("prior", "T2N"), ("both", "X16N")):
        if c["delta_nll"][key] != c["nll"][rule] - c["nll"]["T2P"]:
            probs.append(f"delta {key} != nll difference ({c['delta_nll'][key]} vs {c['nll'][rule] - c['nll']['T2P']})")
    for rule in ("T2P", "T2N", "X16P", "X16N"):
        co = c["concentration"][rule]
        cnt = co["selected_slot_counts"]
        tot = sum(cnt)
        if tot != 8 * Q:
            probs.append(f"concentration {rule} counts sum")
        uniq = sum(1 for x in cnt if x)
        ent = -math.fsum((x / tot) * math.log(x / tot) for x in cnt if x)
        if uniq != co["unique_selected_slots"]:
            probs.append(f"concentration {rule} unique")
        if abs(math.exp(ent) - co["effective_selected_slots"]) > 1e-9 * co["effective_selected_slots"]:
            probs.append(f"concentration {rule} effective {co['effective_selected_slots']} vs {math.exp(ent)}")
        if max(cnt) / tot != co["hottest_selected_slot_fraction"]:
            probs.append(f"concentration {rule} hottest")
        if abs(ent / math.log(SLOTS) - co["selected_slot_entropy_normalized"]) > 1e-12:
            probs.append(f"concentration {rule} normalized entropy")
        vbc = co["router"]["selected_value_branch_counts"]
        bc = [sum(cnt[b * PER_BRANCH:(b + 1) * PER_BRANCH]) for b in range(BRANCHES)]
        if bc != vbc:
            probs.append(f"concentration {rule} per-branch selected counts vs slot counts (contiguous 256-slot branches)")
    cert = c["certificate"]
    if cert["fraction"] != cert["certified_queries"] / Q:
        probs.append("certificate fraction")
    if cert["certified_queries"] > c["recall"]["P"]["histogram"][8] + cert["certified_with_recall_below_one"]:
        probs.append("certified queries exceed recall-1 queries")
    if c["token_loss"]["X16P"]["changed"]["tokens"] != Q - c["recall"]["P"]["histogram"][8]:
        probs.append("per-token split X16P changed count != queries with recall_P<1")
    if c["token_loss"]["X16N"]["changed"]["tokens"] != Q - c["recall"]["C"]["histogram"][8]:
        probs.append("per-token split X16N changed count != queries with recall_C<1")
    if abs(c["token_loss"]["T2N"]["changed"]["tokens"] / Q - c["prior_effects"]["fraction_t2n_t2p_sets_differ"]) > 0:
        probs.append("per-token split T2N changed count != fraction_t2n_t2p_sets_differ")
    if final:
        cv = c["coverage"]
        if cv["either_changed"] != cv["key_changed"] + cv["value_changed"] - cv["both_changed"]:
            probs.append("coverage either != key + value - both")
        if cv["key_only_changed"] != cv["key_changed"] - cv["both_changed"] or cv["value_only_changed"] != cv["value_changed"] - cv["both_changed"]:
            probs.append("coverage only-counts")
    return probs


consistency = {}
for lab, c in cells.items():
    consistency[lab] = cell_checks(c, final=(c["kind"] == "final"))
out["per_cell_internal_consistency_problems"] = {k: v for k, v in consistency.items() if v}

# --------------------------------------------------------------------------- (a) flags
flags = {}
vals = {}
for k in KINDS:
    v = {
        "recall_P": {p: finals[(p, k)]["recall"]["P"]["mean"] for p in PAIRS},
        "recall_C": {p: finals[(p, k)]["recall"]["C"]["mean"] for p in PAIRS},
        "d_restrict": {p: finals[(p, k)]["nll"]["X16P"] - finals[(p, k)]["nll"]["T2P"] for p in PAIRS},
        "d_prior": {p: finals[(p, k)]["nll"]["T2N"] - finals[(p, k)]["nll"]["T2P"] for p in PAIRS},
        "d_both": {p: finals[(p, k)]["nll"]["X16N"] - finals[(p, k)]["nll"]["T2P"] for p in PAIRS},
    }
    vals[k] = v
    f = {}
    for name, key in (("FID", "recall_P"), ("COS", "recall_C")):
        m = mean(v[key].values())
        pm = parent_means(v[key])
        cells_ok = sum(x >= 0.95 for x in v[key].values())
        par_ok = sum(x >= 0.95 for x in pm.values())
        f[name] = {"mean": m, "cells>=0.95": cells_ok, "parents>=0.95": par_ok, "parent_means": pm,
                   "clauses": {"mean": m >= 0.95, "cells": cells_ok >= 22, "parents": par_ok >= 8}}
        f[name]["passed"] = all(f[name]["clauses"].values())
    m = mean(v["d_restrict"].values())
    pm = parent_means(v["d_restrict"])
    cn = sum(x < 0 for x in v["d_restrict"].values())
    pn = sum(x < 0 for x in pm.values())
    f["LOSS"] = {"mean": m, "cells<0": cn, "parents<0": pn, "parent_means": pm,
                 "clauses": {"mean": m <= -0.005, "cells": cn >= 22, "parents": pn >= 8}}
    f["LOSS"]["passed"] = all(f["LOSS"]["clauses"].values())
    m = mean(v["d_prior"].values())
    pm = parent_means(v["d_prior"])
    sgn = 1 if m > 0 else (-1 if m < 0 else 0)
    cs = sum((x > 0) if sgn > 0 else (x < 0) for x in v["d_prior"].values())
    ps = sum((x > 0) if sgn > 0 else (x < 0) for x in pm.values())
    f["PRIOR"] = {"mean": m, "sign": sgn, "cells_sharing_sign": cs, "parents_sharing_sign": ps, "parent_means": pm,
                  "clauses": {"magnitude": abs(m) >= 0.005, "cells": cs >= 22, "parents": ps >= 8},
                  "gap_to_margin": 0.005 - abs(m)}
    f["PRIOR"]["passed"] = all(f["PRIOR"]["clauses"].values())
    for name in f:
        f[name]["verdict"] = "INCOMPLETE" if flags_status == "INCOMPLETE" else ("PASS" if f[name]["passed"] else "FAIL")
    flags[k] = f
    # compare with analysis
    af = ana["flags"][k]
    for name in ("FID", "COS", "LOSS", "PRIOR"):
        a = af[name]
        if a["passed"] != f[name]["passed"]:
            disc(f"{k} {name} passed: analysis {a['passed']} vs mine {f[name]['passed']}")
        if abs(a["mean"] - f[name]["mean"]) > 1e-15:
            disc(f"{k} {name} mean: analysis {a['mean']} vs mine {f[name]['mean']}")
        for pk, pv in a["parent_means"].items():
            if abs(pv - f[name]["parent_means"][pk]) > 1e-15:
                disc(f"{k} {name} parent {pk}: analysis {pv} vs mine {f[name]['parent_means'][pk]}")
        mine_cl = f[name]["clauses"]
        for ck, cv in a["clauses"].items():
            if mine_cl.get(ck) != cv:
                disc(f"{k} {name} clause {ck}: analysis {cv} vs mine {mine_cl.get(ck)}")
    if af["FID"]["cells_meeting"] != f["FID"]["cells>=0.95"] or af["FID"]["parents_meeting"] != f["FID"]["parents>=0.95"]:
        disc(f"{k} FID counts differ")
    if af["COS"]["cells_meeting"] != f["COS"]["cells>=0.95"] or af["COS"]["parents_meeting"] != f["COS"]["parents>=0.95"]:
        disc(f"{k} COS counts differ")
    if af["LOSS"]["cells_negative"] != f["LOSS"]["cells<0"] or af["LOSS"]["parents_negative"] != f["LOSS"]["parents<0"]:
        disc(f"{k} LOSS counts differ")
    if af["PRIOR"]["cells_with_sign"] != f["PRIOR"]["cells_sharing_sign"] or af["PRIOR"]["parents_with_sign"] != f["PRIOR"]["parents_sharing_sign"] or af["PRIOR"]["sign"] != f["PRIOR"]["sign"]:
        disc(f"{k} PRIOR counts/sign differ")
if ana["flags_status"] != flags_status:
    disc(f"flags_status analysis {ana['flags_status']} vs mine {flags_status}")
# delta field vs nll-field difference
for (p, k), c in finals.items():
    for key, rule in (("restrict", "X16P"), ("prior", "T2N"), ("both", "X16N")):
        if c["delta_nll"][key] != c["nll"][rule] - c["nll"]["T2P"]:
            disc(f"{flabel(p, k)} delta_nll.{key} field differs from nll difference")
out["a_flags"] = flags


# --------------------------------------------------------------------------- (b)-(f) descriptive per kind
def per_kind(getter, kind_cells):
    xs = [getter(c) for c in kind_cells]
    return dist(xs)


desc = {}
for k in KINDS:
    cs = [finals[(p, k)] for p in PAIRS]
    d = {}
    d["recall_P"] = per_kind(lambda c: c["recall"]["P"]["mean"], cs)
    d["recall_C"] = per_kind(lambda c: c["recall"]["C"]["mean"], cs)
    d["fraction_recall_P_eq_1"] = per_kind(lambda c: c["recall"]["P"]["fraction_one"], cs)
    d["fraction_recall_C_eq_1"] = per_kind(lambda c: c["recall"]["C"]["fraction_one"], cs)
    d["pooled_recall_P_histogram"] = [sum(c["recall"]["P"]["histogram"][i] for c in cs) for i in range(9)]
    d["pooled_recall_C_histogram"] = [sum(c["recall"]["C"]["histogram"][i] for c in cs) for i in range(9)]
    d["width_curve_mean_recall_P"] = {w: mean(c["recall_by_width"][w]["mean"] for c in cs) for w in ("2", "3", "4", "6", "8", "12", "16")}
    d["width_curve_fraction_one"] = {w: mean(c["recall_by_width"][w]["fraction_one"] for c in cs) for w in ("2", "3", "4", "6", "8", "12", "16")}
    d["width_cells_mean_ge_0.95"] = {w: sum(c["recall_by_width"][w]["mean"] >= 0.95 for c in cs) for w in ("2", "3", "4", "6", "8", "12", "16")}
    d["certificate_fraction"] = per_kind(lambda c: c["certificate"]["fraction"], cs)
    d["certified_with_recall_below_one_total"] = sum(c["certificate"]["certified_with_recall_below_one"] for c in cs)
    # (c) coverage
    d["fraction_slots_trained"] = per_kind(lambda c: c["coverage"]["either_changed"] / c["coverage"]["slots"], cs)
    d["key_only/value_only totals"] = [sum(c["coverage"]["key_only_changed"] for c in cs), sum(c["coverage"]["value_only_changed"] for c in cs)]
    for rule in ("P", "C"):
        lt = sum(c["lost"][rule]["lost_trained"] for c in cs)
        lu = sum(c["lost"][rule]["lost_untrained"] for c in cs)
        d[f"lost_{rule}_trained_untrained_pooled"] = {"trained": lt, "untrained": lu, "fraction_untrained": lu / (lt + lu)}
        d[f"lost_{rule}_fraction_untrained_per_cell"] = per_kind(lambda c: c["lost"][rule]["lost_untrained"] / c["lost"][rule]["lost_candidates"], cs)
        d[f"recall_{rule}_trained_macro"] = per_kind(lambda c: c["lost"][rule]["reference_recall_trained"]["recall_macro_over_queries_with_trained_reference"], cs)
        d[f"recall_{rule}_trained_pooled"] = per_kind(lambda c: c["lost"][rule]["reference_recall_trained"]["recall_pooled"], cs)
        d[f"reference_{rule}_slots_trained_fraction"] = per_kind(lambda c: c["lost"][rule]["reference_recall_trained"]["reference_slots_trained"] / c["lost"][rule]["reference_recall_trained"]["reference_slots_total"], cs)
        d[f"queries_with_trained_reference_{rule}_min"] = min(c["lost"][rule]["reference_recall_trained"]["queries_with_trained_reference"] for c in cs)
        # (d) route rank and weighted recall
        rh = [sum(c["lost"][rule]["route_rank_histogram"][i] for c in cs) for i in range(16)]
        tot = sum(rh)
        d[f"lost_{rule}_route_rank_pooled_fraction"] = {str(i + 1): rh[i] / tot for i in range(16)}
        d[f"weighted_recall_{rule}"] = per_kind(lambda c: c["weighted_recall"][rule], cs)
    d["lost_P_margin_median_of_cell_medians"] = st.median(c["lost"]["P"]["margin_to_t2p_boundary"]["quantiles"]["0.5"] for c in cs)
    d["lost_P_margin_min"] = min(c["lost"]["P"]["margin_to_t2p_boundary"]["min"] for c in cs)
    # (e) prior effects
    d["fraction_all_selected_in_top1_branch"] = per_kind(lambda c: c["prior_effects"]["fraction_all_selected_in_top1_branch"], cs)
    d["route_gap_median"] = per_kind(lambda c: c["prior_effects"]["route_gap_top1_minus_top2"]["quantiles"]["0.5"], cs)
    d["route_gap_q10"] = per_kind(lambda c: c["prior_effects"]["route_gap_top1_minus_top2"]["quantiles"]["0.1"], cs)
    d["route_gap_q90"] = per_kind(lambda c: c["prior_effects"]["route_gap_top1_minus_top2"]["quantiles"]["0.9"], cs)
    d["route_gap_mean"] = per_kind(lambda c: c["prior_effects"]["route_gap_top1_minus_top2"]["mean"], cs)
    d["fraction_t2n_t2p_sets_differ"] = per_kind(lambda c: c["prior_effects"]["fraction_t2n_t2p_sets_differ"], cs)
    d["t2n_t2p_overlap_mean"] = per_kind(lambda c: c["prior_effects"]["t2n_t2p_overlap_mean"], cs)
    # (f) concentration
    for rule in ("T2P", "T2N", "X16P", "X16N"):
        d[f"conc_{rule}_unique"] = per_kind(lambda c: c["concentration"][rule]["unique_selected_slots"], cs)
        d[f"conc_{rule}_effective"] = per_kind(lambda c: c["concentration"][rule]["effective_selected_slots"], cs)
        d[f"conc_{rule}_hottest"] = per_kind(lambda c: c["concentration"][rule]["hottest_selected_slot_fraction"], cs)
    # (g) NLL deltas
    for key in ("d_restrict", "d_prior", "d_both"):
        xs = list(vals[k][key].values())
        d[key] = {**dist(xs), "negative": sum(x < 0 for x in xs), "zero": sum(x == 0 for x in xs), "positive": sum(x > 0 for x in xs),
                  "parent_means": parent_means(vals[k][key]),
                  "by_backbone": {b: mean(vals[k][key][p] for p in PAIRS if p[0] == b) for b in BACKBONES},
                  "by_order": {o: mean(vals[k][key][p] for p in PAIRS if p[1] == o) for o in ORDERS},
                  "by_seed": {s: mean(vals[k][key][p] for p in PAIRS if p[2] == s) for s in SEEDS}}
    for rule in ("X16P", "T2N", "X16N"):
        for part in ("changed", "unchanged"):
            xs = [c["token_loss"][rule][part]["mean_difference"] for c in cs if c["token_loss"][rule][part]["tokens"]]
            toks = [c["token_loss"][rule][part]["tokens"] for c in cs]
            d[f"token_split_{rule}_{part}"] = {"cells_with_tokens": len(xs), "mean_tokens": mean(toks),
                                               "mean_of_cell_mean_differences": mean(xs) if xs else None,
                                               "cells_negative": sum(x < 0 for x in xs),
                                               "mean_fraction_alternative_lower": mean(c["token_loss"][rule][part]["fraction_alternative_lower"] for c in cs if c["token_loss"][rule][part]["tokens"]) if xs else None}
    desc[k] = d
out["b_to_g_descriptive_by_kind"] = desc

# --------------------------------------------------------------------------- (h) paired learned minus fixed
paired_keys = {
    "recall.P.mean": lambda c: c["recall"]["P"]["mean"], "recall.C.mean": lambda c: c["recall"]["C"]["mean"],
    "delta_nll.restrict": lambda c: c["delta_nll"]["restrict"], "delta_nll.prior": lambda c: c["delta_nll"]["prior"],
    "delta_nll.both": lambda c: c["delta_nll"]["both"], "nll.T2P": lambda c: c["nll"]["T2P"],
    "weighted_recall.P": lambda c: c["weighted_recall"]["P"], "weighted_recall.C": lambda c: c["weighted_recall"]["C"],
    "coverage.either_changed": lambda c: c["coverage"]["either_changed"],
    "certificate.fraction": lambda c: c["certificate"]["fraction"],
    "prior_effects.fraction_all_selected_in_top1_branch": lambda c: c["prior_effects"]["fraction_all_selected_in_top1_branch"],
    "prior_effects.fraction_t2n_t2p_sets_differ": lambda c: c["prior_effects"]["fraction_t2n_t2p_sets_differ"],
    "prior_effects.route_gap_top1_minus_top2.mean": lambda c: c["prior_effects"]["route_gap_top1_minus_top2"]["mean"],
    "concentration.T2P.unique_selected_slots": lambda c: c["concentration"]["T2P"]["unique_selected_slots"],
    "concentration.X16P.unique_selected_slots": lambda c: c["concentration"]["X16P"]["unique_selected_slots"],
    "concentration.X16N.unique_selected_slots": lambda c: c["concentration"]["X16N"]["unique_selected_slots"],
    "concentration.T2P.effective_selected_slots": lambda c: c["concentration"]["T2P"]["effective_selected_slots"],
    "lost.P.lost_untrained": lambda c: c["lost"]["P"]["lost_untrained"],
    "lost.P.reference_recall_trained.recall_pooled": lambda c: c["lost"]["P"]["reference_recall_trained"]["recall_pooled"],
}
paired = {}
for name, g in paired_keys.items():
    diffs = {p: g(finals[(p, "learned_tree")]) - g(finals[(p, "fixed_tree")]) for p in PAIRS}
    pm = parent_means(diffs)
    xs = list(diffs.values())
    paired[name] = {"mean": mean(xs), "sd": st.stdev(xs), "min": min(xs), "max": max(xs), "positive": sum(x > 0 for x in xs),
                    "negative": sum(x < 0 for x in xs), "zero": sum(x == 0 for x in xs),
                    "parents_positive": sum(x > 0 for x in pm.values()), "parents_negative": sum(x < 0 for x in pm.values()),
                    "parent_means": pm}
    a = ana["paired_learned_minus_fixed"].get(name)
    if a is None:
        disc(f"paired {name} absent from analysis")
        continue
    if abs(a["mean_difference"] - paired[name]["mean"]) > 1e-12 * max(1, abs(paired[name]["mean"])) or \
            a["positive"] != paired[name]["positive"] or a["negative"] != paired[name]["negative"] or \
            a["parents_positive"] != paired[name]["parents_positive"] or a["parents_negative"] != paired[name]["parents_negative"]:
        disc(f"paired {name}: analysis {a['mean_difference']} +{a['positive']}/-{a['negative']} vs mine {paired[name]['mean']} +{paired[name]['positive']}/-{paired[name]['negative']}")
out["h_paired_learned_minus_fixed"] = paired

# --------------------------------------------------------------------------- (i) step-0
init_cells = [inits[p] for p in PAIRS if ilabel(p) in init_done]
i_desc = {
    "completed": init_done, "unexecuted": init_missing,
    "recall_P": dist(c["recall"]["P"]["mean"] for c in init_cells),
    "recall_C": dist(c["recall"]["C"]["mean"] for c in init_cells),
    "fraction_recall_P_eq_1": dist(c["recall"]["P"]["fraction_one"] for c in init_cells),
    "d_restrict": dist(c["nll"]["X16P"] - c["nll"]["T2P"] for c in init_cells),
    "d_prior": dist(c["nll"]["T2N"] - c["nll"]["T2P"] for c in init_cells),
    "d_both": dist(c["nll"]["X16N"] - c["nll"]["T2P"] for c in init_cells),
    "certificate_fraction": dist(c["certificate"]["fraction"] for c in init_cells),
    "fraction_all_selected_in_top1_branch": dist(c["prior_effects"]["fraction_all_selected_in_top1_branch"] for c in init_cells),
    "route_gap_median": dist(c["prior_effects"]["route_gap_top1_minus_top2"]["quantiles"]["0.5"] for c in init_cells),
    "conc_T2P_unique": dist(c["concentration"]["T2P"]["unique_selected_slots"] for c in init_cells),
    "coverage_field": sorted({json.dumps(c.get("coverage")) for c in init_cells})[:1],
}
# matched comparison: same pair, step-0 vs fixed final vs learned final
matched = []
for p in PAIRS:
    if ilabel(p) in init_done:
        matched.append({"pair": f"b{p[0]}-o{p[1]}-s{p[2]}", "recall_P_step0": inits[p]["recall"]["P"]["mean"],
                        "recall_P_fixed": finals[(p, "fixed_tree")]["recall"]["P"]["mean"],
                        "recall_P_learned": finals[(p, "learned_tree")]["recall"]["P"]["mean"]})
i_desc["matched_recall_P"] = {"n": len(matched),
                              "mean_step0": mean(m["recall_P_step0"] for m in matched),
                              "mean_fixed_same_pairs": mean(m["recall_P_fixed"] for m in matched),
                              "mean_learned_same_pairs": mean(m["recall_P_learned"] for m in matched),
                              "rows": matched}
ai = ana["initial_checkpoints"]["summary"]
if abs(ai["recall.P.mean"]["mean"] - i_desc["recall_P"]["mean"]) > 1e-15 or ai["recall.P.mean"]["cells"] != len(init_cells):
    disc(f"step-0 recall_P mean analysis {ai['recall.P.mean']['mean']} vs mine {i_desc['recall_P']['mean']}")
out["i_step0"] = i_desc

# --------------------------------------------------------------------------- (j) gates
gates = {"i_fail": [], "ii_fail": [], "iii_fail": [], "iv_fail": [], "iv_disagreements_total": 0, "iv_sets_differ_total": 0,
         "iv_cells_with_disagreements": 0, "iv_min_adjacent_gap_max": 0.0, "iv_boundary_gap_min": None, "state_rng_fail": [],
         "hash_fail": [], "width_cross_check_fail": [], "cert_below_one": 0, "p5_nll_mismatch": [], "p5_conc_mismatch": [],
         "iv_near_tie_flags": {}}
for lab, c in cells.items():
    g = c["gates"]
    if not g["i"]["passed"] or not (g["i"]["unmodified_nll"] == g["i"]["recorded_nll"] == g["i"]["t2p_wrapper_nll"] == c["nll"]["T2P"]):
        gates["i_fail"].append(lab)
    if not g["ii"]["passed"] or g["ii"]["restricted_score_bitwise_mismatch_queries"] or g["ii"]["queries_checked"] != Q:
        gates["ii_fail"].append(lab)
    if not g["iii"]["passed"]:
        gates["iii_fail"].append(lab)
    iv = g["iv"]
    # clarification 7: stop only when the ID sets differ AND the reference boundary gap exceeds 1e-5
    if not iv["passed"]:
        gates["iv_fail"].append(lab + " (record says not passed)")
    for dd in iv["disagreements"]:
        sd = sorted(dd["frozen_ids"]) != sorted(dd["reference_ids"])
        if sd != dd["sets_differ"]:
            gates["iv_fail"].append(f"{lab} q{dd['query']} sets_differ flag inconsistent")
        if sd and dd["boundary_gap"] > iv["near_tie_threshold"]:
            gates["iv_fail"].append(f"{lab} q{dd['query']} sets differ outside near-tie")
        if (dd["boundary_gap"] <= iv["near_tie_threshold"]) != dd["near_tie"]:
            gates["iv_fail"].append(f"{lab} q{dd['query']} near_tie flag inconsistent")
        if sd:
            gates.setdefault("iv_sets_differ_list", []).append({"cell": lab, "query": dd["query"], "rule": dd["rule"],
                                                                "boundary_gap": dd["boundary_gap"],
                                                                "symmetric_difference": sorted(set(dd["frozen_ids"]) ^ set(dd["reference_ids"]))})
    if iv["disagreement_count"] != len(iv["disagreements"]):
        gates["iv_fail"].append(lab + " (count != list length)")
    gates["iv_disagreements_total"] += iv["disagreement_count"]
    gates["iv_sets_differ_total"] += iv["sets_differ_count"]
    gates["iv_cells_with_disagreements"] += bool(iv["disagreement_count"])
    for dd in iv["disagreements"]:
        same_set = sorted(dd["frozen_ids"]) == sorted(dd.get("reference_ids", dd.get("float64_ids", dd["frozen_ids"])))
        if not same_set:
            gates["iv_sets_differ_total_recounted"] = gates.get("iv_sets_differ_total_recounted", 0) + 1
        gates["iv_min_adjacent_gap_max"] = max(gates["iv_min_adjacent_gap_max"], dd["min_adjacent_gap_top8"])
        bg = dd["boundary_gap"]
        gates["iv_boundary_gap_min"] = bg if gates["iv_boundary_gap_min"] is None else min(gates["iv_boundary_gap_min"], bg)
        for kk, vv in dd.items():
            if kk.startswith("near_tie") or kk in ("rule", "kind"):
                gates["iv_near_tie_flags"][f"{kk}={vv}"] = gates["iv_near_tie_flags"].get(f"{kk}={vv}", 0) + 1
    if not g["state_and_rng_unchanged"]:
        gates["state_rng_fail"].append(lab)
    ck = c["checkpoint"]
    if ck["state_sha256_before"] != ck["state_sha256_after"]:
        gates["hash_fail"].append(lab)
    for kk, vv in ck["state_sha256_before"].items():
        if ck["recorded_state_sha256"].get(kk) != vv:
            gates["hash_fail"].append(lab + " vs recorded " + kk)
    if not c["width_cross_check"]["passed"]:
        gates["width_cross_check_fail"].append(lab)
    gates["cert_below_one"] += c["certificate"]["certified_with_recall_below_one"]
    # P5 registered NLL and T2P concentration (finals only; P5 cell directory per kind)
    if c["kind"] == "final":
        cl = c["cell"]
        p5 = load(os.path.join(P5, f"b{cl['backbone']}-o{cl['order']}-{cl['variant']}-s{cl['seed']}", "result.json"))
        if p5["final"]["nll"] != c["nll"]["T2P"]:
            gates["p5_nll_mismatch"].append(lab)
        r5 = p5["final"]["retrieval"]
        mine = c["concentration"]["T2P"]
        for kk in ("unique_selected_slots", "effective_selected_slots", "hottest_selected_slot_fraction", "selected_slot_counts"):
            if r5[kk] != mine[kk]:
                gates["p5_conc_mismatch"].append(f"{lab}:{kk}")
    else:
        cl = c["cell"]
        for kind in KINDS:
            p5 = load(os.path.join(P5, f"b{cl['backbone']}-o{cl['order']}-{kind}-s{cl['seed']}", "result.json"))
            ini = p5.get("initial", {})
            if isinstance(ini, dict) and "nll" in ini and ini["nll"] != c["nll"]["T2P"]:
                gates["p5_nll_mismatch"].append(f"{lab} vs P5 {kind} initial")
            if isinstance(ini, dict) and "retrieval" in ini:
                if ini["retrieval"]["selected_slot_counts"] != c["concentration"]["T2P"]["selected_slot_counts"]:
                    gates["p5_conc_mismatch"].append(f"{lab} vs P5 {kind} initial")
out["j_gates"] = gates
# example disagreement record keys, so the reader can see the schema used
ex = next((dd for c in cells.values() for dd in c["gates"]["iv"]["disagreements"]), None)
out["j_gates"]["iv_example_record"] = ex

# --------------------------------------------------------------------------- (k) resources
walls = [c["wall_seconds"] for c in suite["cells"] if c["status"] == "completed"]
rss = [c["peak_rss_bytes"] for c in suite["cells"] if c.get("peak_rss_bytes")]
cell_rss = [c["resources"]["peak_rss_bytes_ru_maxrss"] for c in cells.values()]
out["k_resources"] = {"active_worker_seconds": suite["active_worker_seconds"], "cap_s": 1800,
                      "sum_completed_wall_seconds": math.fsum(walls), "max_cell_wall_s": max(walls), "per_cell_cap_s": 60,
                      "max_suite_sampled_rss_bytes": max(rss), "max_cell_ru_maxrss_bytes": max(cell_rss), "rss_cap_bytes": 2 * 1024 ** 3,
                      "suite_wall_seconds": suite.get("suite_wall_seconds"), "reason": suite["reason"],
                      "final_wall": dist(c["wall_seconds"] for c in suite["cells"] if c["status"] == "completed" and c["label"].endswith("-final")),
                      "step0_wall": dist(c["wall_seconds"] for c in suite["cells"] if c["status"] == "completed" and "shared_initial" in c["label"]),
                      "started_with_remaining_min": min(c["started_with_remaining_seconds"] for c in suite["cells"] if c["status"] == "completed")}

# --------------------------------------------------------------------------- raw arrays (sample)
run_of = {c["label"]: c["run_id"] for c in suite["cells"] if c.get("run_id")}
expdir = sorted(glob.glob(os.path.join(ROOT, "experiments", "P6Q-*")))
assert len(expdir) == 1, expdir
TYPECODE = {"float32": ("f", 4), "float64": ("d", 8), "int16": ("h", 2), "int8": ("b", 1), "uint8": ("B", 1)}


def read_arr(lab, name, meta):
    path = os.path.join(expdir[0], "cells", run_of[lab], "arrays", meta["file"])
    raw = open(path, "rb").read()
    ok = hashlib.sha256(raw).hexdigest() == meta["sha256"] and len(raw) == meta["bytes"]
    tc, size = TYPECODE[meta["dtype"]]
    a = array.array(tc)
    a.frombytes(raw)
    assert a.itemsize == size and sys.byteorder == "little"
    n = 1
    for s in meta["shape"]:
        n *= s
    assert len(a) == n
    return a, ok


raw_out = {}
for lab in RAW_SAMPLE:
    c = cells[lab]
    meta = c["arrays"]
    arr, sha_ok = {}, {}
    for name, m in meta.items():
        arr[name], sha_ok[name] = read_arr(lab, name, m)
    r = {"sha256_all_ok": all(sha_ok.values()), "sha256_failures": [k for k, v in sha_ok.items() if not v]}

    def rows(a, w):
        return [a[i * w:(i + 1) * w] for i in range(len(a) // w)]
    sel = {rule: rows(arr[f"selected_ids_{rule}"], 8) for rule in ("T2P", "T2N", "X16P", "X16N")}
    sets = {rule: [set(x) for x in v] for rule, v in sel.items()}
    for rule, ref in (("P", "X16P"), ("C", "X16N")):
        ov = [len(a & b) for a, b in zip(sets["T2P"], sets[ref])]
        h = [0] * 9
        for x in ov:
            h[x] += 1
        r[f"recall_{rule}"] = sum(ov) / (8 * Q)
        r[f"recall_{rule}_matches_record"] = r[f"recall_{rule}"] == c["recall"][rule]["mean"] and h == c["recall"][rule]["histogram"]
        w = rows(arr[f"softmax_weights_{ref}"], 8)
        wr = mean(math.fsum(wt for sid, wt in zip(ids, ww) if sid in s2) for ids, ww, s2 in zip(sel[ref], w, sets["T2P"]))
        r[f"weighted_recall_{rule}"] = wr
        r[f"weighted_recall_{rule}_abs_diff"] = abs(wr - c["weighted_recall"][rule])
        # lost route ranks from the X16 visited-branch order (route-rank order)
        vb = rows(arr[f"visited_branches_{ref}"], 16)
        rh = [0] * 16
        lt = lu = 0
        either = None
        if c["kind"] == "final":
            kc, vc = arr["coverage_key_changed"], arr["coverage_value_changed"]
            either = [kc[i] or vc[i] for i in range(SLOTS)]
        for q in range(Q):
            rank = {b: i for i, b in enumerate(vb[q])}
            for sid in sets[ref][q] - sets["T2P"][q]:
                rh[rank[sid // PER_BRANCH]] += 1
                if either is not None:
                    if either[sid]:
                        lt += 1
                    else:
                        lu += 1
        r[f"lost_{rule}_rank_hist_matches"] = rh == c["lost"][rule]["route_rank_histogram"]
        if either is not None:
            r[f"lost_{rule}_trained_untrained"] = [lt, lu]
            r[f"lost_{rule}_trained_matches"] = [lt, lu] == [c["lost"][rule]["lost_trained"], c["lost"][rule]["lost_untrained"]]
    if c["kind"] == "final":
        r["fraction_trained_raw"] = sum(1 for i in range(SLOTS) if arr["coverage_key_changed"][i] or arr["coverage_value_changed"][i]) / SLOTS
        r["fraction_trained_matches"] = r["fraction_trained_raw"] == c["coverage"]["either_changed"] / SLOTS
        r["key_changed_equals_value_changed_array"] = arr["coverage_key_changed"] == arr["coverage_value_changed"]
    # width curve
    wc = {}
    for wdt in (3, 4, 6, 8, 12):
        ws = [set(x) for x in rows(arr[f"selected_ids_width{wdt}"], 8)]
        wc[wdt] = sum(len(a & b) for a, b in zip(ws, sets["X16P"])) / (8 * Q)
    r["width_curve_matches"] = all(wc[w] == c["recall_by_width"][str(w)]["mean"] for w in wc)
    # NLL deltas from per-token losses (float32 values summed in float64)
    tl = {rule: arr[f"token_loss_{rule}"] for rule in ("T2P", "T2N", "X16P", "X16N")}
    mloss = {rule: math.fsum(v) / Q for rule, v in tl.items()}
    r["token_mean_loss"] = mloss
    r["token_mean_vs_registered_nll_abs_diff"] = {rule: abs(mloss[rule] - c["nll"][rule]) for rule in mloss}
    r["delta_from_tokens"] = {"restrict": mloss["X16P"] - mloss["T2P"], "prior": mloss["T2N"] - mloss["T2P"], "both": mloss["X16N"] - mloss["T2P"]}
    r["delta_record"] = c["delta_nll"]
    r["delta_abs_diff_tokens_vs_record"] = {k2: abs(r["delta_from_tokens"][k2] - c["delta_nll"][k2]) for k2 in c["delta_nll"]}
    # per-token split for X16P
    ch = [i for i in range(Q) if sets["X16P"][i] != sets["T2P"][i]]
    r["token_split_X16P_changed_tokens"] = len(ch)
    r["token_split_X16P_changed_mean_diff"] = math.fsum(tl["X16P"][i] - tl["T2P"][i] for i in ch) / len(ch) if ch else None
    r["token_split_X16P_changed_mean_diff_record"] = c["token_loss"]["X16P"]["changed"]["mean_difference"]
    # prior effects
    rs = rows(arr["route_scores_T2P"], 16)
    vb2 = rows(arr["visited_branches_T2P"], 2)
    gaps = []
    allt1 = 0
    cert = 0
    for q in range(Q):
        srt = sorted(rs[q], reverse=True)
        gaps.append(srt[0] - srt[1])
        if all(sid // PER_BRANCH == vb2[q][0] for sid in sel["T2P"][q]):
            allt1 += 1
        m = max(rs[q])
        lse = m + math.log(math.fsum(math.exp(x - m) for x in rs[q]))
        unvisited = max(rs[q][b] for b in range(BRANCHES) if b not in (vb2[q][0], vb2[q][1])) - lse
        s8 = arr["selected_scores_T2P"][q * 8 + 7]
        if s8 >= 1 / TEMP + unvisited:
            cert += 1
    r["route_gap_mean_raw"] = mean(gaps)
    r["route_gap_mean_record"] = c["prior_effects"]["route_gap_top1_minus_top2"]["mean"]
    r["route_gap_min_max_match"] = [min(gaps) == c["prior_effects"]["route_gap_top1_minus_top2"]["min"], max(gaps) == c["prior_effects"]["route_gap_top1_minus_top2"]["max"]]
    r["fraction_all_in_top1_raw"] = allt1 / Q
    r["fraction_all_in_top1_matches"] = allt1 / Q == c["prior_effects"]["fraction_all_selected_in_top1_branch"]
    r["certificate_raw_float64"] = cert
    r["certificate_record"] = c["certificate"]["certified_queries"]
    r["t2n_t2p_differ_raw"] = sum(a != b for a, b in zip(sets["T2N"], sets["T2P"])) / Q
    r["t2n_t2p_differ_matches"] = r["t2n_t2p_differ_raw"] == c["prior_effects"]["fraction_t2n_t2p_sets_differ"]
    r["route_scores_identical_across_rules"] = all(meta[f"route_scores_{x}"]["sha256"] == meta["route_scores_T2P"]["sha256"] for x in ("T2N", "X16P", "X16N"))
    # concentration
    cm = {}
    for rule in ("T2P", "T2N", "X16P", "X16N"):
        cnt = [0] * SLOTS
        for x in arr[f"selected_ids_{rule}"]:
            cnt[x] += 1
        cm[rule] = cnt == c["concentration"][rule]["selected_slot_counts"]
    r["concentration_counts_match"] = cm
    # T2P selected sorted by descending score, ties by ascending ID (registered tie rule)
    sc = rows(arr["selected_scores_T2P"], 8)
    viol = 0
    for q in range(Q):
        for j in range(7):
            a_, b_ = sc[q][j], sc[q][j + 1]
            if a_ < b_ or (a_ == b_ and sel["T2P"][q][j] > sel["T2P"][q][j + 1]):
                viol += 1
                break
    r["T2P_order_violations"] = viol
    raw_out[lab] = r
out["raw_array_sample"] = raw_out

# --------------------------------------------------------------------------- extra descriptive (NOT registered)
extra = {}
for k in KINDS:
    cs = [finals[(p, k)] for p in PAIRS]
    extra[k] = {
        "cells_d_prior_ge_0.005": sum(vals[k]["d_prior"][p] >= 0.005 for p in PAIRS),
        "parents_d_prior_ge_0.005": sum(x >= 0.005 for x in parent_means(vals[k]["d_prior"]).values()),
        "cells_recall_P_ge_0.95": sum(vals[k]["recall_P"][p] >= 0.95 for p in PAIRS),
        "lost_P_margin_min_exact": min(c["lost"]["P"]["margin_to_t2p_boundary"]["min"] for c in cs),
        "lost_P_margin_q01_min": min(c["lost"]["P"]["margin_to_t2p_boundary"]["quantiles"]["0.01"] for c in cs),
        "corr_recall_P_vs_route_gap_mean": st.correlation([c["recall"]["P"]["mean"] for c in cs], [c["prior_effects"]["route_gap_top1_minus_top2"]["mean"] for c in cs]),
        "corr_recall_P_vs_all_in_top1": st.correlation([c["recall"]["P"]["mean"] for c in cs], [c["prior_effects"]["fraction_all_selected_in_top1_branch"] for c in cs]),
        "corr_recall_C_vs_route_gap_mean": st.correlation([c["recall"]["C"]["mean"] for c in cs], [c["prior_effects"]["route_gap_top1_minus_top2"]["mean"] for c in cs]),
        "corr_d_restrict_vs_recall_P": st.correlation([vals[k]["d_restrict"][p] for p in PAIRS], [vals[k]["recall_P"][p] for p in PAIRS]),
    }
allc = [finals[(p, k)] for p in PAIRS for k in KINDS]
extra["pooled_54"] = {
    "corr_recall_P_vs_route_gap_mean": st.correlation([c["recall"]["P"]["mean"] for c in allc], [c["prior_effects"]["route_gap_top1_minus_top2"]["mean"] for c in allc]),
    "corr_recall_P_vs_route_gap_median": st.correlation([c["recall"]["P"]["mean"] for c in allc], [c["prior_effects"]["route_gap_top1_minus_top2"]["quantiles"]["0.5"] for c in allc]),
}
# paired: does the learned-minus-fixed recall_P difference track the route-gap difference?
dr = [finals[(p, "learned_tree")]["recall"]["P"]["mean"] - finals[(p, "fixed_tree")]["recall"]["P"]["mean"] for p in PAIRS]
dg = [finals[(p, "learned_tree")]["prior_effects"]["route_gap_top1_minus_top2"]["mean"] - finals[(p, "fixed_tree")]["prior_effects"]["route_gap_top1_minus_top2"]["mean"] for p in PAIRS]
extra["paired_corr_d_recall_P_vs_d_route_gap_mean"] = st.correlation(dr, dg)
extra["pairs_where_learned_route_gap_smaller_but_recall_P_higher"] = sum(1 for a, b in zip(dr, dg) if b < 0 and a > 0)
out["extra_descriptive_NOT_REGISTERED"] = extra

out["discrepancies_with_implementation_analysis"] = disc
out["environment"] = {"python": sys.version, "argv": sys.argv}
with open(OUT, "w") as fh:
    json.dump(out, fh, indent=1, sort_keys=True, default=str)

print("cells", len(cells), "finals missing", missing, "step0 done", len(init_done))
print("internal consistency problems", {k: v for k, v in consistency.items() if v})
for k in KINDS:
    print(k, {n: (f[n]["verdict"], round(f[n]["mean"], 6)) for n, f in [(n, flags[k]) for n in flags[k]]})
print("gates", {k: v for k, v in gates.items() if k != "iv_example_record"})
for lab, r in raw_out.items():
    print(lab, {k: v for k, v in r.items() if isinstance(v, bool) or k in ("sha256_failures", "certificate_raw_float64", "certificate_record", "T2P_order_violations")})
print("discrepancies", len(disc))
for d in disc:
    print("  -", d)
