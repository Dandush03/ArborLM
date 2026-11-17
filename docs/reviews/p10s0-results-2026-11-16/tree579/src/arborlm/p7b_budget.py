"""P7-B mandatory timed dry run (ADR-0014 section 11): the complete configuration set on full-size
synthetic traces for one flat and one tree checkpoint, projected to 81 checkpoints against each cap.

Everything here is synthetic and measured wall time on this machine; projections multiply by the
registered checkpoint counts. The one model-dependent part (tracing stream B through the real
checkpoints) cannot be timed without running a model; it is projected from supplied measurements
of a bitwise replay (``--replay-seconds``, ``--load-seconds`` from ``loader-smoke``) or, if absent,
from P7-A's recorded trace stage (analytical scaling, labelled). Nothing is written to
``experiments/`` or ``results/``. Status: implementation self-check only.
"""

import argparse
import copy
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from . import p7a_core as a_core
from . import p7b_core as core
from . import p7b_layout as layout_mod
from . import p7b_sim as sim
from .io import canonical_json
from .p7a_trace import synthetic_trace
from .p7b_workers import calibration_transfer_runs, split_half_runs, verify_layouts

P7A_TRACE_ACTIVE_SECONDS = 135.27083324996056  # results/p7a-2026-11-13/trace/*/result.json
MARGIN_REQUIRED = 2.0


def _peak() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def time_panel_ranking() -> float:
    import random

    from .p7b_panel import PANEL_SIZE, TRAIN_RANKED, _bytes
    from .pilot_data import select

    generator = random.Random(1)
    train = [generator.randbytes(135).hex() for _ in range(36718)]
    validation = [generator.randbytes(160).hex() for _ in range(3760)]
    start = time.monotonic()
    _, full_train, _ = select(train, "train", TRAIN_RANKED)
    ranked, _, _ = select(validation, "validation", 6 * PANEL_SIZE, excluded=full_train)
    _bytes(ranked)
    return time.monotonic() - start


def startup_seconds() -> float:
    start = time.monotonic()
    subprocess.run(
        [sys.executable, "-c", "import arborlm.p7b_workers, arborlm.p7b_study"],
        check=True,
        capture_output=True,
    )
    return time.monotonic() - start


def budget(args: argparse.Namespace) -> int:
    from .p7b_analysis import analyze_streams

    report: dict[str, Any] = {
        "command": "budget",
        "label": "measured wall time on full-size synthetic traces (hypothetical concentration: "
        "Zipf over 400 hot slots, trees restricted to two branches); projections multiply by the "
        "registered checkpoint counts",
        "queries": core.QUERIES,
        "caps_seconds": {
            "layouts": core.LAYOUT_CAP,
            "panel_and_trace_b": core.TRACE_B_CAP,
            "simulate_each_stream": core.SIM_CAP,
            "analysis": core.ANALYSIS_CAP,
            "study_total": core.STUDY_CAP,
        },
    }
    per: dict[str, dict[str, float]] = {}
    sim_records: dict[str, dict[str, Any]] = {}
    layout_records: dict[str, dict[str, Any]] = {}
    start_up = startup_seconds()
    report["worker_startup_seconds_measured"] = start_up
    with tempfile.TemporaryDirectory(prefix="p7b-budget-") as scratch:
        root = Path(scratch)
        for kind, label, seed in (
            (core.FLAT, "b101-o301-flat-s501", 7001),
            ("fixed_tree", "b101-o301-fixed_tree-s501", 7002),
        ):
            pair, _ = core.parse_label(label)
            index = core.cell_index(pair, kind)
            t: dict[str, float] = {}
            evaluation, eval_branches = synthetic_trace(kind, seed)
            calibration, cal_branches = synthetic_trace(kind, seed + 1000)
            cal = layout_mod.CalibrationTrace.declared(calibration, cal_branches, kind, label)
            t0 = time.monotonic()
            built, meta = layout_mod.build_layouts(cal)
            t["layout_build"] = time.monotonic() - t0
            t0 = time.monotonic()
            index_entries = layout_mod.write_layout_file(root / f"{label}.bin", built)
            table = layout_mod.hash_table(built)
            t["layout_write_and_hash"] = time.monotonic() - t0
            t0 = time.monotonic()
            transfer = calibration_transfer_runs(cal.selected, built)
            t["calibration_transfer"] = time.monotonic() - t0
            t0 = time.monotonic()
            split = split_half_runs(cal)
            t["split_half"] = time.monotonic() - t0
            t["layout_stage_total"] = (
                t["layout_build"]
                + t["layout_write_and_hash"]
                + t["calibration_transfer"]
                + t["split_half"]
            )
            layout_records[label] = {
                "calibration_transfer": transfer,
                "split_half": split,
                "outcome": "completed",
            }
            # trace-b non-model work: integrity, files, counts hash and three null streams
            t0 = time.monotonic()
            a_core.check_trace(evaluation, eval_branches, kind, queries=core.QUERIES)
            a_core.write_trace(root / "tb" / label, "streamB", evaluation, eval_branches)
            counts = a_core.selection_counts(evaluation)
            core.counts_sha256(counts)
            nulls, _ = core.null_streams(counts, core.STREAM_B_NULL_SEEDS, index)
            t["trace_b_non_model"] = time.monotonic() - t0
            # simulate: read + verify layouts, nulls, the complete plan
            t0 = time.monotonic()
            orders = layout_mod.read_layout_file(root / f"{label}.bin", index_entries)
            verify_layouts(label, orders, {label: table})
            nulls2, _ = core.null_streams(counts, core.STREAM_A_NULL_SEEDS, index)
            t["simulate_setup"] = time.monotonic() - t0
            t0 = time.monotonic()
            record = sim.simulate_checkpoint(
                trace=sim.EvaluationTrace(evaluation, eval_branches, kind, label, "A"),
                layouts=sim.LayoutSet(orders),
                null_selected=dict(zip(core.STREAMS_NULL, nulls2, strict=True)),
            )
            t["simulate_plan"] = time.monotonic() - t0
            t["simulate_total"] = t["simulate_setup"] + t["simulate_plan"]
            per[kind] = t
            sim_records[kind] = {"outcome": "completed", "label": label, "record": record}
            report[kind] = {
                "plan": sim.plan_size(kind),
                "layout_builds": sum(1 for b in built if b.rows is not None),
                "layouts_total_entries": len(built),
                "unique_selected_slots_calibration": meta["unique_selected_slots"],
                "max_refinement_passes": max(b.info.get("passes", 0) for b in built),
                "seconds": t,
            }
            del nulls
    flat, tree = per[core.FLAT], per["fixed_tree"]

    def project(key: str, extra: float = 0.0) -> float:
        return 27 * flat[key] + 54 * tree[key] + 81 * extra

    layouts_total = project("layout_stage_total", start_up)
    panel_seconds = time_panel_ranking()
    replay = args.replay_seconds
    load = args.load_seconds
    if replay is not None and load is not None:
        model = 81 * 4 * replay + 27 * load
        model_label = "measured per-replay and per-pair-load seconds (loader-smoke), 4 passes each"
    else:
        model = P7A_TRACE_ACTIVE_SECONDS * 4 / 3
        model_label = (
            "analytical: P7-A's recorded trace stage (135.3 s for 3 passes) scaled by 4/3 for the "
            "extra stream-B pass; hypothetical until measured"
        )
    trace_b_total = panel_seconds + project("trace_b_non_model", start_up) + model
    sim_total = project("simulate_total", start_up)
    # analysis on 81 replicated records per stream
    streams: dict[str, dict[str, dict[str, Any]]] = {"A": {}, "B": {}}
    layout_all: dict[str, dict[str, Any]] = {}
    for s in ("A", "B"):
        for n, (pair, kind) in enumerate(core.registered_checkpoints()):
            label = core.cell_label(pair, kind)
            src = sim_records[core.FLAT if kind == core.FLAT else "fixed_tree"]
            rec = copy.copy(src["record"])
            rec["evaluation_counts"] = {
                **rec["evaluation_counts"],
                "entropy_nats": rec["evaluation_counts"]["entropy_nats"] + 0.002 * n,
            }
            streams[s][label] = {"outcome": "completed", "label": label, "record": rec}
            stand_in = "b101-o301-flat-s501" if kind == core.FLAT else "b101-o301-fixed_tree-s501"
            layout_all[label] = layout_records[stand_in]
    t0 = time.monotonic()
    analyze_streams(streams, layout_records=layout_all)
    analysis_seconds = time.monotonic() - t0
    stages = {
        "layouts": (layouts_total, core.LAYOUT_CAP),
        "panel_and_trace_b": (trace_b_total, core.TRACE_B_CAP),
        "simulate_stream_A": (sim_total, core.SIM_CAP),
        "simulate_stream_B": (sim_total, core.SIM_CAP),
        "analysis": (analysis_seconds, core.ANALYSIS_CAP),
    }
    total = sum(v[0] for v in stages.values())
    report["projection_seconds_81_checkpoints"] = {
        k: {
            "projected": v[0],
            "cap": v[1],
            "margin": v[1] / v[0],
            "twofold_margin_met": v[1] / v[0] >= MARGIN_REQUIRED,
        }
        for k, v in stages.items()
    }
    report["projection_seconds_81_checkpoints"]["study_total"] = {
        "projected": total,
        "cap": core.STUDY_CAP,
        "margin": core.STUDY_CAP / total,
        "twofold_margin_met": core.STUDY_CAP / total >= MARGIN_REQUIRED,
    }
    report["panel_reconstruction_seconds_measured_on_synthetic_registered_scale_corpus"] = (
        panel_seconds
    )
    report["trace_b_model_part"] = {"projected_seconds": model, "basis": model_label}
    report["analysis_seconds_measured_on_81_replicated_records_per_stream"] = analysis_seconds
    report["peak_rss_bytes_ru_maxrss"] = _peak()
    report["all_twofold_margins_met"] = all(
        v["twofold_margin_met"] for v in report["projection_seconds_81_checkpoints"].values()
    )
    print(canonical_json(report).decode().strip())
    return 0 if report["all_twofold_margins_met"] else 1
