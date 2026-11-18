# ruff: noqa: E501
"""P10IS5 stages M (the measuring rehearsal) and K (the counting rehearsal) (ADR-0028 sections 5.4, 8, 12; rulings 11, 12, 14).

M runs every stage end to end on R1's rehearsal file in the rehearsal geometry (24 cells x 5 repeats, n(s) = 100, 100, 40, 16; 28 tiles per (repeat, k); 840 of tiles 0 to 895) with M's seeds, on provisional caps, and measures rates, times and
CV_R: the larger of the repeat-to-repeat coefficients of variation (sample standard deviation over mean of the per-repeat medians) of c(1) and c(3) at depth 1. m_t = max(0.10, 2 x CV_R); above 0.30, EQ-B's label is registered
as ENGINEERING NOT EVALUABLE (TIMING SPREAD). A rehearsal made on provisional caps cannot be frozen on.
K runs the same end-to-end run AGAINST THE CANDIDATE PLAN FILE ITSELF on the rehearsal file with K's own seeds, enumerates the registered geometry's passes in RAM (tile counts, no page twice), and writes the rehearsal record
whose candidate section names the plan file's SHA-256. K produces nothing that any frozen file contains. Neither reads the 4 GiB file, which does not exist before E1. Both have five repeats and no spare: an invalid
rehearsal block is recorded, not replaced.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import bench, blocks, core, e2, layout, report
from .plan import Plan

REPEATS_NEEDED = 5
REHEARSAL_STAGES = ("prediction", "harness_figure", "blocks", "analysis", "report", "registered_enumeration")


def cv_r(passes: Sequence[Mapping[str, Any]], blks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """CV_R from stage M: for c(1) and c(3) at depth 1, the sample CV of the per-repeat medians over the repeats whose pass met the counter rule (every one of the five when all did). Repeats whose pass failed the counter rule
    are left out of that cell's CV and listed. Returns None for CV_R when fewer than two repeats are available for a cell."""
    out: dict[str, Any] = {"cells": {}}
    cvs = []
    for s in (1, 3):
        meds = {}
        left_out = []
        for p in passes:
            if p["k"] == 1 and p["s"] == s:
                if p["counter_status"] == "OK":
                    meds[p["repeat"]] = core.median(p["latency_ns"])
                else:
                    left_out.append(p["key"])
        c = core.cv(list(meds.values()))
        enough = len(meds) >= REPEATS_NEEDED
        out["cells"][f"c({s})"] = {"medians_ns": {str(r): v for r, v in sorted(meds.items())}, "cv": c if enough else None, "left_out": left_out, "valid_medians": len(meds)}
        if c is not None and enough:
            cvs.append(c)
    out["cv_r"] = max(cvs) if len(cvs) == 2 else None  # NOT DETERMINED unless all five repeats gave a valid median for both c(1) and c(3)
    return out


def m_summary(ctx: bench.Context, cfg: Mapping[str, Any], hours_charged: float) -> dict[str, Any]:
    """M's record: CV_R, m_t (and whether TIMING SPREAD applies), the per-cell medians, the measured pass seconds and an ANALYTICAL projection of E2's charged hours from them (not a measurement of E2)."""
    passes, blks = bench.load_stage_records(ctx)
    cv = cv_r(passes, blks)
    margin = None
    if cv["cv_r"] is not None:
        m_t, spread = core.margin_from_cv(float(cv["cv_r"]), cfg)
        margin = {"m_t": m_t, "timing_spread": spread}
    wall = [p["wall_ns"] / 1e9 for p in passes]
    reg = core.registered_geometry(cfg)
    n_passes = len(reg.all_repeats) * len(reg.cells())
    settle = float(cfg["quiet"]["settle_seconds"])
    mean_pass_seconds = sum(wall) / len(wall) if wall else None
    return {
        "cv": cv, "margin": margin, "passes": len(passes), "mean_read_seconds_per_pass_measured": mean_pass_seconds, "charged_seconds_measured": hours_charged * 3600.0,
        "projection_analytical": None if mean_pass_seconds is None else {"note": "ANALYTICAL: read seconds only (process start and hashing excluded) x 144 registered passes + 120 s settle x 6 blocks; not a measurement of E2", "read_seconds": mean_pass_seconds * n_passes, "settle_seconds": settle * len(reg.all_repeats)},
        "invalid_blocks_recorded_not_replaced": [b["key"] for b in blks if not b.get("complete")],
    }  # fmt: skip


def run_rehearsal_stage(
    ctx: bench.Context,
    cfg: Mapping[str, Any],
    deps: blocks.Deps,
    hours: core.HoursLedger,
    runner_for: Any,
    control: Path,
    r1_record: Mapping[str, Any],
) -> dict[str, Any]:
    """P (prediction), the harness figure, the five blocks (no spare), the analysis and the report on the stage's own records. Resumable. Raises ``Paused`` or ``EngineeringStop`` after saving the state."""
    if not ctx.prediction_manifest_path().is_file():
        bench.write_prediction(ctx)
    bench.load_prediction(ctx)
    e2.run_harness(ctx, cfg, deps, control)
    state = blocks.StageState.load(ctx.stage_dir() / "state.json")
    if state.data["status"] != "COMPLETE":
        blocks.run_stage_blocks(ctx, deps, state, runner_for, hours=hours, recover=None, extra_sessions=int(cfg["quiet"]["extra_sessions"]))
    return {"state": state.data}


def analyse_rehearsal(ctx: bench.Context, cfg: Mapping[str, Any], r1_record: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """The stage's analysis and report text on its own records (K: with the config's fixed figures; M: m_t is the provisional zero placeholder, so M's EQ-B is read only as figures)."""
    reg = e2.build_registry(ctx, cfg, r1_record)
    reg["thresholds"]["valid_min_repeats"] = int(cfg["thresholds"]["valid_min_repeats"])
    res = e2.labels_of(reg)
    text = report.render_report(res, {"write_ledger_bytes": "see the write ledger", "hours": "see the hours ledger"}, ctx.geometry.cells())
    return res, text


def enumerate_registered_from_plan(plan: Plan) -> dict[str, int]:
    """K's check of the registered geometry in RAM, from the plan only: tile counts and no page requested twice across all passes of all repeats, the spare included."""
    geo = plan.geometry("registered")
    sec = plan.section("registered")
    seeds = [int(b["request_order_seed"]) for b in plan.blocks("registered")]
    counts = layout.enumerate_registered(geo, int(sec["tile_assignment_seed"]), seeds)
    expect = {"tiles_dealt": 3996, "passes": 144, "distinct_pages": counts["pages"]}
    if geo.tiles_needed() != expect["tiles_dealt"] or counts["tiles_dealt"] != 3996 or counts["passes"] != 144 or counts["distinct_pages"] != counts["pages"]:
        raise AssertionError(f"the registered geometry's enumeration differs from the fixed arithmetic: {counts}")
    return counts


def k_record(ctx: bench.Context, cfg: Mapping[str, Any], plan: Plan, plan_sha: str, enumeration: Mapping[str, int], analysis_ok: bool, report_ok: bool, seed_gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state = read_json(ctx.stage_dir() / "state.json")
    stages = {
        "prediction": {"status": "COMPLETE" if ctx.prediction_manifest_path().is_file() else "MISSING"}, "harness_figure": {"status": "COMPLETE" if e2.harness_log_path(ctx).is_file() else "MISSING"},
        "blocks": {"status": state["status"]}, "analysis": {"status": "COMPLETE" if analysis_ok else "FAILED"}, "report": {"status": "COMPLETE" if report_ok else "FAILED"}, "registered_enumeration": {"status": "COMPLETE", **enumeration},
    }  # fmt: skip
    return {
        **core.envelope("rehearsal"), "stage": "K", "caps_provisional": core.caps_provisional(cfg), "figures_provisional": core.provisional_figures(cfg), "candidate": {"status": "COMPLETE" if all(v["status"] == "COMPLETE" for v in stages.values()) else "INCOMPLETE", "plan_file_sha256": plan_sha},
        "stages": stages, "plan_content_sha256": plan.sha256(), "geometry": ctx.geometry.name, "seed_gate_ok": None if seed_gate is None else seed_gate.get("passed"), "utc": core.utc_stamp(),
    }  # fmt: skip


def plan_file_sha(plan_path: Path) -> str:
    return file_sha256(plan_path)
