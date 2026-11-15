# ruff: noqa: E501
"""P10S1 calibration rules (ADR-0021 section 10.1): the load calibration and its fixed rule table, the U_P check, the H8 report, D-OQ's learning rate, the overload row's U_P,
and the record (``calibration.json``) the freeze binds the rehearsal to. Pure functions of counts, plus the reader of the calibration cells' records.

Nothing here chooses a value by itself where the ADR leaves the choice to the human lead: every return named in section 10.1 is a ``RETURN_TO_LEAD`` decision with its reason, and
a tie in the dense-rate choice (a difference below 0.02, which the ADR sends 'to the faster of the two' without defining it) raises ``TieNeedsLead``. Calibration accuracies are
calibration, never results; they are read only from the calibration draws and panels.

READINGS (printed with the record): the U_P check, H8's UNDERTRAINED flag and the overload row's U_P read raw accuracy (the ADR says 'accuracy'); loadedness reads i (section 8.2).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from . import analysis as A
from . import classes as C
from . import core

GRID_STANDS, OVERLOAD_ROW, RETURN_TO_LEAD = "GRID_STANDS", "OVERLOAD_ROW", "RETURN_TO_LEAD"
UNDERTRAINED_BELOW = 0.90
U_P_F_OQ_MIN = 0.90
U_P_R2_MIN = 0.95


class TieNeedsLead(RuntimeError):
    """Section 10.1 item 3: the dense rates' minimum accuracies differ by less than 0.02 and the ADR's tie-break ('the faster of the two') is not defined; the lead decides."""


def calibration_snapshots(cell: core.Cell) -> tuple[int, ...]:
    """The snapshots a calibration cell is evaluated at: the load runs' doubling grid plus the registered U_run/2 and U_run of the slot count; the overload U_P runs at the three
    candidates; the dense-rate runs at U_P and their run length; the other runs at U_P."""
    unit = cell.u_p
    if cell.arm == "F-OQ" and cell.run_updates == core.load_updates(unit):
        return core.load_snapshots(cell.slots, cell.run_updates, unit)
    if cell.facts == core.OVERLOAD_FACTS and cell.slots == 65536:
        return tuple(sorted(u for u in core.overload_candidates(unit) if u <= cell.run_updates))
    if cell.arm == "D-OQ":
        return tuple(sorted({unit, cell.run_updates}))
    return (cell.run_updates,)


# --- the load rule (section 10.1 item 0) ----------------------------------------------------------------------------------------------------
def loaded_at_slot_count(views: Mapping[tuple[int, str], C.View]) -> bool:
    """A load is loaded at a slot count if, on both draws and both calibration panels, the cell is loaded by the definition of section 8.2 read at the registered U_run of that
    slot count (the views are built with that run length; the 65,536-update snapshots enter no rule)."""
    return bool(views) and all(v.loaded() for v in views.values())


class LoadDecision(NamedTuple):
    action: str
    reasons: list[str]
    overload_facts: int | None
    note: str


def load_decision(loaded: Mapping[tuple[int, int], bool]) -> LoadDecision:
    """The rule of section 10.1 item 0, keyed (slots, facts): 4,096 slots: load 2 (8,192 facts) or load 8 (32,768) loaded -> the 4K to 16K transition is tested by the registered
    rows, else RETURN_TO_LEAD. 16,384 slots: load 2 (32,768) loaded -> the grid stands; load 2 not loaded and load 4 (65,536) loaded -> the overload row (65,536 facts at 16,384 and
    65,536 slots); only load 8 (131,072) loaded, or none -> RETURN_TO_LEAD (131,072 facts exceed 65,536 slots; the lead never runs a row without R2)."""
    reasons: list[str] = []
    if not (loaded[(4096, 8192)] or loaded[(4096, 32768)]):
        return LoadDecision(RETURN_TO_LEAD, ["at 4,096 slots neither load 2 nor load 8 is loaded: no registered 4,096-slot cell is predicted loaded"], None, "returns to the human lead before the freeze")
    reasons.append("4K to 16K: tested by the registered rows (load 2 or load 8 is loaded at 4,096 slots)")
    if loaded[(16384, 32768)]:
        return LoadDecision(GRID_STANDS, [*reasons, "16K to 64K: load 2 is loaded at 16,384 slots; the grid of section 5.1 stands"], None, "")
    if loaded[(16384, 65536)]:
        return LoadDecision(OVERLOAD_ROW, [*reasons, "16K to 64K: load 2 is not loaded and load 4 is loaded at 16,384 slots: the row of 65,536 facts replaces the 32,768-fact row's 16K to 64K step"], core.OVERLOAD_FACTS, "load 4 was judged at 32,768 updates while the row's smaller cell runs 4 x U_P: a prediction only")
    return LoadDecision(RETURN_TO_LEAD, [*reasons, "at 16,384 slots only load 8 is loaded, or none: the 16K to 64K transition cannot be loaded with an R2 reference within the budget"], None, "returns to the human lead before the freeze")


def cut3_eligibility(loaded: Mapping[tuple[int, int], bool]) -> dict[str, bool]:
    """Cut 3 (section 10.3): D-OQ at a larger cell may be cut only if the load calibration predicted that step's smaller cell not loaded: 8K/64K (step A2) from the load-0.5 cell
    (8,192 facts at 16,384 slots), 32K/16K (step B1) from 32K/4K (32,768 facts at 4,096 slots)."""
    return {"8K/64K": not loaded[(16384, 8192)], "32K/16K": not loaded[(4096, 32768)]}


# --- U_P check, H8, dense rate, overload U_P -----------------------------------------------------------------------------------------------
def u_p_check(acc: Mapping[tuple[str, str, int, str], float]) -> dict[str, Any]:
    """Item 1: U_P stands if R2 >= 0.95 and F-OQ >= 0.90 at every diagonal cell on both draws and both calibration panels (key: arm, cell, draw, panel -> accuracy at U_P). If not,
    the work stops and returns to the human lead; no larger U_P is substituted by rule."""
    failures = []
    for (arm, cell, draw, panel), a in sorted(acc.items()):
        need = U_P_R2_MIN if arm == "R2" else U_P_F_OQ_MIN
        if a < need - C.EPS:
            failures.append({"arm": arm, "cell": cell, "draw": draw, "panel": panel, "accuracy": a, "needed": need})
    expected = len(core.DIAGONAL) * len(core.CALIBRATION_DRAWS) * len(core.PANELS) * 2
    if len(acc) != expected:
        failures.append({"reason": f"{len(acc)} accuracies, {expected} expected"})
    return {"stands": not failures, "failures": failures, "action": "none" if not failures else RETURN_TO_LEAD}


def h8_report(acc: Mapping[tuple[str, int, str], float]) -> dict[str, Any]:
    """Item 2: H8 below 0.90 at a cell at U_P -> its classes there carry UNDERTRAINED-AT-U_P (key: cell, draw, panel -> accuracy). H8 gates nothing."""
    low: dict[str, float] = {}
    for (cell, _draw, _panel), a in acc.items():
        if a < UNDERTRAINED_BELOW - C.EPS:
            low[cell] = min(low.get(cell, 1.0), a)
    return {"undertrained_cells": sorted(low), "min_accuracy_of_undertrained": low}


def select_dense_rate(min_accuracy: Mapping[float, float]) -> dict[str, Any]:
    """Item 3: the rate with the higher minimum Panel A accuracy at U_P (minimum over the two draws). A difference below 0.02 between the best and another rate is a tie the ADR sends
    to 'the faster of the two' without defining it: ``TieNeedsLead`` (the lead decides)."""
    ordered = sorted(min_accuracy.items(), key=lambda kv: (-kv[1], kv[0]))
    best_rate, best = ordered[0]
    contenders = [r for r, a in ordered if best - a < core.DENSE_TIE_DIFFERENCE - C.EPS]
    if len(contenders) > 1:
        raise TieNeedsLead(f"rates {sorted(contenders)} are within {core.DENSE_TIE_DIFFERENCE} in minimum Panel A accuracy at U_P: {C.READINGS['dense_rate_tie']}")
    return {"rate": best_rate, "min_accuracy": dict(min_accuracy)}


def overload_u_p(acc_foq: Mapping[tuple[int, int, str], float], acc_r2: Mapping[tuple[int, int, str], float], unit: int = core.U_P) -> dict[str, Any]:
    """The overload row's U_P: the smallest of {8,192, 16,384, 32,768} at which F-OQ >= 0.90 and R2 >= 0.95 at its larger cell on both draws and panels (key: update, draw, panel).
    None qualifies -> RETURN_TO_LEAD."""
    for u in core.overload_candidates(unit):
        f = [a for (uu, _d, _p), a in acc_foq.items() if uu == u]
        r = [a for (uu, _d, _p), a in acc_r2.items() if uu == u]
        if len(f) == 4 and len(r) == 4 and all(a >= U_P_F_OQ_MIN - C.EPS for a in f) and all(a >= U_P_R2_MIN - C.EPS for a in r):
            return {"u_p": u, "action": GRID_STANDS}
    return {"u_p": None, "action": RETURN_TO_LEAD, "reason": "none of 8,192, 16,384, 32,768 qualifies"}


# --- reading the calibration cells ------------------------------------------------------------------------------------------------------------------
def read_obs(run_dir: Path, cell: core.Cell) -> dict[int, dict[str, C.PanelObs]]:
    """``{update: {panel: PanelObs}}`` of a calibration cell from its eval records (a missing record raises ``FileNotFoundError``)."""
    out: dict[int, dict[str, C.PanelObs]] = {}
    for u in calibration_snapshots(cell):
        rec = core.read_record(core.eval_path(run_dir, cell.label, u), "eval")
        out[u] = {p: A.obs_from_panel(rec["reads"]["main"]["panels"][p]) for p in core.PANELS}
    return out


def finalize(run_dir: Path, *, include_overload: bool = False, unit: int = core.U_P) -> dict[str, Any]:
    """The calibration record from the calibration cells' eval records. Raises ``TieNeedsLead`` or leaves a RETURN_TO_LEAD action in the record where the ADR returns the work."""
    loaded: dict[tuple[int, int], bool] = {}
    table: dict[str, Any] = {}
    groups: dict[tuple[int, int], dict[tuple[int, str], C.View]] = {}
    for cell in core.load_calibration_cells(unit):
        obs = read_obs(run_dir, cell)
        run = core.run_length("F-OQ", cell.slots, unit)  # loadedness is read at the registered U_run of the slot count
        for p in core.PANELS:
            groups.setdefault((cell.slots, cell.facts), {})[(cell.draw, p)] = C.View({u: o[p] for u, o in obs.items() if u <= core.load_updates(unit)}, run, unit)
    for key, views in sorted(groups.items()):
        loaded[key] = loaded_at_slot_count(views)
        v0 = views[(1, "A")]
        table[f"{key[0]}x{key[1]}"] = {"slots": key[0], "facts": key[1], "load": key[1] / key[0], "loaded": loaded[key], "i_star_run": {f"d{d}{p}": v.i_star(v.run)[0] for (d, p), v in views.items()}, "plateaued": {f"d{d}{p}": v.plateaued() for (d, p), v in views.items()}, "i_at_65536": {f"d{d}{p}": v.i(core.load_updates(unit)) for (d, p), v in views.items()}, "run": v0.run}
    decision = load_decision(loaded)
    acc: dict[tuple[str, str, int, str], float] = {}
    for cell in core.u_p_check_cells(unit):
        obs = read_obs(run_dir, cell)
        for p in core.PANELS:
            acc[(cell.arm, cell.name, cell.draw, p)] = obs[unit][p].accuracy
    h8: dict[tuple[str, int, str], float] = {}
    for cell in core.h8_report_cells(unit):
        obs = read_obs(run_dir, cell)
        for p in core.PANELS:
            h8[(cell.name, cell.draw, p)] = obs[unit][p].accuracy
    dense_min: dict[int, dict[float, float]] = {}
    for cell in core.dense_rate_cells(unit):
        obs = read_obs(run_dir, cell)
        a = obs[unit]["A"].accuracy
        dense_min.setdefault(cell.slots, {})[cell.lr] = min(a, dense_min.get(cell.slots, {}).get(cell.lr, 1.0))
    dense: dict[str, Any] = {}
    tie: str | None = None
    for slots, m in sorted(dense_min.items()):
        try:
            dense[str(slots)] = select_dense_rate(m)
        except TieNeedsLead as exc:
            dense[str(slots)] = {"rate": None, "min_accuracy": {str(k): v for k, v in m.items()}, "tie": str(exc)}
            tie = str(exc)
    overload: dict[str, Any] | None = None
    if include_overload:
        f: dict[tuple[int, int, str], float] = {}
        r2: dict[tuple[int, int, str], float] = {}
        for cell in core.overload_u_p_cells(unit):
            obs = read_obs(run_dir, cell)
            for u, per in obs.items():
                for p in core.PANELS:
                    (f if cell.arm == "F-OQ" else r2)[(u, cell.draw, p)] = per[p].accuracy
        overload = overload_u_p(f, r2, unit)
    out: dict[str, Any] = core.jsonable({
        **core.envelope("calibration"), "load": table, "load_decision": decision._asdict(), "cut3_eligible": cut3_eligibility(loaded), "u_p_check": u_p_check(acc), "h8": h8_report(h8),
        "dense_rates": {k: v for k, v in dense.items()}, "dense_tie_needs_lead": tie, "overload": overload, "readings": C.READINGS, "calibration_accuracy_note": "calibration accuracies are reported as calibration, never as results",
        "returns_to_lead": _returns(decision, acc, overload, tie), "identity": core.code_identity(), "environment": core.environment(),
    })  # fmt: skip
    return out


def _returns(decision: LoadDecision, acc: Mapping[Any, float], overload: Mapping[str, Any] | None, tie: str | None) -> list[str]:
    out: list[str] = []
    if decision.action == RETURN_TO_LEAD:
        out += decision.reasons[-1:]
    if not u_p_check(acc)["stands"]:
        out.append("the U_P check failed: the work returns to the human lead; no larger U_P is substituted by rule")
    if overload is not None and overload["action"] == RETURN_TO_LEAD:
        out.append("no U_P of the overload row qualifies")
    if tie:
        out.append("D-OQ's learning rate: " + tie)
    return out


def dense_rates_of(record: Mapping[str, Any]) -> dict[int, float]:
    """D-OQ's calibrated learning rate by slot count (the 16,384 choice also serves 4,096 slots); refuses when a rate is undecided."""
    rates: dict[int, float] = {}
    for slots in (16384, 65536):
        entry = record["dense_rates"].get(str(slots))
        if entry is None or entry.get("rate") is None:
            raise TieNeedsLead(f"no D-OQ rate decided for {slots} slots")
        rates[slots] = float(entry["rate"])
    rates[4096] = rates[16384]
    return rates
