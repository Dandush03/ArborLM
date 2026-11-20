# ruff: noqa: E501
"""P10IS1 freeze commands (ADR-0024 sections 11, 17.1, 18): ``generate`` (the draws' manifests: generating a draw is not an observation of a seed by a model), ``candidate-plan`` (writes ``freeze/plan.json`` first; refuses to
overwrite without ``--supersede``, which moves the old file to ``freeze/superseded/``), ``project`` (the projection of section 17.1, once: granted lengths and caps from the measuring rehearsal's rates), ``freeze`` (writes
``freeze/freeze_record.json`` for the committed candidate plan), ``caps-proposal``.

``freeze`` REFUSES unless: the quiet baseline is not provisional and its figures re-derived from the committed samples equal the config's (ADR-0024 addendum A8 item 3); the candidate plan exists and its caps are not provisional (the caps are set from the measuring rehearsal and the plan rewritten); the plan is not BASE PLAN ABOVE BUDGET; the plan re-derived from the
current code, config and calibration record equals the committed one (the ADR's hash is not compared); the counting rehearsal's record was made on caps that are not provisional, shows every stage COMPLETE and names the SHA-256
of THIS plan file; gate G9 passes with the registry's checker. It writes only the freeze record. The freeze commit is the human lead's act; nothing here is a freeze until those commands are run and committed.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import baseline, budget, core, gates, items
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
    began = time.monotonic()
    try:
        return _generate(cfg, run_dir, ctx, s1)
    finally:
        core.prefreeze_ledger(run_dir).charge("generate", run_dir.name, time.monotonic() - began)  # the hours before the freeze are recorded: they are part of H_c


def _generate(cfg: Any, run_dir: Path, ctx: items.Ctx, s1: Any) -> int:
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


def require_baseline(repo: Path, cfg: Any) -> dict[str, Any]:
    """The candidate plan and the freeze need the quiet baseline: ``[quiet] baseline_provisional`` false, the committed record hashing to the config's SHA-256, and P95, L, the condition and both presences re-derived
    from its samples equal to the config's (a difference, an unsettled window or L above the ceiling refuses). Prints a notice when L is above 250 (a report to the human lead, not a gate)."""
    if core.baseline_provisional(cfg):
        raise StageRefused("refused: [quiet] baseline_provisional is true: the quiet baseline (python -m studies.p10is1.baseline run) has not been taken and written into the config; no candidate plan is written without it (ADR-0024 addendum A3.1 item 8)")
    d = baseline.verify_against_config(repo, cfg)
    if d.get("notice"):
        print(d["notice"], flush=True)
    return d


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write the CANDIDATE ``freeze/plan.json`` once. The measuring rehearsal runs against it on provisional caps; the projection and the caps are then written into it (``--projection``, ``--supersede``) and the counting
    rehearsal runs against that exact file. Refuses to overwrite without ``--supersede``; a freeze record forbids superseding."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    require_baseline(repo, cfg)  # ADR-0024 addendum A3.1 item 8 / A8 item 3: no candidate plan without the study's own quiet baseline written into [quiet]
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
    ledgers = {str(p): core.read_ledger_seconds(Path(p)) / 3600.0 for p in (args.ledger or [])}
    h_c = float(args.charged_hours or 0.0) + sum(ledgers.values())  # H_c: the hours charged before the freeze: the typed figure plus every ledger named
    cells = core.planned_cells(params_from_calibration(calibration), core.REGISTERED, cfg)
    w = {int(k): v for k, v in rates_in["by_workers"].items()}
    cand = {k: budget.Rates({tuple(x.split("|")[:1]) + (int(x.split("|")[1]),): float(v) for x, v in r["train"].items()}, {tuple(x.split("|")[:1]) + (int(x.split("|")[1]),): float(v) for x, v in r["evaluate"].items()}, float(r["contention"]), r["fixed"], k) for k, r in ((k, w[k]) for k in w)}  # type: ignore[misc]
    base_grants = {k: int(v) for k, v in calibration["u0"].items()}
    chosen = budget.choose_workers(cand, cells, base_grants)
    out = budget.grant_levels(cells, cand[chosen["chosen_workers"]], h_c, cfg)
    out["worker_choice"] = chosen
    out["h_charged_breakdown"] = {"typed_hours": float(args.charged_hours or 0.0), "ledgers_hours": ledgers}
    by_item = {k: float(v) for k, v in (w[chosen["chosen_workers"]].get("contention_by_item") or {}).items()}
    used = float(w[chosen["chosen_workers"]]["contention"])
    vals = sorted(by_item.values())
    out["measured_slowdown"] = {
        "rule_value_used_for_every_item": used, "rule_worst_item": max(by_item, key=lambda k: by_item[k]) if by_item else None, "by_item": by_item, "minimum": vals[0] if vals else None, "median": vals[len(vals) // 2] if vals else None,
        "note": "the rule multiplies every training item by the single worst item's slowdown; the per-item figures show how conservative that is (P10-S1's measured per-item slowdown was 1.3 to 1.8)",
    }  # fmt: skip
    if not out["refused"]:
        out["caps"] = budget.caps_from_projection(h_c, out["stage_hours"], cfg)
    Path(args.out).write_text(json.dumps(core.jsonable(out), indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": out["status"], "grants": out["grants"], "total_hours": out["total_hours"], "budget_B_hours": out["budget_B_hours"], "h_charged_hours": h_c, "slowdown_rule_worst_item": used, "slowdown_by_item": by_item}))
    return 0 if not out["refused"] else 3


def require_projection(plan: planmod.Plan, cfg: Any) -> None:
    """The freeze requires the projection of section 17.1: present, WITHIN BUDGET (a base plan above it is refused), its grants equal to the plan's granted lengths, its caps (charged + 2 x projected remaining, rounded up) equal
    to the config's, and the total cap within the block budget's 60 charged hours (a cap above it is the human lead's own decision, recorded elsewhere, never here)."""
    proj = plan.data.get("projection")
    if not proj:
        raise StageRefused("refused: the candidate plan carries no projection (section 17.1): the granted lengths and the caps are fixed by it, once, from the measuring rehearsal; every loaded cell at 4 x U0 is not a grant")
    if proj.get("refused") or proj.get("status") != "WITHIN BUDGET":
        raise StageRefused(f"refused: the projection is not WITHIN BUDGET ({proj.get('status')}): {planmod.BASE_PLAN_ABOVE_BUDGET} returns the work to the human lead")
    granted = {k: int(v) for k, v in plan.data["params"]["granted"].items()}
    if {k: int(v) for k, v in proj["grants"].items()} != granted:
        raise StageRefused("refused: the plan's granted lengths differ from the projection's grants")
    caps = proj.get("caps")
    if not caps:
        raise StageRefused("refused: the projection carries no caps")
    limit = float(cfg["budget"]["total_cap_hours"])
    if caps["total_above_limit"] or float(caps["total_cap_hours"]) > limit + 1e-9:
        raise StageRefused(f"refused: the projection's total cap {caps['total_cap_hours']} h is above the block budget's {limit} h: raising it is the human lead's own decision")
    c = cfg["caps"]
    want = {k: float(v) for k, v in (caps.get("config_caps") or {}).items()}  # EVERY cap of the config (train, evaluate, timing, throughput, analysis, rehearsal, total) from the projection's rule
    if set(want) != {"train_hours", "evaluate_hours", "timing_hours", "throughput_hours", "analysis_hours", "rehearsal_hours", "total_hours"}:
        raise StageRefused("refused: the projection does not carry a cap for every stage")
    got = {k: float(c[k]) for k in want}
    if got != want:
        raise StageRefused(f"refused: the config's caps {got} are not the caps the projection's rule gives {want} (charged + 2 x projected remaining, rounded up)")
    if not plan.data["projection"].get("h_charged_hours", 0) > 0:
        raise StageRefused("refused: the projection does not record the hours charged before the freeze (H_c)")


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
    bl = require_baseline(repo, cfg)  # re-derived from the committed samples: P95, L, the condition and both presences must equal the config's
    if core.caps_provisional(cfg) or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the caps are set from the measuring rehearsal (section 15) and the candidate plan is rewritten and rehearsed again")
    require_projection(plan, cfg)
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
    q = rehearsal.get("qualification") or {}
    missing_rows = [str(r) for r in core.row_facts(cfg) if not q.get(str(r))]
    if missing_rows:
        raise StageRefused(f"refused: the rehearsal record has no R2 qualification table for row(s) {missing_rows}: an absent table would silently qualify every condition (section 8.1)")
    reh = gates.rehearsal_gate(rehearsal, REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    if reh["passed"] is not True:
        raise StageRefused(f"refused: the rehearsal record does not show every stage COMPLETE on non-provisional caps against the candidate plan of SHA-256 {plan_sha}: {reh}")
    seed = gates.seed_gate(cfg, root=repo)
    if seed["passed"] is not True:
        raise StageRefused(f"refused: gate G9 (seeds) did not pass: {seed['problems']}")
    rec = {**core.envelope("freeze_record"), "plan_file_sha256": plan_sha, "rehearsal": {"path": str(Path(args.rehearsal).resolve()), "sha256": file_sha256(Path(args.rehearsal))}, "g9": {k: seed[k] for k in ("passed", "roles", "declared_reuse_not_new", "checker")}, "rehearsal_gate": reh, "quiet_baseline": {k: bl[k] for k in ("load_p95", "load_limit", "condition", "app_present", "cli_present", "record_sha256", "samples_sha256", "report_above")}, "adr_sha256_provenance_only": planmod.adr_provenance(repo)["sha256"]}
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record_path), "sha256": file_sha256(record_path), "plan_file_sha256": plan_sha}))
    return 0
