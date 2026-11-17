"""Audit script a5 (Claude Opus 5.5 auditor; P10-S1 revision 5 implementation audit; not Astra review).

ADR-0021 section 10.1 item 0b: if the human lead directs that S1 run with a transition fixed as CAPACITY NOT TESTED (a loaded
cell NOT LOADED WITHIN ITS CEILING), "the saturation pair that uses the cell is fixed as NOT FULL". Does analysis.saturation_line
honour Frozen.no_loaded_transitions?

In-memory study (counts chosen by me; nothing trained): every saturation cell full at a_use 0.60 (flat from 16,384), R2 at 1.0;
the freeze names the transition 1K->4K (8K/1K not loaded) as directed. Expected by the ADR: the pairs 256->1,024 and
1,024->4,096 that use 8K/1K are NOT FULL.

  UV_NO_SYNC=1 uv run --locked python -I <this file> <worktree root>
"""

import sys

sys.path.insert(0, sys.argv[1])
from studies.p10s1 import analysis as A  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import core  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

plan = core.Plan(seed_block_draws=(), row_u_p=(8192, 8192, 16384), u_l=(131072, 393216), u_l_256=98304)
fro = fz.Frozen.build(plan, fz.default_cpu_table(), no_loaded_transitions=["1K→4K"])


def views(facts, run, a_late, a_early=0.2):  # attempt 2: attempt 1 gave R2 a_use 0.2 at U_P (my error: REF failed, every pair NOT_EVALUATED)
    def ob(a):
        u = int(round(a * facts))
        return C.PanelObs(n=facts, correct=u, useful=u, disabled=facts // 32, shuffled=facts // 32)
    ups = [u for u in (512, 1024, 2048, 4096, 8192, 16384, 32768, 49152, 65536, 98304, 131072, 196608, 262144, 393216) if u <= run]
    return {p: C.View({u: ob(a_late if u >= 16384 else a_early) for u in ups}, run, 8192) for p in core.PANELS}


study = A.Study()
for r in range(1, 6):
    for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
        for size, (f, n) in core.SATURATION_CELLS.items():
            if n == 256 and arm != "F-OQ":
                continue
            run = core.run_updates_of(plan, "F-OQ", f, n)
            study.cells[(r, arm, f, n)] = A.CellData(label="x", arm=arm, facts=f, slots=n, draw=r, u_p=8192, run=run, memory=True, views=views(f, run, 0.60), meta={}, secondary={}, robust={}, work={}, ivf_measured={}, deep={}, leakage=False, train={})
    for f, n in A.REF_CELL.values():
        study.cells[(r, "R2", f, n)] = A.CellData(label="r", arm="R2", facts=f, slots=n, draw=r, u_p=8192, run=8192, memory=True, views=views(f, 8192, 1.0, 1.0), meta={}, secondary={}, robust={}, work={}, ivf_measured={}, deep={}, leakage=False, train={})

sat = A.saturation_line(study, fro)
print("directed transitions in the freeze:", fro.no_loaded_transitions)
for arm, v in sat["arms"].items():
    print(f"  {arm}: class {v['class']}; " + "; ".join(f"{k} {p['class']}" for k, p in v["pairs"].items()))
print("  saturation outcome:", sat["outcome"]["label"], "|", sat["outcome"]["printed"][:160])
ok = all(p["class"] == C.NOT_FULL for v in sat["arms"].values() for k, p in v["pairs"].items())
print("ADR 10.1 item 0b (pairs using the directed cell fixed NOT FULL) honoured:", ok)
