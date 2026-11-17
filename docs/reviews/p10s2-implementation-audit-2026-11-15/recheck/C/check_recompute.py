"""Auditor C: the recomputation rule on synthetic records: (a) own-code differences within 1e-6 in a number that is
not a verdict (APPEND COST); (b) a GEN gate flip at a snapshot that changes no class or label.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import copy, sys
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src"); sys.path.insert(0, sys.argv[2])
import check_rules as K, spec_rules as S
from studies.p10s2 import analysis
base = {"s0": {"E_A": 0.1, "E_B": 0.1}, "t": {"E_A": 0.9, "E_B": 0.9}, "s0sub": {"E_A": 0.12, "E_B": 0.12}, "tsub": {"E_A": 0.88, "E_B": 0.88}}
cells = {}
for r in range(3):
    for (g, v), (ga, gb) in K.TEMPLATE.items():
        p = {"E_A": ga, "E_B": gb}
        cells[(r, g, v)] = S.Cell(panels=p, abl={q: {"unablated": p[q], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for q in p} if g in K.MEMORY else None, gen=0.001 if g in K.GEN else None)
nc = K.numeric_cells(base, cells)
reg = K.serialize(base, nc, 3)
for r in range(3):
    for o in ("AB", "BA"):
        lab = f"r{r}/MAF/{o}"
        reg["replicates"][r]["cells"][lab]["scores"][lab + "@append"] = {"panels": {"E_A": {"mean": 0.6}, "E_B": {"mean": 0.6}}}
rec_cells = {lab: copy.deepcopy(c) for rep in reg["replicates"] for lab, c in rep["cells"].items()}
rec_cells["r0/MAF/AB"]["scores"]["r0/MAF/AB@append"]["panels"]["E_A"]["mean"] = 0.6 + 4e-7
out = analysis.analyze_with_recomputation(reg, rec_cells, "own-code")
print("(a) own-code, APPEND COST input differs by 4e-7 (< 1e-6): label", out["label_row"], out["label"], "| changes:", out["recomputation"].get("changes"))
rec2 = {lab: copy.deepcopy(c) for rep in reg["replicates"] for lab, c in rep["cells"].items()}
rec2["r0/MSEQ/AB"]["scores"]["r0/MSEQ/AB"]["gen"]["loss_increase"] = 0.5
out2 = analysis.analyze_with_recomputation(reg, rec2, "frozen-code")
print("(b) frozen-code, GEN of r0/MSEQ/AB flips pass->fail in the recomputation: label", out2["label_row"], out2["label"], "| NE cells", out2["recomputation"]["not_evaluated_cells"], "| changes:", out2["recomputation"].get("changes"))
