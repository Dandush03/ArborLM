"""Re-check auditor C: the six warning annotations under the ruling "printed if they hold in ANY replicate or order", my
implementation against analysis.annotations on random records. Seeds 229701.. (test range).
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval. Usage: <python> check_annotations.py <pin> <trials>"""

import math
import random
import sys
from collections import Counter
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402

import check_edges_v2_lib as E  # noqa: E402

rng = random.Random(229701)
S0, T = 0.1, 0.9
VALS = [0.3, 0.5, 0.6, 0.66, 0.69, 0.7, 0.72, 0.75, 0.8, 0.85, 0.9, "nan", None]


def num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) or x == "nan" else float(x)


def G(x):
    x = num(x)
    return None if x is None else (x - S0) / (T - S0)


def within(a, b):
    a, b = num(a), num(b)
    return None if a is None or b is None else a >= b - 0.03


def any3(xs):
    return True if any(x is True for x in xs) else (None if any(x is None for x in xs) else False)


def all3(xs):
    return None if any(x is None for x in xs) else all(xs)


def mine(n, maf, lsep, ret, gold, st1, mj, em, em_s0, em_t):
    out = {}
    out["NO ADVANTAGE OVER SEPARATE ADAPTERS"] = any3([all3([within(lsep[r][c], maf[(r, o)][c]) for c in "AB"]) for r in range(n) for o in ("AB", "BA")])
    out["RETRIEVAL SUFFICES"] = any3([any3([all3([within(ret[r][c][nm], maf[(r, o)][c]) for c in "AB"]) for nm in ("R-icl", "R-nn")]) for r in range(n) for o in ("AB", "BA")])
    out["LEXICON-EQUIVALENT"] = any3([all3([within(ret[r][c]["R-gloss"], maf[(r, o)][c]) for c in "AB"]) for r in range(n) for o in ("AB", "BA")])
    out["TEACHER-EQUIVALENT-TO-GOLD (both capabilities)"] = any3([all3([None if G(gold[r][c]) is None or G(st1[r][c]) is None else G(gold[r][c]) >= G(st1[r][c]) - 0.03 for c in "AB"]) for r in range(n)])
    out["TEACHER-EQUIVALENT-TO-GOLD (either capability)"] = any3([None if G(gold[r][c]) is None or G(st1[r][c]) is None else G(gold[r][c]) >= G(st1[r][c]) - 0.03 for r in range(n) for c in "AB"])
    out["BELOW JOINT BOUND"] = any3([any3([None if G(maf[(r, o)][c]) is None or G(mj[r][c]) is None else G(maf[(r, o)][c]) < 0.9 * G(mj[r][c]) for c in "AB"]) for r in range(n) for o in ("AB", "BA")])
    em_v = []
    for r in range(n):
        for o in ("AB", "BA"):
            res = []
            for c in "AB":
                a, s0, t = num(em[(r, o)][c]), em_s0[c], em_t[c]
                res.append(None if a is None or t - s0 < 0.30 else (a - s0) / (t - s0) < 0.10)
            em_v.append(any3(res))
    out["EXACT-MATCH WEAK"] = any3(em_v)
    return out


trials = int(sys.argv[2])
mism = Counter()
seen = Counter()
for t in range(trials):
    st = E.build()
    n = 3
    maf = {(r, o): {c: rng.choice(VALS[:-1]) for c in "AB"} for r in range(n) for o in ("AB", "BA")}
    em = {(r, o): {c: rng.choice([0.0, 0.05, 0.1, 0.2, 0.4, "nan"]) for c in "AB"} for r in range(n) for o in ("AB", "BA")}
    lsep = {r: {c: rng.choice(VALS[:-1]) for c in "AB"} for r in range(n)}
    ret = {r: {c: {nm: rng.choice(VALS) for nm in ("R-icl", "R-nn", "R-gloss")} for c in "AB"} for r in range(n)}
    gold = {r: {c: rng.choice(VALS[:-1]) for c in "AB"} for r in range(n)}
    st1 = {r: {c: rng.choice(VALS[:-1]) for c in "AB"} for r in range(n)}
    mj = {r: {c: rng.choice(VALS[:-1]) for c in "AB"} for r in range(n)}
    em_s0 = {c: 0.0 for c in "AB"}
    em_t = {c: rng.choice([0.2, 0.35, 0.6]) for c in "AB"}
    for c in "AB":
        st["baseline"]["student"]["E_" + c]["panel"]["exact_rate"] = em_s0[c]
        st["baseline"]["teacher"]["E_" + c]["exact_rate"] = em_t[c]
    for r in range(n):
        rep = st["replicates"][r]
        for o in ("AB", "BA"):
            sn = rep["cells"][f"r{r}/MAF/{o}"]["scores"][f"r{r}/MAF/{o}"]
            for c in "AB":
                sn["panels"]["E_" + c]["mean"] = maf[(r, o)][c]
                sn["panels"]["E_" + c]["exact_rate"] = em[(r, o)][c]
        for c, o in (("A", "AB"), ("B", "BA")):
            rep["cells"][f"r{r}/ST1/{o}"]["scores"][f"r{r}/ST1/{o}"]["panels"]["E_" + c]["mean"] = st1[r][c]
            rep["cells"][f"r{r}/MAGOLD/{c}"]["scores"][f"r{r}/MAGOLD/{c}"]["panels"]["E_" + c]["mean"] = gold[r][c]
        for c in "AB":
            rep["cells"][f"r{r}/MJOINT/-"]["scores"][f"r{r}/MJOINT/-"]["panels"]["E_" + c]["mean"] = mj[r][c]
            rep["assembled"]["L-sep"]["E_" + c] = {"mean": lsep[r][c]}
        rep["retrieval"] = {c: {nm: ({"mean": v} if v is not None else None) for nm, v in ret[r][c].items()} for c in "AB"}
    got, _d = analysis.annotations(analysis.Study(st), {})
    me = mine(n, maf, lsep, ret, gold, st1, mj, em, em_s0, em_t)
    for k, v in me.items():
        key = k.split(" (")[0]
        seen[(k, v)] += 1
        if got[key] != v:
            mism[k] += 1
print("trials", trials)
print("mismatches per annotation (impl vs my any-replicate-or-order reading):", dict(mism) or "none")
print("values seen (mine):", dict(sorted(seen.items(), key=str)))
