# ruff: noqa: E501
"""P10IR stage driver (ADR-0029 sections 10, 11, 13): ``registered <stage>`` (the entry point the fixed launch scripts call), ``freeze``, ``generate-bridge``, ``rehearse``, ``work`` (the worker processes).

Registered stages, in order: ``gates-a1``, ``a1``, ``gates-a2``, ``a2-train``, ``a2``, ``analysis``, ``report``. Run from the repository root:
``uv run --locked python -m studies.p10ir.stages <command> ...``. Registered stages take the run directory and the freeze commit and nothing else; every other value (items, caps, seeds, paths) comes from
``freeze/plan.json`` and ``configs/p10ir_routing.toml``. They REFUSE unless the working tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan
exists and every identity in it holds, and a committed Decision 2 for the stage's group (A1 or A2) names the freeze commit (``plan.check_preconditions``, ``plan.verify_plan``, ``plan.require_decision_2``).
Every stage derives its items from ``freeze/plan.json`` only. Stages are resumable: a PAUSED stage continues and finished reads are not recomputed; the stage manifest records PAUSED or COMPLETE.

Freeze procedure (nothing here is a freeze until the human lead's commands write ``plan.json``): tests and the independent audit pass; ``rehearse`` (synthetic and real-size cells, gates 1 and 2 on the registered
checkpoints) writes ``rehearsal.json``; the lead sets the caps in the config from the rehearsal (``caps-proposal``) and clears ``provisional``; ``generate-bridge`` writes the bridge draws' manifests; ``freeze``
writes ``plan.json``; the freeze commit is made; Decision 2 for A1 (and, separately, for A2) is committed; then ``studies/p10ir/launch/*.sh``.
"""

import argparse
import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import analysis, core, gates, items, report, runner, sealed, stages_io
from . import plan as planmod
from .plan import Plan, StageRefused

READ_STAGES = {"a1": core.STAGE_A1, "a2": core.STAGE_A2}
GROUP_STAGES = {core.STAGE_A1: ("gates-a1", "a1", "analysis", "report"), core.STAGE_A2: ("gates-a2", "a2-train", "a2")}
REHEARSAL_STAGES = ("gates-a1", "a1", "gates-a2", "a2-train", "a2", "analysis", "report")


# --- context and tasks ---------------------------------------------------------------------------------------------------------------------------------
def repo_of(args: argparse.Namespace | None = None) -> Path:
    return Path(getattr(args, "repo", None) or core.repo_root())


def ctx_for(plan: Plan, run_dir: Path, *, run_sealed: bool, experiments_root: Path | None, config_path: Path | None = None) -> items.Ctx:
    d = plan.data
    manifests = {name: Path(rec["path"]) for name, rec in (d.get("draw_manifests") or {}).items()}
    sizes = dict(d.get("sizes") or {})
    return items.Ctx(
        mode=plan.mode, run_dir=run_dir, s1_run_dir=None if d.get("s1_run_dir") is None else Path(d["s1_run_dir"]), experiments_root=experiments_root, synthetic=bool(d.get("synthetic", False)),
        run_sealed=run_sealed, config_path=config_path, manifests=manifests, **({"sizes": sizes} if sizes else {}),
    )  # fmt: skip


def labels_of_stage(plan: Plan, stage: str) -> list[str]:
    """The cell labels of a read stage's items, in the plan's order (from the plan only)."""
    seen: list[str] = []
    for it in plan.items(READ_STAGES[stage]):
        if it["cell"] not in seen:
            seen.append(it["cell"])
    return seen


def bridge_cells(plan: Plan) -> dict[str, dict[str, Any]]:
    cells = plan.data.get("bridge_cells")
    if not isinstance(cells, dict):
        raise StageRefused("refused: the plan has no bridge cells")
    return cells


def task_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "tasks"


def make_tasks(stage: str, plan: Plan, run_dir: Path, plan_path: Path, args: argparse.Namespace, extra: Sequence[str]) -> list[runner.Task]:
    if stage in READ_STAGES:
        labels = labels_of_stage(plan, stage)
        kind = "reads"
    elif stage == "a2-train":
        labels = list(bridge_cells(plan))
        kind = "train"
    else:
        raise ValueError(f"{stage} has no pool tasks")
    tasks = []
    for label in labels:
        result = (run_dir / "A2" / "train" / "cells" / label / "train.json") if kind == "train" else task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.done.json"
        argv = (sys.executable, "-m", "studies.p10ir.stages", "work", kind, "--stage", stage, "--labels", label, "--run-dir", str(run_dir), "--plan", str(plan_path), "--mode", plan.mode, *extra)
        tasks.append(runner.Task(label, argv, result, task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.failed.json", task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.log"))
    return tasks


# --- workers --------------------------------------------------------------------------------------------------------------------------------------------
def work_reads(ctx: items.Ctx, plan: Plan, stage: str, labels: Sequence[str]) -> int:
    """Run (or resume) every item of ``labels`` of read stage ``stage`` (items from the plan only) and write the task's done mark."""
    digests = plan.data.get("checkpoint_digests") or {}
    todo = [it for it in plan.items(READ_STAGES[stage]) if it["cell"] in labels]
    unknown = [lab for lab in labels if lab not in {it["cell"] for it in todo}]
    if unknown:
        raise StageRefused(f"refused: {unknown[0]} is not a cell of the frozen plan's {stage} items")
    for label in labels:
        for it in [i for i in todo if i["cell"] == label]:
            items.run_item(ctx, it, digests)
        core.write_record(task_dir(ctx.run_dir, stage) / f"{stages_io.safe_name(label)}.done.json", {**core.envelope("item"), "stage": READ_STAGES[stage], "cell": label, "update": 1, "complete": True, "items": [i["id"] for i in todo if i["cell"] == label]}, overwrite=True)
    return 0


def work_gates12(ctx: items.Ctx, plan: Plan, labels: Sequence[str]) -> int:
    """Gates 1 and 2 on the checkpoints of the cells in ``labels`` (rehearsal on the registered checkpoints): one result file per item under ``<run>/gates12/``."""
    for it in [i for i in plan.items(core.STAGE_A1) if i["cell"] in labels]:
        path = ctx.run_dir / "gates12" / "items" / f"{stages_io.safe_name(it['id'])}.json"
        if not path.is_file():
            core.write_record(path, {**core.envelope("gate"), "name": "gates12", "gate": items.run_gates12_item(ctx, it)})
    for label in labels:
        core.write_record(ctx.run_dir / "gates12" / "tasks" / f"{stages_io.safe_name(label)}.done.json", {**core.envelope("item"), "stage": core.STAGE_A1, "cell": label, "update": 1, "complete": True}, overwrite=True)
    return 0


def work_train(ctx: items.Ctx, plan: Plan, labels: Sequence[str]) -> int:
    from . import adapter

    cells = bridge_cells(plan)
    for label in labels:
        if label not in cells:
            raise StageRefused(f"refused: {label} is not a bridge cell of the frozen plan")
        adapter.train_bridge_cell(ctx, label, cells)
    return 0


# --- pre-read gate stages -------------------------------------------------------------------------------------------------------------------------------
def gates_record_path(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "gates.json"


def require_gates_passed(run_dir: Path, stage: str) -> dict[str, Any]:
    """A read or training stage starts only when its ``gates-*`` stage ran and every gate passed (a failure of gate 1, 5, 6 or the identity gate stops the stage before any read or training)."""
    path = gates_record_path(run_dir, stage)
    if not path.is_file():
        raise StageRefused(f"refused: no gates record at {path}: run {stage} first")
    rec = core.read_record(path, "gates_record")
    if rec.get("passed") is not True:
        raise StageRefused(f"refused: the {stage} gates did not all pass; nothing is read or trained: {rec.get('failed')}")
    return rec


def rehearsal_record_of(plan: Plan) -> dict[str, Any] | None:
    ref = plan.data.get("rehearsal")
    if not ref:
        return None
    p = Path(ref["path"])
    if not p.is_file() or file_sha256(p) != ref["sha256"]:
        raise StageRefused(f"refused: {p} does not hash to the frozen rehearsal record")
    return core.read_record(p, "rehearsal")


def run_gate_stage(stage: str, plan: Plan, ctx: items.Ctx, run_dir: Path, *, repo: Path, run_checker: bool = True, adapter_identity: bool = True) -> dict[str, Any]:
    """``gates-a1`` (gate 1 for the manifests and the frozen digests, gate 5, gate 6) and ``gates-a2`` (the same for the bridge draws' manifests, and the adapter identity gate)."""
    group = core.STAGE_A1 if stage == "gates-a1" else core.STAGE_A2
    record: dict[str, Any] = {**core.envelope("gates_record"), "stage": stage, "mode": plan.mode, "platform": gates.platform_record(), "gates": {}, "failed": []}
    cfg = ctx.cfg()
    g1: dict[str, Any] = {"manifests": {}, "checkpoint_digests": len(plan.data.get("checkpoint_digests") or {})}
    names = [n for n, r in (plan.data.get("draw_manifests") or {}).items() if group in r["groups"]]
    for name in names:
        rec = plan.data["draw_manifests"][name]
        p = Path(rec["path"])
        g1["manifests"][name] = p.is_file() and file_sha256(p) == rec["sha256"]
    g1["passed"] = bool(g1["manifests"]) and all(g1["manifests"].values())
    if group == core.STAGE_A1 and plan.mode == planmod.REGISTERED:
        g1["passed"] = g1["passed"] and g1["checkpoint_digests"] == len([i for i in plan.items(core.STAGE_A1)])
    record["gates"]["gate1_identities"] = g1
    reh = gates.rehearsal_gate(rehearsal_record_of(plan), REHEARSAL_STAGES) if plan.mode == planmod.REGISTERED else {"passed": True, "note": f"{plan.mode} mode"}
    record["gates"]["gate5_rehearsal"] = reh
    seeds = gates.seed_gate(cfg, run_checker=run_checker and plan.mode == planmod.REGISTERED)
    record["gates"]["gate6_seeds"] = seeds
    if group == core.STAGE_A2 and adapter_identity:
        from . import adapter

        cfg_s = cfg["seeds"]
        gate_cell = [int(x) for x in cfg_s["identity_gate_cell"]]
        s1_cells = [(arm, gate_cell[0], gate_cell[1], int(cfg_s["identity_gate_draw"]), int(cfg_s["p10s1_init_base"]) + int(cfg_s["identity_gate_draw"]), 8192, 49152) for arm in ("F-OQ", "T-OQ")]
        if plan.mode != planmod.REGISTERED:
            s1_cells = [tuple(c) for c in plan.data["identity_gate_cells"]]  # type: ignore[misc]
        record["gates"]["adapter_identity"] = adapter.identity_gate(
            ctx, run_dir / stage / "identity_work", cells=s1_cells, seeds_of=(core.p10s1_draw_seeds if plan.mode == planmod.REGISTERED else _mini_seeds_of(plan)), updates=[int(u) for u in plan.data.get("identity_gate_updates") or cfg_s["identity_gate_updates"]], cfg=cfg,
        )  # fmt: skip
    failed = [n for n, g in record["gates"].items() if g.get("passed") is False]
    record["failed"], record["passed"] = failed, not failed
    core.write_record(gates_record_path(run_dir, stage), record, overwrite=True)
    return record


def _mini_seeds_of(plan: Plan) -> Any:
    from studies.p10s1 import core as s1

    seeds = plan.data["identity_seed_sets"]
    return lambda d: s1.seed_set(seeds[str(d)]["name"], seeds[str(d)]["base"])


# --- charged time, caps -------------------------------------------------------------------------------------------------------------------------------------
def ledger_of(plan: Plan, run_dir: Path, ledger_root: Path | None) -> core.Ledger:
    root = ledger_root or run_dir.parent
    return core.Ledger(root / ("P10IR-ledger.json" if plan.mode == planmod.REGISTERED else f"P10IR-{plan.mode}-{run_dir.name}-ledger.json"), plan.total_cap_seconds())


def stage_cap_seconds(plan: Plan, stage: str, ledger: core.Ledger) -> float:
    """The stage's wall-clock cap: what remains of its group's cap and of the total (section 12: a stop on a resource cap is PAUSED)."""
    key = planmod.STAGE_CAP_KEY[stage]
    group_stages = [s for s, k in planmod.STAGE_CAP_KEY.items() if k == key]
    spent = sum(ledger.charged(s) for s in group_stages)
    return max(0.0, min(plan.cap_seconds(key) - spent, ledger.remaining()))


# --- executing a stage ----------------------------------------------------------------------------------------------------------------------------------------
def execute_stage(stage: str, plan: Plan, ctx: items.Ctx, run_dir: Path, plan_path: Path, *, repo: Path, workers: int, inline: bool, extra_worker_args: Sequence[str] = (), ledger_root: Path | None = None, run_checker: bool = True, adapter_identity: bool = True) -> dict[str, Any]:
    """One stage, resumable, from the plan only. ``inline`` runs the workers in this process (rehearsal's synthetic phase and tests); otherwise as subprocesses under ``runner.run_tasks``."""
    cfg = ctx.cfg()
    ledger = ledger_of(plan, run_dir, ledger_root)
    cap = stage_cap_seconds(plan, stage, ledger)
    ledger.require_room(stage, max(cap, 1.0) if cap > 0 else 0.0)
    prior = runner.read_manifest(run_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        raise StageRefused(f"refused: {runner.manifest_path(run_dir, stage)} is COMPLETE; a completed stage is never rewritten")
    started = datetime.now(UTC).isoformat()
    began = time.monotonic()
    identity = {"plan_sha256": plan.sha256(), "config_sha256": plan.data["config_sha256"], "platform": gates.platform_record()}
    caps = {"stage_seconds": cap, "rss_worker_bytes": float(cfg["resources"]["rss_worker_bytes"]), "rss_aggregate_bytes": float(cfg["resources"]["rss_aggregate_bytes"])}
    if stage.startswith("gates-"):
        rec = run_gate_stage(stage, plan, ctx, run_dir, repo=repo, run_checker=run_checker, adapter_identity=adapter_identity)
        outcomes = {stage: {"status": runner.COMPLETED if rec["passed"] else runner.FAILED, "seconds": time.monotonic() - began, "peak_rss_bytes": 0, "reason": None if rec["passed"] else f"gates failed: {rec['failed']}"}}
    elif stage in ("analysis", "report"):
        outcomes = {stage: {"status": runner.COMPLETED, "seconds": 0.0, "peak_rss_bytes": 0}}
        if stage == "analysis":
            m1 = runner.read_manifest(run_dir, "a1")
            if m1 is None or m1["status"] != "COMPLETE":
                raise StageRefused("refused: a1 is not COMPLETE: the analysis needs every A1 read")
        (run_analysis if stage == "analysis" else run_report)(plan, ctx, run_dir)
        outcomes[stage]["seconds"] = time.monotonic() - began
    else:
        if stage in ("a1", "a2-train"):
            require_gates_passed(run_dir, "gates-a1" if stage == "a1" else "gates-a2")
        if stage == "a2":
            require_gates_passed(run_dir, "gates-a2")
            m = runner.read_manifest(run_dir, "a2-train")
            if m is None or m["status"] != "COMPLETE":
                raise StageRefused("refused: a2-train is not COMPLETE: the bridge checkpoints do not all exist")
        extra = list(extra_worker_args)
        tasks = make_tasks(stage, plan, run_dir, plan_path, argparse.Namespace(), extra)
        if inline:
            outcomes = {}
            for t in tasks:
                if t.result_path.is_file():
                    outcomes[t.label] = {"status": runner.COMPLETED, "seconds": 0.0, "skipped": "result exists", "peak_rss_bytes": 0}
                    continue
                t0 = time.monotonic()
                if stage == "a2-train":
                    work_train(ctx, plan, [t.label])
                else:
                    work_reads(ctx, plan, stage, [t.label])
                outcomes[t.label] = {"status": runner.COMPLETED, "seconds": time.monotonic() - t0, "peak_rss_bytes": 0}
        else:
            outcomes, _ = runner.run_tasks(tasks, workers=workers, cap_seconds=cap, rss_worker_bytes=int(cfg["resources"]["rss_worker_bytes"]), rss_aggregate_bytes=int(cfg["resources"]["rss_aggregate_bytes"]), env={"PYTHONPATH": str(repo)})
    seconds = time.monotonic() - began
    ledger.charge(stage, run_dir.name, seconds)
    manifest = runner.write_manifest(run_dir, stage, plan.mode, outcomes, seconds, identity=identity, started=started, caps=caps)
    print(json.dumps({"stage": stage, "status": manifest["status"], "tasks": len(outcomes), "charged_seconds": round(seconds, 1)}))
    return manifest


# --- analysis and report ----------------------------------------------------------------------------------------------------------------------------------------
def _context(plan: Plan, ctx: items.Ctx) -> dict[str, Any]:
    """D-OQ's a_use at the same cells from P10-S1's records (descriptive; the dense map has no retrieval to change, section 7)."""
    out: dict[str, Any] = {}
    if ctx.s1_run_dir is None:
        return out
    from studies.p10s1 import core as s1

    for entry in plan.data.get("context", {}).get("dense", []):
        vals = []
        for lab in entry["labels"]:
            try:
                c = sealed.counts(ctx.s1_run_dir, lab, int(entry["update"]), "main")
                vals.append(sum(c[p]["useful"] for p in sealed.PANELS) / sum(c[p]["n"] for p in sealed.PANELS))
            except sealed.SealedMissing:
                continue
        out[f"D-OQ a_use, {entry['cell_name']} at {entry['checkpoint']} (mean over {len(vals)} replicates; P10-S1's recorded counts)"] = None if not vals else sum(vals) / len(vals)
    _ = s1
    return out


def _plateau(plan: Plan, ctx: items.Ctx) -> dict[str, dict[str, list[Any]]]:
    out: dict[str, dict[str, list[Any]]] = {}
    if ctx.s1_run_dir is None:
        return out
    for cell_name, arms in (plan.data.get("plateau") or {}).items():
        out[cell_name] = {}
        for arm_key, per_draw in arms.items():
            series: list[Any] = []
            for lab_updates in per_draw:
                try:
                    series.append(sealed.information_series(ctx.s1_run_dir, lab_updates["label"], [int(u) for u in lab_updates["updates"]]) if lab_updates["updates"] else None)
                except sealed.SealedMissing:
                    series.append(None)
            out[cell_name][arm_key] = series
    return out


def analysis_path(run_dir: Path) -> Path:
    return run_dir / "analysis" / "analysis.json"


def run_analysis(plan: Plan, ctx: items.Ctx, run_dir: Path) -> dict[str, Any]:
    from . import registry

    cfg = ctx.cfg()
    reg1 = registry.load(run_dir, core.STAGE_A1)
    a1 = analysis.analyze_stage(reg1, core.STAGE_A1, cfg, plateau=_plateau(plan, ctx), context=_context(plan, ctx), seal_broken=bool(plan.data.get("seal", {}).get("broken")), specs=_specs_of(plan, core.STAGE_A1))
    m2 = runner.read_manifest(run_dir, "a2")
    a2 = None
    complete = False
    if m2 is not None:
        complete = m2["status"] == "COMPLETE"
        if complete:
            a2 = analysis.analyze_stage(registry.load(run_dir, core.STAGE_A2), core.STAGE_A2, cfg, specs=_specs_of(plan, core.STAGE_A2))
    full = analysis.analyze_all(a1, a2, a2_complete=complete)
    full["kind"] = "analysis"
    core.write_record(analysis_path(run_dir), {**core.envelope("analysis"), **full}, overwrite=True)
    return full


def _specs_of(plan: Plan, stage: str) -> list[core.CellSpec]:
    """The cell specs of a stage as the plan's items name them (from the plan only)."""
    seen: dict[tuple[int, int], core.CellSpec] = {}
    for it in plan.items(stage):
        key = (it["facts"], it["slots"])
        if key not in seen:
            cps = sorted({i["update"] for i in plan.items(stage) if (i["facts"], i["slots"]) == key})
            traj = [u for u in cps if u not in (it["u_p"], it["run"])]
            seen[key] = core.CellSpec(it["facts"], it["slots"], it["role"], it["u_p"], it["run"], (traj[0], traj[1]) if len(traj) == 2 else (it["u_p"], it["run"]))
    return list(seen.values())


def run_report(plan: Plan, ctx: items.Ctx, run_dir: Path) -> Path:
    path = analysis_path(run_dir)
    if not path.is_file():
        raise StageRefused("refused: no analysis.json: run the analysis first")
    full = read_json(path)
    note = f"Mode: {plan.mode}. Plan SHA-256 {plan.sha256()}. Platform: {gates.platform_record()['platform']}."
    out = run_dir / "report" / "REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.render(full, note), encoding="utf-8")
    return out


# --- registered entry point ---------------------------------------------------------------------------------------------------------------------------------
def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name. Free arguments: the run directory and the freeze commit, nothing else."""
    if args.name not in planmod.REGISTERED_STAGES:
        raise StageRefused(f"refused: unknown registered stage {args.name!r}")
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
    plan = planmod.load_registered_plan(repo)
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, args.freeze_commit, planmod.STAGE_GROUP[args.name])
    ctx = ctx_for(plan, run_dir, run_sealed=True, experiments_root=_experiments_root())
    manifest = execute_stage(args.name, plan, ctx, run_dir, repo / core.PLAN, repo=repo, workers=int(ctx.cfg()["resources"]["workers"]), inline=False, extra_worker_args=("--freeze-commit", args.freeze_commit, "--run-sealed"))
    return 0 if manifest["status"] != "FAILED" else 1


def _experiments_root() -> Path:
    from studies.p9 import core as p9core

    return Path(p9core.default_experiments_root())


# --- worker entry point --------------------------------------------------------------------------------------------------------------------------------------
def cmd_work(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    plan = Plan.load(Path(args.plan))
    if plan.mode == planmod.REGISTERED:  # a registered worker re-checks the freeze, the plan and Decision 2 itself
        if Path(args.plan) != repo / core.PLAN:
            raise StageRefused(f"refused: the registered plan is {core.PLAN}")
        planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
        planmod.verify_plan(plan, repo, run_dir)
        planmod.require_decision_2(repo, args.freeze_commit, planmod.STAGE_GROUP[args.stage])
    ctx = ctx_for(plan, run_dir, run_sealed=bool(args.run_sealed), experiments_root=None if plan.data.get("synthetic") else _experiments_root())
    labels = [s for s in args.labels.split(",") if s]
    if args.kind == "train":
        return work_train(ctx, plan, labels)
    if args.kind == "gates12":
        return work_gates12(ctx, plan, labels)
    return work_reads(ctx, plan, args.stage, labels)


# --- parser ----------------------------------------------------------------------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("registered", help="one registered stage (run dir and freeze commit only)")
    reg.add_argument("name", choices=planmod.REGISTERED_STAGES)
    reg.add_argument("--run-dir", required=True)
    reg.add_argument("--freeze-commit")
    reg.add_argument("--repo")
    w = sub.add_parser("work", help="worker process of a registered stage or of the rehearsal")
    w.add_argument("kind", choices=("reads", "train", "gates12"))
    w.add_argument("--stage", required=True)
    w.add_argument("--labels", required=True)
    w.add_argument("--run-dir", required=True)
    w.add_argument("--plan", required=True)
    w.add_argument("--mode", required=True, choices=planmod.MODES)
    w.add_argument("--freeze-commit")
    w.add_argument("--run-sealed", action="store_true")
    w.add_argument("--repo")
    from . import freeze as freezemod

    freezemod.add_commands(sub)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("registered", "work"):
            from studies.p10s1 import train as s1train

            s1train.configure()  # one thread, one interop thread, deterministic algorithms: the platform of record's settings (section 13) are set before the platform is checked
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return cmd_work(args)
        from . import freeze as freezemod

        return freezemod.dispatch(args)
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except core.LedgerRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
