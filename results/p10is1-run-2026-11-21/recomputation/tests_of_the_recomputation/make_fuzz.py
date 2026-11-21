# ruff: noqa
"""Synthetic five-replicate run directories built from the counting rehearsal's records (draw 1), with seeded perturbations, so that recompute.py and the study's
analysis can be compared on branches one replicate never reaches (counts of 4 and 5, DEP failures, leakage, REF failure, MC disagreement, MC-SHORT).
Usage: python3 make_fuzz.py <rehearsal run dir> <view plan> <rehearsal record> <out dir> <seed>
Ladder cells get G = U0 in the synthetic plan, so the recorded stop (U0) is always the rule's answer within G."""

import json
import random
import sys
from pathlib import Path

run, planp, rehp, out, seed = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5])
rng = random.Random(seed)
plan = json.loads(planp.read_text())
out.mkdir(parents=True, exist_ok=False)
(out / "run" / "evaluate").mkdir(parents=True)
(out / "run" / "baselines").mkdir(parents=True)
(out / "run" / "ladder").mkdir(parents=True)
(out / "run" / "timing").mkdir(parents=True)

# scenario knobs
p_dep = rng.choice([0.0, 0.002, 0.01])        # chance a snapshot panel gets an out-of-chance disabled/shuffled count
p_leak = rng.choice([0.0, 0.0, 0.003])
p_cfail = rng.choice([0.0, 0.01])              # chance of a DEP-c-sized excess
noise = rng.choice([0.0, 0.01, 0.03, 0.08])    # relative noise on useful counts
shift = {arm: rng.uniform(-0.15, 0.15) for arm in ("F-OQ", "T-OQ", "H8", "D-OQ", "R2")}  # per-arm drift of a_use
cpu_scale = {arm: rng.choice([1.0, 1.0, 0.5, 2.0, 0.3, 3.0]) for arm in ("F-OQ", "T-OQ", "H8", "D-OQ", "R2")}
qual_drop = rng.choice([0.0, 0.2])
if seed >= 100:  # mild (also for seeds >= 200) scenarios: the rehearsal's curves nearly unchanged, so the positive branches (CAPACITY STEP, dense labels, FASTER) are reached; costs varied for MC disagreement
    p_dep, p_leak, p_cfail, qual_drop = 0.0, 0.0, 0.0, 0.0
    noise = rng.choice([0.0, 0.002])
    shift = {arm: rng.uniform(-0.02, 0.02) for arm in shift}
    cpu_scale = {arm: rng.choice([1.0, 0.7, 1.4, 0.4, 2.5, 5.0]) for arm in cpu_scale}

cells = []
for c in plan["cells"]:
    for d in range(1, 6):
        lab = c["label"].replace("_d1_", f"_d{d}_")
        c2 = {**c, "draw": d, "label": lab}
        if c["ladder_cell"]:
            c2["run"] = int(c["u0"])
        cells.append(c2)
        src = run / "evaluate" / c["label"]
        dst = out / "run" / "evaluate" / lab
        dst.mkdir()
        rep_shift = shift[c["arm"]] * (0.5 + rng.random()) * (1 if d % 2 else -0.5)
        for p in sorted(src.glob("u*.json")):
            rec = json.loads(p.read_text())
            rec["label"], rec["draw"] = lab, d
            for rn, body in rec["reads"].items():
                for pn, pa in body["panels"].items():
                    n = pa["n"]
                    u0, c0 = pa["useful"], pa["correct"]
                    u1 = int(round(u0 * (1 + rep_shift + rng.gauss(0, noise))))
                    u1 = max(0, min(n, u1))
                    c1 = max(u1, min(n, c0 + (u1 - u0)))
                    if rng.random() < p_cfail:
                        c1 = min(n, c1 + int(0.03 * n))
                    pa["useful"], pa["correct"] = u1, c1
                    if rng.random() < p_dep and pa.get("disabled_correct") is not None:
                        pa["disabled_correct"] = int(n * 0.2)
                    if rng.random() < p_dep and pa.get("shuffled_correct") is not None:
                        pa["shuffled_correct"] = int(n * 0.2)
                    if rng.random() < p_leak:
                        pa["unseen_correct"] = int(pa.get("unseen_n", 2048) * 0.2)
            (dst / p.name).write_text(json.dumps(rec))
for p in sorted((run / "baselines").glob("d1_*.json")):
    r = json.loads(p.read_text())
    for d in range(1, 6):
        r2 = {**r, "draw": d, "no_memory": {k: max(0, v + rng.randint(-8, 8)) for k, v in r["no_memory"].items()}}
        (out / "run" / "baselines" / p.name.replace("d1_", f"d{d}_")).write_text(json.dumps(r2))
for p in sorted((run / "ladder").glob("*.json")):
    r = json.loads(p.read_text())
    if "u_run" in r:
        (out / "run" / "ladder" / p.name).write_text(json.dumps(r))
t = json.loads((run / "timing" / "timing.json").read_text())
if seed >= 200:  # per-(arm, slots) CPU costs: MC-AMBIGUOUS within an arm's step and MC-SHORT (a multiplier above 6)
    t["cpu"] = {k: v * rng.choice([0.3, 0.8, 1.0, 1.25, 3.0, 8.0]) for k, v in t["cpu"].items()}
else:
    t["cpu"] = {k: v * cpu_scale[k.split("|")[0]] for k, v in t["cpu"].items()}
(out / "run" / "timing" / "timing.json").write_text(json.dumps(t))
plan2 = {**plan, "cells": cells}
(out / "plan.json").write_text(json.dumps(plan2))
reh = json.loads(rehp.read_text())
q = reh["qualification"]
for row in q.values():
    for k in row:
        row[k] = [x for x in row[k] if rng.random() >= qual_drop]
(out / "rehearsal.json").write_text(json.dumps({"qualification": q}))
(out / "knobs.json").write_text(json.dumps({"seed": seed, "p_dep": p_dep, "p_leak": p_leak, "p_cfail": p_cfail, "noise": noise, "shift": shift, "cpu_scale": cpu_scale, "qual_drop": qual_drop}))
print(json.dumps({"seed": seed, "cells": len(cells)}))
