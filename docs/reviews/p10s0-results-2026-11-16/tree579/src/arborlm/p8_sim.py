# ruff: noqa: E501
"""P8 stage "simulate": layouts from the calibration trace only, then page-miss simulation of both
panels (ADR-0015 sections 7.1 and 10.7).

Everything about layouts and the page model is ADR-0014's, unchanged and called by import:
``p7b_layout`` (``pair_affinity``, ``coax_pages``, ``group_coax_pages``, ``partition_groups``,
``branch_groups``, ``layout_from_pages``), ``p7a_core`` (``layout_freq``, ``frequency_matched_detail``,
``query_order``), ``p7b_sim`` (``page_sets``, ``simulate_group`` -> ``lru_pass`` / ``cache_counts``)
and ``p7b_core.canonical_hash``. P8 only chooses which of those to run: L-ID, L-FREQ, L-COAX, L-BCOAX
(trees), L-PCOAX-1..5 at R in {2, 8} (primary R = 2 / C = 32, confirmation R = 8 / C = 8), both
eviction tie rules, on the actual trace and the three count-preserving nulls (seeds 91331-91333 for
Panel A, 91341-91343 for Panel B, generator seed ``s * 1000 + cell.index``) under L-FREQ and L-COAX,
and on the order-shuffled trace (``p7a_core.query_order``, seed 91201) under L-FREQ and L-COAX.

m = warm capacity misses per query = (misses_warm - first_touch_warm) / 16,384 counted queries; the
raw integer counts are recorded for every (panel, setting, tie, layout, stream).

Layout builders take a ``p7b_layout.CalibrationTrace`` only (``require_calibration``); the simulator
takes an ``EvaluationTrace``. A panel trace cannot be passed as layout input (TypeError).

Hard-trace statistics (ADR-0015 7.1): temporal reuse and (trees) branch persistence.

CLI::

    python -m arborlm.p8_sim simulate --eval-run E --out-root O [--reproduction-record F]
    python -m arborlm.p8_sim simulate --dry-run --eval-run DRY_EVAL --out-root O
    python -m arborlm.p8_sim p7b-reproduction --experiments-root X [--repo R] --out F

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import json
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7a_core as a_core
from . import p7b_core as b_core
from . import p7b_layout as layout_mod
from . import p7b_sim as sim
from . import p8_core as core
from . import p8_pool
from .io import file_sha256, read_json, write_json
from .p7a_trace import configure_deterministic_cpu
from .records import allocate_run, utc_now

SCHEMA_SIM = "P8-sim-v1"
SCHEMA_SIM_STAGE = "P8-sim-stage-v1"
SCHEMA_REPRO = "P8-p7b-reproduction-v1"
SIM_PREFIX, SIM_PREFIX_DRY = "P8S", "P8SD"
ROWS = tuple(r for r, _ in core.CRITERION_SETTINGS)  # (2, 8)
CAP_FOR_ROWS = dict(core.CRITERION_SETTINGS)  # {2: 32, 8: 8}
PANEL_SEEDS = {"A": core.PANEL_A_NULL_SEEDS, "B": core.PANEL_B_NULL_SEEDS}
COUNT_KEYS = sim.COUNT_KEYS
REPRO_LABELS = ("b101-o301-flat-s501", "b101-o301-learned_tree-s501")


def is_tree(kind: str) -> bool:
    return kind != "flat"


def actual_layouts(kind: str) -> tuple[str, ...]:
    base = (b_core.L_ID, b_core.L_FREQ, b_core.L_COAX)
    return (*base, b_core.L_BCOAX, *b_core.L_PCOAX) if is_tree(kind) else (*base, *b_core.L_PCOAX)


NULL_LAYOUTS = (b_core.L_FREQ, b_core.L_COAX)  # nulls and the order-shuffled trace
ORDER_LAYOUTS = (b_core.L_FREQ, b_core.L_COAX)


# --- layouts: calibration only ---------------------------------------------------------------------
def build_p8_layouts(
    calibration: layout_mod.CalibrationTrace, rows_list: tuple[int, ...] = ROWS
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    """The ADR-0014 constructions, unchanged, for the P8 layout set. Returns ``(orders, meta)``;
    ``orders`` maps ``name`` (R-independent) or ``name|R<rows>`` to the slot at each position.
    ``calibration`` must be a ``CalibrationTrace`` (``TypeError`` otherwise)."""
    cal = layout_mod.require_calibration(calibration)
    tree = is_tree(cal.kind)
    counts = cal.counts()
    positions = a_core.layout_freq(counts)
    freq_order = [0] * core.SLOTS
    for slot, position in enumerate(positions):
        freq_order[position] = slot
    orders: dict[str, list[int]] = {
        b_core.L_ID: list(range(core.SLOTS)),
        b_core.L_FREQ: freq_order,
    }
    adj = layout_mod.pair_affinity(cal.selected)
    branches = layout_mod.branch_groups()
    partitions = {
        name: layout_mod.partition_groups(seed)
        for name, seed in zip(b_core.L_PCOAX, core.PARTITION_SEEDS, strict=True)
    }
    infos: dict[str, Any] = {}
    for rows in rows_list:
        plan: list[tuple[str, Any]] = [(b_core.L_COAX, None)]
        plan += [(name, groups) for name, groups in partitions.items()]
        if tree:
            plan.append((b_core.L_BCOAX, branches))
        for name, groups in plan:
            if groups is None:
                pages, info = layout_mod.coax_pages(rows, counts, adj, refine=True)
            else:
                pages, info = layout_mod.group_coax_pages(groups, rows, counts, adj, refine=True)
            built = layout_mod.BuiltLayout(name, rows, layout_mod.layout_from_pages(pages), info)
            layout_mod._check_layout(built, groups)
            orders[built.key()] = built.order
            infos[built.key()] = info
    meta = {
        "calibration_counts_sha256": b_core.counts_sha256(counts),
        "unique_selected_slots": sum(1 for c in counts if c),
        "affinity_nonzero_entries": sum(len(r) for r in adj.values()),
        "refinement": infos,
        "built_from": "calibration trace only (CalibrationTrace)",
    }
    return orders, meta


def layout_hashes(orders: dict[str, list[int]]) -> dict[str, str]:
    """Canonical hash (ADR-0014 section 4) of every layout at every R it is used at."""
    table: dict[str, str] = {}
    for key, order in orders.items():
        name, _, rows = key.partition("|R")
        if rows:
            table[key] = b_core.canonical_hash(order, int(rows))
        else:
            for r in ROWS:
                table[b_core.layout_key(name, r)] = b_core.canonical_hash(order, r)
    return table


# --- simulation of one trace ------------------------------------------------------------------------
def simulate_trace(
    trace: sim.EvaluationTrace,
    orders: dict[str, list[int]],
    nulls: dict[str, Tensor],
    *,
    layouts: tuple[str, ...] | None = None,
    rows_list: tuple[int, ...] = ROWS,
    deadline: float | None = None,
) -> dict[str, Any]:
    """The P8 plan for one evaluation trace: ``actual`` under every layout, ``order_shuffled`` and the
    nulls under L-FREQ and L-COAX; at each (R, C) both tie rules."""
    if not isinstance(trace, sim.EvaluationTrace):
        raise TypeError("simulate_trace needs an EvaluationTrace")
    kind = trace.kind
    layout_set = sim.LayoutSet(orders)
    names = layouts if layouts is not None else actual_layouts(kind)
    n = int(trace.selected.shape[0])
    reorder = a_core.query_order(a_core.STREAM_ORDER, n)
    streams: dict[str, dict[str, Any]] = {s: {} for s in b_core.STREAMS_ALL}
    for rows in rows_list:
        cap = CAP_FOR_ROWS[rows]
        for name in names:
            if deadline is not None and time.monotonic() > deadline:
                raise sim.CapExceeded("simulation deadline passed")
            positions = layout_set.positions(name, rows)
            base = sim.page_sets(positions, rows, trace.selected)
            key = b_core.layout_key(name, rows)
            streams[b_core.STREAM_ACTUAL][key] = sim.simulate_group(
                base, (cap,), (cap,), f"actual|{key}"
            )
            if name in ORDER_LAYOUTS:
                shuffled = [base[i] for i in reorder]
                streams[b_core.STREAM_ORDER][key] = sim.simulate_group(
                    shuffled, (cap,), (cap,), f"order_shuffled|{key}"
                )
            if name in NULL_LAYOUTS:
                for stream, selected in nulls.items():
                    queries = sim.page_sets(positions, rows, selected)
                    streams[stream][key] = sim.simulate_group(
                        queries, (cap,), (cap,), f"{stream}|{key}"
                    )
    counts = torch.bincount(trace.selected.flatten(), minlength=core.SLOTS).tolist()
    return {
        "kind": kind,
        "label": trace.label,
        "stream": trace.stream,
        "queries": n,
        "evaluation_counts": sim.effective_record(counts),
        "streams": streams,
    }


def counted_queries(queries: int) -> int:
    return queries - queries // 2


def m_fraction(record: dict[str, Any], stream: str, layout: str, rows: int, tie: str) -> Fraction:
    """Warm capacity misses per query of one simulated configuration, exactly."""
    counts = record["streams"][stream][b_core.layout_key(layout, rows)]["by_c"][
        str(CAP_FOR_ROWS[rows])
    ][tie]
    return Fraction(
        counts["misses_warm"] - counts["first_touch_warm"], counted_queries(int(record["queries"]))
    )


# --- hard-trace statistics ------------------------------------------------------------------------
def temporal_reuse(selected: Tensor, window: int = core.TEMPORAL_WINDOW_QUERIES) -> dict[str, Any]:
    """Fraction of a query's 8 selected slots that were selected in the previous up-to-``window``
    queries of the same 64-query context, positions >= 1; mean over those queries. Exact: every query
    has 8 slots, so the mean of fractions is ``hits / (8 * queries)``."""
    rows = selected.to(torch.int64).tolist()
    n = len(rows)
    if n % core.CONTEXT:
        raise ValueError("a stream must hold whole 64-query contexts")
    hits = 0
    counted = 0
    for base in range(0, n, core.CONTEXT):
        for t in range(1, core.CONTEXT):
            previous: set[int] = set()
            for u in range(max(0, t - window), t):
                previous.update(rows[base + u])
            hits += sum(1 for slot in rows[base + t] if slot in previous)
            counted += 1
    top = len(rows[0])
    return {
        "hits": hits,
        "queries_counted": counted,
        "slots_per_query": top,
        "value": hits / (top * counted),
        "window": window,
    }


def branch_persistence(branches: Tensor, order: list[int] | None = None) -> dict[str, Any]:
    """Fraction of consecutive in-context query pairs (t-1, t), t >= 1, with the same top branch
    (first column of the stable-top branch IDs) and with the same visited pair as a set. ``order``
    optionally gives the stream as indices into ``branches`` (the order-shuffled construction)."""
    rows = branches.to(torch.int64).tolist()
    if order is not None:
        rows = [rows[i] for i in order]
    n = len(rows)
    if n % core.CONTEXT:
        raise ValueError("a stream must hold whole 64-query contexts")
    same_top = same_pair = pairs = 0
    for base in range(0, n, core.CONTEXT):
        for t in range(1, core.CONTEXT):
            previous, current = rows[base + t - 1], rows[base + t]
            pairs += 1
            same_top += previous[0] == current[0]
            same_pair += set(previous) == set(current)
    return {
        "pairs": pairs,
        "same_top": same_top,
        "same_pair": same_pair,
        "top_fraction": same_top / pairs,
        "pair_fraction": same_pair / pairs,
    }


# --- one cell, one panel ----------------------------------------------------------------------------
def simulate_panel(
    cell: core.Cell,
    panel: str,
    selected: Tensor,
    branches: Tensor | None,
    orders: dict[str, list[int]],
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    kind = cell.variant
    trace = sim.EvaluationTrace(selected, branches, kind, cell.label, panel)
    counts = a_core.selection_counts(selected)
    seeds = PANEL_SEEDS[panel]
    null_list, null_info = b_core.null_streams(counts, seeds, cell.index)
    nulls = dict(zip(b_core.STREAMS_NULL, null_list, strict=True))
    record = simulate_trace(trace, orders, nulls, deadline=deadline)
    reorder = a_core.query_order(a_core.STREAM_ORDER, int(selected.shape[0]))
    reuse = {
        "actual": temporal_reuse(selected),
        "order_shuffled": temporal_reuse(selected[torch.tensor(reorder, dtype=torch.int64)]),
        **{name: temporal_reuse(stream) for name, stream in nulls.items()},
    }
    record["null_streams"] = [
        {k: d[k] for k in ("replicate_seed", "generator_seed", "stream_sha256")} for d in null_info
    ]
    record["temporal_reuse"] = reuse
    record["branch_persistence"] = (
        None
        if branches is None
        else {
            "actual": branch_persistence(branches),
            "order_shuffled": branch_persistence(branches, reorder),
        }
    )
    return record


def load_trace(
    cell_dir: Path, eval_record: dict[str, Any], name: str
) -> tuple[Tensor, Tensor | None]:
    entry = eval_record["traces"][name]
    selected, branches = a_core.read_trace(cell_dir, entry["prefix"], entry["files"])
    a_core.check_trace(selected, branches, eval_record["variant"], queries=core.EVAL_QUERIES)
    if (
        b_core.counts_sha256(a_core.selection_counts(selected))
        != (entry["utilization"]["counts_sha256"])
    ):
        raise b_core.StopError(f"{eval_record['label']}: {name} trace counts differ from eval.json")
    return selected, branches


def simulate_cell(
    cell: core.Cell, cell_dir: Path, out_dir: Path, *, deadline: float | None = None
) -> dict[str, Any]:
    started = time.monotonic()
    eval_path = cell_dir / "eval.json"
    eval_record = read_json(eval_path)
    if eval_record.get("outcome") != "completed" or eval_record["label"] != cell.label:
        raise b_core.StopError(f"{cell.label}: eval.json is not a completed record of this cell")
    if eval_record.get("source_sha256") != core.source_digest():
        raise b_core.StopError(f"{cell.label}: eval.json was produced by different source files")
    # layouts: the calibration trace only
    cal_selected, cal_branches = load_trace(cell_dir, eval_record, "calibration")
    calibration = layout_mod.CalibrationTrace.declared(
        cal_selected, cal_branches, cell.variant, cell.label
    )
    layout_mod.verify_partitions()
    t0 = time.monotonic()
    orders, meta = build_p8_layouts(calibration)
    build_seconds = time.monotonic() - t0
    hashes = layout_hashes(orders)
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
    seconds: dict[str, float] = {"layouts": build_seconds}
    for panel in ("A", "B"):
        t0 = time.monotonic()
        selected, branches = load_trace(cell_dir, eval_record, panel)
        panels[panel] = simulate_panel(cell, panel, selected, branches, orders, deadline=deadline)
        panels[panel]["trace_files"] = eval_record["traces"][panel]["files"]
        seconds[f"panel_{panel}"] = time.monotonic() - t0
    return {
        "schema": SCHEMA_SIM,
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
        "seconds": {**seconds, "total": time.monotonic() - started},
    }


def worker_main(job_path: Path) -> int:
    job = read_json(job_path)
    configure_deterministic_cpu()
    cell = core.parse_label(job["label"])
    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record = simulate_cell(
        cell,
        Path(job["eval_cell_dir"]),
        out_dir,
        deadline=started + max(float(job["stage_deadline_epoch"]) - time.time(), 1.0),
    )
    record.update(
        {
            "dry_run": bool(job["dry_run"]),
            "source_sha256": core.source_digest(),
            "spec_sha256": core.spec_sha256(),
            "reproduction_record_sha256": job.get("reproduction_record_sha256"),
            "determinism": p8_pool.determinism(),
            "worker_seconds": time.monotonic() - started,
            "peak_rss_bytes_ru_maxrss": p8_pool.peak_rss_bytes(),
        }
    )
    write_json(out_dir / "sim.json", record)
    return 0


# --- stage -------------------------------------------------------------------------------------------
def check_reproduction_record(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if (
        data.get("schema") != SCHEMA_REPRO
        or data.get("verdict") != "ALL_EQUAL"
        or data.get("source_sha256") != core.source_digest()
    ):
        raise b_core.GateError(
            "refused: the p7b-reproduction record is missing, not ALL_EQUAL, or was produced by "
            "different source files"
        )
    return {"file": str(path), "sha256": file_sha256(path)}


def run_stage(
    eval_run: Path,
    *,
    out_root: Path,
    dry_run: bool,
    labels: list[str] | None = None,
    reproduction_record: Path | None = None,
    freeze_commit: str | None = None,
    workers: int = core.WORKERS,
    cap_seconds: float = core.SIM_CAP,
) -> Path:
    gate: dict[str, Any] | None = None
    freeze = p8_pool.require_freeze(dry_run, freeze_commit)
    if not dry_run:
        if reproduction_record is None:
            raise b_core.GateError("refused: a registered simulation needs --reproduction-record")
        gate = check_reproduction_record(reproduction_record)
    eval_manifest = read_json(eval_run / "manifest.json")
    if bool(eval_manifest["dry_run"]) != dry_run:
        raise b_core.GateError("refused: dry-run flag differs from the evaluation run's")
    if freeze is not None:
        theirs = (eval_manifest.get("freeze") or {}).get("freeze_commit")
        if theirs != freeze["freeze_commit"]:
            raise b_core.GateError(
                "refused: the evaluation run's freeze commit differs from this one"
            )
        if eval_manifest["source_sha256"] != core.source_digest():
            raise b_core.GateError("refused: the evaluation run used different source files")
    chosen = labels or core.all_labels()
    run = allocate_run(out_root, prefix=SIM_PREFIX_DRY if dry_run else SIM_PREFIX)
    jobs: list[p8_pool.Job] = []
    missing: list[str] = []
    for label in chosen:
        eval_cell = eval_run / "cells" / label
        if not (eval_cell / "eval.json").is_file():
            missing.append(label)
            continue
        out_dir = run / "cells" / label
        out_dir.mkdir(parents=True)
        write_json(
            out_dir / "job.json",
            {
                "label": label,
                "eval_cell_dir": str(eval_cell),
                "out_dir": str(out_dir),
                "dry_run": dry_run,
                "stage_deadline_epoch": time.time() + cap_seconds,
                "reproduction_record_sha256": gate["sha256"] if gate else None,
            },
        )
        jobs.append(
            p8_pool.Job(
                label,
                [sys.executable, "-m", "arborlm.p8_sim", "_worker", str(out_dir / "job.json")],
                out_dir / "sim.json",
                out_dir / "sim.failed.json",
                out_dir / "worker.log",
            )
        )
    started = utc_now()
    result = p8_pool.run_pool(jobs, workers=workers, cap_seconds=cap_seconds)
    completed = sum(1 for o in result.outcomes if o.status == "completed")
    write_json(
        run / "manifest.json",
        {
            "schema": SCHEMA_SIM_STAGE,
            "family": core.FAMILY,
            "dry_run": dry_run,
            "spec_sha256": core.spec_sha256(),
            "source_sha256": core.source_digest(),
            "eval_run": str(eval_run),
            "eval_manifest_sha256": file_sha256(eval_run / "manifest.json"),
            "reproduction_gate": gate,
            "freeze": freeze,
            "labels": chosen,
            "cells_expected": len(chosen),
            "cells_completed": completed,
            "missing_eval_records": missing,
            "outcomes": [o.__dict__ for o in result.outcomes],
            "started_utc": started,
            "finished_utc": utc_now(),
            "wall_seconds": result.wall_seconds,
            "cap_seconds": cap_seconds,
            "cap_hit": result.cap_hit,
            "workers": workers,
            "peak_aggregate_rss_bytes": result.peak_aggregate_rss_bytes,
            "peak_worker_rss_bytes": max((o.peak_rss_bytes for o in result.outcomes), default=0),
            "status": "completed" if completed == len(chosen) and not missing else "INCOMPLETE",
        },
    )
    return run


# --- the P7-B reproduction gate (ADR-0015 section 10.7) ---------------------------------------------
def p7b_reproduction(
    experiments_root: Path, repo: Path, labels: tuple[str, ...] = REPRO_LABELS
) -> dict[str, Any]:
    """Run the P8 layout + simulation path on one P5 checkpoint's existing P7-A calibration trace and
    stream-A trace and compare every miss count with P7-B's recorded stream-A simulation (L-ID,
    L-FREQ, L-COAX, L-BCOAX for the tree, L-PCOAX-1..5; actual, order-shuffled and the three stream-A
    nulls; both settings, both tie rules). Stream A is P5's already-published panel."""
    identity = b_core.load_identity(
        experiments_root.parent, repo / b_core.IDENTITY_MANIFEST, list(b_core.all_labels())
    )
    if identity.data["overall_hash"]["sha256"] != b_core.IDENTITY_OVERALL_SHA256:
        raise b_core.StopError("identity manifest overall hash differs from the registered one")
    sim_runs = sorted((repo / b_core.DEFAULT_RESULTS / "simulate-a").glob("*/workers"))
    layout_runs = sorted((repo / b_core.DEFAULT_RESULTS / "layouts").glob("*/workers"))
    if len(sim_runs) != 1 or len(layout_runs) != 1:
        raise b_core.StopError("expected exactly one P7-B stream-A simulation and layout run")
    out: dict[str, Any] = {"labels": {}}
    all_equal = True
    for label in labels:
        pair, kind = b_core.parse_label(label)
        index = b_core.cell_index(pair, kind)
        reference = read_json(sim_runs[0] / f"{label}.result.json")["record"]
        layout_record = read_json(layout_runs[0] / f"{label}.result.json")
        cal = layout_mod.CalibrationTrace.from_identity(identity, label)
        orders, meta = build_p8_layouts(cal)
        hashes = layout_hashes(orders)
        hash_diffs = [k for k, h in hashes.items() if layout_record["hash_table"].get(k) != h]
        directory, files = identity.trace_record(label, "evaluation")
        selected, branches = a_core.read_trace(directory, "eval", files)
        a_core.check_trace(selected, branches, kind, queries=int(selected.shape[0]))
        counts = a_core.selection_counts(selected)
        nulls, _ = b_core.null_streams(counts, b_core.STREAM_A_NULL_SEEDS, index)
        trace = sim.EvaluationTrace(selected, branches, kind, label, "A")
        mine = simulate_trace(trace, orders, dict(zip(b_core.STREAMS_NULL, nulls, strict=True)))
        compared = 0
        diffs: list[str] = []
        skipped: list[str] = []
        table: dict[str, Any] = {}
        for stream, groups in mine["streams"].items():
            for key, group in groups.items():
                theirs = reference["streams"][stream][key]
                if group["stats"] != theirs["stats"]:
                    diffs.append(f"{stream}|{key}|stats")
                for cap, ties in group["by_c"].items():
                    for tie, counts_mine in ties.items():
                        counts_ref = theirs["by_c"][cap].get(tie)
                        if counts_ref is None:  # P7-B did not run this tie rule on this group
                            skipped.append(f"{stream}|{key}|C{cap}|{tie}")
                            continue
                        compared += 1
                        if any(counts_mine[k] != counts_ref[k] for k in COUNT_KEYS) or (
                            counts_mine["ctx_q"] != counts_ref["ctx_q"]
                        ):
                            diffs.append(f"{stream}|{key}|C{cap}|{tie}")
        for name in (b_core.L_FREQ, b_core.L_COAX, *((b_core.L_BCOAX,) if is_tree(kind) else ())):
            for rows in ROWS:
                for tie in core.TIES:
                    mine_m = m_fraction(mine, "actual", name, rows, tie)
                    ref_m = m_fraction(reference, "actual", name, rows, tie)
                    table[f"{name}|R{rows}|C{CAP_FOR_ROWS[rows]}|{tie}"] = {
                        "p8_m": float(mine_m),
                        "p7b_m": float(ref_m),
                        "p8_m_exact": f"{mine_m.numerator}/{mine_m.denominator}",
                        "p7b_m_exact": f"{ref_m.numerator}/{ref_m.denominator}",
                        "equal": mine_m == ref_m,
                    }
        equal = not diffs and not hash_diffs and all(v["equal"] for v in table.values())
        all_equal = all_equal and equal
        out["labels"][label] = {
            "kind": kind,
            "cell_index_for_null_generator": index,
            "configurations_compared": compared,
            "count_differences": diffs,
            "configurations_without_p7b_counterpart": skipped,
            "layout_hashes_compared": len(hashes),
            "layout_hash_differences": hash_diffs,
            "m_table": table,
            "layout_meta_refinement": meta["refinement"],
            "equal": equal,
        }
    return {
        "schema": SCHEMA_REPRO,
        "verdict": "ALL_EQUAL" if all_equal else "DIFFERENT",
        "source_sha256": core.source_digest(),
        "spec_sha256": core.spec_sha256(repo),
        "identity_manifest_sha256": identity.file_sha256,
        "p7b_simulate_a_run": sim_runs[0].parent.name,
        "p7b_layouts_run": layout_runs[0].parent.name,
        "label": "self-check; not independent review, not Astra validation",
        **out,
    }


def main(argv: list[str] | None = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    if args_in and args_in[0] == "_worker":
        return worker_main(Path(args_in[1]))
    parser = argparse.ArgumentParser(prog="python -m arborlm.p8_sim")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("simulate")
    s.add_argument("--eval-run", type=Path, required=True)
    s.add_argument("--out-root", type=Path, required=True)
    s.add_argument("--reproduction-record", type=Path)
    s.add_argument("--freeze-commit")
    s.add_argument("--labels", nargs="*")
    s.add_argument("--workers", type=int, default=core.WORKERS)
    s.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("p7b-reproduction")
    r.add_argument("--experiments-root", type=Path, required=True)
    r.add_argument("--repo", type=Path, default=None)
    r.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(args_in)
    if args.command == "p7b-reproduction":
        configure_deterministic_cpu()
        record = p7b_reproduction(args.experiments_root, args.repo or Path.cwd())
        write_json(args.out, record)
        print(json.dumps({"verdict": record["verdict"], "out": str(args.out)}, indent=2))
        return 0 if record["verdict"] == "ALL_EQUAL" else 1
    try:
        run = run_stage(
            args.eval_run,
            out_root=args.out_root,
            dry_run=args.dry_run,
            labels=args.labels,
            reproduction_record=args.reproduction_record,
            freeze_commit=args.freeze_commit,
            workers=args.workers,
        )
    except b_core.GateError as exc:
        print(f"P8 simulate REFUSED: {exc}", file=sys.stderr)
        return 2
    manifest = read_json(run / "manifest.json")
    keys = ("status", "cells_completed", "cells_expected", "wall_seconds")
    print(json.dumps({k: manifest[k] for k in keys}, indent=2))
    print(f"run directory: {run}")
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
