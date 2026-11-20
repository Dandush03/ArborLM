# ruff: noqa: E501
"""Part T's registered stages through the task runner (ADR-0025 sections 8.6, 9, 10, 11 items 2 and 4, 19 rulings G7, G13, G14, L2).

* Tasks are derived from the FROZEN PLAN only (``plan.items(stage)``): one task per trained cell, one per replicate for scoring and for the combined tasks, one for the references and one for the gates.
* Each task is a worker process (``partt_stages task``) that re-checks the freeze (clean tree, frozen files, plan, Decision 2) before it starts: a refusal on identity exits 75 and the runner records PAUSED —
  IDENTITY with nothing written; restoring the file resumes the task. Completed tasks (a result file) are never run again; a task that failed keeps its failed record and is not re-run (a code or environment
  error is released for ONE resume by ``retry`` once its cause is recorded and the fix changes no frozen file; a non-finite cell is never released).
* A failed task is an ITEM ERROR (``item_errors/``): the analysis refuses while one exists; it is never a scientific NOT EVALUABLE.
* Hour caps are cumulative across stages and resumes: a ledger of charged seconds (the SUM of each worker process's wall time, correction C10) in the run directory; a stage gets the smaller of its own cap
  less what it already used and what is left of the part's total; a cap stop is PAUSED and a resume gets what is left.
* A per-worker memory guard (8 GiB; 24 GiB aggregate; two workers and 16 GiB aggregate while another study's process is alive; at most three workers otherwise).
"""

import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import read_json, write_json

from . import partt_plan, partt_rehearsal
from .common import core, procs, runner
from .common import plan as planmod
from .common.core import StageRefused

TASK_STAGES = ("gates", "train", "evaluate", "combined")  # "controls" scores nothing again (ruling 12): a check stage; "recompute" is a stage with its own body
WAVES = ((("M1", "D1", "M-joint", "D-joint", "E-table"),), (("M-append", "M-seq", "D-append", "D-seq"),), (("M-ii",),))  # dependency order of the cells: stage-1 modules, then the stage-2 modules, then M-ii


def safe(task_id: str) -> str:
    return task_id.replace("|", "__").replace("/", "_").replace("@", "_at_")


other_studies_alive = procs.other_studies_alive  # shared with Part Q and the timing benchmark


def worker_policy(cfg: Mapping[str, Any], other_alive: bool) -> dict[str, Any]:
    """Ruling G7 and section 20: at most three workers (8 GiB each, 24 GiB aggregate); at most two (16 GiB aggregate) while another study runs."""
    c = cfg["caps"]
    workers = int(c["workers_max_shared"] if other_alive else c["workers_max"])
    per = float(c["memory_per_worker_gib"])
    return {"workers": workers, "rss_worker_bytes": int(per * 2**30), "rss_aggregate_bytes": int(min(float(c["memory_aggregate_gib"]), per * workers) * 2**30), "other_study_alive": other_alive}


def waves_of(stage: str, plan: planmod.Plan, rehearsal: bool = False) -> list[list[dict[str, Any]]]:
    """The task groups of a stage from the plan's items. Training runs in dependency waves; every other stage is one wave. A rehearsal takes the plan-derived subset (``partt_rehearsal.subset_items``) of the same items."""
    items = list(plan.items(stage))
    if rehearsal:
        items = list(partt_rehearsal.subset_items(stage, items))
    if stage == "train":
        return [[i for i in items if i["arm"] in w[0]] for w in WAVES]
    if stage in ("evaluate", "controls", "combined"):
        reps = sorted({int(i["rep"]) if "rep" in i else int(i["of"].rsplit("|r", 1)[1]) for i in items if ("rep" in i or "of" in i) and ("rep" in i or "|r" in i["of"])})
        tasks = [{"id": f"{stage}|r{r}", "stage": stage, "rep": r} for r in reps]
        if any(("rep" not in i and not ("of" in i and "|r" in i["of"])) for i in items):
            tasks.append({"id": f"{stage}|reference", "stage": stage, "reference": True})
        return [tasks]
    if stage == "gates":
        return [[{"id": "gates|all", "stage": "gates", "gates": [i["gate"] for i in items]}]]
    raise StageRefused(f"refused: {stage!r} has no task stage")


def stage_marker(run_dir: Path, stage: str) -> Path:
    return run_dir / "stages" / f"{stage}.complete.json"


def mark_complete(run_dir: Path, stage: str, mode: str = "registered") -> None:
    p = stage_marker(run_dir, stage)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, {"stage": stage, "status": "COMPLETE", "mode": mode, "utc": core.utc_stamp()})


def require_predecessor(run_dir: Path, stage: str, order: Sequence[str]) -> None:
    """Stage order is enforced: a stage runs only after its predecessor's completion record (no stage needs a record that only it or a later stage writes: audit B3)."""
    i = order.index(stage)
    if i and not stage_marker(run_dir, order[i - 1]).is_file():
        raise StageRefused(f"refused: stage {stage!r} needs {order[i - 1]!r} to be complete first (no completion record)")


def tasks_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / "tasks" / stage


FORCED_PAUSE_CELL = "train|M1|AB|r0"  # the cell the rehearsal's ONE forced pause stops


def make_tasks(stage: str, wave: Sequence[Mapping[str, Any]], repo: Path, run_dir: Path, freeze_commit: str, qdir: Path, extra: Sequence[str] = (), pause_after_updates: int | None = None) -> list[runner.Task]:
    d = tasks_dir(run_dir, stage)
    out = []
    for it in wave:
        sid = safe(it["id"])
        more = [*extra, *(["--pause-after-updates", str(pause_after_updates)] if pause_after_updates and it["id"] == FORCED_PAUSE_CELL else [])]
        argv = (sys.executable, "-m", "studies.p10is2.partt_stages", "task", "--stage", stage, "--task-id", it["id"], "--run-dir", str(run_dir), "--freeze-commit", freeze_commit, "--repo", str(repo), "--part-q-dir", str(qdir), *more)
        out.append(runner.Task(it["id"], argv, d / f"{sid}.result.json", d / f"{sid}.failed.json", run_dir / "logs" / stage / f"{sid}.log"))
    return out


def ledger_of(plan: planmod.Plan, run_dir: Path) -> core.Ledger:
    return core.Ledger(run_dir / "charged_ledger.json", "T", plan.total_cap_seconds() if plan.total_cap_seconds() > 0 else 1e12)


def charge_before_freeze(plan: planmod.Plan) -> float:
    """Everything Part T charged before the freeze (the measuring rehearsal, calibration and its repetitions, earlier counting rehearsals), as the plan RECORDED it: it counts against the total cap (ruling 4)."""
    return float((plan.data.get("charge_before_freeze") or {}).get("seconds", 0.0))


def stage_cap_for(plan: planmod.Plan, stage: str, led: core.Ledger) -> float:
    """The seconds this invocation may use: the stage's cap less what it already used, but never more than is left of the part's total less the charge before the freeze (cumulative across stages and resumes).
    A cap of 0 is NEVER "uncapped": every registered stage has a cap by the rule, or this refuses."""
    own = plan.cap_seconds(stage)
    if own <= 0 or plan.total_cap_seconds() <= 0:
        raise StageRefused(f"refused: stage {stage!r} has no cap (a cap of 0 is not 'uncapped'): the caps are computed by the rule from the measuring rehearsal and written before the freeze")
    return min(own - led.charged(stage), plan.total_cap_seconds() - charge_before_freeze(plan) - led.charged())


def record_item_errors(run_dir: Path, stage: str, outcomes: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Each FAILED task becomes an item error the analysis refuses on (ruling G13); PAUSED tasks do not."""
    errs = []
    for label, o in outcomes.items():
        if o["status"] == runner.FAILED:
            p = run_dir / "item_errors" / f"{stage}__{safe(label)}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            write_json(p, {"stage": stage, "task": label, "reason": o.get("reason"), "kind": "item_error", "utc": datetime.now(UTC).isoformat()})
            errs.append(str(p))
    return errs


def rehearsal_cap_seconds(cfg: Mapping[str, Any], kind: str) -> float:
    """A rehearsal's fixed cap (ADR section 10): the measuring rehearsal's 3.0 charged hours, the counting rehearsal's, both from the config; they are not the registered stages' caps."""
    return float(cfg["caps"]["measuring_rehearsal_hours" if kind == "measuring" else "rehearsal_hours"]) * 3600.0


def run_stage_tasks(stage: str, plan: planmod.Plan, cfg: Mapping[str, Any], repo: Path, run_dir: Path, freeze_commit: str, qdir: Path, *, other_alive: Callable[[], Sequence[str]] = other_studies_alive, poll: float = 0.5, task_runner: Callable[..., Any] | None = None, mode: str = "registered", kind: str = "counting", extra: Sequence[str] = (), pause_after_updates: int | None = None) -> dict[str, Any]:
    """One invocation of a task stage, for a registered run (``mode="registered"``) or a rehearsal (``mode="rehearsal"``: the plan-derived subset, the rehearsal's fixed cap, the same runner and workers).
    Returns the stage manifest (COMPLETE, PAUSED or FAILED). Waves run one after another; a wave that does not complete stops the stage (the next wave needs its snapshots)."""
    started = datetime.now(UTC).isoformat()
    led = ledger_of(plan, run_dir) if mode == "registered" else core.Ledger(run_dir / "charged_ledger.json", "T", 1e12)
    pol = worker_policy(cfg, bool(other_alive()))
    run = task_runner or runner.run_tasks
    all_out: dict[str, dict[str, Any]] = {}
    caps_used: dict[str, float] = {}
    t_stage = time.monotonic()
    for wave in waves_of(stage, plan, mode == "rehearsal"):
        cap = stage_cap_for(plan, stage, led) if mode == "registered" else rehearsal_cap_seconds(cfg, kind) - led.charged()
        caps_used = {"stage_seconds_left": cap, "total_seconds_left": led.remaining()}
        if cap <= 0:  # nothing left: PAUSED, the extension is the lead's (section 9)
            for it in wave:
                all_out.setdefault(it["id"], {"status": runner.NOT_STARTED, "seconds": 0.0, "reason": "the cumulative hour cap is spent", "peak_rss_bytes": 0})
            break
        tasks = make_tasks(stage, wave, repo, run_dir, freeze_commit, qdir, extra, pause_after_updates)
        outcomes, _wall = run(tasks, workers=pol["workers"], cap_seconds=cap, rss_worker_bytes=pol["rss_worker_bytes"], rss_aggregate_bytes=pol["rss_aggregate_bytes"], poll=poll)
        for label, o in outcomes.items():
            led.charge_process(stage, label, f"worker:{label}", float(o.get("seconds", 0.0)))  # the sum of each worker process's wall time (C10)
        all_out.update(outcomes)
        record_item_errors(run_dir, stage, outcomes)
        if runner.stage_status(outcomes) != "COMPLETE":
            break
    manifest = runner.write_manifest(run_dir, "T", stage, mode, all_out, time.monotonic() - t_stage, identity={"freeze_commit": freeze_commit}, started=started, caps={**caps_used, **{k: v for k, v in pol.items() if k != "other_study_alive"}}, extra={"worker_policy": pol})
    return manifest


def retry(run_dir: Path, stage: str, task_id: str, cause: str, fix_changes_frozen_file: bool) -> dict[str, Any]:
    """Release a FAILED task for one resume (section 8.6): only a code or environment error whose cause is recorded and whose fix changes no frozen file. A non-finite cell is never released. The failed record
    is MOVED to ``failed_kept/`` (never deleted) with the cause."""
    d = tasks_dir(run_dir, stage)
    sid = safe(task_id)
    failed = d / f"{sid}.failed.json"
    if not failed.is_file():
        raise StageRefused(f"refused: no failed record for {task_id}")
    cell = d / f"{sid}.cell.json"
    rec = read_json(cell) if cell.is_file() else {"status": "ERROR"}
    decision = partt_plan.resume_decision({**rec, "cause_recorded": bool(cause), "fix_changes_frozen_file": fix_changes_frozen_file})
    if decision["action"] != "resume":
        raise StageRefused(f"refused: {decision.get('label', 'ENGINEERING STOP')}: {decision.get('note', 'not released')}")
    keep = d / "failed_kept"
    keep.mkdir(parents=True, exist_ok=True)
    stamp = core.utc_stamp()
    write_json(keep / f"{sid}.{stamp}.json", {"failed": read_json(failed), "cause": cause, "released_for_one_resume": True})
    failed.rename(keep / f"{sid}.{stamp}.failed.json")
    item = run_dir / "item_errors" / f"{stage}__{sid}.json"
    if item.is_file():
        item.rename(keep / f"{sid}.{stamp}.item_error.json")
    return {"released": task_id, "resume_from": decision["from"]}
