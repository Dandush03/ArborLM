"""(library copy of check_edges_v2.build) Re-check auditor C: the predecessor's counterexamples E1-E8 and C-m1/C-m2 re-run on the fixed code with a complete
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


