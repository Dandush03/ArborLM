# ruff: noqa: E501
"""P10IR report (ADR-0029 sections 1, 8 to 10): Markdown from the analysis, no torch. Every printed label carries the stage tag (``REGISTERED RE-ANALYSIS OF OBSERVED CELLS`` for A1,
``FRESH CHECKPOINTS`` for A2) and ``ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK``; the limit sentence of section 9 is printed with every label block.
Nothing here is a success claim: ArborLM is unproven research."""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core, labels

HEADER = (
    "ArborLM is unproven research. This report is a diagnosis of read-time reads over memories trained under the registered read; it is neither a positive nor a negative result for ArborLM. "
    "Implementation self-checked only: not independent review, not Astra validation, not human approval. `Astra review: NOT_PERFORMED`."
)


def tagged(label: str, stage_tag: str) -> str:
    """``label [stage tag; standing tag]``: the only way a label is printed."""
    return f"{label} [{stage_tag}; {core.STANDING_TAG}]"


def _f(x: Any, nd: int = 3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    return f"{float(x):.{nd}f}"


def _rows_line(reps: Sequence[Mapping[str, Any]]) -> str:
    out = []
    for r in reps:
        suffix = f" {r['suffix']}" if r.get("suffix") else ""
        mainly = f" ({r['tags']['mainly']})" if r.get("tags", {}).get("mainly") else ""
        out.append(f"d{r['draw']}: {r['row']}{suffix}{mainly}")
    return "; ".join(out)


def _retention_lines(reps: Sequence[Mapping[str, Any]]) -> list[str]:
    """The retention status of every comparison with the accuracy version beside it (ruling 3; the accuracy version decides nothing)."""
    out = ["    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):"]
    for r in reps:
        parts = []
        for read, e in (r.get("retention") or {}).items():
            if not e:
                parts.append(f"{read}: n/a")
            else:
                parts.append(f"{read} " + " / ".join(f"{p}: {e[p]['status']} (accuracy version {_f(e[p]['accuracy_version'])})" for p in labels.PANELS))
        out.append(f"      - d{r['draw']}: " + "; ".join(parts))
    return out


def _component_text(name: str, comp: Mapping[str, Any], stage_tag: str) -> list[str]:
    lines = [f"- **{name}: {tagged(str(comp['value']), stage_tag)}**"]
    for cp in labels.CHECKPOINTS:
        at = comp["at"][cp]
        cells = ", ".join(f"{c} = {v}" for c, v in at["cells"].items())
        lines.append(f"  - at {cp}: {at['value']} ({cells})")
    return lines


def render_stage(a: Mapping[str, Any], title: str) -> list[str]:
    tag = str(a["stage_tag"])
    out = [f"## {title}", ""]
    rd = a.get("r_diagnosis")
    if rd is not None:
        out.append(f"**R-DIAGNOSIS: {tagged(str(rd['value']), tag)}**")
        out.append("")
        if not rd["evaluable"]:
            out.append("Both components are printed with their NOT EVALUABLE primary cells; nothing of the combination is applied (section 9 item 1).")
            out.append("- NOT EVALUABLE (component, cell, checkpoint): " + "; ".join(f"{c} / {cell} / {cp}" for c, cell, cp in rd["not_evaluable_cells"]))
        out += _component_text("tree component", rd["components"]["tree"], tag)
        out += _component_text("index component", rd["components"]["index"], tag)
        if rd["evaluable"]:
            out.append(f"- pair (tree, index): ({rd['pair'][0]}, {rd['pair'][1]})")
            out.append(f"- recommended action, tree component: {rd['recommended']['tree'] or 'none'}")
            out.append(f"- recommended action, index component: {rd['recommended']['index'] or 'none'}")
            if rd["banner"]:
                out.append(f"- **{tagged(rd['banner'], tag)}**: recommends nothing; a failure of read-time reads to identify a cause is not evidence that nothing short of a fundamental change would work (section 9).")
        out.append("")
        out.append(core.LIMIT_SENTENCE)
        out.append("")
    ld = a["r_diagnosis_loaded"]
    out.append("### R-DIAGNOSIS-LOADED (descriptive; printed only; recommends nothing; no combination rule)")
    out.append("")
    for cell, by_cp in ld["cells"].items():
        for cp, lab in by_cp.items():
            out.append(f"- {cell} at {cp}: tree {tagged(lab['tree'], tag)}; index {tagged(lab['index'], tag)}")
    out.append("")
    out.append("### Cells and checkpoints")
    out.append("")
    for name, cell in a["cells"].items():
        tags = ("; ".join(cell["tags"]) + "; ") if cell["tags"] else ""
        out.append(f"#### {name} ({cell['role']}; {tags}facts {cell['facts']}, slots {cell['slots']})")
        out.append("")
        for cp, ck in cell["checkpoints"].items():
            descr = " (trajectory; descriptive; enters no label)" if ck["descriptive_only"] else ""
            out.append(f"- **{cp}, update {ck['update']}{descr}**")
            plateau = ck.get("plateau")
            extra = f" [{'; '.join(plateau['tags'])}]" if plateau and plateau.get("tags") else (f" [plateau check {plateau['status']}]" if plateau else "")
            out.append(f"  - tree label: {tagged(ck['tree']['label'], tag)}{extra}")
            out.append(f"    - replicates: {_rows_line(ck['tree']['replicates'])}")
            out += _retention_lines(ck["tree"]["replicates"])
            out.append(f"  - index label: {tagged(ck['index']['label'], tag)}{extra}")
            out.append(f"    - replicates: {_rows_line(ck['index']['replicates'])}")
            out += _retention_lines(ck["index"]["replicates"])
            out.append(f"    - median c*: {_f(ck['index']['c_star_median'], 1)} keys, share of N: {_f(ck['index']['c_star_share_of_N'])}, N/8 for comparison: {_f(ck['index']['descriptive']['N_over_8'], 1)}; replicates without c*: {ck['index']['replicates_without_c_star']}")
            if ck["tree"].get("seal_note"):
                out.append(f"    - CONTENT rows carry: {ck['tree']['seal_note']}")
            out += _tree_printed(ck["tree"]["descriptive"])
            out += _index_printed(ck["index"]["descriptive"])
        out.append("")
    ctx = a.get("context") or {}
    if ctx:
        out.append("### Context from P10-S1's records (descriptive)")
        out.append("")
        for k, v in ctx.items():
            out.append(f"- {k}: {v}")
        out.append("")
    return out


def _tree_printed(d: Mapping[str, Any]) -> list[str]:
    out = ["  - printed with the tree label (means over the replicates present):"]
    reads = ", ".join(f"{r}: i {_f(v['i'])}, a_use {_f(v['a_use'])}" for r, v in d["reads"].items())
    out.append(f"    - {reads}")
    cm = d["closure_means"]
    out.append(f"    - g_P {_f(cm.get('g_P'))}, g_C {_f(cm.get('g_C'))}, g_PC {_f(cm.get('g_PC'))}; i(F0) - i(T2) {_f(d['i_f0_minus_t2'])}")
    sweep = "; ".join(f"v={v}: " + (f"NOT APPLICABLE ({s['reason']})" if s["status"] == "NOT APPLICABLE" else f"i on {_f(s['i_on'])}, off {_f(s['i_off'])}, CR8(on) {_f(s['cr8_on'])}, keys scored {_f(s['keys_scored_per_query_on'], 0)}") for v, s in d["sweep"].items())
    out.append(f"    - visit sweep Tv: {sweep}")
    m = d["t0_measures"]
    out.append(f"    - T0: CR8 {_f(m['cr8'])}, CR1 {_f(m['cr1'])}, SR8 {_f(m['sr8'])}, AM_C {_f(m['am_c'])}, AM_S {_f(m['am_s'])}")
    pe = d["prior_effect"]
    out.append(
        f"    - prior effect: i(T1)-i(T0) {_f(pe['i_T1_minus_T0'])}, i(T1w)-i(T0) {_f(pe['i_T1w_minus_T0'])}, i(T2)-i(T3) {_f(pe['i_T2_minus_T3'])}; selection changed T0->T1 {_f(pe['share_selection_changed_T0_to_T1'])}; "
        f"facts spanning both branches {_f(pe['share_facts_span_both_branches_T0'])}; TV distance T0->T1 {_f(pe['tv_distance_T0_to_T1'])}"
    )
    t = d["testability"]
    out.append(f"    - testability of the candidate restriction: share of facts whose T3 selection equals T0's {_f(t['share_T3_selection_equals_T0'])} ({t['note']})")
    return out


def _index_printed(d: Mapping[str, Any]) -> list[str]:
    out = ["  - printed with the index label:"]
    out.append(f"    - F0: i {_f(d['F0']['i'])}, a_use {_f(d['F0']['a_use'])}; I256@512: i {_f(d['I256@512']['i'])}, a_use {_f(d['I256@512']['a_use'])}, CR8 {_f(d['I256@512']['cr8'])}, measured candidates mean {_f(d['I256@512']['candidates_mean'], 1)}, p99 {_f(d['I256@512']['candidates_p99'], 1)}")
    for c, b in d["budgets"].items():
        if b["status"] == "NOT APPLICABLE":
            out.append(f"    - I64@{c}: NOT APPLICABLE ({b['reason']})")
        else:
            out.append(f"    - I64@{c}: i {_f(b['i'])}, a_use {_f(b['a_use'])}, CR8 {_f(b['cr8'])}, CR1 {_f(b['cr1'])}, AM_C {_f(b['am_c'])}, candidates mean {_f(b['candidates_mean'], 1)}, p99 {_f(b['candidates_p99'], 1)}")
    return out


def render(full: Mapping[str, Any], plan_note: str = "") -> str:
    """The whole report: header, R-CONFIRM, A1, A2 (if any), the readings, what may be said."""
    out = ["# P10-I-R routing diagnosis (ADR-0029)", "", HEADER, ""]
    if plan_note:
        out += [plan_note, ""]
    conf = full["r_confirm"]
    out.append("## R-CONFIRM (does not change R-DIAGNOSIS)")
    out.append("")
    for name in ("R-CONFIRM-TREE", "R-CONFIRM-INDEX"):
        c = conf[name]
        detail = f" (A1: {c['a1']}; A2: {c['a2']})" if "a1" in c else ""
        out.append(f"- **{name}: {c['value']}**{detail}")
    out.append("")
    sa = full["statement_allowed"]
    out.append("## What may be said")
    out.append("")
    out.append(f"- After A1 alone: \"{sa['after_a1_alone']}\".")
    out.append(f"- A statement that the tree's gap is caused by a named factor at read time requires R-CONFIRM-TREE: CONFIRMED. Allowed here: {sa['caused_by_a_named_factor_at_read_time']}.")
    out.append("- Neither A1 nor A2 supports a statement about training-time causes (Stage B).")
    out.append("")
    out += render_stage(full["A1"], "Stage A1")
    if full.get("A2"):
        out += render_stage(full["A2"], "Stage A2")
    if full["r_confirm"]["R-CONFIRM-TREE"]["value"] == "NOT RUN":
        out += ["R-CONFIRM is computed by the separate `confirm` stage (group A2) against this record; this record is never rewritten.", ""]
    errs = full.get("item_errors")
    if errs is not None:
        out += [f"ITEM ERRORS (worker code raised inside an item; counted apart from gate failures): {len(errs)}" + ("" if not errs else "; " + "; ".join(errs[:10])), ""]
    out.append("## Readings of the ADR taken here (each the most conservative course)")
    out.append("")
    for k, v in full["A1"]["readings"].items():
        out.append(f"- {k}: {v}")
    out.append("")
    out.append("`Astra review: NOT_PERFORMED`.")
    return "\n".join(out) + "\n"


def render_confirm(record: Mapping[str, Any], note: str = "") -> str:
    """The ``confirm`` stage's report section: R-CONFIRM-TREE and R-CONFIRM-INDEX against A1's frozen analysis record, and A2's own analysis."""
    out = ["# P10-I-R confirmation (ADR-0029 section 10; stage `confirm`, group A2)", "", HEADER, ""]
    if note:
        out += [note, ""]
    out.append(f"Against A1's analysis record, SHA-256 {record['a1_analysis_sha256']}; that record is not rewritten.")
    out += ["", "## R-CONFIRM (does not change R-DIAGNOSIS)", ""]
    for name in ("R-CONFIRM-TREE", "R-CONFIRM-INDEX"):
        c = record["r_confirm"][name]
        detail = f" (A1: {c['a1']}; A2: {c['a2']})" if "a1" in c else ""
        out.append(f"- **{name}: {c['value']}**{detail}")
    sa = record["statement_allowed"]
    out += ["", f"- A statement that the tree's gap is caused by a named factor at read time requires R-CONFIRM-TREE: CONFIRMED. Allowed here: {sa['caused_by_a_named_factor_at_read_time']}.", ""]
    errs = record.get("item_errors")
    if errs is not None:
        out += [f"ITEM ERRORS (worker code raised inside an item; counted apart from gate failures): {len(errs)}" + ("" if not errs else "; " + "; ".join(errs[:10])), ""]
    out += render_stage(record["A2"], "Stage A2")
    out.append("`Astra review: NOT_PERFORMED`.")
    return "\n".join(out) + "\n"
