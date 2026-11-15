# ruff: noqa: E501
"""P10S1 stages (ADR-0021 sections 8.1, 10, 11): ``generate``, ``calibrate``, ``gates``, ``rehearse``, ``timing`` (isolated CPU seconds per update), ``synthetic`` (analysis and report on
synthetic records of the whole registry), ``project`` (the projection, the headroom rule and the cuts), ``freeze`` (writes the frozen ``plan.json`` and ``stage_caps.json``), ``train``,
``evaluate``, ``simulate``, ``analyze``, ``report``, ``dry`` and ``registered`` (the driver the fixed launch scripts call).

Run from the repository root: ``uv run --locked python -m studies.p10s1.stages <command> ...``. Stages run through P9's job manager (``studies.p9.pool.run_stage``): immutable task ids,
per-worker RSS cap (3 GiB), aggregate cap (18 GiB), failed records kept, a failed cell stops the cells that depend on it, nothing is re-run with changed settings. Workers are
single-thread subprocesses (six).

One charged-time ledger (``core.Ledger``, the cap is ``resources.cap_hours`` of the config) carries calibration, rehearsal and every registered stage; a stage refuses to start when the
remainder of the cap is below its stage cap. Registered stages take their caps from the frozen table (``stage_caps.json``), one entry per configuration, and everything else from the
frozen plan (``plan.json``); the launch scripts pass the run directory and the freeze commit and nothing else.

Modes and seeds (``core.check_seed_set``). ``registered`` (needs ``--freeze-commit`` and a clean tree): ``p10s1-draw-1..5`` only; ``calibration``: ``p10s1-cal-1`` and ``-2`` only, refusing
any cell that is not a calibration cell; ``rehearsal``: ``p10s1-rehearsal`` only, writing nothing but the whitelisted records; the DRY stage and the unit tests use test seeds (921001+)
and a random synthetic backbone.

Not run by this module's author: the calibration, the rehearsal and every registered stage.
"""

import argparse
import dataclasses
import functools
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import torch

from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json
from studies.p9 import controls, pool
from studies.p9 import core as p9core
from studies.p9 import data as data_mod

from . import (
    analysis,
    budget,
    calibrate,
    core,
    evaluate,
    gates,
    report,
    synthetic,
    timing,
    traffic,
    train,
)
from . import frozen as fz

REGISTERED, CALIBRATION, REHEARSAL = "registered", "calibration", "rehearsal"
DRY_BANNER = "DRY: tiny synthetic sizes, random synthetic backbone, test seeds; not a measurement of anything"
DRY_UNIT = 8
DRY_FACTS = {2048: 128, 8192: 256, 16384: 384, 32768: 512, 65536: 640, 131072: 768}  # multiples of 128, in the registered order
DRY_SIZES = data_mod.DataSizes(main_trained=1024, unseen=64, lane_d_per_set=128)
DRY_G1_PERMUTATIONS = 200
SYNTHETIC_CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
PARENT = p9core.PRIMARY_PARENT
STAGE_GROUP = {"generate": "analyze", "gates": "train", "calibrate": "train", "rehearse": "train", "train": "train", "evaluate": "evaluate", "timing": "train", "simulate": "evaluate", "analyze": "analyze", "report": "analyze", "synthetic": "analyze"}
FREEZE_PLAN = core.FREEZE_DIR / "plan.json"
CAPS_FILE = str(core.FREEZE_DIR / "stage_caps.json")
REGISTERED_STAGES = ("gates", "train", "evaluate", "timing", "simulate", "analysis", "report")
GATE_NAMES = ("g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9")


class StageError(RuntimeError):
    """A stage cannot start for a reason other than a pool refusal."""


class CalibrationRefused(RuntimeError):
    """The calibration was asked to build or train something other than a calibration cell."""


class RegisteredRefused(RuntimeError):
    """A registered stage was asked to build or train a cell that is not in the frozen registry."""


def _utc() -> str:
    return datetime.now(UTC).isoformat()


# --- guards ---------------------------------------------------------------------------------------------------------------------------
def calibration_guard(cell: core.Cell, unit: int = core.U_P) -> None:
    """Section 10.1: the calibration runs its calibration cells on the calibration draws and nothing else; refused in code before anything is built."""
    if cell.kind != "CAL" or cell.draw not in core.CALIBRATION_DRAWS or cell.label not in {c.label for c in core.calibration_cells(True, unit)}:
        raise CalibrationRefused(f"the calibration trains only its calibration cells on calibration draws 1 and 2 (ADR-0021 section 10.1); refused: {cell.label}")


def registered_guard(cell: core.Cell, fro: fz.Frozen) -> None:
    """A registered training or evaluation runs the cells of the frozen registry only (no cell outside it, no lane L)."""
    allowed = {c.label for c in core.registered_cells(fro.plan, dense_rates=fro.dense_rates) if c.kind != "LN"}
    if cell.label not in allowed:
        raise RegisteredRefused(f"{cell.label} is not a cell of the frozen registry (plan {fro.plan.key()})")


def is_synthetic(args: argparse.Namespace) -> bool:
    return bool(args.dry or args.synthetic_backbone)


def unit_of(args: argparse.Namespace) -> int:
    return DRY_UNIT if args.dry else core.U_P


def experiments_root(args: argparse.Namespace) -> Path:
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def repo_of(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def ledger_root(args: argparse.Namespace) -> Path:
    return Path(args.ledger_root) if args.ledger_root else experiments_root(args)


def facts_for(args: argparse.Namespace, facts: int) -> int:
    return DRY_FACTS[facts] if args.dry else facts


def worker_cell(args: argparse.Namespace, label: str) -> core.Cell:
    """The cell of ``label`` as a worker builds it: the DRY profile shrinks the facts (labels and slots stay the registered ones)."""
    cell = core.parse_label(label)
    return dataclasses.replace(cell, facts=facts_for(args, cell.facts)) if args.dry else cell


# --- the plan of a command -------------------------------------------------------------------------------------------------------------
def load_plan_file(path: Path) -> dict[str, Any]:
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise pool.StageRefused("refused: the freeze plan is not an object")
    return plan


def frozen_of(args: argparse.Namespace) -> fz.Frozen:
    """The frozen inputs: from the freeze plan when given (registered stages; the DRY stage's own), else the default plan (with ``--overload-u-p`` and the seed-block draws of the command) and
    the cost table of ``--timing`` (or the placeholder table, which only fixes snapshot grids for the calibration and the rehearsal)."""
    if args.freeze_plan:
        return fz.Frozen.from_json(load_plan_file(Path(args.freeze_plan))["frozen"])
    plan = core.Plan(args.overload_u_p, tuple(int(d) for d in args.seed_block.split(",") if d), (), False, unit_of(args))
    return fz.Frozen.build(plan, cpu_table_of(args))


def cpu_table_of(args: argparse.Namespace) -> dict[tuple[str, int], float]:
    if not args.timing:
        return fz.default_cpu_table()
    rec = core.read_record(Path(args.timing), "timing")
    return {(k.split("|")[0], int(k.split("|")[1])): float(v) for k, v in rec["cpu_per_update"].items()}


def seeds_for(args: argparse.Namespace, draw: int | None = None) -> p9core.SeedSet:
    """The data seeds a command may use in its mode (``core.check_seed_set`` is applied again by every training job)."""
    k = args.draw if draw is None else draw
    if is_synthetic(args):
        if args.mode == REGISTERED:
            raise pool.StageRefused("refused: registered seeds with the DRY profile or a synthetic backbone")
        return core.test_seeds(0)
    if args.mode == REGISTERED:
        return core.registered_draw_seeds(k)
    if args.mode == CALIBRATION:
        return core.calibration_seeds(k)
    return core.rehearsal_seeds()


def corpus_bytes(args: argparse.Namespace) -> bytes:
    return SYNTHETIC_CORPUS if is_synthetic(args) else p9core.load_trained_corpus(experiments_root(args))


def table_facts(args: argparse.Namespace, plan: core.Plan) -> int:
    """Facts of the draw's table: the plan's (32,768, or 65,536 with the overload row); the calibration's 131,072; the DRY profile's 1,024."""
    if args.dry:
        return DRY_SIZES.main_trained
    return core.CALIBRATION_TABLE_FACTS if args.mode == CALIBRATION else plan.table_facts


@functools.cache
def _build_data(seeds: p9core.SeedSet, corpus: bytes, main_trained: int, unseen: int) -> data_mod.StudyData:
    return data_mod.build_study_data(seeds, corpus, sizes=data_mod.DataSizes(main_trained=main_trained, unseen=unseen, lane_d_per_set=core.LANE_D_STUB))


def study_data(args: argparse.Namespace, seeds: p9core.SeedSet, plan: core.Plan) -> data_mod.StudyData:
    core.check_seed_set(args.mode, seeds.name)
    study = _build_data(seeds, corpus_bytes(args), table_facts(args, plan), DRY_SIZES.unseen if args.dry else core.UNSEEN_FACTS)
    if args.mode == REGISTERED and study.pool != p9core.TEMPLATE_POOL:
        raise StageError("template pool differs from the registered pool (studies.p9.core.TEMPLATE_POOL)")
    return study


@functools.cache
def _synthetic_backbone() -> Any:
    return controls.synthetic_backbone(*PARENT)


def backbone_for(args: argparse.Namespace) -> Any:
    return _synthetic_backbone() if is_synthetic(args) else controls.load_backbone(PARENT, experiments_root(args))[0]


def manifest_dir(run_dir: Path, name: str) -> Path:
    return run_dir / "draws" / name


def verified_data(args: argparse.Namespace, seeds: p9core.SeedSet, plan: core.Plan, *, require_manifest: bool) -> data_mod.StudyData:
    """``study_data`` checked against the stream hashes of the draw's data manifest."""
    study = study_data(args, seeds, plan)
    path = manifest_dir(Path(args.run_dir), seeds.name) / "data_manifest.json"
    if path.is_file():
        if core.read_record(path, "data_manifest")["sha256s"] != study.sha256s():
            raise StageError(f"regenerated data differ from the hashes in {path}")
    elif require_manifest:
        raise StageError(f"no data manifest at {path}: run generate first")
    return study


def data_manifest_ok(run_dir: Path, name: str) -> bool:
    p = manifest_dir(run_dir, name) / "data_manifest.json"
    return p.is_file() and core.read_record(p, "data_manifest").get("g1_passed") is True


def require_draws(run_dir: Path, names: Sequence[str] = core.DRAW_NAMES) -> None:
    """A registered stage that reads data needs the five registered draws generated with a passed G1."""
    for name in names:
        if not data_manifest_ok(run_dir, name):
            raise pool.StageRefused(f"refused: {name} has no passed G1 record in {run_dir}")


def require_gates_passed(run_dir: Path) -> dict[str, Any]:
    """A registered training starts only when the ``gates`` record exists and G1, G2 and G4 to G9 all passed."""
    path = run_dir / "gates.json"
    if not path.is_file():
        raise pool.StageRefused(f"refused: no gates record at {path}: run the gates stage first")
    record = core.read_record(path, "gates")
    failed = [n.upper() for n in GATE_NAMES if record.get(f"{n}_passed") is not True]
    if failed:
        raise pool.StageRefused(f"refused: gate(s) {', '.join(failed)} did not pass; nothing is trained")
    return record


# --- git, preconditions ---------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/`` (code, launch scripts, freeze files), the P10S1 config, the
    ADR and every ``tests/test_p10s1_*`` equal their content at that commit, and ``frozen_input_check`` (src/arborlm, uv.lock, pyproject.toml, P8 digest) is ok. Returns the freeze
    identity (None for calibration and rehearsal)."""
    if mode != REGISTERED:
        return None
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise pool.StageRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise pool.StageRefused("refused: a registered stage requires --freeze-commit")
    ok = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise pool.StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise pool.StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems = [f"{p} at HEAD differs from the freeze commit" for p in ("studies", str(core.DEFAULT_CONFIG), core.SPEC) if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    for name in git(repo, "ls-tree", "--name-only", "HEAD", "tests/").stdout.decode().split():
        if name.startswith("tests/test_p10s1_") and git(repo, "rev-parse", f"{full}:{name}").stdout != git(repo, "rev-parse", f"HEAD:{name}").stdout:
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise pool.StageRefused("refused: " + "; ".join(problems))
    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise pool.StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


# --- the pool -------------------------------------------------------------------------------------------------------------------------------
def common_args(args: argparse.Namespace) -> list[str]:
    """Options every worker needs to rebuild the same draw and plan (never a scientific value)."""
    out = ["--run-dir", str(args.run_dir), "--mode", args.mode, "--draw", str(args.draw), "--experiments-root", str(experiments_root(args)), "--seed-block", args.seed_block]
    if args.dry:
        out.append("--dry")
    if args.synthetic_backbone:
        out.append("--synthetic-backbone")
    for flag, value in (("--calibration", args.calibration), ("--freeze-plan", args.freeze_plan), ("--timing", args.timing), ("--overload-u-p", args.overload_u_p), ("--updates", args.updates), ("--item", None)):
        if value is not None:
            out += [flag, str(value)]
    return out


def worker_argv(worker: str, *extra: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "studies.p10s1.stages", "work", worker, *extra)


def make_task(stage: str, label: str, argv: Sequence[str], run_dir: Path, identity: dict[str, str], result_path: Path, *, after: Sequence[str] = ()) -> pool.Task:
    if len(argv) < 5 or argv[1:3] != ("-m", "studies.p10s1.stages"):
        raise ValueError("worker argv must be '<python> -m studies.p10s1.stages work ...'")
    folder = run_dir / stage
    return pool.Task(
        task_id=pool.task_id(stage, label, cast(Any, identity)), stage=stage, label=label, argv=tuple(argv), depends_on=(), after=tuple(after), group=STAGE_GROUP[stage.split("-")[0].rstrip("0123456789")],
        result_path=result_path, failed_path=folder / f"{label}.failed.json", log_path=folder / f"{label}.log",
    )  # fmt: skip


def run_stage_tasks(stage: str, args: argparse.Namespace, tasks: Sequence[pool.Task], run_dir: Path, *, cap: float, completed_ids: Sequence[str] = (), workers: int | None = None, skip_preconditions: bool = False) -> dict[str, Any]:
    """Ledger check, preconditions, the pool, the ledger charge, and the stage manifest (written once, with the environment)."""
    target = run_dir / stage / "manifest.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} already exists; a stage is run once and never overwritten")
    ledger = core.Ledger.from_config(ledger_root(args), repo_of(args) / core.DEFAULT_CONFIG if args.repo else None)
    ledger.require_room(stage, cap)
    if not skip_preconditions:
        check_preconditions(args.mode, repo_of(args), args.freeze_commit)
    count = workers or args.workers
    if args.mode == REGISTERED and not 1 <= count <= core.WORKERS:
        raise pool.StageRefused(f"refused: {count} workers; P10S1 uses at most {core.WORKERS}")
    identity = core.code_identity()
    started = _utc()
    result = pool.run_stage(
        tasks, workers={"train": count, "evaluate": count, "analyze": 1}, stage_cap_seconds=cap, rss_worker_bytes=args.rss_worker_bytes, rss_aggregate_bytes=args.rss_aggregate_bytes,
        env={"PYTHONPATH": str(core.repo_root())}, completed_ids=list(completed_ids), total_remaining_seconds=ledger.remaining(),
    )  # fmt: skip
    ledger.charge(stage, run_dir.name, result.wall_seconds)
    manifest = dict(pool.build_manifest(stage, run_dir, args.mode, cast(Any, identity), tasks, result, started_utc=started, finished_utc=_utc(), workers=count, caps=pool.StageCaps(cap, args.rss_worker_bytes, args.rss_aggregate_bytes).as_dict()))
    manifest["study"] = core.STUDY
    manifest["cap_seconds"] = ledger.cap_seconds
    manifest["environment"] = core.environment()
    core.write_record(target, manifest)
    print(json.dumps({"stage": stage, "status": manifest["status"], "tasks": len(tasks), "manifest": str(target), "charged_seconds": round(result.wall_seconds, 1)}))
    return manifest


def stage_cap(args: argparse.Namespace, default: float | None = None) -> float:
    if args.stage_cap_seconds is not None:
        return float(args.stage_cap_seconds)
    if args.dry:
        return 3600.0
    if default is not None:
        return default
    raise pool.StageRefused("refused: --stage-cap-seconds is required (caps are fixed after the rehearsal)")


def labels_of_args(args: argparse.Namespace) -> list[str]:
    if not args.labels:
        raise StageError("--labels is required")
    return [s for s in args.labels.split(",") if s]


def cell_task_label(args: argparse.Namespace, c: core.Cell) -> str:
    """One task per cell; the DRY stage groups the cells of a draw and slot count into one task to keep its process count small."""
    return f"g-d{c.draw}-n{c.slots}-k{c.kind}" if args.dry else c.label


def cell_tasks(name: str, worker: str, args: argparse.Namespace, cells: Sequence[core.Cell], run_dir: Path, result_for: Any, *, previous: str | None = None, extra: Sequence[str] = ()) -> tuple[list[pool.Task], list[str]]:
    """Tasks of a cell stage; ``previous`` names the earlier stage whose manifest supplies the ``after`` dependency (a cell without a completed upstream task is not run)."""
    identity = core.code_identity()
    prior: dict[str, str] = {}
    completed: list[str] = []
    if previous is not None:
        path = run_dir / previous / "manifest.json"
        if not path.is_file():
            raise StageError(f"no {path}: run {previous} first")
        upstream = core.read_record(path, "stage_manifest")
        prior = {t["label"]: t["task_id"] for t in upstream["tasks"]}
        completed = [t["task_id"] for t in upstream["tasks"] if t["status"] == "completed"]
        cells = [c for c in cells if cell_task_label(args, c) in prior]
    groups: dict[str, list[core.Cell]] = {}
    for c in cells:
        groups.setdefault(cell_task_label(args, c), []).append(c)
    tasks = [
        make_task(name, label, worker_argv(worker, "--labels", ",".join(m.label for m in members), *common_args(args), *extra), run_dir, identity, result_for(members[-1]), after=[prior[label]] if label in prior else [])
        for label, members in groups.items()
    ]
    return tasks, completed


# --- job construction ------------------------------------------------------------------------------------------------------------------------
def build_job(args: argparse.Namespace, cell: core.Cell, study: data_mod.StudyData, out_dir: Path, fro: fz.Frozen, *, mode: str | None = None, snapshots: Sequence[int] | None = None, max_updates: int | None = None, updates: int | None = None) -> train.TrainJob:
    """The training job of a cell (``cell.facts`` is the facts the data uses: shrunk in the DRY profile; the snapshots are those of the registered cell, whose facts key the
    matched-compute snapshots)."""
    seeds = study.seeds
    return train.TrainJob(
        cell=cell, data=study, stream=train.training_stream_for(study, cell.facts), backbone=backbone_for(args), out_dir=out_dir, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), mode=mode or args.mode,
        updates=cell.run_updates if updates is None else updates, snapshots=tuple(snapshots) if snapshots is not None else fro.snapshots(core.parse_label(cell.label)), optimizer_marks=(cell.run_updates,), max_updates=max_updates,
        fact_lut=train.fact_lut_for(study, cell.facts) if cell.arm == "R2" else None, extra={"freeze_plan_sha256": file_sha256(Path(args.freeze_plan))} if args.freeze_plan else {},
    )  # fmt: skip


def configure() -> None:
    train.configure()


def seeds_of_cell(args: argparse.Namespace, cell: core.Cell) -> p9core.SeedSet:
    return seeds_for(args, cell.draw)


# --- workers ---------------------------------------------------------------------------------------------------------------------------------
def work_generate(args: argparse.Namespace) -> int:
    """One draw: generate, hash and G1-check it (not an observation of a seed by a model). G1 is P9's generator check plus S1's own (``gates.g1_s1``); the calibration draws are
    hashed and not G1-checked (the calibration is not a registered result)."""
    seeds = seeds_for(args)
    folder = manifest_dir(Path(args.run_dir), seeds.name)
    target = folder / "data_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    fro = frozen_of(args)
    study = study_data(args, seeds, fro.plan)
    g1: dict[str, Any] | None = None
    g1_extra: dict[str, Any] | None = None
    if args.mode != CALIBRATION or args.dry:
        g1 = dict(data_mod.run_g1(study, permutations=DRY_G1_PERMUTATIONS if args.dry else None, train_epochs=None))
        g1_extra = gates.g1_s1(study, fro.plan, [facts_for(args, f) for f in sorted({f for f, _ in core.grid_cells(fro.plan)})] if args.dry else None)
    folder.mkdir(parents=True, exist_ok=True)
    passed: bool | None = None if g1 is None else bool(g1["passed"]) and bool(g1_extra and g1_extra["passed"])
    if g1 is not None:
        write_json(folder / "g1.json", {"p9_g1": g1, "s1_g1": g1_extra})
    core.write_record(target, {
        **core.envelope("data_manifest"), "seed_set": seeds.name, "seeds": dataclasses.asdict(seeds), "dry": bool(args.dry), "mode": args.mode, "main_trained": table_facts(args, fro.plan), "sha256s": study.sha256s(),
        "template_pool": list(study.pool), "g1_passed": passed, "g1_failed_checks": [] if g1 is None else [c["name"] for c in g1["checks"] if not c["passed"]], "g1_file": None if g1 is None else "g1.json",
        "identity": core.code_identity(), "environment": core.environment(),
    })  # fmt: skip
    print(json.dumps({"seed_set": seeds.name, "g1_passed": passed}))
    return 0 if passed in (True, None) else 1


def g2_for(args: argparse.Namespace, run_dir: Path, plan: core.Plan, backbone: Any) -> tuple[dict[str, Any], dict[str, bool | None]]:
    """G2 over every draw of the mode (registered: the five registered draws, 40 tests) and G1 as read from the draws' records."""
    counts = [facts_for(args, f) for f in sorted({f for f, _ in core.grid_cells(plan)})]
    by_draw: dict[str, Any] = {}
    g1: dict[str, bool | None] = {}
    if args.mode == REGISTERED and not is_synthetic(args):
        require_draws(run_dir)
        for r in range(1, core.REPLICATES + 1):
            seeds = core.registered_draw_seeds(r)
            study = verified_data(args, seeds, plan, require_manifest=True)
            by_draw[str(r)] = gates.no_memory_counts(backbone, study, counts)
            g1[str(r)] = True
    else:
        seeds = seeds_for(args)
        study = verified_data(args, seeds, plan, require_manifest=False)
        by_draw[str(args.draw)] = gates.no_memory_counts(backbone, study, counts)
        p = manifest_dir(run_dir, seeds.name) / "data_manifest.json"
        g1[str(args.draw)] = core.read_record(p, "data_manifest").get("g1_passed") if p.is_file() else None
    return gates.g2_report(by_draw), g1


def work_gates(args: argparse.Namespace) -> int:
    """G1 (read from the draws' records), G2 (no-memory baseline at chance, every registered draw), G4 to G9 at real size on one draw (registered: draw 1; rehearsal: the rehearsal draw).
    A failed G1 or G2 on any draw is a failed gate; a harness error is reported separately and fails nothing."""
    run_dir = Path(args.run_dir)
    target = run_dir / "gates.json"
    if target.exists():
        raise FileExistsError(target)
    started = time.monotonic()
    fro = frozen_of(args)
    seeds = seeds_for(args, 1 if args.mode == REGISTERED else None)
    study = verified_data(args, seeds, fro.plan, require_manifest=args.mode == REGISTERED and not args.dry)
    backbone = backbone_for(args)
    rows = evaluate_rows(args)
    g2, g1_by_draw = g2_for(args, run_dir, fro.plan, backbone)
    g1_all = all(v is True for v in g1_by_draw.values()) if g1_by_draw else False
    init = seeds.facts if is_synthetic(args) else (core.INIT_SEEDS[0] if args.mode == REGISTERED else core.REHEARSAL_INIT_SEED)
    cfgs = [(a, facts_for(args, f), n) for a in core.ARMS for f, n in core.arm_cells(core.Plan(fro.plan.overload_u_p, unit=fro.plan.unit), a)]
    result = gates.run_gates(study, backbone, mode=args.mode, plan=fro.plan, out_dir=run_dir / "gate_runs", init_seed=init, rows=rows, restore_split=4 if args.dry else args.restore_split, configurations=cfgs, small_facts=facts_for(args, 2048))
    passed = {n: bool(result.get(f"{n}_passed")) for n in ("g4", "g5", "g6", "g7", "g8", "g9")}
    record = core.jsonable({
        **core.envelope("gates"), "seed_set": seeds.name, "g1_passed": g1_all, "g1_by_draw": g1_by_draw, "g2": g2, "g2_passed": bool(g2["passed"]), **{f"{n}_passed": v for n, v in passed.items()},
        "g4_defects": result["g4_defects"], "harness_errors": result["harness_errors"], "configurations_checked": result["configurations_checked"], "checks": result["checks"], "dry": bool(args.dry), "mode": args.mode,
        "wall_seconds": time.monotonic() - started, "environment": core.environment(), "identity": core.code_identity(),
    })  # fmt: skip
    core.write_record(target, record)
    ok = all(passed.values()) and g1_all and bool(g2["passed"])
    print(json.dumps({**passed, "g1": g1_all, "g2": bool(g2["passed"]), "harness_errors": len(result["harness_errors"]), "defects": len(result["g4_defects"])}))
    return 0 if ok and not result["harness_errors"] else 1


def evaluate_rows(args: argparse.Namespace) -> Any:
    return evaluate_rows_cached(corpus_bytes(args))


@functools.cache
def evaluate_rows_cached(corpus: bytes) -> Any:
    raw = torch.frombuffer(bytearray(corpus), dtype=torch.uint8).to(torch.int64)
    return raw.reshape(-1, p9core.CORPUS_ROW_BYTES)


def work_train(args: argparse.Namespace) -> int:
    failed = 0
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
        require_draws(run_dir)
    for label in labels_of_args(args):
        cell = worker_cell(args, label)
        registered_guard(core.parse_label(label), fro)
        seeds = seeds_of_cell(args, cell)
        study = verified_data(args, seeds, fro.plan, require_manifest=not args.dry and args.mode == REGISTERED)
        job = build_job(args, cell, study, core.cell_dir(run_dir, label), fro)
        try:
            record = train.train_cell(job)
            print(json.dumps({"label": label, "status": record["status"]}))
        except Exception as exc:  # the failed record was written by run_job; the others of a group go on
            failed += 1
            print(json.dumps({"label": label, "status": "failed", "reason": type(exc).__name__}))
    return 0 if not failed else 1


def work_evaluate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    rows = evaluate_rows(args)
    failed = 0
    for label in labels_of_args(args):
        cell = worker_cell(args, label)
        registered_guard(core.parse_label(label), fro)
        seeds = seeds_of_cell(args, cell)
        study = verified_data(args, seeds, fro.plan, require_manifest=not args.dry and args.mode == REGISTERED)
        try:
            evaluate.evaluate_cell(cell, run_dir, study, backbone_for(args), readouts=list(fro.snapshots(core.parse_label(label))), deep_at=cell.u_p, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), rows=rows, require_train_record=True)
            print(json.dumps({"label": label, "evaluated": True}))
        except Exception as exc:
            failed += 1
            print(json.dumps({"label": label, "evaluated": False, "reason": type(exc).__name__}))
    return 0 if not failed else 1


def work_baseline(args: argparse.Namespace) -> int:
    """DICT, KNN-W, KNN-W-IVF and the no-memory baseline for one (draw, facts): evaluation only, nothing trained."""
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    draw, facts_s = args.item.split(",")
    draw_i, facts = int(draw), int(facts_s)
    seeds = seeds_for(args, draw_i)
    study = verified_data(args, seeds, fro.plan, require_manifest=not args.dry and args.mode == REGISTERED)
    f = facts_for(args, facts)
    stream = train.training_stream_for(study, f)
    rec = evaluate.baseline_record(study, backbone_for(args), f, draw_i, evaluate_first_epoch(stream), seeds)
    rec["facts_registered"] = facts
    core.write_record(run_dir / "baselines" / f"d{draw_i}_f{facts}.json", core.jsonable(rec))
    print(json.dumps({"baseline": f"d{draw_i}_f{facts}"}))
    return 0


def evaluate_first_epoch(stream: Any) -> list[tuple[Any, Any]]:
    from .index import first_epoch

    return first_epoch(stream)


def work_calibrate_cell(args: argparse.Namespace) -> int:
    """Train one calibration cell for its run length and evaluate its snapshots (counts only). Refuses any other cell."""
    failed = 0
    unit = unit_of(args)
    fro = frozen_of(args)
    for label in labels_of_args(args):
        try:
            registered = core.parse_label(label)
        except ValueError as exc:
            raise CalibrationRefused(f"not a calibration cell: {label!r}") from exc
        calibration_guard(registered, unit)
        cell = worker_cell(args, label)
        run_dir = Path(args.run_dir)
        seeds = seeds_of_cell(args, cell)
        study = study_data(args, seeds, fro.plan)
        out_dir = core.cell_dir(run_dir, label)
        snaps = calibrate.calibration_snapshots(registered)
        job = build_job(args, cell, study, out_dir, fro, mode=CALIBRATION, snapshots=snaps)
        try:
            train.train_cell(job)
            evaluate.evaluate_cell(cell, run_dir, study, backbone_for(args), readouts=list(snaps), deep_at=None, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), rows=None, require_train_record=True, with_ivf=False)
            print(json.dumps({"label": label, "status": "completed"}))
        except Exception as exc:
            failed += 1
            print(json.dumps({"label": label, "status": "failed", "reason": type(exc).__name__}))
    return 0 if not failed else 1


def work_rehearse_cell(args: argparse.Namespace) -> int:
    """One configuration of the matrix at real size for ``--updates`` (64) updates in rehearsal mode (whitelisted record only), then the time of one full evaluation (all panels and
    ablations, deep measures, robustness, the index build). Nothing but time, memory, shapes, counts and identity is written; no loss or accuracy is read out."""
    arm, facts_s, slots_s = args.item.split(",")
    facts, slots = int(facts_s), int(slots_s)
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    seeds = seeds_for(args)
    study = study_data(args, seeds, fro.plan)
    f = facts_for(args, facts)
    cell = core.make_cell("P", arm, f, slots, 1, core.REHEARSAL_INIT_SEED, u_p=unit_of(args))
    item = budget.item_label((arm, facts, slots))
    out_dir = run_dir / "rehearsal" / item
    updates = args.updates if args.updates is not None else core.REHEARSAL_UPDATES
    job = build_job(args, cell, study, out_dir, fro, mode=REHEARSAL, snapshots=(), max_updates=updates)
    run = train.run_job(job)
    wall0, cpu0 = time.monotonic(), time.process_time()
    rows = evaluate_rows(args)
    evaluate.evaluate_readout(cell, run.model, study, updates, frozen_backbone=job.backbone, rows=rows, deep=True, robustness=True, with_ivf=True)  # discarded
    wall, cpu = time.monotonic() - wall0, time.process_time() - cpu0
    train.write_rehearsal_record(out_dir / "rehearsal_evaluate.json", {
        **core.envelope("rehearsal"), "label": cell.label, "mode": "rehearsal", "stage": "rehearse-evaluate", "arm": arm, "slots": slots, "facts": facts, "identity": core.code_identity(), "updates": 0, "wall_seconds": wall,
        "evaluation_wall_seconds": wall, "evaluation_cpu_seconds": cpu, "evaluation_snapshots": 1, "peak_rss_bytes": train.peak_rss(), "seed_set": study.seeds.name, "item": item,
    })  # fmt: skip
    print(json.dumps({"item": item, "evaluation_seconds": round(wall, 2)}))
    return 0


def work_rehearse_baseline(args: argparse.Namespace) -> int:
    """The time of the baselines (DICT, KNN-W, KNN-W-IVF, no-memory) for one fact count on the rehearsal draw: evaluation only."""
    facts = int(args.item)
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    seeds = seeds_for(args)
    study = study_data(args, seeds, fro.plan)
    f = facts_for(args, facts)
    started, cpu0 = time.monotonic(), time.process_time()
    evaluate.baseline_record(study, backbone_for(args), f, 1, evaluate_first_epoch(train.training_stream_for(study, f)), seeds)  # discarded
    wall = time.monotonic() - started
    item = budget.baseline_label(facts)
    train.write_rehearsal_record(run_dir / "rehearsal" / item / "rehearsal_evaluate.json", {
        **core.envelope("rehearsal"), "label": item, "mode": "rehearsal", "stage": "rehearse-baseline", "facts": facts, "identity": core.code_identity(), "updates": 0, "wall_seconds": wall,
        "evaluation_wall_seconds": wall, "evaluation_cpu_seconds": time.process_time() - cpu0, "evaluation_snapshots": 1, "peak_rss_bytes": train.peak_rss(), "seed_set": study.seeds.name, "item": item,
    })  # fmt: skip
    print(json.dumps({"item": item, "seconds": round(wall, 2)}))
    return 0


def dry_quiet() -> dict[str, Any]:
    """The DRY stage does not wait for a quiet machine (its numbers measure nothing); the record says so."""
    return {"quiet": True, "attempts": 0, "load_averages": [float(os.getloadavg()[0])], "dry_skip": True}


def work_cpu_timing(args: argparse.Namespace) -> int:
    """The isolated timing part of the rehearsal (section 10.2): process CPU seconds per update for every arm and slot count, the median of three runs of 256 updates after 32 warm-up
    updates, in one process with nothing else running. Refused if the load average exceeds 1.0 (retried up to three times); if never quiet the status is NOT MEASURED."""
    run_dir = Path(args.run_dir)
    target = run_dir / "timing.json"
    if target.exists():
        raise FileExistsError(target)
    quiet = dry_quiet() if args.dry else timing.wait_for_quiet()
    fro = frozen_of(args)
    seeds = seeds_for(args)
    study = study_data(args, seeds, fro.plan)
    cpu: dict[str, float] = {}
    runs: dict[str, Any] = {}
    status = "MEASURED" if quiet["quiet"] else timing.NOT_MEASURED
    warm, n, reps = (2, 4, core.TIMING_REPEATS) if args.dry else (core.TIMING_WARMUP_UPDATES, core.TIMING_UPDATES, core.TIMING_REPEATS)
    if quiet["quiet"]:
        for arm in core.ARMS:
            for facts, slots in sorted(c for c in core.arm_cells(core.Plan(unit=fro.plan.unit), arm) if c in core.DIAGONAL):
                f = facts_for(args, facts)
                cell = core.make_cell("P", arm, f, slots, 1, core.REHEARSAL_INIT_SEED, u_p=unit_of(args), run_updates=10**6)
                job = build_job(args, cell, study, run_dir / "timing_runs" / f"{arm}-{slots}", fro, mode=REHEARSAL, snapshots=())
                r = timing.cpu_seconds_per_update(job, warmup=warm, updates=n, repeats=reps)
                cpu[f"{arm}|{slots}"] = r["cpu_seconds_per_update"]
                runs[f"{arm}|{slots}"] = r
    core.write_record(target, core.jsonable({**core.envelope("timing"), "status": status, "cpu_per_update": cpu, "runs": runs, "quiet": quiet, "load_average_max": core.LOAD_AVERAGE_MAX, "dry": bool(args.dry), "environment": core.environment(), "identity": core.code_identity(), "seed_set": study.seeds.name}))
    print(json.dumps({"status": status, "configurations": len(cpu)}))
    return 0 if status == "MEASURED" else 1


def work_throughput(args: argparse.Namespace) -> int:
    """Read-path queries per second at batch 1 and 128 for F-OQ, F-OQ-IVF, T-OQ, H8 and D-OQ at each slot count on replicate-1 snapshots (U_P), five repeats, after all training and
    evaluation; refused if the load average exceeds 1.0 at start (retried up to three times); if never quiet THROUGHPUT NOT MEASURED (S1 stays complete)."""
    run_dir = Path(args.run_dir)
    target = run_dir / "throughput.json"
    if target.exists():
        raise FileExistsError(target)
    quiet = dry_quiet() if args.dry else timing.wait_for_quiet()
    fro = frozen_of(args)
    out: dict[str, Any] = {}
    status = "MEASURED" if quiet["quiet"] else timing.THROUGHPUT_NOT_MEASURED
    if quiet["quiet"]:
        seeds = seeds_for(args, 1)
        study = study_data(args, seeds, fro.plan)
        for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8", "D-OQ"):
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            for facts, slots in core.DIAGONAL:
                registered = next(c for c in core.registered_cells(fro.plan, dense_rates=fro.dense_rates) if c.kind == "P" and c.arm == base and c.draw == 1 and (c.facts, c.slots) == (facts, slots))
                cell = dataclasses.replace(registered, facts=facts_for(args, facts)) if args.dry else registered
                job = build_job(args, cell, study, core.cell_dir(run_dir, registered.label), fro)
                model = train.job_model(job, seed_rng=False)
                train.load_model_state(core.cell_dir(run_dir, registered.label) / "snapshots" / core.snapshot_stem(registered.u_p), model)
                out[f"{arm}|{slots}"] = timing.throughput_record(model, study, cell.facts, seeds, arm)
    core.write_record(target, core.jsonable({**core.envelope("throughput"), "status": status, "results": out, "quiet": quiet, "scope": "read path only, RAM, CPU, one process: not storage I/O, not latency of a language model", "dry": bool(args.dry), "environment": core.environment()}))
    print(json.dumps({"status": status, "configurations": len(out)}))
    return 0


def work_simulate(args: argparse.Namespace) -> int:
    """Estimated storage traffic (section 7.5) of replicate-1 memory cells at their U_P snapshot: simulation and arithmetic, no device."""
    run_dir = Path(args.run_dir)
    fro = frozen_of(args)
    failed = 0
    for label in labels_of_args(args):
        cell = worker_cell(args, label)
        registered = core.parse_label(label)
        registered_guard(registered, fro)
        seeds = seeds_of_cell(args, cell)
        study = verified_data(args, seeds, fro.plan, require_manifest=not args.dry and args.mode == REGISTERED)
        try:
            job = build_job(args, cell, study, core.cell_dir(run_dir, label), fro)
            model = train.job_model(job, seed_rng=False)
            train.load_model_state(core.cell_dir(run_dir, label) / "snapshots" / core.snapshot_stem(registered.u_p), model)
            rec = traffic.traffic_record(model, study, cell.facts, label, registered.u_p, seeds)
            core.write_record(run_dir / "simulation" / f"{label}.json", core.jsonable(rec))
            print(json.dumps({"label": label, "simulated": True}))
        except Exception as exc:
            failed += 1
            print(json.dumps({"label": label, "simulated": False, "reason": type(exc).__name__}))
    return 0 if not failed else 1


def aggregate_side_records(run_dir: Path, timing_path: Path | None = None) -> dict[str, Any]:
    """Timing (the isolated CPU table of the rehearsal, which the freeze binds by hash: ``timing_path``), throughput and the simulation records, as the analysis prints them."""
    out: dict[str, Any] = {"timing": None, "throughput": None, "simulation": None}
    for name in ("timing", "throughput"):
        p = run_dir / f"{name}.json"
        out[name] = read_json(p) if p.is_file() else None
    if out["timing"] is None and timing_path is not None and timing_path.is_file():
        out["timing"] = read_json(timing_path)
    sims = {p.stem: read_json(p) for p in sorted((run_dir / "simulation").glob("*.json"))} if (run_dir / "simulation").is_dir() else {}
    out["simulation"] = sims or None
    return out


def work_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "analysis.json"
    if target.exists():
        raise FileExistsError(target)
    fro = frozen_of(args)
    manifests = [read_json(p) for p in sorted(run_dir.glob("*/manifest.json"))]
    failed = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"] if t["status"] != "completed" and m["stage"] in ("train", "evaluate"))
    gates_path = run_dir / "gates.json"
    gates_rec = core.read_record(gates_path, "gates") if gates_path.is_file() else None
    study = analysis.load_study(run_dir, fro)
    plan_rec = read_json(Path(args.freeze_plan)) if args.freeze_plan else None
    side = aggregate_side_records(run_dir, Path(plan_rec["timing"]["path"]) if plan_rec else None)
    expected = plan_rec.get("identity") if plan_rec else None
    result = analysis.analyze_study(study, fro, gates=gates_rec, failed_tasks=failed, expected_identity=expected, timing=side["timing"], throughput=side["throughput"], simulation=side["simulation"])
    core.write_record(target, core.jsonable({**core.envelope("analysis"), "dry": bool(args.dry), "result": result, "freeze_plan_sha256": file_sha256(Path(args.freeze_plan)) if args.freeze_plan else None, "identity": core.code_identity(), "environment": core.environment()}))
    print(json.dumps({"status": result["assessment"]["status"], "capacity": result["outcome"]["capacity"]["label"], "efficiency": result["outcome"]["efficiency"]["label"]}))
    return 0


def work_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise FileExistsError(out / "results.json")
    paths = report.write_report(run_dir, out, banner=DRY_BANNER if args.dry else None)
    print(json.dumps({"written": [p.name for p in paths]}))
    return 0


def work_synthetic(args: argparse.Namespace) -> int:
    """Analysis and report exercised on synthetic records of the full registry (section 10.2): missing, failed and non-finite cells, a failed gate, and the default scenario; writes the
    time of one analysis and one report (they bound the caps of those stages) and what each scenario produced. Nothing of a model or a seed is read."""
    run_dir = Path(args.run_dir)
    target = run_dir / "synthetic.json"
    if target.exists():
        raise FileExistsError(target)
    fro = frozen_of(args)
    first_cell = core.registered_cells(fro.plan, dense_rates=fro.dense_rates)[0].label
    scenarios = {"default": synthetic.Scenario(), "missing cell": synthetic.Scenario(missing={first_cell}), "failed cell": synthetic.Scenario(fail={first_cell}), "non-finite cell": synthetic.Scenario(nonfinite={first_cell}), "failed gate": synthetic.Scenario(gates_ok=False)}
    results: dict[str, Any] = {}
    analyze_seconds = report_seconds = 0.0
    with tempfile.TemporaryDirectory(prefix="p10s1-synthetic-") as tmp:
        for name, scn in scenarios.items():
            d = Path(tmp) / name.replace(" ", "_")
            synthetic.write_run(d, fro, scn)
            t0 = time.monotonic()
            study = analysis.load_study(d, fro)
            res = analysis.analyze_study(study, fro, gates=read_json(d / "gates.json"))
            analyze_seconds = max(analyze_seconds, time.monotonic() - t0)
            core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": res}))
            t1 = time.monotonic()
            report.write_report(d, d / "results", banner="synthetic")
            report_seconds = max(report_seconds, time.monotonic() - t1)
            results[name] = {"status": res["assessment"]["status"], "capacity": res["outcome"]["capacity"]["label"], "efficiency": res["outcome"]["efficiency"]["label"]}
    core.write_record(target, {**core.envelope("rehearsal"), "synthetic": True, "analysis_wall_seconds": analyze_seconds, "report_wall_seconds": report_seconds, "scenarios": results, "note": "synthetic records; not a measurement of a model or a seed"})
    print(json.dumps({"analysis_seconds": round(analyze_seconds, 2), "report_seconds": round(report_seconds, 2), "scenarios": results}))
    return 0


WORKERS: dict[str, Any] = {
    "generate": work_generate, "gates": work_gates, "train": work_train, "evaluate": work_evaluate, "baseline": work_baseline, "analyze": work_analyze, "report": work_report, "simulate": work_simulate,
    "calibrate-cell": work_calibrate_cell, "rehearse-cell": work_rehearse_cell, "rehearse-baseline": work_rehearse_baseline, "cpu-timing": work_cpu_timing, "throughput": work_throughput, "synthetic": work_synthetic,
}  # fmt: skip


# --- commands --------------------------------------------------------------------------------------------------------------------------------
def new_run_dir(args: argparse.Namespace, stage: str) -> Path:
    run_dir = Path(args.run_dir) if args.run_dir else experiments_root(args) / core.run_name(stage)
    args.run_dir = str(run_dir)
    return run_dir


def single(stage: str, worker: str, args: argparse.Namespace, run_dir: Path, result: Path, extra: Sequence[str] = (), *, skip_preconditions: bool = False, cap: float | None = None) -> dict[str, Any]:
    task = make_task(stage, stage, worker_argv(worker, *common_args(args), *extra), run_dir, core.code_identity(), result)
    return run_stage_tasks(stage, args, [task], run_dir, cap=stage_cap(args, cap), workers=1, skip_preconditions=skip_preconditions)


def cmd_generate(args: argparse.Namespace) -> int:
    if args.mode == REGISTERED and not args.i_understand_freeze_time:
        raise pool.StageRefused("refused: registered-seed generation is used at freeze time; add --i-understand-freeze-time")
    run_dir = new_run_dir(args, "generate")
    seeds = seeds_for(args)
    if (manifest_dir(run_dir, seeds.name) / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {seeds.name} is already generated in {run_dir}")
    manifest = single(f"generate-{seeds.name}", "generate", args, run_dir, manifest_dir(run_dir, seeds.name) / "data_manifest.json", skip_preconditions=True)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("gates", "gates", args, run_dir, run_dir / "gates.json", ["--restore-split", str(args.restore_split)])
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_calibrate(args: argparse.Namespace) -> int:
    args.mode = CALIBRATION
    run_dir = new_run_dir(args, "calibrate")
    unit = unit_of(args)
    cells = core.calibration_cells(args.with_overload, unit)
    for c in cells:
        calibration_guard(c, unit)
    tasks, _ = cell_tasks("calibrate", "calibrate-cell", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "train.json")
    manifest = run_stage_tasks("calibrate", args, tasks, run_dir, cap=stage_cap(args))
    record = calibrate.finalize(run_dir, include_overload=args.with_overload, unit=unit)
    path = run_dir / "calibration.json"
    if path.exists():
        raise FileExistsError(path)
    core.write_record(path, record)
    print(json.dumps({"calibration": str(path), "returns_to_lead": record["returns_to_lead"]}))
    return 0 if manifest["status"] == "COMPLETE" and not record["returns_to_lead"] else 1


def cmd_rehearse(args: argparse.Namespace) -> int:
    if not is_synthetic(args) and not args.calibration:
        raise pool.StageRefused("refused: the rehearsal is bound to the calibration record: give --calibration (its sha256 is bound into the projection)")
    args.mode = REHEARSAL
    run_dir = new_run_dir(args, "rehearse")
    fro = frozen_of(args)
    identity = core.code_identity()
    tasks = [make_task("rehearse", budget.item_label(i), worker_argv("rehearse-cell", *common_args(args), "--item", ",".join(map(str, i))), run_dir, identity, run_dir / "rehearsal" / budget.item_label(i) / "rehearsal_evaluate.json") for i in budget.rehearsal_items(fro.plan)]
    for facts in sorted({f for f, _ in core.grid_cells(fro.plan)}):
        tasks.append(make_task("rehearse", budget.baseline_label(facts), worker_argv("rehearse-baseline", *common_args(args), "--item", str(facts)), run_dir, identity, run_dir / "rehearsal" / budget.baseline_label(facts) / "rehearsal_evaluate.json"))
    manifest = run_stage_tasks("rehearse", args, tasks, run_dir, cap=stage_cap(args))
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_timing(args: argparse.Namespace) -> int:
    """Rehearsal (default): the isolated CPU-seconds-per-update part; registered or ``--throughput``: the read-path throughput after all training and evaluation."""
    run_dir = Path(args.run_dir) if args.run_dir else new_run_dir(args, "timing")
    worker, result = ("throughput", run_dir / "throughput.json") if args.throughput else ("cpu-timing", run_dir / "timing.json")
    manifest = single("timing", worker, args, run_dir, result)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_synthetic(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir) if args.run_dir else new_run_dir(args, "synthetic")
    manifest = single("synthetic", "synthetic", args, run_dir, run_dir / "synthetic.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def registered_cell_list(fro: fz.Frozen) -> list[core.Cell]:
    cells = [c for c in core.registered_cells(fro.plan, dense_rates=fro.dense_rates) if c.kind != "LN"]
    cost = fro.cost

    def estimate(c: core.Cell) -> float:
        return c.run_updates * fz.costs_of(cost, c.arm, c.slots)["cpu"]

    return sorted(cells, key=lambda c: (-estimate(c), c.label))


def run_train(args: argparse.Namespace, fro: fz.Frozen, cap: float | None) -> int:
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
        require_draws(run_dir)
    cells = registered_cell_list(fro)
    if args.only:
        cells = [c for c in cells if c.label in set(args.only)]
    tasks, _ = cell_tasks("train", "train", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "train.json")
    m = run_stage_tasks("train", args, tasks, run_dir, cap=stage_cap(args, cap))
    return 0 if m["status"] == "COMPLETE" else 1


def run_evaluate(args: argparse.Namespace, fro: fz.Frozen, cap: float | None) -> int:
    run_dir = Path(args.run_dir)
    cells = registered_cell_list(fro)
    if args.only:
        cells = [c for c in cells if c.label in set(args.only)]
    tasks, completed = cell_tasks("evaluate", "evaluate", args, cells, run_dir, lambda c: core.eval_path(run_dir, c.label, fro.snapshots(c)[-1]), previous="train")
    identity = core.code_identity()
    for r in range(1, core.REPLICATES + 1):
        for facts in sorted({f for f, _ in core.grid_cells(fro.plan)}):
            tasks.append(make_task("evaluate", f"baseline-d{r}-f{facts}", worker_argv("baseline", *common_args(args), "--item", f"{r},{facts}"), run_dir, identity, run_dir / "baselines" / f"d{r}_f{facts}.json"))
    m = run_stage_tasks("evaluate", args, tasks, run_dir, cap=stage_cap(args, cap), completed_ids=completed)
    return 0 if m["status"] == "COMPLETE" else 1


def run_simulate(args: argparse.Namespace, fro: fz.Frozen, cap: float | None) -> int:
    run_dir = Path(args.run_dir)
    cells = [c for c in registered_cell_list(fro) if c.kind == "P" and c.draw == 1 and c.arm in ("F-OQ", "T-OQ", "H8")]
    tasks, completed = cell_tasks("simulate", "simulate", args, cells, run_dir, lambda c: run_dir / "simulation" / f"{c.label}.json", previous="evaluate")
    m = run_stage_tasks("simulate", args, tasks, run_dir, cap=stage_cap(args, cap), completed_ids=completed)
    return 0 if m["status"] == "COMPLETE" else 1


def cmd_train(args: argparse.Namespace) -> int:
    return run_train(args, frozen_of(args), None)


def cmd_evaluate(args: argparse.Namespace) -> int:
    return run_evaluate(args, frozen_of(args), None)


def cmd_simulate(args: argparse.Namespace) -> int:
    return run_simulate(args, frozen_of(args), None)


def cmd_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("analyze", "analyze", args, run_dir, run_dir / "analysis.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise pool.StageRefused("refused: the report runs once and never overwrites")
    manifest = single("report", "report", args, run_dir, out / "results.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


# --- the projection, the headroom rule and the cuts (section 10.2, 10.3) -----------------------------------------------------------------------------
def read_rehearsal(run_dir: Path, plan: core.Plan) -> tuple[budget.Rates, dict[int, float]]:
    """Rates (training, evaluation, task start-up, peaks) of every configuration of the plan and the baselines' seconds per fact count, from the rehearsal's whitelisted records and the pool's
    task table (the task seconds include the process start-up that a registered task pays again)."""
    trains, evals = [], []
    for item in budget.rehearsal_items(plan):
        folder = run_dir / "rehearsal" / budget.item_label(item)
        if (folder / "rehearsal.json").is_file():
            trains.append({**core.read_record(folder / "rehearsal.json", "rehearsal"), "facts": item[1]})  # the item's registered facts (the DRY profile trains fewer)
        if (folder / "rehearsal_evaluate.json").is_file():
            e = core.read_record(folder / "rehearsal_evaluate.json", "rehearsal")
            evals.append(e)
    tasks: dict[str, dict[str, float]] = {}
    manifest_path = run_dir / "rehearse" / "manifest.json"
    if manifest_path.is_file():
        tasks = {t["label"]: {"seconds": float(t["seconds"]), "peak_rss_bytes": float(t["peak_rss_bytes"])} for t in core.read_record(manifest_path, "stage_manifest")["tasks"]}
    rates = budget.rates_from_records(trains, evals, tasks)
    baselines: dict[int, float] = {}
    for facts in sorted({f for f, _ in core.grid_cells(plan)}):
        p = run_dir / "rehearsal" / budget.baseline_label(facts) / "rehearsal_evaluate.json"
        if p.is_file():
            task = tasks.get(budget.baseline_label(facts))
            baselines[facts] = float(task["seconds"]) if task is not None else float(core.read_record(p, "rehearsal")["evaluation_wall_seconds"])
    return rates, baselines


def cmd_project(args: argparse.Namespace) -> int:
    """The projection: rates from the rehearsal, the cost tables of the isolated timing, the memory rule (evaluation peaks included), the headroom rule and the cuts in their fixed order
    (``budget.choose_plan``), the cap table of every configuration, all bound to the calibration record, the timing record, the rehearsal gates and the synthetic-registry record by hash. A
    return to the human lead named in section 10.1 or 10.3 is written into the record and the command exits 1; nothing is chosen on the lead's behalf."""
    run_dir = Path(args.run_dir)
    for need, what in ((args.calibration, "--calibration"), (args.timing, "--timing"), (args.gates, "--gates"), (args.synthetic, "--synthetic")):
        if not need:
            raise pool.StageRefused(f"refused: {what} is required (the projection binds them by hash)")
    cal = core.read_record(Path(args.calibration), "calibration")
    tim = core.read_record(Path(args.timing), "timing")
    syn = core.read_record(Path(args.synthetic), "rehearsal")
    gts = core.read_record(Path(args.gates), "gates")
    returns = list(cal["returns_to_lead"])
    if tim.get("status") != "MEASURED":
        returns.append("the isolated timing was NOT MEASURED: no cost table, no matched-compute plan")
    if not all(gts.get(f"{n}_passed") is True for n in GATE_NAMES):
        returns.append("the gates stage on the rehearsal draw did not pass")
    unit = unit_of(args)
    load_action = cal["load_decision"]["action"]
    overload = cal["overload"]["u_p"] if load_action == calibrate.OVERLOAD_ROW and cal.get("overload") else None
    if load_action == calibrate.OVERLOAD_ROW and overload is None:
        returns.append("the overload row has no qualifying U_P")
    if args.dry:
        returns = []  # the DRY stage proceeds on synthetic numbers; the record says so
    try:
        dense_rates = calibrate.dense_rates_of(cal)
    except calibrate.TieNeedsLead as exc:
        if not args.dry:
            returns.append(str(exc))
        dense_rates = {4096: core.LEARNING_RATE, 16384: core.LEARNING_RATE, 65536: core.LEARNING_RATE}
    plan0 = core.Plan(overload, (1, 2), (), False, unit)
    rates, baselines = read_rehearsal(run_dir, plan0)
    missing = budget.missing_items(rates, plan0)
    cpu = {(k.split("|")[0], int(k.split("|")[1])): float(v) for k, v in tim.get("cpu_per_update", {}).items()}
    if missing:
        returns.append(f"{len(missing)} rehearsal item(s) have no record: {[budget.item_label(i) for i in missing[:5]]}")
    record: dict[str, Any] = {
        **core.envelope("projection"), "calibration": {"path": str(Path(args.calibration).resolve()), "sha256": file_sha256(Path(args.calibration))}, "timing": {"path": str(Path(args.timing).resolve()), "sha256": file_sha256(Path(args.timing))},
        "rehearsal_gates": {"path": str(Path(args.gates).resolve()), "sha256": file_sha256(Path(args.gates))}, "synthetic": {"path": str(Path(args.synthetic).resolve()), "sha256": file_sha256(Path(args.synthetic))},
        "calibration_sha256": file_sha256(Path(args.calibration)), "dry": bool(args.dry), "rates": {budget.item_label(i): dataclasses.asdict(r) for i, r in rates.items()}, "missing_items": [budget.item_label(i) for i in missing],
        "memory": budget.memory_headroom(rates), "baseline_seconds": {str(k): v for k, v in baselines.items()}, "returns_to_lead": returns, "overload_u_p": overload, "dense_rates": {str(k): v for k, v in dense_rates.items()},
        "h8_undertrained": cal["h8"]["undertrained_cells"], "eligible_doq_cuts": cal["cut3_eligible"], "cap_seconds": core.cap_seconds(repo_of(args) / core.DEFAULT_CONFIG if args.repo else None),
        "environment": core.environment(),
    }  # fmt: skip
    ledger = core.Ledger.from_config(ledger_root(args), repo_of(args) / core.DEFAULT_CONFIG if args.repo else None)
    record["charged_seconds"] = ledger.charged()
    if not returns and cpu:
        fixed = budget.Fixed(gates=float(gts["wall_seconds"]), timing=sum(float(v["cpu_seconds_per_update"]) * (core.TIMING_WARMUP_UPDATES + core.TIMING_REPEATS * core.TIMING_UPDATES) for v in tim["runs"].values()) + 120.0, simulate=60.0, analysis=float(syn["analysis_wall_seconds"]), report=float(syn["report_wall_seconds"]))
        kw = {"dense_rates": {int(k): v for k, v in dense_rates.items()}, "h8_undertrained": list(cal["h8"]["undertrained_cells"])}
        chosen = budget.choose_plan(rates, fixed, cpu, charged_seconds=ledger.charged(), cap_seconds=record["cap_seconds"], eligible_doq=cal["cut3_eligible"], overload_u_p=overload, baseline_seconds=baselines, frozen_kwargs=kw, unit=unit)
        record["fixed"] = dataclasses.asdict(fixed)
        record["chosen"] = {"ok": chosen.ok, "plan": None if chosen.plan is None else chosen.plan.as_json(), "applied_cuts": chosen.applied_cuts, "headroom": None if chosen.headroom is None else chosen.headroom._asdict(), "projection": None if chosen.projection is None else chosen.projection._asdict(), "tried": chosen.tried}
        if chosen.returns_to_lead:
            record["returns_to_lead"] = [*returns, chosen.returns_to_lead]
        if chosen.ok:
            record["caps"] = budget.caps_table(rates, fixed, cpu, overload_u_p=overload, unit=unit, baseline_seconds=baselines, frozen_kwargs=kw)
            record["cpu_per_update"] = {f"{a}|{n}": v for (a, n), v in sorted(cpu.items())}
    path = run_dir / "projection.json"
    if path.exists():
        raise FileExistsError(path)
    core.write_record(path, core.jsonable(record))
    print(json.dumps({"projection": str(path), "returns_to_lead": record["returns_to_lead"], "chosen": record.get("chosen", {}).get("applied_cuts")}))
    return 0 if not record["returns_to_lead"] else 1


# --- the freeze (section 11 item 7) ------------------------------------------------------------------------------------------------------------------
def cmd_freeze(args: argparse.Namespace) -> int:
    """Write ``plan.json`` (identities, the frozen plan and tables, the headroom proof) and ``stage_caps.json`` into ``--freeze-dir`` (default ``studies/p10s1/freeze``) from the
    calibration, the projection, the timing and the rehearsal gates, and the five registered draws' data manifests of ``--run-dir``. Deterministic: a pure function of its inputs. It
    refuses when any return to the human lead is open, when a binding hash differs, when the cap changed after the projection, or when lane L is requested (F-LA is S0's frozen candidate;
    no implementation of it is in this tree)."""
    out_dir = Path(args.freeze_dir) if args.freeze_dir else repo_of(args) / core.FREEZE_DIR
    plan_path, caps_path = out_dir / "plan.json", out_dir / "stage_caps.json"
    if plan_path.exists() or caps_path.exists():
        raise pool.StageRefused(f"refused: {out_dir} already holds a freeze; a freeze is written once")
    if args.lane_l:
        raise pool.StageRefused("refused: lane L is not implemented (F-LA is S0's frozen candidate, whose code is not in this tree); it stays OMITTED and changes nothing in S1")
    run_dir = Path(args.run_dir)
    proj_dir = Path(args.projection).parent
    proj = core.read_record(Path(args.projection), "projection")
    if proj["returns_to_lead"] or not proj.get("chosen", {}).get("ok") or "caps" not in proj:
        raise pool.StageRefused(f"refused: the projection has open returns to the human lead or no plan: {proj['returns_to_lead']}")
    for key, path in (("calibration", args.calibration), ("timing", args.timing), ("rehearsal_gates", args.gates)):
        if file_sha256(Path(path)) != proj[key]["sha256"]:
            raise pool.StageRefused(f"refused: {path} does not hash to the {key} record the projection was bound to")
    if proj["cap_seconds"] != core.cap_seconds(repo_of(args) / core.DEFAULT_CONFIG if args.repo else None):
        raise pool.StageRefused("refused: the cap in the config differs from the cap the projection was computed under")
    if not proj["memory"]["ok"]:
        raise pool.StageRefused(f"refused: {budget.NOT_RUN_MEMORY}")
    manifests = {}
    for name in manifest_names(args):
        p = manifest_dir(run_dir, name) / "data_manifest.json"
        if not data_manifest_ok(run_dir, name):
            raise pool.StageRefused(f"refused: {name} has no passed G1 record in {run_dir}")
        manifests[name] = file_sha256(p)
    cal = core.read_record(Path(args.calibration), "calibration")
    plan = core.Plan.from_json(proj["chosen"]["plan"])
    cpu = {(k.split("|")[0], int(k.split("|")[1])): float(v) for k, v in proj["cpu_per_update"].items()}
    directed = [t for t in args.no_loaded_transitions.split(",") if t]
    fro = fz.Frozen.build(
        plan, cpu, dense_rates={int(k): float(v) for k, v in proj["dense_rates"].items()}, h8_undertrained=list(proj["h8_undertrained"]), s0_status=args.s0_status, lane_status=args.lane_status,
        no_loaded_transitions=directed, cuts=list(proj["chosen"]["applied_cuts"]),
    )  # fmt: skip
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(caps_path, core.jsonable(proj["caps"]))
    identity = core.code_identity()
    record = {
        **core.envelope("freeze_plan"), "calibration": proj["calibration"], "projection": {"path": str(Path(args.projection).resolve()), "sha256": file_sha256(Path(args.projection))}, "timing": proj["timing"],
        "rehearsal_gates": proj["rehearsal_gates"], "synthetic": proj["synthetic"], "stage_caps_sha256": file_sha256(caps_path), "run_dir": str(run_dir.resolve()), "data_manifests": manifests,
        "frozen": fro.as_json(), "frozen_sha256": sha256(canonical_json(fro.as_json())), "cap_seconds": proj["cap_seconds"], "headroom": proj["chosen"]["headroom"], "cuts": proj["chosen"]["applied_cuts"],
        "identity": identity, "dense_rates": proj["dense_rates"], "load_decision": cal["load_decision"], "lane_l": args.lane_status, "s0_status": args.s0_status, "no_loaded_transitions": directed,
        "projection_dir": str(proj_dir.resolve()), "note": "the freeze record: nothing registered runs without it; every hash is checked by every registered stage",
    }  # fmt: skip
    write_json(plan_path, core.jsonable(record))
    print(json.dumps({"plan": str(plan_path), "sha256": file_sha256(plan_path), "caps": str(caps_path), "caps_sha256": file_sha256(caps_path)}))
    return 0


# --- the registered driver (called by the fixed launch scripts) ---------------------------------------------------------------------------------------
def load_plan(repo: Path) -> dict[str, Any]:
    """The frozen plan (``studies/p10s1/freeze/plan.json``): the calibration, projection, timing and rehearsal-gates records, the stage-cap table, the data manifests and the frozen plan
    and tables, each with its sha256, and the registered run directory. Absent before the freeze: nothing registered then runs."""
    path = repo / FREEZE_PLAN
    if not path.is_file():
        raise pool.StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
    return load_plan_file(path)


def manifest_names(args: argparse.Namespace | None = None) -> tuple[str, ...]:
    return ("p10s1-test-0",) if args is not None and args.dry else core.DRAW_NAMES


def verify_plan(plan: dict[str, Any], repo: Path, run_dir: Path) -> None:
    """Every identity the freeze recorded must hold now: the calibration, projection, timing and rehearsal-gates records, the stage-cap table (the one source of the caps), the data manifest
    of every registered draw, the frozen plan and tables, the cap in the config, the running code against the code the freeze was written for, and the run directory. The projection must
    have been bound to the calibration record."""

    def check(path: Path, expected: str, what: str) -> None:
        if not path.is_file() or file_sha256(path) != expected:
            raise pool.StageRefused(f"refused: {path} does not hash to the frozen {what}")

    for key in ("calibration", "projection", "timing", "rehearsal_gates", "synthetic"):
        check(Path(plan[key]["path"]), plan[key]["sha256"], f"{key} record")
    check(repo / CAPS_FILE, plan["stage_caps_sha256"], "stage-cap table")
    if Path(plan["run_dir"]).resolve() != run_dir.resolve():
        raise pool.StageRefused(f"refused: the freeze names the run directory {plan['run_dir']}, not {run_dir}")
    if set(plan["data_manifests"]) != set(core.DRAW_NAMES):
        raise pool.StageRefused("refused: the freeze must name the data manifest of all five registered draws")
    for name, digest in plan["data_manifests"].items():
        check(manifest_dir(run_dir, name) / "data_manifest.json", digest, f"data manifest of {name}")
    if sha256(canonical_json(plan["frozen"])) != plan["frozen_sha256"]:
        raise pool.StageRefused("refused: the frozen plan and tables do not hash to the recorded digest")
    projection = core.read_record(Path(plan["projection"]["path"]), "projection")
    if projection.get("calibration_sha256") != plan["calibration"]["sha256"]:
        raise pool.StageRefused("refused: the projection was not bound to the frozen calibration record")
    config = repo / core.DEFAULT_CONFIG
    if core.cap_seconds(config) != plan["cap_seconds"]:
        raise pool.StageRefused("refused: the cap in the config differs from the cap of the freeze")
    if core.code_identity(repo) != plan["identity"]:
        raise pool.StageRefused("refused: the running code, spec or config differ from the identity of the freeze")


def stage_cap_of(caps: dict[str, Any], stage: str, plan: core.Plan) -> float:
    try:
        return budget.cap_for(caps, stage, plan)
    except budget.CapMissing as exc:
        raise pool.StageRefused(f"refused: {exc}") from exc


def require_manifest(run_dir: Path, stage: str) -> None:
    if not (run_dir / stage / "manifest.json").is_file():
        raise pool.StageRefused(f"refused: the {stage} stage has no manifest in {run_dir}: stages run in order")


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name (``REGISTERED_STAGES``), with everything else (caps, plan, seeds) from the frozen plan and the frozen cap table. The only free arguments are the run
    directory and the freeze commit; the launch scripts pass nothing else."""
    if args.name not in REGISTERED_STAGES:
        raise pool.StageRefused(f"refused: unknown registered stage {args.name!r}")
    args.mode = REGISTERED
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    check_preconditions(REGISTERED, repo, args.freeze_commit)
    if args.caps and Path(args.caps) != Path(CAPS_FILE):
        raise pool.StageRefused(f"refused: the cap table is {CAPS_FILE}")
    plan_rec = load_plan(repo)
    verify_plan(plan_rec, repo, run_dir)
    caps = read_json(repo / CAPS_FILE)
    args.freeze_plan = str(repo / FREEZE_PLAN)
    args.workers = core.WORKERS
    fro = frozen_of(args)
    name = args.name
    projection = core.read_record(Path(plan_rec["projection"]["path"]), "projection")
    if name in ("train", "evaluate", "timing", "simulate") and not projection["memory"]["ok"]:
        raise pool.StageRefused(f"refused: {budget.NOT_RUN_MEMORY}: twice the largest measured peak ({projection['memory']['peak_rss_bytes']} bytes) exceeds the per-worker or aggregate cap; nothing is run")
    cap = stage_cap_of(caps, "analysis" if name == "analysis" else name, fro.plan)
    if name == "gates":
        args.stage_cap_seconds = cap
        return cmd_gates(args)
    if name == "train":
        return run_train(args, fro, cap)
    if name == "evaluate":
        require_manifest(run_dir, "train")
        return run_evaluate(args, fro, cap)
    if name == "timing":
        require_manifest(run_dir, "evaluate")
        args.throughput, args.stage_cap_seconds = True, cap
        return cmd_timing(args)
    if name == "simulate":
        require_manifest(run_dir, "evaluate")
        return run_simulate(args, fro, cap)
    if name == "analysis":
        require_manifest(run_dir, "evaluate")
        args.stage_cap_seconds = cap
        return cmd_analyze(args)
    if not (run_dir / "analysis.json").is_file():
        raise pool.StageRefused("refused: no analysis.json: run the analysis first")
    args.stage_cap_seconds = cap
    return cmd_report(args)


# --- the DRY stage ---------------------------------------------------------------------------------------------------------------------------------
def cmd_dry(args: argparse.Namespace) -> int:
    """Every stage, in order, at tiny size on test seeds in a temporary root, with a private ledger: generate (G1), calibrate (all calibration cells), the gates, the rehearsal, the isolated
    timing, the synthetic-registry analysis, the projection, the freeze (into a temporary freeze directory), the training and evaluation of the whole registry, the throughput, the
    simulation, the analysis and the report. Every number is tiny-size and synthetic: it measures nothing."""
    root = Path(args.out_root) if args.out_root else Path(tempfile.mkdtemp(prefix="p10s1-dry-"))
    run_dir, reh, cal, frz = root / "P10S1DRY-run", root / "P10S1DRY-rehearsal", root / "P10S1DRY-calibration", root / "freeze"
    if run_dir.exists():
        raise pool.StageRefused(f"refused: {run_dir} exists")
    shared = ["--dry", "--experiments-root", str(root), "--ledger-root", str(root), "--workers", str(args.workers), "--stage-cap-seconds", str(args.stage_cap_seconds or 3600)]
    plan_file = frz / "plan.json"
    steps: list[tuple[str, list[str]]] = [
        ("generate", ["generate", *shared, "--mode", CALIBRATION, "--run-dir", str(run_dir)]),
        ("generate-rehearsal", ["generate", *shared, "--mode", REHEARSAL, "--run-dir", str(reh)]),
        ("calibrate", ["calibrate", *shared, "--run-dir", str(cal)]),
        ("gates", ["gates", *shared, "--mode", REHEARSAL, "--run-dir", str(reh)]),
        ("rehearse", ["rehearse", *shared, "--run-dir", str(reh), "--calibration", str(cal / "calibration.json")]),
        ("timing", ["timing", *shared, "--mode", REHEARSAL, "--run-dir", str(reh)]),
        ("synthetic", ["synthetic", *shared, "--mode", REHEARSAL, "--run-dir", str(reh)]),
        ("project", ["project", *shared, "--mode", REHEARSAL, "--run-dir", str(reh), "--calibration", str(cal / "calibration.json"), "--timing", str(reh / "timing.json"), "--gates", str(reh / "gates.json"), "--synthetic", str(reh / "synthetic.json")]),
        ("freeze", ["freeze", *shared, "--mode", REHEARSAL, "--run-dir", str(run_dir), "--projection", str(reh / "projection.json"), "--calibration", str(cal / "calibration.json"), "--timing", str(reh / "timing.json"), "--gates", str(reh / "gates.json"), "--freeze-dir", str(frz)]),
    ]
    tail = ["--mode", CALIBRATION, "--run-dir", str(run_dir), "--freeze-plan", str(plan_file)]
    steps += [("gates-run", ["gates", *shared, "--mode", CALIBRATION, "--run-dir", str(run_dir), "--freeze-plan", str(plan_file)])]
    steps += [
        ("train", ["train", *shared, *tail]), ("evaluate", ["evaluate", *shared, *tail]), ("throughput", ["timing", *shared, *tail, "--throughput"]), ("simulate", ["simulate", *shared, *tail]),
        ("analyze", ["analyze", *shared, *tail]), ("report", ["report", *shared, *tail]),
    ]  # fmt: skip
    summary: dict[str, Any] = {"run_dir": str(run_dir), "banner": DRY_BANNER, "stages": {}}
    for name, argv in steps:
        code = main(argv)
        summary["stages"][name] = code
        if name in ("generate", "generate-rehearsal", "gates", "project", "freeze") and code != 0:
            break
    analysis_path = run_dir / "analysis.json"
    if analysis_path.is_file():
        data = core.read_record(analysis_path, "analysis")
        summary["status"] = data["result"]["assessment"]["status"]
        summary["capacity"] = data["result"]["outcome"]["capacity"]["label"]
        summary["efficiency"] = data["result"]["outcome"]["efficiency"]["label"]
    summary["report"] = str(run_dir / "results" / "RESULTS.md") if (run_dir / "results" / "results.json").is_file() else None
    summary["charged_seconds"] = core.Ledger.from_config(root).charged()
    write_json(root / "DRY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["report"] else 1


# --- command line ----------------------------------------------------------------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--run-dir", default=None)
    p.add_argument("--experiments-root", default=None)
    p.add_argument("--ledger-root", default=None, help="directory of the ledger (default: the experiments root)")
    p.add_argument("--repo", default=None, help="repository to check for a registered stage (tests)")
    p.add_argument("--mode", choices=(REGISTERED, CALIBRATION, REHEARSAL), default=None)
    p.add_argument("--draw", type=int, default=1, help="registered draw 1-5, or calibration draw 1 or 2")
    p.add_argument("--dry", action="store_true", help="the DRY profile (tiny sizes, test seeds; never registered)")
    p.add_argument("--synthetic-backbone", action="store_true", help="random stand-in backbone (DRY and tests only)")
    p.add_argument("--freeze-commit", default=None)
    p.add_argument("--caps", default=None, help="stage caps file of the freeze (fixed in the launch scripts)")
    p.add_argument("--calibration", default=None, help="calibration record the rehearsal and projection are bound to")
    p.add_argument("--timing", default=None, help="isolated timing record (the cost tables)")
    p.add_argument("--gates", default=None, help="project: the rehearsal gates record")
    p.add_argument("--synthetic", default=None, help="project: the synthetic-registry record")
    p.add_argument("--projection", default=None, help="freeze: the projection record")
    p.add_argument("--freeze-plan", default=None, help="the frozen plan (set by the registered driver)")
    p.add_argument("--freeze-dir", default=None, help="freeze: where plan.json and stage_caps.json are written")
    p.add_argument("--workers", type=int, default=core.WORKERS)
    p.add_argument("--stage-cap-seconds", type=float, default=None)
    p.add_argument("--rss-worker-bytes", type=int, default=core.RSS_WORKER_BYTES)
    p.add_argument("--rss-aggregate-bytes", type=int, default=core.RSS_AGGREGATE_BYTES)
    p.add_argument("--only", action="append", default=None, help="restrict a stage to these cell labels")
    p.add_argument("--labels", default=None, help="worker commands: comma-separated cell labels")
    p.add_argument("--item", default=None, help="worker commands: the rehearsal item (arm,facts,slots), the baseline (draw,facts) or a fact count")
    p.add_argument("--restore-split", type=int, default=16)
    p.add_argument("--results-dir", default=None)
    p.add_argument("--updates", type=int, default=None, help="rehearsal updates")
    p.add_argument("--overload-u-p", type=int, default=None, help="the overload row's U_P (calibration decision)")
    p.add_argument("--seed-block", default="1", help="draws that carry the seed block, comma-separated (the plan decides in registered mode)")
    p.add_argument("--with-overload", action="store_true", help="calibrate: add the overload row's U_P calibration (4 runs)")
    p.add_argument("--throughput", action="store_true", help="timing: the throughput stage instead of the isolated CPU timing")
    p.add_argument("--s0-status", default=fz.S0_NOT_DECIDED, help="freeze: S0's status line (K7(c))")
    p.add_argument("--lane-status", default=fz.LANE_OMITTED_NO_INTERFACE, help="freeze: lane L's status")
    p.add_argument("--no-loaded-transitions", default="", help="freeze: transitions the human lead directed to run with no loaded row (comma-separated)")
    p.add_argument("--lane-l", action="store_true", help="freeze: enable lane L (refused: not implemented)")
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p10s1.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", parents=[common])
    gen.add_argument("--i-understand-freeze-time", action="store_true")
    for name in ("calibrate", "rehearse", "gates", "timing", "synthetic", "project", "freeze", "train", "evaluate", "simulate", "analyze", "report"):
        sub.add_parser(name, parents=[common])
    reg = sub.add_parser("registered", parents=[common])
    reg.add_argument("name", choices=REGISTERED_STAGES)
    dry = sub.add_parser("dry", parents=[common])
    dry.add_argument("--out-root", default=None)
    work = sub.add_parser("work")
    wsub = work.add_subparsers(dest="worker", required=True)
    for name in WORKERS:
        wsub.add_parser(name, parents=[common])
    return parser


COMMANDS: dict[str, Any] = {
    "generate": cmd_generate, "calibrate": cmd_calibrate, "rehearse": cmd_rehearse, "gates": cmd_gates, "timing": cmd_timing, "synthetic": cmd_synthetic, "project": cmd_project, "freeze": cmd_freeze,
    "train": cmd_train, "evaluate": cmd_evaluate, "simulate": cmd_simulate, "analyze": cmd_analyze, "report": cmd_report, "registered": cmd_registered, "dry": cmd_dry,
}  # fmt: skip
DEFAULT_MODE = {"generate": CALIBRATION, "calibrate": CALIBRATION, "rehearse": REHEARSAL, "timing": REHEARSAL, "synthetic": REHEARSAL, "project": REHEARSAL, "freeze": REHEARSAL}


def main(argv: Sequence[str] | None = None) -> int:
    """Exit codes: 0 stage complete, 1 stage ran but a task or gate failed (records kept), 2 refused."""
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.command == "registered":
        args.mode = REGISTERED
    if args.mode is None:
        args.mode = DEFAULT_MODE.get(args.command, REGISTERED)
    if args.dry and args.mode == REGISTERED:
        print("refused: --dry cannot be combined with --mode registered", file=sys.stderr)
        return 2
    try:
        if args.command == "work":
            configure()
            return int(WORKERS[args.worker](args))
        if args.command == "dry":
            args.dry, args.mode = True, CALIBRATION
        elif args.run_dir is None and args.command not in ("calibrate", "rehearse", "generate", "timing", "synthetic"):
            raise StageError("--run-dir is required")
        return int(COMMANDS[args.command](args))
    except (pool.StageRefused, core.LedgerRefused) as exc:
        print(f"P10S1 stage REFUSED: {exc}", file=sys.stderr)
        return 2
    except CalibrationRefused as exc:
        print(f"P10S1 calibration REFUSED: {exc}", file=sys.stderr)
        return 2
    except (StageError, RegisteredRefused) as exc:
        print(f"P10S1 stage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
