# ruff: noqa: E501
"""P9I stages (ADR-0017 Part I, sections I.6, I.9-I.12): ``generate``, ``calibrate``, ``rehearse``, ``gates``,
``train``, ``evaluate``, ``analyze``, ``report`` and ``dry`` (tiny synthetic end to end).

Run from the repository root: ``uv run --locked python -m studies.p9i.stages <command> ...``. Stages run
through P9's job manager (``studies.p9.pool.run_stage``): immutable task ids, per-worker RSS cap (3 GiB),
aggregate cap (24 GiB), failed records kept, a failed cell stops the cells that depend on it, nothing is
re-run with changed settings. Workers are single-thread subprocesses (``--workers``, six by default).

Charged time. Every pool stage first asks the ledger (``core.Ledger``, one JSON file for calibration,
rehearsal and the run together; cap 4 hours) and refuses to start when the remainder is smaller than its
own stage cap; it charges the wall time it used. ``--stage-cap-seconds`` is required except in the DRY
stage.

Modes and seeds. ``registered`` (needs ``--freeze-commit`` and a clean tree) uses only the registered data
seeds 182001+; ``calibration`` only rehearsal draw 1 (data seeds 179101+) and runs only the controls, R1
and R2 (``calibration_guard`` refuses anything else before anything is built); ``rehearsal`` uses the other
rehearsal draws (default 2) and writes only the whitelisted time, memory, shape and count record; the
DRY stage and unit tests use test seeds (900001+).

Not run by this module's author: the calibration, the rehearsal and every registered stage (the DRY
stage runs on a random synthetic backbone and test seeds only).
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

import torch

from arborlm.io import file_sha256, read_json, write_json
from studies.p9 import controls, pool
from studies.p9 import core as p9core
from studies.p9 import data as data_mod
from studies.p9 import model as p9model

from . import classes, core, evaluate, model, report, train

REGISTERED, CALIBRATION, REHEARSAL = "registered", "calibration", "rehearsal"
DRY_BANNER = "DRY: tiny synthetic sizes, random synthetic backbone, test seeds; not a measurement of anything"
DRY_SIZES = data_mod.DataSizes(main_trained=2048, unseen=64, lane_d_per_set=128)  # 128 of 2,048 facts: the registered 2,048 / 32,768 proportion of the smallest size
DRY_FACTS = {4096: 128, 16384: 256, 65536: 512}
DRY_UPDATES = 8
DRY_CAL_SNAPSHOTS = (2, 4, 6, 8)
DRY_CANDIDATES = (4, 6, 8)
DRY_SLOTS = (4096,)
DRY_G1_PERMUTATIONS = 200
SYNTHETIC_CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
REHEARSAL_DEFAULT_UPDATES = 64
GROUP_OF_STAGE = {"generate": "analyze", "calibrate": "train", "rehearse": "train", "gates": "train", "train": "train", "evaluate": "evaluate", "analyze": "analyze", "report": "analyze"}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


class CalibrationRefused(RuntimeError):
    """The calibration was asked to build or train something other than R1, R2 or the controls."""


class HarnessError(RuntimeError):
    """The gates harness chose inputs that do not belong to the cell it checks. Distinct from a gradient,
    identity or restoration defect (those are recorded as G4 defects): nothing was learnt about the model."""


class StageError(RuntimeError):
    """A stage cannot start for a reason other than a pool refusal."""


# --- guards -------------------------------------------------------------------------------------------------------------
def calibration_guard(cell: core.Cell) -> None:
    """Section I.6: the calibration builds and trains controls, R1 and R2 only (and only calibration
    cells). Called by every calibration entry point before anything is built or trained."""
    if cell.block != "CAL" or cell.arm not in core.CALIBRATION_ARMS:
        raise CalibrationRefused(f"the calibration trains only R1 and R2 and controls (ADR-0017 section I.6); refused: {cell.label}")


# --- options, seeds, data, backbones -----------------------------------------------------------------------------------
def seeds_for(args: argparse.Namespace) -> p9core.SeedSet:
    """The data seeds of the mode (``core.check_seed_set`` is applied again by every training job)."""
    synthetic = bool(args.dry or args.synthetic_backbone)
    if args.mode == REGISTERED:
        if synthetic:
            raise pool.StageRefused("refused: registered seeds with the DRY profile or a synthetic backbone")
        return core.registered_seeds()
    if synthetic:
        return core.test_seeds(0)
    if args.mode == CALIBRATION:
        return core.calibration_seeds()
    if args.draw == core.CALIBRATION_DRAW:
        raise pool.StageRefused(f"refused: rehearsal draw {core.CALIBRATION_DRAW} is the calibration draw")
    return core.rehearsal_draw_seeds(args.draw)


def experiments_root(args: argparse.Namespace) -> Path:
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def study_data(args: argparse.Namespace) -> data_mod.StudyData:
    corpus = SYNTHETIC_CORPUS if args.dry or args.synthetic_backbone else p9core.load_trained_corpus(experiments_root(args))
    seeds = seeds_for(args)
    core.check_seed_set(args.mode, seeds.name)
    study = data_mod.build_study_data(seeds, corpus, sizes=DRY_SIZES if args.dry else None)
    if args.mode == REGISTERED and study.pool != p9core.TEMPLATE_POOL:
        raise StageError("template pool differs from the registered pool (studies.p9.core.TEMPLATE_POOL)")
    return study


def corpus_bytes(args: argparse.Namespace) -> bytes:
    return SYNTHETIC_CORPUS if args.dry or args.synthetic_backbone else p9core.load_trained_corpus(experiments_root(args))


@functools.cache
def _synthetic(parent: tuple[int, int]) -> Any:
    return controls.synthetic_backbone(*parent)


def backbone_for(args: argparse.Namespace, parent: tuple[int, int]) -> Any:
    if args.synthetic_backbone or args.dry:
        return _synthetic(parent)
    return controls.load_backbone(parent, experiments_root(args))[0]


def verified_data(args: argparse.Namespace, *, require_manifest: bool) -> data_mod.StudyData:
    """``study_data`` checked against the stream hashes of ``<run>/data_manifest.json``."""
    study = study_data(args)
    path = Path(args.run_dir) / "data_manifest.json"
    if path.is_file():
        if read_json(path)["sha256s"] != study.sha256s():
            raise StageError(f"regenerated data differ from the hashes in {path}")
    elif require_manifest:
        raise StageError(f"no data manifest at {path}: run generate first")
    return study


def facts_for(args: argparse.Namespace, cell: core.Cell) -> int:
    return DRY_FACTS[cell.slots] if args.dry else cell.facts


def init_seed(args: argparse.Namespace, cell: core.Cell) -> int:
    return core.init_seed_of(cell, args.mode, seeds_for(args))


# --- cell selection -----------------------------------------------------------------------------------------------
def dry_cells() -> list[core.Cell]:
    """The DRY registry: every arm at 4,096 slots, both initialization seeds, on parent B101 (24 cells)."""
    return [core.make_cell(arm, 4096, core.PRIMARY_PARENT, seed) for arm in core.ARMS for seed in core.INIT_SEEDS]


def dry_calibration_cells() -> list[core.Cell]:
    return [c for c in core.calibration_cells() if c.slots == 4096]


def calibration_record_of(args: argparse.Namespace) -> dict[str, Any] | None:
    """The calibration record named by ``--calibration``; when ``--calibration-sha256`` is given (every
    worker gets it) the file must hash to it."""
    if not args.calibration:
        return None
    path = Path(args.calibration)
    if args.calibration_sha256 and file_sha256(path) != args.calibration_sha256:
        raise pool.StageRefused(f"refused: {path} does not hash to the calibration record the stage was started with")
    return core.read_record(path, "calibration")


def calibration_binding(args: argparse.Namespace) -> dict[str, Any] | None:
    """What a stage carries into its records: the calibration record's sha256, its selected U and its
    failed sizes (None without a record)."""
    record = calibration_record_of(args)
    if record is None:
        return None
    return {"calibration_sha256": file_sha256(Path(args.calibration)), "calibration_selected_updates": record["selected_updates"], "calibration_failed_sizes": record["failed_sizes"]}


def check_binding(args: argparse.Namespace, run_dir: Path) -> None:
    """The train stage writes ``calibration_binding.json``; every later stage of a registered run must
    present the same record (same hash, selected U and failed sizes) and refuses otherwise."""
    binding = calibration_binding(args)
    path = run_dir / "calibration_binding.json"
    if binding is None:
        if args.mode == REGISTERED:
            raise pool.StageRefused("refused: a registered stage needs --calibration")
        return
    if not path.is_file():
        raise pool.StageRefused(f"refused: no {path}: the train stage has not recorded the calibration")
    if read_json(path) != binding:
        raise pool.StageRefused("refused: the calibration record differs (hash, selected U or failed sizes) from the one the train stage recorded")


def require_gates_passed(run_dir: Path) -> dict[str, Any]:
    """A registered training starts only when the ``gates`` record exists and G1, G2 and G4 all passed."""
    path = run_dir / "gates.json"
    if not path.is_file():
        raise pool.StageRefused(f"refused: no gates record at {path}: run the gates stage first")
    gates = core.read_record(path, "gates")
    failed = [name for name, ok in (("G1", gates.get("g1_passed") is True), ("G2", gates.get("g2_passed") is True), ("G4", gates.get("g4_passed") is True)) if not ok]
    if failed:
        raise pool.StageRefused(f"refused: gate(s) {', '.join(failed)} did not pass; nothing is trained")
    return gates


def remember_updates(args: argparse.Namespace) -> int:
    """U for a command; a registered run's workers re-derive it from the calibration record."""
    updates = updates_for(args)
    if args.mode != REGISTERED:
        args.updates = updates
    return updates


def cells_for(args: argparse.Namespace) -> list[core.Cell]:
    """Cells of a stage: the DRY registry, or the registered cells minus the sizes the calibration marked
    failed, restricted by ``--only`` and ``--group``."""
    cells = dry_cells() if args.dry else core.cells()
    if args.only:
        wanted = set(args.only)
        cells = [c for c in cells if c.label in wanted]
    if args.group:
        cells = [c for c in cells if c.group in args.group]
    record = calibration_record_of(args)
    if record is not None and not args.dry:
        failed = {int(s) for s in record["failed_sizes"]}
        cells = [c for c in cells if c.slots not in failed]
    return cells


def updates_for(args: argparse.Namespace) -> int:
    """U of the run: ``DRY_UPDATES`` in the DRY stage; else the calibration record's selected U (required
    in a registered run, which refuses ``--updates``), or ``--updates`` (rehearsal and tests)."""
    if args.dry:
        return DRY_UPDATES
    record = calibration_record_of(args)
    if args.mode == REGISTERED:
        if record is None:
            raise pool.StageRefused("refused: a registered stage needs --calibration")
        if args.updates is not None:
            raise pool.StageRefused("refused: a registered stage takes U from the calibration record, not from --updates")
    if record is not None:
        value = record["selected_updates"]
        if value is None:
            raise pool.StageRefused("refused: the calibration selected no U")
        if args.updates is not None and int(args.updates) != int(value):
            raise StageError(f"--updates {args.updates} differs from the calibration's U {value}")
        return int(value)
    if args.updates is None:
        raise StageError("give --calibration (the registered U) or --updates")
    return int(args.updates)


# --- running a stage through the pool ----------------------------------------------------------------------------------
def repo_of(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def _git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of
    HEAD, ``studies/``, the P9I config, the ADR and ``tests/test_p9i_*`` equal their content at that commit,
    and ``core.frozen_input_check`` (src/arborlm, uv.lock, pyproject.toml, P8 digest) is ok. Returns the
    freeze identity (None for calibration and rehearsal)."""
    if mode != REGISTERED:
        return None
    dirty = _git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise pool.StageRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise pool.StageRefused("refused: a registered stage requires --freeze-commit")
    ok = _git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise pool.StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if _git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise pool.StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems = []
    for path in ("studies", str(core.DEFAULT_CONFIG), core.SPEC, "tests"):
        a = _git(repo, "rev-parse", f"{full}:{path}").stdout
        b = _git(repo, "rev-parse", f"HEAD:{path}").stdout
        if a != b and path != "tests":
            problems.append(f"{path} at HEAD differs from the freeze commit")
    for name in _git(repo, "ls-tree", "--name-only", "HEAD", "tests/").stdout.decode().split():
        if name.startswith("tests/test_p9i_") and _git(repo, "rev-parse", f"{full}:{name}").stdout != _git(repo, "rev-parse", f"HEAD:{name}").stdout:
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise pool.StageRefused("refused: " + "; ".join(problems))
    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise pool.StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": _git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def ledger_for(args: argparse.Namespace) -> core.Ledger:
    return core.Ledger(Path(args.ledger)) if args.ledger else core.default_ledger(experiments_root(args))


def stage_cap(args: argparse.Namespace) -> float:
    if args.stage_cap_seconds is not None:
        return float(args.stage_cap_seconds)
    if args.dry:
        return 3600.0
    raise pool.StageRefused("refused: --stage-cap-seconds is required (caps are fixed after the rehearsal)")


def common_args(args: argparse.Namespace, run_dir: Path | None = None) -> list[str]:
    """Options every worker needs to rebuild the same draw (never a scientific value)."""
    out = ["--run-dir", str(run_dir or args.run_dir), "--mode", args.mode, "--draw", str(args.draw), "--experiments-root", str(experiments_root(args))]
    if args.dry:
        out.append("--dry")
    if args.synthetic_backbone:
        out.append("--synthetic-backbone")
    if args.calibration:
        out += ["--calibration", str(args.calibration), "--calibration-sha256", file_sha256(Path(args.calibration))]
    if args.updates is not None:
        out += ["--updates", str(args.updates)]
    return out


def worker_argv(worker: str, *extra: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "studies.p9i.stages", "work", worker, *extra)


def make_task(stage: str, label: str, argv: Sequence[str], run_dir: Path, identity: core.Identity, result_path: Path, *, after: Sequence[str] = ()) -> pool.Task:
    if len(argv) < 5 or argv[1:3] != ("-m", "studies.p9i.stages"):
        raise ValueError("worker argv must be '<python> -m studies.p9i.stages work ...'")
    folder = run_dir / stage
    return pool.Task(
        task_id=pool.task_id(stage, label, cast(Any, identity)),
        stage=stage,
        label=label,
        argv=tuple(argv),
        depends_on=(),
        after=tuple(after),
        group=GROUP_OF_STAGE[stage],
        result_path=result_path,
        failed_path=folder / f"{label}.failed.json",
        log_path=folder / f"{label}.log",
    )


def run_stage_tasks(
    stage: str,
    args: argparse.Namespace,
    tasks: Sequence[pool.Task],
    run_dir: Path,
    *,
    completed_ids: Sequence[str] = (),
    workers: int | None = None,
    skip_preconditions: bool = False,
) -> dict[str, Any]:
    """Ledger check, preconditions, the pool, the ledger charge, and the stage manifest (written once)."""
    cap = stage_cap(args)
    target = run_dir / stage / "manifest.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} already exists; a stage is run once and never overwritten")
    ledger = ledger_for(args)
    ledger.require_room(stage, cap)
    if not skip_preconditions:
        check_preconditions(args.mode, repo_of(args), args.freeze_commit)
    count = workers or args.workers
    if args.mode == REGISTERED and not 1 <= count <= core.WORKERS:
        raise pool.StageRefused(f"refused: {count} workers; Part I uses at most {core.WORKERS}")
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
    manifest = dict(
        pool.build_manifest(
            stage,
            run_dir,
            args.mode,
            cast(Any, identity),
            tasks,
            result,
            started_utc=started,
            finished_utc=_utc(),
            workers=count,
            caps=pool.StageCaps(cap, args.rss_worker_bytes, args.rss_aggregate_bytes).as_dict(),
        )
    )
    manifest["study"] = core.STUDY  # P9's builder writes its own code; the P9I record carries P9I
    core.write_record(target, manifest)
    print(json.dumps({"stage": stage, "status": manifest["status"], "tasks": len(tasks), "manifest": str(target), "charged_seconds": round(result.wall_seconds, 1)}))
    return manifest


def run_cells(stage: str, worker: str, args: argparse.Namespace, cells: Sequence[core.Cell], run_dir: Path, result_for: Any, *, previous: str | None = None, extra: Sequence[str] = ()) -> dict[str, Any]:
    """One task per cell: ``stages work <worker> --label L ...``; ``previous`` names the earlier stage whose
    manifest supplies the ``after`` dependency (a cell without a completed upstream task is not run)."""
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
        cells = [c for c in cells if c.label in prior]
    tasks = [
        make_task(stage, c.label, worker_argv(worker, "--label", c.label, *common_args(args), *extra), run_dir, identity, result_for(c), after=[prior[c.label]] if c.label in prior else [])
        for c in cells
    ]
    return run_stage_tasks(stage, args, tasks, run_dir, completed_ids=completed)


def single_task(stage: str, label: str, worker: str, args: argparse.Namespace, run_dir: Path, result_path: Path, extra: Sequence[str] = (), *, skip_preconditions: bool = False) -> dict[str, Any]:
    task = make_task(stage, label, worker_argv(worker, *common_args(args), *extra), run_dir, core.code_identity(), result_path)
    return run_stage_tasks(stage, args, [task], run_dir, workers=1, skip_preconditions=skip_preconditions)


# --- train jobs ------------------------------------------------------------------------------------------------------------
def build_job(args: argparse.Namespace, cell: core.Cell, study: data_mod.StudyData, out_dir: Path, updates: int, *, snapshots: Sequence[int] | None = None, max_updates: int | None = None, mode: str | None = None) -> train.TrainJob:
    facts = facts_for(args, cell)
    seeds = study.seeds
    return train.TrainJob(
        cell=cell,
        updates=updates,
        mode=mode or args.mode,
        data=study,
        stream=train.training_stream_for(study, facts),
        backbone=backbone_for(args, cell.parent),
        out_dir=out_dir,
        init_seed=init_seed(args, cell),
        r1_seed=seeds.r1_codes,
        fact_lut=train.fact_lut_for(study, facts) if cell.arm == "R2" else None,
        snapshots=snapshots,
        max_updates=max_updates,
        extra=calibration_binding(args) or {},
    )


def configure() -> None:
    train.configure()


# --- workers ------------------------------------------------------------------------------------------------------------------
def work_generate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "data_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    study = study_data(args)
    g1 = data_mod.run_g1(study, permutations=DRY_G1_PERMUTATIONS if args.dry else None, train_epochs=None)
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
            "identity": dict(core.code_identity()),
        },
    )
    print(json.dumps({"seed_set": study.seeds.name, "g1_passed": g1["passed"]}))
    return 0 if g1["passed"] else 1


def fact_counts_of(args: argparse.Namespace) -> list[int]:
    return sorted({facts_for(args, c) for c in (dry_cells() if args.dry else core.cells())})


def gate_contexts(study: data_mod.StudyData, facts: int, count: int = 8) -> tuple[torch.Tensor, torch.Tensor]:
    """``count`` contexts for the gates of a cell with ``facts`` trained facts: rows of Panel A restricted to
    those facts by ``evaluate.stream_for`` (the function the evaluate path uses), keeping the rows in which
    every record's fact is one the cell covers (the restricted stream also holds unseen-control contexts).
    Returns ``(tokens [count, 64], fact_ids [count, 8])``; raises ``HarnessError`` when there are too few."""
    stream = evaluate.stream_for(study, facts, "panel_a")
    rows = (stream.fact_ids < facts).all(dim=1).nonzero().squeeze(1)[:count]
    if rows.numel() < count:
        raise HarnessError(f"only {rows.numel()} Panel A contexts hold {facts} facts or fewer; {count} are needed")
    return stream.tokens[rows], stream.fact_ids[rows]


def assert_covered(tokens: torch.Tensor, fact_ids: torch.Tensor, facts: int, lut: torch.Tensor | None = None) -> None:
    """Every answer site of the chosen contexts must refer to a fact covered by the cell (id below
    ``facts``) and, for R2, by its lookup table (the table must map the record's identifier to that fact's
    slot). Raises ``HarnessError`` otherwise, so that a bad choice of inputs is never read as a gradient
    defect."""
    if bool((fact_ids >= facts).any()) or bool((fact_ids < 0).any()):
        bad = sorted({int(i) for i in fact_ids.reshape(-1) if not 0 <= int(i) < facts})
        raise HarnessError(f"gate inputs refer to facts the cell does not cover (ids {bad[:5]} outside 0..{facts - 1})")
    if lut is not None:
        slots = lut[p9model.identifier_codes(tokens[:, : core.INPUT_LENGTH])]
        if not torch.equal(slots, fact_ids):
            raise HarnessError("the R2 lookup table does not map the chosen contexts' identifiers to their facts' slots")


def work_gates(args: argparse.Namespace) -> int:
    """G2 (no-memory baseline, exact retrieval, unseen set) and G4 (arm N against P9's R0a, the initial
    identities of block BB, checkpoint restoration for N and BB)."""
    run_dir = Path(args.run_dir)
    target = run_dir / "gates.json"
    if target.exists():
        raise FileExistsError(target)
    study = verified_data(args, require_manifest=True)
    defects: list[str] = []
    backbones = {p: backbone_for(args, p) for p in (core.PRIMARY_PARENT, core.REPLICATE_PARENT)}
    controls_rec = evaluate.controls_record(study, backbones, fact_counts_of(args))
    cell_facts = facts_for(args, core.make_cell("N", 4096))
    gate_tokens, gate_ids = gate_contexts(study, cell_facts)
    assert_covered(gate_tokens, gate_ids, cell_facts)
    tokens = gate_tokens[:, : core.INPUT_LENGTH]
    identity: list[dict[str, Any]] = []
    for parent, bb in backbones.items():
        n_r0a = model.n_against_p9_r0a(bb, 4096, core.INIT_SEEDS[0], tokens)
        ids = model.initial_identities(bb, 4096, core.INIT_SEEDS[0], tokens)
        identity.append({"parent": list(parent), "n_against_r0a": n_r0a, "initial_identities": ids})
        if not (n_r0a["logits_identical"] and n_r0a["selection_identical"] and n_r0a["read_vector_identical"] and n_r0a["same_parameters"]):
            defects.append(f"arm N differs from P9's R0a on parent {parent}")
        defects += [f"initial identity failed: {k} on parent {parent}" for k, v in ids.items() if not v]
    split = 4 if args.dry else args.restore_split
    restoration: dict[str, Any] = {}
    for arm in ("N", "BB"):
        cell = core.make_cell(arm, 4096)
        job = build_job(args, cell, study, run_dir / "g4_restore" / arm, 2 * split, snapshots=(), mode=args.mode)
        restoration[arm] = train.checkpoint_restoration_check(job, split)
        if not restoration[arm]["identical"]:
            defects.append(f"checkpoint restoration is not bit-identical for {arm}")
    reach: dict[str, Any] = {}
    for arm in core.ARMS:
        lut = train.fact_lut_for(study, cell_facts) if arm == "R2" else None
        assert_covered(gate_tokens, gate_ids, cell_facts, lut)  # a harness error, never a gradient defect
        net = model.build_model(arm, 4096, core.INIT_SEEDS[0], backbones[core.PRIMARY_PARENT], fact_lut=lut, r1_seed=study.seeds.r1_codes)
        r = train.gradient_reach(net, gate_tokens)
        reach[arm] = {"all_reached": all(r["reached"].values()), "stray": r["stray"], "trainable": len(r["trainable"])}
        if not reach[arm]["all_reached"] or r["stray"]:
            defects.append(f"gradient reach failed for {arm}")
    g1_path = run_dir / "g1.json"
    g1_passed = bool(read_json(g1_path)["passed"]) if g1_path.is_file() else None
    write_json(
        target,
        {**core.envelope("gates"), "g2": controls_rec["g2"], "g2_passed": bool(controls_rec["g2"]["passed"]), "g1_passed": g1_passed, "g4_defects": defects, "g4_passed": not defects, "identity": identity, "restoration": restoration, "gradient_reach": reach, "controls": controls_rec, "dry": bool(args.dry)},
    )
    print(json.dumps({"g4_passed": not defects, "g2_passed": bool(controls_rec["g2"]["passed"]), "defects": len(defects)}))
    return 0 if not defects else 1


def work_train(args: argparse.Namespace) -> int:
    cell = core.parse_label(args.label)
    if cell.block == "CAL":
        raise StageError("calibration cells are trained by the calibrate stage")
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
    study = verified_data(args, require_manifest=not args.dry and args.mode == REGISTERED)
    updates = updates_for(args)
    job = build_job(args, cell, study, core.cell_dir(run_dir, cell.label), updates)
    record = train.train_cell(job)
    print(json.dumps({"label": record["label"], "status": record["status"]}))
    return 0 if record["status"] == "completed" else 1


def work_evaluate(args: argparse.Namespace) -> int:
    cell = core.parse_label(args.label)
    run_dir = Path(args.run_dir)
    study = verified_data(args, require_manifest=not args.dry and args.mode == REGISTERED)
    updates = updates_for(args)
    backbone = backbone_for(args, cell.parent)
    facts = facts_for(args, cell)
    rows = evaluate.corpus_rows(corpus_bytes(args)) if cell.arm in core.BB_ARMS else None
    evaluate.evaluate_cell(
        cell,
        run_dir,
        study,
        backbone,
        facts=facts,
        updates=[updates],
        init_seed=init_seed(args, cell),
        r1_seed=study.seeds.r1_codes,
        fact_lut=train.fact_lut_for(study, facts) if cell.arm == "R2" else None,
        rows=rows,
        extra=calibration_binding(args),
        require_train_record=True,
    )
    print(json.dumps({"label": cell.label, "evaluated": updates}))
    return 0


def work_calibrate_cell(args: argparse.Namespace) -> int:
    """Train one calibration run (R1 or R2) to the last snapshot, then score each snapshot on Panels A and
    B (accuracy only). Refuses any other cell."""
    cell = core.parse_label(args.label)
    calibration_guard(cell)
    run_dir = Path(args.run_dir)
    study = study_data(args)
    marks = DRY_CAL_SNAPSHOTS if args.dry else core.CALIBRATION_SNAPSHOTS
    out_dir = core.cell_dir(run_dir, cell.label)
    job = build_job(args, cell, study, out_dir, marks[-1], snapshots=marks, mode=CALIBRATION)
    record = train.train_cell(job)
    facts = facts_for(args, cell)
    curves: dict[str, dict[str, float]] = {}
    for update in marks:
        net = model.build_model(cell.arm, cell.slots, job.init_seed, job.backbone, fact_lut=job.fact_lut, r1_seed=job.r1_seed, seed_rng=False)
        train.load_snapshot(out_dir / "snapshots" / core.snapshot_stem(update), net)
        net.eval()
        curves[str(update)] = {p: float(evaluate.evaluate_stream(net, study, facts, core.PANEL_STREAM[p], primary=False)["accuracy"]) for p in core.PANELS}
    write_json(out_dir / "calibration_cell.json", {**core.envelope("calibration"), "label": cell.label, "arm": cell.arm, "slots": cell.slots, "parent": list(cell.parent), "seed": cell.seed, "snapshots": list(marks), "accuracy": curves, "status": record["status"]})
    print(json.dumps({"label": cell.label, "status": record["status"]}))
    return 0 if record["status"] == "completed" else 1


def work_calibrate_controls(args: argparse.Namespace) -> int:
    """The controls on the calibration draw: no-memory baseline, exact retrieval and G2 (no trained arm)."""
    run_dir = Path(args.run_dir)
    study = study_data(args)
    backbones = {p: backbone_for(args, p) for p in (core.PRIMARY_PARENT, core.REPLICATE_PARENT)}
    record = evaluate.controls_record(study, backbones, fact_counts_of(args))
    write_json(run_dir / "calibration_controls.json", {**core.envelope("calibration"), "controls": record, "seed_set": study.seeds.name})
    print(json.dumps({"g2_passed": bool(record["g2"]["passed"])}))
    return 0


def curves_of(run_dir: Path, cells: Sequence[core.Cell]) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, float]], dict[str, Any]]:
    """``r2[size][U]``, ``r1[size][U]`` = minimum over the two B101 calibration runs and both panels; the
    B102 run is reported beside them."""
    r: dict[str, dict[int, dict[int, float]]] = {"R1": {}, "R2": {}}
    replicate: dict[str, Any] = {}
    for cell in cells:
        path = core.cell_dir(run_dir, cell.label) / "calibration_cell.json"
        if not path.is_file():
            continue
        record = core.read_record(path, "calibration")
        for update, panels in record["accuracy"].items():
            value = min(panels.values())
            if cell.parent == core.PRIMARY_PARENT:
                slot = r[cell.arm].setdefault(cell.slots, {})
                slot[int(update)] = min(slot.get(int(update), math.inf), value)
            else:
                replicate.setdefault(cell.arm, {}).setdefault(str(cell.slots), {})[update] = value
    return r["R2"], r["R1"], replicate


def finalize_calibration(args: argparse.Namespace, run_dir: Path, cells: Sequence[core.Cell]) -> Path:
    r2, r1, replicate = curves_of(run_dir, cells)
    candidates = DRY_CANDIDATES if args.dry else core.CANDIDATE_UPDATES
    sizes = DRY_SLOTS if args.dry else core.SLOTS_BY_SIZE
    for s in sizes:  # a size with no record at all is failed by the rule, not silently dropped
        r2.setdefault(s, {})
        r1.setdefault(s, {})
    chosen = core.select_updates(r2, r1, candidates)
    controls_path = run_dir / "calibration_controls.json"
    path = run_dir / "calibration.json"
    core.write_record(
        path,
        {
            **core.envelope("calibration"),
            "selected_updates": chosen.updates,
            "failed_sizes": {str(s): v for s, v in chosen.failed.items()},
            "live_sizes": chosen.live,
            "r2_min_accuracy": {str(s): {str(u): a for u, a in c.items()} for s, c in r2.items()},
            "r1_min_accuracy": {str(s): {str(u): a for u, a in c.items()} for s, c in r1.items()},
            "b102_replicate": replicate,
            "candidates": list(candidates),
            "controls": read_json(controls_path)["controls"] if controls_path.is_file() else None,
            "inconclusive_by_step_0": bool(chosen.failed),
            "dry": bool(args.dry),
            "identity": dict(core.code_identity()),
            "note": "after calibration only U and the failed sizes may change (ADR-0017 section I.6)",
        },
    )
    return path


def work_rehearse_cell(args: argparse.Namespace) -> int:
    """Rehearsal of one cell: ``--updates`` updates in rehearsal mode (whitelisted record only), then the
    time of one full evaluation of the written snapshot into a scratch directory that is deleted. Nothing
    but time, memory, shapes, counts and identity is written; no loss or accuracy is read out."""
    cell = core.parse_label(args.label)
    run_dir = Path(args.run_dir)
    study = study_data(args)
    updates = args.updates if args.updates is not None else REHEARSAL_DEFAULT_UPDATES
    out_dir = core.cell_dir(run_dir, cell.label)
    job = build_job(args, cell, study, out_dir, updates, snapshots=(updates,), max_updates=updates, mode=REHEARSAL)
    train.train_cell(job)
    started = time.monotonic()
    facts = facts_for(args, cell)
    net = model.build_model(cell.arm, cell.slots, job.init_seed, job.backbone, fact_lut=job.fact_lut, r1_seed=job.r1_seed, seed_rng=False)
    train.load_snapshot(out_dir / "snapshots" / core.snapshot_stem(updates), net)
    rows = evaluate.corpus_rows(corpus_bytes(args))[:256] if cell.arm in core.BB_ARMS else None
    evaluate.evaluate_snapshot(cell, net, study, facts, updates, frozen_backbone=job.backbone, rows=rows)  # result discarded
    wall = time.monotonic() - started
    record = {
        **core.envelope("rehearsal"),
        "label": cell.label,
        "mode": "rehearsal",
        "stage": "rehearse-evaluate",
        "identity": dict(core.code_identity()),
        "updates": 0,
        "wall_seconds": wall,
        "seconds_per_update": 0.0,
        "peak_rss_bytes": train.peak_rss(),
        "seed_set": study.seeds.name,
    }
    train.write_rehearsal_record(out_dir / "rehearsal_evaluate.json", record)
    print(json.dumps({"label": cell.label, "evaluation_seconds": round(wall, 2)}))
    return 0


def assess(
    *,
    table: Any,
    lm: Any,
    size_status: dict[int, str | None],
    sizes: tuple[int, ...],
    missing: list[str],
    failed_tasks: list[str],
    gates: dict[str, Any] | None,
    leakage: list[str],
) -> dict[str, Any]:
    """Status, interpretability and the analysis of a run (pure function of its inputs).

    * Status: ``ENGINEERING_FAIL`` only for identity, determinism, checkpoint or gradient-reach defects
      (G4; ADR-0017 section 8.6); else ``INCOMPLETE`` when a registered cell lacks a record, a task did not
      complete or the gates record is absent; else ``COMPLETE``. A G1 or G2 failure is not a status.
    * Missing or failed cells (M1): no class, annotation or selection is derived; the outcome is
      ``NOT_INTERPRETED (INCOMPLETE)`` with the missing labels (the denominator is never reduced).
    * Gates to interpretation (M2): a failed or unrecorded G1, a failed G2, any LEAKAGE flag or a G4 defect
      gives ``interpretable`` False, and the selection outcome is ``NOT_INTERPRETED`` with the reasons; the
      classes are still returned, marked not interpreted.
    """
    defects = [] if gates is None else list(gates["g4_defects"])
    g1 = None if gates is None else gates.get("g1_passed")
    g2 = None if gates is None else gates.get("g2_passed")
    g4 = None if gates is None else bool(gates.get("g4_passed", not defects))
    incomplete = bool(missing or failed_tasks or gates is None)
    status = "ENGINEERING_FAIL" if defects else ("INCOMPLETE" if incomplete else "COMPLETE")
    reasons: list[str] = []
    if gates is not None:
        if g1 is not True:
            reasons.append("G1 failed" if g1 is False else "G1 not recorded")
        if g2 is not True:
            reasons.append("G2 failed" if g2 is False else "G2 not recorded")
        if g4 is not True:
            reasons.append("G4 failed: " + "; ".join(defects))
    if leakage:
        reasons.append("LEAKAGE: " + ", ".join(leakage))
    if incomplete:
        absent = [*missing, *failed_tasks, *(["gates record"] if gates is None else [])]
        selection: dict[str, Any] = {
            "outcome": classes.NOT_INTERPRETED_INCOMPLETE, "step": None, "inconclusive_sizes": {},
            "missing": absent, "reasons": reasons,
            "scope": ["no class, annotation or selection is derived: registered cells or records are missing (ADR-0017 section 8.6)"],
        }  # fmt: skip
        analysis: dict[str, Any] = {
            "classes": {}, "details": {}, "annotations": {}, "backbone_contrast": {},
            "size_status": {str(s): size_status.get(s) for s in sizes}, "selection": selection,
        }  # fmt: skip
    else:
        analysis = classes.analyze_classes(table, lm, size_status, sizes=sizes)
        if reasons:
            analysis["selection"] = {
                "outcome": classes.NOT_INTERPRETED, "step": None, "inconclusive_sizes": {}, "missing": [], "reasons": reasons,
                "scope": ["a gate to interpretation failed (ADR-0017 sections 3, 8.1, I.9): " + "; ".join(reasons) + "; the classes are descriptive until the auditor explains it and the human lead decides"],
            }  # fmt: skip
    return {
        "status": status, "interpretable": not incomplete and not reasons, "gate_reasons": reasons, "defects": defects,
        "g1_passed": g1, "g2_passed": g2, "g4_passed": g4, "analysis": analysis,
    }  # fmt: skip


def work_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "analysis.json"
    if target.exists():
        raise FileExistsError(target)
    cells = cells_for(args)
    updates = updates_for(args)
    expected = dry_cells() if args.dry else core.cells()
    missing: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    for cell in expected:
        path = core.eval_path(run_dir, cell.label, updates, "eval").with_name("eval.json")
        if path.is_file() and cell in cells:
            records[cell.label] = core.read_record(path, "eval")
        elif cell in cells:
            missing.append(cell.label)
    calibration = calibration_record_of(args)
    size_status: dict[int, str | None] = {}
    if calibration is not None:
        for s, labels in calibration["failed_sizes"].items():
            size_status[int(s)] = "+".join(labels)
    sizes = DRY_SLOTS if args.dry else core.SLOTS_BY_SIZE
    table = classes.measures_from_eval(records)
    lm = {
        (r["arm"], int(r["slots"]), int(r["seed"])): float(r["language_modelling"]["relative_rise"])
        for r in records.values()
        if "language_modelling" in r and tuple(r["parent"]) == core.PRIMARY_PARENT
    }
    gates_path = run_dir / "gates.json"
    gates = read_json(gates_path) if gates_path.is_file() else None
    manifests = [read_json(p) for p in sorted(run_dir.glob("*/manifest.json"))]
    failed_tasks = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"] if t["status"] != "completed")
    leakage = sorted(f"{r['label']}/{p}" for r in records.values() for p, panel in r["panels"].items() if panel.get("leakage"))
    verdict = assess(table=table, lm=lm, size_status=size_status, sizes=sizes, missing=missing, failed_tasks=failed_tasks, gates=gates, leakage=leakage)
    result, status = verdict["analysis"], verdict["status"]
    write_json(
        target,
        {
            **core.envelope("analysis"),
            "dry": bool(args.dry),
            "status": status,
            "interpretable": verdict["interpretable"],
            "gate_reasons": verdict["gate_reasons"],
            "updates": updates,
            "engineering_defects": verdict["defects"],
            "g1_passed": verdict["g1_passed"],
            "g2_passed": verdict["g2_passed"],
            "g4_passed": verdict["g4_passed"],
            "missing_cells": missing,
            "failed_tasks": failed_tasks,
            "leakage": leakage,
            "analysis": result,
            "cells_read": sorted(records),
            "calibration": calibration_binding(args),
            "identity": dict(core.code_identity()),
        },
    )
    print(json.dumps({"status": status, "outcome": result["selection"]["outcome"]}))
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
    "generate": work_generate,
    "gates": work_gates,
    "train": work_train,
    "evaluate": work_evaluate,
    "analyze": work_analyze,
    "report": work_report,
    "calibrate-cell": work_calibrate_cell,
    "calibrate-controls": work_calibrate_controls,
    "rehearse-cell": work_rehearse_cell,
}


# --- commands ---------------------------------------------------------------------------------------------------------------------
def new_run_dir(args: argparse.Namespace, stage: str) -> Path:
    run_dir = Path(args.run_dir) if args.run_dir else experiments_root(args) / core.run_name(stage)
    args.run_dir = str(run_dir)
    return run_dir


def cmd_generate(args: argparse.Namespace) -> int:
    if args.mode == REGISTERED and not args.i_understand_freeze_time:
        raise pool.StageRefused("refused: registered-seed generation is used at freeze time; add --i-understand-freeze-time")
    run_dir = new_run_dir(args, "generate")
    if (run_dir / "generate" / "manifest.json").exists() or (run_dir / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {run_dir} already holds generated data")
    manifest = single_task("generate", "generate", "generate", args, run_dir, run_dir / "data_manifest.json", skip_preconditions=True)  # generation precedes the freeze commit
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single_task("gates", "gates", "gates", args, run_dir, run_dir / "gates.json", ["--restore-split", str(args.restore_split)])
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_calibrate(args: argparse.Namespace) -> int:
    args.mode = CALIBRATION
    run_dir = new_run_dir(args, "calibrate")
    cells = dry_calibration_cells() if args.dry else core.calibration_cells()
    for c in cells:
        calibration_guard(c)
    identity = core.code_identity()
    tasks = [make_task("calibrate", "controls", worker_argv("calibrate-controls", *common_args(args)), run_dir, identity, run_dir / "calibration_controls.json")]
    tasks += [make_task("calibrate", c.label, worker_argv("calibrate-cell", "--label", c.label, *common_args(args)), run_dir, identity, core.cell_dir(run_dir, c.label) / "calibration_cell.json") for c in cells]
    manifest = run_stage_tasks("calibrate", args, tasks, run_dir)
    path = finalize_calibration(args, run_dir, cells)
    print(json.dumps({"calibration": str(path)}))
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_rehearse(args: argparse.Namespace) -> int:
    args.mode = REHEARSAL
    run_dir = new_run_dir(args, "rehearse")
    cells = cells_for(args)
    updates = args.updates if args.updates is not None else REHEARSAL_DEFAULT_UPDATES
    args.updates = updates
    manifest = run_cells("rehearse", "rehearse-cell", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "rehearsal.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_train(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)  # a gate failure seen before training stops the run; nothing is trained
    updates = remember_updates(args)
    run_dir.mkdir(parents=True, exist_ok=True)
    binding = calibration_binding(args)
    if binding is not None:
        if (run_dir / "calibration_binding.json").exists():
            check_binding(args, run_dir)
        else:
            write_json(run_dir / "calibration_binding.json", binding)
    elif args.mode == REGISTERED:
        raise pool.StageRefused("refused: a registered stage needs --calibration")
    if not (run_dir / "updates.json").exists():
        write_json(run_dir / "updates.json", {"updates": updates, "dry": bool(args.dry)})
    cells = cells_for(args)
    manifest = run_cells("train", "train", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "train.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    check_binding(args, run_dir)
    updates = remember_updates(args)
    cells = cells_for(args)
    manifest = run_cells("evaluate", "evaluate", args, cells, run_dir, lambda c: core.eval_path(run_dir, c.label, updates, "eval").with_name("eval.json"), previous="train")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    check_binding(args, run_dir)
    remember_updates(args)
    manifest = single_task("analyze", "analysis", "analyze", args, run_dir, run_dir / "analysis.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise pool.StageRefused("refused: the report runs once and never overwrites")
    manifest = single_task("report", "report", "report", args, run_dir, out / "results.json")
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_dry(args: argparse.Namespace) -> int:
    """Every stage, in order, at tiny size on test seeds in a temporary root, with a private ledger."""
    root = Path(args.out_root) if args.out_root else Path(tempfile.mkdtemp(prefix="p9i-dry-"))
    run_dir = root / "P9IDRY-run"
    if run_dir.exists():
        raise pool.StageRefused(f"refused: {run_dir} exists")
    shared = ["--dry", "--mode", CALIBRATION, "--experiments-root", str(root), "--ledger", str(root / "P9I-ledger.json"), "--workers", str(args.workers), "--stage-cap-seconds", str(args.stage_cap_seconds or 3600)]
    base = [*shared, "--run-dir", str(run_dir)]
    steps: list[tuple[str, list[str]]] = [
        ("generate", ["generate", *base]),
        ("calibrate", ["calibrate", *shared, "--run-dir", str(root / "P9IDRY-calibration")]),
        ("gates", ["gates", *base]),
        ("train", ["train", *base]),
        ("evaluate", ["evaluate", *base]),
        ("analyze", ["analyze", *base]),
        ("report", ["report", *base]),
    ]
    summary: dict[str, Any] = {"run_dir": str(run_dir), "banner": DRY_BANNER, "cells": [c.label for c in dry_cells()], "stages": {}}
    for name, argv in steps:
        code = main(argv)
        summary["stages"][name] = code
        if name in ("generate", "gates") and code != 0:
            break
    analysis = run_dir / "analysis.json"
    if analysis.is_file():
        data = read_json(analysis)
        summary["status"] = data["status"]
        summary["outcome"] = data["analysis"]["selection"]["outcome"]
    summary["report"] = str(run_dir / "results" / "RESULTS.md") if (run_dir / "results" / "results.json").is_file() else None
    summary["charged_seconds"] = core.Ledger(root / "P9I-ledger.json").charged()
    write_json(root / "DRY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["report"] else 1


# --- command line ----------------------------------------------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--run-dir", default=None)
    p.add_argument("--experiments-root", default=None)
    p.add_argument("--repo", default=None, help="repository to check for a registered stage (tests)")
    p.add_argument("--mode", choices=(REGISTERED, CALIBRATION, REHEARSAL), default=None)
    p.add_argument("--draw", type=int, default=2, help="rehearsal draw (0, 2..9; draw 1 is the calibration draw)")
    p.add_argument("--dry", action="store_true", help="the DRY profile (tiny sizes, test seeds; never registered)")
    p.add_argument("--synthetic-backbone", action="store_true", help="random stand-in backbone (DRY and tests only)")
    p.add_argument("--updates", type=int, default=None)
    p.add_argument("--freeze-commit", default=None)
    p.add_argument("--calibration", default=None, help="calibration record (selected U, failed sizes)")
    p.add_argument("--calibration-sha256", default=None, help="worker: the sha256 the calibration record must have")
    p.add_argument("--workers", type=int, default=core.WORKERS)
    p.add_argument("--stage-cap-seconds", type=float, default=None)
    p.add_argument("--rss-worker-bytes", type=int, default=core.RSS_WORKER_BYTES)
    p.add_argument("--rss-aggregate-bytes", type=int, default=core.RSS_AGGREGATE_BYTES)
    p.add_argument("--ledger", default=None, help="charged-time ledger (default <experiments>/P9I-ledger.json)")
    p.add_argument("--only", action="append", default=None, help="restrict a stage to these cell labels")
    p.add_argument("--group", action="append", default=None, help="restrict a stage to registry rows (e.g. core-16384)")
    p.add_argument("--label", default=None, help="worker commands: the cell")
    p.add_argument("--restore-split", type=int, default=16)
    p.add_argument("--results-dir", default=None)
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p9i.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", parents=[common])
    gen.add_argument("--i-understand-freeze-time", action="store_true")
    for name in ("calibrate", "rehearse", "gates", "train", "evaluate", "analyze", "report"):
        sub.add_parser(name, parents=[common])
    dry = sub.add_parser("dry", parents=[common])
    dry.add_argument("--out-root", default=None)
    work = sub.add_parser("work")
    wsub = work.add_subparsers(dest="worker", required=True)
    for name in WORKERS:
        wsub.add_parser(name, parents=[common])
    return parser


COMMANDS: dict[str, Any] = {
    "generate": cmd_generate,
    "calibrate": cmd_calibrate,
    "rehearse": cmd_rehearse,
    "gates": cmd_gates,
    "train": cmd_train,
    "evaluate": cmd_evaluate,
    "analyze": cmd_analyze,
    "report": cmd_report,
    "dry": cmd_dry,
}
DEFAULT_MODE = {"generate": CALIBRATION, "calibrate": CALIBRATION, "rehearse": REHEARSAL}


def main(argv: Sequence[str] | None = None) -> int:
    """Exit codes: 0 stage complete, 1 stage ran but a task or gate failed (records kept), 2 refused."""
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
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
        print(f"P9I stage REFUSED: {exc}", file=sys.stderr)
        return 2
    except CalibrationRefused as exc:
        print(f"P9I calibration REFUSED: {exc}", file=sys.stderr)
        return 2
    except StageError as exc:
        print(f"P9I stage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

