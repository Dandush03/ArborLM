# ruff: noqa: E501
"""Part T labels (ADR-0025 sections 1, 8.3, 8.4, 8.5, 8.6): the study status, the six registered lines, the milestone line and the descriptive MODIFICATION line, as pure functions over a registry.

Order of reading: the study status first. Under ENGINEERING-FAILURE, ENGINEERING STOP (item errors, a non-finite value, a recomputation difference) or INCOMPLETE no line is derived. The NOT EVALUABLE clauses
that name a missing, non-finite or recomputation-failed value are a second guard: no rule turns such a value into a pass or into a measured failure. "Every cell" means all six (three replicates x two orders).
No result printed BY CONSTRUCTION (E-table, M-sep, D-sep) satisfies any rule: none of them is read by a rule below except as the lookup baseline E-table, which AGAINST-LOOKUP names.
"""

from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from .common import core
from .quantities import (
    CELLS,
    CONTROL_CONDITIONS,
    GEN_POSITIONS,
    NONE,
    ORDERS,
    REPLICATES,
    Quantities,
    Registry,
    cells_where,
    first,
    second,
)

OK = "OK"
ENGINEERING_FAILURE = "ENGINEERING-FAILURE"
STOP_ITEMS = "ENGINEERING STOP — ITEM ERRORS"
STOP_NONFINITE = "ENGINEERING STOP — NON-FINITE VALUE"
STOP_RECOMPUTATION = "ENGINEERING STOP — RECOMPUTATION"
INCOMPLETE = "INCOMPLETE"
LOOKUPS = ("R-gloss", "R-gloss-icl", "R-nn", "R-icl", "E-table")
MEMORY_CONTROL_ARMS = ("M1", "M-append", "M-seq", "M-ii", "M-joint")


def study_status(reg: Registry, *, item_errors: Sequence[str] = (), recompute_failed: Collection[Any] = (), engineering_failure: Sequence[str] = (), required: Collection[str] = ()) -> dict[str, Any]:
    """Section 8.6. An engineering stop is never a scientific label; INCOMPLETE is a registered record missing after the run with no error recorded for it (no denominator is reduced)."""
    if engineering_failure:
        return {"status": ENGINEERING_FAILURE, "why": "; ".join(engineering_failure), "derive": False}
    if item_errors:
        return {"status": STOP_ITEMS, "why": f"{len(item_errors)} item error(s) recorded: {'; '.join(item_errors[:3])}", "derive": False}
    bad = reg.nonfinite()
    if bad:
        return {"status": STOP_NONFINITE, "why": f"non-finite value(s) in {len(bad)} registered record(s): {', '.join(bad[:3])}; the cell is not resumed", "derive": False}
    if recompute_failed:
        return {"status": STOP_RECOMPUTATION, "why": f"recomputation beyond tolerance in {sorted(map(str, recompute_failed))[:4]}; no line, condition or annotation is derived", "derive": False}
    missing = sorted(k for k in required if k not in reg.values)
    if missing:
        return {"status": INCOMPLETE, "why": f"{len(missing)} registered record(s) missing and no error recorded for them, e.g. {missing[:3]}; no denominator is reduced", "derive": False}
    return {"status": OK, "why": "", "derive": True}


def per_cell(q: Quantities, fn: Any) -> list[tuple[int, str, Any]]:
    return [(r, o, fn(r, o)) for r, o in CELLS]


# --- ACQUISITION -------------------------------------------------------------------------------------------------------------------------------
def acquisition(q: Quantities, recompute_failed: Collection[Any] = ()) -> dict[str, Any]:
    th = q.th
    if not q.gap_defined() or recompute_failed:
        return {"label": "NOT EVALUABLE", "why": "a gap is undefined on E_A or E_B, or a cell it reads failed recomputation", "table": None}
    g1 = {(r, o): q.G_first("M1", o, r) for r, o in CELLS}
    g2 = {(r, o): q.G_second("M-append", o, r) for r, o in CELLS}
    acq1 = {(r, o): q.acq1(o, r) for r, o in CELLS}
    acq2 = {(r, o): q.acq2("M-append", o, r) for r, o in CELLS}
    undefined = sorted((r, o, c) for r, o in CELLS for c in (first(o), second(o)) if not q.controls_defined(c))
    table = {"G_first(M1)": {f"{r}{o}": g1[(r, o)] for r, o in CELLS}, "G_second(M-append)": {f"{r}{o}": g2[(r, o)] for r, o in CELLS}, "ACQ1": {f"{r}{o}": acq1[(r, o)] for r, o in CELLS}, "ACQ2": {f"{r}{o}": acq2[(r, o)] for r, o in CELLS},
             "CONTROLS UNDEFINED": [f"{r}{o}:{c}" for r, o, c in undefined]}  # fmt: skip
    first_neg = all(g1[k] is not None and g1[k] < th.negative_acquisition for k in g1)  # type: ignore[operator]
    second_neg = all(g2[k] is not None and g2[k] < th.negative_acquisition for k in g2)  # type: ignore[operator]
    if first_neg or second_neg:
        who = "FIRST TEACHER; SECOND TEACHER" if first_neg and second_neg else ("FIRST TEACHER" if first_neg else "SECOND TEACHER")
        return {"label": f"ACQUISITION-NEGATIVE ({who})", "table": table}
    failed = []
    for arm in MEMORY_CONTROL_ARMS:
        for r, o in CELLS if arm != "M-joint" else [(r, NONE) for r in REPLICATES]:
            for c in q.control_gap_reads(arm, o if o != NONE else "AB"):
                if not q.controls_defined(c):
                    continue  # CONTROLS UNDEFINED: CONTROL-FAILED does not fire on it
                order = o if o != NONE else NONE
                for cond in ("value", "code"):
                    g = q.G_sub(arm, order, r, c, cond)
                    if g is not None and g >= th.control_failed_gap:
                        failed.append(f"{arm} {r}{o} {cond}-permuted on {c}: G {g:.3f}")
    if failed:
        return {"label": "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED", "why": "; ".join(failed[:4]), "table": table}
    if all(acq1.values()) and all(acq2.values()):
        return {"label": "ACQUISITION-POSITIVE", "table": table}
    return {"label": "ACQUISITION-INCONCLUSIVE", "passing_cells_per_order": {"ACQ1": cells_where((r, o, acq1[(r, o)]) for r, o in CELLS), "ACQ2": cells_where((r, o, acq2[(r, o)]) for r, o in CELLS)}, "table": table}


# --- RETENTION ---------------------------------------------------------------------------------------------------------------------------------
def forgetting_pressure(q: Quantities) -> dict[str, Any]:
    """In at least 4 of the 6 cells: G_second(M-seq) >= 0.50 and rho(M-seq) < 0.90 (rho must be defined). D-seq's rho is printed beside it and does not count."""
    th = q.th
    holds = []
    for r, o in CELLS:
        g2, rho = q.G_second("M-seq", o, r), q.rho("M-seq", o, r)
        holds.append(g2 is not None and rho is not None and g2 >= th.forgetting_pressure_second_min and rho < th.forgetting_pressure_rho_max)
    return {"holds": sum(holds) >= th.forgetting_pressure_cells, "cells": sum(holds), "d_seq_rho": {f"{r}{o}": q.rho("D-seq", o, r) for r, o in CELLS}, "m_seq_rho": {f"{r}{o}": q.rho("M-seq", o, r) for r, o in CELLS}}


def retention(q: Quantities, recompute_failed: Collection[Any] = ()) -> dict[str, Any]:
    th = q.th
    if not q.gap_defined() or recompute_failed:
        return {"label": "NOT EVALUABLE: GAP UNDEFINED / RECOMPUTATION", "table": None}
    evaluable = [(r, o) for r, o in CELLS if q.evaluable("M-append", o, r)]
    rho = {f"{r}{o}": q.rho("M-append", o, r) for r, o in CELLS}
    table = {
        "G_first(M1)": {f"{r}{o}": q.G_first("M1", o, r) for r, o in CELLS}, "ACQ1": {f"{r}{o}": q.acq1(o, r) for r, o in CELLS}, "G_second(M-append)": {f"{r}{o}": q.G_second("M-append", o, r) for r, o in CELLS},
        "F": {f"{r}{o}": q.forgetting("M-append", o, r) for r, o in CELLS}, "rho": rho, "evaluable_cells": len(evaluable), "evaluable_cells_in_negative_zone": sum(1 for r, o in evaluable if (q.rho("M-append", o, r) or 0.0) < th.negative_retention),
    }  # fmt: skip
    if len(evaluable) >= th.retention_negative_min_cells and all((q.rho("M-append", o, r) or 0.0) < th.negative_retention for r, o in evaluable):
        return {"label": "RETENTION-NEGATIVE: FORGETTING", "table": table}
    if not all(q.acq1(o, r) for r, o in CELLS):
        return {"label": "NOT EVALUABLE: FIRST NOT ACQUIRED", "table": table}
    if any((q.G_second("M-append", o, r) is None or q.G_second("M-append", o, r) < th.second_not_acquired) for r, o in CELLS):  # type: ignore[operator]
        return {"label": "RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED", "table": table}
    fp = forgetting_pressure(q)
    table["forgetting_pressure"] = fp
    if not fp["holds"]:
        return {"label": "RETENTION-INCONCLUSIVE: NOT CHALLENGED — NO FORGETTING PRESSURE", "table": table}
    if all(q.ret("M-append", o, r) for r, o in CELLS):
        return {"label": "RETENTION-POSITIVE", "table": table}
    return {"label": "RETENTION-INCONCLUSIVE", "table": table}


# --- GENERAL-QUALITY ----------------------------------------------------------------------------------------------------------------------------
def general_quality(q: Quantities, arm: str = "M-append") -> dict[str, Any]:
    """PRESERVED if, for the arm's stage-2 snapshot in every cell and under both decision positions, the loss increase over the unmodified student is <= 0.02 nats per token. NOT PRESERVED if every reading is
    recorded and finite and one exceeds 0.02. NOT EVALUABLE if a reading is missing or non-finite (never NOT PRESERVED)."""
    vals: dict[str, float] = {}
    for r, o in CELLS:
        for pos in GEN_POSITIONS:
            k = f"{r}{o}:{pos}"
            if not q.reg.has(arm, o, r, f"gen:{pos}"):
                return {"label": "NOT EVALUABLE", "why": f"a GEN reading is missing ({k})", "readings": vals}
            v = q.reg.get(arm, o, r, f"gen:{pos}")
            if v != v or v in (float("inf"), float("-inf")):
                return {"label": "NOT EVALUABLE", "why": f"a GEN reading is not finite ({k})", "readings": vals}
            vals[k] = v
    over = {k: v for k, v in vals.items() if v > q.th.gen_loss_margin}
    if over:
        return {"label": "NOT PRESERVED", "readings": vals, "over": over}
    return {"label": "PRESERVED", "note": "the keyword router stayed silent", "readings": vals}


# --- AGAINST-DENSE -------------------------------------------------------------------------------------------------------------------------------
def delta_label(deltas: Sequence[float], margin: float) -> str:
    if all(d >= margin for d in deltas):
        return "MEMORY AHEAD"
    if all(d <= -margin for d in deltas):
        return "DENSE AHEAD"
    if all(abs(d) < margin for d in deltas):
        return "NOT DISTINGUISHED"
    return "MIXED"


def against_dense(q: Quantities, m: str = "M-append", d: str = "D-append") -> dict[str, Any]:
    """Two quantities, two labels, never merged: dG = G_second(m) - G_second(d) and drho = rho(m) - rho(d) (guard: NOT EVALUABLE if, in any cell, either arm's rho is undefined or either arm has G_second below 0.50)."""
    th = q.th
    if not q.gap_defined():
        return {"acquisition": "NOT EVALUABLE", "retention": "NOT EVALUABLE", "value": "acquisition: NOT EVALUABLE; retention: NOT EVALUABLE"}
    dg, guard = [], False
    for r, o in CELLS:
        gm, gd = q.G_second(m, o, r), q.G_second(d, o, r)
        if gm is None or gd is None:
            return {"acquisition": "NOT EVALUABLE", "retention": "NOT EVALUABLE", "value": "acquisition: NOT EVALUABLE; retention: NOT EVALUABLE"}
        dg.append(gm - gd)
        rm, rd = q.rho(m, o, r), q.rho(d, o, r)
        if rm is None or rd is None or gm < th.second_not_acquired or gd < th.second_not_acquired:
            guard = True
    drho = None if guard else [q.rho(m, o, r) - q.rho(d, o, r) for r, o in CELLS]  # type: ignore[operator]
    acq = delta_label(dg, th.dense_margin)
    ret = "NOT EVALUABLE" if drho is None else delta_label(drho, th.dense_margin)
    return {"acquisition": acq, "retention": ret, "value": f"acquisition: {acq}; retention: {ret}", "delta_G": dg, "delta_rho": drho}


# --- AGAINST-LOOKUP -----------------------------------------------------------------------------------------------------------------------------
def against_lookup(q: Quantities, arm: str = "M-append") -> dict[str, Any]:
    """b is the best score among R-gloss, R-gloss-icl, R-nn, R-icl and E-table, per cell and capability. LOOKUP SUFFICES if b >= s(arm) - 0.03 on both capabilities in every cell; MEMORY ADDS OVER LOOKUP if
    s(arm) - b >= 0.05 on both capabilities in every cell; MIXED otherwise. The baseline that gave b is named FOR EACH CELL AND CAPABILITY (ruling 5): one name if the same baseline gave b in every reading, otherwise the list per cell and capability; every reading is listed."""
    th = q.th
    gave: Counter[str] = Counter()
    suff, adds = [], []
    readings = []
    for r, o in CELLS:
        ok_s, ok_a = [], []
        for c in core.TASKS:
            s = q.score(arm, o, r, c)
            cand = {b: q.reg.get(b, NONE, r, f"s:{('E_A' if c == 'A' else 'E_B')}") for b in LOOKUPS}
            best = max(cand, key=lambda b: (cand[b], b))
            gave[best] += 1
            readings.append({"cell": f"{r}{o}", "capability": c, "best": best, "b": cand[best], "s": s})
            ok_s.append(cand[best] >= s - th.lookup_sufficient_margin)
            ok_a.append(s - cand[best] >= th.lookup_adds_margin)
        suff.append(all(ok_s))
        adds.append(all(ok_a))
    per_cell = {f"{x['cell']}/{x['capability']}": x["best"] for x in readings}
    name = next(iter(gave)) if len(gave) == 1 else "per cell and capability: " + ", ".join(f"{k} {v}" for k, v in per_cell.items())
    if all(suff):
        return {"label": "LOOKUP SUFFICES", "baseline": name, "per_cell": per_cell, "line": f"a lookup baseline does as well: {name}", "readings": readings}
    if all(adds):
        return {"label": "MEMORY ADDS OVER LOOKUP", "baseline": name, "per_cell": per_cell, "readings": readings}
    return {"label": "MIXED", "baseline": name, "per_cell": per_cell, "readings": readings}


# --- MODIFICATION (M-ii), descriptive -------------------------------------------------------------------------------------------------------------
def modification(q: Quantities, recompute_failed: Collection[Any] = ()) -> dict[str, Any]:
    """First match: CONSOLIDATION-REJECTED (count printed) if any cell failed the D_con constraint (chrF on D_con of each capability at least M-append's minus 0.02); NOT EVALUABLE if fewer than four cells are
    evaluable for M-ii or a cell failed recomputation; FORGETS UNDER MODIFICATION if rho < 0.70 in every evaluable cell; RETENTION BY INERTIA if ACQ2 and RET pass in every cell and any cell is below the
    modification floor; RETAINS UNDER MODIFICATION if ACQ2 and RET pass in every cell; INTERMEDIATE otherwise. In a rejected cell M-ii's snapshot for every other reading is the pinned M-append snapshot."""
    th = q.th
    rejected = [(r, o) for r, o in CELLS if any(q.reg.get("M-ii", o, r, f"dcon:{c}") < q.reg.get("M-append", o, r, f"dcon:{c}") - th.modification_dcon_tolerance for c in core.TASKS)]
    if rejected:
        return {"label": "CONSOLIDATION-REJECTED", "count": len(rejected), "cells": [f"{r}{o}" for r, o in rejected], "pinned_append_snapshot_used_in_rejected_cells": True}
    ev = [(r, o) for r, o in CELLS if q.evaluable("M-ii", o, r)]
    if len(ev) < th.retention_negative_min_cells or recompute_failed:
        return {"label": "NOT EVALUABLE", "evaluable_cells": len(ev)}
    if all((q.rho("M-ii", o, r) or 0.0) < th.negative_retention for r, o in ev):
        return {"label": "FORGETS UNDER MODIFICATION", "evaluable_cells": len(ev)}
    passes = all(q.acq2("M-ii", o, r) and q.ret("M-ii", o, r) for r, o in CELLS)
    if passes and any(q.reg.get("M-ii", o, r, "modification") < th.modification_floor for r, o in CELLS):
        return {"label": "RETENTION BY INERTIA"}
    if passes:
        return {"label": "RETAINS UNDER MODIFICATION"}
    return {"label": "INTERMEDIATE"}


def gen_of_arm_passes(q: Quantities, arm: str) -> bool | None:
    """True if the arm's GEN check passes in every cell, False if one fails, None if a reading is not evaluable (the suffix is not given then)."""
    g = general_quality(q, arm)
    return None if g["label"] == "NOT EVALUABLE" else g["label"] == "PRESERVED"


# --- milestone ------------------------------------------------------------------------------------------------------------------------------
def milestone(acq: Mapping[str, Any], ret: Mapping[str, Any], gen: Mapping[str, Any], lookup: Mapping[str, Any], mod: Mapping[str, Any] | None, mii_gen: bool | None) -> dict[str, Any]:
    """SUPPORTED (append-frozen) needs ACQUISITION-POSITIVE, RETENTION-POSITIVE and GENERAL-QUALITY PRESERVED; the suffix "(append-frozen + consolidation)" if MODIFICATION is RETAINS UNDER MODIFICATION and M-ii's
    snapshots pass the GEN check in every cell (not given if any M-ii GEN reading is not evaluable). WITHHELD if ACQUISITION and RETENTION are positive and GENERAL-QUALITY is NOT PRESERVED; NOT ESTABLISHED
    (GENERAL QUALITY NOT EVALUABLE) if it is not evaluable; otherwise NOT ESTABLISHED. If AGAINST-LOOKUP is LOOKUP SUFFICES the line itself carries the baseline's name."""
    both = acq["label"] == "ACQUISITION-POSITIVE" and ret["label"] == "RETENTION-POSITIVE"
    tail = f" — {lookup['line']}" if lookup.get("label") == "LOOKUP SUFFICES" else ""
    if both and gen["label"] == "PRESERVED":
        plus = bool(mod and mod.get("label") == "RETAINS UNDER MODIFICATION" and mii_gen is True)
        return {"label": "SUPPORTED (append-frozen + consolidation)" if plus else "SUPPORTED (append-frozen)", "line_tail": tail}
    if both and gen["label"] == "NOT PRESERVED":
        return {"label": "WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE", "line_tail": tail}
    if gen["label"] == "NOT EVALUABLE":
        return {"label": "NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE)", "line_tail": tail}
    return {"label": "NOT ESTABLISHED", "line_tail": tail}


def derive_all(q: Quantities, recompute_failed: Collection[Any] = ()) -> dict[str, Any]:
    acq, ret, gen = acquisition(q, recompute_failed), retention(q, recompute_failed), general_quality(q)
    lookup, dense = against_lookup(q), against_dense(q)
    mod = modification(q, recompute_failed)
    mii_gen = gen_of_arm_passes(q, "M-ii")
    return {"ACQUISITION": acq, "RETENTION": ret, "GENERAL-QUALITY": gen, "AGAINST-DENSE": dense, "AGAINST-DENSE (M-seq vs D-seq)": against_dense(q, "M-seq", "D-seq"), "AGAINST-LOOKUP": lookup, "MODIFICATION": mod, "M-ii GEN": mii_gen, "MILESTONE": milestone(acq, ret, gen, lookup, mod, mii_gen)}  # fmt: skip


__all__ = ["CONTROL_CONDITIONS", "ORDERS", "derive_all", "study_status"]
