# ruff: noqa: E501
"""The end-to-end exercise of the whole registered sequence (audit B M12): ``python -m studies.p10s2.e2e``.

It runs the real launch scripts, in the real order, on a SOURCE-ONLY THROWAWAY CLONE of this working tree (the tracked and untracked-but-not-ignored source files, committed into a fresh git repository
in a temporary folder), with the CURRENT interpreter: ``uv`` is replaced on ``PATH`` by a stub that execs ``sys.executable`` with the arguments after ``python``, and ``PYTHONPATH`` puts the clone's
``src`` first. NO new virtual environment is created, nothing is installed, nothing is downloaded, no real model or dataset is touched, and no registered, calibration or rehearsal seed of the real
configuration is drawn: the clone's configuration is rewritten so that the registered, calibration and rehearsal seed sets lie inside 229001-229999, the read layers are those of the stand-in student,
the rungs are tiny, and the "registered" sizes are the stand-ins' (every substitution is listed in the result under ``substitutions``). The code that runs is the registered code: the same launch
scripts, the same ``stages`` driver, the same freeze, the same ledger, the same stage functions. The clone and everything in it is deleted when the exercise ends (``--keep`` keeps it for inspection).

What it exercises, in order: the data-generation step is replaced by the stand-in pre-freeze steps (``datagen.sh`` needs downloads and is not run; its ledger charge is written by this exercise);
one calibration stopped by its stage cap (exit 4); ``calibrate.sh``; ``prefreeze_gates.sh``; ``rehearse.sh`` (the layer and the LoRA learning rate are read from ``calibration.json``); the freeze; the
freeze commit; the run decision commit; refused registered stages (no gates record, a typed caps file, ``--repo``); ``gates.sh``, ``train.sh``, ``evaluate.sh``, ``timing.sh``, ``recompute.sh``,
``analysis.sh``, ``report.sh``; a second run of a finished stage (refused); and one recomputation difference (a tampered recomputed score) through the analysis. Every number is a mechanics check on
stand-ins, never a result. Self-check only: not independent review, not Astra validation, not human approval.
"""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

from . import core

SOURCE_PREFIXES = ("studies/", "src/", "configs/", "tests/test_p10s2_", "tests/test_support", ".gitignore", "pyproject.toml", "uv.lock", "docs/decisions/ADR-0022")
GIT = ("git", "-c", "user.name=e2e", "-c", "user.email=e2e@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null")


# --- the clone's test configuration ---------------------------------------------------------------------------------------------------------------
def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, int | float):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    raise TypeError(type(v))


def dumps_toml(d: dict[str, Any]) -> str:
    out: list[str] = []
    for table, body in d.items():
        if isinstance(body, dict):
            out.append(f"\n[{table}]")
            out += [f"{k} = {_fmt(v)}" for k, v in body.items()]
        else:
            out.insert(0, f"{table} = {_fmt(body)}")
    return "\n".join(out) + "\n"


def test_configuration(base: dict[str, Any], *, training_device: str, relax_pilot: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """The real configuration with the substitutions of the exercise. Returns (configuration, the substitutions made, for the record). Thresholds are not touched, except that ``relax_pilot`` (used only after the
    exercise has shown, with the real threshold, that a failed pilot stops the sequence) replaces the pilot threshold of this throwaway clone: a stand-in student trained for a few hundred updates closes no gap,
    and the mechanics of the later stages cannot be exercised behind a pilot that fails by design."""
    cfg = json.loads(json.dumps(base))
    dry = cfg["dry"]
    sub: dict[str, Any] = {}

    def put(table: str, key: str, value: Any) -> None:
        sub[f"{table}.{key}"] = {"real": cfg[table].get(key), "exercise": value}
        cfg[table][key] = value

    for key, value in (("replicate_bases", [229001, 229101, 229201, 229301]), ("registered_low", 229001), ("registered_high", 229399), ("calibration_low", 229401), ("calibration_high", 229599), ("calibration_base", 229401), ("rehearsal_low", 229601), ("rehearsal_high", 229799), ("rehearsal_base", 229601), ("draw_count", 2), ("test_low", 229900), ("test_high", 229999), ("partition", 229381), ("partition_streams", list(range(229382, 229393)))):
        put("seeds", key, value)
    put("memory", "read_layers", [0, 1])
    put("memory", "rows_per_stage", dry["rows_per_stage"])
    put("data", "vocabulary", dry["vocabulary"])
    put("data", "router_decision_token", dry["router_decision_token"])
    put("data", "general_window_tokens", dry["window_tokens"])
    put("data", "seen_items", dry["seen_items"])
    put("training", "batch", dry["batch"])
    put("training", "replay_rows", dry["replay_rows"])
    put("training", "lora_rank_single", 2)
    put("training", "lora_rank_joint", 4)
    for key, dkey in (("updates", "router_updates"), ("batch", "router_batch"), ("none_prefixes", "none_prefixes"), ("none_prefixes_full_length", "none_prefixes_full_length"), ("prefix_tokens", "prefix_tokens")):
        put("router", key, dry[dkey])
    put("budget", "rungs", [[2, 4], [1, 4], [2, 2], [1, 2]])
    put("budget", "timing_items", 3)
    put("budget", "training_device", training_device)
    put("calibration", "read_layers", [0, 1])
    put("calibration", "updates", 150)
    put("rehearsal", "short_updates", 3)
    put("rehearsal", "full_updates", 6)
    put("gates", "g4_repeat_updates", 5)
    if relax_pilot:
        put("gates", "pilot_gap_min", -1.0)
    return cfg, sub


# --- the clone -----------------------------------------------------------------------------------------------------------------------------------
def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=timeout)  # noqa: S603
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n--- stdout\n{p.stdout[-3000:]}\n--- stderr\n{p.stderr[-3000:]}")
    return p


def source_files(root: Path) -> list[str]:
    out = run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root).stdout.splitlines()
    return [f for f in out if f.startswith(SOURCE_PREFIXES) and (root / f).is_file()]


def stamp_data_record(clone: Path, pre: Path) -> None:
    """The exercise's stand-in data step is not ``datagen``; it stamps its record with what datagen records (re-check confirmation F3): the code commit, the configuration and requirements SHA-256 and where transformers
    was loaded from (here: nowhere). Called again after the clone's configuration is committed, so that the record names the configuration that is frozen."""
    from arborlm.io import file_sha256

    path = pre / "data" / "prefreeze_record.json"
    rec = json.loads(path.read_text())
    rec.update(code_commit=head(clone), config_sha256=file_sha256(clone / core.DEFAULT_CONFIG), requirements_sha256=file_sha256(clone / "studies" / "p10s2" / "requirements-datagen.txt"), transformers_file="stand-in (the exercise's data step is not datagen: no transformers)")
    path.write_text(json.dumps(rec, sort_keys=True, indent=1))


def relax_pilot_threshold(clone: Path, base: dict[str, Any], *, training_device: str) -> dict[str, Any]:
    """Replace the pilot threshold in the clone's configuration (see ``test_configuration``) and commit it; returns the substitution record."""
    cfg, subs = test_configuration(base, training_device=training_device, relax_pilot=True)
    (clone / core.DEFAULT_CONFIG).write_text("# the exercise's test configuration (studies/p10s2/e2e.py): seed sets inside 229001-229999, stand-in sizes, tiny rungs; the pilot threshold is replaced (stand-ins close no gap)\n" + dumps_toml(cfg))
    commit_all(clone, "e2e: the pilot threshold of this throwaway clone is replaced")
    rec: dict[str, Any] = subs["gates.pilot_gap_min"]
    return rec


def make_clone(parent: Path, *, source: Path | None = None, training_device: str = "cpu") -> tuple[Path, dict[str, Any], dict[str, str]]:
    """The source-only throwaway clone with the test configuration committed, a stub ``uv`` and the environment that makes the clone's processes use the current interpreter. Returns (clone, substitutions,
    environment)."""
    src = source or core.ROOT
    clone = parent / "clone"
    for f in source_files(src):
        dst = clone / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, dst)
    cfg_path = clone / core.DEFAULT_CONFIG
    with (src / core.DEFAULT_CONFIG).open("rb") as fh:
        base = tomllib.load(fh)
    cfg, subs = test_configuration(base, training_device=training_device)
    cfg_path.write_text("# the exercise's test configuration (studies/p10s2/e2e.py): seed sets inside 229001-229999, stand-in sizes, tiny rungs; thresholds untouched\n" + dumps_toml(cfg))
    run([*GIT, "init", "-q", "-b", "main"], cwd=clone)
    run([*GIT, "add", "-A"], cwd=clone)
    run([*GIT, "commit", "-q", "-m", "e2e: source-only clone with the test configuration"], cwd=clone)
    bindir = parent / "bin"
    bindir.mkdir()
    stub = bindir / "uv"
    stub.write_text(
        '#!/bin/sh\n# stub for `uv run --locked [--with-requirements F] python ...`: the current interpreter, no environment is created\n'
        'shift; [ "${1:-}" = "--locked" ] && shift\n[ "${1:-}" = "--with-requirements" ] && shift 2\n[ "${1:-}" = "python" ] && shift\nexec "$E2E_PYTHON" "$@"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTORCH_ENABLE_MPS_FALLBACK", "PYTEST_CURRENT_TEST")}  # the clone is the exercise's own throwaway root: the test guard (which protects the real checkout) is not inherited
    env.update({"PATH": f"{bindir}:{os.environ['PATH']}", "E2E_PYTHON": sys.executable, "PYTHONPATH": str(clone / "src"), "PYTHONDONTWRITEBYTECODE": "1"})
    return clone, subs, env


def head(clone: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=clone).stdout.strip()


def commit_all(clone: Path, message: str) -> str:
    run([*GIT, "add", "-A"], cwd=clone)
    run([*GIT, "commit", "-q", "-m", message], cwd=clone)
    return head(clone)


def script(clone: Path, env: dict[str, str], name: str, *args: str, timeout: float = 3600) -> subprocess.CompletedProcess[str]:
    return run(["sh", str(clone / "studies/p10s2/launch" / f"{name}.sh"), *args], cwd=clone, env=env, check=False, timeout=timeout)


def stages_cmd(clone: Path, env: dict[str, str], *args: str, timeout: float = 3600) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-m", "studies.p10s2.stages", *args], cwd=clone, env=env, check=False, timeout=timeout)


def expect(label: str, p: subprocess.CompletedProcess[str], code: int, results: list[dict[str, Any]], *, in_output: str | None = None) -> None:
    out = (p.stdout + p.stderr)
    ok = p.returncode == code and (in_output is None or in_output in out)
    results.append({"step": label, "exit": p.returncode, "expected_exit": code, "ok": ok, "tail": out[-600:] if not ok else ""})
    if not ok:
        raise AssertionError(f"{label}: exit {p.returncode}, expected {code}" + (f", expected the text {in_output!r}" if in_output else "") + f"\n{out[-2500:]}")


def mps_available() -> bool:
    import torch

    return bool(torch.backends.mps.is_available())


# --- the exercise ----------------------------------------------------------------------------------------------------------------------------------
def exercise(workdir: Path | None = None, *, keep: bool = False) -> dict[str, Any]:
    """Run the whole sequence; returns a record (steps, ledger summary, substitutions). Raises ``AssertionError`` at the first step that does not behave as the registered procedure requires."""
    t_start = time.perf_counter()
    parent = Path(tempfile.mkdtemp(prefix="p10s2-e2e-", dir=workdir))
    results: list[dict[str, Any]] = []
    try:
        device = "mps" if mps_available() else "cpu"
        clone, subs, env = make_clone(parent, training_device=device)
        record: dict[str, Any] = {"clone": str(clone) if keep else "(deleted)", "interpreter": sys.executable, "training_device": device, "substitutions": subs, "new_virtual_environment": False, "steps": results}
        pre, reg = parent / "pre-run", parent / "registered-run"
        # --- the data-generation step on stand-ins (datagen.sh needs downloads and is not run) ---
        from . import standins
        from .ledger import Ledger
        from .stages import _dry_equivalence
        from .worldio import write_bundle

        t0 = time.perf_counter()
        bundle, prerec = standins.build_synthetic_bundle(4)
        bundle.extra["equivalence"] = _dry_equivalence(bundle, 1)
        write_bundle(bundle, pre / "data" / "bundle")
        from arborlm.io import file_sha256

        prerec["bundle_manifest_sha256"] = file_sha256(pre / "data" / "bundle" / "manifest.json")  # what datagen records at the end of its step (re-check B, N3)
        (pre / "data" / "prefreeze_record.json").write_text(json.dumps(core.jsonable(prerec), sort_keys=True, indent=1))
        stamp_data_record(clone, pre)
        shutil.copytree(pre / "data" / "bundle", clone / "data" / "p10s2-bundle")
        led = Ledger(clone / "experiments" / "P10S2" / "ledger.jsonl")
        led.charge("datagen", time.perf_counter() - t0, process="e2e: stand-in data generation (datagen.sh is not run: it needs downloads)")
        code = head(clone)
        # --- calibration stopped by its stage cap (one cap stop, exit 4), in a run directory of its own ---
        shutil.copytree(pre / "data", parent / "capstop-run" / "data")  # the stage needs the completed data record of its bundle (confirmation F9)
        p = stages_cmd(clone, env, "calibrate", "--run-dir", str(parent / "capstop-run"), "--code-commit", code, "--stage-cap-seconds", "0.3", "--data-dir", str(pre / "data" / "bundle"))
        expect("calibrate with a stage cap of 0.3 s stops (cap stop)", p, 4, results, in_output="calibration stopped")
        assert (parent / "capstop-run" / "calibration_stopped.json").exists()
        # --- a failed pilot with the REAL threshold stops the sequence: the rehearsal refuses (the stand-in student closes no gap in a mechanics-size calibration) ---
        shutil.copytree(pre / "data", parent / "pilot-run" / "data")
        expect("calibrate.sh with the real pilot threshold fails the pilot (exit 3)", script(clone, env, "calibrate", str(parent / "pilot-run"), code), 3, results, in_output="calibration record written")
        assert json.loads((parent / "pilot-run" / "calibration.json").read_text())["pilot"]["ok"] is False
        expect("rehearse.sh refuses after a failed pilot", script(clone, env, "rehearse", str(parent / "pilot-run"), code), 2, results, in_output="STUDENT CANNOT USE THE MEMORY")
        with (core.ROOT / core.DEFAULT_CONFIG).open("rb") as fh:
            record["substitutions"]["gates.pilot_gap_min"] = relax_pilot_threshold(clone, tomllib.load(fh), training_device=device)
        code = head(clone)
        stamp_data_record(clone, pre)
        # --- the pre-freeze stages through their launch scripts ---
        p = script(clone, env, "calibrate", str(pre), code)
        results.append({"step": "calibrate.sh", "exit": p.returncode, "ok": p.returncode == 0, "tail": (p.stdout + p.stderr)[-400:]})
        if p.returncode != 0:
            raise AssertionError(f"calibrate.sh did not complete with a passed pilot (exit {p.returncode}): {(p.stdout + p.stderr)[-800:]}")
        cal = json.loads((pre / "calibration.json").read_text())
        record["calibration_selection"] = cal["selection"]
        expect("prefreeze_gates.sh", script(clone, env, "prefreeze_gates", str(pre), code), 0, results)
        expect("rehearse.sh (reads the layer and the LoRA learning rate from calibration.json)", script(clone, env, "rehearse", str(pre), code), 0, results, in_output="rung rule outcome")
        reh = json.loads((pre / "rehearsal.json").read_text())
        record["rehearsal"] = {"decision": reh["headroom_check"]["decision"]["outcome"], "proposal": reh["headroom_check"]["proposal"], "charged_hours_at_end_of_rehearsal": reh["charged_hours_at_end_of_rehearsal"]}
        if reh["headroom_check"]["proposal"] is not None:
            expect("raise-cap (recomputed from the rehearsal record)", stages_cmd(clone, env, "raise-cap", "--run-dir", str(pre)), 0, results)
        # --- the freeze, the freeze commit and the run decision ---
        expect("freeze (layer, learning rates, pilot, cap and device from the records)", stages_cmd(clone, env, "freeze", "--pre-run-dir", str(pre), "--run-dir", str(reg), "--data-dir", "data/p10s2-bundle"), 0, results, in_output="freeze files written")
        freeze_commit = commit_all(clone, "e2e: freeze commit")
        d = clone / "results" / "p10s2-freeze-e2e"
        d.mkdir(parents=True)
        (d / "DECISION.md").write_text(f"# e2e run decision (a throwaway exercise, not a decision of the lead)\n\nDECISION: RUN\n\nFreeze commit: {freeze_commit}\n")
        commit_all(clone, "e2e: run decision")
        plan = json.loads((clone / core.PLAN_FILE).read_text())
        record["frozen_design"] = plan["design"]
        record["freeze_commit"] = freeze_commit
        # --- refused stages ---
        expect("train before gates is refused (no completion record of gates)", script(clone, env, "train", str(reg), freeze_commit), 2, results, in_output="requires the completion record of gates")
        expect("a typed caps file is refused", stages_cmd(clone, env, "registered", "gates", "--run-dir", str(reg), "--freeze-commit", freeze_commit, "--caps", str(parent / "typed_caps.json")), 2, results, in_output="invalid choice")
        expect("--repo is refused", stages_cmd(clone, env, "registered", "gates", "--run-dir", str(reg), "--freeze-commit", freeze_commit, "--caps", str(core.CAPS_FILE), "--repo", str(parent)), 2, results, in_output="unrecognized arguments")
        # --- the registered stages, in order, through their launch scripts ---
        for name in ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report"):
            expect(f"{name}.sh", script(clone, env, name, str(reg), freeze_commit), 0, results)
            assert json.loads((reg / "stages" / f"{name}.json").read_text())["status"] in ("completed", "stopped"), name
        expect("a second gates.sh is refused (a stage is run once)", script(clone, env, "gates", str(reg), freeze_commit), 2, results, in_output="already has a record")
        outcome = json.loads((reg / "outcome.json").read_text())["outcome"]
        record["label"] = outcome["label_with_design"]
        record["recomputation_state"] = outcome["recomputation"]["state"]
        record["registered_stage_peaks_bytes"] = {n: json.loads((reg / "memory" / f"{n}.json").read_text())["peak_bytes"] for n in ("gates", "train", "evaluate", "timing", "recompute")}
        seeds = [u for f in (reg / "seeds").glob("*.json") for u in json.loads(f.read_text()).get("recorded", [])]
        assert seeds and all(229001 <= u["seed"] <= 229399 for u in seeds if u["mode"] == "registered-run"), "a registered-run process drew a seed outside the exercise's registered set"
        assert not any(220001 <= u["seed"] <= 228999 for u in seeds), "a real registered seed was drawn"
        # --- one recomputation difference through the analysis (on a copy: the registered run directory is write-once) ---
        tamper = parent / "tampered-run"
        shutil.copytree(reg, tamper)
        for rel in ("outcome.json", "REPORT.md", "stages/analysis.json", "stages/report.json", "seeds/analysis.json"):
            (tamper / rel).unlink()
        recs = json.loads((tamper / "recompute" / "r0.json").read_text())
        lab = next(k for k, v in recs["cells"].items() if v.get("status") == "completed" and v.get("scores"))
        snap = next(iter(recs["cells"][lab]["scores"]))
        recs["cells"][lab]["scores"][snap]["panels"]["E_A"]["mean"] = recs["cells"][lab]["scores"][snap]["panels"]["E_A"]["mean"] + 0.25
        (tamper / "recompute" / "r0.json").write_text(json.dumps(recs))
        from . import stages

        tout = stages.stage_analysis(tamper, plan["design"], plan["prefreeze"])
        diffs = tout["recomputation"].get("differences", [])
        assert diffs and lab in tout["recomputation"]["not_evaluated_cells"] or tout["label"].startswith("ENGINEERING-FAILURE"), "the tampered recomputed score was not reported"
        results.append({"step": "a tampered recomputed score is listed and the cell is NOT_EVALUATED (or the label is ENGINEERING-FAILURE)", "ok": True, "label": tout["label"], "differences": len(diffs), "cell": lab})
        record["ledger"] = led.summary()
        record["wall_seconds"] = time.perf_counter() - t_start
        record["ok"] = all(r["ok"] for r in results)
        return record
    finally:
        if keep:
            sys.stdout.write(f"kept: {parent}\n")
        else:
            shutil.rmtree(parent, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m studies.p10s2.e2e", description=__doc__.split("\n\n")[0] if __doc__ else None)
    ap.add_argument("--workdir", default=None, help="a folder for the temporary clone (default: the system temporary directory)")
    ap.add_argument("--keep", action="store_true", help="keep the clone and the run directories for inspection")
    a = ap.parse_args(argv)
    rec = exercise(Path(a.workdir) if a.workdir else None, keep=a.keep)
    sys.stdout.write(json.dumps(core.jsonable(rec), indent=1, sort_keys=True, default=str) + "\n")
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
