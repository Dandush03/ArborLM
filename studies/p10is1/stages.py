# ruff: noqa: E501
"""P10IS1 stage driver (ADR-0024 sections 7.2, 11, 14, 16, 18): ``registered <stage>`` (the entry point the fixed launch scripts call), ``generate``, ``candidate-plan``, ``project``, ``freeze``, ``caps-proposal``,
``rehearse``, ``work`` (the worker processes).

Registered stages, in order: ``gates``, ``timing`` (alone, quiet condition), ``train`` (every cell to its base length: a ladder cell to U0), ``ladder`` (the whole cell continues ladder point by ladder point, all arms and all
five replicates together, up to its granted length G; it stops at the first ladder point at which every store arm is full in every replicate; no per-arm early stop), ``evaluate``, ``baselines``, ``analysis``,
``report``, ``throughput`` (alone, after all training and evaluation). Run from the repository root: ``uv run --locked python -m studies.p10is1.stages <command> ...``. A registered stage takes the run directory and the
freeze commit and nothing else; every other value (items, caps, seeds, paths) comes from ``freeze/plan.json`` and ``configs/p10is1_capacity.toml``. It REFUSES unless the working tree is clean, the freeze commit is an ancestor
of HEAD, the frozen files equal their content at it, the plan exists and every identity in it holds, and a committed Decision 2 names the freeze commit. Nothing is frozen today, so every registered stage refuses today.
Stages are resumable (a finished item is not recomputed); a stage manifest records PAUSED or COMPLETE. A code error is an item error (the analysis refuses while any exists); an environment error pauses the task.
"""

import argparse
import json
import sys
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import adapter, analysis, core, gates, items, machine, quiet, report, runner
from . import freeze as freezemod
from . import plan as planmod
from .plan import Plan, StageRefused

CAP_KEY = {"gates": "analysis", "timing": "timing", "train": "train", "ladder": "train", "evaluate": "evaluate", "baselines": "evaluate", "analysis": "analysis", "report": "analysis", "throughput": "throughput"}
WORKER_KINDS = ("train", "evaluate", "baseline")
PRE_TRAINING = ("gates",)


def repo_of(args: argparse.Namespace | None = None) -> Path:
    return Path(getattr(args, "repo", None) or core.repo_root())


def safe(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in text)


def task_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "tasks"


def ctx_for(plan: Plan, run_dir: Path, *, experiments_root: Path | None, synthetic: bool = False, config_path: Path | None = None) -> items.Ctx:
    d = plan.data
    return items.Ctx(mode=plan.mode, run_dir=run_dir, experiments_root=experiments_root, synthetic=synthetic, sizes=dict(d.get("sizes") or {"table_facts": 32768, "unseen": 2048}), manifests={n: Path(r["path"]) for n, r in (d.get("manifests") or {}).items()}, config_path=config_path)


# --- errors and statuses -----------------------------------------------------------------------------------------------------------------------------------
def record_item_error(run_dir: Path, stage: str, item_id: str, exc: BaseException) -> None:
    p = run_dir / stage / "item_errors" / f"{safe(item_id)}.json"
    core.write_record(p, {**core.envelope("engineering_stop"), "stage": stage, "item": item_id, "error": f"{type(exc).__name__}: {str(exc)[:400]}", "traceback": traceback.format_exc()[-2000:]}, overwrite=True)


def item_errors(run_dir: Path) -> list[str]:
    out = []
    for p in sorted(run_dir.glob("*/item_errors/*.json")):
        rec = core.read_record(p, "engineering_stop")
        out.append(f"{rec['stage']}: {rec['item']}: {rec['error']}")
    return out


def failed_cells(run_dir: Path) -> list[str]:
    return sorted(f"{p.parent.name}: {read_json(p).get('reason')}" for p in run_dir.glob("train/cells/*/" + adapter.FAILED_RECORD))


def gates_path(run_dir: Path) -> Path:
    return run_dir / "gates" / "gates.json"


def require_gates_passed(run_dir: Path) -> dict[str, Any]:
    """Training, ladder and evaluation start only when the ``gates`` stage ran and every gate passed (an engineering failure stops a stage before training)."""
    p = gates_path(run_dir)
    if not p.is_file():
        raise StageRefused(f"refused: no gates record at {p}: run the gates stage first")
    rec = core.read_record(p, "gates_record")
    if rec.get("passed") is not True:
        raise StageRefused(f"refused: the gates did not all pass; nothing is trained or read: {rec.get('failed')}")
    return rec


def ledger_of(plan: Plan, run_dir: Path, repo: Path | None = None) -> core.Ledger:
    path = run_dir.parent / ("P10IS1-ledger.json" if plan.mode == core.REGISTERED else f"P10IS1-{plan.mode}-{run_dir.name}-ledger.json")
    if repo is not None:
        planmod.require_ignored_path(repo, path)
    led = core.Ledger(path, float(plan.data["stage_caps"]["total_hours"]) * 3600.0)
    proj = plan.data.get("projection") or {}
    if proj.get("h_charged_hours") and not path.is_file():  # H_c, the hours charged before the freeze, is in the registered ledger from its first entry: the block budget on caps binds on the TRUE total
        led.charge("pre-freeze", "H_c", float(proj["h_charged_hours"]) * 3600.0)
    return led


def stage_cap_seconds(plan: Plan, stage: str, ledger: core.Ledger) -> float:
    key = CAP_KEY[stage]
    spent = sum(ledger.charged(s) for s, k in CAP_KEY.items() if k == key)
    return max(0.0, min(plan.cap_seconds(key) - spent, ledger.remaining()))


# --- workers (the same functions run inline in the rehearsal and in subprocesses) -----------------------------------------------------------------------------
def do_train(ctx: items.Ctx, plan: Plan, label: str, to: int) -> None:
    spec = plan.cell(label)
    spec = {**spec, "mode": plan.mode}
    data, seeds = items.load_data(ctx, spec)
    adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, to, mode=plan.mode, cfg=ctx.cfg())


def do_evaluate(ctx: items.Ctx, plan: Plan, label: str, updates: Sequence[int]) -> None:
    spec = {**plan.cell(label), "mode": plan.mode}
    data, seeds = items.load_data(ctx, spec)
    for u in updates:
        items.evaluate_snapshot(ctx, spec, int(u), data=data, seeds=seeds)


def do_baseline(ctx: items.Ctx, plan: Plan, draw: int, facts: int) -> None:
    spec = next({**c, "mode": plan.mode} for c in plan.data["cells"] if c["draw"] == draw and c["facts"] == facts)
    data, seeds = items.load_data(ctx, spec)
    items.baseline_item(ctx, draw, facts, spec, data=data, seeds=seeds)


def worker_main(args: argparse.Namespace) -> int:
    """A worker process: re-check the identity before the task (a difference exits 75: PAUSED — IDENTITY, nothing written), run the task, write its done mark. A code error is recorded as an item error and exits 1; an
    environment error exits 76 (PAUSED — ENVIRONMENT)."""
    repo, run_dir = repo_of(args), Path(args.run_dir)
    try:
        mode = args.mode
        gates.configure_worker(core.load_config(Path(args.config)) if args.config else None)  # one thread, one interop thread, deterministic: BEFORE the platform check (a fresh worker interpreter has neither set)
        if mode == core.REGISTERED and args.synthetic:
            raise StageRefused("refused: a registered task never uses the synthetic corpus and backbone")
        if mode == core.REGISTERED:
            planmod.check_preconditions(mode, repo, args.freeze_commit)
        pl = Plan.load(Path(args.plan))
        planmod.verify_plan(pl, repo, run_dir, candidate=mode != core.REGISTERED, freeze_commit=args.freeze_commit if mode == core.REGISTERED else None)
        ctx = ctx_for(pl, run_dir, experiments_root=None if args.synthetic else freezemod.experiments_root(), synthetic=args.synthetic, config_path=Path(args.config) if args.config else None)
        label = args.label
        if args.kind == "train":
            do_train(ctx, pl, label, int(args.to))
        elif args.kind == "evaluate":
            do_evaluate(ctx, pl, label, [int(u) for u in args.updates.split(",")])
        elif args.kind == "baseline":
            do_baseline(ctx, pl, int(args.draw), int(args.facts))
        else:
            raise ValueError(f"unknown worker kind {args.kind!r}")
        core.write_record(Path(args.done), {**core.envelope("task_done"), "kind": "task_done", "label": label, "worker": args.kind, "utc": datetime.now(UTC).isoformat()}, overwrite=True)
        return 0
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return core.IDENTITY_EXIT
    except (adapter.NonFinite, adapter.CellFailedBefore) as exc:  # FAILED — NON-FINITE: the cell's own failed record is the whole record (section 14); not an item error
        print(str(exc), file=sys.stderr)
        return 1
    except (MemoryError, OSError) as exc:
        print(f"PAUSED — ENVIRONMENT: {type(exc).__name__}: {exc}", file=sys.stderr)
        return runner.ENVIRONMENT_EXIT
    except Exception as exc:  # noqa: BLE001 - recorded as an item error: never a scientific label
        record_item_error(run_dir, args.stage, f"{args.kind}|{args.label}", exc)
        print(f"ITEM ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


# --- running a pool of tasks ----------------------------------------------------------------------------------------------------------------------------------
class Pool:
    """Runs worker tasks for one stage: inline (rehearsal, tests: in this process) or as subprocesses under ``runner.run_tasks`` (registered)."""

    def __init__(self, plan: Plan, run_dir: Path, plan_path: Path, args: argparse.Namespace, ctx: items.Ctx, *, inline: bool, workers: int, cap_seconds: float, extra_argv: Sequence[str] = ()) -> None:
        self.plan, self.run_dir, self.plan_path, self.args, self.ctx, self.inline, self.workers, self.cap, self.extra = plan, run_dir, plan_path, args, ctx, inline, workers, cap_seconds, list(extra_argv)
        self.outcomes: dict[str, dict[str, Any]] = {}
        self.seconds = 0.0

    def run(self, stage: str, tasks: Sequence[tuple[str, str, Mapping[str, Any]]]) -> dict[str, dict[str, Any]]:
        """``tasks``: (label, worker kind, parameters). A task whose done mark exists is not run again."""
        cfg = self.ctx.cfg()
        began = time.monotonic()
        out: dict[str, dict[str, Any]] = {}
        if self.inline:
            for label, kind, params in tasks:
                done = task_dir(self.run_dir, stage) / f"{safe(kind + '|' + label + '|' + json.dumps(params, sort_keys=True))}.done.json"
                if done.is_file():
                    out[label] = {"status": runner.COMPLETED, "skipped": "done mark exists"}
                    continue
                try:
                    if kind == "train":
                        do_train(self.ctx, self.plan, label, int(params["to"]))
                    elif kind == "evaluate":
                        do_evaluate(self.ctx, self.plan, label, params["updates"])
                    else:
                        do_baseline(self.ctx, self.plan, int(params["draw"]), int(params["facts"]))
                except (MemoryError, OSError):
                    raise
                except (adapter.NonFinite, adapter.CellFailedBefore) as exc:
                    out[label] = {"status": runner.FAILED, "reason": str(exc)}
                    continue
                except Exception as exc:  # noqa: BLE001
                    record_item_error(self.run_dir, stage, f"{kind}|{label}", exc)
                    out[label] = {"status": runner.FAILED, "reason": f"{type(exc).__name__}: {exc}"}
                    continue
                core.write_record(done, {**core.envelope("task_done"), "label": label, "worker": kind}, overwrite=True)
                out[label] = {"status": runner.COMPLETED}
            self.seconds += time.monotonic() - began
            return out
        pending = []
        for label, kind, params in tasks:
            done = task_dir(self.run_dir, stage) / f"{safe(kind + '|' + label + '|' + json.dumps(params, sort_keys=True))}.done.json"
            argv = [sys.executable, "-m", "studies.p10is1.stages", "work", kind, "--stage", stage, "--label", label, "--run-dir", str(self.run_dir), "--plan", str(self.plan_path), "--mode", self.plan.mode, "--done", str(done), *self.extra]
            for k, v in params.items():
                argv += [f"--{k}", ",".join(map(str, v)) if isinstance(v, list | tuple) else str(v)]
            pending.append(runner.Task(f"{kind}|{label}|{json.dumps(params, sort_keys=True)}", tuple(argv), done, task_dir(self.run_dir, stage) / f"{safe(label)}.failed.json", task_dir(self.run_dir, stage) / f"{safe(label)}.log"))
        res = cfg["resources"]
        outcomes, secs = runner.run_tasks(pending, workers=self.workers, cap_seconds=max(0.0, self.cap - self.seconds), rss_worker_bytes=int(res["rss_worker_bytes"]), rss_aggregate_bytes=int(res["rss_aggregate_bytes"]), memory_ok=lambda: quiet.memory_ok_once(int(res["rss_aggregate_bytes"])), memory_retry=float(cfg["memory_check"]["retry_seconds"]), memory_max=float(cfg["memory_check"]["max_hours"]) * 3600.0)
        self.seconds += secs
        return outcomes


# --- the ladder (the whole cell stops together) ----------------------------------------------------------------------------------------------------------------
def ladder_path(run_dir: Path, name: str) -> Path:
    return run_dir / "ladder" / f"{name.replace('/', '_')}.json"


def run_ladder_cell(pool: Pool, item: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    """One ladder cell, whole: every arm and replicate trains to U0; the stop rule is evaluated for every store arm and replicate at U0; while any store arm is not full in any replicate and the next level lies within G
    the WHOLE cell continues to the next ladder point (never one arm); the cell stops at the first ladder point at which every store arm is full in every replicate, or at G. U_run is the same for every arm and replicate.
    The decision is recorded (``ladder/<cell>.json``) and a finished decision is final (resumable)."""
    name = item["cell_name"]
    path = ladder_path(run_dir, name)
    if path.is_file():
        return core.read_record(path, "decision")
    cfg = pool.ctx.cfg()
    specs = [pool.plan.cell(label) for label in item["labels"]]
    u0, granted = int(item["u0"]), int(item["granted"])
    rounds: list[dict[str, Any]] = []
    point = u0
    while True:
        for stage_kind in ("train", "evaluate"):
            tasks = []
            for s in specs:
                ups = [u for u in s["snapshots"] if (rounds[-1]["point"] if rounds else 0) < u <= point]
                tasks.append((s["label"], stage_kind, {"to": point} if stage_kind == "train" else {"updates": ups}))
            res = pool.run("ladder", tasks)
            bad = {k: v for k, v in res.items() if v["status"] != runner.COMPLETED}
            if bad:
                raise StageRefused(f"refused: ladder cell {name} could not finish the round at {point}: {sorted(bad)[:3]} (PAUSED; the cell resumes)")
        dec = items.ladder_decision(pool.ctx, [pool.plan.cell(s["label"]) for s in specs], point, cfg)
        rounds.append({"point": point, "all_full": dec["all_full"]})  # the per-arm statistic is not recorded: the stop rule sees it, nobody else
        nxt = items.next_level(u0, granted, point, cfg)
        if dec["all_full"] or nxt is None:
            break
        point = nxt
    rec = {**core.envelope("decision"), "cell_name": name, "u0": u0, "granted": granted, "u_run": point, "stopped_by": "full" if rounds[-1]["all_full"] else "granted length G", "rounds": rounds, "not_full_within_budget_at_g": not rounds[-1]["all_full"]}
    core.write_record(path, rec)
    return rec


# --- gates ------------------------------------------------------------------------------------------------------------------------------------------------------
def run_gates(pl: Plan, ctx: items.Ctx, run_dir: Path, *, repo: Path, run_checker: bool = True, adapter_identity: bool = True) -> dict[str, Any]:
    """The engineering gates before any training: the platform of record (registered), gate G9 (seeds), the draws' manifests (each draw regenerated by the fixed generator and equal to its manifest), the adapter identity
    gate (P10-S1's stored F-OQ and T-OQ checkpoints reproduced tensor for tensor) and the restoration check G4 on the rehearsal draw. A failure stops the stage before training."""
    cfg = ctx.cfg()
    rec: dict[str, Any] = {**core.envelope("gates_record"), "mode": pl.mode, "platform": gates.platform_record(), "gates": {}, "failed": []}
    rec["gates"]["platform"] = gates.gate("platform", not gates.platform_problems(cfg) if pl.mode == core.REGISTERED else None, name="platform", problems=gates.platform_problems(cfg))
    rec["gates"]["G9"] = gates.seed_gate(cfg, root=repo, run_checker=run_checker and pl.mode == core.REGISTERED)
    seen: set[str] = set()
    ok_draws, why = True, []
    for c in pl.data["cells"]:
        if c["seed_name"] in seen:
            continue
        seen.add(c["seed_name"])
        try:
            items.load_data(ctx, {**c, "mode": pl.mode}, verify=True)
        except core.StageRefused as exc:
            ok_draws = False
            why.append(str(exc))
        except Exception as exc:  # noqa: BLE001 - a gate that cannot run (no corpus, no backbone) fails and is recorded; it is not raised past the stage
            ok_draws = False
            why.append(f"{type(exc).__name__}: {str(exc)[:200]}")
    rec["gates"]["manifests"] = gates.gate("data", ok_draws, name="manifests", draws=len(seen), problems=why)
    ident = pl.data.get("identity_gate") or {}
    if adapter_identity and pl.mode == core.REGISTERED:
        s1_dir = ident.get("s1_run_dir")
        if not s1_dir or not Path(s1_dir).is_dir():
            rec["gates"]["adapter_identity"] = gates.gate("adapter identity gate", False, name="adapter_identity", reason="no P10-S1 run directory with the stored checkpoints is named by the plan")
        else:
            from studies.p9 import data as dm
            from studies.p10s1 import core as s1

            seeds = s1.registered_draw_seeds(int(cfg["seeds"]["identity_gate_draw"]))
            d1 = dm.build_study_data(seeds, items.corpus_of(ctx)[1], sizes=dm.DataSizes(main_trained=ctx.sizes["table_facts"], unseen=ctx.sizes["unseen"], lane_d_per_set=s1.LANE_D_STUB))
            cells = [(arm, ident["cell"][0], ident["cell"][1], int(cfg["seeds"]["identity_gate_draw"]), int(cfg["seeds"]["identity_gate_init"]), 8192, 49152) for arm in ("F-OQ", "T-OQ")]
            rec["gates"]["adapter_identity"] = adapter.identity_gate(Path(s1_dir), run_dir / "gates" / "identity_work", data=d1, seeds=seeds, backbone=items.backbone_of(ctx), cells=cells, updates=[int(u) for u in ident["updates"]], cfg=cfg)
    else:
        rec["gates"]["adapter_identity"] = gates.gate("adapter identity gate", None, name="adapter_identity", reason=f"not run in {pl.mode} mode: the registered gate reproduces P10-S1's stored checkpoints")
    rec["failed"] = [n for n, g in rec["gates"].items() if g.get("passed") is False]
    rec["passed"] = not rec["failed"]
    core.write_record(gates_path(run_dir), rec, overwrite=True)
    return rec


# --- timing and throughput (alone) ---------------------------------------------------------------------------------------------------------------------
def measure_timing(pl: Plan, ctx: items.Ctx, *, warmup: int | None = None, updates: int | None = None, repeats: int | None = None, guard: Callable[[], None] | None = None) -> dict[str, Any]:
    """The isolated timing stage's measurement (the source of MC-T): single-thread process CPU seconds per update of every (arm, slots) of the plan on the rehearsal draw (P10-S1's ``cpu_seconds_per_update``). All or
    nothing. Every item keeps its PER-REPEAT values (``runs``: CPU seconds per update, ``wall_runs``: wall seconds per update) and the CPU-to-wall ratio per repeat (addendum A3.4, A8 item 5: the timing-spread rule
    reads them). ``guard`` (the stage's own cap) is called before each item and may raise ``quiet.CapReached``."""
    from studies.p10s1 import timing as s1timing

    cfg = ctx.cfg()
    q = cfg["quiet"]
    cpu: dict[str, float] = {}
    detail: dict[str, Any] = {}
    seeds, init = core.seeds_for(core.REHEARSAL if pl.mode == core.REGISTERED else pl.mode, 1, cfg)
    for it in pl.items("timing"):
        if guard is not None:
            guard()
        c = next(x for x in pl.data["cells"] if x["arm"] == it["arm"] and x["slots"] == it["slots"])
        spec = {**c, "seed_name": seeds.name, "seed_base": seeds.facts, "init_seed": init, "mode": core.REHEARSAL if pl.mode == core.REGISTERED else pl.mode}
        data, sd = items.load_data(ctx, spec, verify=False)
        cell = core.make_cell(spec["mode"], c["arm"], c["facts"], c["slots"], 1, init, u_p=c["u_p"], run=c["run"], lr=c["lr"])
        job = adapter.job_for(cell, data, sd, items.backbone_of(ctx), ctx.run_dir / "timing" / "work", (), optimizer_marks=(), max_updates=None, mode="calibration")
        r = s1timing.cpu_seconds_per_update(job, warmup=warmup or int(q["timing_warmup_updates"]), updates=updates or int(q["timing_updates"]), repeats=repeats or int(q["timing_repeats"]))
        cpu[f"{it['arm']}|{it['slots']}"] = float(r["cpu_seconds_per_update"])
        detail[f"{it['arm']}|{it['slots']}"] = {"wall_seconds_per_update": r["wall_seconds_per_update"], "peak_rss_bytes": r["peak_rss_bytes"], "runs": [float(x) for x in r["runs"]], "wall_runs": [float(x) for x in r["wall_runs"]], "cpu_to_wall_per_repeat": [float(c_) / float(w_) if w_ > 0 else None for c_, w_ in zip(r["runs"], r["wall_runs"], strict=False)]}
    return {"cpu": cpu, "detail": detail, "draw": "rehearsal", "platform": gates.platform_record()}


def measure_throughput(pl: Plan, ctx: items.Ctx, guard: Callable[[], None] | None = None) -> dict[str, Any]:
    """The read-path throughput of the trained checkpoints at U_P of the first replicate (RAM, one process; descriptive only), for every item of the plan's throughput list."""
    import torch

    from studies.p10s1 import core as s1
    from studies.p10s1 import timing as s1timing
    from studies.p10s1.model import build_model
    from studies.p10s1.train import fact_lut_for, load_model_state

    out: dict[str, Any] = {}
    for it in pl.items("throughput"):
        if guard is not None:
            guard()  # the stage's own cap on charged measuring seconds, checked before each item
        spec = {**pl.cell(it["cell"]), "mode": pl.mode}
        data, seeds = items.load_data(ctx, spec, verify=False)
        snap = adapter.cell_dir(ctx.run_dir, spec["label"]) / "snapshots" / s1.snapshot_stem(int(it["update"]))
        cell = adapter.cell_of(spec, pl.mode)
        model = build_model(cell.arm, cell.slots, cell.init_seed, items.backbone_of(ctx), fact_lut=fact_lut_for(data, cell.facts) if cell.arm == "R2" else None, r1_seed=seeds.r1_codes, hash_seed=s1.h8_seed(seeds), seed_rng=False)
        load_model_state(snap, model)
        with torch.no_grad():
            out[f"{it['arm']}|{it['facts']}|{it['slots']}"] = s1timing.throughput_record(model, data, cell.facts, seeds, it["arm"])
    return {"results": out, "scope": "read path only, RAM, CPU, one process: not storage I/O, not latency of a language model", "platform": gates.platform_record()}


# --- the registry and the analysis ----------------------------------------------------------------------------------------------------------------------------
def build_registry(ctx: items.Ctx, pl: Plan, run_dir: Path, *, rehearsal_record: Mapping[str, Any] | None = None) -> analysis.Registry:
    d = pl.data
    cells = d["cells"]
    names = items.cell_names_of(cells)
    stops = items.stops_from_records(run_dir, names)
    reads: dict[str, dict[str, Any]] = {}
    for c in cells:
        run = int(stops[core.cell_name(c["facts"], c["slots"])]["u_run"]) if c["ladder_cell"] and core.cell_name(c["facts"], c["slots"]) in stops else int(c["run"])
        for u in c["snapshots"]:
            if u > run:
                continue
            p = ctx.eval_path(c["label"], u)
            if p.is_file():
                rec = core.read_record(p, "eval")
                for read, body in rec["reads"].items():
                    reads[core.read_key(c["label"], u, read)] = {"panels": body["panels"]}
    baselines: dict[str, dict[str, int]] = {}
    for p in sorted((run_dir / "baselines").glob("*.json")) if (run_dir / "baselines").is_dir() else []:
        rec = core.read_record(p, "baseline")
        baselines[core.baseline_key(int(rec["draw"]), int(rec["facts"]))] = {k: int(v) for k, v in rec["no_memory"].items()}
    cpu: dict[str, float] | None = None
    tp = run_dir / "timing" / "timing.json"
    if tp.is_file():
        cpu = {k: float(v) for k, v in core.read_record(tp, "timing")["cpu"].items()}
    cal = d["calibration"]
    h8 = cal.get("h8", {})
    status = {
        "run": f"{run_dir.name} ({pl.mode})", "stages": {"analysis (capacity)": "the registered run's records", "analysis (saturation)": "the registered run's records", "analysis (efficiency)": "the registered run's records and the isolated timing record", "train (ladder)": "ladder decisions", "throughput": quiet.throughput_label(run_dir)},
        "item_errors": item_errors(run_dir), "failed_cells": failed_cells(run_dir), "lane_l": d.get("lane_l", core.LANE_L_NOT_LICENSED),
    }  # fmt: skip
    paused = []
    for mp in sorted(run_dir.glob("*/manifest.json")):
        m = core.read_record(mp, "stage_manifest")
        if m.get("status") == "PAUSED":
            paused.append(f"{m['stage']}: PAUSED")
    status["paused"] = paused
    gp = gates_path(run_dir)
    if gp.is_file() and core.read_record(gp, "gates_record").get("passed") is not True:
        status["gate_failures"] = core.read_record(gp, "gates_record").get("failed", ["gates"])
    return analysis.Registry(cells=cells, reads=reads, baselines=baselines, ladder_stops={k: {"u_run": v["u_run"]} for k, v in stops.items()}, cpu=cpu, qualification=dict((rehearsal_record or {}).get("qualification") or {}), calibration={"h8_undertrained": h8.get("undertrained_cells", []), "h8_calibrated": h8.get("calibrated_cells", []), "sat256": bool(cal.get("sat256", True))}, status=status, cfg=ctx.cfg())


def do_analysis(ctx: items.Ctx, pl: Plan, run_dir: Path, rehearsal_record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The analysis REFUSES while any item error exists (section 14); else a pure function over the records. Written once per call (overwritten with the same inputs)."""
    errs = item_errors(run_dir)
    if errs:
        res = analysis.analyze(build_registry(ctx, pl, run_dir, rehearsal_record=rehearsal_record))
        core.write_record(run_dir / "analysis" / "analysis.json", {**core.envelope("analysis"), "result": core.jsonable(res)}, overwrite=True)
        raise StageRefused("refused: the analysis refuses while a registered stage holds an item error (ENGINEERING STOP — ITEM ERRORS): " + "; ".join(errs[:3]))
    res = analysis.analyze(build_registry(ctx, pl, run_dir, rehearsal_record=rehearsal_record))
    core.write_record(run_dir / "analysis" / "analysis.json", {**core.envelope("analysis"), "result": core.jsonable(res)}, overwrite=True)
    return res


def do_report(run_dir: Path, pl: Plan) -> str:
    res = read_json(run_dir / "analysis" / "analysis.json")["result"]
    text = report.render(res, throughput={"state": {"MEASURED": "MEASURED", "THROUGHPUT NOT MEASURED": "NOT MEASURED"}.get(quiet.throughput_label(run_dir), "PAUSED")}, caps=pl.data["stage_caps"])
    out = run_dir / "report" / "REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return text


# --- executing a registered stage ------------------------------------------------------------------------------------------------------------------------------
def _execute_stage_body(stage: str, pl: Plan, ctx: items.Ctx, run_dir: Path, plan_path: Path, args: argparse.Namespace, *, repo: Path, inline: bool = False, workers: int | None = None, sleep: Callable[[float], None] | None = None, quiet_reading: Callable[[], dict[str, Any]] | None = None, end_fn: Callable[[Sequence[int]], dict[str, Any]] | None = None, clock: Callable[[], float] | None = None, ledger: core.Ledger | None = None, holder: dict[str, Any] | None = None) -> tuple[str, dict[str, Any], Any]:
    """The body of a stage: returns (status, result, pool)."""
    cfg = ctx.cfg()
    cap = stage_cap_seconds(pl, stage, ledger)
    n_workers = workers or int(cfg["resources"]["workers"])
    extra = ["--freeze-commit", args.freeze_commit] if getattr(args, "freeze_commit", None) else []
    if getattr(args, "synthetic", False):
        extra.append("--synthetic")
    if ctx.config_path:
        extra += ["--config", str(ctx.config_path)]
    pool = Pool(pl, run_dir, plan_path, args, ctx, inline=inline, workers=n_workers, cap_seconds=cap, extra_argv=extra)
    if holder is not None:
        holder["pool"] = pool
    status, result = "COMPLETE", {}
    if stage == "gates":
        rec = run_gates(pl, ctx, run_dir, repo=repo, run_checker=pl.mode == core.REGISTERED)
        status = "COMPLETE" if rec["passed"] else "FAILED"
        result = {"passed": rec["passed"], "failed": rec["failed"]}
    elif stage in ("timing", "throughput"):
        if stage == "throughput":
            require_gates_passed(run_dir)
        if quiet.stage_state(run_dir, stage, f"{stage}.json") in ("COMPLETE", quiet.NOT_MEASURED):
            result = {"state": quiet.stage_state(run_dir, stage, f"{stage}.json")}
        else:
            measure = (lambda guard: measure_timing(pl, ctx, guard=guard)) if stage == "timing" else (lambda guard: measure_throughput(pl, ctx, guard))
            sleeper = sleep or time.sleep
            account = holder["account"] if holder is not None else {}
            clock_kw: dict[str, Any] = {"clock": clock} if clock else {}
            # ONE code path for the registered stage and the counting rehearsal: the reading is the config's measured rule (``quiet.quiet_reading``) unless a test injects one; the waiting is not charged (it goes to
            # ``account['wait_seconds']``), the measuring seconds are, against the stage's own cap
            r = quiet.run_alone_stage(
                run_dir, stage, measure, reading=quiet_reading or quiet.quiet_reading, end=end_fn or (lambda s: quiet.end_check(s, sleep=sleeper)), sleep=sleeper, cfg=cfg, **clock_kw,
                validate=(lambda res: quiet.timing_spreads(res, cfg)) if stage == "timing" else None, cap_seconds=cap, account=account, guarded=True,
            )  # fmt: skip
            if r["status"] == "COMPLETE":
                core.write_record(run_dir / stage / f"{stage}.json", {**core.envelope("timing" if stage == "timing" else "throughput"), **{k: v for k, v in r["result"].items()}, "quiet": r["end_check"], "attempt_record": r["attempt_record"], "wait_seconds": r["wait_seconds"], "measure_seconds": r["measure_seconds"], "retimed": r["retimed"], "timing_spread": r.get("validation")})
            else:
                status = "PAUSED"
            result = {k: v for k, v in r.items() if k not in ("result", "load_trace", "timing_attempts")}
    elif stage in ("train", "ladder", "evaluate", "baselines"):
        require_gates_passed(run_dir)
        if stage in ("train", "ladder"):
            quiet.require_timing_settled(run_dir)
        if stage == "train":
            tasks = [(it["cell"], "train", {"to": it["to"]}) for it in pl.items("train")]
            out = pool.run("train", tasks)
            status = "COMPLETE" if all(v["status"] == runner.COMPLETED for v in out.values()) else "PAUSED"
            result = {k: v["status"] for k, v in out.items() if v["status"] != runner.COMPLETED}
        elif stage == "ladder":
            decisions = {}
            for it in pl.items("ladder"):
                decisions[it["cell_name"]] = run_ladder_cell(pool, it, run_dir)["u_run"]
            result = {"u_run": decisions}
        elif stage == "evaluate":
            ladder_names = {core.cell_name(c["facts"], c["slots"]) for c in pl.data["cells"] if c["ladder_cell"]}
            for n in ladder_names:
                if not ladder_path(run_dir, n).is_file():
                    raise StageRefused(f"refused: the ladder stage has not decided {n}: evaluate runs after it")
            out = pool.run("evaluate", [(it["cell"], "evaluate", {"updates": it["updates"]}) for it in pl.items("evaluate")])
            status = "COMPLETE" if all(v["status"] == runner.COMPLETED for v in out.values()) else "PAUSED"
            result = {k: v["status"] for k, v in out.items() if v["status"] != runner.COMPLETED}
        else:
            out = pool.run("baselines", [(it["cell"], "baseline", {"draw": it["draw"], "facts": it["facts"]}) for it in pl.items("baselines")])
            status = "COMPLETE" if all(v["status"] == runner.COMPLETED for v in out.values()) else "PAUSED"
    elif stage == "analysis":
        res = do_analysis(ctx, pl, run_dir, rehearsal_record_of(pl, repo))
        result = {"status": res["status"], "lines": res["lines"]}
    elif stage == "report":
        do_report(run_dir, pl)
        result = {"report": str(run_dir / "report" / "REPORT.md")}
    else:
        raise ValueError(f"unknown stage {stage!r}")
    return status, result, pool


def execute_stage(stage: str, pl: Plan, ctx: items.Ctx, run_dir: Path, plan_path: Path, args: argparse.Namespace, *, repo: Path, inline: bool = False, workers: int | None = None, sleep: Callable[[float], None] | None = None, quiet_reading: Callable[[], dict[str, Any]] | None = None, end_fn: Callable[[Sequence[int]], dict[str, Any]] | None = None, clock: Callable[[], float] | None = None) -> dict[str, Any]:
    """One stage, resumable, from the plan only. The seconds it used are charged to the ledger in a ``finally``: a stage that raises (a paused ladder round) still charges what it spent, so the caps are cumulative across invocations."""
    ledger = ledger_of(pl, run_dir, repo if pl.mode == core.REGISTERED else None)
    ledger.require_room(stage)
    began = time.monotonic()
    started = datetime.now(UTC).isoformat()
    holder: dict[str, Any] = {"account": {"measure_seconds": 0.0, "wait_seconds": 0.0}}
    try:
        status, result, pool = _execute_stage_body(stage, pl, ctx, run_dir, plan_path, args, repo=repo, inline=inline, workers=workers, sleep=sleep, quiet_reading=quiet_reading, end_fn=end_fn, clock=clock, ledger=ledger, holder=holder)
    finally:
        pool_seconds = holder["pool"].seconds if "pool" in holder else 0.0
        waited = float(holder["account"]["wait_seconds"])
        if stage in ("train", "ladder", "evaluate", "baselines"):
            secs = pool_seconds
        elif stage in quiet.STAGES_ALONE:
            secs = float(holder["account"]["measure_seconds"])  # the measuring seconds only: the waiting for a quiet reading is recorded, never charged (ADR-0024 addendum A8 item 9; ADR-0028 section 9)
        else:
            secs = max(pool_seconds, time.monotonic() - began)
        ledger.charge(stage, run_dir.name, secs)
    rec = {**core.envelope("stage_manifest"), "stage": stage, "mode": pl.mode, "status": status, "result": result, "started_utc": started, "finished_utc": datetime.now(UTC).isoformat(), "charged_seconds": secs, "waited_seconds_not_charged": waited}
    p = run_dir / stage / "manifest.json"
    prior = core.read_record(p, "stage_manifest") if p.is_file() else None
    if prior is not None and prior["status"] == "COMPLETE" and status == "COMPLETE":
        return prior
    core.write_record(p, rec, overwrite=True)
    return rec


def rehearsal_record_of(pl: Plan, repo: Path) -> dict[str, Any] | None:
    """The rehearsal record the freeze named (its R2 qualification table is a frozen input of the analysis); None where there is no freeze record."""
    fr = repo / planmod.FREEZE_RECORD
    if pl.mode != core.REGISTERED or not fr.is_file():
        return None
    ref = read_json(fr).get("rehearsal") or {}
    p = Path(ref.get("path", ""))
    if not p.is_file() or core.file_sha256(p) != ref.get("sha256"):
        raise StageRefused("refused: the freeze record's rehearsal record does not hash to what it names (PAUSED — IDENTITY)")
    return core.read_record(p, "rehearsal")


def cmd_registered(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    try:
        gates.configure_worker()  # one thread, one interop thread, deterministic: BEFORE the platform check, so a registered launch can start whatever the shell had set
        planmod.check_preconditions(core.REGISTERED, repo, args.freeze_commit)
        pl = planmod.load_registered_plan(repo)
        planmod.verify_plan(pl, repo, run_dir, freeze_commit=args.freeze_commit)
        planmod.require_decision_2(repo, args.freeze_commit)
        planmod.require_ignored_run_dir(repo, run_dir)
        ctx = ctx_for(pl, run_dir, experiments_root=freezemod.experiments_root())
        with machine.keep_awake():  # a child of this process: inside the stage's own process family (the study-process check counts descendants as its own)
            rec = execute_stage(args.stage, pl, ctx, run_dir, repo / core.PLAN, args, repo=repo)
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return core.IDENTITY_EXIT if "IDENTITY" in str(exc) or "not clean" in str(exc) or "freeze commit" in str(exc) else 2
    print(json.dumps({"stage": args.stage, "status": rec["status"], "result": core.jsonable(rec.get("result"))}))
    return 0 if rec["status"] == "COMPLETE" else 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studies.p10is1.stages")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("registered", help="one registered stage (refuses unless frozen and decided)")
    r.add_argument("stage", choices=planmod.REGISTERED_STAGES)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--repo")
    g = sub.add_parser("generate", help="the draws' manifests (before the freeze)")
    g.add_argument("--run-dir", required=True)
    cp = sub.add_parser("candidate-plan", help="write the candidate freeze/plan.json once")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--calibration", required=True)
    cp.add_argument("--projection")
    cp.add_argument("--s1-run-dir")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    pr = sub.add_parser("project", help="the projection of section 17.1 from the measuring rehearsal's rates")
    pr.add_argument("--calibration", required=True)
    pr.add_argument("--rates", required=True)
    pr.add_argument("--charged-hours", type=float, default=0.0, help="hours charged before the freeze that have no ledger (typed by hand); added to every --ledger")
    pr.add_argument("--ledger", action="append", help="a ledger file of a stage before the freeze (calibration, generate/qualify/rehearsal pre-freeze ledger); repeatable")
    pr.add_argument("--out", required=True)
    pr.add_argument("--repo")
    f = sub.add_parser("freeze", help="write freeze/freeze_record.json for the committed candidate plan")
    f.add_argument("--rehearsal", required=True)
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal", help="print the cap section 15 proposes: charged + 2 x projected remaining, rounded up")
    c.add_argument("--charged-hours", type=float, required=True)
    c.add_argument("--projected-remaining-hours", type=float, required=True)
    ca = sub.add_parser("calibrate", help="the calibration on the calibration draws; item records go to the sealed directory")
    ca.add_argument("--sealed-dir", required=True)
    ca.add_argument("--run-dir", required=True)
    ca.add_argument("--workers")
    wc = sub.add_parser("work-calibrate", help="a calibration worker process (one job)")
    for a in ("--job", "--sealed-dir", "--done"):
        wc.add_argument(a, required=True)
    wc.add_argument("--config")
    wc.add_argument("--synthetic", action="store_true")
    wc.add_argument("--table-facts", default="32768")
    wc.add_argument("--unseen", default="2048")
    rh = sub.add_parser("rehearse", help="the synthetic rehearsal (tiny sizes, test seeds) end to end")
    rh.add_argument("--run-dir", required=True)
    rh.add_argument("--repo")
    rh.add_argument("--measuring", action="store_true")
    rh.add_argument("--counting", action="store_true")
    rh.add_argument("--resume", action="store_true", help="the counting rehearsal's existing directory: completed stages are not run again, a PAUSED quiet stage is retried by itself")
    for a in ("--plan", "--rates-out", "--record-out", "--qualification"):
        rh.add_argument(a)
    rh.add_argument("--workers", default="6,7")
    qa = sub.add_parser("qualify", help="R2 through every validity check on the rehearsal and calibration draws")
    qa.add_argument("--sealed-dir", required=True)
    qa.add_argument("--run-dir", required=True)
    qa.add_argument("--calibration", required=True)
    w = sub.add_parser("work", help="a worker process (one task)")
    w.add_argument("kind", choices=WORKER_KINDS)
    for a in ("--stage", "--label", "--run-dir", "--plan", "--mode", "--done"):
        w.add_argument(a, required=True)
    for a in ("--freeze-commit", "--config", "--to", "--updates", "--draw", "--facts", "--repo"):
        w.add_argument(a)
    w.add_argument("--synthetic", action="store_true")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return worker_main(args)
        if args.command == "generate":
            return freezemod.cmd_generate(args)
        if args.command == "candidate-plan":
            return freezemod.cmd_candidate_plan(args)
        if args.command == "project":
            return freezemod.cmd_project(args)
        if args.command == "freeze":
            return freezemod.cmd_freeze(args)
        if args.command == "caps-proposal":
            print(json.dumps({"proposed_cap_hours": core.propose_cap_hours(args.charged_hours, args.projected_remaining_hours), "rule": "section 15: charged + 2 x projected remaining, rounded up to the hour; the caps sum to at most 60 by the construction of B; anything above is the human lead's own decision"}))
            return 0
        if args.command == "work-calibrate":
            from . import calibrate_engine

            return calibrate_engine.worker_main(args)
        if args.command == "calibrate":
            from . import calibrate_engine

            return calibrate_engine.cmd_calibrate(args)
        if args.command == "qualify":
            from . import rehearsal_real

            return rehearsal_real.cmd_qualify(args)
        if args.command == "rehearse":
            from . import rehearsal_real

            return rehearsal_real.cmd_rehearse(args)
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())

