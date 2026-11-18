# ruff: noqa: E501
"""P10IS0 stage commands (ADR-0023 section 10). Run from the repository root: ``uv run --locked python -m studies.p10is0.stages <command> ...``.

Before the freeze (stages 2 to 5; each needs ``--run-dir``, a named git-ignored directory): ``rehearse`` (the pipeline rehearsal, ``rehearsal.py``), ``generate`` (the 14 draws, G1, the draw plan), ``timing`` (stage 3: one attempt per call, the quiet condition read
before the workers start), ``stage-r`` (Stage R and ``freeze/durations.json``), ``caps`` (``freeze/stage_caps.json``), ``candidate-plan``, ``counting-rehearsal``, ``freeze``, ``seed-gate``, ``quiet-check``.
Registered entry points (``registered <stage>``: main, x8-gate, x8, analysis, report): REFUSE unless the tree is clean, the plan, the freeze record, ``durations.json`` and ``stage_caps.json`` exist, the freeze commit is an ancestor of HEAD, a
committed Decision 2 names the freeze commit, every frozen input matches its recorded hash (exit 75: PAUSED — IDENTITY, nothing written) and the code equals the identity ``durations.json`` records (exit 4: ENGINEERING STOP), and the run directory
is git-ignored and untracked. A launch script passes exactly the run directory and the freeze commit; everything else comes from ``freeze/plan.json``. Exit codes: 0 COMPLETE, 5 PAUSED (run again to resume), 1 FAILED (item errors), 2 refused, 3 not quiet or an
engineering stop of the analysis, 4 code changed, 75 identity.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from arborlm.io import write_json

from . import accounting, core, drivers, freeze, sealed, seeds
from . import ladder as ladder_mod
from . import plan as planmod
from .plan import IDENTITY_EXIT, IdentityMismatch, StageRefused

REGISTERED_STAGES = ("main", "x8-gate", "x8", "analysis", "report", "disclose")
PAUSED_EXIT, FAILED_EXIT = 5, 1


def exit_of(status: str | None) -> int:
    s = str(status)
    return 0 if status in ("COMPLETE", None) else drivers.CODE_CHANGED_EXIT if s.startswith("ENGINEERING") else PAUSED_EXIT if s.startswith("PAUSED") else FAILED_EXIT


def cmd_platform(args: argparse.Namespace) -> int:
    """Configure the process (one thread, one interop thread, deterministic), THEN check the platform of record, and print the record."""
    accounting.configure_process()
    try:
        rec = accounting.check_platform(core.load_config(Path(args.repo) / core.CONFIG) if args.repo else None)
    except accounting.PlatformMismatch as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(rec, sort_keys=True))
    return 0


def cmd_registered(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    run_dir = Path(args.run_dir).resolve()
    accounting.configure_process()  # BEFORE the platform check, whatever thread variables the launching shell set (N6)
    try:
        accounting.check_platform(core.load_config(repo / core.CONFIG))
    except accounting.PlatformMismatch as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    try:
        planmod.check_preconditions(repo, run_dir, args.freeze_commit)
        drivers.check_code_identity(repo)
        ctx = drivers.Ctx(repo, run_dir, registered=True)
        if args.stage == "main":
            res = drivers.cmd_main(ctx)
        elif args.stage == "x8-gate":
            res = drivers.cmd_x8_gate(ctx)
        elif args.stage == "x8":
            res = drivers.cmd_x8(ctx)
        elif args.stage == "analysis":
            res = drivers.cmd_analysis(ctx)
        elif args.stage == "disclose":
            res = drivers.cmd_disclose(ctx)
        else:
            res = drivers.cmd_report(ctx)
    except IdentityMismatch as exc:
        print(json.dumps({"status": "PAUSED — IDENTITY", "reason": str(exc)[:300]}), file=sys.stderr)
        return IDENTITY_EXIT
    except (drivers.CodeChanged, ladder_mod.EngineeringStop) as exc:
        print(str(exc), file=sys.stderr)
        return drivers.CODE_CHANGED_EXIT
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 3 if "ITEM ERRORS" in str(exc) else 2
    print(json.dumps(core.jsonable(res), default=str))
    return exit_of(res.get("status"))


def cmd_quiet_check(args: argparse.Namespace) -> int:
    r = accounting.quiet_check()
    sealed.emit({"stage": "3", "status": "quiet" if r["quiet"] else accounting.PAUSED_NOT_QUIET, "load_average": [round(x, 2) for x in r["samples"]], "count": len(r["other_processes"])})
    return 0 if r["quiet"] else 3


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is0.stages")
    sub = ap.add_subparsers(dest="command", required=True)

    def add(name: str, help_: str, run_dir: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        if run_dir:
            p.add_argument("--run-dir", required=True)
        p.add_argument("--repo")
        return p

    add("generate", "stage 5: generate and G1-check the 14 draws; the draw plan").add_argument("--cap-hours", type=float, default=2.0)
    add("timing", "stage 3: one attempt (quiet condition first, then six workers alone, then the twelve-busy repeat)").add_argument("--cap-hours", type=float, default=2.0)
    sr = add("stage-r", "stage 4: Stage R, the extension rule, freeze/durations.json")
    sr.add_argument("--cause-file")
    sr.add_argument("--events-dir")
    sr.add_argument("--sealed-dir", required=True, help="outside version control: refused inside any working tree and under the main checkout")
    add("caps", "write freeze/stage_caps.json from the measured projection")
    add("a0-memory", "stage 5: the full-length A0 memory cell on the rehearsal draw (time and memory only)")
    cp = add("candidate-plan", "write freeze/plan.json (refuses to overwrite without --supersede)", run_dir=False)
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--run-dir")
    cr = add("counting-rehearsal", "resolve the candidate plan's items without training and write the rehearsal record", run_dir=False)
    cr.add_argument("--out", required=True)
    f = add("freeze", "write freeze/freeze_record.json", run_dir=False)
    f.add_argument("--rehearsal", required=True)
    f.add_argument("--attest-sealed-unopened", default="")
    f.add_argument("--seal-broken", action="store_true")
    f.add_argument("--sealed-dir")
    f.add_argument("--disclosed-read", action="append", default=[], help="a sealed file the lead read (disclosed in the freeze record; prints CALIBRATION VALUES SEEN BY THE LEAD)")
    f.add_argument("--no-checker", action="store_true", help="test profile only (the rehearsal copy has no registry inventory to scan)")
    sg = sub.add_parser("seed-gate", help="run the seed gate (the cited checker as a copy)")
    sg.add_argument("--no-checker", action="store_true")
    sub.add_parser("quiet-check", help="stage 3's quiet condition, read before the workers start")
    pf = sub.add_parser("platform", help="configure the process, then check and print the platform of record")
    pf.add_argument("--repo")
    rh = add("rehearse", "stage 2: the pipeline rehearsal end to end (synthetic phase; real-size phase named separately)")
    rh.add_argument("--phase", choices=("synthetic", "real"), default="synthetic")
    rh.add_argument("--cell-type")
    rh.add_argument("--exposures", type=int)
    reg = add("registered", "a registered stage (refuses unless frozen and approved)")
    reg.add_argument("stage", choices=REGISTERED_STAGES)
    reg.add_argument("--freeze-commit", required=True)
    w = sub.add_parser("work", help="a worker (called by the drivers)")
    w.add_argument("rest", nargs=argparse.REMAINDER)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "work":
        return drivers.worker_main(argv[2:] if len(argv) > 1 and argv[1] == "--" else argv[1:])
    args = build_parser().parse_args(argv)
    repo = Path(getattr(args, "repo", None) or core.repo_root())
    try:
        if args.command == "candidate-plan":
            print(json.dumps(freeze.candidate_plan(repo, supersede=args.supersede, run_dir=Path(args.run_dir) if args.run_dir else None)))
        elif args.command == "counting-rehearsal":
            rec = freeze.counting_rehearsal(repo)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            write_json(out, core.jsonable(rec))
            print(json.dumps({"rehearsal": str(out), "status": rec["candidate"]["status"], "plan_file_sha256": rec["candidate"]["plan_file_sha256"]}))
        elif args.command == "freeze":
            if args.no_checker and planmod.load_plan(repo / core.PLAN).get("profile") != "test":
                raise StageRefused("refused: --no-checker is allowed for a test-profile plan only: a registered freeze runs the registry's checker")
            res = freeze.freeze(repo, Path(args.rehearsal), attest_unopened=[x for x in args.attest_sealed_unopened.split(",") if x], seal_broken=args.seal_broken, sealed_dir=Path(args.sealed_dir) if args.sealed_dir else None, run_checker=not args.no_checker, disclosed_reads=args.disclosed_read)
            print(json.dumps(res))
        elif args.command == "seed-gate":
            res = seeds.seed_gate(run_checker=not args.no_checker)
            print(json.dumps({k: v for k, v in res.items() if k != "checker"} | {"checker_result": res["checker"].get("result_line")}, default=str))
            return 0 if res["passed"] else 1
        elif args.command == "quiet-check":
            return cmd_quiet_check(args)
        elif args.command == "platform":
            return cmd_platform(args)
        elif args.command == "registered":
            return cmd_registered(args)
        elif args.command == "rehearse":
            from . import rehearsal

            return rehearsal.cmd_rehearse(args)
        else:
            ctx = drivers.Ctx(repo, Path(args.run_dir).resolve(), registered=False, sealed_dir=Path(args.sealed_dir) if getattr(args, "sealed_dir", None) else None)
            if args.command == "generate":
                res = drivers.cmd_generate(ctx, args.cap_hours)
            elif args.command == "timing":
                res = drivers.cmd_timing(ctx, args.cap_hours)
                print(json.dumps(core.jsonable(res)))
                return 0 if res["decision"] == "READY" else 3
            elif args.command == "stage-r":
                res = drivers.cmd_stage_r(ctx, cause_file=Path(args.cause_file) if args.cause_file else None, events_dir=Path(args.events_dir) if args.events_dir else None)
                return exit_of(res["status"])
            elif args.command == "a0-memory":
                res = drivers.cmd_a0_memory(ctx)
            else:
                res = drivers.cmd_caps(ctx)
            print(json.dumps(core.jsonable(res), default=str))
            return exit_of(res.get("status"))
    except drivers.CodeChanged as exc:
        print(str(exc), file=sys.stderr)
        return drivers.CODE_CHANGED_EXIT
    except ladder_mod.EngineeringStop as exc:
        print(f"ENGINEERING STOP: {exc}", file=sys.stderr)
        return drivers.CODE_CHANGED_EXIT
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
