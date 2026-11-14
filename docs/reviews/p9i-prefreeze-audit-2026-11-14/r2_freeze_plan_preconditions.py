"""R2 (auditor, Opus 5.5): the lead's M3 plan against studies.p9i.stages.check_preconditions, in a
throw-away clone of the repository at dd8b205 (argument 1). The clone is modified to simulate the plan: one
"freeze commit" that edits only ADR-0017 (a simulated section 15.5 freeze record and a simulated decision-2
entry), then a later commit that adds a results file, then (refusal probe) a later ADR edit. Nothing is
generated, trained or evaluated; the real repository is not touched.

usage: r2_freeze_plan_preconditions.py CLONE
"""
import subprocess
import sys
from pathlib import Path

from studies.p9 import pool
from studies.p9i import stages

clone = Path(sys.argv[1])
ADR = clone / "docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md"
GIT = ["git", "-C", str(clone), "-c", "user.name=auditor", "-c", "user.email=a@b", "-c", "commit.gpgsign=false"]


def commit(msg):
    subprocess.run([*GIT, "add", "-A"], check=True)
    subprocess.run([*GIT, "commit", "-qm", msg], check=True)
    return subprocess.run([*GIT, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def attempt(name, freeze):
    try:
        out = stages.check_preconditions("registered", clone, freeze)
        print(f"{name}: ACCEPTED {out}")
    except pool.StageRefused as e:
        print(f"{name}: REFUSED: {str(e)[:220]}")


ADR.write_text(ADR.read_text() + "\n### 15.5 Freeze record (SIMULATED BY THE AUDITOR)\n\ncode commit dd8b205; calibration sha256 087bf0b5...; U = 8192.\n\n### Decision 2 of Part I (SIMULATED BY THE AUDITOR, NOT A DECISION)\n")
freeze = commit("simulated freeze commit: ADR only")
changed = subprocess.run([*GIT, "diff", "--name-only", "dd8b205", freeze], check=True, capture_output=True, text=True).stdout.split()
print("files changed between the code commit and the simulated freeze commit:", changed)
attempt("HEAD = freeze commit, --freeze-commit = freeze", freeze)
(clone / "results/p9i-run-sim").mkdir(parents=True, exist_ok=True)
(clone / "results/p9i-run-sim/README.md").write_text("simulated\n")
commit("simulated results commit after the freeze")
attempt("HEAD = freeze + results commit, --freeze-commit = freeze", freeze)
attempt("--freeze-commit = dd8b205 (code commit, ADR differs)", "dd8b205")
ADR.write_text(ADR.read_text() + "\nlater ADR edit\n")
commit("simulated ADR edit after the freeze")
attempt("ADR edited after the freeze, --freeze-commit = freeze", freeze)
