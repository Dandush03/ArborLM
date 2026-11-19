# ruff: noqa: E501
"""P10IS3 report (ADR-0026 sections 6.5, 6.6, 6.7, 12): a pure function of the analysis result. No torch, no IO. Labels carry no success claim: ArborLM is unproven research."""

from collections.abc import Mapping
from typing import Any

REPEATED_NOTE = "Repeated-data regime: at 16,384 updates this is 64 passes over 131,072 target bytes with a 198k-parameter addition and no weight decay; the endpoint largely measures how each arm behaves once it can fit its training set, and a competitiveness label here can come from the dense adapter overfitting faster."


def fmt(v: Any) -> str:
    if v is None:
        return "NON-FINITE"
    if isinstance(v, float):
        return f"{v:+.6f}"
    return str(v)


def label_text(entry: Mapping[str, Any]) -> str:
    tags = " ".join(entry.get("tags") or [])
    edge = " [RATE-AT-EDGE]" if entry.get("rate_at_edge") else ""
    return f"{entry['label']}{(' ' + tags) if tags else ''}{edge}"


def render(result: Mapping[str, Any], mode: str) -> str:
    out: list[str] = ["# P10-I-S3 report (ADR-0026)", "", f"Mode: {mode}. Measured values below are measured; none is a success claim. `Astra review: NOT_PERFORMED`.", ""]
    if not result["base_ok"]:
        out += [f"BASE failed or is missing on: {', '.join(result['base_bad'])}. Every line is NOT EVALUABLE.", ""]
    out += ["## Registered labels (the registered label of a line is its FRESH regime label)", ""]
    out += [f"- Line 1, DEPENDENCE: **{result['line1']['label']}**", f"- Line 2, COMPETITIVENESS[TREE]: **{result['line2_tree']['label']}**", f"- Line 2, COMPETITIVENESS[FLAT] (a separate sub-label, never merged): **{result['line2_flat']['label']}**"]
    pos = result["registered_positive"]
    out += [f"- Registered positive: line 1 {pos['line1']}, line 2 {pos['line2']}", ""]
    r = result["route_a"]
    out += ["## Labels that qualify for ADR-0027 Route A (section 12)", "", f"- A1 (dependence, FRESH, M-TREE): label qualifies {r['A1_label_qualifies']}; qualifies after the open-choice-13 ruling {r['A1']}", f"- A2 (competitiveness[TREE], FRESH): label qualifies {r['A2_label_qualifies']}; qualifies after the ruling {r['A2']}", f"- D-ADAPT's registered FRESH convergence tag counts as NOT CONVERGED: {r['dense_fresh_not_converged']}", ""]
    out += ["## Regime labels (printed beside the registered label; never the line's label, never positive)", ""]
    for g in ("FRESH", "REP-U", "REP"):
        reg = result["regimes"][g]
        n_col = reg["line1"].get("collapsed_cells", 0)
        out += [f"### {g}", "", f"- line 1: {label_text(reg['line1'])} (COLLAPSED cells: {n_col}" + ("; D2 is false for the regime because of them: a collapsed cell is never averaged away)" if n_col else ")"), f"- line 2 [TREE]: {label_text(reg['line2_tree'])}"]
        if "line2_flat" in reg:
            out.append(f"- line 2 [FLAT]: {label_text(reg['line2_flat'])}")
        for arm, c in reg["convergence"].items():
            out.append(f"- {arm}: {c['tag']} (delta {fmt(c['delta'])})" + (f"; reason: {c['reason']}" if c.get("reason") else ""))
        for arm, p in reg["past_best"].items():
            if p.get("flag"):
                out.append(f"- {arm}: PAST BEST CHECKPOINT")
        d = reg["line1"]["detail"]
        if d.get("conditions"):
            for k, v in d["conditions"].items():
                out.append(f"- {k}: mean {fmt(v['mean'])}, cells {v['cells']}, parents {v['parents']}, ok {v['ok']}")
        if d.get("collapsed"):
            out.append(f"- COLLAPSED cells (fewer than two used slots): {d['collapsed']}")
        if g != "FRESH":
            out += ["", REPEATED_NOTE]
        for arm, probs in reg["integrity_problems"].items():
            if probs:
                out.append(f"- INTEGRITY problems of {arm}: {probs[:3]}")
        out.append("")
    out += ["## Routing and duration (descriptive; not a third outcome line)", ""]
    for g, rt in result["routing"].items():
        out.append(f"### {g}")
        for k, row in rt["rows"].items():
            out.append(f"- {k} updates: G_train {row['G_train_label']}; G_read {row['G_read_label']}; G_train at the primary rates {fmt(row['G_train_primary_rate_mean'])}; G_prior mean {fmt(row['G_prior_stats']['mean'])} (no label)")
        for nm in ("G_train", "G_read"):
            t = rt[f"{nm}_trend"]
            out.append(f"- {nm} trend: {t['trend']}; delta G mean {fmt(t['delta_G']['mean'])}, positive {t['delta_G']['n_positive']}, negative {t['delta_G']['n_negative']}")
        out.append("")
    out += ["## Six-parent readout (the parents not used in calibration; plain figures, no label)", ""]
    for g, s in result["six_parent"].items():
        out.append(f"- {g}: {s['cells']} cells, {s['parents']} parents; mean C {fmt(s['C']['mean'])}, mean C_dense {fmt(s['C_dense']['mean'])}, mean Q {fmt(s['Q']['mean'])}; C>0 in {s['n_C_positive']}/{s['cells']}; P_used >= half C in {s['n_P_half']}; X_mean >= half C in {s['n_X_half']}; Q within tolerance in {s['n_Q_within']}; Q ahead in {s['n_Q_ahead']}")
    out += ["", "## Contrasts of section 3.3 (descriptive)", ""]
    for g, rows in result["contrasts"].items():
        for k, v in rows.items():
            out.append(f"- {g} at {k}: " + ", ".join(f"{n} {fmt(x)}" for n, x in v.items()))
    if result.get("anchor"):
        out += ["", "## P4-rate anchor (descriptive)", ""] + [f"- {a}: rate for U* {v['rate_for_ustar']}, mean C at 0.003 {fmt(v['C_at_p4_rate']['mean'])}, at the frozen rate {fmt(v['C_at_frozen_rate']['mean'])}" for a, v in result["anchor"].items()]
    out += ["", "## Limits", "", *[f"- {x}" for x in result["limits"]], "- Nine correlated parents, one corpus, byte-level text, one addition size. No p-value is computed. Seconds per update are descriptive records of this implementation and not an efficiency result.", ""]
    return "\n".join(out)


def render_whitelist(result: Mapping[str, Any], mode: str) -> str:
    """The public report of a calibration or DRY run (B4, ruling 15): stage and gate pass/fail and nothing else. No loss, no effect, no mean, no delta, no label of a registered line."""
    base = "BASE check passed" if result["base_ok"] else "BASE check FAILED"
    return "\n".join(["# P10-I-S3 rehearsal report (whitelist only)", "", f"Mode: {mode}. This report carries pass or fail only; every value of a calibration or DRY run is in the sealed directory. `Astra review: NOT_PERFORMED`.", "", f"- the analysis ran to the end on the DRY items: yes ({base})", f"- regimes analysed: {', '.join(sorted(result['regimes']))}", ""])
