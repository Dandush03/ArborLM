# ruff: noqa: E501
"""P10-I-S2 Part T, the TARGETED rehearsal (ruling 51; ``partt_amendment/AMENDMENT_NOTES.md``).

It exercises exactly what the cap amendment changes and what had never run at registered size, on REHEARSAL seeds and the stand-in panels, reading no outcome value:
(a) one M-ii cell at registered size (U updates) run ALONE (workers = 1), timed, with its MPS driver memory recorded; its parents (M1, M-append) are trained at the ADR's 200 updates only because the cell's cost does not depend on its parent's content;
(b) a stop at a cap and a resume of the same cell from its checkpoint (a rehearsal cap forced through a plan copy with a small allowance, then the real plan);
(c) the charged-time cap check and the memory admission check, each made to refuse once with tiny worker processes;
(d) a PREFLIGHT: the registered-mode preconditions that a rehearsal does not run, read-only, against the real worktree and the real registered run directory (the L11 guard, the platform, the clean tree, the run directory's mode, the
amendment record and the cap headroom of the amended plan on the registered ledger).
The record is ``rehearsal_targeted.json``; ``partt_amendment.targeted_gate`` reads it at the freeze. Gates, evaluate, controls, combined, recompute, analysis and report are NOT re-rehearsed here (the first counting
rehearsal completed them against the pre-amendment plan): a departure from ADR-0025 section 10 item 5, stated in the notes."""

import json
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import partt_amendment, partt_counting, partt_tasks
from .common import core, gates, runner
from .common import plan as planmod
from .common.core import StageRefused

CAP_STOP_SECONDS = 700.0  # the M-ii cell is stopped by the cap after about this much charged time (about 1,700 updates alone: past the checkpoint at 1,500), then resumed
TINY_SECONDS = 3.0


def preflight(repo: Path, cfg: Mapping[str, Any], plan: planmod.Plan, amend: Mapping[str, Any]) -> dict[str, Any]:
    """Check (d), read-only."""
    items: dict[str, Any] = {}
    reg = Path(plan.data["run_dir"])
    items["foreign_freeze_records"] = planmod.foreign_freeze_records(repo)
    items["platform_problems"] = gates.platform_problems(cfg)
    dirty = core.git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().rstrip()
    items["tree_clean"] = not dirty
    items["pythonpath_clean"] = not any(q and os.path.realpath(q) == os.path.realpath(core.DURABLE_PACKAGES) for q in os.environ.get("PYTHONPATH", "").split(os.pathsep))
    mode_file = reg / "run_mode.json"
    items["registered_run_dir_mode"] = read_json(mode_file).get("mode") if mode_file.is_file() else None
    try:
        core.require_ignored_run_dir(repo, reg)
        items["registered_run_dir_ignored"] = True
    except StageRefused as e:
        items["registered_run_dir_ignored"] = str(e)
    ckdir = reg / "checkpoints"
    health = checkpoint_health(ckdir) if ckdir.is_dir() else {}
    items["checkpoints"] = health
    items["checkpoints_loadable"] = all(v["loadable"] for v in health.values())
    items["amendment_manifest_problem"] = partt_amendment.manifest_problem(plan.data.get("manifests"), amend, repo)
    ledger = reg / "charged_ledger.json"
    if ledger.is_file():
        led = core.Ledger(ledger, "T", 1e12)
        plan_charge = float((plan.data.get("charge_before_freeze") or {}).get("seconds", 0.0))
        allowance = float(plan.data.get("counting_allowance_hours", 0.0)) * 3600.0
        own_left = plan.cap_seconds("train") - led.charged("train")
        total_left = plan.total_cap_seconds() - plan_charge - allowance - led.charged()
        items["train_cap_left_seconds"] = own_left
        items["total_left_seconds_after_the_targeted_allowance"] = total_left
        items["registered_ledger_total_seconds"] = led.charged()
        items["amended_cap_lets_the_stage_resume"] = min(own_left, total_left) > 0.0
    else:
        items["amended_cap_lets_the_stage_resume"] = False
    passed = not items["foreign_freeze_records"] and not items["platform_problems"] and items["tree_clean"] is True and items["pythonpath_clean"] is True and items["registered_run_dir_mode"] == "registered" and items["registered_run_dir_ignored"] is True and items["checkpoints_loadable"] is True and items["amendment_manifest_problem"] is None and items["amended_cap_lets_the_stage_resume"] is True
    return {"passed": bool(passed), **items}


def checkpoint_health(directory: Path, pattern: str = "*M-ii*.ckpt") -> dict[str, dict[str, Any]]:
    """Read-only (audit 17): each checkpoint matching ``pattern`` is loaded on CPU exactly as the resume path loads it (``torch.load`` of the dict ``engine.train_cell`` reads: ``update``, ``params``, ``opt``,
    ``losses``) and checked for structure, an integer update counter within the calibrated updates' reach, one loss per update and finite parameters. Nothing is written; no tensor value or loss is returned, only
    loadable yes/no and the update the cell would resume from. ``engine.train_cell`` itself does NOT validate on load and does not fall back to a fresh start: a corrupt file makes the cell ERROR."""
    import torch

    out: dict[str, dict[str, Any]] = {}
    for f in sorted(directory.glob(pattern)):
        try:
            ck = torch.load(f, weights_only=False, map_location="cpu")
            missing = [k for k in ("update", "params", "opt", "losses") if k not in ck]
            if missing:
                out[f.name] = {"loadable": False, "update": None, "problem": f"missing {missing}"}
                continue
            update = int(ck["update"])
            finite = all(bool(torch.isfinite(p).all()) for p in ck["params"])
            problems = [] if len(ck["losses"]) == update and finite and update >= 0 and isinstance(ck["opt"], dict) and "state" in ck["opt"] else ["structure, loss count or finiteness"]
            out[f.name] = {"loadable": not problems, "update": update, "problem": problems[0] if problems else None}
        except Exception as e:  # a truncated or corrupt file
            out[f.name] = {"loadable": False, "update": None, "problem": type(e).__name__}
    return out


def tiny_tasks(directory: Path, n: int, seconds: float) -> list[runner.Task]:
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for i in range(n):
        res = directory / f"t{i}.result.json"
        code = f"import json,sys,time;time.sleep({seconds});open(sys.argv[1],'w').write(json.dumps({{'t':time.time()}}))"
        out.append(runner.Task(f"tiny{i}", (sys.executable, "-c", code, str(res)), res, directory / f"t{i}.failed.json", directory / f"t{i}.log"))
    return out


def cap_and_admission_checks(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check (c): two worker processes of TINY_SECONDS each. Charged-time cap: a cap of 1.5 s kills both well inside the 3 s each would take in wall time (wall-clock accounting would not have stopped them before they ended).
    Admission: a threshold no machine meets lets the first worker start and holds the second until the first has ended."""
    kw = {"rss_worker_bytes": 2**30, "rss_aggregate_bytes": 2**31, "poll": 0.05}
    t0 = time.monotonic()
    out, wall = runner.run_tasks(tiny_tasks(directory / "cap", 2, TINY_SECONDS), workers=2, cap_seconds=1.5, **kw)
    killed = [k for k, v in out.items() if v["status"] == runner.KILLED_CAP]
    cap = {"passed": len(killed) == 2 and wall < TINY_SECONDS, "statuses": {k: v["status"] for k, v in out.items()}, "wall_seconds": wall, "cap_seconds": 1.5, "worker_seconds_each_would_take": TINY_SECONDS, "elapsed": time.monotonic() - t0}
    out2, wall2 = runner.run_tasks(tiny_tasks(directory / "admit", 2, 1.0), workers=2, cap_seconds=60.0, admit_free_bytes=2**60, **kw)
    done = [v for v in out2.values() if v["status"] == runner.COMPLETED]
    ts = sorted(read_json(directory / "admit" / f"t{i}.result.json")["t"] for i in range(2)) if len(done) == 2 else []
    adm = {"passed": len(done) == 2 and len(ts) == 2 and ts[1] - ts[0] >= 0.9, "wall_seconds": wall2, "second_started_after_first_ended": bool(ts and ts[1] - ts[0] >= 0.9), "admit_free_bytes": 2**60}
    return cap, adm


def capped_plan_file(plan: planmod.Plan, run_dir: Path, led: core.Ledger) -> Path:
    """A copy of the plan whose counting allowance leaves CAP_STOP_SECONDS of the rehearsal cap (kept under the run directory, never under ``freeze/``)."""
    data = json.loads(json.dumps(plan.data))
    data["counting_allowance_hours"] = (led.charged() + CAP_STOP_SECONDS) / 3600.0
    path = run_dir / "cap_probe/partt_plan_capped.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    return path


def run_targeted_rehearsal(repo: Path, run_dir: Path, part_q_dir: Path, *, launch: partt_counting.Launch = partt_counting.subprocess_launch, clock: Callable[[], float] = time.monotonic, charged_ledgers: Sequence[str] = ()) -> dict[str, Any]:
    from .partt_stages import claim_run_dir

    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)
    core.require_ignored_run_dir(repo, run_dir)
    plan_file = repo / core.PLAN_T
    plan = planmod.Plan.load(plan_file, "T")
    amend = partt_amendment.load(cfg, repo)
    if not amend:
        raise StageRefused("refused: a targeted rehearsal exists only with an amendment ([cap_amendment] and its record)")
    claim_run_dir(run_dir, "rehearsal", plan.data["run_dir"])
    led = core.Ledger(run_dir / "charged_ledger.json", "T", 1e12)
    t0 = clock()
    problems: list[str] = []
    checks: dict[str, Any] = {}
    logs = run_dir.parent / f"{run_dir.name}_driver_logs"

    def go(name: str, stage: str, kind: str, expect: int, *extra: str) -> bool:
        cap = partt_tasks.rehearsal_cap_seconds(cfg, kind, plan) + 900.0
        rc = launch(partt_counting.stage_argv(repo, stage, run_dir, kind, *extra), logs / f"{name}.log", cap)
        if rc != expect:
            problems.append(f"{name}: exit {rc}, expected {expect}")
        return rc == expect

    checks["preflight"] = preflight(repo, cfg, plan, amend)
    if not checks["preflight"]["passed"]:
        problems.append("preflight failed")
    cap_chk, adm_chk = cap_and_admission_checks(run_dir / "tiny")
    checks["charged_time_cap_refused_once"], checks["memory_admission_refused_once"] = cap_chk, adm_chk
    if not (partt_tasks.stage_marker(run_dir, "gates")).is_file():
        partt_tasks.mark_complete(run_dir, "gates", "targeted")  # gates are not re-rehearsed here (the first counting rehearsal and the registered run completed them): stated in the record and the notes
    m_ii_id = "train|M-ii|AB|r0"
    mii: dict[str, Any] = {"passed": False}
    stop: dict[str, Any] = {"passed": False}
    if not problems:
        ok = go("train-parents", "train", "measuring", 0, "--rehearsal-arms", "M1,M-append")
        ok = ok and go("train-m-ii-to-the-cap", "train", "counting", partt_counting.EXIT_PAUSED, "--plan-file", str(capped_plan_file(plan, run_dir, led)), "--rehearsal-arms", "M-ii")
        ckpts = sorted(p.name for p in (run_dir / "checkpoints").glob("*M-ii*")) if (run_dir / "checkpoints").is_dir() else []
        man = partt_counting.runner_manifest(run_dir, "train") or {}
        status = (man.get("tasks", {}).get(m_ii_id) or {}).get("status")
        stop_ok = ok and status == runner.KILLED_CAP and bool(ckpts)
        ok = ok and stop_ok and go("train-m-ii-resume", "train", "counting", 0, "--rehearsal-arms", "M-ii")
        tf = partt_tasks.tasks_dir(run_dir, "train") / f"{partt_tasks.safe(m_ii_id)}.timing.json"
        cell = partt_tasks.tasks_dir(run_dir, "train") / f"{partt_tasks.safe(m_ii_id)}.cell.json"
        resumed = cell.is_file() and bool(read_json(cell).get("resumed"))
        timing = read_json(tf) if tf.is_file() else {}
        stop = {"passed": bool(ok and resumed), "first_attempt_status": status, "checkpoints": ckpts, "resumed_from_checkpoint": resumed, "cap_stop_seconds": CAP_STOP_SECONDS}
        units = (timing.get("kinds") or {}).get("units", {}).get("train:M-ii")
        mii = {"passed": bool(ok and resumed and timing and units and int(units) == int(plan.data["calibration"]["U"])), "updates": units, "task_body_seconds": timing.get("task_body_seconds"), "seconds_of_the_resumed_attempt": (timing.get("kinds") or {}).get("seconds", {}).get("train:M-ii"), "mps_driver_allocated_bytes": (timing.get("mps") or {}).get("driver_allocated_bytes"), "peak_rss_bytes": timing.get("peak_rss_bytes"), "workers": 1, "charged_seconds_in_the_run": led.charged("train"), "note": "the cell was stopped once by the cap and resumed; the figure that sets the M-ii cost is the charged sum of both attempts"}
    checks["m_ii_alone_at_registered_size"] = mii
    checks["cap_stop_and_resume_from_checkpoint"] = stop
    complete = not problems and all(checks[c].get("passed") is True for c in partt_amendment.REQUIRED_CHECKS)
    rec = {
        **core.envelope("rehearsal", "T"), "kind_of_rehearsal": "targeted", "status": "COMPLETE" if complete else "INCOMPLETE", "plan_file_sha256": file_sha256(plan_file), "caps_provisional": bool(plan.data.get("caps_provisional", True)),
        "checks": checks, "problems": problems, "not_rehearsed_here": ["gates", "evaluate", "controls", "combined", "recompute", "analysis", "report"], "amendment_record": amend["record"],
        "platform": gates.platform_record(), "timings": {"total_seconds": clock() - t0}, "charged_seconds": led.charged(), "charged_ledgers": {str(run_dir / "charged_ledger.json"): led.charged(), **{str(Path(x)): core.Ledger(Path(x), "T", 1e12).charged() for x in charged_ledgers}},
        "targeted_allowance_hours": amend["allowance_hours"], "part_q_dir": str(part_q_dir),
    }  # fmt: skip
    partt_counting.write_rehearsal_record(run_dir / "rehearsal_targeted.json", rec)
    if not complete:
        raise StageRefused(f"refused: the targeted rehearsal is incomplete: {problems or [c for c in partt_amendment.REQUIRED_CHECKS if checks[c].get('passed') is not True]}")
    return rec


if __name__ == "__main__":  # python -m studies.p10is2.partt_targeted <checkpoints directory> [glob]: read-only, CPU, prints loadable yes/no and the update per checkpoint
    d = Path(sys.argv[1])
    for name, r in checkpoint_health(d, sys.argv[2] if len(sys.argv) > 2 else "*M-ii*.ckpt").items():
        print(f"{name}: loadable={'yes' if r['loadable'] else 'no'} resume_from_update={r['update']}" + (f" ({r['problem']})" if r["problem"] else ""))
