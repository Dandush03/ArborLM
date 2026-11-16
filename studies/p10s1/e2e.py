# ruff: noqa: E501
"""P10S1 end-to-end exercise of the registered sequence on TEST seeds (ADR-0021 section 22, M8).

One command, run by the lead (or by ``tests/test_p10s1_e2e.py`` at tiny size)::

    uv run --locked python -m studies.p10s1.e2e [--workdir DIR]

It makes a throwaway clone of this repository, overlays the working tree on it and commits that, and then drives the real registered path inside the clone with the real fixed launch
scripts: the DRY prerequisites (calibration, rehearsal, timing, synthetic registry, projection), ``set-generation-cap``, ``launch/generate.sh``, ``freeze``, the freeze commit, Decision 2, and
``launch/{gates,train,evaluate,timing,simulate,analysis,report}.sh``. The test-only switch ``P10S1_TEST_SEEDS=1`` makes the registered driver accept ONLY the seed sets ``p10s1-test-0`` to ``-4``
(never a registered draw), with the synthetic backbone and the DRY sizes; without it, registered mode accepts only ``p10s1-draw-1..5``. It also runs the refusal probes (before the freeze, before
Decision 2, and a typed override) and checks that each refuses.

Every number it produces is tiny-size and synthetic and measures nothing; the point is that the commands, the commit checks and the hashes work in order. It reads no model, no corpus, no
registered seed. Nothing is written into this repository: the clone and every run directory live under ``--workdir``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import core

GIT_IDENTITY = ("-c", "user.name=p10s1-e2e", "-c", "user.email=p10s1-e2e@invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null")
REGISTERED_SCRIPTS = ("gates", "train", "evaluate", "timing", "simulate", "analysis", "report")
GENERATION_SECONDS = "600"  # a test-only figure for the tiny draws (the real cap is twice the rehearsal draw's measured G1 time)


def environment() -> dict[str, str]:
    """The clone is source files only: it uses this process's interpreter and environment. ``UV_PROJECT_ENVIRONMENT`` points the launch scripts' ``uv run`` at that environment and
    ``UV_NO_SYNC`` stops uv from changing it, so no virtual environment is ever created."""
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONPATH")}
    env[core.TEST_SWITCH_ENV] = "1"
    env["UV_OFFLINE"] = "1"
    env["UV_NO_SYNC"] = "1"
    env["UV_PROJECT_ENVIRONMENT"] = sys.prefix
    return env


class Runner:
    """Runs commands in the clone, keeps each one's output in ``logs/`` and every result in ``steps``."""

    def __init__(self, workdir: Path, clone: Path) -> None:
        self.workdir, self.clone = workdir, clone
        self.logs = workdir / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict[str, Any]] = []

    def run(self, name: str, argv: Sequence[str], *, expect: int | None = 0) -> int:
        started = time.monotonic()
        done = subprocess.run(list(argv), cwd=self.clone, env=environment(), capture_output=True, check=False)  # noqa: S603
        seconds = time.monotonic() - started
        log = self.logs / f"{len(self.steps):02d}-{name}.log"
        log.write_bytes(b"$ " + " ".join(argv).encode() + b"\n\n--- stdout\n" + done.stdout + b"\n--- stderr\n" + done.stderr)
        ok = expect is None or done.returncode == expect
        self.steps.append({"step": name, "argv": list(argv), "exit": done.returncode, "expected": expect, "ok": ok, "seconds": round(seconds, 1), "log": str(log)})
        return done.returncode

    def git(self, name: str, *argv: str) -> str:
        done = subprocess.run(["git", *GIT_IDENTITY, "-C", str(self.clone), *argv], capture_output=True, check=False)  # noqa: S603, S607
        ok = done.returncode == 0
        self.steps.append({"step": f"git {name}", "argv": ["git", *argv], "exit": done.returncode, "expected": 0, "ok": ok, "seconds": 0.0, "log": None})
        if not ok:
            raise RuntimeError(f"git {' '.join(argv)} failed: {done.stderr.decode()[:400]}")
        return done.stdout.decode().strip()


def stages(*argv: str) -> list[str]:
    return [sys.executable, "-m", "studies.p10s1.stages", *argv]


def make_clone(source: Path, clone: Path) -> None:
    """A clone of ``source``'s HEAD with the working tree (tracked and untracked, not ignored) laid over it, so the clone runs exactly the code under test."""
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(source), str(clone)], check=True, capture_output=True)  # noqa: S603, S607
    listed = subprocess.run(["git", "-C", str(source), "ls-files", "-z", "--cached", "--others", "--exclude-standard"], check=True, capture_output=True).stdout  # noqa: S603, S607
    wanted = {p for p in listed.decode().split("\0") if p}
    tracked = subprocess.run(["git", "-C", str(clone), "ls-files", "-z"], check=True, capture_output=True).stdout.decode().split("\0")  # noqa: S603, S607
    for name in tracked:
        if name and name not in wanted:
            (clone / name).unlink(missing_ok=True)
    for name in sorted(wanted):
        src = source / name
        if src.is_file():
            target = clone / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)


def run_e2e(workdir: Path, source: Path | None = None) -> dict[str, Any]:
    """The whole sequence; returns the summary (also written to ``<workdir>/E2E_SUMMARY.json``). Exit status 0 only when every step ended as expected and the report exists."""
    source = (source or core.repo_root()).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    if any(workdir.iterdir()):
        raise FileExistsError(f"{workdir} is not empty")
    clone = workdir / "clone"
    r = Runner(workdir, clone)
    run_dir, dry_root = workdir / "registered-run", workdir / "dry"
    summary: dict[str, Any] = {"source": str(source), "clone": str(clone), "workdir": str(workdir), "switch": f"{core.TEST_SWITCH_ENV}=1 (test seed sets only; DRY sizes; synthetic backbone)", "note": "tiny synthetic sizes: nothing here measures anything"}
    try:
        make_clone(source, clone)
        r.git("add code", "add", "-A")
        r.git("commit code", "commit", "--quiet", "--allow-empty", "-m", "e2e: code under test")
        # before the freeze nothing registered runs: a launch script on a commit with no freeze plan refuses
        head = r.git("rev-parse", "rev-parse", "HEAD")
        r.run("probe: gates.sh before the freeze", ["sh", "studies/p10s1/launch/gates.sh", str(run_dir), head], expect=2)
        # the prerequisites: calibration, rehearsal, timing, synthetic registry and projection, all DRY (the projection and the other records the freeze binds)
        r.run("dry prerequisites", stages("dry", "--out-root", str(dry_root), "--workers", "3"))
        reh, cal = dry_root / "P10S1DRY-rehearsal", dry_root / "P10S1DRY-calibration"
        r.run("set-cap (the computed cap of the projection)", stages("set-cap", "--projection", str(reh / "projection.json")))
        r.run("set-generation-cap", stages("set-generation-cap", "--generation-seconds", GENERATION_SECONDS))
        r.git("add generation cap", "add", "-A")
        r.git("commit generation cap", "commit", "--quiet", "-m", "e2e: generation cap set")
        code = r.git("rev-parse", "rev-parse", "HEAD")
        r.run("generate.sh (five test draws)", ["sh", "studies/p10s1/launch/generate.sh", str(run_dir), code, str(cal / "calibration.json")])
        r.run(
            "freeze",
            stages("freeze", "--run-dir", str(run_dir), "--projection", str(reh / "projection.json"), "--calibration", str(cal / "calibration.json"), "--timing", str(reh / "timing.json"), "--gates", str(reh / "gates.json")),
        )
        r.git("add freeze", "add", "-A")
        r.git("commit freeze", "commit", "--quiet", "-m", "e2e: freeze")
        freeze = r.git("rev-parse", "rev-parse", "HEAD")
        r.run("probe: gates.sh before Decision 2", ["sh", "studies/p10s1/launch/gates.sh", str(run_dir), freeze], expect=2)
        decision = clone / "results" / "p10s1-freeze-e2e" / "DECISION_2.md"
        decision.parent.mkdir(parents=True, exist_ok=True)
        decision.write_text(f"# Decision 2 (end-to-end exercise on test seeds)\n\nFreeze commit: {freeze}\n\nDECISION: RUN\n\nThis file stands in for the lead's recorded decision in the exercise; it decides nothing.\n", encoding="utf-8")
        r.git("add decision 2", "add", "-A")
        r.git("commit decision 2", "commit", "--quiet", "-m", "e2e: decision 2 record")
        r.run("probe: typed stage cap", stages("registered", "gates", "--run-dir", str(run_dir), "--freeze-commit", freeze, "--stage-cap-seconds", "999999"), expect=2)
        for name in REGISTERED_SCRIPTS:
            if r.run(f"{name}.sh", ["sh", f"studies/p10s1/launch/{name}.sh", str(run_dir), freeze], expect=0) != 0:
                break
        analysis_path = run_dir / "analysis.json"
        if analysis_path.is_file():
            data = core.read_record(analysis_path, "analysis")["result"]
            from . import classes

            summary["analysis"] = {"status": data["assessment"]["status"], "capacity": classes.printable(data["outcome"]["capacity"]["label"]), "efficiency": classes.printable(data["outcome"]["efficiency"]["label"]), "saturation": classes.printable(data["outcome"]["saturation"]["label"])}
        summary["freeze_commit"] = freeze
        summary["report"] = "RESULTS.md written (the run directory is removed at the end)" if (run_dir / "results" / "results.json").is_file() else None
        ledger = clone / "experiments" / f"{core.STUDY}-ledger.json"
        summary["ledger_entries"] = len(json.loads(ledger.read_text())["entries"]) if ledger.is_file() else 0
        summary["draws"] = sorted(p.name for p in (run_dir / "draws").iterdir()) if (run_dir / "draws").is_dir() else []
        plan_path = clone / "studies" / "p10s1" / "freeze" / "plan.json"
        if plan_path.is_file():
            plan = json.loads(plan_path.read_text())
            summary["plan"] = {"data_manifests": sorted(plan["data_manifests"]), "generation": plan["generation"]}
        summary["report_bytes"] = (run_dir / "results" / "RESULTS.md").stat().st_size if (run_dir / "results" / "RESULTS.md").is_file() else 0
    except Exception as exc:  # noqa: BLE001  (the exercise reports its own failure and keeps every log)
        summary["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for folder in (clone, run_dir, dry_root):  # a clone is source files and outputs only: removed on success and on failure; the logs and the summary stay
            shutil.rmtree(folder, ignore_errors=True)
    summary["steps"] = r.steps
    summary["ok"] = bool(summary.get("report")) and "error" not in summary and all(s["ok"] for s in r.steps)
    (workdir / "E2E_SUMMARY.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m studies.p10s1.e2e", description=__doc__)
    parser.add_argument("--workdir", default=None, help="an empty or new directory (default: a new temporary directory)")
    parser.add_argument("--source", default=None, help="the repository to clone (default: this one)")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="p10s1-e2e-"))
    summary = run_e2e(workdir, Path(args.source) if args.source else None)
    brief = {k: v for k, v in summary.items() if k != "steps"}
    brief["steps"] = [f"{'ok ' if s['ok'] else 'FAIL'} {s['step']} (exit {s['exit']}, expected {s['expected']}, {s['seconds']} s)" for s in summary["steps"]]
    print(json.dumps(brief, indent=1))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
