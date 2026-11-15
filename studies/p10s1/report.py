# ruff: noqa: E501
"""P10S1 report (ADR-0021 sections 7.6, 8.7, 8.9, 12): ``results.json`` and ``RESULTS.md`` from ``analysis.json``.

Every line of RESULTS.md goes through ``classes.emit``: a positive label (CAPACITY STEP, CAPACITY_SUPPORTED, CAPACITY-POSITIVE, EFFICIENCY_SUPPORTED, EFFICIENCY-POSITIVE,
BEATS DENSE, KNOWLEDGE SCALES WITH MEMORY, TREE_AHEAD, the storage-half reading, ...) without ``STORE ONLY; ORACLE-ADDRESSED`` raises and nothing is written. Nothing here
decides anything: it prints what ``analysis`` computed, with the readings that need the lead's review, what S1 cannot establish, and the sentence "addressing was supplied by an
oracle". A negative, an INCONCLUSIVE and a NOT TESTED are printed as prominently as a positive.
"""

import json
from pathlib import Path
from typing import Any

from arborlm.io import write_json

from . import classes as C
from . import core

NOT_ESTABLISHED_SENTENCE = "S1 establishes nothing about an autonomous learned memory, about the language model forming queries, about capability beyond recall of the trained facts, or about natural-language knowledge."
CANNOT = (
    "That a learned memory works without an oracle (no autonomous learned-memory success may be claimed from S1).",
    "That the language model can form the queries, or that any interface reaches the capacity measured here.",
    "Useful capability beyond recall of the trained facts; any improvement of a language model's behaviour.",
    "Efficiency, speed, latency or I/O: counted work is logical, simulated traffic is not a storage measurement, throughput is an in-RAM CPU figure for a 27,392-parameter backbone.",
    "Capacity where no cell is loaded; anything beyond the registered slots, facts and run lengths.",
    "Anything about natural-language knowledge, composition, reasoning, skewed fact frequency, another backbone, or a trainable backbone.",
    "That a dense lead (DENSE AHEAD) or a conventional retrieval that suffices means memory is not needed in general, or that a win over the dense control holds off this task.",
    "That a hierarchy helps locality, or that sublinear counted work is a finding about the tree.",
    "That 'more slots' differs from 'more store parameters': this read path cannot separate them.",
    "Generalization across facts. That a dense architecture other than D-OQ would not do as well.",
    "TRANSFER-POSITIVE, SYSTEM-POSITIVE, a failure of the ArborLM concept, Astra validation, or a human approval that is not recorded. No S1 outcome is ever summarised as 'ArborLM's capacity scales'.",
)


def show(label: str) -> str:
    """A label as printed: tagged when positive (the replicate verdict CAPACITY is tagged too), plain otherwise."""
    if label == C.CAPACITY or C.is_positive(label):
        return C.tagged(label)
    return label


def _row(*cells: object) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _fmt(x: Any, digits: int = 3) -> str:
    if isinstance(x, float):
        return "inf" if x == float("inf") else ("-inf" if x == float("-inf") else ("nan" if x != x else f"{x:.{digits}f}"))
    return str(x)


def _capacity_table(cap: dict[str, Any]) -> list[str]:
    steps = sorted({s for a in cap["steps"].values() for s in a})
    lines = ["| Arm | Arm class | Dense label | Active work | " + " | ".join(f"Step {s} (class; replicate verdicts)" for s in steps) + " |", "|---|---|---|---|" + "---|" * len(steps)]
    for arm, info in cap["arms"].items():
        cells = [f"{show(cap['steps'][arm][s]['class'])}; " + ", ".join(show(v) for v in cap["steps"][arm][s]["verdicts"]) for s in steps]
        extra = " UNDERTRAINED-AT-U_P" if arm == "H8" and info.get("undertrained_h8") else ""
        dense = show(info["dense"])
        if "NOT ESTABLISHED AT MATCHED COMPUTE" in info["dense"]:  # the matched-updates comparison is printed beside the label (ADR-0021 section 22 M5)
            dense += " — " + (" ".join(info["dense_detail"].get("mu_text") or []) or "no matched-updates comparison available").replace("|", "/")
        if info.get("dense_matches_sentence"):  # the DENSE MATCHES sentence, verbatim, wherever that reading is established
            dense += " — " + str(info["dense_matches_sentence"]).replace("|", "/")
        lines.append(_row(arm, show(info["class"]) + extra, dense, info.get("work_label") or "n/a", *cells))
    return lines


def _efficiency_table(eff: dict[str, Any]) -> list[str]:
    steps = sorted({s for a in eff["steps"].values() for s in a})
    lines = ["| Arm | Arm class | Dense label | " + " | ".join(f"Step {s} (class; replicate verdicts)" for s in steps) + " |", "|---|---|---|" + "---|" * len(steps)]
    for arm, cls in eff["arm_classes"].items():
        cells = [f"{show(eff['steps'][arm][s]['class'])}; " + ", ".join(show(v) for v in eff["steps"][arm][s]["verdicts"]) for s in steps]
        lines.append(_row(arm, show(cls), eff["dense"].get(arm, "n/a"), *cells))
    return lines


def _movement_lines(cap: dict[str, Any], eff: dict[str, Any]) -> list[str]:
    lines = ["| Line | Arm | Step | Row-movement ratio, total (larger / smaller, per replicate) | Without-gradient share ratio | OPTIMIZER-ASSISTED (replicates) |", "|---|---|---|---|---|---|"]
    for line, steps in (("capacity", {a: v for a, v in cap["steps"].items()}), ("efficiency", eff["steps"])):
        for arm, st in steps.items():
            for name, info in st.items():
                tot, share, assisted = [], [], 0
                for rep in info["replicates"]:
                    mv = rep.get("movement") or rep.get("movement_at_U_P") or {}
                    ratios = mv.get("ratios") or {}
                    tot.append(_fmt(ratios.get("total"), 2) if ratios.get("total") is not None else "n/a")
                    share.append(_fmt(ratios.get("share_without"), 2) if ratios.get("share_without") is not None else "n/a")
                    assisted += int(bool(mv.get("optimizer_assisted") or rep.get("optimizer_assisted")))
                lines.append(_row(line, arm, name, ", ".join(tot), ", ".join(share), f"{assisted}/{len(info['replicates'])}"))
    return lines


def render_markdown(analysis: dict[str, Any], banner: str | None = None) -> str:
    """RESULTS.md. ``analysis`` is the ``result`` of an ``analysis`` record."""
    a = analysis["assessment"]
    out = analysis["outcome"]
    lines: list[str] = ["# P10S1 results (ADR-0021, revision 4)", ""]
    if banner:
        lines += [f"**{banner}**", ""]
    lines += [
        f"**Every positive label below carries `{core.STORE_ONLY_TAG}`. Addressing was supplied by an oracle.** {NOT_ESTABLISHED_SENTENCE}",
        "",
        "Self-checked analysis. Not independent review, not Astra validation, not human approval. **Astra review: NOT_PERFORMED.**",
        "",
        f"- Status: **{a['status']}**",
        f"- Addressing: {analysis['oracle_sentence']} (S1 measures the store, not the interface).",
        f"- S0 status (ADR-0020, K7(c)): {analysis['s0_status']}",
        f"- Learned-address lane (lane L): {analysis['lane_l']}",
        f"- Cells read: {a['cells_read']}; missing: {len(a['missing_cells'])}; failed: {len(a['failed_cells'])}; failed tasks: {len(a['failed_tasks'])}",
        f"- Plan: {json.dumps(a['plan'], sort_keys=True)}; cuts: {', '.join(a['cuts']) or 'none'}",
        "",
    ]
    if a["engineering"]["reasons"]:
        lines += ["## Engineering", "", *[f"- {r}" for r in a["engineering"]["reasons"]], ""]
    if a["missing_cells"] or a["failed_cells"]:
        lines += ["## Cells without a record (the denominator is never reduced)", ""]
        lines += [f"- missing: {c} ({a['reasons'].get(c, '')})" for c in a["missing_cells"][:50]] + [f"- failed: {c} ({a['reasons'].get(c, '')})" for c in a["failed_cells"][:50]] + [""]
    lines += ["## Outcomes", "", f"- **Capacity line:** {out['capacity']['printed']}", f"- **Efficiency line:** {out['efficiency']['printed']}"]
    if out["capacity"].get("reading"):
        lines += [f"- **Reading for milestone question 1 (capacity line only):** {out['capacity']['reading']}"]
    lines += ["- The two lines are separate; neither implies the other. The reading for milestone question 1 uses the capacity line only.", ""]
    cap, eff = analysis.get("capacity"), analysis.get("efficiency")
    if cap is not None and eff is not None:
        lines += ["## Capacity line: arms and steps", "", *_capacity_table(cap), ""]
        lines += [f"- Hierarchy (T-OQ against F-OQ-IVF at equal candidate count): {show(cap['hierarchy']['label'])}", f"- KEY-LEARNING-LIMITED: {cap['key_learning_limited']}"]
        lines += [f"- Conventional retrieval, {arm}: " + ("CONVENTIONAL RETRIEVAL SUFFICES" if v["suffices"] else "not sufficient") for arm, v in cap["conventional"]["arms"].items()]
        lines += [f"- {cap['conventional']['dict_dominates_on_this_task']}", ""]
        lines += ["## Efficiency line: arms and steps", "", *_efficiency_table(eff), ""]
        lines += ["## Row movement (section 7.3; printed with every budget and efficiency verdict; no class depends on it)", "", *_movement_lines(cap, eff), ""]
        lines += ["## Study B (knowledge with memory; descriptive, beside the outcome)", ""]
        for arm, sb in cap["study_b"].items():
            lines.append(f"- {arm}: {show(sb['label'])} (MEMORY-ATTRIBUTED steps {sb['memory_attributed']}; sublinear {sb['sublinear']}; ratio not assessed {sb['ratio_not_assessed']}). {sb['me_note']}")
        lines += ["", "## Robustness (descriptive)", ""]
        for arm, steps in cap["robustness"].items():
            lines.append(f"- {arm}: " + "; ".join(f"{s}: {v['label']}" for s, v in steps.items()))
        lines += ["", "## Seed block (descriptive, enters no rule)", ""]
        for key, v in cap["seed_block"]["cells"].items():
            lines.append(f"- {key}: spread within draw {_fmt(v['spread_within_draw'])}, across draws {_fmt(v['spread_across_draws'])}; dominates: {v['dominates']}")
        if cap["mc_mismatch"]:
            lines += ["", "## MC-MISMATCH (a flag; changes no class)", ""] + [f"- {m['pair']} replicate {m['replicate']}: CPU ratio {_fmt(m['cpu_ratio'], 2)}" for m in cap["mc_mismatch"]]
        lines += ["", "## Cost table (replicate 1; logical counts and measured CPU seconds; not measured efficiency)", ""]
        lines += ["| Arm | Cell | I_use (A / B) bits | Trainable | Stored | Bits per stored byte (A) | K | V | W | Exposures per fact (U_P / U_run) | CPU s to U_P | Analytic multiply-adds to U_P |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in analysis["cost_table"]:
            lines.append(_row(r["arm"], r["cell"], f"{_fmt(r['I_use_bits_at_U_P']['A'], 1)} / {_fmt(r['I_use_bits_at_U_P']['B'], 1)}", r["trainable_parameters"], r["stored_parameters"], _fmt(r["retained_bits_per_stored_byte"]["A"], 4), r["K"], r["V"], _fmt(r["W"], 1), f"{_fmt(r['exposures_per_fact_U_P'], 1)} / {_fmt(r['exposures_per_fact_U_run'], 1)}", _fmt(r["cpu_seconds_to_U_P"], 1), f"{r['analytic_madds_to_U_P']:.3g}"))
        lines.append("")
    for name, title in (("timing", "Isolated timing"), ("throughput", "Throughput (measured, RAM only)"), ("simulation", "Estimated storage traffic (arithmetic and simulation, no device)")):
        if analysis.get(name) is not None:
            lines += [f"## {title}", "", "```json", json.dumps(analysis[name], indent=1, sort_keys=True)[:6000], "```", ""]
    lines += ["## Readings and open items that need the lead's review", "", *[f"- {C.tag_positives(v)}" for v in analysis["readings"].values()], ""]
    lines += ["## Decision map (recommendations only; nothing is authorized)", "", *[f"- {C.tag_positives(d)}" for d in analysis["decision_map"]], ""]
    lines += ["## What S1 cannot establish (section 12)", "", *[f"- {c}" for c in CANNOT], ""]
    return C.emit("\n".join(lines))


def write_report(run_dir: Path, out_dir: Path, *, banner: str | None = None) -> list[Path]:
    """Write ``results.json`` and ``RESULTS.md`` into ``out_dir`` from ``<run_dir>/analysis.json``; refuses to overwrite and refuses text with an untagged positive label."""
    record = core.read_record(run_dir / "analysis.json", "analysis")
    result = record["result"]
    text = render_markdown(result, banner)  # raises before anything is written if a positive label is untagged
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "results.json", out_dir / "RESULTS.md"]
    for p in paths:
        if p.exists():
            raise FileExistsError(p)
    write_json(paths[0], {"study": core.STUDY, "kind": "results", "store_only_tag": core.STORE_ONLY_TAG, "tag_note": f"every class, label and outcome name in this file is {core.STORE_ONLY_TAG}; the structured fields hold the bare names, RESULTS.md prints each with its tag", "analysis": result, "banner": banner, "identity": record.get("identity"), "environment": record.get("environment")})
    paths[1].write_text(text, encoding="utf-8")
    return paths
