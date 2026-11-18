# ruff: noqa: E501
"""P10IS0 pipeline rehearsal (ADR-0023 section 10 stage 2): every stage end to end.

``synthetic`` phase (the implementer's, runs here): in a COPY of the repository made inside the run directory (so no file of the worktree is written and the preconditions can be exercised for real: a git repository of its own, a freeze
record, a committed Decision 2), on the synthetic tiny configuration (marker ``TEST_PROFILE``: exposures divided by 64, 128 and 256 facts, a random synthetic backbone, test-range seeds, the registered plan builder with only the seed sets and
sizes changed): generate, timing, Stage R, caps, candidate plan, counting rehearsal, freeze, registered main, X8 gate, X8, analysis, report. The record says each stage's status and that nothing here is a measurement of anything.

``real`` phase (the lead runs it; not run by the implementer): one real-size cell type on the rehearsal draw (309201, initialisation 330092): its draw is generated and G1-checked, one worker times and trains each of its arms for
``--exposures`` exposures per fact and evaluates once; only whitelisted figures (times, memory, counts) are printed.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import core, drivers, items, sealed
from .profile import MARKER

GIT = ("git", "-c", "commit.gpgsign=false", "-c", "user.name=rehearsal", "-c", "user.email=rehearsal@example.invalid")


def make_copy(repo: Path, dest: Path, workers: int | None = None) -> Path:
    """A repository of its own holding what the stages read; committed, so the tree is clean."""
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "freeze", "results")
    shutil.copytree(repo / "studies", dest / "studies", ignore=ign)
    shutil.copytree(repo / "configs", dest / "configs")
    shutil.copytree(repo / "docs" / "decisions", dest / "docs" / "decisions")  # the evaluation records hash the specifications of the studies whose code it calls
    for rel in (core.SPEC, load_checker_rel(repo)):
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / rel, dest / rel)
    if workers is not None:  # the copy's config only (never the study's): fewer worker and busy processes on a shared machine
        cfgp = dest / core.CONFIG
        text = cfgp.read_text(encoding="utf-8")
        text = text.replace("workers = 6                        # stage 3 then runs", f"workers = {workers}                        # stage 3 then runs").replace("busy_processes = 12", "busy_processes = 0")
        text = text.replace("[budget]\nb_hours = 55.0", "[budget]\nb_hours = 55.0", 1)
        cfgp.write_text(text.replace("workers = 6\nstage_cap_factor", f"workers = {workers}\nstage_cap_factor"), encoding="utf-8")
    (dest / ".gitignore").write_text("/experiments/\n__pycache__/\n*.pyc\n", encoding="utf-8")
    (dest / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    run(dest, *GIT, "init", "-q")
    run(dest, *GIT, "add", "-A")
    run(dest, *GIT, "commit", "-q", "-m", "rehearsal copy")
    return dest


def load_checker_rel(repo: Path) -> str:
    return str(core.load_config(repo / core.CONFIG)["seed_ranges"]["checker"])


def run(cwd: Path, *argv: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(argv[:6])} failed ({p.returncode}): {p.stderr[-400:]}")
    return p


def stage(copy: Path, run_dir: Path, *args: str, ok: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    p = run(copy, sys.executable, "-m", "studies.p10is0.stages", *args, check=False)
    if p.returncode not in ok:
        raise RuntimeError(f"stage {' '.join(args[:2])} exited {p.returncode}: {p.stderr[-500:]} {p.stdout[-300:]}")
    return p


def accounting_platform() -> dict[str, Any]:
    from . import accounting

    accounting.configure_process()
    return accounting.platform_record()


def synthetic(repo: Path, run_dir: Path, workers: int | None = None) -> dict[str, Any]:
    """The synthetic pipeline rehearsal. Returns the rehearsal record (also written to ``<run dir>/rehearsal.json``)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / MARKER).write_text("synthetic tiny configuration: no registered seed, no real draw, no real backbone\n", encoding="utf-8")
    copy = make_copy(repo, run_dir / "repo", workers)
    rd = copy / "experiments" / "rehearsal-run"
    rd.mkdir(parents=True)
    (rd / MARKER).write_text("synthetic tiny configuration\n", encoding="utf-8")
    stages: dict[str, dict[str, Any]] = {}

    def rec(name: str, p: subprocess.CompletedProcess[str]) -> None:
        stages[name] = {"status": "COMPLETE" if p.returncode == 0 else f"EXIT {p.returncode}", "stdout_lines": len(p.stdout.splitlines())}

    rec("generate", stage(copy, rd, "generate", "--run-dir", str(rd), "--cap-hours", "1"))
    rec("timing", stage(copy, rd, "timing", "--run-dir", str(rd), "--cap-hours", "1"))
    sealed_dir = run_dir / "sealed_store"  # outside the copy (no working tree above it) and outside the worktree
    rec("stage_r", stage(copy, rd, "stage-r", "--run-dir", str(rd), "--sealed-dir", str(sealed_dir)))
    rec("a0_memory", stage(copy, rd, "a0-memory", "--run-dir", str(rd)))
    rec("caps", stage(copy, rd, "caps", "--run-dir", str(rd)))
    rec("candidate_plan", stage(copy, rd, "candidate-plan", "--run-dir", str(rd)))
    reh = rd / "counting_rehearsal.json"
    rec("counting_rehearsal", stage(copy, rd, "counting-rehearsal", "--out", str(reh)))
    p = stage(copy, rd, "freeze", "--rehearsal", str(reh), "--attest-sealed-unopened", "lead,implementer,auditor", "--sealed-dir", str(sealed_dir), "--no-checker", ok=(0, 2))
    rec("freeze", p)
    if p.returncode != 0:
        raise RuntimeError(f"freeze refused in the rehearsal copy: {p.stderr[-400:]}")
    run(copy, *GIT, "add", "-A")
    run(copy, *GIT, "commit", "-q", "-m", "freeze")
    commit = run(copy, "git", "rev-parse", "HEAD").stdout.strip()
    (copy / "results" / "p10is0-freeze-rehearsal").mkdir(parents=True)
    (copy / "results/p10is0-freeze-rehearsal/DECISION_2.md").write_text(f"Decision 2 (synthetic rehearsal): run the frozen plan as frozen. Freeze commit {commit}.\n", encoding="utf-8")
    run(copy, *GIT, "add", "-A")
    run(copy, *GIT, "commit", "-q", "-m", "decision 2")
    assert (rd / "timing" / "a0_memory.json").is_file()
    for name, ok in (("main", (0,)), ("x8-gate", (0,)), ("x8", (0, 2)), ("analysis", (0,)), ("report", (0,))):
        p = stage(copy, rd, "registered", name, "--run-dir", str(rd), "--freeze-commit", commit, ok=ok)
        rec(name, p)
    gate = rd / "x8" / "gate.json"
    forced = False
    if not read_json(gate)["x8_triggered"]:
        # synthetic tiny data never reaches L_Q = 4, so X8's path is exercised by forcing the gate record of this synthetic run directory (test profile only; the registered gate is computed by code and nothing forces it)
        g = read_json(gate)
        g["x8_triggered"], g["L_Q"], forced = True, 4.0, True
        write_json(gate, g)
        for name in ("x8", "analysis", "report"):
            rec(f"{name}_after_forced_gate", stage(copy, rd, "registered", name, "--run-dir", str(rd), "--freeze-commit", commit))
    analysis = read_json(rd / "analysis.json")
    record = {
        **core.envelope("rehearsal"), "phase": "synthetic", "profile": "test", "stages": stages, "candidate": {"status": "COMPLETE", "plan_file_sha256": file_sha256(copy / core.PLAN)}, "caps_provisional": False,
        "headline_step": analysis["headline"]["step"], "x8_gate_forced_in_synthetic_run": forced, "sealed_dir": str(sealed_dir), "x8_status": analysis.get("x8", {}).get("status"), "platform": accounting_platform(), "wave_size_limit": sealed.WAVE_LIMIT_SENTENCE, "note": "a pipeline rehearsal on synthetic tiny data: not a measurement of anything", "seeds": "test profile only",
    }  # fmt: skip
    write_json(run_dir / "rehearsal.json", core.jsonable(record))
    return record


def real(repo: Path, run_dir: Path, ct_name: str, exposures: int) -> dict[str, Any]:
    """One real-size cell type on the rehearsal draw (the lead runs this). Prints and records whitelisted figures only."""
    ctx = drivers.Ctx(repo, run_dir, registered=False)
    if ctx.profile.tiny:
        raise ValueError("the real phase runs under the registered profile")
    ct = core.cell_type_by_name(ct_name, ctx.cfg)
    out: dict[str, Any] = {**core.envelope("rehearsal"), "phase": "real", "cell_type": ct_name, "exposures": exposures, "stages": {}}
    drivers.work_generate_rehearsal(ctx)
    env = drivers.env_for(run_dir)
    for arm in ct.arms:
        timing = drivers.work_timing(ctx, arm, ct_name, "rehearsal")
        cell = core.make_cell("REH", ct, arm, 1, 0, ctx.cfg)
        items.run_cell(cell, ct, exposures, run_dir, env, ctx.cfg, spec=core.rehearsal_set(ctx.cfg), reference_swap=arm == "A6")
        out["stages"][arm] = {"status": "COMPLETE", "seconds_per_update": timing["seconds_per_update"], "peak_rss_bytes": timing["peak_rss_bytes"], "evaluation_wall_seconds": timing["evaluation_wall_seconds"]}
        sealed.emit({"stage": "rehearsal", "arm": arm, "cell_type": ct_name, "seconds_per_update": timing["seconds_per_update"], "peak_rss_bytes": timing["peak_rss_bytes"], "status": "COMPLETE"})
    write_json(run_dir / "rehearsal_real.json", core.jsonable(out))
    return out


def cmd_rehearse(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    run_dir = Path(args.run_dir).resolve()
    if args.phase == "synthetic":
        res = synthetic(repo, run_dir)
        print(json.dumps({"phase": "synthetic", "stages": {k: v["status"] for k, v in res["stages"].items()}, "headline_step": res["headline_step"]}))
    else:
        if not args.cell_type or not args.exposures:
            raise SystemExit("the real phase needs --cell-type and --exposures")
        res = real(repo, run_dir, args.cell_type, args.exposures)
        print(json.dumps({"phase": "real", "cell_type": args.cell_type, "stages": {k: v["status"] for k, v in res["stages"].items()}}))
    return 0
