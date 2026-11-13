#!/usr/bin/env python3
"""Visual-analysis package for the completed (immutable) P5 study.

Reads ONLY the committed compact records
  results/p5-2026-11-13/<cell>/result.json            (117 quality cells)
  results/p5-2026-11-13/timing/<worker>/result.json   (36 timing workers)
and derives every plotted number independently (no arborlm import, no audit code).
Writes figure_data.json, inputs.sha256, fig*.png and README.md next to this script.

Implementer self-check output; NOT Astra validation and NOT human approval.

Reproduce (from repository root):
  uv run --locked --extra pilot --with matplotlib==3.10.8 \
      python docs/reviews/p5-claude-review-2026-11-13/figures/make_figures.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.transforms  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RES = ROOT / "results" / "p5-2026-11-13"
TIM = RES / "timing"

BACKBONES = (101, 102, 103)
ORDERS = (301, 302, 303)
SEEDS = (501, 502, 503)
PARENTS = [(b, o) for b in BACKBONES for o in ORDERS]
MEM = ("flat", "fixed_tree", "learned_tree")
ALLV = ("flat", "fixed_tree", "learned_tree", "dense")
SCOPES = ("lookup_score_select", "addition_forward", "model_forward")
WORKLOADS = (8, 1)  # primary, secondary
ANALYTICAL_WORK = 528 / 4096

LABEL = {"baseline": "Frozen baseline", "flat": "Flat", "fixed_tree": "Fixed tree",
         "learned_tree": "Learned tree", "dense": "Dense adapter"}
# Okabe-Ito colour-blind-safe palette, one colour per architecture, used in every figure
COL = {"baseline": "#6E6E6E", "flat": "#0072B2", "fixed_tree": "#E69F00",
       "learned_tree": "#009E73", "dense": "#CC79A7"}
MARK = {101: "o", 102: "s", 103: "^"}  # one marker per parent backbone B
NOTE = ("Note: the 27 cells share 9 parents (3 backbones x 3 orders), 3 seeds and one validation panel; "
        "they are correlated paired observations,\nnot independent replicates. No inference is implied.")

PUBLISHED = {
    "mean_final_nll.baseline": 2.356630572,
    "mean_final_nll.flat": 2.333691890,
    "mean_final_nll.fixed_tree": 2.334497243,
    "mean_final_nll.learned_tree": 2.335080704,
    "mean_final_nll.dense": 2.329312946,
    "mean_R_fixed_minus_learned": -0.000583461,
    "R_positive_cells": 10,
    "R_positive_parent_means": 3,
    "primary_geomean_ratio.addition_forward.fixed_tree": 2.603052,
    "primary_geomean_ratio.addition_forward.learned_tree": 2.598485,
    "primary_geomean_ratio.model_forward.fixed_tree": 2.190282,
    "primary_geomean_ratio.model_forward.learned_tree": 2.184086,
    "mean_final_unique_selected_slots.flat": 428.59,
    "mean_final_unique_selected_slots.fixed_tree": 383.41,
    "mean_final_unique_selected_slots.learned_tree": 313.11,
    "mean_final_effective_selected_slots.flat": 132.34,
    "mean_final_effective_selected_slots.fixed_tree": 96.25,
    "mean_final_effective_selected_slots.learned_tree": 83.02,
    # secondary published values (README table) for extra cross-checking
    "mean_gain_G.flat": 0.022938682,
    "mean_gain_G.fixed_tree": 0.022133329,
    "mean_gain_G.learned_tree": 0.021549867,
    "mean_gain_G.dense": 0.027317625,
    "mean_shuffle_penalty_P.flat": 0.022679532,
    "mean_shuffle_penalty_P.fixed_tree": 0.021944248,
    "mean_shuffle_penalty_P.learned_tree": 0.021603653,
    "mean_T_minus_flat.fixed_tree": 0.000805353,
    "mean_T_minus_flat.learned_tree": 0.001388814,
}
# precision used by the published numbers (decimal places) -> rounding tolerance for the match flag
PUB_DP = {k: (9 if "nll" in k or "gain" in k or "penalty" in k or "T_minus" in k or k.startswith("mean_R") else
              6 if "ratio" in k else 2) for k in PUBLISHED}

inputs_sha: dict[str, str] = {}


def load(path: Path) -> dict:
    data = path.read_bytes()
    inputs_sha[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def mean(x):
    return float(sum(x) / len(x))


def geomean(x):
    return float(math.exp(sum(math.log(v) for v in x) / len(x)))


# ----------------------------------------------------------------------------- load quality
base, cellrec = {}, {}
for b, o in PARENTS:
    base[(b, o)] = load(RES / f"b{b}-o{o}-baseline" / "result.json")
    for v in ALLV:
        for s in SEEDS:
            r = load(RES / f"b{b}-o{o}-{v}-s{s}" / "result.json")
            assert r["cell"] == {"backbone": b, "order": o, "seed": s, "variant": v}, (b, o, v, s)
            assert r["outcome"] == "completed"
            cellrec[(b, o, v, s)] = r
assert len(base) == 9 and len(cellrec) == 108

Z = {p: base[p]["final"]["nll"] for p in PARENTS}
cells = []  # one row per (parent, seed): all variants
for b, o in PARENTS:
    for s in SEEDS:
        row = {"backbone": b, "order": o, "seed": s, "Z_baseline_nll": Z[(b, o)]}
        for v in ALLV:
            r = cellrec[(b, o, v, s)]
            x = r["final"]["nll"]
            # disabled intervention must equal the frozen baseline (ADR-0010 section 8)
            assert r["interventions"]["disabled"]["nll"] == Z[(b, o)] or \
                abs(r["interventions"]["disabled"]["nll"] - Z[(b, o)]) < 1e-12
            d = {"final_nll": x, "initial_nll": r["initial"]["nll"], "G": Z[(b, o)] - x}
            if v != "dense":
                d["shuffled_nll"] = r["interventions"]["values_permuted"]["nll"]
                d["P"] = d["shuffled_nll"] - x
                for ph in ("initial", "final"):
                    rt = r[ph]["retrieval"]
                    d[f"{ph}_unique_selected_slots"] = rt["unique_selected_slots"]
                    d[f"{ph}_effective_selected_slots"] = rt["effective_selected_slots"]
                    if v != "flat":
                        d[f"{ph}_nonzero_top1_branches"] = rt["router"]["nonzero_top1_branches"]
            row[v] = d
        row["R_fixed_minus_learned"] = row["fixed_tree"]["final_nll"] - row["learned_tree"]["final_nll"]
        row["T_fixed_minus_flat"] = row["fixed_tree"]["final_nll"] - row["flat"]["final_nll"]
        row["T_learned_minus_flat"] = row["learned_tree"]["final_nll"] - row["flat"]["final_nll"]
        cells.append(row)
assert len(cells) == 27


def sel(v, key):
    return [c[v][key] for c in cells]


agg: dict = {}
agg["mean_final_nll.baseline"] = mean([Z[p] for p in PARENTS])
for v in ALLV:
    agg[f"mean_final_nll.{v}"] = mean(sel(v, "final_nll"))
    agg[f"mean_gain_G.{v}"] = mean(sel(v, "G"))
for v in MEM:
    agg[f"mean_shuffle_penalty_P.{v}"] = mean(sel(v, "P"))
    agg[f"mean_final_unique_selected_slots.{v}"] = mean(sel(v, "final_unique_selected_slots"))
    agg[f"mean_final_effective_selected_slots.{v}"] = mean(sel(v, "final_effective_selected_slots"))
    agg[f"mean_initial_unique_selected_slots.{v}"] = mean(sel(v, "initial_unique_selected_slots"))
    agg[f"mean_initial_effective_selected_slots.{v}"] = mean(sel(v, "initial_effective_selected_slots"))
for v in ("fixed_tree", "learned_tree"):
    agg[f"mean_T_minus_flat.{v}"] = mean([c["fixed_tree" if v == "fixed_tree" else "learned_tree"]["final_nll"]
                                         - c["flat"]["final_nll"] for c in cells])
    agg[f"mean_initial_nonzero_top1_branches.{v}"] = mean(sel(v, "initial_nonzero_top1_branches"))
    agg[f"mean_final_nonzero_top1_branches.{v}"] = mean(sel(v, "final_nonzero_top1_branches"))
Rs = [c["R_fixed_minus_learned"] for c in cells]
agg["mean_R_fixed_minus_learned"] = mean(Rs)
agg["R_positive_cells"] = sum(r > 0 for r in Rs)
parent_R = {}
for b, o in PARENTS:
    parent_R[f"b{b}-o{o}"] = mean([c["R_fixed_minus_learned"] for c in cells if (c["backbone"], c["order"]) == (b, o)])
agg["R_positive_parent_means"] = sum(v > 0 for v in parent_R.values())
agg["R_cells_at_or_above_0.005"] = sum(r >= 0.005 for r in Rs)
agg["parent_mean_R"] = parent_R

# ----------------------------------------------------------------------------- load timing
workers = {}
for b, o in PARENTS:
    for tag in ("baseline", "s501", "s502", "s503"):
        name = f"b{b}-o{o}-{tag}"
        workers[name] = load(TIM / name / "result.json")
assert len(workers) == 36
# (b,o,seed|None, variant, scope, batch) -> record
tr = {}
for name, w in workers.items():
    seed = None if name.endswith("baseline") else int(name[-3:])
    assert w["outcome"] == "completed"
    for r in w["timing"]["records"]:
        tr[(w["backbone"], w["order"], seed, r["variant"], r["scope"], r["batch_size"])] = r

lat_abs = []  # all measured records (for fig7)
for (b, o, s, v, sc, bs), r in sorted(tr.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
    lat_abs.append({"backbone": b, "order": o, "seed": s, "variant": v, "scope": sc, "batch": bs,
                    "median_ns": r["median_ns"], "median_us": r["median_ns"] / 1000.0, "usable": r["usable"]})

ratios = []  # hierarchy/flat per paired worker
for hv in ("fixed_tree", "learned_tree"):
    for sc in SCOPES:
        for bs in WORKLOADS:
            for b, o in PARENTS:
                for s in SEEDS:
                    h, f = tr[(b, o, s, hv, sc, bs)], tr[(b, o, s, "flat", sc, bs)]
                    ratios.append({"variant": hv, "scope": sc, "batch": bs, "backbone": b, "order": o, "seed": s,
                                   "ratio_hier_over_flat": h["median_ns"] / f["median_ns"],
                                   "usable_pair": bool(h["usable"] and f["usable"])})
agg["latency_geomean_ratio"] = {}
agg["latency_ratio_stats"] = {}
for hv in ("fixed_tree", "learned_tree"):
    for sc in SCOPES:
        for bs in WORKLOADS:
            rr = [x["ratio_hier_over_flat"] for x in ratios
                  if x["variant"] == hv and x["scope"] == sc and x["batch"] == bs]
            assert len(rr) == 27
            key = f"b{bs}.{sc}.{hv}"
            agg["latency_geomean_ratio"][key] = geomean(rr)
            agg["latency_ratio_stats"][key] = {
                "min": min(rr), "max": max(rr), "n_below_1": sum(v < 1 for v in rr),
                "n_unusable_pairs": sum((not x["usable_pair"]) for x in ratios
                                        if x["variant"] == hv and x["scope"] == sc and x["batch"] == bs)}
            if bs == 8:
                agg[f"primary_geomean_ratio.{sc}.{hv}"] = geomean(rr)
agg["n_unusable_timing_records"] = sum(not r["usable"] for r in tr.values())
agg["n_timing_records"] = len(tr)

# ----------------------------------------------------------------------------- comparison
comparison = []
for k, pub in PUBLISHED.items():
    mine = agg[k]
    dp = PUB_DP[k]
    diff = abs(mine - pub)
    tol = 0.5 * 10 ** (-dp) + 1e-12
    comparison.append({"quantity": k, "computed": mine, "published": pub, "abs_diff": diff,
                       "matches_at_published_precision": bool(diff <= tol)})
mismatches = [c for c in comparison if not c["matches_at_published_precision"]]


# ----------------------------------------------------------------------------- plotting helpers
def style():
    plt.rcdefaults()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
                         "axes.labelsize": 9, "legend.fontsize": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150, "savefig.dpi": 150,
                         "svg.hashsalt": "p5", "axes.grid": True, "grid.alpha": 0.25})


def save(fig, name, note=NOTE):
    fig.text(0.01, 0.005, note, fontsize=7, color="#444444", ha="left", va="bottom")
    fig.savefig(HERE / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def jit(n, w=0.18):
    return np.linspace(-w, w, n) if n > 1 else np.zeros(1)


def backbone_legend(ax, loc="best", **kw):
    hs = [plt.Line2D([], [], marker=MARK[b], ls="", color="#333333", mfc="none", label=f"parent backbone B={b}")
          for b in BACKBONES]
    hs.append(plt.Line2D([], [], marker="D", ls="", color="k", label="mean of cells"))
    ax.legend(handles=hs, loc=loc, frameon=True, framealpha=0.9, **kw)


def cell_order_key(c):
    return (c["backbone"], c["order"], c["seed"])


# ----------------------------------------------------------------------------- fig1
style()
fig, ax = plt.subplots(figsize=(9, 5.6))
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.14)
cats = ["baseline", "flat", "fixed_tree", "learned_tree", "dense"]
for i, v in enumerate(cats):
    if v == "baseline":
        pts = [(b, o, Z[(b, o)]) for b, o in PARENTS]
    else:
        pts = [(c["backbone"], c["order"], c[v]["final_nll"]) for c in cells]
    for bi, b in enumerate(BACKBONES):
        ys = [y for (bb, oo, y) in pts if bb == b]
        n = len(ys)
        xs = i + (bi - 1) * 0.24 + jit(n, 0.07)
        ax.scatter(xs, ys, marker=MARK[b], s=22, facecolors="none" if False else COL[v], edgecolors="k",
                   linewidths=0.4, alpha=0.85, zorder=3)
    m = agg[f"mean_final_nll.{v}"]
    ax.scatter([i], [m], marker="D", s=70, color="k", zorder=5)
    ax.annotate(f"{m:.6f}", (i, m), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7.5,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.5))
ax.set_xticks(range(5), [LABEL[v] + ("\n(9 parents)" if v == "baseline" else "\n(27 cells)") for v in cats])
ax.set_ylabel("Final validation NLL (nats per byte; lower is better)")
ax.set_title("Fig 1. Final NLL by architecture, every cell shown (fresh P5 validation panel)\n"
             "marker shape = parent backbone B; x-offset groups B=101 | 102 | 103 left to right", loc="left")
backbone_legend(ax, loc="upper right")
save(fig, "fig1_nll_by_architecture.png")

# ----------------------------------------------------------------------------- fig2
style()
fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
fig.subplots_adjust(left=0.07, right=0.99, top=0.82, bottom=0.27, wspace=0.05)
fig.subplots_adjust(left=0.09)
POS, NEG = "#0072B2", "#D55E00"
for ax, b in zip(axes, BACKBONES):
    sub = sorted([c for c in cells if c["backbone"] == b], key=cell_order_key)
    xs, off = [], 0
    for oi, o in enumerate(ORDERS):
        for si, s in enumerate(SEEDS):
            xs.append(oi * 4 + si)
    vals = [c["R_fixed_minus_learned"] for c in sub]
    ax.bar(xs, vals, color=[POS if v > 0 else NEG for v in vals], edgecolor="k", linewidth=0.4, width=0.8, zorder=3)
    ax.axhline(0, color="k", lw=1)
    ax.axhline(0.005, color="#444444", lw=1.2, ls="--")
    ax.set_xticks(xs, [f"s{c['seed']}" for c in sub], rotation=90, fontsize=7)
    for oi, o in enumerate(ORDERS):
        ax.text(oi * 4 + 1, -0.17, f"O = {o}", ha="center", va="top", fontsize=8.5, fontweight="bold",
                transform=matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes), clip_on=False)
    ax.set_title(f"B = {b}", fontsize=9)
    ax.set_ylim(-0.006, 0.0065)
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("R = NLL(fixed) - NLL(learned)\n(nats per byte; positive favours learned)")
axes[2].text(0.99, 0.005 + 0.0003, "registered +0.005 threshold", ha="right", va="bottom", fontsize=7.5,
             color="#444444", transform=axes[2].get_yaxis_transform())
axes[0].text(0.01, 0.0003, "zero (no difference)", ha="left", va="bottom", fontsize=7.5,
             transform=axes[0].get_yaxis_transform())
pm = agg["R_positive_parent_means"]
fig.suptitle("Fig 2. Router contrast R for all 27 paired cells, laid out by B, O and seed\n"
             f"mean R = {agg['mean_R_fixed_minus_learned']:.9f}; positive in {agg['R_positive_cells']}/27 cells, "
             f"positive parent means {pm}/9; cells >= +0.005: {agg['R_cells_at_or_above_0.005']}/27",
             x=0.01, ha="left", fontsize=10)
fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc=POS, ec="k", label="R > 0 (learned lower NLL)"),
                    plt.Rectangle((0, 0), 1, 1, fc=NEG, ec="k", label="R < 0 (fixed lower NLL)")],
           loc="lower right", bbox_to_anchor=(0.99, 0.03), ncol=2, frameon=False)
save(fig, "fig2_router_contrast.png")

# ----------------------------------------------------------------------------- fig3
style()
fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
fig.subplots_adjust(left=0.08, right=0.99, top=0.86, bottom=0.14, wspace=0.18)
for ax, key, vs, ttl, yl in (
        (axes[0], "G", ALLV, "Gain over frozen baseline  G = Z - X", "G (nats per byte; positive = memory helps)"),
        (axes[1], "P", MEM, "Value-shuffle penalty  P = NLL(values permuted) - X",
         "P (nats per byte; positive = shuffling hurts)")):
    for i, v in enumerate(vs):
        for bi, b in enumerate(BACKBONES):
            ys = [c[v][key] for c in cells if c["backbone"] == b]
            xs = i + (bi - 1) * 0.24 + jit(len(ys), 0.07)
            ax.scatter(xs, ys, marker=MARK[b], s=22, color=COL[v], edgecolors="k", linewidths=0.4, alpha=0.85,
                       zorder=3)
        m = mean([c[v][key] for c in cells])
        ax.scatter([i], [m], marker="D", s=70, color="k", zorder=5)
        ax.annotate(f"{m:.5f}", (i, m), xytext=(0, -16), textcoords="offset points", ha="center", fontsize=7.5,
                    bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5), zorder=7)
    ax.axhline(0.005, color="#444444", ls="--", lw=1.2)
    ax.axhline(0, color="k", lw=0.8)
    ax.text(-0.55, 0.0052, "registered 0.005 line", ha="left", va="bottom", fontsize=7.5, color="#444444")
    ax.set_xticks(range(len(vs)), [LABEL[v] for v in vs])
    ax.set_xlim(-0.6, len(vs) - 0.4)
    ax.set_ylabel(yl)
    ax.set_title(ttl, loc="left")
axes[0].text(0.02, 0.97, "dense adapter shown for reference (not a memory)", transform=axes[0].transAxes,
             fontsize=7.5, va="top")
axes[1].set_ylim(top=0.0335)
axes[1].text(0.02, 0.995, "dense: no shuffle intervention exists", transform=axes[1].transAxes, fontsize=7.5,
             va="top")
backbone_legend(axes[1], loc="lower right", bbox_to_anchor=(1.0, 0.1))
fig.suptitle("Fig 3. Memory dependence: gain over frozen baseline (G) and value-shuffle penalty (P), 27 cells each",
             x=0.01, ha="left", fontsize=10)
save(fig, "fig3_memory_dependence.png")

# ----------------------------------------------------------------------------- fig4
style()
fig, axes = plt.subplots(2, 3, figsize=(13, 8.2), sharey=True)
fig.subplots_adjust(left=0.07, right=0.99, top=0.88, bottom=0.2, wspace=0.06, hspace=0.32)
SC_T = {"lookup_score_select": "scope: lookup_score_select", "addition_forward": "scope: addition_forward",
        "model_forward": "scope: model_forward"}
for ri, bs in enumerate(WORKLOADS):
    for ci, sc in enumerate(SCOPES):
        ax = axes[ri, ci]
        for i, hv in enumerate(("fixed_tree", "learned_tree")):
            rr = [x for x in ratios if x["variant"] == hv and x["scope"] == sc and x["batch"] == bs]
            for bi, b in enumerate(BACKBONES):
                sub = [x for x in rr if x["backbone"] == b]
                xs = i + (bi - 1) * 0.24 + jit(len(sub), 0.07)
                ok = [(x_, s_["ratio_hier_over_flat"]) for x_, s_ in zip(xs, sub) if s_["usable_pair"]]
                bad = [(x_, s_["ratio_hier_over_flat"]) for x_, s_ in zip(xs, sub) if not s_["usable_pair"]]
                if ok:
                    ax.scatter(*zip(*ok), marker=MARK[b], s=20, color=COL[hv], edgecolors="k", linewidths=0.4,
                               alpha=0.85, zorder=3)
                if bad:
                    ax.scatter(*zip(*bad), marker="X", s=60, color="#D55E00", edgecolors="k", linewidths=0.6,
                               zorder=6)
            g = agg["latency_geomean_ratio"][f"b{bs}.{sc}.{hv}"]
            ax.scatter([i], [g], marker="D", s=70, color="k", zorder=5)
            ax.annotate(f"geo-mean {g:.3f}", (i, g), xytext=(0, 14), textcoords="offset points", ha="center",
                        fontsize=7.5, bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5), zorder=7)
        ax.axhline(1.0, color="k", lw=1)
        ax.axhline(ANALYTICAL_WORK, color="#7B3294", lw=1.6, ls=(0, (1, 1.5)))
        if bs == 8 and sc == "addition_forward":
            ax.axhline(0.80, color="#444444", lw=1.2, ls="--")
            ax.text(1.45, 0.80 * 1.03, "registered ceiling 0.80", ha="right", va="bottom", fontsize=7.5)
        if bs == 8 and sc == "model_forward":
            ax.axhline(1.05, color="#444444", lw=1.2, ls="--")
            ax.text(1.45, 1.05 * 1.03, "registered ceiling 1.05", ha="right", va="bottom", fontsize=7.5)
        ax.set_yscale("log")
        ax.set_ylim(0.09, 6)
        ax.set_yticks([0.1, 0.2, 0.5, 1, 2, 5], ["0.1", "0.2", "0.5", "1", "2", "5"])
        ax.set_xticks([0, 1], ["Fixed tree", "Learned tree"])
        ax.set_xlim(-0.6, 1.6)
        ax.set_title(f"{SC_T[sc]}\n" + ("batch 8 x T=64 (PRIMARY)" if bs == 8 else "batch 1 x T=64 (secondary)"),
                     fontsize=9, loc="left")
        if ci == 0:
            ax.set_ylabel("MEASURED latency ratio, hierarchy / flat\n(median_ns per paired worker; log scale)")
        ax.text(0.0, 0.1288 * 0.78 if False else ANALYTICAL_WORK * 0.8, "", fontsize=1)
h = [plt.Line2D([], [], color="#7B3294", lw=1.6, ls=(0, (1, 1.5)),
                label="ANALYTICAL score-work ratio 528/4096 = 0.1289 (a count; NOT a speed or latency)"),
     plt.Line2D([], [], marker="o", ls="", color="#888888", mec="k",
                label="MEASURED latency ratio, one marker per paired worker (shape = parent backbone B)"),
     plt.Line2D([], [], marker="D", ls="", color="k", label="MEASURED geometric mean of 27 ratios"),
     plt.Line2D([], [], color="#444444", ls="--", label="registered ceiling (primary workload only)"),
     plt.Line2D([], [], color="k", lw=1, label="ratio = 1.0 (equal latency)"),
     plt.Line2D([], [], marker="X", ls="", color="#D55E00", mec="k",
                label=f"record with usable=false ({agg['n_unusable_timing_records']} of {agg['n_timing_records']} records)")]
fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 0.025), ncol=2, frameon=False, fontsize=8)
fig.suptitle("Fig 4. Analytical score-work ratio versus MEASURED latency ratio (hierarchy / flat), CPU, single thread\n"
             "ratio above 1 = hierarchy slower than flat in this implementation; the dotted line is a count of "
             "dot products, not a latency", x=0.01, ha="left", fontsize=10)
save(fig, "fig4_work_vs_latency.png", note=NOTE + "  Latency pairs share parent and seed.")

# ----------------------------------------------------------------------------- fig5
style()
fig, axes = plt.subplots(1, 3, figsize=(13, 5.4), gridspec_kw={"width_ratios": [3, 3, 2]})
fig.subplots_adjust(left=0.06, right=0.99, top=0.84, bottom=0.17, wspace=0.22)
panels = [("unique_selected_slots", "Unique selected slots (of 4096)", MEM),
          ("effective_selected_slots", "Effective selected slots, exp(entropy) (of 4096)", MEM),
          ("nonzero_top1_branches", "Nonzero top-1 branches (of 16)", ("fixed_tree", "learned_tree"))]
for ax, (key, yl, vs) in zip(axes, panels):
    xt, xl = [], []
    for i, v in enumerate(vs):
        for j, ph in enumerate(("initial", "final")):
            xpos = i * 2.6 + j
            xt.append(xpos)
            xl.append(f"{LABEL[v].replace(' ', chr(10))}\n{ph}")
        for c in cells:
            y0, y1 = c[v][f"initial_{key}"], c[v][f"final_{key}"]
            ax.plot([i * 2.6, i * 2.6 + 1], [y0, y1], color=COL[v], alpha=0.25, lw=0.7, zorder=2)
        for j, ph in enumerate(("initial", "final")):
            for bi, b in enumerate(BACKBONES):
                ys = [c[v][f"{ph}_{key}"] for c in cells if c["backbone"] == b]
                ax.scatter(i * 2.6 + j + (bi - 1) * 0.2 + jit(len(ys), 0.05), ys, marker=MARK[b], s=14, color=COL[v],
                           edgecolors="k", linewidths=0.3, alpha=0.8, zorder=3)
            m = mean([c[v][f"{ph}_{key}"] for c in cells])
            ax.scatter([i * 2.6 + j], [m], marker="D", s=60, color="k", zorder=5)
            ax.annotate(f"{m:.1f}", (i * 2.6 + j, m), xytext=(9, -2), textcoords="offset points", fontsize=7.5)
    ax.set_xticks(xt, xl, fontsize=7)
    ax.set_ylabel(yl)
    ax.set_xlim(-0.6, (len(vs) - 1) * 2.6 + 1.6)
axes[0].set_ylim(bottom=0)
axes[1].set_ylim(bottom=0)
axes[2].set_ylim(0, 17)
backbone_legend(axes[2], loc="lower left", fontsize=6.5)
fig.suptitle("Fig 5. Slot utilisation at initial and final checkpoints on the P5 validation panel; lines join each cell's "
             "initial and final value\n(flat has no branches; counts are per cell over the full panel, "
             "measured by the study's retrieval recorder)", x=0.01, ha="left", fontsize=10)
save(fig, "fig5_slot_utilization.png")

# ----------------------------------------------------------------------------- fig6
style()
fig, ax = plt.subplots(figsize=(12, 5.6))
fig.subplots_adjust(left=0.08, right=0.99, top=0.86, bottom=0.26)
archs = ["flat", "fixed_tree", "learned_tree", "dense"]
for pi, (b, o) in enumerate(PARENTS):
    for ai, v in enumerate(archs):
        x0 = pi + (ai - 1.5) * 0.19
        ys = [-c[v]["G"] for c in cells if (c["backbone"], c["order"]) == (b, o)]
        ax.scatter([x0] * 3, ys, marker=MARK[b], s=22, color=COL[v], edgecolors="k", linewidths=0.4, zorder=3)
        ax.hlines(mean(ys), x0 - 0.07, x0 + 0.07, color="k", lw=2.2, zorder=5)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(range(9), [f"B={b}\nO={o}" for b, o in PARENTS], fontsize=8)
for k in (3, 6):
    ax.axvline(k - 0.5, color="#999999", lw=0.8)
ax.set_ylabel("final NLL minus parent baseline NLL, = -G\n(nats per byte; more negative is better)")
ax.set_xlabel("parent (backbone B, order O); three points per architecture = three seeds; black bar = mean of the 3 seeds")
ax.set_title("Fig 6. Between-parent versus within-parent spread of each architecture's gain relative to its own parent baseline",
             loc="left", fontsize=10)
hs = [plt.Line2D([], [], marker="o", ls="", color=COL[v], mec="k", label=LABEL[v]) for v in archs]
ax.legend(handles=hs, loc="upper center", ncol=4, frameon=True, framealpha=0.9, bbox_to_anchor=(0.5, 1.0))
ax.set_ylim(top=ax.get_ylim()[1] + 0.003)
save(fig, "fig6_parent_dispersion.png")

# ----------------------------------------------------------------------------- fig7
style()
fig, axes = plt.subplots(2, 3, figsize=(13, 8.2))
fig.subplots_adjust(left=0.07, right=0.99, top=0.88, bottom=0.12, wspace=0.28, hspace=0.35)
VCATS = ("baseline", "flat", "fixed_tree", "learned_tree", "dense")
fig7_n = {}
for ri, bs in enumerate(WORKLOADS):
    for ci, sc in enumerate(SCOPES):
        ax = axes[ri, ci]
        vs = [v for v in VCATS if any(r["variant"] == v and r["scope"] == sc and r["batch"] == bs for r in lat_abs)]
        for i, v in enumerate(vs):
            recs = [r for r in lat_abs if r["variant"] == v and r["scope"] == sc and r["batch"] == bs]
            fig7_n[f"b{bs}.{sc}.{v}"] = len(recs)
            for bi, b in enumerate(BACKBONES):
                sub = [r for r in recs if r["backbone"] == b]
                xs = i + (bi - 1) * 0.24 + jit(len(sub), 0.07)
                good = [(x_, r["median_us"]) for x_, r in zip(xs, sub) if r["usable"]]
                bad = [(x_, r["median_us"]) for x_, r in zip(xs, sub) if not r["usable"]]
                if good:
                    ax.scatter(*zip(*good), marker=MARK[b], s=18, color=COL[v], edgecolors="k", linewidths=0.4,
                               alpha=0.85, zorder=3)
                if bad:
                    ax.scatter(*zip(*bad), marker="X", s=60, color="#D55E00", edgecolors="k", linewidths=0.6,
                               zorder=6)
            ax.scatter([i], [mean([r["median_us"] for r in recs])], marker="D", s=50, color="k", zorder=5)
        ax.set_xticks(range(len(vs)), [LABEL[v].replace(" adapter", "").replace("Frozen baseline", "Baseline")
                                       + f"\n(n={fig7_n[f'b{bs}.{sc}.{v}']})" for v in vs], fontsize=7.5)
        ax.set_ylim(bottom=0)
        ax.set_title(f"{SC_T[sc]}\n" + ("batch 8 x T=64 (PRIMARY)" if bs == 8 else "batch 1 x T=64 (secondary)"),
                     fontsize=9, loc="left")
        ax.set_ylabel("MEASURED median latency (microseconds per call)")
h = [plt.Line2D([], [], marker="o", ls="", color="#888888", mec="k",
                label="one marker per timing worker, its median_ns / 1000 (shape = parent backbone B)"),
     plt.Line2D([], [], marker="D", ls="", color="k", label="mean of the plotted medians"),
     plt.Line2D([], [], marker="X", ls="", color="#D55E00", mec="k",
                label=f"record with usable=false ({agg['n_unusable_timing_records']} of {agg['n_timing_records']})")]
fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 0.045), ncol=3, frameon=False, fontsize=8)
fig.suptitle("Fig 7. MEASURED absolute latency per call (CPU, single thread, no KV cache), all timing workers\n"
             "baseline exists only for model_forward; dense only for addition_forward and model_forward; "
             "y axes differ by scope", x=0.01, ha="left", fontsize=10)
save(fig, "fig7_absolute_latency.png", note=NOTE + "  Scopes are not comparable across panels.")

# ----------------------------------------------------------------------------- outputs
png_names = sorted(p.name for p in HERE.glob("fig*.png"))
png_sha = {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in png_names}
inputs_list = "".join(f"{h}  {p}\n" for p, h in sorted(inputs_sha.items()))
(HERE / "inputs.sha256").write_text(inputs_list)
inputs_digest = hashlib.sha256("".join(h + "\n" for _, h in sorted(inputs_sha.items())).encode()).hexdigest()
versions = {"python": platform.python_version(), "matplotlib": matplotlib.__version__, "numpy": np.__version__,
            "platform": platform.platform()}
figure_data = {
    "description": "Every number plotted in fig1-fig7 plus aggregates; derived only from compact result.json records. "
                   "Implementer self-check; not Astra validation or human approval.",
    "labels": {"nll_units": "nats per byte", "work_ratio": "ANALYTICAL (528/4096), not a speedup",
               "latency": "MEASURED (median_ns per paired worker)", "G_P_R": "DERIVED from measured NLL"},
    "definitions": {"Z": "frozen-baseline final.nll on the P5 panel (baseline cell result.json)",
                    "G": "Z - final NLL", "P": "interventions.values_permuted.nll - final NLL (value-only shuffle)",
                    "R": "NLL(fixed_tree) - NLL(learned_tree)",
                    "latency_ratio": "record median_ns(hierarchy) / record median_ns(flat), same worker, scope, batch",
                    "slots": "retrieval.unique_selected_slots, retrieval.effective_selected_slots, "
                             "retrieval.router.nonzero_top1_branches of initial/final records"},
    "analytical_score_work_ratio": ANALYTICAL_WORK,
    "versions": versions,
    "inputs": {"n_files": len(inputs_sha), "sha256_of_sorted_per_file_sha256_lines": inputs_digest,
               "per_file_list": "inputs.sha256"},
    "aggregates": agg,
    "comparison_to_published": comparison,
    "n_mismatches": len(mismatches),
    "parent_baseline_nll": {f"b{b}-o{o}": Z[(b, o)] for b, o in PARENTS},
    "cells": cells,
    "latency_ratios": ratios,
    "absolute_latency_records": lat_abs,
    "output_png_sha256": png_sha,
}
(HERE / "figure_data.json").write_text(json.dumps(figure_data, indent=1, sort_keys=True) + "\n")

# ----------------------------------------------------------------------------- README
rows = "\n".join(
    f"| `{c['quantity']}` | {c['computed']:.9f} | {c['published']} | {c['abs_diff']:.3e} | "
    f"{'yes' if c['matches_at_published_precision'] else '**NO - MISMATCH**'} |" for c in comparison)
mm = ("**No mismatches** at the precision of the published values." if not mismatches else
      "**MISMATCHES FOUND:** " + ", ".join(m["quantity"] for m in mismatches))
readme = f"""# P5 visual-analysis package

Visualisation of the completed, immutable P5 study (ADR-0010) from the committed compact records only
(`results/p5-2026-11-13/<cell>/result.json`, 117 quality cells; `.../timing/<worker>/result.json`, 36 workers).
Every number is derived independently from raw per-cell / per-worker JSON: no `arborlm` import, no audit
scripts, no checkpoints, no model run. These figures are an implementer self-check and visualisation aid. They are
**not** independent review, **not** Astra validation and **not** human approval; no scientific claim is added.

All 27 cells share 9 parents, 3 seeds and one validation panel: they are correlated paired observations, not
independent replicates. Accordingly there are no p-values, significance marks, brackets or error bars.

## Reproduction

Run from the repository root (the `--with` overlay does not touch `uv.lock`; `git status` was checked afterwards):

```sh
uv run --locked --extra pilot --with matplotlib==3.10.8 \\
    python docs/reviews/p5-claude-review-2026-11-13/figures/make_figures.py
```

Versions used: Python {versions['python']}, matplotlib {versions['matplotlib']}, numpy {versions['numpy']}
({versions['platform']}). Inputs: {len(inputs_sha)} files, per-file sha256 in `inputs.sha256`; sha256 over the sorted
per-file hash lines = `{inputs_digest}`. PNG metadata carries no timestamp/software tag; byte stability across reruns
on this machine/version is checked (see report) but is not promised across platforms or font/library versions.
Output PNG sha256 values are recorded in `figure_data.json` (`output_png_sha256`).

## Quantities and their status

* **MEASURED**: NLL values (nats per byte, fresh P5 panel), value-shuffle NLL, slot/branch counts from the
  study's retrieval recorder, `median_ns` timings (CPU, one thread, no KV cache, full fixed-context forward).
* **ANALYTICAL**: score-work ratio 528/4096 = 0.12890625 (key plus router dot products per query). It is a count,
  **not** a speedup, latency, FLOP, memory-traffic or SSD figure.
* **DERIVED**: G = Z - X (Z = frozen-baseline NLL of the same parent), P = shuffled - X, R = fixed - learned,
  latency ratio = median_ns(hierarchy)/median_ns(flat) on the same worker, scope and batch, geometric means.

## Figures

| File | Shows | Units / axes |
|---|---|---|
| `fig1_nll_by_architecture.png` | Final NLL of baseline (9), flat, fixed, learned, dense (27 each); marker shape = parent backbone B; diamond = mean | nats per byte, lower is better |
| `fig2_router_contrast.png` | R = NLL(fixed) - NLL(learned) for 27 paired cells by B, O, seed; registered +0.005 line and zero line; mean and positive counts annotated | nats per byte |
| `fig3_memory_dependence.png` | G (all 4 variants, dense for reference) and P (3 memories) for all cells; registered 0.005 line | nats per byte |
| `fig4_work_vs_latency.png` | ANALYTICAL 528/4096 line beside MEASURED latency ratios hierarchy/flat per scope and workload (batch 8 primary, batch 1 secondary), log axis, ceilings 0.80 / 1.05 on primary row only; `usable=false` records drawn as X | dimensionless ratio |
| `fig5_slot_utilization.png` | Unique selected slots, effective selected slots exp(entropy), nonzero top-1 branches (trees) at initial vs final; lines join each cell | counts (slots of 4096, branches of 16) |
| `fig6_parent_dispersion.png` | Per parent: three seed values and mean of (final NLL - parent baseline NLL) = -G, per architecture | nats per byte, negative is better |
| `fig7_absolute_latency.png` | Every worker's median latency by variant, scope, workload | microseconds per call |

`figure_data.json` holds every plotted number (per-cell table, per-pair ratios, all 36x22-record medians
with `usable` flags), the aggregates and the comparison below. Timing records with `usable=false`:
{agg['n_unusable_timing_records']} of {agg['n_timing_records']} (marked, never dropped).

## Independently computed aggregates versus published values

{mm}  "Matches" means the difference is within half a unit of the published last digit.

| Quantity | Computed (this package) | Published | Absolute difference | Match |
|---|---:|---:|---:|---|
{rows}

## PENDING LEAD REVIEW (ambiguities; not decided silently)

1. **Shuffle definition for P.** Memory cells carry both `values_permuted` and `joint_within_branch`
   interventions. P uses `values_permuted` (value-only shuffle, ADR-0010 sections 5/8: "value-only shuffle changes
   only values"). The published README penalty means match this choice (see table); `joint_within_branch` was not used.
2. **Z.** Taken from each parent's baseline cell `final.nll`; each memory cell's `disabled` NLL was asserted equal to
   it (within 1e-12) while loading.
3. **Latency ratio basis.** Uses each record's `median_ns` (as specified in the brief and ADR section 8). The
   `usable` flag is plotted/marked but is not used to exclude any ratio from the geometric means (ADR counts all 27
   pairs; a ratio is marked when either record is unusable).
4. **Fig 4 analytical line in non-lookup scopes.** The brief asks for the 528/4096 line beside the measured ratios for
   every scope. It is only a score-work count for key/router dot products; it is drawn in every panel but is not a
   prediction of addition/model-forward latency. Reviewer may prefer to restrict it to `lookup_score_select`.
5. **Cell naming.** The brief writes `s50x`; the directories are `s501`, `s502`, `s503`.
6. **`usable=false` records.** Four records are false (flat lookup_score_select b8 [B101,O302,s502]; fixed_tree
   lookup_score_select b8 [B102,O301,s501]; fixed_tree model_forward b1 [B102,O302,s503]; fixed_tree
   lookup_score_select b1 [B102,O303,s503]). Three are in the explanatory lookup scope or secondary workload; none is in the
   primary addition_forward/model_forward decision scopes. They are shown, not dropped (full list: `figure_data.json`).
7. **Fig 5 slot counts** are per-cell values over the whole validation panel from the study's own recorder; they were
   not recomputed from `selected_slot_counts` here (rerunning the entropy from the raw histogram is possible but was
   outside the brief).
"""
(HERE / "README.md").write_text(readme)

print("mismatches:", len(mismatches))
for c in comparison:
    print(f"{c['quantity']:62s} {c['computed']:.9f} {c['published']:<12} {c['abs_diff']:.2e} {c['matches_at_published_precision']}")
print("unusable timing records:", agg["n_unusable_timing_records"], "/", agg["n_timing_records"])
print("python", sys.version.split()[0], "mpl", matplotlib.__version__, "np", np.__version__)
