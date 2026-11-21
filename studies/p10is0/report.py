# ruff: noqa: E501
"""P10IS0 report (ADR-0023 sections 6.5, 6.6, 7, 15): a pure function from the analysis dictionary to markdown. Every number is labelled MEASURED (read from the cell records), ANALYTICAL (the false-negative table) or absent. No cost figure is
printed as an efficiency claim. A headline of step 0 prints no scientific label. Nothing here reads a file."""

from collections.abc import Mapping, Sequence
from typing import Any

from . import labels, sealed


def _fmt(x: Any) -> str:
    return "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def render(a: Mapping[str, Any], h_ratio: Mapping[str, Sequence[float]] | None = None) -> str:
    h = a["headline"]
    out = ["# P10-I-S0 result (self-checked; not independent review, not Astra validation, not human approval)\n", f"**Headline (step {h['step']}): {h['text']}**\n"]
    if a.get("scientific_labels") is None and h["step"] == 0:
        out.append(f"No scientific label: the study is incomplete or stopped on an engineering or resource cause. Missing cells: {len(a.get('missing_cells', []))}.\n")
        return "\n".join(out) + "\n" + labels.FIXED_SENTENCES + "\n"
    out.append("## Lines (MEASURED, from the cell records)\n")
    for line in ("A", "G", "Q"):
        ln = a["lines"][line]
        states = ", ".join(f"{float(ld):g}: {s}" for ld, s in sorted(ln["states"].items(), key=lambda kv: float(kv[0])))
        out.append(f"- Line {line}: L_{line} = {_fmt(ln['L'])} ({'none' if ln['L'] is None else 'largest load held with every lower load'}); l1 = {_fmt(ln['l1'])} ({ln['l1_state']}){'; NON-MONOTONE' if ln['non_monotone'] else ''}. States by load: {states}.")
    out.append("\n## Section 7 prints at L_Q and at l1 (MEASURED)\n")
    for k, title in (("at_L_Q", "at L_Q"), ("at_l1", "at l1")):
        for s, v in (a.get(k) or {}).items():
            out.append(f"- {title}, series {s} ({v['cell_type']}): {v['regime']}; {v['convergence']} {v['tags']}")
    for s, w in (a.get("l1_which_line") or {}).items():
        out.append(f"- which line fails at l1, series {s}: {w}")
    for s, w in (a.get("l1_line_a_beside_headline") or {}).items():
        out.append(f"- LINE A {w} AT l1 (series {s}); LINE G NOT EVALUABLE — REFERENCE")
    out.append(f"- {a.get('ratio_above_1_definition', '')}")
    out.append("\n## Series states by load\n")
    for ld, per in a["states_by_load_series"].items():
        out.append(f"- load {ld}: " + "; ".join(f"series {s} ({v['cell_type']}): A {v['A']}, G {v['G']}, Q {v['Q']} (combination {v['combination']})" for s, v in per.items()) + (f" — {a['holds_in_one_series_only'][ld]}" if ld in a.get("holds_in_one_series_only", {}) else ""))
    out.append("\n## Cell types: labels and descriptive measures (MEASURED)\n")
    for name, t in a["types"].items():
        d = t["descriptive"]
        x = ", ".join(f"{v:.3f}" for v in (h_ratio or {}).get(name, [])) or "disclosed separately after the outcome (command `disclose`); the registered report reads nothing sealed"
        labs = "; ".join(s.replace("{x}", x) for s in t["labels"])
        out.append(f"- {name}: {labs or 'no label'} | successes {d.get('successes')} of {d.get('evaluated_cells')} evaluated cells, one-sided 95% per-draw bound {_fmt(d.get('per_draw_bound'))} | class {d.get('class')} | n_A {d.get('n_a')} n_G {d.get('n_g')} | A5-D accuracy median {_fmt(d.get('a5d_accuracy_median'))}, A6 {_fmt(d.get('a6_accuracy_median'))}, ratio {_fmt(d.get('median_ratio_to_a6'))} | {d.get('regime')} | convergence {d['convergence']['status']} {d['convergence']['tags']} | {d.get('collapse_free')} | condition 6 decided {d.get('condition_6_decided')} cell(s) | 512-exposure readout: {d['e512_readout']['label']} (class {d['e512_readout']['class']})")
    out.append("\n## Annotations\n")
    for name, p in a["annotations"]["penalty_vs_a0"].items():
        if p:
            out.append(f"- penalty against answer-only at {name}: {p['label']} (d = {p['d']}, p = {p['p']:.4f}, {p['pairs']} pairs used)")
    out.append(f"- hypotheses (each can fail; a reading is not a success of the science): {a['annotations']['hypotheses']}")
    out.append(f"- lane licence (loads, tested cell types only): {a['annotations']['licence_loads'] or a.get('licence_text')}")
    out.append(f"- X8: {a['x8']['status']}")
    if a.get("replaced_draws"):
        out.append(f"- replaced draws: {a['replaced_draws']}")
    out.append("\n## False-negative table (ANALYTICAL, not measured; independent cells)\n")
    for r in a["false_negative_table"]:
        out.append(f"- p = {r['p']}: RELIABLE in one series {r['one_series']:.3f}, in both {r['both_series']:.3f}, Line Q at 0.5, 1 and 2 about {r['l_q_at_least_2']:.2f} ({r['kind']})")
    out.append("\n" + sealed.WAVE_LIMIT_SENTENCE)
    return "\n".join(out) + "\n\n" + labels.FIXED_SENTENCES + "\n"
