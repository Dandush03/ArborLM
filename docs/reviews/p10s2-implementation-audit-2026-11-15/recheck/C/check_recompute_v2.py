"""Re-check auditor C: the predecessor's C-M3 cases on the fixed recomputation rule (recompute.outcome_under_recomputation),
plus a within-tolerance difference that crosses a threshold and a composition-class change.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval. Usage: <python> check_recompute_v2.py <pin>"""

import copy
import sys
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import recompute  # noqa: E402

import check_edges_v2_lib as E  # noqa: E402
import synth as Y  # noqa: E402

reg = E.build()
for r in range(3):
    for o in ("AB", "BA"):
        lab = f"r{r}/MAF/{o}"
        reg["replicates"][r]["cells"][lab]["scores"][lab + "@append"] = {"panels": {"E_A": {"mean": 0.6}, "E_B": {"mean": 0.6}}}


def run(name, mutate, mode):
    rec = copy.deepcopy(reg)
    mutate(rec)
    out = recompute.outcome_under_recomputation(reg, rec, mode)
    rc = out["recomputation"]
    print(f"{name} [{mode}]: label row {out['label_row']} {out['label']} | changes {rc.get('changes', [])[:4]} | NE cells {rc.get('not_evaluated_cells', [])}")


print("tolerances: frozen-code", recompute.tolerance_of("frozen-code"), "own-code", recompute.tolerance_of("own-code"))
run("(0) identical recomputation", lambda r: None, "own-code")


def a(r):
    r["replicates"][0]["cells"]["r0/MAF/AB"]["scores"]["r0/MAF/AB@append"]["panels"]["E_A"]["mean"] = 0.6 + 4e-7


run("(a) APPEND COST input differs by 4e-7", a, "own-code")


def b(r):
    r["replicates"][0]["cells"]["r0/MSEQ/AB"]["scores"]["r0/MSEQ/AB"]["gen"]["loss_increase"] = 0.5


run("(b) GEN of r0/MSEQ/AB flips pass->fail", b, "frozen-code")


def b2(r):
    r["replicates"][0]["cells"]["r0/MAF/AB"]["scores"]["r0/MAF/AB"]["gen"]["loss_increase_first_marker"] = 0.5


run("(b2) first-marker GEN of r0/MAF/AB flips pass->fail", b2, "frozen-code")


def c(r):
    """A within-tolerance (own-code 1e-6) difference that crosses the 0.02 GEN threshold."""
    for rr in (reg, r):
        pass
    r["replicates"][1]["cells"]["r1/MAF/BA"]["scores"]["r1/MAF/BA"]["gen"]["loss_increase"] = 0.02 + 5e-7


reg_c = copy.deepcopy(reg)
reg_c["replicates"][1]["cells"]["r1/MAF/BA"]["scores"]["r1/MAF/BA"]["gen"]["loss_increase"] = 0.02
rec_c = copy.deepcopy(reg_c)
rec_c["replicates"][1]["cells"]["r1/MAF/BA"]["scores"]["r1/MAF/BA"]["gen"]["loss_increase"] = 0.02 + 5e-7
out = recompute.outcome_under_recomputation(reg_c, rec_c, "own-code")
print(f"(c) GEN exactly 0.02 registered, 0.02+5e-7 recomputed (own-code tolerance): label row {out['label_row']} {out['label']} | changes {out['recomputation'].get('changes', [])[:3]}")


def d(r):
    """A composition-class change in the recomputation: M-joint's combined record keeps less of its gain."""
    worse = Y.comb_record({"C1": {"A": 0.1, "B": 0.1}, "C2": {"A": 0.1, "B": 0.1}, "single": {"A": 0.7, "B": 0.7}})
    for rr in range(3):
        r["replicates"][rr]["cells"][f"r{rr}/MJOINT/-"]["scores"][f"r{rr}/MJOINT/-"]["combined"] = worse


reg_d = copy.deepcopy(reg)
good = Y.comb_record({"C1": {"A": 0.7, "B": 0.7}, "C2": {"A": 0.7, "B": 0.7}, "single": {"A": 0.7, "B": 0.7}})
reg_d["baseline"]["combined"] = {"stage0": Y.comb_record({"C1": {"A": 0.2, "B": 0.2}, "C2": {"A": 0.2, "B": 0.2}, "single": {"A": 0.2, "B": 0.2}}),
                                 "ensemble": Y.comb_record({"C1": {"A": 0.8, "B": 0.8}, "C2": {"A": 0.8, "B": 0.8}, "single": {"A": 0.8, "B": 0.8}})}
for rr in range(3):
    reg_d["replicates"][rr]["cells"][f"r{rr}/MJOINT/-"]["scores"][f"r{rr}/MJOINT/-"]["combined"] = good
rec_d = copy.deepcopy(reg_d)
d(rec_d)
out = recompute.outcome_under_recomputation(reg_d, rec_d, "frozen-code")
print(f"(d) recomputed M-joint combined scores change its composition class: label row {out['label_row']} {out['label']} | changes {out['recomputation'].get('changes', [])[:3]}")
