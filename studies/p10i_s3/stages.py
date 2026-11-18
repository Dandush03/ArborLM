# ruff: noqa: E501
"""P10IS3 stage driver (ADR-0026 sections 8, 10, 11): ``registered <stage>`` (the entry point the launch scripts call), ``work`` (worker processes), ``candidate-plan``, ``freeze``, ``prepare-data``, ``write-rate-table``,
``caps-proposal``, ``rehearse`` (see ``rehearsal.py``). Run from the repository root as ``uv run --locked python -m studies.p10i_s3.stages <command> ...``.

Registered stages: ``gates``, ``train``, ``eval``, ``analysis``, ``report``. They take the run directory and the freeze commit and nothing else; every other value comes from ``freeze/plan.json`` and the config. They REFUSE
(exit 2) unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and freeze record exist and verify, and a committed Decision 2 names the freeze
commit. A worker whose identity check fails exits 75 (PAUSED — IDENTITY, nothing written); the lead's pause file (``<run>/PAUSE_BY_LEAD``) pauses a stage between tasks (PAUSED — BY THE LEAD). A code or environment
error is an ENGINEERING STOP: it is recorded as ``item_error`` and the analysis refuses. Nothing here is a freeze or a registered run.
"""

import argparse
import copy
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json, write_json

from . import analysis, core, gates, items, report, runner
from . import plan as planmod
from .plan import Plan, StageRefused

IDENTITY_EXIT = runner.IDENTITY_EXIT
PREFIX_ARM_REGIMES = [(a, g) for g in core.REGIMES for a in core.REGIME_ARMS[g]]


# --- config and resources ---------------------------------------------------------------------------------------------------------------
def deep_update(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def cfg_for(plan: Plan, repo: Path) -> dict[str, Any]:
    """The registered config, or (rehearsal and test plans only) the config with the plan's recorded overrides. A registered plan never has overrides."""
    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    if plan.mode != planmod.REGISTERED:
        deep_update(cfg, plan.data.get("cfg_override") or {})
    elif plan.data.get("cfg_override"):
        raise StageRefused("refused: a registered plan carries config overrides")
    return cfg


def synthetic_resources(cfg: Mapping[str, Any], seed: int = 0) -> items.Resources:
    """Random bytes and random backbones: tests and the synthetic rehearsal. Never used by a registered plan."""
    from arborlm.p4_model import Backbone
    from arborlm.pilot_model import PilotModel

    n = int(cfg["setting"]["panel_chunks"])
    g = torch.Generator().manual_seed(core.test_seed(900 + seed))

    def rows(k: int) -> torch.Tensor:
        return torch.randint(0, 256, (k, 65), generator=g, dtype=torch.int64)

    pool = int(cfg["data"].get("synthetic_fresh", 256))
    cache: dict[int, Any] = {}

    def backbone(parent: int) -> Any:
        if parent not in cache:
            cache[parent] = Backbone(PilotModel("dense_small", 42 + parent % 3))
        return cache[parent]

    return items.Resources(cfg, {core.REP: rows(64), core.REPU: rows(64), core.FRESH: rows(pool)}, {"registered": rows(n), "calibration": rows(n)}, backbone, expected_targets=n * 64)


def real_resources(plan: Plan, repo: Path, cfg: Mapping[str, Any]) -> items.Resources:
    """From the plan's data directory and parent suite: the chunk files (hash-checked against the data manifest) and the nine parents (digest-checked against the P4 record)."""
    from . import parents

    d = plan.data
    manifest = read_json(Path(d["data_manifest"]["path"]))
    ddir = Path(d["data_dir"])
    for name, digest in manifest["files"].items():
        if file_sha256(ddir / name) != digest:
            raise StageRefused(f"refused: {name} does not hash to the data manifest (PAUSED — IDENTITY)")
    train = torch.frombuffer(bytearray((ddir / "train_all.bytes").read_bytes()), dtype=torch.uint8).long().reshape(-1, 65)
    val = torch.frombuffer(bytearray((ddir / "validation_all.bytes").read_bytes()), dtype=torch.uint8).long().reshape(-1, 65)
    lo, hi = cfg["data"]["rep_ranks"], cfg["data"]["rep_u_ranks"]
    rows = {core.REP: train[lo[0] : lo[1]], core.REPU: train[hi[0] : hi[1]], core.FRESH: train[int(cfg["data"]["fresh_start"]) :]}
    panels = {k: val[torch.tensor(manifest["panels"][k], dtype=torch.int64)] for k in ("registered", "calibration")}
    cache: dict[int, Any] = {}

    def backbone(parent: int) -> Any:
        if parent not in cache:
            cache[parent] = parents.load_backbone(repo, Path(d["parent_suite"]), parent)[0]
        return cache[parent]

    return items.Resources(cfg, rows, panels, backbone)


def resources_for(plan: Plan, repo: Path, cfg: Mapping[str, Any]) -> items.Resources:
    return synthetic_resources(cfg) if plan.data.get("synthetic") else real_resources(plan, repo, cfg)


# --- paths, tasks ---------------------------------------------------------------------------------------------------------------------------
def task_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "tasks"


def safe(text: str) -> str:
    return text.replace("|", "__").replace("/", "~")


def make_tasks(stage: str, plan: Plan, run_dir: Path, plan_path: Path, repo: Path, state_dir: Path | None = None) -> list[runner.Task]:
    """``run_dir`` holds the item records (shared by every plan of a rehearsal); ``state_dir`` (default the run directory) holds the gate results and task marks of this plan."""
    state_dir = state_dir or run_dir
    base = (sys.executable, "-m", "studies.p10i_s3.stages", "work")
    common = ("--run-dir", str(run_dir), "--state-dir", str(state_dir), "--plan", str(plan_path), "--repo", str(repo))
    tasks: list[runner.Task] = []
    if stage == "gates":
        names = ["core"] + [f"prefix|{a}|{g}" for a, g in PREFIX_ARM_REGIMES]
        for n in names:
            tasks.append(runner.Task(n, (*base, "gates", "--name", n, *common), gate_path(state_dir, n), task_dir(state_dir, stage) / f"{safe(n)}.failed.json", task_dir(state_dir, stage) / f"{safe(n)}.log"))
    elif stage == "train":
        for it in plan.items("train"):
            tasks.append(runner.Task(it["id"], (*base, "train", "--item", it["id"], *common), items.train_record_path(run_dir, it), task_dir(state_dir, stage) / f"{safe(it['id'])}.failed.json", task_dir(state_dir, stage) / f"{safe(it['id'])}.log"))
    elif stage == "eval":
        with_evals = {i["train"] for i in plan.items("eval")}
        for it in plan.items("train"):
            n = it["id"]
            if n in with_evals:
                tasks.append(runner.Task(n, (*base, "eval", "--train-id", n, *common), task_dir(state_dir, stage) / f"{safe(n)}.done.json", task_dir(state_dir, stage) / f"{safe(n)}.failed.json", task_dir(state_dir, stage) / f"{safe(n)}.log"))
    else:
        raise ValueError(f"{stage} has no pool tasks")
    return tasks


# --- gates ---------------------------------------------------------------------------------------------------------------------------------
def gate_path(run_dir: Path, name: str) -> Path:
    return run_dir / "gates" / "results" / f"{safe(name)}.json"


def run_core_gates(plan: Plan, repo: Path, run_dir: Path, res: items.Resources, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Stage G, the gates that need no training: platform record, identity of every frozen input, seed gate, read equality, planted positive, BASE and disabled = BASE on every parent (registered panel; ruling 15: the
    only trained-model-free reads of the registered panel), data reproduction and lineage, REP/REP-U/FRESH disjointness."""
    th = core.Thresholds.from_config(cfg)
    out: dict[str, Any] = {}
    out["platform"] = gates.gate("platform", not gates.platform_problems(cfg) if plan.mode == planmod.REGISTERED else None, record=gates.platform_record(), problems=gates.platform_problems(cfg))
    planmod.verify_identity(plan, repo)
    out["identity"] = gates.gate("identity", True, frozen_files=len(plan.data["frozen_files"]), src_files=len(plan.data["src"]["files"]), named_not_reached=plan.data["src"]["named_not_reached"], reached_not_named=plan.data["src"]["reached_not_named"])
    out["seeds"] = gates.seed_gate(cfg, root=repo, run_checker=plan.mode == planmod.REGISTERED)
    out["read_equality"] = gates.read_equality_gate(core.test_seed(1), cfg=cfg)
    from . import planted

    pp = planted.planted_positive(th, core.Seeds("test", cfg))
    out["planted_positive"] = gates.gate("planted_positive", pp["passed"], detail=pp["arms"])
    from . import model

    bitwise = gates.on_platform_of_record(cfg)
    vals: dict[str, tuple[float, float, float]] = {}
    panel = res.panels["registered"]
    for p in range(9 if plan.mode == planmod.REGISTERED else 3):
        bb = res.backbone(p)
        b = model.evaluate(model.build_model(copy.deepcopy(bb), core.BASE, 0), panel, expected_targets=res.expected_targets)
        r = model.evaluate(model.build_model(copy.deepcopy(bb), core.BASE, 0), panel, expected_targets=res.expected_targets)
        t = model.build_model(copy.deepcopy(bb), core.TREE, int(cfg["seeds"]["init_registered"][0]))
        t.bypass = True
        d = model.evaluate(t, panel, expected_targets=res.expected_targets)
        vals[core.parent_label(p)] = (b, r, d)
    out["base_and_disabled"] = gates.base_gate(vals, bitwise=bitwise)
    out["base_values"] = {str(p): {"enabled": v[0], "replay": v[1], "disabled": v[2]} for p, v in zip(range(len(vals)), vals.values(), strict=True)}
    if plan.data.get("data_manifest"):
        m = read_json(Path(plan.data["data_manifest"]["path"]))
        out["data"] = gates.gate("data", bool(m["gates"]["reproduction"]["passed"] and m["gates"]["lineage"]["passed"] and m["gates"]["disjoint"]["passed"]), recorded=m["gates"])
    return out


def work_gates(plan: Plan, repo: Path, run_dir: Path, name: str, state_dir: Path) -> int:
    cfg = cfg_for(plan, repo)
    res = resources_for(plan, repo, cfg)
    path = gate_path(state_dir, name)
    if path.is_file():
        return 0
    if name == "core":
        results = run_core_gates(plan, repo, run_dir, res, cfg)
        passed = all(v["passed"] is not False for k, v in results.items() if k != "base_values")
        core.write_record(path, {**core.envelope("gate"), "name": name, "passed": passed, "results": results})
    else:
        _, arm, regime = name.split("|")
        cell = 0
        profile = plan.data.get("gate_profile", "calibration")
        seeds = core.Seeds(profile, cfg)
        short, long = int(cfg["duration"]["checkpoints"][0]), int(cfg["duration"]["u_star"])
        rt = plan.rate_table["rates"][f"{arm}|{regime}"]
        rate = float(rt[str(long)])
        import tempfile

        with tempfile.TemporaryDirectory(dir=run_dir) as tmp:
            r = gates.prefix_identity_gate(arm, res.backbone(core.calibration_parent(cell) if profile == "calibration" else cell), res.rows[regime], init_seed=seeds.init(cell), stream_seed=seeds.stream(cell, core.REGIME_INDEX[regime]), fresh=regime == core.FRESH, rate=rate, short=short, long=long, root=Path(tmp), cfg=cfg)
        core.write_record(path, {**core.envelope("gate"), "name": name, "passed": r["passed"] is not False, "results": {"prefix": r}})
    return 0


def gates_status(run_dir: Path) -> dict[str, Any]:
    d = run_dir / "gates" / "results"
    recs = {p.stem: core.read_record(p, "gate") for p in sorted(d.glob("*.json"))} if d.is_dir() else {}
    return {"all_present": len(recs) == 1 + len(PREFIX_ARM_REGIMES), "failed": [k for k, v in recs.items() if v["passed"] is not True], "records": recs}


def require_gates_passed(run_dir: Path) -> None:
    s = gates_status(run_dir)
    if not s["all_present"] or s["failed"]:
        raise StageRefused(f"refused: the gates did not all pass (present: {s['all_present']}); nothing is trained or evaluated: {s['failed']}")


# --- workers --------------------------------------------------------------------------------------------------------------------------------
def worker_precheck(plan: Plan, repo: Path, run_dir: Path) -> None:
    planmod.verify_identity(plan, repo)
    if plan.mode == planmod.REGISTERED:
        planmod.verify_plan(plan, repo, run_dir)


def work_train(plan: Plan, repo: Path, run_dir: Path, item_id: str) -> int:
    cfg = cfg_for(plan, repo)
    it = plan.item(item_id)
    res = resources_for(plan, repo, cfg)
    path = items.train_record_path(run_dir, it)
    items.guarded(path, item_id, lambda: items.run_train(res, it, run_dir))
    return 0


def work_eval(plan: Plan, repo: Path, run_dir: Path, train_id: str, state_dir: Path) -> int:
    cfg = cfg_for(plan, repo)
    res = resources_for(plan, repo, cfg)
    tr = plan.item(train_id)
    rec = core.read_record(items.train_record_path(run_dir, tr), "train")
    if rec.get("status") == "item_error":
        raise RuntimeError("the training item ended in an item error")
    for it in [i for i in plan.items("eval") if i["train"] == train_id]:
        items.guarded(items.eval_record_path(run_dir, it), it["id"], lambda it=it: items.run_eval(res, it, run_dir, rec))
    core.write_record(task_dir(state_dir, "eval") / f"{safe(train_id)}.done.json", {**core.envelope("eval"), "id": train_id, "complete": True}, overwrite=True)
    return 0


def work_main(args: argparse.Namespace) -> int:
    repo, run_dir = Path(args.repo), Path(args.run_dir)
    state_dir = Path(args.state_dir) if args.state_dir else run_dir
    plan = Plan.load(Path(args.plan))
    try:
        worker_precheck(plan, repo, run_dir)
    except StageRefused as e:
        print(f"PAUSED — IDENTITY: {e}", file=sys.stderr)
        return IDENTITY_EXIT
    torch.set_num_threads(1)
    from arborlm.engine import configure_cpu

    configure_cpu()
    if args.kind == "gates":
        return work_gates(plan, repo, run_dir, args.name, state_dir)
    if plan.mode == planmod.REGISTERED:
        require_gates_passed(state_dir)
    if args.kind == "train":
        return work_train(plan, repo, run_dir, args.item)
    return work_eval(plan, repo, run_dir, args.train_id, state_dir)


# --- the stage driver ---------------------------------------------------------------------------------------------------------------------
def run_stage(stage: str, plan: Plan, repo: Path, run_dir: Path, plan_path: Path, *, mode: str, identity: Mapping[str, Any], state_dir: Path | None = None) -> int:
    """Run (or resume) a pool stage. Prints the status; exit 0 only when COMPLETE."""
    started = datetime.now(UTC).isoformat()
    state_dir = state_dir or run_dir
    if stage != "gates" and plan.mode == planmod.REGISTERED:
        require_gates_passed(state_dir)
    tasks = make_tasks(stage, plan, run_dir, plan_path, repo, state_dir)
    cap = plan.cap_seconds(stage)
    out, seconds = runner.run_tasks(tasks, workers=int(plan.data["workers"]), cap_seconds=cap, rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=run_dir)
    prior = runner.read_manifest(state_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        print(json.dumps({"stage": stage, "status": "COMPLETE", "note": "already complete"}))
        return 0
    rec = runner.write_manifest(state_dir, stage, mode, out, seconds, identity=dict(identity), started=started, caps={"stage_cap_seconds": cap})
    print(json.dumps({"stage": stage, "status": rec["status"], "charged_seconds": rec["charged_seconds"]}))
    return 0 if rec["status"] == "COMPLETE" else 1


def bases_of(run_dir: Path) -> dict[str, dict[str, float | None]]:
    p = gate_path(run_dir, "core")
    return dict(core.read_record(p, "gate")["results"]["base_values"]) if p.is_file() else {}


def run_analysis(plan: Plan, repo: Path, run_dir: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Section 10: refuses while any item error exists or any planned evaluation is missing; labels nothing then."""
    reg = items.collect_registry(run_dir, plan.data["items"], bases_of(run_dir))
    cells = sorted({i["cell"] for i in plan.items("train")})
    cell_parent = {c: next(i["parent"] for i in plan.items("train") if i["cell"] == c) for c in cells}
    th = core.Thresholds.from_config(cfg) if plan.mode == planmod.REGISTERED else core.Thresholds.from_config(cfg).scaled(len(cells))
    for it in plan.items("train"):  # a planned run without a record is a missing cell: engineering stop, never a reduced denominator
        if core.run_key(it["arm"], it["regime"], it["rate"], it["cell"]) not in reg:
            raise core.EngineeringStop(f"ENGINEERING STOP — a planned run has no record: {it['id']}")
    result = analysis.analyse(reg, plan.rate_table, cfg, cells=cell_parent, th=th, bitwise=gates.on_platform_of_record(cfg))
    core.write_record(run_dir / "analysis" / "analysis.json", {**core.envelope("analysis"), "result": result, "mode": plan.mode})
    return result


def cmd_registered(args: argparse.Namespace) -> int:
    repo, run_dir = Path(args.repo or core.repo_root()), Path(args.run_dir).resolve()
    try:
        identity = planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
        assert identity is not None
        planmod.require_decision_2(repo, args.freeze_commit)
        planmod.require_ignored_run_dir(repo, run_dir)
        plan = planmod.load_registered_plan(repo)
        planmod.verify_plan(plan, repo, run_dir)
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return 2
    plan_path = repo / core.PLAN
    stage = args.stage
    if stage in ("gates", "train", "eval"):
        if stage == "eval":
            m = runner.read_manifest(run_dir, "train")
            if m is None or m["status"] != "COMPLETE":
                print("refused: the train stage is not COMPLETE", file=sys.stderr)
                return 2
        return run_stage(stage, plan, repo, run_dir, plan_path, mode=planmod.REGISTERED, identity=identity)
    cfg = cfg_for(plan, repo)
    if stage == "analysis":
        m = runner.read_manifest(run_dir, "eval")
        if m is None or m["status"] != "COMPLETE":
            print("refused: the eval stage is not COMPLETE", file=sys.stderr)
            return 2
        try:
            run_analysis(plan, repo, run_dir, cfg)
        except core.EngineeringStop as e:
            print(str(e), file=sys.stderr)
            return 3
        return 0
    if stage == "report":
        rec = core.read_record(run_dir / "analysis" / "analysis.json", "analysis")
        (run_dir / "analysis" / "report.md").write_text(report.render(rec["result"], plan.mode), encoding="utf-8")
        return 0
    print(f"unknown stage {stage}", file=sys.stderr)
    return 2


# --- freeze commands -------------------------------------------------------------------------------------------------------------------------------
def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write ``freeze/plan.json`` first and once; ``--supersede`` moves an older file aside (never deletes it). The rate table is ``freeze/rate_table.json`` (written by ``write-rate-table`` from ``rehearsal_public.json``)."""
    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    if plan_path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {plan_path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(plan_path)
        target = plan_path.parent / "superseded" / f"plan-{old[:12]}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise StageRefused(f"refused: {target} exists")
        plan_path.rename(target)
    rt = read_json(repo / core.RATE_TABLE)
    extra: dict[str, Any] = {}
    if args.data_manifest:
        dm = Path(args.data_manifest).resolve()
        extra = {"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_suite": str(Path(args.parent_suite).resolve())}
    if args.projected_remaining_hours is not None and 2 * args.projected_remaining_hours > float(cfg["caps"]["registered_hours"]) and not args.over_cap_approved:
        raise StageRefused(f"refused: the section-7 cap (2 x {args.projected_remaining_hours} h) exceeds 48 charged hours: the lead returns to the human lead with the projection (pass --over-cap-approved once the human lead extends it)")
    record = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(args.run_dir).resolve(), rate_table=rt, projected_remaining_hours=args.projected_remaining_hours, extra=extra)
    core.write_record(plan_path, record)
    print(json.dumps({"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "items": {k: len(v) for k, v in record["items"].items()}, "caps_provisional": record["caps_provisional"]}))
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    """Write ``freeze/freeze_record.json`` for the committed candidate plan, only if: the plan's caps are not provisional; the plan equals a re-derivation of its scientific content from current code and config; the
    counting rehearsal's record names this plan file's SHA-256 and was made on non-provisional caps; the seed gate passes. The ADR's hash is not compared."""
    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    record_path = repo / core.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    plan = Plan.load(repo / core.PLAN)
    if plan.data.get("caps_provisional") or cfg["caps"]["provisional"]:
        raise StageRefused("refused: the caps are provisional")
    plan_sha = file_sha256(repo / core.PLAN)
    extra = {k: plan.data[k] for k in ("data_manifest", "data_dir", "parent_suite") if k in plan.data}
    again = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(plan.data["run_dir"]), rate_table=plan.data["rate_table"], projected_remaining_hours=plan.data["caps"]["registered_hours"] / 2.0, extra=extra)
    if planmod.scientific_content(json.loads(json.dumps(again))) != planmod.scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and rate table: supersede it and rehearse again")
    rehearsal = core.read_record(Path(args.rehearsal), "rehearsal_public")
    if rehearsal.get("caps_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps (a measuring rehearsal cannot be frozen on)")
    reh = gates.rehearsal_gate(rehearsal, ("R1", "R2", "R3"), plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the rehearsal record does not show R1, R2 and R3 COMPLETE with this plan file's SHA-256: {reh}")
    seed = gates.seed_gate(cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: the seed gate did not pass: {seed['problems']}")
    write_json(record_path, {**core.envelope("freeze_record"), "plan_file_sha256": plan_sha, "rehearsal": {"path": str(Path(args.rehearsal).resolve()), "sha256": file_sha256(Path(args.rehearsal))}, "seed_gate": seed, "rehearsal_gate": reh})
    print(json.dumps({"freeze_record": str(record_path), "plan_file_sha256": plan_sha}))
    return 0


def cmd_write_rate_table(args: argparse.Namespace) -> int:
    """``freeze/rate_table.json`` from ``rehearsal_public.json`` (the whitelist file): the rate table and edge flags only."""
    repo = Path(args.repo or core.repo_root())
    pub = core.read_record(Path(args.public), "rehearsal_public")
    target = repo / core.RATE_TABLE
    if target.exists():
        raise StageRefused(f"refused: {target} exists")
    write_json(target, pub["rate_table"])
    print(json.dumps({"rate_table": str(target), "sha256": file_sha256(target)}))
    return 0


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    print(json.dumps({"proposed_registered_cap_hours": args.charged_hours + 2.0 * args.projected_remaining_hours, "rule": "section 7: charged so far + 2 x projected remaining (charged is 0 at candidate-plan time)"}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studies.p10i_s3.stages")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("registered")
    r.add_argument("stage", choices=planmod.REGISTERED_STAGES)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--repo")
    w = sub.add_parser("work")
    w.add_argument("kind", choices=("gates", "train", "eval"))
    w.add_argument("--run-dir", required=True)
    w.add_argument("--state-dir")
    w.add_argument("--plan", required=True)
    w.add_argument("--repo", required=True)
    w.add_argument("--name")
    w.add_argument("--item")
    w.add_argument("--train-id")
    cp = sub.add_parser("candidate-plan")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--data-manifest")
    cp.add_argument("--parent-suite")
    cp.add_argument("--projected-remaining-hours", type=float)
    cp.add_argument("--over-cap-approved", action="store_true")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze")
    f.add_argument("--rehearsal", required=True)
    f.add_argument("--repo")
    wr = sub.add_parser("write-rate-table")
    wr.add_argument("--public", required=True)
    wr.add_argument("--repo")
    c = sub.add_parser("caps-proposal")
    c.add_argument("--charged-hours", type=float, default=0.0)
    c.add_argument("--projected-remaining-hours", type=float, required=True)
    pd = sub.add_parser("prepare-data")
    pd.add_argument("--source", required=True)
    pd.add_argument("--parent-suite", required=True)
    pd.add_argument("--out", required=True)
    pd.add_argument("--excluded-spans", required=True, help="JSON list of [row, start, end]: the spans of P10-S2's windows and ADR-0025's windows (computed by the clerk and the auditor)")
    pd.add_argument("--repo")
    rh = sub.add_parser("rehearse")
    rh.add_argument("phase", choices=("r1", "r2", "r3", "synthetic"))
    rh.add_argument("--run-dir", required=True)
    rh.add_argument("--repo")
    rh.add_argument("--sealed-path")
    rh.add_argument("--plan")
    rh.add_argument("--data-manifest")
    rh.add_argument("--parent-suite")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return work_main(args)
        if args.command == "candidate-plan":
            return cmd_candidate_plan(args)
        if args.command == "freeze":
            return cmd_freeze(args)
        if args.command == "write-rate-table":
            return cmd_write_rate_table(args)
        if args.command == "caps-proposal":
            return cmd_caps_proposal(args)
        from . import rehearsal

        if args.command == "prepare-data":
            return rehearsal.cmd_prepare_data(args)
        return rehearsal.cmd_rehearse(args)
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    t0 = time.time()
    code = main()
    sys.exit(code)
