"""D1 (auditor, Opus 5.5): projections of ADR-0019 section 10 recomputed from the raw rehearsal records (rehearsal.json and
rehearsal_evaluate.json of each item) with my own code (plain json; no studies.* import). Reproduces projection.json with the
rehearsed (worst-case) values, then recomputes with the calibrated values, stating which rates were measured at the calibrated
setting and which are only upper bounds.

usage: d1_projection_recompute.py REHEARSAL_RUN_DIR CALIBRATION_JSON LEDGER_A_JSON
"""
import itertools
import json
import math
import sys
from pathlib import Path

RUN, CAL, LEDGER = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
U = 8192
rates, evals, peaks = {}, {}, {}
for d in sorted((RUN / "rehearsal").iterdir()):
    t = json.loads((d / "rehearsal.json").read_text())
    e = json.loads((d / "rehearsal_evaluate.json").read_text())
    key = (t["arm"], t["slots"], t["phase"])
    assert t["updates"] == 256 and t["seed_set"] == "rehearsal-5" and t["mode"] == "rehearsal", d
    rates[key] = t["seconds_per_update"]
    evals[key] = e["evaluation_wall_seconds"]
    peaks[key] = max(t["peak_rss_bytes"], t["sampled_rss_bytes"], e["peak_rss_bytes"])
print("items:", len(rates), "peak RSS over train+evaluation records: %.3f GiB" % (max(peaks.values()) / 2**30))


def k_at(t, k0, ta):
    return 8 if t >= ta else max(8, round(k0 * (8 / k0) ** (t / ta)))


def cell_seconds(arm, slots, stage, hyper):
    total = U * (4 if stage == 2 else 1)
    if arm == "A2":
        pre = round(hyper["u_pre"] * (4 if stage == 2 else 1))
        return pre * rates[(arm, slots, "pre")] + (total - pre) * rates[(arm, slots, "post")]
    if arm == "A4":
        ta = total // 2
        return ta * max(rates[(arm, slots, "k0")], rates[(arm, slots, "mid")]) + (total - ta) * rates[(arm, slots, "k8")]
    return total * rates[(arm, slots, "main")]


def eval_seconds(arm, slots, stage):
    phase = {"A2": "post", "A4": "k8"}.get(arm, "main")
    return (2 if stage == 2 else 1) * evals[(arm, slots, phase)]


def rounds(xs, w=6):
    xs = sorted(xs, reverse=True)
    return sum(xs[i] for i in range(0, len(xs), w))


LEARNED = ["A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S"]
ADV = ["A5-C", "A5-D", "A4", "A2", "A1"]


def stage1(h):
    cells = [(a, 4096) for a in LEARNED for _ in range(16)] + [(a, 4096) for a in ("A6", "A7") for _ in range(8)]
    tr = rounds([cell_seconds(a, s, 1, h) for a, s in cells])
    ev = rounds([eval_seconds(a, s, 1) for a, s in cells])
    return tr, ev


def stage2(adv, h):
    arms = ["A0", *adv] + (["A1-S"] if any(a in ("A1", "A2") for a in adv) else [])
    cells = [(a, 16384) for a in arms for _ in range(8)] + [(a, 16384) for a in ("A6", "A7") for _ in range(4)]
    return rounds([cell_seconds(a, s, 2, h) for a, s in cells]), rounds([eval_seconds(a, s, 2) for a, s in cells]), len(cells)


def stage3(sel, h):
    arms = ["A0"] if sel == "A0" else ["A0", sel]
    cells = [(a, 65536) for a in arms + ["A6", "A7"] for _ in range(2)]
    return rounds([cell_seconds(a, s, 3, h) for a, s in cells]), rounds([eval_seconds(a, s, 3) for a, s in cells]), len(cells)


ledger = json.loads(LEDGER.read_text())
charged_a = sum(e["seconds"] for e in ledger["entries"])
print("Budget A charged so far %.1f s; remaining %.1f s" % (charged_a, 14400 - charged_a))
worst = {"lambda": 1.0, "u_pre": 1024.0, "k0_fraction": 1.0, "mu": 1.0}
cal = json.loads(CAL.read_text())["hyper"]
recorded = json.loads((RUN / "projection.json").read_text())
for name, h in (("rehearsed (worst-case grid values)", worst), ("calibrated values, A4 annealing at the measured k0 = N rate (UPPER BOUND: k0 = N/8 never rehearsed)", cal)):
    print(f"\n=== {name}: {h}")
    tr, ev = stage1(h)
    print(f"Stage 1: training {tr:.1f} s + evaluation {ev:.1f} s = {tr + ev:.1f} s; doubled {2 * (tr + ev):.1f} s; fits Budget A remainder: {2 * (tr + ev) <= 14400 - charged_a}")
    if h is worst:
        print("   projection.json Stage 1 total:", round(recorded["stage1"]["projection"]["total_seconds"], 1))
    for adv in [(), *[(a,) for a in ADV], *itertools.combinations(ADV, 2)]:
        tr2, ev2, n = stage2(adv, h)
        key = "+".join(adv) if adv else "A0-only"
        rec = recorded["stage2_table"][key]["total_seconds"] if h is worst else None
        print(f"Stage 2 {key:10s} {n:2d} cells: {tr2 + ev2:8.1f} s, doubled {2 * (tr2 + ev2):8.1f} s, fits 10,800 s: {2 * (tr2 + ev2) <= 10800}" + (f"   (projection.json {rec:.1f})" if rec is not None else ""))
    for sel in ("A0", "A1", "A5-C", "A5-D"):
        tr3, ev3, n = stage3(sel, h)
        print(f"Stage 3 {sel:5s} {n} cells: {tr3 + ev3:7.1f} s, doubled {2 * (tr3 + ev3):7.1f} s")
print("\nA4 rates measured (s/update): ", {k: round(v, 5) for k, v in rates.items() if k[0] == "A4"})
print("A4 read widths of the REHEARSED phases at 16,384: k0 =", 16384, " mid =", k_at(16384 // 2 // 2, 16384, 16384 // 2), "| of the CALIBRATED matrix: k0 =", 2048, " mid =", k_at(16384 // 2 // 2, 2048, 16384 // 2))
print("A4 read widths at 4,096: rehearsed k0 = 4096, mid =", k_at(2048, 4096, 4096), "| calibrated k0 = 512, mid =", k_at(2048, 512, 4096))
# what the A4 annealing rate at 16,384 must not exceed for the largest A4 configuration to fit 2x within Budget B
for adv in (("A4",), ("A5-C", "A4"), ("A4", "A2"), ("A4", "A1")):
    lo, hi = rates[("A4", 16384, "k8")], 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        saved = rates[("A4", 16384, "k0")], rates[("A4", 16384, "mid")]
        rates[("A4", 16384, "k0")] = rates[("A4", 16384, "mid")] = mid
        tr2, ev2, _ = stage2(adv, cal)
        rates[("A4", 16384, "k0")], rates[("A4", 16384, "mid")] = saved
        lo, hi = (mid, hi) if 2 * (tr2 + ev2) <= 10800 else (lo, mid)
    print(f"largest A4 annealing rate (s/update at 16,384) with which Stage 2 {'+'.join(adv)} fits 2x in 10,800 s: {lo:.4f}")
