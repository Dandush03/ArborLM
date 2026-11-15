"""A12 (auditor, Opus 5.5): registered-mode preconditions (accept and refuse paths) of
studies.p9i.stages.check_preconditions, run against a throw-away clone of the repository at e626280
(argument 1). The clone is modified (an ADR line appended and committed; an untracked file) to probe the
refusals; the real repository is not touched."""
import sys, subprocess
from pathlib import Path
from studies.p9i import stages
from studies.p9 import pool
clone = Path(sys.argv[1])
def attempt(name, commit):
    try:
        print(name, "ACCEPTED", stages.check_preconditions("registered", clone, commit))
    except pool.StageRefused as e:
        print(name, "REFUSED:", str(e)[:200])
attempt("clean clone, freeze=HEAD", "HEAD")
attempt("clean clone, freeze=HEAD~1", "HEAD~1")
attempt("freeze=939b4bf (calibration code)", "939b4bf")
attempt("no freeze commit", None)
# simulate decision-2 approval recorded in the ADR after the freeze
adr = clone / "docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md"
adr.write_text(adr.read_text() + "\nDecision 2 of Part I: approved by the lead (simulated by the auditor).\n")
subprocess.run(["git", "-C", str(clone), "-c", "user.name=a", "-c", "user.email=a@b", "-c", "commit.gpgsign=false", "commit", "-qam", "approval"], check=True)
attempt("approval recorded in the ADR after freeze, freeze=HEAD~1", "HEAD~1")
# a results README added after freeze
(clone / "results/p9i-x").mkdir(parents=True, exist_ok=True); (clone / "results/p9i-x/README.md").write_text("x")
attempt("untracked file present", "HEAD")
