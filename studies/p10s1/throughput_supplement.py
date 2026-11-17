# ruff: noqa: E501
"""P10S1 supplementary throughput measurement (ADR-0021 section 25.21). NOT the registered throughput stage and not part of the registered result.

The registered stage (``stages.work_throughput``) stopped before any measurement in attempt 2: it asks for the F-OQ cell at 2,048 facts and 256 slots, which the frozen plan does not run
(``sat256`` false), so the lookup of the registered cell found nothing. That stage's failed record is kept and the frozen code is not edited. This module repeats the same measurement
(``timing.throughput_record``: read path, batch 1 and 128, five repeats, replicate-1 snapshots at U_P) for every configuration whose registered cell exists, names the configuration it skips,
and writes one record outside the run directory. The quiet rule is the registered one (``timing.wait_for_quiet``: load average at most 1.0, three retries); if the machine is never quiet the
record says THROUGHPUT NOT MEASURED. Nothing here reads an accuracy or a loss, and no outcome line of S1 depends on this record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from . import core, stages, timing, train

ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8", "D-OQ")
KIND = "p10s1_throughput_supplement"
SCOPE = "read path only, RAM, CPU, one process: not storage I/O, not latency of a language model"


def select(fro: Any) -> tuple[list[tuple[str, core.Cell]], list[dict[str, Any]]]:
    """The registered stage's configurations in its order, split into those with a registered replicate-1 cell (measured) and those without (skipped, with the reason)."""
    cells = {(c.arm, c.facts, c.slots): c for c in core.registered_cells(fro.plan, dense_rates=fro.dense_rates) if c.kind == "P" and c.draw == 1}
    items = stages.timing_items(fro.plan)
    measured: list[tuple[str, core.Cell]] = []
    skipped: list[dict[str, Any]] = []
    for arm in ARMS:
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        for facts, slots in sorted((f, n) for a, f, n in items if a == base and not (arm == "F-OQ-IVF" and n == core.SATURATION_ONLY_CELL[1])):
            cell = cells.get((base, facts, slots))
            if cell is None:
                skipped.append({"arm": arm, "facts": facts, "slots": slots, "reason": "no registered cell in the frozen plan (the 2K/256 cell is not run: sat256 false)"})
            else:
                measured.append((arm, cell))
    return measured, skipped


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(["git", *argv], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def worker_args(run_dir: Path, repo: Path) -> argparse.Namespace:
    """The namespace of a registered worker for this run directory (the same draw, plan and experiments root), built by the stages' own parser."""
    plan = repo / stages.FREEZE_PLAN
    argv = ["work", "throughput", "--run-dir", str(run_dir), "--mode", stages.REGISTERED, "--draw", "1", "--experiments-root", str(run_dir.parent), "--freeze-plan", str(plan)]
    args = stages.build_parser().parse_args(argv)
    args.mode = stages.REGISTERED
    return args


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out", required=True, help="a new directory outside the run directory")
    p.add_argument("--check-only", action="store_true", help="load every snapshot and stop: no quiet rule, no measurement, no record")
    ns = p.parse_args(argv)
    repo = core.repo_root()
    run_dir, out = Path(ns.run_dir).resolve(), Path(ns.out).resolve()
    if out == run_dir or run_dir in out.parents:
        print("refused: the supplement's record is never written inside the registered run directory", file=sys.stderr)
        return 2
    target = out / "throughput_supplement.json"
    if target.exists():
        print(f"refused: {target} exists; a record is never overwritten", file=sys.stderr)
        return 2
    args = worker_args(run_dir, repo)
    stages.configure()
    fro = stages.frozen_of(args)
    measured, skipped = select(fro)
    started = time.monotonic()
    quiet = {"quiet": True, "attempts": 0, "load_averages": [], "note": "check only"} if ns.check_only else timing.wait_for_quiet()
    status = "MEASURED" if quiet["quiet"] else timing.THROUGHPUT_NOT_MEASURED
    results: dict[str, Any] = {}
    snapshots: dict[str, str] = {}
    if quiet["quiet"]:
        seeds = stages.seeds_for(args, 1)
        study = stages.study_data(args, seeds, fro.plan)
        for arm, cell in measured:
            folder = core.cell_dir(run_dir, cell.label)
            job = stages.build_job(args, cell, study, folder, fro)
            model = train.job_model(job, seed_rng=False)
            train.load_model_state(folder / "snapshots" / core.snapshot_stem(cell.u_p), model)
            snapshots[f"{arm}|{cell.slots}"] = f"{cell.label}/snapshots/{core.snapshot_stem(cell.u_p)}"
            if not ns.check_only:
                results[f"{arm}|{cell.slots}"] = timing.throughput_record(model, study, cell.facts, seeds, arm)
    if ns.check_only:
        print(json.dumps({"check_only": True, "loaded": len(snapshots), "skipped": skipped}))
        return 0
    record = {
        "kind": KIND, "schema": 1, "study": "P10S1", "status": status,
        "standing": "SUPPLEMENTARY: not the registered throughput stage, which failed before any measurement (its record is kept); enters no outcome line of S1 (ADR-0021 section 25.21)",
        "run_dir": str(run_dir), "freeze_plan_sha256": hashlib.sha256((repo / stages.FREEZE_PLAN).read_bytes()).hexdigest(),
        "head_commit": _git(repo, "rev-parse", "HEAD"), "tree_clean": _git(repo, "status", "--porcelain") == "",
        "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "code_identity": core.code_identity(),
        "results": results, "snapshots": snapshots, "skipped": skipped, "quiet": quiet, "load_average_max": core.LOAD_AVERAGE_MAX,
        "batches": list(core.THROUGHPUT_BATCHES), "repeats": core.THROUGHPUT_REPEATS, "cv_max": core.THROUGHPUT_CV_MAX, "scope": SCOPE,
        "seconds": time.monotonic() - started, "environment": core.environment(),
    }  # fmt: skip
    out.mkdir(parents=True, exist_ok=False)
    target.write_text(json.dumps(core.jsonable(record), indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "configurations": len(results), "skipped": len(skipped), "record": str(target)}))
    return 0 if status == "MEASURED" else 1


if __name__ == "__main__":
    sys.exit(main())
