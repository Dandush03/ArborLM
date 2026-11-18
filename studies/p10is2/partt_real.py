# ruff: noqa: E501
"""Part T's real-run drivers: the world from Part Q's outputs, calibration, the registered stage bodies and the two rehearsals (ADR-0025 sections 7, 10, 11 item 5).

Everything is a function of a ``WorldT`` (``engine.build_world_t``), so the tests drive it with a tiny world on CPU and the lead's runs drive it with the real bundle on MPS. Part T uses the lock alone: nothing
here imports a package outside it. Part T reads Part Q's manifest files only, by hash (ruling L12): the bundle, the pools, the generation record and the gloss bank; never a sealed file, never a Q_fit or Q_check
per-item score. Charged time is the wall time of each process (ruling L2); the stage bodies run in one process here (a worker split is an optimisation the lead's launch can add: the cell tasks are independent).
"""

import json
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json, write_json
from studies.p10s2.data import TrainItem
from studies.p10s2.evaluate import score_panel
from studies.p10s2.memory import NullArm
from studies.p10s2.worldio import read_bundle

from . import annotations, calibration, engine, partt_gates, partt_plan, partt_run, report, scoring
from . import labels as L
from .common import core
from .common.gates import platform_record
from .quantities import CELLS, Quantities, Registry, Thresholds


# --- Part Q's outputs -------------------------------------------------------------------------------------------------------------------------------
def load_part_q(qdir: Path, cfg: Mapping[str, Any], mode: str) -> tuple[Any, list[dict[str, list[TrainItem]]], dict[str, Any], dict[str, Any]]:
    """The bundle, the replicates' training draws, the gloss bank and the draws record from a Part Q run directory (``outputs/bundle``, ``generation/pools.json``, ``generation/result.json``,
    ``outputs/gloss_bank.json``). DISJOINT DRAWS: the recorded permutation positions; OVERLAPPING DRAWS: each replicate draws 8,000 from the whole pool with its training-draw seed (capability A first, then B, one
    generator per replicate)."""
    bundle = read_bundle(qdir / "outputs/bundle")
    pools = read_json(qdir / "generation/pools.json")["pools"]
    result = read_json(qdir / "generation/result.json")
    pool = {c: [TrainItem(x["key"], x["en"], x["target"], int(x["group"])) for x in pools[c]] for c in core.TASKS}
    per = int(cfg["data"].get("per_replicate", 8000)) if "per_replicate" in cfg.get("data", {}) else 8000
    if result["draws_label"] == "DISJOINT DRAWS":
        idx = result["draws"]["indices"]
        draws = [{c: [pool[c][i] for i in idx[c][r]] for c in core.TASKS} for r in range(3)]
    elif result["draws_label"] == "OVERLAPPING DRAWS":
        draws = []
        for r in range(3):
            plan = engine.SeedPlanT(cfg, mode, r)
            g = plan.gen(1, "overlapping draw")
            draws.append({c: [pool[c][i] for i in torch.randperm(len(pool[c]), generator=g).tolist()[:per]] for c in core.TASKS})
    else:
        raise core.StageRefused(f"refused: Part Q's draws label is {result['draws_label']!r}: Part T has no material")
    gloss = read_json(qdir / "outputs/gloss_bank.json")
    return bundle, draws, gloss, result


def shared_share(draws: Sequence[Mapping[str, Sequence[TrainItem]]]) -> dict[str, float]:
    """Mean over replicate pairs of |intersection| / draw size, per capability: printed beside every line that says "every cell" when the draws overlap."""
    out = {}
    for c in core.TASKS:
        sets = [{x.key for x in d[c]} for d in draws]
        pairs = [(i, j) for i in range(len(sets)) for j in range(i + 1, len(sets))]
        out[c] = sum(len(sets[i] & sets[j]) / max(1, len(sets[i])) for i, j in pairs) / max(1, len(pairs))
    return out


# --- calibration ------------------------------------------------------------------------------------------------------------------------------------
@torch.no_grad()
def dcal_mean(world: engine.WorldT, arm: Any, cap: str) -> float:
    return score_panel(world.ctx, arm, world.d_cal[cap]).mean


def calibration_draws(pool: Mapping[str, Sequence[TrainItem]], cfg: Mapping[str, Any], indices: Sequence[int], per: int = 8000) -> list[dict[str, list[TrainItem]]]:
    """The training draws of calibration draws 0..3 (draws 2 and 3 are the repetition of section 7.1 rule 4): from Part Q's accepted pools with each draw's training-draw seed (+1), A then B."""
    out = []
    for i in indices:
        g = engine.SeedPlanT(cfg, "calibration", i).gen(1, "calibration training draw")
        out.append({c: [pool[c][k] for k in torch.randperm(len(pool[c]), generator=g).tolist()[:per]] for c in core.TASKS})
    return out


def run_unit(world: engine.WorldT, unit: Mapping[str, Any], rate: float, layer: int | None, draw_index: int) -> dict[str, Any]:
    """One calibration training unit on a calibration draw's seeds (the world is built in ``calibration`` mode with the calibration draws), scored on D_cal. A non-finite loss is DIVERGED (``diverged``, no
    mean at the diverged snapshot); the caller applies ``calibration``'s rules. A ladder unit has ``snapshots``; each is scored on D_cal on CPU while the optimizer state is kept."""
    cap, module = unit["capability"], unit["module"]
    saved = (world.layer, world.store_lr, world.lora_lr, getattr(world, "etable_lr", None), world.ctx.router_layer)
    try:
        if layer is not None:
            world.layer = world.ctx.router_layer = int(layer)
        if module == "lora":
            world.lora_lr = rate
        else:
            world.store_lr = rate
            world.etable_lr = rate  # type: ignore[attr-defined]
        arm_name = {"store": "M1", "lora": "D1", "etable": "E-table"}[module]
        spec = engine.CellSpec(arm_name, cap + core.other_task(cap) if module != "etable" else "-", draw_index, cap if module == "etable" else "")
        arm, rows, opts = engine.build_cell_arm(world, spec, None)
        snaps = list(unit.get("snapshots") or [])
        means: dict[int, float | None] = {}

        def cb(update: int, a: Any) -> None:
            means[update] = dcal_mean(world, a, cap)

        rec = engine.train_cell(world, spec, arm, rows, {**opts, "rate": rate}, int(unit["updates"]), snapshots=snaps, on_snapshot=cb)
        if not snaps and rec["status"] == "COMPLETE":
            means[int(unit["updates"])] = dcal_mean(world, arm, cap)
        if rec["status"] == "ERROR":
            raise RuntimeError(f"calibration unit {unit['id']} stopped on a code or environment error (an engineering stop, never DIVERGED): {rec['error']}")
        diverged = rec["status"] == "STOPPED_NONFINITE"
        return {"unit": unit["id"], "rate": rate, "layer": world.layer, "means": means, "diverged": diverged, "status": rec["status"], "error": rec["error"], "seconds_per_update": rec["seconds_per_update"]}
    finally:
        world.layer, world.store_lr, world.lora_lr, el, world.ctx.router_layer = saved
        if el is not None:
            world.etable_lr = el  # type: ignore[attr-defined]


def run_calibration(world: engine.WorldT, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The whole of section 7.1 on a calibration world: the store's and LoRA's rate grids (draw 0, store at L = 4), the store at L = 12 at its chosen rate, E-table's grid at the chosen layer, the convergence
    ladder (M1 and D1 on each capability, draw 1, to 8,000 updates), then U and the pilot. Returns the record the Part T plan is built from. A stop (every rate diverged, a non-finite value in the ladder
    or the pilot) is ``calibration.CalibrationStop``: the work returns to the human lead."""
    c = cfg["calibration"]
    units = {u["id"]: u for u in calibration.calibration_units(cfg)}
    rec: dict[str, Any] = {"units": {}, "stand_in": False}

    def mean_over_caps(prefix: str, rate: float, layer: int | None, mod: str) -> float | None:
        vals = []
        for cap in core.TASKS:
            r = run_unit(world, units[f"{prefix}-{cap}-{rate}"], rate, layer, 0)
            rec["units"][r["unit"]] = r
            if r["diverged"]:
                return None
            vals.append(next(iter(r["means"].values())))
        return float(sum(vals) / len(vals))

    store = {r: mean_over_caps("grid-store", r, int(c["rate_grid_read_layer"]), "store") for r in c["store_rates"]}
    lora = {r: mean_over_caps("grid-lora", r, None, "lora") for r in c["lora_rates"]}
    store_rate, lora_rate = calibration.select_rate(cfg, "store", store), calibration.select_rate(cfg, "lora", lora)
    l12 = []
    for cap in core.TASKS:
        r = run_unit(world, units[f"layer12-{cap}"], store_rate, int(cfg["memory"]["read_layers"][1]), 0)
        rec["units"][r["unit"]] = r
        l12.append(None if r["diverged"] else next(iter(r["means"].values())))
    layer = calibration.select_read_layer(cfg, store[store_rate] or 0.0, None if any(v is None for v in l12) else sum(l12) / 2)  # type: ignore[arg-type]
    et = {r: mean_over_caps("grid-etable", r, layer, "etable") for r in c["store_rates"]}
    etable_rate = calibration.select_rate(cfg, "etable", et)
    ladder: dict[str, dict[str, dict[int, float | None]]] = {"store": {}, "lora": {}}
    for module in ("store", "lora"):
        for cap in core.TASKS:
            r = run_unit(world, units[f"ladder-{module}-{cap}"], store_rate if module == "store" else lora_rate, layer if module == "store" else None, 1)
            rec["units"][r["unit"]] = r
            ladder[module][cap] = r["means"]
    length = calibration.choose_training_length(cfg, ladder)
    gaps: dict[str, float | None] = {}
    for cap in core.TASKS:
        r = rec["units"][f"ladder-store-{cap}"]
        s0 = score_panel(world.ctx, NullArm(), world.d_cal[cap]).mean
        gaps[cap] = None  # the gap needs the teacher's D_cal score: filled below
        t = sum(chrf for chrf in _teacher_dcal(world, cap)) / max(1, len(_teacher_dcal(world, cap)))
        mean = r["means"][length["U"]]
        gaps[cap] = None if t - s0 < float(cfg["data"]["gap_denominator_min"]) else (mean - s0) / (t - s0)
    pilot = calibration.pilot_gate(cfg, gaps)
    rec.update({"store_rate": store_rate, "lora_rate": lora_rate, "etable_rate": etable_rate, "read_layer": layer, "U": length["U"], "converged": length["converged"], "line_note": length["line_note"], "pilot": pilot, "grids": {"store": store, "lora": lora, "etable": et}, "ladder_differences": length["differences"]})
    return rec


def _teacher_dcal(world: engine.WorldT, cap: str) -> list[float]:
    from studies.p10s2.text import chrf_item

    texts = world.teacher_outputs[cap]["D_cal"]
    return [chrf_item(t, r) for t, r in zip(texts, world.d_cal[cap].refs, strict=True)]


# --- rehearsals ----------------------------------------------------------------------------------------------------------------------------------
def measure_rates(world: engine.WorldT, snap_dir: Path, gloss: Mapping[str, Any], updates: int = 200, items: int = 20) -> dict[str, Any]:
    """The Part T measuring rehearsal's measurements: seconds per update of every trained cell type, seconds per scored item of each kind, the router's training time and the combined scoring of one arm of
    each kind, with the peak resident set. Rates are measured, never labels."""
    import resource

    rates: dict[str, float] = {}
    units: dict[str, float] = {}
    for arm in ("M1", "D1", "M-joint", "D-joint"):
        spec = engine.CellSpec(arm, "AB" if arm in ("M1", "D1") else "-", 0)
        a, rows, opts = engine.build_cell_arm(world, spec, None)
        rec = engine.train_cell(world, spec, a, rows, opts, updates)
        rates[f"train:{arm}"] = rec["seconds_per_update"]
        engine.save_t(a, snap_dir, spec.label)
    t0 = time.perf_counter()
    scoring.build_routers_t(world, 0)
    rates["router_seconds"] = time.perf_counter() - t0
    m1 = engine.load_t(world, 0, snap_dir, "r0/M1/AB")
    t0 = time.perf_counter()
    for n in ("E_A", "E_B"):
        score_panel(world.ctx, m1, world.ctx.panels[n], indices=list(range(min(items, len(world.ctx.panels[n].examples)))))
    rates["score_seconds_per_item"] = (time.perf_counter() - t0) / (2 * items)
    t0 = time.perf_counter()
    from studies.p10s2 import combined as cm

    cm.score_combined_cell(world.ctx, m1, world.ctx.ec)
    rates["combined_seconds_per_arm_cell"] = time.perf_counter() - t0
    plan = partt_plan.stage_items({"U": updates, "store_rate": 0, "lora_rate": 0, "etable_rate": 0, "read_layer": world.layer})
    units["train"] = float(sum(i["updates"] for i in plan["train"]))
    units["evaluate"], units["combined"] = float(len(plan["evaluate"])), float(len(plan["combined"]))
    return {"rates_seconds_per_unit": rates, "projection_units": units, "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)}


def counting_rehearsal(world: engine.WorldT, snap_dir: Path, gloss: Mapping[str, Any], *, plan_file_sha256: str, caps_provisional: bool, updates: int, identity_probe: Callable[[], None] | None = None, require_mps: bool = False) -> dict[str, Any]:
    """Every cell type once (a cell of each trained type at the plan's U), one combined scoring of each arm kind, the analysis and the report on the scored registry, ONE forced pause and resume of a cell
    (checkpoint, then resume) and ONE forced PAUSED — IDENTITY (the probe refuses once and the stage then resumes)."""
    stages: dict[str, dict[str, str]] = {}
    spec = engine.CellSpec("M1", "AB", 0)
    a, rows, opts = engine.build_cell_arm(world, spec, None)
    first = engine.train_cell(world, spec, a, rows, opts, updates, checkpoint_dir=snap_dir / "ck", checkpoint_every=max(1, updates // 2), stop_after=max(1, updates // 2))
    paused = first["status"] == "PAUSED"
    identity_ok = False
    if identity_probe is not None:
        try:
            identity_probe()
        except core.StageRefused:
            identity_ok = True
    a2, rows, opts = engine.build_cell_arm(world, spec, None)
    resumed = engine.train_cell(world, spec, a2, rows, opts, updates, checkpoint_dir=snap_dir / "ck", checkpoint_every=max(1, updates // 2))
    ok_resume = resumed["status"] == "COMPLETE" and resumed["resumed"]
    recs = partt_run.train_all(world, snap_dir / "all", None, updates)
    stages["train"] = {"status": "COMPLETE" if all(r["status"] == "COMPLETE" for r in recs.values()) else "INCOMPLETE"}
    reg, side = partt_run.score_all(world, snap_dir / "all", gloss)
    stages["evaluate"] = stages["controls"] = {"status": "COMPLETE"}
    comb = partt_run.combined_all(world, snap_dir / "all")
    stages["combined"] = {"status": "COMPLETE"}
    gate = partt_gates.run_gates(world, world.cfg_t, snap_dir / "gates", run_checker=False, require_mps=require_mps)
    stages["gates"] = {"status": "COMPLETE" if gate["status"] == "PASSED" else "ENGINEERING-FAILURE"}
    out = analyse(reg, side, comb, {"U": updates, "converged": True}, required=partt_plan.required_keys(), thresholds=Thresholds.from_config(world.cfg_t))
    stages["analysis"] = {"status": "COMPLETE"}
    stages["report"] = {"status": "COMPLETE" if out["report"] else "INCOMPLETE"}
    return {**core.envelope("rehearsal", "T"), "kind_of_rehearsal": "counting", "plan_file_sha256": plan_file_sha256, "caps_provisional": caps_provisional, "stages": stages, "forced": {"pause_resume": bool(paused and ok_resume), "paused_identity_restore": identity_ok}, "g4_mps": gate["gates"]["G4-MPS"], "platform": platform_record(), "sealed": True}


# --- analysis and report -----------------------------------------------------------------------------------------------------------------------------
def analyse(reg: Registry, side: Mapping[str, Any], comb: Mapping[str, Any] | None, ctx: Mapping[str, Any], *, required: Sequence[str], thresholds: Thresholds, item_errors: Sequence[str] = (), recompute_failed: Sequence[Any] = (), engineering_failure: Sequence[str] = ()) -> dict[str, Any]:
    """Study status, the lines, the annotations and the report (pure over the records). Under a status that does not derive, no line is produced."""
    st = L.study_status(reg, item_errors=item_errors, recompute_failed=recompute_failed, engineering_failure=engineering_failure, required=required)
    if not st["derive"]:
        return {"status": st, "report": report.render(st, None, ctx)}
    q = Quantities(reg, thresholds)
    derived = L.derive_all(q, recompute_failed)
    ann = annotations.all_annotations(q, side if all(f"r{r}/M-append/{o}" in side and "route" in side[f"r{r}/M-append/{o}"] for r, o in CELLS) else None, comb)
    return {"status": st, "lines": derived, "annotations": ann, "report": report.render(st, derived, ctx)}


def write_analysis(run_dir: Path, result: Mapping[str, Any]) -> None:
    core.write_record(run_dir / "analysis.json", {**core.envelope("analysis", "T"), **core.jsonable(dict(result))}, overwrite=True)
    (run_dir / "report.txt").write_text(core.require_oracle_line(result["report"]) + "\n", encoding="utf-8")


def json_safe(x: Any) -> Any:
    return json.loads(json.dumps(core.jsonable(x), default=str))


__all__ = ["file_sha256", "write_json"]


# --- the registered stage bodies and the commands --------------------------------------------------------------------------------------------------
def build_world_real(repo: Path, cfg: Mapping[str, Any], qdir: Path, plan_calibration: Mapping[str, Any], mode: str) -> tuple[engine.WorldT, Mapping[str, Any], Any]:
    """The world of a registered run or a rehearsal: Part Q's bundle and draws, the calibrated settings, the frozen devices (MPS training, CPU scoring)."""
    bundle, draws, gloss, result = load_part_q(qdir, cfg, mode)
    run = engine.run_config(cfg, layer=int(plan_calibration["read_layer"]), updates=int(plan_calibration["U"]), store_rate=float(plan_calibration["store_rate"]), lora_rate=float(plan_calibration["lora_rate"]), device=cfg["training"]["training_device"])
    w = engine.build_world_t(bundle, cfg, draws, run, plan_mode=mode)
    w.etable_lr = float(plan_calibration["etable_rate"])  # type: ignore[attr-defined]
    return w, gloss, result


def run_stage(stage: str, repo: Path, run_dir: Path, qdir: Path, plan: Any, mode: str = "registered") -> dict[str, Any]:
    """One registered Part T stage over the run directory (``train``, ``evaluate``, ``controls``, ``combined``, ``gates``, ``analysis``, ``report``). The entry point has checked identity."""
    cfg = core.load_config("T", repo / core.CONFIG_T)
    calib = plan.data["calibration"]
    w, gloss, qres = build_world_real(repo, cfg, qdir, calib, mode)
    snaps = run_dir / "snapshots"
    t0 = time.monotonic()
    if stage == "gates":
        out = partt_gates.run_gates(w, cfg, snaps / "gates", equivalence_records=(bundle_equivalence(qdir) or None), root=repo, require_mps=mode == "registered")
        core.write_record(run_dir / "gates.json", {**core.envelope("gates", "T"), **core.jsonable(out)}, overwrite=True)
    elif stage == "train":
        out = partt_run.train_all(w, snaps, run_dir / "checkpoints", int(calib["U"]))
        core.write_record(run_dir / "train_records.json", {**core.envelope("cell_record", "T"), "records": core.jsonable(out)}, overwrite=True)
    elif stage in ("evaluate", "controls"):
        reg, side = partt_run.score_all(w, snaps, gloss)
        write_json(run_dir / "registry.json", reg.values)
        core.write_record(run_dir / "side_records.json", {**core.envelope("cell_record", "T"), "side": core.jsonable(side)}, overwrite=True)
        out = {"registry_keys": len(reg.values)}
    elif stage == "combined":
        comb = partt_run.combined_all(w, snaps)
        core.write_record(run_dir / "combined.json", {**core.envelope("cell_record", "T"), "combined": core.jsonable(comb)}, overwrite=True)
        out = {"records": len(comb)}
    elif stage in ("analysis", "report"):
        reg = Registry(read_json(run_dir / "registry.json"))
        side = read_json(run_dir / "side_records.json")["side"]
        comb = read_json(run_dir / "combined.json")["combined"] if (run_dir / "combined.json").is_file() else None
        errors = sorted(str(p) for p in (run_dir / "item_errors").glob("*.json")) if (run_dir / "item_errors").is_dir() else []
        ctx = {"U": int(calib["U"]), "converged": bool(calib.get("converged", True)), "draws": qres["draws_label"], "shared_share": shared_share([dict(s.t) for s in w.streams])}
        res = analyse(reg, side, comb, ctx, required=sorted(partt_plan.required_keys()), thresholds=Thresholds.from_config(cfg), item_errors=errors)
        write_analysis(run_dir, res)
        out = {"status": res["status"]["status"]}
    else:
        raise core.StageRefused(f"refused: {stage!r} is not a Part T stage")
    total = float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0
    led = core.Ledger(run_dir / "charged_ledger.json", "T", total if total > 0 else 1e12)
    led.charge_process(stage, mode, "main", time.monotonic() - t0)  # the wall time of this process (ruling L2)
    return json_safe(out)  # type: ignore[no-any-return]


def bundle_equivalence(qdir: Path) -> Mapping[str, Any] | None:
    return read_bundle(qdir / "outputs/bundle").extra.get("equivalence_layers")


def calibrate_command(repo: Path, qdir: Path, run_dir: Path, repetition: int) -> dict[str, Any]:
    """Calibration and the pilot on calibration draws (0, 1; a repetition 2, 3) with the frozen devices; writes ``calibration_<repetition>.json`` with the code hashes of every file it ran (section 7.1 rule 4).
    Nothing it scores is a result."""
    from .common import plan as planmod

    cfg = core.load_config("T", repo / core.CONFIG_T)
    bundle = read_bundle(qdir / "outputs/bundle")
    pools = read_json(qdir / "generation/pools.json")["pools"]
    pool = {c: [TrainItem(x["key"], x["en"], x["target"], int(x["group"])) for x in pools[c]] for c in core.TASKS}
    off = 2 * repetition
    run = engine.run_config(cfg, layer=int(cfg["calibration"]["rate_grid_read_layer"]), updates=int(cfg["calibration"]["rate_grid_updates"]), store_rate=0.003, lora_rate=0.0003, device=cfg["training"]["training_device"])
    w = engine.build_world_t(bundle, cfg, calibration_draws(pool, cfg, [off, off + 1]), run, plan_mode="calibration")
    w.plan_offset = off
    rec = run_calibration(w, cfg)
    rec["code_hashes"] = planmod.frozen_file_hashes(repo, "T")
    rec["repetition"] = repetition
    core.write_record(run_dir / f"calibration_{repetition}.json", {**core.envelope("calibration", "T"), **core.jsonable(rec)}, overwrite=True)
    return {k: rec[k] for k in ("store_rate", "lora_rate", "etable_rate", "read_layer", "U", "converged", "pilot")}
