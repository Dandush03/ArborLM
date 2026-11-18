# ruff: noqa: E501
"""P10IS5 stages E1 (build the 4 GiB file), P (prediction) and E2 (the read benchmark), plus the registry that analysis reads (ADR-0028 sections 5.2, 6, 7 item 7, 8, 9; rulings 13, 14).

E1 builds the file in 1 GiB chunks, each verified by an uncached read against the regenerated SHA-256 and the counter rule; resumable. E2 starts no sooner than 10 minutes after E1's last write, after the order of checks of
ruling 14, after a quiet check, and after the cold check of section 7 item 7 (a short count is PAUSED — STORE NOT COLD: the file is rebuilt once within the cap and checked again after another 10 minutes; a second short count is
ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD). Then the harness figure, then the five blocks, then the spare if needed. No part of this module is run by the tests against a real device: they use fakes.
"""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import analysis, bench, blocks, core, device, r1, system
from .core import Paused


def e1_record_path(run_dir: Path) -> Path:
    return run_dir / "E1" / "e1.json"


def check_order(cfg: Mapping[str, Any], deps: blocks.Deps, where: Path, run_dir: Path, label: str, *, needed_bytes: int, ledger: device.WriteLedger | None, file_exists: bool) -> dict[str, Any]:
    """Ruling 14, after the identity check the entry point has made: the EC3 record, free space, hygiene, memory guard, the write-budget projection. (The quiet check is the block gate's.) Returns the records;
    raises ``Paused`` for a health warning, a full drive, Spotlight indexing the directory, or a projected write past the cap."""
    ec3 = system.ec3_record(deps.run, deps.run_b, where, label)
    if not ec3["health_ok"]:
        raise Paused("PAUSED — DRIVE HEALTH", f"SMART status {ec3['smart_status']}: goes to the human lead")
    free = device.require_free_space(where, int(cfg["budget"]["free_space_min_bytes"]))
    hyg = system.hygiene_record(deps.run, where, file_exists=file_exists)
    if hyg["blocks_e1"]:
        raise Paused("PAUSED — SPOTLIGHT INDEXES THE DIRECTORY", str(where))
    snap = deps.counter.read()
    if snap.phys_footprint > int(cfg["resources"]["memory_guard_bytes"]):
        raise core.EngineeringStop("MEMORY GUARD", f"footprint {snap.phys_footprint} B")
    proj = {"needed_bytes": needed_bytes, "ledger_total": None if ledger is None else ledger.total(), "ledger_remaining": None if ledger is None else ledger.remaining()}
    if ledger is not None and needed_bytes > ledger.remaining():
        raise core.WriteBudgetExceeded(f"{label}: {needed_bytes} B planned, {ledger.remaining()} B left under the cap")
    return {"ec3": ec3, "free_bytes": free, "hygiene": hyg, "projection": proj}


def run_e1(plan: Any, cfg: Mapping[str, Any], deps: blocks.Deps, ledger: device.WriteLedger, run_dir: Path, *, now: Callable[[], float], builder: Callable[..., dict[str, Any]] = device.build_file) -> dict[str, Any]:
    """E1. Resumable: a verified chunk is not rebuilt. Writes the E1 record (with ``built_at``, the time of the last write) only when the whole file is built and verified."""
    paths, files, sec = plan.paths, plan.content["files"], plan.section("registered")
    store = Path(paths["store"])
    done = e1_record_path(run_dir)
    if done.is_file():
        return read_json(done)
    manifest = device.manifest_path(store)
    verified = len(read_json(manifest)["verified_chunks"]) if manifest.is_file() else 0
    left = max(0, int(cfg["budget"]["store_file_bytes"]) - verified * int(cfg["device"]["build_chunk_bytes"]))  # the unverified chunks are written (and charged) again
    pre = check_order(cfg, deps, store.parent, run_dir, "E1 before", needed_bytes=left, ledger=ledger, file_exists=store.exists())
    rep = builder(store, int(files["store_tiles"]), int(sec["file_contents_seed"]), ledger, deps.counter, chunk_bytes=int(cfg["device"]["build_chunk_bytes"]), resume=manifest.is_file() or store.exists(), pread=deps.pread, min_free=int(cfg["budget"]["free_space_min_bytes"]))
    post = system.ec3_record(deps.run, deps.run_b, store.parent, "E1 after")
    rec = {**core.envelope("stage_manifest"), "stage": "E1", "status": "COMPLETE", "built_at": now(), "build": rep, "ec3_before": pre["ec3"], "ec3_after": post, "ledger_bytes": ledger.total()}
    core.write_record(done, rec)
    return rec


def cold_log_path(ctx: bench.Context) -> Path:
    return ctx.stage_dir() / "cold_checks.json"


def load_cold_checks(ctx: bench.Context) -> list[dict[str, Any]]:
    p = cold_log_path(ctx)
    return list(read_json(p)["checks"]) if p.is_file() else []


def save_cold_checks(ctx: bench.Context, checks: list[dict[str, Any]]) -> None:
    core.write_record(cold_log_path(ctx), {**core.envelope("cold_check"), "checks": checks}, overwrite=True)


def harness_log_path(ctx: bench.Context) -> Path:
    return ctx.stage_dir() / "harness_figure.json"


def run_harness(ctx: bench.Context, cfg: Mapping[str, Any], deps: blocks.Deps, control: Path) -> dict[str, Any]:
    """The harness figure at the start of E2 (and of M and K): the same threaded loop on cached pages of R1's control file. Written once."""
    p = harness_log_path(ctx)
    if p.is_file():
        return read_json(p)
    fig = r1.harness_figure(control, cfg, deps)
    rec = {**core.envelope("harness_figure"), "stage": ctx.stage, "figure": fig}
    core.write_record(p, rec)
    return rec


def run_e2(
    ctx: bench.Context,
    cfg: Mapping[str, Any],
    deps: blocks.Deps,
    ledger: device.WriteLedger,
    hours: core.HoursLedger,
    runner_for: Callable[[int], bench.PassRunner],
    control: Path,
    *,
    now: Callable[[], float],
    e1_built_at: float,
    rerun_after_stop: str | None = None,
    builder: Callable[..., dict[str, Any]] = device.build_file,
) -> blocks.StageState:
    """E2: the checks, the 10-minute wait after E1, the cold check, the harness figure, the blocks. Resumable; raises ``Paused`` or ``EngineeringStop`` after saving the state."""
    q, b = cfg["quiet"], cfg["budget"]
    state = blocks.StageState.load(ctx.stage_dir() / "state.json")
    if state.data["status"] == "COMPLETE":
        return state
    seeds = cfg["seeds"]
    store_tiles = int(cfg["device"]["store_tiles"])
    checks = load_cold_checks(ctx)
    if checks and checks[-1]["outcome"] != "COLD":
        state.data["status"] = "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD"
        state.save()
        return state
    if not checks:
        check_order(cfg, deps, ctx.file_path.parent, ctx.run_dir, "E2 before", needed_bytes=0, ledger=None, file_exists=True)
        deps.sleep(max(0.0, e1_built_at + float(q["cold_wait_seconds"]) - now()))  # no sooner than 10 minutes after E1's last write
        try:
            ctx_gate_ok = deps.gate.at_start()  # the quiet check before the cold check
        except Paused as e:
            state.data["quiet_sessions_failed"] += 1
            state.data["quiet_exhausted"] = state.data["quiet_sessions_failed"] >= 1 + int(q["extra_sessions"])
            state.data["status"] = e.reason
            state.save()
            raise
        state.note("quiet_before_cold_check", ok=ctx_gate_ok["ok"])

        def rebuild() -> None:
            device.delete_built_file(ctx.file_path)
            builder(ctx.file_path, store_tiles, int(seeds["store_contents"]), ledger, deps.counter, chunk_bytes=int(cfg["device"]["build_chunk_bytes"]), pread=deps.pread, min_free=int(b["free_space_min_bytes"]))
            state.data["rebuilds"] += 1
            state.save()

        rec = device.hold_cold(ctx.file_path, store_tiles, int(seeds["store_contents"]), deps.counter, rebuild, lambda: deps.sleep(float(q["cold_wait_seconds"])), pread=deps.pread)
        save_cold_checks(ctx, [rec])
        if rec["outcome"] != "COLD":
            state.data["status"] = "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD"
            state.save()
            return state
    run_harness(ctx, cfg, deps, control)

    def recover() -> None:
        """Section 7 item 5: the file is deleted and rebuilt once (charged to the write budget), the cold wait and a cold check follow. A write that would pass the cap is PAUSED (WRITE BUDGET)."""
        device.delete_built_file(ctx.file_path)
        builder(ctx.file_path, store_tiles, int(seeds["store_contents"]), ledger, deps.counter, chunk_bytes=int(cfg["device"]["build_chunk_bytes"]), pread=deps.pread, min_free=int(b["free_space_min_bytes"]))
        deps.sleep(float(q["cold_wait_seconds"]))
        again = device.cold_check(ctx.file_path, store_tiles, int(seeds["store_contents"]), deps.counter, pread=deps.pread)
        save_cold_checks(ctx, [*load_cold_checks(ctx), {"first": again, "rebuilt": True, "second": None, "outcome": "COLD" if again["cold"] else f"{core.ENG_NOT_EVALUABLE} — {core.STORE_CANNOT_BE_HELD_COLD}"}])
        if not again["cold"]:
            raise Paused("PAUSED — STORE NOT COLD", "after the recovery rebuild")

    return blocks.run_stage_blocks(ctx, deps, state, runner_for, hours=hours, recover=recover, rerun_after_stop=rerun_after_stop, extra_sessions=int(q["extra_sessions"]))


# --- the registry the analysis reads ------------------------------------------------------------------------------------------------------------
def build_registry(ctx: bench.Context, cfg: Mapping[str, Any], r1_record: Mapping[str, Any] | None, *, m_t: float | None = None, timing_spread: bool | None = None) -> dict[str, Any]:
    """The analysis input from the run directory alone: passes, blocks, the stage's harness figure, R1's reasons, the cold checks, the manifest, the stops (resolved when a complete spare block names them) and the
    thresholds. ``m_t`` and ``timing_spread`` default to the config's fixed figures."""
    passes, blks = bench.load_stage_records(ctx)
    state = blocks.StageState.load(ctx.stage_dir() / "state.json")
    th, f = cfg["thresholds"], cfg["fixed_after_r1_and_m"]
    thresholds = {
        "m_t": float(f["m_t"] if m_t is None else m_t), "timing_spread": bool(f["timing_spread"] if timing_spread is None else timing_spread), "label_min_repeats": int(th["label_min_repeats"]), "valid_min_repeats": int(th["valid_min_repeats"]),
        "harness_limited_fraction": float(th["harness_limited_fraction"]), "sizes": list(ctx.geometry.sizes), "depths": list(ctx.geometry.depths), "grid": [list(c) for c in ctx.geometry.cells()],
    }  # fmt: skip
    hp = harness_log_path(ctx)
    fig = r1.harness_by_depth(read_json(hp)["figure"]) if hp.is_file() else {}
    return {
        "passes": passes, "blocks": blks, "harness": fig, "r1": dict(r1_record or {}), "cold_checks": load_cold_checks(ctx), "manifest": state.data, "stops": blocks.resolved_stops(ctx, blks), "thresholds": thresholds,
    }  # fmt: skip


def labels_of(registry: Mapping[str, Any]) -> dict[str, Any]:
    """The analysis, with the stage's own refusals (an engineering stop, no pass at all) kept as refusals."""
    if not registry["passes"] and not (registry["r1"] or {}).get("not_evaluable_reasons") and not any("STORE CANNOT BE HELD COLD" in str(c.get("outcome")) for c in registry["cold_checks"]):
        raise analysis.AnalysisRefused("no pass record exists: nothing is labelled")
    return analysis.analyse(registry)
