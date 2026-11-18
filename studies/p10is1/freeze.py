# ruff: noqa: E501
"""P10IS1 freeze commands (ADR-0024 sections 11, 17.1, 18): ``generate`` (the draws' manifests: generating a draw is not an observation of a seed by a model), ``candidate-plan`` (writes ``freeze/plan.json`` first; refuses to
overwrite without ``--supersede``, which moves the old file to ``freeze/superseded/``), ``project`` (the projection of section 17.1, once: granted lengths and caps from the measuring rehearsal's rates), ``freeze`` (writes
``freeze/freeze_record.json`` for the committed candidate plan), ``caps-proposal``.

``freeze`` REFUSES unless: the candidate plan exists and its caps are not provisional (the caps are set from the measuring rehearsal and the plan rewritten); the plan is not BASE PLAN ABOVE BUDGET; the plan re-derived from the
current code, config and calibration record equals the committed one (the ADR's hash is not compared); the counting rehearsal's record was made on caps that are not provisional, shows every stage COMPLETE and names the SHA-256
of THIS plan file; gate G9 passes with the registry's checker. It writes only the freeze record. The freeze commit is the human lead's act; nothing here is a freeze until those commands are run and committed.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import budget, core, gates, items
from . import plan as planmod
from .plan import StageRefused

REHEARSAL_STAGES = ("gates", "timing", "train", "ladder", "evaluate", "baselines", "analysis", "report", "throughput")
NOT_COMPARED = ("adr", "platform")  # the ADR is recorded for provenance only; the platform block is the freezing process's own


def experiments_root() -> Path:
    from studies.p9 import core as p9core

    return Path(p9core.default_experiments_root())


def manifest_path(run_dir: Path, name: str) -> Path:
    return run_dir / "draws" / name / "data_manifest.json"


def cmd_generate(args: argparse.Namespace) -> int:
    """The five block M draws (complete P10-S1-style draws), hashed: nothing is trained or read on them. Each draw is generated once."""
    from studies.p10s1 import core as s1

    cfg = core.load_config()
    run_dir = Path(args.run_dir)
    ctx = items.Ctx(core.REGISTERED, run_dir, experiments_root())
    for d in range(1, int(cfg["seeds"]["registered_draws"]) + 1):
        seeds, init = core.seeds_for(core.REGISTERED, d, cfg)
        path = manifest_path(run_dir, seeds.name)
        if path.exists():
            raise StageRefused(f"refused: {path} exists; a draw is generated once")
        began = time.monotonic()
        spec = {"seed_name": seeds.name, "seed_base": seeds.facts, "init_seed": init, "draw": d, "mode": core.REGISTERED}
        data, _ = items.load_data(ctx, spec, verify=False)
        core.write_record(path, {**core.envelope("snapshot"), "seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": s1.FACT_TABLE, "unseen": s1.UNSEEN_FACTS, "sha256s": data.sha256s(), "seed_values": sorted(core.seed_set_values(seeds)), "seconds": time.monotonic() - began})
        print(json.dumps({"draw": seeds.name, "manifest": str(path), "sha256": file_sha256(path)}))
    return 0


def params_from_calibration(record: dict[str, Any], granted: dict[str, int] | None = None) -> core.PlanParams:
    """``PlanParams`` from a complete calibration record (rates, U_P per row, U0 per ladder cell, 2K/256 run or not). The granted length of each ladder cell is 4 x U0 (every loaded cell listed to 4 x U0) until the
    projection of section 17.1 fixes it."""
    if not record.get("complete"):
        raise StageRefused("refused: the calibration record is not complete (a return to the human lead is open): no plan is written")
    u0 = {k: int(v) for k, v in record["u0"].items()}
    return core.PlanParams({int(k): int(v) for k, v in record["row_u_p"].items()}, {k: float(v) for k, v in record["rates"].items()}, u0, granted or {k: 4 * v for k, v in u0.items()}, bool(record["sat256"]))


def build_candidate(repo: Path, run_dir: Path, cfg: Any, calibration: dict[str, Any], projection: dict[str, Any] | None, *, manifests: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """The registered plan record: a pure function of the repository, the config, the calibration record, the projection and the draws' manifests. It carries no rehearsal and no attestation."""
    granted = {k: int(v) for k, v in projection["grants"].items()} if projection else None
    params = params_from_calibration(calibration, granted)
    return planmod.build_plan(
        mode=planmod.REGISTERED, cfg=cfg, repo=repo, params=params, run_dir=run_dir, projection=projection,
        extra={"calibration": calibration, "manifests": manifests or {}, "sizes": {"table_facts": int(cfg["grid"]["table_facts"]), "unseen": _unseen()}, **(extra or {})},
    )  # fmt: skip


def _unseen() -> int:
    from studies.p10s1 import core as s1

    return int(s1.UNSEEN_FACTS)


def scientific_content(plan_data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in plan_data.items() if k not in NOT_COMPARED}


def draw_manifests(run_dir: Path, cfg: Any) -> dict[str, Any]:
    out = {}
    for d in range(1, int(cfg["seeds"]["registered_draws"]) + 1):
        name = core.registered_seeds(d, cfg).name
        p = manifest_path(run_dir, name)
        if not p.is_file():
            raise StageRefused(f"refused: {p} does not exist: run generate first")
        out[name] = {"path": str(p), "sha256": file_sha256(p)}
    return out


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write the CANDIDATE ``freeze/plan.json`` once. The measuring rehearsal runs against it on provisional caps; the projection and the caps are then written into it (``--projection``, ``--supersede``) and the counting
    rehearsal runs against that exact file. Refuses to overwrite without ``--supersede``; a freeze record forbids superseding."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    if plan_path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {plan_path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / planmod.FREEZE_RECORD).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(plan_path)
        target = plan_path.parent / "superseded" / f"plan-{old[:12]}.json"
        if target.exists():
            raise StageRefused(f"refused: {target} exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        plan_path.rename(target)
        print(json.dumps({"superseded": str(target), "sha256": old}))
    run_dir = Path(args.run_dir).resolve()
    calibration = read_json(Path(args.calibration))
    projection = read_json(Path(args.projection)) if args.projection else None
    record = build_candidate(repo, run_dir, cfg, calibration, projection, manifests=draw_manifests(run_dir, cfg), extra={"identity_gate": {"s1_run_dir": args.s1_run_dir, "cell": cfg["seeds"]["identity_gate_cell"], "updates": cfg["seeds"]["identity_gate_updates"]}, "calibration_path": str(Path(args.calibration).resolve()), "calibration_sha256": file_sha256(Path(args.calibration))})
    core.write_record(plan_path, record)
    print(json.dumps({"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "cells": len(record["cells"]), "caps_provisional": record["caps_provisional"], "base_plan_above_budget": record["base_plan_above_budget"]}))
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    """The projection of section 17.1, once, from the measuring rehearsal's rates only: the base plan, the levels granted to whole cells, the caps. Writes the projection record (the candidate plan is then rewritten with it)."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    calibration = read_json(Path(args.calibration))
    rates_in = read_json(Path(args.rates))
    cells = core.planned_cells(params_from_calibration(calibration), core.REGISTERED, cfg)
    w = {int(k): v for k, v in rates_in["by_workers"].items()}
    cand = {k: budget.Rates({tuple(x.split("|")[:1]) + (int(x.split("|")[1]),): float(v) for x, v in r["train"].items()}, {tuple(x.split("|")[:1]) + (int(x.split("|")[1]),): float(v) for x, v in r["evaluate"].items()}, float(r["contention"]), r["fixed"], k) for k, r in ((k, w[k]) for k in w)}  # type: ignore[misc]
    base_grants = {k: int(v) for k, v in calibration["u0"].items()}
    chosen = budget.choose_workers(cand, cells, base_grants)
    out = budget.grant_levels(cells, cand[chosen["chosen_workers"]], float(args.charged_hours), cfg)
    out["worker_choice"] = chosen
    if not out["refused"]:
        out["caps"] = budget.caps_from_projection(float(args.charged_hours), out["stage_hours"], cfg)
    Path(args.out).write_text(json.dumps(core.jsonable(out), indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": out["status"], "grants": out["grants"], "total_hours": out["total_hours"], "budget_B_hours": out["budget_B_hours"]}))
    return 0 if not out["refused"] else 3


def cmd_freeze(args: argparse.Namespace) -> int:
    """Write ``freeze/freeze_record.json`` for the committed candidate plan (refusals in the module docstring). It never rewrites the plan."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    plan_path, record_path = repo / core.PLAN, repo / planmod.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    if not plan_path.is_file():
        raise StageRefused("refused: no candidate plan: write it first (candidate-plan), rehearse against it, then freeze")
    plan = planmod.Plan.load(plan_path)
    if plan.data.get("base_plan_above_budget"):
        raise StageRefused(f"refused: {planmod.BASE_PLAN_ABOVE_BUDGET}: the freeze refuses this plan; the work returns to the human lead (section 17.1 item 2)")
    if core.caps_provisional(cfg) or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the caps are set from the measuring rehearsal (section 15) and the candidate plan is rewritten and rehearsed again")
    plan_sha = file_sha256(plan_path)
    calibration = read_json(Path(plan.data["calibration_path"]))
    if file_sha256(Path(plan.data["calibration_path"])) != plan.data["calibration_sha256"]:
        raise StageRefused("refused: the calibration record differs from the one the plan names")
    rederived = build_candidate(repo, Path(plan.data["run_dir"]), cfg, calibration, plan.data["projection"], manifests=draw_manifests(Path(plan.data["run_dir"]), cfg), extra={"identity_gate": plan.data["identity_gate"], "calibration_path": plan.data["calibration_path"], "calibration_sha256": plan.data["calibration_sha256"]})
    if scientific_content(json.loads(json.dumps(core.jsonable(rederived)))) != scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config, calibration record and manifests (something changed after the plan was written): supersede it and rehearse again")
    rehearsal = core.read_record(Path(args.rehearsal), "rehearsal")
    if rehearsal.get("caps_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps (or does not say): the counting rehearsal runs against the plan with the caps set")
    reh = gates.rehearsal_gate(rehearsal, REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    if reh["passed"] is not True:
        raise StageRefused(f"refused: the rehearsal record does not show every stage COMPLETE on non-provisional caps against the candidate plan of SHA-256 {plan_sha}: {reh}")
    seed = gates.seed_gate(cfg, root=repo)
    if seed["passed"] is not True:
        raise StageRefused(f"refused: gate G9 (seeds) did not pass: {seed['problems']}")
    rec = {**core.envelope("freeze_record"), "plan_file_sha256": plan_sha, "rehearsal": {"path": str(Path(args.rehearsal).resolve()), "sha256": file_sha256(Path(args.rehearsal))}, "g9": {k: seed[k] for k in ("passed", "roles", "declared_reuse_not_new", "checker")}, "rehearsal_gate": reh, "adr_sha256_provenance_only": planmod.adr_provenance(repo)["sha256"]}
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record_path), "sha256": file_sha256(record_path), "plan_file_sha256": plan_sha}))
    return 0
