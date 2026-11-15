# ruff: noqa: E501
"""P10S0 end-to-end exercise of the whole registered sequence through the real launch scripts, on test seeds (the audit's M7; ADR-0020 addendum: "the whole registered sequence is exercised end to end on
test seeds through the real launch scripts before the freeze").

One command: ``uv run --locked python -m studies.p10s0.e2e [--out <dir>]``. It copies the working tree (tracked and untracked, not ignored) into a throwaway git repository, marks a run directory with the
``TEST_PROFILE`` marker (which selects seed sets ``p10s0-test-draw-k`` / ``p10s0-test-reserve-k``, tiny sizes and a synthetic backbone: test seeds 920001+ only, never a registered or rehearsal seed), and runs, in the
clone and through the real scripts and commands (the clone is source files only: a ``uv`` shim on PATH runs the current interpreter, so no environment is built; the clone and its outputs are deleted at the end, success or failure; only e2e.log and summary.json stay):

  rehearsal (tiny, the DRY profile) -> generation of a draw and its measured time -> ``set-generation-cap`` -> gates on that draw (timed) -> ``projection`` (rehearsed rates scaled so that Q1 needs CUT 3, and the
  probe's rehearsal peak raised above 1.5 GiB so that the probe is NOT RUN — MEMORY) -> ``caps`` -> a commit -> ``launch/generate.sh`` -> ``freeze-plan`` -> the freeze commit -> ``launch/gates.sh``, ``q1.sh``,
  ``q1_gate.sh``, ``wx.sh``, ``probe.sh`` (refused), ``analysis.sh``, ``report.sh``, and a second ``q1.sh`` (refused).

Everything it prints is a status of the pipeline on a random backbone, never a result. It runs nothing at real size and reads no registered, rehearsal or check seed. Exit code 0 when every expectation held.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import core

SCALED_Q1_FULL_HOURS = 8.3  # the scaled rehearsal makes the full Q1 projection 8.3 h: 2 x 8.3 h > 16 h, so cut 3 applies, and cut 3 (about 6 h) still fits
OVER_LIMIT_BYTES = 2 * 1024**3  # a rehearsal peak above 1.5 GiB for the 32K/64K items
GIT = ["git", "-c", "commit.gpgsign=false", "-c", "user.name=e2e", "-c", "user.email=e2e@example.invalid"]


class E2EError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path, log: Path, *, expect: int | None = 0, env: dict[str, str] | None = None) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as stream:
        stream.write(("$ " + " ".join(cmd) + "\n").encode())
        proc = subprocess.run(cmd, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})}, check=False)  # noqa: S603
        stream.write(f"[exit {proc.returncode}]\n".encode())
    if expect is not None and proc.returncode != expect:
        raise E2EError(f"{' '.join(cmd[:8])}: exit {proc.returncode}, expected {expect} (see {log})")
    return proc.returncode


def copy_working_tree(source: Path, target: Path) -> None:
    names = subprocess.run(["git", "-C", str(source), "ls-files", "-z", "--cached", "--others", "--exclude-standard"], capture_output=True, check=True).stdout.decode().split("\0")  # noqa: S603, S607
    for name in sorted(n for n in names if n):
        src = source / name
        if not src.is_file():
            continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def commit(clone: Path, message: str, log: Path) -> str:
    run([*GIT, "-C", str(clone), "add", "-A"], clone, log)
    run([*GIT, "-C", str(clone), "commit", "-q", "-m", message], clone, log)
    return subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, check=True, text=True).stdout.strip()  # noqa: S603, S607


def clone_env(clone: Path, shim: Path) -> dict[str, str]:
    """The environment of every command in the clone: the clone's sources first on the path, and a ``uv`` shim first on PATH. The launch scripts call ``uv run --locked python -m ...``; the shim runs the
    current interpreter instead, so the clone is source files only and no virtual environment is ever built (the lead's constraint on disk use)."""
    return {"PYTHONPATH": str(clone), "PATH": f"{shim}{os.pathsep}{os.environ.get('PATH', '')}", "UV_OFFLINE": "1"}


def write_uv_shim(shim: Path) -> Path:
    shim.mkdir(parents=True, exist_ok=True)
    exe = shim / "uv"
    exe.write_text(f'#!/bin/sh\n# test shim: `uv run --locked python <args>` runs the current interpreter, so no environment is created\nif [ "$1" = run ] && [ "$2" = --locked ] && [ "$3" = python ]; then\n    shift 3\n    exec "{sys.executable}" "$@"\nfi\necho "uv shim: unsupported: $*" >&2\nexit 64\n')
    exe.chmod(0o755)
    return exe


def stages(clone: Path, log: Path, *argv: str, expect: int | None = 0) -> int:
    return run([sys.executable, "-m", "studies.p10s0.stages", *argv], clone, log, expect=expect, env=clone_env(clone, clone.parent / "shim"))


def script(clone: Path, log: Path, name: str, run_dir: Path, freeze: str, *, expect: int | None = 0) -> int:
    return run(["sh", f"studies/p10s0/launch/{name}.sh", str(run_dir), freeze], clone, log, expect=expect, env=clone_env(clone, clone.parent / "shim"))


def solve_factor(projection: dict[str, Any]) -> float:
    """The factor on seconds-per-update that makes the full Q1 projection 8.3 h. Only the training rate is scaled (start-up, evaluation and the guard are not), so the projection is linear in the factor:
    total(f) = O + f R, solved from the projection at f = 1 and f = 2 with the budget functions themselves."""
    import dataclasses

    from . import budget, stages

    rates = stages.rates_of(projection)

    def total(f: float) -> float:
        scaled = {k: dataclasses.replace(v, seconds_per_update=v.seconds_per_update * f) for k, v in rates.items()}
        return budget.block_projection(core.q1_cells(), scaled, unit=int(projection["unit_updates"])).total_seconds

    t1, t2 = total(1.0), total(2.0)
    rate_part = t2 - t1
    return (SCALED_Q1_FULL_HOURS * 3600.0 - (t1 - rate_part)) / rate_part


def scale_rehearsal(src: Path, dst: Path, factor: float) -> None:
    """A copy of the rehearsal records with every seconds-per-update multiplied by ``factor`` and the 32K/64K items' peak raised above the memory limit (test data only; the whitelist is unchanged)."""
    shutil.copytree(src, dst)
    for path in dst.glob("rehearsal/*/rehearsal.json"):
        rec = json.loads(path.read_text())
        rec["seconds_per_update"] = float(rec["seconds_per_update"]) * factor
        if rec["celltype"] == "32K/64K":
            rec["peak_rss_bytes"] = OVER_LIMIT_BYTES
            rec["sampled_rss_bytes"] = OVER_LIMIT_BYTES
        path.write_text(json.dumps(rec, sort_keys=True))


def diagnose(work: Path, log: Path) -> None:
    """Before the working directory is deleted, put into the log which tasks of which stage did not complete and why (stage manifests of every run directory)."""
    with log.open("a", encoding="utf-8") as stream:
        for manifest in sorted(work.glob("clone/experiments/*/*/manifest.json")):
            try:
                data = json.loads(manifest.read_text())
            except ValueError:
                continue
            bad = [t for t in data.get("tasks", []) if t.get("status") != "completed"]
            if bad:
                stream.write(f"DIAGNOSIS {manifest.parent.name}: status {data.get('status')}, cap {data.get('caps', {}).get('stage_seconds')}, {len(bad)} of {len(data['tasks'])} tasks not completed; first: {json.dumps(bad[0])[:500]}\n")
        for failed in sorted(work.glob("clone/experiments/*/*/*.failed.json"))[:3]:
            stream.write(f"DIAGNOSIS {failed.name}: {failed.read_text()[:500]}\n")


def run_e2e(out: Path, source: Path | None = None) -> dict[str, Any]:
    """The exercise. ``out`` keeps only ``e2e.log`` and ``summary.json``: the clone, its run directories and the uv shim live in ``out/work`` and are deleted when it ends, on success and on failure."""
    source = source or core.repo_root()
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    if work.exists():
        raise E2EError(f"{work} exists")
    work.mkdir()
    try:
        return _run_e2e(out, work, source)
    except E2EError:
        diagnose(work, out / "e2e.log")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _run_e2e(out: Path, work: Path, source: Path) -> dict[str, Any]:
    log = out / "e2e.log"
    clone = work / "clone"
    write_uv_shim(work / "shim")
    summary: dict[str, Any] = {"out": str(out), "steps": {}}
    clone.mkdir()
    copy_working_tree(source, clone)
    run(["git", "init", "-q"], clone, log)
    base = commit(clone, "e2e base: copy of the working tree", log)
    summary["base_commit"] = base
    exp = clone / "experiments"
    arm = clone / "studies/p10s0/freeze/arm_selection.json"
    if not arm.is_file():
        raise E2EError("the arm-selection record is missing from the tree")
    # --- rehearsal (tiny), generation time, the generation cap, the gates of the rehearsal draw ---
    reh = exp / "E2E-rehearsal"
    stages(clone, log, "rehearse", "--dry", "--run-dir", str(reh), "--arm-selection", str(arm), "--stage-cap-seconds", "3000")
    gen = exp / "E2E-generation"
    stages(clone, log, "generate", "--dry", "--run-dir", str(gen), "--stage-cap-seconds", "600")
    gen_manifest = next((gen).glob("generate-*/manifest.json"))
    stages(clone, log, "set-generation-cap", "--generate-manifest", str(gen_manifest))
    stages(clone, log, "gates", "--dry", "--run-dir", str(gen), "--arm-selection", str(arm), "--stage-cap-seconds", "3000")
    gates_manifest = json.loads((gen / "gates/manifest.json").read_text())
    gates_seconds = float(sum(t["seconds"] for t in gates_manifest["tasks"]))
    per_draw = float(json.loads((gen / "gates.json").read_text())["timing"]["per_draw_seconds"])
    generate_seconds = float(sum(t["seconds"] for t in json.loads(gen_manifest.read_text())["tasks"]))
    summary["steps"]["generation_cap"] = core.generation_block(clone / core.DEFAULT_CONFIG)
    # --- projection, scaled so that cut 3 applies and the probe is over the memory limit; caps ---
    probe_json = exp / "E2E-projection-unscaled.json"
    stages(clone, log, "projection", "--dry", "--rehearsal-alone", str(reh), "--rehearsal-busy", str(reh), "--arm-selection", str(arm), "--out", str(probe_json))
    factor = solve_factor(json.loads(probe_json.read_text()))
    scaled = exp / "E2E-rehearsal-scaled"
    scale_rehearsal(reh, scaled, factor)
    projection = exp / "E2E-projection.json"
    stages(clone, log, "projection", "--dry", "--rehearsal-alone", str(scaled), "--rehearsal-busy", str(scaled), "--arm-selection", str(arm), "--out", str(projection))
    summary["steps"]["scale_factor"] = factor
    caps = clone / "studies/p10s0/freeze/stage_caps.json"
    stages(clone, log, "caps", "--dry", "--projection", str(projection), "--out", str(caps), "--gates-wall-seconds", str(gates_seconds), "--gates-per-draw-seconds", str(per_draw), "--analysis-wall-seconds", "1", "--report-wall-seconds", "1", "--generate-wall-seconds", str(generate_seconds))
    decision = clone / "results/p10s0-freeze-e2e/DECISION.md"
    decision.parent.mkdir(parents=True)
    decision.write_text("# End-to-end exercise on test seeds (throwaway clone): not a decision about S0.\n")
    pre_freeze = commit(clone, "e2e pre-freeze inputs: generation cap, cap table, run decision stand-in", log)
    # --- registered generation through the real script, the freeze plan, the freeze commit ---
    run_dir = exp / "E2E-registered"
    run_dir.mkdir(parents=True)
    (run_dir / core.TEST_PROFILE_MARKER).write_text("test profile: test seeds, tiny sizes, synthetic backbone\n")
    summary["steps"]["generate.sh"] = run(["sh", "studies/p10s0/launch/generate.sh", str(run_dir), pre_freeze], clone, log, expect=None, env=clone_env(clone, clone.parent / "shim"))
    if not (run_dir / "draw_plan.json").is_file():
        raise E2EError("generate.sh wrote no draw plan")
    plan_path = clone / "studies/p10s0/freeze/plan.json"
    stages(clone, log, "freeze-plan", "--test-profile", "--test-candidate", "A5-D", "--run-dir", str(run_dir), "--arm-selection", str(arm), "--projection", str(projection), "--out", str(plan_path))
    freeze = commit(clone, "e2e freeze", log)
    summary["freeze_commit"] = freeze
    # --- the registered sequence, through the scripts ---
    order = [("gates", 0), ("q1", 0), ("q1_gate", 0), ("wx", 0), ("probe", 2), ("analysis", 0), ("report", 0), ("q1", 2)]
    codes: list[tuple[str, int]] = []
    for name, expect in order:
        codes.append((name, script(clone, log, name, run_dir, freeze, expect=expect)))
    summary["steps"]["scripts"] = codes
    start = json.loads((run_dir / "q1_start.json").read_text())
    gate = json.loads((run_dir / "q1_gate.json").read_text())
    analysis = json.loads((run_dir / "analysis.json").read_text())["result"]
    summary["steps"].update(
        cut3=start["cut3"], cut_label=start["label"], candidate=gate["candidate"], blocks=gate["blocks"], outcome_row=analysis["outcome"]["row"], outcome_label=analysis["outcome"]["label"],
        results_markdown_bytes=len((run_dir / "results" / "RESULTS.md").read_bytes()), ledger_entries=len(json.loads((exp / "P10S0-ledger.json").read_text())["entries"]),
    )  # fmt: skip
    if not (start["cut3"] and start["label"] == core.CUT3_LABEL):
        raise E2EError("the Q1 start record does not carry cut 3 and its label")
    if gate["blocks"]["probe"]["status"] != "NOT RUN — MEMORY" or not gate["blocks"]["wx"]["run"]:
        raise E2EError(f"unexpected block decisions: {gate['blocks']}")
    if core.CUT3_LABEL not in analysis["outcome"]["label"] or not (run_dir / "results/RESULTS.md").is_file():
        raise E2EError("the analysis does not print the cut-3 label or the report is missing")
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m studies.p10s0.e2e", description=__doc__)
    parser.add_argument("--out", default=None, help="a new directory for the throwaway clone and the logs (default: a temporary directory)")
    args = parser.parse_args(argv)
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="p10s0-e2e-"))
    try:
        summary = run_e2e(out)
    except E2EError as exc:
        print(f"E2E FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
