# ruff: noqa: E501
"""P10IS0 analysis (ADR-0023 sections 5.3, 6, 7, 8, 15): a pure function from the registry of cell records and ``durations.json`` to the per-cell-type states, the lines per series, the combination into loads, the break
points, the headline, the annotations and the descriptive sections. It reads no file and trains nothing. It refuses (``AnalysisRefused``) while any item error exists (ADR-0029 ruling 11 style): an item error is an
ENGINEERING STOP, never a scientific label.

Input shapes (all plain data, built by the evaluation stage from the cell records):

* ``registry``: ``{(cell_type_name, arm, draw): CellRecord}``;
* ``durations``: ``{cell_type_name: {"t_exposures", "convergence", "flat_below_floor", "reference_flags": {"cond4", "other"}, "removed", ...}}`` (``durations.json``'s ``cell_types``).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from . import core, labels
from .core import CellType, Thresholds
from .labels import CellResult, Obs

READOUTS = ("e512", "half", "T")


class AnalysisRefused(RuntimeError):
    """An item error exists (or the registry is not what the plan lists): the analysis does not run; the outcome is ENGINEERING STOP — ITEM ERRORS."""


@dataclass
class CellRecord:
    """One finished (or missing) cell. ``status``: ``ok``, ``nonfinite`` (the trainer's own check fired at ``nonfinite_update``) or None (no completed record). ``readouts`` hold ``Obs`` at e512, half and T."""

    status: str | None
    readouts: dict[str, Obs] = field(default_factory=dict)
    nonfinite_update: int | None = None
    collapse_onset: bool | None = None


Key = tuple[str, str, int]


def removed(entry: Mapping[str, Any] | None) -> labels.RefFlags:
    flags = (entry or {}).get("reference_flags") or {}
    return labels.RefFlags(bool(flags.get("cond4")), tuple(int(x) for x in flags.get("other", ())))


def cell_results(ct: CellType, arm: str, registry: Mapping[Key, CellRecord], readout: str, th: Thresholds, draws: Sequence[int]) -> dict[int, CellResult]:
    """Per draw: the cell's result at ``readout`` against A6 of the same draw, cell type and readout (condition 1's denominator)."""
    floor = ct.floor(th)
    out: dict[int, CellResult] = {}
    for d in draws:
        ref_rec = registry.get((ct.name, "A6", d))
        ref = ref_rec.readouts.get(readout) if ref_rec is not None and ref_rec.status == "ok" else None
        rec = registry.get((ct.name, arm, d))
        if rec is None or rec.status is None:
            continue  # a missing cell is step 0's business, not a result
        if arm == "A6":
            continue
        if rec.status == "nonfinite":
            out[d] = labels.cell_result(None, ref, floor, th, nonfinite_update=rec.nonfinite_update, a6_nonfinite=(ref_rec is not None and ref_rec.status == "nonfinite"))
        else:
            out[d] = labels.cell_result(rec.readouts.get(readout), ref, floor, th, a6_nonfinite=(ref_rec is not None and ref_rec.status == "nonfinite"))
    return out


def deltas(ct: CellType, registry: Mapping[Key, CellRecord], draws: Sequence[int]) -> dict[str, list[Fraction]]:
    """m(T) - m(T/2) per cell with a record, for m_P and m_H, A5-D and A6 (section 5.3)."""
    out: dict[str, list[Fraction]] = {f"{a}|{m}": [] for a in ("A5-D", "A6") for m in ("P", "H")}
    for a in ("A5-D", "A6"):
        for d in draws:
            rec = registry.get((ct.name, a, d))
            if rec is None or rec.status != "ok" or "T" not in rec.readouts or "half" not in rec.readouts:
                continue
            t, h = rec.readouts["T"], rec.readouts["half"]
            out[f"{a}|P"].append(t.m_p - h.m_p)
            out[f"{a}|H"].append(t.m_h - h.m_h)
    return out


def _mean_panel(o: Obs) -> float:
    return float((o.acc_a + o.acc_b) / 2)


@dataclass
class TypeReport:
    ct: CellType
    state: labels.TypeState
    cls: labels.ArmClass | None
    convergence: labels.Convergence
    regime: str | None
    labels_text: list[str]
    descriptive: dict[str, Any]
    a0: dict[str, Any] | None = None


def analyse_type(ct: CellType, registry: Mapping[Key, CellRecord], entry: Mapping[str, Any] | None, th: Thresholds, draws: Sequence[int]) -> TypeReport:
    flags = removed(entry)
    entry = entry or {}
    shown = entry.get("convergence") == "SHOWN"
    conv = labels.convergence_check(shown, deltas(ct, registry, draws), th) if not flags.removed else labels.Convergence(labels.NOT_CONFIRMED, (labels.NOT_SHOWN,), {})
    text: list[str] = []
    if flags.removed:
        n = "/".join(str(x) for x in flags.other)
        text.append(f"NOT RUN — REFERENCE FAILS CONDITION {n}")
        return TypeReport(ct, labels.type_state(None, flags, None, th), None, conv, None, text, {})
    if entry.get("convergence") and entry["convergence"] != "SHOWN":
        text.append(str(entry["convergence"]))
    if entry.get("flat_below_floor"):
        text.append(labels.FLAT_BELOW_FLOOR)
    if flags.cond4:
        text.append("REFERENCE ALSO FAILS CONDITION 4 (A6 H-ratio {x} on calibration draws)")
    if entry.get("reference_below_floor_at_t"):
        text.append("REFERENCE BELOW FLOOR AT T")
    if entry.get("lead_saw_sealed"):
        text.append("CALIBRATION VALUES SEEN BY THE LEAD")
    results = cell_results(ct, "A5-D", registry, "T", th, draws)
    cls = labels.arm_class(results, th)
    ev = [d for d, r in results.items() if r.status != labels.CELL_NOT_EVALUATED]
    stab_values = [registry[(ct.name, "A5-D", d)].readouts["T"].address_stability if registry[(ct.name, "A5-D", d)].status == "ok" else None for d in ev]
    stable = labels.address_stable(stab_values, th)
    state = labels.type_state(cls, flags, stable, th)
    a6_acc = [_mean_panel(registry[(ct.name, "A6", d)].readouts["T"]) for d in draws if (ct.name, "A6", d) in registry and registry[(ct.name, "A6", d)].status == "ok"]
    regime = labels.reference_regime(a6_acc, th) if a6_acc else None
    ratios = []
    for d in ev:
        a, r = registry[(ct.name, "A5-D", d)], registry[(ct.name, "A6", d)]
        if a.status == "ok" and r.status == "ok":
            ratios.append(_mean_panel(a.readouts["T"]) / _mean_panel(r.readouts["T"]))
    median_ratio = core.median(ratios) if ratios else None
    if median_ratio is not None and median_ratio > 1.0:
        text.append("RATIO ABOVE 1")
    if regime is not None and regime.startswith(labels.REGIME_DEGRADED) and state.q == labels.HOLDS:
        text.append("QUALIFIED RELATIVE TO A DEGRADED REFERENCE")
    text.append("A0 takes the cell type's T without a rehearsal of its own" if "A0" in ct.arms else "")
    text = [x for x in text if x]
    e512 = cell_results(ct, "A5-D", registry, "e512", th, draws)
    desc: dict[str, Any] = {
        "median_ratio_to_a6": median_ratio, "regime": regime, "state": [state.a, state.g, state.q], "combination": state.combination, "condition_failure_counts": dict(cls.condition_failures),
        "n_a": cls.n_a, "n_g": cls.n_g, "class": cls.cls, "address_stable": stable, "evaluated_draws": cls.evaluated, "lm_reduced": cls.lm_reduced,
        "a5d_accuracy_median": core.median([_mean_panel(registry[(ct.name, "A5-D", d)].readouts["T"]) for d in ev if registry[(ct.name, "A5-D", d)].status == "ok"]) if any(registry[(ct.name, "A5-D", d)].status == "ok" for d in ev) else None,
        "a6_accuracy_median": core.median(a6_acc) if a6_acc else None,
        "collapse_free": labels.collapse_free([bool(registry[(ct.name, "A5-D", d)].collapse_onset) for d in draws if (ct.name, "A5-D", d) in registry and registry[(ct.name, "A5-D", d)].collapse_onset is not None]),
        "e512_readout": {"label": "P10-S0's regime on new draws; descriptive; not a replication verdict", "class": labels.arm_class(e512, th).cls if e512 else None, "successes": sum(1 for r in e512.values() if r.status == labels.SUCCEEDED)},
        "successes": cls.successes, "evaluated_cells": cls.evaluated, "per_draw_bound": labels.per_draw_bound(cls.successes, cls.evaluated),
        "condition_6_decided": sum(1 for r in results.values() if r.failed == {6}),
        "non_finite_cells": {d: r.nonfinite_update for d, r in results.items() if r.nonfinite_update is not None},
        "convergence": {"status": conv.status, "tags": list(conv.tags), "d": {k: (float(v) if v is not None else None) for k, v in conv.d.items()}},
    }  # fmt: skip
    rep = TypeReport(ct, state, cls, conv, regime, text, desc)
    if "A0" in ct.arms:
        a0r = cell_results(ct, "A0", registry, "T", th, draws)
        rep.a0 = {"results": a0r, "paired": labels.paired(results, a0r, th), "class": labels.arm_class(a0r, th).cls}
    return rep


def missing_cells(plan_cells: Sequence[core.Cell], registry: Mapping[Key, CellRecord], cts: Mapping[str, CellType], durations: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Planned main-grid cells with no completed record (a NON-FINITE cell has one). A cell type removed by the reference rule has no planned cells."""
    out = []
    for c in plan_cells:
        name = core.cell_type_by_name(f"{core.size_name(c.facts)}/{core.size_name(c.slots)}").name
        if removed(durations.get(name)).removed:
            continue
        rec = registry.get((name, c.arm, c.draw))
        if rec is None or rec.status is None:
            out.append(c.label)
    return out


def analyze(
    registry: Mapping[Key, CellRecord],
    durations: Mapping[str, Mapping[str, Any]],
    *,
    plan_cells: Sequence[core.Cell] | None = None,
    item_errors: Sequence[str] = (),
    gate_failed: bool = False,
    paused: bool = False,
    x8_status: str | None = None,
    replaced_draws: Mapping[int, str] | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The whole analysis. ``x8_status`` is the state of X8's run when it was triggered: None (not run), ``COMPLETE``, ``PAUSED`` or ``INCOMPLETE``. Raises ``AnalysisRefused`` while any item error exists."""
    if item_errors:
        raise AnalysisRefused(f"{len(item_errors)} item error(s): ENGINEERING STOP — ITEM ERRORS; the analysis does not run: {list(item_errors)[:3]}")
    c = cfg or core.load_config()
    th = Thresholds.from_config(c)
    draws = list(range(1, int(c["draws"]["registered"]) + 1))
    all_cts = core.cell_types(c, include_x8=True)
    by_name = {ct.name: ct for ct in all_cts}
    planned = list(plan_cells) if plan_cells is not None else core.registered_cells(c)
    gaps = missing_cells(planned, registry, by_name, durations)
    out: dict[str, Any] = {**core.envelope("analysis"), "replaced_draws": dict(replaced_draws or {}), "false_negative_table": labels.false_negative_table(), "fixed_sentences": labels.FIXED_SENTENCES, "missing_cells": gaps}
    if gaps or paused or gate_failed:
        h = labels.decide(loads={}, missing_cells=len(gaps), gate_failed=gate_failed, paused=paused, th=th)
        out["headline"] = {"step": h.step, "text": h.text, "detail": h.detail}
        out["scientific_labels"] = None
        out["status"] = "INCOMPLETE"
        return out
    reports: dict[str, TypeReport] = {ct.name: analyse_type(ct, registry, durations.get(ct.name), th, draws) for ct in all_cts if not ct.conditional}
    by_load: dict[float, list[labels.SeriesAtLoad]] = {}
    for name, rep in reports.items():
        by_load.setdefault(rep.ct.load, []).append(labels.SeriesAtLoad(rep.ct.series, rep.state, rep.convergence, name))
    head = labels.decide(loads=by_load, th=th)
    triggered = labels.x8_triggered(head.detail.get("L_Q"), th, head.step)
    x8 = next(ct for ct in all_cts if ct.conditional)
    if triggered and x8_status is not None:
        reports[x8.name] = analyse_type(x8, registry, durations.get(x8.name), th, draws)
        by_load.setdefault(x8.load, []).append(labels.SeriesAtLoad("X", reports[x8.name].state, reports[x8.name].convergence, x8.name))
        head = labels.decide(loads=by_load, x8_triggered=True, x8_status=x8_status, th=th)
    elif triggered:
        head = labels.decide(loads=by_load, x8_triggered=True, x8_status="INCOMPLETE", th=th)
    out["x8"] = {"triggered": triggered, "status": x8_status if triggered else f"NOT RUN — L_Q BELOW 4 (or the result of steps 0 to 2: step {head.step})", "label": "ONE SERIES" if triggered else None}
    out["headline"] = {"step": head.step, "text": head.text, "detail": head.detail}
    out["status"] = "COMPLETE"
    loads_main = sorted(by_load)
    lines: dict[str, Any] = {}
    for line in ("A", "G", "Q"):
        st = {ld: labels.combine_series([getattr(s.state, line.lower()) for s in by_load[ld]], line) for ld in loads_main if not (ld == 8.0 and not (triggered and x8_status == "COMPLETE"))}
        b = labels.break_point(st, line)
        lines[line] = {"states": st, "L": b.l, "l1": b.l1, "l1_state": b.l1_state, "non_monotone": b.non_monotone}
    out["lines"] = lines
    out["states_by_load_series"] = {f"{ld:g}": {s.series: {"cell_type": s.cell_type, "A": s.state.a, "G": s.state.g, "Q": s.state.q, "combination": s.state.combination} for s in by_load[ld]} for ld in loads_main}
    out["types"] = {n: {"labels": r.labels_text, "descriptive": r.descriptive} for n, r in reports.items()}
    only = {}
    for ld in loads_main:
        holding = [s.series for s in by_load[ld] if s.state.q == labels.HOLDS]
        if holding and len(holding) < len(by_load[ld]) and len(by_load[ld]) > 1:
            only[f"{ld:g}"] = f"IN SERIES {'/'.join(holding)} ONLY (slots {', '.join(str(by_name[s.cell_type].slots) for s in by_load[ld] if s.series in holding)})"
    out["holds_in_one_series_only"] = only
    l1 = head.detail.get("l1")
    if l1 is not None and l1 in by_load:
        out["l1_failure_counts_by_series"] = {s.series: dict(reports[s.cell_type].cls.condition_failures) for s in by_load[l1] if reports[s.cell_type].cls is not None}
        out["l1_line_a_beside_headline"] = {s.series: s.state.a for s in by_load[l1] if s.state.q == labels.NOT_EVALUABLE and s.state.flagged_cond4}
    at_l1 = {s.series: s.state for s in by_load[l1]} if l1 in by_load else {}
    if l1 in by_load:
        out["l1_which_line"] = {s.series: labels.fails_print(s.state) for s in by_load[l1] if s.state.q == labels.FAILS}  # section 7: printed at every step that has an l1 that FAILS
    lq = head.detail.get("L_Q")
    out["at_L_Q"] = {s.series: {"cell_type": s.cell_type, "regime": reports[s.cell_type].regime, "convergence": reports[s.cell_type].convergence.status, "tags": list(reports[s.cell_type].convergence.tags)} for s in by_load[lq]} if lq in by_load else {}
    out["at_l1"] = {s.series: {"cell_type": s.cell_type, "regime": reports[s.cell_type].regime, "convergence": reports[s.cell_type].convergence.status, "tags": list(reports[s.cell_type].convergence.tags)} for s in by_load[l1]} if l1 in by_load else {}
    out["ratio_above_1_definition"] = "RATIO ABOVE 1 is this study's descriptive tag: the median over evaluated draws of A5-D's mean panel accuracy over A6's exceeds 1; it enters no line (ADR-0023 section 3 says only that the label adds it)"
    pair2 = reports[next(n for n, r in reports.items() if r.ct.series == "M" and r.ct.load == 2.0)].a0
    out["annotations"] = {
        "penalty_vs_a0": {r.ct.name: (r.a0["paired"] if r.a0 else None) for r in reports.values() if r.ct.series in ("M", "X")},
        "hypotheses": labels.hypotheses(head, at_l1, pair2["paired"]["label"] if pair2 else None, lines["Q"]["states"].get(0.5)),
        "licence_loads": labels.licence(head),
    }
    out["licence_text"] = "OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023)" if not out["annotations"]["licence_loads"] else None
    return out


def math_safe(x: float | None) -> float | None:
    return x if x is None or math.isfinite(x) else None
