# ruff: noqa: E501
"""Report step of D0 after the driver's rendering defect (lead decision 1, 2026-11-25): ``python -m studies.p10is2d0.finalize_only --out <run dir> --cause <text>``.

It never recomputes a pass. It refuses unless the run directory is exactly the state the driver left after its last pass (launch.json; no run_complete.json and no report.txt; 96 pass records, 24 gate passes, 6 statistics
records, the gate files), the tree is clean, and the only code that differs from the launch commit is finalize.py and finalize_only.py under studies/p10is2d0 (plus tests/ and docs/). It writes the SHA-256 of every
pass/statistics/gate record BEFORE reading any of them, appends to resumes.json, then performs the driver's post-pass steps by calling finalize/run/passes directly (driver.py is not edited and its same-commit check is
not bypassed: this is a different entry point with its own, stricter, check)."""

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from studies.p10is2.common import core
from studies.p10is2.quantities import Thresholds

from . import finalize, passes, run
from .driver import PART_T_RUN, REPO, jwrite, say

EXIT_ENGINEERING = 5
ALLOWED_STUDY_FILES = frozenset({"studies/p10is2d0/finalize.py", "studies/p10is2d0/finalize_only.py"})
ALLOWED_PREFIXES = ("tests/", "docs/")
NOTE = "report step re-run after a rendering defect; lead decision 1"
RECORD_DIRS = ("passes", "gate_passes", "stats")
GATE_FILES = ("identity.json", "repro.json", "no_write_demonstration.json", "gate_record.json")


def expected_record_paths(out: Path) -> dict[str, list[Path]]:
    main, gate = passes.main_tasks(), passes.gate_tasks()
    return {
        "passes": [passes.record_path(out, t["id"]) for t in main if t["kind"] == "pass"],
        "stats": [passes.record_path(out, t["id"]) for t in main if t["kind"] == "stats"],
        "gate_passes": [passes.record_path(out, t["id"]) for t in gate],
    }


def check_run_directory(out: Path) -> None:
    """Refusals of lead decision 1 (3a); nothing is read except the existence and names of files."""
    if not (out / "launch.json").is_file():
        raise run.D0Refused("refused: launch.json is absent")
    for name in ("run_complete.json", "report.txt"):
        if (out / name).exists():
            raise run.D0Refused(f"refused: {name} already exists")
    if (out / "records").exists():
        raise run.D0Refused("refused: records/ already exists (nothing is overwritten)")
    exp = expected_record_paths(out)
    for d in RECORD_DIRS:
        have = {p.name for p in (out / d).glob("*.json")} if (out / d).is_dir() else set()
        want = {p.name for p in exp[d]}
        if have != want:
            raise run.D0Refused(f"refused: {d}/ holds {len(have)} records, expected exactly {len(want)} (missing {sorted(want - have)[:3]}, unexpected {sorted(have - want)[:3]})")
    for g in GATE_FILES:
        if not (out / "gates" / g).is_file():
            raise run.D0Refused(f"refused: gates/{g} is absent")


def check_code_difference(changed: list[str]) -> list[str]:
    """Lead decision 1 (3b): within studies/p10is2d0 only finalize.py and finalize_only.py may differ from the launch commit; elsewhere only tests/ and docs/."""
    bad = [f for f in changed if not (f in ALLOWED_STUDY_FILES or f.startswith(ALLOWED_PREFIXES))]
    if bad:
        raise run.D0Refused(f"refused: files other than finalize.py, finalize_only.py, tests/ and docs/ differ from the launch commit: {bad}")
    return changed


def git(repo: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True, check=True, timeout=60).stdout.strip()  # noqa: S603, S607


def hash_records(out: Path) -> dict[str, str]:
    """SHA-256 of every pass, statistics and gate record, by hashing bytes only (no JSON is parsed)."""
    h: dict[str, str] = {}
    for d in (*RECORD_DIRS, "gates"):
        for p in sorted((out / d).glob("*.json")):
            h[f"{d}/{p.name}"] = run._sha(p)
    return h


def post_pass(out: Path, registry: Mapping[str, float], cfg: Any, part_t_run: Path, launch_commit: str, finalize_commit: str, led: passes.Ledger, t_start: float) -> int:
    """The driver's post-pass steps (driver.py, after the main workers), by calling finalize/run/passes directly."""
    gate_record = json.loads((out / "gates" / "gate_record.json").read_text())
    rec = finalize.build_records(out, registry, Thresholds.from_config(cfg))
    stats_by_cell = {f"r{t['rep']}/{t['order']}": json.loads(passes.record_path(out, t["id"]).read_text()) for t in passes.main_tasks() if t["kind"] == "stats"}
    led.tick()
    cost = {"worker_seconds_total": passes.charged_total(out / "cost"), "worker_hours_total": passes.charged_total(out / "cost") / 3600.0, "cap_worker_hours": passes.CAP_SECONDS / 3600.0, "orchestrator_wall_seconds": time.monotonic() - t_start}
    commit_line = f"{launch_commit} (launch); finalize commit {finalize_commit}; {NOTE}"
    text = finalize.render(rec, gate_record, stats_by_cell, cost, commit_line, f"COMPLETE ({NOTE})")
    (out / "report.txt").write_text(text, encoding="utf-8")
    jwrite(out / "records" / "readings.json", {**rec, "oracle_line": core.ORACLE_LINE, "label": "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL"})
    jwrite(out / "records" / "stats.json", stats_by_cell)
    jwrite(out / "records" / "gate_record.json", gate_record)
    jwrite(out / "records" / "cost.json", cost)
    after_t = run.fs_manifest(part_t_run)
    diff = run.manifest_diff(json.loads((out / "inputs/partt_run_dir.before.json").read_text()), after_t)
    changed = bool(diff["added"] or diff["removed"] or diff["changed"])
    jwrite(out / "inputs" / "partt_run_dir.after.json", after_t)
    jwrite(out / "records" / "partt_run_dir_diff.json", diff)
    led.tick()
    jwrite(out / "run_complete.json", {"launch_commit": launch_commit, "finalize_commit": finalize_commit, "note": NOTE, "part_t_run_dir_changed": changed, "engineering_stop": changed, "worker_hours": passes.charged_total(out / "cost") / 3600.0})
    counts = {k: len(v) for k, v in diff.items()}
    say(f"COMPLETE; worker hours {passes.charged_total(out / 'cost') / 3600.0:.3f}; part T run directory diff counts {counts}")
    return EXIT_ENGINEERING if changed else 0


def finalize_run(out: Path, repo: Path, cause: str) -> int:
    t_start = time.monotonic()
    check_run_directory(out)
    status = git(repo, "status", "--porcelain")
    if status:
        raise run.D0Refused(f"refused: the working tree is not clean:\n{status}")
    launch_commit = json.loads((out / "launch.json").read_text())["commit"]
    head = git(repo, "rev-parse", "HEAD")
    subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", launch_commit, head], check=True, timeout=60)  # noqa: S603, S607
    changed = check_code_difference([f for f in git(repo, "diff", "--name-only", launch_commit, head).splitlines() if f])
    jwrite(out / "inputs" / "finalize_code_difference.json", {"launch_commit": launch_commit, "finalize_commit": head, "changed_files": changed})
    jwrite(out / "inputs" / "record_hashes_before_finalize.json", hash_records(out))  # (3c): before any record is read
    prior = json.loads((out / "resumes.json").read_text()) if (out / "resumes.json").is_file() else []
    jwrite(out / "resumes.json", [*prior, {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": "finalize_only", "cause": cause or "UNSTATED", "launch_commit": launch_commit, "finalize_commit": head}])
    led = passes.Ledger(out, f"finalize_{int(time.time())}")
    led.note = {"stage": "finalize_only"}
    led.tick()
    cfg = core.load_config("T", repo / core.CONFIG_T)
    reg = json.loads((PART_T_RUN / "registry.json").read_text())
    return post_pass(out, reg, cfg, PART_T_RUN, launch_commit, head, led, t_start)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cause", required=True)
    a = ap.parse_args(argv)
    try:
        return finalize_run(Path(a.out), REPO, a.cause)
    except run.D0Refused as e:
        say(str(e))
        return EXIT_ENGINEERING


if __name__ == "__main__":
    sys.exit(main())
