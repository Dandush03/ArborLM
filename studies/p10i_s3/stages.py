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

from . import analysis, core, cost, gates, items, report, runner
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
    out["read_equality"] = gates.read_equality_gate(core.Seeds("dry", cfg).init(0), cfg=cfg)  # the registry's dry-rehearsal value, never a test seed
    out["synthetic_registry"] = gates.synthetic_registry_gate()  # always the registered config: it tests the rules, not a rehearsal's shortened checkpoints
    out["notes"] = {"passed": True, **gates.NOTES}
    from . import planted

    pp = planted.planted_positive(th, core.Seeds("dry", cfg))
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

        run_dir.mkdir(parents=True, exist_ok=True)
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
        items.guarded(items.eval_record_path(run_dir, it), it["id"], lambda it=it: items.run_eval(res, it, run_dir, rec), "eval")
    core.write_record(task_dir(state_dir, "eval") / f"{safe(train_id)}.done.json", {**core.envelope("eval"), "id": train_id, "complete": True}, overwrite=True)
    return 0


def work_r2probe(plan: Plan, repo: Path, arm: str, out: Path) -> int:
    """One R2 probe (R5): a worker, configured (one thread), trains ``r2_updates`` updates of one arm on the DRY seeds (init 330392, the dry stream), then times the enabled read and a full read set with its replay and
    writes timings only (no loss value)."""
    import copy
    import resource
    import tempfile

    from . import model

    cfg = cfg_for(plan, repo)
    res = resources_for(plan, repo, cfg)
    seeds = core.Seeds("dry", cfg)
    n = int(plan.data.get("r2_updates", 50))
    bb = copy.deepcopy(res.backbone(0))
    m = model.build_model(bb, arm, seeds.init(0))
    stream = model.Stream(res.rows[core.REP], seeds.stream(0, 0), fresh=False)
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.monotonic()
        r = model.train_run(m, stream, 0.003, Path(tmp), [n], n, {"r2": arm})
        spu = (time.monotonic() - t0) / max(1, r["updates_done"])
    panel = res.panels["calibration"]
    t0 = time.monotonic()
    model.evaluate(m, panel, expected_targets=res.expected_targets)
    enabled = time.monotonic() - t0
    t0 = time.monotonic()
    model.evaluate_reads(m, panel, seeds, 0, expected_targets=res.expected_targets)
    model.evaluate(m, panel, expected_targets=res.expected_targets)  # the replay
    full = time.monotonic() - t0
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, {"arm": arm, "seconds_per_update": spu, "seconds_per_enabled_read": enabled, "seconds_per_full_read_set": full, "bytes_per_snapshot": r["bytes"], "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "updates": n})
    return 0


def work_main(args: argparse.Namespace) -> int:
    """B1: the process is configured first. An identity difference anywhere in the worker (code, config, src, data files, parent files) exits 75: PAUSED — IDENTITY, nothing written, resumes on restore (R2)."""
    gates.configure_process()
    repo, run_dir = Path(args.repo), Path(args.run_dir)
    state_dir = Path(args.state_dir) if args.state_dir else run_dir
    plan = Plan.load(Path(args.plan))
    try:
        worker_precheck(plan, repo, run_dir)
        return _work_body(args, plan, repo, run_dir, state_dir)
    except StageRefused as e:
        print(f"PAUSED — IDENTITY: {e}", file=sys.stderr)
        return IDENTITY_EXIT


def _work_body(args: argparse.Namespace, plan: Plan, repo: Path, run_dir: Path, state_dir: Path) -> int:
    if args.kind == "r2probe":
        return work_r2probe(plan, repo, args.arm, Path(args.out))
    if args.kind == "gates":
        return work_gates(plan, repo, run_dir, args.name, state_dir)
    if plan.mode == planmod.REGISTERED:
        require_gates_passed(state_dir)
    if args.kind == "train":
        return work_train(plan, repo, run_dir, args.item)
    return work_eval(plan, repo, run_dir, args.train_id, state_dir)


# --- the stage driver ---------------------------------------------------------------------------------------------------------------------
def ledger_of(plan: Plan, repo: Path) -> core.Ledger:
    """The cumulative ledger of charged seconds, in the public run directory (never where it would dirty a working tree)."""
    public = Path(plan.data["run_dir"])
    path = public / "ledger.json"
    planmod.require_ignored_path(repo, path)
    return core.Ledger(path, plan.cap_seconds("any"))


def run_stage(stage: str, plan: Plan, repo: Path, run_dir: Path, plan_path: Path, *, mode: str, identity: Mapping[str, Any], state_dir: Path | None = None) -> int:
    """Run (or resume) a pool stage. ``run_dir`` is the item root (the sealed directory for calibration and DRY items). The cap is cumulative (R1): the invocation gets the cap minus what every earlier stage and
    resume charged; with nothing left the stage is PAUSED and nothing starts. Prints the status; exit 0 only when COMPLETE."""
    started = datetime.now(UTC).isoformat()
    state_dir = state_dir or run_dir
    if stage != "gates" and plan.mode == planmod.REGISTERED:
        require_gates_passed(state_dir)
    tasks = make_tasks(stage, plan, run_dir, plan_path, repo, state_dir)
    ledger = ledger_of(plan, repo)
    left = ledger.remaining()
    if left <= 0:
        out = {t.label: {"status": runner.NOT_STARTED, "seconds": 0.0, "reason": f"the cap of {ledger.total_seconds:.0f} s is spent (cumulative ledger); the stage is PAUSED and the extension is the human lead's", "peak_rss_bytes": 0} for t in tasks if not t.result_path.is_file()}
        seconds = 0.0
    else:
        out, seconds = runner.run_tasks(tasks, workers=int(plan.data["workers"]), cap_seconds=left, rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=Path(plan.data["run_dir"]))
        ledger.charge(stage, seconds)
    prior = runner.read_manifest(state_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        print(json.dumps({"stage": stage, "status": "COMPLETE", "note": "already complete"}))
        return 0
    rec = runner.write_manifest(state_dir, stage, mode, out, seconds, identity=dict(identity), started=started, caps={"cap_seconds_total": ledger.total_seconds, "charged_before_seconds": ledger.charged() - seconds})
    print(json.dumps({"stage": stage, "status": rec["status"], "charged_seconds": rec["charged_seconds"]}))
    return 0 if rec["status"] == "COMPLETE" else 1


def bases_of(state_dir: Path) -> dict[str, dict[str, float | None]]:
    p = gate_path(state_dir, "core")
    return dict(core.read_record(p, "gate")["results"]["base_values"]) if p.is_file() else {}


def run_analysis(plan: Plan, repo: Path, items_dir: Path, cfg: Mapping[str, Any], *, state_dir: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    """Section 10: refuses (ENGINEERING STOP — ITEM ERRORS) while any train or evaluation item error exists, and while any planned evaluation is missing; labels nothing then. Written to ``out_dir`` (for a DRY run, the
    sealed directory)."""
    state_dir = state_dir or items_dir
    reg = items.collect_registry(items_dir, plan.data["items"], bases_of(state_dir))
    cells = sorted({i["cell"] for i in plan.items("train")})
    cell_parent = {c: next(i["parent"] for i in plan.items("train") if i["cell"] == c) for c in cells}
    th = core.Thresholds.from_config(cfg) if plan.mode == planmod.REGISTERED else core.Thresholds.from_config(cfg).scaled(len(cells))
    for it in plan.items("train"):  # a planned run without a record is a missing cell: engineering stop, never a reduced denominator
        if core.run_key(it["arm"], it["regime"], it["rate"], it["cell"]) not in reg:
            raise core.EngineeringStop(f"ENGINEERING STOP — a planned run has no record: {it['id']}")
    result = analysis.analyse(reg, plan.rate_table, cfg, cells=cell_parent, th=th, bitwise=gates.on_platform_of_record(cfg))
    core.write_record((out_dir or items_dir) / "analysis" / "analysis.json", {**core.envelope("analysis"), "result": result, "mode": plan.mode})
    return result


def execute_stage(stage: str, plan: Plan, repo: Path, run_dir: Path, plan_path: Path, *, mode: str, identity: Mapping[str, Any], items_dir: Path | None = None, state_dir: Path | None = None, out_dir: Path | None = None, whitelist_only: bool = False) -> int:
    """The registered driver's stage dispatch, shared with R3's DRY run (R6): gates, train and eval through ``run_stage``; analysis and report through the same functions. ``whitelist_only`` renders the report from
    the whitelist alone (DRY runs: ruling 15, the values go into the sealed archive)."""
    items_dir = items_dir or run_dir
    state_dir = state_dir or run_dir
    out_dir = out_dir or run_dir
    if stage in ("gates", "train", "eval"):
        if stage == "eval":
            m = runner.read_manifest(state_dir, "train")
            if m is None or m["status"] != "COMPLETE":
                print("refused: the train stage is not COMPLETE", file=sys.stderr)
                return 2
        return run_stage(stage, plan, repo, items_dir, plan_path, mode=mode, identity=identity, state_dir=state_dir)
    cfg = cfg_for(plan, repo)
    if stage == "analysis":
        m = runner.read_manifest(state_dir, "eval")
        if m is None or m["status"] != "COMPLETE":
            print("refused: the eval stage is not COMPLETE", file=sys.stderr)
            return 2
        try:
            run_analysis(plan, repo, items_dir, cfg, state_dir=state_dir, out_dir=out_dir)
        except core.EngineeringStop as e:
            print(str(e), file=sys.stderr)
            return 3
        return 0
    if stage == "report":
        rec = core.read_record(out_dir / "analysis" / "analysis.json", "analysis")
        text = report.render_whitelist(rec["result"], plan.mode) if whitelist_only else report.render(rec["result"], plan.mode)
        target = state_dir / "report.md" if whitelist_only else out_dir / "analysis" / "report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return 0
    print(f"unknown stage {stage}", file=sys.stderr)
    return 2


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
    return execute_stage(args.stage, plan, repo, run_dir, repo / core.PLAN, mode=planmod.REGISTERED, identity=identity)


# --- freeze commands -------------------------------------------------------------------------------------------------------------------------------
def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write ``freeze/plan.json`` first and once; ``--supersede`` moves an older file aside (never deletes it). The rate table is ``freeze/rate_table.json`` (written by ``write-rate-table`` from ``rehearsal_public.json``)."""
    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    rt0 = read_json(repo / core.RATE_TABLE)
    projection: dict[str, Any] | None = None
    projected: float | None = None
    if args.r2:  # the cap is COMPUTED by code from R2's record and the candidate item list (section 7: charged + 2 x projected remaining); it is never typed
        r2 = read_json(Path(args.r2))
        hours = cost.project_hours(items.registered_items(cfg, rt0), r2["unit_costs"], cfg)
        projected = hours["hours"]
        projection = {"hours": projected, "detail": hours, "r2_sha256": file_sha256(Path(args.r2)), "unit_costs": r2["unit_costs"]}
        if 2 * projected > float(cfg["caps"]["registered_hours"]) and not args.over_cap_approved:
            raise StageRefused(f"refused: the section-7 cap (2 x {projected:.2f} h) exceeds 48 charged hours: the lead returns to the human lead with the projection (pass --over-cap-approved once the human lead extends it)")
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
    old_files = [repo / gates.SEED_PLAN_FILE, repo / gates.CHECKER_FILE]
    if any(f.exists() for f in old_files):  # a superseded candidate's seed files are moved aside too, never deleted
        if not args.supersede:
            raise StageRefused("refused: the seed plan or checker copy exists; they are replaced only with --supersede")
        for f in old_files:
            if f.exists():
                target = f.parent / "superseded" / f"{f.stem}-{file_sha256(f)[:12]}{f.suffix}"
                target.parent.mkdir(parents=True, exist_ok=True)
                f.rename(target)
    seed_hashes = gates.write_seed_files(repo, cfg)  # real files, frozen inputs: hashed in plan.json with the rest of studies/p10i_s3
    extra: dict[str, Any] = {"seed_files": seed_hashes, "projection": projection}
    if args.data_manifest:
        from . import parents

        dm = Path(args.data_manifest).resolve()
        suite = Path(args.parent_suite).resolve()
        extra.update({"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_suite": str(suite), "parent_files": parents.checkpoint_files(repo, suite)})
    record = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(args.run_dir).resolve(), rate_table=rt, projected_remaining_hours=projected, extra=extra)
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
    sp = gates.seed_files_problems(repo, cfg)
    if sp:
        raise StageRefused("refused: " + "; ".join(sp))
    plan_sha = file_sha256(repo / core.PLAN)
    extra = {k: plan.data[k] for k in ("data_manifest", "data_dir", "parent_suite", "parent_files", "seed_files", "projection") if k in plan.data}
    proj = plan.data.get("projection")
    if proj is not None:  # the cap was computed by code: recompute it from the plan's own items and the recorded unit costs
        again_h = cost.project_hours(plan.data["items"], proj["unit_costs"], cfg)["hours"]
        if again_h != proj["hours"] or plan.data["caps"]["registered_hours"] != 2.0 * proj["hours"]:
            raise StageRefused("refused: the registered cap is not charged + 2 x the projection recomputed from R2's record and the plan's items")
    again = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(plan.data["run_dir"]), rate_table=plan.data["rate_table"], projected_remaining_hours=plan.data["caps"]["registered_hours"] / 2.0, extra=extra)
    if planmod.scientific_content(json.loads(json.dumps(again))) != planmod.scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and rate table: supersede it and rehearse again")
    rehearsal = core.read_record(Path(args.rehearsal), "rehearsal_public")
    if rehearsal.get("caps_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps (a measuring rehearsal cannot be frozen on)")
    # R3: the plan's rate table equals freeze/rate_table.json and R1's public file, and the public file carries the sealed archive's hash
    on_disk = read_json(repo / core.RATE_TABLE)
    if not (plan.data["rate_table"] == on_disk == rehearsal.get("rate_table")):
        raise StageRefused("refused: the plan's rate table, freeze/rate_table.json and rehearsal_public.json's rate table are not the same (the selection is made by code, never typed)")
    sealed_sha = rehearsal.get("sealed_sha256")
    if not (isinstance(sealed_sha, str) and len(sealed_sha) == 64):
        raise StageRefused("refused: rehearsal_public.json carries no sealed-archive SHA-256")
    # R4: no condition is changed after any rehearsal output exists
    if rehearsal.get("rule_hashes") != planmod.rule_hashes(repo):
        raise StageRefused("refused: the rule-bearing configuration sections or labels.py, analysis.py or calibration.py differ from what R1 recorded (an amendment re-runs R1, ruling 18)")
    reh = gates.rehearsal_gate(rehearsal, ("R1", "R2", "R3"), plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the rehearsal record does not show R1, R2 and R3 COMPLETE with this plan file's SHA-256: {reh}")
    seed = gates.seed_gate(cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: the seed gate did not pass: {seed['problems']}")
    record_path.parent.mkdir(parents=True, exist_ok=True)
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
    target.parent.mkdir(parents=True, exist_ok=True)  # a clean checkout has no freeze directory contents to rely on
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
    w.add_argument("kind", choices=("gates", "train", "eval", "r2probe"))
    w.add_argument("--arm")
    w.add_argument("--out")
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
    cp.add_argument("--r2", help="R2's record: the registered cap is computed from it and the candidate items (charged + 2 x projected remaining); without it the plan carries the 48-hour bound and is provisional")
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
    pd.add_argument("--excluded-spans", required=True, help="the output of window-spans (P10-S2's windows, ADR-0025's 44 marker-like windows and the ledger's windows)")
    pd.add_argument("--shared-ledger", help="required when the excluded-spans file says ABSENT-DECLARED: the path this study writes its own spans to first")
    pd.add_argument("--repo")
    ws = sub.add_parser("window-spans")
    ws.add_argument("--source", required=True)
    ws.add_argument("--bundle", required=True, help="P10-S2's recorded bundle directory (windows.json and tokenizer_table.json)")
    ws.add_argument("--manifest", help="bundle_manifest.json that pins both files (default: results/p10s2-datagen-2026-11-16/bundle_manifest.json)")
    ws.add_argument("--out", required=True)
    ws.add_argument("--ledger", help="the shared panel ledger file (ADR-0025 section 4.1)")
    ws.add_argument("--ledger-absent", action="store_true", help="declare, on the record, that the ledger does not exist yet")
    ws.add_argument("--repo")
    rh = sub.add_parser("rehearse")
    rh.add_argument("phase", choices=("r1", "r2", "r3", "synthetic"))
    rh.add_argument("--run-dir", required=True)
    rh.add_argument("--repo")
    rh.add_argument("--sealed-dir", help="r1/synthetic: the folder for the sealed archive (rehearsal_sealed.json) and the sealed item records (items/, about 1.4-2.6 GB of snapshots); r3: the folder for the DRY item records. Required: it must be outside the repository, the lead's checkout and every git working tree")
    rh.add_argument("--plan")
    rh.add_argument("--data-manifest")
    rh.add_argument("--parent-suite")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gates.configure_process()  # B1: before any platform check, in the supervisor as well as in the workers
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
        if args.command == "window-spans":
            return rehearsal.cmd_window_spans(args)
        return rehearsal.cmd_rehearse(args)
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    t0 = time.time()
    code = main()
    sys.exit(code)
