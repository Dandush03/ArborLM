# ruff: noqa: E501
"""P10S0 stages (ADR-0020 sections 9, 10, 13): ``generate`` (per draw), ``draw-plan``, ``check`` (the pipeline check), ``rehearse`` (twice, the second under busy processes), ``projection``,
``caps``, ``gates``, ``train`` (a block: Q1, WX, probe), ``q1-gate``, ``analyze``, ``report``, ``dry`` and ``registered`` (the driver the fixed launch scripts call).

Run from the repository root: ``uv run --locked python -m studies.p10s0.stages <command> ...``. Stages run through P9's job manager (``studies.p9.pool.run_stage``): immutable task ids, per-worker RSS cap
(3 GiB), aggregate cap (18 GiB, both read from ``configs/p10s0_addressing.toml``), failed records kept, a failed cell stops the cells that depend on it, nothing is re-run with changed settings. Workers are
single-thread subprocesses (six).

One budget: 16 charged hours (``core.Ledger``) covering the pipeline check, the rehearsal, the gates, generation and every registered block. A block starts only under the headroom rule of section 10.4
(reading A): ``budget.pre_q1_decision`` before Q1 (cut 3 is the only cut then) and ``budget.post_q1_decision`` after the Q1 gate (cuts 1 and then 2). Each block's own time cap is the frozen table's
(twice its rehearsed projection, per configuration), passed by the fixed launch scripts through ``--caps``.

Modes and seeds (``core.check_seed_set``). ``registered`` (needs ``--freeze-commit`` and a clean tree): ``p10s0-draw-k`` and ``p10s0-reserve-k``; ``check``: the pipeline-check draw only; ``rehearsal``: the
rehearsal draw only, writing nothing but the whitelisted records; ``dry``: test seeds 920001+ and a random synthetic backbone, tiny sizes.

Not run by this module's author: the pipeline check at real size, the gates on the rehearsal draw, the rehearsal and every registered stage.
"""

import argparse
import dataclasses
import functools
import json
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
from studies.p9ii import core as p9iicore

from . import analysis, arm_selection, budget, core, evaluate, gates, report, train
from . import classes as C

REGISTERED, CHECK, REHEARSAL, DRY = core.MODES
DRY_BANNER = "DRY: tiny synthetic sizes, random synthetic backbone, test seeds; not a measurement of anything"
DRY_FACTS = {2048: 128, 8192: 256, 32768: 512}  # the registered 1 : 4 : 16 proportions
DRY_UNIT = 8
DRY_DIAG_EVERY = 2
DRY_G1_PERMUTATIONS = 200
DRY_REHEARSAL_UPDATES = 4
SYNTHETIC_CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
PARENT = p9core.PRIMARY_PARENT
STAGE_GROUP = {"generate": "analyze", "gates": "train", "rehearse": "train", "check": "train", "train": "train", "evaluate": "evaluate", "analyze": "analyze", "report": "analyze"}
FREEZE_PLAN = core.FREEZE_DIR / "plan.json"
CAPS_FILE = str(core.FREEZE_DIR / "stage_caps.json")
ARM_SELECTION_FILE = core.FREEZE_DIR / "arm_selection.json"
REGISTERED_STAGES = ("gates", "q1", "q1_gate", "probe", "wx", "analysis", "report")
BLOCK_OF_STAGE = {"q1": "q1", "probe": "probe", "wx": "wx"}
BLOCK_LABEL = {"q1": "Q1", "probe": "PR", "wx": "WX"}


class StageError(RuntimeError):
    """A stage cannot start for a reason other than a pool refusal."""


def _utc() -> str:
    return datetime.now(UTC).isoformat()


# --- profile helpers ----------------------------------------------------------------------------------------------------------------------
def is_synthetic(args: argparse.Namespace) -> bool:
    return bool(args.dry or args.synthetic_backbone)


def unit_of(args: argparse.Namespace) -> int:
    return DRY_UNIT if args.dry else core.UPDATES


def diag_every_of(args: argparse.Namespace) -> int:
    return DRY_DIAG_EVERY if args.dry else core.DIAG_EVERY


def facts_of(args: argparse.Namespace, real: int) -> int:
    return DRY_FACTS[real] if args.dry else real


def experiments_root(args: argparse.Namespace) -> Path:
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def repo_of(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def ledger_root(args: argparse.Namespace) -> Path:
    return Path(args.ledger_root) if args.ledger_root else experiments_root(args)


def manifest_dir(run_dir: Path, name: str) -> Path:
    return run_dir / "draws" / name


def corpus_bytes(args: argparse.Namespace) -> bytes:
    return SYNTHETIC_CORPUS if is_synthetic(args) else p9core.load_trained_corpus(experiments_root(args))


@functools.cache
def _synthetic() -> Any:
    return controls.synthetic_backbone(*PARENT)


def backbone_for(args: argparse.Namespace) -> Any:
    return _synthetic() if is_synthetic(args) else controls.load_backbone(PARENT, experiments_root(args))[0]


@functools.cache
def _build_data(seeds: p9core.SeedSet, corpus: bytes, facts: int, dry: bool) -> data_mod.StudyData:
    sizes = data_mod.DataSizes(main_trained=facts, unseen=64, lane_d_per_set=128) if dry else data_mod.DataSizes(main_trained=facts)
    return data_mod.build_study_data(seeds, corpus, sizes=sizes)


def study_data(args: argparse.Namespace, spec: core.SeedSetSpec, real_facts: int) -> data_mod.StudyData:
    """The draw of ``spec`` for the ``real_facts`` fact set (2,048, 8,192 or 32,768; tiny stand-ins in DRY). The seed set must be allowed in the mode."""
    core.check_seed_set(args.mode, spec.name)
    study = _build_data(spec.seeds(real_facts), corpus_bytes(args), facts_of(args, real_facts), bool(args.dry))
    if args.mode == REGISTERED and study.pool != p9core.TEMPLATE_POOL:
        raise StageError("template pool differs from the registered pool (studies.p9.core.TEMPLATE_POOL)")
    return study


def require_draw_plan(run_dir: Path) -> dict[str, Any]:
    """A registered stage that reads data needs the draw plan (section 9): ``draw_plan.json`` present with ``ok`` true, and every seed set it names has a data manifest whose G1 passed on every fact set."""
    path = run_dir / "draw_plan.json"
    if not path.is_file():
        raise pool.StageRefused(f"refused: no draw plan at {path}: generate the draws and run draw-plan first")
    plan = core.read_record(path, "draw_plan")
    if plan.get("ok") is not True:
        raise pool.StageRefused(f"refused: the draw plan is not ok ({plan.get('reason')}); the matter returns to the human lead")
    for slot, name in sorted(plan["seed_set_of"].items(), key=lambda kv: int(kv[0])):
        manifest = manifest_dir(run_dir, name) / "data_manifest.json"
        if not manifest.is_file() or core.read_record(manifest, "data_manifest").get("g1_passed") is not True:
            raise pool.StageRefused(f"refused: draw {slot} ({name}) has no passed G1 record")
    return plan


def spec_for(args: argparse.Namespace, cell: core.Cell | None = None, *, draw: int | None = None, reserve: int | None = None, planned: bool = True) -> core.SeedSetSpec:
    """The seed set a command may use in its mode. A registered command reads the draw plan (``planned``; only generation does not)."""
    reserve = args.reserve if reserve is None else reserve
    if args.mode == DRY:
        return core.test_set(0)
    if args.mode == CHECK:
        return core.CHECK_SET
    if args.mode == REHEARSAL:
        return core.REHEARSAL_SET
    if reserve is not None:
        return core.reserve_set(reserve)
    k = draw if draw is not None else (cell.draw if cell is not None else args.draw)
    if not planned:
        return core.registered_set(k)
    if not args.run_dir:
        raise pool.StageRefused("refused: a registered command needs --run-dir (the draw plan lives there)")
    return core.set_of_name(require_draw_plan(Path(args.run_dir))["seed_set_of"][str(k)])


def verified_data(args: argparse.Namespace, spec: core.SeedSetSpec, real_facts: int, *, require_manifest: bool) -> data_mod.StudyData:
    """``study_data`` checked against the stream hashes of the draw's data manifest."""
    study = study_data(args, spec, real_facts)
    path = manifest_dir(Path(args.run_dir), spec.name) / "data_manifest.json"
    if path.is_file():
        if core.read_record(path, "data_manifest")["sha256s"][str(real_facts)] != study.sha256s():
            raise StageError(f"regenerated data differ from the hashes in {path}")
    elif require_manifest:
        raise StageError(f"no data manifest at {path}: run generate first")
    return study


def arm_selection_record(args: argparse.Namespace) -> dict[str, Any]:
    """The arm-selection record the stage was started with (``--arm-selection``; a registered stage reads the frozen file)."""
    path = Path(args.arm_selection) if args.arm_selection else repo_of(args) / ARM_SELECTION_FILE
    if args.arm_selection_sha256 and file_sha256(path) != args.arm_selection_sha256:
        raise pool.StageRefused(f"refused: {path} does not hash to the arm-selection record the stage was started with")
    record = read_json(path)
    if not isinstance(record, dict) or record.get("kind") != "arm_selection" or record.get("study") != core.STUDY:
        raise StageError(f"not an arm-selection record: {path}")
    return record


def require_gates_passed(run_dir: Path) -> dict[str, Any]:
    """A registered training starts only when the ``gates`` record exists and G1, G2, G4, G5, G6, G9 and G10 all passed."""
    path = run_dir / "gates.json"
    if not path.is_file():
        raise pool.StageRefused(f"refused: no gates record at {path}: run the gates stage first")
    record = core.read_record(path, "gates")
    failed = [n.upper() for n in analysis.GATES if record.get(f"{n}_passed") is not True]
    if failed:
        raise pool.StageRefused(f"refused: gate(s) {', '.join(failed)} did not pass; nothing is trained")
    return record


# --- cells of a block --------------------------------------------------------------------------------------------------------------------------
def block_cells_of(args: argparse.Namespace, block: str) -> list[core.Cell]:
    """Q1: the registry (cut 3 as the start record says); WX and the probe: the candidate the Q1 gate recorded (never chosen by hand); the pipeline check: its 3 cells."""
    if block == "check":
        cells = core.check_cells()
    elif block == "q1":
        cells = core.q1_cells(q1_cut3(args))
    else:
        cand = args.dry_candidate if args.dry and args.dry_candidate else None
        if cand is None:
            record = core.read_record(Path(args.run_dir) / "q1_gate.json", "q1_gate")
            if not record["blocks"][block]["run"]:
                raise pool.StageRefused(f"refused: {block} is not to run ({record['blocks'][block]['status']})")
            cand = record["candidate"]
        cells = core.wx_cells(cand) if block == "wx" else core.probe_cells(cand)
    if args.only:
        cells = [c for c in cells if c.label in set(args.only)]
    return cells


def q1_cut3(args: argparse.Namespace) -> bool:
    path = Path(args.run_dir) / "q1_start.json" if args.run_dir else None
    if path is not None and path.is_file():
        return bool(core.read_record(path, "q1_gate")["cut3"])
    return bool(getattr(args, "cut3", False))


# --- the pool -----------------------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/``, the S0 config, the ADR and every ``tests/test_p10s0_*`` equal their content at that
    commit, and ``frozen_input_check`` (src/arborlm, uv.lock, pyproject.toml, P8 digest) is ok. Returns the freeze identity (None for the other modes)."""
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
        if name.startswith("tests/test_p10s0_") and git(repo, "rev-parse", f"{full}:{name}").stdout != git(repo, "rev-parse", f"HEAD:{name}").stdout:
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise pool.StageRefused("refused: " + "; ".join(problems))
    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise pool.StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def limits(args: argparse.Namespace) -> dict[str, Any]:
    """Per-worker and aggregate RSS caps and the worker count, read from the config (``--rss-*`` override them downwards only in tests)."""
    lim = core.resource_limits(repo_of(args) / core.DEFAULT_CONFIG if (repo_of(args) / core.DEFAULT_CONFIG).is_file() else None)
    return {"rss_worker_bytes": int(args.rss_worker_bytes or lim["rss_worker_bytes"]), "rss_aggregate_bytes": int(args.rss_aggregate_bytes or lim["rss_aggregate_bytes"]), "workers": int(lim["workers"])}


def common_args(args: argparse.Namespace) -> list[str]:
    """Options every worker needs to rebuild the same draw (never a scientific value)."""
    out = ["--run-dir", str(args.run_dir), "--mode", args.mode, "--draw", str(args.draw), "--experiments-root", str(experiments_root(args))]
    if args.dry:
        out.append("--dry")
    if args.synthetic_backbone:
        out.append("--synthetic-backbone")
    if args.arm_selection:
        out += ["--arm-selection", str(args.arm_selection), "--arm-selection-sha256", file_sha256(Path(args.arm_selection))]
    if args.updates is not None:
        out += ["--updates", str(args.updates)]
    if args.reserve is not None:
        out += ["--reserve", str(args.reserve)]
    if args.dry_candidate:
        out += ["--dry-candidate", args.dry_candidate]
    if args.busy_processes:
        out += ["--busy-processes", str(args.busy_processes)]
    if args.repo:
        out += ["--repo", str(args.repo)]
    return out


def worker_argv(worker: str, *extra: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "studies.p10s0.stages", "work", worker, *extra)


def make_task(stage: str, label: str, argv: Sequence[str], run_dir: Path, identity: dict[str, str], result_path: Path, *, after: Sequence[str] = ()) -> pool.Task:
    if len(argv) < 5 or argv[1:3] != ("-m", "studies.p10s0.stages"):
        raise ValueError("worker argv must be '<python> -m studies.p10s0.stages work ...'")
    folder = run_dir / stage
    return pool.Task(
        task_id=pool.task_id(stage, label, cast(Any, identity)), stage=stage, label=label, argv=tuple(argv), depends_on=(), after=tuple(after),
        group=STAGE_GROUP[stage.split("-")[0]], result_path=result_path, failed_path=folder / f"{label}.failed.json", log_path=folder / f"{label}.log",
    )  # fmt: skip


def run_stage_tasks(stage: str, args: argparse.Namespace, tasks: Sequence[pool.Task], run_dir: Path, *, cap: float, completed_ids: Sequence[str] = (), workers: int | None = None, skip_preconditions: bool = False) -> dict[str, Any]:
    """Ledger check, preconditions, the pool, the ledger charge and the stage manifest (written once, with the environment)."""
    target = run_dir / stage / "manifest.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} already exists; a stage is run once and never overwritten")
    ledger = core.ledger_for(ledger_root(args))
    ledger.require_room(stage, cap)
    if not skip_preconditions:
        check_preconditions(args.mode, repo_of(args), args.freeze_commit)
    lim = limits(args)
    count = workers or args.workers or lim["workers"]
    if args.mode == REGISTERED and not 1 <= count <= core.WORKERS:
        raise pool.StageRefused(f"refused: {count} workers; P10S0 uses at most {core.WORKERS}")
    identity = core.code_identity()
    started = _utc()
    result = pool.run_stage(
        tasks, workers={"train": count, "evaluate": count, "analyze": 1}, stage_cap_seconds=cap, rss_worker_bytes=lim["rss_worker_bytes"], rss_aggregate_bytes=lim["rss_aggregate_bytes"],
        env={"PYTHONPATH": str(core.repo_root())}, completed_ids=list(completed_ids), total_remaining_seconds=ledger.remaining(),
    )  # fmt: skip
    ledger.charge(stage, run_dir.name, result.wall_seconds)
    pool_mode = {REGISTERED: "registered", REHEARSAL: "rehearsal"}.get(args.mode, "calibration")
    manifest = dict(pool.build_manifest(stage, run_dir, pool_mode, cast(Any, identity), tasks, result, started_utc=started, finished_utc=_utc(), workers=count, caps=pool.StageCaps(cap, lim["rss_worker_bytes"], lim["rss_aggregate_bytes"]).as_dict()))
    manifest["study"] = core.STUDY
    manifest["mode"] = args.mode
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


def cell_tasks(name: str, worker: str, args: argparse.Namespace, cells: Sequence[core.Cell], run_dir: Path, result_for: Any, *, previous: str | None = None) -> tuple[list[pool.Task], list[str]]:
    """One task per cell (DRY groups the cells of a draw into one task to keep its process count small); ``previous`` names the earlier stage whose manifest supplies the ``after`` dependency."""
    identity = core.code_identity()

    def task_label(c: core.Cell) -> str:
        return f"g-d{c.draw:02d}" if args.dry else c.label

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
        make_task(name, label, worker_argv(worker, "--labels", ",".join(m.label for m in members), *common_args(args)), run_dir, identity, result_for(members[-1]), after=[prior[label]] if label in prior else [])
        for label, members in groups.items()
    ]  # fmt: skip
    return tasks, completed


# --- job construction -------------------------------------------------------------------------------------------------------------------------
def init_seed_of(args: argparse.Namespace, cell: core.Cell, spec: core.SeedSetSpec) -> int:
    if args.mode == REGISTERED:
        return cell.init_seed
    if args.mode == CHECK:
        return core.CHECK_INIT
    if args.mode == REHEARSAL:
        return core.REHEARSAL_INIT
    return spec.base + 41 + cell.seed_index  # DRY: a test seed inside the test block


def build_job(args: argparse.Namespace, cell: core.Cell, study: data_mod.StudyData, spec: core.SeedSetSpec, out_dir: Path, *, mode: str | None = None, snapshots: Sequence[int] | None = None, max_updates: int | None = None, rehearsal_phase: str | None = None, extra: dict[str, Any] | None = None, whitelist_only: bool | None = None) -> train.Job:
    unit = unit_of(args)
    return train.Job(
        cell=cell, mode=mode or args.mode, data=study, stream=train.training_stream_for(study, facts_of(args, cell.facts)), backbone=backbone_for(args), out_dir=out_dir, init_seed=init_seed_of(args, cell, spec),
        r1_seed=study.seeds.r1_codes, target_seed=spec.target_seed(cell.celltype, cell.seed_index), hyper=core.HYPER, unit=unit, snapshots=tuple(snapshots) if snapshots is not None else cell.ct.readout_updates(unit),
        max_updates=max_updates, diag_every=diag_every_of(args), rehearsal_phase=rehearsal_phase, extra=extra or {}, whitelist_only=whitelist_only,
    )  # fmt: skip


def labels_of_args(args: argparse.Namespace) -> list[str]:
    if not args.labels:
        raise StageError("--labels is required")
    return [s for s in args.labels.split(",") if s]


# --- workers -----------------------------------------------------------------------------------------------------------------------------------
def work_generate(args: argparse.Namespace) -> int:
    """One draw (all three fact sets): generate, hash and G1-check it (not an observation of a seed by a model)."""
    spec = spec_for(args, reserve=args.reserve, planned=False)
    folder = manifest_dir(Path(args.run_dir), spec.name)
    target = folder / "data_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    folder.mkdir(parents=True, exist_ok=True)
    passed: dict[str, bool] = {}
    hashes: dict[str, Any] = {}
    seeds: dict[str, Any] = {}
    failed_checks: dict[str, list[str]] = {}
    for real in core.FACT_SETS:
        study = study_data(args, spec, real)
        g1 = data_mod.run_g1(study, permutations=DRY_G1_PERMUTATIONS if args.dry else None, train_epochs=None)
        write_json(folder / f"g1_{real}.json", g1)
        passed[str(real)] = bool(g1["passed"])
        hashes[str(real)] = study.sha256s()
        seeds[str(real)] = dataclasses.asdict(spec.seeds(real))
        failed_checks[str(real)] = [c["name"] for c in g1["checks"] if not c["passed"]]
    ok = all(passed.values())
    core.write_record(target, {**core.envelope("data_manifest"), "seed_set": spec.name, "seeds": seeds, "dry": bool(args.dry), "sha256s": hashes, "g1_passed": ok, "g1_by_fact_set": passed, "g1_failed_checks": failed_checks, "identity": core.code_identity(), "environment": core.environment()})
    print(json.dumps({"seed_set": spec.name, "g1_passed": ok}))
    return 0 if ok else 1


def work_gates(args: argparse.Namespace) -> int:
    """G1 (read from the draws' records), G2 (no-memory baseline at chance) for every registered draw and fact set, G4, G5 and G6 at real size on the gate draw of the mode (registered draw 1; the
    rehearsal draw in the rehearsal), G9 and G10. A harness error is recorded apart from a gate failure."""
    run_dir = Path(args.run_dir)
    target = run_dir / "gates.json"
    if target.exists():
        raise FileExistsError(target)
    spec = spec_for(args, draw=1)
    backbone = backbone_for(args)
    rows = evaluate.corpus_rows(corpus_bytes(args))
    datas = {real: verified_data(args, spec, real, require_manifest=args.mode == REGISTERED and not args.dry) for real in core.FACT_SETS}
    g1_by_draw: dict[str, bool | None] = {}
    g2_by_draw: dict[str, bool] = {}
    g2_all = True
    if args.mode == REGISTERED and not is_synthetic(args):
        plan = require_draw_plan(run_dir)
        for slot in range(1, core.N_DRAWS + 1):
            name = plan["seed_set_of"][str(slot)]
            g1_by_draw[str(slot)] = bool(core.read_record(manifest_dir(run_dir, name) / "data_manifest.json", "data_manifest")["g1_passed"])
            ok = True
            for real in core.FACT_SETS:
                study_k = verified_data(args, core.set_of_name(name), real, require_manifest=True)
                ok = ok and bool(evaluate.controls_record(study_k, {PARENT: backbone}, [real])["g2"]["passed"])
            g2_by_draw[str(slot)] = ok
        g1: bool | None = all(g1_by_draw.values())
        g2_all = all(g2_by_draw.values())
    else:
        manifest_path = manifest_dir(run_dir, spec.name) / "data_manifest.json"
        g1 = bool(core.read_record(manifest_path, "data_manifest")["g1_passed"]) if manifest_path.is_file() else None
        g1_by_draw = {"gate draw": g1}
        ok = True
        for real, study in datas.items():
            ok = ok and bool(evaluate.controls_record(study, {PARENT: backbone}, [facts_of(args, real)])["g2"]["passed"])
        g2_by_draw = {"gate draw": ok}
        g2_all = ok
    identity_data, identity_modes = None, None
    if not is_synthetic(args):
        identity_data = data_mod.build_study_data(p9core.rehearsal_seeds(p9iicore.REHEARSAL_SEED_SET), corpus_bytes(args), sizes=data_mod.DataSizes(main_trained=2048))
        identity_modes = (REHEARSAL, REHEARSAL)
    elif args.dry:
        identity_data = data_mod.build_study_data(p9iicore.test_seeds(1), corpus_bytes(args), sizes=data_mod.DataSizes(main_trained=DRY_FACTS[2048], unseen=64, lane_d_per_set=128))
        identity_modes = ("calibration", DRY)
    split = 4 if args.dry else args.restore_split
    init = spec.base + 41 if args.dry else (core.REHEARSAL_INIT if args.mode == REHEARSAL else core.INIT_SEEDS[0])
    result = gates.run_g4_g5_g6(
        datas, backbone, mode=DRY if args.dry else (REHEARSAL if args.mode == REHEARSAL else REGISTERED), restore_split=split, out_dir=run_dir / "gate_runs", init_seed=init, rows=rows, swap_seed=spec.swap_seed(2048),
        identity_data=identity_data, identity_modes=identity_modes, unit=unit_of(args), facts_of=lambda real: facts_of(args, real),
    )  # fmt: skip
    repo = repo_of(args)
    g9 = gates.g9_check(repo)
    record_sel = arm_selection_record(args) if (args.arm_selection or (repo / ARM_SELECTION_FILE).is_file()) else arm_selection.build_record(repo)
    g10 = gates.g10_check(record_sel, repo, run_script=not args.dry)
    core.write_record(target, core.jsonable({**core.envelope("gates"), "seed_set": spec.name, "g1_passed": g1, "g1_by_draw": g1_by_draw, "g2_passed": g2_all, "g2_by_draw": g2_by_draw, **result, "g9_passed": g9["passed"], "g9": g9, "g10_passed": g10["passed"], "g10": g10, "dry": bool(args.dry), "environment": core.environment(), "identity": core.code_identity()}))
    print(json.dumps({"g4_passed": result["g4_passed"], "g5_passed": result["g5_passed"], "g6_passed": result["g6_passed"], "g9_passed": g9["passed"], "g10_passed": g10["passed"], "g2_passed": g2_all, "defects": len(result["g4_defects"]), "harness_errors": len(result["harness_errors"])}))
    return 0 if result["g4_passed"] and result["g5_passed"] and result["g6_passed"] and g9["passed"] and g10["passed"] else 1


def work_train(args: argparse.Namespace) -> int:
    failed = 0
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
    for label in labels_of_args(args):
        cell = core.parse_label(label)
        spec = spec_for(args, cell)
        study = verified_data(args, spec, cell.facts, require_manifest=not args.dry and args.mode == REGISTERED)
        job = build_job(args, cell, study, spec, core.cell_dir(run_dir, label))
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
        spec = spec_for(args, cell)
        study = verified_data(args, spec, cell.facts, require_manifest=not args.dry and args.mode == REGISTERED)
        job = build_job(args, cell, study, spec, core.cell_dir(run_dir, label))
        try:
            evaluate.evaluate_cell(
                cell, run_dir, study, backbone_for(args), facts=facts_of(args, cell.facts), readouts=list(cell.ct.readout_updates(unit_of(args))), init_seed=job.init_seed, r1_seed=job.r1_seed, rows=rows,
                target_seed=job.target_seed, swap_seed=spec.swap_seed(cell.facts), require_train_record=True,
            )  # fmt: skip
            print(json.dumps({"label": label, "evaluated": True}))
        except Exception as exc:
            failed += 1
            print(json.dumps({"label": label, "evaluated": False, "reason": type(exc).__name__}))
    return 0 if not failed else 1


def _item_cell(item: budget.Item, args: argparse.Namespace) -> core.Cell:
    arm, ct, _ = item
    block = "WX" if core.is_wx(arm) else ("PR" if ct == "32K/64K" else "Q1")
    return core.make_cell(arm, ct, block, 1, 0, "REH-")


def work_rehearse_cell(args: argparse.Namespace) -> int:
    """One (arm, cell type, phase) of the matrix for ``--updates`` (256) updates in rehearsal mode (whitelisted record only), then the time of one full evaluation with the read swap. Nothing but
    time, memory, shapes, counts and identity is written; no loss or accuracy is read out."""
    arm, ct, phase = args.item.split(",")
    item = (arm, ct, phase)
    cell = _item_cell(item, args)
    run_dir = Path(args.run_dir)
    spec = spec_for(args)
    study = study_data(args, spec, cell.facts)
    out_dir = run_dir / "rehearsal" / budget.item_label(item)
    updates = args.updates if args.updates is not None else (DRY_REHEARSAL_UPDATES if args.dry else core.REHEARSAL_UPDATES)
    job = build_job(args, cell, study, spec, out_dir, mode=DRY if args.dry else REHEARSAL, snapshots=(), max_updates=updates, rehearsal_phase=None if phase == "main" else phase, extra={"busy_processes": args.busy_processes}, whitelist_only=True)
    run = train.run_job(job)
    started = time.monotonic()
    rows = evaluate.corpus_rows(corpus_bytes(args))
    evaluate.evaluate_readout(cell, run.model, study, facts_of(args, cell.facts), updates, frozen_backbone=job.backbone, rows=rows, target_seed=job.target_seed, swap_seed=spec.swap_seed(cell.facts))  # discarded
    wall = time.monotonic() - started
    train.write_rehearsal_record(out_dir / "rehearsal_evaluate.json", {**core.envelope("rehearsal"), "label": cell.label, "mode": "rehearsal" if not args.dry else "dry", "block": cell.block, "arm": arm, "celltype": ct, "slots": cell.slots, "facts": facts_of(args, cell.facts), "phase": phase, "identity": core.code_identity(), "updates": 0, "wall_seconds": wall, "evaluation_wall_seconds": wall, "peak_rss_bytes": train.peak_rss(), "seed_set": study.seeds.name})
    print(json.dumps({"item": budget.item_label(item), "evaluation_seconds": round(wall, 2)}))
    return 0


def work_analyze(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    target = run_dir / "analysis.json"
    if target.exists():
        raise FileExistsError(target)
    manifests = [read_json(p) for p in sorted(run_dir.glob("*/manifest.json"))]
    failed = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"] if t["status"] != "completed" and not str(m["stage"]).startswith("generate"))
    gates_path = run_dir / "gates.json"
    gates_rec = core.read_record(gates_path, "gates") if gates_path.is_file() else None
    plan_path = run_dir / "draw_plan.json"
    plan_rec = core.read_record(plan_path, "draw_plan") if plan_path.is_file() else None
    start = run_dir / "q1_start.json"
    cut3 = bool(core.read_record(start, "q1_gate")["cut3"]) if start.is_file() else bool(getattr(args, "cut3", False))
    gate_path = run_dir / "q1_gate.json"
    q1_gate = core.read_record(gate_path, "q1_gate") if gate_path.is_file() else None
    block_status = {b: q1_gate["blocks"][b]["status"] for b in ("wx", "probe") if q1_gate and not q1_gate["blocks"][b]["run"] and q1_gate["blocks"][b]["status"]} if q1_gate else {}
    mismatches = identity_mismatches(manifests)
    arm_sel = arm_selection_record(args)
    run = analysis.load_run(run_dir, arm_sel, cut3=cut3, unit=unit_of(args), failed_tasks=failed, gates=gates_rec, draw_plan=plan_rec, block_status=block_status, candidate_run=q1_gate["candidate"] if q1_gate else None, frozen_mismatch=mismatches)
    result = analysis.analyze(run)
    core.write_record(target, core.jsonable({**core.envelope("analysis"), "dry": bool(args.dry), "unit_updates": unit_of(args), "result": result, "draw_plan": plan_rec, "arm_selection_sha256": file_sha256(Path(args.arm_selection)) if args.arm_selection else None, "identity": core.code_identity(), "environment": core.environment()}))
    print(json.dumps({"outcome": result["outcome"]["outcome"], "row": result["outcome"]["row"]}))
    return 0


def identity_mismatches(manifests: Sequence[dict[str, Any]]) -> list[str]:
    """A stage whose recorded code identity differs from the running code's (ADR-0020 section 8.7 row 2: a difference between frozen and running code)."""
    now = core.code_identity()
    return [f"{m['stage']}: identity {k} differs" for m in manifests if not str(m["stage"]).startswith(("generate", "rehearse")) for k, v in (m.get("identity") or {}).items() if now.get(k) != v]


def work_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise FileExistsError(out / "results.json")
    paths = report.write_report(run_dir, out, banner=DRY_BANNER if args.dry else None)
    print(json.dumps({"written": [p.name for p in paths]}))
    return 0


WORKERS: dict[str, Any] = {"generate": work_generate, "gates": work_gates, "train": work_train, "evaluate": work_evaluate, "analyze": work_analyze, "report": work_report, "rehearse-cell": work_rehearse_cell}


# --- commands ------------------------------------------------------------------------------------------------------------------------------------
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
    spec = spec_for(args, reserve=args.reserve, planned=False)
    if (manifest_dir(run_dir, spec.name) / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {spec.name} is already generated in {run_dir}")
    manifest = single(f"generate-{spec.name}", "generate", args, run_dir, manifest_dir(run_dir, spec.name) / "data_manifest.json", skip_preconditions=True)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_draw_plan(args: argparse.Namespace) -> int:
    """Section 9: the plan of which seed set serves each draw slot, from the G1 records of the fifteen generated draws (a pure function)."""
    run_dir = Path(args.run_dir)
    g1: dict[str, bool] = {}
    for name in core.SET_NAMES:
        p = manifest_dir(run_dir, name) / "data_manifest.json"
        if p.is_file():
            g1[name] = bool(core.read_record(p, "data_manifest")["g1_passed"])
    plan = core.plan_draws(g1)
    core.write_record(run_dir / "draw_plan.json", {**core.envelope("draw_plan"), "ok": plan.ok, "seed_set_of": {str(k): v for k, v in plan.seed_set_of.items()}, "replacements": {str(k): v for k, v in plan.replacements.items()}, "labels": {str(k): core.replacement_label(v) for k, v in plan.replacements.items()}, "reason": plan.reason, "g1": g1})
    print(json.dumps({"ok": plan.ok, "replacements": plan.replacements, "reason": plan.reason}))
    return 0 if plan.ok else 1


def cmd_gates(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("gates", "gates", args, run_dir, run_dir / "gates.json", ["--restore-split", str(args.restore_split)])
    return 0 if manifest["status"] == "COMPLETE" else 1


def run_block(args: argparse.Namespace, block: str, *, cap_train: float | None = None, cap_eval: float | None = None) -> int:
    """Train then evaluate the cells of a block (Q1, WX, probe, check), charged to the one ledger."""
    run_dir = Path(args.run_dir)
    if args.mode == REGISTERED:
        require_gates_passed(run_dir)
        require_draw_plan(run_dir)
    cells = block_cells_of(args, block)
    unit = unit_of(args)
    tasks, _ = cell_tasks(f"train-{block}", "train", args, cells, run_dir, lambda c: core.cell_dir(run_dir, c.label) / "train.json")
    m1 = run_stage_tasks(f"train-{block}", args, tasks, run_dir, cap=stage_cap(args, cap_train))
    tasks2, completed = cell_tasks(f"evaluate-{block}", "evaluate", args, cells, run_dir, lambda c: core.eval_path(run_dir, c.label, c.ct.decisive(unit)), previous=f"train-{block}")
    m2 = run_stage_tasks(f"evaluate-{block}", args, tasks2, run_dir, cap=stage_cap(args, cap_eval), completed_ids=completed)
    return 0 if m1["status"] == "COMPLETE" and m2["status"] == "COMPLETE" else 1


def cmd_check(args: argparse.Namespace) -> int:
    """The pipeline check (section 10.1): A0, A6 and A7 at 2K/4K, one cell each, on the check draw. Their accuracies are not results and select nothing."""
    args.mode = DRY if args.dry else CHECK
    new_run_dir(args, "check")
    return run_block(args, "check")


def cmd_train(args: argparse.Namespace) -> int:
    return run_block(args, args.block)


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The rehearsal (section 10.3): every item of ``budget.rehearsal_items`` for ``--updates`` updates and one full evaluation, on the rehearsal draw. Run it twice: alone, and with ``--busy-processes 12``."""
    args.mode = DRY if args.dry else REHEARSAL
    run_dir = new_run_dir(args, "rehearse")
    items = budget.rehearsal_items(_candidates_of(args))
    identity = core.code_identity()
    tasks = [make_task("rehearse", budget.item_label(i), worker_argv("rehearse-cell", "--item", ",".join(i), *common_args(args)), run_dir, identity, run_dir / "rehearsal" / budget.item_label(i) / "rehearsal_evaluate.json") for i in items]
    busy = [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(args.busy_processes)]  # noqa: S603
    try:
        manifest = run_stage_tasks("rehearse", args, tasks, run_dir, cap=stage_cap(args))
    finally:
        for p in busy:
            p.kill()
            p.wait()
    return 0 if manifest["status"] == "COMPLETE" else 1


def _candidates_of(args: argparse.Namespace) -> tuple[str, ...]:
    if args.arm_selection:
        return tuple(arm_selection_record(args)["candidates"]["arms"])
    return core.CANDIDATE_ARMS


def read_rates(run_dir: Path, candidates: Sequence[str]) -> budget.Rates:
    trains, evals = [], []
    for item in budget.rehearsal_items(candidates):
        folder = run_dir / "rehearsal" / budget.item_label(item)
        if (folder / "rehearsal.json").is_file():
            trains.append(core.read_record(folder / "rehearsal.json", "rehearsal"))
        if (folder / "rehearsal_evaluate.json").is_file():
            e = core.read_record(folder / "rehearsal_evaluate.json", "rehearsal")
            e["label"] = trains[-1]["label"] if trains else e["label"]
            evals.append(e)
    manifest_path = run_dir / "rehearse" / "manifest.json"
    tasks: dict[str, dict[str, float]] = {}
    if manifest_path.is_file():  # the pool's task seconds minus the timed training and evaluation: the start-up time every registered task pays again
        tasks = {t["label"]: {"seconds": float(t["seconds"]), "peak_rss_bytes": float(t["peak_rss_bytes"])} for t in core.read_record(manifest_path, "stage_manifest")["tasks"]}
    return budget.rates_from_records(trains, evals, tasks)


def cmd_projection(args: argparse.Namespace) -> int:
    """The projection record of the two rehearsals (alone: ``--rehearsal-alone``; busy: ``--rehearsal-busy``): the larger rate of each item, the memory rule per block configuration, the projection of every
    block configuration and, for the freeze, the informational projection of WX and the probe at the most expensive candidate and whether the rule would hold after a Q1 that ran at its projection."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    cands = _candidates_of(args)
    alone, busy = read_rates(Path(args.rehearsal_alone), cands), read_rates(Path(args.rehearsal_busy), cands)
    rates = budget.merge_rates(alone, busy)
    missing = budget.missing_items(rates, cands)
    record: dict[str, Any] = {
        **core.envelope("projection"), "rates": {budget.item_label(i): dataclasses.asdict(r) for i, r in rates.items()}, "rates_alone": {budget.item_label(i): dataclasses.asdict(r) for i, r in alone.items()},
        "rates_busy": {budget.item_label(i): dataclasses.asdict(r) for i, r in busy.items()}, "missing_items": [budget.item_label(i) for i in missing], "candidates": list(cands),
        "memory": budget.memory_table(rates), "cost_differences": budget.cost_differences(rates), "arm_selection_sha256": file_sha256(Path(args.arm_selection)) if args.arm_selection else None, "environment": core.environment(),
        "note": "analytical projections from measured rehearsal rates (task start-up included); no efficiency claim; never a speedup",
    }  # fmt: skip
    if not missing:
        table = budget.projection_table(rates)
        record["table"] = table
        wx_arm, wx_s = budget.most_expensive(table, "wx", cands)
        pr_arm, pr_s = budget.most_expensive(table, "probe", cands)
        q1_s = float(table["q1:full"]["total_seconds"])
        other = core.PROJECTED_OTHER_HOURS * 3600.0
        record["freeze_information"] = {
            "wx_at_most_expensive_candidate": {"arm": wx_arm, "seconds": wx_s}, "probe_at_most_expensive_candidate": {"arm": pr_arm, "seconds": pr_s},
            "rule_holds_before_q1": budget.holds(0.0, [other, q1_s]), "rule_would_hold_after_q1_at_its_projection": budget.holds(other + q1_s, [wx_s, pr_s]),
            "projected_other_hours": core.PROJECTED_OTHER_HOURS, "kind": "information, not a start condition",
        }  # fmt: skip
    core.write_record(out, core.jsonable(record))
    print(json.dumps({"projection": str(out), "missing": len(missing), "sha256": file_sha256(out)}))
    return 0 if not missing else 1


def rates_of(projection: dict[str, Any]) -> budget.Rates:
    return {budget.parse_item_label(k): budget.Rate(**{f: v[f] for f in budget.Rate.__dataclass_fields__ if f in v}) for k, v in projection["rates"].items()}


def cmd_caps(args: argparse.Namespace) -> int:
    """Write the cap table of the freeze from a projection record (a pure function, ``budget.caps_table``)."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    projection = core.read_record(Path(args.projection), "projection")
    table = budget.caps_table(rates_of(projection), gates_wall_seconds=float(args.gates_wall_seconds), analysis_wall_seconds=float(args.analysis_wall_seconds), report_wall_seconds=float(args.report_wall_seconds), generate_wall_seconds=float(args.generate_wall_seconds))
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, core.jsonable(table))
    print(json.dumps({"caps": str(out), "sha256": file_sha256(out)}))
    return 0


def _stored_path(repo: Path, path: Path) -> str:
    """A path inside the repository is stored relative to it (so the plan survives a move of the checkout); any other (the run's projection in the experiments directory) is stored absolute."""
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path.resolve())


def cmd_freeze_plan(args: argparse.Namespace) -> int:
    """Write the freeze plan (``studies/p10s0/freeze/plan.json``) from files, never by hand: the sha256 of the arm-selection record, the projection record and the cap table, the registered run directory, the
    draw plan and the data manifest of all fifteen draw sets (read from the run directory, which must hold a draw plan that is ok with a passed G1 for every draw), and the projected seconds of the stages
    before Q1 that have not yet run (the gates: half of their cap). Refuses unless the projection was measured for this arm-selection record."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    repo, run_dir = repo_of(args), Path(args.run_dir)
    selection, projection = Path(args.arm_selection), Path(args.projection)
    caps_file = repo / CAPS_FILE
    if not caps_file.is_file():
        raise pool.StageRefused(f"refused: no cap table at {caps_file}: write it first (the caps command)")
    require_draw_plan(run_dir)
    proj = core.read_record(projection, "projection")
    if proj.get("arm_selection_sha256") != file_sha256(selection):
        raise pool.StageRefused("refused: the projection was not measured for this arm-selection record")
    if proj["missing_items"]:
        raise pool.StageRefused(f"refused: the projection has missing rehearsal items: {proj['missing_items'][:3]}")
    caps = read_json(caps_file)
    plan = {
        **core.envelope("freeze_plan"), "arm_selection": {"path": _stored_path(repo, selection), "sha256": file_sha256(selection)}, "projection": {"path": _stored_path(repo, projection), "sha256": file_sha256(projection)},
        "stage_caps_sha256": file_sha256(caps_file), "run_dir": str(run_dir.resolve()), "draw_plan": {"sha256": file_sha256(run_dir / "draw_plan.json")},
        "data_manifests": {name: file_sha256(manifest_dir(run_dir, name) / "data_manifest.json") for name in core.SET_NAMES},
        "before_q1_projected_seconds": {"gates": float(caps["gates"]) / core.HEADROOM}, "written_by": "studies.p10s0.stages freeze-plan",
    }  # fmt: skip
    core.write_record(out, plan)
    print(json.dumps({"plan": str(out), "sha256": file_sha256(out)}))
    return 0


def cmd_arm_selection(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    record = arm_selection.build_record(repo_of(args))
    write_json(out, core.jsonable(record))
    print(json.dumps({"arm_selection": str(out), "sha256": file_sha256(out), "printed": record["mapping_printed"]}))
    return 0 if record["mapping"]["steps_equal_table"] else 1


def cmd_q1_gate(args: argparse.Namespace) -> int:
    """The Q1 gate (section 8.5, 10.4): the candidate from Q1's records by the fixed rule, and the headroom re-check after Q1 with the actual candidate's rehearsed rates and the hours charged (cuts 1 and then
    2 as needed, ``budget.post_q1_decision``), and the memory rule per block. Written once as ``q1_gate.json``."""
    run_dir = Path(args.run_dir)
    target = run_dir / "q1_gate.json"
    if target.exists():
        raise pool.StageRefused(f"refused: {target} exists; a gate is computed once")
    projection = core.read_record(Path(args.projection), "projection") if args.projection else None
    sel = arm_selection_record(args)
    start = run_dir / "q1_start.json"
    cut3 = bool(core.read_record(start, "q1_gate")["cut3"]) if start.is_file() else False
    cut3 = cut3 or bool(getattr(args, "cut3", False))
    manifests = [read_json(p) for p in sorted(run_dir.glob("*/manifest.json"))]
    failed = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"] if t["status"] != "completed" and not str(m["stage"]).startswith("generate"))
    gates_rec = core.read_record(run_dir / "gates.json", "gates") if (run_dir / "gates.json").is_file() else None
    plan_path = run_dir / "draw_plan.json"
    run = analysis.load_run(run_dir, sel, cut3=cut3, unit=unit_of(args), failed_tasks=failed, gates=gates_rec, draw_plan=core.read_record(plan_path, "draw_plan") if plan_path.is_file() else None)
    result = analysis.analyze(run)
    record: dict[str, Any] = {**core.envelope("q1_gate"), "cut3": cut3, "environment": core.environment(), "outcome_row": result["outcome"]["row"], "outcome": result["outcome"]["outcome"], "candidate": None, "blocks": {"wx": {"run": False, "status": C.NOT_RUN_NO_CANDIDATE}, "probe": {"run": False, "status": C.NOT_RUN_NO_CANDIDATE}}}
    if result["outcome"]["row"] == 4:
        cand = result["outcome"]["arm"]
        record["candidate"] = cand
        if cand not in core.CANDIDATE_ARMS:
            record["note"] = "the candidate is not an arm that can still be the candidate: WX and the probe are not defined for it"
        elif projection is not None:
            ledger = core.ledger_for(ledger_root(args))
            table = projection["table"]
            decision = budget.post_q1_decision(ledger.charged(), float(table[f"wx:{cand}"]["total_seconds"]), float(table[f"probe:{cand}"]["total_seconds"]))
            memory = projection["memory"]
            wx_mem, pr_mem = memory[f"wx:{cand}"], memory[f"probe:{cand}"]
            wx_run, pr_run = decision.wx and wx_mem["ok"], decision.probe and pr_mem["ok"]
            record["blocks"] = {
                "wx": {"run": bool(wx_run), "status": None if wx_run else (decision.wx_status or budget.NOT_RUN_MEMORY)},
                "probe": {"run": bool(pr_run), "status": None if pr_run else (decision.probe_status or budget.NOT_RUN_MEMORY)},
            }
            record["headroom"] = {"cuts": list(decision.cuts), "charged_seconds": decision.charged_seconds, "wx_projection_seconds": table[f"wx:{cand}"]["total_seconds"], "probe_projection_seconds": table[f"probe:{cand}"]["total_seconds"], "memory": {"wx": wx_mem, "probe": pr_mem}}
        elif args.dry:
            record["blocks"] = {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}
    core.write_record(target, core.jsonable(record))
    print(json.dumps({"candidate": record["candidate"], "row": record["outcome_row"], "blocks": record["blocks"]}))
    return 0


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


# --- the registered driver (called by the fixed launch scripts) -------------------------------------------------------------------------------------------------
def load_plan(repo: Path) -> dict[str, Any]:
    """The frozen plan (``studies/p10s0/freeze/plan.json``): the arm-selection record, the projection record and the cap table, the draw plan and the data manifests, each with its sha256, and the registered
    run directory. Absent before the freeze: nothing registered then runs."""
    path = repo / FREEZE_PLAN
    if not path.is_file():
        raise pool.StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise pool.StageRefused("refused: the freeze plan is not an object")
    return plan


def verify_plan(plan: dict[str, Any], repo: Path, run_dir: Path) -> None:
    """Every identity the freeze recorded must hold now: the arm-selection, projection and cap-table files, the draw plan and the data manifest of every draw and reserve, and the run directory."""

    def check(path: Path, expected: str, what: str) -> None:
        if not path.is_file() or file_sha256(path) != expected:
            raise pool.StageRefused(f"refused: {path} does not hash to the frozen {what}")

    for key in ("arm_selection", "projection"):
        check(repo / plan[key]["path"] if not Path(plan[key]["path"]).is_absolute() else Path(plan[key]["path"]), plan[key]["sha256"], f"{key} record")
    check(repo / CAPS_FILE, plan["stage_caps_sha256"], "stage-cap table")
    if plan.get("run_dir") is not None and Path(plan["run_dir"]).resolve() != run_dir.resolve():
        raise pool.StageRefused(f"refused: the freeze names the run directory {plan['run_dir']}, not {run_dir}")
    check(run_dir / "draw_plan.json", plan["draw_plan"]["sha256"], "draw plan")
    for name, digest in plan["data_manifests"].items():
        check(manifest_dir(run_dir, name) / "data_manifest.json", digest, f"data manifest of {name}")
    if set(plan["data_manifests"]) != set(core.SET_NAMES):
        raise pool.StageRefused("refused: the freeze must name the data manifest of all thirteen draws and both reserves")
    projection = core.read_record(repo / plan["projection"]["path"] if not Path(plan["projection"]["path"]).is_absolute() else Path(plan["projection"]["path"]), "projection")
    if projection.get("arm_selection_sha256") != plan["arm_selection"]["sha256"]:
        raise pool.StageRefused("refused: the projection was not measured for the frozen arm-selection record")


def _path(repo: Path, p: str) -> Path:
    return Path(p) if Path(p).is_absolute() else repo / p


def block_cap(name: str, caps: dict[str, Any], key: str) -> Any:
    try:
        return budget.cap_for(caps, name, key)
    except budget.CapMissing as exc:
        raise pool.StageRefused(f"refused: {exc}") from exc


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name (``REGISTERED_STAGES``), with everything else (caps, projection, arm-selection record, seeds) from the frozen plan and the frozen cap table. The only free arguments are the run
    directory and the freeze commit; the launch scripts pass nothing else, and pass ``--caps`` (the stage caps, checked against the frozen file)."""
    if args.name not in REGISTERED_STAGES:
        raise pool.StageRefused(f"refused: unknown registered stage {args.name!r}")
    args.mode = REGISTERED
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    check_preconditions(REGISTERED, repo, args.freeze_commit)
    if args.caps != CAPS_FILE:
        raise pool.StageRefused(f"refused: the launch script must pass --caps {CAPS_FILE} (the stage caps are those of the frozen table)")
    plan = load_plan(repo)
    verify_plan(plan, repo, run_dir)
    caps = read_json(repo / CAPS_FILE)
    args.arm_selection = str(_path(repo, plan["arm_selection"]["path"]))
    args.arm_selection_sha256 = plan["arm_selection"]["sha256"]
    args.projection = str(_path(repo, plan["projection"]["path"]))
    args.workers = core.WORKERS
    projection = core.read_record(Path(args.projection), "projection")
    name = args.name
    ledger = core.ledger_for(ledger_root(args))
    if name == "gates":
        args.stage_cap_seconds = float(caps["gates"])
        return cmd_gates(args)
    if name == "q1":
        table = projection["table"]
        ran = {e["stage"] for e in ledger.entries()}
        before = sum(float(s) for st, s in (plan.get("before_q1_projected_seconds") or {}).items() if st not in ran)
        decision = budget.pre_q1_decision(ledger.charged(), before, float(table["q1:full"]["total_seconds"]), float(table["q1:cut3"]["total_seconds"]))
        if decision.action == "stop":
            raise pool.StageRefused(f"refused: {budget.NOT_RUN_BUDGET}: the headroom rule does not hold for Q1 even under cut 3 ({decision.required_seconds:.0f} s required with {decision.charged_seconds:.0f} s charged); nothing registered is run and the matter returns to the human lead")
        key = decision.action
        memory = projection["memory"][f"q1:{key}"]
        if not memory["ok"]:
            raise pool.StageRefused(f"refused: {budget.NOT_RUN_MEMORY}: Q1's rehearsal peak ({memory['peak_rss_bytes']} bytes) exceeds {memory['limit_bytes']} per worker (or an item is missing); nothing registered is run and the matter returns to the human lead")
        start = run_dir / "q1_start.json"
        if start.exists():
            raise pool.StageRefused("refused: Q1 was already started in this run directory")
        core.write_record(start, {**core.envelope("q1_gate"), "cut3": key == "cut3", "decision": decision._asdict(), "cut": decision.cut, "label": "cut 3: one initialization seed per draw at 8K/16K" if key == "cut3" else "no cut"})
        cap = block_cap("q1", caps, key)
        return run_block(args, "q1", cap_train=float(cap["train"]), cap_eval=float(cap["evaluate"]))
    if name == "q1_gate":
        return cmd_q1_gate(args)
    if name in ("wx", "probe"):
        record = core.read_record(run_dir / "q1_gate.json", "q1_gate")
        if not record["blocks"][name]["run"]:
            raise pool.StageRefused(f"refused: {name} is not to run: {record['blocks'][name]['status']}")
        cap = block_cap(name, caps, record["candidate"])
        return run_block(args, name, cap_train=float(cap["train"]), cap_eval=float(cap["evaluate"]))
    args.stage_cap_seconds = float(caps["analysis"] if name == "analysis" else caps["report"])
    return cmd_analyze(args) if name == "analysis" else cmd_report(args)


# --- the DRY stage --------------------------------------------------------------------------------------------------------------------------------------------
def cmd_dry(args: argparse.Namespace) -> int:
    """Every stage, in order, at tiny size on test seeds in a temporary root, with a private ledger: generate, the pipeline check, gates, rehearsal (alone), Q1 (all 230 cells), the Q1 gate, WX and the probe
    for the candidate named by ``--dry-candidate``, analysis and report. A tiny synthetic backbone: every arm is at chance, so the outcome is a status and no label is a result."""
    root = Path(args.out_root) if args.out_root else Path(tempfile.mkdtemp(prefix="p10s0-dry-"))
    run_dir = root / "P10S0DRY-run"
    if run_dir.exists():
        raise pool.StageRefused(f"refused: {run_dir} exists")
    root.mkdir(parents=True, exist_ok=True)
    selection = root / "arm_selection.json"
    write_json(selection, core.jsonable(arm_selection.build_record(repo_of(args))))
    shared = ["--dry", "--experiments-root", str(root), "--ledger-root", str(root), "--workers", str(args.workers), "--stage-cap-seconds", str(args.stage_cap_seconds or 3600), "--arm-selection", str(selection)]
    base = [*shared, "--run-dir", str(run_dir), "--mode", DRY]
    cand = args.dry_candidate or "A5-D"
    extra = ["--dry-candidate", cand]
    steps: list[tuple[str, list[str]]] = [
        ("generate", ["generate", *base]), ("check", ["check", *shared, "--run-dir", str(root / "P10S0DRY-check")]), ("gates", ["gates", *base]),
        ("rehearse", ["rehearse", *shared, "--run-dir", str(root / "P10S0DRY-rehearsal")]), ("q1", ["train", *base, "--block", "q1"]),
        ("q1_gate", ["q1-gate", *base, *extra]), ("wx", ["train", *base, "--block", "wx", *extra]), ("probe", ["train", *base, "--block", "probe", *extra]),
        ("analyze", ["analyze", *base]), ("report", ["report", *base]),
    ]  # fmt: skip
    summary: dict[str, Any] = {"run_dir": str(run_dir), "banner": DRY_BANNER, "stages": {}}
    for name, argv in steps:
        code = main(argv)
        summary["stages"][name] = code
        if name in ("generate", "gates") and code != 0:
            break
    analysis_path = run_dir / "analysis.json"
    if analysis_path.is_file():
        data = core.read_record(analysis_path, "analysis")
        summary["outcome"] = data["result"]["outcome"]["outcome"]
        summary["row"] = data["result"]["outcome"]["row"]
    summary["report"] = str(run_dir / "results" / "RESULTS.md") if (run_dir / "results" / "results.json").is_file() else None
    summary["charged_seconds"] = core.ledger_for(root).charged()
    write_json(root / "DRY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["report"] else 1


# --- command line --------------------------------------------------------------------------------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--run-dir", default=None)
    p.add_argument("--experiments-root", default=None)
    p.add_argument("--ledger-root", default=None, help="directory of the ledger (default: the experiments root)")
    p.add_argument("--repo", default=None, help="repository to check for a registered stage (tests)")
    p.add_argument("--mode", choices=core.MODES, default=None)
    p.add_argument("--draw", type=int, default=1, help="registered draw 1-13")
    p.add_argument("--reserve", type=int, default=None, help="registered reserve draw 1 or 2")
    p.add_argument("--dry", action="store_true", help="the DRY profile (tiny sizes, test seeds; never registered)")
    p.add_argument("--synthetic-backbone", action="store_true", help="random stand-in backbone (DRY and tests only)")
    p.add_argument("--block", choices=("check", "q1", "wx", "probe"), default="q1")
    p.add_argument("--updates", type=int, default=None, help="rehearsal updates")
    p.add_argument("--freeze-commit", default=None)
    p.add_argument("--caps", default=None, help="stage caps file of the freeze (fixed in the launch scripts)")
    p.add_argument("--arm-selection", default=None, help="the arm-selection record")
    p.add_argument("--arm-selection-sha256", default=None)
    p.add_argument("--projection", default=None, help="projection record of the rehearsals")
    p.add_argument("--rehearsal-alone", default=None)
    p.add_argument("--rehearsal-busy", default=None)
    p.add_argument("--busy-processes", type=int, default=0, help="rehearsal: busy single-thread processes alongside the six workers")
    p.add_argument("--workers", type=int, default=core.WORKERS)
    p.add_argument("--stage-cap-seconds", type=float, default=None)
    p.add_argument("--rss-worker-bytes", type=int, default=None)
    p.add_argument("--rss-aggregate-bytes", type=int, default=None)
    p.add_argument("--only", action="append", default=None, help="restrict a stage to these cell labels")
    p.add_argument("--labels", default=None, help="worker commands: comma-separated cell labels")
    p.add_argument("--item", default=None, help="rehearse-cell: arm,celltype,phase")
    p.add_argument("--restore-split", type=int, default=16)
    p.add_argument("--results-dir", default=None)
    p.add_argument("--out", default=None, help="caps, projection, arm-selection: where to write")
    p.add_argument("--gates-wall-seconds", type=float, default=0.0)
    p.add_argument("--analysis-wall-seconds", type=float, default=0.0)
    p.add_argument("--report-wall-seconds", type=float, default=0.0)
    p.add_argument("--generate-wall-seconds", type=float, default=0.0)
    p.add_argument("--dry-candidate", default=None, help="DRY only: the candidate whose WX and probe blocks are run")
    p.add_argument("--cut3", action="store_true", help="DRY and tests only: Q1 under cut 3")
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p10s0.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", parents=[common])
    gen.add_argument("--i-understand-freeze-time", action="store_true")
    for name in ("draw-plan", "caps", "freeze-plan", "projection", "arm-selection", "check", "rehearse", "gates", "train", "q1-gate", "analyze", "report"):
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
    "generate": cmd_generate, "draw-plan": cmd_draw_plan, "check": cmd_check, "rehearse": cmd_rehearse, "projection": cmd_projection, "caps": cmd_caps, "freeze-plan": cmd_freeze_plan, "arm-selection": cmd_arm_selection, "gates": cmd_gates,
    "train": cmd_train, "q1-gate": cmd_q1_gate, "analyze": cmd_analyze, "report": cmd_report, "registered": cmd_registered, "dry": cmd_dry,
}  # fmt: skip
DEFAULT_MODE = {"generate": CHECK, "check": CHECK, "rehearse": REHEARSAL}


def main(argv: Sequence[str] | None = None) -> int:
    """Exit codes: 0 stage complete, 1 stage ran but a task or gate failed (records kept), 2 refused."""
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.command == "registered":
        args.mode = REGISTERED
    if args.dry and args.mode in (REGISTERED, CHECK, REHEARSAL):
        print("refused: --dry cannot be combined with --mode registered, check or rehearsal", file=sys.stderr)
        return 2
    if args.mode is None:
        args.mode = DRY if args.dry else DEFAULT_MODE.get(args.command, REGISTERED)
    if args.dry:
        args.mode = DRY
    try:
        if args.command == "work":
            train.configure()
            return int(WORKERS[args.worker](args))
        if args.command == "dry":
            args.dry, args.mode = True, DRY
        elif args.run_dir is None and args.command not in ("check", "rehearse", "generate", "caps", "projection", "arm-selection"):
            raise StageError("--run-dir is required")
        return int(COMMANDS[args.command](args))
    except (pool.StageRefused, core.LedgerRefused) as exc:
        print(f"P10S0 stage REFUSED: {exc}", file=sys.stderr)
        return 2
    except StageError as exc:
        print(f"P10S0 stage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

