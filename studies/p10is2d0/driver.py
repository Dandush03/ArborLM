# ruff: noqa: E501
"""The one fixed launch of D0 (ADR-0035 section 8): ``python -m studies.p10is2d0.driver run --out <new directory>``; workers are its own children (``worker`` is internal).

Order: preflight (clean tree, commit, new output directory, file lists and hashes of the Part T run directory and Part Q's directory) -> world built once with the no-write demonstration and the identity gates on the
real snapshots -> reproduction gate (24 unmodified-read passes against the registered item records) -> [only if every gate passed] read statistics and the 96 scoring passes -> report, written by code from a fixed
template -> file lists again. A gate failure writes ``gate_failure.json``, computes no counterfactual score and stops (exit 3). The cap is 8 worker-hours (exit 4, INCOMPLETE)."""

import argparse
import gc
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import torch

from arborlm.io import atomic_write
from studies.p10is2.common import core
from studies.p10is2.quantities import Thresholds

from . import finalize, gates, passes, run
from .world import (
    ITEM_RECORDS_SHA256_PREFIX,
    ITEM_RECORDS_SHA256_SUFFIX,
    PART_T_RUN,
    build_world,
    world_inputs,
)

REPO = Path(__file__).resolve().parents[2]
PART_Q_RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-Q-registered3-20261119")
STAGE_WALL_DEADLINE = 6 * 3600.0
POLL = 10.0
EXIT_GATE, EXIT_CAP, EXIT_ENGINEERING = 3, 4, 5


def jwrite(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, (json.dumps(obj, sort_keys=True, indent=1, default=str) + "\n").encode())


def git(*argv: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *argv], capture_output=True, text=True, check=True, timeout=60).stdout.strip()  # noqa: S603, S607


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def spawn_workers(out: Path, stage: str, led: passes.Ledger) -> int:
    """Three worker processes (six threads each); wait with a deadline. Returns 0 if all finished, EXIT_CAP at the cap, else a failure code. The orchestrator's clock is paused while it waits."""
    logs = out / "logs"
    logs.mkdir(exist_ok=True)
    procs = []
    for k in range(passes.WORKERS):
        f = (logs / f"worker_{stage}_{k}_{int(time.time())}.log").open("wb")
        procs.append((subprocess.Popen([sys.executable, "-m", "studies.p10is2d0.driver", "worker", "--out", str(out), "--stage", stage, "--index", str(k), "--count", str(passes.WORKERS)], cwd=REPO, stdout=f, stderr=subprocess.STDOUT), f))  # noqa: S603
    led.pause()
    deadline = time.monotonic() + STAGE_WALL_DEADLINE
    codes: list[int | None] = [None] * len(procs)
    try:
        while any(c is None for c in codes):
            time.sleep(POLL)
            codes = [p.poll() for p, _ in procs]
            if any(c not in (None, 0) for c in codes) or time.monotonic() > deadline:
                break
    finally:
        for p, f in procs:
            if p.poll() is None:
                p.terminate()
            f.close()
    for p, _ in procs:
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
    led.unpause()
    codes = [p.returncode for p, _ in procs]
    say(f"stage {stage}: worker exit codes {codes}")
    if all(c == 0 for c in codes):
        return 0
    if 9 in codes:
        return EXIT_CAP
    return EXIT_ENGINEERING


def identity_stage(out: Path, repo: Path) -> dict[str, Any]:
    """The world is built once here; every cell's three snapshots are loaded (hash-checked) and the identity gates run on every distinct query of both panels. No score is computed."""
    world, _cfg = build_world(repo)
    rec: dict[str, Any] = {"cells": {}}
    for rep, order in passes.cells():
        arms = run.load_cell(world, rep, order, PART_T_RUN / "snapshots")
        q = passes.distinct_queries(world, order, arms["final"].codes)
        gr = gates.identity_gates(arms["M1"].store, arms["append"].store, arms["final"].store, q)
        rec["cells"][f"r{rep}/{order}"] = {"distinct_queries": int(q.shape[0]), "gates": gr}
    rec["pass"] = all(v["pass"] for c in rec["cells"].values() for v in c["gates"].values())
    rec["largest_deviation"] = max(v["largest_deviation"] for c in rec["cells"].values() for v in c["gates"].values())
    rec["module_hashes_sha256"] = run.imported_module_hashes(repo)
    del world
    gc.collect()
    return rec


def repro_stage(out: Path) -> dict[str, Any]:
    items = json.loads((PART_T_RUN / "item_records.json").read_text())["items"]
    rec: dict[str, Any] = {"passes": {}}
    for t in passes.gate_tasks():
        got = json.loads(passes.record_path(out, t["id"]).read_text())
        reg = items[f"{passes.REGISTERED_ARM[t['store']]}|{t['order']}|{t['rep']}|s:{passes.panel_of(t['order'], t['role'])}"]
        rec["passes"][t["id"]] = gates.compare_pass(reg, got)
    rec["pass"] = all(v["pass"] for v in rec["passes"].values())
    devs = [v["largest_deviation"] for v in rec["passes"].values()]
    rec["largest_deviation"] = None if any(d is None for d in devs) else max(devs)
    return rec


def run_command(args: argparse.Namespace) -> int:
    out = Path(args.out)
    t_start = time.monotonic()
    if args.resume:
        if not (out / "launch.json").is_file() or (out / "run_complete.json").is_file():
            raise run.D0Refused("refused: --resume needs an interrupted run directory (launch.json present, run_complete.json absent)")
        prior = json.loads((out / "resumes.json").read_text()) if (out / "resumes.json").is_file() else []
        jwrite(out / "resumes.json", [*prior, {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cause": args.resume_cause or "UNSTATED"}])
    else:
        run.require_new_output_dir(out, PART_T_RUN)
    led = passes.Ledger(out, f"orchestrator_{int(time.time())}")
    led.note = {"stage": "orchestrator"}
    led.tick()
    status = git("status", "--porcelain")
    commit = git("rev-parse", "HEAD")
    if status:
        raise run.D0Refused(f"refused: the working tree is not clean (the run uses committed code):\n{status}")
    if torch.__version__.split("+")[0] != "2.8.0":
        raise run.D0Refused(f"refused: torch {torch.__version__}, not 2.8.0")
    if not args.resume:
        jwrite(out / "launch.json", {"commit": commit, "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "torch": torch.__version__, "python": sys.version, "argv": sys.argv, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cap_worker_seconds": passes.CAP_SECONDS, "workers": passes.WORKERS, "threads_per_worker": 6, "uv_lock_sha256": run._sha(REPO / "uv.lock")})
        jwrite(out / "inputs" / "partt_run_dir.before.json", run.fs_manifest(PART_T_RUN))
        jwrite(out / "inputs" / "partq_dir.before.json", run.fs_manifest(PART_Q_RUN))
        wi = world_inputs(REPO)
        sha = wi["item_records"]["sha256"]
        if not (sha.startswith(ITEM_RECORDS_SHA256_PREFIX) and sha.endswith(ITEM_RECORDS_SHA256_SUFFIX)):
            raise run.D0Refused(f"refused: item_records.json hashes to {sha}, not the OUTCOME.md value")
        jwrite(out / "inputs" / "world_inputs.json", wi)
    elif json.loads((out / "launch.json").read_text())["commit"] != commit:
        raise run.D0Refused("refused: the commit differs from the interrupted run's: a resume uses the same code")
    led.tick()

    def stop(code: int, why: str) -> int:
        led.tick()
        jwrite(out / "run_stopped.json", {"why": why, "exit": code, "charged_worker_seconds": passes.charged_total(out / "cost"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        say(f"STOP ({code}): {why}")
        return code

    # world build, no-write demonstration and identity gates (no score is computed)
    if not (out / "gates" / "identity.json").is_file():
        ident = identity_stage(out, REPO)
        t_after, q_after = run.fs_manifest(PART_T_RUN), run.fs_manifest(PART_Q_RUN)
        nw = {"part_t_run_dir": run.manifest_diff(json.loads((out / "inputs/partt_run_dir.before.json").read_text()), t_after), "part_q_dir": run.manifest_diff(json.loads((out / "inputs/partq_dir.before.json").read_text()), q_after)}
        nw["pass"] = all(not v for d in nw.values() if isinstance(d, dict) for v in d.values())
        jwrite(out / "gates" / "no_write_demonstration.json", nw)
        jwrite(out / "inputs" / "module_hashes.json", ident.pop("module_hashes_sha256"))
        jwrite(out / "gates" / "identity.json", ident)
        if not ident["pass"] or not nw["pass"]:
            jwrite(out / "gate_failure.json", {"stage": "identity or no-write", "identity_pass": ident["pass"], "no_write_pass": nw["pass"], "note": "no counterfactual score was computed"})
            return stop(EXIT_GATE, "identity gate or no-write demonstration failed")
    # reproduction gate
    if not (out / "gates" / "repro.json").is_file():
        code = spawn_workers(out, "gate", led)
        if code != 0:
            return stop(code, "gate workers did not finish")
        repro = repro_stage(out)
        jwrite(out / "gates" / "repro.json", repro)
        if not repro["pass"]:
            jwrite(out / "gate_failure.json", {"stage": "reproduction", "largest_deviation": repro["largest_deviation"], "failed": [k for k, v in repro["passes"].items() if not v["pass"]], "note": "no counterfactual score was computed"})
            return stop(EXIT_GATE, "reproduction gate failed")
    ident_rec = json.loads((out / "gates" / "identity.json").read_text())
    repro_rec = json.loads((out / "gates" / "repro.json").read_text())
    gate_record = {"identity": {"pass": ident_rec["pass"], "largest_deviation": ident_rec["largest_deviation"]}, "reproduction": {"pass": repro_rec["pass"], "largest_deviation": repro_rec["largest_deviation"]}, "no_write": json.loads((out / "gates" / "no_write_demonstration.json").read_text())["pass"]}
    jwrite(out / "gates" / "gate_record.json", gate_record)
    # read statistics and the 96 passes
    code = spawn_workers(out, "main", led)
    if code != 0:
        return stop(code, "main workers did not finish (cap or error); completed per-pass records are kept; the result is INCOMPLETE")
    # report
    cfg = core.load_config("T", REPO / core.CONFIG_T)
    reg = json.loads((PART_T_RUN / "registry.json").read_text())
    rec = finalize.build_records(out, reg, Thresholds.from_config(cfg))
    stats_by_cell = {f"r{t['rep']}/{t['order']}": json.loads(passes.record_path(out, t["id"]).read_text()) for t in passes.main_tasks() if t["kind"] == "stats"}
    led.tick()
    cost = {"worker_seconds_total": passes.charged_total(out / "cost"), "worker_hours_total": passes.charged_total(out / "cost") / 3600.0, "cap_worker_hours": passes.CAP_SECONDS / 3600.0, "orchestrator_wall_seconds": time.monotonic() - t_start}
    text = finalize.render(rec, gate_record, stats_by_cell, cost, commit, "COMPLETE")
    (out / "report.txt").write_text(text, encoding="utf-8")
    jwrite(out / "records" / "readings.json", {**rec, "oracle_line": core.ORACLE_LINE, "label": "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL"})
    jwrite(out / "records" / "stats.json", stats_by_cell)
    jwrite(out / "records" / "gate_record.json", gate_record)
    jwrite(out / "records" / "cost.json", cost)
    after_t = run.fs_manifest(PART_T_RUN)
    diff = run.manifest_diff(json.loads((out / "inputs/partt_run_dir.before.json").read_text()), after_t)
    jwrite(out / "inputs" / "partt_run_dir.after.json", after_t)
    jwrite(out / "records" / "partt_run_dir_diff.json", diff)
    led.tick()
    jwrite(out / "run_complete.json", {"commit": commit, "part_t_run_dir_changed": bool(diff["added"] or diff["removed"] or diff["changed"]), "engineering_stop": bool(diff["added"] or diff["removed"] or diff["changed"]), "worker_hours": passes.charged_total(out / "cost") / 3600.0})
    say(f"COMPLETE; worker hours {passes.charged_total(out / 'cost') / 3600.0:.3f}; part T run directory diff {diff}")
    return 0 if not (diff["added"] or diff["removed"] or diff["changed"]) else EXIT_ENGINEERING


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studies.p10is2d0.driver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--resume", action="store_true")
    r.add_argument("--resume-cause", default="")
    w = sub.add_parser("worker")
    w.add_argument("--out", required=True)
    w.add_argument("--stage", choices=["gate", "main"], required=True)
    w.add_argument("--index", type=int, required=True)
    w.add_argument("--count", type=int, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "worker":
        return passes.worker_main(Path(a.out), a.stage, a.index, a.count, REPO)
    try:
        return run_command(a)
    except run.D0Refused as e:
        say(str(e))
        return EXIT_ENGINEERING


if __name__ == "__main__":
    sys.exit(main())
