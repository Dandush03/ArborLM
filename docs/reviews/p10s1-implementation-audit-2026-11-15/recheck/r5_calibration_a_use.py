"""(j) / 22.1 re-check: calibration items 1 and 2 and the overload row's U_P read a_use, not raw accuracy; M7: the tie walk runs on the records finalize() reads.

calibrate.read_obs is replaced IN THIS PROCESS ONLY by a synthetic reader (no record, no seed, no file): every observation has raw accuracy above the threshold
and a_use below it (useful < correct), so a reading of raw accuracy and a reading of a_use give different decisions. The implementer says the overload row's a_use
reading has no unit test; this is that test.

Run (worktree root): PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r5_calibration_a_use.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys
from pathlib import Path

from studies.p10s1 import calibrate as CAL
from studies.p10s1 import classes as C
from studies.p10s1 import core

N = 4096
UNIT = core.U_P


def po(acc, use):
    return C.PanelObs(n=N, correct=round(acc * N), useful=round(use * N), disabled=128, shuffled=128)


def make_reader(scenario):
    def reader(run_dir, cell):
        out = {}
        for u in CAL.calibration_snapshots(cell):
            if cell.kind == "CAL" and cell.facts == core.OVERLOAD_FACTS and cell.slots == 65536:  # overload row's U_P cells
                acc, use = scenario["overload"](cell.arm, u)
            elif cell.arm == "D-OQ":
                acc, use = scenario["dense"](cell.lr, cell.draw, u)
            elif cell.arm == "R2":
                acc, use = scenario["r2"]
            elif cell.arm == "H8":
                acc, use = scenario["h8"]
            else:
                acc, use = scenario["foq"](cell, u)
            out[u] = {p: po(acc, use) for p in core.PANELS}
        return out

    return reader


def foq_default(cell, u):
    return (1.0, 0.99) if cell.facts / cell.slots <= 0.5 else (0.97, 0.96)


def dense_tie(lr, draw, u):
    # U_P: 0.001 -> 0.60, 0.003 -> 0.61 (a tie within 0.02), 0.01 -> 0.30. Doubling grid: equal at U_P/2, 0.003 ahead by 0.05 at U_P/4.
    if u == UNIT:
        a = {0.001: 0.60, 0.003: 0.61, 0.01: 0.30}[lr]
    elif u == UNIT // 4:
        a = {0.001: 0.20, 0.003: 0.25, 0.01: 0.10}[lr]
    else:
        a = {0.001: 0.40, 0.003: 0.40, 0.01: 0.10}[lr] if u < UNIT else 0.7
    return (min(1.0, a + 0.02), a)


SCEN = {
    "raw passes, a_use fails (R2 0.97/0.93, H8 0.95/0.85, overload F-OQ 0.95/0.85 at every candidate)": {
        "foq": foq_default, "r2": (0.97, 0.93), "h8": (0.95, 0.85), "dense": dense_tie, "overload": lambda arm, u: (0.95, 0.85) if arm == "F-OQ" else (0.99, 0.99),
    },
    "a_use passes only from 16,384 updates on the overload row": {
        "foq": foq_default, "r2": (0.99, 0.99), "h8": (0.99, 0.99), "dense": dense_tie, "overload": lambda arm, u: ((0.97, 0.85) if u < 16384 else (0.97, 0.92)) if arm == "F-OQ" else (0.99, 0.99),
    },
}

out = {}
orig = CAL.read_obs
for name, scen in SCEN.items():
    CAL.read_obs = make_reader(scen)
    try:
        rec = CAL.finalize(Path("/nonexistent-run-dir"), include_overload=True, unit=UNIT)
        out[name] = {"u_p_check_stands": rec["u_p_check"]["stands"], "u_p_failures": len(rec["u_p_check"]["failures"]), "h8_undertrained": rec["h8"]["undertrained_cells"], "overload": rec["overload"],
                     "dense_rates": rec["dense_rates"], "returns_to_lead": rec["returns_to_lead"]}
    except Exception as exc:  # noqa: BLE001
        out[name] = f"{type(exc).__name__}: {exc}"
CAL.read_obs = orig
out["expected"] = {
    "scenario 1": "U_P check fails (R2 a_use 0.93 < 0.95), every H8 cell UNDERTRAINED (a_use 0.85 < 0.90), overload RETURN_TO_LEAD (F-OQ a_use 0.85 < 0.90 at 8,192, 16,384, 32,768); dense rate 0.003 decided at U_P/4",
    "scenario 2": "overload U_P = 16,384 (raw accuracy would have given 8,192)",
}
json.dump(out, sys.stdout, indent=1, default=str)
print()
