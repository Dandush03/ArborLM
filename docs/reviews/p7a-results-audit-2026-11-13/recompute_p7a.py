"""Independent recomputation of the P7-A registered criteria and descriptive results.

Auditor role. Standard library only. Does NOT import arborlm and does not reuse p7a_analysis.py.
Reads the 81 per-checkpoint simulation records, the trace records, the P5 result records, the
stage manifests and (optionally) the raw local traces; writes one JSON file.

Usage (from the repository root):
  .venv/bin/python -I docs/reviews/p7a-results-audit-2026-11-13/recompute_p7a.py \
      [--raw-full LABEL ...] [--raw-primary-all] [--out PATH]

Every number is a count under the ADR-0013 page model; none is a device measurement.
Independent engineering/mathematical evidence; not Astra validation; not human approval.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import random
import struct
import sys
import time
from collections import OrderedDict
from fractions import Fraction
from math import comb

ROOT = os.getcwd()
RES = "results/p7a-2026-11-13"
TRACE_RUN = "P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e"
SIM_RUN = "P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b"
ANA_RUN = "P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a"
RAW_ROOT = f"experiments/{TRACE_RUN}/traces"
P5_ROOT = "results/p5-2026-11-13"

KINDS = ("flat", "fixed_tree", "learned_tree")
TREES = ("fixed_tree", "learned_tree")
RS = (1, 2, 8, 32, 128, 512)
CS = (8, 16, 32, 64, 128)
RAND = ("L-RAND-91101", "L-RAND-91102", "L-RAND-91103")
FM = ("freq_matched_1", "freq_matched_2", "freq_matched_3")
Q = 32768
WARM_Q = 16384
CTX = 64
NCTX = 512
TOP = 8
SLOTS = 4096
PER_BRANCH = 256
NBR = 16
PRIMARY = (2, 32)
RATIO = Fraction(4, 5)
FLAT_FLOOR = Fraction(1, 20)
TREE_FLOOR = Fraction(1, 100)


# ------------------------------------------------------------------------------------------------
def load(path):
    with open(path) as f:
        return json.load(f)


def parse(label):
    b, o, *kind, s = label.split("-")
    return (int(b[1:]), int(o[1:]), int(s[1:])), "-".join(kind) if kind else None


def fl(x):
    return None if x is None else float(x)


def fmean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
class Records:
    def __init__(self):
        wdir = f"{RES}/simulate/{SIM_RUN}/workers"
        self.sim = {}
        self.outer = {}
        for p in sorted(glob.glob(f"{wdir}/*.result.json")):
            d = load(p)
            self.outer[d["label"]] = d
            self.sim[d["label"]] = d["record"]
        self.trace = {}
        for p in sorted(glob.glob(f"{RES}/trace/{TRACE_RUN}/checkpoints/*.json")):
            d = load(p)
            self.trace[d["label"]] = d
        self.labels = sorted(self.sim)
        self.kind = {lb: parse(lb)[1] for lb in self.labels}
        self.pair = {lb: parse(lb)[0] for lb in self.labels}
        self.by_kind = {k: sorted([lb for lb in self.labels if self.kind[lb] == k],
                                  key=lambda lb: self.pair[lb]) for k in KINDS}
        self.label_of = {(self.pair[lb], self.kind[lb]): lb for lb in self.labels}
        self.pairs = sorted({self.pair[lb] for lb in self.labels})

    # warm capacity misses per query (exact)
    def cap(self, lb, stream, layout, R, C):
        if stream == "FM":
            return sum(self.cap(lb, s, layout, R, C) for s in FM) / 3
        if layout == "L-RAND":
            return sum(self.cap(lb, stream, x, R, C) for x in RAND) / 3
        e = self.sim[lb]["streams"][stream][f"{layout}|R{R}"]["by_c"][str(C)]
        return Fraction(e["misses_warm"] - e["first_touch_warm"], WARM_Q)

    def entry(self, lb, stream, layout, R, C):
        return self.sim[lb]["streams"][stream][f"{layout}|R{R}"]["by_c"][str(C)]

    def stats(self, lb, stream, layout, R):
        return self.sim[lb]["streams"][stream][f"{layout}|R{R}"]["stats"]

    def pages(self, lb, stream, layout, R):
        if stream == "FM":
            return sum(self.pages(lb, s, layout, R) for s in FM) / 3
        if layout == "L-RAND":
            return sum(self.pages(lb, stream, x, R) for x in RAND) / 3
        return Fraction(self.stats(lb, stream, layout, R)["pages_sum"], Q)

    def has(self, lb, stream, layout):
        lays = RAND if layout == "L-RAND" else (layout,)
        sts = FM if stream == "FM" else (stream,)
        return all(f"{x}|R1" in self.sim[lb]["streams"][s] for s in sts for x in lays)


# ------------------------------------------------------------------------------------------------
def adv(cand, ref, keys, parent):
    """ADR-0013 section 7 ADV clauses. cand/ref: key -> Fraction. Ties count as not lower."""
    cm = sum(cand[k] for k in keys) / len(keys)
    rm = sum(ref[k] for k in keys) / len(keys)
    lower = sum(1 for k in keys if cand[k] < ref[k])
    tied = sum(1 for k in keys if cand[k] == ref[k])
    groups = {}
    for k in keys:
        groups.setdefault(parent(k), []).append(k)
    plower = 0
    for g in groups.values():
        if sum(cand[k] for k in g) / len(g) < sum(ref[k] for k in g) / len(g):
            plower += 1
    c_ratio = cm <= RATIO * rm
    c_cells = lower >= 22
    c_par = plower >= 8
    return {
        "candidate_mean": float(cm), "candidate_mean_exact": str(cm),
        "reference_mean": float(rm), "reference_mean_exact": str(rm),
        "ratio_of_means": float(cm / rm) if rm else None,
        "cells_strictly_lower": lower, "cells_tied": tied, "cells_total": len(keys),
        "parents_strictly_lower": plower, "parents_total": len(groups),
        "clause_mean_ratio": c_ratio, "clause_cells": c_cells, "clause_parents": c_par,
        "holds": c_ratio and c_cells and c_par,
    }


def arch_values(rec, kind, stream, layout, R, C):
    return {rec.pair[lb]: rec.cap(lb, stream, layout, R, C) for lb in rec.by_kind[kind]}


def setting(rec, K, R, C, stream_l="actual", layout="L-FREQ"):
    """Non-degeneracy, LRU and CONC for tree kind K at (R, C)."""
    parent = lambda p: (p[0], p[1])
    flat = arch_values(rec, "flat", stream_l, layout, R, C)
    tree = arch_values(rec, K, stream_l, layout, R, C)
    keys = sorted(flat)
    fm_ = sum(flat.values()) / 27
    tm_ = sum(tree.values()) / 27
    nd = fm_ >= FLAT_FLOOR and tm_ >= TREE_FLOOR
    lru = adv(tree, flat, keys, parent)
    flat_c = arch_values(rec, "flat", "FM", layout, R, C)
    tree_c = arch_values(rec, K, "FM", layout, R, C)
    fcm = sum(flat_c.values()) / 27
    tcm = sum(tree_c.values()) / 27
    conc = adv(tree_c, flat_c, keys, parent)
    # ADR-0013 section 7: in a DEGENERATE setting every criterion is DEGENERATE; item 9 adds the
    # frequency-matched flat floor for CONC. (Attempt 1 omitted the first clause: see attempt log.)
    conc_eval = "HOLDS" if conc["holds"] else "FAILS"
    conc_status = "DEGENERATE" if (not nd or fcm < FLAT_FLOOR) else conc_eval
    return {
        "R": R, "C": C, "cached_rows": R * C,
        "flat_mean": float(fm_), "flat_mean_exact": str(fm_),
        "tree_mean": float(tm_), "tree_mean_exact": str(tm_),
        "flat_floor_met": fm_ >= FLAT_FLOOR, "tree_floor_met": tm_ >= TREE_FLOOR,
        "status": "NON-DEGENERATE" if nd else "DEGENERATE",
        "LRU": ("HOLDS" if lru["holds"] else "FAILS") if nd else "DEGENERATE",
        "LRU_clauses": lru,
        "CONC_flat_mean": float(fcm), "CONC_tree_mean": float(tcm),
        "CONC_flat_floor_met": fcm >= FLAT_FLOOR, "CONC_tree_floor_met": tcm >= TREE_FLOOR,
        "CONC": conc_status, "CONC_clauses": conc, "CONC_if_evaluated_regardless_of_setting": conc_eval,
    }


def outcome(s):
    if s["LRU"] == "DEGENERATE":
        return "UNRESOLVED"
    if s["LRU"] == "FAILS":
        return "NO ADVANTAGE"
    if s["CONC"] == "DEGENERATE":
        return "UNSPECIFIED"
    if s["CONC"] == "HOLDS":
        return "CONCENTRATION-ONLY"
    return "STRUCTURAL ADVANTAGE"


def branch_placement(rec, K, R, C):
    ids = {lb: rec.cap(lb, "actual", "L-ID", R, C) for lb in rec.by_kind[K]}
    rnd = {lb: rec.cap(lb, "actual", "L-RAND", R, C) for lb in rec.by_kind[K]}
    keys = rec.by_kind[K]
    res = adv(ids, rnd, keys, lambda lb: rec.pair[lb][:2])
    rm = sum(rnd.values()) / 27
    flat_rand = sum(rec.cap(lb, "actual", "L-RAND", R, C) for lb in rec.by_kind["flat"]) / 27
    nd_a = rm >= TREE_FLOOR
    nd_b = nd_a and flat_rand >= FLAT_FLOOR
    return {
        "R": R, "C": C, "L_RAND_tree_mean": float(rm), "L_ID_tree_mean": float(res["candidate_mean"]),
        "flat_L_RAND_mean": float(flat_rand),
        "nondegenerate_reading_tree_floor_only": nd_a,
        "nondegenerate_reading_with_flat_floor": nd_b,
        "BR": ("HOLDS" if res["holds"] else "FAILS") if nd_a else "DEGENERATE",
        "clauses": res,
    }


# ------------------------------------------------------------------------------------------------
def summary(xs):
    xs = [float(x) for x in xs]
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return {"mean": m, "min": min(xs), "max": max(xs), "sd": sd, "n": n}


def integrity(rec):
    out = {"problems": [], "counts": {}}
    P = out["problems"]
    out["counts"]["sim_records"] = len(rec.labels)
    out["counts"]["completed"] = sum(1 for lb in rec.labels if rec.outer[lb]["outcome"] == "completed"
                                     and rec.sim[lb].get("complete") is True)
    out["counts"]["trace_records"] = len(rec.trace)
    bit = 0
    for lb, t in rec.trace.items():
        r = t["replay"]
        ok = (r["bitwise_equal"] is True and r["recorded_nll"] == r["replayed_nll"]
              and t["checkpoint"]["files_unchanged"] is True
              and t["checkpoint"]["files_sha256_before"] == t["checkpoint"]["files_sha256_after"]
              and t["checkpoint"]["state_digest_before"] == t["checkpoint"]["state_digest_after"]
              and t["checkpoint"]["files_sha256_before"]["state.pt"] == t["checkpoint"]["recorded_state_sha256"]
              and t["integrity"]["histogram_matches_p5"] is True)
        bit += ok
        if not ok:
            P.append(f"trace record {lb}: replay/hash/histogram flag not clean")
        p5 = load(f"{P5_ROOT}/{lb}/result.json")
        if p5["final"]["nll"] != r["recorded_nll"]:
            P.append(f"{lb}: trace recorded_nll {r['recorded_nll']} != P5 final.nll {p5['final']['nll']}")
        if p5["checkpoint_state_sha256"]["checkpoint-512"] != t["checkpoint"]["recorded_state_sha256"]:
            P.append(f"{lb}: P5 checkpoint_state_sha256 differs from trace record")
        if rec.sim[lb]["evaluation_counts"]["unique_selected_slots"] != t["integrity"]["unique_selected_slots"]:
            P.append(f"{lb}: unique slots differ between trace and sim records")
        if p5["final"]["retrieval"].get("unique_selected_slots", t["integrity"]["unique_selected_slots"]) != t["integrity"]["unique_selected_slots"]:
            P.append(f"{lb}: unique slots differ from P5")
    out["counts"]["trace_replay_bitwise_and_hash_clean"] = bit
    fmok = 0
    for lb in rec.labels:
        f = rec.sim[lb]["frequency_matched"]
        ok = all(f[s]["counts_equal_trace"] is True and f[s]["distinct_slots_per_query"] is True for s in FM)
        idx = rec.sim[lb]["cell_index"]
        ok2 = all(f[s]["generator_seed"] == f[s]["replicate_seed"] * 1000 + idx and f[s]["cell_index"] == idx
                  for s in FM)
        if not (ok and ok2):
            P.append(f"{lb}: frequency-matched flags/seed not clean")
        fmok += ok and ok2
        lays = rec.sim[lb]["layouts"]
        if not all(v["permutation"] is True for v in lays.values()):
            P.append(f"{lb}: a layout is not a permutation")
    out["counts"]["fm_flags_clean"] = fmok
    # registered order / cell index
    order = sorted(rec.labels, key=lambda lb: (rec.pair[lb], KINDS.index(rec.kind[lb])))
    bad_idx = [lb for i, lb in enumerate(order) if rec.sim[lb]["cell_index"] != i]
    if bad_idx:
        P.append(f"cell_index not registered order for {bad_idx[:5]}")
    # invariants
    n_cfg = 0
    for lb in rec.labels:
        for stream, d in rec.sim[lb]["streams"].items():
            for key, e in d.items():
                n_cfg += 1
                st = e["stats"]
                fts = {e["by_c"][str(C)]["first_touch_all"] for C in CS}
                ftw = {e["by_c"][str(C)]["first_touch_warm"] for C in CS}
                if len(fts) != 1 or len(ftw) != 1:
                    P.append(f"{lb} {stream} {key}: first-touch depends on C")
                if fts != {st["distinct_stream"]}:
                    P.append(f"{lb} {stream} {key}: first_touch_all != distinct pages of stream")
                if st["curve"][-1] != st["distinct_stream"] or st["curve"][-2] != st["distinct_first_half"]:
                    P.append(f"{lb} {stream} {key}: curve end != distinct counts")
                if sum(st["hist"]) != Q or sum((i + 1) * h for i, h in enumerate(st["hist"])) != st["pages_sum"]:
                    P.append(f"{lb} {stream} {key}: histogram inconsistent with pages_sum")
                prev_w = prev_a = None
                for C in CS:
                    x = e["by_c"][str(C)]
                    capw = x["misses_warm"] - x["first_touch_warm"]
                    capa = x["misses_all"] - x["first_touch_all"]
                    if x["misses_all"] > st["pages_sum"]:
                        P.append(f"{lb} {stream} {key} C{C}: misses exceed touches")
                    if x["misses_all"] < st["distinct_stream"]:
                        P.append(f"{lb} {stream} {key} C{C}: cold misses below distinct pages")
                    if capw < 0 or capa < 0 or x["misses_warm"] > x["misses_all"]:
                        P.append(f"{lb} {stream} {key} C{C}: negative capacity misses")
                    if x["first_touch_all"] - x["first_touch_warm"] != st["distinct_first_half"]:
                        P.append(f"{lb} {stream} {key} C{C}: first_touch warm split != first-half distinct")
                    if prev_w is not None and (capw > prev_w or capa > prev_a):
                        P.append(f"{lb} {stream} {key} C{C}: capacity misses increase with C")
                    prev_w, prev_a = capw, capa
                if st["reuse_within"][1] != 32256 * 0 + st["reuse_within"][1]:
                    pass
                if st["reuse_within"][0] > st["reuse_within"][1] or st["reuse_cross"][0] > st["reuse_cross"][1]:
                    P.append(f"{lb} {stream} {key}: reuse > touches")
                if st["reuse_within"][1] + st["reuse_cross"][1] + 0 > st["pages_sum"]:
                    P.append(f"{lb} {stream} {key}: reuse denominators exceed touches")
                if key.endswith("|R1") and st["pages_sum"] != Q * TOP:
                    P.append(f"{lb} {stream} {key}: R=1 pages != 8 per query")
    out["counts"]["stream_layout_R_configurations_checked"] = n_cfg
    out["counts"]["cache_configurations_checked"] = n_cfg * len(CS)
    # same stream across layouts: order-shuffled/context-shuffled/actual have the same multiset of
    # per-query slot sets -> at R=1 identical pages_sum; FM streams likewise
    return out


# ------------------------------------------------------------------------------------------------
def decomposition(rec):
    out = {}
    for K in KINDS:
        per = []
        for lb in rec.by_kind[K]:
            u = Fraction(rec.sim[lb]["uniform_reference"]["L-FREQ"][str(PRIMARY[0])])
            pf = rec.pages(lb, "FM", "L-FREQ", 2)
            po = rec.pages(lb, "order_shuffled", "L-FREQ", 2)
            pa = rec.pages(lb, "actual", "L-FREQ", 2)
            pc = rec.pages(lb, "context_shuffled", "L-FREQ", 2)
            mf = rec.cap(lb, "FM", "L-FREQ", 2, 32)
            mo = rec.cap(lb, "order_shuffled", "L-FREQ", 2, 32)
            ma = rec.cap(lb, "actual", "L-FREQ", 2, 32)
            mc = rec.cap(lb, "context_shuffled", "L-FREQ", 2, 32)
            per.append({
                "label": lb, "pages_uniform": float(u), "pages_fm": float(pf), "pages_os": float(po),
                "pages_actual": float(pa), "pages_cs": float(pc),
                "pages_fm_over_uniform": float(pf / u), "pages_os_over_fm": float(po / pf),
                "pages_actual_over_os": float(pa / po), "pages_actual_over_fm": float(pa / pf),
                "m_fm": float(mf), "m_os": float(mo), "m_actual": float(ma), "m_cs": float(mc),
                "m_os_over_fm": float(mo / mf), "m_actual_over_os": float(ma / mo),
                "m_actual_over_fm": float(ma / mf), "m_cs_over_actual": float(mc / ma),
                "m_actual_below_fm": ma < mf, "m_actual_below_os": ma < mo,
                "pages_actual_below_fm": pa < pf,
            })
        agg = {}
        for f in ("pages_uniform", "pages_fm", "pages_os", "pages_actual", "pages_cs", "m_fm", "m_os",
                  "m_actual", "m_cs", "pages_fm_over_uniform", "pages_os_over_fm", "pages_actual_over_os",
                  "pages_actual_over_fm", "m_os_over_fm", "m_actual_over_os", "m_actual_over_fm",
                  "m_cs_over_actual"):
            agg[f] = summary([p[f] for p in per])
        for f in ("m_actual_below_fm", "m_actual_below_os", "pages_actual_below_fm"):
            agg[f + "_cells"] = sum(p[f] for p in per)
        m = lambda f: agg[f]["mean"]
        agg["ratio_of_means"] = {
            "pages_fm/uniform": m("pages_fm") / m("pages_uniform"),
            "pages_os/fm": m("pages_os") / m("pages_fm"),
            "pages_actual/os": m("pages_actual") / m("pages_os"),
            "pages_actual/fm": m("pages_actual") / m("pages_fm"),
            "m_os/fm": m("m_os") / m("m_fm"),
            "m_actual/os": m("m_actual") / m("m_os"),
            "m_actual/fm": m("m_actual") / m("m_fm"),
            "m_cs/actual": m("m_cs") / m("m_actual"),
        }
        out[K] = {"per_checkpoint": per, "summary": agg}
    # trees vs flat: is the beyond-concentration structure larger?
    cmp = {}
    flat_by_pair = {rec.pair[p["label"]]: p for p in out["flat"]["per_checkpoint"]}
    for K in TREES:
        n_lower = 0
        diffs = []
        for p in out[K]["per_checkpoint"]:
            f = flat_by_pair[rec.pair[p["label"]]]
            diffs.append(p["m_actual_over_fm"] - f["m_actual_over_fm"])
            n_lower += p["m_actual_over_fm"] < f["m_actual_over_fm"]
        fa, ff = out["flat"]["summary"]["m_actual"]["mean"], out["flat"]["summary"]["m_fm"]["mean"]
        ta, tf = out[K]["summary"]["m_actual"]["mean"], out[K]["summary"]["m_fm"]["mean"]
        cmp[K] = {
            "pairs_tree_actual_over_fm_lower_than_flat": n_lower,
            "paired_difference_tree_minus_flat_of_actual_over_fm": summary(diffs),
            "gap_actual_flat_minus_tree": fa - ta,
            "gap_fm_flat_minus_tree": ff - tf,
            "share_of_actual_gap_reproduced_by_fm_gap": (ff - tf) / (fa - ta),
            "LRU_ratio_of_means": ta / fa, "CONC_ratio_of_means": tf / ff,
            "tree_vs_flat_ratio_of_structure_terms": (ta / tf) / (fa / ff),
        }
    out["trees_vs_flat"] = cmp
    return out


def pages_vs_uniform(rec):
    out = {}
    for K in KINDS:
        for lay in ("L-ID", "L-RAND", "L-FREQ") + (("L-BFREQ",) if K != "flat" else ()):
            for R in RS:
                pg = [rec.pages(lb, "actual", lay, R) for lb in rec.by_kind[K]]
                if lay == "L-RAND":
                    un = [sum(Fraction(rec.sim[lb]["uniform_reference"][x][str(R)]) for x in RAND) / 3
                          for lb in rec.by_kind[K]]
                else:
                    un = [Fraction(rec.sim[lb]["uniform_reference"][lay][str(R)]) for lb in rec.by_kind[K]]
                mp, mu = sum(pg) / 27, sum(un) / 27
                out[f"{K}|{lay}|R{R}"] = {
                    "mean_pages": float(mp), "mean_uniform": float(mu), "ratio_of_means": float(mp / mu),
                    "uncached_amplification": float(mp * R / TOP),
                    "min_pages": float(min(pg)), "max_pages": float(max(pg)),
                }
    tf = {}
    for K in TREES:
        for lay in ("L-ID", "L-FREQ"):
            for R in RS:
                t = out[f"{K}|{lay}|R{R}"]
                f = out[f"flat|{lay}|R{R}"]
                tf[f"{K}|{lay}|R{R}"] = {
                    "tree_over_flat_actual_pages": t["mean_pages"] / f["mean_pages"],
                    "tree_over_flat_uniform": t["mean_uniform"] / f["mean_uniform"],
                }
    return out, tf


def closed_form_uniform_flat(R):
    n = SLOTS
    return float((SLOTS // R) * (1 - Fraction(comb(n - R, TOP), comb(n, TOP))))


def closed_form_two_branches(R):
    n = 2 * PER_BRANCH
    pages = n // R if R <= PER_BRANCH else None
    if pages is None:
        return None
    return float(pages * (1 - Fraction(comb(n - R, TOP), comb(n, TOP))))


def layouts_table(rec):
    out = {}
    for K in KINDS:
        lays = ("L-ID", "L-RAND", "L-FREQ") + (("L-BFREQ",) if K != "flat" else ())
        for R in RS:
            for C in CS:
                row = {}
                for lay in lays:
                    v = [rec.cap(lb, "actual", lay, R, C) for lb in rec.by_kind[K]]
                    row[lay] = float(sum(v) / 27)
                row["freq_over_id"] = row["L-FREQ"] / row["L-ID"] if row["L-ID"] else None
                row["freq_over_rand"] = row["L-FREQ"] / row["L-RAND"] if row["L-RAND"] else None
                if K != "flat":
                    row["bfreq_over_freq"] = row["L-BFREQ"] / row["L-FREQ"] if row["L-FREQ"] else None
                    row["id_over_rand"] = row["L-ID"] / row["L-RAND"] if row["L-RAND"] else None
                out[f"{K}|R{R}|C{C}"] = row
    return out


def cold_amp(rec):
    out = {}
    for K in KINDS:
        for lay in ("L-FREQ", "L-ID", "L-RAND"):
            for R in RS:
                for C in CS:
                    labs = rec.by_kind[K]
                    lays = RAND if lay == "L-RAND" else (lay,)
                    def avg(f):
                        return fmean([fmean([f(rec.entry(lb, "actual", x, R, C)) for x in lays]) for lb in labs])
                    ft_all = avg(lambda e: e["first_touch_all"] / Q)
                    ft_warm = avg(lambda e: e["first_touch_warm"] / WARM_Q)
                    cold = avg(lambda e: e["misses_all"] / Q)
                    warm_all = avg(lambda e: e["misses_warm"] / WARM_Q)
                    capw = avg(lambda e: (e["misses_warm"] - e["first_touch_warm"]) / WARM_Q)
                    out[f"{K}|{lay}|R{R}|C{C}"] = {
                        "first_touch_misses_per_query_whole_stream": ft_all,
                        "first_touch_misses_per_query_warm_half": ft_warm,
                        "cold_misses_per_query_whole_stream": cold,
                        "warm_misses_per_query_all": warm_all,
                        "warm_capacity_misses_per_query": capw,
                        "cached_amplification_all_warm_misses": warm_all * R / TOP,
                        "cached_amplification_warm_capacity_misses": capw * R / TOP,
                    }
    return out


def reuse(rec):
    out = {}
    for K in KINDS:
        for stream in ("actual", "order_shuffled", "context_shuffled", "FM"):
            for lay in ("L-FREQ", "L-ID"):
                for R in RS:
                    sts = FM if stream == "FM" else (stream,)
                    w = [0, 0]
                    c = [0, 0]
                    per_w, per_c = [], []
                    for lb in rec.by_kind[K]:
                        for s in sts:
                            st = rec.stats(lb, s, lay, R)
                            w[0] += st["reuse_within"][0]; w[1] += st["reuse_within"][1]
                            c[0] += st["reuse_cross"][0]; c[1] += st["reuse_cross"][1]
                            per_w.append(st["reuse_within"][0] / st["reuse_within"][1])
                            per_c.append(st["reuse_cross"][0] / st["reuse_cross"][1])
                    out[f"{K}|{stream}|{lay}|R{R}"] = {
                        "reuse_within_pooled": w[0] / w[1], "reuse_cross_pooled": c[0] / c[1],
                        "reuse_within_mean_of_cells": fmean(per_w), "reuse_cross_mean_of_cells": fmean(per_c),
                    }
    return out


def branch_loc(rec):
    out = {}
    for K in TREES:
        agg = {}
        for f in ("same_top1_within", "same_top1_across", "share_branch_within", "share_branch_across"):
            num = sum(rec.sim[lb]["branch_locality"][f][0] for lb in rec.by_kind[K])
            den = sum(rec.sim[lb]["branch_locality"][f][1] for lb in rec.by_kind[K])
            agg[f + "_pooled"] = num / den
            agg[f + "_mean_of_cells"] = fmean([rec.sim[lb]["branch_locality"][f][0] / rec.sim[lb]["branch_locality"][f][1]
                                               for lb in rec.by_kind[K]])
        agg["distinct_branches_per_context"] = fmean([rec.sim[lb]["branch_locality"]["distinct_branches_per_context_sum"] / NCTX
                                                      for lb in rec.by_kind[K]])
        runs = [rec.sim[lb]["branch_locality"] for lb in rec.by_kind[K]]
        agg["top1_mean_run_length_mean_of_cells"] = fmean([r["top1_mean_run_length"] for r in runs])
        agg["top1_mean_run_length_recomputed_from_hist"] = fmean(
            [sum((i + 1) * h for i, h in enumerate(r["top1_run_length_hist"])) / sum(r["top1_run_length_hist"]) for r in runs])
        agg["top1_runs_hist_consistent"] = all(
            sum(r["top1_run_length_hist"]) == r["top1_runs"] and sum((i + 1) * h for i, h in enumerate(r["top1_run_length_hist"])) == Q
            for r in runs)
        # chance level for same top-1 if consecutive queries were independent draws from the
        # checkpoint's top-1 distribution (sum p^2), from the P5 top1_branch_counts
        chance = []
        for lb in rec.by_kind[K]:
            t1 = load(f"{P5_ROOT}/{lb}/result.json")["final"]["retrieval"]["router"]["top1_branch_counts"]
            s = sum(t1)
            chance.append(sum((x / s) ** 2 for x in t1))
        agg["same_top1_chance_sum_p2_mean"] = fmean(chance)
        out[K] = agg
    return out


def key_reads(rec):
    out = {}
    pb = {1: "4096", 2: "4096", 8: "4096", 32: "4096", 128: "16384", 512: "65536"}
    for K in KINDS:
        for R in RS:
            for C in CS:
                if K == "flat":
                    vals = []
                    for lb in rec.by_kind[K]:
                        e = rec.sim[lb]["key_reads"]["flat"][str(R)]
                        b = e["by_c"][str(C)]
                        vals.append(b["misses_warm"] / WARM_Q)
                        kp = e["key_pages"]
                        analytic = 0 if C >= kp else kp
                        if b["misses_warm"] / WARM_Q != analytic:
                            out.setdefault("problems", []).append(f"{lb} flat key R{R} C{C}")
                    out[f"{K}|R{R}|C{C}"] = {"key_warm_misses_per_query": fmean(vals), "label": "analytical",
                                              "key_pages": rec.sim[rec.by_kind[K][0]]["key_reads"]["flat"][str(R)]["key_pages"]}
                else:
                    per_layout = {}
                    for lay in ("L-ID",) + RAND:
                        vals_all, vals_cap = [], []
                        for lb in rec.by_kind[K]:
                            b = rec.sim[lb]["key_reads"]["tree"][pb[R]]["layouts"][lay]["by_c"][str(C)]
                            vals_all.append(b["misses_warm"] / WARM_Q)
                            vals_cap.append((b["misses_warm"] - b["first_touch_warm"]) / WARM_Q)
                        per_layout[lay] = {"warm_misses": fmean(vals_all), "warm_capacity_misses": fmean(vals_cap)}
                    out[f"{K}|R{R}|C{C}"] = {
                        "L-ID_warm_misses": per_layout["L-ID"]["warm_misses"],
                        "L-RAND_mean_warm_misses": fmean([per_layout[x]["warm_misses"] for x in RAND]),
                        "mean_of_4_layouts_warm_misses": fmean([per_layout[x]["warm_misses"] for x in per_layout]),
                        "mean_of_LID_and_LRANDavg": (per_layout["L-ID"]["warm_misses"] + fmean([per_layout[x]["warm_misses"] for x in RAND])) / 2,
                        "label": "simulated",
                    }
    return out


def key_capacity_bound(rec):
    """A cache of C pages cannot serve a query that touches n > C distinct pages without at least
    n - C misses. Check every recorded cache result (values and tree keys) against
    misses_all >= sum over queries of max(0, n_q - C), from the per-query page histogram."""
    bad = []
    checked = 0
    for lb in rec.labels:
        groups = []
        for stream, d in rec.sim[lb]["streams"].items():
            for key, e in d.items():
                groups.append((f"value {stream} {key}", e))
        for pb, t in rec.sim[lb]["key_reads"].get("tree", {}).items():
            for lay, e in t["layouts"].items():
                groups.append((f"tree-key {pb}B {lay}", e))
        for where, e in groups:
            h = e["stats"]["hist"]
            for C in CS:
                bound = sum(max(0, (i + 1) - C) * n for i, n in enumerate(h))
                checked += 1
                if e["by_c"][str(C)]["misses_all"] < bound:
                    bad.append({"label": lb, "where": where, "C": C,
                                "misses_all": e["by_c"][str(C)]["misses_all"], "lower_bound": bound})
    summ = {}
    for b in bad:
        k = f"{rec.kind[b['label']]}|{b['where'].split(' ', 1)[1]}|C{b['C']}".replace("-91101", "").replace("-91102", "").replace("-91103", "")
        summ[k] = summ.get(k, 0) + 1
    return {"configurations_checked": checked, "violations": len(bad), "by_setting": summ, "examples": bad[:6]}


def eviction(rec):
    out = {"per_arch": {}}
    vals = {}
    for K in KINDS:
        a, d = {}, {}
        for lb in rec.by_kind[K]:
            e = rec.sim[lb]["eviction_order_sensitivity"]
            s = e["setting"]
            assert s == {"C": 32, "R": 2, "index": "RAM-index", "layout": "L-FREQ", "stream": "actual"}, s
            asc = e["ascending"]
            if asc != rec.entry(lb, "actual", "L-FREQ", 2, 32):
                out.setdefault("problems", []).append(f"{lb}: ascending entry differs from the actual stream entry")
            a[rec.pair[lb]] = Fraction(asc["misses_warm"] - asc["first_touch_warm"], WARM_Q)
            ds = e["descending"]
            d[rec.pair[lb]] = Fraction(ds["misses_warm"] - ds["first_touch_warm"], WARM_Q)
        vals[K] = (a, d)
        out["per_arch"][K] = {"mean_ascending": float(sum(a.values()) / 27), "mean_descending": float(sum(d.values()) / 27),
                              "desc_over_asc": float(sum(d.values()) / sum(a.values())),
                              "cells_desc_lower": sum(1 for k in a if d[k] < a[k])}
    par = lambda p: (p[0], p[1])
    for K in TREES:
        keys = sorted(vals["flat"][1])
        r = adv(vals[K][1], vals["flat"][1], keys, par)
        fm_ = sum(vals["flat"][1].values()) / 27
        tm_ = sum(vals[K][1].values()) / 27
        out[f"{K}_LRU_descending"] = {"nondegenerate": fm_ >= FLAT_FLOOR and tm_ >= TREE_FLOOR, **r}
    return out


def bootstrap_tab(rec):
    out = {}
    for K in KINDS:
        for lay in ("L-FREQ", "L-ID") + (("L-BFREQ",) if K != "flat" else ()):
            for R in RS:
                b = [rec.sim[lb]["bootstrap"][f"{lay}|R{R}"] for lb in rec.by_kind[K]]
                widths = [x["boot_upper"] - x["boot_lower"] for x in b]
                means = [x["mean"] for x in b]
                # consistency: bootstrap mean equals the actual stream's pages per query
                cons = all(abs(x["mean"] - float(rec.pages(lb, "actual", lay, R))) < 1e-12
                           for x, lb in zip(b, rec.by_kind[K]))
                out[f"{K}|{lay}|R{R}"] = {
                    "mean_of_means": fmean(means), "mean_lower": fmean([x["boot_lower"] for x in b]),
                    "mean_upper": fmean([x["boot_upper"] for x in b]),
                    "mean_width": fmean(widths), "max_width": max(widths),
                    "between_checkpoint_sd": summary(means)["sd"],
                    "bootstrap_mean_equals_actual_pages": cons,
                }
    return out


def flat_exchange(rec):
    out = {}
    for R in RS:
        for C in CS:
            n = 0
            for lb in rec.by_kind["flat"]:
                i = rec.cap(lb, "actual", "L-ID", R, C)
                rs = [rec.cap(lb, "actual", x, R, C) for x in RAND]
                n += i < min(rs) or i > max(rs)
            out[f"R{R}|C{C}"] = n
    return out


def curves(rec):
    out = {}
    for K in KINDS:
        for lay in ("L-FREQ", "L-ID", "L-RAND"):
            for R in RS:
                lays = RAND if lay == "L-RAND" else (lay,)
                cur = [fmean([rec.stats(lb, "actual", x, R)["curve"][i] for x in lays] ) for lb in rec.by_kind[K] for i in [0]]
                curve = [fmean([fmean([rec.stats(lb, "actual", x, R)["curve"][i] for x in lays]) for lb in rec.by_kind[K]])
                         for i in range(10)]
                dpc = fmean([fmean([rec.stats(lb, "actual", x, R)["distinct_per_context_sum"] / NCTX for x in lays])
                             for lb in rec.by_kind[K]])
                out[f"{K}|{lay}|R{R}"] = {"curve": curve, "distinct_pages_per_context": dpc}
    return out


# ------------------------------------------------------------------------------------------------
# raw traces
def read_i16(path):
    import array
    a = array.array("h")
    with open(path, "rb") as f:
        a.frombytes(f.read())
    if sys.byteorder != "little":
        a.byteswap()
    return a


def read_i8(path):
    import array
    a = array.array("b")
    with open(path, "rb") as f:
        a.frombytes(f.read())
    return a


def counts_of(sel):
    c = [0] * SLOTS
    for s in sel:
        c[s] += 1
    return c


def layout_freq(calc):
    order = sorted(range(SLOTS), key=lambda s: (-calc[s], s))
    pos = [0] * SLOTS
    for p, s in enumerate(order):
        pos[s] = p
    return pos


def layout_bfreq(calc):
    pos = [0] * SLOTS
    for b in range(NBR):
        base = b * PER_BRANCH
        order = sorted(range(base, base + PER_BRANCH), key=lambda s: (-calc[s], s))
        for r, s in enumerate(order):
            pos[s] = base + r
    return pos


def query_pages(sel, pos, R):
    out = []
    for q in range(Q):
        out.append(tuple(sorted({pos[sel[q * TOP + j]] // R for j in range(TOP)})))
    return out


def lru(pq, C, descending=False):
    cache = OrderedDict()
    seen = set()
    ma = fa = mw = fw = 0
    for qi, ps in enumerate(pq):
        warm = qi >= WARM_Q
        for p in (reversed(ps) if descending else ps):
            if p in cache:
                cache.move_to_end(p)
            else:
                ma += 1
                if warm:
                    mw += 1
                if p not in seen:
                    seen.add(p)
                    fa += 1
                    if warm:
                        fw += 1
                cache[p] = None
        while len(cache) > C:
            cache.popitem(last=False)
    return {"first_touch_all": fa, "first_touch_warm": fw, "misses_all": ma, "misses_warm": mw}


def page_stats(pq):
    hist = [0] * TOP
    pages_sum = 0
    rw = [0, 0]
    rc = [0, 0]
    dpc = 0
    seen = set()
    curve = []
    points = [64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
    ctxset = set()
    for q, ps in enumerate(pq):
        hist[len(ps) - 1] += 1
        pages_sum += len(ps)
        if q % CTX == 0:
            dpc += len(ctxset)
            ctxset = set()
        ctxset.update(ps)
        if q > 0:
            prev = set(pq[q - 1])
            inter = sum(1 for p in ps if p in prev)
            if q % CTX == 0:
                rc[0] += inter; rc[1] += len(ps)
            else:
                rw[0] += inter; rw[1] += len(ps)
        seen.update(ps)
        if q + 1 in points:
            curve.append(len(seen))
    dpc += len(ctxset)
    return {"hist": hist, "pages_sum": pages_sum, "reuse_within": rw, "reuse_cross": rc,
            "distinct_per_context_sum": dpc, "curve": curve, "distinct_stream": len(seen),
            "distinct_first_half": curve[-2]}


def fm_stream(counts, rep_seed, idx):
    g = random.Random(rep_seed * 1000 + idx)
    occ = []
    for s, c in enumerate(counts):
        occ.extend([s] * c)
    g.shuffle(occ)
    rows = [occ[i * TOP:(i + 1) * TOP] for i in range(Q)]
    swaps = 0
    for q in range(Q):
        row = rows[q]
        while len(set(row)) < TOP:
            seen = set()
            pos = None
            for j, s in enumerate(row):
                if s in seen:
                    pos = j
                    break
                seen.add(s)
            x = row[pos]
            mine = set(row)
            done = False
            for step in range(1, Q):
                other = rows[(q + step) % Q]
                if x in other:
                    continue
                for k, y in enumerate(other):
                    if y not in mine:
                        row[pos], other[k] = y, x
                        swaps += 1
                        done = True
                        break
                if done:
                    break
            if not done:
                raise RuntimeError("repair dead end")
    order = list(range(Q))
    g.shuffle(order)
    stream = [rows[i] for i in order]
    flatl = [s for r in stream for s in r]
    sha = hashlib.sha256(struct.pack(f"<{len(flatl)}h", *flatl)).hexdigest()
    real = counts_of(flatl)
    return flatl, swaps, sha, real == counts and all(len(set(r)) == TOP for r in stream)


def uniform_tree(pos, R, branches):
    """mean over queries of E[distinct pages] for 8 rows uniformly from the two visited branches."""
    cache = {}
    tot = Fraction(0)
    n = 2 * PER_BRANCH
    den = comb(n, TOP)
    for q in range(Q):
        a, b = branches[2 * q], branches[2 * q + 1]
        key = (min(a, b), max(a, b))
        if key not in cache:
            pc = {}
            for br in key:
                for s in range(br * PER_BRANCH, (br + 1) * PER_BRANCH):
                    p = pos[s] // R
                    pc[p] = pc.get(p, 0) + 1
            cache[key] = sum((1 - Fraction(comb(n - m, TOP), den)) for m in pc.values())
        tot += cache[key]
    return tot / Q


def branch_stats(br):
    sw = [0, 32256]; sa = [0, 511]; shw = [0, 32256]; sha_ = [0, 511]
    dbc = 0
    hist = [0] * 64
    run = 0
    for q in range(Q):
        t = br[2 * q]
        vis = {br[2 * q], br[2 * q + 1]}
        if q % CTX == 0:
            if q:
                hist[run - 1] += 1
            run = 1
        if q > 0:
            pt = br[2 * q - 2]
            pv = {br[2 * q - 2], br[2 * q - 1]}
            same = t == pt
            share = bool(vis & pv)
            if q % CTX == 0:
                sa[0] += same; sha_[0] += share
            else:
                sw[0] += same; shw[0] += share
                if same:
                    run += 1
                else:
                    hist[run - 1] += 1
                    run = 1
    hist[run - 1] += 1
    for c in range(NCTX):
        s = set()
        for q in range(c * CTX, (c + 1) * CTX):
            s.add(br[2 * q]); s.add(br[2 * q + 1])
        dbc += len(s)
    return {"same_top1_within": sw, "same_top1_across": sa, "share_branch_within": shw,
            "share_branch_across": sha_, "distinct_branches_per_context_sum": dbc,
            "top1_run_length_hist": hist, "top1_runs": sum(hist)}


def raw_all(rec, primary_all, full_labels):
    """Raw-trace checks on all 81 (cheap ones), primary-setting re-simulation on all 81 when asked,
    and full re-simulation of the listed checkpoints."""
    out = {"per_checkpoint": {}, "problems": [], "full": {}}
    t0 = time.perf_counter()
    for lb in rec.labels:
        K = rec.kind[lb]
        tr = rec.trace[lb]
        d = f"{RAW_ROOT}/{tr['trace_dir']}"
        files = tr["files"]
        r = {}
        for stream in ("evaluation", "calibration"):
            for part in ("selected", "branches"):
                e = files[stream][part]
                if e is None:
                    continue
                h = sha256_file(f"{d}/{e['file']}")
                if h != e["sha256"] or h != rec.outer[lb]["trace"]["files"][stream][part]["sha256"]:
                    out["problems"].append(f"{lb}: sha256 mismatch {e['file']}")
        ev = read_i16(f"{d}/eval_selected.int16.bin")
        ca = read_i16(f"{d}/calib_selected.int16.bin")
        if len(ev) != Q * TOP or len(ca) != Q * TOP:
            out["problems"].append(f"{lb}: trace length")
        ok_range = all(0 <= s < SLOTS for s in ev) and all(0 <= s < SLOTS for s in ca)
        ok_dist = all(len(set(ev[q * TOP:(q + 1) * TOP])) == TOP for q in range(Q))
        ok_dist_c = all(len(set(ca[q * TOP:(q + 1) * TOP])) == TOP for q in range(Q))
        if not (ok_range and ok_dist and ok_dist_c):
            out["problems"].append(f"{lb}: id range/distinctness")
        evc = counts_of(ev)
        cac = counts_of(ca)
        p5 = load(f"{P5_ROOT}/{lb}/result.json")["final"]
        if evc != p5["retrieval"]["selected_slot_counts"]:
            out["problems"].append(f"{lb}: eval histogram != P5 selected_slot_counts")
        uniq = sum(1 for c in evc if c)
        tot = sum(evc)
        H = -sum((c / tot) * math.log(c / tot) for c in evc if c)
        eff = math.exp(H)
        r["unique_slots"] = uniq
        r["effective_slots"] = eff
        r["p5_effective_slots"] = p5["retrieval"]["effective_selected_slots"]
        r["p5_nll"] = p5["nll"]
        r["calib_unique_slots"] = sum(1 for c in cac if c)
        zero = sum(evc[s] for s in range(SLOTS) if cac[s] == 0)
        r["eval_selections_on_zero_calib_slots_fraction"] = zero / tot
        r["eval_unique_slots_with_zero_calib"] = sum(1 for s in range(SLOTS) if evc[s] and not cac[s])
        pos = layout_freq(cac)
        r["eval_mass_in_first_64_LFREQ_positions"] = sum(evc[s] for s in range(SLOTS) if pos[s] < 64) / tot
        # mass the eval trace itself would put in its own top-64 slots (oracle packing)
        r["eval_mass_in_own_top64"] = sum(sorted(evc, reverse=True)[:64]) / tot
        if K != "flat":
            br = read_i8(f"{d}/eval_branches.int8.bin")
            ok_b = all(ev[q * TOP + j] // PER_BRANCH in (br[2 * q], br[2 * q + 1]) for q in range(Q) for j in range(TOP))
            ok_b2 = all(br[2 * q] != br[2 * q + 1] and 0 <= br[2 * q] < NBR and 0 <= br[2 * q + 1] < NBR for q in range(Q))
            if not (ok_b and ok_b2):
                out["problems"].append(f"{lb}: branch membership")
        if primary_all or lb in full_labels:
            pq = query_pages(ev, pos, 2)
            asc = lru(pq, 32)
            dsc = lru(pq, 32, descending=True)
            r["primary_actual_asc"] = asc
            r["primary_actual_desc"] = dsc
            if asc != rec.entry(lb, "actual", "L-FREQ", 2, 32):
                out["problems"].append(f"{lb}: primary actual ascending differs: {asc}")
            if dsc != rec.sim[lb]["eviction_order_sensitivity"]["descending"]:
                out["problems"].append(f"{lb}: primary actual descending differs: {dsc}")
            idx = rec.sim[lb]["cell_index"]
            fmr = {}
            for i, s in enumerate((91301, 91302, 91303)):
                stream, swaps, sha, ok = fm_stream(evc, s, idx)
                fr = rec.sim[lb]["frequency_matched"][FM[i]]
                pqf = query_pages(stream, pos, 2)
                m = lru(pqf, 32)
                fmr[FM[i]] = {"swaps": swaps, "sha_equal": sha == fr["stream_sha256"],
                              "swaps_equal": swaps == fr["repair_swaps"], "counts_and_distinct_ok": ok,
                              "primary": m, "primary_equal": m == rec.entry(lb, FM[i], "L-FREQ", 2, 32)}
                if not (fmr[FM[i]]["sha_equal"] and fmr[FM[i]]["swaps_equal"] and ok and fmr[FM[i]]["primary_equal"]):
                    out["problems"].append(f"{lb} {FM[i]}: regenerated FM stream differs: {fmr[FM[i]]}")
                if lb in full_labels:
                    fmr[FM[i]]["stream"] = stream
            r["fm"] = fmr
        if lb in full_labels:
            out["full"][lb] = full_check(rec, lb, ev, cac, evc, r["fm"], d, K)
            for i in FM:
                r["fm"][i].pop("stream", None)
        out["per_checkpoint"][lb] = r
    out["seconds"] = time.perf_counter() - t0
    return out


def full_check(rec, lb, ev, cac, evc, fmr, d, K):
    t0 = time.perf_counter()
    res = {"configs_compared": 0, "differences": [], "stats_compared": 0}
    lays = {"L-ID": list(range(SLOTS)), "L-FREQ": layout_freq(cac)}
    if K != "flat":
        lays["L-BFREQ"] = layout_bfreq(cac)
        br = read_i8(f"{d}/eval_branches.int8.bin")
    streams = {"actual": ev}
    for i in FM:
        streams[i] = fmr[i]["stream"]
    for sname, sel in streams.items():
        for lname, pos in lays.items():
            if sname != "actual" and lname == "L-BFREQ":
                continue
            for R in RS:
                pq = query_pages(sel, pos, R)
                st = page_stats(pq)
                rs = rec.stats(lb, sname, lname, R)
                for k, v in st.items():
                    res["stats_compared"] += 1
                    if rs[k] != v:
                        res["differences"].append(f"{sname} {lname} R{R} stats {k}: mine {v} rec {rs[k]}")
                for C in CS:
                    m = lru(pq, C)
                    res["configs_compared"] += 1
                    if m != rec.entry(lb, sname, lname, R, C):
                        res["differences"].append(f"{sname} {lname} R{R} C{C}: mine {m} rec {rec.entry(lb, sname, lname, R, C)}")
                if sname == "actual":
                    # uniform reference
                    if K == "flat":
                        u = closed_form_uniform_flat(R)
                    else:
                        u = float(uniform_tree(pos, R, br))
                    ru = rec.sim[lb]["uniform_reference"][lname][str(R)]
                    res.setdefault("uniform", {})[f"{lname}|R{R}"] = [u, ru]
                    if abs(u - ru) > 1e-12:
                        res["differences"].append(f"uniform {lname} R{R}: mine {u} rec {ru}")
                    # own bootstrap (stdlib generator, not the registered one): widths comparable
                    if (lname, R) in (("L-FREQ", 2), ("L-ID", 32)):
                        per_ctx = [sum(len(pq[q]) for q in range(c * CTX, (c + 1) * CTX)) for c in range(NCTX)]
                        g = random.Random(424242)
                        ms = sorted(sum(per_ctx[g.randrange(NCTX)] for _ in range(NCTX)) / Q for _ in range(1000))
                        b = rec.sim[lb]["bootstrap"][f"{lname}|R{R}"]
                        res.setdefault("bootstrap_own", {})[f"{lname}|R{R}"] = {
                            "mine_2.5_97.5": [ms[24], ms[974]], "mine_width": ms[974] - ms[24],
                            "recorded": [b["boot_lower"], b["boot_upper"]], "recorded_width": b["boot_upper"] - b["boot_lower"]}
    if K != "flat":
        bs = branch_stats(br)
        rb = rec.sim[lb]["branch_locality"]
        for k, v in bs.items():
            res["stats_compared"] += 1
            if k == "top1_run_length_hist":
                if rb[k][:64] != v:
                    res["differences"].append(f"branch {k}: mine {v[:10]} rec {rb[k][:10]}")
            elif rb[k] != v:
                res["differences"].append(f"branch {k}: mine {v} rec {rb[k]}")
    res["seconds"] = time.perf_counter() - t0
    return res


# ------------------------------------------------------------------------------------------------
def utilization(rec, raw, prim):
    out = {}
    pts = []
    for K in KINDS:
        xs, ys, nll, uq = [], [], [], []
        for lb in rec.by_kind[K]:
            r = raw["per_checkpoint"][lb]
            xs.append(r["effective_slots"])
            uq.append(r["unique_slots"])
            ys.append(float(rec.cap(lb, "actual", "L-FREQ", 2, 32)))
            nll.append(r["p5_nll"])
            pts.append((K, r["effective_slots"], ys[-1], r["unique_slots"]))
        out[K] = {
            "unique_slots": summary(uq), "effective_slots": summary(xs), "p5_nll": summary(nll),
            "primary_m": summary(ys),
            "pearson_effective_vs_m": pearson(xs, ys), "spearman_effective_vs_m": spearman(xs, ys),
            "pearson_unique_vs_m": pearson(uq, ys), "spearman_unique_vs_m": spearman(uq, ys),
            "pearson_m_vs_nll": pearson(ys, nll), "spearman_m_vs_nll": spearman(ys, nll),
            "pearson_effective_vs_nll": pearson(xs, nll), "spearman_effective_vs_nll": spearman(xs, nll),
            "max_abs_effective_minus_p5_record": max(abs(raw["per_checkpoint"][lb]["effective_slots"] - raw["per_checkpoint"][lb]["p5_effective_slots"]) for lb in rec.by_kind[K]),
        }
    X = [p[1] for p in pts]
    Y = [p[2] for p in pts]
    out["pooled"] = {"pearson_effective_vs_m": pearson(X, Y), "spearman_effective_vs_m": spearman(X, Y),
                     "pearson_unique_vs_m": pearson([p[3] for p in pts], Y)}
    # pooled least squares m = a + b*eff; mean residual per architecture
    mx, my = sum(X) / len(X), sum(Y) / len(Y)
    b = sum((x - mx) * (y - my) for x, y in zip(X, Y)) / sum((x - mx) ** 2 for x in X)
    a = my - b * mx
    out["pooled"]["ols_m_on_effective"] = {"intercept": a, "slope": b}
    for K in KINDS:
        res = [p[2] - (a + b * p[1]) for p in pts if p[0] == K]
        out["pooled"][f"mean_residual_{K}"] = fmean(res)
        out["pooled"][f"cells_positive_residual_{K}"] = sum(1 for x in res if x > 0)
    resid_all = [p[2] - (a + b * p[1]) for p in pts]
    ss_res = sum(x * x for x in resid_all)
    ss_tot = sum((y - my) ** 2 for y in Y)
    out["pooled"]["r2_effective_only"] = 1 - ss_res / ss_tot
    # with architecture intercepts (ANCOVA-style, common slope)
    groups = {K: [(p[1], p[2]) for p in pts if p[0] == K] for K in KINDS}
    sxx = sum(sum((x - sum(g[0] for g in G) / len(G)) ** 2 for x, _ in G) for G in groups.values())
    sxy = sum(sum((x - sum(g[0] for g in G) / len(G)) * (y - sum(g[1] for g in G) / len(G)) for x, y in G)
              for G in groups.values())
    bw = sxy / sxx
    ss_res2 = sum(sum((y - (sum(g[1] for g in G) / len(G) + bw * (x - sum(g[0] for g in G) / len(G)))) ** 2 for x, y in G)
                  for G in groups.values())
    out["pooled"]["common_slope_with_arch_intercepts"] = {
        "slope": bw, "r2": 1 - ss_res2 / ss_tot,
        "intercept_shift_at_pooled_mean_eff": {K: (sum(g[1] for g in G) / len(G) + bw * (mx - sum(g[0] for g in G) / len(G)))
                                               for K, G in groups.items()}}
    # pairwise checkpoint ordering: fraction of cross-architecture pairs ordered by effective slots
    agree = tot = 0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if pts[i][0] == pts[j][0]:
                continue
            tot += 1
            agree += (pts[i][1] - pts[j][1]) * (pts[i][2] - pts[j][2]) > 0
    out["pooled"]["cross_arch_pairs_concordant_fraction"] = agree / tot
    return out


def calib_transfer(rec, raw):
    out = {}
    for K in KINDS:
        f = [raw["per_checkpoint"][lb]["eval_selections_on_zero_calib_slots_fraction"] for lb in rec.by_kind[K]]
        u = [raw["per_checkpoint"][lb]["eval_unique_slots_with_zero_calib"] for lb in rec.by_kind[K]]
        h = [raw["per_checkpoint"][lb]["eval_mass_in_first_64_LFREQ_positions"] for lb in rec.by_kind[K]]
        o = [raw["per_checkpoint"][lb]["eval_mass_in_own_top64"] for lb in rec.by_kind[K]]
        out[K] = {"zero_calib_selection_fraction": summary(f), "eval_unique_slots_with_zero_calib": summary(u),
                  "eval_mass_in_LFREQ_first64": summary(h), "eval_mass_in_own_top64": summary(o),
                  "packing_shortfall_own_minus_LFREQ_first64": summary([a - b for a, b in zip(o, h)])}
    return out


def resources():
    out = {}
    for s in ("trace", "simulate", "analyze"):
        m = load(glob.glob(f"{RES}/{s}/*/manifest.json")[0])
        r = load(glob.glob(f"{RES}/{s}/*/result.json")[0])
        out[s] = {"caps": m["caps"], "wall_seconds": m["wall_seconds"], "git_head": m["git_head"],
                  "git_dirty": m["git_dirty"], "status": m["status"],
                  "active_seconds": r.get("active_seconds", r.get("analysis_seconds")),
                  "peak_rss_bytes": r.get("peak_rss_bytes"),
                  "deterministic_algorithms_env": m["environment"].get("deterministic_algorithms"),
                  "threads_env": m["environment"].get("threads")}
    wk = [load(p) for p in glob.glob(f"{RES}/simulate/{SIM_RUN}/workers/*.manifest.json")]
    out["simulate"]["max_worker_process_tree_rss"] = max(w["peak_process_tree_rss_bytes"] for w in wk)
    out["simulate"]["sum_worker_wall_seconds"] = sum(w["process_wall_seconds"] for w in wk)
    tw = [load(p) for p in glob.glob(f"{RES}/trace/{TRACE_RUN}/workers/*.manifest.json")]
    out["trace"]["max_worker_process_tree_rss"] = max(w.get("peak_process_tree_rss_bytes", 0) for w in tw)
    out["trace"]["sum_worker_wall_seconds"] = sum(w.get("process_wall_seconds", 0) for w in tw)
    ind = load("docs/reviews/p7a-results-audit-2026-11-13/independent_sim_registered.json")
    out["independent_sim_seconds"] = ind["total_seconds"]
    tr, sm, an = out["trace"]["active_seconds"], out["simulate"]["active_seconds"], out["analyze"]["active_seconds"]
    out["checks"] = {
        "trace<=900": tr <= 900, "sim+analysis<=3600": sm + an <= 3600, "combined<=4500": tr + sm + an <= 4500,
        "rss<=2GiB": all(out[s]["peak_rss_bytes"] is None or out[s]["peak_rss_bytes"] <= 2 ** 31 for s in ("trace", "simulate"))
        and out["simulate"]["max_worker_process_tree_rss"] <= 2 ** 31,
        "independent<=1800": ind["total_seconds"] <= 1800,
        "trace_margin": 900 / tr, "sim_analysis_margin": 3600 / (sm + an), "combined": tr + sm + an,
    }
    return out


# ------------------------------------------------------------------------------------------------
class Cmp:
    def __init__(self):
        self.n = 0
        self.diffs = []

    def eq(self, path, mine, theirs, tol=1e-9):
        self.n += 1
        if isinstance(mine, float) or isinstance(theirs, float):
            if mine is None or theirs is None:
                ok = mine is theirs
            else:
                ok = abs(mine - theirs) <= tol * max(1.0, abs(theirs))
        elif isinstance(mine, str) and isinstance(theirs, str) and "exact" in path:
            ok = Fraction(mine) == Fraction(theirs)
        else:
            ok = mine == theirs
        if not ok:
            self.diffs.append({"path": path, "mine": mine, "analysis": theirs})


def compare(res, rec, A):
    c = Cmp()
    cr = A["criteria"]
    prim = cr["primary_setting"]
    c.eq("criteria.primary_setting", [prim["R"], prim["C"], prim["layout"], prim["stream"], prim["index"]],
         [2, 32, "L-FREQ", "actual", "RAM-index"])
    for K in TREES:
        t = cr["tree_kinds"][K]
        mine = res["criteria"][K]
        p = mine["primary"]
        c.eq(f"{K}.LRU", p["LRU"], t["LRU"])
        c.eq(f"{K}.CONC", p["CONC"], t["CONC"])
        c.eq(f"{K}.outcome", mine["outcome"], t["outcome"])
        c.eq(f"{K}.BR", mine["BR_primary"]["BR"], t["BR"])
        c.eq(f"{K}.status", p["status"], t["primary"]["status"])
        c.eq(f"{K}.robust_other_settings_count", len(mine["robust_other_settings"]), len(t["robust_other_settings"]))
        for part, mpart in (("LRU_clauses", "LRU_clauses"), ("CONC_clauses", "CONC_clauses")):
            for f in ("candidate_mean_exact", "reference_mean_exact", "cells_strictly_lower", "cells_tied",
                      "parents_strictly_lower", "ratio_of_means", "clause_mean_ratio", "clause_cells",
                      "clause_parents", "holds"):
                c.eq(f"{K}.primary.{part}.{f}", p[mpart][f], t["primary"][part][f])
        c.eq(f"{K}.CONC_nd.flat_mean_exact", str(Fraction(p["CONC_flat_mean"]).limit_denominator(10 ** 7)) if False else p["CONC_flat_mean"], t["primary"]["CONC_non_degeneracy"]["flat_mean"])
        c.eq(f"{K}.CONC_nd.tree_mean", p["CONC_tree_mean"], t["primary"]["CONC_non_degeneracy"]["tree_mean"])
        c.eq(f"{K}.nd.flat_mean_exact", p["flat_mean_exact"], t["primary"]["non_degeneracy"]["flat_mean_exact"])
        c.eq(f"{K}.nd.tree_mean_exact", p["tree_mean_exact"], t["primary"]["non_degeneracy"]["tree_mean_exact"])
        grid = {(g["R"], g["C"]): g for g in t["robustness_grid"]}
        for g in mine["grid"]:
            a = grid[(g["R"], g["C"])]
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.status", g["status"], a["status"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.LRU", g["LRU"], a["LRU"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC", g["CONC"], a["CONC"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.flat_mean", g["flat_mean"], a["flat_mean"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.tree_mean", g["tree_mean"], a["tree_mean"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.ratio", g["LRU_clauses"]["ratio_of_means"], a["ratio_of_means"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.cells_lower", g["LRU_clauses"]["cells_strictly_lower"], a["cells_lower"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.parents_lower", g["LRU_clauses"]["parents_strictly_lower"], a["parents_lower"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC_flat_mean", g["CONC_flat_mean"], a["CONC_flat_mean"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC_tree_mean", g["CONC_tree_mean"], a["CONC_tree_mean"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC_ratio", g["CONC_clauses"]["ratio_of_means"], a["CONC_ratio_of_means"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC_cells_lower", g["CONC_clauses"]["cells_strictly_lower"], a["CONC_cells_lower"])
            c.eq(f"{K}.grid.R{g['R']}C{g['C']}.CONC_parents_lower", g["CONC_clauses"]["parents_strictly_lower"], a["CONC_parents_lower"])
        bgrid = {(g["R"], g["C"]): g for g in t["branch_placement_grid"]}
        for g in mine["BR_grid"]:
            a = bgrid[(g["R"], g["C"])]
            c.eq(f"{K}.BRgrid.R{g['R']}C{g['C']}.BR", g["BR"], a["BR"])
            c.eq(f"{K}.BRgrid.R{g['R']}C{g['C']}.L_RAND_mean", g["L_RAND_tree_mean"], a["L_RAND_tree_mean"])
            for f in ("candidate_mean_exact", "reference_mean_exact", "cells_strictly_lower", "cells_tied",
                      "parents_strictly_lower", "holds"):
                c.eq(f"{K}.BRgrid.R{g['R']}C{g['C']}.{f}", g["clauses"][f], a["clauses"][f])
    D = A["descriptive"]
    # decomposition (by kind/layout/R)
    for key, a in D["decomposition"]["by_kind_layout_R"].items():
        K, lay, Rs = key.split("|")
        R = int(Rs[1:])
        labs = rec.by_kind[K]
        for st, mst in (("actual", "actual"), ("order_shuffled", "order_shuffled"),
                        ("context_shuffled", "context_shuffled"), ("frequency_matched", "FM")):
            c.eq(f"decomp.{key}.pages.{st}", float(sum(rec.pages(lb, mst, lay, R) for lb in labs) / 27),
                 a["pages_per_query"][st])
            for C in CS:
                c.eq(f"decomp.{key}.m.C{C}.{st}", float(sum(rec.cap(lb, mst, lay, R, C) for lb in labs) / 27),
                     a["warm_capacity_misses_per_query"][str(C)][st])
        c.eq(f"decomp.{key}.pages.uniform",
             float(sum(Fraction(rec.sim[lb]["uniform_reference"][lay][str(R)]) for lb in labs) / 27),
             a["pages_per_query"]["uniform"])
    for lb, d in D["decomposition"]["per_checkpoint"].items():
        for key, a in d.items():
            lay, Rs = key.split("|")
            R = int(Rs[1:])
            for st, mst in (("actual", "actual"), ("order_shuffled", "order_shuffled"),
                            ("context_shuffled", "context_shuffled"), ("frequency_matched", "FM")):
                c.eq(f"decomp_pc.{lb}.{key}.pages.{st}", float(rec.pages(lb, mst, lay, R)), a["pages_per_query"][st])
                for C in CS:
                    c.eq(f"decomp_pc.{lb}.{key}.m.C{C}.{st}", float(rec.cap(lb, mst, lay, R, C)),
                         a["warm_capacity_misses_per_query"][str(C)][st])
    for key, a in D["pages_per_query_vs_uniform"].items():
        m = res["item4_pages_vs_uniform"][key]
        c.eq(f"pvu.{key}.pages", m["mean_pages"], a["mean_distinct_pages_per_query"])
        c.eq(f"pvu.{key}.uniform", m["mean_uniform"], a["mean_uniform_reference"])
        c.eq(f"pvu.{key}.ratio", m["ratio_of_means"], a["ratio_of_means"])
        c.eq(f"pvu.{key}.uamp", m["uncached_amplification"], a["uncached_amplification"])
    for key, a in D["warm_capacity_misses_by_layout"].items():
        K, lay, Rs, Cs_ = key.split("|")
        c.eq(f"wcm.{key}", res["item6_layouts"][f"{K}|{Rs}|{Cs_}"][lay], a)
    for key, a in D["cold_misses_and_amplification"].items():
        m = res["item10_cold_amp"][key]
        for f in a:
            if f == "cells":
                continue
            c.eq(f"cold.{key}.{f}", m[f], a[f])
    for key, a in D["context_shuffled_vs_actual"].items():
        K, lay, Rs, Cs_ = key.split("|")
        R, C = int(Rs[1:]), int(Cs_[1:])
        labs = rec.by_kind[K]
        c.eq(f"csa.{key}.actual", float(sum(rec.cap(lb, "actual", lay, R, C) for lb in labs) / 27), a["actual"])
        c.eq(f"csa.{key}.cs", float(sum(rec.cap(lb, "context_shuffled", lay, R, C) for lb in labs) / 27), a["context_shuffled"])
    for key, a in D["page_reuse"].items():
        K, lay, Rs = key.split("|")
        m = res["item8_reuse"][f"{K}|actual|{lay}|{Rs}"]
        c.eq(f"reuse.{key}.within", m["reuse_within_pooled"], a["reuse_within"])
        c.eq(f"reuse.{key}.cross", m["reuse_cross_pooled"], a["reuse_cross"])
    for K, a in D["branch_locality"].items():
        m = res["item9_branch_locality"][K]
        for f in ("same_top1_within", "same_top1_across", "share_branch_within", "share_branch_across"):
            pooled_ok = abs(m[f + "_pooled"] - a[f]) <= 1e-9
            mean_ok = abs(m[f + "_mean_of_cells"] - a[f]) <= 1e-9
            c.eq(f"branch.{K}.{f}.(pooled or mean-of-cells)", True, pooled_ok or mean_ok)
            res.setdefault("branch_locality_definition_matched", {})[f"{K}.{f}"] = "pooled" if pooled_ok else ("mean_of_cells" if mean_ok else "neither")
        c.eq(f"branch.{K}.distinct_branches_per_context", m["distinct_branches_per_context"], a["distinct_branches_per_context"])
        c.eq(f"branch.{K}.run_length", m["top1_mean_run_length_mean_of_cells"], a["top1_mean_run_length"])
    for K, a in D["utilization"].items():
        c.eq(f"util.{K}.unique", fmean([rec.sim[lb]["evaluation_counts"]["unique_selected_slots"] for lb in rec.by_kind[K]]), a["mean_unique_selected_slots"])
    ev = D["eviction_order_sensitivity"]
    for K in KINDS:
        c.eq(f"evict.{K}.asc", res["item11_eviction"]["per_arch"][K]["mean_ascending"], ev["by_architecture"][K]["mean_ascending"])
        c.eq(f"evict.{K}.desc", res["item11_eviction"]["per_arch"][K]["mean_descending"], ev["by_architecture"][K]["mean_descending"])
    for K in TREES:
        c.eq(f"evict.{K}.desc_pairs_lower", res["item11_eviction"][f"{K}_LRU_descending"]["cells_strictly_lower"],
             ev["by_architecture"][K]["descending_pairs_strictly_lower_than_flat"])
        c.eq(f"evict.{K}.desc_ratio", res["item11_eviction"][f"{K}_LRU_descending"]["ratio_of_means"],
             ev["by_architecture"][K]["descending_ratio_of_means_vs_flat"])
    for key, a in D["ssd_index_key_reads"].items():
        K, Rs, Cs_ = key.split("|")
        m = res["item9_key_reads"][key]
        if K == "flat":
            c.eq(f"keys.{key}", m["key_warm_misses_per_query"], a["key_warm_misses_per_query_mean"])
        else:
            cand = {k: m[k] for k in ("L-ID_warm_misses", "L-RAND_mean_warm_misses", "mean_of_4_layouts_warm_misses", "mean_of_LID_and_LRANDavg")}
            hit = [k for k, v in cand.items() if abs(v - a["key_warm_misses_per_query_mean"]) <= 1e-9]
            res.setdefault("key_reads_definition_matched", {})[key] = hit
            c.eq(f"keys.{key}.matches_some_definition", True, bool(hit))
        R, C = int(Rs[1:]), int(Cs_[1:])
        c.eq(f"keys.{key}.value", float(sum(rec.cap(lb, "actual", "L-FREQ", R, C) for lb in rec.by_kind[K]) / 27),
             a["value_warm_capacity_misses_L_FREQ_mean"])
    for key, a in D["flat_layout_report_only"].items():
        if key == "note":
            continue
        c.eq(f"flatexch.{key}", res["flat_layout_exchangeability"][key], a["L_ID_outside_L_RAND_range"])
    for key, a in D["bootstrap_distinct_pages"].items():
        m = res["item12_bootstrap"][key]
        c.eq(f"boot.{key}.mean", m["mean_of_means"], a["mean_of_means"])
        c.eq(f"boot.{key}.lower", m["mean_lower"], a["mean_lower"])
        c.eq(f"boot.{key}.upper", m["mean_upper"], a["mean_upper"])
    for key, a in D["cumulative_distinct_pages"].items():
        m = res["cumulative"][key]
        for i, v in enumerate(a["mean_distinct_pages_over_first_n_queries"]):
            c.eq(f"curve.{key}.{i}", m["curve"][i], v)
        c.eq(f"curve.{key}.dpc", m["distinct_pages_per_context"], a["mean_distinct_pages_per_context"])
    c.eq("checkpoints_complete", res["item2_integrity"]["counts"]["completed"], A["checkpoints_complete"])
    return {"values_compared": c.n, "differences": c.diffs}


# ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-full", nargs="*", default=[])
    ap.add_argument("--raw-primary-all", action="store_true")
    ap.add_argument("--no-raw", action="store_true")
    ap.add_argument("--out", default="docs/reviews/p7a-results-audit-2026-11-13/recompute_p7a.json")
    args = ap.parse_args()
    t0 = time.perf_counter()
    rec = Records()
    assert len(rec.labels) == 81 and all(len(rec.by_kind[k]) == 27 for k in KINDS)
    res = {"tool": "recompute_p7a.py (auditor, stdlib only; no arborlm import)",
           "python": sys.version, "argv": sys.argv, "cwd": ROOT,
           "label": "independent engineering/mathematical evidence; not Astra validation; not human approval",
           "inputs": {"sim_run": SIM_RUN, "trace_run": TRACE_RUN, "analysis_run": ANA_RUN,
                      "analysis_sha256": sha256_file(f"{RES}/analyze/{ANA_RUN}/analysis.json"),
                      "script_sha256": sha256_file(__file__)}}
    res["item2_integrity"] = integrity(rec)
    # item 1: per-checkpoint m for every stream/layout/R/C
    per = {}
    for lb in rec.labels:
        d = {}
        for stream, sd in rec.sim[lb]["streams"].items():
            for key in sd:
                for C in CS:
                    e = sd[key]["by_c"][str(C)]
                    d[f"{stream}|{key}|C{C}"] = (e["misses_warm"] - e["first_touch_warm"]) / WARM_Q
        per[lb] = d
    res["item1_per_checkpoint_m"] = per
    crit = {}
    for K in TREES:
        grid = [setting(rec, K, R, C) for R in RS for C in CS]
        prim = next(g for g in grid if (g["R"], g["C"]) == PRIMARY)
        out = outcome(prim)
        robust = [{"R": g["R"], "C": g["C"]} for g in grid
                  if (g["R"], g["C"]) != PRIMARY and g["R"] <= 8 and g["status"] == "NON-DEGENERATE"
                  and g["LRU"] == "HOLDS" and g["CONC"] == "FAILS"]
        brg = [branch_placement(rec, K, R, C) for R in RS for C in CS]
        crit[K] = {"primary": prim, "outcome": out,
                   "robust_other_settings": robust,
                   "robust": (out == "STRUCTURAL ADVANTAGE" and bool(robust)) if out == "STRUCTURAL ADVANTAGE" else None,
                   "BR_primary": next(b for b in brg if (b["R"], b["C"]) == PRIMARY),
                   "grid": grid, "BR_grid": brg,
                   "grid_cell_outcomes": {f"R{g['R']}C{g['C']}": outcome(g) for g in grid}}
    res["criteria"] = crit
    res["item3_decomposition"] = decomposition(rec)
    res["item4_pages_vs_uniform"], res["item4_tree_over_flat"] = pages_vs_uniform(rec)
    res["item4_closed_form"] = {f"R{R}": {"flat_whole_store": closed_form_uniform_flat(R),
                                          "two_contiguous_branches": closed_form_two_branches(R)} for R in RS}
    res["item6_layouts"] = layouts_table(rec)
    res["item8_reuse"] = reuse(rec)
    res["item9_branch_locality"] = branch_loc(rec)
    res["item9_key_reads"] = key_reads(rec)
    res["item10_cold_amp"] = cold_amp(rec)
    res["item11_eviction"] = eviction(rec)
    res["item9_capacity_lower_bound_check"] = key_capacity_bound(rec)
    res["lru_vs_conc_grid"] = {K: {"nondegenerate_cells": sum(1 for g in crit[K]["grid"] if g["status"] == "NON-DEGENERATE"),
                                   "max_abs_ratio_gap": max(abs(g["LRU_clauses"]["ratio_of_means"] - g["CONC_clauses"]["ratio_of_means"])
                                                            for g in crit[K]["grid"] if g["status"] == "NON-DEGENERATE"),
                                   "verdict_mismatch_cells": [f"R{g['R']}C{g['C']}" for g in crit[K]["grid"]
                                                              if g["status"] == "NON-DEGENERATE" and g["LRU"] != g["CONC"]]}
                               for K in TREES}
    res["item12_bootstrap"] = bootstrap_tab(rec)
    res["flat_layout_exchangeability"] = flat_exchange(rec)
    res["cumulative"] = curves(rec)
    res["item14_resources"] = resources()
    if not args.no_raw:
        raw = raw_all(rec, args.raw_primary_all, set(args.raw_full))
        res["raw"] = raw
        res["item7_utilization"] = utilization(rec, raw, None)
        res["item13_calibration_transfer"] = calib_transfer(rec, raw)
    A = load(f"{RES}/analyze/{ANA_RUN}/analysis.json")
    res["comparison_with_analysis_json"] = compare(res, rec, A)
    res["seconds"] = time.perf_counter() - t0
    with open(args.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    # console summary
    print("compared", res["comparison_with_analysis_json"]["values_compared"],
          "differences", len(res["comparison_with_analysis_json"]["differences"]))
    for d in res["comparison_with_analysis_json"]["differences"][:40]:
        print("DIFF", d)
    print("integrity problems", len(res["item2_integrity"]["problems"]), res["item2_integrity"]["problems"][:10])
    if "raw" in res:
        print("raw problems", len(res["raw"]["problems"]), res["raw"]["problems"][:10])
        for lb, f in res["raw"]["full"].items():
            print("full", lb, f["configs_compared"], f["stats_compared"], len(f["differences"]), f["differences"][:5], round(f["seconds"], 1))
    for K in TREES:
        p = crit[K]["primary"]
        print(K, p["status"], "LRU", p["LRU"], p["LRU_clauses"]["ratio_of_means"], p["LRU_clauses"]["cells_strictly_lower"],
              p["LRU_clauses"]["parents_strictly_lower"], "CONC", p["CONC"], p["CONC_clauses"]["ratio_of_means"],
              p["CONC_clauses"]["cells_strictly_lower"], p["CONC_clauses"]["parents_strictly_lower"],
              "BR", crit[K]["BR_primary"]["BR"], "->", crit[K]["outcome"], "robust_other", crit[K]["robust_other_settings"])
    kb = res["item9_capacity_lower_bound_check"]
    print("capacity lower-bound check", kb["configurations_checked"], "violations", kb["violations"], kb["by_setting"])
    print("seconds", round(res["seconds"], 1))


if __name__ == "__main__":
    main()
