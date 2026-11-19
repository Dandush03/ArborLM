# ruff: noqa: E501
"""P10IS0 stage drivers and workers (ADR-0023 section 10): generation and G1 of the draws, stage 3 (timing), Stage R (with the extension rule), the caps, the main grid, the X8 gate, X8 with its calibration and addendum, the analysis and the
report. Every registered stage derives its items from ``freeze/plan.json`` only (X8 from its addendum in the run directory); every stage is resumable (a task whose result file exists is not run again); an identity or precondition failure exits
75 (PAUSED — IDENTITY, nothing written); an environment error exits 76 (PAUSED — ENVIRONMENT); an item error is a failed task whose record is kept (ENGINEERING STOP; the analysis refuses); a code change after ``durations.json`` exists is an ENGINEERING
STOP (exit 4) for every later stage (``check_code_identity``).

A run directory is named and git-ignored (or outside the repository). Under the ``test`` profile (marker ``TEST_PROFILE`` in the run directory) everything runs on the synthetic tiny configuration with test-range seeds; the registered plan
builder is the same code (``plan.build_plan``).
"""

import json
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from arborlm.io import file_sha256, read_json, write_json

from . import accounting, adapter, analysis, core, items, labels, ladder, report, runner, sealed
from . import plan as planmod
from .plan import IDENTITY_EXIT, IdentityMismatch, StageRefused
from .profile import Profile, profile_of

ENV_EXIT = runner.ENV_EXIT
CODE_CHANGED_EXIT = 4
CODE_IDENTITY_FILE = "code_identity.json"


class CodeChanged(RuntimeError):
    """The frozen code differs from the code Stage R ran under (or changed without a recorded cause before ``durations.json`` existed): an ENGINEERING STOP for the human lead; no automatic re-draw."""


# --- code identity (ruling 5) -------------------------------------------------------------------------------------------------------------------
def code_identity(repo: Path) -> dict[str, str]:
    """SHA-256 of each file the training and evaluation path imports or this study owns, without the freeze files (they change by design)."""
    return planmod.hash_inputs(repo, planmod.frozen_paths(repo, include_freeze_files=False))


def current_attempt(run_dir: Path) -> int:
    p = run_dir / CODE_IDENTITY_FILE
    return int(read_json(p)["history"][-1].get("attempt", 0)) if p.is_file() else 0


def record_code_identity(run_dir: Path, repo: Path, *, cause_file: Path | None = None) -> dict[str, Any]:
    """Stage R's start: record the code identity it runs under and return the ATTEMPT number. A change of the code before ``durations.json`` exists VOIDS Stage R (R8): it needs a recorded cause (a file under ``results/``) and starts the
    next attempt, which repeats Stage R in full on the registry's spare draws (repeat k = 1, 2, 3); the voided results stay sealed, are listed in the history and enter nothing. A fourth repeat has no allocated values and a change
    after ``durations.json`` exists is an engineering stop: both for the human lead."""
    path = run_dir / CODE_IDENTITY_FILE
    now = code_identity(repo)
    if not path.is_file():
        write_json(path, {"history": [{"inputs": now, "cause": None, "attempt": 0, "utc": datetime.now(UTC).isoformat()}]})
        return {"recorded": True, "attempt": 0}
    rec = read_json(path)
    last = rec["history"][-1]
    if last["inputs"] == now:
        return {"recorded": False, "attempt": int(last.get("attempt", 0))}
    if (repo / core.DURATIONS).is_file():
        raise CodeChanged("ENGINEERING STOP: the code changed after freeze/durations.json exists; the human lead rules (no automatic re-draw)")
    if cause_file is None or not cause_file.is_file() or "results" not in cause_file.resolve().parts:
        raise CodeChanged("ENGINEERING STOP: the code changed during Stage R without a recorded cause (a file under results/ naming it)")
    nxt = int(last.get("attempt", 0)) + 1
    if nxt > int(core.load_config(repo / core.CONFIG)["seeds"]["repeat_count"]):
        raise CodeChanged("ENGINEERING STOP: a fourth repeat of Stage R has no allocated values; the human lead rules")
    rec["history"].append({"inputs": now, "cause": str(cause_file), "cause_sha256": file_sha256(cause_file), "attempt": nxt, "voids_attempt": int(last.get("attempt", 0)), "utc": datetime.now(UTC).isoformat()})
    write_json(path, rec)
    return {"recorded": True, "cause": str(cause_file), "attempt": nxt}


def check_code_identity(repo: Path, run_dir: Path | None = None) -> None:
    """Every stage after Stage R: the running code must equal the identity ``durations.json`` records; before it exists, the identity in the run directory's record."""
    dur = repo / core.DURATIONS
    if dur.is_file():
        want = read_json(dur).get("code_identity")
        if want is None:
            raise CodeChanged("ENGINEERING STOP: durations.json records no code identity")
    elif run_dir is not None and (run_dir / CODE_IDENTITY_FILE).is_file():
        want = read_json(run_dir / CODE_IDENTITY_FILE)["history"][-1]["inputs"]
    else:
        return
    now = code_identity(repo)
    diff = sorted(k for k in set(now) | set(want) if now.get(k) != want.get(k))
    if diff:
        raise CodeChanged(f"ENGINEERING STOP: the code differs from the code Stage R ran under: {diff[:5]}")


# --- context -------------------------------------------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, repo: Path, run_dir: Path, *, registered: bool, total_hours: float | None = None, sealed_dir: Path | None = None) -> None:
        self.repo, self.run_dir, self.registered = repo, run_dir, registered
        self.cfg = core.load_config(repo / core.CONFIG)
        self.profile: Profile = profile_of(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        problems = planmod.run_dir_problems(run_dir, repo)
        if problems:
            raise StageRefused("refused: " + "; ".join(problems))
        caps = repo / core.STAGE_CAPS
        total = total_hours if total_hours is not None else (float(read_json(caps)["total_hours"]) if registered and caps.is_file() else 1000.0)
        self.ledger = core.Ledger(run_dir / "P10IS0-ledger.json", total * 3600.0)
        self.sealed_base: Path | None = None
        loc = run_dir / "sealed_location.json"
        recorded = Path(read_json(loc)["path"]) if loc.is_file() else None
        chosen = Path(sealed_dir).resolve() if sealed_dir is not None else recorded
        if chosen is not None:
            bad = sealed.sealed_location_problems(chosen, repo)
            if bad:
                raise StageRefused("refused: the sealed directory must be outside version control: " + "; ".join(bad))
            if recorded is not None and recorded != chosen:
                raise StageRefused(f"refused: the sealed directory is {recorded}, not {chosen}")
            chosen.mkdir(parents=True, exist_ok=True)
            if recorded is None:
                write_json(loc, {"path": str(chosen)})
            self.sealed_base = chosen

    @property
    def th(self) -> core.Thresholds:
        return core.Thresholds.from_config(self.cfg)

    def need_sealed(self) -> Path:
        if self.sealed_base is None:
            raise StageRefused("refused: Stage R needs an explicit --sealed-dir outside version control")
        return self.sealed_base

    def worker_argv(self, kind: str, *extra: str) -> tuple[str, ...]:
        s = ("--sealed-dir", str(self.sealed_base)) if self.sealed_base is not None else ()
        return (sys.executable, "-m", "studies.p10is0.stages", "work", kind, "--run-dir", str(self.run_dir), "--repo", str(self.repo), *s, *extra)

    def task(self, stage: str, name: str, kind: str, *extra: str, sealed_tasks: bool = False) -> runner.Task:
        """D1: every per-task file of Stage R (log, result, failed record) lives in the sealed directory, because the times of their creation and last write give each task's duration, which splits by cell type."""
        d = (sealed.sealed_dir(self.need_sealed()) / "tasks" / stage) if sealed_tasks else self.run_dir / "tasks" / stage
        result = d / f"{name}.result.json"
        return runner.Task(name, self.worker_argv(kind, *extra, "--result", str(result)), result, d / f"{name}.failed.json", d / f"{name}.log")

    def peaks(self) -> dict[str, int]:
        p = self.run_dir / "timing" / "memory_peaks.json"
        return {k: int(v) for k, v in read_json(p).items()} if p.is_file() else {}

    def record_peak(self, name: str, peak: int) -> None:
        pk = self.peaks()
        pk[name] = max(pk.get(name, 0), int(peak))
        (self.run_dir / "timing").mkdir(parents=True, exist_ok=True)
        write_json(self.run_dir / "timing" / "memory_peaks.json", pk)

    def workers(self) -> int:
        """R6: n = min(6, floor(9 GiB / the largest measured peak per worker)) over stage 3, Stage R's runs (at 2T) and the full-length A0 memory cell; above 3 GiB per worker is an engineering stop (``ladder.worker_count``)."""
        pk = self.peaks()
        rates = self.run_dir / "timing" / "rates.json"
        if rates.is_file():
            pk = {"stage3": int(read_json(rates)["peak_rss_bytes"]), **pk}
        return ladder.worker_count(max(pk.values()), self.cfg) if pk else int(self.cfg["budget"]["workers"])


def mode_of(ctx: Ctx) -> str:
    return "registered" if ctx.registered else ctx.profile.name


def run_stage(ctx: Ctx, stage: str, tasks: Sequence[runner.Task], cap_seconds: float, *, workers: int | None = None, group: str | None = None, seal_task_stats: bool = False) -> dict[str, Any]:
    """Run a stage's tasks (resumable), charge the ledger, write the manifest. The stage's cap is CUMULATIVE over its group (R3): an invocation gets what the group's cap has left and what the total cap has left, so a resume cannot
    run beyond either. A stage at its cap is PAUSED; an identity refusal PAUSED — IDENTITY; an environment error or the disk rule PAUSED — ENVIRONMENT; a code change ENGINEERING STOP (never a failed task); an item error FAILED."""
    grp = group or stage
    left = min(cap_seconds - ctx.ledger.charged(group=grp), ctx.ledger.remaining())
    if left <= 0:
        return {"status": "PAUSED", "reason": f"the cap of group {grp} or the total cap is spent: an extension is the human lead's, on cost projections only"}
    started = datetime.now(UTC).isoformat()
    r = ctx.cfg["resources"]
    outcomes, seconds = runner.run_tasks(
        tasks, workers=workers or ctx.workers(), cap_seconds=left, rss_worker_bytes=int(r["rss_worker_bytes"]), rss_aggregate_bytes=int(r["rss_aggregate_bytes"]), disk_check=lambda: accounting.check_disk(ctx.run_dir, ctx.cfg, also=[ctx.sealed_base] if ctx.sealed_base is not None else ())
    )  # fmt: skip
    ctx.ledger.charge(stage, f"{stage}-{core.utc_stamp()}", seconds, group=grp)
    peak = max((int(o.get("peak_rss_bytes", 0)) for o in outcomes.values()), default=0)
    if peak:
        ctx.record_peak(grp, peak)
    prior = runner.read_manifest(ctx.run_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        return prior
    extra: dict[str, Any] | None = None
    if seal_task_stats and ctx.sealed_base is not None:
        # N3 remainder: per-task seconds and peak memory split by cell type, so they go to the sealed directory; the public manifest keeps each task's status, and per invocation only the task count, the total seconds and the maximum peak
        sealed.write_sealed(ctx.sealed_base, f"taskstats-{stage}-{core.utc_stamp()}.json", {"outcomes": outcomes})
        extra = {"wave": {"tasks": len(outcomes), "total_seconds": float(sum(float(o.get("seconds", 0.0)) for o in outcomes.values())), "max_peak_rss_bytes": peak, "limit": sealed.WAVE_LIMIT_SENTENCE}}
        outcomes = {k: {"status": o["status"], "seconds": 0.0, "peak_rss_bytes": 0} for k, o in outcomes.items()}
    return runner.write_manifest(ctx.run_dir, stage, mode_of(ctx), outcomes, seconds, identity={"profile": ctx.profile.name, "platform": accounting.platform_record()}, started=started, caps={"stage_seconds": cap_seconds, "group": grp}, extra=extra)


def stage_status(ctx: Ctx, stage: str) -> str | None:
    m = runner.read_manifest(ctx.run_dir, stage)
    return None if m is None else str(m["status"])


# --- environment of a worker ---------------------------------------------------------------------------------------------------------------------
def env_for(run_dir: Path) -> items.Env:
    """The corpus, backbone and evaluation rows: real (P9's trained corpus and primary parent) or, under the test profile, synthetic."""
    prof = profile_of(run_dir)
    if prof.tiny:
        return items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), profile=prof)
    from studies.p9 import controls
    from studies.p9 import core as p9core

    root = p9core.default_experiments_root()
    return items.Env(p9core.load_trained_corpus(root), controls.load_backbone(p9core.PRIMARY_PARENT, root)[0], profile=prof)


def worker_guard(ctx: Ctx) -> None:
    """Identity and precondition re-check before each task: a registered worker verifies every frozen input; every worker verifies the code identity. A difference raises (exit 75 for a frozen file, 4 for a code change)."""
    if ctx.registered:
        rec = core.read_record(ctx.repo / core.FREEZE_RECORD, "freeze_record")
        diffs = planmod.verify_inputs(ctx.repo, rec["inputs"])
        if diffs:
            raise IdentityMismatch("; ".join(diffs[:3]))
    check_code_identity(ctx.repo, ctx.run_dir)


# --- generation and G1 (stage 5) ------------------------------------------------------------------------------------------------------------------
def draw_manifest_path(run_dir: Path, name: str) -> Path:
    return run_dir / "draws" / name / "data_manifest.json"


def work_generate(ctx: Ctx, set_name: str) -> dict[str, Any]:
    """Generate, hash and G1-check both fact sets of one draw set (generating a draw is not an observation of a seed by a model). A failed G1 is the draw's result, not an error."""
    return _generate(ctx, core.set_of_name(set_name, ctx.cfg, ctx.profile.name))


def work_generate_rehearsal(ctx: Ctx) -> dict[str, Any]:
    """The rehearsal draw (309201), generated and G1-checked for the real-size rehearsal phase."""
    return _generate(ctx, core.rehearsal_set(ctx.cfg, ctx.profile.name))


def _generate(ctx: Ctx, spec: core.SetSpec) -> dict[str, Any]:
    from studies.p9 import data as data_mod

    set_name = spec.name
    env = env_for(ctx.run_dir)
    out = draw_manifest_path(ctx.run_dir, set_name)
    if out.exists():
        return core.read_record(out, "data_manifest")
    out.parent.mkdir(parents=True, exist_ok=True)
    passed: dict[str, bool] = {}
    hashes: dict[str, Any] = {}
    failed: dict[str, list[str]] = {}
    for real in (int(k) for k in ctx.cfg["seeds"]["fact_set_offsets"]):
        study = items.data_for(env, spec, real, ctx.cfg)
        g1 = data_mod.run_g1(study, permutations=200 if ctx.profile.tiny else None, train_epochs=None)
        write_json(out.parent / f"g1_{real}.json", core.jsonable(g1))
        passed[str(real)] = bool(g1["passed"])
        hashes[str(real)] = study.sha256s()
        failed[str(real)] = [c["name"] for c in g1["checks"] if not c["passed"]]
    rec = {**core.envelope("data_manifest"), "seed_set": set_name, "profile": ctx.profile.name, "sha256s": hashes, "g1_passed": all(passed.values()), "g1_by_fact_set": passed, "g1_failed_checks": failed}
    core.write_record(out, rec)
    return rec


class DrawPlan:
    def __init__(self, ok: bool, seed_set_of: dict[int, str], replacements: dict[int, str], reason: str | None) -> None:
        self.ok, self.seed_set_of, self.replacements, self.reason = ok, seed_set_of, replacements, reason


def plan_draws(g1: Mapping[str, bool], cfg: Mapping[str, Any] | None = None) -> DrawPlan:
    """Section 4.2 and ruling 9: draws are generated until ten pass G1 within the four reserves. A draw that fails (or has no G1 result) is replaced by the next reserve that passes, in order; a reserve that fails is skipped; fewer than ten
    passing sets is an ENGINEERING STOP before the freeze (the class rule is tied to ten draws): ``ok`` False with the reason."""
    c = cfg or core.load_config()
    n, k = int(c["draws"]["registered"]), int(c["draws"]["reserve"])
    names = [f"p10is0-draw-{d}" for d in range(1, n + 1)]
    reserves = [f"p10is0-reserve-{r}" for r in range(1, k + 1)]
    seed_set_of = {d: names[d - 1] for d in range(1, n + 1)}
    spare = [r for r in reserves if g1.get(r) is True]
    replacements: dict[int, str] = {}
    for d in range(1, n + 1):
        if g1.get(names[d - 1]) is True:
            continue
        if not spare:
            return DrawPlan(False, seed_set_of, replacements, f"fewer than {n} draws pass G1 within {k} reserves: ENGINEERING STOP before the freeze until the human lead rules; nothing is frozen")
        replacements[d] = spare.pop(0)
        seed_set_of[d] = replacements[d]
    return DrawPlan(True, seed_set_of, replacements, None)


def cmd_generate(ctx: Ctx, cap_hours: float) -> dict[str, Any]:
    sets = [f"p10is0-draw-{d}" for d in range(1, int(ctx.cfg["draws"]["registered"]) + 1)] + [f"p10is0-reserve-{r}" for r in range(1, int(ctx.cfg["draws"]["reserve"]) + 1)]
    tasks = [ctx.task("generate", s, "generate", "--set", s) for s in sets]
    m = run_stage(ctx, "generate", tasks, cap_hours * 3600.0)
    g1 = {s: bool(core.read_record(draw_manifest_path(ctx.run_dir, s), "data_manifest")["g1_passed"]) for s in sets if draw_manifest_path(ctx.run_dir, s).is_file()}
    dp = plan_draws(g1, ctx.cfg) if m["status"] == "COMPLETE" else DrawPlan(False, {}, {}, f"generation {m['status']}")
    write_json(ctx.run_dir / "draw_plan.json", core.jsonable({**core.envelope("gate"), "ok": dp.ok, "seed_set_of": {str(k): v for k, v in dp.seed_set_of.items()}, "replacements": {str(k): v for k, v in dp.replacements.items()}, "reason": dp.reason, "g1": g1, "number_used": 10 + len(dp.replacements)}))
    return {"status": m["status"], "draw_plan_ok": dp.ok, "replacements": dp.replacements, "reason": dp.reason}


def read_draw_plan(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "draw_plan.json"
    if not p.is_file():
        raise StageRefused(f"refused: no draw plan at {p}")
    d = read_json(p)
    if not d["ok"]:
        raise StageRefused(f"refused: the draw plan is not ok: {d['reason']}")
    return dict(d)


# --- stage 3: timing -----------------------------------------------------------------------------------------------------------------------------
def timing_combos(ctx: Ctx) -> list[tuple[str, str]]:
    return [(arm, ct.name) for ct in core.cell_types(ctx.cfg, include_x8=True) for arm in ct.arms]


def work_timing(ctx: Ctx, arm: str, ct_name: str, tag: str) -> dict[str, Any]:
    """One (arm, cell type): at least ``min_updates`` updates (no records written), one evaluation, peak memory. Times only: nothing here is a measurement of accuracy."""
    from studies.p9i.train import training_stream_for

    ct = core.cell_type_by_name(ct_name, ctx.cfg)
    env = env_for(ctx.run_dir)
    updates = ctx.profile.min_timing_updates or int(ctx.cfg["timing"]["min_updates"])
    facts = env.facts_of(ct.facts)
    spec = core.rehearsal_set(ctx.cfg, ctx.profile.name)
    data = items.data_for(env, spec, ct.facts, ctx.cfg)
    cell = core.Cell("REH", ct.series, arm, ct.facts, ct.slots, 1, core.init_seed("REH", arm, 1, 0, ctx.cfg, ctx.profile.name))
    began = time.monotonic()
    seg = adapter.run_segment(adapter.Job(cell, data, training_stream_for(data, facts), env.backbone, ctx.run_dir / "timing" / tag / f"{arm}-{ct.name.replace('/', '-')}", data.seeds.r1_codes, last_update=updates, snapshots=(), write_records=False))
    train_seconds = time.monotonic() - began
    t0 = time.monotonic()
    adapter.evaluate_readout(cell, seg.model, data, facts, updates, backbone=env.backbone, rows=env.rows, target_seed=0, swap_seed=spec.swap_seed(ct.facts, ctx.cfg))
    rec = {
        **core.envelope("timing"), "label": f"{tag}-{arm}-{ct.name}", "arm": arm, "cell_type": ct.name, "slots": ct.slots, "facts": facts, "updates": updates, "wall_seconds": train_seconds, "seconds_per_update": train_seconds / updates,
        "evaluation_wall_seconds": time.monotonic() - t0, "peak_rss_bytes": int(max(seg.record["sampled_rss_bytes"], seg.record["peak_rss_bytes"])), "load_average": list(__import__("os").getloadavg()), "status": seg.record["status"],
    }  # fmt: skip
    sealed.validate_public(rec)
    return rec


def _spawn_busy(n: int) -> list["subprocess.Popen[bytes]"]:
    return [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(n)]  # noqa: S603


def _stop_busy(procs: Sequence["subprocess.Popen[bytes]"]) -> None:
    for p in procs:
        p.kill()
    for p in procs:
        p.wait(timeout=30)


def cmd_timing(ctx: Ctx, cap_hours: float) -> dict[str, Any]:
    """One stage-3 attempt per invocation (no sleep, no wait): the quiet condition is read BEFORE the stage's own workers start; if it fails the attempt is kept and not used and the decision says RETRY or PAUSED — MACHINE NOT QUIET
    (the lead reschedules). If it holds, six workers run alone, then the twelve-busy repeat; the rates and the worker count of the memory rule are written."""
    rates_path = ctx.run_dir / "timing" / "rates.json"
    if rates_path.is_file():
        return {"decision": "READY", "rates": str(rates_path)}
    att_path = ctx.run_dir / "timing" / "attempts.json"
    att_path.parent.mkdir(parents=True, exist_ok=True)
    state = read_json(att_path) if att_path.is_file() else {"first_started": datetime.now(UTC).isoformat(), "attempts": []}
    first = datetime.fromisoformat(state["first_started"])
    if ctx.profile.tiny:
        q: dict[str, Any] = {"quiet": True, "samples": [], "bypassed": "test profile: the quiet condition is not read (never in a registered run)"}
    else:
        q = accounting.quiet_check(ctx.cfg)
    state["attempts"].append({"utc": datetime.now(UTC).isoformat(), **{k: q[k] for k in q if k != "other_processes"}, "other_processes": len(q.get("other_processes", []))})
    write_json(att_path, core.jsonable(state))
    decision = accounting.attempt_decision(state["attempts"], first, cfg=ctx.cfg)
    if not q["quiet"]:
        return {"decision": decision["decision"], "attempts": len(state["attempts"]), "reasons": q["reasons"]}
    results: dict[str, Any] = {}
    for tag, busy in (("quiet", 0), ("busy", int(ctx.cfg["timing"]["busy_processes"]))):
        tasks = [ctx.task(f"timing-{tag}", f"{a}-{n.replace('/', '-')}", "timing", "--arm", a, "--cell-type", n, "--tag", tag) for a, n in timing_combos(ctx)]
        procs = _spawn_busy(busy) if busy else []
        try:
            m = run_stage(ctx, f"timing-{tag}", tasks, cap_hours * 3600.0, workers=int(ctx.cfg["timing"]["workers"]))
        finally:
            _stop_busy(procs)
        if m["status"] != "COMPLETE":
            return {"decision": f"PAUSED ({m['status']})", "tag": tag}
        if tag == "quiet" and not ctx.profile.tiny:
            alive = accounting.other_study_processes()  # R13: the condition is checked again at the end of the attempt; a process of another study that started during it makes the attempt unusable (kept, never used)
            if alive:
                state["attempts"][-1].update({"quiet": False, "reasons": ["another study's process was alive at the end of the attempt"], "other_processes": len(alive)})
                write_json(att_path, core.jsonable(state))
                return {"decision": accounting.attempt_decision(state["attempts"], first, cfg=ctx.cfg)["decision"], "attempts": len(state["attempts"]), "reasons": ["another study's process was alive at the end of the attempt"]}
        results[tag] = [read_json(t.result_path) for t in tasks]
    peak = max(int(r["peak_rss_bytes"]) for rs in results.values() for r in rs)
    n_workers = ladder.worker_count(peak, ctx.cfg)
    ctx.record_peak("stage3", peak)
    rates = {"quiet": {f"{r['arm']}|{r['cell_type']}": r["seconds_per_update"] for r in results["quiet"]}, "busy": {f"{r['arm']}|{r['cell_type']}": r["seconds_per_update"] for r in results["busy"]},
             "eval_seconds": {f"{r['arm']}|{r['cell_type']}": r["evaluation_wall_seconds"] for r in results["quiet"]}, "eval_seconds_busy": {f"{r['arm']}|{r['cell_type']}": r["evaluation_wall_seconds"] for r in results["busy"]},
             "slots": {f"{r['arm']}|{r['cell_type']}": r["slots"] for r in results["quiet"]}, "peak_rss_bytes": peak, "workers": n_workers, "used_attempt": len(state["attempts"]) - 1}  # fmt: skip
    write_json(rates_path, rates)
    state["used"] = len(state["attempts"]) - 1
    write_json(att_path, core.jsonable(state))
    return {"decision": "READY", "workers": n_workers, "peak_rss_bytes": peak}


def load_rates(run_dir: Path, *, which: str = "quiet", cfg: Mapping[str, Any] | None = None) -> ladder.Rates:
    """``ladder.Rates`` keyed by (arm, slots): where two cell types share a slot count the larger rate is kept (conservative). ``which``: quiet (the extension rule) or larger (the caps use the larger of quiet and busy)."""
    r = read_json(run_dir / "timing" / "rates.json")
    spu: dict[tuple[str, int], float] = {}
    ev: dict[tuple[str, int], float] = {}
    for key, v in r["quiet"].items():
        arm = key.split("|")[0]
        slots = int(r["slots"][key])
        b = float(r["busy"][key]) if which == "larger" else 0.0
        e_b = float(r["eval_seconds_busy"][key]) if which == "larger" else 0.0
        spu[(arm, slots)] = max(spu.get((arm, slots), 0.0), float(v), b)
        ev[(arm, slots)] = max(ev.get((arm, slots), 0.0), float(r["eval_seconds"][key]), e_b)
    return ladder.Rates(spu, ev)


# --- Stage R -----------------------------------------------------------------------------------------------------------------------------------------
# One task per RUN (cell type, arm, calibration draw, next ladder exposure): the driver runs the runs of every undecided cell type in parallel, one wave per round (the barrier of ruling 11), and decides by code from the sealed points.
# Stage R's wall time is therefore set by the longest runs, not by the sum of the four runs of a cell type. Everything per run, and every intermediate decision, lives in the sealed directory; a task's result file says only ok (B1, B3).
def ladders_of(ctx: Ctx, phase: str) -> tuple[list[int], int]:
    base = [ctx.profile.exp(int(e)) for e in ctx.cfg["ladder"]["base"]]
    lad = base if phase == "base" else [*base, ctx.profile.exp(int(ctx.cfg["ladder"]["extension_ceiling"]))]
    return lad, lad[-1]


def opaque_label(sealed_base: Path, attempt: int, ct: str, arm: str, draw: int, e: int) -> str:
    """A deterministic label that carries no cell type, arm or exposure: a hash with a salt kept in the sealed directory (created once, so a resumed wave names its tasks the same way)."""
    import hashlib
    import secrets

    p = sealed.sealed_dir(sealed_base) / f"tasksalt-r{attempt}.json"
    if not p.is_file():
        sealed.write_sealed(sealed_base, p.name, {"salt": secrets.token_hex(16)})
    salt = sealed.read_sealed(sealed_base, p.name, reader="stage-r-code", why="opaque task labels")["salt"]
    return "t" + hashlib.sha256(f"{salt}|{attempt}|{ct}|{arm}|{draw}|{e}".encode()).hexdigest()[:14]


def run_waves(ctx: Ctx, cts: Sequence[core.CellType], *, phase: str, attempt: int, prefix: str, group: str, cap_seconds: float) -> str:
    """Wave after wave until no cell type needs another run: COMPLETE, or the status of the stage that stopped (PAUSED, FAILED, ENGINEERING STOP)."""
    sb = ctx.need_sealed()
    lad_phase, ceil_phase = ladders_of(ctx, phase)
    while True:
        n = 0
        while stage_status(ctx, f"{prefix}_{phase}_i{n}") == "COMPLETE":
            n += 1
        stage = f"{prefix}_{phase}_i{n}"
        tasks = []
        taskmap: dict[str, list[Any]] = {}
        for ct in cts:
            st = items.read_state(ct, sb, ctx.th, ctx.cfg, ctx.profile, attempt=attempt, lad=lad_phase, ceiling=ceil_phase)
            for arm, d, e in items.stage_r_needs(st, lad_phase, ctx.profile, ctx.cfg, ceiling=ceil_phase):
                label = opaque_label(sb, attempt, ct.name, arm, d, e)  # N3: nothing public says which cell type continues
                taskmap[label] = [ct.name, arm, d, e]
                tasks.append(ctx.task(stage, label, "stage-r-run", "--cell-type", ct.name, "--arm", arm, "--draw", str(d), "--exposures", str(e), "--attempt", str(attempt), sealed_tasks=True))
        if not tasks:
            return "COMPLETE"
        mp = f"taskmap-{stage}.json"
        if not (sealed.sealed_dir(sb) / mp).is_file():
            sealed.write_sealed(sb, mp, {"label_to_run": taskmap})  # the label-to-run map lives only in the sealed directory
        m = run_stage(ctx, stage, tasks, cap_seconds, group=group, seal_task_stats=True)
        if m["status"] != "COMPLETE":
            return str(m["status"])


def res_of(state: items.RState, ct: core.CellType, th: core.Thresholds) -> dict[str, Any]:
    d = state.decision
    return {"status": d.status, "e_star": d.e_star, "t_exposures": d.t, "shown": d.shown, "flat_below_floor": d.flat_below_floor, "label": d.label, **items.stage_r_flags(state, ct, th)}


def stage_r_entry(res: Mapping[str, Any], *, extension: str, convergence: str, t: int | None = None) -> dict[str, Any]:
    """One ``durations.json`` entry (section 5.2 (iii)) from a cell type's final Stage R result. An empty flag set is never silent: ``reference_flags_computed`` says whether any flag could be computed (B2)."""
    flags = res.get("reference_flags") or {"cond4": False, "other": []}
    nf = res["status"] == ladder.STATUS_NONFINITE
    computed = bool(res.get("computed", False))
    labs: list[str] = []
    if nf:
        labs.append(labels.NON_FINITE_REHEARSAL)
    if res.get("reference_nonfinite"):
        labs.append("REFERENCE NON-FINITE IN REHEARSAL")
    elif not computed:
        labs.append("REFERENCE FLAGS NOT COMPUTED (A6 BELOW ITS FLOOR AT T ON BOTH DRAWS)")
    if res.get("flat_below_floor"):
        labs.append(labels.FLAT_BELOW_FLOOR)
    if res.get("reference_below_floor_at_t"):
        labs.append("REFERENCE BELOW FLOOR AT T")
    return {
        "e_star": res["e_star"], "t_exposures": t if t is not None else res["t_exposures"], "convergence": convergence, "flat_below_floor": bool(res.get("flat_below_floor")), "extension": extension, "reference_flags": flags,
        "reference_flags_computed": computed, "reference_below_floor_at_t": res.get("reference_below_floor_at_t", []), "reference_nonfinite": bool(res.get("reference_nonfinite")), "nonfinite_in_rehearsal": nf,
        "removed": bool(flags.get("other")), "labels": labs,
    }  # fmt: skip


def final_entry(res_base: Mapping[str, Any], res_ext: Mapping[str, Any] | None, extension: str, prof: Profile, cfg: Mapping[str, Any]) -> dict[str, Any]:
    ext_t = prof.exp(int(cfg["ladder"]["extended_ceiling_t"]))
    base_t = prof.exp(int(cfg["ladder"]["base_ceiling_t"]))
    st = res_base["status"]
    if st == ladder.STATUS_SHOWN:
        return stage_r_entry(res_base, extension="none", convergence="SHOWN")
    if st == ladder.STATUS_NONFINITE:
        return stage_r_entry(res_base, extension="none", convergence=labels.NON_FINITE_REHEARSAL, t=base_t)
    if st == ladder.STATUS_CANDIDATE and extension == "refused":
        return stage_r_entry(res_base, extension="refused", convergence=labels.NOT_SHOWN_REFUSED, t=base_t)
    assert res_ext is not None
    if res_ext["status"] == ladder.STATUS_SHOWN:
        return stage_r_entry(res_ext, extension="granted", convergence="SHOWN")
    if res_ext["status"] == ladder.STATUS_NONFINITE:
        return stage_r_entry(res_ext, extension="granted", convergence=labels.NON_FINITE_REHEARSAL, t=base_t)
    return stage_r_entry(res_ext, extension="granted", convergence=labels.NOT_SHOWN_REHEARSAL, t=ext_t)


def entry_for(ctx: Ctx, ct: core.CellType, attempt: int, ext_status: str) -> dict[str, Any]:
    sb = ctx.need_sealed()
    lad, top = ladders_of(ctx, "base")
    base = res_of(items.read_state(ct, sb, ctx.th, ctx.cfg, ctx.profile, attempt=attempt, lad=lad, ceiling=top), ct, ctx.th)
    ext = None
    if ext_status == "granted":
        lad2, top2 = ladders_of(ctx, "ext")
        ext = res_of(items.read_state(ct, sb, ctx.th, ctx.cfg, ctx.profile, attempt=attempt, lad=lad2, ceiling=top2), ct, ctx.th)
    return final_entry(base, ext, ext_status, ctx.profile, ctx.cfg)


def other_hours_of(ctx: Ctx) -> float:
    """R16: the hours of the stages P adds beyond training: the measured generation and gates (stage 2) times, and the analysis and report at the config's allowance."""
    return core.hours(ctx.ledger.charged(group="generate") + ctx.ledger.charged(group="gates")) + float(ctx.cfg["budget"]["analysis_report_hours"])


def emit_stage_r_completion(ctx: Ctx, dur_path: Path, ev: Sequence[str]) -> None:
    """The one public status line of Stage R, printed after ``durations.json`` exists: its path and hash, the events, the number of sealed files and ONE digest of their hashes (not the hundreds of sealed file names)."""
    sb = ctx.need_sealed()
    sealed.emit({"stage": "R", "status": "COMPLETE", "path": str(dur_path), "sha256": file_sha256(dur_path), "labels": list(ev), "count": len(sealed.sealed_hashes(sb)), "sealed_digest": sealed.hashes_digest(sb)})


def cmd_stage_r_status(ctx: Ctx, *, events_dir: Path | None = None) -> dict[str, Any]:
    """After a Stage R whose completion line failed: re-derive the events from ``durations.json`` (read-only), write the ``EVENT_<n>.md`` files that are missing (never overwriting), and print the completion line. Reads no sealed value
    (the sealed files are hashed as bytes only) and writes nothing else."""
    dur_path = ctx.repo / core.DURATIONS
    if not dur_path.is_file():
        raise StageRefused("refused: no freeze/durations.json: Stage R has not finished")
    rec = core.read_record(dur_path, "durations")
    cts = core.cell_types(ctx.cfg)
    ev = ladder.events(rec["cell_types"], cts)
    written: list[str] = []
    if events_dir is not None:
        events_dir.mkdir(parents=True, exist_ok=True)
        existing = {p.name for p in events_dir.glob("EVENT_*.md")}
        for i, e in enumerate(ev, 1):
            if f"EVENT_{i}.md" not in existing:
                written += [p.name for p in write_events_numbered(events_dir, [(i, e)], rec)]
    emit_stage_r_completion(ctx, dur_path, ev)
    return {"status": "COMPLETE", "events": ev, "event_files_written": written}


def write_events_numbered(events_dir: Path, numbered: Sequence[tuple[int, str]], durations: Mapping[str, Any]) -> list[Path]:
    events_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, e in numbered:
        p = events_dir / f"EVENT_{i}.md"
        if p.exists():
            continue
        p.write_text(f"# EVENT {i} (ADR-0023 section 5.2)\n\n{e}\n\nBy the rule fixed before any observation the study proceeds to the counting rehearsal, the freeze and Decision 2, unchanged. The human lead may stop it; that stop is his alone.\n\n`durations.json` entries at the time:\n\n```json\n{json.dumps(core.jsonable(durations.get('cell_types', {})), indent=2, sort_keys=True)}\n```\n\n`Astra review: NOT_PERFORMED`.\n", encoding="utf-8")
        out.append(p)
    return out


RULING_COSMETIC_FILES = frozenset({"studies/p10is0/sealed.py", "studies/p10is0/stages.py", "studies/p10is0/drivers.py", "studies/p10is0/plan.py"})  # plan.py: frozen_paths lists the rebind record as a frozen input (F2 b)
REBIND_RECORD = core.FREEZE_DIR / "durations_identity_rebind.json"
PIN_RE = re.compile(r"^PIN (stage_r_commit|new_commit|ruler|file) (.+)$")


def _changed_since_stage_r(repo: Path, recorded: Mapping[str, str]) -> dict[str, tuple[str, str]]:
    now = code_identity(repo)
    return {k: (recorded.get(k, ""), now.get(k, "")) for k in sorted(set(recorded) | set(now)) if recorded.get(k) != now.get(k)}


def rebind_pins(repo: Path, stage_r_commit: str, new_commit: str, ruler: str) -> str:
    """The pin block the ruling file must contain, printed for pasting (nothing typed by hand): Stage R's commit, the new commit, and for every file whose hash differs from the identity ``durations.json`` records its old and new SHA-256. The
    old hashes are checked against Stage R's commit and the new ones against the new commit; a difference refuses."""
    rec = core.read_record(repo / core.DURATIONS, "durations")
    changed = _changed_since_stage_r(repo, rec["code_identity"])
    full = {}
    for name, c in (("stage_r_commit", stage_r_commit), ("new_commit", new_commit)):
        r = planmod.git(repo, "rev-parse", "--verify", f"{c}^{{commit}}")
        if r.returncode != 0:
            raise StageRefused(f"refused: {name} {c!r} is not a commit")
        full[name] = r.stdout.decode().strip()
    lines = [f"PIN stage_r_commit {full['stage_r_commit']}", f"PIN new_commit {full['new_commit']}"]
    for path, (old, new) in changed.items():
        if planmod.committed_hash(repo, full["stage_r_commit"], path) != old or planmod.committed_hash(repo, full["new_commit"], path) != new:
            raise StageRefused(f"refused: {path} does not match Stage R's commit and the new commit")
        lines.append(f"PIN file {path} old {old} new {new}")
    lines.append(f"PIN ruler {ruler}")
    return "\n".join(lines) + "\n"


def cmd_rebind_identity(ctx: Ctx, ruling_file: Path) -> dict[str, Any]:
    """A code change after ``durations.json`` exists is an ENGINEERING STOP for the human lead. This command applies his RULING that a change confined to output validation, the command line and the frozen-input list does not void Stage R, and only on a ruling
    that pins exactly what changed (F2):

    * the ruling file is COMMITTED under ``results/`` and the tree has no uncommitted change;
    * it carries the pin block of ``rebind_pins``: Stage R's commit, the new commit (an ancestor of HEAD), the old and new SHA-256 of every changed file and the ruler's name;
    * every pin is verified: the set of pinned files equals the set that differs from ``durations.json``'s recorded identity, each old hash equals that identity and the file at Stage R's commit, each new hash equals the current file and
      the file at the new commit, and every changed file is one of ``sealed.py``, ``stages.py``, ``drivers.py``, ``plan.py``;
    * once: a second rebind, or one after the candidate plan exists, is refused.

    It rewrites only ``code_identity`` in ``durations.json`` and writes ``freeze/durations_identity_rebind.json`` (a frozen input: the freeze and the registered stages check it)."""
    repo = ctx.repo
    dur_path = repo / core.DURATIONS
    record_path = repo / REBIND_RECORD
    if record_path.exists() or (repo / core.PLAN).exists():
        raise StageRefused("refused: a rebind was already made or the candidate plan exists; one ruling covers one change and nothing after the plan")
    if not dur_path.is_file() or not ruling_file.is_file() or "results" not in ruling_file.resolve().parts:
        raise StageRefused("refused: needs freeze/durations.json and a ruling file under results/")
    rel = str(ruling_file.resolve().relative_to(repo.resolve()))
    if planmod.git(repo, "ls-files", "--error-unmatch", rel).returncode != 0 or planmod.git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise StageRefused("refused: the ruling file must be committed and the tree must have no uncommitted change")
    pins: dict[str, Any] = {"files": {}}
    for line in ruling_file.read_text(encoding="utf-8").splitlines():
        m = PIN_RE.match(line.strip())
        if m is None:
            continue
        if m[1] == "file":
            parts = m[2].split()
            if len(parts) != 5 or parts[1] != "old" or parts[3] != "new":
                raise StageRefused(f"refused: a malformed PIN file line: {line!r}")
            pins["files"][parts[0]] = (parts[2], parts[4])
        else:
            pins[m[1]] = m[2].strip()
    for need in ("stage_r_commit", "new_commit", "ruler"):
        if not pins.get(need):
            raise StageRefused(f"refused: the ruling pins no {need}")
    rec = core.read_record(dur_path, "durations")
    changed = _changed_since_stage_r(repo, rec["code_identity"])
    if set(changed) != set(pins["files"]):
        raise StageRefused(f"refused: the files that differ ({sorted(changed)}) are not the files the ruling pins ({sorted(pins['files'])})")
    outside = [k for k in changed if k not in RULING_COSMETIC_FILES]
    if outside:
        raise StageRefused(f"refused: files outside the ruling's scope differ from Stage R's code: {outside}")
    for k, v in (("stage_r_commit", pins["stage_r_commit"]), ("new_commit", pins["new_commit"])):
        r = planmod.git(repo, "rev-parse", "--verify", f"{v}^{{commit}}")
        if r.returncode != 0 or r.stdout.decode().strip() != v:
            raise StageRefused(f"refused: {k} must be a full commit hash that exists")
    if planmod.git(repo, "merge-base", "--is-ancestor", pins["stage_r_commit"], pins["new_commit"]).returncode != 0 or planmod.git(repo, "merge-base", "--is-ancestor", pins["new_commit"], "HEAD").returncode != 0:
        raise StageRefused("refused: Stage R's commit must be an ancestor of the new commit, and the new commit an ancestor of HEAD")
    for path, (old, new) in changed.items():
        pin_old, pin_new = pins["files"][path]
        ok = pin_old == old == planmod.committed_hash(repo, pins["stage_r_commit"], path) and pin_new == new == planmod.committed_hash(repo, pins["new_commit"], path)
        if not ok:
            raise StageRefused(f"refused: the pinned hashes of {path} do not equal durations.json's identity, the file at Stage R's commit, the current file and the file at the new commit")
    now = code_identity(repo)
    out = {
        **core.envelope("event"), "kind": "event", "what": "durations code identity rebound by the lead's ruling", "stage_r_commit": pins["stage_r_commit"], "new_commit": pins["new_commit"], "ruler": pins["ruler"],
        "files": [{"path": k, "old_sha256": o, "new_sha256": n} for k, (o, n) in sorted(changed.items())], "ruling_file": rel, "ruling_sha256": file_sha256(ruling_file), "utc": datetime.now(UTC).isoformat(),
    }  # fmt: skip
    write_json(record_path, core.jsonable(out))
    rec["code_identity"] = now
    write_json(dur_path, core.jsonable(rec))
    return {"status": "COMPLETE", "changed_files": sorted(changed), "durations_sha256": file_sha256(dur_path), "record": str(record_path)}


def stage_r_charged_hours(ctx: Ctx, attempt: int) -> float:
    """N2: Stage R's hours already charged, under the group ``run_waves`` writes (``stage_r_base_a<attempt>``)."""
    return core.hours(ctx.ledger.charged(group=f"stage_r_base_a{attempt}"))


def workers_cfg(ctx: Ctx) -> Mapping[str, Any]:
    """A-a: the projections and the Stage R cap use the worker count the memory rule allows, not the nominal six."""
    return {**ctx.cfg, "budget": {**ctx.cfg["budget"], "workers": ctx.workers()}}


def stage_r_extensions(ctx: Ctx, cts: Sequence[core.CellType], attempt: int, rates: ladder.Rates) -> list[dict[str, Any]]:
    """Section 5.1 items 1 to 6, once, by code, on stage 3's quiet rates; persisted in the SEALED directory (an interrupted Stage R reuses it) and public only inside ``durations.json``."""
    sb = ctx.need_sealed()
    name = f"extensions-r{attempt}.json"
    if (sealed.sealed_dir(sb) / name).is_file():
        return list(sealed.read_sealed(sb, name, reader="stage-r-code", why="resume")["decisions"])
    lad, top = ladders_of(ctx, "base")
    states = {ct.name: items.read_state(ct, sb, ctx.th, ctx.cfg, ctx.profile, attempt=attempt, lad=lad, ceiling=top) for ct in cts}
    cands = [ct for ct in cts if states[ct.name].decision.status == ladder.STATUS_CANDIDATE]
    t_known = {ct.name: int(states[ct.name].decision.t or 0) for ct in cts if ct not in cands}
    x8 = core.cell_type_by_name("8K/1K", ctx.cfg)
    dec = ladder.decide_extensions(
        cands, cts=cts, t_known=t_known, rates=rates, charged_hours=stage_r_charged_hours(ctx, attempt), other_hours=other_hours_of(ctx), x8=x8, cfg=_scaled_cfg(workers_cfg(ctx), ctx.profile)
    )  # fmt: skip
    decisions = [{"cell_type": d.cell_type, "granted": d.granted, "projected_hours": d.projected_hours, "budget_hours": d.budget_hours} for d in dec]
    sealed.write_sealed(sb, name, {"decisions": decisions})
    return decisions


def cmd_stage_r(ctx: Ctx, *, cause_file: Path | None = None, events_dir: Path | None = None) -> dict[str, Any]:
    """Stage R on the main grid's eight cell types. Prints nothing and writes nothing in the clear per cell type before ``durations.json`` exists (B3); all measurements, snapshots and intermediate decisions are in the sealed directory
    (B1). Refuses to overwrite ``durations.json``. The attempt number comes from the code-identity record (R8)."""
    dur_path = ctx.repo / core.DURATIONS
    if dur_path.exists():
        raise StageRefused(f"refused: {dur_path} exists")
    if not (ctx.run_dir / "timing" / "rates.json").is_file():
        raise StageRefused("refused: stage 3 has not written timing/rates.json")
    ctx.need_sealed()
    attempt = int(record_code_identity(ctx.run_dir, ctx.repo, cause_file=cause_file)["attempt"])
    cts = core.cell_types(ctx.cfg)
    rates = load_rates(ctx.run_dir, cfg=ctx.cfg)
    caps_rates = load_rates(ctx.run_dir, which="larger", cfg=ctx.cfg)
    tiny = ctx.profile.tiny
    cap_base = 3600.0 if tiny else ladder.stage_r_cap_hours(cts, caps_rates, [], workers_cfg(ctx)) * 3600.0
    s = run_waves(ctx, cts, phase="base", attempt=attempt, prefix=f"stage_r_a{attempt}", group=f"stage_r_base_a{attempt}", cap_seconds=cap_base)
    if s != "COMPLETE":
        return {"status": s}
    decisions = stage_r_extensions(ctx, cts, attempt, rates)
    granted = [d["cell_type"] for d in decisions if d["granted"]]
    if granted:
        by = {ct.name: ct for ct in cts}
        cap_ext = 3600.0 if tiny else (ladder.stage_r_cap_hours(cts, caps_rates, granted, workers_cfg(ctx)) - ladder.stage_r_cap_hours(cts, caps_rates, [], workers_cfg(ctx))) * 3600.0
        s = run_waves(ctx, [by[n] for n in granted], phase="ext", attempt=attempt, prefix=f"stage_r_a{attempt}", group=f"stage_r_ext_a{attempt}", cap_seconds=cap_ext)
        if s != "COMPLETE":
            return {"status": s}
    status_of = {d["cell_type"]: ("granted" if d["granted"] else "refused") for d in decisions}
    entries = {ct.name: entry_for(ctx, ct, attempt, status_of.get(ct.name, "none")) for ct in cts}
    rec = ladder.durations_record(entries, code_identity(ctx.repo))
    rec["extension_decisions"] = decisions
    rec["attempt"] = attempt
    dur_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(dur_path, core.jsonable(rec))
    ev = ladder.events(entries, cts)
    if events_dir is not None:
        write_events(events_dir, ev, rec)
    emit_stage_r_completion(ctx, dur_path, ev)
    return {"status": "COMPLETE", "events": ev}


def _scaled_cfg(cfg: Mapping[str, Any], prof: Profile) -> Mapping[str, Any]:
    """The extension rule reads T ceilings from the config: under the test profile they are the profile's tiny exposures (the rates are tiny too)."""
    if not prof.tiny:
        return cfg
    lad = {**cfg["ladder"], "base": [prof.exp(int(e)) for e in cfg["ladder"]["base"]], "base_ceiling_t": prof.exp(int(cfg["ladder"]["base_ceiling_t"])), "extended_ceiling_t": prof.exp(int(cfg["ladder"]["extended_ceiling_t"])), "extension_ceiling": prof.exp(int(cfg["ladder"]["extension_ceiling"]))}
    return {**cfg, "ladder": lad}


def write_events(events_dir: Path, events: Sequence[str], durations: Mapping[str, Any]) -> list[Path]:
    """One ``EVENT_<n>.md`` per event of section 5.2 (the study proceeds; the human lead is told at once), by the same template ``write_events_numbered`` uses. Refuses to overwrite."""
    events_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, len(events) + 1):
        if (events_dir / f"EVENT_{i}.md").exists():
            raise FileExistsError(events_dir / f"EVENT_{i}.md")
    return write_events_numbered(events_dir, list(enumerate(events, 1)), durations)


# --- caps -----------------------------------------------------------------------------------------------------------------------------------------------
def cmd_caps(ctx: Ctx, *, other_hours: float | None = None) -> dict[str, Any]:
    """``freeze/stage_caps.json``: the total cap is the hours CHARGED SO FAR plus twice the measured projection (R2), the projection taken at the larger of the quiet and busy rates (the registered run may share the machine), with X8 at its
    ceiling included; X8 has its own stage cap (twice its own projected stage), and so has its calibration. Refuses to overwrite."""
    path = ctx.repo / core.STAGE_CAPS
    if path.exists():
        raise StageRefused(f"refused: {path} exists")
    dur = core.read_record(ctx.repo / core.DURATIONS, "durations")["cell_types"]
    cts = core.cell_types(ctx.cfg)
    rates = load_rates(ctx.run_dir, which="larger", cfg=ctx.cfg)
    t_assumed = {ct.name: int(dur[ct.name]["t_exposures"]) for ct in cts if not dur[ct.name].get("removed")}
    live = [ct for ct in cts if ct.name in t_assumed]
    x8 = core.cell_type_by_name("8K/1K", ctx.cfg)
    x8_t = ctx.profile.exp(int(ctx.cfg["ladder"]["extended_ceiling_t"]))
    oh = other_hours if other_hours is not None else other_hours_of(ctx)
    charged = core.hours(ctx.ledger.charged())
    att = int(read_json(ctx.repo / core.DURATIONS).get("attempt", 0))
    proj, stages = ladder.projected_hours(cts=live, t_assumed=t_assumed, granted_rounds=[], rates=rates, charged_hours=0.0, other_hours=oh, x8=x8, workers=ctx.workers(), ladder_top=0, x8_t=x8_t)
    f = float(ctx.cfg["budget"]["stage_cap_factor"])
    per = {s.name: f * (s.total_seconds / ctx.workers() + s.longest_seconds) / 3600.0 for s in stages}
    updates_total = sum(it["updates"] for it in planmod.build_plan(ctx.cfg, dur, profile=ctx.profile)["items"]["main"])
    rec = {
        **core.envelope("stage_caps"), "provisional": False, "projection_hours": proj, "charged_hours_at_caps": charged, "total_hours": charged + f * proj,
        "stage_hours": {"main": per["main"], "x8_calibration": next((v for k, v in per.items() if k.startswith("calibration")), 0.0), "x8": per["x8"], "analysis": 1.0, "report": 1.0},
        "stage_r_hours": f * core.hours(ctx.ledger.charged(group=f"stage_r_base_a{att}") + ctx.ledger.charged(group=f"stage_r_ext_a{att}")), "rates_used": "the larger of the quiet and busy rates", "workers": ctx.workers(),
        "disk_projection_bytes_main": accounting.disk_projection_bytes(updates_total, ctx.cfg), "label": "ANALYTICAL projection from stage 3's measured rates; caps are charged-so-far plus twice it (resource caps, never a label)",
    }  # fmt: skip
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(rec))
    return rec


# --- main grid ------------------------------------------------------------------------------------------------------------------------------------
def verify_manifest(ctx: Ctx, plan: Mapping[str, Any], set_name: str, ct: core.CellType, data: Any) -> None:
    """R17 (section 14): the draw's manifest is a frozen input. Its file must hash to the value the plan names, and the regenerated data must equal the hashes in it; a difference is PAUSED — IDENTITY."""
    path = draw_manifest_path(ctx.run_dir, set_name)
    want = (plan.get("draw_manifests") or {}).get(set_name)
    if want is None or not path.is_file() or file_sha256(path) != want:
        raise IdentityMismatch(f"the data manifest of {set_name} is missing or differs from the SHA-256 the plan names")
    m = core.read_record(path, "data_manifest")
    if m["sha256s"][str(ct.facts)] != data.sha256s():
        raise IdentityMismatch(f"the data of {set_name} differ from the manifest the plan names")


def work_cell_group(ctx: Ctx, plan_items: Sequence[Mapping[str, Any]], plan: Mapping[str, Any], *, x8: bool = False) -> dict[str, Any]:
    env = env_for(ctx.run_dir)
    done = []
    for it in plan_items:
        ct = core.cell_type_by_name(it["cell_type"], ctx.cfg)
        spec = core.set_of_name(it["seed_set"], ctx.cfg, ctx.profile.name)
        verify_manifest(ctx, plan, it["seed_set"], ct, items.data_for(env, spec, ct.facts, ctx.cfg))
        cell = core.Cell("REG", ct.series, it["arm"], ct.facts, ct.slots, it["draw"], it["init_seed"])
        items.run_cell(cell, ct, int(it["t_exposures"]), ctx.run_dir, env, ctx.cfg, spec=spec)
        done.append(it["label"])
    return {"cells": done}


def groups_of(plan_items: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    """Tasks of the main grid: one per (cell type, draw), its arms in one process so that the draw is generated once."""
    g: dict[str, list[Mapping[str, Any]]] = {}
    for it in plan_items:
        g.setdefault(f"{it['cell_type'].replace('/', '-')}-d{it['draw']:02d}", []).append(it)
    return g


def load_plan_checked(ctx: Ctx) -> dict[str, Any]:
    plan = planmod.load_plan(ctx.repo / core.PLAN)
    for it in plan["items"]["main"]:
        it["t_exposures"] = plan["cell_types"][it["cell_type"]]["t_exposures"]
    return plan


def cmd_main(ctx: Ctx) -> dict[str, Any]:
    plan = load_plan_checked(ctx)
    caps = core.read_record(ctx.repo / core.STAGE_CAPS, "stage_caps")
    groups = groups_of(plan["items"]["main"])
    tasks = [ctx.task("main", n, "cells", "--group", n) for n in groups]
    m = run_stage(ctx, "main", tasks, float(caps["stage_hours"]["main"]) * 3600.0)
    return {"status": m["status"]}


# --- X8 --------------------------------------------------------------------------------------------------------------------------------------------
def registry_of(ctx: Ctx, plan: Mapping[str, Any], extra: Sequence[Mapping[str, Any]] = ()) -> tuple[dict[analysis.Key, analysis.CellRecord], list[str]]:
    return items.load_registry(ctx.run_dir, [*plan["items"]["main"], *extra])


def item_errors_of(ctx: Ctx, stages: Sequence[str]) -> list[str]:
    errs = []
    for st in stages:
        m = runner.read_manifest(ctx.run_dir, st)
        if m is not None:
            errs += [f"{st}:{k}" for k, v in m["tasks"].items() if v["status"] == runner.FAILED]
    return errs


def main_analysis(ctx: Ctx, plan: Mapping[str, Any], *, x8_items: Sequence[Mapping[str, Any]] = (), x8_status: str | None = None, x8_entry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    reg, load_errors = registry_of(ctx, plan, x8_items)
    durations = {n: {**v, "t_exposures": v.get("t_exposures")} for n, v in plan["cell_types"].items()}
    if x8_entry is not None:
        durations[x8_entry["cell_type"]] = dict(x8_entry)
    errs = [*load_errors, *item_errors_of(ctx, ("main", "x8", *x8_stage_names(ctx)))]
    dp = read_json(ctx.run_dir / "draw_plan.json") if (ctx.run_dir / "draw_plan.json").is_file() else {}
    cells = [core.make_cell("REG", core.cell_type_by_name(it["cell_type"], ctx.cfg), it["arm"], it["draw"], 0, ctx.cfg, ctx.profile.name) for it in plan["items"]["main"]]
    paused = any(stage_status(ctx, s) == "PAUSED" for s in ("main",))
    fr_path = ctx.repo / core.FREEZE_RECORD
    for n in sealed.disclosed_cell_types(read_json(fr_path) if fr_path.is_file() else None, list(durations)):
        durations[n] = {**durations[n], "lead_saw_sealed": True}
    return analysis.analyze(reg, durations, plan_cells=cells, item_errors=errs, paused=paused, x8_status=x8_status, replaced_draws={int(k): v for k, v in dp.get("replacements", {}).items()}, cfg=ctx.cfg)


def x8_stage_names(ctx: Ctx) -> list[str]:
    """R7: every stage of X8's calibration, whatever attempt and iteration (their failed tasks are item errors that stop the analysis)."""
    return sorted(p.name for p in (ctx.run_dir).glob("x8_cal_a*_i*") if (p / "manifest.json").is_file())


def x8_dir(ctx: Ctx) -> Path:
    return ctx.run_dir / "x8"


def cmd_x8_gate(ctx: Ctx) -> dict[str, Any]:
    """Section 8: read by the frozen analysis at a gate stage that passes L_Q and nothing else. X8 is triggered only if L_Q = 4 after the COMPLETE main grid."""
    if stage_status(ctx, "main") != "COMPLETE":
        raise StageRefused("refused: the main grid is not COMPLETE")
    plan = load_plan_checked(ctx)
    try:
        out = main_analysis(ctx, plan)
    except analysis.AnalysisRefused as exc:
        raise StageRefused(str(exc)) from exc
    h = out["headline"]
    lq = h["detail"].get("L_Q") if h["step"] >= 1 else None
    trig = labels.x8_triggered(lq, ctx.th, h["step"])
    gate = {**core.envelope("gate"), "x8_triggered": trig, "L_Q": lq, "not_run_label": None if trig else f"NOT RUN — L_Q BELOW 4 (or the result of steps 0 to 2: step {h['step']})"}
    p = x8_dir(ctx) / "gate.json"
    if not p.exists():
        core.write_record(p, gate)
    print(json.dumps({"x8_triggered": trig, "L_Q": lq}))
    return {"x8_triggered": trig, "L_Q": lq}


def cmd_x8(ctx: Ctx) -> dict[str, Any]:
    """The conditional block: X8's calibration by the same ladder (one task per run, waves) on the calibration draws of the Stage R whose durations.json was frozen (its attempt is read from it), the extension rule with B unchanged and P
    equal to the hours charged so far plus X8's remaining projection on stage 3's quiet rates (R1; a refusal gives NOT SHOWN), the addendum written to the run directory (never the worktree) with its SHA-256 in the ledger, then its cells."""
    gate = core.read_record(x8_dir(ctx) / "gate.json", "gate") if (x8_dir(ctx) / "gate.json").is_file() else None
    if gate is None or not gate["x8_triggered"]:
        raise StageRefused("refused: X8 was not triggered (no gate record, or L_Q is below 4)")
    plan = load_plan_checked(ctx)
    ct = core.cell_type_by_name("8K/1K", ctx.cfg)
    add_path = x8_dir(ctx) / "addendum.json"
    caps = core.read_record(ctx.repo / core.STAGE_CAPS, "stage_caps")
    attempt = int(read_json(ctx.repo / core.DURATIONS).get("attempt", 0))
    if not add_path.is_file():
        sb = ctx.need_sealed()
        cap_s = float(caps["stage_hours"]["x8_calibration"]) * 3600.0
        prefix = f"x8_cal_a{attempt}"
        s = run_waves(ctx, [ct], phase="base", attempt=attempt, prefix=prefix, group="x8_cal", cap_seconds=cap_s)
        if s != "COMPLETE":
            return {"status": s, "stage": prefix}
        ext_status = "none"
        lad, top = ladders_of(ctx, "base")
        if items.read_state(ct, sb, ctx.th, ctx.cfg, ctx.profile, attempt=attempt, lad=lad, ceiling=top).decision.status == ladder.STATUS_CANDIDATE:
            name = f"x8-extension-r{attempt}.json"
            if (sealed.sealed_dir(sb) / name).is_file():
                d = sealed.read_sealed(sb, name, reader="stage-r-code", why="resume")["decision"]
            else:
                dd = ladder.decide_x8_extension(ct, load_rates(ctx.run_dir, cfg=ctx.cfg), core.hours(ctx.ledger.charged()), _scaled_cfg(workers_cfg(ctx), ctx.profile))
                d = {"granted": dd.granted, "projected_hours": dd.projected_hours, "budget_hours": dd.budget_hours}
                sealed.write_sealed(sb, name, {"decision": d})
            ext_status = "granted" if d["granted"] else "refused"
            if d["granted"]:
                s = run_waves(ctx, [ct], phase="ext", attempt=attempt, prefix=prefix, group="x8_cal", cap_seconds=cap_s)
                if s != "COMPLETE":
                    return {"status": s, "stage": prefix}
        entry = entry_for(ctx, ct, attempt, ext_status)
        cells = []
        if not entry["removed"]:
            for arm in ct.arms:
                for draw in range(1, int(ctx.cfg["draws"]["registered"]) + 1):
                    p0 = next(it for it in plan["items"]["main"] if it["draw"] == draw)
                    c = core.make_cell("REG", ct, arm, draw, 0, ctx.cfg, ctx.profile.name)
                    cells.append({"label": c.label, "cell_type": ct.name, "arm": arm, "draw": draw, "init_seed": c.init_seed, "seed_set": p0["seed_set"], "t_exposures": entry["t_exposures"], "updates": core.updates_for(entry["t_exposures"], ctx.profile.facts_of(ct.facts))})
        add = {**core.envelope("x8_addendum"), "cell_type": ct.name, "entry": entry, "items": cells, "plan_file_sha256": file_sha256(ctx.repo / core.PLAN), "code_identity": code_identity(ctx.repo), "attempt": attempt}
        core.write_record(add_path, add)
        ctx.ledger.charge("x8-addendum", f"sha256:{file_sha256(add_path)}", 0.0)
        gate_hash = file_sha256(x8_dir(ctx) / "gate.json")
        ctx.ledger.charge("x8-gate", f"sha256:{gate_hash}", 0.0)
    add = core.read_record(add_path, "x8_addendum")
    if not any(e["run"] == f"sha256:{file_sha256(add_path)}" for e in ctx.ledger.entries()):
        raise IdentityMismatch("the X8 addendum differs from the SHA-256 in the ledger")
    if not any(e["run"] == f"sha256:{file_sha256(x8_dir(ctx) / 'gate.json')}" for e in ctx.ledger.entries()):
        raise IdentityMismatch("the X8 gate record differs from the SHA-256 in the ledger")
    if add["entry"]["removed"] or not add["items"]:
        return {"status": "COMPLETE", "not_run": "NOT RUN — REFERENCE FAILS CONDITION " + "/".join(str(x) for x in add["entry"]["reference_flags"]["other"])}
    groups = groups_of(add["items"])
    tasks = [ctx.task("x8", n, "cells", "--group", n, "--x8") for n in groups]
    m = run_stage(ctx, "x8", tasks, float(caps["stage_hours"]["x8"]) * 3600.0)
    return {"status": m["status"]}


# --- analysis and report ------------------------------------------------------------------------------------------------------------------------
def cmd_analysis(ctx: Ctx) -> dict[str, Any]:
    plan = load_plan_checked(ctx)
    gate_p = x8_dir(ctx) / "gate.json"
    x8_items: list[Mapping[str, Any]] = []
    x8_status = None
    x8_entry = None
    if gate_p.is_file() and core.read_record(gate_p, "gate")["x8_triggered"]:
        ap = x8_dir(ctx) / "addendum.json"
        if ap.is_file():
            add = core.read_record(ap, "x8_addendum")
            x8_items, x8_entry = add["items"], {**add["entry"], "cell_type": add["cell_type"]}
            x8_status = "COMPLETE" if (add["entry"]["removed"] or stage_status(ctx, "x8") == "COMPLETE") else (stage_status(ctx, "x8") or "INCOMPLETE")
        else:
            x8_status = "INCOMPLETE"
    try:
        out = main_analysis(ctx, plan, x8_items=x8_items, x8_status=x8_status, x8_entry=x8_entry)
    except analysis.AnalysisRefused as exc:
        write_json(ctx.run_dir / "engineering_stop.json", {**core.envelope("engineering_stop"), "reason": str(exc), "outcome": labels.HEAD_ITEM_ERRORS})
        raise StageRefused(f"{labels.HEAD_ITEM_ERRORS}: {exc}") from exc
    write_json(ctx.run_dir / "analysis.json", core.jsonable(out))
    return {"headline": out["headline"]["text"], "step": out["headline"]["step"]}


def cmd_report(ctx: Ctx) -> dict[str, Any]:
    """N5 (the lead's ruling): the registered report reads NOTHING sealed. It prints the label and says the measured value is disclosed by the separate post-outcome command ``disclose``."""
    p = ctx.run_dir / "analysis.json"
    if not p.is_file():
        raise StageRefused("refused: no analysis.json (the analysis refused or has not run)")
    text = report.render(read_json(p))
    (ctx.run_dir / "report.md").write_text(text, encoding="utf-8")
    return {"report": str(ctx.run_dir / "report.md")}


def cmd_disclose(ctx: Ctx) -> dict[str, Any]:
    """The post-outcome disclosure of the A6 H-ratio x of the condition-4 label: refuses unless ``analysis.json`` exists and is COMPLETE. x is condition 4's own ratio: the smallest of (H1, H2 accuracy) over (Panel A, Panel B accuracy) of A6 at the
    cell type's T on each calibration draw. A missing A6 point (a non-finite run) is recorded as missing, never a crash. Every read is logged (``disclose-code``)."""
    p = ctx.run_dir / "analysis.json"
    if not p.is_file():
        raise StageRefused("refused: no analysis record: the disclosure follows the recomputed outcome")
    a = read_json(p)
    if a.get("status") != "COMPLETE":
        raise StageRefused("refused: the analysis record is not COMPLETE")
    sb = ctx.need_sealed()
    attempt = int(read_json(ctx.repo / core.DURATIONS).get("attempt", 0))
    plan = load_plan_checked(ctx)
    out: dict[str, Any] = {}
    for name, ty in a.get("types", {}).items():
        if not any("{x}" in x for x in ty["labels"]):
            continue
        ct = core.cell_type_by_name(name, ctx.cfg)
        vals: dict[str, Any] = {}
        for d in (1, 2):
            fname = items.point_name(ct, "A6", d, attempt, int(plan["cell_types"][name]["t_exposures"]))
            if not (sealed.sealed_dir(sb) / fname).is_file():
                vals[f"calibration_draw_{d}"] = "missing"
                continue
            o = items.obs_from_json(sealed.read_sealed(sb, fname, reader="disclose-code", why="x of the condition-4 label, after the outcome was recomputed")["obs"])
            vals[f"calibration_draw_{d}"] = float(min(h / acc for h in (o.acc_h1, o.acc_h2) for acc in (o.acc_a, o.acc_b)))
        out[name] = vals
    rec = {**core.envelope("report_manifest"), "kind": "report_manifest", "a6_h_ratio_x": out, "note": "disclosed after the outcome was recomputed; changes no label"}
    write_json(ctx.run_dir / "disclosure.json", core.jsonable(rec))
    return {"status": "COMPLETE", "disclosed_cell_types": sorted(out)}


def cmd_a0_memory(ctx: Ctx) -> dict[str, Any]:
    """Sections 9 and 10 (R6): one A0 cell on the rehearsal draw at the full frozen T of the series-M cell type with the most updates (ties: the larger slot count); time and memory are its only output. Its peak joins the memory rule."""
    from studies.p9i.train import training_stream_for

    dur = core.read_record(ctx.repo / core.DURATIONS, "durations")["cell_types"]
    ms = [ct for ct in core.cell_types(ctx.cfg) if ct.series == "M" and not dur[ct.name].get("removed")]
    ct = max(ms, key=lambda c: (core.updates_for(int(dur[c.name]["t_exposures"]), ctx.profile.facts_of(c.facts)), c.slots))
    t_exp = int(dur[ct.name]["t_exposures"])
    env = env_for(ctx.run_dir)
    facts = env.facts_of(ct.facts)
    spec = core.rehearsal_set(ctx.cfg, ctx.profile.name)
    data = items.data_for(env, spec, ct.facts, ctx.cfg)
    cell = core.Cell("REH", ct.series, "A0", ct.facts, ct.slots, 1, core.init_seed("REH", "A0", 1, 0, ctx.cfg, ctx.profile.name))
    began = time.monotonic()
    seg = adapter.run_segment(adapter.Job(cell, data, training_stream_for(data, facts), env.backbone, sealed.sealed_dir(ctx.need_sealed()) / "a0_memory", data.seeds.r1_codes, last_update=core.updates_for(t_exp, facts), snapshots=(), diag_early=(ctx.profile.diag or (64, 1024, 4096))[0], diag_late=(ctx.profile.diag or (64, 1024, 4096))[1], diag_switch=(ctx.profile.diag or (64, 1024, 4096))[2]))
    peak = int(max(seg.record["sampled_rss_bytes"], seg.record["peak_rss_bytes"]))
    ctx.record_peak("a0_memory", peak)
    rec = {**core.envelope("timing"), "label": "a0-memory", "cell_type": ct.name, "arm": "A0", "updates": core.updates_for(t_exp, facts), "wall_seconds": time.monotonic() - began, "peak_rss_bytes": peak, "status": seg.record["status"]}
    sealed.validate_public(rec)
    write_json(ctx.run_dir / "timing" / "a0_memory.json", core.jsonable(rec))
    return {"status": "COMPLETE" if seg.record["status"] == "completed" else "FAILED", "workers": ctx.workers(), "peak_rss_bytes": peak}


# --- worker entry ------------------------------------------------------------------------------------------------------------------------------
def worker_main(argv: Sequence[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=("generate", "timing", "stage-r-run", "cells"))
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sealed-dir")
    ap.add_argument("--result", required=True)
    ap.add_argument("--set")
    ap.add_argument("--arm")
    ap.add_argument("--cell-type")
    ap.add_argument("--tag")
    ap.add_argument("--draw", type=int)
    ap.add_argument("--exposures", type=int)
    ap.add_argument("--attempt", type=int, default=0)
    ap.add_argument("--group")
    ap.add_argument("--x8", action="store_true")
    a = ap.parse_args(list(argv))
    accounting.configure_process()  # first: the platform check below reads the settings this sets (N6)
    run_dir, repo = Path(a.run_dir), Path(a.repo)
    registered = (repo / core.FREEZE_RECORD).is_file() and a.kind == "cells"
    try:
        if registered:
            accounting.check_platform(core.load_config(repo / core.CONFIG))
        ctx = Ctx(repo, run_dir, registered=registered, sealed_dir=Path(a.sealed_dir) if a.sealed_dir else None)
        worker_guard(ctx)
        public: dict[str, Any] = {}
        if a.kind == "generate":
            res = work_generate(ctx, a.set)
            public = {"g1_passed": res["g1_passed"]}
        elif a.kind == "timing":
            res = work_timing(ctx, a.arm, a.cell_type, a.tag)
            public = {k: res[k] for k in ("arm", "cell_type", "slots", "facts", "updates", "wall_seconds", "seconds_per_update", "evaluation_wall_seconds", "peak_rss_bytes")}
        elif a.kind == "stage-r-run":
            ct = core.cell_type_by_name(a.cell_type, ctx.cfg)
            lad, _ = ladders_of(ctx, "ext")
            items.stage_r_run(ct, a.arm, a.draw, a.exposures, ctx.need_sealed(), env_for(run_dir), ctx.cfg, attempt=a.attempt, lad=lad)  # nothing about the run is returned or printed (B3)
        else:
            plan = load_plan_checked(ctx)
            its = list(core.read_record(x8_dir(ctx) / "addendum.json", "x8_addendum")["items"]) if a.x8 else plan["items"]["main"]
            work_cell_group(ctx, groups_of(its)[a.group], plan, x8=a.x8)
        out = Path(a.result)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_json(out, core.jsonable({"ok": True, **public}))
        return 0
    except (IdentityMismatch, StageRefused) as exc:
        print(f"PAUSED — IDENTITY: {str(exc)[:200]}", file=sys.stderr)
        return IDENTITY_EXIT
    except (adapter.EnvironmentStop, accounting.DiskPause, MemoryError, psutil.Error, OSError) as exc:
        print(f"PAUSED — ENVIRONMENT: {type(exc).__name__}", file=sys.stderr)  # R4: an environment condition anywhere in a worker is a pause, never a permanent failed task
        return ENV_EXIT
    except accounting.PlatformMismatch as exc:
        print(f"PAUSED — IDENTITY: {exc}", file=sys.stderr)
        return IDENTITY_EXIT
    except CodeChanged as exc:
        print(str(exc), file=sys.stderr)
        return CODE_CHANGED_EXIT
