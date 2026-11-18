# ruff: noqa: E501
"""P10IR labels (ADR-0029 sections 8, 9 and 10): pure functions over plain numbers and strings. No torch, no I/O.

Inputs are the information measure ``i`` (bits per fact, computed by P10-S1's ``bits_per_fact`` where the records are made) per read and per panel, the candidate recall CR8 of T0, and the
gate outcomes of a replicate. Every threshold is an argument (``core.Thresholds``, read from the config). First match wins in the tree table; labels are compared by row name only.

Readings the ADR leaves open (each takes the most conservative course and is listed in ``READINGS``) are printed in the report.
"""

import math
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .core import Thresholds

EPS = 1e-12
PANELS = ("A", "B")
CHECKPOINTS = ("U_P", "RUN")


def ge(a: float, b: float) -> bool:
    return a >= b - EPS


def le(a: float, b: float) -> bool:
    return a <= b + EPS


# --- row names -----------------------------------------------------------------------------------------------------------------------
NOT_EVALUABLE = "NOT EVALUABLE"
NO_GAP = "NO GAP"
MIXED_PANEL = "MIXED-PANEL"
PRIORS_AND_CANDIDATES = "PRIORS AND CANDIDATES, SEPARATELY"
PRIORS = "PRIORS"
CANDIDATES = "CANDIDATES"
JOINT = "JOINT"
EXACT_SEARCH_HARMS = "EXACT SEARCH HARMS"
CONTENT = "CONTENT"
NOT_IDENTIFIED = "NOT IDENTIFIED"
MIXED = "MIXED"
CELL_DEPENDENT = "CELL-DEPENDENT"
CHECKPOINT_DEPENDENT = "CHECKPOINT-DEPENDENT"

TREE_ROWS = (NOT_EVALUABLE, NO_GAP, MIXED_PANEL, PRIORS_AND_CANDIDATES, PRIORS, CANDIDATES, JOINT, EXACT_SEARCH_HARMS, CONTENT, NOT_IDENTIFIED)
TREE_ROW_ORDER = {"NOT EVALUABLE": "1", "NO GAP": "2", "MIXED-PANEL": "2a", PRIORS_AND_CANDIDATES: "3", PRIORS: "4", CANDIDATES: "5", JOINT: "6", EXACT_SEARCH_HARMS: "7", CONTENT: "8", NOT_IDENTIFIED: "9"}
EXACT_SEARCH_LONG = "EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME"  # the row's full wording in the ADR's table; the row name for every comparison is EXACT_SEARCH_HARMS

SPARSE_APPROACHES = "SPARSE INDEX APPROACHES FLAT"
ONLY_ABOVE_512 = "INDEX APPROACHES FLAT ONLY ABOVE 512"
NOT_APPROACH = "INDEX DOES NOT APPROACH FLAT"
INDEX_ROWS = (SPARSE_APPROACHES, ONLY_ABOVE_512, NOT_APPROACH, NOT_EVALUABLE)

# the next action of each row (sections 8.3 and 8.4); a row not listed recommends nothing
TREE_ACTIONS = {
    PRIORS_AND_CANDIDATES: "Either: how routing scores enter the read, or candidate coverage",
    PRIORS: "Redesign how routing scores enter the read",
    CANDIDATES: "Improve the router and candidate coverage",
    CONTENT: "Improve memory training and representation",
}
INDEX_ACTIONS = {SPARSE_APPROACHES: "Investigate a separately trained sparse index"}
NO_READ_TIME_CAUSE = "NO READ-TIME CAUSE IDENTIFIED"
FULLY, PARTLY = "FULLY", "PARTLY"

READINGS = {
    "weak_reference": "READING: a WEAK REFERENCE (i(F0) below the floor on either panel) makes the replicate NOT EVALUABLE for the label concerned (row 1 / index NOT EVALUABLE); no row is assigned",
    "panel_closure": "ADR §16 item 10 (ruled as recommended): P, C and J need the condition on both panels; a closure on one panel only is not P, C or J",
    "fully_row3": "READING: row 3 is FULLY if T1 and T3 are both RESTORED on both panels, else PARTLY",
    "mainly": "READING: 'mainly weights' / 'mainly selection' compares i(T1w) - i(T0) with i(T1) - i(T1w), each the mean of the two panels; equal is printed 'equal'",
    "cell_dependent_equality": "READING: two CELL-DEPENDENT values are the same value only if they hold the same row at each primary cell (R-CONFIRM and the checkpoint rule compare these signatures)",
    "index_gate_scope": "§11 and §16 item 11: a failure of I256@512 or of an I64 index with F0 passing voids the index label of the replicate only; study-level NOT EVALUABLE (§9 item 1) applies per component's primary cells",
    "median_c_star": "READING: a cell's c* is the statistics.median of its replicates' c* (those that have one); with an even count this is the mean of the two middle values",
    "missing_plateau": "READING: a replicate whose recorded snapshots do not allow the plateau check counts as failing it",
    "mixed_cell": "READING: MIXED is a value that two primary cells can share; the component is then MIXED and recommends nothing",
}


# --- the retention rule (section 8.1) ----------------------------------------------------------------------------------------------
RESTORED, NOT_RESTORED, WEAK = "RESTORED", "NOT RESTORED", "WEAK REFERENCE"


def has_gap(i_ref: float, i_x: float, th: Thresholds) -> bool:
    """A gap exists if i(Y) - i(X) >= 0.5 bits."""
    return ge(i_ref - i_x, th.gap_bits)


def retention(i_x: float, i_ref: float, th: Thresholds) -> str:
    """X is RESTORED to Y if i(Y) - i(X) <= 0.25 bits and i(X) >= 0.90 i(Y), with i(Y) >= the floor; below the floor: WEAK REFERENCE."""
    if i_ref < th.floor_i_bits - EPS:
        return WEAK
    return RESTORED if le(i_ref - i_x, th.restored_margin_bits) and ge(i_x, th.restored_ratio * i_ref) else NOT_RESTORED


def closure(i_x: float, i_t0: float, i_f0: float) -> float:
    """g(X') = [i(X') - i(T0)] / [i(F0) - i(T0)], defined where a gap exists between T0 and F0 (the denominator is then at least the gap threshold)."""
    den = i_f0 - i_t0
    if den <= 0:
        raise ValueError("closure is defined only where i(F0) > i(T0)")
    return (i_x - i_t0) / den


# --- replicates: tree label (section 8.3) --------------------------------------------------------------------------------------------
@dataclass
class TreeRep:
    """One replicate at one checkpoint: ``evaluable`` is False if a gate failed for the T-OQ checkpoint or for F0 (the scope of section 11); ``i[read][panel]``; ``cr8`` is CR8 of T0."""

    evaluable: bool
    i: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    cr8: float | None = None
    reason: str = ""


@dataclass
class RepLabel:
    row: str
    suffix: str | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


TREE_READS = ("T0", "T1", "T1w", "T2", "T3", "F0")


def _panel_values(rep: TreeRep, read: str) -> dict[str, float]:
    try:
        return {p: float(rep.i[read][p]) for p in PANELS}
    except KeyError as exc:
        raise ValueError(f"replicate lacks i of {read} on a panel: {exc}") from exc


def tree_replicate(rep: TreeRep, th: Thresholds) -> RepLabel:
    """First match wins over rows 1, 2, 2a, 3 to 9 of section 8.3."""
    if not rep.evaluable:
        return RepLabel(NOT_EVALUABLE, reason=rep.reason or "a gate failed (scope of section 11)")
    i = {r: _panel_values(rep, r) for r in TREE_READS}
    if any(i["F0"][p] < th.floor_i_bits - EPS for p in PANELS):
        return RepLabel(NOT_EVALUABLE, reason=WEAK)
    gaps = {p: has_gap(i["F0"][p], i["T0"][p], th) for p in PANELS}
    if not any(gaps.values()):
        return RepLabel(NO_GAP)
    if not all(gaps.values()):
        return RepLabel(MIXED_PANEL, tags={"gap_panels": [p for p in PANELS if gaps[p]]})
    g = {r: {p: closure(i[r][p], i["T0"][p], i["F0"][p]) for p in PANELS} for r in ("T1", "T3", "T2")}
    rest = {r: all(retention(i[r][p], i["F0"][p], th) == RESTORED for p in PANELS) for r in ("T1", "T3", "T2")}

    def holds(r: str) -> bool:
        return all(retention(i[r][p], i["F0"][p], th) == RESTORED or ge(g[r][p], th.closure) for p in PANELS)

    p_, c_, j_ = holds("T1"), holds("T3"), holds("T2")
    h_ = all(le(i["T2"][p], i["T0"][p] - th.restored_margin_bits) for p in PANELS)
    if rep.cr8 is None:
        raise ValueError("an evaluable replicate needs CR8 of T0")
    r_ = ge(float(rep.cr8), th.recall_r)
    tags: dict[str, Any] = {"P": p_, "C": c_, "J": j_, "H": h_, "R": r_, "g_P": g["T1"], "g_C": g["T3"], "g_PC": g["T2"], "cr8": float(rep.cr8)}
    if p_ and c_:
        return RepLabel(PRIORS_AND_CANDIDATES, FULLY if rest["T1"] and rest["T3"] else PARTLY, tags)
    if p_:
        w = sum(i["T1w"][p] - i["T0"][p] for p in PANELS) / 2
        s = sum(i["T1"][p] - i["T1w"][p] for p in PANELS) / 2
        tags["mainly"] = "weights" if w > s + EPS else "selection" if s > w + EPS else "equal"
        return RepLabel(PRIORS, FULLY if rest["T1"] else PARTLY, tags)
    if c_:
        return RepLabel(CANDIDATES, FULLY if rest["T3"] else PARTLY, tags)
    if j_:
        return RepLabel(JOINT, FULLY if rest["T2"] else PARTLY, tags)
    if h_:
        return RepLabel(EXACT_SEARCH_HARMS, None, tags)
    return RepLabel(CONTENT if r_ else NOT_IDENTIFIED, None, tags)


# --- replicates: index label (section 8.4) -----------------------------------------------------------------------------------------
@dataclass
class IndexRep:
    """One replicate at one checkpoint: ``i_f0[panel]``; ``i_budget[c][panel]`` is the mean over the three index seeds (taken before the panel test, section 8.2) for every FEASIBLE budget c."""

    evaluable: bool
    i_f0: Mapping[str, float] = field(default_factory=dict)
    i_budget: Mapping[int, Mapping[str, float]] = field(default_factory=dict)
    reason: str = ""


def index_replicate(rep: IndexRep, th: Thresholds) -> RepLabel:
    """A budget c is sufficient if I64@c is RESTORED to F0 at c and at every larger feasible budget; c* is the smallest sufficient budget."""
    if not rep.evaluable:
        return RepLabel(NOT_EVALUABLE, reason=rep.reason or "a gate failed (scope of section 11)")
    if any(float(rep.i_f0[p]) < th.floor_i_bits - EPS for p in PANELS):
        return RepLabel(NOT_EVALUABLE, reason=WEAK)
    budgets = sorted(rep.i_budget)
    if not budgets:
        raise ValueError("an index replicate needs at least one feasible budget")
    ok = {c: all(retention(float(rep.i_budget[c][p]), float(rep.i_f0[p]), th) == RESTORED for p in PANELS) for c in budgets}
    c_star: int | None = None
    for k, c in enumerate(budgets):
        if all(ok[x] for x in budgets[k:]):
            c_star = c
            break
    if c_star is None:
        return RepLabel(NOT_APPROACH, tags={"c_star": None})
    return RepLabel(SPARSE_APPROACHES if c_star <= th.tree_candidates else ONLY_ABOVE_512, tags={"c_star": c_star})


# --- cells (section 8.2) ------------------------------------------------------------------------------------------------------------
def cell_label(rows: Sequence[str], th: Thresholds) -> str:
    """A cell is NOT EVALUABLE if at least 2 of its 5 replicates are (applied before the 4-of-5 rule); else its label is the row held by at least 4 of 5 replicates; else MIXED. The
    denominator is always 5: a replicate that is NOT EVALUABLE satisfies no row."""
    if len(rows) != th.replicates:
        raise ValueError(f"a cell has exactly {th.replicates} replicates (a missing record is a NOT EVALUABLE row)")
    if sum(1 for r in rows if r == NOT_EVALUABLE) >= th.not_evaluable_min_replicates:
        return NOT_EVALUABLE
    for row, k in Counter(r for r in rows if r != NOT_EVALUABLE).most_common():
        if k >= th.label_min_replicates:
            return row
    return MIXED


def median_c_star(values: Sequence[int | None]) -> float | None:
    got = [v for v in values if v is not None]
    return float(statistics.median(got)) if got else None


# --- the plateau check (section 9) ----------------------------------------------------------------------------------------------------
def i_star(series: Mapping[int, float], limit: int) -> float | None:
    """The maximum of i over the snapshots at or below ``limit`` (``studies/p10s1/classes.py`` ``View.i_star``); None if there is none."""
    eligible = [v for u, v in series.items() if u <= limit]
    return max(eligible) if eligible else None


def plateau_ok(per_panel: Mapping[str, Mapping[int, float]], run: int, th: Thresholds) -> bool:
    """i*(run) - i*(run/2) <= 0.10 and i*(run/2) >= the floor, on both panels; missing records count as failing."""
    for p in PANELS:
        series = per_panel.get(p)
        if not series:
            return False
        top, half = i_star(series, run), i_star(series, run // 2)
        if top is None or half is None or not (le(top - half, th.plateau_gain_bits) and ge(half, th.floor_i_bits)):
            return False
    return True


def still_learning(per_replicate: Sequence[Mapping[str, Mapping[int, float]] | None], run: int, th: Thresholds) -> bool:
    """The STILL LEARNING tag: the plateau check fails in at least 2 of the 5 replicates (a missing replicate fails)."""
    if len(per_replicate) != th.replicates:
        raise ValueError("five replicates")
    failing = sum(1 for s in per_replicate if s is None or not plateau_ok(s, run, th))
    return failing >= th.still_learning_min_replicates


# --- study level (section 9) --------------------------------------------------------------------------------------------------------
@dataclass
class Component:
    value: str  # a row, MIXED, CELL-DEPENDENT or CHECKPOINT-DEPENDENT
    at: dict[str, dict[str, Any]]  # checkpoint -> {"value": row | CELL-DEPENDENT, "cells": {cell: row}}
    signature: tuple[Any, ...] = ()
    single_row: bool = False


@dataclass
class Diagnosis:
    evaluable: bool
    not_evaluable: list[tuple[str, str, str]]  # (component, cell, checkpoint)
    components: dict[str, Component]
    pair: tuple[str, str] | None
    recommended: dict[str, str | None]
    no_read_time_cause: bool


def _checkpoint_value(cells: Mapping[str, str]) -> tuple[str, tuple[Any, ...]]:
    rows = set(cells.values())
    if len(rows) == 1:
        (row,) = rows
        return row, (row,)
    return CELL_DEPENDENT, (CELL_DEPENDENT, tuple(sorted(cells.items())))


def combine(labels: Mapping[str, Mapping[str, Mapping[str, str]]], primary: Sequence[str]) -> Diagnosis:
    """``labels[component][cell][checkpoint]`` with components 'tree' and 'index', the two primary cells and the checkpoints U_P and RUN.

    1. If either component has a NOT EVALUABLE primary cell at either checkpoint, R-DIAGNOSIS is NOT EVALUABLE (nothing below is applied).
    2. Per component and checkpoint, the common row of the primary cells, else CELL-DEPENDENT.
    3. Per component, the value if the same at both checkpoints, else CHECKPOINT-DEPENDENT (no recommended action).
    4. The pair. Actions only for a component that is one row everywhere; NO READ-TIME CAUSE IDENTIFIED is printed (recommending nothing) when the tree component is EXACT SEARCH HARMS or
    NOT IDENTIFIED and the index component is INDEX DOES NOT APPROACH FLAT."""
    comps = ("tree", "index")
    bad = [(comp, cell, cp) for comp in comps for cell in primary for cp in CHECKPOINTS if labels[comp][cell][cp] == NOT_EVALUABLE]
    components: dict[str, Component] = {}
    for comp in comps:
        at: dict[str, dict[str, Any]] = {}
        sigs: dict[str, tuple[Any, ...]] = {}
        for cp in CHECKPOINTS:
            cells = {cell: labels[comp][cell][cp] for cell in primary}
            value, sig = _checkpoint_value(cells)
            at[cp] = {"value": value, "cells": cells}
            sigs[cp] = sig
        if sigs["U_P"] == sigs["RUN"]:
            value = at["U_P"]["value"]
            sig_all: tuple[Any, ...] = sigs["U_P"]
        else:
            value = CHECKPOINT_DEPENDENT
            sig_all = (CHECKPOINT_DEPENDENT, sigs["U_P"], sigs["RUN"])
        single = len(sig_all) == 1
        components[comp] = Component(value, at, sig_all, single)
    if bad:
        return Diagnosis(False, bad, components, None, {"tree": None, "index": None}, False)
    rec = {
        "tree": TREE_ACTIONS.get(components["tree"].value) if components["tree"].single_row else None,
        "index": INDEX_ACTIONS.get(components["index"].value) if components["index"].single_row else None,
    }
    none_found = components["tree"].single_row and components["index"].single_row and components["tree"].value in (EXACT_SEARCH_HARMS, NOT_IDENTIFIED) and components["index"].value == NOT_APPROACH
    return Diagnosis(True, [], components, (components["tree"].value, components["index"].value), rec, none_found)


# --- R-CONFIRM (section 10) -------------------------------------------------------------------------------------------------------------
CONFIRMED, NOT_CONFIRMED, NOT_APPLICABLE, NOT_RUN = "CONFIRMED", "NOT CONFIRMED", "NOT APPLICABLE", "NOT RUN"


def r_confirm(a1: Diagnosis, a2: Diagnosis | None, *, a2_complete: bool = True) -> dict[str, dict[str, Any]]:
    """R-CONFIRM-TREE and R-CONFIRM-INDEX. NOT APPLICABLE if A1's R-DIAGNOSIS is NOT EVALUABLE; NOT RUN if stage A2 is not funded or not complete; NOT EVALUABLE if A1's is evaluable and A2's is not;
    else CONFIRMED if A2's component equals A1's (row names; two CHECKPOINT-DEPENDENT components are equal only if their values at U_P and at the run length are equal), else NOT CONFIRMED with both printed."""
    out: dict[str, dict[str, Any]] = {}
    for comp, name in (("tree", "R-CONFIRM-TREE"), ("index", "R-CONFIRM-INDEX")):
        if not a1.evaluable:
            out[name] = {"value": NOT_APPLICABLE}
        elif a2 is None or not a2_complete:
            out[name] = {"value": NOT_RUN}
        elif not a2.evaluable:
            out[name] = {"value": NOT_EVALUABLE, "a2_not_evaluable": [list(x) for x in a2.not_evaluable if x[0] == comp]}
        else:
            c1, c2 = a1.components[comp], a2.components[comp]
            out[name] = {"value": CONFIRMED if c1.signature == c2.signature else NOT_CONFIRMED, "a1": c1.value, "a2": c2.value}
    return out


def may_say_cause(confirm: Mapping[str, Mapping[str, Any]]) -> bool:
    """A statement that the tree's gap is caused by a named factor at read time requires R-CONFIRM-TREE: CONFIRMED."""
    return confirm["R-CONFIRM-TREE"]["value"] == CONFIRMED


def accuracy_retained(acc_x: float, acc_ref: float, acc0: float) -> float:
    """The accuracy version of the retention ratio, [acc(X) - acc0] / [acc(Y) - acc0], printed beside the rule and deciding nothing (section 8.1)."""
    den = acc_ref - acc0
    return math.nan if den <= 0 else (acc_x - acc0) / den
