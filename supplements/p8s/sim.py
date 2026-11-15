# ruff: noqa: E501
"""ADR-0016 section 4: ``simulate_panel`` and ``simulate_cell`` copied from ``arborlm.p8_sim`` with
exactly two differences: they take a null provider, and each recorded null entry keeps ``method``
and ``precondition`` besides the three registered keys. No frozen module is patched.

``simulate_cell_s`` keeps the frozen check that ``eval.json``'s ``source_sha256`` equals the current
``src/arborlm`` digest and does not compare the spec hash. The worker never reads the freeze.
"""

import sys
import time
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm import p7a_core as a_core
from arborlm import p7b_core as b_core
from arborlm import p7b_layout as layout_mod
from arborlm import p7b_sim as sim
from arborlm import p8_core as core
from arborlm import p8_pool, p8_sim
from arborlm.io import file_sha256, read_json, write_json
from arborlm.p7a_trace import configure_deterministic_cpu

from . import common
from .null import NullProvider, detect_single_set, supplement_null_provider

NULL_KEYS = ("replicate_seed", "generator_seed", "stream_sha256", "method", "precondition")


def simulate_panel_s(
    cell: core.Cell,
    panel: str,
    selected: Tensor,
    branches: Tensor | None,
    orders: dict[str, list[int]],
    null_provider: NullProvider,
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    """``p8_sim.simulate_panel`` with the null provider replaced (and ``method``/``precondition``
    kept in the record). Everything else is the frozen function's body."""
    kind = cell.variant
    trace = sim.EvaluationTrace(selected, branches, kind, cell.label, panel)
    seeds = p8_sim.PANEL_SEEDS[panel]
    null_list, null_info = null_provider(selected, seeds, cell.index)
    nulls = dict(zip(b_core.STREAMS_NULL, null_list, strict=True))
    record = p8_sim.simulate_trace(trace, orders, nulls, deadline=deadline)
    reorder = a_core.query_order(a_core.STREAM_ORDER, int(selected.shape[0]))
    reuse = {
        "actual": p8_sim.temporal_reuse(selected),
        "order_shuffled": p8_sim.temporal_reuse(selected[torch.tensor(reorder, dtype=torch.int64)]),
        **{name: p8_sim.temporal_reuse(stream) for name, stream in nulls.items()},
    }
    record["null_streams"] = [{k: d[k] for k in NULL_KEYS} for d in null_info]
    record["temporal_reuse"] = reuse
    record["branch_persistence"] = (
        None
        if branches is None
        else {
            "actual": p8_sim.branch_persistence(branches),
            "order_shuffled": p8_sim.branch_persistence(branches, reorder),
        }
    )
    return record


def simulate_cell_s(
    cell: core.Cell,
    cell_dir: Path,
    out_dir: Path,
    null_provider: NullProvider,
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    """``p8_sim.simulate_cell`` with the null provider replaced; adds
    ``supplement_null_preconditions`` (the detector's result per panel, evaluated on the loaded
    trace rows)."""
    started = time.monotonic()
    eval_path = cell_dir / "eval.json"
    eval_record = read_json(eval_path)
    if eval_record.get("outcome") != "completed" or eval_record["label"] != cell.label:
        raise b_core.StopError(f"{cell.label}: eval.json is not a completed record of this cell")
    if eval_record.get("source_sha256") != core.source_digest():
        raise b_core.StopError(f"{cell.label}: eval.json was produced by different source files")
    # layouts: the calibration trace only
    cal_selected, cal_branches = p8_sim.load_trace(cell_dir, eval_record, "calibration")
    calibration = layout_mod.CalibrationTrace.declared(
        cal_selected, cal_branches, cell.variant, cell.label
    )
    layout_mod.verify_partitions()
    t0 = time.monotonic()
    orders, meta = p8_sim.build_p8_layouts(calibration)
    build_seconds = time.monotonic() - t0
    hashes = p8_sim.layout_hashes(orders)
    index = layout_mod.write_layout_file(
        out_dir / "layouts.int16.bin",
        [
            layout_mod.BuiltLayout(
                key.partition("|R")[0],
                int(key.partition("|R")[2]) if "|R" in key else None,
                order,
            )
            for key, order in orders.items()
        ],
    )
    panels: dict[str, Any] = {}
    preconditions: dict[str, Any] = {}
    seconds: dict[str, float] = {"layouts": build_seconds}
    for panel in ("A", "B"):
        t0 = time.monotonic()
        selected, branches = p8_sim.load_trace(cell_dir, eval_record, panel)
        preconditions[panel] = detect_single_set(selected).as_record()
        panels[panel] = simulate_panel_s(
            cell, panel, selected, branches, orders, null_provider, deadline=deadline
        )
        panels[panel]["trace_files"] = eval_record["traces"][panel]["files"]
        seconds[f"panel_{panel}"] = time.monotonic() - t0
    return {
        "schema": p8_sim.SCHEMA_SIM,
        "outcome": "completed",
        "label": cell.label,
        "cell": cell.fields(),
        "cell_index": cell.index,
        "variant": cell.variant,
        "case": cell.case,
        "eval_json_sha256": file_sha256(eval_path),
        "calibration_files": eval_record["traces"]["calibration"]["files"],
        "layouts": {
            "hash_table": hashes,
            "meta": meta,
            "file": "layouts.int16.bin",
            "file_sha256": file_sha256(out_dir / "layouts.int16.bin"),
            "index": [{k: e[k] for k in ("name", "rows", "entry", "bytes_offset")} for e in index],
            "note": "built from the calibration trace only with ADR-0014's unchanged constructions",
        },
        "settings": [list(s) for s in core.CRITERION_SETTINGS],
        "ties": list(core.TIES),
        "panels": panels,
        "supplement_null_preconditions": preconditions,
        "seconds": {**seconds, "total": time.monotonic() - started},
    }


def build_record(
    cell: core.Cell,
    eval_cell_dir: Path,
    out_dir: Path,
    *,
    freeze: dict[str, str] | None,
    deadline: float | None,
    null_provider: NullProvider = supplement_null_provider,
) -> dict[str, Any]:
    """One supplementary ``sim.json`` record: the simulated cell plus the worker fields of the
    frozen worker that stay truthful (``dry_run``, ``source_sha256`` = the digest computed here,
    ``determinism``, timings, RSS) plus the supplement's own identity. ``spec_sha256`` and
    ``reproduction_record_sha256`` are not written: the supplement computed no registered value."""
    started = time.monotonic()
    record = simulate_cell_s(cell, eval_cell_dir, out_dir, null_provider, deadline=deadline)
    eval_record = read_json(eval_cell_dir / "eval.json")
    record.update(
        {
            "dry_run": False,
            "source_sha256": core.source_digest(),
            "determinism": p8_pool.determinism(),
            "worker_seconds": time.monotonic() - started,
            "peak_rss_bytes_ru_maxrss": p8_pool.peak_rss_bytes(),
            "supplement": "ADR-0016",
            "supplement_label": common.RECORD_LABEL,
            "supplement_spec_sha256": common.supplement_spec_sha256(),
            "supplement_source_sha256": common.supplement_source_digest(),
            "supplement_freeze_commit": freeze,
            "frozen_inputs": common.frozen_inputs(common.ROOT, str(eval_record["spec_sha256"])),
        }
    )
    return record


def worker_main(job_path: Path) -> int:
    job = read_json(job_path)
    configure_deterministic_cpu()
    cell = core.parse_label(job["label"])
    if cell.label not in common.SUPPLEMENT_CELLS:
        raise common.SupplementError(f"{cell.label} is not one of the five supplement cells")
    if job["supplement_spec_sha256"] != common.supplement_spec_sha256():
        raise common.SupplementError("ADR-0016 changed between the stage start and this worker")
    if job["supplement_source_sha256"] != common.supplement_source_digest():
        raise common.SupplementError(
            "supplement code changed between the stage start and the worker"
        )
    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record = build_record(
        cell,
        Path(job["eval_cell_dir"]),
        out_dir,
        freeze=job["supplement_freeze_commit"],
        deadline=started + max(float(job["stage_deadline_epoch"]) - time.time(), 1.0),
    )
    write_json(out_dir / "sim.json", record)
    return 0


if __name__ == "__main__":
    sys.exit(worker_main(Path(sys.argv[1])))
