# ruff: noqa: E501
"""P9I report (ADR-0017 Part I, sections I.8.3 and I.13): CSV, JSON and Markdown of the classes, the
annotations, the selection, the exposures per fact per size, and the parameters and optimizer-state bytes
per arm, written from the records of a run directory. Every number is labelled measured (a record of
this run) or analytical (derived from the registry); none is described as a speedup or as success.
"""

import csv
import json
from pathlib import Path
from typing import Any

from arborlm.io import read_json, write_json

from . import classes, core

NOT_CLAIMED = (
    "Nothing about capacity scaling, utilization, locality or incremental learning is tested here. A difference in class between sizes is not evidence about capacity: exposures per fact differ sixteenfold.",
    "A WORKS class for W7, E7, A4 or A4E does not show the language model communicating what it needs.",
    "INTERFACE_WORKS for BB does not show that a language model reliably communicates what it needs; the block-0 attention was retrained on this task's answer loss alone, with its next-byte loss unprotected.",
    "An interface that works here is not shown to work on natural language (fixed-length records, random identifiers).",
    "W7 is not a general interface: it is told the record length.",
    "A failure of all interfaces is not a failure of the ArborLM concept; it is a statement about this backbone within U updates.",
    "DENSE SUFFICES does not say memory is not needed in general.",
    "The oracle rungs R1 and R2 are references, not systems.",
    "Astra review: NOT_PERFORMED. Claude review is not Astra review; no human approval is implied by this report.",
)


def load_cell_records(run_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """``(train records, eval records)`` by label for every cell directory of the run."""
    trains: dict[str, dict[str, Any]] = {}
    evals: dict[str, dict[str, Any]] = {}
    for folder in sorted((run_dir / "cells").glob("*")):
        if (folder / "train.json").is_file():
            trains[folder.name] = core.read_record(folder / "train.json", "train")
        found = sorted(folder.glob("eval/*/eval.json"))
        if found:
            evals[folder.name] = core.read_record(found[-1], "eval")
    return trains, evals


def _rows_classes(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm, per in analysis["analysis"]["classes"].items():
        for size, cls in per.items():
            detail = analysis["analysis"]["details"][arm][size]
            note = analysis["analysis"]["annotations"].get(arm, {}).get(size, {})
            dense = (note.get("dense_comparison") or {}).get("label", "")
            lm = (note.get("language_modelling") or {}).get("label", "")
            rows.append({"arm": arm, "slots": int(size), "class": cls, "raw": json.dumps(detail["raw"], sort_keys=True), "b102_present": detail["b102_present"], "b102_demoted": detail["b102_demoted"], "dense_comparison": dense, "language_modelling": lm})
    return rows


def _rows_cells(trains: dict[str, dict[str, Any]], evals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    r1: dict[tuple[int, tuple[int, int], int, str], float] = {}
    for ev in evals.values():
        if ev["arm"] == "R1":
            for panel, pr in ev["panels"].items():
                r1[(int(ev["slots"]), (int(ev["parent"][0]), int(ev["parent"][1])), int(ev["seed"]), panel)] = float(pr["accuracy"])
    rows = []
    for label, t in sorted(trains.items()):
        facts = int(t["facts"])
        updates = int(t["matched_updates"])
        e = evals.get(label)
        row: dict[str, Any] = {
            "label": label,
            "arm": t["arm"],
            "slots": t["slots"],
            "parent": "b{}-o{}".format(*t["parent"]),
            "seed": t["seed"],
            "facts": facts,
            "matched_updates": updates,
            "exposure_per_fact_analytical": updates * core.ANSWER_SITES_PER_BATCH / facts if facts else None,
            "exposure_per_fact_mean_measured": t["exposure_per_fact_mean"],
            "exposure_per_fact_min_measured": t["exposure_per_fact_min"],
            "exposure_per_fact_max_measured": t["exposure_per_fact_max"],
            "trainable_parameters": t["trainable_parameters"],
            "trainable_backbone_parameters": t["trainable_backbone_parameters"],
            "interface_extra_parameters": t["interface_extra_parameters"],
            "dense_hidden": t["dense_hidden"],
            "stored_parameters": t["stored_parameters"],
            "optimizer_state_bytes": t["optimizer_state_bytes"],
            "wall_seconds": t["wall_seconds"],
            "status": t["status"],
        }
        if e is not None:
            for panel, p in e["panels"].items():
                row[f"accuracy_{panel}"] = p["accuracy"]
                row[f"unseen_accuracy_{panel}"] = p.get("unseen_accuracy")
                row[f"leakage_{panel}"] = p.get("leakage")
                reference = r1.get((int(e["slots"]), (int(e["parent"][0]), int(e["parent"][1])), int(e["seed"]), panel))
                row[f"eta_{panel}"] = None if not reference else float(p["accuracy"]) / reference
                row[f"permuted_accuracy_{panel}"] = p.get("permuted_accuracy")
                row[f"disabled_accuracy_{panel}"] = p.get("disabled_accuracy")
                support = p.get("support") or {}
                row[f"support_share_{panel}"] = support.get("share_with_support")
                row[f"support_mean_length_{panel}"] = support.get("mean_length")
                row[f"useful_slots_{panel}"] = support.get("useful_slots")
            lm = e.get("language_modelling") or {}
            row["lm_before_nats"] = lm.get("before_nats")
            row["lm_after_nats"] = lm.get("after_nats")
            row["lm_relative_rise"] = lm.get("relative_rise")
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


def render_markdown(analysis: dict[str, Any], class_rows: list[dict[str, Any]], cell_rows: list[dict[str, Any]], banner: str | None) -> str:
    sel = analysis["analysis"]["selection"]
    lines = ["# ADR-0017 Part I (P9I) results", ""]
    if banner:
        lines += [f"**{banner}**", ""]
    if analysis.get("interpretable") is False:
        lines += ["**NOT INTERPRETED** (classes below, if any, are descriptive only):", *[f"- {r}" for r in analysis.get("gate_reasons", [])]]
        if analysis["analysis"]["selection"].get("missing"):
            lines.append("- missing or failed: " + ", ".join(analysis["analysis"]["selection"]["missing"]))
        lines.append("")
    lines += [
        f"Study status: **{analysis['status']}** (measured: derived from the run's manifests, gates and records).",
        f"Matched updates U: {analysis['updates']} (the same at every size).",
        f"Gate G1 passed: {analysis['g1_passed']}; gate G2 passed: {analysis['g2_passed']}; gate G4 passed: {analysis.get('g4_passed')}; LEAKAGE flags: {analysis['leakage'] or 'none'}.",
        f"Missing cells: {analysis['missing_cells'] or 'none'}; non-completed tasks: {analysis['failed_tasks'] or 'none'}.",
        "",
        "## Selection (section I.8.3)",
        "",
        f"Outcome: **{sel['outcome']}**" + (f" (decided at step {sel['step']})." if sel["step"] is not None else "."),
    ]
    if sel["inconclusive_sizes"]:
        lines.append("Step 0, sizes that make the outcome INCONCLUSIVE: " + ", ".join(f"{k}: {v}" for k, v in sorted(sel["inconclusive_sizes"].items())))
    lines += ["", "Scope statements carried with the outcome:", *[f"- {s}" for s in sel["scope"]], "", "## Classes at each size (measured accuracies, rules of section I.8.1)", "", "| arm | slots | class | dense comparison | language modelling | B102 present |", "|---|---|---|---|---|---|"]
    for r in sorted(class_rows, key=lambda r: (r["arm"], r["slots"])):
        lines.append(f"| {r['arm']} | {r['slots']} | {r['class']} | {r['dense_comparison']} | {r['language_modelling']} | {r['b102_present']} |")
    lines += ["", "## Backbone contrast at 16,384 (annotation, does not change a class)", ""]
    for pair, c in analysis["analysis"]["backbone_contrast"].items():
        lines.append(f"- {pair}: {c['label'] if c else 'not printed'}")
    lines += ["", "## Exposures per fact and parameters (analytical exposure, measured counts)", "", "| cell | facts | U | exposures per fact (analytical) | trainable | trainable backbone | optimizer-state bytes |", "|---|---|---|---|---|---|---|"]
    for r in cell_rows:
        e = r["exposure_per_fact_analytical"]
        lines.append(f"| {r['label']} | {r['facts']} | {r['matched_updates']} | {e:.1f} | {r['trainable_parameters']} | {r['trainable_backbone_parameters']} | {r['optimizer_state_bytes']} |")
    lines += ["", "## What must not be claimed (section I.13)", "", *[f"- {s}" for s in NOT_CLAIMED], ""]
    return "\n".join(lines) + "\n"


def write_report(run_dir: Path, out_dir: Path, *, banner: str | None = None) -> list[Path]:
    """Write ``classes.csv``, ``cells.csv``, ``results.json`` and ``RESULTS.md`` into ``out_dir`` (never
    over an existing file)."""
    analysis = read_json(run_dir / "analysis.json")
    trains, evals = load_cell_records(run_dir)
    class_rows = _rows_classes(analysis)
    cell_rows = _rows_cells(trains, evals)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "classes.csv", out_dir / "cells.csv", out_dir / "RESULTS.md", out_dir / "results.json"]
    for p in paths:
        if p.exists():
            raise FileExistsError(p)
    class_rows, cell_rows = core.jsonable(class_rows), core.jsonable(cell_rows)  # non-finite values as strings
    _write_csv(paths[0], class_rows)
    _write_csv(paths[1], cell_rows)
    paths[2].write_text(render_markdown(analysis, class_rows, cell_rows, banner), encoding="utf-8")
    write_json(paths[3], core.jsonable({**core.envelope("analysis"), "banner": banner, "status": analysis["status"], "selection": analysis["analysis"]["selection"], "interpretable": analysis.get("interpretable"), "gate_reasons": analysis.get("gate_reasons"), "classes": class_rows, "cells": cell_rows, "not_claimed": list(NOT_CLAIMED), "classes_module": classes.OUTCOMES}))
    return paths
