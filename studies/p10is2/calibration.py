# ruff: noqa: E501
"""Part T calibration rules (ADR-0025 sections 7.1, 7.2; rulings G1-G4, L4): rate and read-layer selection, the convergence ladder, the pilot gate, the divergence cases and calibration's code identity.

Pure functions over recorded D_cal scores. Nothing here trains. One rate grid; the rule everywhere is "the smallest value within 0.01 of the best", over the eligible (not DIVERGED) values. Calibration scores are
never results.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .common import core

DIVERGED = None  # a rate (or a layer run) whose training produced a non-finite loss is recorded as DIVERGED: its mean is None


class CalibrationStop(RuntimeError):
    """Calibration stops and the work returns to the human lead: every rate of a module type diverged, or a non-finite loss in the convergence ladder or the pilot (ruling L4)."""


def within(best: float, value: float, tol: float) -> bool:
    """``value`` is within ``tol`` of ``best`` (inclusive). Compared after rounding to 12 places so that 0.0100000000001 of float noise does not decide a tie (the ADR's 'within 0.01')."""
    return round(best - value, 12) <= tol


def select_smallest_within(means: Mapping[float, float | None], tol: float, what: str = "rate") -> float:
    """Among eligible values (mean not None: not DIVERGED) the smallest whose mean is within ``tol`` of the best mean. Every value diverged: ``CalibrationStop``."""
    eligible = {k: v for k, v in means.items() if v is not None}
    for k, v in eligible.items():
        if not math.isfinite(v):
            raise CalibrationStop(f"a non-finite mean for {what} {k}: record it as DIVERGED (None) instead")
    if not eligible:
        raise CalibrationStop(f"every {what} diverged: calibration stops and the work returns to the human lead (section 7.1)")
    best = max(eligible.values())
    return min(k for k, v in eligible.items() if within(best, v, tol))


def select_rate(cfg: Mapping[str, Any], module: str, means: Mapping[float, float | None]) -> float:
    """``module``: ``store``, ``lora`` or ``etable``. ``means[rate]`` is the mean chrF on D_cal over the two capabilities of a stage 1 of 2,000 updates on calibration draw 0 (None = DIVERGED). The rates
    must be exactly the module's grid (store and E-table {0.001, 0.003, 0.01}; LoRA {0.0001, 0.0003, 0.001}). Ties go to the smaller rate."""
    c = cfg["calibration"]
    grid = list(c["lora_rates"] if module == "lora" else c["store_rates"])
    if sorted(means) != sorted(grid):
        raise ValueError(f"the rates for {module} must be exactly {grid}, got {sorted(means)}")
    return select_smallest_within(means, float(c["rate_tie_tolerance"]), f"{module} rate")


def select_read_layer(cfg: Mapping[str, Any], mean_l4: float, mean_l12: float | None) -> int:
    """The store's read layer by the same rule with L = 4 as 'the smaller': the store at L = 12 at its chosen rate, against its L = 4 result; a read-layer run that diverges (None) is not eligible, so L = 4."""
    tol = float(cfg["calibration"]["rate_tie_tolerance"])
    return int(select_smallest_within({4.0: mean_l4, 12.0: mean_l12}, tol, "read layer"))


def choose_training_length(cfg: Mapping[str, Any], snapshots: Mapping[str, Mapping[str, Mapping[int, float | None]]]) -> dict[str, Any]:
    """U is the smallest u in {1,000, 2,000, 4,000} such that, for BOTH module types (store and LoRA) and both capabilities, chrF on D_cal at 2u exceeds chrF at u by less than 0.01 (any difference below 0.01,
    a decrease included, is converged; a paired difference on the same 500 items). If none qualifies U = 8,000 and every Part T line carries NOT CONVERGED AT U. ``snapshots[module][capability][updates]``.
    A non-finite or missing value in the ladder is ``CalibrationStop`` (ruling L4). E-table, the joint arms and the stage-2 arms are not checked (a stated limit)."""
    c = cfg["calibration"]
    tol = float(c["convergence_tolerance"])
    for module in ("store", "lora"):
        for cap in core.TASKS:
            for u in c["ladder_snapshots"]:
                v = snapshots[module][cap].get(u)
                if v is None or not math.isfinite(v):
                    raise CalibrationStop(f"the convergence ladder has no finite chrF for {module} {cap} at {u} updates: calibration stops and the work returns to the human lead (ruling L4)")
    detail: dict[int, dict[str, float]] = {}
    for u in c["ladder_rungs"]:
        diffs = {f"{m}/{cap}": float(snapshots[m][cap][2 * u]) - float(snapshots[m][cap][u]) for m in ("store", "lora") for cap in core.TASKS}  # type: ignore[arg-type]
        detail[u] = diffs
        if all(round(d, 12) < tol for d in diffs.values()):
            return {"U": u, "converged": True, "line_note": None, "differences": detail}
    return {"U": int(c["ladder_top"]), "converged": False, "line_note": "NOT CONVERGED AT U", "differences": detail}


def pilot_gate(cfg: Mapping[str, Any], gap_by_capability: Mapping[str, float | None]) -> dict[str, Any]:
    """On D_cal at the calibrated settings: if M1's gap closed (calibration draw 1, the chosen U) is below 0.25 for either capability, Part T is NOT STARTED: PILOT and the work returns to the human lead. An
    undefined D_cal gap gives NOT STARTED: PILOT (GAP UNDEFINED). A non-finite value is ``CalibrationStop``."""
    floor = float(cfg["pilot"]["gap_min"])
    for c, g in gap_by_capability.items():
        if g is not None and not math.isfinite(g):
            raise CalibrationStop(f"the pilot's gap for capability {c} is not finite: calibration stops (ruling L4)")
    if any(gap_by_capability.get(c) is None for c in core.TASKS):
        return {"passed": False, "label": "NOT STARTED: PILOT (GAP UNDEFINED)"}
    low = [c for c in core.TASKS if float(gap_by_capability[c]) < floor]  # type: ignore[arg-type]
    return {"passed": not low, "label": None if not low else "NOT STARTED: PILOT", "below": low}


# --- units of calibration (section 14: 36 units of 2,000) ------------------------------------------------------------------------------------------
def calibration_units(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every training run of calibration: the two rate grids and E-table's grid (stage 1 of 2,000 updates on each capability, draw 0), the store at L = 12, and the convergence ladder (M1 and D1 on each
    capability, draw 1, to 8,000 updates = 4 units of 2,000). Section 14's count: 22 store-type units and 14 LoRA units, 36 in all. The grid is run at read layer 4; E-table's grid after the layer is chosen."""
    c = cfg["calibration"]
    units: list[dict[str, Any]] = []
    for cap in core.TASKS:
        for r in c["store_rates"]:
            units.append({"id": f"grid-store-{cap}-{r}", "module": "store", "capability": cap, "rate": r, "updates": c["rate_grid_updates"], "draw": 0, "layer": c["rate_grid_read_layer"], "kind": "store-type", "units_of_2000": 1})
        for r in c["lora_rates"]:
            units.append({"id": f"grid-lora-{cap}-{r}", "module": "lora", "capability": cap, "rate": r, "updates": c["rate_grid_updates"], "draw": 0, "kind": "lora", "units_of_2000": 1})
        units.append({"id": f"layer12-{cap}", "module": "store", "capability": cap, "rate": "chosen", "updates": c["rate_grid_updates"], "draw": 0, "layer": 12, "kind": "store-type", "units_of_2000": 1})
        for r in c["store_rates"]:
            units.append({"id": f"grid-etable-{cap}-{r}", "module": "etable", "capability": cap, "rate": r, "updates": c["rate_grid_updates"], "draw": 0, "layer": "chosen", "kind": "store-type", "units_of_2000": 1})
        for module, kind in (("store", "store-type"), ("lora", "lora")):
            units.append({"id": f"ladder-{module}-{cap}", "module": module, "capability": cap, "rate": "chosen", "updates": c["ladder_top"], "draw": 1, "snapshots": c["ladder_snapshots"], "layer": "chosen" if module == "store" else None, "kind": kind, "units_of_2000": c["ladder_top"] // 2000})
    return units


# --- code identity (section 7.1 rule 4) ---------------------------------------------------------------------------------------------------------
def code_identity_problems(record: Mapping[str, Any], frozen_files: Mapping[str, str], files: Sequence[str]) -> list[str]:
    """A calibration record carries the SHA-256 of each training and scoring file it ran; the Part T freeze refuses records whose hashes differ from the frozen files, and stand-in records."""
    out = []
    if record.get("stand_in"):
        out.append("a stand-in record is refused")
    if record.get("superseded"):
        out.append("a SUPERSEDED record is used for nothing")
    hashes = record.get("code_hashes") or {}
    for f in files:
        if f not in hashes:
            out.append(f"{f}: the record carries no hash")
        elif hashes[f] != frozen_files.get(f):
            out.append(f"{f}: the record's hash differs from the frozen file")
    return out


def repetition_used(records_by_repetition: Mapping[int, Mapping[str, Any]], frozen_files: Mapping[str, str], files: Sequence[str]) -> dict[str, Any]:
    """The repetition used is the one whose hashes equal the frozen files; it is never chosen on its values. Repetition 0 is the original (draws 0 and 1), 1 the repetition (draws 2 and 3 take the roles of draws
    0 and 1). Every other repetition is marked SUPERSEDED and used for nothing. If both match, the original (0) is used (reading, listed). None matches: refused (a second repetition needs seeds entered in the
    registry first and a recorded decision of the lead)."""
    matching = [i for i in sorted(records_by_repetition) if not code_identity_problems(records_by_repetition[i], frozen_files, files)]
    if not matching:
        return {"used": None, "refused": "no repetition's code hashes equal the frozen files: a second repetition needs seeds in the registry and a recorded decision of the lead"}
    used = matching[0]
    return {"used": used, "superseded": [i for i in sorted(records_by_repetition) if i != used], "draws": {0: [0, 1], 1: [2, 3]}[used]}
