# ruff: noqa: E501
"""The outcome report (ADR-0022 sections 11.3, 11.4, 11.5, 17): a markdown text and a machine-readable record, both headed by the oracle-assisted line wherever a class, label, annotation, mechanism,
router, GEN, composition or cost line appears. ``render_report`` composes only through ``output.block`` (every part after the heading goes under the line; the notes too) and ``output.check_text``
refuses anything else; the tests feed it synthetic records of the whole registry.

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


def design_suffix(design: Mapping[str, Any]) -> str:
    return f"({design.get('replicates', '?')} replicates, U = {design.get('updates', '?')})"


def class_table(classes: Mapping[str, Mapping[str, Mapping[str, Any]]], design: str) -> list[str]:
    rows = ["Table 1. Mechanism class per order, over all replicates " + design + "; the oracle-assisted line above applies to the whole table and to this caption.", "| mechanism | order AB | order BA | reasons | design |", "|---|---|---|---|---|"]
    for mech, by in classes.items():
        reasons = "; ".join(f"{o}: {', '.join(c.get('reasons', []))}" for o, c in by.items() if c.get("reasons"))
        if mech == "L-seq":
            reasons = (reasons + "; " if reasons else "") + "NO PERMUTATION CONTROL (ADAPTER)"
        rows.append(f"| {mech} | {by['AB']['class']} | {by['BA']['class']} | {reasons} | {design} |")
    return rows


def gate_table(gates: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[str]:
    rows = ["Table 2. Cell gates per mechanism, order and replicate (ACQ1, ACQ2, RET; NOT_EVALUATED where a gap is undefined, a control record is missing or a value is not finite); the oracle-assisted line above applies to the whole table and to this caption.", "| mechanism/order | replicate | ACQ1 | ACQ2 | RET | negative acquisition | negative retention | CONSOLIDATION-REJECTED | below floor |", "|---|---|---|---|---|---|---|---|---|"]
    for key, reps in gates.items():
        for i, g in enumerate(reps):
            rows.append(f"| {key} | {i} | {_fmt(g['acq1']['ok'])} | {_fmt(g['acq2']['ok'])} | {_fmt(g['ret']['ok'])} | {_fmt(g['neg_acq'])} | {_fmt(g['neg_ret'])} | {g['rejected']} | {g['below_floor']} |")
    return rows


def _means(m: Mapping[str, Any]) -> str:
    return ", ".join(f"{k} {_fmt(v)}" for k, v in m.items())


def annotation_lines(ann: Mapping[str, Any], detail: Mapping[str, Any] | None = None) -> list[str]:
    """The mandatory annotations. A warning that holds in any replicate or order is printed as holding, with the mean beside it (the lead's ruling on reading 5)."""
    detail = detail or {}
    out = ["Mandatory annotations (they do not change the label); each is printed under the oracle-assisted line:"]
    for name, v in ann.items():
        d = detail.get(name)
        extra = f" (rule: {d['rule']}; means beside it: {_means(d['mean'])})" if d else ""
        if name == "APPEND COST":
            for k, x in v["change_in_G_first_at_append"].items():
                out.append(f"- APPEND COST {k}: change in G of the first capability at the append point {_fmt(x)}")
        elif v is None:
            out.append(f"- {name}: {core.NOT_EVALUATED}{extra}")
        else:
            out.append(f"- {name}: {'yes' if v else 'no'}{extra}")
    return out


NOTES = (
    "The ADR's reference test of the read against the P9 flat memory was dropped by the lead's choice (section 3); the read is unit-tested against its definition instead.",
    "The append cost depends on the initialization of the appended keys (the same normal distribution, standard deviation 0.02, as the first-stage keys, drawn with the stage-2 seed).",
    "Both teachers were trained on OPUS, which includes Tatoeba; this raises the teachers' scores and enlarges the gap the student must close; it does not help the student.",
    "The two capabilities are two translation directions, two capabilities of one kind.",
    "chrF-norm is implemented in the study (sacrebleu is not in the lock); the cross-check against sacrebleu is made in the data-generation step.",
    "The combined tasks C1 and C2 follow the ADR-0022 addendum (human-approved 2026-11-15): C1 alternates the order of the two languages by item, C2 is German then French; the composition rule is the strengthened per-answer rule, with revision 5's ratio printed beside it as replaced.",
    "GEN is measured twice for the marker stratum (the lead's ruling on the audit's C-M6): with the decision at token 64 as registered and with the decision at the last token of the first marker-like string in tokens 1-64; the existing threshold (a loss increase of at most 0.02 nats) must hold under both; the false-trigger rate is a printed diagnostic only.",
    "The bootstrap intervals are 95% percentile intervals of the mean over items, 10,000 resamples, a fresh generator seeded 220906 per interval, drawn in the analysis stage only, in the order of the table; they are descriptive and enter no rule.",
    "EXACT-MATCH WEAK keeps the definedness floor of 0.30 on the exact-match gap as written; teacher-minus-student exact-match rates are likely below 0.30, so it is expected to print NOT_EVALUATED (the audit's C-m8; the choice of a different floor is the lead's).",
    "E-table trains at the store's calibrated learning rate (a reading not listed among the freeze readings; reported to the lead).",
    "Route accuracy on general prefixes is measured on 64-token pieces of the WikiText-2 train file that the router did not see in training, never on the GEN windows (a reading, reported to the lead).",
    "Warning annotations (NO ADVANTAGE OVER SEPARATE ADAPTERS, RETRIEVAL SUFFICES, LEXICON-EQUIVALENT, TEACHER-EQUIVALENT-TO-GOLD, BELOW JOINT BOUND, EXACT-MATCH WEAK) are printed if they hold in any replicate or order, with the mean beside them.",
)


def overlap_line(overlap: Mapping[str, float]) -> str:
    """The share of training items common to each pair of replicates (section 5.2); the reading of 'every replicate' is given with it."""
    pairs = ", ".join(f"{k}: {v:.3f}" for k, v in sorted(overlap.items()))
    return f"Share of training items common to each pair of replicates (all replicates draw from one accepted pool per capability, so their draws overlap): {pairs}."


def composition_lines(comp: Mapping[str, Any], design: str) -> list[str]:
    """The composition lines of the combined-tasks addendum section 8: n, every H_a per cell, the single-task G_a^C, Stage 0's per-answer combined and single scores (the floor), the pass rate, and
    revision 5's ratio labelled as replaced. The ensemble's and Stage 0's values carry no composition word."""
    n = comp.get("n_replicates", "?")
    out = [f"Table 4. Composition on E_C (the strengthened per-answer rule, addendum section 8) {design}; both fixed lines above apply to the whole table and to this caption. Descriptive; n replicates = {n}. A high H with a low exact-match pass rate is contamination, not composition."]
    for kind, arms in comp.get("arms", {}).items():
        for arm, rec in arms.items():
            if arm == "_stage0":
                v = rec
                out.append(f"- {kind} Stage 0 (the floor of the rule, no composition word): per-answer combined {v.get('s_combined')}, per-answer single {v.get('s_single')}")
            elif arm == "_ensemble":
                out.append(f"- {kind} ensemble (BY CONSTRUCTION, no composition word): H per answer {rec.get('H')}")
            else:
                items = f"n items {rec.get('n_items', '-')}; items per answer {rec.get('items_per_answer') or '-'}"
                tail = ""
                if rec.get("rests_on"):
                    tail = f"; this COMPOSES line rests on {rec['rests_on']}" if rec["composition"] == "COMPOSES" else f"; its German answer is BY CONSTRUCTION (the line rests on {rec['rests_on']})"
                out.append(f"- {kind} {arm}: {rec['composition']} {design} ({items}; n replicates = {n}); exact-match pass rate {_fmt(rec['mean_pass_rate'])} (a high H with a low pass rate is contamination, not composition){tail}; reasons: {'; '.join(rec['reasons']) or 'none'}; revision 5's ratio C/(0.80 S), {rec['label']}: {rec['revision5_ratio_replaced']}")
                for o, cells in rec["orders"].items():
                    for c in cells:
                        if c and "NOT_EVALUATED" in c:
                            out.append(f"  - order {o}, replicate {c['replicate']}: NOT_EVALUATED, {c['NOT_EVALUATED']}")
                            continue
                        h = dict(c["H"]) if c else {}
                        if c and rec.get("by_construction_answers"):
                            h["A"] = f"BY CONSTRUCTION ({h.get('A')})"
                        out.append("  - order " + o + (f", replicate {c['replicate']} (n items {c.get('n_items')}; per answer {c.get('items_per_answer')}): H {h}, single-task G {c['single_task_G']}, s combined {c['s_combined']}, s single {c['s_single']}" if c else ": no record"))
    return out


def gen_lines(rows: Sequence[Mapping[str, Any]], routers: Sequence[Mapping[str, Any]]) -> list[str]:
    out = ["Table 3. General quality under the keyword router (GEN) per snapshot, measured twice for the marker stratum (the decision at token 64 as registered, and the decision at the last token of the first marker-like string in tokens 1-64); the existing threshold of 0.02 nats must hold under both. With the router's false-trigger count per stratum, the always-on diagnostic and the router diagnostic; the oracle-assisted line above applies to the whole table and to this caption. A pass is described as the keyword router stayed silent, not as the memory preserving general language.",
           "| snapshot | loss increase, decision at token 64 (nats per token) | loss increase, decision at first marker string | GEN gate (both decisions) | false triggers at token 64 (marker-like / ordinary) | false triggers at first marker string (marker-like / ordinary) | always-on loss increase |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        ft = r.get("false_triggers") or {}
        fm = r.get("false_triggers_first_marker") or {}
        out.append(f"| {r['cell']} | {_fmt(r['loss_increase'])} | {_fmt(r.get('loss_increase_first_marker'))} | {_fmt(r['gen_gate'])} | {ft.get('marker', '-')} / {ft.get('ordinary', '-')} | {fm.get('marker', '-')} / {fm.get('ordinary', '-')} | {_fmt(r.get('always_on_loss_increase'))} |")
    out += ["Router diagnostic (it enters no rule): false-trigger rate on the marker-like windows when the decision is taken at the last token of the first marker-like string within tokens 1-64:"]
    for r in routers:
        d = r.get("diagnostic_first_marker") or {}
        out.append(f"- replicate {r['replicate']}, router {r['router_tasks']}: {_fmt(d.get('rate'))} ({d.get('count', '-')} of {d.get('n', '-')} windows); route accuracy {r.get('accuracy')}")
    return out


def interval_lines(outcome: Mapping[str, Any]) -> list[str]:
    """Table 5: every printed score with its bootstrap interval, the score on single-reference items alone, and the reference-count distribution; E_open where it was scored."""
    if not outcome.get("intervals_computed"):
        return ["Table 5. Scores with bootstrap intervals: NOT_EVALUATED (the intervals are drawn in the analysis stage, seed 220906, and were not computed in this analysis); the oracle-assisted line above applies to this caption."]
    out = [f"Table 5. Every printed score with its 95% percentile bootstrap interval over items ({outcome.get('bootstrap_resamples', 10000):,} resamples, seed 220906, a fresh generator per interval, drawn in the analysis stage only; descriptive, enters no rule), the score on single-reference items alone (section 5.2) and the reference-count distribution; the oracle-assisted line above applies to the whole table and to this caption.",
           "| score | mean | interval | items | single-reference items | single-reference score | references per item |", "|---|---|---|---|---|---|---|"]
    for e in outcome["intervals"]:
        iv = f"[{_fmt(e['lo'])}, {_fmt(e['hi'])}]" if e.get("lo") is not None else core.NOT_EVALUATED
        sr = e.get("single_reference") or {}
        out.append(f"| {e['name']} | {_fmt(e.get('mean'))} | {iv} | {_fmt(e.get('n'))} | {sr.get('n', '-')} | {_fmt(sr.get('mean')) if sr else '-'} | {e.get('reference_counts') or '-'} |")
    if not any("E_open" in e["name"] for e in outcome["intervals"]):
        out.append("E_open (descriptive only; at least one out-of-vocabulary word): not scored in this record (NOT_EVALUATED).")
    return out


def consolidation_lines(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    out = ["Table 6. M-ii consolidation per cell (section 6.3): the share of first-stage rows that changed at all, the change of the first-stage gate g_1, the relative change of the first-stage value rows against the modification floor, and how the cell was scored (selected on D_con, then confirmed on E); the oracle-assisted line above applies to the whole table and to this caption.",
           "| cell | CONSOLIDATION-REJECTED | published | below floor | relative change | changed-row share | g_1 change | scored |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['cell']} | {_fmt(r.get('rejected'))} | {_fmt(r.get('published'))} | {_fmt(r.get('below_floor'))} | {_fmt(r.get('relative_change'))} | {_fmt(r.get('changed_row_share'))} | {_fmt(r.get('g1_change'))} | {r.get('scored_on', 'selected on D_con, then confirmed on E')} |")
    return out


def training_lines(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    out = ["Table 7. Updates and rows per update of every trained cell (section 6.3: updates and rows are reported; replay cells see twice the rows per update); the oracle-assisted line above applies to the whole table and to this caption.",
           "| cell | updates | batch | replay rows | rows per update | device |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['cell']} | {_fmt(r.get('updates'))} | {_fmt(r.get('batch'))} | {_fmt(r.get('replay_rows'))} | {_fmt(r.get('rows_per_update'))} | {_fmt(r.get('device'))} |")
    return out


def m_ii_gen_sentence(outcome: Mapping[str, Any]) -> list[str]:
    """Section 11.3: "When M-ii alone fails GEN, row 8 applies and the report says so." A missing or non-finite M-ii GEN value is NOT_EVALUATED and is said so, not called a failure."""
    gen = outcome.get("gen") or {}
    out: list[str] = []
    if gen.get("M-ii alone fails GEN"):
        out.append("M-ii alone fails GEN while M-append-frozen holds it: row 8 applies (TRANSFER-POSITIVE (append-frozen)), by section 11.3.")
    status = (gen.get("status") or {}).get("M-ii") or {}
    if any(v == "not_evaluated" for v in status.values()):
        out.append("M-ii's GEN is NOT_EVALUATED in at least one order (a value is missing or not finite): it is not a measured failure; row 7 does not apply.")
    return out


def render_report(outcome: Mapping[str, Any], *, title: str = "P10-S2 outcome report", extra: Sequence[str] = ()) -> str:
    """The report text. Every part after the heading is a block that begins with the oracle-assisted line (and the second fixed line for a composition line); ``check_text`` verifies it before the text is returned."""
    design = design_suffix(outcome["design"])
    parts: list[str] = [f"# {title}", "", "Standing: self-check. Astra review: NOT_PERFORMED. Not independent review, not human approval. Implementation on synthetic stand-ins unless a registered run is recorded elsewhere."]
    label_lines = [f"Study label (row {outcome['label_row']}): **{outcome['label_with_design']}**"]
    label_lines += [f"- reason: {r}" for r in outcome.get("not_evaluated_reasons", [])]
    label_lines += [f"- engineering: {e}" for e in outcome.get("engineering", [])]
    label_lines += [f"- incomplete: {e}" for e in outcome.get("incomplete", [])]
    label_lines += [f"- control failed: {e}" for e in outcome.get("control_failed", [])]
    label_lines += [f"- control NOT_EVALUATED: {e}" for e in outcome.get("control_not_evaluated", [])]
    label_lines += [f"- {s}" for s in m_ii_gen_sentence(outcome)]
    parts += ["", block(label_lines)]
    parts += ["", block(class_table(outcome["classes"], design))]
    if outcome.get("gates"):
        parts += ["", block(gate_table(outcome["gates"]))]
    if outcome.get("gen_table"):
        parts += ["", block(gen_lines(outcome["gen_table"], outcome.get("router_table", [])))]
    if outcome.get("annotations"):
        parts += ["", block(annotation_lines(outcome["annotations"], outcome.get("annotation_detail")))]
    if outcome.get("composition"):
        parts += ["", block(composition_lines(outcome["composition"], design), composition=True)]
    if outcome.get("cost_lines"):
        parts += ["", block(["Cost and active-memory lines (registered rules, descriptive standing; none is an efficiency result):", *[f"- {c}" for c in outcome["cost_lines"]]])]
    if "intervals_computed" in outcome:
        parts += ["", block(interval_lines(outcome))]
    if outcome.get("consolidation"):
        parts += ["", block(consolidation_lines(outcome["consolidation"]))]
    if outcome.get("training"):
        parts += ["", block(training_lines(outcome["training"]))]
    parts += ["", block(["Printed by construction (they enter no class and no label):", *[f"- {k}: {v}" for k, v in outcome.get("by_construction", {}).items()]])]
    rc = outcome.get("recomputation")
    if rc:
        lines = [f"Independent recomputation: state {rc['state']}; cells marked NOT_EVALUATED by a difference beyond tolerance: {', '.join(rc['not_evaluated_cells']) or 'none'}; differences listed: {len(rc.get('differences', []))}"]
        parts += ["", block(lines)]
    if extra:
        parts += ["", *extra]
    parts += ["", "## Notes", "", block([f"- {x}" for x in NOTES]), "", "## What S2 cannot establish", "", block([f"- {core.LEAD_RULE}", *[f"- {x}" for x in NOT_ESTABLISHED]])]
    text = "\n".join(parts) + "\n"
    check_text(text)
    return text


def render_json(outcome: Mapping[str, Any]) -> dict[str, Any]:
    rec = outcome_record(outcome)
    check_record(rec)
    return rec


def summary_lines(outcome: Mapping[str, Any]) -> list[str]:
    """The terminal and log summary: the label and the classes (each with "(n replicates, U = ...)"), to be passed to ``output.emit`` (which heads them with the oracle-assisted line)."""
    design = design_suffix(outcome["design"])
    out = [f"label: {outcome['label_with_design']}"]
    for mech, by in outcome["classes"].items():
        out.append(f"{mech}: AB {by['AB']['class']}, BA {by['BA']['class']} {design}")
    out += m_ii_gen_sentence(outcome)
    return out
