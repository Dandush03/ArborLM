"""Auditor C: label edge cases and annotations of studies/p10s2/analysis.py against the auditor's reading.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import copy, random, sys
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src"); sys.path.insert(0, sys.argv[2])
import check_rules as K, spec_rules as S
from studies.p10s2 import analysis

rng = random.Random(229901)
def good(n=3):
    base = {"s0": {"E_A": 0.1, "E_B": 0.1}, "t": {"E_A": 0.9, "E_B": 0.9}, "s0sub": {"E_A": 0.12, "E_B": 0.12}, "tsub": {"E_A": 0.88, "E_B": 0.88}}
    cells = {}
    for r in range(n):
        for (g, v), (ga, gb) in K.TEMPLATE.items():
            p = {"E_A": ga, "E_B": gb}
            abl = {q: {"unablated": p[q], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for q in ("E_A", "E_B")} if g in K.MEMORY else None
            cells[(r, g, v)] = S.Cell(panels=p, abl=abl, gen=0.001 if g in K.GEN else None)
    return base, cells
base, cells = good()
nc = K.numeric_cells(base, cells)
st = K.serialize(base, nc, 3)
print("baseline good record: impl row", analysis.analyze(st)["label_row"], "auditor row", S.label(base, nc, 3))
s2 = copy.deepcopy(st); s2["gates"] = {}
print("E1 gates record empty: impl row", analysis.analyze(s2)["label_row"], "(auditor: a registered label needs passed G1, G4-G9 records; expected 1 or 2, not a positive row)")
s3 = copy.deepcopy(st); del s3["gates"]["G5"]
print("E2 G5 record absent: impl row", analysis.analyze(s3)["label_row"])
s4 = copy.deepcopy(st); s4["replicates"][0]["ensemble"] = None
print("E3 ensemble record absent: impl row", analysis.analyze(s4)["label_row"])
s5 = copy.deepcopy(st); s5["prefreeze"] = {}
print("E4 prefreeze record absent (teacher_only unknown): impl row", analysis.analyze(s5)["label_row"])
# E5: an absent ablation section on one ST1 cell and an absent panel on one MAF cell
s6 = copy.deepcopy(st)
del s6["replicates"][0]["cells"]["r0/ST1/AB"]["scores"]["r0/ST1/AB"]["ablations"]
del s6["replicates"][1]["cells"]["r1/MAF/BA"]["scores"]["r1/MAF/BA"]["ablations"]["E_A"]
print("E5 ablations absent for r0/ST1/AB and E_A of r1/MAF/BA: impl row", analysis.analyze(s6)["label_row"], "classes MAF", analysis.analyze(s6)["classes"]["M-append-frozen"])
# E6: an ablation panel present but one kind absent -> crash?
s7 = copy.deepcopy(st)
del s7["replicates"][0]["cells"]["r0/ST1/AB"]["scores"]["r0/ST1/AB"]["ablations"]["E_A"]["code_perm"]
try:
    print("E6 one ablation kind absent: impl row", analysis.analyze(s7)["label_row"])
except Exception as e:
    print("E6 one ablation kind absent: analysis raises", type(e).__name__, e)
# E7: exact thresholds in floating point: G = 0.50 exactly and margin exactly 0.30
b = {"s0": {"E_A": 0.0, "E_B": 0.0}, "t": {"E_A": 1.0, "E_B": 1.0}, "s0sub": {"E_A": 0.0, "E_B": 0.0}, "tsub": {"E_A": 1.0, "E_B": 1.0}}
from studies.p10s2 import classes as C
from studies.p10s2.classes import Lexical
print("E7 ACQ1 at G=0.5, margin 0.7-0.4 (=0.29999999999999993 in binary):", C.acq1(0.5, Lexical(0.7, 0.4, 0.1, 0.1)))
print("E7b same margin as exact decimals 0.8-0.5:", C.acq1(0.5, Lexical(0.8, 0.5, 0.1, 0.1)))
# E8: annotations on random records vs auditor reading
def ann_mine(base, nc, n, lsep, ret):
    Gf = lambda c, p: S.G_full(base, c, p)
    def mean(xs):
        return None if any(x in (None, S.UNDEF) for x in xs) else sum(xs) / len(xs)
    out = {}
    ev = []
    for r in range(n):
        for c, o in (("A", "AB"), ("B", "BA")):
            e, s = Gf(nc[(r, "ETABLE", c)], "E_" + c), Gf(nc[(r, "ST1", o)], "E_" + c)
            ev.append(None if S.UNDEF in (e, s) else e >= s - 0.03)
    out["EQUIVALENT TO A WORD TABLE"] = None if None in ev else all(ev)
    tc = []
    for r in range(n):
        for o in ("AB", "BA"):
            f = "E_" + o[0]
            a, b2, c2, d = Gf(nc[(r, "ST1", o)], f), Gf(nc[(r, "MSEQ", o)], f), Gf(nc[(r, "LORA1", o)], f), Gf(nc[(r, "LSEQ", o)], f)
            tc.append(None if S.UNDEF in (a, b2, c2, d) else (c2 - d) - (a - b2) >= 0.10)
    out["TASK-CODED SPARSE RETENTION"] = None if None in tc else all(tc)
    res = []
    for c in ("A", "B"):
        a = mean([Gf(nc[(r, "MAF", o)], "E_" + c) for r in range(n) for o in ("AB", "BA")])
        j = mean([Gf(nc[(r, "MJOINT", "-")], "E_" + c) for r in range(n)])
        res.append(None if None in (a, j) else a < 0.9 * j)
    out["BELOW JOINT BOUND"] = True if True in res else (None if None in res else False)
    return out
mism = 0
for t in range(400):
    base, cells = good()
    for _ in range(4):
        key = rng.choice(list(cells)); p = rng.choice(["E_A", "E_B"])
        cells[key].panels[p] = rng.choice([0.0, 0.3, 0.6, 0.75, 0.8, 0.86, 0.9, 1.0, "nan"])
        if cells[key].abl is not None: cells[key].abl[p]["unablated"] = cells[key].panels[p]
    nc = K.numeric_cells(base, cells)
    st = K.serialize(base, nc, 3)
    got = analysis.annotations(analysis.Study(st), {})
    mine = ann_mine(base, nc, 3, None, None)
    for k, v in mine.items():
        if got[k] != v:
            mism += 1
            if mism < 4: print("annotation mismatch", t, k, got[k], v)
print("E8 annotations EQUIVALENT TO A WORD TABLE / TASK-CODED / BELOW JOINT BOUND: mismatches", mism, "of", 400 * 3)
