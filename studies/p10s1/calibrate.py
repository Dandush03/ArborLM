# ruff: noqa: E501
"""P10S1 calibration rules (ADR-0021 revision 5, section 10.1): the load search (item 0b: U_L of the two loaded cells and of 2K/256), U_P of each row (item 1), the H8 report (item 2), D-OQ's
learning rate in four units (item 3), and the records the freeze binds the rehearsal to. Pure functions of counts, plus the reader of the calibration cells' records.

Every rule is applied to the FINISHED record of the runs: nothing here decides, stops, extends or re-runs a run from an observed curve. A run that ends ``failed`` (or that was stopped by its
item cap) is an input to the rule (no U_L; a diverged rate), kept and never re-run. Every return named in section 10.1 is a ``RETURN_TO_LEAD`` decision with its reason; nothing is chosen on the
lead's behalf. Calibration accuracies are calibration, never results; they are read only from the calibration draws and panels.

Rulings (ADR-0021 section 22 and section 25.12): the row U_P check and H8's UNDERTRAINED flag read a_use ((j)); loadedness reads i (section 8.2, with the plateau floor of revision 5); the dense
rate's tie is the faster learner (M7); a dense rate is diverged if its run failed or its raw Panel A correct count lies inside the chance interval on either draw.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import analysis as A
from . import classes as C
from . import core

GRID_STANDS, RETURN_TO_LEAD = "GRID_STANDS", "RETURN_TO_LEAD"
UNDERTRAINED_BELOW = 0.90
U_P_F_OQ_MIN = 0.90
U_P_R2_MIN = 0.95
EDGE_BY_TIE_WALK = "EDGE BY TIE-WALK"
NOT_LOADED_WITHIN_CEILING = "NOT LOADED WITHIN ITS CEILING"
TOQ_PREDICTED_NOT_LOADED = "T-OQ PREDICTED NOT LOADED AT"
STOPPED_BY_CAP = "STOPPED BY CAP"  # a run stopped by its item cap: never diverged, never not loaded; its unit or cell returns to the lead (ADR-0021 section 25.14 item 1)
NOT_RUN_DRIVER = "NOT RUN — DRIVER STOPPED"  # a run without a record after `close-stage` (section 25.14 item 2)
NOT_MEASURED_256 = "256 NOT MEASURED — NOT FULL WITHIN CEILING"


class NotComplete(RuntimeError):
    """A finalize command was asked while its stage is not complete (audit M1): the once-only record is never written from runs that may still be in progress."""


def require_stage_complete(run_dir: Path, stage: str, cells: Sequence[core.Cell]) -> dict[str, Any]:
    """The stage's manifest exists (the pool has finished) and every cell of its items has a ``train.json`` (completed, failed, or stopped at its item cap), or a manifest task of its label that did not
    complete (not started, killed, skipped). Returns the cells without a record, which the finalize record lists; raises ``NotComplete`` otherwise."""
    path = run_dir / stage / "manifest.json"
    if not path.is_file():
        raise NotComplete(f"no {stage}/manifest.json in {run_dir}: the stage has not finished; nothing is finalized while runs may be in progress")
    tasks = {t["label"]: t["status"] for t in core.read_record(path, "stage_manifest")["tasks"]}
    relaunch = run_dir / f"{stage}-relaunch" / "manifest.json"
    relaunched = {t["label"]: t["status"] for t in core.read_record(relaunch, "stage_manifest")["tasks"]} if relaunch.is_file() else {}
    grouped = [s for lab, s in tasks.items() if lab.startswith("cal-")]  # the DRY profile's grouped tasks
    no_record: list[str] = []
    for c in cells:
        if (core.cell_dir(run_dir, c.label) / "train.json").is_file():
            continue
        status = relaunched.get(c.label) or tasks.get(c.label) or (("failed" if any(g != "completed" for g in grouped) else None) if grouped else None)
        if status is None or status == "completed":
            raise NotComplete(f"{c.label} has no train record and the {stage} manifest does not list it as a task that did not run: the stage is not complete")
        no_record.append(f"{c.label}: {status}")
    return {"stage": stage, "cells": len(cells), "no_record": no_record}


class TieNeedsLead(RuntimeError):
    """Section 10.1 item 3: the dense rates' readouts differ by less than 0.02 and the doubling-snapshot a_use the tie walk needs are missing; the lead decides."""


# --- the snapshots of a calibration cell ----------------------------------------------------------------------------------------------------------
def calibration_snapshots(cell: core.Cell, unit: int | None = None) -> tuple[int, ...]:
    """The snapshots a calibration cell is evaluated at: the load search at the doubling grid from U_P/16 (512), every candidate and the half of every candidate up to its ceiling; the row U_P runs
    at 8,192 / 16,384 / 32,768; H8 at its row's U_P; D-OQ at the doubling snapshots the tie walk reads (readout / 2^k, k = 0..4)."""
    base = cell.u_p if unit is None else unit
    top = cell.run_updates
    key = (cell.facts, cell.slots)
    if cell.arm in ("F-OQ", "T-OQ") and (key in core.LOADED_CELLS or key == core.SATURATION_ONLY_CELL):
        name = core.cell_name(*key)
        grid = {base // 16 * 2**k for k in range(0, 12) if base // 16 >= 1}
        cands = core.load_candidates(name, core.U_P if base == core.U_P else base)
        marks = {*grid, *cands, *(c // 2 for c in cands)}
        return tuple(sorted(m for m in marks if 1 <= m <= top))
    if cell.arm in ("F-OQ", "R2"):
        return tuple(core.scaled(c, base) for c in core.U_P_CANDIDATES if core.scaled(c, base) <= top)
    if cell.arm == "D-OQ":
        return tuple(sorted({top // 2**k for k in range(0, core.DENSE_WALK_STEPS + 1) if top % 2**k == 0 and top // 2**k >= 1}))
    return (top,)


# --- the load search (item 0b) --------------------------------------------------------------------------------------------------------------------
def passes_at(views: Mapping[tuple[int, str], C.View], upto: int) -> bool:
    """An arm passes at candidate ``upto`` if each of its four views (two draws x two panels) is loaded by section 8.2 read with ``upto`` in place of U_run: i*(U) - i*(U/2) at most 0.10, i*(U/2) at
    least 0.473 (the plateau floor) and i*(U) at most 4.0. A view without the snapshots at U and U/2 (a run that ended early) does not pass."""
    if len(views) != 4:
        return False
    for v in views.values():
        if upto not in v.obs or upto // 2 not in v.obs:
            return False
        sub = C.View({u: o for u, o in v.obs.items() if u <= upto}, upto, v.u_p, memory=v.memory)
        if not sub.loaded():
            return False
    return True


def arm_u_l(views: Mapping[tuple[int, str], C.View] | None, candidates: Sequence[int]) -> int | None:
    """U_L of an arm: the smallest candidate U_k such that the arm passes at U_(k-1) and at U_k (two consecutive candidates; the first candidate cannot be U_L). None if no such candidate exists:
    that covers a view above 4.0 bits, a run that ended ``failed`` or was stopped at its item cap (``views`` None or short), and a first pass alone."""
    if not views:
        return None
    cands = list(candidates)
    for k in range(1, len(cands)):
        if passes_at(views, cands[k - 1]) and passes_at(views, cands[k]):
            return cands[k]
    return None


def cell_outcome(foq_u_l: int | None, toq_u_l: int | None) -> dict[str, Any]:
    """The fixed outcomes of item 0b for a loaded cell: F-OQ and T-OQ both have a U_L -> the larger; F-OQ has one and T-OQ none -> F-OQ's, with T-OQ PREDICTED NOT LOADED; F-OQ has none -> NOT LOADED
    WITHIN ITS CEILING, which returns to the human lead before the freeze (even if T-OQ has a U_L)."""
    if foq_u_l is None:
        return {"action": RETURN_TO_LEAD, "u_l": None, "toq_predicted_not_loaded": toq_u_l is None, "status": NOT_LOADED_WITHIN_CEILING, "note": "the record returns to the human lead before the freeze; nothing registered is generated"}
    if toq_u_l is None:
        return {"action": GRID_STANDS, "u_l": foq_u_l, "toq_predicted_not_loaded": True, "status": "F-OQ ONLY", "note": TOQ_PREDICTED_NOT_LOADED}
    return {"action": GRID_STANDS, "u_l": max(foq_u_l, toq_u_l), "toq_predicted_not_loaded": False, "status": "BOTH ARMS", "note": ""}


def saturation_cell_outcome(foq_u_l: int | None) -> dict[str, Any]:
    """2K/256 (F-OQ alone): a U_L, or '256 NOT MEASURED — NOT FULL WITHIN CEILING' with the cell not run and no return to the human lead."""
    if foq_u_l is None:
        return {"action": GRID_STANDS, "u_l": None, "runs": False, "status": NOT_MEASURED_256, "note": "the pair 256 to 1,024 is fixed as NOT FULL; the cell is not run; the registry is 30 configurations and 150 cells"}
    return {"action": GRID_STANDS, "u_l": foq_u_l, "runs": True, "status": "U_L FOUND", "note": ""}


# --- row U_P (item 1), H8 (item 2) ---------------------------------------------------------------------------------------------------------------
def row_u_p(foq: Mapping[tuple[int, int, str], float], r2: Mapping[tuple[int, int, str], float], candidates: Sequence[int]) -> dict[str, Any]:
    """U_P of one row: the smallest candidate at which F-OQ's a_use is at least 0.90 and R2's at least 0.95 on both draws and both panels (keys: update, draw, panel). None qualifies ->
    RETURN_TO_LEAD; no other value is substituted."""
    for u in candidates:
        f = [a for (uu, _d, _p), a in foq.items() if uu == u]
        r = [a for (uu, _d, _p), a in r2.items() if uu == u]
        if len(f) == 4 and len(r) == 4 and all(a >= U_P_F_OQ_MIN - C.EPS for a in f) and all(a >= U_P_R2_MIN - C.EPS for a in r):
            return {"u_p": u, "action": GRID_STANDS}
    return {"u_p": None, "action": RETURN_TO_LEAD, "reason": f"none of {list(candidates)} qualifies (F-OQ a_use >= 0.90 and R2 a_use >= 0.95 on both draws and panels)"}


def h8_report(acc: Mapping[tuple[str, int, str], float]) -> dict[str, Any]:
    """Item 2: H8 below 0.90 at a cell at its row's U_P -> its classes there carry UNDERTRAINED-AT-U_P (key: cell, draw, panel -> a_use). H8 gates nothing. At 2K/1K, 8K/1K and 32K/4K, where H8
    was not calibrated, its classes carry H8 NOT CALIBRATED AT <cell> (``classes.h8_annotations``)."""
    low: dict[str, float] = {}
    count: dict[str, int] = {}
    for (cell, _draw, _panel), _a in acc.items():
        count[cell] = count.get(cell, 0) + 1
    calibrated = sorted(c for c, n in count.items() if n == len(core.CALIBRATION_DRAWS) * len(core.PANELS))  # a cell with a failed or missing run is not calibrated (audit m7)
    for (cell, _draw, _panel), a in acc.items():
        if a < UNDERTRAINED_BELOW - C.EPS:
            low[cell] = min(low.get(cell, 1.0), a)
    undertrained = sorted(low)
    return {"undertrained_cells": undertrained, "min_a_use_of_undertrained": low, "annotations": C.h8_annotations(undertrained, calibrated), "calibrated_cells": calibrated}


# --- D-OQ's learning rate (item 3) ------------------------------------------------------------------------------------------------------------------
def tie_snapshots(readout: int) -> tuple[int, ...]:
    """readout/2, /4, /8, /16: the doubling grid the tie rule walks down (a snapshot below 1 update does not exist)."""
    return tuple(readout // d for d in (2, 4, 8, 16) if readout % d == 0 and readout // d >= 1)


def select_dense_rate(readout_a_use: Mapping[float, float], a_use: Mapping[float, Mapping[int, float]] | None = None, readout: int = core.U_P, diverged: Sequence[float] = ()) -> dict[str, Any]:
    """Item 3 for one unit (ADR-0021 section 10.1, with the rulings of sections 22 M7 and 25.12). ``readout_a_use[rate]`` is the minimum Panel A a_use over the two draws at the readout;
    ``a_use[rate][update]`` the same at the walk's snapshots; ``diverged`` the rates left out (run failed, or raw Panel A count inside the chance interval on either draw).

    * every rate diverged -> RETURN_TO_LEAD;
    * the highest readout among the rest is the top rate (0.1) by 0.02 or more over the next one (or alone) -> RETURN_TO_LEAD (the boundary is on the returning side, ruling m2) (the best rate is at the edge of the grid; no further rate is tried);
    * else the rates within 0.02 of the best are separated by the walk of section 22 M7 and 22.1 (a_use at readout/2, /4, down to /16; at each snapshot keep those within 0.02 of the best there;
      if one remains it wins); if several remain at readout/16 the smallest rate is taken;
    * a 0.1 chosen only by the walk (it was one of several contenders) is recorded EDGE BY TIE-WALK."""
    top_rate = max(core.DENSE_RATES)
    live = {r: v for r, v in readout_a_use.items() if r not in set(diverged)}
    base: dict[str, Any] = {"readout_a_use": {str(k): v for k, v in readout_a_use.items()}, "diverged": [float(r) for r in sorted(set(diverged))], "readout": readout}
    if not live:
        return {"rate": None, "action": RETURN_TO_LEAD, "reason": "every rate diverged", "edge": None, **base}
    ordered = sorted(live.items(), key=lambda kv: (-kv[1], kv[0]))
    best_rate, best = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else None
    if best_rate == top_rate and (second is None or best - second >= core.DENSE_TIE_DIFFERENCE - C.EPS):
        reason = f"the top rate {top_rate} has the highest readout ({best:.3f}) " + ("and no other rate is left" if second is None else f"by {core.DENSE_TIE_DIFFERENCE} or more over the next ({second:.3f})")
        return {"rate": None, "action": RETURN_TO_LEAD, "reason": reason, "edge": "TOP OF GRID", **base}
    contenders = sorted(r for r, a in ordered if best - a < core.DENSE_TIE_DIFFERENCE - C.EPS or r == best_rate)
    base["contenders"] = list(contenders)
    if len(contenders) == 1:
        return {"rate": best_rate, "action": GRID_STANDS, "decided_by": "readout a_use", "edge": None, **base}
    if a_use is None or any(r not in a_use for r in contenders):
        raise TieNeedsLead(f"rates {contenders} are within {core.DENSE_TIE_DIFFERENCE} at the readout and the doubling-snapshot a_use the tie walk needs are missing")
    walked: list[dict[str, Any]] = []
    for u in tie_snapshots(readout):
        if any(u not in a_use[r] for r in contenders):
            raise TieNeedsLead(f"the doubling snapshot {u} is missing for a tied rate")
        vals = {r: a_use[r][u] for r in contenders}
        walked.append({"update": u, "a_use": {str(r): v for r, v in vals.items()}})
        top = max(vals.values())
        contenders = sorted(r for r, v in vals.items() if top - v < core.DENSE_TIE_DIFFERENCE - C.EPS)
        if len(contenders) == 1:
            rate = contenders[0]
            return {"rate": rate, "action": GRID_STANDS, "decided_by": f"faster learner: a_use at {u}", "walk": walked, "edge": EDGE_BY_TIE_WALK if rate == top_rate else None, **base}
    rate = min(contenders)
    return {"rate": rate, "action": GRID_STANDS, "decided_by": "smaller learning rate (no snapshot separates the tied rates by 0.02)", "walk": walked, "edge": EDGE_BY_TIE_WALK if rate == top_rate else None, **base}


# --- reading the calibration cells -----------------------------------------------------------------------------------------------------------------------
def read_obs(run_dir: Path, cell: core.Cell) -> dict[int, dict[str, C.PanelObs]]:
    """``{update: {panel: PanelObs}}`` of a calibration cell from its eval records (a missing record raises ``FileNotFoundError``)."""
    out: dict[int, dict[str, C.PanelObs]] = {}
    for u in calibration_snapshots(cell):
        rec = core.read_record(core.eval_path(run_dir, cell.label, u), "eval")
        out[u] = {p: A.obs_from_panel(rec["reads"]["main"]["panels"][p]) for p in core.PANELS}
    return out


def read_train(run_dir: Path, cell: core.Cell) -> dict[str, Any] | None:
    path = core.cell_dir(run_dir, cell.label) / "train.json"
    return core.read_record(path, "train") if path.is_file() else None


def _read_or_none(run_dir: Path, cell: core.Cell) -> tuple[dict[int, dict[str, C.PanelObs]] | None, str]:
    """The observations of a cell, or None with the reason (no train record, a failed run, a run stopped at its item cap, missing evaluation records)."""
    train = read_train(run_dir, cell)
    if train is None:
        return None, "no train record (not run)"
    if train.get("status") != "completed":
        reason = str(train.get("reason") or "")
        return None, (f"{STOPPED_BY_CAP}: stopped at its item cap" if "ItemCapReached" in reason else f"run ended {train.get('status')!r}")
    try:
        return read_obs(run_dir, cell), ""
    except FileNotFoundError as exc:
        return None, f"no evaluation record: {exc}"


def _views_of_arm(run_dir: Path, arm: str, facts: int, slots: int, unit: int) -> tuple[dict[tuple[int, str], C.View] | None, dict[int, str]]:
    cells = [c for c in core.load_search_cells(unit) if c.arm == arm and (c.facts, c.slots) == (facts, slots)]
    views: dict[tuple[int, str], C.View] = {}
    notes: dict[int, str] = {}
    for c in cells:
        obs, why = _read_or_none(run_dir, c)
        if obs is None:
            notes[c.draw] = why
            continue
        for p in core.PANELS:
            views[(c.draw, p)] = C.View({u: o[p] for u, o in obs.items()}, c.run_updates, unit)
    return (views if len(views) == 4 else None), notes


def run_flag(why: str) -> str | None:
    """STOPPED BY CAP or NOT RUN — DRIVER STOPPED for the reason a cell could not be read; None for an ordinary failed run."""
    if STOPPED_BY_CAP in why:
        return STOPPED_BY_CAP
    if why.startswith("no train record"):
        return NOT_RUN_DRIVER
    return None


def _failing_candidates(views: Mapping[tuple[int, str], C.View] | None, candidates: Sequence[int]) -> list[dict[str, Any]]:
    """For the record that returns to the human lead: for each candidate, which views fail which condition (curves are in the cells' records)."""
    out: list[dict[str, Any]] = []
    for u in candidates:
        row: dict[str, Any] = {"candidate": u, "views": {}}
        for (d, p), v in (views or {}).items():
            if u not in v.obs or u // 2 not in v.obs:
                row["views"][f"d{d}{p}"] = "no snapshot"
                continue
            sub = C.View({k: o for k, o in v.obs.items() if k <= u}, u, v.u_p, memory=v.memory)
            hi, half = sub.i_star(u)[0], sub.i_star(u // 2)[0]
            row["views"][f"d{d}{p}"] = {"i_star": hi, "i_star_half": half, "gain_flat": sub.gain_flat(), "above_floor": sub.above_floor(), "i_at_most_4": C.le(hi, core.LOADED_I_MAX)}
        out.append(row)
    return out


def finalize_load_and_row_up(run_dir: Path, *, unit: int = core.U_P, dry: bool = False) -> dict[str, Any]:
    """Items 0b and 1 applied to the finished records: U_L per loaded cell (with the fixed outcomes), U_L of 2K/256 or its absence, U_P per row, and the list of returns. A run that is missing,
    failed or stopped at its item cap is an input (no U_L). Nothing is decided while runs are in progress: this reads the finished record."""
    load: dict[str, Any] = {}
    returns: list[str] = []
    for facts, slots in core.LOADED_CELLS:
        name = core.cell_name(facts, slots)
        cands = core.load_candidates(name, unit)
        per_arm: dict[str, Any] = {}
        u_l: dict[str, int | None] = {}
        for arm in ("F-OQ", "T-OQ"):
            views, notes = _views_of_arm(run_dir, arm, facts, slots, unit)
            u_l[arm] = arm_u_l(views, cands)
            per_arm[arm] = {"u_l": u_l[arm], "run_notes": notes, "candidates": list(cands), "failed_conditions": [] if u_l[arm] is not None else _failing_candidates(views, cands)}
        out = cell_outcome(u_l["F-OQ"], u_l["T-OQ"])
        flags = {arm: sorted({f for w in per_arm[arm]["run_notes"].values() if (f := run_flag(w))}) for arm in per_arm}
        if any(flags.values()):  # a run stopped by its cap or never run is not 'not loaded': the cell returns to the lead with that label
            label = "; ".join(f"{arm}: {', '.join(v)}" for arm, v in flags.items() if v)
            out = {"action": RETURN_TO_LEAD, "u_l": None, "toq_predicted_not_loaded": False, "status": label, "note": "a run was stopped by its item cap or never run: the cell returns to the human lead and is neither loaded nor not loaded"}
            load[name] = {**out, "arms": per_arm}
            returns.append(f"{name}: {label}; the cell returns to the human lead")
            continue
        load[name] = {**out, "arms": per_arm}
        if out["action"] == RETURN_TO_LEAD:
            returns.append(f"{name}: {NOT_LOADED_WITHIN_CEILING} (F-OQ has no U_L); the record returns to the human lead before the freeze")
    sat_views, sat_notes = _views_of_arm(run_dir, "F-OQ", *core.SATURATION_ONLY_CELL, unit)
    sat_cands = core.load_candidates(core.SATURATION_CELL_NAME, unit)
    sat = saturation_cell_outcome(arm_u_l(sat_views, sat_cands))
    sat_flags = sorted({f for w in sat_notes.values() if (f := run_flag(w))})
    if sat_flags:
        sat = {"action": RETURN_TO_LEAD, "u_l": None, "runs": False, "status": ", ".join(sat_flags), "note": "a run was stopped by its item cap or never run: 2K/256 returns to the human lead"}
        returns.append(f"2K/256: {', '.join(sat_flags)}; the cell returns to the human lead")
    sat["run_notes"] = sat_notes
    sat["failed_conditions"] = [] if sat["u_l"] is not None else _failing_candidates(sat_views, sat_cands)
    rows: dict[str, Any] = {}
    row_cells = core.row_u_p_cells(unit)
    for facts in core.ROW_FACTS:
        foq_acc: dict[tuple[int, int, str], float] = {}
        r2_acc: dict[tuple[int, int, str], float] = {}
        row_flags: set[str] = set()
        for cell in (c for c in row_cells if c.facts == facts):
            obs, why = _read_or_none(run_dir, cell)
            if obs is None:
                if (f := run_flag(why)) is not None:
                    row_flags.add(f)
                continue
            acc = foq_acc if cell.arm == "F-OQ" else r2_acc
            for u, per in obs.items():
                for p in core.PANELS:
                    acc[(u, cell.draw, p)] = per[p].a_use  # a_use, as REF uses (section 22 (j))
        rows[str(facts)] = row_u_p(foq_acc, r2_acc, core.row_u_p_candidates(unit))
        if row_flags:
            rows[str(facts)] = {"u_p": None, "action": RETURN_TO_LEAD, "reason": ", ".join(sorted(row_flags)) + ": a run of this row was stopped by its item cap or never run"}
        if rows[str(facts)]["action"] == RETURN_TO_LEAD:
            returns.append(f"row of {facts} facts: {rows[str(facts)]['reason']}; the work returns to the human lead before the freeze")
    substituted: list[str] = []
    if dry:  # the DRY profile (tiny synthetic sizes) proceeds on placeholders where a rule gives nothing; the record says so and carries no return (never used for a registered freeze)
        for name, entry in load.items():
            if entry["u_l"] is None:
                entry.update(u_l=core.load_candidates(name, unit)[0], action=GRID_STANDS)
                substituted.append(f"u_l {name}")
        if sat["u_l"] is None:
            sat.update(u_l=core.load_candidates(core.SATURATION_CELL_NAME, unit)[0], runs=True)
            substituted.append("u_l 2K/256")
        for row_name, entry in rows.items():
            if entry.get("u_p") is None:
                entry.update(u_p=core.row_u_p_candidates(unit)[0], action=GRID_STANDS)
                substituted.append(f"u_p row {row_name}")
        returns = []
    return core.jsonable({"load": load, "saturation_256": sat, "row_u_p": rows, "returns_to_lead": returns, "unit": unit, "dry_substituted": substituted})


def row_u_p_map(items_record: Mapping[str, Any]) -> dict[int, int]:
    """``{facts: U_P}`` from a record of ``finalize_load_and_row_up`` (refuses while a row has none: items 2 and 3 need it)."""
    out: dict[int, int] = {}
    for facts in core.ROW_FACTS:
        entry = items_record["row_u_p"][str(facts)]
        if entry.get("u_p") is None:
            raise TieNeedsLead(f"the row of {facts} facts has no U_P: items 2 and 3 cannot start (a return to the human lead is open)")
        out[facts] = int(entry["u_p"])
    return out


def _chance_diverged(obs: Mapping[int, Mapping[str, C.PanelObs]], readout: int) -> bool:
    p = obs[readout]["A"]
    return core.at_chance(p.correct, p.n)


def finalize_h8_dense(run_dir: Path, row_map: Mapping[int, int], *, unit: int = core.U_P, dry: bool = False) -> dict[str, Any]:
    """Items 2 and 3 applied to the finished records: H8's UNDERTRAINED-AT-U_P cells and annotations, and D-OQ's rate per unit with diverged rates left out."""
    h8: dict[tuple[str, int, str], float] = {}
    h8_returns: list[str] = []
    for cell in core.h8_report_cells(row_map, unit):
        obs, why = _read_or_none(run_dir, cell)
        if obs is None:
            if (f := run_flag(why)) is not None:
                h8_returns.append(f"H8 {cell.name} draw {cell.draw}: {f}")
            continue
        for p in core.PANELS:
            h8[(cell.name, cell.draw, p)] = obs[cell.run_updates][p].a_use
    dense: dict[str, Any] = {}
    returns: list[str] = []
    for name in core.DENSE_UNITS:
        readout = core.dense_readout(name, row_map, unit)
        readout_a: dict[float, float] = {}
        traj: dict[float, dict[int, float]] = {}
        diverged: set[float] = set()
        notes: dict[str, str] = {}
        no_record: list[str] = []
        capped: list[str] = []
        for lr in core.DENSE_RATES:
            cells = [c for c in core.dense_rate_cells(row_map, unit) if c.lr == lr and core.dense_unit_of(c.facts, c.slots) == name]
            for c in cells:
                obs, why = _read_or_none(run_dir, c)
                if obs is None and read_train(run_dir, c) is None:  # a run without a record is not a diverged rate (section 25.12 item 3): the unit returns
                    no_record.append(c.label)
                    notes[f"{lr:g}:d{c.draw}"] = why
                    continue
                if obs is None and run_flag(why) == STOPPED_BY_CAP:  # never read as diverged
                    capped.append(c.label)
                    notes[f"{lr:g}:d{c.draw}"] = why
                    continue
                if obs is None:
                    diverged.add(lr)
                    notes[f"{lr:g}:d{c.draw}"] = why
                    continue
                if _chance_diverged(obs, readout):
                    diverged.add(lr)
                    notes[f"{lr:g}:d{c.draw}"] = "raw Panel A count inside the chance interval at the readout"
                readout_a[lr] = min(obs[readout]["A"].a_use, readout_a.get(lr, 1.0))
                t = traj.setdefault(lr, {})
                for u, per in obs.items():
                    t[u] = min(per["A"].a_use, t.get(u, 1.0))
        for lr in core.DENSE_RATES:
            readout_a.setdefault(lr, 0.0)
        try:
            if capped:
                entry = {"rate": None, "action": RETURN_TO_LEAD, "reason": f"{STOPPED_BY_CAP}: runs stopped by their item cap (never read as diverged): {capped}", "edge": None, "diverged": sorted(diverged)}
            elif no_record:
                entry = {"rate": None, "action": RETURN_TO_LEAD, "reason": f"runs without a record (not started or killed): {no_record}", "edge": None, "diverged": sorted(diverged)}
            else:
                entry = select_dense_rate(readout_a, traj, readout, sorted(diverged))
        except TieNeedsLead as exc:
            entry = {"rate": None, "action": RETURN_TO_LEAD, "reason": str(exc), "edge": None, "diverged": sorted(diverged)}
        entry["diverged_notes"] = notes
        if dry and entry["action"] == RETURN_TO_LEAD:  # DRY placeholder (see finalize_load_and_row_up)
            entry.update(rate=core.LEARNING_RATE, action=GRID_STANDS, dry_substituted=True)
        dense[name] = entry
        if entry["action"] == RETURN_TO_LEAD:
            returns.append(f"D-OQ's rate, unit {name}: {entry['reason']}")
    return core.jsonable({"h8": h8_report(h8), "dense_rates": dense, "returns_to_lead": [*h8_returns, *returns]})


def seconds_per_update(run_dir: Path, cells: Sequence[core.Cell]) -> dict[str, Any]:
    """The measured six-worker training wall seconds per update of every calibration configuration (arm and slot count), the largest per configuration, and the charged seconds (the sum of the
    cells' training wall seconds): the inputs of the contention ratio c (section 10.3)."""
    per: dict[str, float] = {}
    total = 0.0
    for c in cells:
        train = read_train(run_dir, c)
        if train is None or train.get("status") != "completed":
            continue
        done = max(1, int(train.get("run_updates") or c.run_updates))
        wall = float(train["wall_seconds"])
        total += wall
        key = f"{c.arm}|{c.slots}"
        per[key] = max(per.get(key, 0.0), wall / done)
    return {"training_wall_seconds_per_update": dict(sorted(per.items())), "training_wall_seconds_total": total}


def finalize(run_dir: Path, *, unit: int = core.U_P, charged_seconds: float | None = None) -> dict[str, Any]:
    """The calibration record (kind ``calibration``): U_L per loaded cell and for 2K/256, U_P per row, H8's annotations, D-OQ's rate per unit, the list of returns, the measured six-worker training seconds
    per update of every calibration configuration and the charged seconds. Recomputed from the raw records; refuses (``TieNeedsLead``) while items 2 and 3 cannot be read because a row has no U_P."""
    dry = unit != core.U_P
    first = finalize_load_and_row_up(run_dir, unit=unit, dry=dry)
    returns = list(first["returns_to_lead"])
    second: dict[str, Any] = {"h8": None, "dense_rates": None, "returns_to_lead": []}
    row_map: dict[int, int] | None = None
    if not first["returns_to_lead"]:
        row_map = row_u_p_map(first)
        second = finalize_h8_dense(run_dir, row_map, unit=unit, dry=dry)
        returns += second["returns_to_lead"]
    cells = core.calibration_cells(row_map, unit)
    cost = seconds_per_update(run_dir, cells)
    u_l = {n: v["u_l"] for n, v in first["load"].items()}
    return core.jsonable({
        **core.envelope("calibration"), "load": first["load"], "u_l": u_l, "saturation_256": first["saturation_256"], "u_l_256": first["saturation_256"]["u_l"], "row_u_p": first["row_u_p"],
        "toq_predicted_not_loaded": sorted(n for n, v in first["load"].items() if v["toq_predicted_not_loaded"]), "h8": second["h8"], "dense_rates": second["dense_rates"],
        "h8_undertrained_cells": [] if second["h8"] is None else second["h8"]["undertrained_cells"], "returns_to_lead": returns, "readings": C.READINGS,
        "calibration_accuracy_note": "calibration accuracies are reported as calibration, never as results", **cost,
        "charged_seconds": cost["training_wall_seconds_total"] if charged_seconds is None else charged_seconds, "dry": dry, "dry_substituted": first.get("dry_substituted", []),
        "identity": core.code_identity(), "source_hashes": core.source_hashes(), "environment": core.environment(),
    })  # fmt: skip


def plan_values(record: Mapping[str, Any]) -> dict[str, Any]:
    """The plan fields the calibration fixes (``core.Plan`` keywords): row U_P, U_L of the loaded cells, U_L of 2K/256 and its presence, the T-OQ flags. Refuses while a return is open."""
    if record.get("returns_to_lead"):
        raise TieNeedsLead(f"the calibration has open returns to the human lead: {record['returns_to_lead']}")
    sat = record["saturation_256"]
    return {
        "row_u_p": tuple(int(record["row_u_p"][str(f)]["u_p"]) for f in core.ROW_FACTS), "u_l": tuple(int(record["u_l"][core.cell_name(*c)]) for c in core.LOADED_CELLS),
        "u_l_256": int(sat["u_l"]) if sat["runs"] else 0, "sat256": bool(sat["runs"]), "toq_not_loaded": tuple(record["toq_predicted_not_loaded"]),
    }


def dense_rates_of(record: Mapping[str, Any]) -> dict[str, float]:
    """D-OQ's calibrated learning rate by unit ('4096', '16384', '8K/1K', '32K/4K'); refuses when a rate is undecided."""
    rates: dict[str, float] = {}
    for name in core.DENSE_UNITS:
        entry = (record.get("dense_rates") or {}).get(name)
        if entry is None or entry.get("rate") is None:
            raise TieNeedsLead(f"no D-OQ rate decided for unit {name}")
        rates[name] = float(entry["rate"])
    return rates


def read_items_record(path: Path) -> dict[str, Any]:
    rec = read_json(path)
    if not isinstance(rec, dict):
        raise ValueError(f"not a record: {path}")
    return rec
