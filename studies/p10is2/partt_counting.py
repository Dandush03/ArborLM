# ruff: noqa: E501
"""The Part T rehearsals, driven through the SAME entry point as the registered run (ADR-0025 section 10; audit B1, B4; the lesson of Part Q's five stops).

Every stage is launched as ``sh studies/p10is2/launch/partt_registered.sh <stage> <run-dir> - --rehearsal ...`` in a FRESH process, in the registered order; the stage's tasks are worker processes of the task runner.
It is the registered launch script, the ``work`` entry point, ``partt_stages.execute_stage`` (the one function a registered stage and a rehearsal stage both call, with only ``mode`` differing), ``partt_tasks``, the
worker ``partt_stages task`` and ``partt_real.run_task`` / ``run_stage``. The documented overrides are listed in ``partt_rehearsal``. Records:

* COUNTING (``rehearsal_counting.json``): the candidate plan itself; each stage's status read from its real manifest or completion record; ONE forced pause and resume (a worker of the cell
  ``train|M1|AB|r0`` stops, exit 74, and the same command resumes it from its checkpoint) and ONE forced PAUSED — IDENTITY (a plan copy with one frozen hash altered exits 75 and writes nothing; the real plan then runs).
* MEASURING (``rehearsal_measuring.json``): the same stages against a plan built here from the config with the caps unset; per kind seconds per unit and per stage the per-process overhead apart, from WHOLE-PROCESS
  seconds; per worker the peak resident set (process tree and own), the MPS memory, the disk written and the load at start and end; the other studies alive. Its record carries ``caps_formula``.
"""

import json
import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import partt_caps, partt_plan, partt_tasks
from .common import core, gates, procs
from .common import plan as planmod
from .common.core import StageRefused

Launch = Callable[[Sequence[str], Path, float], int]  # (argv, log file, timeout seconds) -> exit code
EXIT_PAUSED, EXIT_IDENTITY = 4, planmod.IDENTITY_EXIT


def subprocess_launch(argv: Sequence[str], log: Path, timeout: float) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as fh:
        try:
            return subprocess.run(list(argv), stdout=fh, stderr=subprocess.STDOUT, timeout=timeout, check=False).returncode  # noqa: S603
        except subprocess.TimeoutExpired:
            return -9


def stage_argv(repo: Path, stage: str, run_dir: Path, kind: str, *extra: str) -> list[str]:
    return ["sh", str(repo / "studies/p10is2/launch/partt_registered.sh"), stage, str(run_dir), "-", "--rehearsal", "--rehearsal-kind", kind, *extra]


def altered_plan_file(plan: planmod.Plan, run_dir: Path) -> Path:
    """A copy of the plan with ONE frozen file's hash altered, kept under the run directory (never under freeze/). It names the plan's own run directory, so the check that fires is the frozen-file one."""
    data = json.loads(json.dumps(plan.data))
    data["frozen_files"][sorted(data["frozen_files"])[0]] = "0" * 64
    path = run_dir / "identity_probe/partt_plan_altered.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    return path


def completion(run_dir: Path, stage: str) -> dict[str, Any]:
    f = partt_tasks.stage_marker(run_dir, stage)
    return json.loads(f.read_text()) if f.is_file() else {}


def stage_record(run_dir: Path, stage: str, led: core.Ledger) -> dict[str, Any]:
    """A stage's status from its REAL records: the completion marker (the entry point's) and, for a task stage, the task runner's manifest."""
    man = runner_manifest(run_dir, stage)
    done = completion(run_dir, stage).get("status") == "COMPLETE"
    return {"status": "COMPLETE" if done else "NOT RUN", "manifest_status": (man or {}).get("status"), "seconds": led.charged(stage), "tasks": len((man or {}).get("tasks", {}))}


def runner_manifest(run_dir: Path, stage: str) -> dict[str, Any] | None:
    from .common import runner

    return runner.read_manifest(run_dir, stage)


def run_stages(repo: Path, run_dir: Path, plan: planmod.Plan, kind: str, launch: Launch, plan_file: Path | None, *, forced: dict[str, bool] | None, problems: list[str], timings: dict[str, float], clock: Callable[[], float]) -> bool:
    """The registered order, one fresh process per stage invocation; ``forced`` (counting) adds the one forced identity stop before ``train`` and the one forced pause inside it."""
    base = ("--plan-file", str(plan_file)) if plan_file else ()

    def go(name: str, stage: str, expect: int, *extra: str) -> bool:
        cap = partt_tasks.rehearsal_cap_seconds(core.load_config("T", repo / core.CONFIG_T), kind, plan)
        t = clock()
        rc = launch(stage_argv(repo, stage, run_dir, kind, *extra), run_dir.parent / f"{run_dir.name}_driver_logs" / f"{name}.log", cap + 900.0)
        timings[name] = clock() - t
        if rc != expect:
            problems.append(f"{name}: exit {rc}, expected {expect}")
        return rc == expect

    ok = True
    state_file = run_dir / "forced_events.json"
    if forced is not None and state_file.is_file():  # a resumed counting rehearsal: the forced events recorded once are not run again
        forced.update(read_json(state_file))
    for stage in partt_plan.STAGES:
        if not ok:
            break
        if partt_tasks.stage_marker(run_dir, stage).is_file():
            continue  # complete: a resume does not start it again
        if stage == "train" and forced is not None and not (forced["paused_identity_restore"] and forced["pause_resume"]):
            if not forced["paused_identity_restore"]:
                alt = altered_plan_file(plan, run_dir)
                ident = go("train-identity-altered-plan", stage, EXIT_IDENTITY, "--plan-file", str(alt))
                forced["paused_identity_restore"] = ident and not partt_tasks.stage_marker(run_dir, stage).exists() and runner_manifest(run_dir, stage) is None
                write_json(state_file, dict(forced))
                ok = ident
                if not ok:
                    break
            if not forced["pause_resume"]:
                updates = max(1, int(plan.data["calibration"]["U"]) // 2)  # ruling 27: the counting rehearsal trains at the calibrated U
                ok = go("train-forced-pause", stage, EXIT_PAUSED, *base, "--pause-after-updates", str(updates))
                if not ok:
                    break
                ok = go("train-resume", stage, 0, *base)
                forced["pause_resume"] = ok and _resumed(run_dir)
                write_json(state_file, dict(forced))
            continue
        ok = go(stage, stage, 0, *base)
    return ok


def _resumed(run_dir: Path) -> bool:
    f = partt_tasks.tasks_dir(run_dir, "train") / f"{partt_tasks.safe(partt_tasks.FORCED_PAUSE_CELL)}.cell.json"
    return f.is_file() and bool(read_json(f).get("resumed"))


def write_rehearsal_record(path: Path, rec: Mapping[str, Any]) -> None:
    """A rehearsal's record is written when the run ends, complete or not. A later (resumed) run that ends writes a new final record; the INCOMPLETE one before it is KEPT as ``<name>.attempt<n>.json``. A COMPLETE record is never replaced."""
    if path.exists():
        if read_json(path).get("status") == "COMPLETE":
            raise StageRefused(f"refused: {path} is COMPLETE; a complete rehearsal record is never replaced")
        n = 2
        while path.with_name(f"{path.stem}.attempt{n}.json").exists():
            n += 1
        path.rename(path.with_name(f"{path.stem}.attempt{n}.json"))
    core.write_record(path, rec, overwrite=False)


def run_counting_rehearsal(repo: Path, run_dir: Path, *, launch: Launch = subprocess_launch, clock: Callable[[], float] = time.monotonic, charged_ledgers: Sequence[str] = ()) -> dict[str, Any]:
    from .partt_stages import claim_run_dir

    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)
    core.require_ignored_run_dir(repo, run_dir)
    plan_file = repo / core.PLAN_T
    plan = planmod.Plan.load(plan_file, "T")
    claim_run_dir(run_dir, "rehearsal", plan.data["run_dir"])
    t0 = clock()
    problems: list[str] = []
    timings: dict[str, float] = {}
    forced = {"pause_resume": False, "paused_identity_restore": False}
    run_stages(repo, run_dir, plan, "counting", launch, None, forced=forced, problems=problems, timings=timings, clock=clock)
    led = core.Ledger(run_dir / "charged_ledger.json", "T", 1e12)
    stages = {s: stage_record(run_dir, s, led) for s in partt_plan.STAGES}
    gates_rec = read_json(run_dir / "gates.json") if (run_dir / "gates.json").is_file() else {}
    complete = all(v["status"] == "COMPLETE" for v in stages.values()) and all(forced.values()) and not problems
    rec = {
        **core.envelope("rehearsal", "T"), "kind_of_rehearsal": "counting", "status": "COMPLETE" if complete else "INCOMPLETE", "plan_file_sha256": file_sha256(plan_file), "caps_provisional": bool(plan.data.get("caps_provisional", True)),
        "stages": stages, "forced": forced, "problems": problems, "entry_point": "partt_registered.sh <stage> <run-dir> - --rehearsal, one fresh process per stage invocation; the stage's tasks are worker processes of the task runner",
        "rehearsal_draw": read_json(run_dir / "rehearsal_draw.json") if (run_dir / "rehearsal_draw.json").is_file() else None, "g4_mps": (gates_rec.get("gates") or {}).get("G4-MPS"), "platform": gates.platform_record(), "timings": {"total_seconds": clock() - t0, "process_seconds": timings}, "load": {"end": os.getloadavg()[0]},
        "other_studies_alive": procs.other_studies_alive(), "charged_seconds": led.charged(), "charged_ledgers": {str(run_dir / "charged_ledger.json"): led.charged(), **{str(Path(x)): core.Ledger(Path(x), "T", 1e12).charged() for x in charged_ledgers}},
        "plan_stage_items": {st: len(v) for st, v in plan.data["items"].items()}, "subset": "replicate 0; one cell of each of the ten trained types at full U; D_cal only",
    }  # fmt: skip
    write_rehearsal_record(run_dir / "rehearsal_counting.json", rec)
    if not complete:
        raise StageRefused(f"refused: the counting rehearsal is incomplete: {problems or 'a stage did not complete'}")
    return rec


def measuring_plan(repo: Path, run_dir: Path, part_q_dir: Path, part_q_plan: Path | None, manifests: Mapping[str, Any] | None) -> Path:
    """The measuring rehearsal's own plan, built here from the config with the caps unset and NO calibration result (ADR section 10: 200 updates of every trained cell type): a stand-in calibration block from the
    config's ``[rehearsal]`` section (U = 200, the grid's starting rates, the grid's read layer). Kept in the run directory, never under ``freeze/``; reused when the rehearsal resumes."""
    path = run_dir / "measuring_plan.json"
    if path.is_file():
        return path
    from .partt_stages import part_q_block

    cfg = core.load_config("T", repo / core.CONFIG_T)
    if not cfg["caps"]["provisional"] or any(float(v) != 0.0 for k, v in cfg["stage_caps"].items() if k != "calibration_hours"):
        raise StageRefused("refused: the config holds registered caps already; a measuring rehearsal runs with them unset, so that no stage can stop on a cap it is there to measure")
    r = cfg["rehearsal"]
    stand_in = {"U": int(r["updates"]), "converged": True, "store_rate": float(r["store_rate"]), "lora_rate": float(r["lora_rate"]), "etable_rate": float(r["etable_rate"]), "read_layer": int(r["read_layer"]), "pilot": {"passed": True}, "records": {}, "stand_in": True}
    rec = partt_plan.build_candidate(repo, run_dir.parent / f"{run_dir.name}_registered_run_dir_unused", cfg, stand_in, walk=planmod.import_walk(repo, "T"), manifests=dict(manifests or {}), part_q=part_q_block(part_q_dir, part_q_plan))
    write_json(path, core.jsonable(rec))
    return path


def process_table(run_dir: Path) -> dict[str, Any]:
    """Per stage and task: the whole-process seconds and the tree's peak resident set (the runner's), and the worker's own record (world build, body, peak RSS, MPS memory, disk written, load)."""
    out: dict[str, Any] = {}
    for stage in partt_plan.STAGES:
        man = runner_manifest(run_dir, stage)
        rows: dict[str, Any] = {}
        if man is not None:
            for label, o in man["tasks"].items():
                tf = partt_tasks.tasks_dir(run_dir, stage) / f"{partt_tasks.safe(label)}.timing.json"
                rows[label] = {"process_seconds": float(o.get("seconds", 0.0)), "tree_peak_rss_bytes": int(o.get("peak_rss_bytes", 0)), **({"worker": read_json(tf)} if tf.is_file() else {})}
        else:
            tf = run_dir / "stages" / f"{stage}.timing.json"
            if tf.is_file():
                rows[stage] = {"worker": read_json(tf)}
        out[stage] = rows
    return out


def derive_rates(run_dir: Path, plan: planmod.Plan) -> tuple[dict[str, float], dict[str, float], list[str], dict[str, float]]:
    """Seconds per unit of every kind (sum of the kind's seconds over the tasks that ran it / the units they covered) and, per stage, the per-process overhead (the mean over its processes of whole-process seconds
    less the seconds of unit work). A stage that runs as one body (gates, controls, analysis, report, recompute) takes its body seconds as the unit work of its one unit (the recomputation reuses the scoring rates)."""
    seconds: dict[str, float] = {}
    units: dict[str, float] = {}
    over: dict[str, list[float]] = {}
    problems: list[str] = []
    table = process_table(run_dir)
    single = {"gates": "gates:all", "controls": "controls:check", "analysis": "analysis:run", "report": "report:run"}
    for stage, rows in table.items():
        for label, row in rows.items():
            w = row.get("worker") or {}
            proc = float(row.get("process_seconds") or 0.0)
            if "kinds" in w:
                k = w["kinds"] or {}
                ksec = {kk: float(v) for kk, v in (k.get("seconds") or {}).items()}
                body = sum(ksec.values())
                if stage in single and not ksec:
                    ksec = {single[stage]: float(w.get("task_body_seconds", 0.0))}
                    body = ksec[single[stage]]
                for kk, n in (k.get("units") or {}).items():
                    units[kk] = units.get(kk, 0.0) + float(n)
                for kk, v in ksec.items():
                    seconds[kk] = seconds.get(kk, 0.0) + v
                over.setdefault(stage, []).append(max(0.0, proc - body))
            elif "body_seconds" in w:
                if stage in single:
                    seconds[single[stage]] = seconds.get(single[stage], 0.0) + float(w["body_seconds"])
                    units[single[stage]] = units.get(single[stage], 0.0) + 1.0
                m = runner_manifest(run_dir, stage)
                whole = float(w["body_seconds"]) + float(w["world_build_seconds"])
                over.setdefault(stage, []).append(max(0.0, whole - float(w["body_seconds"])) if m is None else 0.0)
    rates = {k: seconds[k] / units[k] for k in seconds if units.get(k)}
    overhead = {s: sum(v) / len(v) for s, v in over.items() if v}
    return rates, overhead, problems, units


def mean_world_build(run_dir: Path) -> float:
    """The mean seconds the processes of this rehearsal spent building their world (measured)."""
    vals = [float(r["worker"]["world_build_seconds"]) for rows in process_table(run_dir).values() for r in rows.values() if "world_build_seconds" in r.get("worker", {})]
    return sum(vals) / len(vals) if vals else 0.0


def run_measuring_rehearsal(repo: Path, run_dir: Path, part_q_dir: Path, *, part_q_plan: Path | None = None, manifests: Mapping[str, Any] | None = None, launch: Launch = subprocess_launch, clock: Callable[[], float] = time.monotonic, charged_ledgers: Sequence[str] = ()) -> dict[str, Any]:
    from .partt_stages import claim_run_dir

    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)
    core.require_ignored_run_dir(repo, run_dir)
    claim_run_dir(run_dir, "rehearsal", None)
    plan_file = measuring_plan(repo, run_dir, part_q_dir, part_q_plan, manifests)
    plan = planmod.Plan.load(plan_file, "T")
    t0 = clock()
    problems: list[str] = []
    timings: dict[str, float] = {}
    load_start, others_start = os.getloadavg()[0], procs.other_studies_alive()
    run_stages(repo, run_dir, plan, "measuring", launch, plan_file, forced=None, problems=problems, timings=timings, clock=clock)
    led = core.Ledger(run_dir / "charged_ledger.json", "T", 1e12)
    stages = {s: stage_record(run_dir, s, led) for s in partt_plan.STAGES}
    rates, overhead, rate_problems, subset_units = derive_rates(run_dir, plan) if all(v["status"] == "COMPLETE" for v in stages.values()) else ({}, {}, [], {})
    problems += rate_problems
    missing = [k for k in partt_caps.required_kinds(plan.data["items"], plan.data["task_units_basis"]) if k not in rates] if rates else []
    if rates and missing:
        problems.append(f"kinds the plan holds that this rehearsal did not measure: {missing}")
    complete = all(v["status"] == "COMPLETE" for v in stages.values()) and not problems
    rec = {
        **core.envelope("rehearsal", "T"), "kind_of_rehearsal": "measuring", "status": "COMPLETE" if complete else "INCOMPLETE", "caps_provisional": True, "cannot_be_frozen_on": True, "caps_formula": partt_caps.CAPS_FORMULA,
        "entry_point": "partt_registered.sh <stage> <run-dir> - --rehearsal --rehearsal-kind measuring --plan-file <measuring plan>, one fresh process per stage; tasks are worker processes", "plan_file_sha256": file_sha256(plan_file),
        "stages": stages, "problems": problems, "rates_seconds_per_unit": rates, "overhead_seconds": overhead, "updates": int(plan.data["calibration"]["U"]), "rehearsal_draw": read_json(run_dir / "rehearsal_draw.json") if (run_dir / "rehearsal_draw.json").is_file() else None, "subset_units": subset_units, "subset_processes": {s: max(1, len(rows)) for s, rows in process_table(run_dir).items()}, "world_build_seconds": mean_world_build(run_dir), "processes": process_table(run_dir), "timings": {"total_seconds": clock() - t0, "process_seconds": timings},
        "load": {"start": load_start, "end": os.getloadavg()[0]}, "other_studies_alive": {"start": others_start, "end": procs.other_studies_alive()}, "platform": gates.platform_record(),
        "disk_written_bytes": sum(int(r.get("worker", {}).get("disk_written_bytes", 0)) for rows in process_table(run_dir).values() for r in rows.values()),
        "charged_seconds": led.charged(), "charged_before_freeze_seconds": led.charged() + sum(core.Ledger(Path(x), "T", 1e12).charged() for x in charged_ledgers), "charged_ledgers": {str(run_dir / "charged_ledger.json"): led.charged(), **{str(Path(x)): core.Ledger(Path(x), "T", 1e12).charged() for x in charged_ledgers}},
        "subset": "replicate 0; one cell of each of the ten trained types at full U; D_cal only",
    }  # fmt: skip
    write_rehearsal_record(run_dir / "rehearsal_measuring.json", rec)
    if not complete:
        raise StageRefused(f"refused: the measuring rehearsal is incomplete: {problems or 'a stage did not complete'}")
    return rec
