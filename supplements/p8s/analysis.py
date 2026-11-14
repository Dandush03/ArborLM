# ruff: noqa: E501
"""ADR-0016 section 5: the supplementary analysis.

    uv run --locked python -m supplements.p8s.analysis --supplement-run <P8SUP dir>

The frozen ``p8_analysis.analyse`` is called on 60 ``CellData`` objects (55 registered records and the
five supplementary ones). Its result is nested under ``supplementary_analysis`` inside a file whose top
level carries the supplementary label and the registered (INCOMPLETE, ``none``) status. The result is
compared with the registered ``analysis.json`` and CSVs under the exact allowed-difference rule of
section 5 (W5); any other difference stops the supplement. Predictions 1-9 of section 2 are checked
explicitly and written into the output. The frozen ``load_cells``, ``check_provenance`` and
``run_analysis`` are not called.
"""

import argparse
import csv
import json
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from arborlm import p7b_core as b_core
from arborlm import p8_analysis as an
from arborlm import p8_core as core
from arborlm.io import file_sha256, read_json
from arborlm.records import allocate_run, utc_now

from . import common, frozen

REGISTERED_STATUS = "INCOMPLETE"
REGISTERED_DECISION = "none"
NESTED_NOTE = (
    "The nested study_status and decision describe the 60-record supplementary input only. They are "
    "not the registered study's: the registered P8 study remains INCOMPLETE (55/60 simulated) with "
    "decision 'none'."
)
ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("study_status",),
    ("cells_with_complete_records",),
    ("missing_cells",),
    ("cases", "C04"),
    ("cases", "C05"),
    ("decision_inputs", "section_8_option_indicated"),
    ("decision_inputs", "section_8_reason"),
)
AFFECTED_CASES = ("C04", "C05")
SCHEMA = "P8SUP-analysis-v1"


# --- loading ---------------------------------------------------------------------------------------
def load_cell_data(
    eval_run: Path, registered_sim_run: Path, supplement_run: Path | None
) -> tuple[dict[str, an.CellData], list[dict[str, Any]]]:
    """The 60 registry cells with a completed eval and sim record (supplement records for the five
    labels, registered records otherwise), and the missing ones with the frozen loader's reasons.
    Same checks and reason strings as ``p8_analysis.load_cells``, without its provenance step."""
    cells: dict[str, an.CellData] = {}
    missing: list[dict[str, Any]] = []
    for cell in core.cells():
        reasons: list[str] = []
        e_path = eval_run / "cells" / cell.label / "eval.json"
        run = (
            supplement_run
            if cell.label in common.SUPPLEMENT_CELLS and supplement_run is not None
            else registered_sim_run
        )
        s_path = run / "cells" / cell.label / "sim.json"
        e_rec = s_rec = None
        if not e_path.is_file():
            reasons.append("eval.json missing")
        else:
            e_rec = read_json(e_path)
            if e_rec.get("outcome") != "completed":
                reasons.append("eval record not completed")
        if not s_path.is_file():
            reasons.append("sim.json missing")
        else:
            s_rec = read_json(s_path)
            if s_rec.get("outcome") != "completed" or set(s_rec.get("panels", {})) != set(
                an.PANELS
            ):
                reasons.append("sim record not completed for both panels")
        if not reasons and e_rec is not None and s_rec is not None:
            if s_rec["eval_json_sha256"] != file_sha256(e_path):
                reasons.append("sim.json was built from a different eval.json")
        if reasons or e_rec is None or s_rec is None:
            missing.append({"label": cell.label, "reasons": reasons})
        else:
            cells[cell.label] = an.CellData(cell, e_rec, s_rec)
    return cells, missing


def check_supplement_provenance(
    supplement_run: Path, eval_run: Path, repo: Path = common.ROOT
) -> dict[str, Any]:
    """New provenance check (replaces ``check_provenance``): every supplementary record's
    ``eval_json_sha256``, one consistent supplement identity over the five records, the identity
    equal to the current ADR-0016 and supplement code, the frozen digest, and the stage manifest."""
    problems: list[str] = []
    spec = common.supplement_spec_sha256(repo)
    source = common.supplement_source_digest(repo)
    identities: set[str] = set()
    for label in common.SUPPLEMENT_CELLS:
        path = supplement_run / "cells" / label / "sim.json"
        if not path.is_file():
            problems.append(f"{label}: no supplementary sim.json")
            continue
        rec = read_json(path)
        if rec.get("supplement") != "ADR-0016" or rec.get("label") != label:
            problems.append(f"{label}: not an ADR-0016 supplementary record of this cell")
        if rec.get("eval_json_sha256") != file_sha256(eval_run / "cells" / label / "eval.json"):
            problems.append(
                f"{label}: eval_json_sha256 differs from the evaluation run's eval.json"
            )
        if rec.get("supplement_spec_sha256") != spec:
            problems.append(f"{label}: supplement_spec_sha256 differs from the current ADR-0016")
        if rec.get("supplement_source_sha256") != source:
            problems.append(f"{label}: supplement_source_sha256 differs from the current code")
        if rec.get("source_sha256") != common.FROZEN_SOURCE_DIGEST:
            problems.append(f"{label}: source_sha256 is not the frozen digest")
        if (rec.get("frozen_inputs") or {}).get("source_sha256") != common.FROZEN_SOURCE_DIGEST:
            problems.append(f"{label}: frozen_inputs.source_sha256 is not the frozen digest")
        if (rec.get("frozen_inputs") or {}).get(
            "p7b_reproduction_record_cited"
        ) != common.p7b_reproduction_record_cited():
            problems.append(f"{label}: frozen_inputs.p7b_reproduction_record_cited differs")
        freeze = rec.get("supplement_freeze_commit")
        if not freeze or not freeze.get("commit") or not freeze.get("tree"):
            problems.append(f"{label}: supplement_freeze_commit lacks commit and tree")
        identities.add(
            json.dumps(
                [rec.get("supplement_spec_sha256"), rec.get("supplement_source_sha256"), freeze],
                sort_keys=True,
            )
        )
    if len(identities) > 1:
        problems.append("the five supplementary records do not share one supplement identity")
    manifest_path = supplement_run / "manifest.json"
    manifest: dict[str, Any] = {}
    if not manifest_path.is_file():
        problems.append("stage manifest missing")
    else:
        manifest = read_json(manifest_path)
        if manifest.get("status") != "completed" or manifest.get("cells_completed") != 5:
            problems.append(f"stage status is {manifest.get('status')}, not completed 5/5")
        if manifest.get("supplement_spec_sha256") != spec:
            problems.append(
                "stage manifest supplement_spec_sha256 differs from the current ADR-0016"
            )
        if manifest.get("p7b_reproduction_record_cited") != common.p7b_reproduction_record_cited():
            problems.append("stage manifest p7b_reproduction_record_cited differs")
    if problems:
        raise common.SupplementError("supplement provenance: " + "; ".join(problems[:8]))
    return {
        "supplement_spec_sha256": spec,
        "supplement_source_sha256": source,
        "supplement_freeze_commit": manifest.get("supplement_freeze_commit"),
        "stage_wall_seconds": manifest.get("wall_seconds"),
        "stage_peak_worker_rss_bytes": manifest.get("peak_worker_rss_bytes"),
        "stage_cap_seconds": manifest.get("cap_seconds"),
        "stage_workers": manifest.get("workers"),
        "p7b_reproduction_record_cited": common.p7b_reproduction_record_cited(),
    }


# --- comparison with the registered outputs (W5) -----------------------------------------------------
def diff_paths(a: Any, b: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[tuple[Any, ...]] = []
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((*path, key))
            else:
                out += diff_paths(a[key], b[key], (*path, key))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += diff_paths(x, y, (*path, i))
        return out
    return [] if (type(a) is type(b) or {type(a), type(b)} <= {int, float}) and a == b else [path]


def is_allowed(path: tuple[Any, ...]) -> bool:
    return any(path[: len(prefix)] == prefix for prefix in ALLOWED_PREFIXES)


def compare_analysis(registered: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """``jsonable(analyse(...))`` against the registered ``analysis.json`` without ``dry_run`` and
    ``inputs`` (written by ``run_analysis``, not by ``analyse``)."""
    reg = {k: v for k, v in registered.items() if k not in ("dry_run", "inputs")}
    paths = diff_paths(reg, new)
    allowed = sorted(
        {".".join(map(str, p[: 2 if p[:1] == ("cases",) else 1])) for p in paths if is_allowed(p)}
    )
    disallowed = [".".join(map(str, p)) for p in paths if not is_allowed(p)]
    return {
        "allowed_differences_seen": allowed,
        "disallowed_differences": disallowed[:50],
        "disallowed_count": len(disallowed),
        "ok": not disallowed,
    }


def read_csv_rows(path: Path, skip_header_line: bool) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        if skip_header_line:
            stream.readline()
        rows = list(csv.reader(stream))
    return rows[0], rows[1:]


def compare_csvs(
    registered_dir: Path, new_dir: Path, skip_new_header_line: bool = True
) -> dict[str, Any]:
    """CSV bodies below the supplementary header line: cells.csv differs only by the rows of the five
    new cells, pairs.csv only by rows whose case is C04 or C05, scorecard.csv only in the C04/C05
    rows and in the study_status column of every row."""
    out: dict[str, Any] = {}
    five = set(common.SUPPLEMENT_CELLS)
    for name in ("cells.csv", "pairs.csv", "scorecard.csv"):
        rh, rr = read_csv_rows(registered_dir / name, False)
        nh, nr = read_csv_rows(new_dir / name, skip_new_header_line)
        problems: list[str] = []
        detail: dict[str, Any]
        if rh != nh:
            problems.append("header differs")
        if name == "cells.csv":
            li = nh.index("label")
            kept = [r for r in nr if r[li] not in five]
            extra = [r for r in nr if r[li] in five]
            if kept != rr:
                problems.append("rows of the 55 registered cells differ")
            detail = {"rows_of_new_cells": len(extra), "rows_registered": len(rr)}
        elif name == "pairs.csv":
            ci = nh.index("case")
            kept = [r for r in nr if r[ci] not in AFFECTED_CASES]
            ref = [r for r in rr if r[ci] not in AFFECTED_CASES]
            if kept != ref:
                problems.append("rows of cases other than C04 and C05 differ")
            detail = {
                "rows_C04_C05_registered": len(rr) - len(ref),
                "rows_C04_C05_supplementary": len(nr) - len(kept),
            }
        else:
            ci, si = nh.index("case"), nh.index("study_status")
            if [r[ci] for r in nr] != [r[ci] for r in rr]:
                problems.append("case order or count differs")
            else:
                for new_row, reg_row in zip(nr, rr, strict=True):
                    if new_row[ci] in AFFECTED_CASES:
                        continue
                    a = [v for i, v in enumerate(new_row) if i != si]
                    b = [v for i, v in enumerate(reg_row) if i != si]
                    if a != b:
                        problems.append(f"row {new_row[ci]} differs outside study_status")
            detail = {"study_status_column": sorted({r[si] for r in nr})}
        out[name] = {"ok": not problems, "problems": problems, **detail}
    out["ok"] = all(v["ok"] for v in out.values() if isinstance(v, dict))
    return out


# --- predictions 1-9 of section 2 ------------------------------------------------------------------
def _groups(sim: dict[str, Any]) -> list[tuple[str, str, str, dict[str, Any]]]:
    return [
        (panel, stream, key, group)
        for panel in an.PANELS
        for stream, groups in sim["panels"][panel]["streams"].items()
        for key, group in groups.items()
    ]


def _counts(group: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [(cap, tie, c) for cap, ties in group["by_c"].items() for tie, c in ties.items()]


def _result(statement: str, checked: int, violations: list[str]) -> dict[str, Any]:
    return {
        "statement": statement,
        "checked": checked,
        "violations": violations[:20],
        "violation_count": len(violations),
        "holds": checked > 0 and not violations,
    }


def pred_1(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad: list[str] = []
    n = 0
    for label in labels:
        sim = cells[label].sim
        for panel, stream, key, group in _groups(sim):
            if stream != "actual":
                continue
            for cap, tie, c in _counts(group):
                n += 1
                if c["misses_warm"] != 0:
                    bad.append(
                        f"{label} {panel} {key} C{cap} {tie}: misses_warm={c['misses_warm']}"
                    )
    return _result("counted (post-warm-up) miss count is 0 for the actual stream", n, bad)


def expected_layout_keys(variant: str) -> set[str]:
    """The layout keys of the order-shuffled and null streams of a cell (measured on the registered
    records: L-FREQ and L-COAX at R = 2 and R = 8, for flat and tree variants alike)."""
    return {f"{name}|R{rows}" for name in (b_core.L_FREQ, an.L_COAX) for rows in (2, 8)}


def pred_2(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad: list[str] = []
    n = 0
    for label in labels:
        sim = cells[label].sim
        expected = expected_layout_keys(cells[label].cell.variant)
        for panel in an.PANELS:
            streams = sim["panels"][panel]["streams"]
            for stream in ("order_shuffled", *b_core.STREAMS_NULL):
                got = set(streams[stream])
                if not got or got != expected or not got <= set(streams["actual"]):
                    bad.append(
                        f"{label} {panel} {stream}: layout keys {sorted(got)} differ from the "
                        f"expected {sorted(expected)} (empty or different set compared)"
                    )
                for key, group in streams[stream].items():
                    n += 1
                    if group != streams["actual"][key]:
                        bad.append(f"{label} {panel} {stream} {key}: record differs from actual")
            reuse = sim["panels"][panel]["temporal_reuse"]
            for stream in ("order_shuffled", *b_core.STREAMS_NULL):
                n += 1
                if reuse[stream] != reuse["actual"]:
                    bad.append(f"{label} {panel} temporal_reuse {stream} differs from actual")
    return _result("null and order-shuffled records equal the actual record", n, bad)


def pred_3(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad = []
    n = 0
    for label in labels:
        for panel in an.PANELS:
            n += 1
            ratio = cells[label].reuse(panel)["ratio_to_null"]
            if ratio != 1.0:
                bad.append(f"{label} {panel}: ratio_to_null={ratio!r}")
    return _result("temporal-reuse ratio to null is exactly 1.0", n, bad)


def pred_4(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad = []
    n = 0
    for label in labels:
        data = cells[label]
        for panel in an.PANELS:
            for key in data.sim["panels"][panel]["streams"]["actual"]:
                name, _, rows = key.partition("|R")
                for tie in core.TIES:
                    n += 1
                    e, _ = data.e(panel, int(rows), tie, name)
                    null = data.null_mean(panel, int(rows), tie, b_core.L_FREQ)
                    if e is not None or not null < Fraction(1, 20):
                        bad.append(f"{label} {panel} {key} {tie}: E={e}, null mean={float(null)}")
    return _result("E is undefined (null mean below 0.05) in all five cells", n, bad)


def pred_5(result: dict[str, Any]) -> dict[str, Any]:
    bad = []
    n = 0
    for case in AFFECTED_CASES:
        for panel in an.PANELS:
            n += 1
            got = result["cases"][case]["panels"][panel].get("classification")
            if got != an.QUALITY_FAILED:
                bad.append(f"{case} panel {panel}: {got}")
        n += 1
        got = result["cases"][case]["study_classification"]["class"]
        if got != an.QUALITY_FAILED:
            bad.append(f"{case} study class: {got}")
    return _result("supplementary class of C04 and C05 is QUALITY-FAILED on both panels", n, bad)


def pred_6(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad = []
    n = 0
    for label in labels:
        for panel, stream, key, group in _groups(cells[label].sim):
            distinct = group["stats"]["distinct_stream"]
            for cap, tie, c in _counts(group):
                n += 1
                ok = (
                    distinct <= 8
                    and c["misses_warm"] == 0
                    and c["first_touch_warm"] == 0
                    and c["misses_all"] == c["first_touch_all"] == distinct
                )
                if not ok:
                    bad.append(
                        f"{label} {panel} {stream} {key} C{cap} {tie}: {c} distinct={distinct}"
                    )
    return _result(
        "misses_warm = first_touch_warm = 0, misses_all = first_touch_all = distinct pages, "
        "and distinct pages <= 8",
        n,
        bad,
    )


def pred_7(
    cells: dict[str, an.CellData], labels: tuple[str, ...] = common.SUPPLEMENT_CELLS
) -> dict[str, Any]:
    bad = []
    n = 0
    for label in labels:
        for panel in an.PANELS:
            n += 1
            hashes = {e["stream_sha256"] for e in cells[label].sim["panels"][panel]["null_streams"]}
            if len(hashes) != 1:
                bad.append(f"{label} {panel}: {len(hashes)} distinct null stream hashes")
    return _result("the three null stream_sha256 values of a panel are identical", n, bad)


def pred_8(result: dict[str, Any]) -> dict[str, Any]:
    bad = []
    if result["concentration_controls_bind"] is not False:
        bad.append(f"concentration_controls_bind={result['concentration_controls_bind']}")
    cases = [q["case"] for q in result["open_questions"]]
    if cases != ["C09"]:
        bad.append(f"open_questions cases={cases}")
    return _result("concentration_controls_bind is false and open_questions is [C09]", 2, bad)


def pred_9(result: dict[str, Any]) -> dict[str, Any]:
    letter = result["decision_inputs"]["section_8_option_indicated"]
    bad = [] if letter == "c" else [f"letter={letter}"]
    return _result(
        "supplementary mechanical decision letter is 'c' (not a registered decision)", 1, bad
    )


def check_predictions(cells: dict[str, an.CellData], result: dict[str, Any]) -> dict[str, Any]:
    preds = {
        "1": pred_1(cells),
        "2": pred_2(cells),
        "3": pred_3(cells),
        "4": pred_4(cells),
        "5": pred_5(result),
        "6": pred_6(cells),
        "7": pred_7(cells),
        "8": pred_8(result),
        "9": pred_9(result),
    }
    return {
        "source": "ADR-0016 section 2, fixed before observation; these are checks of derived "
        "predictions, not findings; any violation is a discrepancy to investigate, never adjusted",
        "predictions": preds,
        "all_hold": all(p["holds"] for p in preds.values()),
    }


# --- outputs -----------------------------------------------------------------------------------------
def csv_text(path_name: str, header: list[str], rows: list[list[Any]]) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / path_name
        an.write_csv(target, header, rows)
        return target.read_text(encoding="utf-8")


def render_markdown(wrapper: dict[str, Any]) -> str:
    nested = wrapper["supplementary_analysis"]
    pred = wrapper["predictions_check"]
    comp = wrapper["comparison_with_registered"]
    lines = [
        f"# {common.SUPPLEMENT_LABEL}",
        "",
        f"- Registered P8 study status: **{wrapper['registered_study_status']}**; registered "
        f"decision: **{wrapper['registered_decision']}** (unchanged).",
        f"- {NESTED_NOTE}",
        f"- Nested (supplementary, 60-record input) status: `{nested['study_status']}`; mechanical "
        f"decision-map letter: `{nested['decision_inputs']['section_8_option_indicated']}`. It "
        "authorizes nothing and is not a registered decision.",
        "- Status: implementation self-check output. Not independent review, not Astra validation, "
        "not human approval. Astra review: NOT_PERFORMED.",
        "- All values below are computed from the records (measured), none is hypothetical.",
        "",
        "## Supplementary classes of the concentration controls (not registered classes)",
        "",
        "| case | panel A | panel B | study class |",
        "|---|---|---|---|",
    ]
    for case in AFFECTED_CASES:
        entry = nested["cases"][case]
        lines.append(
            f"| {case} | {entry['panels']['A'].get('classification')} | "
            f"{entry['panels']['B'].get('classification')} | "
            f"{entry['study_classification']['class']} |"
        )
    lines += [
        "",
        "## Predictions of ADR-0016 section 2 (derived on paper before execution)",
        "",
        f"All nine hold: **{pred['all_hold']}**.",
        "",
        "| # | statement | checked | violations | holds |",
        "|---|---|---|---|---|",
    ]
    for number, p in pred["predictions"].items():
        lines.append(
            f"| {number} | {p['statement']} | {p['checked']} | {p['violation_count']} | {p['holds']} |"
        )
    lines += [
        "",
        "## Comparison with the registered analysis (section 5, W5)",
        "",
        f"- analysis.json: ok = {comp['analysis']['ok']}; allowed differences seen: "
        f"{', '.join(comp['analysis']['allowed_differences_seen']) or 'none'}; disallowed: "
        f"{comp['analysis']['disallowed_count']}.",
    ]
    for name in ("cells.csv", "pairs.csv", "scorecard.csv"):
        c = comp["csv"][name]
        lines.append(
            f"- {name}: ok = {c['ok']}"
            + (f" ({'; '.join(c['problems'])})" if c["problems"] else "")
        )
    lines += [
        "",
        "## Claims this output does not make",
        "",
        "- It is not the registered P8 output and does not supersede `analysis.json`.",
        "- The registered study is not complete and its decision is not (c).",
        "- The identity null carries no locality information; with one set E is undefined by "
        "construction. The supplement reuses the same traces and replicates nothing.",
        "- No positive result for locality-aware training.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    cells: dict[str, an.CellData],
    missing: list[dict[str, Any]],
    registered_dir: Path,
    out_root: Path,
    meta: dict[str, Any],
) -> Path:
    """Analyse, compare, check predictions, write. Raises ``SupplementError`` on any disallowed
    difference (nothing is written then; the caller keeps the failure record)."""
    if missing:
        raise common.SupplementError(f"supplement incomplete: {len(missing)} cells lack records")
    result = an.analyse(cells, missing)
    nested = json.loads(json.dumps(an.jsonable(result)))
    registered = read_json(registered_dir / "analysis.json")
    analysis_cmp = compare_analysis(registered, nested)
    texts = {
        "scorecard.csv": csv_text(
            "scorecard.csv", *an.scorecard_rows(an.clean_scorecard_source(result))
        ),
        "cells.csv": csv_text("cells.csv", *an.cells_rows(cells)),
        "pairs.csv": csv_text("pairs.csv", *an.pairs_rows(cells)),
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in texts.items():
            _write_text(Path(tmp) / name, f"# {common.SUPPLEMENT_LABEL}\n{text}")
        csv_cmp = compare_csvs(registered_dir, Path(tmp))
    if not (analysis_cmp["ok"] and csv_cmp["ok"]):
        raise common.SupplementError(
            "STOP: differences outside the allowed set of ADR-0016 section 5: "
            + json.dumps({"analysis": analysis_cmp, "csv": csv_cmp})[:2000]
        )
    wrapper = {
        "label": common.SUPPLEMENT_LABEL,
        "schema": SCHEMA,
        "registered_study_status": REGISTERED_STATUS,
        "registered_decision": REGISTERED_DECISION,
        "note": NESTED_NOTE,
        "supplement": "ADR-0016",
        "p7b_reproduction_record_cited": common.p7b_reproduction_record_cited(),
        "inputs": meta,
        "comparison_with_registered": {"analysis": analysis_cmp, "csv": csv_cmp},
        "predictions_check": check_predictions(cells, nested),
        "supplementary_analysis": nested,
    }
    out = allocate_run(out_root, prefix="P8SUPA")
    try:
        _write_files(out, wrapper, texts)
    except Exception as exc:
        # an unexpected failure after the output folder exists: record it, keep the folder, re-raise
        _write_text(out / "failed.json", _dump(failure_record(exc), indent=1))
        raise
    return out


def failure_record(exc: BaseException) -> dict[str, Any]:
    return {
        "label": common.SUPPLEMENT_LABEL,
        "status": "FAILED",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": "".join(traceback.format_exception(exc)),
        "note": "unexpected exception; the output is kept and the analysis is not re-run",
    }


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _dump(obj: Any, **kwargs: Any) -> str:
    """JSON text as the frozen writers do it: sorted keys, ``allow_nan=False``, UTF-8 on disk."""
    return json.dumps(obj, sort_keys=True, allow_nan=False, **kwargs) + "\n"


def _write_files(out: Path, wrapper: dict[str, Any], texts: dict[str, str]) -> None:
    _write_text(out / "supplementary_analysis.json", _dump(wrapper, indent=1, ensure_ascii=False))
    for name, text in texts.items():
        _write_text(out / name, f"# {common.SUPPLEMENT_LABEL}\n{text}")
    _write_text(out / "SUPPLEMENTARY_ANALYSIS.md", render_markdown(wrapper))
    _write_text(
        out / "manifest.json",
        _dump(
            {
                "label": common.SUPPLEMENT_LABEL,
                "schema": SCHEMA + "-manifest",
                "finished_utc": utc_now(),
                "predictions_all_hold": wrapper["predictions_check"]["all_hold"],
                "outputs": {
                    n: file_sha256(out / n)
                    for n in (
                        "supplementary_analysis.json",
                        "cells.csv",
                        "pairs.csv",
                        "scorecard.csv",
                        "SUPPLEMENTARY_ANALYSIS.md",
                    )
                },
            },
            indent=1,
        ),
    )


def run(
    eval_run: Path,
    registered_sim_run: Path,
    supplement_run: Path,
    registered_dir: Path,
    out_root: Path,
    repo: Path = common.ROOT,
) -> Path:
    started = time.monotonic()
    verification = frozen.verify_frozen_material(repo, eval_run, registered_sim_run)
    if not verification["ok"]:
        raise common.SupplementError(
            "frozen material does not verify: " + "; ".join(verification["problems"][:5])
        )
    provenance = check_supplement_provenance(supplement_run, eval_run, repo)
    cells, missing = load_cell_data(eval_run, registered_sim_run, supplement_run)
    meta = {
        "eval_run": str(eval_run),
        "registered_sim_run": str(registered_sim_run),
        "supplement_run": str(supplement_run),
        "registered_analysis": str(registered_dir),
        "registered_analysis_sha256": file_sha256(registered_dir / "analysis.json"),
        "frozen_verification": verification,
        "supplement_provenance": provenance,
        "cells_with_complete_records": len(cells),
    }
    out = write_outputs(cells, missing, registered_dir, out_root, meta)
    analysis_seconds = time.monotonic() - started
    stage_seconds = float(provenance["stage_wall_seconds"] or 0.0)
    timing = {
        "stage_wall_seconds": stage_seconds,
        "analysis_wall_seconds": analysis_seconds,
        "combined_within_limit": stage_seconds + analysis_seconds <= common.WALL_LIMIT_SECONDS,
        "limit_seconds": common.WALL_LIMIT_SECONDS,
    }
    _write_text(out / "timing.json", _dump(timing, indent=1))
    return out


def _write_stopped(out_root: Path, record: dict[str, Any]) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    stopped = out_root / f"STOPPED-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write_text(stopped, _dump(record, indent=1))
    return stopped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m supplements.p8s.analysis")
    parser.add_argument("--supplement-run", type=Path, required=True)
    parser.add_argument("--experiments-root", type=Path, default=None)
    parser.add_argument("--eval-run", type=Path, default=None)
    parser.add_argument("--registered-sim-run", type=Path, default=None)
    parser.add_argument("--registered-analysis", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = args.experiments_root or common.default_experiments_root()
    registered = args.registered_analysis or (
        common.ROOT / "results/p8-2026-11-14/analysis" / common.ANALYSIS_RUN_NAME
    )
    out_root = args.out_root or common.ROOT / common.RESULTS_DIR / "analysis"
    try:
        out = run(
            args.eval_run or root / common.EVAL_RUN_NAME,
            args.registered_sim_run or root / common.SIM_RUN_NAME,
            args.supplement_run,
            registered,
            out_root,
        )
    except common.SupplementError as exc:
        print(f"P8 supplementary analysis STOPPED: {exc}", file=sys.stderr)
        _write_stopped(out_root, {"label": common.SUPPLEMENT_LABEL, "stopped": str(exc)})
        return 2
    except Exception as exc:
        # unexpected failure: keep type, message and traceback, then re-raise (not re-runnable)
        _write_stopped(out_root, failure_record(exc))
        raise
    wrapper = json.loads((out / "supplementary_analysis.json").read_text(encoding="utf-8"))
    print(json.dumps({"predictions_all_hold": wrapper["predictions_check"]["all_hold"]}, indent=1))
    print(f"output directory: {out}")
    return 0 if wrapper["predictions_check"]["all_hold"] else 3


if __name__ == "__main__":
    sys.exit(main())
