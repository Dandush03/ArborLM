# ruff: noqa: E501
"""P9II report (ADR-0019 sections 8 and 13): CSV, JSON and Markdown of the outcome, the stage statuses, the classes with their annotations, the hypothesis
readings, the draw-sensitivity estimands, the exposures per fact and the parameter counts per cell, written from the records of a run directory. Every
number is labelled measured (a record of this run) or analytical (derived from the registry); none is described as a speedup or as success. Labels carry the
supervision class of the arm and the paired reading against A0, and are never shortened.
"""

import csv
from pathlib import Path
from typing import Any

from arborlm.io import write_json

from . import classes as C
from . import core

NOT_CLAIMED = (
    "Nothing about memory capacity, useful-capacity scaling, locality or incremental learning is tested here. More slots in use is not more capacity.",
    "A reliable arm is not shown reliable on natural language, on another backbone, with another interface than W7, or at 65,536 slots. Stage 3 is a probe at 32 exposures per fact and can only be positive or uninformative.",
    "Address supervision is a training label this task provides; a supervised arm's success says nothing about learning addresses without labels.",
    "W7 is told the record length and the memory is told the answer position; the LM-capability criterion is measured under that condition and says nothing about a deployed system.",
    "Matched exposure at 16,384 is not matched optimization.",
    "A0 is untuned by design; no tuned arm is shown to beat a tuned baseline.",
    "No success probability above the per-draw bounds stated in section 5 is claimed.",
    "No efficiency claim: work counts and CPU seconds are descriptive.",
    "A failure here is not a failure of the ArborLM concept.",
    "Astra review: NOT_PERFORMED. A Claude review is not an Astra review; no human approval is implied by this report.",
)  # fmt: skip


def load_cell_records(run_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    """``(train records, {label: {readout: eval record}})`` for every cell directory of the run."""
    trains: dict[str, dict[str, Any]] = {}
    evals: dict[str, dict[str, dict[str, Any]]] = {}
    for folder in sorted((run_dir / "cells").glob("*")):
        if (folder / "train.json").is_file():
            trains[folder.name] = core.read_record(folder / "train.json", "train")
        found = sorted(folder.glob("eval/*/eval.json"))
        if found:
            evals[folder.name] = {p.parent.name: core.read_record(p, "eval") for p in found}
    return trains, evals


def class_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage_key, size in (("stage1", 4096), ("stage2", 16384)):
        for arm, d in (result.get(stage_key) or {}).get("arms", {}).items():
            paired = d.get("paired_against_a0") or {}
            rows.append({"stage": stage_key, "slots": size, "arm": arm, "supervision": core.SUPERVISION_LABEL.get(arm, ""), "class": d["class"], "evaluated": d["counts"]["evaluated"], "successes": d["counts"]["successes"], "failures": d["counts"]["failures"], "lm_flagged_cells": d["counts"]["lm_flagged_cells"], "paired_label": paired.get("label", ""), "paired_d": paired.get("d", ""), "paired_p_value": paired.get("p_value", ""), "median_escape_update_escaped_cells_only": d["median_escape_update_escaped_cells_only"], "median_escape_update_censored_at_readout": d["draw_sensitivity"]["median_escape_update_censored_at_readout"], "dense_comparison": (d.get("dense_comparison") or {}).get("label", "")})
    return rows


def cell_rows(trains: dict[str, dict[str, Any]], evals: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for label, t in sorted(trains.items()):
        row: dict[str, Any] = {"label": label, "arm": t["arm"], "stage": t["stage"], "slots": t["slots"], "draw": t["draw"], "seed_index": t["seed_index"], "facts": t["facts"], "matched_updates": t["matched_updates"], "exposure_per_fact_analytical": t["exposure_per_fact_analytical"], "exposure_per_fact_mean_measured": t["exposure_per_fact_mean"], "trainable_parameters": t["trainable_parameters"], "trainable_backbone_parameters": t["trainable_backbone_parameters"], "stored_parameters": t["stored_parameters"], "optimizer_state_bytes": t["optimizer_state_bytes"], "wall_seconds": t["wall_seconds"], "peak_rss_bytes": t["peak_rss_bytes"], "status": t["status"]}
        for update, e in sorted(evals.get(label, {}).items()):
            tag = update.lstrip("u").lstrip("0")
            for panel, p in e["panels"].items():
                row[f"accuracy_{panel}_u{tag}"] = p["accuracy"]
                row[f"leakage_{panel}_u{tag}"] = p.get("leakage")
            for name, p in e["secondary"].items():
                row[f"accuracy_{name}_u{tag}"] = p["accuracy"]
            probe = e.get("probe") or {}
            row[f"probe_distinct_top1_u{tag}"] = probe.get("distinct_top1")
            row[f"probe_largest_share_u{tag}"] = probe.get("largest_top1_share")
            row[f"lm_relative_rise_u{tag}"] = (e.get("language_modelling") or {}).get("relative_rise")
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        keys += [k for k in row if k not in keys]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def annotation_lines(result: dict[str, Any]) -> list[str]:
    """Every label sections 8.4 and 8.5 say are printed: NEGATIVE CONTROL FAILED, SUPERVISION-DEPENDENT, ADDRESS RECALL and ADDRESS STABLE, the four category counts, the
    MID-SCHEDULE / ALSO AT MATCHED UPDATES readout, d(A2 against A1), the LM-capability numbers (A6's r beside each arm's), the dense comparison and the SCALE PROBE."""
    lines: list[str] = []
    for key, size in (("stage1", "4,096"), ("stage2", "16,384")):
        stage = result.get(key)
        if not stage or "arms" not in stage:
            continue
        lines += [f"## Annotations at {size} slots", ""]
        lines.append(f"- {C.NEGATIVE_CONTROL_FAILED}: {'printed' if stage['negative_control_failed'] else 'not printed'}" + (" (A1 and A2 are printed but not interpreted as fact-specific supervision)" if stage["negative_control_failed"] else ""))
        a6 = stage.get("a6", {})
        lines.append("- A6 (oracle reference) relative next-byte loss rise r by draw (measured): " + ", ".join(f"d{d}: {v['lm_relative_rise']}" for d, v in a6.items()))
        for arm, d in stage["arms"].items():
            lm = d["lm_capability"]
            parts = [f"class {d['class']}", "categories " + "; ".join(f"{k}: {v}" for k, v in d["categories"].items()), f"r by cell {lm['relative_rises']}", f"absolute rise (percent) {lm['absolute_rise_percent']}"]
            if lm["reduced"]:
                parts.append(C.LM_REDUCED)
            addr = d["address"]
            if "recall" in addr:
                parts.append(f"{C.ADDRESS_RECALL} median {addr['recall']['median']} -> {addr['recall']['label'] or 'not printed'}")
            parts.append(f"{C.ADDRESS_STABLE} median {addr['stable']['median']} -> {addr['stable']['label'] or 'not printed'}")
            if "supervision_dependent" in d:
                sd = d["supervision_dependent"]
                parts.append(f"{C.SUPERVISION_DEPENDENT}: {sd['label'] or 'not printed'} ({sd['cells']} of {sd['of']} evaluated cells; {C.ADDRESSES_REMAPPED}: {d['addresses_remapped_cells']} cells, descriptive)")
                parts.append("d(A2 against A1) " + (str(d["paired_against_a1"]["d"]) if "paired_against_a1" in d else "not available") + " (descriptive)")
            if "readout_u" in d:
                parts.append(f"readout at U: {d['readout_u']['label'] or 'not RELIABLE at U'}")
            if "dense_comparison" in d:
                parts.append(f"dense comparison {d['dense_comparison']['label']}")
            lines.append(f"- {arm} {core.SUPERVISION_LABEL.get(arm, '')}: " + "; ".join(parts))
        lines.append("")
    stage3 = result.get("stage3")
    if stage3 and "label" in stage3:
        lines += ["## Stage 3 (probe)", "", f"- {stage3['label']}: {stage3['successes']} of {stage3['cells']} cells succeed ({stage3['selected']}); {stage3['note']}", ""]
    plan = result.get("draw_plan")
    if plan and plan.get("replacements"):
        lines += ["## Draw plan", "", *[f"- draw {k}: {plan['labels'][k] if plan.get('labels') else v} ({v})" for k, v in plan["replacements"].items()], ""]
    return lines


def render_markdown(analysis: dict[str, Any], classes: list[dict[str, Any]], banner: str | None) -> str:
    result = analysis["result"]
    out = result["outcome"]
    lines = ["# ADR-0019 (P9II) results", ""]
    if banner:
        lines += [f"**{banner}**", ""]
    assessment = result["assessment"]
    if not assessment["interpretable"]:
        lines += ["**NOT INTERPRETED** (any classes below are descriptive only):", *[f"- {r}" for r in assessment["gate_reasons"]]]
        if assessment["missing"]:
            lines.append("- missing or failed: " + ", ".join(map(str, assessment["missing"])))
        lines.append("")
    lines += [
        f"Study status: **{assessment['status']}** (measured: derived from the run's manifests, gates and records).",
        f"Outcome: **{out['label']}**",
        f"Stage 2 status: {(result.get('stage2') or {}).get('status', 'not run')}; Stage 3 status: {(result.get('stage3') or {}).get('status', 'not run')}.",
        f"Updates per unit U: {analysis['unit_updates']}.",
        "",
    ]
    carried = result.get("carried_forward")
    if carried:
        lines += [f"Interface carried forward: {carried['arm']} {carried['supervision'] or ''}" + (f"; {carried['recommendation']}" if carried["recommendation"] else ""), ""]
    lines += ["## Classes (measured counts, rules of section 8.4)", "", "| stage | slots | arm | supervision | class | evaluated | successes | paired against A0 | d | median escape update (escaped cells only) | median escape update (censored at the readout) | dense |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in classes:
        lines.append(f"| {r['stage']} | {r['slots']} | {r['arm']} | {r['supervision']} | {r['class']} | {r['evaluated']} | {r['successes']} | {r['paired_label']} | {r['paired_d']} | {r['median_escape_update_escaped_cells_only']} | {r['median_escape_update_censored_at_readout']} | {r['dense_comparison']} |")
    lines += ["", "Every contrast against A0 compares an arm at its better of two calibrated settings with an untuned baseline.", ""]
    lines += annotation_lines(result)
    if result.get("hypotheses"):
        lines += ["## Hypothesis readings (section 8.6)", ""] + [f"- {k}: {v['reading']}" for k, v in result["hypotheses"].items()] + [""]
    lines += ["## What must not be claimed (section 13)", "", *[f"- {s}" for s in NOT_CLAIMED], ""]
    return "\n".join(lines) + "\n"


def write_report(run_dir: Path, out_dir: Path, *, banner: str | None = None) -> list[Path]:
    """Write ``classes.csv``, ``cells.csv``, ``RESULTS.md`` and ``results.json`` into ``out_dir`` (never over an existing file)."""
    analysis = core.read_record(run_dir / "analysis.json", "analysis")
    trains, evals = load_cell_records(run_dir)
    classes = class_rows(analysis["result"])
    cells = cell_rows(trains, evals)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "classes.csv", out_dir / "cells.csv", out_dir / "RESULTS.md", out_dir / "results.json"]
    for p in paths:
        if p.exists():
            raise FileExistsError(p)
    classes, cells = core.jsonable(classes), core.jsonable(cells)
    _write_csv(paths[0], classes)
    _write_csv(paths[1], cells)
    paths[2].write_text(render_markdown(analysis, classes, banner), encoding="utf-8")
    write_json(paths[3], core.jsonable({**core.envelope("analysis"), "banner": banner, "result": analysis["result"], "classes": classes, "cells": cells, "not_claimed": list(NOT_CLAIMED), "environment": core.environment()}))
    return paths
