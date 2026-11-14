# ruff: noqa: E501
"""ADR-0016 gate 4, checks that need local data. A skipped test does not satisfy them, so they run as
this recorded script:

    uv run --locked python -m supplements.p8s.preflight --scratch <dir>

1. frozen material: file blobs at 378aeac, ADR-0015 vs its blob at 2d10338, the digest, 60 eval.json
   and 55 sim.json vs the blobs at b8302c2;
2. trace verification: ``p8_sim.load_trace`` on calibration, A and B of all 60 cells (file hashes
   against eval.json, ``check_trace``, counts hash);
3. layout equality for the five cells: layout build from the CALIBRATION trace only (no null, no
   ``simulate_trace``, nothing else of the five cells' panel traces is read here) against the
   ``layouts.int16.bin`` already in each failed cell directory;
4. replay of registered completed cells through the new wrappers (precondition evaluated and false),
   field by field against the registered ``sim.json`` (W6 exclusions only);
5. extra self-check: the frozen ``analyse`` on the 55 registered records reproduces the registered
   ``analysis.json`` and CSVs exactly (validates the supplement's loader and comparison code).

Nothing here simulates, nulls or analyses any of the five supplement cells' real traces. Scratch
output goes to ``--scratch``; the record goes to ``results/p8-supplement-2026-11-14/preflight/``.
"""

import argparse
import json
import platform
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from arborlm import p7b_layout as layout_mod
from arborlm import p8_analysis as an
from arborlm import p8_core as core
from arborlm import p8_sim
from arborlm.io import file_sha256, read_json, write_json
from arborlm.p7a_trace import configure_deterministic_cpu
from arborlm.records import utc_now

from . import analysis, common, frozen
from . import sim as supplement_sim

REPLAY_LABELS = (
    "b102-o302-s601-C04",  # near-collapsed concentration cell, 17 slots (flat)
    "b102-o302-s602-C05",  # near-collapsed concentration cell, 16 slots (tree)
    "b103-o303-s601-C01",  # ordinary flat cell
    "b101-o301-s601-C07",  # ordinary tree cell
)
REGISTERED_NULL_METHOD = "exact count-preserving (ADR-0013 section 14 item 8)"
EXCLUDED_TOP_LEVEL = (
    "seconds",
    "worker_seconds",
    "peak_rss_bytes_ru_maxrss",
    "source_sha256",
    "spec_sha256",
    "reproduction_record_sha256",
)


def is_supplement_key(key: str) -> bool:
    """Exactly the key ``supplement`` and the keys ``supplement_*`` (W6), nothing broader."""
    return key == "supplement" or key.startswith("supplement_")


def _norm(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


def compare_replay(registered: dict[str, Any], mine: dict[str, Any]) -> dict[str, Any]:
    """Every field equals the registered ``sim.json`` except exactly the W6 list: the timing, RSS and
    identity fields, the added ``supplement``/``supplement_*``/``frozen_inputs`` fields and the added ``method`` and
    ``precondition`` keys of each ``panels.*.null_streams`` entry."""
    mine = _norm(mine)
    problems: list[str] = []
    added_top = sorted(
        k for k in mine if k not in registered and not is_supplement_key(k) and k != "frozen_inputs"
    )
    if added_top:
        problems.append(f"unexpected added top-level keys: {added_top}")
    mine_core = {
        k: v
        for k, v in mine.items()
        if k not in EXCLUDED_TOP_LEVEL and not is_supplement_key(k) and k != "frozen_inputs"
    }
    reg_core = {k: v for k, v in registered.items() if k not in EXCLUDED_TOP_LEVEL}
    for panel, record in mine_core["panels"].items():
        for entry in record["null_streams"]:
            if entry.pop("method", None) != REGISTERED_NULL_METHOD:
                problems.append(f"panel {panel}: null method is not the registered one")
            if entry.pop("precondition", None) is not False:
                problems.append(f"panel {panel}: precondition is not false")
    diffs = analysis.diff_paths(reg_core, mine_core)
    problems += [f"differs: {'.'.join(map(str, p))}" for p in diffs[:20]]
    return {
        "ok": not problems,
        "problems": problems,
        "fields_excluded": [
            *EXCLUDED_TOP_LEVEL,
            "supplement",
            "supplement_*",
            "frozen_inputs",
            "panels.*.null_streams[].method",
            "panels.*.null_streams[].precondition",
        ],
        "top_level_keys_compared": sorted(reg_core),
    }


def check_frozen(repo: Path, eval_run: Path, sim_run: Path) -> dict[str, Any]:
    out = frozen.verify_frozen_material(repo, eval_run, sim_run)
    results = out.get("results_blobs", {})
    out["ok"] = bool(
        out["ok"]
        and results.get("eval_json_verified") == 60
        and results.get("sim_json_verified") == 55
    )
    return out


def check_traces(eval_run: Path) -> dict[str, Any]:
    problems: list[str] = []
    verified = 0
    for cell in core.cells():
        cell_dir = eval_run / "cells" / cell.label
        record = read_json(cell_dir / "eval.json")
        for name in ("calibration", "A", "B"):
            try:
                p8_sim.load_trace(cell_dir, record, name)
                verified += 1
            except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                problems.append(f"{cell.label} {name}: {type(exc).__name__}: {exc}")
    return {
        "ok": not problems and verified == 180,
        "traces_verified": verified,
        "expected": 180,
        "problems": problems,
        "method": "p8_sim.load_trace: file sha256 vs eval.json, check_trace, counts sha256",
    }


def check_layout_equality(eval_run: Path, sim_run: Path, scratch: Path) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for label in common.SUPPLEMENT_CELLS:
        cell = core.parse_label(label)
        cell_dir = eval_run / "cells" / label
        record = read_json(cell_dir / "eval.json")
        cal_selected, cal_branches = p8_sim.load_trace(cell_dir, record, "calibration")
        calibration = layout_mod.CalibrationTrace.declared(
            cal_selected, cal_branches, cell.variant, label
        )
        orders, _ = p8_sim.build_p8_layouts(calibration)
        hashes = p8_sim.layout_hashes(orders)
        target = scratch / "layout_equality" / label / "layouts.int16.bin"
        index = layout_mod.write_layout_file(
            target,
            [
                layout_mod.BuiltLayout(
                    key.partition("|R")[0],
                    int(key.partition("|R")[2]) if "|R" in key else None,
                    order,
                )
                for key, order in orders.items()
            ],
        )
        failed = sim_run / "cells" / label / "layouts.int16.bin"
        problems: list[str] = []
        if not failed.is_file():
            problems.append("no layouts.int16.bin in the failed cell directory")
            equal_bytes = equal_hashes = False
        else:
            equal_bytes = target.read_bytes() == failed.read_bytes()
            decoded = layout_mod.read_layout_file(failed, index)
            equal_hashes = decoded == orders and p8_sim.layout_hashes(decoded) == hashes
        if not equal_bytes:
            problems.append("rebuilt layout file differs from the failed directory's")
        if not equal_hashes:
            problems.append("rebuilt hash table differs from the failed directory's layouts")
        cells[label] = {
            "ok": not problems,
            "problems": problems,
            "layout_file_sha256": file_sha256(target),
            "failed_dir_layout_file_sha256": file_sha256(failed) if failed.is_file() else None,
            "layouts": len(orders),
            "hash_table_entries": len(hashes),
            "built_from": "calibration trace only",
        }
    return {"ok": all(c["ok"] for c in cells.values()), "cells": cells}


def check_replay(eval_run: Path, sim_run: Path, scratch: Path) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for label in REPLAY_LABELS:
        cell = core.parse_label(label)
        out_dir = scratch / "replay" / label
        out_dir.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        mine = supplement_sim.build_record(
            cell, eval_run / "cells" / label, out_dir, freeze=None, deadline=None
        )
        write_json(out_dir / "sim.json", mine)
        registered = read_json(sim_run / "cells" / label / "sim.json")
        verdict = compare_replay(registered, mine)
        preconditions = {p: v["holds"] for p, v in mine["supplement_null_preconditions"].items()}
        layout_ok = (
            file_sha256(out_dir / "layouts.int16.bin") == registered["layouts"]["file_sha256"]
        )
        problems = list(verdict["problems"])
        if any(preconditions.values()):
            problems.append(f"precondition held on a registered cell: {preconditions}")
        if not layout_ok:
            problems.append("rebuilt layouts.int16.bin differs from the registered file_sha256")
        cells[label] = {
            "ok": not problems,
            "problems": problems,
            "variant": cell.variant,
            "unique_selected_slots": mine["layouts"]["meta"]["unique_selected_slots"],
            "precondition_holds": preconditions,
            "layout_file_sha256": registered["layouts"]["file_sha256"],
            "layout_file_sha256_equal": layout_ok,
            "fields_excluded": verdict["fields_excluded"],
            "seconds": time.monotonic() - started,
        }
    return {"ok": all(c["ok"] for c in cells.values()), "cells": cells}


def check_analysis_reproduction(
    eval_run: Path, sim_run: Path, registered_dir: Path
) -> dict[str, Any]:
    """The supplement's loader + the frozen ``analyse`` on the 55 registered records reproduce the
    registered analysis.json (minus dry_run/inputs) and the three CSVs exactly."""
    cells, missing = analysis.load_cell_data(eval_run, sim_run, None)
    result = an.analyse(cells, missing)
    new = _norm(an.jsonable(result))
    registered = read_json(registered_dir / "analysis.json")
    diffs = analysis.diff_paths(
        {k: v for k, v in registered.items() if k not in ("dry_run", "inputs")}, new
    )
    texts = {
        "scorecard.csv": analysis.csv_text(
            "scorecard.csv", *an.scorecard_rows(an.clean_scorecard_source(result))
        ),
        "cells.csv": analysis.csv_text("cells.csv", *an.cells_rows(cells)),
        "pairs.csv": analysis.csv_text("pairs.csv", *an.pairs_rows(cells)),
    }
    csv_equal = {n: (registered_dir / n).read_text(encoding="utf-8") == t for n, t in texts.items()}
    return {
        "ok": not diffs and all(csv_equal.values()) and len(cells) == 55 and len(missing) == 5,
        "cells": len(cells),
        "missing": [m["label"] for m in missing],
        "analysis_json_differences": [".".join(map(str, p)) for p in diffs[:20]],
        "csv_byte_equal": csv_equal,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m supplements.p8s.preflight")
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--experiments-root", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = args.experiments_root or common.default_experiments_root()
    eval_run, sim_run = root / common.EVAL_RUN_NAME, root / common.SIM_RUN_NAME
    registered_dir = common.ROOT / "results/p8-2026-11-14/analysis" / common.ANALYSIS_RUN_NAME
    out_dir = args.out_dir or common.ROOT / common.RESULTS_DIR / "preflight"
    out_dir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    configure_deterministic_cpu()
    started = time.monotonic()
    record: dict[str, Any] = {
        "schema": "P8SUP-preflight-v1",
        "label": common.SUPPLEMENT_LABEL,
        "status": "self-check; not independent review, not Astra validation, not human approval",
        "utc": utc_now(),
        "commands": [
            "uv run --locked python -m supplements.p8s.preflight " + " ".join(argv or sys.argv[1:])
        ],
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "head": common.git_text(common.ROOT, "rev-parse", "HEAD"),
        },
        "inputs": {
            "eval_run": str(eval_run),
            "registered_sim_run": str(sim_run),
            "registered_analysis": str(registered_dir),
            "adr0016_sha256": common.supplement_spec_sha256(),
            "supplement_source_sha256": common.supplement_source_digest(),
            "supplement_source_files": common.supplement_source_hashes(),
        },
        "checks": {},
    }
    steps: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
        ("frozen_material", lambda: check_frozen(common.ROOT, eval_run, sim_run)),
        ("trace_verification", lambda: check_traces(eval_run)),
        (
            "layout_equality_five_cells",
            lambda: check_layout_equality(eval_run, sim_run, args.scratch),
        ),
        ("replay_registered_cells", lambda: check_replay(eval_run, sim_run, args.scratch)),
        (
            "analysis_reproduction_55_cells",
            lambda: check_analysis_reproduction(eval_run, sim_run, registered_dir),
        ),
    )
    for name, step in steps:
        t0 = time.monotonic()
        try:
            result = step()
        except Exception as exc:  # noqa: BLE001 - a failed check is recorded, never hidden
            result = {"ok": False, "exception": f"{type(exc).__name__}: {exc}"}
        result["seconds"] = time.monotonic() - t0
        record["checks"][name] = result
        print(
            f"{name}: {'PASS' if result['ok'] else 'FAIL'} ({result['seconds']:.1f} s)", flush=True
        )
    record["overall"] = "PASS" if all(c["ok"] for c in record["checks"].values()) else "FAIL"
    record["wall_seconds"] = time.monotonic() - started
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = out_dir / f"preflight-{stamp}.json"
    target.write_text(
        json.dumps(record, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"overall: {record['overall']}\nrecord: {target}")
    return 0 if record["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
