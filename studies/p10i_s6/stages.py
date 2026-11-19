# ruff: noqa: E501
"""P10IS6 stage driver (ADR-0031 section 16): ``registered <stage>`` (the entry point the launch scripts call), ``work`` (worker processes), ``candidate-plan``, ``freeze``, ``write-rate-table``, ``caps-proposal``, ``r2``.
Run from the repository root as ``uv run --locked python -m studies.p10i_s6.stages <command> ...``.

Registered stages: ``gates``, ``train``, ``eval``, ``analysis``, ``report``. They take the run directory and the freeze commit and nothing else; every other value comes from ``freeze/plan.json`` and the config. They REFUSE (exit 2) unless the
tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and freeze record exist and verify, and a committed Decision 2 names the freeze commit. A worker whose identity check fails exits 75
(PAUSED — IDENTITY, nothing written); a training item that stops at a rung on ``<run>/pause-request`` exits 76 (PAUSED — BY REQUEST). A code or environment error is an item error and the analysis refuses. Nothing here is a freeze or a registered run.
A completion print can never fail a finished stage: the stage's record is written and closed first, printing errors are caught (``printing.report.announce``).
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

from . import analysis, core, cost, gates, items, runner
from . import plan as planmod
from .plan import Plan, StageRefused
from .printing import report

IDENTITY_EXIT = runner.IDENTITY_EXIT
ARM_GATES = [f"identity|{a}" for a in core.ARMS]


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


def synthetic_resources(cfg: Mapping[str, Any], seed: int = 0, registered_mode: bool = True) -> items.Resources:
    """Random bytes and random backbones: tests and the synthetic rehearsal. Never used by a registered plan."""
    from .testing import random_rows, synthetic_backbone

    n_reg, n_cal = int(cfg.get("synthetic", {}).get("registered_pool", 200)), int(cfg.get("synthetic", {}).get("calibration_pool", 100))
    table = random_rows(n_reg + n_cal, core.test_seed(900 + seed, cfg)).to(torch.uint8)
    panel = random_rows(4, core.test_seed(901 + seed, cfg))
    return items.Resources(cfg, table, {"registered": (0, n_reg), "calibration": (n_reg, n_cal)}, {"registered": panel, "calibration": panel}, lambda g, p: synthetic_backbone(p % 3), expected_targets=4 * 64, resume_ok=True, registered_mode=registered_mode)


def real_resources(plan: Plan, repo: Path, cfg: Mapping[str, Any]) -> items.Resources:
    """From the plan's data directory and parent directories: the chunk table (memory-mapped, hash-checked), the panels and the parents (digest-checked)."""
    from . import model, parents

    d = plan.data
    manifest = read_json(Path(d["data_manifest"]["path"]))
    ddir = Path(d["data_dir"])
    for name, digest in manifest["files"].items():
        if file_sha256(ddir / name) != digest:
            raise StageRefused(f"refused: {name} does not hash to the data manifest (PAUSED — IDENTITY)")
    t = manifest["table"]
    table = model.map_table(ddir / t["name"], int(t["rows"]))
    panel_bytes = (ddir / manifest["panels_file"]).read_bytes()
    allp = torch.frombuffer(bytearray(panel_bytes), dtype=torch.uint8).long().reshape(-1, 65)
    n = int(cfg["setting"]["panel_chunks"])
    panels = {"registered": allp[:n], "calibration": allp[n : 2 * n]}
    template = None
    cache: dict[tuple[str, int], Any] = {}

    def backbone(group: str, p: int) -> Any:
        nonlocal template
        if (group, p) not in cache:
            if group == "old":
                from studies.p10i_s3 import parents as s3parents

                cache[(group, p)] = s3parents.load_backbone(repo, Path(d["parent_suite"]), p)[0]
            else:
                if template is None:
                    from .testing import synthetic_backbone

                    template = synthetic_backbone(0)
                cache[(group, p)] = parents.load_new_backbone(Path(d["parent_dir"]) / f"{group}{p:02d}.pt", template)
        return cache[(group, p)]

    return items.Resources(cfg, table, {"registered": (0, int(t["registered_rows"])), "calibration": (int(t["registered_rows"]), int(t["calibration_rows"]))}, panels, backbone, resume_ok=_resume_ok(Path(d["run_dir"])), registered_mode=plan.mode == planmod.REGISTERED)


def _resume_ok(public_dir: Path) -> bool:
    p = public_dir / "gates" / "results"
    ok = [p / f"{x.replace('|', '__')}.json" for x in ARM_GATES]
    return all(f.is_file() and core.read_record(f, "gate")["results"]["resume"]["passed"] is True for f in ok)


def resources_for(plan: Plan, repo: Path, cfg: Mapping[str, Any]) -> items.Resources:
    if plan.data.get("synthetic") and plan.mode == planmod.REGISTERED and "synthetic" not in cfg:
        raise StageRefused("refused: a registered plan may use synthetic inputs only in an injected configuration that declares a [synthetic] section (the real config has none)")
    return synthetic_resources(cfg, registered_mode=plan.mode == planmod.REGISTERED) if plan.data.get("synthetic") else real_resources(plan, repo, cfg)


# --- paths, tasks ---------------------------------------------------------------------------------------------------------------------------
def task_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "tasks"


def safe(text: str) -> str:
    return text.replace("|", "__").replace("/", "~")


def gate_path(state_dir: Path, name: str) -> Path:
    return state_dir / "gates" / "results" / f"{safe(name)}.json"


def make_tasks(stage: str, plan: Plan, run_dir: Path, plan_path: Path, repo: Path, state_dir: Path | None = None) -> list[runner.Task]:
    state_dir = state_dir or run_dir
    base = (sys.executable, "-m", "studies.p10i_s6.stages", "work")
    common = ("--run-dir", str(run_dir), "--state-dir", str(state_dir), "--plan", str(plan_path), "--repo", str(repo))
    tasks: list[runner.Task] = []

    def t(label: str, argv: tuple[str, ...], result: Path) -> None:
        tasks.append(runner.Task(label, argv, result, task_dir(state_dir, stage) / f"{safe(label)}.failed.json", task_dir(state_dir, stage) / f"{safe(label)}.log"))

    if stage == "gates":
        for n in ["core", *ARM_GATES]:
            t(n, (*base, "gates", "--name", n, *common), gate_path(state_dir, n))
    elif stage == "train":
        for it in plan.items("train"):
            t(it["id"], (*base, "train", "--item", it["id"], *common), items.train_record_path(run_dir, it))
    elif stage == "eval":
        with_evals = {i["train"] for i in plan.items("eval")}
        for it in plan.items("train"):
            if it["id"] in with_evals:
                t(it["id"], (*base, "eval", "--train-id", it["id"], *common), task_dir(state_dir, stage) / f"{safe(it['id'])}.done.json")
    else:
        raise ValueError(f"{stage} has no pool tasks")
    return tasks


# --- gates ---------------------------------------------------------------------------------------------------------------------------------------
def run_core_gates(plan: Plan, repo: Path, res: items.Resources, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Platform record, identity of every frozen input, seed gate, read equality, planted positive, BASE and disabled = BASE on every parent (registered panel: ruling 15's only trained-model-free reads of it), the D0 and P0 records."""
    from . import model

    out: dict[str, Any] = {}
    registered = plan.mode == planmod.REGISTERED
    out["platform"] = gates.gate("platform", (not gates.platform_problems(cfg)) if registered else None, record=gates.platform_record(), problems=gates.platform_problems(cfg))
    planmod.verify_identity(plan, repo)
    out["identity"] = gates.gate("identity", True, frozen_files=len(plan.data["frozen_files"]), src_files=len(plan.data["src"]["files"]))
    out["seeds"] = gates.seed_gate(cfg, root=repo, run_checker=registered)
    out["read_equality"] = gates.read_equality_gate(core.Seeds("dry", cfg).init(0), cfg)
    pp = model.planted_positive(cfg, core.Seeds("test", cfg))
    out["planted_positive"] = gates.gate("planted_positive", pp["passed"], detail={k: v for k, v in pp.items() if k != "neg_ref"}, neg_ref=pp["neg_ref"])
    bitwise = gates.on_platform_of_record(cfg)
    vals: dict[str, tuple[float, float, float]] = {}
    bases: dict[str, dict[str, float]] = {}
    panel = res.panels["registered" if registered else "calibration"]  # ruling 15: BASE is read on the registered panel in registered mode only
    groups = [("registered", 9 if registered else 3, ""), ("old", 9 if registered else 3, "oa")]
    for group, n, prefix in groups:
        for p in range(n):
            bb = res.backbone(group, p)
            b = model.evaluate(model.build_model(copy.deepcopy(bb), core.BASE, 0), panel, expected_targets=res.expected_targets)
            r = model.evaluate(model.build_model(copy.deepcopy(bb), core.BASE, 0), panel, expected_targets=res.expected_targets)
            flat = model.build_model(copy.deepcopy(bb), core.FLAT, core.Seeds("dry", cfg).init(0))
            flat.bypass = True
            dis = model.evaluate(flat, panel, expected_targets=res.expected_targets)
            vals[f"{prefix}{p}"] = (b, r, dis)
            bases[f"{prefix}{p}"] = {"enabled": b, "replay": r}
    out["base_and_disabled"] = gates.base_gate(vals, bitwise=bitwise)
    out["base_values"] = bases
    if plan.data.get("data_manifest"):
        m = read_json(Path(plan.data["data_manifest"]["path"]))
        out["data"] = gates.gate("data", all(g.get("passed") is True for g in m["gates"].values()), recorded=m["gates"])
    if plan.data.get("parents_record"):
        pr = read_json(Path(plan.data["parents_record"]["path"]))
        out["parents"] = gates.gate("parents", pr.get("adapter_identity", {}).get("passed") is True, recorded={"adapter_identity_passed": pr.get("adapter_identity", {}).get("passed")})
    return out


def run_identity_gate(arm: str, res: items.Resources, cfg: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Prefix identity (a separate run to U_-1 equals snapshot U_-1 of the long run) and resume identity (stopped at U_0 and resumed to U_1 equals the uninterrupted run), bitwise, on calibration cell 0, per arm (G15)."""
    import copy as _copy

    from . import model

    g = cfg["gates"]
    cell, rate = int(g["identity_cell"]), float(g["identity_rate"])
    u_m1, u0, u1 = (core.rung_updates(cfg, k) for k in (-1, 0, 1))
    seeds = core.Seeds("calibration", cfg)
    pstart, psize = res.pools["calibration"]
    ident = {"gate": "identity", "arm": arm}

    def build() -> Any:
        return model.build_model(_copy.deepcopy(res.backbone("calibration", cell)), arm, seeds.init(cell))

    def stream() -> Any:
        return model.PoolStream(res.table, pstart, psize, seeds.stream(cell))

    long_ = model.train_run(build(), stream(), rate, root / "long", [u_m1, u0, u1], u1, ident)
    short = model.train_run(build(), stream(), rate, root / "short", [u_m1], u_m1, ident)
    part = build()
    p1 = model.train_run(part, stream(), rate, root / "part", [u0], u0, ident)
    resumed = build()
    opt = model.restore_for_resume(root / "part", resumed, rate, u0, ident)
    p2 = model.train_run(resumed, stream(), rate, root / "part", [u1], u1, ident, start=u0, optimizer=opt)
    if any(r["status"] != "ok" for r in (long_, short, p1, p2)):
        return {"prefix": {"passed": False, "reason": "a run failed"}, "resume": {"passed": False, "reason": "a run failed"}}
    prefix = model.snapshots_equal(root / "long", u_m1, root / "short", u_m1)
    resume = model.snapshots_equal(root / "long", u1, root / "part", u1)
    return {"prefix": {"passed": bool(prefix), "short": u_m1}, "resume": {"passed": bool(resume), "stop": u0, "resume_to": u1}}


def work_gates(plan: Plan, repo: Path, run_dir: Path, name: str, state_dir: Path) -> int:
    import tempfile

    cfg = cfg_for(plan, repo)
    path = gate_path(state_dir, name)
    if path.is_file():
        return 0
    res = resources_for(plan, repo, cfg)
    if name == "core":
        results = run_core_gates(plan, repo, res, cfg)
        passed = all(v["passed"] is not False for k, v in results.items() if k != "base_values")
        core.write_record(path, {**core.envelope("gate"), "name": name, "passed": passed, "results": results})
    else:
        arm = name.split("|")[1]
        run_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=run_dir) as tmp:
            r = run_identity_gate(arm, res, cfg, Path(tmp))
        core.write_record(path, {**core.envelope("gate"), "name": name, "passed": r["prefix"]["passed"] and r["resume"]["passed"], "results": r})
    return 0


def gates_status(state_dir: Path) -> dict[str, Any]:
    d = state_dir / "gates" / "results"
    recs = {p.stem: core.read_record(p, "gate") for p in sorted(d.glob("*.json"))} if d.is_dir() else {}
    return {"all_present": len(recs) == 1 + len(ARM_GATES), "failed": [k for k, v in recs.items() if v["passed"] is not True], "records": recs}


def require_gates_passed(state_dir: Path) -> None:
    s = gates_status(state_dir)
    if not s["all_present"] or s["failed"]:
        raise StageRefused(f"refused: the gates did not all pass (present: {s['all_present']}); nothing is trained or evaluated: {s['failed']}")


# --- workers --------------------------------------------------------------------------------------------------------------------------------
def worker_precheck(plan: Plan, repo: Path, run_dir: Path) -> None:
    planmod.verify_identity(plan, repo)
    if plan.mode == planmod.REGISTERED:
        planmod.verify_plan(plan, repo, run_dir)


def work_train(plan: Plan, repo: Path, run_dir: Path, item_id: str, public_dir: Path | None) -> int:
    cfg = cfg_for(plan, repo)
    it = plan.item(item_id)
    res = resources_for(plan, repo, cfg)
    if core.pause_requested(public_dir or run_dir):  # item boundary: a pause request before the item starts
        core.log_attempt(public_dir or run_dir, "pause before item", item=item_id)
        return runner.PAUSE_EXIT
    out = items.guarded(items.train_record_path(run_dir, it), item_id, lambda: items.run_train(res, it, run_dir, public_dir or run_dir))
    if out.get("status") == "paused":
        core.log_attempt(public_dir or run_dir, "item paused at a rung snapshot", item=item_id, resume_from=out["resume_from"])
        return runner.PAUSE_EXIT
    return 0


def work_eval(plan: Plan, repo: Path, run_dir: Path, train_id: str, state_dir: Path) -> int:
    cfg = cfg_for(plan, repo)
    res = resources_for(plan, repo, cfg)
    tr = plan.item(train_id)
    rec = core.read_record(items.train_record_path(run_dir, tr), "train")
    if rec.get("status") == "item_error":
        raise RuntimeError("the training item ended in an item error")
    for it in [i for i in plan.items("eval") if i["train"] == train_id]:
        items.guarded(items.eval_record_path(run_dir, it), it["id"], lambda it=it: items.run_eval(res, it, run_dir, rec, tr), "eval")
    core.write_record(task_dir(state_dir, "eval") / f"{safe(train_id)}.done.json", {**core.envelope("eval"), "id": train_id, "complete": True}, overwrite=True)
    return 0


def work_r2probe(plan: Plan, repo: Path, kind: str, arm: str | None, mode: str | None, out: Path, count: int) -> int:
    """One R2 probe as a fresh process through the registered entry point: ``overhead`` does the identity check and builds the resources and nothing else; ``train`` trains ``count`` updates of one arm on the DRY seeds; ``eval`` runs ``count``
    evaluations of one mode on a DRY-trained snapshot. The supervisor times the WHOLE process; no loss value is written."""
    from . import model

    cfg = cfg_for(plan, repo)
    res = resources_for(plan, repo, cfg)
    if kind != "overhead":
        assert arm is not None
        seeds = core.Seeds("dry", cfg)
        pstart, psize = res.pools["calibration"]
        m = model.build_model(copy.deepcopy(res.backbone("calibration", 0)), arm, seeds.init(0))
        if kind == "train":
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                model.train_run(m, model.PoolStream(res.table, pstart, psize, seeds.stream(0)), 0.01, Path(tmp), [], count, {"r2": arm})
        else:
            assert mode is not None
            for _ in range(count):
                model.evaluate_reads(m, res.panel_for("calibration"), seeds, 0, mode, expected_targets=res.expected_targets)
    write_json(out, {"kind": kind, "arm": arm, "mode": mode, "count": count})
    return 0


def work_main(args: argparse.Namespace) -> int:
    gates.configure_process()
    repo, run_dir = Path(args.repo), Path(args.run_dir)
    state_dir = Path(args.state_dir) if args.state_dir else run_dir
    plan = Plan.load(Path(args.plan))
    try:
        worker_precheck(plan, repo, run_dir)
        if args.kind == "r2probe":
            return work_r2probe(plan, repo, args.probe, args.arm, args.mode, Path(args.out), int(args.count))
        if args.kind == "gates":
            return work_gates(plan, repo, run_dir, args.name, state_dir)
        if plan.mode == planmod.REGISTERED:
            require_gates_passed(state_dir)
        if args.kind == "train":
            return work_train(plan, repo, run_dir, args.item, Path(plan.data["run_dir"]))
        return work_eval(plan, repo, run_dir, args.train_id, state_dir)
    except StageRefused as e:
        print(f"PAUSED — IDENTITY: {e}", file=sys.stderr)
        core.log_attempt(run_dir, "identity refusal", reason=str(e)[:300])
        return IDENTITY_EXIT


# --- the stage driver -------------------------------------------------------------------------------------------------------------------------------
def ledger_of(plan: Plan, repo: Path) -> core.Ledger:
    public = Path(plan.data["run_dir"])
    path = public / ("ledger.json" if plan.mode == planmod.REGISTERED else "ledger-rehearsal.json")  # the rehearsals and the registered run charge separate ledgers (the registered cap is charged so far + 2 x projected FROM THE REGISTERED RUN)
    planmod.require_ignored_path(repo, path)
    return core.Ledger(path, plan.cap_seconds())


def run_stage(stage: str, plan: Plan, repo: Path, run_dir: Path, plan_path: Path, *, mode: str, identity: Mapping[str, Any], state_dir: Path | None = None) -> int:
    """Run (or resume) a pool stage under the cumulative cap. The stage's manifest is written first; the completion message comes after and cannot fail the stage."""
    started = datetime.now(UTC).isoformat()
    state_dir = state_dir or run_dir
    if stage != "gates" and plan.mode == planmod.REGISTERED:
        require_gates_passed(state_dir)
    public = Path(plan.data["run_dir"])
    runner.record_stage_start(public, stage)
    tasks = make_tasks(stage, plan, run_dir, plan_path, repo, state_dir)
    ledger = ledger_of(plan, repo)
    left = ledger.remaining()
    if left <= 0:
        out = {t.label: {"status": runner.NOT_STARTED, "seconds": 0.0, "reason": f"the cap of {ledger.total_seconds:.0f} s is spent (cumulative ledger); the stage is PAUSED and the extension is the human lead's", "peak_rss_bytes": 0} for t in tasks if not t.result_path.is_file()}
        seconds = 0.0
    else:
        out, seconds = runner.run_tasks(tasks, workers=int(plan.data["workers"]), cap_seconds=left, rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=public)
        ledger.charge(stage, seconds)
    for label, o in out.items():
        if o["status"] not in (runner.COMPLETED,):
            core.log_attempt(public, f"task {o['status']}", stage=stage, task=label, reason=o.get("reason"))
    prior = runner.read_manifest(state_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        report.announce(json.dumps({"stage": stage, "status": "COMPLETE", "note": "already complete"}))
        return 0
    rec = runner.write_manifest(state_dir, stage, mode, out, seconds, identity={**dict(identity), "computing_files": plan.data["computing_files"]}, started=started, caps={"cap_seconds_total": ledger.total_seconds, "charged_before_seconds": ledger.charged() - seconds})
    report.announce(json.dumps({"stage": stage, "status": rec["status"], "charged_seconds": rec["charged_seconds"]}))
    return 0 if rec["status"] == "COMPLETE" else 1


def bases_of(state_dir: Path) -> dict[str, dict[str, float | None]]:
    p = gate_path(state_dir, "core")
    return dict(core.read_record(p, "gate")["results"]["base_values"]) if p.is_file() else {}


def run_analysis(plan: Plan, repo: Path, items_dir: Path, cfg: Mapping[str, Any], *, state_dir: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    """Refuses (ENGINEERING STOP — ITEM ERRORS / INCOMPLETE REGISTRY) while any item error or missing record exists; labels nothing then."""
    state_dir = state_dir or items_dir
    reg = items.collect_registry(items_dir, plan.data["items"], bases_of(state_dir))
    for it in plan.items("train"):
        if core.run_key(it["arm"], it["rate"], it["cell"], oa=it["profile"] == "oa") not in reg:
            raise core.EngineeringStop(f"ENGINEERING STOP — INCOMPLETE REGISTRY: a planned run has no record: {it['id']}")
    cells = sorted({i["cell"] for i in plan.items("train") if i["profile"] != "oa"})
    oa_cells = sorted({i["cell"] for i in plan.items("train") if i["profile"] == "oa"})
    th = core.Thresholds.from_config(cfg) if plan.mode == planmod.REGISTERED else core.Thresholds.from_config(cfg).scaled(len(cells))
    if plan.mode == planmod.REGISTERED and not gates.on_platform_of_record(cfg):
        raise core.EngineeringStop("ENGINEERING STOP — not the platform of record: a registered result is never produced elsewhere (the integrity checks of section 12.2 are bitwise on macOS arm64, torch 2.8.0, one thread)")
    bitwise = True if plan.mode == planmod.REGISTERED else gates.on_platform_of_record(cfg)  # registered: always bitwise; the 1e-6 tolerance exists only for rehearsals and tests off the platform
    result = analysis.analyse(reg, plan.rate_table, cfg, k_max=plan.k_max, bitwise=bitwise, th=th, cells=len(cells), oa_cells=len(oa_cells) or None)
    core.write_record((out_dir or items_dir) / "analysis" / "analysis.json", {**core.envelope("analysis"), "result": result, "mode": plan.mode})
    return result


def execute_stage(stage: str, plan: Plan, repo: Path, run_dir: Path, plan_path: Path, *, mode: str, identity: Mapping[str, Any], items_dir: Path | None = None, state_dir: Path | None = None, out_dir: Path | None = None) -> int:
    items_dir, state_dir, out_dir = items_dir or run_dir, state_dir or run_dir, out_dir or run_dir
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
            core.log_attempt(Path(plan.data["run_dir"]), "analysis refused", reason=str(e)[:300])
            print(str(e), file=sys.stderr)
            return 3
        return 0
    if stage == "report":
        rec = core.read_record(out_dir / "analysis" / "analysis.json", "analysis")
        text = report.render(rec["result"], plan.mode)
        target = out_dir / "analysis" / "report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        report.announce(f"report written: {target}")
        return 0
    print(f"unknown stage {stage}", file=sys.stderr)
    return 2


def cmd_registered(args: argparse.Namespace) -> int:
    repo, run_dir = Path(args.repo or core.repo_root()), Path(args.run_dir).resolve()
    try:
        identity = planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
        assert identity is not None
        planmod.require_decision_2(repo, args.freeze_commit)
        planmod.require_ignored_path(repo, run_dir)
        plan = planmod.load_registered_plan(repo)
        planmod.verify_plan(plan, repo, run_dir)
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return 2
    return execute_stage(args.stage, plan, repo, run_dir, repo / core.PLAN, mode=planmod.REGISTERED, identity=identity)


# --- freeze commands ---------------------------------------------------------------------------------------------------------------------------------
def _move_aside(path: Path) -> None:
    target = path.parent / "superseded" / f"{path.stem}-{file_sha256(path)[:12]}{path.suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise StageRefused(f"refused: {target} exists")
    path.rename(target)


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write ``freeze/plan.json`` first and once; ``--supersede`` moves an older file aside (never deletes it). The registered cap is COMPUTED from R2's record and the candidate item list (``plan.caps_from_projection``); it is never typed."""
    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    rt = read_json(repo / core.RATE_TABLE)
    dm = Path(args.data_manifest).resolve() if args.data_manifest else None
    manifest = read_json(dm) if dm else None
    k_max = int(manifest["decision"]["k_max"]) if manifest else int(args.k_max)
    plan_items = items.registered_items(cfg, rt, k_max)
    projection: dict[str, Any] | None = None
    projected: float | None = None
    if args.r2:
        r2 = read_json(Path(args.r2))
        hours = cost.project_hours(plan_items, r2["unit_costs"])
        projected = hours["hours"]
        projection = {"hours": projected, "detail": hours, "r2_sha256": file_sha256(Path(args.r2)), "unit_costs": r2["unit_costs"]}
        if planmod.caps_from_projection(0.0, projected) > float(cfg["caps"]["registered_hours_bound"]) and not args.over_cap_approved:
            raise StageRefused(f"refused: the cap ({planmod.caps_from_projection(0.0, projected):.2f} h) exceeds the {cfg['caps']['registered_hours_bound']} h bound: the lead returns to the human lead before Decision 2 and the matrix is not cut")
    plan_path = repo / core.PLAN
    if plan_path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {plan_path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        _move_aside(plan_path)
    extra: dict[str, Any] = {"projection": projection}
    if args.synthetic:
        if "synthetic" not in cfg:
            raise StageRefused("refused: --synthetic needs an injected configuration with a [synthetic] section; the real configuration has none")
        extra["synthetic"] = True
    if dm and manifest is not None:
        extra.update({"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_dir": str(Path(args.parent_dir).resolve()), "parent_suite": str(Path(args.parent_suite).resolve())})
        if args.parents_record:
            pr = Path(args.parents_record).resolve()
            extra["parents_record"] = {"path": str(pr), "sha256": file_sha256(pr)}
        extra["parent_files"] = {str(p): file_sha256(p) for p in sorted(Path(args.parent_dir).resolve().glob("*.pt"))}
    record = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(args.run_dir).resolve(), rate_table=rt, k_max=k_max, projected_remaining_hours=projected, extra=extra, plan_items=plan_items)
    core.write_record(plan_path, record)
    report.announce(json.dumps({"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "items": {k: len(v) for k, v in record["items"].items()}, "caps_provisional": record["caps_provisional"], "registered_cap_hours": record["caps"]["registered_hours"]}))
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    """Write ``freeze/freeze_record.json`` for the committed candidate plan, only if: the caps are not provisional; the plan equals a re-derivation of its scientific content from current code and config; the cap is the shared formula applied to
    the projection recomputed from R2's record and the plan's own items; the counting rehearsal's record names this plan file's SHA-256 and was made on non-provisional caps; the seed gate passes. The ADR's hash is not compared."""
    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    record_path = repo / core.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    plan = Plan.load(repo / core.PLAN)
    if plan.data.get("caps_provisional") or cfg["caps"]["provisional"]:
        raise StageRefused("refused: the caps are provisional")
    plan_sha = file_sha256(repo / core.PLAN)
    proj = plan.data.get("projection")
    if proj is None:
        raise StageRefused("refused: the plan carries no projection from R2")
    again_h = cost.project_hours(plan.data["items"], proj["unit_costs"])["hours"]
    if again_h != proj["hours"] or plan.data["caps"]["registered_hours"] != planmod.caps_from_projection(0.0, proj["hours"]):
        raise StageRefused("refused: the registered cap is not the shared formula (charged + 2 x projected remaining) applied to the projection recomputed from R2's record and the plan's items")
    extra = {k: plan.data[k] for k in ("data_manifest", "data_dir", "parent_dir", "parent_suite", "parent_files", "parents_record", "projection", "synthetic") if k in plan.data}
    rederived = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, run_dir=Path(plan.data["run_dir"]), rate_table=plan.data["rate_table"], k_max=plan.k_max, projected_remaining_hours=proj["hours"], extra=extra)
    if planmod.scientific_content(json.loads(json.dumps(rederived))) != planmod.scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and rate table: supersede it and rehearse again")
    rehearsal = core.read_record(Path(args.rehearsal), "rehearsal_public")
    if rehearsal.get("caps_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps (a measuring rehearsal cannot be frozen on)")
    on_disk = read_json(repo / core.RATE_TABLE)
    if not (plan.data["rate_table"] == on_disk == rehearsal.get("rate_table")):
        raise StageRefused("refused: the plan's rate table, freeze/rate_table.json and rehearsal_public.json's rate table are not the same (the selection is made by code, never typed)")
    if not (isinstance(rehearsal.get("sealed_sha256"), str) and len(rehearsal["sealed_sha256"]) == 64):
        raise StageRefused("refused: rehearsal_public.json carries no sealed-archive SHA-256")
    if rehearsal.get("rule_hashes") != planmod.rule_hashes(repo):
        raise StageRefused("refused: the rule-bearing configuration sections or labels.py, analysis.py or calibration.py differ from what R1 recorded")
    reh = gates.rehearsal_gate(rehearsal, ("R1", "R2", "R3"), plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the rehearsal record does not show R1, R2 and R3 COMPLETE with this plan file's SHA-256: {reh}")
    seed = gates.seed_gate(cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: the seed gate did not pass: {seed['problems']}")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, {**core.envelope("freeze_record"), "plan_file_sha256": plan_sha, "rehearsal": {"path": str(Path(args.rehearsal).resolve()), "sha256": file_sha256(Path(args.rehearsal))}, "seed_gate": seed, "rehearsal_gate": reh})
    report.announce(json.dumps({"freeze_record": str(record_path), "plan_file_sha256": plan_sha}))
    return 0


def cmd_write_rate_table(args: argparse.Namespace) -> int:
    repo = Path(args.repo or core.repo_root())
    pub = core.read_record(Path(args.public), "rehearsal_public")
    target = repo / core.RATE_TABLE
    if target.exists():
        raise StageRefused(f"refused: {target} exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, pub["rate_table"])
    report.announce(json.dumps({"rate_table": str(target), "sha256": file_sha256(target)}))
    return 0


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    """The same formula as the candidate plan and the freeze (``plan.caps_from_projection``)."""
    report.announce(json.dumps({"proposed_registered_cap_hours": planmod.caps_from_projection(args.charged_hours, args.projected_remaining_hours), "rule": "charged so far + 2 x projected remaining (charged is 0 at candidate-plan time)"}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studies.p10i_s6.stages")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("registered")
    r.add_argument("stage", choices=planmod.REGISTERED_STAGES)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--repo")
    w = sub.add_parser("work")
    w.add_argument("kind", choices=("gates", "train", "eval", "r2probe"))
    for a in ("--probe", "--arm", "--mode", "--out", "--state-dir", "--name", "--item", "--train-id"):
        w.add_argument(a)
    w.add_argument("--count", default="1")
    w.add_argument("--run-dir", required=True)
    w.add_argument("--plan", required=True)
    w.add_argument("--repo", required=True)
    cp = sub.add_parser("candidate-plan")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--data-manifest")
    cp.add_argument("--parent-dir")
    cp.add_argument("--parent-suite")
    cp.add_argument("--parents-record")
    cp.add_argument("--k-max", default="4")
    cp.add_argument("--synthetic", action="store_true", help="tiny synthetic inputs; refused unless the configuration declares a [synthetic] section (an injected test configuration)")
    cp.add_argument("--r2")
    cp.add_argument("--over-cap-approved", action="store_true")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze")
    f.add_argument("--rehearsal", required=True)
    f.add_argument("--repo")
    wr = sub.add_parser("write-rate-table")
    wr.add_argument("--public", required=True)
    wr.add_argument("--repo")
    rh = sub.add_parser("rehearse")
    rh.add_argument("rest", nargs=argparse.REMAINDER)
    c = sub.add_parser("caps-proposal")
    c.add_argument("--charged-hours", type=float, default=0.0)
    c.add_argument("--projected-remaining-hours", type=float, required=True)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gates.configure_process()
    try:
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return work_main(args)
        if args.command == "rehearse":
            from . import rehearsal

            return rehearsal.main(args.rest)
        if args.command == "candidate-plan":
            return cmd_candidate_plan(args)
        if args.command == "freeze":
            return cmd_freeze(args)
        if args.command == "write-rate-table":
            return cmd_write_rate_table(args)
        return cmd_caps_proposal(args)
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    t0 = time.time()
    sys.exit(main())
