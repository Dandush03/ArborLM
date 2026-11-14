"""A5 (auditor, Opus 5.5): section I.8 re-implemented from the ADR text and compared with
studies.p9i.classes.analyze_classes on random and structured synthetic measurement tables.

Readings of the auditor where the ADR is silent are marked AUD; where they differ from the
implementer's, the comparison is made both ways and the cases that differ are counted.
"""
import itertools
import math
import random
from collections import Counter

from studies.p9i import classes as C
from studies.p9i import core

SIZES = (4096, 16384, 65536)
P1, P2 = (101, 301), (102, 302)
SEEDS, PANELS = (1801, 1802), ("A", "B")
CH = {4096: 96 / 2048, 16384: 318 / 8192, 65536: 1147 / 32768}  # upper ends of the G2 intervals (draw 1 numbers)
ARMS_AT = {16384: ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7", "BB", "BB-D", "BB-0"),
           65536: ("N", "W7", "A4", "R1", "D7", "BB", "BB-D", "BB-0"),
           4096: ("N", "W7", "A4", "R1", "BB", "BB-0")}
REPL = ("W7", "A4", "R1", "D7", "BB")


def aud_raw(acc, dep, chance, r1, not_eval):
    if not_eval:
        return "NOT_EVALUATED"
    eta = acc / r1 if r1 > 0 else (math.inf if acc > 0 else 0.0)
    if acc >= 0.5 and eta >= 0.90 and dep:
        return "WORKS"
    if acc > chance and acc >= 0.25:
        return "PARTIAL"
    return "FAILS"


def aud(table, lm):
    out = {"classes": {}, "dense": {}, "contrast": {}}
    status = {}
    for s in SIZES:
        if any(table[("R1", s, P1, sd, p)][0] < 0.5 for sd in SEEDS for p in PANELS):
            status[s] = "NOT_EVALUATED"
    for arm in ("N", "W7", "E7", "A4", "A4E", "BB"):
        for s in SIZES:
            if arm not in ARMS_AT[s]:
                continue
            raws = {(sd, p): aud_raw(table[(arm, s, P1, sd, p)][0], table[(arm, s, P1, sd, p)][1], CH[s], table[("R1", s, P1, sd, p)][0], s in status) for sd in SEEDS for p in PANELS}
            if "NOT_EVALUATED" in raws.values():
                cls = "NOT_EVALUATED"
            elif any(raws[(sd, "A")] != raws[(sd, "B")] for sd in SEEDS):
                cls = "NOT REPLICATED"
            elif raws[(SEEDS[0], "A")] != raws[(SEEDS[1], "A")]:
                cls = "INTERMEDIATE"
            else:
                cls = "INTERFACE_" + raws[(SEEDS[0], "A")]
            if s == 16384 and arm in REPL and cls == "INTERFACE_WORKS":
                b102 = [aud_raw(table[(arm, s, P2, 1801, p)][0], table[(arm, s, P2, 1801, p)][1], CH[s], table[("R1", s, P2, 1801, p)][0], False) for p in PANELS]
                if "FAILS" in b102:
                    cls = "INTERMEDIATE"
            if arm == "BB" and cls == "INTERFACE_WORKS" and any(table[("BB-0", s, P1, sd, p)][0] > CH[s] for sd in SEEDS for p in PANELS):
                cls = "MODEL_STORES_FACTS"
            out["classes"][(arm, s)] = cls
            dense = {"W7": "D7", "BB": "BB-D"}.get(arm)
            if dense and dense in ARMS_AT[s]:
                if cls in ("INTERFACE_WORKS", "INTERFACE_PARTIAL"):
                    rs = []
                    for sd in SEEDS:
                        for p in PANELS:
                            a, d = table[(arm, s, P1, sd, p)][0], table[(dense, s, P1, sd, p)][0]
                            rs.append(a / d if d > 0 else (math.inf if a > 0 else 1.0))  # AUD: same 0-handling as implementer
                    out["dense"][(arm, s)] = "BEATS DENSE" if min(rs) >= 1.10 else "DENSE SUFFICES"
                else:
                    out["dense"][(arm, s)] = "NOT COMPARED"
            elif arm in ("A4", "A4E", "N", "E7"):
                out["dense"][(arm, s)] = "NOT COMPARED"
    for emb, st in (("E7", "W7"), ("A4E", "A4")):
        if out["classes"].get((emb, 16384)) == "INTERFACE_FAILS" and out["classes"].get((st, 16384)) == "INTERFACE_FAILS":
            out["contrast"][f"{emb}/{st}"] = None
            continue
        rs = []
        for sd in SEEDS:
            for p in PANELS:
                e, a = table[(emb, 16384, P1, sd, p)][0], table[(st, 16384, P1, sd, p)][0]
                rs.append(e / a if a > 0 else (math.inf if e > 0 else 1.0))
        if all(r >= 1.03 for r in rs):
            lab = "BACKBONE HURTS ADDRESSING"
        elif all(r >= 0.97 for r in rs):
            lab = "BACKBONE ADDS NOTHING"
        elif all(r < 0.97 for r in rs):
            lab = "BACKBONE CONTRIBUTES"
        else:
            lab = "BACKBONE CONTRAST MIXED"
        out["contrast"][f"{emb}/{st}"] = lab
    if status:
        out["selection"] = ("INCONCLUSIVE", 0)
    else:
        for step, arm in ((1, "BB"), (2, "A4"), (3, "W7")):
            if all(out["classes"].get((arm, s)) == "INTERFACE_WORKS" for s in SIZES):
                out["selection"] = (arm, step)
                break
        else:
            out["selection"] = ("NO_INTERFACE_SELECTED", 4)
    return out


def theirs(table, lm):
    t = {k: C.Measure(acc, CH[k[1]], dep) for k, (acc, dep) in table.items()}
    res = C.analyze_classes(t, lm, {})
    out = {"classes": {}, "dense": {}, "contrast": {}}
    for arm, per in res["classes"].items():
        for s, cls in per.items():
            out["classes"][(arm, int(s))] = cls
    for arm, per in res["annotations"].items():
        for s, note in per.items():
            if "dense_comparison" in note:
                out["dense"][(arm, int(s))] = note["dense_comparison"]["label"]
    for pair, c in res["backbone_contrast"].items():
        out["contrast"][pair] = None if c is None else c["label"]
    out["selection"] = (res["selection"]["outcome"], res["selection"]["step"])
    return out


def random_table(rng, regime):
    vals = [0.0, 0.02, 0.04, 0.05, 0.2, 0.249, 0.25, 0.26, 0.45, 0.4999, 0.5, 0.55, 0.8, 0.9, 0.95, 1.0]
    r1vals = [0.49, 0.5, 0.52, 0.6, 0.9, 1.0] if regime == "mixed" else [0.55, 1.0]
    table = {}
    base = {a: rng.choice(vals) for a in ("N", "W7", "E7", "A4", "A4E", "D", "D7", "BB", "BB-D", "BB-0")}
    for s in SIZES:
        for arm in ARMS_AT[s]:
            parents = [(P1, sd) for sd in SEEDS] + ([(P2, 1801)] if s == 16384 and arm in REPL else [])
            for par, sd in parents:
                for p in PANELS:
                    if arm == "R1":
                        acc = rng.choice(r1vals)
                    elif arm == "R2":
                        acc = 1.0
                    else:  # correlated across seeds/panels so that agreeing classes are common
                        acc = base[arm] if rng.random() < 0.85 else rng.choice(vals)
                    table[(arm, s, par, sd, p)] = (acc, rng.random() < 0.9)
    return table


rng = random.Random(900001)
diffs = Counter()
seen = Counter()
examples = []
N = 20000
for i in range(N):
    tab = random_table(rng, "mixed" if i % 4 == 0 else "ok")
    a, b = aud(tab, {}), theirs(tab, {})
    for k in ("classes", "dense", "contrast"):
        keys = set(a[k]) | set(b[k])
        for key in keys:
            seen[(k, a[k].get(key))] += 1
            if a[k].get(key) != b[k].get(key):
                diffs[(k, str(key), a[k].get(key), b[k].get(key))] += 1
                if len(examples) < 5:
                    examples.append((k, key, a[k].get(key), b[k].get(key)))
    seen[("selection", a["selection"])] += 1
    if a["selection"] != b["selection"]:
        diffs[("selection", a["selection"], b["selection"])] += 1
print(f"{N} random tables; disagreements: {sum(diffs.values())}")
for d, n in diffs.most_common(20):
    print("  DIFF", n, d)
print("examples:", examples)
print("outcomes exercised:")
for k, n in sorted(seen.items(), key=lambda x: (x[0][0], str(x[0][1]))):
    print(f"  {k[0]:9} {k[1]!s:28} {n}")

# structured edge cases ------------------------------------------------------------------------------
def all_ok():
    tab = {}
    for s in SIZES:
        for arm in ARMS_AT[s]:
            for par, sd in [(P1, 1801), (P1, 1802)] + ([(P2, 1801)] if s == 16384 and arm in REPL else []):
                for p in PANELS:
                    tab[(arm, s, par, sd, p)] = ({"R1": 1.0, "R2": 1.0, "BB-0": 0.03, "D": 0.03, "D7": 0.5, "BB-D": 0.5}.get(arm, 0.95), True)
    return tab

t = all_ok()
print("\nall interfaces work, dense 0.5, BB-0 at chance:", theirs(t, {})["selection"], aud(t, {})["selection"])
t = all_ok(); t[("BB-0", 4096, P1, 1802, "B")] = (0.2, True)
print("BB-0 above chance at 4096 on one seed/panel -> BB", theirs(t, {})["classes"][("BB", 4096)], "selection", theirs(t, {})["selection"])
t = all_ok(); t[("BB", 16384, P2, 1801, "A")] = (0.03, True)
print("BB B102 FAILS on panel A ->", theirs(t, {})["classes"][("BB", 16384)], theirs(t, {})["selection"])
t = all_ok(); t[("A4", 16384, P2, 1801, "B")] = (0.3, True)
print("A4 B102 PARTIAL (not FAILS) ->", theirs(t, {})["classes"][("A4", 16384)])
t = all_ok(); t[("R1", 65536, P1, 1801, "A")] = (0.4999, True)
print("R1 0.4999 at 65536 ->", theirs(t, {})["selection"], theirs(t, {})["classes"][("BB", 65536)])
t = all_ok(); t[("R1", 16384, P2, 1801, "A")] = (0.2, True)
print("B102 R1 at 0.2 (B102 not NOT_EVALUATED per 15.4.5): W7 B102 eta = 4.75 ->", theirs(t, {})["classes"][("W7", 16384)])
# missing BB-0 cell: MODEL_STORES_FACTS cannot be checked
t = all_ok(); t[("BB-0", 4096, P1, 1801, "A")] = (0.5, True)
t2 = dict(t); del t2[("BB-0", 4096, P1, 1801, "A")]
print("BB-0 above chance present ->", theirs(t, {})["classes"][("BB", 4096)], "| same cell missing ->", theirs(t2, {})["classes"][("BB", 4096)], theirs(t2, {})["selection"])
# missing BB cells entirely at 65536: selection falls through to A4
t3 = {k: v for k, v in all_ok().items() if not (k[0] == "BB" and k[1] == 65536 and k[3] == 1802)}
print("one BB seed missing at 65536 ->", theirs(t3, {})["selection"])
# missing B102 replicate of A4 while B102 would FAIL
t4 = all_ok(); t4[("A4", 16384, P2, 1801, "A")] = (0.03, True)
t5 = {k: v for k, v in t4.items() if not (k[0] == "A4" and k[2] == P2)}
print("A4 B102 FAILS ->", theirs(t4, {})["classes"][("A4", 16384)], "| A4 B102 missing ->", theirs(t5, {})["classes"][("A4", 16384)])
# both arms of a backbone pair at 0 on one seed/panel
t6 = all_ok(); t6[("E7", 16384, P1, 1801, "A")] = (0.0, True); t6[("W7", 16384, P1, 1801, "A")] = (0.0, True)
print("E7 = W7 = 0 on one pair:", theirs(t6, {})["contrast"])
# eta exactly 0.90
t7 = all_ok()
for sd in SEEDS:
    for p in PANELS:
        t7[("W7", 4096, P1, sd, p)] = (0.9, True)
print("eta exactly 0.9 (0.9 / 1.0) ->", theirs(t7, {})["classes"][("W7", 4096)])
for sd in SEEDS:
    for p in PANELS:
        t7[("W7", 4096, P1, sd, p)] = (0.45, True); t7[("R1", 4096, P1, sd, p)] = (0.5, True)
print("eta = 0.45/0.5 with acc 0.45 ->", theirs(t7, {})["classes"][("W7", 4096)], "(acc < 0.5 so PARTIAL expected)")
print("0.45/0.5 >= 0.9 in floating point:", 0.45 / 0.5 >= 0.9, "| 0.54/0.6:", 0.54 / 0.6, 0.54 / 0.6 >= 0.9)
