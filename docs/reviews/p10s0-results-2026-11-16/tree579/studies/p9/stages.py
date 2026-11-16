# ruff: noqa: E501
"""P9 command-line driver (package I7): the single entry point of every stage.

Run from the repository root as ``uv run --locked python -m studies.p9.stages <command> ...``.

Commands (each runs through ``pool``: stage manifest, worker semaphores, RSS and time limits, failed
records kept, the dependent-cell stop rule, one manifest per stage written once and never overwritten):

* ``generate``   build ``StudyData``, write stream hashes and run gate G1; writes ``data_manifest.json``.
  A rehearsal draw (``--rehearsal-draw K``) is the default use before the freeze; registered-seed
  generation needs the separate explicit flag ``--registered-seeds`` (used at freeze time).
* ``calibrate``  ADR 12 step 4 on a REHEARSAL draw only: frozen-hidden probes, R2 learning curves at
  E = 32 / 64 / 128, no-memory and exact controls with G2, attainable answer probability, then
  ``core.select_exposure``. It refuses to build or train any arm other than R2 (``CalibrationRefused``).
* ``rehearse``   ADR 12 step 5 on a rehearsal draw: timing and memory of one cell of each kind for a small
  fixed number of updates, one evaluation and one simulation, a worker-contention measurement, and the
  projection table. Records are written only through ``train.write_rehearsal_record`` (time, RSS,
  finiteness, shapes): no loss or accuracy value is computed into any record, stdout, or log.
* ``gates``      gate G4 (P5 forward invariance on the real backbones, checkpoint restoration) -> ``g4.json``.
* ``train``, ``evaluate``, ``simulate``  the registered stages (``--dry`` for the DRY profile).
* ``analyze``, ``report``  run once; refuse to overwrite.
* ``dry``        everything at tiny size on test seeds in a temporary root. Outputs are marked DRY; the
  numbers mean nothing. Reduced registry: see ``dry_scope_labels``.

A ``registered`` stage refuses unless the working tree is clean and ``--freeze-commit`` names an ancestor
commit that equals HEAD on the P9 package, config, specification and tests (``pool.check_preconditions``).
Every stage is idempotent by refusal: it never overwrites an existing manifest or record.

Hidden ``work <name>`` subcommands are the worker processes the pool launches; they print only status
facts, never a loss or an accuracy of a compared arm.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import argparse
import contextlib
import dataclasses
import functools
import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import psutil

from arborlm.io import file_sha256, read_json, write_json

from . import (
    analysis_a,
    controls,
    core,
    evaluate,
    incremental,
    model,
    pool,
    report,
    sim,
    train,
)
from . import data as data_mod
from .core import Cell, ClassResult

REGISTERED, CALIBRATION, REHEARSAL = "registered", "calibration", "rehearsal"
DRY_BANNER = (
    "DRY RUN: plumbing only (tiny sizes, test seeds, no meaning in any number); "
    "not a calibration, a rehearsal or a registered result."
)
DRY_DRAW = 90  # rehearsal-namespace draw of the DRY profile: seeds 179001 + 9000 + i
DRY_SIZES = data_mod.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
DRY_G1_PERMUTATIONS = 200
SYNTHETIC_CORPUS = bytes(range(256)) * 8  # a stand-in for the training bytes (synthetic backbone only)
REHEARSAL_DEFAULT_UPDATES = 64
CONTENTION_WORKERS = (1, 2, 4, 8)
CONTENTION_CELL = "A1-flat-R0-n16384-b101-o301-s1701"
EVAL_CELLS = (
    "A1-flat-R0-n4096-b101-o301-s1701",
    "A1-flat-R0-n16384-b101-o301-s1701",
    "A1-flat-R0-n65536-b101-o301-s1701",
    "A2-tree-R0-n16384-b101-o301-s1701",
)
PROJECTION_EXPOSURES = (32, 64, 128)
PROJECTION_WORKERS = (2, 4, 6, 8)
STAGE_ORDER_BLOCKS = ("A5", "A1", "A2", "A3", "A4", "A5b", "A6", "A7", "A8", "A10", "D1", "B1", "C1", "D2")
FORBIDDEN_IN_REHEARSAL_OUTPUT = train._FORBIDDEN_WORDS  # words no rehearsal file may contain


class CalibrationRefused(RuntimeError):
    """The calibration was asked to build or train an arm other than R2 (ADR 12 step 4)."""


class StageError(RuntimeError):
    """A stage cannot start for a reason other than a pool refusal (missing upstream record, ...)."""


# --- the calibration guard -----------------------------------------------------------------------------------
def calibration_guard(cell: Cell) -> None:
    """ADR 12 step 4: allowed are the R2 readout rung and the controls; not allowed are any R0, R0a, R1,
    tree, dense or regularized arm. Called by every calibration entry point before anything is built."""
    allowed = (
        cell.rung == "R2"
        and cell.arch == "flat"
        and cell.alpha_u == 0.0
        and cell.alpha_c == 0.0
        and cell.optimizer == core.ADAMW
        and not cell.is_lane_d
    )
    if not allowed:
        raise CalibrationRefused(
            f"the calibration builds and trains only R2 cells and controls (ADR 12 step 4); refused: {cell.label}"
        )


# --- options, data and backbones --------------------------------------------------------------------------
def _seeds(args: argparse.Namespace) -> core.SeedSet:
    """Registered seeds only in ``registered`` mode (never with a synthetic backbone or the DRY profile);
    every other mode uses a rehearsal-namespace draw, each of whose seeds is checked."""
    if args.mode == REGISTERED:
        if args.dry or args.synthetic_backbone:
            raise pool.StageRefused("refused: registered seeds with the DRY profile or a synthetic backbone")
        return core.registered_seeds()
    seeds = core.rehearsal_seeds(args.draw)
    for value in (*seeds.data_values(), *seeds.null_seeds_a, *seeds.null_seeds_b):
        core.assert_not_registered_seed(value)
    return seeds


def init_seed_of(cell: Cell, study: data_mod.StudyData, mode: str) -> int | None:
    """Initialization seed of a cell: ``None`` (the registered 1701 / 1702) in a registered run, else a
    rehearsal-namespace seed that keeps the cell's seed offset (so the two seeds of a calibration or
    DRY cell still differ)."""
    if mode == REGISTERED:
        return None
    return study.seeds.facts + (cell.seed - core.INIT_SEEDS[0])


def _experiments_root(args: argparse.Namespace) -> Path:
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def study_data(args: argparse.Namespace) -> data_mod.StudyData:
    """The draw of ``args`` (registered seeds, a rehearsal draw, or the tiny DRY sizes). Deterministic."""
    corpus = (
        SYNTHETIC_CORPUS if args.synthetic_backbone else core.load_trained_corpus(_experiments_root(args))
    )
    return data_mod.build_study_data(_seeds(args), corpus, sizes=DRY_SIZES if args.dry else None)


@functools.cache
def _synthetic(parent: tuple[int, int]) -> Any:
    return controls.synthetic_backbone(*parent)


def backbone_for(args: argparse.Namespace, parent: tuple[int, int]) -> Any:
    """The verified frozen parent (or, with ``--synthetic-backbone``, a random full-size stand-in)."""
    if args.synthetic_backbone:
        return _synthetic(parent)
    return controls.load_backbone(parent, _experiments_root(args))[0]


def verified_data(args: argparse.Namespace, *, require_manifest: bool) -> data_mod.StudyData:
    """``study_data`` checked against the stream hashes of ``<run>/data_manifest.json``."""
    study = study_data(args)
    path = Path(args.run_dir) / "data_manifest.json"
    if path.is_file():
        recorded = read_json(path)["sha256s"]
        if recorded != study.sha256s():
            raise StageError(f"regenerated data differ from the hashes in {path}")
    elif require_manifest:
        raise StageError(f"no data manifest at {path}: run generate first")
    return study


def _exposure(args: argparse.Namespace) -> int:
    value = int(args.exposure) if args.exposure is not None else core.DEFAULT_EXPOSURE
    if value not in core.EXPOSURE_MENU:
        raise StageError(f"exposure {value} is not in the menu {core.EXPOSURE_MENU}")
    return value


def read_exposure(args: argparse.Namespace) -> int:
    """The run's exposure: ``<run>/exposure.json`` (written by ``train``), checked against ``--exposure``."""
    path = Path(args.run_dir) / "exposure.json"
    if not path.is_file():
        raise StageError(f"no {path}: run train first")
    recorded = int(read_json(path)["exposure"])
    if args.exposure is not None and int(args.exposure) != recorded:
        raise StageError(f"--exposure {args.exposure} differs from the run's recorded exposure {recorded}")
    return recorded


# --- cell selection -----------------------------------------------------------------------------------------
def dry_scope_labels(scope: str) -> list[str]:
    """The DRY registry (open choice of package I7, documented in the report):

    * ``full``    all 100 registered cells with tiny facts (``core.DRY_FACTS``).
    * ``reduced`` one cell per configuration: every distinct (block, arch, rung, slots, key width, track,
      optimizer, doses, Lane D arm) kept once, as its B101 seed-1701 cell (the second seed and the B102
      replicate are dropped). That is one cell per block, rung and arm at each size (47 of the 100), so
      the 4,096-, 16,384- and 65,536-slot code paths all run.
    * ``lane_d``  the 20 Lane D cells (D1 and D2, both seeds), for the dependent-cell stop test.
    * ``smoke``   eleven cells (one per record kind) for the integration tests.
    """
    cells = core.cells()
    if scope == "full":
        return [c.label for c in cells]
    if scope == "lane_d":
        return [c.label for c in cells if c.lane == "D"]
    if scope == "smoke":  # the tests' scope: every record kind in about a dozen cells
        wanted = {
            ("A1", "flat", 4096, "R0", None),
            ("A1", "flat", 16384, "R0", None),
            ("A2", "learned_tree", 16384, "R0", None),
            ("A5", "flat", 4096, "R2", None),
            ("A6", "learned_tree", 16384, "OB", None),
            ("A8", "dense", 16384, "R0", None),
            ("B1", "flat", 16384, "R0", None),
            ("C1", "flat", 16384, "R0", None),
            ("D1", "flat", 16384, "R0", "phaseA"),
            ("D2", "flat", 16384, "R0", "sequential"),
            ("D2", "flat", 16384, "R0", "joint"),
        }
        return [
            c.label
            for c in cells
            if (c.block, c.arch, c.slots, c.rung, c.lane_d_arm) in wanted
            and c.parent == core.PRIMARY_PARENT
            and c.seed == core.INIT_SEEDS[0]
            and (c.block not in ("B1", "C1") or (c.alpha_u == 0.25 and c.alpha_c in (0.0, 0.05)))
            and (c.block != "B1" or c.alpha_c == 0.0)
        ]
    if scope != "reduced":
        raise ValueError(f"unknown DRY scope {scope!r}")
    seen: set[tuple[Any, ...]] = set()
    out: list[str] = []
    for c in cells:
        key = (c.block, c.arch, c.rung, c.slots, c.key_width, c.track, c.optimizer, c.alpha_u, c.alpha_c, c.lane_d_arm)
        if key in seen or c.parent != core.PRIMARY_PARENT or c.seed != core.INIT_SEEDS[0]:
            continue
        seen.add(key)
        out.append(c.label)
    return out


def order_cells(cells: Sequence[Cell]) -> list[Cell]:
    """Launch order (EXECUTION_PLAN phase 3): R2 diagnostics first, then Lane A smallest size first with
    Lane D phase A early (so its dependants can start), Lane B and C, then phase B."""
    def key(c: Cell) -> tuple[int, int, int]:
        block_rank = STAGE_ORDER_BLOCKS.index(c.block)
        r2_first = 0 if c.rung == "R2" else 1
        return (r2_first, c.slots if c.block not in ("D1", "D2") else 0, block_rank * 1000 + c.index)

    return sorted(cells, key=key)


def select_cells(args: argparse.Namespace, *, only: Callable[[Cell], bool] | None = None) -> list[Cell]:
    chosen = core.cells()
    if args.dry and getattr(args, "scope", None):
        keep = set(dry_scope_labels(args.scope))
        chosen = [c for c in chosen if c.label in keep]
    if getattr(args, "block", None):
        chosen = [c for c in chosen if c.block in args.block]
    if getattr(args, "only", None):
        chosen = [c for c in chosen if c.label in args.only]
    if only is not None:
        chosen = [c for c in chosen if only(c)]
    return order_cells(chosen)


def calibration_record_of(args: argparse.Namespace) -> dict[str, Any] | None:
    path = getattr(args, "calibration", None)
    return None if not path else dict(read_json(Path(path)))


def excluded_for_ceiling(cells: Sequence[Cell], calibration: dict[str, Any] | None) -> tuple[list[Cell], list[dict[str, Any]]]:
    """TASK_CEILING_FAIL sizes are not run (ADR 8.1 G3); if 16,384 fails Lanes B, C (trained part) and D
    are not run either. The exclusions are recorded in ``<run>/<stage>/exclusions.json``; the registered
    denominator is not reduced (the report lists the cells as missing)."""
    fail = set(analysis_a.ceiling_fail_sizes(calibration))
    kept: list[Cell] = []
    dropped: list[dict[str, Any]] = []
    for c in cells:
        reason = None
        if c.slots in fail:
            reason = f"TASK_CEILING_FAIL({c.slots})"
        elif 16384 in fail and c.lane in ("B", "C", "D"):
            reason = "TASK_CEILING_FAIL(16384) removes Lanes B, C (trained part) and D"
        if reason:
            dropped.append({"label": c.label, "reason": reason})
        else:
            kept.append(c)
    return kept, dropped


# --- running a stage through the pool -------------------------------------------------------------------------
def _repo(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def _pool_mode(args: argparse.Namespace) -> str:
    return REGISTERED if args.mode == REGISTERED else (REHEARSAL if getattr(args, "rehearse", False) else CALIBRATION)


def _caps(args: argparse.Namespace, default_hours: float | None) -> pool.StageCaps:
    seconds = args.stage_cap_seconds
    if seconds is None:
        if args.mode == REGISTERED or default_hours is None:
            raise pool.StageRefused("refused: --stage-cap-seconds is required (caps are fixed at decision 2)")
        seconds = default_hours * 3600.0
    return pool.StageCaps(float(seconds), args.rss_worker_bytes, args.rss_aggregate_bytes)


def _worker_counts(args: argparse.Namespace) -> dict[str, int]:
    return {
        "train": args.train_workers,
        "evaluate": args.train_workers,
        "simulate": args.sim_workers,
        "analyze": 1,
    }


def common_args(args: argparse.Namespace, run_dir: Path | None = None) -> list[str]:
    """The options every worker needs to rebuild the same draw (never a scientific value)."""
    out = [
        "--run-dir", str(run_dir or args.run_dir),
        "--mode", args.mode,
        "--draw", str(args.draw),
        "--experiments-root", str(_experiments_root(args)),
    ]  # fmt: skip
    if args.dry:
        out.append("--dry")
    if args.synthetic_backbone:
        out.append("--synthetic-backbone")
    return out


def _task(
    stage: str,
    label: str,
    argv: Sequence[str],
    run_dir: Path,
    identity: core.Identity,
    result_path: Path,
    *,
    depends_on: Sequence[str] = (),
) -> pool.Task:
    pool.validate_worker_argv(argv)
    folder = run_dir / stage
    return pool.Task(
        task_id=pool.task_id(stage, label, identity),
        stage=stage,
        label=label,
        argv=tuple(argv),
        depends_on=tuple(depends_on),
        after=(),
        group=pool.STAGE_GROUP[stage],
        result_path=result_path,
        failed_path=folder / f"{label}.failed.json",
        log_path=folder / f"{label}.log",
    )


def run_tasks(
    stage: str,
    args: argparse.Namespace,
    tasks: Sequence[pool.Task],
    run_dir: Path,
    *,
    workers: dict[str, int] | None = None,
    default_hours: float | None = None,
    completed_ids: Sequence[str] = (),
    manifest_dir: Path | None = None,
) -> core.StageManifest:
    """Preconditions (registered: clean tree, freeze commit), then the pool, then the manifest."""
    mode = _pool_mode(args)
    pool.check_preconditions(mode, _repo(args), args.freeze_commit)
    counts = workers or _worker_counts(args)
    pool.validate_workers(mode, counts)
    manifest, path = pool.execute_tasks(
        stage,
        mode,
        tasks,
        run_dir,
        core.code_identity(),
        workers=counts,
        caps=_caps(args, default_hours),
        completed_ids=list(completed_ids),
        env={"PYTHONPATH": str(core.repo_root())},
        manifest_dir=manifest_dir or run_dir / stage,
    )
    print(json.dumps({"stage": stage, "status": manifest["status"], "tasks": len(manifest["tasks"]), "manifest": str(path)}))
    return manifest


def run_cells(
    stage: str,
    args: argparse.Namespace,
    cells: Sequence[Cell],
    worker: str,
    *,
    previous: str | None = None,
    extra: Sequence[str] = (),
    default_hours: float | None = None,
) -> core.StageManifest:
    """One task per cell: ``stages work <worker> --label L ...``; ``previous`` names the earlier stage whose
    manifest supplies the ``after`` dependency (a cell without a completed upstream task is skipped)."""
    run_dir = Path(args.run_dir)
    manifest_dir = run_dir / stage
    if (manifest_dir / "manifest.json").exists():
        raise pool.StageRefused(f"refused: {manifest_dir / 'manifest.json'} already exists; a stage is run once")
    prior_ids: dict[str, str] = {}
    completed: list[str] = []
    skipped_upstream: list[dict[str, Any]] = []
    cells = list(cells)
    if previous is not None:
        path = run_dir / previous / "manifest.json"
        if not path.is_file():
            raise StageError(f"no {path}: run {previous} first")
        upstream = core.read_record(path, "stage_manifest")
        prior_ids = {t["label"]: t["task_id"] for t in upstream["tasks"]}
        completed = [t["task_id"] for t in upstream["tasks"] if t["status"] == "completed"]
        present = [c for c in cells if c.label in prior_ids]
        skipped_upstream = [
            {"label": c.label, "reason": f"no {previous} task for this cell"} for c in cells if c.label not in prior_ids
        ]
        cells = present
    cells, dropped = excluded_for_ceiling(cells, calibration_record_of(args))
    identity = core.code_identity()
    argv_for = {
        c.label: pool.worker_argv("stages", "work", worker, "--label", c.label, *common_args(args), *extra)
        for c in cells
    }
    tasks = pool.plan_stage(stage, cells, run_dir, identity, argv_for=argv_for, previous_stage_ids=prior_ids or None)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    write_json(manifest_dir / "exclusions.json", {"task_ceiling_fail": dropped, "no_upstream_task": skipped_upstream})
    return run_tasks(stage, args, tasks, run_dir, completed_ids=completed, default_hours=default_hours)


# --- workers ---------------------------------------------------------------------------------------------------
def _configure() -> None:
    train._configure()


def _train_job(
    cell: Cell,
    args: argparse.Namespace,
    study: data_mod.StudyData,
    run_dir: Path,
    exposure: int,
    *,
    mode: str,
    max_updates: int | None = None,
    snapshot_updates: Sequence[int] | None = None,
    v1: Path | None = None,
) -> train.TrainJob:
    """The ``TrainJob`` of a registry or calibration cell on the draw ``study`` (any Lane D arm through
    ``incremental``; ``v1`` overrides the V1 snapshot path of a phase-B arm, used by the rehearsal)."""
    bb = backbone_for(args, cell.parent)
    seeds = study.seeds
    if cell.lane_d_arm == "phaseA":
        job = incremental.phase_a_job(cell, study, bb, run_dir, exposure, mode)
    elif cell.is_lane_d and v1 is None:
        start = None if cell.lane_d_arm == "joint" else incremental.v1_snapshot_path(run_dir, cell.depends_on[0], exposure)
        job = incremental.phase_b_job(cell, study, bb, run_dir, start, exposure, mode)
    elif cell.is_lane_d:
        job = train.TrainJob(
            cell=cell,
            exposure=exposure,
            mode=mode,
            data=study,
            stream=data_mod.training_stream_for(study, cell),
            backbone=bb,
            out_dir=core.cell_dir(run_dir, cell.label),
            init_snapshot=v1,
            restore_optimizer=False,
            trainable_groups=incremental.MEMORY_ONLY_GROUPS if cell.lane_d_arm == "memory_only" else None,
            init_seed=init_seed_of(cell, study, mode),
            r1_seed=seeds.r1_codes,
            branch_seed=seeds.branch_hash,
        )
    else:
        lut = data_mod.identifier_lut(study.facts, data_mod.facts_of(study, cell)) if cell.rung == "R2" else None
        job = train.TrainJob(
            cell=cell,
            exposure=exposure,
            mode=mode,
            data=study,
            stream=data_mod.training_stream_for(study, cell),
            backbone=bb,
            out_dir=core.cell_dir(run_dir, cell.label),
            fact_lut=lut,
            init_seed=init_seed_of(cell, study, mode),
            r1_seed=seeds.r1_codes,
            branch_seed=seeds.branch_hash,
        )
    job.init_seed = init_seed_of(cell, study, mode)
    job.max_updates = max_updates
    if snapshot_updates is not None:
        job.snapshot_updates = tuple(snapshot_updates)
    return job


def _marker(path: Path, stage: str, label: str, run_dir: Path, files: Sequence[Path]) -> None:
    """The completion record of a worker whose products are many files (never overwrites)."""
    if path.exists():
        raise FileExistsError(path)
    write_json(
        path,
        {
            "study": core.STUDY,
            "schema": core.SCHEMA,
            "kind": "stage_task",
            "stage": stage,
            "label": label,
            "files": {p.relative_to(run_dir).as_posix(): file_sha256(p) for p in sorted(files)},
        },
    )


def work_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    if args.inject_failure:
        if not args.dry:
            raise StageError("--inject-failure exists for the DRY profile only")
        if cell.label in args.inject_failure:
            print(f"injected DRY failure for {cell.label}", file=sys.stderr)
            return 1
    study = verified_data(args, require_manifest=args.mode == REGISTERED or args.dry)
    exposure = read_exposure(args)
    job = _train_job(cell, args, study, run_dir, exposure, mode=args.mode if args.mode == REGISTERED else CALIBRATION)
    record = train.train_cell(job)
    print(json.dumps({"label": record["label"], "status": record["status"]}))
    return 0 if record["status"] == "completed" else 1


def lane_d_support_slots(cell: Cell, run_dir: Path, study: data_mod.StudyData, args: argparse.Namespace, exposure: int) -> dict[str, dict[str, list[list[int]]]]:
    """Minimal-support slot lists of the A and B facts of a D2 cell on each primary panel at its phase-end
    snapshot (input of ``incremental.support_overlap_detail``; ADR 8.5 'overlap of A and B minimal
    supports'). Dense cells have no slots and no supports."""
    bb = backbone_for(args, cell.parent)
    net = model.build_model(cell, bb, seed_rng=False, r1_seed=study.seeds.r1_codes, branch_seed=study.seeds.branch_hash)
    train.load_snapshot(core.snapshot_dir(run_dir, cell.label, core.updates(cell, exposure)), net)
    out: dict[str, dict[str, list[list[int]]]] = {}
    for panel in core.PANELS:
        per: dict[str, list[list[int]]] = {}
        for which in ("A", "B"):
            stream = study.streams[f"lane_d_{panel.lower()}_{which}"]
            nomem = controls.evaluate_no_memory(bb, study.lane_d, stream)
            cache = evaluate.build_cache(net, stream)
            scores = evaluate.score_cache(cache, stream.answer_targets().reshape(-1))
            per[which] = [list(map(int, slots)) for slots in evaluate.minimal_supports(net, cache, nomem, scores).slots]
        out[panel] = per
    return out


def work_evaluate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    study = verified_data(args, require_manifest=True)
    exposure = read_exposure(args)
    written = evaluate.evaluate_cell(
        cell,
        run_dir,
        study,
        _experiments_root(args),
        exposure,
        secondary=not args.no_secondary,
        backbone=backbone_for(args, cell.parent),
    )
    files = sorted((core.cell_dir(run_dir, cell.label) / "eval").rglob("*"))
    files = [p for p in files if p.is_file()]
    if cell.block == "D2" and cell.arch != "dense":
        supports_path = core.cell_dir(run_dir, cell.label) / "lane_d_supports.json"
        write_json(supports_path, lane_d_support_slots(cell, run_dir, study, args, exposure))
        files.append(supports_path)
    _marker(core.cell_dir(run_dir, cell.label) / "evaluate.json", "evaluate", cell.label, run_dir, files)
    print(json.dumps({"label": cell.label, "eval_records": len(written)}))
    return 0


def work_simulate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    scope = sim.simulation_scope(cell)
    if scope is None:
        raise StageError(f"{cell.label} is not simulated (sim.simulation_plan)")
    exposure = read_exposure(args)
    update = core.updates(cell, exposure)  # the snapshot evaluate traced (matched exposure)
    count = 0
    for stream in ("panel_a", "panel_b"):
        count += len(sim.simulate_cell(cell, run_dir, update, stream, trace_kinds=scope.trace_kinds))
    files = [p for p in (core.cell_dir(run_dir, cell.label) / "sim").rglob("*.json")]
    _marker(core.cell_dir(run_dir, cell.label) / "simulate.json", "simulate", cell.label, run_dir, files)
    print(json.dumps({"label": cell.label, "sim_records": count}))
    return 0


def work_generate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "data_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    study = study_data(args)
    permutations = DRY_G1_PERMUTATIONS if args.dry else None
    epochs = None
    g1 = data_mod.run_g1(study, permutations=permutations, train_epochs=epochs)
    write_json(run_dir / "g1.json", g1)
    write_json(
        target,
        {
            "study": core.STUDY,
            "schema": core.SCHEMA,
            "kind": "data_manifest",
            "seed_set": study.seeds.name,
            "seeds": dataclasses.asdict(study.seeds),
            "dry": bool(args.dry),
            "sha256s": study.sha256s(),
            "template_pool": list(study.pool),
            "g1_passed": bool(g1["passed"]),
            "g1_failed_checks": [c["name"] for c in g1["checks"] if not c["passed"]],
            "g1_file": "g1.json",
            "identity": core.code_identity(),
        },
    )
    print(json.dumps({"seed_set": study.seeds.name, "g1_passed": g1["passed"]}))
    return 0 if g1["passed"] else 1


def work_gates(args: argparse.Namespace) -> int:
    """Gate G4: P5 forward invariance on the frozen backbones and the checkpoint restoration test."""
    run_dir = Path(args.run_dir)
    target = run_dir / "g4.json"
    if target.exists():
        raise FileExistsError(target)
    study = verified_data(args, require_manifest=True)
    tokens = study.streams["panel_a"].tokens[:8, : core.INPUT_LENGTH]
    defects: list[str] = []
    invariance: list[dict[str, Any]] = []
    for parent in (core.PRIMARY_PARENT, core.REPLICATE_PARENT):
        bb = backbone_for(args, parent)
        for variant in ("flat", "fixed_tree", "learned_tree"):
            result = model.p5_forward_invariance(bb, variant, core.INIT_SEEDS[0], tokens)
            result["parent"] = list(parent)
            invariance.append(result)
            ok = (
                result["logits_identical"]
                and result["selection_identical"]
                and result["routing_identical"]
                and result["same_parameters"]
            )
            if not ok:
                defects.append(f"P5 forward invariance failed: {variant} on parent {parent}")
    cell = next(c for c in core.cells() if c.block == "A1" and c.arch == "flat" and c.slots == 4096 and c.seed == core.INIT_SEEDS[0] and c.parent == core.PRIMARY_PARENT)
    split = 4 if args.dry else args.restore_split
    job = _train_job(cell, args, study, run_dir / "g4_restore", _exposure(args), mode=CALIBRATION if args.mode != REGISTERED else REGISTERED)
    restoration = train.checkpoint_restoration_check(job, split)
    if not restoration["identical"]:
        defects.append("checkpoint restoration is not bit-identical")
    manifest_path = run_dir / "data_manifest.json"
    stream_hashes_recorded = manifest_path.is_file()
    if not stream_hashes_recorded:
        defects.append("no data manifest: stream hashes were not recorded")
    write_json(
        target,
        {
            "study": core.STUDY,
            "schema": core.SCHEMA,
            "kind": "g4",
            "passed": not defects,
            "defects": defects,
            "p5_invariance": invariance,
            "restoration": restoration,
            "stream_hashes_verified_against_manifest": stream_hashes_recorded,
            "dry": bool(args.dry),
        },
    )
    print(json.dumps({"g4_passed": not defects, "defects": len(defects)}))
    return 0 if not defects else 1


# --- calibration --------------------------------------------------------------------------------------------
def build_calibration_job(cell: Cell, args: argparse.Namespace, study: data_mod.StudyData, run_dir: Path) -> train.TrainJob:
    """The job of one R2 calibration cell (to E = 128, snapshots at E = 32, 64, 128). Refuses anything but R2."""
    calibration_guard(cell)
    top = core.EXPOSURE_MENU[-1]
    marks = [core.matched_updates(cell.facts, e) for e in core.EXPOSURE_MENU]
    return _train_job(cell, args, study, run_dir, top, mode=CALIBRATION, max_updates=marks[-1], snapshot_updates=marks)


def r2_accuracy_at(cell: Cell, args: argparse.Namespace, study: data_mod.StudyData, run_dir: Path, update: int) -> dict[str, float]:
    """Accuracy of the R2 cell's snapshot on rehearsal panels A and B (the quantity G3 is about)."""
    bb = backbone_for(args, cell.parent)
    lut = data_mod.identifier_lut(study.facts, data_mod.facts_of(study, cell))
    net = model.build_model(cell, bb, fact_lut=lut, seed_rng=False, r1_seed=study.seeds.r1_codes, branch_seed=study.seeds.branch_hash)
    train.load_snapshot(core.snapshot_dir(run_dir, cell.label, update), net)
    out: dict[str, float] = {}
    for panel in core.PANELS:
        stream = data_mod.panel_streams(study, cell, panel)[0]
        cache = evaluate.build_cache(net, stream)
        scores = evaluate.score_cache(cache, stream.answer_targets().reshape(-1))
        trained = stream.fact_ids.reshape(-1) < cell.facts
        out[panel] = float(scores.correct[trained].float().mean())
    return out


def work_calibrate_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    calibration_guard(cell)  # before any data or model is built
    study = study_data(args)
    job = build_calibration_job(cell, args, study, run_dir)
    train.train_cell(job)
    curve = {
        str(e): r2_accuracy_at(cell, args, study, run_dir, core.matched_updates(cell.facts, e))
        for e in core.EXPOSURE_MENU
    }
    target = core.cell_dir(run_dir, cell.label) / "calibrate.json"
    write_json(target, {"study": core.STUDY, "schema": core.SCHEMA, "kind": "calibration_cell", "label": cell.label, "slots": cell.slots, "parent": list(cell.parent), "seed": cell.seed, "r2_accuracy": curve})
    print(json.dumps({"label": cell.label, "snapshots_evaluated": len(curve)}))
    return 0


def frozen_probes(args: argparse.Namespace, study: data_mod.StudyData) -> tuple[dict[str, Any], dict[str, float], dict[tuple[int, int], Any]]:
    """Frozen-hidden probes at each fact count on both parents (nearest stored state, linear probe per
    identifier position) and the attainable answer probability; no memory involved."""
    probes: dict[str, Any] = {}
    attainable: dict[str, float] = {}
    backbones: dict[tuple[int, int], Any] = {}
    sizes = controls.proportional_fact_counts()
    for parent in (core.PRIMARY_PARENT, core.REPLICATE_PARENT):
        bb = backbone_for(args, parent)
        backbones[parent] = bb
        name = f"b{parent[0]}-o{parent[1]}"
        probes[name] = {}
        for facts in sizes:
            fit = data_mod.restrict_stream(study.streams["calibration"], study.facts, facts)
            held = data_mod.restrict_stream(study.streams["panel_a"], study.facts, facts)
            trained = held.fact_ids.reshape(-1) < facts
            nearest = controls.nearest_stored_state_probe(bb, study.facts, fit, held)
            linear = controls.linear_probe_per_position(bb, study.facts, fit, held, seed=study.seeds.permutation_tests)
            assert nearest.per_query_correct is not None
            probes[name][str(facts)] = {
                "queries": int(trained.sum()),
                "nearest_stored_state": float(nearest.per_query_correct[trained].float().mean()),
                "linear_probe_by_position": [
                    float(r.per_query_correct[trained].float().mean()) for r in linear if r.per_query_correct is not None
                ],
            }
        smallest = data_mod.restrict_stream(study.streams["panel_a"], study.facts, sizes[0])
        stats = controls.attainable_answer_probability(bb, smallest)
        attainable.update({f"{name}:{k}": float(v) for k, v in stats.items()})
    return probes, attainable, backbones


def work_calibrate_controls(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    study = study_data(args)
    probes, attainable, backbones = frozen_probes(args, study)
    record = controls.controls_record(study, backbones, probes=probes)
    target = run_dir / "calibrate" / "controls.json"
    write_json(target, {"study": core.STUDY, "schema": core.SCHEMA, "kind": "calibration_controls", "probes": probes, "attainable_probability": attainable, "controls": record})
    print(json.dumps({"parents": len(backbones), "sizes": len(controls.proportional_fact_counts())}))
    return 0


def finalize_calibration(args: argparse.Namespace, run_dir: Path, manifest: core.StageManifest) -> Path:
    """Aggregate the cell results into the ``CalibrationRecord`` (ADR 12 step 4) and select E by the
    registered rule ``core.select_exposure``. The R2 accuracy of a size and exposure is the MINIMUM over
    both panels and all runs (B101 seeds 1701 and 1702, B102 seed 1701): G3 asks for 0.95 on the
    rehearsal panels, and the lowest value is the conservative reading (PENDING LEAD REVIEW)."""
    target = run_dir / "calibration.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} already exists")
    complete = manifest["status"] == "COMPLETE"
    detail: dict[str, Any] = {}
    curves: dict[int, dict[int, float]] = {}
    for cell in core.calibration_cells():
        path = core.cell_dir(run_dir, cell.label) / "calibrate.json"
        if not path.is_file():
            complete = False
            continue
        result = read_json(path)
        detail[cell.label] = result["r2_accuracy"]
        for e, panels in result["r2_accuracy"].items():
            slot = curves.setdefault(cell.slots, {})
            slot[int(e)] = min(slot.get(int(e), 1.0), *[float(v) for v in panels.values()])
    controls_path = run_dir / "calibrate" / "controls.json"
    extra = read_json(controls_path) if controls_path.is_file() else {}
    complete = complete and bool(extra)
    if complete:
        selected, failed = core.select_exposure(curves)
    else:
        selected, failed = None, []
    record: dict[str, Any] = {
        **core.envelope("calibration"),
        "seeds": dataclasses.asdict(core.rehearsal_seeds(args.draw)),
        "r2_accuracy": {str(s): {str(e): a for e, a in sorted(c.items())} for s, c in sorted(curves.items())},
        "probes": extra.get("probes"),
        "attainable_probability": extra.get("attainable_probability"),
        "selected_exposure": selected,
        "task_ceiling_fail": failed,
        "identity": core.code_identity(),
        "complete": complete,
        "rule": "E = smallest of {32, 64, 128} at which R2 reaches 0.95 at every size that does not fail at 128 (core.select_exposure); R2 accuracy = minimum over panels A and B and over runs",
        "r2_detail": detail,
        "controls": extra.get("controls"),
        "provenance": {
            "draw": args.draw,
            "dry": bool(args.dry),
            "stage_manifest": str(run_dir / "calibrate" / "manifest.json"),
            "stage_status": manifest["status"],
            "experiments_root": str(_experiments_root(args)),
            "cells": [c.label for c in core.calibration_cells()],
        },
    }
    core.write_record(target, record)
    return target


def cmd_calibrate(args: argparse.Namespace) -> int:
    if args.mode == REGISTERED:
        raise pool.StageRefused("refused: calibrate runs on a rehearsal draw only")
    run_dir = Path(args.run_dir) if args.run_dir else _experiments_root(args) / core.run_name("calibrate")
    args.run_dir = str(run_dir)
    if (run_dir / "calibrate" / "manifest.json").exists() or (run_dir / "calibration.json").exists():
        raise pool.StageRefused(f"refused: {run_dir} already holds a calibration")
    identity = core.code_identity()
    cells = core.calibration_cells()
    for cell in cells:
        calibration_guard(cell)
    tasks = pool.plan_stage(
        "calibrate",
        cells,
        run_dir,
        identity,
        argv_for={c.label: pool.worker_argv("stages", "work", "calibrate-train", "--label", c.label, *common_args(args)) for c in cells},
    )
    controls_task = _task(
        "calibrate",
        "controls",
        pool.worker_argv("stages", "work", "calibrate-controls", *common_args(args)),
        run_dir,
        identity,
        run_dir / "calibrate" / "controls.json",
    )
    manifest = run_tasks("calibrate", args, [*tasks, controls_task], run_dir, default_hours=core.CALIBRATION_REHEARSAL_HOURS)
    path = finalize_calibration(args, run_dir, manifest)
    record = read_json(path)
    print(json.dumps({"calibration": str(path), "selected_exposure": record["selected_exposure"], "task_ceiling_fail": record["task_ceiling_fail"], "complete": record["complete"], "run_dir": str(run_dir)}))
    return 0 if record["complete"] else 1


# --- rehearsal ----------------------------------------------------------------------------------------------
def kind_key(cell: Cell) -> str:
    """The cost class of a cell: what changes the time or memory of one update (not the seed, parent,
    track, the dose magnitude or the fact count)."""
    reg = f"u{int(cell.alpha_u > 0)}c{int(cell.alpha_c > 0)}"
    return "|".join([cell.arch, cell.rung, f"n{cell.slots}", f"k{cell.key_width}", cell.optimizer, reg, cell.lane_d_arm or "-"])


def rehearsal_cells() -> list[Cell]:
    """One registry cell (B101, seed 1701) of every cost class, at every size it occurs."""
    seen: set[str] = set()
    out: list[Cell] = []
    for cell in core.cells():
        key = kind_key(cell)
        if key in seen or cell.parent != core.PRIMARY_PARENT or cell.seed != core.INIT_SEEDS[0]:
            continue
        seen.add(key)
        out.append(cell)
    return out


def _rehearsal_record(label: str, stage: str, wall: float, rss_peak: int, rss_sampled: int, shapes: dict[str, list[int]]) -> dict[str, Any]:
    return {
        **core.envelope("rehearsal"),
        "label": label,
        "mode": "rehearsal",
        "stage": stage,
        "identity": dict(core.code_identity()),
        "wall_seconds": wall,
        "peak_rss_bytes": rss_peak,
        "sampled_rss_bytes": rss_sampled,
        "load_average": list(os.getloadavg()),
        "shapes": shapes,
    }


@contextlib.contextmanager
def _timed() -> Iterator[dict[str, Any]]:
    out: dict[str, Any] = {}
    process = psutil.Process()
    begun = time.monotonic()
    try:
        yield out
    finally:
        out["wall"] = time.monotonic() - begun
        out["rss"] = int(process.memory_info().rss)
        out["peak"] = train._peak_rss()


def work_rehearse_cell(args: argparse.Namespace) -> int:
    """Train one cell for ``--updates`` updates in rehearsal mode (the whitelisted record only), then copy
    that record to ``rehearse.json`` (the pool's result file). Phase-B arms start from the phase-A
    rehearsal snapshot of their D1 cell."""
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    study = study_data(args)
    exposure = _exposure(args)
    n = args.updates
    v1 = None
    if cell.is_lane_d and cell.lane_d_arm not in ("phaseA", "joint"):
        v1 = core.snapshot_dir(run_dir, cell.depends_on[0], n)
    job = _train_job(cell, args, study, run_dir, exposure, mode="rehearsal", max_updates=n, snapshot_updates=(n,), v1=v1)
    train.train_cell(job)
    record = read_json(core.cell_dir(run_dir, cell.label) / "rehearsal.json")
    train.write_rehearsal_record(core.cell_dir(run_dir, cell.label) / "rehearse.json", record)
    print(f"{cell.label}: rehearsal record written")
    return 0


def _write_timing(run_dir: Path, label: str, step: str, timing: dict[str, Any], shapes: dict[str, list[int]]) -> None:
    folder = core.cell_dir(run_dir, label)
    train.write_rehearsal_record(
        folder / f"rehearse-{step}.json",
        _rehearsal_record(label, f"rehearse-{step}", timing["wall"], timing["peak"], timing["rss"], shapes),
    )


def work_rehearse_evaluate(args: argparse.Namespace) -> int:
    """Time the evaluation of one rehearsal snapshot (deep: panels A and B with interventions and traces,
    and the calibration stream traced; light: panels A and B without interventions). The evaluation runs
    into a scratch directory that is deleted at exit; only wall time, RSS and stream shapes are recorded."""
    run_dir = Path(args.run_dir)
    cell = core.parse_label(args.label)
    study = study_data(args)
    bb = backbone_for(args, cell.parent)
    n = args.updates
    lut = data_mod.identifier_lut(study.facts, data_mod.facts_of(study, cell)) if cell.rung == "R2" else None
    net = model.build_model(cell, bb, fact_lut=lut, seed_rng=False, r1_seed=study.seeds.r1_codes, branch_seed=study.seeds.branch_hash)
    train.load_snapshot(core.snapshot_dir(run_dir, cell.label, n), net)
    streams = [data_mod.panel_streams(study, cell, p)[0] for p in core.PANELS]
    calibration = data_mod.restrict_stream(study.streams["calibration"], study.facts, cell.facts)
    shapes = {s.name: [int(s.tokens.shape[0]), int(s.tokens.shape[1])] for s in (*streams, calibration)}
    seed = study.seeds.permutation_tests
    with tempfile.TemporaryDirectory(prefix="p9-rehearse-eval-") as scratch:
        scratch_dir = Path(scratch)
        nomem = {s.name: controls.evaluate_no_memory(bb, study.facts, s) for s in (*streams, calibration)}
        with _timed() as deep:
            for s in streams:
                evaluate.evaluate_snapshot(cell, scratch_dir, n, s, study, net, nomem=nomem[s.name], interventions=True, write_traces=True, seed=seed)
            evaluate.evaluate_snapshot(cell, scratch_dir, n, calibration, study, net, nomem=nomem[calibration.name], interventions=False, write_traces=True, seed=seed)
        with _timed() as light:
            for s in streams:
                evaluate.evaluate_snapshot(cell, scratch_dir, n, s, study, net, nomem=nomem[s.name], interventions=False, write_traces=False, seed=seed)
        _write_timing(run_dir, cell.label, "evaluate-deep", deep, shapes)
        _write_timing(run_dir, cell.label, "evaluate-light", light, shapes)
        # the scratch traces stay for the simulation timing of the same worker when the cell is simulated
        scope = sim.simulation_scope(cell)
        if scope is not None:
            for kind in ("answer", "all"):
                if kind not in scope.trace_kinds:
                    continue
                with _timed() as t:
                    for stream_name in ("panel_a", "panel_b"):
                        sim.simulate_cell(cell, scratch_dir, n, stream_name, trace_kinds=(kind,))
                _write_timing(run_dir, cell.label, f"simulate-{kind}", t, shapes)
    marker = _rehearsal_record(cell.label, "rehearse-evaluate", deep["wall"] + light["wall"], deep["peak"], deep["rss"], shapes)
    train.write_rehearsal_record(core.cell_dir(run_dir, cell.label) / "rehearse-eval.json", marker)
    print(f"{cell.label}: evaluation timings written")
    return 0


def cmd_rehearse(args: argparse.Namespace) -> int:
    if args.mode == REGISTERED:
        raise pool.StageRefused("refused: rehearse runs on a rehearsal draw only")
    args.rehearse = True
    run_dir = Path(args.run_dir) if args.run_dir else _experiments_root(args) / core.run_name("rehearse")
    args.run_dir = str(run_dir)
    if (run_dir / "rehearse" / "manifest.json").exists():
        raise pool.StageRefused(f"refused: {run_dir} already holds a rehearsal")
    identity = core.code_identity()
    cells = [c for c in rehearsal_cells() if not args.only or c.label in args.only]
    eval_labels = [core.parse_label(label) for label in (args.eval_cells or EVAL_CELLS)] if not args.dry else []
    if args.dry:
        eval_labels = [c for c in cells if c.block in ("A1", "A2") and c.slots in (4096, 16384)][:2]
    if not cells:
        raise StageError("no rehearsal cell selected")
    extra = ["--updates", str(args.updates), "--exposure", str(_exposure(args))]
    argv_for = {c.label: pool.worker_argv("stages", "work", "rehearse-cell", "--label", c.label, *common_args(args), *extra) for c in cells}
    tasks = pool.plan_stage("rehearse", cells, run_dir, identity, argv_for=argv_for)
    for c in eval_labels:
        tasks.append(
            _task(
                "rehearse",
                f"evaluate:{c.label}",
                pool.worker_argv("stages", "work", "rehearse-evaluate", "--label", c.label, *common_args(args), *extra),
                run_dir,
                identity,
                core.cell_dir(run_dir, c.label) / "rehearse-eval.json",
                depends_on=(c.label,),
            )
        )
    # timing runs alone (ADR 11): one cell at a time; the contention measurement follows
    manifest = run_tasks("rehearse", args, tasks, run_dir, workers={"train": 1, "evaluate": 1, "simulate": 1, "analyze": 1}, default_hours=core.CALIBRATION_REHEARSAL_HOURS)
    contention = measure_contention(args, run_dir, args.contention_cell or (CONTENTION_CELL if not args.dry else cells[0].label), extra)
    table = projection_table(run_dir, cells, eval_labels, contention, manifest)
    out_json, out_md = run_dir / "projection.json", run_dir / "projection.md"
    write_json(out_json, table)
    out_md.write_text(render_projection(table), encoding="utf-8")
    problems = scan_rehearsal_outputs(run_dir)
    print(json.dumps({"run_dir": str(run_dir), "projection": str(out_md), "status": manifest["status"], "forbidden_words_found": problems}))
    return 0 if manifest["status"] == "COMPLETE" and not problems else 1


def measure_contention(args: argparse.Namespace, run_dir: Path, label: str, extra: Sequence[str]) -> dict[str, Any]:
    """The same cell with 1, 2, 4 and 8 concurrent single-thread workers (each a separate rehearsal run
    directory); the pool is used with K worker slots and K tasks, one manifest per K."""
    identity = core.code_identity()
    out: dict[str, Any] = {"cell": label, "workers": {}}
    for k in CONTENTION_WORKERS:
        tasks = []
        for i in range(k):
            sub = run_dir / "contention" / f"k{k}-{i}"
            tasks.append(
                _task(
                    "rehearse",
                    f"contention-k{k}-{i}",
                    pool.worker_argv("stages", "work", "rehearse-cell", "--label", label, *common_args(args, sub), *extra),
                    run_dir,
                    identity,
                    core.cell_dir(sub, label) / "rehearse.json",
                )
            )
        manifest = run_tasks("rehearse", args, tasks, run_dir, workers={"train": k, "evaluate": k, "simulate": k, "analyze": 1}, default_hours=core.CALIBRATION_REHEARSAL_HOURS, manifest_dir=run_dir / "contention" / f"manifest-k{k}")
        rows = []
        for i in range(k):
            path = core.cell_dir(run_dir / "contention" / f"k{k}-{i}", label) / "rehearse.json"
            if path.is_file():
                record = read_json(path)
                rows.append({"seconds_per_update": record["seconds_per_update"], "wall_seconds": record["wall_seconds"], "peak_rss_bytes": record["peak_rss_bytes"]})
        out["workers"][str(k)] = {"status": manifest["status"], "runs": rows}
    return out


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def contention_slowdown(contention: dict[str, Any]) -> dict[int, float]:
    """Per-worker slowdown t_K / t_1 (mean seconds per update with K concurrent workers over one worker);
    1.0 is ideal, parallel efficiency is its inverse."""
    means = {int(k): _mean([r["seconds_per_update"] for r in v["runs"]]) for k, v in contention["workers"].items()}
    base = means.get(1)
    return {k: (v / base if base and base == base else float("nan")) for k, v in sorted(means.items())}


def interpolate(table: dict[int, float], workers: int) -> float:
    """Linear interpolation of the slowdown between measured worker counts (6 lies between 4 and 8)."""
    points = sorted(table.items())
    if workers in table:
        return table[workers]
    lo = max((p for p in points if p[0] < workers), default=None)
    hi = min((p for p in points if p[0] > workers), default=None)
    if lo is None or hi is None:
        return (lo or hi or (0, float("nan")))[1]
    return lo[1] + (hi[1] - lo[1]) * (workers - lo[0]) / (hi[0] - lo[0])


def _record_of(run_dir: Path, label: str, name: str) -> dict[str, Any] | None:
    path = core.cell_dir(run_dir, label) / name
    return read_json(path) if path.is_file() else None


def eval_snapshot_counts(cell: Cell, exposure: int) -> tuple[int, int, int]:
    """``(deep snapshots, light snapshots, traced snapshots)`` of ``evaluate.evaluate_cell``."""
    marks = core.snapshots(cell, exposure)
    matched = core.updates(cell, exposure)
    fixed = None if cell.is_lane_d else core.fixed_compute_updates(exposure)
    deep = [m for m in marks if m in (matched, fixed)]
    traced = 1 if cell.block in evaluate.TRACE_BLOCKS and cell.arch != "dense" else 0
    return len(deep), len(marks) - len(deep), traced


def projection_table(run_dir: Path, cells: Sequence[Cell], eval_cells: Sequence[Cell], contention: dict[str, Any], manifest: core.StageManifest) -> dict[str, Any]:
    """Per cell kind seconds per update and RSS (measured, rehearsal), evaluation and simulation seconds
    (measured), parallel efficiency (measured), and the projected wall time of the 100-cell matrix at
    E in {32, 64, 128} for 2, 4, 6, 8 training workers (DERIVED from the measurements by the formulas in
    ``notes``; a projection, never a measurement; logical work is not used anywhere)."""
    kinds: dict[str, Any] = {}
    for cell in cells:
        record = _record_of(run_dir, cell.label, "rehearse.json")
        if record is None:
            continue
        kinds[kind_key(cell)] = {"label": cell.label, "seconds_per_update": record["seconds_per_update"], "peak_rss_bytes": record["peak_rss_bytes"], "sampled_rss_bytes": record["sampled_rss_bytes"], "updates": record["updates"], "label_kind": "measured"}
    evals: dict[str, Any] = {}
    for cell in eval_cells:
        rows: dict[str, Any] = {"label": cell.label, "slots": cell.slots, "facts": cell.facts, "arch": cell.arch}
        for step in ("evaluate-deep", "evaluate-light", "simulate-answer", "simulate-all"):
            rec = _record_of(run_dir, cell.label, f"rehearse-{step}.json")
            if rec is not None:
                rows[step] = {"wall_seconds": rec["wall_seconds"], "peak_rss_bytes": rec["peak_rss_bytes"]}
        evals[cell.label] = rows
    slowdown = contention_slowdown(contention)

    def per_update(cell: Cell) -> float | None:
        entry = kinds.get(kind_key(cell))
        return None if entry is None else float(entry["seconds_per_update"])

    def eval_seconds(cell: Cell, step: str) -> float | None:
        """Measured at the same slots and architecture if available, else scaled linearly in facts from
        the nearest measured size of the same architecture (an assumption, labelled hypothetical)."""
        pool_ = [e for e in evals.values() if step in e and e["arch"] == ("learned_tree" if cell.arch in ("learned_tree", "fixed_tree") else "flat")]
        if cell.arch == "dense":
            pool_ = [e for e in evals.values() if "evaluate-light" in e and e["arch"] == "flat"]
            step = "evaluate-light"
        if not pool_:
            return None
        best = min(pool_, key=lambda e: abs(e["slots"] - cell.slots))
        return float(best[step]["wall_seconds"]) * (float(cell.facts) / float(best["facts"]))

    def total(exposure: int) -> dict[str, Any]:
        train_s = eval_s = sim_s = 0.0
        longest = 0.0
        missing: list[str] = []
        for cell in core.cells():
            u = per_update(cell)
            if u is None:
                missing.append(cell.label)
                continue
            seconds = u * core.run_updates(cell, exposure)
            train_s += seconds
            longest = max(longest, seconds)
            deep, light, traced = eval_snapshot_counts(cell, exposure)
            d, li = eval_seconds(cell, "evaluate-deep"), eval_seconds(cell, "evaluate-light")
            if d is not None and li is not None:
                eval_s += deep * d + light * li
            scope = sim.simulation_scope(cell)
            if scope is not None:
                for kind in scope.trace_kinds:
                    s = eval_seconds(cell, f"simulate-{kind}")
                    if s is not None:
                        sim_s += s
        return {"train_cpu_seconds": train_s, "evaluate_cpu_seconds": eval_s, "simulate_cpu_seconds": sim_s, "longest_cell_seconds": longest, "cells_without_timing": missing}

    projection: dict[str, Any] = {}
    for exposure in PROJECTION_EXPOSURES:
        base = total(exposure)
        rows = {}
        for w in PROJECTION_WORKERS:
            s = interpolate(slowdown, w)
            train_wall = max(base["train_cpu_seconds"] * s / w, base["longest_cell_seconds"] * s)
            eval_wall = base["evaluate_cpu_seconds"] * s / w
            sim_wall = base["simulate_cpu_seconds"] * interpolate(slowdown, min(w, core.SIMULATION_WORKERS)) / min(w, core.SIMULATION_WORKERS)
            rows[str(w)] = {"slowdown": s, "train_wall_seconds": train_wall, "evaluate_wall_seconds": eval_wall, "simulate_wall_seconds": sim_wall, "total_wall_seconds": train_wall + eval_wall + sim_wall, "total_wall_hours": (train_wall + eval_wall + sim_wall) / 3600.0}
        projection[str(exposure)] = {"single_worker_seconds": base, "by_training_workers": rows}
    rss = [e["peak_rss_bytes"] for e in kinds.values()]
    return {
        "kind": "rehearsal_projection",
        "study": core.STUDY,
        "schema": core.SCHEMA,
        "rehearsal_status": manifest["status"],
        "label_kind": "measured (rehearsal) and derived (projection); not a registered result",
        "cell_kinds": kinds,
        "evaluation_and_simulation": evals,
        "contention": {"cell": contention["cell"], "slowdown_vs_one_worker": {str(k): v for k, v in slowdown.items()}, "parallel_efficiency": {str(k): (1.0 / v if v == v and v > 0 else None) for k, v in slowdown.items()}, "raw": contention["workers"]},
        "peak_rss_bytes_max_over_kinds": max(rss) if rss else None,
        "projection": projection,
        "notes": [
            "seconds per update = wall time of the rehearsal training run / updates, so it includes model construction and the final snapshot write (an over-estimate for long runs).",
            "train wall = max(sum over the 100 cells of updates x seconds per update of the cell's kind x slowdown / W, longest cell x slowdown); slowdown is the measured per-worker slowdown at W concurrent workers, linearly interpolated between measured worker counts.",
            "evaluation and simulation are projected from the measured timings of the cells in 'evaluation_and_simulation' (same slots and architecture where measured; otherwise scaled linearly with the fact count: an assumption, hypothetical); the dense adapter is taken as the light evaluation of a flat cell.",
            "the evaluation timing was taken on a freshly initialised model after a few updates: the minimal-support search stops early for facts that are not answered, so the deep evaluation of trained cells can take longer than measured here.",
            "phases are added (train, then evaluate, then simulate); in the registered run they overlap, so the sum is an upper bound of the pipelined time. Lane D dependencies are not modelled beyond the longest-cell bound.",
        ],
    }


def render_projection(table: dict[str, Any]) -> str:
    lines = ["# Rehearsal projection (measured timings; projected totals are derived, not measured)", "", f"Rehearsal stage status: {table['rehearsal_status']}", "", "## Seconds per update and RSS per cell kind (measured)", "", "| cell kind | seconds / update | peak RSS (MiB) |", "|---|---|---|"]
    for key, e in sorted(table["cell_kinds"].items()):
        lines.append(f"| {key} | {e['seconds_per_update']:.4f} | {e['peak_rss_bytes'] / 2**20:.0f} |")
    lines += ["", "## Evaluation and simulation seconds (measured on the rehearsal snapshot)", "", "| cell | step | seconds | peak RSS (MiB) |", "|---|---|---|---|"]
    for label, e in table["evaluation_and_simulation"].items():
        for step in ("evaluate-deep", "evaluate-light", "simulate-answer", "simulate-all"):
            if step in e:
                lines.append(f"| {label} | {step} | {e[step]['wall_seconds']:.2f} | {e[step]['peak_rss_bytes'] / 2**20:.0f} |")
    lines += ["", "## Worker contention (measured; same cell, K concurrent single-thread workers)", "", "| K | slowdown vs one worker | parallel efficiency |", "|---|---|---|"]
    for k, v in table["contention"]["slowdown_vs_one_worker"].items():
        eff = table["contention"]["parallel_efficiency"][k]
        lines.append(f"| {k} | {v:.3f} | {'n/a' if eff is None else f'{eff:.3f}'} |")
    lines += ["", "## Projected wall time of the 100-cell matrix (derived)", "", "| E | training workers | train h | evaluate h | simulate h | total h |", "|---|---|---|---|---|---|"]
    for exposure, block in table["projection"].items():
        for w, r in block["by_training_workers"].items():
            lines.append(f"| {exposure} | {w} | {r['train_wall_seconds'] / 3600:.2f} | {r['evaluate_wall_seconds'] / 3600:.2f} | {r['simulate_wall_seconds'] / 3600:.2f} | {r['total_wall_hours']:.2f} |")
    lines += ["", "Notes:", *[f"- {n}" for n in table["notes"]]]
    return "\n".join(lines) + "\n"


def scan_rehearsal_outputs(run_dir: Path) -> list[str]:
    """Files of a rehearsal run (records, projection, logs) that contain a word that would indicate a loss
    or accuracy value (``train._FORBIDDEN_WORDS``): the auditor's check, made here as a self-check.
    Binary snapshot files are skipped; the stage manifests and worker logs are scanned."""
    found: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.suffix in (".pt", ".bin"):
            continue
        text = re.sub(r"[0-9a-f]{16,}", "", path.read_text(encoding="utf-8", errors="replace").lower())
        for allowed in core.REHEARSAL_RECORD_KEYS:  # the whitelist's own key names (for example loss_finite)
            text = text.replace(f'"{allowed}"', "")
        hits = sorted({w for w in FORBIDDEN_IN_REHEARSAL_OUTPUT if w in text})
        if hits:
            found.append(f"{path.relative_to(run_dir)}: {hits}")
    return found


# --- generate / gates commands -----------------------------------------------------------------------------------
def _new_run_dir(args: argparse.Namespace, stage: str) -> Path:
    run_dir = Path(args.run_dir) if args.run_dir else _experiments_root(args) / core.run_name(stage)
    args.run_dir = str(run_dir)
    return run_dir


def cmd_generate(args: argparse.Namespace) -> int:
    if bool(args.registered_seeds) == (args.rehearsal_draw is not None):
        raise pool.StageRefused("refused: give exactly one of --registered-seeds and --rehearsal-draw K")
    args.mode = REGISTERED if args.registered_seeds else CALIBRATION
    if args.rehearsal_draw is not None:
        args.draw = args.rehearsal_draw
    if args.registered_seeds and not args.i_understand_freeze_time:
        raise pool.StageRefused("refused: registered-seed generation is used at freeze time; add --i-understand-freeze-time")
    run_dir = _new_run_dir(args, "panel")
    if (run_dir / "generate" / "manifest.json").exists() or (run_dir / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {run_dir} already holds generated data")
    identity = core.code_identity()
    task = _task("generate", "generate", pool.worker_argv("stages", "work", "generate", *common_args(args)), run_dir, identity, run_dir / "data_manifest.json")
    saved_mode = args.mode
    args.mode = CALIBRATION  # the pool stage itself needs no freeze: generation precedes the freeze commit
    try:
        manifest = run_tasks("generate", args, [task], run_dir, default_hours=core.CALIBRATION_REHEARSAL_HOURS)
    finally:
        args.mode = saved_mode
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if (run_dir / "gates" / "manifest.json").exists():
        raise pool.StageRefused("refused: gates manifest already exists")
    extra = ["--exposure", str(_exposure(args)), "--restore-split", str(args.restore_split)]
    task = _task("gates", "gates", pool.worker_argv("stages", "work", "gates", *common_args(args), *extra), run_dir, core.code_identity(), run_dir / "g4.json")
    manifest = run_tasks("gates", args, [task], run_dir, workers={"train": 1, "evaluate": 1, "simulate": 1, "analyze": 1})
    return 0 if manifest["status"] == "COMPLETE" else 1


# --- train / evaluate / simulate commands -------------------------------------------------------------------------
def cmd_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    calibration = calibration_record_of(args)
    exposure = _exposure(args)
    if args.mode == REGISTERED:
        if calibration is None or calibration.get("selected_exposure") is None:
            raise pool.StageRefused("refused: a registered run needs --calibration with a selected exposure")
        if args.exposure is not None and int(args.exposure) != int(calibration["selected_exposure"]):
            raise pool.StageRefused("refused: --exposure differs from the calibration's selected exposure")
        exposure = int(calibration["selected_exposure"])
        args.exposure = exposure
    marker = run_dir / "exposure.json"
    if marker.exists() or (run_dir / "train" / "manifest.json").exists():
        raise pool.StageRefused("refused: this run already has an exposure or a train manifest")
    pre = pool.check_preconditions(_pool_mode(args), _repo(args), args.freeze_commit)  # fail before writing anything
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(marker, {"exposure": exposure, "mode": args.mode, "dry": bool(args.dry), "calibration_sha256": None if not args.calibration else file_sha256(Path(args.calibration)), "freeze": pre})
    cells = select_cells(args)
    extra = [a for label in (args.inject_failure or []) for a in ("--inject-failure", label)]
    manifest = run_cells("train", args, cells, "train", extra=extra)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    read_exposure(args)
    extra = ["--no-secondary"] if args.no_secondary else []
    manifest = run_cells("evaluate", args, select_cells(args), "evaluate", previous="train", extra=extra)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_simulate(args: argparse.Namespace) -> int:
    exposure = read_exposure(args)
    cells = select_cells(args, only=lambda c: sim.simulation_scope(c) is not None)
    # the traces exist only at the matched snapshot of the cells evaluate traced (see the consistency tests)
    for c in cells:
        assert c.block in evaluate.TRACE_BLOCKS and core.updates(c, exposure) in core.snapshots(c, exposure)
    if not cells:
        print(json.dumps({"stage": "simulate", "status": "NOTHING_TO_RUN", "tasks": 0}))
        return 0
    manifest = run_cells("simulate", args, cells, "simulate", previous="evaluate")
    return 0 if manifest["status"] == "COMPLETE" else 1


# --- analyze / report ---------------------------------------------------------------------------------------------
def _manifests(run_dir: Path, dry: bool) -> list[core.StageManifest]:
    found: list[core.StageManifest] = []
    for path in sorted(run_dir.glob("*/manifest.json")):
        record = core.read_record(path, "stage_manifest")
        if dry:  # DRY manifests are read as registered ones so that the status logic is exercised
            record = {**record, "mode": REGISTERED}
        found.append(record)  # type: ignore[arg-type]
    return found


def lane_d_measurements(run_dir: Path, study: data_mod.StudyData, exposure: int, root: Path) -> ClassResult:
    """Lane D reported quantities per D2 cell and panel (slots and bytes changed with the keys-and-values
    only count beside the all-tensor count, updates, examples, logical lookup work), from existing
    records; cells without records are listed. Support overlap (Jaccard of the support slots of the A and B
    facts) comes from ``lane_d_supports.json`` written by the evaluate worker of memory-bearing D2 cells."""
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for cell in core.cells():
        if cell.block != "D2" or not (core.cell_dir(run_dir, cell.label) / "train.json").is_file():
            continue
        supports_path = core.cell_dir(run_dir, cell.label) / "lane_d_supports.json"
        supports = None
        if supports_path.is_file():
            saved = read_json(supports_path)
            supports = {panel: (per["A"], per["B"]) for panel, per in saved.items()}
        try:
            rows += [dataclasses.asdict(m) for m in incremental.measure_arm(cell, run_dir, study, root, exposure, supports=supports)]
        except (FileNotFoundError, ValueError) as error:
            missing.append(f"{cell.label}: {error}")
    for m in incremental.exact_append_control(study):
        rows.append(dataclasses.asdict(m))
    return analysis_a.make_result("D", "lane_d_measurements", "REPORTED", {p: "REPORTED" for p in core.PANELS}, [], {"rows": rows, "missing": missing, "bytes_note": "changed_bytes counts every changed addition tensor; changed_bytes_keys_values counts keys and values only", "support_overlap": "Jaccard index of the union of minimal-support slots of A facts and of B facts (incremental.support_overlap_detail; definition PENDING LEAD REVIEW); None for dense arms"})


def work_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "analysis.json"
    if target.exists():
        raise FileExistsError(target)
    exposure = read_exposure(args)
    study = verified_data(args, require_manifest=True)
    calibration = calibration_record_of(args)
    g4_path = run_dir / "g4.json"
    g4 = read_json(g4_path) if g4_path.is_file() else None
    g1_report = read_json(run_dir / "g1.json")
    backbones = {p: backbone_for(args, p) for p in (core.PRIMARY_PARENT, core.REPLICATE_PARENT)}
    controls_rec = controls.controls_record(
        study, backbones, g1=g1_report, g4=None if g4 is None else {"passed": g4["passed"], "defects": g4["defects"]}, probes=None if calibration is None else calibration.get("probes")
    )
    inputs = report.load_inputs([run_dir], exposure)
    results = report.run_analyses(inputs, calibration, controls_rec)
    results.append(lane_d_measurements(run_dir, study, exposure, _experiments_root(args)))
    manifests = _manifests(run_dir, bool(args.dry))
    defects = [] if g4 is None else list(g4["defects"])
    status = report.study_status(manifests, defects)
    write_json(target, {"study": core.STUDY, "schema": core.SCHEMA, "kind": "analysis", "dry": bool(args.dry), "exposure": exposure, "status": status, "engineering_defects": defects, "controls": controls_rec, "results": analysis_a.jsonable(results), "unreadable": list(inputs.unreadable), "specificity_scope": evaluate.SPECIFICITY_SCOPE})
    print(json.dumps({"classes": len(results), "status": status}))
    return 0


def work_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    results_dir = Path(args.results_dir) if args.results_dir else run_dir / "report"
    if (results_dir / "results.json").exists():
        raise FileExistsError(results_dir / "results.json")
    analysis = read_json(run_dir / "analysis.json")
    exposure = int(analysis["exposure"])
    inputs = report.load_inputs([run_dir], exposure)
    manifests = _manifests(run_dir, bool(args.dry))
    results: list[ClassResult] = analysis["results"]
    banner = DRY_BANNER if args.dry else None
    paths = report.write_report(run_dir, results_dir, results, analysis["status"], manifests=manifests, inputs=inputs, banner=banner)
    if args.dry:
        write_json(results_dir / "DRY.json", {"dry": True, "banner": DRY_BANNER})
    print(json.dumps({"written": len(paths)}))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    read_exposure(args)
    if (run_dir / "analysis.json").exists() or (run_dir / "analyze" / "manifest.json").exists():
        raise pool.StageRefused("refused: the analysis runs once and never overwrites")
    extra = ["--calibration", args.calibration] if args.calibration else []
    task = _task("analyze", "analysis", pool.worker_argv("stages", "work", "analyze", *common_args(args), *extra), run_dir, core.code_identity(), run_dir / "analysis.json")
    manifest = run_tasks("analyze", args, [task], run_dir, workers={"train": 1, "evaluate": 1, "simulate": 1, "analyze": 1}, default_hours=core.CALIBRATION_REHEARSAL_HOURS)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    results_dir = Path(args.results_dir) if args.results_dir else run_dir / "report"
    if (results_dir / "results.json").exists() or (run_dir / "report" / "manifest.json").exists():
        raise pool.StageRefused("refused: the report runs once and never overwrites")
    if not (run_dir / "analysis.json").is_file():
        raise StageError("no analysis.json: run analyze first")
    extra = ["--results-dir", str(results_dir)] if args.results_dir else []
    task = _task("report", "report", pool.worker_argv("stages", "work", "report", *common_args(args), *extra), run_dir, core.code_identity(), results_dir / "results.json")
    manifest = run_tasks("report", args, [task], run_dir, workers={"train": 1, "evaluate": 1, "simulate": 1, "analyze": 1}, default_hours=core.CALIBRATION_REHEARSAL_HOURS, manifest_dir=run_dir / "report-stage")
    return 0 if manifest["status"] == "COMPLETE" else 1


# --- dry ----------------------------------------------------------------------------------------------------------
def cmd_dry(args: argparse.Namespace) -> int:
    """Every stage, in order, at tiny size on test seeds (draw ``DRY_DRAW``, seeds >= 179001) in a
    temporary root. The reduced registry is ``dry_scope_labels(args.scope)``. Outputs are marked DRY."""
    root = Path(args.out_root) if args.out_root else Path(tempfile.mkdtemp(prefix="p9-dry-"))
    run_dir = root / "P9DRY-run"
    if run_dir.exists():
        raise pool.StageRefused(f"refused: {run_dir} exists")
    base = ["--dry", "--mode", CALIBRATION, "--draw", str(DRY_DRAW), "--run-dir", str(run_dir), "--experiments-root", args.experiments_root or str(core.default_experiments_root()), "--train-workers", str(args.train_workers), "--sim-workers", str(args.sim_workers), "--stage-cap-seconds", str(args.stage_cap_seconds or 3600), "--scope", args.scope]
    if args.synthetic_backbone:
        base.append("--synthetic-backbone")
    if args.repo:
        base += ["--repo", args.repo]
    steps: list[tuple[str, list[str]]] = [
        ("generate", ["generate", "--rehearsal-draw", str(DRY_DRAW), "--dry", "--run-dir", str(run_dir), "--experiments-root", base[base.index("--experiments-root") + 1], "--stage-cap-seconds", str(args.stage_cap_seconds or 3600), *(["--synthetic-backbone"] if args.synthetic_backbone else [])]),
        ("gates", ["gates", *base]),
        ("train", ["train", *base, "--exposure", "32", *[a for f in (args.inject_failure or []) for a in ("--inject-failure", f)]]),
        ("evaluate", ["evaluate", *base]),
        ("simulate", ["simulate", *base]),
        ("analyze", ["analyze", *base]),
        ("report", ["report", *base]),
    ]
    summary: dict[str, Any] = {
        "run_dir": str(run_dir),
        "scope": args.scope,
        "scope_cells": dry_scope_labels(args.scope),
        "scope_rule": (dry_scope_labels.__doc__ or "").strip(),
        "banner": DRY_BANNER,
        "stages": {},
    }
    for name, argv in steps:
        code = main(argv)
        summary["stages"][name] = code
        if name in ("generate", "gates") and code != 0:
            break
    analysis_path = run_dir / "analysis.json"
    if analysis_path.is_file():
        analysis = read_json(analysis_path)
        summary["status"] = analysis["status"]
        summary["classes"] = {f"{r['lane']}:{r['subject']}": r["cls"] for r in analysis["results"]}
    summary["report"] = str(run_dir / "report" / "RESULTS.md") if (run_dir / "report" / "results.json").is_file() else None
    write_json(root / "DRY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["report"] else 1


# --- command line --------------------------------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--run-dir", default=None)
    p.add_argument("--experiments-root", default=None)
    p.add_argument("--repo", default=None, help="repository to check for a registered stage (tests)")
    p.add_argument("--mode", choices=(REGISTERED, CALIBRATION), default=None)
    p.add_argument("--draw", type=int, default=0, help="rehearsal-namespace draw (seeds >= 179001)")
    p.add_argument("--dry", action="store_true", help="the DRY profile (tiny sizes; never with --mode registered)")
    p.add_argument("--synthetic-backbone", action="store_true", help="random stand-in backbone (DRY and tests only)")
    p.add_argument("--exposure", type=int, default=None)
    p.add_argument("--freeze-commit", default=None)
    p.add_argument("--calibration", default=None, help="calibration record (selected exposure, TASK_CEILING_FAIL sizes)")
    p.add_argument("--train-workers", type=int, default=2)
    p.add_argument("--sim-workers", type=int, default=core.SIMULATION_WORKERS)
    p.add_argument("--stage-cap-seconds", type=float, default=None)
    p.add_argument("--rss-worker-bytes", type=int, default=core.RSS_WORKER_BYTES)
    p.add_argument("--rss-aggregate-bytes", type=int, default=core.RSS_AGGREGATE_BYTES)
    p.add_argument("--block", action="append", default=None)
    p.add_argument("--only", action="append", default=None, help="restrict a stage to these cell labels")
    p.add_argument("--label", default=None, help="worker commands: the cell")
    p.add_argument("--scope", choices=("reduced", "full", "lane_d", "smoke"), default="reduced", help="DRY registry")
    p.add_argument("--no-secondary", action="store_true")
    p.add_argument("--inject-failure", action="append", default=None, help="DRY only: fail this cell's training")
    p.add_argument("--restore-split", type=int, default=16)
    p.add_argument("--results-dir", default=None)
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p9.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", parents=[common])
    gen.add_argument("--rehearsal-draw", type=int, default=None)
    gen.add_argument("--registered-seeds", action="store_true")
    gen.add_argument("--i-understand-freeze-time", action="store_true")
    for name in ("calibrate", "rehearse", "gates", "train", "evaluate", "simulate", "analyze", "report"):
        p = sub.add_parser(name, parents=[common])
        if name == "rehearse":
            p.add_argument("--updates", type=int, default=REHEARSAL_DEFAULT_UPDATES)
            p.add_argument("--eval-cells", nargs="*", default=None)
            p.add_argument("--contention-cell", default=None)
    dry = sub.add_parser("dry", parents=[common])
    dry.add_argument("--out-root", default=None)
    work = sub.add_parser("work")
    wsub = work.add_subparsers(dest="worker", required=True)
    for name in ("train", "evaluate", "simulate", "generate", "gates", "analyze", "report", "calibrate-train", "calibrate-controls", "rehearse-cell", "rehearse-evaluate"):
        w = wsub.add_parser(name, parents=[common])
        w.add_argument("--updates", type=int, default=REHEARSAL_DEFAULT_UPDATES)
    return parser


REGISTERED_COMMANDS = ("gates", "train", "evaluate", "simulate", "analyze", "report")
WORKERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "train": work_train,
    "evaluate": work_evaluate,
    "simulate": work_simulate,
    "generate": work_generate,
    "gates": work_gates,
    "analyze": work_analyze,
    "report": work_report,
    "calibrate-train": work_calibrate_train,
    "calibrate-controls": work_calibrate_controls,
    "rehearse-cell": work_rehearse_cell,
    "rehearse-evaluate": work_rehearse_evaluate,
}
COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "generate": cmd_generate,
    "calibrate": cmd_calibrate,
    "rehearse": cmd_rehearse,
    "gates": cmd_gates,
    "train": cmd_train,
    "evaluate": cmd_evaluate,
    "simulate": cmd_simulate,
    "analyze": cmd_analyze,
    "report": cmd_report,
    "dry": cmd_dry,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Exit codes: 0 stage complete, 1 stage ran but a task or gate failed (records kept), 2 refused."""
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.mode is None:
        args.mode = REGISTERED if args.command in REGISTERED_COMMANDS and not args.dry else CALIBRATION
    if args.dry and args.mode == REGISTERED and args.command != "generate":
        print("refused: --dry cannot be combined with --mode registered", file=sys.stderr)
        return 2
    installed_here = False
    if (args.dry or args.command == "dry") and not core.dry_active():
        core.install_dry_registry()
        installed_here = True
    try:
        if args.command == "work":
            _configure()
            return WORKERS[args.worker](args)
        if args.command == "dry":
            args.dry = True
            args.mode = CALIBRATION
        elif args.command != "generate" and args.run_dir is None and args.command not in ("calibrate", "rehearse"):
            raise StageError("--run-dir is required")
        return COMMANDS[args.command](args)
    except pool.StageRefused as exc:
        print(f"P9 stage REFUSED: {exc}", file=sys.stderr)
        return 2
    except CalibrationRefused as exc:
        print(f"P9 calibration REFUSED: {exc}", file=sys.stderr)
        return 2
    except StageError as exc:
        print(f"P9 stage error: {exc}", file=sys.stderr)
        return 2
    finally:
        if installed_here:
            core.uninstall_dry_registry()


if __name__ == "__main__":
    sys.exit(main())

