# ruff: noqa: E501
"""Part Q command line (ADR-0025 sections 10, 11): ``candidate-plan``, ``caps-proposal``, ``freeze``, ``rehearse`` and the registered entry points ``registered`` and ``work``.

A registered entry point REFUSES unless: the tree is clean; the freeze commit is an ancestor of HEAD and the frozen files equal their content there; the frozen plan and its freeze record exist and agree; every
identity in the plan holds; a COMMITTED Decision 2 for Part Q names the freeze commit; the run directory is git-ignored or outside the repository. Nothing is frozen today, so every registered path refuses.
Exit codes: 0 done; 2 refused; 75 PAUSED — IDENTITY (a hash difference of a frozen input file; nothing is written, restoring the file resumes the task); 3 returned to the lead (a real-path piece that is not
implemented here, or a rule the ADR leaves open).
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ..common import core, gates
from ..common import plan as planmod
from ..common.core import PendingLeadReview, StageRefused
from . import freeze

EXIT_REFUSED, EXIT_IDENTITY, EXIT_LEAD, EXIT_INCOMPLETE = 2, planmod.IDENTITY_EXIT, 3, 4  # 4: the stage stopped on its cap or the memory guard (PAUSED): resume it
REGISTERED_STAGES = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis")


def repo_of(args: argparse.Namespace | None = None) -> Path:
    r = getattr(args, "repo", None) if args is not None else None
    return Path(r) if r else core.ROOT


def refuse_unless_registered_ready(repo: Path, run_dir: Path, freeze_commit: str | None, stage: str) -> planmod.Plan:
    """The whole chain of preconditions of a registered stage, in order. Raises ``StageRefused``."""
    if stage not in REGISTERED_STAGES:
        raise StageRefused(f"refused: {stage!r} is not a registered Part Q stage")
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    gates.apply_platform_settings(cfg)  # the process is configured BEFORE the platform check: six threads, deterministic algorithms (a fresh process has the machine's default thread count)
    planmod.check_preconditions("Q", planmod.REGISTERED, repo, freeze_commit, cfg)
    plan = planmod.load_registered_plan(repo, "Q")
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, str(freeze_commit), "Q")
    core.require_ignored_run_dir(repo, run_dir)
    return plan


def cmd_registered(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    plan = refuse_unless_registered_ready(repo, run_dir, args.freeze_commit, args.stage)
    from . import real

    out = real.run_registered_stage(args.stage, repo, run_dir, plan)
    return 0 if (out or {}).get("status", "COMPLETE") in ("COMPLETE", "NOT RUN BY RULE") else EXIT_INCOMPLETE  # NOT RUN BY RULE is the registered negative-outcome path, not an incomplete stage


def cmd_work(args: argparse.Namespace) -> int:
    """A worker re-checks everything before each task; an identity difference exits 75 and writes nothing."""
    return cmd_registered(args)


def cmd_rehearse(args: argparse.Namespace) -> int:
    from . import real

    real.run_rehearsal(args.kind, repo_of(args), Path(args.run_dir), args)
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    """THE pre-freeze ledger command (section 4.1): writes this study's 144 GEN windows into the shared panel ledger once (seed 250907). It refuses once a plan or a freeze record exists."""
    repo = repo_of(args)
    if (repo / core.PLAN_Q).exists() or (repo / core.FREEZE_RECORD_Q).exists():
        raise StageRefused("refused: the ledger is written before the plan and the freeze, never after")
    from . import real_stages

    out = real_stages.command_ledger(repo, Path(args.run_dir) if args.run_dir else None, args.mode)
    print(json.dumps(out))
    return 0


def cmd_package_manifest(args: argparse.Namespace) -> int:
    """Produces the installed-package manifest of the durable copy (R7, A7). With ``--merge-into`` the manifest is added under ``package_manifest`` to an inputs file (for ``candidate-plan --inputs``); otherwise it is
    written to ``--out``. Reads the copy and the lock environment's site-packages; writes nothing into either."""
    import sysconfig

    from arborlm.io import write_json

    from . import pkgmanifest

    cfg = core.load_config("Q", repo_of(args) / core.CONFIG_Q)
    m = pkgmanifest.build_manifest(Path(cfg["paths"]["durable_packages"]), Path(args.lock_site_packages or sysconfig.get_paths()["purelib"]))
    if args.merge_into:
        target = Path(args.merge_into)
        inputs = json.loads(target.read_text()) if target.is_file() else {}
        write_json(target, {**inputs, pkgmanifest.KEY: m})
    else:
        write_json(Path(args.out), {pkgmanifest.KEY: m})
    print(json.dumps({"file_count": m["file_count"], "tree_sha256": m["tree_sha256"], "packages": len(m["packages"]), "shadowed_lock_packages": sorted(m["shadowed_lock_packages"])}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is2.partq.stages", description="P10IS2 Part Q (ADR-0025). Registered entry points refuse until a freeze record and a committed Decision 2 exist.")
    sub = ap.add_subparsers(dest="command", required=True)
    freeze.add_commands(sub)
    for name in ("registered", "work"):
        r = sub.add_parser(name)
        r.add_argument("--stage", required=True)
        r.add_argument("--run-dir", required=True)
        r.add_argument("--freeze-commit")
        r.add_argument("--repo")
    lg = sub.add_parser("ledger")
    lg.add_argument("--mode", choices=("registered", "rehearsal"), default="registered")
    lg.add_argument("--run-dir")
    lg.add_argument("--repo")
    pm = sub.add_parser("package-manifest")
    pm.add_argument("--out")
    pm.add_argument("--merge-into")
    pm.add_argument("--lock-site-packages")
    pm.add_argument("--repo")
    h = sub.add_parser("rehearse")
    h.add_argument("--kind", choices=("measuring", "counting"), required=True)
    h.add_argument("--run-dir", required=True)
    h.add_argument("--repo")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("candidate-plan", "freeze", "caps-proposal"):
            return freeze.dispatch(args)
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return cmd_work(args)
        if args.command == "ledger":
            return cmd_ledger(args)
        if args.command == "package-manifest":
            if bool(args.out) == bool(args.merge_into):
                raise StageRefused("refused: give exactly one of --out and --merge-into")
            return cmd_package_manifest(args)
        return cmd_rehearse(args)
    except StageRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_IDENTITY if "PAUSED — IDENTITY" in str(e) else EXIT_REFUSED
    except PendingLeadReview as e:
        print(f"PENDING LEAD REVIEW: {e}", file=sys.stderr)
        return EXIT_LEAD


if __name__ == "__main__":
    raise SystemExit(main())
