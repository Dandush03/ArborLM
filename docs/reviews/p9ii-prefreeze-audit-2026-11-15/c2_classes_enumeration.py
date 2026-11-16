"""C2 (auditor, Opus 5.5): ADR-0019 rev 4 sections 8.3-8.6 re-implemented here from the ADR text (cell success from verdict
tables, arm class, paired rule, negative control, Stage 1 gate, Stage 3 gate, outcome rows 2-8, hypothesis readings B-G and E,
carry-forward) and compared with studies.p9ii.classes on random Stage 1 / Stage 2 tables. Also: the success conditions of
section 8.3 against cell_verdict on random observations, and the 8.7 estimators (Clopper-Pearson, permutation test by brute
force, sign test) against direct computations.

usage: c2_classes_enumeration.py N_TABLES SEED
"""
import itertools
import json
import math
import random
import sys
from pathlib import Path

from studies.p9ii import classes as C
from studies.p9ii import core

N, SEED = int(sys.argv[1]), int(sys.argv[2])
rng = random.Random(SEED)
LEARNED = ["A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S"]
LABEL_FREE = ["A0", "A4", "A5-C", "A5-D"]
SUP = ["A1", "A2"]
ADV = ["A5-C", "A5-D", "A4", "A2", "A1"]
CARRY = ["A0", "A5-C", "A5-D", "A4", "A2", "A1"]


# ---------------- my rules ----------------
def my_class(cells, stage):  # cells: dict key -> (status, lm_flag); status in S, F, N
    ev = {k: v for k, v in cells.items() if v[0] != "N"}
    s = sum(1 for v in ev.values() if v[0] == "S")
    f = len(ev) - s
    flagged = sum(1 for v in ev.values() if v[1])
    reduced = flagged > 1
    if len(ev) < {1: 14, 2: 7}[stage]:
        return "NOT_EVALUATED", reduced
    if f <= 1 and not reduced:
        return "RELIABLE", reduced
    if s >= {1: 4, 2: 2}[stage]:
        return "UNRELIABLE", reduced
    return "FAILS", reduced


def my_paired(x, a0):
    keys = [k for k in x if k in a0 and x[k][0] != "N" and a0[k][0] != "N"]
    b = sum(1 for k in keys if x[k][0] == "S" and a0[k][0] == "F")
    c = sum(1 for k in keys if a0[k][0] == "S" and x[k][0] == "F")
    d = b - c
    xs = sum(1 for k in keys if x[k][0] == "S")
    a0s = sum(1 for k in keys if a0[k][0] == "S")
    if d >= 4 and xs > a0s:
        return "IMPROVES ON A0", d
    if d <= -4:
        return "HARMS", d
    return "NOT DISTINGUISHED FROM A0", d


def my_size(tables, stage):
    cls = {a: my_class(tables[a], stage)[0] for a in tables}
    paired = {a: my_paired(tables[a], tables["A0"])[0] for a in tables if a != "A0"}
    nc = "A1-S" in tables and (paired["A1-S"] == "IMPROVES ON A0" or cls["A1-S"] == "RELIABLE")
    return cls, paired, nc


def my_gate1(cls, nc):
    elig = [a for a in ADV if cls.get(a) == "RELIABLE" and not (nc and a in SUP)]
    run = cls.get("A0") == "RELIABLE" or bool(elig)
    return run, elig[:2] if run else []


def my_gate3(cls2, nc2):
    for a in CARRY:
        if cls2.get(a) == "RELIABLE" and not (nc2 and a in SUP):
            return (a, "not run") if a in ("A2", "A4") else (a, "run")
    return (None, "not run")


def my_outcome(c1, nc1, c2, nc2, s2status):
    if c1["A0"] == "NOT_EVALUATED":
        return 2, None
    if nc1 and not any(c1.get(a) == "RELIABLE" for a in LABEL_FREE):
        return 2, None
    if c1["A0"] == "RELIABLE":
        return 3, "A0"
    cand = [a for a in CARRY[1:] if c1.get(a) == "RELIABLE" and not (nc1 and a in SUP)]
    if cand:
        if s2status == "COMPLETE":
            both = [a for a in cand if c2 is not None and c2.get(a) == "RELIABLE" and not (nc2 and a in SUP)]
            if both:
                return 4, both[0]
            return 5, cand[0]
        return 6, cand[0]
    if any(c1.get(a) == "UNRELIABLE" for a in LEARNED if a != "A1-S"):
        return 7, None
    return 8, None


def my_readings(c, paired, nc, supdep):
    def r(arm, extra=True):
        p = paired.get(arm)
        if p == "HARMS":
            return "CONTRADICTED"
        return "supported" if c.get(arm) == "RELIABLE" and p == "IMPROVES ON A0" and extra else "not supported"
    return {"H19-B": r("A1", not nc), "H19-C": r("A2", not nc and not supdep), "H19-D": r("A4"), "H19-F": r("A5-C"), "H19-G": r("A5-D")}


# ---------------- random tables ----------------
def table(stage, arms, draws, ne_draws):
    out = {}
    for a in arms:
        mode = rng.choice([0.0, 0.25, 0.5, 0.9, 0.97, 1.0])
        lmrate = rng.choice([0.0, 0.0, 0.1, 0.3])
        cells = {}
        for d in draws:
            for j in (0, 1):
                if d in ne_draws:
                    cells[(d, j)] = ("N", False)
                else:
                    cells[(d, j)] = ("S" if rng.random() < mode else "F", rng.random() < lmrate)
        out[a] = cells
    # correlate some arms with A0 to exercise the paired rule
    for a in arms:
        if a != "A0" and rng.random() < 0.3:
            out[a] = {k: (out["A0"][k][0] if rng.random() < 0.8 else ("S" if out["A0"][k][0] == "F" else out["A0"][k][0]), v[1]) for k, v in out[a].items()}
    return out


def to_verdicts(cells):
    m = {"S": C.SUCCEEDED, "F": C.FAILED, "N": C.CELL_NOT_EVALUATED}
    return {k: C.CellVerdict(m[s], (), lm) for k, (s, lm) in cells.items()}


def theirs_size(tables, stage):
    v = {a: to_verdicts(t) for a, t in tables.items()}
    classes = {a: C.arm_class(a, stage, v[a], list(v[a])) for a in v}
    paired = {a: C.paired_against_a0(a, v[a], v["A0"]) for a in v if a != "A0"}
    nc = C.negative_control_failed(classes.get("A1-S"), paired.get("A1-S"))
    return C.SizeAnalysis(stage, classes, paired, nc)


mism = {"class": 0, "paired": 0, "nc": 0, "gate1": 0, "gate3": 0, "outcome": 0, "readings": 0, "carry": 0, "label_lm": 0}
examples = {}
counts = {"rows": {}, "gate1_run": 0, "gate3_run": 0, "gate3_sched": 0, "nc1": 0}
for it in range(N):
    ne1 = set(rng.sample(range(1, 9), rng.choice([0, 0, 0, 0, 1, 2])))
    t1 = table(1, LEARNED, range(1, 9), ne1)
    c1, p1, nc1 = my_size(t1, 1)
    s1 = theirs_size(t1, 1)
    for a in LEARNED:
        if s1.classes[a].cls != c1[a]:
            mism["class"] += 1
            examples.setdefault("class", (a, t1[a]))
        if s1.classes[a].lm_reduced and s1.classes[a].cls == "UNRELIABLE" and s1.classes[a].failures <= 1 and s1.classes[a].label != C.UNRELIABLE_LM:
            mism["label_lm"] += 1
        if a != "A0" and s1.paired[a].label != p1[a]:
            mism["paired"] += 1
    if s1.negative_control_failed != nc1:
        mism["nc"] += 1
    counts["nc1"] += int(nc1)
    g = C.stage1_gate(s1.classes, s1.negative_control_failed)
    run, adv = my_gate1(c1, nc1)
    if (g.run, list(g.advancing)) != (run, adv):
        mism["gate1"] += 1
        examples.setdefault("gate1", (c1, nc1, g))
    counts["gate1_run"] += int(run)
    c2 = nc2 = s2 = None
    s2status = rng.choice(["COMPLETE", "COMPLETE", "COMPLETE", "NOT RUN — BUDGET", "INCOMPLETE"]) if run else "NOT RUN — NO ARM PASSED"
    if run and s2status != "NOT RUN — BUDGET":
        arms2 = core.stage2_arms(adv)
        ne2 = set(rng.sample(range(9, 13), rng.choice([0, 0, 0, 1])))
        t2 = table(2, arms2, range(9, 13), ne2)
        c2, p2, nc2 = my_size(t2, 2)
        s2 = theirs_size(t2, 2)
        for a in arms2:
            if s2.classes[a].cls != c2[a]:
                mism["class"] += 1
        if s2.negative_control_failed != nc2:
            mism["nc"] += 1
        if s2status == "COMPLETE":
            sel, act, st = C.stage3_gate(s2.classes, s2.negative_control_failed, C.COMPLETE)
            msel, mact = my_gate3(c2, nc2)
            if (sel, act) != (msel, mact):
                mism["gate3"] += 1
                examples.setdefault("gate3", (c2, nc2, sel, act))
            counts["gate3_run"] += int(mact == "run")
            counts["gate3_sched"] += int(msel in ("A2", "A4"))
            carried = C.carry_forward(s2)
            mine_c = next((a for a in CARRY if c2.get(a) == "RELIABLE" and not (nc2 and a in SUP)), None)
            if carried != mine_c:
                mism["carry"] += 1
    o = C.study_outcome(s1, s2, s2status)
    mrow, marm = my_outcome(c1, nc1, c2, nc2, s2status)
    if (o.row, o.arm) != (mrow, marm):
        mism["outcome"] += 1
        examples.setdefault("outcome", (c1, nc1, c2, nc2, s2status, o.row, o.arm, mrow, marm))
    counts["rows"][mrow] = counts["rows"].get(mrow, 0) + 1
    # readings at Stage 1 (rows other than 3)
    supdep = rng.random() < 0.3
    s1.supervision_dependent["A2"] = supdep
    rd = C.hypothesis_readings(s1, {"onset_cells": 12, "ratio_cells": 12})
    mr = my_readings(c1, p1, nc1, supdep)
    if any(rd[k]["reading"] != mr[k] for k in mr):
        mism["readings"] += 1
        examples.setdefault("readings", ({k: rd[k]["reading"] for k in mr}, mr))

# ---------------- section 8.3 on random observations ----------------
cell_mism = 0
for it in range(20000):
    a6 = C.A6Reference(rng.choice([0.85, 0.9, 0.95, 1.0]), rng.choice([0.88, 0.9, 1.0]), rng.uniform(0.1, 0.2))
    acc_a, acc_b = rng.uniform(0.7, 1.0), rng.uniform(0.7, 1.0)
    o = C.Observation(acc_a, acc_b, rng.random() < 0.9, rng.random() < 0.9, rng.uniform(0.7, 1.0), rng.uniform(0.7, 1.0), rng.random() < 0.05, rng.choice([100, 127, 128, 129, 256]), rng.choice([0.0195, 0.02, 0.0205, 0.005]), 256, rng.uniform(0.0, 0.4))
    v = C.cell_verdict(o, a6)
    if not (a6.acc_a >= 0.9 and a6.acc_b >= 0.9):
        mine = "N"
    else:
        c1_ = o.acc_a >= 0.9 * a6.acc_a and o.acc_b >= 0.9 * a6.acc_b
        c2_ = o.dep_chance_a and o.dep_chance_b
        c3_ = o.distinct_top1 >= 128 and o.largest_share <= 0.02
        c4_ = min(o.h1, o.h2) >= 0.9 * o.acc_a and min(o.h1, o.h2) >= 0.9 * o.acc_b
        c5_ = not o.leakage
        mine = "S" if (c1_ and c2_ and c3_ and c4_ and c5_) else "F"
    theirs = {"SUCCEEDED": "S", "FAILED": "F", "NOT_EVALUATED": "N"}[v.status]
    lm_mine = o.lm_rise > a6.lm_rise + 0.05
    if mine != theirs or (mine != "N" and v.lm_flagged != lm_mine):
        cell_mism += 1

# ---------------- 8.7 estimators ----------------
est = {}
est["cp_lower_8_of_8"] = C.clopper_pearson_lower(8, 8)
est["cp_lower_7_of_8"] = C.clopper_pearson_lower(7, 8)
est["cp_lower_4_of_4"] = C.clopper_pearson_lower(4, 4)
est["cp_lower_16_of_16_cells"] = C.clopper_pearson_lower(16, 16)
est["direct_8_of_8"] = 0.05 ** (1 / 8)
est["direct_4_of_4"] = 0.05 ** (1 / 4)
perm_bad = 0
for it in range(300):
    d = rng.randint(1, 6)
    per = [rng.choice([0, 1, 2]) for _ in range(d)]
    res = C.permutation_test_clustering(per)
    s = sum(per)
    obs = sum(1 for v in per if v != 1)
    tot = ge = 0
    for combo in itertools.combinations(range(2 * d), s):
        x = [0] * (2 * d)
        for i in combo:
            x[i] = 1
        stat = sum(1 for k in range(d) if x[2 * k] == x[2 * k + 1])
        tot += 1
        ge += stat >= obs
    if abs(res["p_value"] - ge / tot) > 1e-12:
        perm_bad += 1
sign_bad = 0
for b in range(0, 12):
    for c in range(0, 12):
        n = b + c
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
        sign_bad += abs(C.sign_test_p(b, c) - p) > 1e-12
summary = {"tables": N, "seed": SEED, "mismatches": mism, "examples": {k: str(v)[:800] for k, v in examples.items()}, "coverage": counts, "cell_verdict_mismatches_of_20000": cell_mism, "estimators": est, "permutation_test_mismatches_of_300": perm_bad, "sign_test_mismatches": sign_bad}
print(json.dumps(summary, indent=1))
Path(__file__).parent.joinpath("outputs", f"c2_classes_enumeration_{SEED}.json").write_text(json.dumps(summary, indent=1))
