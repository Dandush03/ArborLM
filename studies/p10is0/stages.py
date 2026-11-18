# ruff: noqa: E501
"""P10IS0 stage commands (ADR-0023 section 10). Run from the repository root: ``uv run --locked python -m studies.p10is0.stages <command> ...``.

Commands before the freeze: ``candidate-plan``, ``counting-rehearsal``, ``freeze``, ``quiet-check`` (stage 3's precondition, read before the stage's own workers start), ``seed-gate``.
Registered entry points (``registered <stage>``): REFUSE unless the tree is clean, the plan, the freeze record, ``durations.json`` and ``stage_caps.json`` exist, the freeze commit is an ancestor of HEAD, a committed Decision 2 names the
freeze commit, every frozen input matches its recorded hash (an identity difference exits 75: PAUSED — IDENTITY, nothing written; restoring the file resumes), and the run directory is git-ignored and untracked. Nothing is frozen today, so they
refuse today. A launch script passes exactly the run directory and the freeze commit; everything else comes from ``freeze/plan.json``.

The registered main-grid driver (``registered main``) is NOT finished in this implementation (see the report): after the preconditions it stops with ``NotImplementedError``. ``items.run_cell`` is the worker's unit of work.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from arborlm.io import write_json

from . import accounting, core, freeze, sealed, seeds
from . import plan as planmod
from .plan import IDENTITY_EXIT, IdentityMismatch, StageRefused

REGISTERED_STAGES = ("main", "x8-gate", "x8", "analysis", "report")


def cmd_registered(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    try:
        planmod.check_preconditions(repo, Path(args.run_dir).resolve(), args.freeze_commit)
    except IdentityMismatch as exc:
        print(json.dumps({"status": "PAUSED — IDENTITY", "reason": str(exc)[:300]}), file=sys.stderr)
        return IDENTITY_EXIT
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    raise NotImplementedError(f"registered stage {args.stage!r}: the driver is not finished in this implementation")


def cmd_quiet_check(args: argparse.Namespace) -> int:
    """Stage 3's precondition: the load average sampled every 10 s for 60 s and no other study's process alive, read BEFORE any worker of this study starts. Prints the decision for this attempt only."""
    r = accounting.quiet_check()
    sealed.emit({"stage": "3", "status": "quiet" if r["quiet"] else accounting.PAUSED_NOT_QUIET, "load_average": [round(x, 2) for x in r["samples"]], "count": len(r["other_processes"])})
    return 0 if r["quiet"] else 3


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is0.stages")
    sub = ap.add_subparsers(dest="command", required=True)
    cp = sub.add_parser("candidate-plan", help="write freeze/plan.json (refuses to overwrite without --supersede)")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    cr = sub.add_parser("counting-rehearsal", help="resolve the candidate plan's items without training and write the rehearsal record")
    cr.add_argument("--out", required=True, help="the rehearsal record to write (outside the tracked tree)")
    cr.add_argument("--repo")
    f = sub.add_parser("freeze", help="write freeze/freeze_record.json")
    f.add_argument("--rehearsal", required=True)
    f.add_argument("--attest-sealed-unopened", default="")
    f.add_argument("--seal-broken", action="store_true")
    f.add_argument("--run-dir")
    f.add_argument("--repo")
    sg = sub.add_parser("seed-gate", help="run the seed gate (the cited checker as a copy)")
    sg.add_argument("--no-checker", action="store_true")
    sub.add_parser("quiet-check", help="stage 3's quiet condition, read before the workers start")
    reg = sub.add_parser("registered", help="a registered stage (refuses unless frozen and approved)")
    reg.add_argument("stage", choices=REGISTERED_STAGES)
    reg.add_argument("--run-dir", required=True)
    reg.add_argument("--freeze-commit", required=True)
    reg.add_argument("--repo")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(getattr(args, "repo", None) or core.repo_root())
    try:
        if args.command == "candidate-plan":
            print(json.dumps(freeze.candidate_plan(repo, supersede=args.supersede)))
        elif args.command == "counting-rehearsal":
            rec = freeze.counting_rehearsal(repo)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            write_json(out, core.jsonable(rec))
            print(json.dumps({"rehearsal": str(out), "status": rec["candidate"]["status"], "plan_file_sha256": rec["candidate"]["plan_file_sha256"]}))
        elif args.command == "freeze":
            res = freeze.freeze(repo, Path(args.rehearsal), attest_unopened=[x for x in args.attest_sealed_unopened.split(",") if x], seal_broken=args.seal_broken, run_dir=Path(args.run_dir) if args.run_dir else None)
            print(json.dumps(res))
        elif args.command == "seed-gate":
            res = seeds.seed_gate(run_checker=not args.no_checker)
            print(json.dumps({k: v for k, v in res.items() if k != "checker"} | {"checker_result": res["checker"].get("result_line")}, default=str))
            return 0 if res["passed"] else 1
        elif args.command == "quiet-check":
            return cmd_quiet_check(args)
        else:
            return cmd_registered(args)
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
