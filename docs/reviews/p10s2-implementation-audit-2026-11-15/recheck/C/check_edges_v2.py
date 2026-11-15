"""Re-check auditor C: the predecessor's counterexamples E1-E8 and C-m1/C-m2 re-run on the fixed code with a complete
synthetic record (all gates G1-G9, ensemble, combined records), plus new edge cases. Usage: <python> check_edges_v2.py <pin>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import copy
import sys
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402
from studies.p10s2 import classes as C  # noqa: E402
from studies.p10s2.classes import Lexical  # noqa: E402

import check_rules_v2 as K  # noqa: E402
import rules_v2 as S  # noqa: E402
import synth as Y  # noqa: E402

N = 3
gc = K.good_comb()


def build(mod=None):
    base = {"s0": {"E_A": 0.1, "E_B": 0.1}, "t": {"E_A": 0.9, "E_B": 0.9}, "s0sub": {"E_A": 0.12, "E_B": 0.12}, "tsub": {"E_A": 0.88, "E_B": 0.88}}
    cells = {}
    for r in range(N):
        for (g, v), (ga, gb) in Y.TEMPLATE.items():
            p = {"E_A": ga, "E_B": gb}
            abl = {q: {"unablated": p[q], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for q in ("E_A", "E_B")} if g in Y.MEMORY else None
            cells[(r, g, v)] = S.Cell(panels=p, abl=abl, gen=(0.001, 0.001) if g in Y.GEN else None)
    if mod:
        mod(base, cells)
    nc = K.numeric(base, cells)
    combined = {(r, g, v): gc for r in range(N) for g, vs in S.COMP.items() for v in vs}
    assembled = {r: {"label": "BY CONSTRUCTION", "M-i-separate": {"E_A": {"mean": 0.5}, "E_B": {"mean": 0.5}, "combined": gc}, "L-sep": {"E_A": {"mean": 0.5}, "E_B": {"mean": 0.5}, "combined": gc}} for r in range(N)}
    st = Y.serialize(base, nc, N, gates={g: True for g in Y.GATES}, ensembles=["equal"] * N, combined=combined, assembled=assembled, stage0_comb=gc, ens_comb=gc)
    return st


def row(st):
    out = analysis.analyze(st)
    return out["label_row"], out


st = build()
print("E0 complete good record: row", row(st)[0], "(auditor: 7)")
s = copy.deepcopy(st); s["gates"] = {}
print("E1 gates record empty: row", row(s)[0], "(ruling: 2 INCOMPLETE)")
s = copy.deepcopy(st); s["gates"] = None
print("E1b gates record None: row", row(s)[0], "(ruling: 2)")
for gname in ("G1", "G2", "G3", "G5", "G9"):
    s = copy.deepcopy(st); del s["gates"][gname]
    print(f"E2 {gname} record absent: row", row(s)[0], "(ruling: 2)")
for gname in ("G1", "G2", "G5", "G9"):
    s = copy.deepcopy(st); s["gates"][gname]["ok"] = False
    print(f"E2f {gname} failed: row", row(s)[0], "(ruling: 1)")
s = copy.deepcopy(st); s["gates"]["G5"] = {"ok": "true"}
print("E2s G5 ok is the string 'true': row", row(s)[0], "(auditor: not a pass -> 1)")
s = copy.deepcopy(st); s["replicates"][0]["ensemble"] = None
print("E3 ensemble record absent: row", row(s)[0], "(ruling: 2)")
s = copy.deepcopy(st); s["replicates"][0]["ensemble"]["teacher_own"]["B"] = 0.81
print("E3b ensemble differs: row", row(s)[0], "(1)")
s = copy.deepcopy(st); s["prefreeze"] = {}
print("E4 prefreeze record absent (teacher_only unknown): row", row(s)[0], "(auditor: not a positive row)")
s = copy.deepcopy(st)
del s["replicates"][0]["cells"]["r0/ST1/AB"]["scores"]["r0/ST1/AB"]["ablations"]
del s["replicates"][1]["cells"]["r1/MAF/BA"]["scores"]["r1/MAF/BA"]["ablations"]["E_A"]
r_, o_ = row(s)
print("E5 (C-M1) ablations absent r0/ST1/AB and E_A of r1/MAF/BA: row", r_, "MAF classes", {k: v["class"] for k, v in o_["classes"]["M-append-frozen"].items()}, "(auditor: no positive row)")
s = copy.deepcopy(st)
del s["replicates"][0]["cells"]["r0/ST1/AB"]["scores"]["r0/ST1/AB"]["ablations"]["E_A"]["code_perm"]
print("E6 (C-m3) one ablation kind absent: row", row(s)[0], "(auditor: no crash; no positive row)")
s = copy.deepcopy(st)
del s["replicates"][0]["cells"]["r0/MAGOLD/A"]["scores"]["r0/MAGOLD/A"]["ablations"]["E_A"]["value_perm"]
print("E6b MA-gold value_perm absent (cell outside the classes): row", row(s)[0], "(ruling: a NOT_EVALUATED control blocks rows 6-8 -> 12)")
s = copy.deepcopy(st)
del s["replicates"][0]["cells"]["r0/MAGOLD/A"]["scores"]["r0/MAGOLD/A"]["ablations"]["E_A"]["marker_only"]
print("E6c MA-gold marker_only absent (enters no rule): row", row(s)[0], "(observation)")
s = copy.deepcopy(st)
del s["replicates"][0]["cells"]["r0/MJOINT/-"]["scores"]["r0/MJOINT/-"]["ablations"]
print("E6d M-joint ablations absent: row", row(s)[0], "(ruling: 12)")
print("E7 ACQ1 at G=0.5, margin 0.7-0.4:", C.acq1(0.5, Lexical(0.7, 0.4, 0.1, 0.1)), "(IEEE; observation only)")
# C-M4: undefined gap hidden by a failing clause
print("C-M4 acq2 with g=0.4 (fails) and g_single undefined:", C.acq2(0.4, None, Lexical(0.9, 0.0, 0.0, 0.0)))
print("C-M4 acq2 with g=0.4 and marker-only undefined:", C.acq2(0.4, 0.8, Lexical(0.9, 0.0, 0.0, None)))


# C-m1: missing GEN is NOT a measured failure
def gen_mod(vals, cell=(0, "MAF", "AB")):
    def m(base, cells):
        cells[cell].gen = vals
    return m


for vals, note in (((None, None), "both GEN values missing on r0/MAF/AB"), ((0.001, None), "first-marker value missing"), ((0.001, "nan"), "first-marker non-finite"),
                   ((0.001, 0.03), "first-marker measured 0.03 (fails)"), ((0.03, 0.001), "token-64 measured 0.03"), ((0.02, 0.02), "exactly 0.02 under both (holds)"),
                   ((0.03, None), "measured fail + missing")):
    r_, o_ = row(build(gen_mod(vals)))
    print(f"C-m1/GEN {note}: row", r_, "status", o_["gen"]["status"])
r_, o_ = row(build(gen_mod((0.001, 0.05), (1, "ST1", "BA"))))
print("GEN ST1/BA r1 first-marker 0.05: row", r_, "(auditor: 6)")
r_, o_ = row(build(gen_mod((0.001, 0.05), (1, "MII", "BA"))))
print("GEN MII/BA r1 first-marker 0.05: row", r_, "(auditor: 8, M-ii alone fails)", "M-ii alone fails GEN:", o_["gen"]["M-ii alone fails GEN"])
r_, o_ = row(build(gen_mod(None, (1, "MII", "BA"))))
print("GEN MII/BA r1 record absent: row", r_, "(auditor: 8; M-ii GEN NOT_EVALUATED)")


# rows 3, 4, 9, 10, 11
def all_maf(fa, fb):
    def m(base, cells):
        for r in range(N):
            cells[(r, "MAF", "AB")].panels = {"E_A": fa, "E_B": fb}
            cells[(r, "MAF", "BA")].panels = {"E_A": fb, "E_B": fa}
            for o in ("AB", "BA"):
                for p in ("E_A", "E_B"):
                    cells[(r, "MAF", o)].abl[p]["unablated"] = cells[(r, "MAF", o)].panels[p]
    return m


print("row 9 (MAF forgets everywhere): row", row(build(all_maf(0.3, 0.85)))[0])
print("row 10 (MAF no new capability everywhere): row", row(build(all_maf(0.88, 0.1)))[0])


def st1_neg(base, cells):
    for r in range(N):
        cells[(r, "ST1", "AB")].panels["E_A"] = 0.1
        cells[(r, "ST1", "BA")].panels["E_B"] = 0.1


print("row 4 (ST1 negative everywhere): row", row(build(st1_neg))[0])
s = copy.deepcopy(st); s["prefreeze"]["stop"] = "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"
print("row 3 (prefreeze stop):", row(s)[:1])


# combined-record edge cases (addendum s7, s8)
def rej(base, cells):
    cells[(0, "MII", "AB")].rejected = True


s = build(rej)
del s["replicates"][0]["cells"]["r0/MII/AB"]["scores"]["r0/MII/AB"]["combined"]
r_, o_ = row(s)
print("M-ii r0/AB CONSOLIDATION-REJECTED with no combined record: row", r_, "incomplete:", o_["incomplete"][:2], "(addendum s7: NOT_EVALUATED composition line, auditor expects row 11/12 not INCOMPLETE)")
s = build(rej)
r_, o_ = row(s)
print("M-ii r0/AB rejected with a combined record: row", r_, "composition M-ii C1:", o_["composition"]["arms"]["C1"]["M-ii"]["composition"], o_["composition"]["arms"]["C1"]["M-ii"]["reasons"][:1])
s = copy.deepcopy(st); s["replicates"][0]["assembled"] = {}
r_, o_ = row(s)
print("assembled record of r0 empty: row", r_, "incomplete", o_["incomplete"][:2], "NO ADVANTAGE:", o_["annotations"].get("NO ADVANTAGE OVER SEPARATE ADAPTERS"))
s = copy.deepcopy(st); del s["replicates"][0]["assembled"]["L-sep"]["combined"]
r_, o_ = row(s)
print("assembled L-sep r0 without combined: row", r_, "incomplete", o_["incomplete"][:2])
s = copy.deepcopy(st); del s["replicates"][2]["cells"]["r2/LJOINT/-"]["scores"]["r2/LJOINT/-"]["combined"]
print("L-joint r2 without combined: row", row(s)[0], "(addendum s8: row 2)")
s = copy.deepcopy(st); s["baseline"]["combined"] = {}
r_, o_ = row(s)
print("Stage 0 and ensemble combined records absent: row", r_, "composition MAF C1:", o_["composition"]["arms"]["C1"]["M-append-frozen"]["composition"], o_["composition"]["arms"]["C1"]["M-append-frozen"]["reasons"][:1])
