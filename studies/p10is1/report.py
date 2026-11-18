# ruff: noqa: E501
"""P10IS1 report (ADR-0024 sections 9, 10 and 18): a pure function of the analysis result and the run's records, no I/O. It prints every replicate, panel, cell and reading a rule names (not-full replicates included),
every dense label with all its readings, every annotation in the cell it belongs to, the table of labels that cannot be reached without measured CPU cost, and names the run and the stage each section came from.
Every count says what it counts (cells and reads are counted separately). Every positive label carries the standing tag; text with an untagged positive label cannot be emitted (``labels.emit``).
Status: self-checked only. Not independent review, not Astra validation, not human approval."""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core
from . import labels as L

UNREACHABLE = (
    ("C-CAPACITY", "`CAPACITY-POSITIVE` (`STORE NOT BEHIND` needs MC-T)", "NEGATIVE (a); NEGATIVE (b) through MU, MC-A, D-BEST or saturation; NOT TESTED; INCONCLUSIVE", "MEASURED COST NOT AVAILABLE: a positive was not reachable"),
    ("C-EFFICIENCY", "`EFFICIENCY-POSITIVE` (needs E-T)", "NEGATIVE through E-A; INCONCLUSIVE", "the outcome with '(E-A ONLY; MEASURED COST NOT AVAILABLE)'"),
    ("Dense at saturation (a label of section 9.2, not a C-SATURATION outcome)", "`STORE HOLDS MORE AT SATURATION` (cost condition)", "DENSE HOLDS MORE; SAME AT SATURATION; every C-SATURATION outcome", "the same sentence beside the dense-at-saturation label"),
)  # section 10: what MC-T NOT MEASURED makes unreachable (printed with every report)


READINGS_TAKEN = (
    "DEPARTURE (stricter for the store): a dependence failure on EITHER panel of either cell blocks the capacity step on both panels and gives DEPENDENCE_FAILED, never PANEL-DISAGREE (ADR-0024 section 9: a blocking condition needs one panel; P10-S1's code read DEP per panel; the lead's ruling).",
    "DEPARTURE (stricter for the store): DENSE NOT FASTER is not established in a replicate in which D-OQ failed a qualified dependence condition at ANY snapshot it read, where ruling 17 names only s_prev and s_hit (the lead's ruling: kept).",
    "READING: a snapshot at a fraction of U_P that has no reference-arm read (off the grid) has every dependence condition applied (nothing is disqualified): the stricter reading for the store.",
    "READING: where the larger cell of a capacity step costs no more per update than the smaller, the larger cell is read at U_P in every matched-compute reading, MC-C included (ruling 1), never later.",
    "READING: DENSE NOT FASTER needs the dense map's c_T above 0.8 of the arm's in all 5 replicates, on both panels, for every value the censoring bounds allow.",
    "READING: `STORE HOLDS MORE` and DENSE HOLDS MORE read D-OQ's dependence at the snapshot attaining i* and at U_RUN/2 of the cell (ruling 17).",
    "READING: the edge test of the rate search is 0.02 or more over the next rate (as P10-S1 did); the second extension steps (1.0 upwards, 0.0001 downwards) are not named by the ADR and were ruled by the lead on 2026-11-18, to be recorded in ADR-0024's rulings.",
    "CHECK: the whole cell's recorded stop (U_run) is recomputed from the data; a difference is an engineering failure, never a label.",
)


def readings_section() -> list[str]:
    return ["## Readings taken here (departures and readings the specification leaves to the implementation)", *[f"- {x}" for x in READINGS_TAKEN], ""]


def fmt(v: Any, nd: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return "inf" if v == float("inf") else f"{v:.{nd}f}"
    return str(v)


def table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(fmt(c) for c in r) + " |" for r in rows]
    return out


def stage_line(res: Mapping[str, Any], stage: str) -> str:
    st = (res.get("stages") or {}).get(stage, "stage record not given")
    return f"_Run: {res.get('run') or 'not named'}; stage: {stage} ({st})._"


def cost_note(res: Mapping[str, Any]) -> str:
    return "" if res.get("mct_measured") else "MC-T NOT MEASURED (by a recorded decision): matched compute is read in MC-A only; every CAPACITY verdict carries MATCHED COMPUTE IN MC-A ONLY; " + L.MEASURED_COST_NOT_AVAILABLE


def unreachable_table() -> list[str]:
    return ["### Labels that cannot be reached without measured CPU cost (ADR-0024 section 10)", *table(["Line", "Unreachable", "Still reachable", "Printed"], [list(r) for r in UNREACHABLE])]


def capacity_section(res: Mapping[str, Any]) -> list[str]:
    cap = res["capacity"]
    o = cap["outcome"]
    out = ["## C-CAPACITY", stage_line(res, "analysis (capacity)"), ""]
    detail = [f"arms {', '.join(o['arms'])}" if o.get("arms") else "", *o.get("reasons", [])]
    if o["label"] == L.CAPACITY_POSITIVE and o.get("post_hoc_only"):
        detail.append(L.POST_HOC_ONLY)
    head = L.printable(o["label"], *(d for d in detail if d), core.SIZES_CAPACITY, core.NOT_TESTED_X)
    out += [f"**{L.emit(head)}**", f"saturation outcome beside it: {res['saturation']['outcome']['label']}", core.LANE_L_NOT_LICENSED if not res.get("lane_l") else str(res["lane_l"]), ""]
    if cost_note(res):
        out += [cost_note(res), ""]
    for arm, a in cap["arms"].items():
        cls = L.printable(a["class"]) if a["class"] == L.CAPACITY_SUPPORTED else a["class"]
        extra = " (printed with its annotations; enters no outcome)" if arm == "H8" else ""
        out += [f"### {arm}: arm class {cls}{extra}; arm-level dense label {a['dense_arm']}; a_use >= 0.80 at 32K/16K at U_P in all 5 replicates: {a['a_use_at_32K_16K_all5']}", ""]
        rows = []
        for sname, s in a["steps"].items():
            for r in s["replicates"]:
                dm = {p: r["detail"]["panels"][p]["delta_mu"] if "delta_mu" in r["detail"]["panels"][p] else None for p in core.PANELS}
                rows.append([sname, r["replicate"], r["verdict"], fmt(dm["A"]), fmt(dm["B"]), r["small_full"], r["small_loaded"], r["u_run_small"], r["u_run_large"]])
        out += table(["step", "replicate", "verdict", "d_MU (A)", "d_MU (B)", "smaller cell full", "smaller loaded", "U_run smaller", "U_run larger"], rows)
        out += ["", "step classes: " + "; ".join(f"{k}: {L.printable(v['class'])}" for k, v in a["steps"].items())]
        for cell, d in a["dense_cells"].items():
            label = L.printable(d["label"]) if d["label"] == L.STORE_NOT_BEHIND else d["label"]
            out.append(f"- dense, larger cell {cell}: {label}; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): " + ", ".join(f"{k}: {v}" for k, v in d["counts"].items()) + (f"; {d['reason']}" if d.get("reason") else ""))
        for cell, d in a["dense_at_saturation"].items():
            lab = L.printable(d["label"]) if d["label"] == L.STORE_HOLDS_MORE else d["label"]
            out.append(f"- dense at saturation, loaded cell {cell}: {lab}{' (' + ', '.join(d['sublabels']) + ')' if d['sublabels'] else ''}; replicates with a dense lead: {d['replicates_ahead']}; " + "; ".join(f"r{r['replicate']}: arm length {r['arm_length']}, D-OQ length {r['dense_length']}, d_sat {fmt(r['d_sat']['A'])}/{fmt(r['d_sat']['B'])}, d_sat at the shorter length {fmt(r['d_sat_at_shorter_length']['A'])}/{fmt(r['d_sat_at_shorter_length']['B'])}, D-OQ a_use at U_P {fmt(r['dense_a_use_at_u_p']['A'])}/{fmt(r['dense_a_use_at_u_p']['B'])}" for r in d["replicates"]))
        out.append("")
    out += [f"H8 annotations: {cap['h8_annotations'] or 'none'}; {L.KEY_LEARNING_LIMITED if cap['key_learning_limited'] else 'KEY-LEARNING-LIMITED absent'}", ""]
    for tag, v in cap["sparse"].items():
        out.append(f"sparse arms, T-OQ against F-OQ-IVF at equal candidates, read at {tag}: {v['label']} (descriptive; enters no outcome; may not be cited to select a routing design)")
    out.append("")
    return out


def saturation_section(res: Mapping[str, Any]) -> list[str]:
    sat = res["saturation"]
    o = sat["outcome"]
    out = ["## C-SATURATION", stage_line(res, "analysis (saturation)"), ""]
    arms = ", ".join(o["arms"])
    head = L.printable(o["label"], *([f"arms {arms}"] if arms else []), *o["notes"], *o["reasons"], "EIGHT FACTS PER SLOT", core.NOT_TESTED_X)
    out += [f"**{L.emit(head)}**", "The crowding of the fixed width-16 oracle codes grows with the fact set: a SUBPROPORTIONAL verdict is NOT A PROPERTY OF THE STORE ALONE.", ""]
    for arm, a in sat["arms"].items():
        cls = L.printable(a["class"]) if "PROPORTIONAL_ALL_PAIRS" in a["class"] else a["class"]
        out += [f"### {arm}: saturation arm class {cls}" + (" (H8 alone cannot give SATURATION-PROPORTIONAL)" if arm == "H8" else ""), ""]
        rows = []
        for pname, p in a["pairs"].items():
            for r in p["replicates"]:
                d = r["detail"]
                for panel in core.PANELS:
                    rho = d.get("rho", {}).get(panel)
                    rows.append([pname, r["replicate"], panel, r["verdict"], fmt(rho), fmt(d["small"]["b_bits_per_slot"][panel]), fmt(d["large"]["b_bits_per_slot"][panel]), fmt(d["small"]["last_doubling_gain"][panel]), fmt(d["large"]["last_doubling_gain"][panel]), r["full"]])
            if not p["replicates"]:
                rows.append([pname, "-", "-", p.get("note", "NOT FULL"), "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"])
        out += table(["pair", "replicate", "panel", "verdict", "rho", "b(N) bits/slot", "b(4N)", "last ladder gain N", "last ladder gain 4N", "full (per cell)"], rows)
        out += ["", "pair classes: " + "; ".join(f"{k}: {L.printable(v['class']) if v['class'] == 'PROPORTIONAL STEP' else v['class']}" for k, v in a["pairs"].items()), ""]
    return out


def efficiency_section(res: Mapping[str, Any]) -> list[str]:
    eff = res["efficiency"]
    o = eff["outcome"]
    out = ["## C-EFFICIENCY", stage_line(res, "analysis (efficiency)"), ""]
    tail = "(E-A ONLY; MEASURED COST NOT AVAILABLE)" if eff["e_a_only"] else ""
    head = L.printable(o["label"], *([f"arms {', '.join(o['arms'])}"] if o["arms"] else []), *o["reasons"], eff["sizes"])
    out += [f"**{L.emit(head)}** {tail}".rstrip(), "Each cell is printed under both cost readings; the analytic reading is counted multiply-adds (MC-A), never measured efficiency.", ""]
    for reading, block in eff["readings"].items():
        out += [f"### reading {reading}", ""]
        for arm, a in block["arms"].items():
            out += [f"- {arm}: arm class {L.printable(a['class']) if a['class'] == 'EFFICIENCY_SUPPORTED' else a['class']}; steps: " + "; ".join(f"{k}: {L.printable(v['class']) if v['class'] == 'FASTER STEP' else v['class']}" for k, v in a["steps"].items()) + "; dense speed: " + (", ".join(f"{c}: {v}" for c, v in a["dense_speed"].items()) or "no FASTER STEP")]
            for sname, s in a["steps"].items():
                out.append(f"  - {sname}: verdicts per replicate {s['verdicts']}; u_T (smaller, larger) of replicate 1: {[fmt(x) for x in s['replicates'][0]['u_t_small']]} / {[fmt(x) for x in s['replicates'][0]['u_t_large']]}")
        out.append("")
    return out


def render(res: Mapping[str, Any], *, throughput: Mapping[str, Any] | None = None, caps: Mapping[str, Any] | None = None) -> str:
    """The whole report as text. ``throughput``: ``{"state": MEASURED | PAUSED | NOT MEASURED, ...}``; ``caps``: the plan's one cap figure per stage."""
    out = ["# P10-I-S1 block M report (ADR-0024)", f"_Run: {res.get('run') or 'not named'}. Every label carries: {core.STANDING_TAG}. Lane L and block X are not implemented: {core.NOT_TESTED_X}._", ""]
    if caps:
        out += ["Caps (the plan's figures, in charged hours): " + ", ".join(f"{k} {v}" for k, v in caps.items()), ""]
    status = res["status"]
    out.append(f"Status: **{status}**")
    if status != "COMPLETE":
        out += ["", f"No outcome is printed on any line: C-CAPACITY {res['lines']['C-CAPACITY']}; C-SATURATION {res['lines']['C-SATURATION']}; C-EFFICIENCY {res['lines']['C-EFFICIENCY']}."]
        for k in ("item_errors", "gate_failures", "paused"):
            if res.get(k):
                out += [f"{k}: " + "; ".join(map(str, res[k]))]
        if res.get("missing_count"):
            out.append(f"registered reads with no record: {res['missing_count']} (reads, not cells); first: {res['missing_reads'][:5]}")
        out += ["", *unreachable_table(), ""]
        return L.emit(L.tag_positives("\n".join(out)))
    cnt = res["counts"]
    out += [f"Counts: {cnt['cells']} planned cells (cells); {cnt['reads_recorded']} read records of {cnt['reads_expected']} expected (reads; a cell has one read per snapshot, F-OQ cells two); {cnt['ladder_cells_with_not_reached']} ladder-cell labels with snapshots recorded NOT REACHED (cells).", ""]
    out += capacity_section(res) + saturation_section(res) + efficiency_section(res)
    out += ["## Loaded cells and ladder stops", stage_line(res, "train (ladder)"), ""]
    out += table(["ladder cell", "U_run (the whole cell stopped here)"], [[k, v["u_run"]] for k, v in res["ladder_stops"].items()])
    out += ["", "Items beyond the stop are recorded NOT REACHED, not missing: " + (", ".join(f"{k}: {len(v)}" for k, v in sorted(res["not_reached"].items())[:6]) + (" ..." if len(res["not_reached"]) > 6 else "") or "none"), ""]
    out += ["## Reference qualification", stage_line(res, "rehearsal (R2 table) and registered R2 re-read"), ""]
    q = res["qualification"]
    out += [f"NOT QUALIFIED AT row {row} fraction {frac}: {sorted({'a', 'b', 'c'} - set(conds))}" for row, fr in q.items() for frac, conds in fr.items() if set(conds) != {"a", "b", "c"}] or ["no condition is unqualified at a fraction"]
    out += [f"REFERENCE FAILED DEP: row {r['row']}, replicate {r['draw']}, update {r['update']}, conditions {r['conditions']} (not applied at that snapshot in that replicate, for every arm of the row)" for r in res["reference_failed_dep"]]
    out += ["", *readings_section()]
    out += ["", "## Counted work per query (logical counts; not measured efficiency)", ""]
    out += table(["arm", "cell", "K", "V", "W"], [[r["arm"], r["cell"], r.get("K"), r.get("V"), r.get("W")] for r in res["counted_work"]])
    out += ["", "## Read-path throughput", stage_line(res, "throughput")]
    state = (throughput or {}).get("state", "PAUSED")
    out += ["THROUGHPUT PENDING" if state == "PAUSED" else ("THROUGHPUT NOT MEASURED (by a recorded decision)" if state == "NOT MEASURED" else "measured, RAM, one process, quiet condition met: descriptive only; not storage I/O, not latency"), ""]
    out += unreachable_table() + [""]
    return L.emit(L.tag_positives("\n".join(out)))
