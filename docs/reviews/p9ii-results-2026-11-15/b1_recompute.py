"""P9-II results audit, part B1: recomputation of every registered decision from the per-cell records, written from the text of
ADR-0019 revision 4 (sections 5, 8.1-8.7). Imports nothing from studies/ or arborlm. Compares its own decisions with the run's
results.json at the end.

Usage:
    python3 -I docs/reviews/p9ii-results-2026-11-15/b1_recompute.py <raw-run-dir> <committed-results-dir> <out-json>
"""

from __future__ import annotations

import json
import statistics
import sys
from itertools import combinations
from math import comb, exp, lgamma, log
from pathlib import Path

RAW, COM, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
LEARNED = ["A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S"]
CONSTANT = {"A0", "A1", "A1-S", "A5-C", "A5-D"}
ADVANCE_ORDER = ["A5-C", "A5-D", "A4", "A2", "A1"]
CARRY_ORDER = ["A0", "A5-C", "A5-D", "A4", "A2", "A1"]
LABEL_FREE = {"A0", "A4", "A5-C", "A5-D"}
U = 8192
U_PRE = 2048  # calibrated (freeze record item 3); Stage 1 schedule
out: dict = {}


def say(*a: object) -> None:
    print(*a, flush=True)


def load(p: Path):
    return json.loads(p.read_text())


# ------------------------------------------------------------------ records
cells: dict[str, dict] = {}
for d in sorted((RAW / "cells").iterdir()):
    lab = d.name
    t = load(d / "train.json")
    evals = {int(e.name[1:]): load(e / "eval.json") for e in sorted((d / "eval").iterdir())}
    cells[lab] = {"label": lab, "arm": t["arm"], "stage": t["stage"], "slots": t["slots"], "draw": t["draw"], "j": t["seed_index"],
                  "train": t, "evals": evals, "dir": d}


def cell(stage: int, arm: str, draw: int, j: int) -> dict | None:
    for c in cells.values():
        if (c["stage"], c["arm"], c["draw"], c["j"]) == (stage, arm, draw, j):
            return c
    return None


# ------------------------------------------------------------------ G2 interval, independently (exact binomial, p = 1/32)
def chance_interval(n: int, level: float = 0.999875) -> tuple[int, int]:
    a = 1 - level
    c, lo, hi = 0.0, None, None
    for k in range(n + 1):
        c += exp(lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) + k * log(1 / 32) + (n - k) * log(31 / 32))
        if lo is None and c > a / 2:
            lo = k
        if hi is None and c >= 1 - a / 2:
            hi = k
            break
    return lo, hi


INTERVALS = {n: chance_interval(n) for n in (2048, 8192, 32768)}
say("independent G2 intervals:", INTERVALS)


# ------------------------------------------------------------------ cell success (section 8.3)
def a6_of(stage: int, draw: int, update: int) -> dict:
    return cell(stage, "A6", draw, 0)["evals"][update]


def conditions(c: dict, update: int, h_ref_b: bool = False) -> dict:
    e = c["evals"][update]
    a6 = a6_of(c["stage"], c["draw"], update)
    pa, pb = e["panels"]["A"], e["panels"]["B"]
    a6a, a6b = a6["panels"]["A"]["accuracy"], a6["panels"]["B"]["accuracy"]
    draw_ok = a6a >= 0.90 and a6b >= 0.90
    lo, hi = INTERVALS[e["facts"]]
    c1 = pa["accuracy"] >= 0.90 * a6a and pb["accuracy"] >= 0.90 * a6b
    c2 = all(lo <= p[k] <= hi for p in (pa, pb) for k in ("permuted_correct", "disabled_correct"))
    rec_c2 = all(p["permuted_at_chance"] and p["disabled_at_chance"] for p in (pa, pb))
    rec_iv = all(tuple(p["chance_interval"]) == (lo, hi) for p in (pa, pb))
    pr = e["probe"]
    c3 = pr["distinct_top1"] >= 0.50 * pr["probe_facts"] and pr["largest_top1_share"] <= 0.02
    h1, h2 = e["secondary"]["H1"]["accuracy"], e["secondary"]["H2"]["accuracy"]
    c4 = h1 >= 0.90 * pa["accuracy"] and h2 >= 0.90 * pa["accuracy"]
    c4_b = h1 >= 0.90 * pb["accuracy"] and h2 >= 0.90 * pb["accuracy"]  # reading "condition 4 on Panel B" as a Panel B reference
    c5 = not pa["leakage"] and not pb["leakage"]
    r = e["language_modelling"]["relative_rise"]
    r6 = a6["language_modelling"]["relative_rise"]
    margins = {  # positive = passes; used to list borderline cells
        "c1_A": pa["accuracy"] - 0.90 * a6a, "c1_B": pb["accuracy"] - 0.90 * a6b,
        "c4_H1": h1 - 0.90 * pa["accuracy"], "c4_H2": h2 - 0.90 * pa["accuracy"],
        "lm": (r6 + 0.05) - r,
    }
    ok = c1 and c2 and c3 and c4 and c5
    return {"draw_evaluated": draw_ok, "c1": c1, "c2": c2, "c2_record_flags": rec_c2, "record_interval_equal": rec_iv, "c3": c3,
            "c4": c4, "c4_panelB_variant": c4_b, "c5": c5, "success": ok and draw_ok,
            "success_c4_both_refs": ok and c4_b and draw_ok, "lm_flag": r > r6 + 0.05, "r": r, "r_a6": r6, "margins": margins,
            "acc_A": pa["accuracy"], "acc_B": pb["accuracy"], "H1": h1, "H2": h2, "a6_A": a6a, "a6_B": a6b,
            "probe_distinct": pr["distinct_top1"], "probe_largest_share": pr["largest_top1_share"],
            "probe_largest_count": pr.get("largest_top1_count")}


# ------------------------------------------------------------------ section 8.1 trajectory categories from diagnostics
def diag(c: dict) -> list[dict]:
    return [json.loads(x) for x in (c["dir"] / "diagnostics.jsonl").open()]


def slot_ok(rec: dict) -> bool:
    return rec["distinct_top1"] >= 0.50 * rec["probe_facts"] and rec["largest_top1_share"] <= 0.02


def trajectory(c: dict, readout: int, after: int = 0) -> dict:
    recs = [r for r in diag(c) if after < r["update"] <= readout]
    onset = next((r["update"] for r in recs if r["distinct_top1"] <= 32), None)
    escape = None
    if onset is not None:
        later = [r for r in recs if r["update"] > onset]
        for i, r in enumerate(later):
            if all(slot_ok(x) for x in later[i:]):
                escape = r["update"]
                break
    sep = slot_ok(recs[-1]) if recs else None
    if onset is None:
        cat = "never collapsed and separated" if sep else "never collapsed, not separated"
    else:
        cat = "collapsed and recovered" if escape is not None else "collapsed and not recovered"
    return {"onset": onset, "escape": escape, "separated_at_readout": sep, "category": cat, "last_record": recs[-1]["update"] if recs else None}


# ------------------------------------------------------------------ classes, paired rule
def sign_p(a: int, b: int) -> float:
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def arm_cells(stage: int, arm: str) -> list[dict]:
    return sorted((c for c in cells.values() if c["stage"] == stage and c["arm"] == arm), key=lambda c: (c["draw"], c["j"]))


def classify(stage: int, arm: str, update: int, success_key: str = "success") -> dict:
    cs = arm_cells(stage, arm)
    res = {f"{c['draw']}/{c['j']}": conditions(c, update) for c in cs}
    ev = {k: v for k, v in res.items() if v["draw_evaluated"]}
    succ = sum(v[success_key] for v in ev.values())
    fail = len(ev) - succ
    lm = sum(v["lm_flag"] for v in ev.values())
    need = 14 if stage == 1 else 7
    if len(ev) < need:
        cls = "NOT_EVALUATED"
    elif fail <= 1 and lm <= 1:
        cls = "RELIABLE"
    elif fail <= 1 and lm > 1:
        cls = "UNRELIABLE (LM CAPABILITY REDUCED)"
    elif succ >= (4 if stage == 1 else 2):
        cls = "UNRELIABLE"
    else:
        cls = "FAILS"
    return {"class": cls, "evaluated": len(ev), "successes": succ, "failures": fail, "lm_flagged": lm, "cells": res}


def paired(x: dict, a0: dict, key: str = "success") -> dict:
    keys = sorted(set(x["cells"]) & set(a0["cells"]))
    xo = sum(x["cells"][k][key] and not a0["cells"][k][key] for k in keys)
    ao = sum(a0["cells"][k][key] and not x["cells"][k][key] for k in keys)
    d = xo - ao
    if d >= 4 and x["successes"] > a0["successes"]:
        lab = "IMPROVES ON A0"
    elif d <= -4:
        lab = "HARMS"
    else:
        lab = "NOT DISTINGUISHED FROM A0"
    return {"d": d, "x_only": xo, "a0_only": ao, "pairs": len(keys), "p": sign_p(xo, ao), "label": lab}


# ------------------------------------------------------------------ Stage 1
say("\n=== Stage 1 (4,096 slots, U)")
s1 = {arm: classify(1, arm, U) for arm in LEARNED}
for arm in LEARNED:
    if arm != "A0":
        s1[arm]["paired"] = paired(s1[arm], s1["A0"])
for arm, v in s1.items():
    say(f"{arm:5s} {v['class']:12s} eval {v['evaluated']} succ {v['successes']} fail {v['failures']} lm {v['lm_flagged']} "
        f"paired {v.get('paired')}")
    fails = {k: [n for n in ('c1', 'c2', 'c3', 'c4', 'c5') if not c[n]] for k, c in v['cells'].items() if not c['success']}
    say("      failing conditions per cell:", fails)
var = {arm: classify(1, arm, U, "success_c4_both_refs")["successes"] for arm in LEARNED}
say("successes if condition 4 also had to hold against Panel B:", var)
nc1 = s1["A1-S"]["paired"]["label"] == "IMPROVES ON A0" or s1["A1-S"]["class"] == "RELIABLE"
say("NEGATIVE CONTROL FAILED at 4,096:", nc1)
d_a2_a1 = paired(s1["A2"], s1["A1"])
say("d(A2 against A1) at 4,096:", d_a2_a1)
eligible = [a for a in ADVANCE_ORDER if s1[a]["class"] == "RELIABLE" and not (nc1 and a in ("A1", "A2"))]
advance = eligible[:2]
s2_arms = ["A0", *advance] + (["A1-S"] if {"A1", "A2"} & set(advance) else [])
run_stage2 = bool(eligible) or s1["A0"]["class"] == "RELIABLE"
say("Stage 1 gate: eligible", eligible, "advancing", advance, "Stage 2 arms", s2_arms, "run", run_stage2)

# ------------------------------------------------------------------ Stage 2
say("\n=== Stage 2 (16,384 slots; class at 4U, U printed)")
s2 = {arm: classify(2, arm, 4 * U) for arm in s2_arms}
s2u = {arm: classify(2, arm, U) for arm in s2_arms}
for arm in s2_arms:
    if arm != "A0":
        s2[arm]["paired"] = paired(s2[arm], s2["A0"])
        s2u[arm]["paired"] = paired(s2u[arm], s2u["A0"])
for arm in s2_arms:
    v, vu = s2[arm], s2u[arm]
    say(f"{arm:5s} 4U: {v['class']:12s} succ {v['successes']}/{v['evaluated']} lm {v['lm_flagged']} paired {v.get('paired')}")
    say(f"      U : {vu['class']:12s} succ {vu['successes']}/{vu['evaluated']} lm {vu['lm_flagged']} paired {vu.get('paired')}"
        f"{'  -> ALSO AT MATCHED UPDATES' if arm in CONSTANT and v['class'] == 'RELIABLE' and vu['class'] == 'RELIABLE' else ''}")
    fails = {k: [n for n in ('c1', 'c2', 'c3', 'c4', 'c5') if not c[n]] for k, c in v['cells'].items() if not c['success']}
    say("      4U failing conditions per cell:", fails)
nc2 = "A1-S" in s2 and (s2["A1-S"]["paired"]["label"] == "IMPROVES ON A0" or s2["A1-S"]["class"] == "RELIABLE")
say("NEGATIVE CONTROL FAILED at 16,384:", nc2)
if "A2" in s2 and "A1" in s2:
    say("d(A2 against A1) at 16,384:", paired(s2["A2"], s2["A1"]))
stage2_status = "COMPLETE" if all(len(arm_cells(2, a)) == 8 for a in s2_arms) else "INCOMPLETE"

# ------------------------------------------------------------------ Stage 3
carry = next((a for a in CARRY_ORDER if a in s2 and s2[a]["class"] == "RELIABLE" and not (nc2 and a in ("A1", "A2"))), None)
say("\n=== carry-forward order applied at 16,384 (4U):", carry)
s3 = None
if carry in ("A2", "A4"):
    s3 = {"status": "NOT RUN - SCHEDULED ARM"}
elif carry is not None:
    cs = arm_cells(3, carry)
    res = {f"{c['draw']}/{c['j']}": conditions(c, U) for c in cs}
    n = sum(v["success"] for v in res.values())
    s3 = {"selected": carry, "cells": len(cs), "successes": n,
          "label": "SCALE PROBE POSITIVE" if n == 2 and len(cs) == 2 else "SCALE PROBE UNINFORMATIVE",
          "detail": {k: {kk: v[kk] for kk in ("acc_A", "acc_B", "a6_A", "a6_B", "probe_distinct", "probe_largest_share", "c1", "c3", "c4")}
                     for k, v in res.items()}}
say("Stage 3:", json.dumps(s3))
for arm in ("A6", "A7"):
    for c in arm_cells(3, arm):
        say(f"   Stage 3 {arm} d{c['draw']}: Panel A {c['evals'][U]['panels']['A']['accuracy']:.4f} B {c['evals'][U]['panels']['B']['accuracy']:.4f}")

# ------------------------------------------------------------------ outcome (section 8.6)
others = [a for a in LEARNED if a not in ("A0", "A1-S") and not (nc1 and a in ("A1", "A2"))]
rel4 = [a for a in others if s1[a]["class"] == "RELIABLE"]
rel16 = [a for a in others if a in s2 and s2[a]["class"] == "RELIABLE"]
if s1["A0"]["class"] == "NOT_EVALUATED" or any(s1[a]["class"] == "NOT_EVALUATED" for a in LEARNED) and False:
    row = 2
elif nc1 and not any(s1[a]["class"] == "RELIABLE" for a in ("A0", "A4", "A5-C", "A5-D")):
    row = 2
elif s1["A0"]["class"] == "RELIABLE":
    row = 3
elif stage2_status == "COMPLETE" and [a for a in rel4 if a in rel16]:
    row = 4
elif stage2_status == "COMPLETE" and rel4:
    row = 5
elif rel4:
    row = 6
elif any(s1[a]["class"].startswith("UNRELIABLE") for a in LEARNED if a != "A1-S"):
    row = 7
else:
    row = 8
both = [a for a in CARRY_ORDER if a in rel4 and a in rel16]
say("\n=== outcome row", row, "; arms RELIABLE at 4,096 (excluding A0, A1-S):", rel4, "; at 16,384:", rel16, "; both:", both)
for a in both:
    sup = "(LABEL-FREE)" if a in LABEL_FREE else "(ADDRESS-SUPERVISED IN TRAINING)"
    say(f"   label: ADDRESSING-RELIABLE: {a} {sup}, paired against A0 at 4,096: {s1[a]['paired']['label']}; at 16,384: "
        f"{s2[a]['paired']['label']}")

# ------------------------------------------------------------------ hypothesis readings (at 4,096; row is not 3)
say("\n=== hypotheses (read at 4,096)")
h19a_cells = []
for c in arm_cells(1, "A0"):
    tr = trajectory(c, U)
    ups = [json.loads(x) for x in (c["dir"] / "updates.jsonl").open()]
    win = [u for u in ups if 64 <= u["update"] <= 1024]
    per = [u["grad_norm"]["wq"] / u["grad_norm"]["wo"] for u in win if u["grad_norm"]["wo"] > 0]
    mean_per = sum(per) / len(per)
    ratio_of_means = sum(u["grad_norm"]["wq"] for u in win) / sum(u["grad_norm"]["wo"] for u in win)
    drec = [r for r in diag(c) if 64 <= r["update"] <= 1024]
    diag_ratio = sum(r["gradient_norms_by_loss"]["answer"]["wq"] for r in drec) / sum(r["gradient_norms_by_loss"]["answer"]["wo"] for r in drec)
    h19a_cells.append({"cell": c["label"], "onset": tr["onset"], "updates_in_window": len(win), "mean_ratio": mean_per,
                       "ratio_of_means": ratio_of_means, "diag_ratio_of_means": diag_ratio, "min_per_update_ratio": min(per)})
onset_n = sum(1 for x in h19a_cells if x["onset"] is not None and x["onset"] <= 256)
ratio_n = {k: sum(1 for x in h19a_cells if x[k] <= 0.01) for k in ("mean_ratio", "ratio_of_means", "diag_ratio_of_means")}
for x in h19a_cells:
    say("   H19-A", x)
say(f"H19-A: onset <= 256 in {onset_n}/16; ratio <= 0.01 in {ratio_n} of 16; A0 class {s1['A0']['class']}")
h = {"H19-A": "supported" if onset_n >= 12 and min(ratio_n.values()) >= 12 and s1["A0"]["class"] != "RELIABLE" else "not supported"}


def reading(arm: str, extra: bool = True) -> str:
    v = s1[arm]
    if v["paired"]["label"] == "HARMS":
        return "CONTRADICTED"
    return "supported" if v["class"] == "RELIABLE" and v["paired"]["label"] == "IMPROVES ON A0" and extra else "not supported"


# A2 supervision-dependence (collapse clause only; see below)
a2_sd = []
for c in arm_cells(1, "A2"):
    tr_after = trajectory(c, U, after=U_PRE)
    tr_all = trajectory(c, U)
    a2_sd.append({"cell": c["label"], "after_removal": tr_after["category"], "whole_run": tr_all["category"]})
sd_n = sum(1 for x in a2_sd if x["after_removal"] == "collapsed and not recovered")
sd_whole = sum(1 for x in a2_sd if x["whole_run"] == "collapsed and not recovered")
say(f"A2 SUPERVISION-DEPENDENT collapse clause: after removal {sd_n}/16; whole-run category {sd_whole}/16")
h["H19-B"] = reading("A1", not nc1)
h["H19-C"] = reading("A2", (not nc1) and sd_n * 2 <= 16)
h["H19-D"] = reading("A4")
h["H19-F"] = reading("A5-C")
h["H19-G"] = reading("A5-D")
for arm in LEARNED:
    h[f"H19-E ({arm})"] = "supported" if s1[arm]["class"] == "RELIABLE" else "not supported"
say(json.dumps(h, indent=1))

# ------------------------------------------------------------------ annotations
say("\n=== annotations")
ann: dict = {}
for stage, arms, ro in ((1, LEARNED, U), (2, s2_arms, 4 * U)):
    for arm in arms:
        cs = arm_cells(stage, arm)
        trs = {f"{c['draw']}/{c['j']}": trajectory(c, ro) for c in cs}
        cats: dict[str, int] = {}
        for t in trs.values():
            cats[t["category"]] = cats.get(t["category"], 0) + 1
        esc = [t["escape"] for t in trs.values() if t["escape"] is not None]
        cens = [t["escape"] if t["escape"] is not None else ro for t in trs.values() if t["onset"] is not None or True]
        stab = statistics.median(c["evals"][ro]["panel_statistics"]["address_stability"] for c in cs)
        a = {"categories": cats, "median_escape_escaped_only": statistics.median(esc) if esc else None,
             "median_escape_censored": statistics.median([t["escape"] if t["escape"] is not None else ro for t in trs.values()]),
             "address_stable_median": stab, "address_stable": stab >= 0.80, "trajectories": trs}
        if arm in ("A1", "A2"):
            rec_mean = statistics.median((c["evals"][ro]["panel_statistics"]["target_top8_recall_A"] + c["evals"][ro]["panel_statistics"]["target_top8_recall_B"]) / 2 for c in cs)
            rec_pool = statistics.median([c["evals"][ro]["panel_statistics"][f"target_top8_recall_{p}"] for c in cs for p in "AB"])
            a["address_recall_median_mean_AB"] = rec_mean
            a["address_recall_median_pooled"] = rec_pool
            # attempt 1 used the mean of A and B per cell; the ADR says "on Panels A and B" without saying how the two combine.
            # The run takes the smaller of the two per cell; all three readings are printed and the label is compared for each.
            rec_min = statistics.median(min(c["evals"][ro]["panel_statistics"]["target_top8_recall_A"], c["evals"][ro]["panel_statistics"]["target_top8_recall_B"]) for c in cs)
            a["address_recall_median_min_AB"] = rec_min
            a["address_recall"] = rec_mean >= 0.90 and rec_pool >= 0.90 and rec_min >= 0.90
            a["address_recall_any_reading"] = rec_mean >= 0.90 or rec_pool >= 0.90 or rec_min >= 0.90
        # dense comparison, for RELIABLE arms
        cls = (s1 if stage == 1 else s2)[arm]["class"]
        if cls == "RELIABLE":
            ratios, dense_acc, diffs = [], [], {}
            for dr in sorted({c["draw"] for c in cs}):
                arm_acc = statistics.mean(c["evals"][ro]["panels"]["A"]["accuracy"] for c in cs if c["draw"] == dr)
                a7 = cell(stage, "A7", dr, 0)["evals"][ro]["panels"]["A"]["accuracy"]
                ratios.append(arm_acc / a7)
                dense_acc.append(a7)
                diffs[dr] = arm_acc - a7
            mr, md = statistics.median(ratios), statistics.median(dense_acc)
            a["dense"] = {"median_ratio": mr, "median_dense": md, "diffs": diffs,
                          "label": "BEATS DENSE" if mr >= 1.10 else ("DENSE AT CEILING" if md > 0.909 else "DENSE SUFFICES")}
        ann[f"{stage}/{arm}"] = a
        say(f"S{stage} {arm:5s} cats {cats} esc(escaped) {a['median_escape_escaped_only']} esc(censored) {a['median_escape_censored']} "
            f"stable {stab:.4f} {'ADDRESS STABLE' if a['address_stable'] else '-'} "
            f"{('recall ' + str(a.get('address_recall_median_mean_AB')) + '/' + str(a.get('address_recall_median_pooled'))) if arm in ('A1', 'A2') else ''} "
            f"{a.get('dense', '')}")

# draw sensitivity (section 8.7): table, draw counts, discordance, exact permutation test
say("\n=== draw sensitivity (section 8.7, descriptive)")


def perm_test(table: dict[int, tuple[bool, bool]]) -> tuple[int, float, float]:
    draws = sorted(table)
    outcomes = [o for d in draws for o in table[d]]
    n, s = len(outcomes), sum(outcomes)
    stat = sum(table[d][0] == table[d][1] for d in draws)
    total = 0
    hits = 0
    acc = 0.0
    for succ_pos in combinations(range(n), s):
        sp = set(succ_pos)
        st = sum(((2 * i) in sp) == ((2 * i + 1) in sp) for i in range(len(draws)))
        total += 1
        acc += st
        hits += st >= stat
    return stat, hits / total, acc / total


ds = {}
for stage, arms, ro in ((1, LEARNED, U), (2, s2_arms, 4 * U)):
    for arm in arms:
        v = (s1 if stage == 1 else s2)[arm]
        table: dict[int, list[bool]] = {}
        for k, c in v["cells"].items():
            dr, j = map(int, k.split("/"))
            table.setdefault(dr, [False, False])[j] = c["success"]
        t2 = {d: tuple(x) for d, x in table.items()}
        counts = {"2/2": sum(all(x) for x in t2.values()), "1/2": sum(sum(x) == 1 for x in t2.values()),
                  "0/2": sum(not any(x) for x in t2.values())}
        stat, p, mean = perm_test(t2)
        ds[f"{stage}/{arm}"] = {"counts": counts, "discordance": counts["1/2"] / len(t2), "perm_stat": stat, "perm_p": p, "perm_null_mean": mean}
        say(f"S{stage} {arm:5s} {counts} discordance {counts['1/2'] / len(t2):.3f} permutation stat {stat} p {p:.4f} null mean {mean:.2f}")

# ------------------------------------------------------------------ comparison with the run's printed result
say("\n=== comparison with results.json")
run = load(COM / "results.json")["result"]
disagreements = []


def cmp(name: str, mine: object, theirs: object) -> None:
    same = mine == theirs
    if not same:
        disagreements.append((name, mine, theirs))
    say(f"{'AGREE   ' if same else 'DISAGREE'} {name}: mine={mine} run={theirs}")


for stage, mine in ((1, s1), (2, s2)):
    rs = run[f"stage{stage}"]["arms"]
    for arm, v in mine.items():
        cmp(f"S{stage} {arm} class", v["class"], rs[arm]["class"])
        cmp(f"S{stage} {arm} successes", v["successes"], rs[arm]["counts"]["successes"])
        cmp(f"S{stage} {arm} lm flagged", v["lm_flagged"], rs[arm]["counts"]["lm_flagged_cells"])
        if arm != "A0":
            cmp(f"S{stage} {arm} paired d", v["paired"]["d"], rs[arm]["paired_against_a0"]["d"])
            cmp(f"S{stage} {arm} paired label", v["paired"]["label"], rs[arm]["paired_against_a0"]["label"])
            cmp(f"S{stage} {arm} sign p", round(v["paired"]["p"], 12), round(rs[arm]["paired_against_a0"]["p_value"], 12))
        a = ann[f"{stage}/{arm}"]
        cmp(f"S{stage} {arm} categories", {k: a["categories"].get(k, 0) for k in rs[arm]["categories"]}, rs[arm]["categories"])
        # attempt 1 compared None with the run's string "nan" (no escaped cell); both mean "no escaped cell"
        theirs_esc = rs[arm].get("median_escape_update_escaped_cells_only")
        cmp(f"S{stage} {arm} median escape (escaped only)", a["median_escape_escaped_only"],
            None if theirs_esc in ("nan", None) or theirs_esc != theirs_esc else theirs_esc)
        cmp(f"S{stage} {arm} median escape (censored at readout)", a["median_escape_censored"],
            rs[arm]["draw_sensitivity"]["median_escape_update_censored_at_readout"])
        cmp(f"S{stage} {arm} ADDRESS STABLE median", a["address_stable_median"], rs[arm]["address"]["stable"]["median"])
        if "dense" in a:
            cmp(f"S{stage} {arm} dense label", a["dense"]["label"], rs[arm]["dense_comparison"]["label"])
        dd = ds[f"{stage}/{arm}"]
        rds = rs[arm]["draw_sensitivity"]
        cmp(f"S{stage} {arm} draw counts", dd["counts"], rds["draw_counts"])
        cmp(f"S{stage} {arm} permutation p", round(dd["perm_p"], 12), round(rds["permutation_test"]["p_value"], 12))
        # per-cell success
        run_tab = rds["table"]
        mine_tab = {k: v["cells"][k]["success"] for k in v["cells"]}
        theirs_tab = {f"{d}/{j}": s == "SUCCEEDED" for d, row in run_tab.items() for j, s in row.items()}
        cmp(f"S{stage} {arm} per-cell success table", mine_tab, theirs_tab)
for arm in ("A1", "A2"):
    if f"1/{arm}" in ann:
        cmp(f"S1 {arm} ADDRESS RECALL median (min of A and B per cell)", ann[f"1/{arm}"]["address_recall_median_min_AB"], run["stage1"]["arms"][arm]["address"]["recall"]["median"])
        say(f"   (mean-of-A-and-B reading {ann[f'1/{arm}']['address_recall_median_mean_AB']}, pooled {ann[f'1/{arm}']['address_recall_median_pooled']}; label under every reading: {ann[f'1/{arm}']['address_recall']} / any {ann[f'1/{arm}']['address_recall_any_reading']})")
        cmp(f"S1 {arm} ADDRESS RECALL label", "ADDRESS RECALL" if ann[f"1/{arm}"]["address_recall"] else None, run["stage1"]["arms"][arm]["address"]["recall"]["label"])
for arm in ("A1",):
    cmp(f"S2 {arm} ADDRESS RECALL median (min)", ann[f"2/{arm}"]["address_recall_median_min_AB"], run["stage2"]["arms"][arm]["address"]["recall"]["median"])
cmp("S1 A2 SUPERVISION-DEPENDENT cells", sd_n, run["stage1"]["arms"]["A2"]["supervision_dependent"]["collapse_clause_cells"])
cmp("H19-A onset cells", onset_n, run["stage1"]["h19a_inputs"]["onset_cells"])
cmp("H19-A ratio cells (mean of per-update ratios)", ratio_n["mean_ratio"], run["stage1"]["h19a_inputs"]["ratio_cells"])
for k, v in h.items():
    cmp(f"{k}", v, run["hypotheses"][k]["reading"])
cmp("outcome row", row, run["outcome"]["row"])
cmp("outcome arm", both[0] if both else None, run["outcome"]["arm"])
cmp("carried forward", carry, run["carried_forward"]["arm"])
cmp("Stage 3 label", s3.get("label") if s3 else None, run["stage3"]["label"])
cmp("Stage 3 successes", s3.get("successes") if s3 else None, run["stage3"]["successes"])
cmp("Stage 2 arms", sorted(s2_arms), sorted(load(RAW / "stage_gate_1.json")["arms"]))
cmp("Stage 1 advancing", advance, load(RAW / "stage_gate_1.json")["advancing"])
cmp("NC failed 4096", nc1, run["stage1"]["negative_control_failed"])
cmp("NC failed 16384", nc2, run["stage2"]["negative_control_failed"])
say(f"\nDISAGREEMENTS: {len(disagreements)}")
for d in disagreements:
    say("  ", d)

# borderline list (within 0.005 of a threshold), all learned cells at their deciding readout and Stage 2 U
say("\n=== borderline (|margin| < 0.005)")
border = []
for stage, mine, ro in ((1, s1, U), (2, s2, 4 * U), (2, s2u, U)):
    for arm, v in mine.items():
        for k, c in v["cells"].items():
            others_ok = {"c1_A": c["c2"] and c["c3"] and c["c4"] and c["c5"] and (c["acc_B"] >= 0.9 * c["a6_B"]),
                         "c1_B": c["c2"] and c["c3"] and c["c4"] and c["c5"] and (c["acc_A"] >= 0.9 * c["a6_A"]),
                         "c4_H1": c["c1"] and c["c2"] and c["c3"] and c["c5"] and c["H2"] >= 0.9 * c["acc_A"],
                         "c4_H2": c["c1"] and c["c2"] and c["c3"] and c["c5"] and c["H1"] >= 0.9 * c["acc_A"],
                         "lm": True}
            for m, val in c["margins"].items():
                # attempt 1 listed every margin under 0.005, including cells at chance that fail other conditions anyway;
                # now a margin is listed only when it alone decides the cell (or, for lm, the flag)
                if abs(val) < 0.005 and others_ok[m]:
                    border.append({"stage": stage, "readout": ro, "arm": arm, "cell": k, "threshold": m, "margin": val,
                                   "success": c["success"]})
            if (abs(c["probe_largest_share"] - 0.02) < 0.005 or abs(c["probe_distinct"] - 128) <= 3) and c["c1"] and c["c4"]:
                border.append({"stage": stage, "readout": ro, "arm": arm, "cell": k, "threshold": "c3", "distinct": c["probe_distinct"],
                               "largest_share": c["probe_largest_share"], "success": c["success"]})
for b in border:
    say("  ", b)

out = {"stage1": s1, "stage2": s2, "stage2_at_U": s2u, "stage3": s3, "hypotheses": h, "h19a": h19a_cells, "a2_supervision": a2_sd,
       "annotations": ann, "draw_sensitivity": ds, "row": row, "carry": carry, "disagreements": disagreements, "borderline": border,
       "intervals": INTERVALS}
OUT.write_text(json.dumps(out, indent=1, default=str))
