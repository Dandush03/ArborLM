# ruff: noqa: E501
"""READ-ONLY: run, without running any stage, the identity checks that ``stages.cmd_registered`` performs before it executes a registered stage (the same functions, in the same order), and print each result. It reads git,
the frozen files, the plan, the freeze record, the data manifests and Decision 2; it writes nothing, reads no evaluate output, no ladder decision and no sealed value, and never calls ``execute_stage``.

Usage: PYTHONPATH=<worktree>/src:<worktree> timeout 600 <venv python> results/p10is1-evaluate-cap-extension-20261121/verify_resume_identity.py --run-dir <run dir> --freeze-commit <full hash> [--repo <worktree>]
Exit 0 only if every check passes."""

import argparse
import json
import sys
from pathlib import Path

from studies.p10is1 import core, gates
from studies.p10is1 import plan as planmod
from studies.p10is1.core import StageRefused


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--freeze-commit", required=True)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args(argv)
    repo, run_dir = Path(a.repo), Path(a.run_dir)
    gates.configure_worker()  # as cmd_registered does, before the platform check
    results: dict[str, str] = {}
    state: dict[str, object] = {}

    def check(name: str, fn):  # type: ignore[no-untyped-def]
        try:
            state[name] = fn()
            results[name] = "PASS"
        except StageRefused as exc:
            results[name] = f"REFUSED: {exc}"

    check("check_preconditions (clean tree, freeze commit an ancestor, studies/p10is1 + config + imported roots + uv.lock equal their freeze content, platform of record)", lambda: planmod.check_preconditions(core.REGISTERED, repo, a.freeze_commit))
    check("load_registered_plan", lambda: planmod.load_registered_plan(repo))
    if results.get("load_registered_plan") == "PASS":
        pl = state["load_registered_plan"]
        check("verify_plan (frozen file hashes, config caps == plan caps, run dir, data manifests, freeze record, imported files vs the freeze commit)", lambda: planmod.verify_plan(pl, repo, run_dir, freeze_commit=a.freeze_commit))  # type: ignore[arg-type]
    check("require_decision_2 (committed, names the freeze commit, DECISION: RUN)", lambda: planmod.require_decision_2(repo, a.freeze_commit))
    check("require_ignored_run_dir", lambda: planmod.require_ignored_run_dir(repo, run_dir))
    head = planmod.git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    print(json.dumps({"head": head, "freeze_commit": a.freeze_commit, "results": results}, indent=2))
    return 0 if all(v == "PASS" for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
