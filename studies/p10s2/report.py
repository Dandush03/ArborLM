# ruff: noqa: E501
"""The outcome report (ADR-0022 sections 11.3, 11.4, 11.5, 17): a markdown text and a machine-readable record, both headed by the oracle-assisted line wherever a class, label, annotation, mechanism,
router, composition or cost line appears. ``render_report`` composes only through ``output.block`` and ``output.check_text`` refuses anything else; the tests feed it synthetic records of the whole registry.

Standing: self-check. Astra review: NOT_PERFORMED. Nothing in a report is a success of the science; the registered label is the only statement the design permits, and only with the line.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core
from .analysis import outcome_record
from .output import block, check_record, check_text

NOT_ESTABLISHED = (
    "Autonomous learned memory: addresses and routes are supplied by rule.",
    "Anything about routing beyond keyword detection.",
    "That the sparse keyed store beats a word-vector table, unless E-table loses.",
    "That knowledge came from the teachers rather than from gold data, unless the teacher-only arm passes.",
    "Retention as an advantage: retention in the shared store is retention against crosstalk that the shared top-8 itself creates.",
    "That sparsity protects earlier knowledge: different tasks touch different rows only because their oracle codes differ.",
    "Knowledge fusion, skill transfer, complementarity in kind, large models, superiority, storage, latency, efficiency, capacity scaling or locality.",
    "A success probability: three or four replicates on one partition of one corpus.",
    "That MPS-trained snapshots would be reproduced by re-running.",
    "A failure of the ArborLM concept, whatever the outcome.",
)


def _fmt(x: Any) -> str:
    if x is None:
        return core.NOT_EVALUATED
    if isinstance(x, float):
        return f"{x:.3f}"
    return str(x)


def class_table(classes: Mapping[str, Mapping[str, Mapping[str, Any]]], design: str) -> list[str]:
    rows = ["Table 1. Mechanism class per order, over all replicates " + design + "; the oracle-assisted line above applies to the whole table and to this caption.", "| mechanism | order AB | order BA | reasons |", "|---|---|---|---|"]
    for mech, by in classes.items():
        reasons = "; ".join(f"{o}: {', '.join(c.get('reasons', []))}" for o, c in by.items() if c.get("reasons"))
        if mech == "L-seq":
            reasons = (reasons + "; " if reasons else "") + "NO PERMUTATION CONTROL (ADAPTER)"
        rows.append(f"| {mech} | {by['AB']['class']} | {by['BA']['class']} | {reasons} |")
    return rows


def gate_table(gates: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[str]:
    rows = ["Table 2. Cell gates per mechanism, order and replicate (ACQ1, ACQ2, RET; NOT_EVALUATED where a gap is undefined or a value is not finite); the oracle-assisted line above applies to the whole table and to this caption.", "| mechanism/order | replicate | ACQ1 | ACQ2 | RET | negative acquisition | negative retention | CONSOLIDATION-REJECTED | below floor |", "|---|---|---|---|---|---|---|---|---|"]
    for key, reps in gates.items():
        for i, g in enumerate(reps):
            rows.append(f"| {key} | {i} | {_fmt(g['acq1']['ok'])} | {_fmt(g['acq2']['ok'])} | {_fmt(g['ret']['ok'])} | {_fmt(g['neg_acq'])} | {_fmt(g['neg_ret'])} | {g['rejected']} | {g['below_floor']} |")
    return rows


def annotation_lines(ann: Mapping[str, Any]) -> list[str]:
    out = ["Mandatory annotations (they do not change the label); each is printed under the oracle-assisted line:"]
    for name, v in ann.items():
        if name == "APPEND COST":
            for k, x in v["change_in_G_first_at_append"].items():
                out.append(f"- APPEND COST {k}: change in G of the first capability at the append point {_fmt(x)}")
        elif name == "COMPOSES":
            for k, x in v.items():
                out.append(f"- COMPOSES {k}: {_fmt(x['composes'])} (layout: {x['layout'] or 'not scored'})")
        elif v is None:
            out.append(f"- {name}: {core.NOT_EVALUATED}")
        else:
            out.append(f"- {name}: {'yes' if v else 'no'}")
    return out


NOTES = (
    "The ADR's reference test of the read against the P9 flat memory was dropped by the lead's choice (section 3); the read is unit-tested against its definition instead.",
    "The append cost depends on the initialization of the appended keys (the same normal distribution, standard deviation 0.02, as the first-stage keys, drawn with the stage-2 seed).",
    "Both teachers were trained on OPUS, which includes Tatoeba; this raises the teachers' scores and enlarges the gap the student must close; it does not help the student.",
    "The two capabilities are two translation directions, two capabilities of one kind.",
    "chrF-norm is implemented in the study (sacrebleu is not in the lock); the cross-check against sacrebleu is made in the data-generation step.",
    "The combined tasks C1 and C2 are scored only under a provisional layout until the lead decides how C1 pairs two sources and how C2 lays out its prompt (PENDING LEAD REVIEW).",
)


def overlap_line(overlap: Mapping[str, float]) -> str:
    """The share of training items common to each pair of replicates (section 5.2); the reading of 'every replicate' is given with it."""
    pairs = ", ".join(f"{k}: {v:.3f}" for k, v in sorted(overlap.items()))
    return f"Share of training items common to each pair of replicates (all replicates draw from one accepted pool per capability, so their draws overlap): {pairs}."


def gen_lines(rows: Sequence[Mapping[str, Any]], routers: Sequence[Mapping[str, Any]]) -> list[str]:
    out = ["Table 3. General quality under the keyword router (GEN) per snapshot, with the router's false-trigger count per stratum, the always-on diagnostic and the router diagnostic; the oracle-assisted line above applies to the whole table and to this caption. A pass is described as the keyword router stayed silent, not as the memory preserving general language.",
           "| snapshot | loss increase (nats per token) | GEN gate | false triggers (marker-like / ordinary) | always-on loss increase |", "|---|---|---|---|---|"]
    for r in rows:
        ft = r.get("false_triggers") or {}
        out.append(f"| {r['cell']} | {_fmt(r['loss_increase'])} | {_fmt(r['gen_gate'])} | {ft.get('marker', '-')} / {ft.get('ordinary', '-')} | {_fmt(r.get('always_on_loss_increase'))} |")
    out += ["Router diagnostic (it enters no rule): false-trigger rate on the marker-like windows when the decision is taken at the last token of the first marker-like string within tokens 1-64:"]
    for r in routers:
        d = r.get("diagnostic_first_marker") or {}
        out.append(f"- replicate {r['replicate']}, router {r['router_tasks']}: {_fmt(d.get('rate'))} ({d.get('count', '-')} of {d.get('n', '-')} windows); route accuracy {r.get('accuracy')}")
    return out


def render_report(outcome: Mapping[str, Any], *, title: str = "P10-S2 outcome report", extra: Sequence[str] = ()) -> str:
    """The report text. Every block that carries a guarded line begins with the oracle-assisted line; ``check_text`` verifies it before the text is returned."""
    design = f"({outcome['design'].get('replicates', '?')} replicates, U = {outcome['design'].get('updates', '?')})"
    parts: list[str] = [f"# {title}", "", "Standing: self-check. Astra review: NOT_PERFORMED. Not independent review, not human approval. Implementation on synthetic stand-ins unless a registered run is recorded elsewhere."]
    label_lines = [f"Study label (row {outcome['label_row']}): **{outcome['label_with_design']}**"]
    label_lines += [f"- reason: {r}" for r in outcome.get("not_evaluated_reasons", [])]
    label_lines += [f"- engineering: {e}" for e in outcome.get("engineering", [])]
    label_lines += [f"- incomplete: {e}" for e in outcome.get("incomplete", [])]
    label_lines += [f"- control failed: {e}" for e in outcome.get("control_failed", [])]
    parts += ["", block(label_lines)]
    parts += ["", block(class_table(outcome["classes"], design))]
    if outcome.get("gates"):
        parts += ["", block(gate_table(outcome["gates"]))]
    if outcome.get("gen_table"):
        parts += ["", block(gen_lines(outcome["gen_table"], outcome.get("router_table", [])))]
    if outcome.get("annotations"):
        parts += ["", block(annotation_lines(outcome["annotations"]))]
    if outcome.get("cost_lines"):
        parts += ["", block(["Cost and active-memory lines (registered rules, descriptive standing; none is an efficiency result):", *[f"- {c}" for c in outcome["cost_lines"]]])]
    parts += ["", block(["Printed by construction (they enter no class and no label):", *[f"- {k}: {v}" for k, v in outcome.get("by_construction", {}).items()]])]
    rc = outcome.get("recomputation")
    if rc:
        lines = [f"Independent recomputation: state {rc['state']}; cells marked NOT_EVALUATED by a difference beyond tolerance: {', '.join(rc['not_evaluated_cells']) or 'none'}; differences listed: {len(rc.get('differences', []))}"]
        parts += ["", block(lines)]
    if extra:
        parts += ["", *extra]
    parts += ["", "## Notes", "", *[f"- {x}" for x in NOTES], "", "## What S2 cannot establish", "", *[f"- {x}" for x in NOT_ESTABLISHED]]
    text = "\n".join(parts) + "\n"
    check_text(text)
    return text


def render_json(outcome: Mapping[str, Any]) -> dict[str, Any]:
    rec = outcome_record(outcome)
    check_record(rec)
    return rec


def summary_lines(outcome: Mapping[str, Any]) -> list[str]:
    """The terminal and log summary: the label and the classes, to be passed to ``output.emit`` (which heads them with the oracle-assisted line)."""
    out = [f"label: {outcome['label_with_design']}"]
    for mech, by in outcome["classes"].items():
        out.append(f"{mech}: AB {by['AB']['class']}, BA {by['BA']['class']}")
    return out
