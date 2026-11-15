# ruff: noqa: E501
"""P9II stages (ADR-0019 sections 6, 9, 10, 12): ``generate`` (per draw), ``draw-plan``, ``gates``, ``calibrate``, ``rehearse``, ``train``, ``evaluate``,
``stagegate``, ``analyze``, ``report``, ``dry`` and ``registered`` (the driver the fixed launch scripts call).

Run from the repository root: ``uv run --locked python -m studies.p9ii.stages <command> ...``. Stages run through P9's job manager
(``studies.p9.pool.run_stage``): immutable task ids, per-worker RSS cap (3 GiB), aggregate cap (24 GiB), failed records kept, a failed cell stops the cells
that depend on it, nothing is re-run with changed settings. Workers are single-thread subprocesses (six by default).

Two ledgers. Budget A (4 h: generation, gates, calibration, rehearsal, Stage 1) and Budget B (3 h: Stages 2 and 3), ``core.Ledger``; a stage starts only if twice
its rehearsed projection fits what remains of its budget (``budget.budget_decision``, a pure function), else its status is NOT RUN — BUDGET.

Modes and seeds (``core.check_seed_set``). ``registered`` (needs ``--freeze-commit`` and a clean tree): ``p9ii-draw-k`` and ``p9ii-reserve-k``; ``calibration``:
rehearsal sets 3 and 4 only, refusing any cell that is not a calibration cell; ``rehearsal``: set 5 only, writing nothing but the whitelisted record; the DRY
stage and the unit tests use test seeds (910001+) and a random synthetic backbone.

Not run by this module's author: the calibration, the rehearsal and every registered stage.
"""

import argparse
import dataclasses
import functools
import json
import math
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from arborlm.io import file_sha256, read_json, write_json
from studies.p9 import controls, pool
from studies.p9 import core as p9core
from studies.p9 import data as data_mod

from . import analysis, budget, core, evaluate, gates, model, report, train
from . import classes as C

REGISTERED, CALIBRATION, REHEARSAL = "registered", "calibration", "rehearsal"
DRY_BANNER = "DRY: tiny synthetic sizes, random synthetic backbone, test seeds; not a measurement of anything"
DRY_SIZES = data_mod.DataSizes(main_trained=2048, unseen=64, lane_d_per_set=128)
DRY_FACTS = {4096: 128, 16384: 256, 65536: 512}  # the registered 2,048 : 8,192 : 32,768 proportions
DRY_UNIT = 8
DRY_DIAG_EVERY = 2
DRY_G1_PERMUTATIONS = 200
SYNTHETIC_CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
PARENT = p9core.PRIMARY_PARENT
STAGE_GROUP = {"generate": "analyze", "gates": "train", "calibrate": "train", "rehearse": "train", "train": "train", "evaluate": "evaluate", "analyze": "analyze", "report": "analyze"}
FREEZE_PLAN = Path("studies/p9ii/freeze/plan.json")
CAPS_FILE = "studies/p9ii/freeze/stage_caps.json"
REGISTERED_STAGES = ("gates", "stage1", "stage1_gate", "stage2", "stage3_gate", "stage3", "analysis", "report")


class StageError(RuntimeError):
    """A stage cannot start for a reason other than a pool refusal."""


class CalibrationRefused(RuntimeError):
    """The calibration was asked to build or train something other than a calibration cell."""


def _utc() -> str:
    return datetime.now(UTC).isoformat()


# --- guards ---------------------------------------------------------------------------------------------------------------------
def calibration_guard(cell: core.Cell) -> None:
    """Section 6: the calibration runs the 22 calibration cells on rehearsal sets 3 and 4 and nothing else; refused in code before anything is built."""
    if cell.stage != 0 or cell.draw not in core.CALIBRATION_DRAWS or cell not in core.calibration_cells():
        raise CalibrationRefused(f"the calibration trains only its 22 calibration cells on calibration draws 3 and 4 (ADR-0019 section 6); refused: {cell.label}")


def is_synthetic(args: argparse.Namespace) -> bool:
    return bool(args.dry or args.synthetic_backbone)


def unit_of(args: argparse.Namespace) -> int:
    return DRY_UNIT if args.dry else core.UPDATES


def diag_every_of(args: argparse.Namespace) -> int:
    return DRY_DIAG_EVERY if args.dry else core.DIAG_EVERY


def experiments_root(args: argparse.Namespace) -> Path:
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def repo_of(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def seeds_named(args: argparse.Namespace, draw: int | None = None, reserve: int | None = None) -> p9core.SeedSet:
    """The data seeds a command may use in its mode; ``core.check_seed_set`` is applied again by every training job."""
    reserve = args.reserve if reserve is None else reserve
    if is_synthetic(args):
        if args.mode == REGISTERED:
            raise pool.StageRefused("refused: registered seeds with the DRY profile or a synthetic backbone")
        return core.test_seeds(0)
    if args.mode == REGISTERED:
        if reserve is not None:
            return core.reserve_seeds(reserve)
        plan = Path(args.run_dir) / "draw_plan.json" if args.run_dir else None
        k = args.draw if draw is None else draw
        if plan is not None and plan.is_file():
            return core.seeds_of_name(core.read_record(plan, "draw_plan")["seed_set_of"][str(k)])
        return core.registered_draw_seeds(k)
    if args.mode == CALIBRATION:
        return core.calibration_seeds(args.draw if draw is None else draw)
    return core.rehearsal_seeds()


def seeds_for_cell(args: argparse.Namespace, cell: core.Cell) -> p9core.SeedSet:
    return seeds_named(args, draw=cell.draw)


def corpus_bytes(args: argparse.Namespace) -> bytes:
    return SYNTHETIC_CORPUS if is_synthetic(args) else p9core.load_trained_corpus(experiments_root(args))


@functools.cache
def _build_data(seeds: p9core.SeedSet, corpus: bytes, dry: bool) -> data_mod.StudyData:
    return data_mod.build_study_data(seeds, corpus, sizes=DRY_SIZES if dry else None)


def study_data(args: argparse.Namespace, seeds: p9core.SeedSet) -> data_mod.StudyData:
    core.check_seed_set(args.mode, seeds.name)
    study = _build_data(seeds, corpus_bytes(args), bool(args.dry))
    if args.mode == REGISTERED and study.pool != p9core.TEMPLATE_POOL:
        raise StageError("template pool differs from the registered pool (studies.p9.core.TEMPLATE_POOL)")
    return study


@functools.cache
def _synthetic() -> Any:
    return controls.synthetic_backbone(*PARENT)


def backbone_for(args: argparse.Namespace) -> Any:
    return _synthetic() if is_synthetic(args) else controls.load_backbone(PARENT, experiments_root(args))[0]


def facts_for(args: argparse.Namespace, cell: core.Cell) -> int:
    return DRY_FACTS[cell.slots] if args.dry else cell.facts


def manifest_dir(run_dir: Path, name: str) -> Path:
    return run_dir / "draws" / name


def verified_data(args: argparse.Namespace, seeds: p9core.SeedSet, *, require_manifest: bool) -> data_mod.StudyData:
    """``study_data`` checked against the stream hashes of the draw's data manifest."""
    study = study_data(args, seeds)
    path = manifest_dir(Path(args.run_dir), seeds.name) / "data_manifest.json"
    if path.is_file():
        if core.read_record(path, "data_manifest")["sha256s"] != study.sha256s():
            raise StageError(f"regenerated data differ from the hashes in {path}")
    elif require_manifest:
        raise StageError(f"no data manifest at {path}: run generate first")
    return study


# --- calibration binding, hyperparameters ---------------------------------------------------------------------------------------------
def calibration_record_of(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.calibration:
        return None
    path = Path(args.calibration)
    if args.calibration_sha256 and file_sha256(path) != args.calibration_sha256:
        raise pool.StageRefused(f"refused: {path} does not hash to the calibration record the stage was started with")
    return core.read_record(path, "calibration")


def hyper_of(args: argparse.Namespace) -> core.Hyper:
    """The calibrated values (the worst-case grid values when there is no record: rehearsal and tests)."""
    record = calibration_record_of(args)
    return core.Hyper() if record is None else core.Hyper.from_json(record["hyper"])


def calibration_binding(args: argparse.Namespace) -> dict[str, Any]:
    record = calibration_record_of(args)
    if record is None:
        return {}
    return {"calibration_sha256": file_sha256(Path(args.calibration)), "calibration_hyper": record["hyper"]}


def require_gates_passed(run_dir: Path) -> dict[str, Any]:
    """A registered training starts only when the ``gates`` record exists and G1, G2, G4, G5 and G6 all passed."""
    path = run_dir / "gates.json"
    if not path.is_file():
        raise pool.StageRefused(f"refused: no gates record at {path}: run the gates stage first")
    record = core.read_record(path, "gates")
    failed = [n.upper() for n in ("g1", "g2", "g4", "g5", "g6") if record.get(f"{n}_passed") is not True]
    if failed:
        raise pool.StageRefused(f"refused: gate(s) {', '.join(failed)} did not pass; nothing is trained")
    return record


# --- cells of a stage --------------------------------------------------------------------------------------------------------------------
def stage_cells(args: argparse.Namespace, stage: int) -> list[core.Cell]:
    """Stage 1: the 128 registered cells. Stages 2 and 3: the cells the stage gate record names (never chosen by hand); the DRY stage may name arms with
    ``--dry-advancing`` / ``--dry-selected`` to exercise the later stages."""
    if stage == 1:
        cells = core.stage1_cells()
    elif stage == 2:
        advancing = args.dry_advancing.split(",") if args.dry and args.dry_advancing else None
        if advancing is None:
            record = core.read_record(Path(args.run_dir) / "stage_gate_1.json", "stage_gate")
            if not record["run"]:
                raise pool.StageRefused(f"refused: Stage 2 is not to run ({record['status']})")
            advancing = record["advancing"]
        cells = core.stage2_cells(advancing)
    else:
        selected = args.dry_selected if args.dry and args.dry_selected else None
        if selected is None:
            record = core.read_record(Path(args.run_dir) / "stage_gate_3.json", "stage_gate")
            if not record["run"]:
                raise pool.StageRefused(f"refused: Stage 3 is not to run ({record['status']})")
            selected = record["selected"]
        cells = core.stage3_cells(selected)
    if args.only:
        cells = [c for c in cells if c.label in set(args.only)]
    return cells


# --- the pool ------------------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/``, the P9II config, the ADR and every
    ``tests/test_p9ii_*`` equal their content at that commit, and ``frozen_input_check`` (src/arborlm, uv.lock, pyproject.toml, P8 digest) is ok. Returns the
    freeze identity (None for calibration and rehearsal)."""
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
        if name.startswith("tests/test_p9ii_") and git(repo, "rev-parse", f"{full}:{name}").stdout != git(repo, "rev-parse", f"HEAD:{name}").stdout:
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise pool.StageRefused("refused: " + "; ".join(problems))
    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise pool.StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def ledger_root(args: argparse.Namespace) -> Path:
    return Path(args.ledger_root) if args.ledger_root else experiments_root(args)


def common_args(args: argparse.Namespace) -> list[str]:
    """Options every worker needs to rebuild the same draw (never a scientific value)."""
    out = ["--run-dir", str(args.run_dir), "--mode", args.mode, "--draw", str(args.draw), "--experiments-root", str(experiments_root(args))]
    if args.dry:
        out.append("--dry")
    if args.synthetic_backbone:
        out.append("--synthetic-backbone")
    if args.calibration:
        out += ["--calibration", str(args.calibration), "--calibration-sha256", file_sha256(Path(args.calibration))]
    if args.updates is not None:
        out += ["--updates", str(args.updates)]
    if args.reserve is not None:
        out += ["--reserve", str(args.reserve)]
    if args.dry_advancing:
        out += ["--dry-advancing", args.dry_advancing]
    if args.dry_selected:
        out += ["--dry-selected", args.dry_selected]
    return out


def worker_argv(worker: str, *extra: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "studies.p9ii.stages", "work", worker, *extra)


def make_task(stage: str, label: str, argv: Sequence[str], run_dir: Path, identity: dict[str, str], result_path: Path, *, after: Sequence[str] = ()) -> pool.Task:
    if len(argv) < 5 or argv[1:3] != ("-m", "studies.p9ii.stages"):
        raise ValueError("worker argv must be '<python> -m studies.p9ii.stages work ...'")
    folder = run_dir / stage
    return pool.Task(
        task_id=pool.task_id(stage, label, cast(Any, identity)),
        stage=stage,
        label=label,
        argv=tuple(argv),
        depends_on=(),
        after=tuple(after),
        group=STAGE_GROUP[stage.split("-")[0].rstrip("0123456789")],
        result_path=result_path,
        failed_path=folder / f"{label}.failed.json",
        log_path=folder / f"{label}.log",
    )


def run_stage_tasks(
    stage: str,
    ledger_stage: str,
    args: argparse.Namespace,
    tasks: Sequence[pool.Task],
    run_dir: Path,
    *,
    cap: float,
    completed_ids: Sequence[str] = (),
    workers: int | None = None,
    skip_preconditions: bool = False,
) -> dict[str, Any]:
    """Ledger check, preconditions, the pool, the ledger charge, and the stage manifest (written once, with the environment)."""
    target = run_dir / stage / "manifest.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} already exists; a stage is run once and never overwritten")
    ledger = core.ledger_for_stage(ledger_stage, ledger_root(args))
    ledger.require_room(stage, cap)
    if not skip_preconditions:
        check_preconditions(args.mode, repo_of(args), args.freeze_commit)
    count = workers or args.workers
    if args.mode == REGISTERED and not 1 <= count <= core.WORKERS:
        raise pool.StageRefused(f"refused: {count} workers; P9II uses at most {core.WORKERS}")
    identity = core.code_identity()
    started = _utc()
    result = pool.run_stage(
        tasks,
        workers={"train": count, "evaluate": count, "analyze": 1},
        stage_cap_seconds=cap,
        rss_worker_bytes=args.rss_worker_bytes,
        rss_aggregate_bytes=args.rss_aggregate_bytes,
        env={"PYTHONPATH": str(core.repo_root())},
        completed_ids=list(completed_ids),
        total_remaining_seconds=ledger.remaining(),
    )
    ledger.charge(stage, run_dir.name, result.wall_seconds)
    manifest = dict(pool.build_manifest(stage, run_dir, args.mode, cast(Any, identity), tasks, result, started_utc=started, finished_utc=_utc(), workers=count, caps=pool.StageCaps(cap, args.rss_worker_bytes, args.rss_aggregate_bytes).as_dict()))
    manifest["study"] = core.STUDY
    manifest["budget"] = ledger.budget
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


def cell_tasks(name: str, worker: str, args: argparse.Namespace, cells: Sequence[core.Cell], run_dir: Path, result_for: Any, *, previous: str | None = None, extra: Sequence[str] = ()) -> tuple[list[pool.Task], list[str]]:
    """One task per cell (the DRY stage groups the cells of a draw into one task to keep its process count small); ``previous`` names the earlier stage
    whose manifest supplies the ``after`` dependency (a cell without a completed upstream task is not run)."""
    identity = core.code_identity()

    def task_label(c: core.Cell) -> str:
        return f"g-d{c.draw:02d}-n{c.slots}" if args.dry else c.label

    prior: dict[str, str] = {}
    completed: list[str] = []
    if previous is not None:
        path = run_dir / previous / "manifest.json"
        if not path.is_file():
            raise StageError(f"no {path}: run {previous} first")
        upstream = core.read_record(path, "stage_manifest")
        prior = {t["label"]: t["task_id"] for t in upstream["tasks"]}
        completed = [t["task_id"] for t in upstream["tasks"] if t["status"] == "completed"]
        cells = [c for c in cells if task_label(c) in prior]
    groups: dict[str, list[core.Cell]] = {}
    for c in cells:
        groups.setdefault(task_label(c), []).append(c)
    tasks = [
        make_task(name, label, worker_argv(worker, "--labels", ",".join(m.label for m in members), *common_args(args), *extra), run_dir, identity, result_for(members[-1]), after=[prior[label]] if label in prior else [])
        for label, members in groups.items()
    ]
    return tasks, completed


# --- job construction -----------------------------------------------------------------------------------------------------------------------
def build_job(args: argparse.Namespace, cell: core.Cell, study: data_mod.StudyData, out_dir: Path, *, stage: int | None = None, mode: str | None = None, snapshots: Sequence[int] | None = None, max_updates: int | None = None, rehearsal_phase: str | None = None, hyper: core.Hyper | None = None, run_stage_number: int | None = None) -> train.TrainJob:
    st = stage if stage is not None else (1 if cell.stage == 0 else cell.stage)
    unit = unit_of(args)
    facts = facts_for(args, cell)
    seeds = study.seeds
    j = cell.seed_index
    init = cell.init_seed if args.mode in (REGISTERED, CALIBRATION) and not is_synthetic(args) else seeds.facts + j
    return train.TrainJob(
        cell=cell,
        hyper=hyper or (core.with_value(core.Hyper(), cell.arm, cell.value) if cell.stage == 0 and cell.value is not None else hyper_of(args)),
        updates=core.stage_updates(st, unit),
        mode=mode or args.mode,
        data=study,
        stream=train.training_stream_for(study, facts),
        backbone=backbone_for(args),
        out_dir=out_dir,
        init_seed=init,
        r1_seed=seeds.r1_codes,
        target_seed=core.target_seed(seeds, j),
        stream_seed=core.stream_seed(seeds, j),
        unit=unit,
        stage=st,
        snapshots=tuple(snapshots) if snapshots is not None else core.stage_readouts(st, unit),
        max_updates=max_updates,
        diag_every=diag_every_of(args),
        rehearsal_phase=rehearsal_phase,
        extra=calibration_binding(args),
    )


def configure() -> None:
    train.configure()


def labels_of_args(args: argparse.Namespace) -> list[str]:
    if not args.labels:
        raise StageError("--labels is required")
    return [s for s in args.labels.split(",") if s]


# --- workers ---------------------------------------------------------------------------------------------------------------------------------
def work_generate(args: argparse.Namespace) -> int:
    """One draw: generate, hash and G1-check it (not an observation of a seed by a model)."""
    seeds = seeds_named(args, reserve=args.reserve)
    folder = manifest_dir(Path(args.run_dir), seeds.name)
    target = folder / "data_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    study = study_data(args, seeds)
    g1 = data_mod.run_g1(study, permutations=DRY_G1_PERMUTATIONS if args.dry else None, train_epochs=None)
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "g1.json", g1)
    core.write_record(target, {**core.envelope("data_manifest"), "seed_set": seeds.name, "seeds": dataclasses.asdict(seeds), "dry": bool(args.dry), "sha256s": study.sha256s(), "template_pool": list(study.pool), "g1_passed": bool(g1["passed"]), "g1_failed_checks": [c["name"] for c in g1["checks"] if not c["passed"]], "g1_file": "g1.json", "identity": core.code_identity(), "environment": core.environment()})
    print(json.dumps({"seed_set": seeds.name, "g1_passed": g1["passed"]}))
    return 0 if g1["passed"] else 1


def work_gates(args: argparse.Namespace) -> int:
    """G1 (read from the draw's record), G2 (no-memory baseline at chance), G4, G5 and G6 at real size on the seed set of the mode."""
    run_dir = Path(args.run_dir)
    target = run_dir / "gates.json"
    if target.exists():
        raise FileExistsError(target)
    seeds = seeds_named(args, draw=args.draw)
    study = verified_data(args, seeds, require_manifest=args.mode == REGISTERED and not args.dry)
    backbone = backbone_for(args)
    rows = evaluate.corpus_rows(corpus_bytes(args))
    counts = sorted({DRY_FACTS[s] if args.dry else core.FACTS_PROPORTIONAL[s] for s in core.SLOTS_BY_SIZE})
    controls_rec = evaluate.controls_record(study, {PARENT: backbone}, counts)
    facts = DRY_FACTS[4096] if args.dry else core.FACTS_PROPORTIONAL[4096]
    split = 4 if args.dry else args.restore_split
    init = seeds.facts if is_synthetic(args) or args.mode != REGISTERED else core.INIT_SEEDS[0]
    result = gates.run_g4_g5_g6(study, backbone, mode=args.mode, facts=facts, restore_split=split, out_dir=run_dir / "gate_runs", init_seed=init, rows=rows, unit=unit_of(args))
    manifest_path = manifest_dir(run_dir, seeds.name) / "data_manifest.json"
    g1 = bool(core.read_record(manifest_path, "data_manifest")["g1_passed"]) if manifest_path.is_file() else None
    core.write_record(target, core.jsonable({**core.envelope("gates"), "seed_set": seeds.name, "g1_passed": g1, "g2": controls_rec["g2"], "g2_passed": bool(controls_rec["g2"]["passed"]), "controls": controls_rec, **result, "dry": bool(args.dry), "environment": core.environment(), "identity": core.code_identity()}))
    print(json.dumps({"g4_passed": result["g4_passed"], "g5_passed": result["g5_passed"], "g6_passed": result["g6_passed"], "g2_passed": bool(controls_rec["g2"]["passed"]), "defects": len(result["g4_defects"])}))
    return 0 if result["g4_passed"] and result["g5_passed"] and result["g6_passed"] else 1


def work_train(args: argparse.Namespace) -> int:
    failed = 0
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
    for label in labels_of_args(args):
        cell = core.parse_label(label)
        if cell.stage == 0:
            raise StageError("calibration cells are trained by the calibrate stage")
        seeds = seeds_for_cell(args, cell)
        study = verified_data(args, seeds, require_manifest=not args.dry and args.mode == REGISTERED)
        job = build_job(args, cell, study, core.cell_dir(run_dir, label))
        try:
            record = train.train_cell(job)
            print(json.dumps({"label": label, "status": record["status"]}))
        except Exception as exc:  # the failed record was written by run_job; the others of a group go on
            failed += 1
            print(json.dumps({"label": label, "status": "failed", "reason": type(exc).__name__}))
    return 0 if not failed else 1


def work_evaluate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    rows = evaluate.corpus_rows(corpus_bytes(args))
    failed = 0
    for label in labels_of_args(args):
        cell = core.parse_label(label)
        seeds = seeds_for_cell(args, cell)
        study = verified_data(args, seeds, require_manifest=not args.dry and args.mode == REGISTERED)
        job = build_job(args, cell, study, core.cell_dir(run_dir, label))
        try:
            evaluate.evaluate_cell(cell, run_dir, study, backbone_for(args), facts=facts_for(args, cell), readouts=list(core.stage_readouts(job.stage, job.unit)), init_seed=job.init_seed, r1_seed=job.r1_seed, rows=rows, extra=calibration_binding(args), require_train_record=True)
            print(json.dumps({"label": label, "evaluated": True}))
        except Exception as exc:
            failed += 1
            print(json.dumps({"label": label, "evaluated": False, "reason": type(exc).__name__}))
    return 0 if not failed else 1


def work_calibrate_cell(args: argparse.Namespace) -> int:
    """Train one calibration cell for U updates and score it on its draw's calibration stream (accuracy only). Refuses any other cell."""
    failed = 0
    for label in labels_of_args(args):
        try:
            cell = core.parse_label(label)
        except ValueError as exc:
            raise CalibrationRefused(f"not a calibration cell: {label!r}") from exc
        calibration_guard(cell)
        run_dir = Path(args.run_dir)
        study = study_data(args, seeds_for_cell(args, cell))
        out_dir = core.cell_dir(run_dir, cell.label)
        job = build_job(args, cell, study, out_dir, mode=CALIBRATION, snapshots=(unit_of(args),))
        try:
            record = train.train_cell(job)
        except Exception:
            failed += 1
            continue
        net = model.build_model(cell.arm, cell.slots, job.init_seed, job.backbone, r1_seed=job.r1_seed, seed_rng=False)
        train.load_model_state(out_dir / "snapshots" / core.snapshot_stem(unit_of(args)), net)
        net.eval()
        accuracy = evaluate.calibration_accuracy(net, study, facts_for(args, cell))
        core.write_record(out_dir / "calibration_cell.json", core.jsonable({**core.envelope("calibration"), "label": cell.label, "arm": cell.arm, "value": cell.value, "draw": cell.draw, "accuracy": accuracy, "status": record["status"]}))
        print(json.dumps({"label": cell.label, "status": record["status"]}))
    return 0 if not failed else 1


def finalize_calibration(args: argparse.Namespace, run_dir: Path, cells: Sequence[core.Cell]) -> Path:
    """The rule of section 6 over the calibration cells' records, calibration draws only: per arm, the value with the higher minimum accuracy over the two
    draws; a tie or a difference below 0.02 goes to the earlier median time to first success; then the first value listed."""
    acc: dict[str, float] = {}
    first: dict[str, float] = {}
    a6: dict[int, float] = {}
    for c in cells:
        p = core.cell_dir(run_dir, c.label) / "calibration_cell.json"
        if p.is_file():
            acc[c.label] = core.number(core.read_record(p, "calibration")["accuracy"])
            if c.arm == "A6":
                a6[c.draw] = acc[c.label]
    for c in cells:
        diag = core.cell_dir(run_dir, c.label) / "diagnostics.jsonl"
        if c.label in acc and diag.is_file() and c.draw in a6 and c.arm in core.LEARNED_ARMS:
            u = C.first_success_update(C.probe_points(train.lines_of(diag)), core.SUCCESS_FRACTION_OF_A6 * a6[c.draw])
            first[c.label] = math.inf if u is None else float(u)
    selected: dict[str, float] = {}
    table: dict[str, Any] = {}
    for arm, (name, values) in core.GRID.items():
        per_value_min: dict[float, float] = {}
        per_value_median: dict[float, float] = {}
        for v in values:
            labels = [c.label for c in cells if c.arm == arm and c.value == v]
            accs = [acc[lab] for lab in labels if lab in acc]
            per_value_min[v] = min(accs) if len(accs) == len(labels) and accs else -math.inf
            per_value_median[v] = core.median([first.get(lab, math.inf) for lab in labels])
        selected[arm] = core.select_value(values, per_value_min, per_value_median)
        table[arm] = {"hyperparameter": name, "min_accuracy": {str(v): per_value_min[v] for v in values}, "median_first_success": {str(v): per_value_median[v] for v in values}, "selected": selected[arm]}
    hyper = core.Hyper(selected["A1"], selected["A2"], selected["A4"], selected["A5-D"])
    path = run_dir / "calibration.json"
    if path.exists():
        raise FileExistsError(path)
    core.write_record(path, core.jsonable({**core.envelope("calibration"), "hyper": hyper.as_json(), "table": table, "pipeline_check": {c.label: acc.get(c.label) for c in cells if c.arm in ("A0", "A6", "A7")}, "calibration_accuracy_note": "calibration accuracies are reported as calibration, never as results", "dry": bool(args.dry), "identity": core.code_identity(), "environment": core.environment(), "note": "nothing else may change after calibration (ADR-0019 section 6)"}))
    return path


def stage_for_slots(slots: int) -> int:
    return {4096: 1, 16384: 2, 65536: 3}[slots]


def work_rehearse_cell(args: argparse.Namespace) -> int:
    """One (arm, size, phase) of the matrix for ``--updates`` (256) updates in rehearsal mode (whitelisted record only), then the time of one full evaluation.
    Nothing but time, memory, shapes, counts and identity is written; no loss or accuracy is read out."""
    arm, slots_s, phase = args.item.split(",")
    slots = int(slots_s)
    item = (arm, slots, phase)
    run_dir = Path(args.run_dir)
    st = stage_for_slots(slots)
    cell = core.make_cell(arm, slots, stage=st, draw=1, j=0)
    study = study_data(args, seeds_named(args))
    out_dir = run_dir / "rehearsal" / budget.item_label(item)
    updates = args.updates if args.updates is not None else core.REHEARSAL_UPDATES
    job = build_job(args, cell, study, out_dir, stage=st, mode=REHEARSAL, snapshots=(), max_updates=updates, rehearsal_phase=None if phase == "main" else phase)
    run = train.run_job(job)
    started = time.monotonic()
    rows = evaluate.corpus_rows(corpus_bytes(args))
    evaluate.evaluate_readout(cell, run.model, study, facts_for(args, cell), updates, frozen_backbone=job.backbone, rows=rows, target_seed=job.target_seed)  # discarded
    wall = time.monotonic() - started
    train.write_rehearsal_record(out_dir / "rehearsal_evaluate.json", {**core.envelope("rehearsal"), "label": cell.label, "mode": "rehearsal", "stage": "rehearse-evaluate", "arm": arm, "slots": slots, "phase": phase, "identity": core.code_identity(), "updates": 0, "wall_seconds": wall, "evaluation_wall_seconds": wall, "peak_rss_bytes": train.peak_rss(), "seed_set": study.seeds.name})
    print(json.dumps({"item": budget.item_label(item), "evaluation_seconds": round(wall, 2)}))
    return 0


def finalize_rehearsal(args: argparse.Namespace, run_dir: Path) -> Path:
    """The projection record: rates, coverage, memory headroom, Stage 1 against Budget A's remainder, and the tables for every possible Stage 2 configuration
    and every Stage 3 selected arm (so the Stage 1 gate reads a table and computes nothing new)."""
    trains, evals = [], []
    for item in budget.rehearsal_items():
        folder = run_dir / "rehearsal" / budget.item_label(item)
        if (folder / "rehearsal.json").is_file():
            trains.append(core.read_record(folder / "rehearsal.json", "rehearsal"))
        if (folder / "rehearsal_evaluate.json").is_file():
            e = core.read_record(folder / "rehearsal_evaluate.json", "rehearsal")
            e["label"] = trains[-1]["label"] if trains else e["label"]
            evals.append(e)
    rates = budget.rates_from_records(trains, evals)
    hyper = hyper_of(args)
    unit = unit_of(args)
    missing = budget.missing_items(rates)
    record: dict[str, Any] = {**core.envelope("projection"), "rates": {budget.item_label(i): dataclasses.asdict(r) for i, r in rates.items()}, "missing_items": [budget.item_label(i) for i in missing], "memory": budget.memory_headroom(rates), "hyper": hyper.as_json(), "note": "analytical projections from measured rehearsal rates; no efficiency claim"}
    if not missing:
        remaining = core.Ledger(ledger_root(args) / "P9II-ledger-A.json", "A").remaining()
        p1, d1 = budget.stage1_budget(rates, hyper, remaining, unit)
        record["stage1"] = {"projection": p1._asdict(), "decision": d1._asdict()}
        record["stage2_table"] = budget.stage2_projection_table(rates, hyper, unit)
        record["stage3_table"] = budget.stage3_projection_table(rates, hyper, unit)
    path = run_dir / "projection.json"
    if path.exists():
        raise FileExistsError(path)
    core.write_record(path, core.jsonable(record))
    return path


def work_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "analysis.json"
    if target.exists():
        raise FileExistsError(target)
    unit = unit_of(args)
    manifests = [read_json(p) for p in sorted(run_dir.glob("*/manifest.json"))]
    failed = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"] if t["status"] != "completed")
    gates_path = run_dir / "gates.json"
    gates_rec = core.read_record(gates_path, "gates") if gates_path.is_file() else None
    sd1 = analysis.load_stage(run_dir, 1, stage_cells(args, 1), unit, [f for f in failed if f.startswith(("train1", "evaluate1"))])
    stage2 = stage3 = None
    s2_not_run = s3_not_run = selected = None
    advancing_path = run_dir / "stage_gate_1.json"
    if args.dry and args.dry_advancing:
        stage2 = analysis.load_stage(run_dir, 2, core.stage2_cells(args.dry_advancing.split(",")), unit, [f for f in failed if "2:" in f or f.startswith(("train2", "evaluate2"))])
    elif advancing_path.is_file():
        rec = core.read_record(advancing_path, "stage_gate")
        if rec["run"] and (run_dir / "train2" / "manifest.json").is_file():
            stage2 = analysis.load_stage(run_dir, 2, core.stage2_cells(rec["advancing"]), unit, [f for f in failed if f.startswith(("train2", "evaluate2"))])
        elif not rec["run"] or not (run_dir / "train2" / "manifest.json").is_file():
            s2_not_run = rec["status"] if not rec["run"] else C.NOT_RUN_BUDGET
    g3 = run_dir / "stage_gate_3.json"
    if args.dry and args.dry_selected:
        selected = args.dry_selected
        stage3 = analysis.load_stage(run_dir, 3, core.stage3_cells(selected), unit, [f for f in failed if f.startswith(("train3", "evaluate3"))])
    elif g3.is_file():
        rec3 = core.read_record(g3, "stage_gate")
        if rec3["run"] and (run_dir / "train3" / "manifest.json").is_file():
            selected = rec3["selected"]
            stage3 = analysis.load_stage(run_dir, 3, core.stage3_cells(selected), unit, [f for f in failed if f.startswith(("train3", "evaluate3"))])
        else:
            s3_not_run = rec3["status"]
    result = analysis.analyze_study(sd1, stage2, stage3, stage2_not_run=s2_not_run, stage3_not_run=s3_not_run, stage3_selected=selected, gates=gates_rec, failed_tasks=failed)
    plan_path = run_dir / "draw_plan.json"
    core.write_record(target, core.jsonable({**core.envelope("analysis"), "dry": bool(args.dry), "unit_updates": unit, "result": result, "draw_plan": core.read_record(plan_path, "draw_plan") if plan_path.is_file() else None, "calibration": calibration_binding(args), "identity": core.code_identity(), "environment": core.environment()}))
    print(json.dumps({"status": result["assessment"]["status"], "outcome": result["outcome"]["outcome"]}))
    return 0


def work_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise FileExistsError(out / "results.json")
    paths = report.write_report(run_dir, out, banner=DRY_BANNER if args.dry else None)
    print(json.dumps({"written": [p.name for p in paths]}))
    return 0


WORKERS: dict[str, Any] = {
    "generate": work_generate, "gates": work_gates, "train": work_train, "evaluate": work_evaluate, "analyze": work_analyze, "report": work_report,
    "calibrate-cell": work_calibrate_cell, "rehearse-cell": work_rehearse_cell,
}  # fmt: skip


# --- commands --------------------------------------------------------------------------------------------------------------------------------
def new_run_dir(args: argparse.Namespace, stage: str) -> Path:
    run_dir = Path(args.run_dir) if args.run_dir else experiments_root(args) / core.run_name(stage)
    args.run_dir = str(run_dir)
    return run_dir


def single(stage: str, ledger_stage: str, worker: str, args: argparse.Namespace, run_dir: Path, result: Path, extra: Sequence[str] = (), *, skip_preconditions: bool = False, cap: float | None = None) -> dict[str, Any]:
    task = make_task(stage, stage, worker_argv(worker, *common_args(args), *extra), run_dir, core.code_identity(), result)
    return run_stage_tasks(stage, ledger_stage, args, [task], run_dir, cap=stage_cap(args, cap), workers=1, skip_preconditions=skip_preconditions)


def cmd_generate(args: argparse.Namespace) -> int:
    if args.mode == REGISTERED and not args.i_understand_freeze_time:
        raise pool.StageRefused("refused: registered-seed generation is used at freeze time; add --i-understand-freeze-time")
    run_dir = new_run_dir(args, "generate")
    seeds = seeds_named(args, reserve=args.reserve)
    if (manifest_dir(run_dir, seeds.name) / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {seeds.name} is already generated in {run_dir}")
    name = f"generate-{seeds.name}"
    manifest = single(name, "generate", "generate", args, run_dir, manifest_dir(run_dir, seeds.name) / "data_manifest.json", skip_preconditions=True)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_draw_plan(args: argparse.Namespace) -> int:
    """Section 9: the plan of which seed set serves each draw slot, from the G1 records of the sixteen generated draws (a pure function)."""
    run_dir = Path(args.run_dir)
    g1: dict[str, bool] = {}
    for name in (*core.DRAW_NAMES, *core.RESERVE_NAMES):
        p = manifest_dir(run_dir, name) / "data_manifest.json"
        if p.is_file():
            g1[name] = bool(core.read_record(p, "data_manifest")["g1_passed"])
    plan = core.plan_draws(g1)
    core.write_record(run_dir / "draw_plan.json", {**core.envelope("draw_plan"), "ok": plan.ok, "seed_set_of": {str(k): v for k, v in plan.seed_set_of.items()}, "replacements": {str(k): v for k, v in plan.replacements.items()}, "reason": plan.reason, "g1": g1})
    print(json.dumps({"ok": plan.ok, "replacements": plan.replacements, "reason": plan.reason}))
    return 0 if plan.ok else 1


def cmd_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("gates", "gates", "gates", args, run_dir, run_dir / "gates.json", ["--restore-split", str(args.restore_split)])
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_calibrate(args: argparse.Namespace) -> int:
    args.mode = CALIBRATION
    run_dir = new_run_dir(args, "calibrate")
    cells = core.calibration_cells()
    for c in cells:
        calibration_guard(c)
    identity = core.code_identity()
    tasks = [make_task("calibrate", c.label, worker_argv("calibrate-cell", "--labels", c.label, *common_args(args)), run_dir, identity, core.cell_dir(run_dir, c.label) / "calibration_cell.json") for c in cells]
    manifest = run_stage_tasks("calibrate", "calibrate", args, tasks, run_dir, cap=stage_cap(args))
    path = finalize_calibration(args, run_dir, cells)
    print(json.dumps({"calibration": str(path)}))
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_rehearse(args: argparse.Namespace) -> int:
    args.mode = REHEARSAL
    run_dir = new_run_dir(args, "rehearse")
    identity = core.code_identity()
    items = budget.rehearsal_items()
    if args.dry:
        items = [i for i in items if i[1] == 4096]
    tasks = [make_task("rehearse", budget.item_label(i), worker_argv("rehearse-cell", "--item", ",".join(map(str, i)), *common_args(args)), run_dir, identity, run_dir / "rehearsal" / budget.item_label(i) / "rehearsal_evaluate.json") for i in items]
    manifest = run_stage_tasks("rehearse", "rehearse", args, tasks, run_dir, cap=stage_cap(args))
    print(json.dumps({"projection": str(finalize_rehearsal(args, run_dir))}))
    return 0 if manifest["status"] == "COMPLETE" else 1


def run_cells_stage(args: argparse.Namespace, stage: int, *, cap_train: float | None = None, cap_eval: float | None = None) -> int:
    """Train then evaluate the cells of a stage, charged to the stage's budget."""
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
    cells = stage_cells(args, stage)
    ledger_stage = f"stage{stage}"
    tasks, _ = cell_tasks(f"train{stage}", "train", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "train.json")
    m1 = run_stage_tasks(f"train{stage}", ledger_stage, args, tasks, run_dir, cap=stage_cap(args, cap_train))
    tasks2, completed = cell_tasks(f"evaluate{stage}", "evaluate", args, cells, run_dir, lambda c: core.eval_path(run_dir, c.label, core.decisive_readout(stage, unit_of(args))), previous=f"train{stage}")
    m2 = run_stage_tasks(f"evaluate{stage}", ledger_stage, args, tasks2, run_dir, cap=stage_cap(args, cap_eval), completed_ids=completed)
    return 0 if m1["status"] == "COMPLETE" and m2["status"] == "COMPLETE" else 1


def cmd_train(args: argparse.Namespace) -> int:
    return run_cells_stage(args, args.stage)


def cmd_stagegate(args: argparse.Namespace) -> int:
    """The Stage 1 gate (``--after 1``) or the Stage 3 gate (``--after 2``): a pure function of the stage's records and of the frozen projection table; the
    arms of the later stage are never chosen by hand. Written once as ``stage_gate_<n>.json``."""
    run_dir = Path(args.run_dir)
    unit = unit_of(args)
    after = args.after
    target = run_dir / ("stage_gate_1.json" if after == 1 else "stage_gate_3.json")
    if target.exists():
        raise pool.StageRefused(f"refused: {target} exists; a gate is computed once")
    projection = core.read_record(Path(args.projection), "projection") if args.projection else None
    remaining_b = core.Ledger(ledger_root(args) / "P9II-ledger-B.json", "B").remaining()
    sd = analysis.load_stage(run_dir, after, core.stage1_cells() if after == 1 else core.stage2_cells(_advancing_of(run_dir, args)), unit)
    record: dict[str, Any] = {**core.envelope("stage_gate"), "after_stage": after, "environment": core.environment()}
    if sd.missing() or sd.failed_tasks:
        record.update(run=False, status="NOT RUN — STAGE NOT INTERPRETABLE", advancing=[], arms=[], reason=f"cells missing or failed: {sd.missing()[:5]}")
    elif after == 1:
        r = analysis.analyze_stage(sd)
        gate = C.stage1_gate(r.classes, r.size.negative_control_failed)
        record.update(run=gate.run, status=None if gate.run else C.NOT_RUN_NO_ARM, advancing=gate.advancing, arms=gate.arms, classes={a: c.label for a, c in r.classes.items()}, negative_control_failed=r.size.negative_control_failed)
        if gate.run and projection is not None:
            decision = budget.stage2_decision(gate.advancing, projection["stage2_table"], remaining_b)
            record["budget"] = decision._asdict()
            if not decision.run:
                record.update(run=False, status=budget.NOT_RUN_BUDGET)
    else:
        r = analysis.analyze_stage(sd)
        selected, action, status = C.stage3_gate(r.classes, r.size.negative_control_failed, C.COMPLETE)
        record.update(run=action == "run", status=status, selected=selected, classes={a: c.label for a, c in r.classes.items()}, negative_control_failed=r.size.negative_control_failed)
        if action == "run" and selected is not None and projection is not None:
            decision = budget.stage3_decision(selected, projection["stage3_table"], remaining_b)
            record["budget"] = decision._asdict()
            if not decision.run:
                record.update(run=False, status=budget.NOT_RUN_BUDGET)
    core.write_record(target, core.jsonable(record))
    print(json.dumps({"gate": after, "run": record["run"], "status": record["status"]}))
    return 0


def _advancing_of(run_dir: Path, args: argparse.Namespace) -> list[str]:
    if args.dry and args.dry_advancing:
        return cast(list[str], args.dry_advancing.split(","))
    return cast(list[str], core.read_record(run_dir / "stage_gate_1.json", "stage_gate")["advancing"])


def cmd_evaluate(args: argparse.Namespace) -> int:
    raise pool.StageRefused("refused: evaluation runs inside `train` (train then evaluate, one stage, one ledger)")


def cmd_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("analyze", "analyze", "analyze", args, run_dir, run_dir / "analysis.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise pool.StageRefused("refused: the report runs once and never overwrites")
    manifest = single("report", "report", "report", args, run_dir, out / "results.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


# --- the registered driver (called by the fixed launch scripts) ---------------------------------------------------------------------------------
def load_plan(repo: Path) -> dict[str, Any]:
    """The frozen plan: stage caps, the calibration record and the projection record with their sha256. Absent before the freeze: nothing registered then runs."""
    path = repo / FREEZE_PLAN
    if not path.is_file():
        raise pool.StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise pool.StageRefused("refused: the freeze plan is not an object")
    return plan


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name (``REGISTERED_STAGES``), with everything else (caps, calibration, projection, seeds) from the frozen plan. The only free
    arguments are the run directory and the freeze commit; the launch scripts pass nothing else."""
    if args.name not in REGISTERED_STAGES:
        raise pool.StageRefused(f"refused: unknown registered stage {args.name!r}")
    args.mode = REGISTERED
    repo = repo_of(args)
    check_preconditions(REGISTERED, repo, args.freeze_commit)
    plan = load_plan(repo)
    caps = read_json(repo / args.caps) if args.caps else plan["caps"]
    for key in ("calibration", "projection"):
        entry = plan[key]
        if file_sha256(Path(entry["path"])) != entry["sha256"]:
            raise pool.StageRefused(f"refused: {entry['path']} does not hash to the frozen {key} record")
    args.calibration = plan["calibration"]["path"]
    args.projection = plan["projection"]["path"]
    args.workers = core.WORKERS
    name = args.name
    if name == "gates":
        args.stage_cap_seconds = caps["gates"]
        return cmd_gates(args)
    if name == "stage1_gate":
        args.after = 1
        return cmd_stagegate(args)
    if name == "stage3_gate":
        args.after = 2
        return cmd_stagegate(args)
    if name in ("stage1", "stage2", "stage3"):
        stage = int(name[-1])
        if stage == 1:
            _, decision = budget.stage1_budget(rates_of(args), hyper_of(args), core.Ledger(ledger_root(args) / "P9II-ledger-A.json", "A").remaining())
            if not decision.run:
                raise pool.StageRefused(f"refused: {budget.NOT_RUN_BUDGET}: twice the Stage 1 projection ({decision.required_seconds:.0f} s) exceeds what remains ({decision.remaining_seconds:.0f} s); nothing registered is run")
        return run_cells_stage(args, stage, cap_train=float(caps[name]["train"]), cap_eval=float(caps[name]["evaluate"]))
    args.stage_cap_seconds = caps[name]
    return cmd_analyze(args) if name == "analysis" else cmd_report(args)


def rates_of(args: argparse.Namespace) -> budget.Rates:
    projection = core.read_record(Path(args.projection), "projection")
    return {_parse_item(k): budget.Rate(float(v["seconds_per_update"]), int(v["peak_rss_bytes"]), int(v["sampled_rss_bytes"]), float(v["evaluation_seconds"])) for k, v in projection["rates"].items()}


def _parse_item(label: str) -> budget.Item:
    _, arm_slots_phase = label.split("-", 1)
    arm, rest = arm_slots_phase.rsplit("-n", 1)
    slots, phase = rest.split("-", 1)
    return (arm, int(slots), phase)


# --- the DRY stage ---------------------------------------------------------------------------------------------------------------------------------
def cmd_dry(args: argparse.Namespace) -> int:
    """Every stage, in order, at tiny size on test seeds in a temporary root, with private ledgers: generate, calibrate, gates, rehearse (4,096 slots), Stage 1
    (128 cells at 8 updates), the Stage 1 gate, Stage 2 and Stage 3 (arms named by ``--dry-advancing`` / ``--dry-selected``), analysis and report."""
    root = Path(args.out_root) if args.out_root else Path(tempfile.mkdtemp(prefix="p9ii-dry-"))
    run_dir = root / "P9IIDRY-run"
    if run_dir.exists():
        raise pool.StageRefused(f"refused: {run_dir} exists")
    shared = ["--dry", "--experiments-root", str(root), "--ledger-root", str(root), "--workers", str(args.workers), "--stage-cap-seconds", str(args.stage_cap_seconds or 3600)]
    base = [*shared, "--run-dir", str(run_dir), "--mode", CALIBRATION]
    adv, sel = args.dry_advancing, args.dry_selected
    extra = [*(["--dry-advancing", adv] if adv else []), *(["--dry-selected", sel] if sel else [])]
    steps: list[tuple[str, list[str]]] = [
        ("generate", ["generate", *base]),
        ("calibrate", ["calibrate", *shared, "--run-dir", str(root / "P9IIDRY-calibration")]),
        ("gates", ["gates", *base]),
        ("rehearse", ["rehearse", *shared, "--run-dir", str(root / "P9IIDRY-rehearsal")]),
        ("stage1", ["train", *base, "--stage", "1"]),
        ("stagegate1", ["stagegate", *base, "--after", "1", *extra]),
    ]
    if adv:
        steps += [("stage2", ["train", *base, "--stage", "2", *extra]), ("stagegate3", ["stagegate", *base, "--after", "2", *extra])]
    if sel:
        steps.append(("stage3", ["train", *base, "--stage", "3", *extra]))
    steps += [("analyze", ["analyze", *base, *extra]), ("report", ["report", *base, *extra])]
    summary: dict[str, Any] = {"run_dir": str(run_dir), "banner": DRY_BANNER, "stages": {}}
    for name, argv in steps:
        code = main(argv)
        summary["stages"][name] = code
        if name in ("generate", "gates") and code != 0:
            break
    analysis_path = run_dir / "analysis.json"
    if analysis_path.is_file():
        data = core.read_record(analysis_path, "analysis")
        summary["status"] = data["result"]["assessment"]["status"]
        summary["outcome"] = data["result"]["outcome"]["outcome"]
    summary["report"] = str(run_dir / "results" / "RESULTS.md") if (run_dir / "results" / "results.json").is_file() else None
    summary["charged_seconds"] = {b: core.Ledger(root / f"P9II-ledger-{b}.json", b).charged() for b in ("A", "B")}
    write_json(root / "DRY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["report"] else 1


# --- command line ------------------------------------------------------------------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--run-dir", default=None)
    p.add_argument("--experiments-root", default=None)
    p.add_argument("--ledger-root", default=None, help="directory of the two ledgers (default: the experiments root)")
    p.add_argument("--repo", default=None, help="repository to check for a registered stage (tests)")
    p.add_argument("--mode", choices=(REGISTERED, CALIBRATION, REHEARSAL), default=None)
    p.add_argument("--draw", type=int, default=1, help="registered draw 1-14, or calibration set 3 or 4")
    p.add_argument("--reserve", type=int, default=None, help="registered reserve draw 1 or 2")
    p.add_argument("--dry", action="store_true", help="the DRY profile (tiny sizes, test seeds; never registered)")
    p.add_argument("--synthetic-backbone", action="store_true", help="random stand-in backbone (DRY and tests only)")
    p.add_argument("--stage", type=int, choices=(1, 2, 3), default=1)
    p.add_argument("--after", type=int, choices=(1, 2), default=1)
    p.add_argument("--updates", type=int, default=None, help="rehearsal updates")
    p.add_argument("--freeze-commit", default=None)
    p.add_argument("--caps", default=None, help="stage caps file of the freeze (fixed in the launch scripts)")
    p.add_argument("--calibration", default=None, help="calibration record (the calibrated values)")
    p.add_argument("--calibration-sha256", default=None)
    p.add_argument("--projection", default=None, help="projection record of the rehearsal")
    p.add_argument("--workers", type=int, default=core.WORKERS)
    p.add_argument("--stage-cap-seconds", type=float, default=None)
    p.add_argument("--rss-worker-bytes", type=int, default=core.RSS_WORKER_BYTES)
    p.add_argument("--rss-aggregate-bytes", type=int, default=core.RSS_AGGREGATE_BYTES)
    p.add_argument("--only", action="append", default=None, help="restrict a stage to these cell labels")
    p.add_argument("--labels", default=None, help="worker commands: comma-separated cell labels")
    p.add_argument("--item", default=None, help="rehearse-cell: arm,slots,phase")
    p.add_argument("--restore-split", type=int, default=16)
    p.add_argument("--results-dir", default=None)
    p.add_argument("--dry-advancing", default=None, help="DRY only: arms of Stage 2 (comma-separated)")
    p.add_argument("--dry-selected", default=None, help="DRY only: the selected arm of Stage 3")
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p9ii.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", parents=[common])
    gen.add_argument("--i-understand-freeze-time", action="store_true")
    for name in ("draw-plan", "calibrate", "rehearse", "gates", "train", "stagegate", "analyze", "report"):
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
    "generate": cmd_generate, "draw-plan": cmd_draw_plan, "calibrate": cmd_calibrate, "rehearse": cmd_rehearse, "gates": cmd_gates, "train": cmd_train,
    "stagegate": cmd_stagegate, "analyze": cmd_analyze, "report": cmd_report, "registered": cmd_registered, "dry": cmd_dry,
}  # fmt: skip
DEFAULT_MODE = {"generate": CALIBRATION, "calibrate": CALIBRATION, "rehearse": REHEARSAL}


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
        elif args.run_dir is None and args.command not in ("calibrate", "rehearse", "generate"):
            raise StageError("--run-dir is required")
        return int(COMMANDS[args.command](args))
    except (pool.StageRefused, core.LedgerRefused) as exc:
        print(f"P9II stage REFUSED: {exc}", file=sys.stderr)
        return 2
    except CalibrationRefused as exc:
        print(f"P9II calibration REFUSED: {exc}", file=sys.stderr)
        return 2
    except StageError as exc:
        print(f"P9II stage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
