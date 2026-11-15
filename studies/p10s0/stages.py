# ruff: noqa: E501
"""P10S0 stages (ADR-0020 sections 9, 10, 13): ``generate`` (per draw), ``draw-plan``, ``check`` (the pipeline check), ``rehearse`` (twice, the second under busy processes), ``projection``,
``caps``, ``gates``, ``train`` (a block: Q1, WX, probe), ``q1-gate``, ``analyze``, ``report``, ``dry`` and ``registered`` (the driver the fixed launch scripts call).

Run from the repository root: ``uv run --locked python -m studies.p10s0.stages <command> ...``. Stages run through P9's job manager (``studies.p9.pool.run_stage``): immutable task ids, per-worker RSS cap
(3 GiB), aggregate cap (18 GiB, both read from ``configs/p10s0_qualification.toml``), failed records kept, a failed cell stops the cells that depend on it, nothing is re-run with changed settings. Workers are
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
import hmac
import json
import os
import secrets
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
def profile(args: argparse.Namespace) -> str:
    """'test' for a run directory carrying the TEST_PROFILE marker (the end-to-end exercise of the registered sequence on test seeds), else 'registered'."""
    return core.profile_of(getattr(args, "run_dir", None))


def tiny(args: argparse.Namespace) -> bool:
    """Tiny sizes, test seeds and a synthetic backbone: the DRY profile and the test profile of the registered sequence (never a registered or rehearsal seed)."""
    return bool(args.dry or profile(args) == "test")


def is_synthetic(args: argparse.Namespace) -> bool:
    return bool(args.dry or args.synthetic_backbone or profile(args) == "test")


def unit_of(args: argparse.Namespace) -> int:
    return DRY_UNIT if tiny(args) else core.UPDATES


def diag_every_of(args: argparse.Namespace) -> int:
    return DRY_DIAG_EVERY if tiny(args) else core.DIAG_EVERY


def facts_of(args: argparse.Namespace, real: int) -> int:
    return DRY_FACTS[real] if tiny(args) else real


def experiments_root(args: argparse.Namespace) -> Path:
    if args.mode == REGISTERED:  # fixed: a registered stage cannot be pointed elsewhere (the audit's M2)
        return core.default_experiments_root(repo_of(args))
    return Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()


def repo_of(args: argparse.Namespace) -> Path:
    return Path(args.repo) if args.repo else core.repo_root()


def ledger_root(args: argparse.Namespace) -> Path:
    if args.mode == REGISTERED:  # the one budget is the default root's (the audit's M2)
        return core.default_experiments_root(repo_of(args))
    return Path(args.ledger_root) if args.ledger_root else experiments_root(args)


def config_path(args: argparse.Namespace) -> Path | None:
    path = repo_of(args) / core.DEFAULT_CONFIG
    return path if path.is_file() else None


def ledger_of(args: argparse.Namespace) -> core.Ledger:
    """The one ledger, its hour cap read from the config of the repository in use (the one place the cap is set)."""
    return core.ledger_for(ledger_root(args), config_path(args))


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
    study = _build_data(spec.seeds(real_facts), corpus_bytes(args), facts_of(args, real_facts), tiny(args))
    if args.mode == REGISTERED and not tiny(args) and study.pool != p9core.TEMPLATE_POOL:
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
        return core.reserve_set(reserve, profile(args))
    k = draw if draw is not None else (cell.draw if cell is not None else args.draw)
    if not planned:
        return core.registered_set(k, profile(args))
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
        cand = args.dry_candidate if tiny(args) and args.dry_candidate else None
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
    plan_path = str(FREEZE_PLAN)
    if git(repo, "cat-file", "-e", f"{full}:{plan_path}").returncode != 0:
        raise pool.StageRefused(f"refused: {plan_path} does not exist at {full}: the freeze commit is the commit that adds the frozen plan")
    added = git(repo, "log", "--diff-filter=A", "--format=%H", "HEAD", "--", plan_path).stdout.decode().split()
    if not added or added[0] != full:  # the latest commit that added the plan (a file deleted and re-added has two)
        raise pool.StageRefused(f"refused: {full} is not the commit that added {plan_path}; HEAD itself is not a freeze")
    problems = [f"{p} at HEAD differs from the freeze commit" for p in ("studies", str(core.DEFAULT_CONFIG), core.SPEC) if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    names = set(git(repo, "ls-tree", "--name-only", "HEAD", "tests/").stdout.decode().split()) | set(git(repo, "ls-tree", "--name-only", full, "tests/").stdout.decode().split())
    for name in sorted(names):  # the union: a test added, changed or deleted after the freeze is refused
        if name.startswith("tests/test_p10s0_") and git(repo, "rev-parse", f"{full}:{name}").stdout != git(repo, "rev-parse", f"HEAD:{name}").stdout:
            problems.append(f"{name} differs from the freeze commit (changed, added or deleted)")
    if problems:
        raise pool.StageRefused("refused: " + "; ".join(problems))
    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise pool.StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


# --- registered mode: only through the driver, with the frozen plan, with no override ------------------------------------------------------------------------
REGISTERED_ALLOWED = {"command", "name", "run_dir", "freeze_commit", "caps", "mode"}
WORKER_ALLOWED = {"command", "worker", "run_dir", "mode", "draw", "reserve", "labels", "item", "arm_selection", "arm_selection_sha256", "freeze_commit", "experiments_root", "dry_candidate", "i_understand_freeze_time", "restore_split"}
GENERATE_ALLOWED = {"command", "mode", "draw", "reserve", "run_dir", "i_understand_freeze_time", "generation_cap_from_config"}


def override_violations(args: argparse.Namespace, allowed: set[str]) -> list[str]:
    """Every option of a registered command whose value differs from the parser's default and is not one the command may carry (the audit's M2). Any option, present or future, is covered: the comparison
    runs over every option of the common parser."""
    defaults = vars(_common_parser().parse_args([]))
    bad = []
    for dest, default in defaults.items():
        if dest in allowed:
            continue
        if getattr(args, dest, default) != default:
            bad.append("--" + dest.replace("_", "-"))
    return bad


def refuse_overrides(args: argparse.Namespace, allowed: set[str], what: str) -> None:
    bad = override_violations(args, allowed)
    if bad:
        raise pool.StageRefused(f"refused: {what} accepts no override of the frozen values; remove {', '.join(bad)}")


TOKEN_ENV = "P10S0_STAGE_TOKEN"
E2E_ENV = "P10S0_E2E_CLONE"  # set by the end-to-end harness in the clone's environment, never by a launch script
RUNNING_FILE = "RUNNING.json"
TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")


def is_temporary(path: Path) -> bool:
    """Whether ``path`` lies under a temporary directory (the system's, or /tmp, /var/folders)."""
    resolved = path.resolve()
    roots = {Path(tempfile.gettempdir()).resolve(), *(Path(r).resolve() for r in TEMP_ROOTS)}
    return any(resolved == r or r in resolved.parents for r in roots)


def refuse_registered_under_pytest(args: argparse.Namespace) -> None:
    """A registered path reached from a test refuses unless the repository and the run root are temporary directories (the re-check's N1): a test can never start a registered stage in the real tree."""
    if not os.environ.get("PYTEST_CURRENT_TEST") or args.mode != REGISTERED:
        return
    run_dir = Path(args.run_dir) if args.run_dir else experiments_root(args)
    for what, path in (("repository", repo_of(args)), ("run root", run_dir)):
        if not is_temporary(path):
            raise pool.StageRefused(f"refused: a registered path run from a test needs a temporary {what}, not {path}")


def running_path(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / RUNNING_FILE


def task_cells(tasks: Sequence[pool.Task]) -> list[str]:
    """Every cell label named by the ``--labels`` of the stage's tasks."""
    out: list[str] = []
    for task in tasks:
        argv = list(task.argv)
        if "--labels" in argv:
            out += [x for x in argv[argv.index("--labels") + 1].split(",") if x]
    return out


def registered_cell_labels() -> set[str]:
    """Every cell the frozen matrix can run: Q1 (full), and WX and the probe for each candidate arm."""
    labels = {c.label for c in core.q1_cells(False)}
    for cand in core.CANDIDATE_ARMS:
        labels |= {c.label for c in core.wx_cells(cand)} | {c.label for c in core.probe_cells(cand)}
    return labels


def require_stage_token(args: argparse.Namespace, worker: str) -> str:
    """A registered worker runs only inside a running stage of the driver (the re-check's N2): the token ``<stage>:<nonce>`` in the environment must match ``<run>/<stage>/RUNNING.json`` while the stage has no
    manifest, the stage must be of this worker's kind, and every cell it is given must be among the stage's tasks and in the frozen matrix. Returns the stage name."""
    token = os.environ.get(TOKEN_ENV, "")
    stage, _, nonce = token.partition(":")
    if not stage or not nonce:
        raise pool.StageRefused(f"refused: a registered worker runs only inside a running stage of the driver (no {TOKEN_ENV})")
    if stage.split("-")[0] != worker:
        raise pool.StageRefused(f"refused: the stage token is for stage {stage!r}, not for a {worker} worker")
    run_dir = Path(args.run_dir)
    path = running_path(run_dir, stage)
    if (run_dir / stage / "manifest.json").exists() or not path.is_file():
        raise pool.StageRefused(f"refused: stage {stage!r} is not running (no {RUNNING_FILE}, or it has a manifest)")
    record = read_json(path)
    if not hmac.compare_digest(str(record.get("nonce", "")), nonce) or record.get("stage") != stage:
        raise pool.StageRefused("refused: the stage token does not match the running stage")
    if args.labels:
        frozen = registered_cell_labels()
        for label in [x for x in args.labels.split(",") if x]:
            if label not in record.get("cells", []):
                raise pool.StageRefused(f"refused: cell {label} is not among the tasks of the running stage {stage!r}")
            if label not in frozen:
                raise pool.StageRefused(f"refused: cell {label} is not in the frozen matrix")
    return stage


def generation_guard(repo: Path) -> dict[str, Any]:
    """The checks of registered generation, shared by the command and the worker (the re-check's N2): the recorded acceptance of the P9-II outcome, the lead's run decision file, and a generation cap that is not provisional."""
    if not core.p9ii_acceptance(repo)["accepted"]:
        raise pool.StageRefused("refused: the human lead's acceptance of the P9-II outcome is not recorded in this tree (ADR-0019 section 16)")
    if not sorted((repo / "results").glob("p10s0-freeze-*/DECISION.md")):
        raise pool.StageRefused("refused: no recorded run decision (results/p10s0-freeze-<date>/DECISION.md): the lead's separate decision of ADR-0020 section 18 is required before registered generation")
    gen = core.generation_block(repo / core.DEFAULT_CONFIG)
    if gen["provisional"]:
        raise pool.StageRefused("refused: the generation cap in the config is provisional; set it from the rehearsal draw's measured time (set-generation-cap) before registered generation")
    return gen


def registered_state(args: argparse.Namespace) -> dict[str, Any]:
    """Preconditions (clean tree, the freeze commit that added the plan, frozen paths unchanged), then the frozen plan loaded and every identity in it verified against the run directory."""
    repo = repo_of(args)
    check_preconditions(REGISTERED, repo, args.freeze_commit)
    plan = load_plan(repo)
    verify_plan(plan, repo, Path(args.run_dir))
    return plan


def registered_worker_guard(args: argparse.Namespace) -> None:
    """Every worker started in registered mode re-checks the frozen plan, the freeze commit and the absence of overrides (the audit's M1, M2). Generation, which precedes the freeze, checks the overrides only."""
    if args.mode != REGISTERED:
        return
    refuse_registered_under_pytest(args)
    if args.worker == "generate":
        refuse_overrides(args, GENERATE_ALLOWED | WORKER_ALLOWED, "registered generation")
        generation_guard(repo_of(args))
        stage = require_stage_token(args, "generate")
        expected = f"generate-{spec_for(args, reserve=args.reserve, planned=False).name}"
        if stage != expected:
            raise pool.StageRefused(f"refused: the running stage is {stage!r}, not {expected!r}")
        return
    refuse_overrides(args, WORKER_ALLOWED, "a registered worker")
    require_stage_token(args, args.worker)
    if args.experiments_root not in (None, str(core.default_experiments_root(repo_of(args)))):
        raise pool.StageRefused("refused: a registered worker accepts no other experiments root")
    if args.dry_candidate and profile(args) != "test":
        raise pool.StageRefused("refused: --dry-candidate is for the test profile only")
    registered_state(args)


def limits(args: argparse.Namespace) -> dict[str, Any]:
    """Per-worker and aggregate RSS caps and the worker count, read from the config. In registered mode the config's values are the only ones (an override is refused before it gets here and ignored if it did)."""
    lim = core.resource_limits(config_path(args))
    if args.mode == REGISTERED:
        return {"rss_worker_bytes": int(lim["rss_worker_bytes"]), "rss_aggregate_bytes": int(lim["rss_aggregate_bytes"]), "workers": int(lim["workers"])}
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
    if args.freeze_commit:
        out += ["--freeze-commit", str(args.freeze_commit)]
    if args.i_understand_freeze_time:
        out.append("--i-understand-freeze-time")
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
    ledger = ledger_of(args)
    ledger.require_room(stage, cap)
    refuse_registered_under_pytest(args)
    if not skip_preconditions and args.mode == REGISTERED:
        registered_state(args)
    lim = limits(args)
    count = workers or args.workers or lim["workers"]
    if args.mode == REGISTERED and not 1 <= count <= core.WORKERS:
        raise pool.StageRefused(f"refused: {count} workers; P10S0 uses at most {core.WORKERS}")
    identity = core.code_identity()
    started = _utc()
    nonce = secrets.token_hex(16)
    marker = running_path(run_dir, stage)
    marker.parent.mkdir(parents=True, exist_ok=True)
    write_json(marker, {"stage": stage, "nonce": nonce, "task_labels": [t.label for t in tasks], "cells": task_cells(tasks), "started_utc": started})
    try:
        result = pool.run_stage(
            tasks, workers={"train": count, "evaluate": count, "analyze": 1}, stage_cap_seconds=cap, rss_worker_bytes=lim["rss_worker_bytes"], rss_aggregate_bytes=lim["rss_aggregate_bytes"],
            env={"PYTHONPATH": str(core.repo_root()), TOKEN_ENV: f"{stage}:{nonce}"}, completed_ids=list(completed_ids), total_remaining_seconds=ledger.remaining(),
        )  # fmt: skip
    finally:
        marker.unlink(missing_ok=True)
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
    if args.mode == REGISTERED:  # never a typed value: the frozen table's cap, set by the driver before this is called
        if default is None:
            raise pool.StageRefused("refused: a registered stage's cap is the frozen table's")
        return default
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
    registered_worker_guard(args)
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
        g1 = data_mod.run_g1(study, permutations=DRY_G1_PERMUTATIONS if tiny(args) else None, train_epochs=None)
        write_json(folder / f"g1_{real}.json", g1)
        passed[str(real)] = bool(g1["passed"])
        hashes[str(real)] = study.sha256s()
        seeds[str(real)] = dataclasses.asdict(spec.seeds(real))
        failed_checks[str(real)] = [c["name"] for c in g1["checks"] if not c["passed"]]
    ok = all(passed.values())
    core.write_record(target, {**core.envelope("data_manifest"), "seed_set": spec.name, "seeds": seeds, "dry": bool(args.dry), "profile": profile(args), "sha256s": hashes, "g1_passed": ok, "g1_by_fact_set": passed, "g1_failed_checks": failed_checks, "identity": core.code_identity(), "environment": core.environment()})
    print(json.dumps({"seed_set": spec.name, "g1_passed": ok}))
    return 0 if ok else 1


def gates_timing(args: argparse.Namespace, per_draw_seconds: float, total_seconds: float) -> dict[str, Any]:
    """The gates' timing. A registered gates run records the ratio of its measured per-draw time (thirteen draws) to the rehearsal draw's per-draw time the frozen cap table was measured on (the ratio the independent
    re-check observed was about 1.6; it is recorded here, measured, so the margin of the gates cap is visible)."""
    out: dict[str, Any] = {"per_draw_seconds": per_draw_seconds, "total_seconds": total_seconds, "draws_timed": core.N_DRAWS if args.mode == REGISTERED else 1}
    if args.mode == REGISTERED:
        caps_path = repo_of(args) / CAPS_FILE
        rehearsal = float((read_json(caps_path).get("measured") or {}).get("gates_per_draw", 0.0)) if caps_path.is_file() else 0.0
        out["rehearsal_per_draw_seconds"] = rehearsal
        out["registered_over_rehearsal_per_draw_ratio"] = per_draw_seconds / rehearsal if rehearsal > 0 else None
    return out


def work_gates(args: argparse.Namespace) -> int:
    """G1 (read from the draws' records), G2 (no-memory baseline at chance) for every registered draw and fact set, G4, G5 and G6 at real size on the gate draw of the mode (registered draw 1; the
    rehearsal draw in the rehearsal), G9 and G10. A harness error is recorded apart from a gate failure. The per-draw part (rebuild and hash-check of the three fact sets, G2) is timed: the registered gates
    do it for thirteen draws, and the gates cap is measured on that (the lead's ruling on M8). The exit code is 0 only if every gate passed, G1 and G2 included."""
    registered_worker_guard(args)
    run_dir = Path(args.run_dir)
    target = run_dir / "gates.json"
    if target.exists():
        raise FileExistsError(target)
    started = time.monotonic()
    spec = spec_for(args, draw=1)
    backbone = backbone_for(args)
    rows = evaluate.corpus_rows(corpus_bytes(args))
    t_draw = time.monotonic()
    datas = {real: verified_data(args, spec, real, require_manifest=args.mode == REGISTERED and not args.dry) for real in core.FACT_SETS}
    g1_by_draw: dict[str, bool | None] = {}
    g2_by_draw: dict[str, bool] = {}
    per_draw_seconds = 0.0
    if args.mode == REGISTERED:
        plan = require_draw_plan(run_dir)
        loop_started = time.monotonic()
        for slot in range(1, core.N_DRAWS + 1):
            name = plan["seed_set_of"][str(slot)]
            g1_by_draw[str(slot)] = bool(core.read_record(manifest_dir(run_dir, name) / "data_manifest.json", "data_manifest")["g1_passed"])
            ok = True
            for real in core.FACT_SETS:
                study_k = verified_data(args, core.set_of_name(name), real, require_manifest=True)
                ok = ok and bool(evaluate.controls_record(study_k, {PARENT: backbone}, [facts_of(args, real)])["g2"]["passed"])
            g2_by_draw[str(slot)] = ok
        per_draw_seconds = (time.monotonic() - loop_started) / core.N_DRAWS
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
        per_draw_seconds = time.monotonic() - t_draw  # one draw: three fact sets rebuilt and hash-checked, G2 on each
    identity_data, identity_modes = None, None
    if not is_synthetic(args):
        identity_data = data_mod.build_study_data(p9core.rehearsal_seeds(p9iicore.REHEARSAL_SEED_SET), corpus_bytes(args), sizes=data_mod.DataSizes(main_trained=2048))
        identity_modes = (REHEARSAL, REHEARSAL)
    elif tiny(args):
        identity_data = data_mod.build_study_data(p9iicore.test_seeds(1), corpus_bytes(args), sizes=data_mod.DataSizes(main_trained=DRY_FACTS[2048], unseen=64, lane_d_per_set=128))
        identity_modes = ("calibration", DRY)
    split = 4 if tiny(args) else args.restore_split
    init = spec.base + 41 if tiny(args) else (core.REHEARSAL_INIT if args.mode == REHEARSAL else core.INIT_SEEDS[0])
    result = gates.run_g4_g5_g6(
        datas, backbone, mode=DRY if args.dry else (REHEARSAL if args.mode == REHEARSAL else REGISTERED), restore_split=split, out_dir=run_dir / "gate_runs", init_seed=init, rows=rows, swap_seed=spec.swap_seed(2048),
        identity_data=identity_data, identity_modes=identity_modes, unit=unit_of(args), facts_of=lambda real: facts_of(args, real),
    )  # fmt: skip
    repo = repo_of(args)
    g9 = gates.g9_check(repo)
    record_sel = arm_selection_record(args) if (args.arm_selection or (repo / ARM_SELECTION_FILE).is_file()) else arm_selection.build_record(repo)
    pinned = None
    if args.mode == REGISTERED:
        pinned = load_plan(repo).get("pinned_auditor_scripts")
    g10 = gates.g10_check(record_sel, repo, run_script=not tiny(args), pinned=pinned)
    passed = bool(result["g4_passed"] and result["g5_passed"] and result["g6_passed"] and g9["passed"] and g10["passed"] and g1 is True and g2_all)
    core.write_record(target, core.jsonable({**core.envelope("gates"), "seed_set": spec.name, "g1_passed": g1, "g1_by_draw": g1_by_draw, "g2_passed": g2_all, "g2_by_draw": g2_by_draw, **result, "g9_passed": g9["passed"], "g9": g9, "g10_passed": g10["passed"], "g10": g10, "dry": bool(args.dry), "profile": profile(args), "timing": gates_timing(args, per_draw_seconds, time.monotonic() - started), "environment": core.environment(), "identity": core.code_identity()}))
    print(json.dumps({"g1_passed": g1, "g4_passed": result["g4_passed"], "g5_passed": result["g5_passed"], "g6_passed": result["g6_passed"], "g9_passed": g9["passed"], "g10_passed": g10["passed"], "g2_passed": g2_all, "defects": len(result["g4_defects"]), "harness_errors": len(result["harness_errors"]), "per_draw_seconds": round(per_draw_seconds, 2)}))
    return 0 if passed else 1


def work_train(args: argparse.Namespace) -> int:
    registered_worker_guard(args)
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
    registered_worker_guard(args)
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
    registered_worker_guard(args)
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
    acceptance = core.p9ii_acceptance(repo_of(args))
    run = analysis.load_run(run_dir, arm_sel, cut3=cut3, unit=unit_of(args), failed_tasks=failed, gates=gates_rec, draw_plan=plan_rec, block_status=block_status, candidate_run=q1_gate["candidate"] if q1_gate else None, frozen_mismatch=mismatches, acceptance=acceptance)
    result = analysis.analyze(run)
    core.write_record(target, core.jsonable({**core.envelope("analysis"), "dry": bool(args.dry), "profile": profile(args), "unit_updates": unit_of(args), "result": result, "draw_plan": plan_rec, "arm_selection_sha256": file_sha256(Path(args.arm_selection)) if args.arm_selection else None, "identity": core.code_identity(), "environment": core.environment()}))
    core.emit_stdout({"outcome": result["outcome"]["outcome"], "row": result["outcome"]["row"], "arm": result["outcome"].get("arm")})
    return 0


def identity_mismatches(manifests: Sequence[dict[str, Any]]) -> list[str]:
    """A stage whose recorded code identity differs from the running code's (ADR-0020 section 8.7 row 2: a difference between frozen and running code)."""
    now = core.code_identity()
    return [f"{m['stage']}: identity {k} differs" for m in manifests if not str(m["stage"]).startswith(("generate", "rehearse")) for k, v in (m.get("identity") or {}).items() if now.get(k) != v]


def work_report(args: argparse.Namespace) -> int:
    registered_worker_guard(args)
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise FileExistsError(out / "results.json")
    paths = report.write_report(run_dir, out, banner=DRY_BANNER if args.dry else None)  # the profile is read from the analysis record
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
    """Generate one draw (all three fact sets). Registered generation precedes the freeze and is guarded in code (the audit's m13): the explicit freeze-time flag, the flag that takes the stage cap from the
    config (a typed cap is refused: the cap is 2 x the rehearsal draw's measured generation time, set in the config by the rehearsal; the freeze refuses while it is provisional), no other override, the recorded
    acceptance of the P9-II outcome, and the lead's recorded decision file ``results/p10s0-freeze-*/DECISION.md``."""
    gen_cap = 0.0
    if args.mode == REGISTERED:
        if not args.i_understand_freeze_time:
            raise pool.StageRefused("refused: registered-seed generation is used at freeze time; add --i-understand-freeze-time")
        if not args.generation_cap_from_config:
            raise pool.StageRefused("refused: registered generation takes its stage cap from the config: pass --generation-cap-from-config (and no --stage-cap-seconds)")
        refuse_overrides(args, GENERATE_ALLOWED, "registered generation")
        refuse_registered_under_pytest(args)
        gen_cap = float(generation_guard(repo_of(args))["cap_seconds"])
    run_dir = new_run_dir(args, "generate")
    spec = spec_for(args, reserve=args.reserve, planned=False)
    if (manifest_dir(run_dir, spec.name) / "data_manifest.json").exists():
        raise pool.StageRefused(f"refused: {spec.name} is already generated in {run_dir}")
    manifest = single(f"generate-{spec.name}", "generate", args, run_dir, manifest_dir(run_dir, spec.name) / "data_manifest.json", skip_preconditions=True, cap=gen_cap if args.mode == REGISTERED else None)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_draw_plan(args: argparse.Namespace) -> int:
    """Section 9: the plan of which seed set serves each draw slot, from the G1 records of the fifteen generated draws (a pure function)."""
    run_dir = Path(args.run_dir)
    g1: dict[str, bool] = {}
    prof = core.profile_of(run_dir)
    for name in core.set_names(prof):
        p = manifest_dir(run_dir, name) / "data_manifest.json"
        if p.is_file():
            g1[name] = bool(core.read_record(p, "data_manifest")["g1_passed"])
    plan = core.plan_draws(g1, prof)
    core.write_record(run_dir / "draw_plan.json", {**core.envelope("draw_plan"), "ok": plan.ok, "seed_set_of": {str(k): v for k, v in plan.seed_set_of.items()}, "replacements": {str(k): v for k, v in plan.replacements.items()}, "labels": {str(k): core.replacement_label(v) for k, v in plan.replacements.items()}, "reason": plan.reason, "g1": g1})
    print(json.dumps({"ok": plan.ok, "replacements": plan.replacements, "reason": plan.reason}))
    return 0 if plan.ok else 1


def cmd_gates(args: argparse.Namespace, cap: float | None = None) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("gates", "gates", args, run_dir, run_dir / "gates.json", ["--restore-split", str(args.restore_split)], cap=cap)
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


def spawn_busy(count: int) -> list[subprocess.Popen[bytes]]:
    """``count`` busy single-thread processes (other studies' workers on the same machine, section 10.3)."""
    return [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(count)]  # noqa: S603


def stop_busy(procs: Sequence[subprocess.Popen[bytes]]) -> None:
    for p in procs:
        p.kill()
        p.wait()


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The rehearsal (section 10.3): every item of ``budget.rehearsal_items`` for ``--updates`` updates and one full evaluation, on the rehearsal draw. Run it twice: alone, and with ``--busy-processes N``
    (12 in the registered plan; other studies' workers may be training on the same machine). ``--only`` restricts it to named items (tests)."""
    args.mode = DRY if args.dry else REHEARSAL
    run_dir = new_run_dir(args, "rehearse")
    items = budget.rehearsal_items(_candidates_of(args))
    if args.only:
        items = [i for i in items if budget.item_label(i) in set(args.only)]
    identity = core.code_identity()
    tasks = [make_task("rehearse", budget.item_label(i), worker_argv("rehearse-cell", "--item", ",".join(i), *common_args(args)), run_dir, identity, run_dir / "rehearsal" / budget.item_label(i) / "rehearsal_evaluate.json") for i in items]
    busy = spawn_busy(args.busy_processes)
    try:
        manifest = run_stage_tasks("rehearse", args, tasks, run_dir, cap=stage_cap(args))
    finally:
        stop_busy(busy)
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


def measure_guard_seconds(repo: Path) -> float:
    """What a registered task pays that a rehearsal task does not: the worker's re-check of the freeze (git status, the frozen-input hashes of src/, the hashing of the frozen files and of fifteen manifests).
    Measured here on the current tree and added to every item's task overhead in the projection, so that the caps cover it (the audit's B1 in P9-II: a projection must include what a registered task pays)."""
    started = time.monotonic()
    git(repo, "status", "--porcelain", "--untracked-files=all")
    p9core.frozen_input_check(repo, "HEAD")
    for rel in (str(core.DEFAULT_CONFIG), str(CAPS_FILE), str(ARM_SELECTION_FILE), core.SPEC):
        if (repo / rel).is_file():
            file_sha256(repo / rel)
    for _ in range(len(core.SET_NAMES)):
        git(repo, "rev-parse", "HEAD:studies")
    return time.monotonic() - started


def cmd_projection(args: argparse.Namespace) -> int:
    """The projection record of the two rehearsals (alone: ``--rehearsal-alone``; busy: ``--rehearsal-busy``): the larger rate of each item, the memory rule per block configuration, the projection of every
    block configuration and, for the freeze, the informational projection of WX and the probe at the most expensive candidate and whether the rule would hold after a Q1 that ran at its projection."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    cands = _candidates_of(args)
    alone, busy = read_rates(Path(args.rehearsal_alone), cands), read_rates(Path(args.rehearsal_busy), cands)
    guard = measure_guard_seconds(repo_of(args))
    rates = {k: dataclasses.replace(v, task_overhead_seconds=v.task_overhead_seconds + guard) for k, v in budget.merge_rates(alone, busy).items()}
    missing = budget.missing_items(rates, cands)
    record: dict[str, Any] = {
        **core.envelope("projection"), "rates": {budget.item_label(i): dataclasses.asdict(r) for i, r in rates.items()}, "rates_alone": {budget.item_label(i): dataclasses.asdict(r) for i, r in alone.items()},
        "rates_busy": {budget.item_label(i): dataclasses.asdict(r) for i, r in busy.items()}, "missing_items": [budget.item_label(i) for i in missing], "candidates": list(cands),
        "unit_updates": unit_of(args), "guard_seconds_per_task": guard, "memory": budget.memory_table(rates), "cost_differences": budget.cost_differences(rates), "arm_selection_sha256": file_sha256(Path(args.arm_selection)) if args.arm_selection else None, "environment": core.environment(),
        "note": "analytical projections from measured rehearsal rates (task start-up included); no efficiency claim; never a speedup",
    }  # fmt: skip
    if not missing:
        table = budget.projection_table(rates, unit=unit_of(args))
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
    """Write the cap table of the freeze from a projection record (a pure function, ``budget.caps_table``). The gates cap is measured on thirteen draws x three fact sets: the rehearsal-draw gates' wall time plus
    twelve more of its per-draw part (``--gates-per-draw-seconds``, from ``gates.json`` of the rehearsal draw); the analysis and report times are also the reserve the headroom rule counts (the lead's ruling on M6)."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    if float(args.gates_per_draw_seconds) <= 0 or float(args.analysis_wall_seconds) <= 0 or float(args.report_wall_seconds) <= 0 or float(args.gates_wall_seconds) <= 0 or float(args.generate_wall_seconds) <= 0:
        raise pool.StageRefused("refused: the caps need the measured wall seconds of the gates (and one draw's share), generation, analysis and report: every one is positive")
    projection = core.read_record(Path(args.projection), "projection")
    if int(projection.get("unit_updates", core.UPDATES)) != unit_of(args):
        raise pool.StageRefused("refused: the projection was measured at another update unit (use --dry for a DRY projection and not for a real one)")
    table = budget.caps_table(rates_of(projection), gates_wall_seconds=float(args.gates_wall_seconds), gates_per_draw_seconds=float(args.gates_per_draw_seconds), analysis_wall_seconds=float(args.analysis_wall_seconds), report_wall_seconds=float(args.report_wall_seconds), generate_wall_seconds=float(args.generate_wall_seconds), unit=unit_of(args))
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
    draw plan and the data manifest of all fifteen draw sets (read from the run directory, which must hold a draw plan that is ok with a passed G1 for every draw), the pinned hashes of the auditor's script
    that G10 executes and of its sibling, the projected seconds of the stages before Q1 that have not yet run (the gates, measured on thirteen draws) and the rehearsed analysis and report seconds (the reserve
    the headroom rule counts). It refuses while the generation cap in the config is provisional, unless the projection was measured for this arm-selection record, and when the run directory's profile
    (the TEST_PROFILE marker of the end-to-end exercise) and ``--test-profile`` disagree. Nothing that is written after the freeze (the ledger, gates, results, the run decision) is hashed into it."""
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    repo, run_dir = repo_of(args), Path(args.run_dir)
    prof = core.profile_of(run_dir)
    if args.test_profile and not os.environ.get(E2E_ENV):
        raise pool.StageRefused(f"refused: --test-profile is for the end-to-end exercise only ({E2E_ENV} is set by it)")
    if (prof == "test") != bool(args.test_profile):
        raise pool.StageRefused("refused: the run directory's profile and --test-profile disagree (a real freeze has no TEST_PROFILE marker and no --test-profile)")
    if args.test_candidate and prof != "test":
        raise pool.StageRefused("refused: --test-candidate is for the test profile only")
    if args.test_candidate and args.test_candidate not in core.CANDIDATE_ARMS:
        raise pool.StageRefused(f"refused: --test-candidate must be one of {core.CANDIDATE_ARMS}")
    gen = core.generation_block(repo / core.DEFAULT_CONFIG)
    if gen["provisional"]:
        raise pool.StageRefused("refused: the generation cap in the config is provisional: set it from the rehearsal draw's measured generation time (set-generation-cap) and commit the config before the freeze")
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
    if "generate" not in caps or float(caps["generate"]) != float(gen["cap_seconds"]):
        raise pool.StageRefused("refused: the cap table's generate entry (" + str(caps.get("generate")) + ") is not the config's generation cap (" + str(gen["cap_seconds"]) + "): both come from the rehearsal draw's measured generation time")
    auditor = repo / gates.AUDITOR_SCRIPT
    pins = {f.name: file_sha256(f) for f in (auditor, auditor.parent / "c2_mapping_enumeration.py") if f.is_file()}
    if len(pins) != 2:
        raise pool.StageRefused("refused: the auditor's script and its sibling must exist to be pinned")
    plan = {
        **core.envelope("freeze_plan"), "profile": prof, "arm_selection": {"path": _stored_path(repo, selection), "sha256": file_sha256(selection)}, "projection": {"path": _stored_path(repo, projection), "sha256": file_sha256(projection)},
        "stage_caps_sha256": file_sha256(caps_file), "run_dir": str(run_dir.resolve()), "draw_plan": {"sha256": file_sha256(run_dir / "draw_plan.json")}, "generation": gen,
        "data_manifests": {name: file_sha256(manifest_dir(run_dir, name) / "data_manifest.json") for name in core.set_names(prof)},
        "pinned_auditor_scripts": pins, "before_q1_projected_seconds": {"gates": float(caps["measured"]["gates"])}, "reserve_analysis_report_seconds": frozen_reserve(caps),
        "test_candidate": args.test_candidate, "written_by": "studies.p10s0.stages freeze-plan",
    }  # fmt: skip
    core.write_record(out, plan)
    print(json.dumps({"plan": str(out), "sha256": file_sha256(out), "profile": prof}))
    return 0


def cmd_set_generation_cap(args: argparse.Namespace) -> int:
    """Set the generation cap in the config from the rehearsal draw's measured generation time (the lead's ruling on item 2): cap = max(60 s, 2 x the measured seconds of the task that generated the three
    fact sets of the rehearsal draw, ``--generate-manifest``). The config is hashed: do this before the freeze commit; the freeze refuses while the block is provisional."""
    repo = repo_of(args)
    manifest = core.read_record(Path(args.generate_manifest), "stage_manifest")
    if manifest["status"] != "COMPLETE" or not str(manifest["stage"]).startswith("generate-"):
        raise pool.StageRefused("refused: --generate-manifest must be the manifest of a COMPLETE generation of the rehearsal draw")
    modes = ("rehearsal", "dry") if os.environ.get(E2E_ENV) else ("rehearsal",)  # a DRY manifest only in the end-to-end exercise
    if manifest.get("mode") not in modes:
        raise pool.StageRefused(f"refused: --generate-manifest is of mode {manifest.get('mode')!r}; the cap is set from a rehearsal-mode generation (the check draw's and a DRY manifest are refused)")
    if not os.environ.get(E2E_ENV) and manifest["stage"] != f"generate-{core.REHEARSAL_SET.name}":
        raise pool.StageRefused(f"refused: --generate-manifest must be the stage generate-{core.REHEARSAL_SET.name}, not {manifest['stage']!r}")
    seconds = float(sum(float(t["seconds"]) for t in manifest["tasks"]))
    block = core.set_generation_cap(seconds)
    config = repo / core.DEFAULT_CONFIG
    before = core.generation_block(config)
    config.write_text(core.render_config_toml(block, core.cap_hours(config)), encoding="utf-8")
    core.validate_config(core.load_config(config))
    print(json.dumps({"config": str(config), "before": before, "after": block}))
    return 0


def cmd_arm_selection(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if out.exists():
        raise pool.StageRefused(f"refused: {out} exists")
    record = arm_selection.build_record(repo_of(args))
    write_json(out, core.jsonable(record))
    print(json.dumps({"arm_selection": str(out), "sha256": file_sha256(out), "printed": record["mapping_printed"]}))
    return 0 if record["mapping"]["steps_equal_table"] else 1


def frozen_reserve(caps: dict[str, Any]) -> float:
    """The headroom rule's reserve: the rule doubles every term, so (analysis cap + report cap) / 2 doubles to the sum of the frozen analysis and report stage caps (the lead's ruling on N4)."""
    return (float(caps.get("analysis", 0.0)) + float(caps.get("report", 0.0))) / core.HEADROOM


def reserve_of(args: argparse.Namespace) -> float:
    """The rehearsed analysis and report seconds the headroom rule reserves (0 where there is no cap table: DRY and tests)."""
    path = repo_of(args) / CAPS_FILE
    if not path.is_file():
        return 0.0
    return frozen_reserve(read_json(path))


def cmd_q1_gate(args: argparse.Namespace) -> int:
    """The Q1 gate (section 8.5, 10.4): the candidate from Q1's records by the fixed rule, and the headroom re-check after Q1 with the actual candidate's rehearsed rates, the hours charged and the reserved analysis and
    report time (cuts 1 and then 2 as needed, ``budget.post_q1_decision``), and the memory rule per block. The frozen cap is used as it is: nothing is raised here (the lead's ruling on M5). Written once as
    ``q1_gate.json``. Under the test profile or DRY, ``--dry-candidate`` names a candidate for the end-to-end exercise (``test_candidate`` is then True in the record)."""
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
    cand = result["outcome"]["arm"] if result["outcome"]["row"] == 4 else None
    test_candidate = False
    if cand is None and tiny(args) and args.dry_candidate:
        cand, test_candidate = args.dry_candidate, True
    record: dict[str, Any] = {**core.envelope("q1_gate"), "cut3": cut3, "profile": profile(args), "dry": bool(args.dry), "environment": core.environment(), "outcome_row": result["outcome"]["row"], "outcome": result["outcome"]["outcome"], "candidate": None, "test_candidate": test_candidate, "blocks": {"wx": {"run": False, "status": C.NOT_RUN_NO_CANDIDATE}, "probe": {"run": False, "status": C.NOT_RUN_NO_CANDIDATE}}}
    if cand is not None:
        record["candidate"] = cand
        if cand not in core.CANDIDATE_ARMS:
            record["note"] = "the candidate is not an arm that can still be the candidate: WX and the probe are not defined for it"
        elif projection is not None:
            ledger = ledger_of(args)
            table = projection["table"]
            decision = budget.post_q1_decision(ledger.charged(), float(table[f"wx:{cand}"]["total_seconds"]), float(table[f"probe:{cand}"]["total_seconds"]), reserve_seconds=reserve_of(args))
            memory = projection["memory"]
            wx_mem, pr_mem = memory[f"wx:{cand}"], memory[f"probe:{cand}"]
            wx_run, pr_run = decision.wx and wx_mem["ok"], decision.probe and pr_mem["ok"]
            record["blocks"] = {
                "wx": {"run": bool(wx_run), "status": None if wx_run else (decision.wx_status or budget.NOT_RUN_MEMORY)},
                "probe": {"run": bool(pr_run), "status": None if pr_run else (decision.probe_status or budget.NOT_RUN_MEMORY)},
            }
            record["headroom"] = {"cuts": list(decision.cuts), "charged_seconds": decision.charged_seconds, "reserve_seconds": reserve_of(args), "wx_projection_seconds": table[f"wx:{cand}"]["total_seconds"], "probe_projection_seconds": table[f"probe:{cand}"]["total_seconds"], "memory": {"wx": wx_mem, "probe": pr_mem}}
        elif tiny(args):
            record["blocks"] = {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}
    core.write_record(target, core.jsonable(record))
    core.emit_stdout({"candidate": record["candidate"], "row": record["outcome_row"], "blocks": record["blocks"]})
    return 0


def cmd_analyze(args: argparse.Namespace, cap: float | None = None) -> int:
    run_dir = Path(args.run_dir)
    manifest = single("analyze", "analyze", args, run_dir, run_dir / "analysis.json", cap=cap)
    return 0 if manifest["status"] == "COMPLETE" else 1


def cmd_report(args: argparse.Namespace, cap: float | None = None) -> int:
    run_dir = Path(args.run_dir)
    out = Path(args.results_dir) if args.results_dir else run_dir / "results"
    if (out / "results.json").exists():
        raise pool.StageRefused("refused: the report runs once and never overwrites")
    manifest = single("report", "report", args, run_dir, out / "results.json", cap=cap)
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
    """Every identity the freeze recorded must hold now: the arm-selection, projection and cap-table files, the draw plan and the data manifest of every draw and reserve, the profile and the run directory."""

    def check(path: Path, expected: str, what: str) -> None:
        if not path.is_file() or file_sha256(path) != expected:
            raise pool.StageRefused(f"refused: {path} does not hash to the frozen {what}")

    prof = plan.get("profile", "registered")
    if prof != core.profile_of(run_dir):
        raise pool.StageRefused(f"refused: the frozen plan's profile {prof!r} is not the run directory's")
    for key in ("arm_selection", "projection"):
        check(_path(repo, plan[key]["path"]), plan[key]["sha256"], f"{key} record")
    check(repo / CAPS_FILE, plan["stage_caps_sha256"], "stage-cap table")
    if plan.get("run_dir") is not None and Path(plan["run_dir"]).resolve() != run_dir.resolve():
        raise pool.StageRefused(f"refused: the freeze names the run directory {plan['run_dir']}, not {run_dir}")
    check(run_dir / "draw_plan.json", plan["draw_plan"]["sha256"], "draw plan")
    for name, digest in plan["data_manifests"].items():
        check(manifest_dir(run_dir, name) / "data_manifest.json", digest, f"data manifest of {name}")
    if set(plan["data_manifests"]) != set(core.set_names(prof)):
        raise pool.StageRefused("refused: the freeze must name the data manifest of all thirteen draws and both reserves")
    projection = core.read_record(_path(repo, plan["projection"]["path"]), "projection")
    if projection.get("arm_selection_sha256") != plan["arm_selection"]["sha256"]:
        raise pool.StageRefused("refused: the projection was not measured for the frozen arm-selection record")
    if plan.get("generation", {}).get("provisional", True):
        raise pool.StageRefused("refused: the frozen plan records a provisional generation cap")


def _path(repo: Path, p: str) -> Path:
    return Path(p) if Path(p).is_absolute() else repo / p


def block_cap(name: str, caps: dict[str, Any], key: str) -> Any:
    try:
        return budget.cap_for(caps, name, key)
    except budget.CapMissing as exc:
        raise pool.StageRefused(f"refused: {exc}") from exc


def require_wx_before_probe(run_dir: Path, q1_gate: dict[str, Any]) -> None:
    """After the Q1 gate WX runs before the 65,536 probe (the lead's ruling on item 7): the probe refuses while a WX block that is to run has no evaluation manifest."""
    if q1_gate["blocks"]["wx"]["run"] and not (run_dir / "evaluate-wx" / "manifest.json").is_file():
        raise pool.StageRefused("refused: WX runs before the 65,536 probe (the lead's ruling on item 7): run wx first")


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name (``REGISTERED_STAGES``), with everything else (caps, projection, arm-selection record, seeds, ledger, memory caps, backbone) from the frozen plan, the frozen cap table and the
    config. The only options it accepts are the run directory, the freeze commit and ``--caps`` (which must be the frozen cap table's path); any other option, whatever its value, is refused. The frozen plan and
    the freeze commit (the commit that added the plan) are verified first."""
    if args.name not in REGISTERED_STAGES:
        raise pool.StageRefused(f"refused: unknown registered stage {args.name!r}")
    args.mode = REGISTERED
    refuse_overrides(args, REGISTERED_ALLOWED, "a registered stage")
    refuse_registered_under_pytest(args)
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    plan = registered_state(args)
    if args.caps != CAPS_FILE:
        raise pool.StageRefused(f"refused: the launch script must pass --caps {CAPS_FILE} (the stage caps are those of the frozen table)")
    caps = read_json(repo / CAPS_FILE)
    args.arm_selection = str(_path(repo, plan["arm_selection"]["path"]))
    args.arm_selection_sha256 = plan["arm_selection"]["sha256"]
    args.projection = str(_path(repo, plan["projection"]["path"]))
    args.workers = core.WORKERS
    if plan.get("profile") == "test":
        args.dry_candidate = plan.get("test_candidate")  # the end-to-end exercise only; refused in a worker of any other profile
    projection = core.read_record(Path(args.projection), "projection")
    name = args.name
    ledger = ledger_of(args)
    reserve = frozen_reserve(caps)
    if name == "gates":
        return cmd_gates(args, cap=float(caps["gates"]))
    if name == "q1":
        table = projection["table"]
        ran = {e["stage"] for e in ledger.entries()}
        before = sum(float(sec) for st, sec in (plan.get("before_q1_projected_seconds") or {}).items() if st not in ran)
        decision = budget.pre_q1_decision(ledger.charged(), before, float(table["q1:full"]["total_seconds"]), float(table["q1:cut3"]["total_seconds"]), reserve_seconds=reserve)
        if decision.action == "stop":
            raise pool.StageRefused(f"refused: {budget.NOT_RUN_BUDGET}: the headroom rule does not hold for Q1 even under cut 3 ({decision.required_seconds:.0f} s required with {decision.charged_seconds:.0f} s charged, the analysis and report reserved); nothing registered is run and the matter returns to the human lead")
        key = decision.action
        memory = projection["memory"][f"q1:{key}"]
        if not memory["ok"]:
            raise pool.StageRefused(f"refused: {budget.NOT_RUN_MEMORY}: Q1's rehearsal peak ({memory['peak_rss_bytes']} bytes) exceeds {memory['limit_bytes']} per worker (or an item is missing); nothing registered is run and the matter returns to the human lead")
        start = run_dir / "q1_start.json"
        if start.exists():
            raise pool.StageRefused("refused: Q1 was already started in this run directory")
        core.write_record(start, {**core.envelope("q1_gate"), "cut3": key == "cut3", "decision": decision._asdict(), "cut": decision.cut, "label": core.CUT3_LABEL if key == "cut3" else "no cut"})
        cap = block_cap("q1", caps, key)
        return run_block(args, "q1", cap_train=float(cap["train"]), cap_eval=float(cap["evaluate"]))
    if name == "q1_gate":
        return cmd_q1_gate(args)
    if name in ("wx", "probe"):
        record = core.read_record(run_dir / "q1_gate.json", "q1_gate")
        if not record["blocks"][name]["run"]:
            raise pool.StageRefused(f"refused: {name} is not to run: {record['blocks'][name]['status']}")
        if name == "probe":
            require_wx_before_probe(run_dir, record)
        cap = block_cap(name, caps, record["candidate"])
        return run_block(args, name, cap_train=float(cap["train"]), cap_eval=float(cap["evaluate"]))
    return cmd_analyze(args, cap=float(caps["analysis"])) if name == "analysis" else cmd_report(args, cap=float(caps["report"]))


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
    p.add_argument("--i-understand-freeze-time", action="store_true")
    p.add_argument("--generation-cap-from-config", action="store_true", help="registered generation: the stage cap is the config's generation cap (no typed cap)")
    p.add_argument("--test-profile", action="store_true", help="freeze-plan: the run directory carries the TEST_PROFILE marker (the end-to-end exercise)")
    p.add_argument("--test-candidate", default=None, help="freeze-plan, test profile only: the candidate the end-to-end exercise's Q1 gate names")
    p.add_argument("--gates-per-draw-seconds", type=float, default=0.0, help="caps: the rehearsal draw's measured per-draw part of the gates (timing.per_draw_seconds of its gates.json)")
    p.add_argument("--generate-manifest", default=None, help="set-generation-cap: the manifest of the rehearsal draw's generation")
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    parser = argparse.ArgumentParser(prog="python -m studies.p10s0.stages", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate", parents=[common])
    for name in ("draw-plan", "caps", "freeze-plan", "set-generation-cap", "projection", "arm-selection", "check", "rehearse", "gates", "train", "q1-gate", "analyze", "report"):
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
    "generate": cmd_generate, "draw-plan": cmd_draw_plan, "check": cmd_check, "rehearse": cmd_rehearse, "projection": cmd_projection, "caps": cmd_caps, "freeze-plan": cmd_freeze_plan, "set-generation-cap": cmd_set_generation_cap, "arm-selection": cmd_arm_selection, "gates": cmd_gates,
    "train": cmd_train, "q1-gate": cmd_q1_gate, "analyze": cmd_analyze, "report": cmd_report, "registered": cmd_registered, "dry": cmd_dry,
}  # fmt: skip
DEFAULT_MODE = {"generate": CHECK, "check": CHECK, "rehearse": REHEARSAL, "dry": DRY}


MODE_FREE = ("draw-plan", "caps", "freeze-plan", "projection", "arm-selection", "set-generation-cap")  # commands that read no seed and have no mode


def main(argv: Sequence[str] | None = None) -> int:
    """Exit codes: 0 stage complete, 1 stage ran but a task or gate failed (records kept), 2 refused. Registered mode is reached only through ``registered <stage>`` (and by the workers it starts, which re-check
    the frozen plan) and by registered generation, which precedes the freeze: no typed command defaults into it and none accepts ``--mode registered`` (the audit's M1)."""
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.command == "registered":
        args.mode = REGISTERED
    elif args.command not in MODE_FREE:
        if args.dry and args.mode in (REGISTERED, CHECK, REHEARSAL):
            print("refused: --dry cannot be combined with --mode registered, check or rehearsal", file=sys.stderr)
            return 2
        if args.mode is None:
            args.mode = DRY if args.dry else DEFAULT_MODE.get(args.command)
        if args.mode is None:
            print(f"P10S0 stage REFUSED: `{args.command}` has no default mode: give --mode check, rehearsal or dry (registered mode is reached only through `registered <stage>`)", file=sys.stderr)
            return 2
        if args.mode == REGISTERED and args.command not in ("generate", "work"):
            print(f"P10S0 stage REFUSED: `{args.command} --mode registered` is not a registered stage: use `registered <stage>` (the launch scripts), which verifies the frozen plan", file=sys.stderr)
            return 2
        if args.dry:
            args.mode = DRY
    try:
        if args.command == "work":
            train.configure()
            return int(WORKERS[args.worker](args))
        if args.command == "dry":
            args.dry, args.mode = True, DRY
        elif args.run_dir is None and args.command not in ("check", "rehearse", "generate", "caps", "projection", "arm-selection", "set-generation-cap"):
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
