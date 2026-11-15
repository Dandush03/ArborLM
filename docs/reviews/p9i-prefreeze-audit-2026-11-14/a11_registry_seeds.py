"""A11 (auditor, Opus 5.5): the 57-cell matrix of section I.7 enumerated from the ADR table and compared
with studies.p9i.core.cells(); seed ranges checked for disjointness from everything observed."""
from studies.p9 import core as p9core
from studies.p9i import core

B1, B2 = (101, 301), (102, 302)
want = set()
for arm in ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7"):
    want |= {(arm, 16384, B1, s) for s in (1801, 1802)}
want |= {(arm, 16384, B2, 1801) for arm in ("W7", "A4", "R1", "D7")}
for arm in ("N", "W7", "A4", "R1", "D7"):
    want |= {(arm, 65536, B1, s) for s in (1801, 1802)}
for arm in ("N", "W7", "A4", "R1"):
    want |= {(arm, 4096, B1, s) for s in (1801, 1802)}
for n in (16384, 65536):
    for arm in ("BB", "BB-D", "BB-0"):
        want |= {(arm, n, B1, s) for s in (1801, 1802)}
want.add(("BB", 16384, B2, 1801))
for arm in ("BB", "BB-0"):
    want |= {(arm, 4096, B1, s) for s in (1801, 1802)}
have = {(c.arm, c.slots, c.parent, c.seed) for c in core.cells()}
print("ADR table cells:", len(want), "| registry:", len(have), "| identical:", want == have)
cal = {(c.arm, c.slots, c.parent, c.seed) for c in core.calibration_cells()}
print("calibration cells:", len(cal), sorted({(a, p, s) for a, _, p, s in cal}))

def vals(s):
    return {*s.data_values(), *s.null_seeds_a, *s.null_seeds_b}

reg = vals(core.registered_seeds())
print("registered data seeds:", min(reg), "..", max(reg), "count", len(reg))
observed = {"rehearsal draw 0 (design probes)": vals(p9core.rehearsal_seeds(0)), "calibration draw 1": vals(p9core.rehearsal_seeds(1)),
            "rehearsal draw 2": vals(p9core.rehearsal_seeds(2)), "all draws 0..9": set().union(*(vals(p9core.rehearsal_seeds(k)) for k in range(10))),
            "auditor probe constants 180101..181900": set(range(180101, 181901)), "P9 registered (ADR-0017 lanes)": set(p9core.registered_seed_values()),
            "test 900001+": set().union(*(vals(core.test_seeds(k)) for k in range(3)))}
for name, s in observed.items():
    print(f"  overlap with {name}: {len(reg & s)}")
print("init seeds registered", core.INIT_SEEDS, "calibration", core.CALIBRATION_INIT_SEEDS, "rehearsal init = facts seed + offset:", core.init_seed_of(core.cells()[0], "rehearsal", p9core.rehearsal_seeds(2)))
print("max rehearsal-draw seed:", max(observed["all draws 0..9"]))
