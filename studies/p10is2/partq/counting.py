# ruff: noqa: E501
"""The COUNTING rehearsal of Part Q, driven through the SAME entry point as the registered run (ADR-0025 section 10, the root-cause fix after the third real launch hit something the in-process rehearsal passed).

Every stage is launched as ``sh studies/p10is2/launch/partq_registered.sh <stage> <run-dir> - --rehearsal`` in a FRESH process, in the registered order, against the candidate plan file: the same launch script
(the per-stage environment: durable packages, offline, no bytecode, six threads), the same ``stages work`` entry point, the same ``real_stages.run_stage`` (stage order, per-stage caps and the cumulative ledger of
the plan, the stage-start check of the plan's inputs and package manifest, a world built per process, completion records and manifests). The documented overrides, and only these:

* ``--rehearsal``: no freeze commit, no committed Decision 2 (``-`` stands for the commit), the plan verified against its own run directory, mode ``rehearsal`` (partition and generation seeds 2529xx, the candidate
  ledger of the rehearsal in the run directory, every output under the rehearsal's own run directory, sealed layout);
* the block limits of the config (``caps.rehearsal_generation_blocks`` generation blocks per capability, one Q_check block) and ``force_generation`` (every stage runs whatever Q1-Q4 gave);
* ONE forced pause: ``generation`` launched with ``--pause-after-batches`` stops PAUSED (exit 4) and the same command, launched again, resumes it;
* ONE forced PAUSED — IDENTITY: ``qfit`` launched with ``--plan-file`` naming a copy of the plan with one frozen file's hash altered must exit 75 and write nothing; the same stage launched with the real plan
  (the restore) then runs.

Nothing else differs. The record (``rehearsal_counting.json``) lists the public figures only; the outcome-dependent values are in ``sealed/``."""

import json
import os
import resource
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, write_json

from ..common import core, gates, procs
from ..common import plan as planmod
from . import pipeline, real_stages, rehearsal
from . import plan as qplan

FORCED_PAUSE_AFTER = 4
Launch = Callable[[Sequence[str], Path, float], int]  # (argv, log file, timeout seconds) -> exit code


def subprocess_launch(argv: Sequence[str], log: Path, timeout: float) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as fh:
        try:
            return subprocess.run(list(argv), stdout=fh, stderr=subprocess.STDOUT, timeout=timeout, check=False).returncode  # noqa: S603
        except subprocess.TimeoutExpired:
            return -9


def stage_argv(repo: Path, stage: str, run_dir: Path, *extra: str) -> list[str]:
    return ["sh", str(repo / "studies/p10is2/launch/partq_registered.sh"), stage, str(run_dir), "-", "--rehearsal", *extra]


def altered_plan_file(plan: planmod.Plan, run_dir: Path) -> Path:
    """A copy of the plan with ONE frozen file's hash altered: written under the run directory, never under freeze/."""
    data = json.loads(json.dumps(plan.data))
    data["frozen_files"][sorted(data["frozen_files"])[0]] = "0" * 64
    path = run_dir / "identity_probe/partq_plan_altered.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    return path


def run_counting_rehearsal(repo: Path, run_dir: Path, *, launch: Launch = subprocess_launch, clock: Callable[[], float] = time.monotonic, charged_ledgers: Sequence[str] = ()) -> dict[str, Any]:
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    gates.apply_platform_settings(cfg)
    core.require_ignored_run_dir(repo, run_dir)
    plan_file = repo / core.PLAN_Q
    plan = planmod.Plan.load(plan_file, "Q")
    run_dir.mkdir(parents=True, exist_ok=True)
    logs = run_dir / "logs"
    t0 = clock()
    problems: list[str] = []
    timings: dict[str, float] = {}
    forced = {"pause_resume": False, "paused_identity_restore": False}

    def go(name: str, argv: Sequence[str], expect: int, stage: str | None = None) -> bool:
        cap = plan.cap_seconds(stage) if stage else 3600.0
        t = clock()
        rc = launch(argv, logs / f"{name}.log", (cap if cap > 0 else 3600.0) + 900.0)
        timings[name] = clock() - t
        if rc != expect:
            problems.append(f"{name}: exit {rc}, expected {expect}")
        return rc == expect

    cand = real_stages.ledger_path(cfg, repo, run_dir, "rehearsal")
    ok = True
    if not cand.is_file():  # the candidate ledger of the rehearsal (seed 252907), by the same command the lead used for the real one
        ok = go("ledger", ["sh", str(repo / "studies/p10is2/launch/partq_ledger.sh"), "rehearsal", str(run_dir)], 0)
    for stage in real_stages.STAGE_ORDER:
        if not ok:
            break
        if stage == "qfit":  # the forced identity difference, then the restore (the stage's real run below)
            alt = altered_plan_file(plan, run_dir)
            ident = go("qfit-identity-altered-plan", stage_argv(repo, stage, run_dir, "--plan-file", str(alt)), planmod.IDENTITY_EXIT, stage)
            forced["paused_identity_restore"] = ident and not real_stages.completion_path(run_dir, stage).exists()
            ok = ident
            if not ok:
                break
        if stage == "generation":  # the forced pause, then the resume by the same command
            ok = go("generation-forced-pause", stage_argv(repo, stage, run_dir, "--pause-after-batches", str(FORCED_PAUSE_AFTER)), 4, stage)
            forced["pause_resume"] = ok
            if not ok:
                break
        ok = go(stage if stage != "generation" else "generation-resume", stage_argv(repo, stage, run_dir), 0, stage)
    ctx = real_stages._light_ctx(cfg, run_dir, "rehearsal")
    led = core.Ledger(run_dir / "charged_ledger.json", "Q", 1e12)
    done = {s: real_stages.completion_path(run_dir, s).is_file() and json.loads(real_stages.completion_path(run_dir, s).read_text()).get("status") == "COMPLETE" for s in qplan.REHEARSAL_STAGES}
    def completion(s: str) -> dict[str, Any]:
        f = real_stages.completion_path(run_dir, s)
        return json.loads(f.read_text()) if f.is_file() else {}

    # seconds = everything charged to the stage in this directory (the wall time of each of its processes from the start of ``execute``: the world build is inside it, the interpreter start and the preconditions are not);
    # within_cap needs the charge under the plan's stage cap AND the stage's own completion record not saying otherwise
    stages = {s: {"status": "COMPLETE" if done[s] else "NOT RUN", "seconds": led.charged(s), "cap_seconds": plan.cap_seconds(s) if plan.cap_seconds(s) > 0 else None, "within_cap": (led.charged(s) <= plan.cap_seconds(s) and completion(s).get("within_cap") is not False) if plan.cap_seconds(s) > 0 else None} for s in qplan.REHEARSAL_STAGES}
    pipeline.write_sealed_summary(ctx)
    summary = pipeline.summary_for_display(ctx)
    sources = sum(float(v) for v in ((summary["counts"] or {}).get("generation_sources") or {}).values())
    gen_seconds = led.charged("generation")
    seconds = clock() - t0
    r = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    peak = float(r) / (1024 * 1024) if os.uname().sysname == "Darwin" else float(r) / 1024
    earlier = {str(Path(x)): core.Ledger(Path(x), "Q", 1e12).charged() for x in charged_ledgers}
    complete = all(v["status"] == "COMPLETE" for v in stages.values()) and all(forced.values()) and not problems
    rec = {
        **core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "counting", "seal_note": rehearsal.SEAL_NOTE, "status": "COMPLETE" if complete else "INCOMPLETE", "plan_file_sha256": file_sha256(plan_file), "caps_provisional": bool(plan.data.get("caps_provisional", True)),
        "fixed_cap_seconds": float(cfg["caps"]["rehearsal_hours"]) * 3600.0, "stages": stages, "forced": forced, "problems": problems, "entry_point": "partq_registered.sh <stage> <run-dir> - --rehearsal, one fresh process per stage",
        "timings": {"total_seconds": seconds, "process_seconds": timings}, "memory": {"peak_rss_mib_of_any_stage_process": peak}, "counts": summary["counts"], "batches": summary["batches"],
        "generation_items_per_second": {"all": (sources / gen_seconds) if gen_seconds and sources else None}, "plan_stage_items": {st: len(v) for st, v in plan.data["items"].items()}, "platform": gates.platform_record(),
        "load": {"end": rehearsal.load_average()}, "other_studies_alive": procs.other_studies_alive(), "charged_seconds": led.charged(), "charged_ledgers": {str(run_dir / "charged_ledger.json"): led.charged(), **earlier},
    }  # fmt: skip
    core.write_record(run_dir / "rehearsal_counting.json", rec, overwrite=True)
    print(json.dumps(rehearsal.whitelist({k: rec[k] for k in ("timings", "memory", "counts", "batches", "generation_items_per_second", "stages", "forced") if k in rec}), default=str))
    if not complete:
        raise core.StageRefused(f"refused: the counting rehearsal is incomplete: {problems or 'a stage did not complete'}")
    return rec
