"""Independent recomputation of P5 aggregate arithmetic from per-cell JSON records.

Written from ADR-0010 section 8 definitions. Imports nothing from `arborlm` and does not
reuse results/p5-2026-11-13/audit/*.py. Reads only:
  results/p5-2026-11-13/<cell>/result.json            (117 cells)
  results/p5-2026-11-13/timing/<worker>/result.json   (36 workers)
Writes recompute.json next to this script. Standard library only.
"""

import json
import math
import statistics as st
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RES = ROOT / "results" / "p5-2026-11-13"
OUT = Path(__file__).resolve().parent / "recompute.json"

BS, OS, SS = (101, 102, 103), (301, 302, 303), (501, 502, 503)
MEM = ("flat", "fixed_tree", "learned_tree")
VAR = (*MEM, "dense")
PAIRS = [(b, o, s) for b in BS for o in OS for s in SS]
PARENTS = [(b, o) for b in BS for o in OS]
TH = 0.005


def bits(x):
    return struct.pack("!d", x)


def dist(xs):
    xs = list(xs)
    return {
        "n": len(xs),
        "mean": st.mean(xs),
        "sample_sd": st.stdev(xs),
        "min": min(xs),
        "max": max(xs),
        "pos": sum(x > 0 for x in xs),
        "zero": sum(x == 0 for x in xs),
        "neg": sum(x < 0 for x in xs),
    }


def load(name):
    return json.loads((RES / name / "result.json").read_text())


# ---------------------------------------------------------------- quality records
cells = {}
for b, o in PARENTS:
    cells[(b, o, 0, "baseline")] = load(f"b{b}-o{o}-baseline")
    for s in SS:
        for v in VAR:
            cells[(b, o, s, v)] = load(f"b{b}-o{o}-{v}-s{s}")
assert len(cells) == 117, len(cells)
n_dirs = sum(1 for p in RES.iterdir() if p.is_dir() and (p / "result.json").exists()
             and p.name.startswith("b"))
checks = {"cell_dirs_with_result_json": n_dirs}

# integrity checks
problems = []
for key, r in cells.items():
    if r["outcome"] != "completed":
        problems.append(f"{key} outcome {r['outcome']}")
    if bits(r["final"]["nll"]) != bits(r["interventions"]["enabled"]["nll"]):
        problems.append(f"{key} final != enabled replay")
    if tuple(r["cell"][k] for k in ("backbone", "order", "seed", "variant")) != key:
        problems.append(f"{key} cell label mismatch")
for (b, o, s) in PAIRS:
    z = cells[(b, o, 0, "baseline")]["final"]["nll"]
    for v in VAR:
        r = cells[(b, o, s, v)]
        if bits(r["interventions"]["disabled"]["nll"]) != bits(z):
            problems.append(f"{(b, o, s, v)} disabled != baseline bitwise")
    for v in MEM:
        r = cells[(b, o, s, v)]
        j = r["interventions"]["joint_within_branch"]["nll"]
        ref = r["final"]["nll"]
        if abs(j - ref) > 1e-6:
            problems.append(f"{(b, o, s, v)} joint permutation |diff|>1e-6")
checks["integrity_problems"] = problems

# exact-equality survey of joint permutation (registered tolerance 1e-6 abs)
joint_exact = {v: sum(bits(cells[(b, o, s, v)]["interventions"]["joint_within_branch"]["nll"])
                      == bits(cells[(b, o, s, v)]["final"]["nll"]) for b, o, s in PAIRS)
               for v in MEM}
joint_maxdiff = {v: max(abs(cells[(b, o, s, v)]["interventions"]["joint_within_branch"]["nll"]
                            - cells[(b, o, s, v)]["final"]["nll"]) for b, o, s in PAIRS)
                 for v in MEM}
checks["joint_permutation_bitwise_equal_cells"] = joint_exact
checks["joint_permutation_max_abs_diff"] = joint_maxdiff
# fixed vs learned initial NLL must be bitwise equal (identical start tensors)
checks["fixed_learned_initial_bitwise_equal"] = sum(
    bits(cells[(b, o, s, "fixed_tree")]["initial"]["nll"])
    == bits(cells[(b, o, s, "learned_tree")]["initial"]["nll"]) for b, o, s in PAIRS)
# any accidental cross-variant exact equality of final NLL
eq_final = []
for b, o, s in PAIRS:
    for i, v in enumerate(VAR):
        for w in VAR[i + 1:]:
            if bits(cells[(b, o, s, v)]["final"]["nll"]) == bits(cells[(b, o, s, w)]["final"]["nll"]):
                eq_final.append([b, o, s, v, w])
checks["cross_variant_equal_final_nll"] = eq_final

# ---------------------------------------------------------------- paired effects
rows = []
for b, o, s in PAIRS:
    z = cells[(b, o, 0, "baseline")]["final"]["nll"]
    f = {v: cells[(b, o, s, v)]["final"]["nll"] for v in VAR}
    ini = {v: cells[(b, o, s, v)]["initial"]["nll"] for v in VAR}
    row = {"b": b, "o": o, "s": s, "Z": z}
    for v in VAR:
        row[f"final_{v}"] = f[v]
        row[f"initial_{v}"] = ini[v]
        row[f"G_{v}"] = z - f[v]
    for v in MEM:
        row[f"P_{v}"] = cells[(b, o, s, v)]["interventions"]["values_permuted"]["nll"] - f[v]
        row[f"T_{v}"] = f[v] - f["flat"]
        row[f"Q_{v}"] = f["dense"] - f[v]
        ident = row[f"G_{v}"] - (z - f["dense"])
        row[f"Qident_absdiff_{v}"] = abs(row[f"Q_{v}"] - ident)
    row["R"] = f["fixed_tree"] - f["learned_tree"]
    rows.append(row)

effect_keys = (["R"] + [f"{k}_{v}" for k in ("G", "P", "T", "Q") for v in MEM if not (k == "T" and v == "flat")]
               + ["G_dense"])
summary = {k: dist(r[k] for r in rows) for k in effect_keys}
final_nll = {v: dist(r[f"final_{v}"] for r in rows) for v in VAR}
initial_nll = {v: dist(r[f"initial_{v}"] for r in rows) for v in VAR}
baseline_nll = dist(cells[(b, o, 0, "baseline")]["final"]["nll"] for b, o in PARENTS)
qident_max = max(r[f"Qident_absdiff_{v}"] for r in rows for v in MEM)


def parent_means(key):
    return {f"b{b}-o{o}": st.mean(r[key] for r in rows if (r["b"], r["o"]) == (b, o))
            for b, o in PARENTS}


parents = {k: parent_means(k) for k in effect_keys}


def marg(key):
    return {
        "backbone": {str(x): st.mean(r[key] for r in rows if r["b"] == x) for x in BS},
        "order": {str(x): st.mean(r[key] for r in rows if r["o"] == x) for x in OS},
        "seed": {str(x): st.mean(r[key] for r in rows if r["s"] == x) for x in SS},
    }


marginals = {k: marg(k) for k in effect_keys}
for v in VAR:
    marginals[f"final_{v}"] = marg(f"final_{v}")


def ranges(m):
    return {f: max(lv.values()) - min(lv.values()) for f, lv in m.items()}


marginal_ranges = {k: ranges(m) for k, m in marginals.items()}

# ---------------------------------------------------------------- flags (ADR-0010 s.8)
flags = {}
for v in MEM:
    g, p = f"G_{v}", f"P_{v}"
    both_cells = sum(r[g] > 0 and r[p] > 0 for r in rows)
    both_par = sum(parents[g][k] > 0 and parents[p][k] > 0 for k in parents[g])
    mean_final = st.mean(r[f"final_{v}"] for r in rows)
    mean_init = st.mean(r[f"initial_{v}"] for r in rows)
    cl = {
        "mean_G>=.005": summary[g]["mean"] >= TH,
        "mean_P>=.005": summary[p]["mean"] >= TH,
        "cells_both_pos>=22": both_cells >= 22,
        "parents_both_pos>=8": both_par >= 8,
        "mean_final<mean_initial": mean_final < mean_init,
    }
    flags[f"U_{v}"] = {"clauses": cl, "pass": all(cl.values()),
                       "counts": {"cells": both_cells, "parents": both_par,
                                  "mean_final": mean_final, "mean_initial": mean_init}}

rc = sum(r["R"] > 0 for r in rows)
rp = sum(x > 0 for x in parents["R"].values())
cl = {"U_learned": flags["U_learned_tree"]["pass"], "mean_R>=.005": summary["R"]["mean"] >= TH,
      "cells_R>0>=22": rc >= 22, "parents_R>0>=8": rp >= 8}
flags["R"] = {"clauses": cl, "pass": all(cl.values()), "counts": {"cells": rc, "parents": rp}}

for v in ("fixed_tree", "learned_tree"):
    k = f"T_{v}"
    c = sum(r[k] <= TH for r in rows)
    pc = sum(x <= TH for x in parents[k].values())
    cl = {"mean_T<=.005": summary[k]["mean"] <= TH, "cells_T<=.005>=22": c >= 22,
          "parents_T<=.005>=8": pc >= 8}
    flags[f"Qtol_{v}"] = {"clauses": cl, "pass": all(cl.values()),
                          "counts": {"cells": c, "parents": pc,
                                     "tree_beats_flat_cells": sum(r[k] < 0 for r in rows)}}

for v in MEM:
    k = f"Q_{v}"
    c = sum(r[k] >= -TH for r in rows)
    pc = sum(x >= -TH for x in parents[k].values())
    cl = {"mean_Q>=-.005": summary[k]["mean"] >= -TH, "cells>=22": c >= 22, "parents>=8": pc >= 8}
    flags[f"dense_tol_{v}"] = {"clauses": cl, "pass": all(cl.values()),
                               "counts": {"cells": c, "parents": pc,
                                          "dense_better_cells": sum(r[k] < 0 for r in rows)}}

# ---------------------------------------------------------------- timing
workers = {}
for b, o in PARENTS:
    workers[(b, o, 0)] = load(f"timing/b{b}-o{o}-baseline")
    for s in SS:
        workers[(b, o, s)] = load(f"timing/b{b}-o{o}-s{s}")
assert len(workers) == 36


def own_reliability(rec):
    d = rec["durations_ns"]
    rm = rec["round_medians_ns"]
    # recompute round medians from raw durations (8 rounds x 10, stored round-major)
    my_rm = [st.median(d[i * 10:(i + 1) * 10]) for i in range(8)]
    med = st.median(d)
    res = rec["resolution_ns"]
    ratio = max(my_rm) / min(my_rm)
    crit = {"positive": min(d) > 0, "median>=100res": med >= 100 * res, "stable<=1.25": ratio <= 1.25}
    return {
        "usable": all(crit.values()),
        "crit": crit,
        "median": med,
        "ratio": ratio,
        "median_matches": med == rec["median_ns"],
        "round_medians_match": my_rm == rm,
        "stored_usable": rec["usable"],
        "n": len(d),
    }


reliab_records = []
mismatch = []
for key, w in workers.items():
    for rec in w["timing"]["records"]:
        mine = own_reliability(rec)
        tag = {"worker": list(key), "bs": rec["batch_size"], "scope": rec["scope"],
               "variant": rec["variant"], "usable": mine["usable"], "ratio": mine["ratio"],
               "crit": mine["crit"]}
        reliab_records.append(tag)
        if (not mine["median_matches"] or not mine["round_medians_match"]
                or mine["usable"] != mine["stored_usable"] or mine["n"] != 80):
            mismatch.append(tag)
unusable = [r for r in reliab_records if not r["usable"]]


def med_of(key, bs, scope, variant):
    for rec in workers[key]["timing"]["records"]:
        if (rec["batch_size"], rec["scope"], rec["variant"]) == (bs, scope, variant):
            return st.median(rec["durations_ns"]), own_reliability(rec)["usable"]
    return None


latency = {}
for bs in (8, 1):
    for scope in ("lookup_score_select", "addition_forward", "model_forward"):
        for v in ("fixed_tree", "learned_tree", "dense"):
            if v == "dense" and scope == "lookup_score_select":
                continue
            ratios, usable = [], []
            for key in PAIRS:
                t, ut = med_of(key, bs, scope, v)
                f, uf = med_of(key, bs, scope, "flat")
                ratios.append(t / f)
                usable.append(ut and uf)
            gm = st.geometric_mean(ratios)
            par = {f"b{b}-o{o}": st.geometric_mean(r for (bb, oo, _), r in zip(PAIRS, ratios)
                                                    if (bb, oo) == (b, o)) for b, o in PARENTS}
            entry = {"geometric_mean": gm, "min": min(ratios), "max": max(ratios),
                     "all_pairs_usable": all(usable), "n_pairs_usable": sum(usable),
                     "parent_geometric_means": par, "ratios": ratios}
            if bs == 8 and scope in ("addition_forward", "model_forward") and v != "dense":
                if scope == "addition_forward":
                    cl = {"gm<=.80": gm <= 0.80, "cells<1>=22": sum(r < 1 for r in ratios) >= 22,
                          "parents<1>=8": sum(x < 1 for x in par.values()) >= 8}
                    entry["cells_passing"] = sum(r < 1 for r in ratios)
                    entry["parents_passing"] = sum(x < 1 for x in par.values())
                else:
                    cl = {"gm<=1.05": gm <= 1.05, "cells<=1.05>=22": sum(r <= 1.05 for r in ratios) >= 22,
                          "parents<=1.05>=8": sum(x <= 1.05 for x in par.values()) >= 8}
                    entry["cells_passing"] = sum(r <= 1.05 for r in ratios)
                    entry["parents_passing"] = sum(x <= 1.05 for x in par.values())
                entry["clauses"] = cl
            latency[f"bs{bs}/{scope}/{v}_over_flat"] = entry

L = {}
for v in ("fixed_tree", "learned_tree"):
    a = latency[f"bs8/addition_forward/{v}_over_flat"]
    m = latency[f"bs8/model_forward/{v}_over_flat"]
    reliable = a["all_pairs_usable"] and m["all_pairs_usable"]
    passed = all(a["clauses"].values()) and all(m["clauses"].values())
    L[v] = "INCONCLUSIVE" if not reliable else ("PASS" if passed else "FAIL")

# work flag: recompute from trace summaries
work = {}
for v in ("fixed_tree", "learned_tree"):
    ok, n = True, 0
    for key in PAIRS:
        tr = workers[key]["traces"]
        for size in ("8", "1"):
            for ft, tt in zip(tr["flat"][size], tr[v][size], strict=True):
                n += 1
                sr = (tt["key_dot_products_per_query"] + tt["router_dot_products_per_query"]) / (
                    ft["key_dot_products_per_query"] + ft["router_dot_products_per_query"])
                lr = (tt["candidate_key_elements_per_query"] + tt["router_elements_per_query"]) / (
                    ft["candidate_key_elements_per_query"] + ft["router_elements_per_query"])
                ok &= (sr == 0.12890625 and lr == 0.12890625 and tt["selected_values_per_query"] == 8
                       and ft["selected_values_per_query"] == 8 and tt["validated"] and ft["validated"])
    work[v] = {"comparisons": n, "all_ratio_0.12890625_and_8_values": ok}

composite = (flags["U_learned_tree"]["pass"] and flags["R"]["pass"] and flags["Qtol_learned_tree"]["pass"]
             and work["learned_tree"]["all_ratio_0.12890625_and_8_values"] and L["learned_tree"] == "PASS")

# ---------------------------------------------------------------- exploratory descriptives
explore = {}
# within-parent ordering of the three memory variants
orders = {}
for r in rows:
    key = ">".join(sorted(MEM, key=lambda v: r[f"final_{v}"]))  # best (lowest NLL) first
    orders[key] = orders.get(key, 0) + 1
explore["memory_rank_orders_best_first"] = orders
# R contribution by parent / seed (sum of R)
explore["R_by_cell"] = {f"b{r['b']}-o{r['o']}-s{r['s']}": r["R"] for r in rows}
tot = sum(r["R"] for r in rows)
explore["R_total_sum"] = tot
explore["R_mean_excluding_each_parent"] = {
    f"b{b}-o{o}": st.mean(r["R"] for r in rows if (r["b"], r["o"]) != (b, o)) for b, o in PARENTS}
explore["R_mean_excluding_each_seed"] = {
    str(s): st.mean(r["R"] for r in rows if r["s"] != s) for s in SS}
# gate / router fields
gates = {}
for v in VAR:
    gf = [cells[(b, o, s, v)]["gate_final"] for b, o, s in PAIRS]
    gates[v] = dist(gf) | {"n_below_initial_-2": sum(g < -2.0 for g in gf)}
explore["gate_final"] = gates
rm = {}
for v in ("fixed_tree", "learned_tree"):
    mv = [cells[(b, o, s, v)]["router_movement_l2"] for b, o, s in PAIRS]
    ns = [cells[(b, o, s, v)]["router_nonzero_gradient_steps"] for b, o, s in PAIRS]
    rm[v] = {"movement": dist(mv), "nonzero_grad_steps": sorted(set(map(str, ns)))}
explore["router"] = rm
# correlation helpers
def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
lt = [cells[(b, o, s, "learned_tree")] for b, o, s in PAIRS]
explore["corr_R_vs_learned_router_movement"] = corr([r["R"] for r in rows], [c["router_movement_l2"] for c in lt])
explore["corr_G_learned_vs_gate_final_learned"] = corr([r["G_learned_tree"] for r in rows], [c["gate_final"] for c in lt])
explore["corr_G_dense_vs_gate_final_dense"] = corr(
    [r["G_dense"] for r in rows], [cells[(b, o, s, "dense")]["gate_final"] for b, o, s in PAIRS])
# utilization
util = {}
for v in MEM:
    eff = [cells[(b, o, s, v)]["final"]["retrieval"]["effective_selected_slots"] for b, o, s in PAIRS]
    uniq = [cells[(b, o, s, v)]["final"]["retrieval"]["unique_selected_slots"] for b, o, s in PAIRS]
    util[v] = {"effective_selected_slots": dist(eff), "unique_selected_slots": dist(uniq)}
    if v != "flat":
        nz = [cells[(b, o, s, v)]["final"]["retrieval"]["router"]["nonzero_top1_branches"] for b, o, s in PAIRS]
        util[v]["nonzero_top1_branches"] = dist(nz)
        unc = [cells[(b, o, s, v)]["final"]["retrieval"]["unique_candidate_slots"] for b, o, s in PAIRS]
        util[v]["unique_candidate_slots"] = dist(unc)
        # fraction of selected values coming from top-1 branch is not recorded; record
        # share of selected values from branches never visited (must be 0)
        bad = 0
        for b, o, s in PAIRS:
            rr = cells[(b, o, s, v)]["final"]["retrieval"]["router"]
            bad += sum(1 for sv, vv in zip(rr["selected_value_branch_counts"], rr["visited_branch_counts"])
                       if sv > 0 and vv == 0)
        util[v]["branches_with_selected_but_never_visited"] = bad
explore["utilization_final"] = util
explore["corr_T_learned_vs_eff_slots_learned"] = corr(
    [r["T_learned_tree"] for r in rows], util and [cells[(b, o, s, "learned_tree")]["final"]["retrieval"]["effective_selected_slots"] for b, o, s in PAIRS])
# further utilization figures quoted in the review
def ent_stats(counts):
    tot = sum(counts)
    ps = [c / tot for c in counts if c > 0]
    h = -sum(p * math.log(p) for p in ps)
    return h, max(counts) / tot


util2 = {}
for v in MEM:
    for tag in ("initial", "final"):
        eff, hot, t1e, t1h = [], [], [], []
        for b, o, s in PAIRS:
            rr = cells[(b, o, s, v)][tag]["retrieval"]
            h, mx = ent_stats(rr["selected_slot_counts"])
            eff.append(math.exp(h))
            hot.append(mx)
            if v != "flat":
                th, tm = ent_stats(rr["router"]["top1_branch_counts"])
                t1e.append(th / math.log(16))
                t1h.append(tm)
        util2[f"{v}/{tag}"] = {"effective_slots_from_counts_mean": st.mean(eff),
                               "hottest_slot_fraction_mean": st.mean(hot)}
        if v != "flat":
            util2[f"{v}/{tag}"]["normalized_top1_entropy_mean"] = st.mean(t1e)
            util2[f"{v}/{tag}"]["hottest_top1_branch_fraction_mean"] = st.mean(t1h)
    if v != "flat":
        same = sum(cells[(b, o, s, "fixed_tree")]["initial"]["retrieval"]["selected_slot_counts"]
                   == cells[(b, o, s, "learned_tree")]["initial"]["retrieval"]["selected_slot_counts"]
                   for b, o, s in PAIRS)
        util2["fixed_learned_initial_slot_counts_identical_cells"] = same
explore["utilization_from_counts"] = util2
# flat joint-permutation non-bitwise cell(s)
explore["flat_joint_non_bitwise_cells"] = [
    [b, o, s, cells[(b, o, s, "flat")]["interventions"]["joint_within_branch"]["nll"]
     - cells[(b, o, s, "flat")]["final"]["nll"]]
    for b, o, s in PAIRS
    if bits(cells[(b, o, s, "flat")]["interventions"]["joint_within_branch"]["nll"])
    != bits(cells[(b, o, s, "flat")]["final"]["nll"])]
# router gradient norms from raw metrics.jsonl (learned tree only)
rg = []
for b, o, s in PAIRS:
    norms, ratios = [], []
    for line in (RES / f"b{b}-o{o}-learned_tree-s{s}" / "metrics.jsonl").read_text().splitlines():
        ev = json.loads(line)
        if ev.get("event") == "train_step":
            norms.append(ev["pre_clip_router_gradient_norm"])
            ratios.append(ev["pre_clip_router_gradient_norm"] / ev["pre_clip_gradient_norm"])
    rg.append({"cell": [b, o, s], "steps": len(norms), "min": min(norms), "median": st.median(norms),
               "max": max(norms), "median_router_share_of_total_norm": st.median(ratios),
               "n_zero": sum(n == 0 for n in norms)})
explore["learned_router_grad_norms"] = {
    "per_cell": rg,
    "global_min": min(r["min"] for r in rg),
    "median_of_medians": st.median(r["median"] for r in rg),
    "median_router_share": st.median(r["median_router_share_of_total_norm"] for r in rg),
}
fixed_router_fields = set()
for b, o, s in PAIRS:
    for line in (RES / f"b{b}-o{o}-fixed_tree-s{s}" / "metrics.jsonl").read_text().splitlines():
        ev = json.loads(line)
        if ev.get("event") == "train_step":
            fixed_router_fields.add(repr(ev.get("pre_clip_router_gradient_norm")))
explore["fixed_tree_router_grad_field_values"] = sorted(fixed_router_fields)
# key-normalization operand counts recorded in traces
kn = {}
for v in MEM:
    vals = set()
    for key in PAIRS:
        for t in workers[key]["traces"][v]["8"]:
            vals.add((t["queries"], t["key_normalization_input_elements"]))
    kn[v] = sorted(vals)
explore["trace_key_norm_elements_bs8"] = kn
# timing call counts summed over the 36 workers
cc = {}
for w in workers.values():
    for k, v in w["timing"]["call_counts"].items():
        cc[k] = cc.get(k, 0) + v
cc["warmups_plus_timed"] = cc.get("warmups", 0) + cc.get("timed", 0)
cc["timed_samples_from_records"] = sum(len(r["durations_ns"]) for w in workers.values()
                                       for r in w["timing"]["records"])
explore["timing_call_counts_sum"] = cc
# training seconds
explore["training_seconds"] = {v: dist(cells[(b, o, s, v)]["training_seconds_including_logs_and_saves"]
                                       for b, o, s in PAIRS) for v in VAR}
# effect sizes in relation to spread: between-cell SD of final NLL vs. contrasts
explore["sd_of_paired_contrasts_vs_mean"] = {k: {"mean": summary[k]["mean"], "sd": summary[k]["sample_sd"],
                                                 "mean_over_sd": summary[k]["mean"] / summary[k]["sample_sd"]}
                                             for k in effect_keys}

# ---------------------------------------------------------------- published numbers
published = {
    "baseline_mean": 2.356630571600464,
    "final_mean_flat": 2.333691890041033, "final_mean_fixed_tree": 2.334497243027996,
    "final_mean_learned_tree": 2.335080704203358, "final_mean_dense": 2.329312946371458,
    "G_flat": 0.022938681559430, "G_fixed_tree": 0.022133328572468, "G_learned_tree": 0.021549867397105,
    "G_dense": 0.027317625229005,
    "P_flat": 0.022679531739818, "P_fixed_tree": 0.021944248289974, "P_learned_tree": 0.021603652586540,
    "R_mean": -0.000583461175362, "R_sd": 0.001871343960431, "R_min": -0.004701465368271,
    "R_max": 0.003432027995586, "R_pos_cells": 10, "R_pos_parents": 3,
    "T_fixed": 0.000805352986963, "T_learned": 0.001388814162325,
    "Q_flat": -0.004378943669575, "Q_fixed": -0.005184296656538, "Q_learned": -0.005767757831900,
    "gm_add_fixed": 2.603052229693476, "gm_add_learned": 2.598485032668176,
    "gm_fwd_fixed": 2.190282147732538, "gm_fwd_learned": 2.184085943163431,
}
mine = {
    "baseline_mean": baseline_nll["mean"],
    **{f"final_mean_{v}": final_nll[v]["mean"] for v in VAR},
    **{f"G_{v}": summary[f"G_{v}"]["mean"] for v in VAR},
    **{f"P_{v}": summary[f"P_{v}"]["mean"] for v in MEM},
    "R_mean": summary["R"]["mean"], "R_sd": summary["R"]["sample_sd"], "R_min": summary["R"]["min"],
    "R_max": summary["R"]["max"], "R_pos_cells": summary["R"]["pos"], "R_pos_parents": rp,
    "T_fixed": summary["T_fixed_tree"]["mean"], "T_learned": summary["T_learned_tree"]["mean"],
    "Q_flat": summary["Q_flat"]["mean"], "Q_fixed": summary["Q_fixed_tree"]["mean"],
    "Q_learned": summary["Q_learned_tree"]["mean"],
    "gm_add_fixed": latency["bs8/addition_forward/fixed_tree_over_flat"]["geometric_mean"],
    "gm_add_learned": latency["bs8/addition_forward/learned_tree_over_flat"]["geometric_mean"],
    "gm_fwd_fixed": latency["bs8/model_forward/fixed_tree_over_flat"]["geometric_mean"],
    "gm_fwd_learned": latency["bs8/model_forward/learned_tree_over_flat"]["geometric_mean"],
}
comparison = {k: {"published": published[k], "recomputed": mine[k],
                  "abs_diff": abs(published[k] - mine[k]),
                  "agrees_to_1e-12": abs(published[k] - mine[k]) <= 1e-12} for k in published}

out = {
    "provenance": {"script": "docs/reviews/p5-claude-review-2026-11-13/audit/recompute.py",
                   "python": sys.version, "inputs": "results/p5-2026-11-13/*/result.json, timing/*/result.json"},
    "checks": checks,
    "Q_identity_max_abs_diff": qident_max,
    "baseline_nll": baseline_nll,
    "final_nll": final_nll,
    "initial_nll": initial_nll,
    "effects": summary,
    "parent_means": parents,
    "marginal_means": marginals,
    "marginal_ranges": marginal_ranges,
    "flags": flags,
    "latency": latency,
    "L_flags": L,
    "work": work,
    "timing_reliability": {"records": len(reliab_records), "unusable": unusable,
                           "stored_vs_recomputed_mismatch": mismatch},
    "composite_full_learned_hierarchy": composite,
    "comparison_with_published": comparison,
    "exploratory": explore,
    "paired_rows": rows,
}
OUT.write_text(json.dumps(out, indent=1, sort_keys=False))
print("problems:", problems)
print("Q identity max abs diff:", qident_max)
for k, v in comparison.items():
    print(f"{k:24s} pub={v['published']!r:24} mine={v['recomputed']!r:24} diff={v['abs_diff']:.3e}")
print("flags:", {k: v["pass"] for k, v in flags.items()}, "L:", L, "work:", work, "composite:", composite)
print("unusable timing records:", [(u["worker"], u["bs"], u["scope"], u["variant"], round(u["ratio"], 4)) for u in unusable])
print("stored-vs-recomputed timing mismatches:", len(mismatch))
