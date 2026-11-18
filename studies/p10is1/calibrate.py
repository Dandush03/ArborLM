# ruff: noqa: E501
"""P10IS1 calibration rules and orchestration (ADR-0024 section 7): the equal five-rate search for every trained arm in the fixed order (rates at a provisional readout, U_P per row computed, the rates of the units whose
selection cell lies in a row whose U_P differs re-selected once at U_P, loaded-cell units last at 65,536 updates), blind to registered seeds (the calibration draws only); the edge rule (the grid is extended one step
towards the edge, at most twice per unit in total across both selections, then RATE AT EDGE returns the work to the human lead); a diverged rate; U_P per row; the ladder search with its ceilings and the registered outcomes on
reaching them; H8's annotations. The rules are pure functions; ``run_calibration`` drives them through an ``Engine`` (the real one trains calibration cells through ``adapter``; the tests use a table engine).
Nothing here runs a registered seed. All figures a calibration finds are measured; the rules are the specification's.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from . import core
from . import labels as L

SELECTED, EXTEND, RATE_AT_EDGE, RETURN_ALL_DIVERGED = "SELECTED", "EXTEND", "RATE AT EDGE", "RETURN TO THE HUMAN LEAD: EVERY RATE DIVERGED"
EDGE_BY_TIE_WALK = "EDGE BY TIE-WALK"
RETURN_TO_LEAD = "RETURN TO THE HUMAN LEAD"
NOT_RUN_256 = "256 NOT MEASURED — NOT FULL WITHIN CEILING"
TOQ_PREDICTED_NOT_FULL = "T-OQ PREDICTED NOT FULL AT"
EPS = 1e-12


class TieNeedsLead(RuntimeError):
    """Rates are within 0.02 at the readout and the doubling-snapshot a_use the tie walk needs are missing."""


@dataclass(frozen=True)
class RateRun:
    """One (unit, rate) on both calibration draws at the unit's readout: ``readout_a_use`` the minimum Panel A a_use over the two draws (the selection figure), ``min_all`` the minimum over both draws and both panels (H8's
    undertrained test), ``walk`` the same minimum Panel A figure at readout/2, /4, /8, /16 (the tie walk), ``diverged`` (a non-finite value, a run that ended failed, or a raw Panel A correct count inside the G2 chance
    interval at the readout on either draw)."""

    readout_a_use: float
    min_all: float
    walk: Mapping[int, float]
    diverged: bool = False


def tie_snapshots(readout: int, steps: int = 4) -> tuple[int, ...]:
    return tuple(readout // d for d in (2, 4, 8, 16)[:steps] if readout % d == 0 and readout // d >= 1)


# --- one selection (section 7.1) -----------------------------------------------------------------------------------------------------------------
def select_rate(results: Mapping[float, RateRun], grid: Sequence[float], ext_used: int, readout: int, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The selection rule of ADR-0021 section 10.1 item 3 and section 22 M7 with ADR-0024's edge rule: the highest minimum Panel A a_use over the two draws at the readout; rates within 0.02 of the best are separated by
    the walk down the doubling grid (the first snapshot at which exactly one is within 0.02 of the best there decides; none: the smaller rate); a diverged rate is kept and left out. If the best rate is at an end of the grid by
    0.02 or more over the next one, the grid is extended one step in that direction (first 0.3 or 0.0003) unless two extensions have been made in total (then RATE AT EDGE); a best rate that is within 0.02 of another
    and was chosen by the tie walk is taken and recorded EDGE BY TIE-WALK when it is an end rate."""
    c = core.cfg_of(cfg)["rates"]
    tie = float(c["tie_difference"])
    lo_rate, hi_rate = min(grid), max(grid)
    live = {r: v for r, v in results.items() if not v.diverged}
    base: dict[str, Any] = {"readout": readout, "readout_a_use": {str(r): v.readout_a_use for r, v in sorted(results.items())}, "diverged": sorted(r for r, v in results.items() if v.diverged), "grid": list(grid), "extensions_used": ext_used}
    if not live:
        return {**base, "action": RETURN_ALL_DIVERGED, "rate": None, "edge": None}
    ordered = sorted(live.items(), key=lambda kv: (-kv[1].readout_a_use, kv[0]))
    best_rate, best = ordered[0][0], ordered[0][1].readout_a_use
    second = ordered[1][1].readout_a_use if len(ordered) > 1 else None
    if best_rate in (lo_rate, hi_rate) and (second is None or best - second >= tie - EPS):
        direction = "up" if best_rate == hi_rate else "down"
        if ext_used < int(c["extensions_max"]):
            steps = c[f"extension_{direction}"]
            return {**base, "action": EXTEND, "rate": None, "direction": direction, "new_rate": float(steps[ext_used_in_direction(grid, direction, c)]), "edge": None}
        return {**base, "action": RATE_AT_EDGE, "rate": None, "direction": direction, "edge": RATE_AT_EDGE, "reason": f"the best rate {best_rate} is at the {direction} end of the grid after {ext_used} extensions: the work returns to the human lead before the freeze"}
    contenders = sorted(r for r, v in ordered if best - v.readout_a_use < tie - EPS or r == best_rate)
    base["contenders"] = contenders
    if len(contenders) == 1:
        return {**base, "action": SELECTED, "rate": best_rate, "decided_by": "readout a_use", "edge": None}
    walk: list[dict[str, Any]] = []
    for u in tie_snapshots(readout, int(c["walk_steps"])):
        if any(u not in live[r].walk for r in contenders):
            raise TieNeedsLead(f"rates {contenders} are within {tie} at the readout and the doubling snapshot {u} is missing for a tied rate")
        vals = {r: live[r].walk[u] for r in contenders}
        walk.append({"update": u, "a_use": {str(r): v for r, v in vals.items()}})
        top = max(vals.values())
        contenders = sorted(r for r, v in vals.items() if top - v < tie - EPS)
        if len(contenders) == 1:
            r = contenders[0]
            return {**base, "action": SELECTED, "rate": r, "decided_by": f"faster learner: a_use at {u}", "walk": walk, "edge": EDGE_BY_TIE_WALK if r in (lo_rate, hi_rate) else None}
    r = min(contenders)
    return {**base, "action": SELECTED, "rate": r, "decided_by": "smaller learning rate (no snapshot separates the tied rates by 0.02)", "walk": walk, "edge": EDGE_BY_TIE_WALK if r in (lo_rate, hi_rate) else None}


def ext_used_in_direction(grid: Sequence[float], direction: str, rates_cfg: Mapping[str, Any]) -> int:
    """How many extension steps the grid already holds in ``direction`` (the next step is the one after them)."""
    base = [float(x) for x in rates_cfg["grid"]]
    steps = [float(x) for x in rates_cfg[f"extension_{direction}"]]
    return sum(1 for s in steps if s in grid and (s > max(base) if direction == "up" else s < min(base)))


class Measure(Protocol):
    def __call__(self, unit: str, rate: float, readout: int) -> RateRun: ...


def search_unit(measure: Measure, unit: str, readout: int, state: dict[str, Any], cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One selection of one unit: measure every rate of the (possibly extended) grid at ``readout``, select, and extend the grid when the edge rule says so. ``state`` holds the unit's grid and its extensions used so far
    (they carry from the provisional selection to the re-selection: at most twice in total)."""
    c = core.cfg_of(cfg)["rates"]
    grid: list[float] = state.setdefault("grid", [float(x) for x in c["grid"]])
    ext = int(state.get("extensions", 0))
    results: dict[float, RateRun] = {}
    trail: list[dict[str, Any]] = []
    while True:
        for r in grid:
            if r not in results:
                results[r] = measure(unit, r, readout)
        sel = select_rate(results, sorted(grid), ext, readout, cfg)
        trail.append({k: sel[k] for k in ("action", "rate", "grid", "extensions_used") if k in sel})
        if sel["action"] == EXTEND:
            grid.append(float(sel["new_rate"]))
            grid.sort()
            ext += 1
            state["extensions"] = ext
            continue
        state["extensions"] = ext
        return {**sel, "unit": unit, "trail": trail, "min_all_at_selected": None if sel["rate"] is None else results[sel["rate"]].min_all, "results": {str(r): {"readout_a_use": v.readout_a_use, "min_all": v.min_all, "diverged": v.diverged} for r, v in sorted(results.items())}}


# --- U_P (section 7.2) -----------------------------------------------------------------------------------------------------------------------------
Views = Mapping[int, Mapping[tuple[int, str], float]]  # update -> (draw, panel) -> a_use


def u_p_of_row(foq: Views, r2: Views, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """U_P of one row: the smallest of {8,192, 16,384, 32,768, 65,536} at which, on both calibration draws and both panels, F-OQ reaches a_use >= 0.90 at the row's larger step cell and R2 reaches >= 0.95. Ceiling 65,536:
    if none qualifies the work returns to the human lead and no other value is substituted."""
    c = core.cfg_of(cfg)
    th = c["thresholds"]
    f_min, r_min = float(th["calibration_a_use_foq"]), float(th["calibration_a_use_r2"])
    cands = [int(x) for x in c["ladder"]["u_p_candidates"]]
    for u in cands:
        f, r = list(foq.get(u, {}).values()), list(r2.get(u, {}).values())
        if len(f) == 4 and len(r) == 4 and all(a >= f_min - EPS for a in f) and all(a >= r_min - EPS for a in r):
            return {"u_p": u, "action": "FIXED"}
    return {"u_p": None, "action": RETURN_TO_LEAD, "reason": f"none of {cands} qualifies (F-OQ a_use >= {f_min} and R2 a_use >= {r_min} on both draws and panels)"}


# --- the ladder search and its registered outcomes (section 7.2 items 4 and 5) -------------------------------------------------------------------------
def arm_calibrated_length(views: Mapping[tuple[int, str], Mapping[int, float]], ceiling: int, cfg: Mapping[str, Any] | None = None) -> int | None:
    """An arm's calibrated length at a cell: the smallest ladder point U (the second of two consecutive ladder points) at which, on all four views (two draws x two panels), i*(U) - i*(U/2) <= 0.10, i*(U/2) >= 0.473
    and, in the calibration, i*(U) <= 4.0, up to the ceiling; None if the cell is not full on all four views at the ceiling (a view above 4.0 bits counts as not full)."""
    c = core.cfg_of(cfg)
    th = core.Thresholds.from_config(c)
    if len(views) != 4:
        return None
    pts = core.ladder_points(ceiling, c)
    for k in range(1, len(pts)):
        if core.full_at({f"{d}{p}": dict(v) for (d, p), v in views.items()}, pts[k], pts[k - 1], plateau_max=th.plateau_max, floor_i=th.plateau_floor_i, i_max=float(c["ladder"]["calibration_i_max"])):
            return pts[k]
    return None


def cell_outcome(name: str, foq: int | None, toq: int | None, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The registered outcomes of section 7.2 item 5 on reaching the calibration ceiling. 2K/256 (F-OQ alone): not full -> the cell is not run, '256 NOT MEASURED — NOT FULL WITHIN CEILING', no return. 8K/1K and 32K/4K:
    F-OQ full and T-OQ full -> U0 is the larger of the two; T-OQ not full -> U0 is F-OQ's and the freeze record states T-OQ PREDICTED NOT FULL AT the cell (the run judges it on its own snapshots); F-OQ not full
    (a view above 4.0 bits counts as this case) -> the work returns to the human lead before the freeze with the curves; the lead changes no load, ceiling or arm."""
    if name == core.cell_name(*core.saturation_only_cell(cfg)):
        if foq is None:
            return {"cell": name, "action": "NOT RUN", "u0": None, "runs": False, "note": NOT_RUN_256, "returns_to_lead": False}
        return {"cell": name, "action": "FIXED", "u0": foq, "runs": True, "note": "", "returns_to_lead": False}
    if foq is None:
        return {"cell": name, "action": RETURN_TO_LEAD, "u0": None, "runs": True, "toq_predicted_not_full": toq is None, "returns_to_lead": True, "options": "stop, or run with this transition fixed in the freeze record as NOT TESTED (ADR-0021 section 10.1 item 0b); no load, ceiling or arm changes", "note": f"F-OQ not full on all four views at the ceiling at {name}"}
    if toq is None:
        return {"cell": name, "action": "FIXED", "u0": foq, "runs": True, "toq_predicted_not_full": True, "note": f"{TOQ_PREDICTED_NOT_FULL} {name}", "returns_to_lead": False}
    return {"cell": name, "action": "FIXED", "u0": max(foq, toq), "runs": True, "toq_predicted_not_full": False, "note": "", "returns_to_lead": False}


def ladder_ceiling(name: str, cfg: Mapping[str, Any] | None = None) -> int:
    """Four times P10-S1's registered run length of the cell (1,572,864 at 8K/1K and 2K/256, 3,145,728 at 32K/4K)."""
    key = {"8K/1K": "8192/1024", "2K/256": "2048/256", "32K/4K": "32768/4096"}[name]
    return int(core.cfg_of(cfg)["ladder"]["calibration_ceiling"][key])


def h8_report(min_all_by_cell: Mapping[str, float], cells: Sequence[str], cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """H8 below 0.90 on either draw or panel at U_P at a calibrated cell: UNDERTRAINED-AT-U_P; a cell it was not calibrated at: H8 NOT CALIBRATED AT U_P AT <cell>. Annotations gate nothing."""
    floor = float(core.cfg_of(cfg)["thresholds"]["undertrained_a_use"])
    under = sorted(c for c, v in min_all_by_cell.items() if v < floor - EPS)
    cal = sorted(min_all_by_cell)
    return {"undertrained_cells": under, "calibrated_cells": cal, "annotations": L.h8_annotations(under, cal, cells), "min_a_use": dict(min_all_by_cell)}


# --- the whole calibration, in the fixed order ----------------------------------------------------------------------------------------------------------
class Engine(Protocol):
    """What the orchestration needs from the runs (the real engine trains calibration cells through the adapter; a table engine answers in the tests)."""

    def measure(self, unit: str, rate: float, readout: int) -> RateRun: ...

    def row_up(self, row: int, foq_rate: float, r2_rate: float) -> tuple[Views, Views]:
        """F-OQ at the row's larger step cell (at ``foq_rate``) and R2 at the row's reference cell (at ``r2_rate``), run on both calibration draws to the largest U_P candidate: update -> (draw, panel) -> a_use."""
        ...

    def ladder_views(self, name: str, arm: str, rate: float, ceiling: int) -> Mapping[tuple[int, str], Mapping[int, float]]:
        """The selected-rate runs of ``arm`` at the ladder cell ``name`` continued from their 65,536 checkpoints up the ladder to ``ceiling`` on both draws: (draw, panel) -> update -> i."""
        ...

    def h8_extra(self, unit_rate: Mapping[str, float]) -> Mapping[str, float]:
        """H8 at its selected rates to U_P at 2K/4K and 8K/16K on both draws (four runs): cell name -> minimum a_use over draws and panels."""
        ...


@dataclass
class Calibration:
    selections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # unit -> [provisional or loaded selection, re-selection]
    rates: dict[str, float] = field(default_factory=dict)
    row_u_p: dict[int, int | None] = field(default_factory=dict)
    u_p_detail: dict[int, dict[str, Any]] = field(default_factory=dict)
    ladder: dict[str, dict[str, Any]] = field(default_factory=dict)
    h8: dict[str, Any] = field(default_factory=dict)
    returns_to_lead: list[str] = field(default_factory=list)
    edge_notes: list[str] = field(default_factory=list)
    order: list[str] = field(default_factory=list)


def run_calibration(engine: Engine, cfg: Mapping[str, Any] | None = None) -> Calibration:
    """The fixed order of section 7.1: (1) rates of the units that are not loaded at the provisional readout of their row (8,192, 8,192, 16,384); (2) U_P of each row at those rates; (3) the units whose selection
    cell lies in a row whose U_P differs from its provisional readout are selected ONCE MORE at U_P (U_P is not recomputed and not re-checked); (4) the loaded-cell units (each loaded cell and 2K/256 its own unit) at
    65,536 updates, last; then the ladder search at each ladder cell from the 65,536 checkpoints, and H8's annotations. A rate unit that ends RATE AT EDGE, or a row with no U_P, returns the work to the human lead."""
    c = core.cfg_of(cfg)
    cal = Calibration()
    states: dict[str, dict[str, Any]] = {}
    prov = {int(k): int(v) for k, v in c["rates"]["provisional_readout"].items()}
    units_all = core.units(c)
    plain = [u for u in units_all if not core.unit_is_loaded(u, c)]
    loaded = [u for u in units_all if core.unit_is_loaded(u, c)]

    def do(unit: str, readout: int) -> dict[str, Any]:
        sel = search_unit(engine.measure, unit, readout, states.setdefault(unit, {}), c)
        cal.selections.setdefault(unit, []).append(sel)
        cal.order.append(f"select {unit} at {readout}")
        if sel["action"] in (RATE_AT_EDGE, RETURN_ALL_DIVERGED):
            cal.returns_to_lead.append(f"{unit}: {sel['action']} (selection at {readout})")
        elif sel.get("edge") == EDGE_BY_TIE_WALK:
            cal.edge_notes.append(f"{unit}: {EDGE_BY_TIE_WALK} (selection at {readout})")
        if sel["rate"] is not None:
            cal.rates[unit] = float(sel["rate"])
        return sel

    for unit in plain:  # (1) provisional readouts
        do(unit, prov[core.unit_row(unit, c)])
    if cal.returns_to_lead:
        return cal
    for row in core.row_facts(c):  # (2) U_P per row, at the provisional rates
        f_cell = tuple(c["grid"]["u_p_larger_step_cell"][str(row)])
        r_cell = tuple(c["grid"]["r2_reference_cell"][str(row)])
        foq_unit, r2_unit = core.unit_key("F-OQ", f_cell[0], f_cell[1], c), core.unit_key("R2", r_cell[0], r_cell[1], c)
        foq, r2 = engine.row_up(row, cal.rates[foq_unit], cal.rates[r2_unit])
        res = u_p_of_row(foq, r2, c)
        cal.u_p_detail[row] = res
        cal.row_u_p[row] = res["u_p"]
        cal.order.append(f"U_P of row {row}: {res['u_p']}")
        if res["u_p"] is None:
            cal.returns_to_lead.append(f"row {row}: no U_P within the ceiling")
    if cal.returns_to_lead:
        return cal
    for row in core.row_facts(c):  # (3) one re-selection at U_P of the units whose selection cell is in a row whose U_P differs from its provisional readout; U_P is not recomputed
        u_p = int(cal.row_u_p[row] or 0)
        if u_p == prov[row]:
            continue
        for unit in plain:
            if core.unit_row(unit, c) == row:
                do(unit, u_p)
    if cal.returns_to_lead:
        return cal
    for unit in loaded:  # (4) the loaded-cell units, last, at 65,536
        do(unit, int(c["rates"]["loaded_readout"]))
    if cal.returns_to_lead:
        return cal
    sat256 = True
    for f, n in core.ladder_cells(c):
        name = core.cell_name(f, n)
        ceiling = ladder_ceiling(name, c)
        foq_len = arm_calibrated_length(engine.ladder_views(name, "F-OQ", cal.rates[f"F-OQ|{name}"], ceiling), ceiling, c)
        toq_len = None
        if (f, n) != core.saturation_only_cell(c):
            toq_len = arm_calibrated_length(engine.ladder_views(name, "T-OQ", cal.rates[f"T-OQ|{name}"], ceiling), ceiling, c)
        out = cell_outcome(name, foq_len, toq_len, c)
        out.update(foq_length=foq_len, toq_length=toq_len, ceiling=ceiling)
        cal.ladder[name] = out
        if out["returns_to_lead"]:
            cal.returns_to_lead.append(f"{name}: F-OQ not full within the ceiling {ceiling}")
        if name == core.cell_name(*core.saturation_only_cell(c)) and not out["runs"]:
            sat256 = False
    h8_unit_rates = {u: cal.rates[u] for u in cal.rates if u.startswith("H8|")}
    min_all = {}
    for unit in plain:
        if unit.startswith("H8|"):
            sel = cal.selections[unit][-1]
            min_all[core.cell_name(*core.unit_selection_cell(unit, c))] = float(sel["min_all_at_selected"])
    min_all.update({k: float(v) for k, v in engine.h8_extra(h8_unit_rates).items()})
    cal.h8 = h8_report(min_all, [core.cell_name(f, n) for f, n in core.arm_cells("H8", c)], c)
    cal.h8["sat256"] = sat256
    return cal


def to_record(cal: Calibration) -> dict[str, Any]:
    """The calibration record (what the plan is built from): rates, U_P per row, U0 of each ladder cell, whether 2K/256 runs, the notes and every return to the human lead."""
    sat256 = bool(cal.ladder.get(core.cell_name(2048, 256), {}).get("runs", True))
    return {
        **core.envelope("calibration"), "rates": dict(cal.rates), "row_u_p": {str(k): v for k, v in cal.row_u_p.items()}, "u_p_detail": {str(k): v for k, v in cal.u_p_detail.items()}, "ladder": cal.ladder,
        "u0": {n: v["u0"] for n, v in cal.ladder.items() if v.get("u0") is not None}, "sat256": sat256, "h8": cal.h8, "returns_to_lead": list(cal.returns_to_lead), "edge_notes": list(cal.edge_notes), "order": list(cal.order),
        "selections": cal.selections, "complete": not cal.returns_to_lead and bool(cal.ladder),
    }  # fmt: skip
