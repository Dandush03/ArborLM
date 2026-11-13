"""Re-audit check (no study data): what the relaxed end-of-stage repository check
(arborlm.p7a_stage.tracked_state_sha256, the code under audit) detects, on a scratch CLONE of this
repository with the current untracked P7-A files copied in, before and after a simulated freeze commit.
The real repository is only read (git clone, file copies); nothing in it is written.

Run (repo root):
  uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/reaudit/check_stage_state.py <scratch>
"""

import shutil
import subprocess
import sys
from pathlib import Path

from arborlm.p7a_stage import tracked_state_sha256

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "user.email=a@example.invalid", "-c", "user.name=a", *args], cwd=repo, text=True
    )


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    clone = scratch / "clone"
    if clone.exists():
        shutil.rmtree(clone)
    scratch.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "clone", "-q", "--no-hardlinks", str(REPO), str(clone)])
    for rel in [*[p.relative_to(REPO) for p in (REPO / "src/arborlm").glob("p7a_*.py")],
                *[p.relative_to(REPO) for p in (REPO / "tests").glob("test_p7a_*.py")],
                Path("docs/decisions/ADR-0013-p7a-storage-page-locality.md")]:
        shutil.copyfile(REPO / rel, clone / rel)
    shutil.copytree(REPO / "docs/reviews/p7a-preflight-2026-11-13", clone / "docs/reviews/p7a-preflight-2026-11-13")
    lines = []

    def probe(name: str, action, undo) -> None:  # type: ignore[no-untyped-def]
        before = tracked_state_sha256(clone)
        action()
        after = tracked_state_sha256(clone)
        undo()
        restored = tracked_state_sha256(clone) == before
        lines.append(f"  {name}: {'DETECTED' if after != before else 'not detected'}"
                     f"{'' if restored else ' (state not restored!)'}")

    def write(rel: str, text: str):  # type: ignore[no-untyped-def]
        path = clone / rel
        old = path.read_bytes() if path.exists() else None

        def do() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

        def undo() -> None:
            if old is None:
                path.unlink()
            else:
                path.write_bytes(old)
        return do, undo

    def append(rel: str):  # type: ignore[no-untyped-def]
        old = (clone / rel).read_bytes()
        return write(rel, old.decode() + "\n# edit\n")

    cases = [
        ("new file docs/reviews/p7a-results-audit/independent_sim_actual.json",
         *write("docs/reviews/p7a-results-audit/independent_sim_actual.json", "{}")),
        ("new log file at repo root (p7a_operator.log)", *write("p7a_operator.log", "log")),
        ("new file results/p7a-2026-11-13/simulate/X/result.json (results/ is NOT git-ignored)",
         *write("results/p7a-2026-11-13/simulate/X/result.json", "{}")),
        ("edit of a tracked P5 record results/p5-2026-11-13/<cell>/result.json",
         *append(str(next((clone / "results/p5-2026-11-13").glob("b101-o301-flat-s501/result.json")).relative_to(clone)))),
        ("edit of src/arborlm/p7a_core.py", *append("src/arborlm/p7a_core.py")),
        ("edit of tests/test_p7a_sim.py", *append("tests/test_p7a_sim.py")),
        ("edit of ADR-0013", *append("docs/decisions/ADR-0013-p7a-storage-page-locality.md")),
        ("edit of docs/reviews/p7a-preflight-2026-11-13/independent_sim.py",
         *append("docs/reviews/p7a-preflight-2026-11-13/independent_sim.py")),
        ("new file src/arborlm/p7a_extra.py", *write("src/arborlm/p7a_extra.py", "x = 1\n")),
        ("edit of tracked README.md", *append("README.md")),
    ]
    lines.append("BEFORE a freeze commit (P7-A files untracked, as now):")
    for name, do, undo in cases:
        probe(name, do, undo)
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "simulated freeze (scratch clone only)")
    lines.append("AFTER a simulated freeze commit of everything (P7-A sources, tests, ADR, review folder):")
    for name, do, undo in cases:
        probe(name, do, undo)
    text = "\n".join(lines) + "\n"
    (HERE / "outputs" / "stage_state.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
