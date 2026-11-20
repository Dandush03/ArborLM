# ruff: noqa: E501
"""P10IS1 measuring and counting rehearsals, the R2 qualification driver and the rehearsal record writer (ADR-0024 sections 8.1, 11, 17.1, 18).

* ``run_r2_qualification``: the reference arm R2 through every validity check (DEP-a, DEP-b, DEP-c) at every snapshot fraction of U_P, at each row's reference cell, on the rehearsal draw and both calibration draws; a check R2
  fails on any view at a fraction is NOT used at that fraction for any arm of that row, by rule, and the failures are recorded. The table holds conditions, never accuracies.
* ``measure_rates``: the MEASURING rehearsal's rates file, the input of ``project``: seconds per update per arm and size, the k-worker slowdown (k concurrent single-thread processes), evaluation seconds per snapshot with
  DEP at every snapshot, the peak memory per worker, the fixed stages. On the rehearsal draw only. Measured figures, not results.
* ``run_counting``: the COUNTING rehearsal: the registered driver's own stage functions (``stages.execute_stage``) against the candidate plan FILE (its rehearsal-draw view), every stage end to end; the analysis and the
  report on a synthetic registry keyed by the plan's labels; the record names the SHA-256 of the plan file and whether its caps are provisional. ``write_rehearsal_record`` is the record the freeze reads.
Real-size execution of any of these is the lead's run; nothing here is a registered run and no registered seed is used (the rehearsal draw 249201 with 330192, the calibration draws, or test seeds)."""

import argparse
import json
import multiprocessing as mp
import resource
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import adapter, analysis, core, gates, items, machine, report, stages, synthetic
from . import labels as L
from . import plan as planmod
from .rehearsal import check_plan_items, qualification_table

REHEARSAL_STAGE_CHAIN = ("gates", "timing", "train", "ladder", "evaluate", "baselines", "throughput")


# --- the R2 qualification driver ------------------------------------------------------------------------------------------------------------------
def view_seeds(mode: str, draw: int, cfg: Mapping[str, Any]) -> tuple[Any, int]:
    if mode == "calibration":
        return core.calibration_seeds(draw, cfg), core.calibration_init(draw, cfg)
    return core.seeds_for(mode, draw, cfg)


def run_r2_qualification(work: Path, rows: Mapping[int, tuple[int, int, int, float]], views: Sequence[tuple[str, str, int]], *, cfg: Mapping[str, Any], synthetic_data: bool = False, sizes: Mapping[str, int] | None = None, experiments_root: Path | None = None) -> dict[str, Any]:
    """``rows``: row facts -> (facts of the cell, slots of the cell, U_P of the row, R2's rate); ``views``: (name, mode, draw). Every record goes under ``work`` (sealed where a calibration draw is read)."""
    r2: dict[tuple[int, str], dict[int, dict[str, L.Obs]]] = {}
    failures: list[dict[str, Any]] = []
    for row, (facts, slots, u_p, rate) in rows.items():
        for name, mode, draw in views:
            seeds, init = view_seeds(mode, draw, cfg)
            run = core.r2_run(u_p, cfg)
            snaps = core.grid_snapshots(u_p, run, cfg)
            calib = mode == "calibration"
            cell = core.make_cell(mode, "R2", facts, slots, draw, init, u_p=u_p, run=run, lr=rate, kind="CAL" if calib else "P", test=False if calib else None)
            spec = {
                "label": cell.label, "arm": "R2", "facts": facts, "slots": slots, "draw": draw, "init_seed": init, "seed_name": seeds.name, "seed_base": seeds.facts, "u_p": u_p, "lr": rate, "run": run, "ladder_cell": False,
                "snapshots": snaps, "mode": mode, "kind": cell.kind, "test_label": False if calib else None,
            }  # fmt: skip
            ctx = items.Ctx(mode, work / name, experiments_root, synthetic=synthetic_data, sizes=dict(sizes or {"table_facts": 32768, "unseen": 2048}))
            data, sd = items.load_data(ctx, spec, verify=False)
            adapter.train_to(data, sd, items.backbone_of(ctx), ctx.run_dir, spec, run, mode=mode, cfg=cfg)
            items.baseline_item(ctx, draw, facts, spec, data=data, seeds=sd)
            base = core.read_record(ctx.baseline_path(draw, facts), "baseline")["no_memory"]
            series: dict[int, dict[str, L.Obs]] = {}
            for u in snaps:
                rec = core.read_record(items.evaluate_snapshot(ctx, spec, u, data=data, seeds=sd), "eval")["reads"]["main"]["panels"]
                series[u] = {p: L.Obs(int(rec[p]["n"]), int(rec[p]["correct"]), int(rec[p]["useful"]), int(rec[p]["disabled_correct"]), int(rec[p]["shuffled_correct"]), int(base[p]), int(rec[p]["unseen_n"]), int(rec[p]["unseen_correct"])) for p in core.PANELS}
                bad: set[str] = set()
                for o in series[u].values():
                    bad |= L.dep_failures(o, memory=True, qualified=set(L.DEP_CONDITIONS))
                if bad:
                    failures.append({"row": row, "view": name, "update": u, "fraction": analysis.fraction_key(u, u_p), "conditions": sorted(bad)})
            r2[(row, name)] = series
    table = qualification_table(r2, {row: v[2] for row, v in rows.items()})
    return {"table": table, "failures": failures, "views": [v[0] for v in views], "rule": "a condition R2 fails at a fraction on any view is not used at that fraction for any arm of that row (NOT QUALIFIED AT that fraction)"}


# --- the plan view of the rehearsal draw -----------------------------------------------------------------------------------------------------------------
def rehearsal_view(pl: planmod.Plan, run_dir: Path, cfg: Mapping[str, Any]) -> planmod.Plan:
    """The candidate plan on the REHEARSAL draw: same parameters, lengths and frozen identities, the cells re-planned with the rehearsal seeds (one replicate). A plan that is not registered is its own view."""
    if pl.mode != core.REGISTERED:
        return pl
    data = {**pl.data, "mode": core.REHEARSAL, "cells": core.planned_cells(pl.params(), core.REHEARSAL, cfg, draws=[1]), "run_dir": str(run_dir.resolve())}
    path = run_dir / "view_plan.json"
    core.write_record(path, data, overwrite=True)
    return planmod.Plan.load(path)


def synthetic_registry_for(pl: planmod.Plan) -> Any:
    params = pl.params()
    return synthetic.build(params, cells=pl.data["cells"], u_run={n: int(params.u0[n]) for n in params.u0})


# --- the measuring rehearsal -----------------------------------------------------------------------------------------------------------------------------
def _concurrent_timing(task: tuple[str, str, str, str, int, bool, int, int, int, int]) -> dict[str, Any]:
    """One process of the k-worker slowdown: single thread, one (arm, slots) item of the plan, wall seconds per update while the other workers run."""
    plan_path, run_dir, config_path, arm, slots, synth, warmup, updates, repeats, eval_update = task
    from studies.p10s1 import timing as s1timing

    cfg = core.load_config(Path(config_path)) if config_path else core.load_config()
    gates.configure_worker(cfg)
    pl = planmod.Plan.load(Path(plan_path))
    ctx = items.Ctx(pl.mode, Path(run_dir), None, synthetic=synth, sizes=dict(pl.data.get("sizes") or {"table_facts": 32768, "unseen": 2048}), config_path=Path(config_path) if config_path else None)
    if not synth:
        from . import freeze as fz

        ctx.experiments_root = fz.experiments_root()
    c = next(x for x in pl.data["cells"] if x["arm"] == arm and x["slots"] == slots)
    data, sd = items.load_data(ctx, {**c, "mode": pl.mode}, verify=False)
    cell = core.make_cell(pl.mode, arm, c["facts"], slots, c["draw"], c["init_seed"], u_p=c["u_p"], run=c["run"], lr=c["lr"])
    job = adapter.job_for(cell, data, sd, items.backbone_of(ctx), Path(run_dir) / "timing" / "work_k", (), optimizer_marks=(), mode="calibration")
    r = s1timing.cpu_seconds_per_update(job, warmup=warmup, updates=updates, repeats=repeats)
    ev_cell = core.make_cell(pl.mode, arm, c["facts"], slots, c["draw"], c["init_seed"], u_p=c["u_p"], run=eval_update, lr=c["lr"])
    ev_spec = {**c, "mode": pl.mode, "snapshots": [eval_update], "run": eval_update, "label": ev_cell.label, "ladder_cell": False}
    adapter.train_to(data, sd, items.backbone_of(ctx), ctx.run_dir / "timing" / "eval_k", ev_spec, eval_update, mode=pl.mode, cfg=cfg)
    ev_ctx = items.Ctx(pl.mode, ctx.run_dir / "timing" / "eval_k", ctx.experiments_root, synthetic=synth, sizes=ctx.sizes, config_path=ctx.config_path)
    t0 = time.monotonic()
    items.evaluate_snapshot(ev_ctx, ev_spec, eval_update, data=data, seeds=sd)  # evaluation seconds per snapshot UNDER the k-worker load, DEP counts at every snapshot included
    return {"item": f"{arm}|{slots}", "wall": float(r["wall_seconds_per_update"]), "cpu": float(r["cpu_seconds_per_update"]), "peak_rss_bytes": int(max(r["peak_rss_bytes"], resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)), "evaluate_seconds": time.monotonic() - t0}


def measure_rates(pl: planmod.Plan, ctx: items.Ctx, plan_path: Path, workers_list: Sequence[int], *, synthetic_data: bool = False, warmup: int | None = None, updates: int | None = None, repeats: int | None = None, eval_update: int = 8, candidate: planmod.Plan | None = None) -> dict[str, Any]:
    """The rates file ``project`` reads (``{"by_workers": {"6": {train, evaluate, contention, fixed, peak_rss_bytes_per_worker}}}``): isolated seconds per update per (arm, slots) of the plan, the k-worker slowdown (the worst
    item's ratio of concurrent to isolated wall seconds per update, at least 1), evaluation seconds per snapshot (DEP at every snapshot), peak memory per worker, fixed stages (analysis and report measured on a synthetic
    registry; the throughput figure is P10-S1's, stated). All MEASURED on the rehearsal draw."""
    cfg = ctx.cfg()
    import os

    from . import quiet as quiet_mod

    machine_before = {"load_average_1m": os.getloadavg()[0], "other_study_processes": quiet_mod.other_study_processes()}  # what else ran: the contention ratio is only as good as this record says (section 16.1 item 3)
    q = cfg["quiet"]  # the config's timing figures (32 warm-up updates, 256 updates, 3 repeats) unless a test passes smaller ones explicitly
    warmup, updates, repeats = int(q["timing_warmup_updates"]) if warmup is None else warmup, int(q["timing_updates"]) if updates is None else updates, int(q["timing_repeats"]) if repeats is None else repeats
    began = time.monotonic()
    iso = stages.measure_timing(pl, ctx, warmup=warmup, updates=updates, repeats=repeats)
    cpu = iso["cpu"]
    wall_iso = {k: float(v["wall_seconds_per_update"]) for k, v in iso["detail"].items()}
    evals: dict[str, float] = {}
    for it in pl.items("timing"):
        c = next(x for x in pl.data["cells"] if x["arm"] == it["arm"] and x["slots"] == it["slots"])
        cell = core.make_cell(pl.mode, c["arm"], c["facts"], c["slots"], c["draw"], c["init_seed"], u_p=c["u_p"], run=eval_update, lr=c["lr"])
        spec = {**c, "mode": pl.mode, "snapshots": [eval_update], "run": eval_update, "label": cell.label, "ladder_cell": False}
        data, sd = items.load_data(ctx, spec, verify=False)
        adapter.train_to(data, sd, items.backbone_of(ctx), ctx.run_dir, spec, eval_update, mode=pl.mode, cfg=cfg)
        t0 = time.monotonic()
        items.evaluate_snapshot(ctx, spec, eval_update, data=data, seeds=sd)
        evals[f"{it['arm']}|{it['slots']}"] = time.monotonic() - t0
    tg = time.monotonic()
    stages.run_gates(pl, ctx, ctx.run_dir, repo=core.repo_root(), run_checker=False, adapter_identity=False)
    gates_s = time.monotonic() - tg  # the gates stage (the registry checker, run once more, adds seconds not counted here)
    base_s = 0.0
    for facts in sorted({c["facts"] for c in pl.data["cells"]}):
        c = next(x for x in pl.data["cells"] if x["facts"] == facts)
        tb = time.monotonic()
        items.baseline_item(ctx, c["draw"], facts, {**c, "mode": pl.mode})
        base_s += (time.monotonic() - tb) * len({x["draw"] for x in (candidate or pl).data["cells"]})  # one baseline per (draw, row): the draws of the REGISTERED plan
    t1 = time.monotonic()
    try:
        res = analysis.analyze(synthetic_registry_for(candidate or pl))
    except Exception:  # noqa: BLE001 - a plan that is not the registry (a tiny plan) has no synthetic registry
        res = {"status": "NOT RUN"}
    t2 = time.monotonic()
    if res["status"] == "COMPLETE":
        report.render(res)
    t3 = time.monotonic()
    item_keys = [f"{it['arm']}|{it['slots']}" for it in pl.items("timing")]
    by: dict[str, Any] = {}
    for k in workers_list:
        tasks = [(str(plan_path), str(ctx.run_dir), str(ctx.config_path or ""), key.split("|")[0], int(key.split("|")[1]), synthetic_data, warmup, updates, repeats, eval_update) for key in item_keys]
        with mp.get_context("spawn").Pool(k) as pool:
            got = pool.map(_concurrent_timing, tasks, chunksize=1)
        ratios = {g["item"]: max(1.0, g["wall"] / wall_iso[g["item"]]) for g in got}
        worst = max(ratios, key=lambda i: ratios[i])
        by[str(k)] = {"contention_worst_item": worst, "train": dict(cpu), "evaluate": {g["item"]: max(g["evaluate_seconds"], evals[g["item"]]) for g in got}, "contention": max(ratios.values()), "contention_by_item": ratios, "peak_rss_bytes_per_worker": max(g["peak_rss_bytes"] for g in got), "workers": k}
    fixed = {"gates": gates_s, "baselines": base_s, "timing": sum(float(v) * (warmup + repeats * updates) for v in cpu.values()), "analysis": t2 - t1, "report": t3 - t2, "throughput": 420.0}
    for v in by.values():
        v["fixed"] = fixed
    return {
        "by_workers": by, "machine": {"before": machine_before, "after": {"load_average_1m": os.getloadavg()[0], "other_study_processes": quiet_mod.other_study_processes()}}, "timing_config": {"warmup_updates": warmup, "updates": updates, "repeats": repeats}, "fixed_notes": {"throughput": "P10-S1's figure (about 7 minutes), stated not measured", "analysis_report": "measured on a synthetic registry keyed by the plan's labels"}, "peak_rss_bytes_main": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "seconds": time.monotonic() - began, "draw": "rehearsal", "platform": gates.platform_record(),
    }  # fmt: skip


# --- the record and the counting rehearsal ----------------------------------------------------------------------------------------------------------------
def write_rehearsal_record(path: Path, *, caps_provisional: bool, stage_status: Mapping[str, str], candidate: Mapping[str, Any], qualification: Mapping[str, Any] | None, kind: str, notes: str = "") -> dict[str, Any]:
    """The rehearsal record the freeze reads: ``stages``, ``caps_provisional`` (a measuring rehearsal is made on provisional caps and cannot be frozen on), ``candidate`` (the SHA-256 of the plan file rehearsed), the R2
    qualification table, the workers' settings."""
    rec = {**core.envelope("rehearsal"), "rehearsal_kind": kind, "caps_provisional": caps_provisional, "stages": {k: {"status": v} for k, v in stage_status.items()}, "candidate": dict(candidate), "qualification": dict(qualification or {}), "platform": gates.platform_record(), "notes": notes}
    core.write_record(path, rec, overwrite=True)
    return rec


def run_counting(plan_path: Path, run_dir: Path, *, repo: Path, config_path: Path | None = None, synthetic_data: bool = False, inline: bool = False, workers: int = 6, qualification: Mapping[str, Any] | None = None, record_path: Path | None = None, quiet_reading: Any = None, end_fn: Any = None, sleep: Any = None, chain: Sequence[str] = REHEARSAL_STAGE_CHAIN, resume: bool = False, clock: Any = None) -> dict[str, Any]:
    """The counting rehearsal (see the module docstring). ``chain`` names the stage functions to run (a test of the record alone passes ``()``; the lead's run uses the whole chain). The quiet stages (timing,
    throughput) run through the SAME ``stages.execute_stage`` as the registered launch, with the config's measured rule (``quiet.quiet_reading``, ``quiet.end_check``) unless a test injects a reading. ``resume=True``
    (ADR-0024 addendum A8 item 6): the run directory already exists; a stage whose manifest says COMPLETE is NOT run again, a PAUSED one is retried by itself; the record is COMPLETE only when every stage, both quiet
    stages included, has a quiet run. The seconds spent waiting for a quiet reading are returned (``waited_seconds``) and are not charged."""
    cfg = core.load_config(config_path) if config_path else core.load_config(repo / core.CONFIG)
    run_dir.mkdir(parents=True, exist_ok=True)
    pl = planmod.Plan.load(plan_path)
    view = rehearsal_view(pl, run_dir, cfg)
    vpath = view.path or plan_path
    ctx = items.Ctx(view.mode, run_dir, None, synthetic=synthetic_data, sizes=dict(view.data.get("sizes") or {"table_facts": 32768, "unseen": 2048}), config_path=config_path)
    if not synthetic_data:
        from . import freeze as fz

        ctx.experiments_root = fz.experiments_root()
    args = argparse.Namespace(freeze_commit=None, synthetic=synthetic_data)
    status: dict[str, str] = {}
    waited = 0.0
    for st in chain:
        mpath = run_dir / st / "manifest.json"
        if resume and mpath.is_file() and core.read_record(mpath, "stage_manifest")["status"] == "COMPLETE":
            status[st] = "COMPLETE"  # completed stages are not run again
            continue
        kw: dict[str, Any] = {"quiet_reading": quiet_reading, "end_fn": end_fn, "sleep": sleep, **({"clock": clock} if clock is not None else {})} if quiet_reading is not None else {}
        rec = stages.execute_stage(st, view, ctx, run_dir, vpath, args, repo=repo, inline=inline, workers=workers, **kw)
        status[st] = rec["status"]
        waited += float(rec.get("waited_seconds_not_charged", 0.0))
        if rec["status"] != "COMPLETE":
            break
    chk = check_plan_items(pl)
    try:
        res = analysis.analyze(synthetic_registry_for(pl))
        ok = chk["passed"] and res["status"] == "COMPLETE" and bool(report.render(res))
    except Exception:  # noqa: BLE001 - a registry that cannot be rendered is a failed rehearsal stage
        ok = False
    status["analysis"] = status["report"] = "COMPLETE" if ok else "FAILED"
    cand = {"status": "COMPLETE" if all(v == "COMPLETE" for v in status.values()) else "FAILED", "plan_file_sha256": file_sha256(plan_path), "item_counts": chk["counts"], "item_problems": chk["problems"]}
    rec2 = write_rehearsal_record(record_path or run_dir / "rehearsal.json", caps_provisional=bool(pl.data.get("caps_provisional", True)), stage_status=status, candidate=cand, qualification=qualification, kind="counting")
    return {"stages": status, "candidate": cand, "record": rec2, "run_dir": str(run_dir), "waited_seconds": waited}


def cmd_rehearse(args: argparse.Namespace) -> int:
    """``rehearse``: the synthetic chain (default); ``--measuring --plan P --rates-out F --workers 6,7`` the measuring rehearsal's rates file; ``--counting --plan P --record-out F [--qualification Q]`` the counting rehearsal."""
    from . import rehearsal as rh

    repo = Path(args.repo) if args.repo else core.repo_root()
    root = Path(args.run_dir)
    resume = bool(getattr(args, "resume", False))
    if resume and not args.counting:
        raise core.StageRefused("refused: --resume belongs to the counting rehearsal (a PAUSED quiet stage is retried by itself in the same directory)")
    if root.exists() and any(root.iterdir()) and not resume:
        raise core.StageRefused(f"refused: {root} is not a new rehearsal directory (a PAUSED counting rehearsal continues with --resume)")
    if resume and not (root / "view_plan.json").is_file():
        raise core.StageRefused(f"refused: {root} holds no counting rehearsal to resume")
    planmod.require_ignored_run_dir(repo, root)
    if not (args.measuring or args.counting):
        rec = rh.run_synthetic(root, repo=repo)
        ok = all(v["status"] == "COMPLETE" for v in rec["stages"].values())
        print(json.dumps({"synthetic": {k: v["status"] for k, v in rec["stages"].items()}, "ladder_u_run": rec["ladder"], "passed": ok}))
        return 0 if ok else 1
    gates.configure_worker()
    if not args.plan:
        raise core.StageRefused("refused: --plan (the candidate plan file) is required")
    root.mkdir(parents=True, exist_ok=resume)
    plan_path = Path(args.plan)
    if args.measuring:
        from . import freeze as fz

        cand = planmod.Plan.load(plan_path)
        view = rehearsal_view(cand, root, core.load_config(repo / core.CONFIG))
        ctx = items.Ctx(view.mode, root, fz.experiments_root(), sizes=dict(view.data.get("sizes") or {}))
        out = measure_rates(view, ctx, view.path or plan_path, [int(w) for w in args.workers.split(",")], candidate=cand)
        Path(args.rates_out).write_text(json.dumps(core.jsonable(out), indent=2, sort_keys=True) + "\n")
        print(json.dumps({"rates_file": args.rates_out, "contention_worst_item_used_by_the_rule": {k: v["contention"] for k, v in out["by_workers"].items()}, "contention_by_item": {k: v["contention_by_item"] for k, v in out["by_workers"].items()}}))
        core.prefreeze_ledger(root).charge("measuring-rehearsal", root.name, out["seconds"])
        return 0
    q = read_json(Path(args.qualification))["table"] if args.qualification else None
    t_count = time.monotonic()
    with machine.keep_awake():  # a child of this process: inside its own process family
        res = run_counting(plan_path, root, repo=repo, qualification=q, record_path=Path(args.record_out) if args.record_out else None, resume=resume, chain=REHEARSAL_STAGE_CHAIN)
    print(json.dumps({"stages": res["stages"], "candidate": res["candidate"]["status"], "waited_seconds_not_charged": res["waited_seconds"]}))
    core.prefreeze_ledger(root).charge("counting-rehearsal", root.name, max(0.0, time.monotonic() - t_count - float(res["waited_seconds"])))  # the waiting for a quiet reading is recorded, never charged
    return 0 if res["candidate"]["status"] == "COMPLETE" else 1


def cmd_qualify(args: argparse.Namespace) -> int:
    """``qualify --sealed-dir D --run-dir R --calibration PUBLIC.json``: R2 through every validity check on the rehearsal and both calibration draws; the work goes into the sealed directory, the public table (conditions only) into R."""
    from . import freeze as fz
    from . import sealed

    sd = sealed.check_sealed_dir(Path(args.sealed_dir))
    cfg = core.load_config()
    cal = read_json(Path(args.calibration))
    rows: dict[int, tuple[int, int, int, float]] = {}
    for k, v in cfg["grid"]["r2_reference_cell"].items():
        f, n = int(v[0]), int(v[1])
        rows[int(k)] = (f, n, int(cal["row_u_p"][str(k)]), float(cal["rates"][core.unit_key("R2", f, n, cfg)]))
    began = time.monotonic()
    out = run_r2_qualification(sd, rows, [("rehearsal", core.REHEARSAL, 1), ("cal1", "calibration", 1), ("cal2", "calibration", 2)], cfg=cfg, experiments_root=fz.experiments_root())
    core.prefreeze_ledger(Path(args.run_dir)).charge("qualify", Path(args.run_dir).name, time.monotonic() - began)
    Path(args.run_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.run_dir) / "qualification.json").write_text(json.dumps(core.jsonable({"table": out["table"], "failures": out["failures"], "rule": out["rule"]}), indent=2, sort_keys=True) + "\n")
    print(json.dumps({"qualification": str(Path(args.run_dir) / "qualification.json"), "failures": len(out["failures"])}))
    return 0
