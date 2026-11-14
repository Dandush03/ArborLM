# ruff: noqa: E501
"""ADR-0016 stage runner: the one execution of the supplement on the five collapsed cells.

    uv run --locked python -m supplements.p8s.stage run --freeze-commit <commit>

Refuses unless the working tree is clean, ``--freeze-commit`` names a commit that is an ancestor of
HEAD whose ``supplements/`` tree, ``tests/test_p8s_*.py`` files and ADR-0016 equal the working tree,
the frozen material verifies (``frozen.verify_frozen_material``) and no earlier ``P8SUP-*`` run exists
under the experiments root (a failed run is kept and not re-run). One worker, 2 GiB RSS and 30 minutes
are enforced by the frozen pool and recorded. Output: ``<experiments root>/P8SUP-<utc>-<id>/``.
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from arborlm import p8_core as core
from arborlm import p8_pool
from arborlm.io import file_sha256, read_json, write_json
from arborlm.records import allocate_run, utc_now

from . import common, frozen

SCHEMA_STAGE = "P8SUP-stage-v1"
PREFIX = "P8SUP"


def require_clean_tree(repo: Path) -> None:
    """No staged, unstaged or untracked (non-ignored) change."""
    status = common.git_text(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise common.SupplementError(
            "refused: the working tree is not clean:\n" + "\n".join(status.splitlines()[:10])
        )


def verify_supplement_freeze(repo: Path, commit: str | None) -> dict[str, str]:
    """The freeze commit of the supplement code, recorded with its tree hash (the identity)."""
    if not commit:
        raise common.SupplementError("refused: --freeze-commit is required")
    if not common.commit_available(repo, commit):
        raise common.SupplementError(f"refused: {commit} is not a commit of this repository")
    full = common.git_text(repo, "rev-parse", f"{commit}^{{commit}}")
    tree = common.git_text(repo, "rev-parse", f"{commit}^{{tree}}")
    if not common.is_ancestor(repo, full, "HEAD"):
        raise common.SupplementError(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems: list[str] = []
    frozen_sub = common.git_text(repo, "rev-parse", f"{full}:supplements")
    head_sub = common.git_text(repo, "rev-parse", "HEAD:supplements")
    if frozen_sub != head_sub:
        problems.append("supplements/ at HEAD differs from the freeze commit")
    names = [
        p
        for p in common.git_text(repo, "ls-tree", "--name-only", "HEAD", "tests/").splitlines()
        if p.startswith("tests/test_p8s_")
    ]
    names_frozen = [
        p
        for p in common.git_text(repo, "ls-tree", "--name-only", full, "tests/").splitlines()
        if p.startswith("tests/test_p8s_")
    ]
    if names != names_frozen:
        problems.append("the set of tests/test_p8s_*.py files differs from the freeze commit")
    for path in [*names_frozen, common.SPEC_PATH]:
        if common.git_text(repo, "rev-parse", f"{full}:{path}") != common.git_text(
            repo, "rev-parse", f"HEAD:{path}"
        ):
            problems.append(f"{path} at HEAD differs from the freeze commit")
    if problems:
        raise common.SupplementError("refused: " + "; ".join(problems))
    return {"commit": full, "tree": tree, "supplements_tree": frozen_sub}


def refuse_if_previous_run(experiments_root: Path) -> None:
    previous = sorted(experiments_root.glob(f"{PREFIX}-*")) if experiments_root.is_dir() else []
    if previous:
        raise common.SupplementError(
            f"refused: {previous[0].name} already exists; the supplement runs once and a failed run "
            "is kept, not re-run"
        )


def run_stage(
    eval_run: Path,
    registered_sim_run: Path,
    experiments_root: Path,
    *,
    freeze_commit: str | None,
    repo: Path = common.ROOT,
    cap_seconds: float = common.WALL_LIMIT_SECONDS,
    labels: tuple[str, ...] = common.SUPPLEMENT_CELLS,
) -> Path:
    require_clean_tree(repo)
    freeze = verify_supplement_freeze(repo, freeze_commit)
    refuse_if_previous_run(experiments_root)
    verification = frozen.verify_frozen_material(repo, eval_run, registered_sim_run)
    if not verification["ok"]:
        raise common.SupplementError(
            "refused: frozen material does not verify: " + "; ".join(verification["problems"][:5])
        )
    return execute(
        eval_run,
        registered_sim_run,
        experiments_root,
        freeze=freeze,
        verification=verification,
        repo=repo,
        cap_seconds=cap_seconds,
        labels=labels,
    )


def execute(
    eval_run: Path,
    registered_sim_run: Path,
    experiments_root: Path,
    *,
    freeze: dict[str, str],
    verification: dict[str, Any],
    repo: Path,
    cap_seconds: float,
    labels: tuple[str, ...],
) -> Path:
    """The gated part is done: write the jobs, run them with ONE worker under the frozen pool's RSS and
    wall-time guards, keep every failure record, write the stage manifest."""
    spec_sha = common.supplement_spec_sha256(repo)
    source_sha = common.supplement_source_digest(repo)
    run = allocate_run(experiments_root, prefix=PREFIX)
    try:
        _execute_in(run, eval_run, registered_sim_run, freeze, verification, cap_seconds, labels,
                    spec_sha, source_sha, repo)  # fmt: skip
    except Exception as exc:
        # an unexpected failure after the run folder exists: record it, keep the folder (it blocks a
        # re-run, as for any failed run), re-raise
        write_json(
            run / "manifest.json",
            {
                "schema": SCHEMA_STAGE,
                "label": common.SUPPLEMENT_LABEL,
                "supplement": "ADR-0016",
                "status": "FAILED",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
                "supplement_spec_sha256": spec_sha,
                "supplement_source_sha256": source_sha,
                "supplement_freeze_commit": freeze,
                "failed_utc": utc_now(),
                "note": "unexpected exception during the stage; the run is kept and not re-run",
            },
        )
        raise
    return run


def _execute_in(
    run: Path,
    eval_run: Path,
    registered_sim_run: Path,
    freeze: dict[str, str],
    verification: dict[str, Any],
    cap_seconds: float,
    labels: tuple[str, ...],
    spec_sha: str,
    source_sha: str,
    repo: Path,
) -> None:
    jobs: list[p8_pool.Job] = []
    deadline_epoch = time.time() + cap_seconds
    for label in labels:
        out_dir = run / "cells" / label
        out_dir.mkdir(parents=True)
        write_json(
            out_dir / "job.json",
            {
                "label": label,
                "eval_cell_dir": str(eval_run / "cells" / label),
                "out_dir": str(out_dir),
                "stage_deadline_epoch": deadline_epoch,
                "supplement_spec_sha256": spec_sha,
                "supplement_source_sha256": source_sha,
                "supplement_freeze_commit": freeze,
            },
        )
        jobs.append(
            p8_pool.Job(
                label,
                [sys.executable, "-m", "supplements.p8s.sim", str(out_dir / "job.json")],
                out_dir / "sim.json",
                out_dir / "sim.failed.json",
                out_dir / "worker.log",
            )
        )
    started = utc_now()
    result = p8_pool.run_pool(
        jobs,
        workers=1,
        cap_seconds=cap_seconds,
        rss_worker=common.RSS_LIMIT_BYTES,
        env={"PYTHONPATH": str(repo)},
    )
    completed = sum(1 for o in result.outcomes if o.status == "completed")
    write_json(
        run / "manifest.json",
        {
            "schema": SCHEMA_STAGE,
            "label": common.SUPPLEMENT_LABEL,
            "supplement": "ADR-0016",
            "supplement_spec_sha256": spec_sha,
            "supplement_source_sha256": source_sha,
            "supplement_freeze_commit": freeze,
            "source_sha256": core.source_digest(),
            "frozen_verification": verification,
            "p7b_reproduction_record_cited": common.p7b_reproduction_record_cited(),
            "eval_run": str(eval_run),
            "eval_manifest_sha256": file_sha256(eval_run / "manifest.json"),
            "registered_sim_run": str(registered_sim_run),
            "labels": list(labels),
            "cells_expected": len(labels),
            "cells_completed": completed,
            "outcomes": [o.__dict__ for o in result.outcomes],
            "started_utc": started,
            "finished_utc": utc_now(),
            "wall_seconds": result.wall_seconds,
            "cap_seconds": cap_seconds,
            "cap_hit": result.cap_hit,
            "workers": 1,
            "rss_limit_per_worker_bytes": common.RSS_LIMIT_BYTES,
            "peak_aggregate_rss_bytes": result.peak_aggregate_rss_bytes,
            "peak_worker_rss_bytes": max((o.peak_rss_bytes for o in result.outcomes), default=0),
            "status": "completed" if completed == len(labels) else "INCOMPLETE",
            "note": "supplementary run; a failed record is kept and the cell is not re-run",
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m supplements.p8s.stage")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--experiments-root", type=Path, default=None)
    r.add_argument("--eval-run", type=Path, default=None)
    r.add_argument("--registered-sim-run", type=Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = args.experiments_root or common.default_experiments_root()
    eval_run = args.eval_run or root / common.EVAL_RUN_NAME
    sim_run = args.registered_sim_run or root / common.SIM_RUN_NAME
    try:
        run = run_stage(eval_run, sim_run, root, freeze_commit=args.freeze_commit)
    except common.SupplementError as exc:
        print(f"P8 supplement stage REFUSED: {exc}", file=sys.stderr)
        return 2
    manifest = read_json(run / "manifest.json")
    keys = ("status", "cells_completed", "cells_expected", "wall_seconds", "peak_worker_rss_bytes")
    print(json.dumps({k: manifest[k] for k in keys}, indent=2))
    print(f"run directory: {run}")
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
