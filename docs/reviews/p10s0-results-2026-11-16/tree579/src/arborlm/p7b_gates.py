"""P7-B confirmation-file gates (ADR-0014 sections 7a, 10 and 15).

The auditor role writes its own tools; this module defines and checks the three JSON files that the
registered stages require, and binds each to the hashes of the records it confirms:

(a) independent panel reconstruction: required by ``trace-b`` (``p7b-panel-confirmation-v1``)
(b) layout-hash reproduction: required by ``trace-b`` and ``simulate``
    (``p7b-layout-confirmation-v1``)
(c) independent re-simulation, one file per stream: required by ``analyze``
    (``p7b-resim-confirmation-v1``)

Each gate refuses on: a missing or unreadable file, a wrong schema, a verdict other than ``AGREE``,
wrong coverage, a hash that differs from the record it claims to confirm (stale or differing), or a
``tool_sha256`` that is not the SHA-256 of the auditor's tool file (a tracked file at a registered
path, ``core.AUDITOR_TOOLS``) as it exists at ``HEAD``. The dry run's stand-in files carry the
labelled stand-in tool hash, which is accepted only when ``dry_run`` is true. A gate returns a
record including the SHA-256 of the confirmation file and the tool hash, which the consuming stage
copies into its manifest.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

from pathlib import Path
from typing import Any

from . import p7b_core as core
from .io import file_sha256, read_json


def _load(path: Path | None, what: str) -> dict[str, Any]:
    if path is None:
        raise core.GateError(f"refused: {what} confirmation file is required (none given)")
    if not path.is_file():
        raise core.GateError(f"refused: {what} confirmation file not found: {path}")
    try:
        data = read_json(path)
    except ValueError as exc:
        raise core.GateError(f"refused: {what} confirmation file is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise core.GateError(f"refused: {what} confirmation file is not a JSON object")
    return data


def _tool_binding(
    data: dict[str, Any], kind: str, problems: list[str], *, dry_run: bool
) -> dict[str, Any]:
    """``tool_sha256`` must equal the SHA-256 of the tracked auditor tool at HEAD. The labelled
    dry-run stand-in is accepted only in a dry run."""
    claimed = data.get("tool_sha256")
    if claimed == core.STAND_IN_TOOL_SHA256 or data.get("tool") == core.STAND_IN_TOOL:
        if not dry_run:
            problems.append("a dry-run stand-in is not accepted outside a dry run")
            return {"tool_sha256": claimed, "stand_in": False}
        if claimed != core.STAND_IN_TOOL_SHA256 or data.get("tool") != core.STAND_IN_TOOL:
            problems.append("a stand-in must carry both the stand-in tool name and hash")
        return {"tool_sha256": claimed, "stand_in": True, "tool_path": core.AUDITOR_TOOLS[kind]}
    if not isinstance(claimed, str) or not claimed:
        problems.append("no tool_sha256")
        return {"tool_sha256": None, "stand_in": False}
    try:
        expected = core.auditor_tool_sha256_at_head(kind)
    except core.GateError as exc:
        problems.append(str(exc).removeprefix("refused: "))
        return {"tool_sha256": claimed, "stand_in": False}
    if claimed != expected:
        problems.append(
            f"tool_sha256 is not the SHA-256 of {core.AUDITOR_TOOLS[kind]} at HEAD ({expected})"
        )
    return {
        "tool_sha256": claimed,
        "tool_path": core.AUDITOR_TOOLS[kind],
        "tool_sha256_at_head": expected,
        "stand_in": False,
    }


def _raise(what: str, problems: list[str]) -> None:
    if problems:
        raise core.GateError(f"refused: {what} confirmation gate failed: " + "; ".join(problems))


# --- (a) independent panel reconstruction
def check_panel_confirmation(
    path: Path | None,
    *,
    panel_record_path: Path,
    panel_run_id: str,
    ranks: tuple[int, int] = core.PANEL_B_RANKS,
    rows: int = 512,
    earlier: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Schema::

        {"schema": "p7b-panel-confirmation-v1", "verdict": "AGREE", "tool": "<name and version>",
         "tool_sha256": "<SHA-256 of independent_panel.py at HEAD>",
         "panel_stage_run_id": "<run id of the panel stage>",
         "panel_record_sha256": "<SHA-256 of panel_record.json of that run>",
         "ranks": [2560, 3072], "panel_sha256": "<hex>", "row_sha256": ["<hex>" x 512],
         "earlier_panels_reproduced": {"P1": "<hex>", ..., "P5": "<hex>"},
         "overlap": {"with_P1_to_P5_panels": 0, "with_calibration_stream": 0,
                     "with_full_training_pool": 0, "duplicates_within_panel": 0}}

    The hashes in the file are the auditor's own reconstruction; they must equal the implementer's
    record exactly (byte-for-byte agreement of the panel and of every row)."""
    what = "panel"
    data = _load(path, what)
    record = read_json(panel_record_path)
    problems: list[str] = []
    if data.get("schema") != core.SCHEMA_PANEL_CONFIRMATION:
        problems.append("wrong schema")
    if data.get("verdict") != "AGREE":
        problems.append(f"verdict is {data.get('verdict')!r}, not 'AGREE'")
    if not data.get("tool"):
        problems.append("no tool name")
    binding = _tool_binding(data, "panel", problems, dry_run=dry_run)
    if data.get("panel_stage_run_id") != panel_run_id:
        problems.append("it confirms a different panel run")
    if data.get("panel_record_sha256") != file_sha256(panel_record_path):
        problems.append("panel_record_sha256 differs from the panel record (stale or different)")
    if data.get("ranks") != list(ranks) or record["ranks"] != list(ranks):
        problems.append("wrong rank range")
    if data.get("panel_sha256") != record["panel_sha256"]:
        problems.append("panel SHA-256 differs from the implementer's reconstruction")
    listed = data.get("row_sha256")
    if not isinstance(listed, list) or len(listed) != rows or listed != record["row_sha256"]:
        problems.append(f"per-row SHA-256 list differs or is not {rows} entries")
    reproduced = data.get("earlier_panels_reproduced")
    if reproduced != (earlier if earlier is not None else core.PRIOR_PANEL_SHA256):
        problems.append("the auditor's P1-P5 panel hashes are not the registered ones")
    overlap = data.get("overlap")
    wanted = {
        "with_P1_to_P5_panels",
        "with_calibration_stream",
        "with_full_training_pool",
        "duplicates_within_panel",
    }
    if not isinstance(overlap, dict) or set(overlap) != wanted or any(overlap.values()):
        problems.append("overlap block missing or not all zero")
    _raise(what, problems)
    return {
        "file": str(path),
        "sha256": file_sha256(path) if path else None,
        "verdict": "AGREE",
        "panel_run_id": panel_run_id,
        "panel_record_sha256": file_sha256(panel_record_path),
        "panel_sha256": record["panel_sha256"],
        "tool_binding": binding,
    }


# --- (b) layout-hash reproduction
def check_layout_confirmation(
    path: Path | None,
    *,
    hash_table_path: Path,
    layout_run_id: str,
    labels: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Schema::

        {"schema": "p7b-layout-confirmation-v1", "verdict": "AGREE", "tool": "<name and version>",
         "tool_sha256": "<SHA-256 of independent_layouts.py at HEAD>",
         "layout_stage_run_id": "<run id of the layouts stage>",
         "layout_hash_table_sha256": "<SHA-256 of layout_hash_table.json of that run>",
         "rows": [2, 8],
         "checkpoints": {"<label>": {"R2": {"L-COAX": "<canonical hash>", "L-NCOAX": ...,
                                            "L-PCOAX-1": ..., ..., "L-PCOAX-5": ...,
                                            "L-BCOAX": ...  (tree checkpoints only)},
                                     "R8": {...same keys...}}, ...}}   # every registered label

    The canonical hashes are the auditor's own rebuild (ADR-0014 section 4 'Exactness'); every one
    must equal the layout stage's recorded hash."""
    what = "layout-hash"
    data = _load(path, what)
    table = read_json(hash_table_path)
    expected_labels = labels if labels is not None else core.all_labels()
    problems: list[str] = []
    if data.get("schema") != core.SCHEMA_LAYOUT_CONFIRMATION:
        problems.append("wrong schema")
    if data.get("verdict") != "AGREE":
        problems.append(f"verdict is {data.get('verdict')!r}, not 'AGREE'")
    if not data.get("tool"):
        problems.append("no tool name")
    binding = _tool_binding(data, "layouts", problems, dry_run=dry_run)
    if data.get("layout_stage_run_id") != layout_run_id:
        problems.append("it confirms a different layouts run")
    if data.get("layout_hash_table_sha256") != file_sha256(hash_table_path):
        problems.append("layout_hash_table_sha256 differs from the layout hash table (stale)")
    if data.get("rows") != [2, 8]:
        problems.append("rows must be [2, 8]")
    checked = data.get("checkpoints")
    if not isinstance(checked, dict) or sorted(checked) != sorted(expected_labels):
        problems.append("checkpoints do not cover exactly the registered checkpoints")
    else:
        for label in expected_labels:
            _, kind = core.parse_label(label)
            wanted = core.required_confirmation_layouts(kind)
            for rows in (2, 8):
                mine = checked[label].get(f"R{rows}")
                if not isinstance(mine, dict) or sorted(mine) != sorted(wanted):
                    problems.append(f"{label} R{rows}: wrong layout set")
                    continue
                for name in wanted:
                    recorded = table["layouts"][label].get(core.layout_key(name, rows))
                    if mine[name] != recorded:
                        problems.append(f"{label} {name} R{rows}: canonical hash differs")
    _raise(what, problems[:20] + ([f"... {len(problems) - 20} more"] if len(problems) > 20 else []))
    return {
        "file": str(path),
        "sha256": file_sha256(path) if path else None,
        "verdict": "AGREE",
        "layout_run_id": layout_run_id,
        "layout_hash_table_sha256": file_sha256(hash_table_path),
        "checkpoints": len(expected_labels),
        "tool_binding": binding,
    }


# --- (c) independent re-simulation, one file per stream
REQUIRED_STREAMS = (core.STREAM_ACTUAL, *core.STREAMS_NULL)


def check_resim_confirmation(
    path: Path | None,
    *,
    stream: str,
    simulate_run_id: str,
    record_sha256: dict[str, str],
    expected_selection: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Schema (one file per evaluation stream)::

        {"schema": "p7b-resim-confirmation-v1", "verdict": "AGREE", "tool": "<name and version>",
         "tool_sha256": "<SHA-256 of independent_resim.py at HEAD>",
         "stream": "A" | "B", "simulate_stage_run_id": "<run id of that simulate stage>",
         "selection": ["<label>" x 18],            # ADR-0013 section 14 item 12 selection
         "settings": [{"R": 2, "C": 32}, {"R": 8, "C": 8}],
         "tie_rules": ["asc", "desc"],
         "streams_compared": ["actual", "null_1", "null_2", "null_3"],
         "layouts_compared": ["L-FREQ", "L-COAX", "L-BCOAX" (trees), "L-PCOAX-1", ..., "L-PCOAX-5"],
         "record_sha256": {"<label>": "<SHA-256 of simulate/<run>/workers/<label>.result.json>"},
         "checkpoints": {"<label>": {"differences": [], "integrity_problems": []}}}

    ``record_sha256`` binds the confirmation to the exact per-checkpoint simulation records it
    re-simulated; each must equal the hash of the record in the simulate stage's compact folder."""
    what = f"re-simulation (stream {stream})"
    data = _load(path, what)
    selection = core.independent_selection() if expected_selection is None else expected_selection
    problems: list[str] = []
    if data.get("schema") != core.SCHEMA_RESIM_CONFIRMATION:
        problems.append("wrong schema")
    if data.get("verdict") != "AGREE":
        problems.append(f"verdict is {data.get('verdict')!r}, not 'AGREE'")
    if not data.get("tool"):
        problems.append("no tool name")
    binding = _tool_binding(data, "resim", problems, dry_run=dry_run)
    if data.get("stream") != stream:
        problems.append(f"it confirms stream {data.get('stream')!r}, not {stream!r}")
    if data.get("simulate_stage_run_id") != simulate_run_id:
        problems.append("it confirms a different simulate run")
    got = data.get("selection")
    if not isinstance(got, list) or sorted(got) != sorted(selection):
        problems.append("selection is not the registered 18-checkpoint selection")
    if data.get("settings") != [{"R": r, "C": c} for r, c in core.CRITERION_SETTINGS]:
        problems.append("settings are not the two criterion settings")
    if data.get("tie_rules") != list(core.TIES):
        problems.append("tie rules are not both asc and desc")
    streams = data.get("streams_compared")
    if not isinstance(streams, list) or not set(REQUIRED_STREAMS) <= set(streams):
        problems.append("streams_compared must include actual and the three nulls")
    layouts = data.get("layouts_compared")
    needed = {core.L_FREQ, core.L_COAX, *core.L_PCOAX}
    if not isinstance(layouts, list) or not needed <= set(layouts):
        problems.append("layouts_compared must include L-FREQ, L-COAX and the five L-PCOAX")
    if any(core.is_tree(core.parse_label(lb)[1]) for lb in selection) and (
        not isinstance(layouts, list) or core.L_BCOAX not in layouts
    ):
        problems.append("layouts_compared must include L-BCOAX (tree checkpoints are selected)")
    hashes = data.get("record_sha256")
    checked = data.get("checkpoints")
    if not isinstance(hashes, dict) or sorted(hashes) != sorted(selection):
        problems.append("record_sha256 does not cover exactly the selection")
    else:
        for label in selection:
            if hashes[label] != record_sha256.get(label):
                problems.append(f"{label}: record hash differs from the simulate record (stale)")
    if not isinstance(checked, dict) or sorted(checked) != sorted(selection):
        problems.append("per-checkpoint results do not cover exactly the selection")
    else:
        for label in selection:
            entry = checked[label]
            if entry.get("differences") or entry.get("integrity_problems"):
                problems.append(f"{label}: differences or integrity problems are listed")
    _raise(what, problems[:20] + ([f"... {len(problems) - 20} more"] if len(problems) > 20 else []))
    return {
        "file": str(path),
        "sha256": file_sha256(path) if path else None,
        "verdict": "AGREE",
        "stream": stream,
        "simulate_run_id": simulate_run_id,
        "selection": sorted(selection),
        "tool_binding": binding,
    }
