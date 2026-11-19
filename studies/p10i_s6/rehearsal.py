# ruff: noqa: E501
"""P10IS6 rehearsals R1, R2, R3 (ADR-0031 section 16, requirement 1). They drive the SAME entry point as the registered run: every training, evaluation, gate and probe is a fresh ``python -m studies.p10i_s6.stages work ...`` process built by
``stages.make_tasks`` and run by ``stages.run_stage`` (the registered stage driver), only with a plan of mode ``rehearsal`` (never registered: the registered entry refuses those). ``launch/rehearse.sh`` is the launch script.

R1  calibration: rounds of calibration items (grid, then the extensions of section 8), the interior rule, NEG-REF and planted-positive gates on each calibration M-FLAT checkpoint at the last rung, the prefix and resume identity gates, the sealed
    archive (outside every git working tree), ``rehearsal_public.json`` (rate table, interior flags, gates, seconds, storage, sealed hash; NO loss, delta or convergence state).
R2  measuring rehearsal on PROVISIONAL caps: whole-process probes (overhead, training, one evaluation mode each) run ``workers`` at once, and the gates stage; per-process overhead is kept SEPARATE from per-unit rates (``cost.unit_costs_from_probes``).
    It cannot be frozen on.
R3  counting rehearsal: every registered stage end to end in the DRY profile (shortened ladder, the real rate table, dry seeds, calibration pool and panel only) against the candidate ``plan.json``, whose SHA-256 goes into the record. The DRY values stay in the sealed folder.
"""

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import analysis, calibration, core, cost, gates, items, model, runner, stages
from . import plan as planmod
from .plan import Plan, StageRefused

PUBLIC = "rehearsal_public.json"


# --- the public record (whitelist) ------------------------------------------------------------------------------------------------------------------
def update_public(run_dir: Path, **fields: Any) -> dict[str, Any]:
    """``rehearsal_public.json`` accumulates R1, R2 and R3. Every write passes the public guard (forbidden measure names as plain substrings, opaque hashes exempt)."""
    path = run_dir / PUBLIC
    rec = core.read_record(path, "rehearsal_public") if path.is_file() else {**core.envelope("rehearsal_public"), "stages": {}}
    stg = {**rec.get("stages", {}), **fields.pop("stages", {})}
    rec = {**rec, **fields, "stages": stg}
    problems = calibration.public_guard({k: v for k, v in rec.items() if k != "whitelist_note"})
    if problems:
        raise core.EngineeringStop(f"ENGINEERING STOP — the public rehearsal file would carry forbidden names: {problems[:5]}")
    core.write_record(path, rec, overwrite=True)
    return rec


def make_plan(repo: Path, run_dir: Path, phase: str, plan_items: Mapping[str, Any], k_max: int, rate_table: Mapping[str, Any], *, cfg_override: Mapping[str, Any] | None, synthetic: bool, data_extra: Mapping[str, Any] | None, provisional: bool = True, projected_hours: float | None = None) -> tuple[Plan, Path]:
    cfg = core.load_config(repo / core.CONFIG)
    extra: dict[str, Any] = {**dict(data_extra or {}), "cfg_override": dict(cfg_override or {}), "synthetic": synthetic}
    rec = planmod.build_plan(mode=planmod.REHEARSAL, cfg=cfg, repo=repo, run_dir=run_dir, rate_table=rate_table, k_max=k_max, projected_remaining_hours=None if provisional else (projected_hours or 0.0), extra=extra, plan_items=plan_items)
    path = run_dir / phase / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    core.write_record(path, rec, overwrite=True)
    return Plan(rec, path), path


def _run(stage: str, plan: Plan, repo: Path, plan_path: Path, items_dir: Path, state_dir: Path, run_dir: Path) -> int:
    runner.record_stage_start(run_dir, f"rehearsal-{stage}")
    return stages.execute_stage(stage, plan, repo, items_dir, plan_path, mode="rehearsal", identity={"mode": "rehearsal"}, state_dir=state_dir, out_dir=state_dir)


def data_extra_for(args: Mapping[str, Any]) -> dict[str, Any]:
    """The plan's data fields for a real rehearsal (the same fields ``candidate-plan`` records for the registered plan)."""
    if args.get("synthetic"):
        return {}
    dm = Path(args["data_manifest"]).resolve()
    extra: dict[str, Any] = {"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_dir": str(Path(args["parent_dir"]).resolve()), "parent_suite": str(Path(args["parent_suite"]).resolve())}
    extra["parent_files"] = {str(p): file_sha256(p) for p in sorted(Path(args["parent_dir"]).resolve().glob("*.pt"))}
    if args.get("parents_record"):
        pr = Path(args["parents_record"]).resolve()
        extra["parents_record"] = {"path": str(pr), "sha256": file_sha256(pr)}
    return extra


# --- R1 -------------------------------------------------------------------------------------------------------------------------------------------------
def curves_from_records(items_dir: Path, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], arm: str, durations: Sequence[int]) -> dict[float, dict[int, dict[int, float | None]]]:
    """``curves[rate][cell][updates]`` of the calibration cells from the evaluation records: the enabled NLL, None once the run failed (no snapshot, a skipped record, or a non-finite value) and for every later duration (ruling 5)."""
    out: dict[float, dict[int, dict[int, float | None]]] = {}
    trains = {t["id"]: t for t in plan_items["train"] if t["arm"] == arm}
    for tid, t in trains.items():
        rec = core.read_record(items.train_record_path(items_dir, t), "train")
        if rec["status"] == "item_error":
            raise core.EngineeringStop(f"ENGINEERING STOP — ITEM ERRORS: {tid}")
        cell: dict[int, float | None] = dict.fromkeys(durations)
        dead = False
        for e in sorted((e for e in plan_items["eval"] if e["train"] == tid), key=lambda e: e["update"]):
            er = core.read_record(items.eval_record_path(items_dir, e), "eval")
            v = None if dead or "skipped" in er else er["reads"].get(f"{core.READ_ENABLED}|0")
            if v is None:
                dead = True
            if e["update"] in cell:
                cell[e["update"]] = v
        out.setdefault(float(t["rate"]), {})[int(t["cell"])] = cell
    return out


def run_r1(repo: Path, run_dir: Path, sealed_dir: Path, *, synthetic: bool = False, cfg_override: Mapping[str, Any] | None = None, data_args: Mapping[str, Any] | None = None, k_max: int | None = None) -> int:
    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    stages.deep_update(cfg, cfg_override or {})
    if k_max is None:
        if synthetic:
            k_max = int(cfg.get("synthetic", {}).get("k_max", 2))
        else:
            k_max = int(read_json(Path(data_args["data_manifest"]))["k_max"])  # type: ignore[index]
    planmod.require_ignored_path(repo, run_dir / "x")
    extra = data_extra_for({**(data_args or {}), "synthetic": synthetic})
    grid = {a: [float(x) for x in cfg["rates"]["grid"]] for a in core.ARMS}
    have: dict[str, list[float]] = {a: [] for a in core.ARMS}
    todo = {a: list(grid[a]) for a in core.ARMS}
    durations = calibration.durations_of(cfg, k_max)
    all_items: dict[str, list[dict[str, Any]]] = {"train": [], "eval": []}
    seconds = 0.0
    rounds = 0
    stop: str | None = None
    while any(todo.values()):
        rounds += 1
        if rounds > int(cfg["rehearsal"]["r1_max_rounds"]):
            raise core.EngineeringStop("ENGINEERING STOP — CALIBRATION NOT INTERIOR: the extension rounds are used up")
        rnd = items.calibration_items(cfg, todo, k_max)
        for kind in ("train", "eval"):
            all_items[kind] += rnd[kind]
        for a in core.ARMS:
            have[a] += todo[a]
        plan, plan_path = make_plan(repo, run_dir, f"r1/round{rounds}", rnd, k_max, {"rates": {a: {} for a in core.ARMS}}, cfg_override=cfg_override, synthetic=synthetic, data_extra=extra)
        state = sealed_dir / "state" / f"round{rounds}"
        for stage in ("train", "eval"):
            code = _run(stage, plan, repo, plan_path, sealed_dir, state, run_dir)
            seconds += float((runner.read_manifest(state, stage) or {"charged_seconds": 0.0})["charged_seconds"])
            if code != 0:
                core.log_attempt(run_dir, "R1 stage not complete", stage=stage, round=rounds)
                update_public(run_dir, stages={"R1": {"status": "PAUSED", "round": rounds, "stage": stage}})
                return 1
        curves = {a: curves_from_records(sealed_dir, all_items, a, durations) for a in core.ARMS}
        todo = {a: [] for a in core.ARMS}
        for a in core.ARMS:
            dec = calibration.extension_decision(curves[a], durations, cfg)
            if dec["stop"]:
                stop = f"{a}: {dec['stop']}"
            for side in ("up", "down"):
                if dec[side] is not None:
                    todo[a].append(float(dec[side]))
        if stop:
            update_public(run_dir, stages={"R1": {"status": "ENGINEERING STOP", "reason": stop}})
            raise core.EngineeringStop(stop)
    rt = calibration.rate_table(curves, cfg, k_max)
    if not all(all(v.values()) for v in rt["interior"].values()):
        raise core.EngineeringStop("ENGINEERING STOP — CALIBRATION NOT INTERIOR")
    # gates: identity (prefix and resume) through the stage driver, then NEG-REF and the planted positive on each calibration M-FLAT checkpoint at the last rung
    gplan, gpath = make_plan(repo, run_dir, "r1/gates", {"train": [], "eval": []}, k_max, rt, cfg_override=cfg_override, synthetic=synthetic, data_extra=extra)
    gstate = sealed_dir / "state" / "gates"
    if _run("gates", gplan, repo, gpath, sealed_dir, gstate, run_dir) != 0:  # the same stage driver and fresh worker processes as the registered gates stage (core gate and both identity gates)
        update_public(run_dir, stages={"R1": {"status": "PAUSED", "stage": "gates"}})
        return 1
    ident = {a: core.read_record(stages.gate_path(gstate, f"identity|{a}"), "gate") for a in core.ARMS}
    res = stages.resources_for(gplan, repo, cfg_for_plan(gplan, repo))
    pp = model.planted_positive(cfg, core.Seeds("test", cfg))
    neg: dict[str, Any] = {}
    seeds = core.Seeds("calibration", cfg)
    for t in [t for t in all_items["train"] if t["arm"] == core.FLAT and abs(float(t["rate"]) - float(rt["rates"][core.FLAT][str(k_max)])) == 0.0]:
        snap = items.item_dir(sealed_dir, t["id"]) / "snapshots"
        m = items._build(res, t)
        model.restore_snapshot(snap, m, core.rung_updates(cfg, k_max), items._identity(t))
        r = model.neg_ref_check(m, res.panels["calibration"], seeds, cfg, cell=int(t["cell"]), expected_targets=res.expected_targets)
        neg[f"c{t['cell']}"] = r["passed"]
    gate_rec = {"identity": {a: ident[a]["passed"] for a in core.ARMS}, "planted_positive": pp["passed"], "neg_ref": neg}
    if not (all(gate_rec["identity"].values()) and pp["passed"] and neg and all(neg.values())):
        update_public(run_dir, gates=gate_rec, stages={"R1": {"status": "ENGINEERING STOP", "reason": "a calibration gate failed"}})
        raise core.EngineeringStop(f"ENGINEERING STOP — a calibration gate failed: {gate_rec}")
    states = calibration.calibration_states(curves, rt, cfg, k_max)
    sealed = calibration.sealed_bytes(curves, states, {"rounds": rounds, "rates_run": {a: sorted(have[a]) for a in core.ARMS}})
    sha = calibration.write_sealed(sealed_dir / "rehearsal_sealed.json", repo, sealed, cfg, allow_inside_repo=synthetic)
    storage = sum(f.stat().st_size for f in sealed_dir.rglob("state.pt"))
    pub = calibration.public_summary(curves, cfg, k_max, gates=gate_rec, seconds={"r1_charged_seconds": seconds, "rounds": rounds}, storage={"snapshot_bytes": storage}, sealed_sha256=sha, rule_hashes=planmod.rule_hashes(repo))
    update_public(run_dir, rate_table=pub["rate_table"], gates=pub["gates"], seconds=pub["seconds"], storage=pub["storage"], sealed_sha256=sha, rule_hashes=pub["rule_hashes"], k_max=k_max, stages={"R1": {"status": "COMPLETE", "rounds": rounds}})
    return 0


def cfg_for_plan(plan: Plan, repo: Path) -> dict[str, Any]:
    return stages.cfg_for(plan, repo)


# --- R2 -------------------------------------------------------------------------------------------------------------------------------------------------
def run_r2(repo: Path, run_dir: Path, sealed_dir: Path, *, rate_table: Mapping[str, Any], k_max: int, synthetic: bool = False, cfg_override: Mapping[str, Any] | None = None, data_args: Mapping[str, Any] | None = None) -> int:
    """The measuring rehearsal on provisional caps. Whole-process probes through ``stages work r2probe`` (fresh processes, ``workers`` at once), then the gates stage; the record is ``r2/r2_record.json`` and a line in the public file."""
    import sys

    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    stages.deep_update(cfg, cfg_override or {})
    planmod.require_ignored_path(repo, run_dir / "x")
    extra = data_extra_for({**(data_args or {}), "synthetic": synthetic})
    plan, plan_path = make_plan(repo, run_dir, "r2", {"train": [], "eval": []}, k_max, rate_table, cfg_override=cfg_override, synthetic=synthetic, data_extra=extra, provisional=True)
    workers = int(plan.data["workers"])
    n_up, n_ev = int(cfg["rehearsal"]["r2_updates"]), int(cfg["rehearsal"]["r2_evals"])
    pdir = run_dir / "r2" / "probes"
    pdir.mkdir(parents=True, exist_ok=True)
    base = (sys.executable, "-m", "studies.p10i_s6.stages", "work", "r2probe", "--run-dir", str(sealed_dir), "--state-dir", str(sealed_dir / "state" / "r2"), "--plan", str(plan_path), "--repo", str(repo))
    specs: list[dict[str, Any]] = [{"label": f"overhead-{i}", "probe": "overhead", "arm": None, "mode": None, "count": 1} for i in range(workers)]
    specs += [{"label": f"train-{a}-{i}", "probe": "train", "arm": a, "mode": None, "count": n_up} for a in core.ARMS for i in range(workers)]
    specs += [{"label": f"eval-{a}-{m}", "probe": "eval", "arm": a, "mode": m, "count": n_ev} for a in core.ARMS for m in core.MODES]
    tasks = []
    for s in specs:
        out = pdir / f"{s['label']}.json"
        argv = (*base, "--probe", s["probe"], "--out", str(out), "--count", str(s["count"]), *(("--arm", s["arm"]) if s["arm"] else ()), *(("--mode", s["mode"]) if s["mode"] else ()))
        tasks.append(runner.Task(s["label"], argv, out, pdir / f"{s['label']}.failed.json", pdir / f"{s['label']}.log"))
    runner.record_stage_start(run_dir, "rehearsal-r2")
    outcomes, _ = runner.run_tasks(tasks, workers=workers, cap_seconds=plan.cap_seconds(), rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=run_dir)
    bad = {k: v["status"] for k, v in outcomes.items() if v["status"] != runner.COMPLETED}
    if bad:
        core.log_attempt(run_dir, "R2 probes not complete", bad=bad)
        update_public(run_dir, stages={"R2": {"status": "PAUSED", "not_complete": sorted(bad)}})
        return 1
    ov = [outcomes[f"overhead-{i}"]["seconds"] for i in range(workers)]
    probes = [{"arm": s["arm"], "kind": s["probe"], "seconds": outcomes[s["label"]]["seconds"], **({"updates": s["count"]} if s["probe"] == "train" else {"evals": {m: (s["count"] if m == s["mode"] else 0) for m in core.MODES}})} for s in specs if s["probe"] != "overhead"]
    gstate = sealed_dir / "state" / "r2-gates"
    code = _run("gates", plan, repo, plan_path, sealed_dir, gstate, run_dir)
    gman = runner.read_manifest(gstate, "gates")
    if code != 0 or gman is None:
        update_public(run_dir, stages={"R2": {"status": "PAUSED", "stage": "gates"}})
        return 1
    gates_seconds = sum(float(t["seconds"]) for t in gman["tasks"].values())
    unit = cost.unit_costs_from_probes({"seconds": sum(ov) / len(ov)}, probes, workers, gates_seconds)
    rec = {**core.envelope("rehearsal_public"), "unit_costs": unit, "probes": probes, "overhead_probe_seconds": ov, "caps_provisional": True, "workers_settings": gates.platform_record(), "provisional_note": "a measuring rehearsal cannot be frozen on"}
    write_json(run_dir / "r2" / "r2_record.json", rec)
    update_public(run_dir, stages={"R2": {"status": "COMPLETE", "caps_provisional": True}}, r2_record_sha256=file_sha256(run_dir / "r2" / "r2_record.json"))
    return 0


# --- R3 -------------------------------------------------------------------------------------------------------------------------------------------------
def dry_override(cfg: Mapping[str, Any], base: Mapping[str, Any] | None) -> dict[str, Any]:
    """The DRY profile's shortened ladder (``[rehearsal]``), merged over any synthetic override."""
    r = cfg["rehearsal"]
    out = copy.deepcopy(dict(base or {}))
    lad = {**cfg["ladder"], **out.get("ladder", {}), "base_updates": int(r["dry_base_updates"]), "below_updates": int(r["dry_below_updates"])}
    out["ladder"] = lad
    return out


def run_r3(repo: Path, run_dir: Path, sealed_dir: Path, *, synthetic: bool = False, cfg_override: Mapping[str, Any] | None = None, data_args: Mapping[str, Any] | None = None) -> int:
    """Every registered stage end to end in the DRY profile against the candidate ``freeze/plan.json`` (non-provisional caps required); its SHA-256 goes into the record."""
    cand_path = repo / core.PLAN
    cand = Plan.load(cand_path)
    if cand.mode != planmod.REGISTERED or cand.data.get("caps_provisional"):
        raise StageRefused("refused: R3 runs against a candidate plan with caps computed from R2 (a provisional plan is not rehearsed)")
    cfg = core.load_config(repo / core.CONFIG)
    ov = dry_override(cfg, cfg_override)
    dcfg = copy.deepcopy(dict(cfg))
    stages.deep_update(dcfg, ov)
    k_max = cand.k_max
    plan_items = items.registered_items(dcfg, cand.rate_table, k_max, profile="dry", cells=[0, 1, 2], oa_cells=[0, 1, 2])
    plan, plan_path = make_plan(repo, run_dir, "r3", plan_items, k_max, cand.rate_table, cfg_override=ov, synthetic=synthetic, data_extra=data_extra_for({**(data_args or {}), "synthetic": synthetic}), provisional=False, projected_hours=cand.data["caps"]["registered_hours"] / 2.0)
    state = sealed_dir / "state" / "r3"
    done: dict[str, Any] = {}
    for stage in ("gates", "train", "eval", "analysis", "report"):
        code = _run(stage, plan, repo, plan_path, sealed_dir, state, run_dir)
        done[stage] = {"status": "COMPLETE" if code == 0 else "NOT COMPLETE", "exit": code}
        if code != 0:
            core.log_attempt(run_dir, "R3 stage not complete", stage=stage, exit=code)
            update_public(run_dir, stages={"R3": {"status": "PAUSED", "stages": done}})
            return 1
    update_public(run_dir, candidate={"plan_file_sha256": file_sha256(cand_path)}, caps_provisional=False, stages={"R3": {"status": "COMPLETE", "stages": done}})
    return 0


def main(argv: Sequence[str]) -> int:  # called by ``stages rehearse``
    import argparse

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.stages rehearse")
    ap.add_argument("phase", choices=("r1", "r2", "r3"))
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--sealed-dir", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--data-manifest")
    ap.add_argument("--parent-dir")
    ap.add_argument("--parent-suite")
    ap.add_argument("--parents-record")
    ap.add_argument("--rate-table", help="r2: a rate table file (default: freeze/rate_table.json)")
    ap.add_argument("--k-max", type=int)
    ap.add_argument("--synthetic-json", help="a JSON file {cfg_override: {...}}: a synthetic rehearsal on tiny inputs (tests); never a real run")
    a = ap.parse_args(list(argv))
    repo = Path(a.repo or core.repo_root())
    syn = json.loads(Path(a.synthetic_json).read_text()) if a.synthetic_json else None
    ov = (syn or {}).get("cfg_override")
    data_args = {"data_manifest": a.data_manifest, "parent_dir": a.parent_dir, "parent_suite": a.parent_suite, "parents_record": a.parents_record}
    run_dir, sealed = Path(a.run_dir).resolve(), Path(a.sealed_dir).resolve()
    if a.phase == "r1":
        return run_r1(repo, run_dir, sealed, synthetic=syn is not None, cfg_override=ov, data_args=data_args, k_max=a.k_max)
    if a.phase == "r2":
        rt = read_json(Path(a.rate_table) if a.rate_table else repo / core.RATE_TABLE)
        km = a.k_max if a.k_max is not None else (int(read_json(Path(a.data_manifest))["k_max"]) if a.data_manifest else 2)
        return run_r2(repo, run_dir, sealed, rate_table=rt, k_max=km, synthetic=syn is not None, cfg_override=ov, data_args=data_args)
    return run_r3(repo, run_dir, sealed, synthetic=syn is not None, cfg_override=ov, data_args=data_args)


__all__ = ["analysis", "main"]
