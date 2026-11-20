# ruff: noqa: E501
"""P10IS5 stage driver (ADR-0028 sections 8 and 12): ``r0``, ``r1``, ``m`` and ``k`` (the Decision 1 stages), ``registered <stage>`` (the entry point the fixed launch scripts call: ``e1``, ``p``, ``e2``, ``analysis``,
``report``, ``delete``), ``candidate-plan``, ``freeze``, ``caps-proposal``, ``config-proposal``, ``seed-gate``, and ``work-pass`` (the worker process: one pass per process). Run from the repository root:
``uv run --locked python -m studies.p10is5.stages <command> ...``.

Registered stages take the run directory and the freeze commit and nothing else; every other value (geometry, seeds, paths, caps) comes from ``freeze/plan.json`` and ``configs/p10is5_ssd.toml``. They REFUSE unless the working
tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and the freeze record exist and every identity holds, and a committed Decision 2 names the freeze commit
(``plan.check_preconditions``, ``plan.verify_plan``, ``plan.require_decision_2``). Nothing is frozen today: they refuse today. Stages R1, M, K and E2 run ALONE (the quiet rule) under ``caffeinate -i`` (the launch scripts).
Exit codes: 0 done; 70 ENGINEERING STOP; 75 PAUSED — IDENTITY (nothing written); 76 PAUSED (resumable: quiet rule, write budget, hours, store not cold, drive health); 2 a refusal.
"""

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

from arborlm.io import read_json

from . import (
    analysis,
    bench,
    blocks,
    core,
    device,
    e2,
    freeze,
    r0,
    r1,
    rehearsal,
    report,
    system,
)
from . import plan as planmod
from .core import EngineeringStop, Paused, StageRefused

PROVISIONAL_NOTE = "provisional caps: this record cannot be frozen on"


# --- process setup and dependencies ---------------------------------------------------------------------------------------------------------------
def configure_process(cfg: Any) -> None:
    """The platform of record: one thread, one interop thread, deterministic algorithms. Called before any torch work in the process."""
    torch.set_num_threads(int(cfg["platform"]["torch_num_threads"]))
    with contextlib.suppress(RuntimeError):
        torch.set_num_interop_threads(int(cfg["platform"]["torch_interop_threads"]))
    torch.use_deterministic_algorithms(bool(cfg["platform"]["deterministic_algorithms"]))


def volume_bsd(run: system.Run, where: Path) -> str | None:
    rc, out, _ = run(["df", "-k", str(where)])
    try:
        return system.parse_df_k(out)["device"].removeprefix("/dev/") if rc == 0 else None
    except ValueError:
        return None


def make_cross_check(run_b: Any, run: system.Run, where: Path) -> Any:
    """The system-wide cross-checks, printed only (never charged, never called NAND or media traffic): the disk0 driver's bytes, and the APFS volume's bytes read from the block device."""
    bsd = volume_bsd(run, where)

    def cross() -> dict[str, Any]:
        rc, out = run_b(["ioreg", "-a", "-r", "-c", "AppleAPFSVolume", "-l"])
        return {"driver": system.read_driver(run_b), "volume": system.parse_volume_stats(out, bsd) if rc == 0 and bsd else None}

    return cross


def make_gate(cfg: Any, deps_run: system.Run, run_b: Any, boot_time: int | None, sleep: Any = time.sleep) -> bench.QuietGate:
    q = cfg["quiet"]

    def read() -> dict[str, Any]:
        return system.read_quiet(deps_run, run_b, cfg, sleep, time.monotonic, boot_time)

    def wait(rd: Any) -> Any:
        return system.wait_for_quiet(rd, retry_interval=float(q["retry_interval_seconds"]), deadline=float(q["retry_deadline_seconds"]), sleep=sleep, clock=time.monotonic)

    return bench.QuietGate(read, wait, lambda: sleep(float(q["settle_seconds"])))


def make_deps(cfg: Any, where: Path) -> blocks.Deps:
    """Real dependencies. Every sleep goes through ``deps.snooze`` so that waiting is not charged to the hours cap."""
    boot = system.read_boottime(system.run_command)
    deps = blocks.Deps(counter=device.ProcCounter(), gate=None, cross_check=make_cross_check(system.run_bytes, system.run_command, where))  # type: ignore[arg-type]
    deps.gate = make_gate(cfg, system.run_command, system.run_bytes, boot, deps.snooze)
    return deps


def cfg_with_r1_figures(cfg: Any, r1_record: dict[str, Any]) -> Any:
    """M's quiet thresholds come straight from R1's record (the config's figures are written after M)."""
    import copy

    out = copy.deepcopy(dict(cfg))
    out["fixed_after_r1_and_m"] = {**cfg["fixed_after_r1_and_m"], **{k: float(r1_record["idle_figures"][k]) for k in freeze.FIGURE_KEYS}}
    return out


def exit_for(e: BaseException) -> int:
    if isinstance(e, EngineeringStop):
        return core.ENGINEERING_STOP_EXIT
    if isinstance(e, Paused | core.LedgerRefused):
        return core.PAUSED_EXIT
    if isinstance(e, StageRefused):
        return core.IDENTITY_EXIT
    raise e


def ledgers(run_dir: Path, cfg: Any, hours_total: float | None = None) -> tuple[device.WriteLedger, core.HoursLedger]:
    """ONE write ledger and ONE hours ledger for the whole study: they live in the study's one run directory, shared by R0, R1, M, K, E1, P, E2 (``candidate-plan`` refuses records from any other run directory)."""
    return device.WriteLedger(run_dir / "write_ledger.json", int(cfg["budget"]["cap_bytes"])), core.hours_ledger_for(run_dir / "hours_ledger.json", cfg)


def guard_run_dir(repo: Path, run_dir: Path) -> None:
    planmod.require_ignored_run_dir(repo, run_dir)


# --- R0, R1 ----------------------------------------------------------------------------------------------------------------------------------
def cmd_r0(args: argparse.Namespace) -> int:
    repo = core.repo_root()
    cfg = core.load_config()
    configure_process(cfg)
    run_dir, data_dir = Path(args.run_dir).resolve(), Path(args.data_dir).resolve()
    guard_run_dir(repo, run_dir)
    planmod.require_data_dir_outside(repo, data_dir, str(cfg["device"]["directory_suffix"]))
    deps = make_deps(cfg, data_dir.parent)
    ledger, _ = ledgers(run_dir, cfg, float(cfg["caps"]["total_hours"]))
    problems = planmod.platform_problems(cfg)
    _, hours = ledgers(run_dir, cfg)
    with hours.timed("R0", "r0", deps.clock, lambda: deps.slept):
        rec = r0.run_r0(cfg, data_dir, run_dir, deps, ledger, problems)
    print(json.dumps({"r0": str(run_dir / "r0" / "r0.json"), "platform_of_record": rec["platform_of_record"], "probe_bytes_written": rec["probe_bytes_written"], "spotlight_indexes_directory": rec["hygiene"]["spotlight_indexes_directory"]}))
    return 0


def cmd_r1(args: argparse.Namespace) -> int:
    repo = core.repo_root()
    cfg = core.load_config()
    configure_process(cfg)
    run_dir, data_dir = Path(args.run_dir).resolve(), Path(args.data_dir).resolve()
    guard_run_dir(repo, run_dir)
    planmod.require_data_dir_outside(repo, data_dir, str(cfg["device"]["directory_suffix"]))
    problems = planmod.platform_problems(cfg)
    if problems:
        raise StageRefused("refused: not the platform of record: " + "; ".join(problems))
    deps = make_deps(cfg, data_dir.parent)
    ledger, _ = ledgers(run_dir, cfg, float(cfg["caps"]["total_hours"]))
    _, hours = ledgers(run_dir, cfg)
    with torch.no_grad(), hours.timed("R1", "r1", deps.clock, lambda: deps.slept):
        rec = r1.run_r1(
            cfg, data_dir, run_dir, deps, ledger, now=time.time,
            hygiene=lambda ex: system.hygiene_record(deps.run, data_dir, file_exists=ex),
            ec3=lambda label: system.ec3_record(deps.run, deps.run_b, data_dir, label),
        )  # fmt: skip
    print(json.dumps({"r1": str(run_dir / "r1" / "r1.json"), "outcome": rec["outcome"], "reasons": rec["not_evaluable_reasons"], "idle_figures": rec["idle_figures"]}))
    return 0 if rec["passed"] else 1


# --- M and K ---------------------------------------------------------------------------------------------------------------------------------
def worker_extra(mode: str, data_dir: Path, repo: Path, freeze_commit: str | None) -> list[str]:
    extra = ["--data-dir", str(data_dir), "--repo", str(repo)]
    if freeze_commit:
        extra += ["--freeze-commit", freeze_commit]
    return extra


def inside(path: Path, run_dir: Path) -> bool:
    try:
        path.resolve().relative_to(run_dir.resolve())
        return True
    except ValueError:
        return False


def cmd_m(args: argparse.Namespace) -> int:
    """M, in the study's ONE run directory (R1's record must be inside it). If CV_R cannot be determined (fewer than five valid medians for c(1) or c(3)), m_t is NOT DETERMINED and the candidate plan is refused;
    M may be repeated ONCE (``--repeat-cause``), in the same run directory under the same ledgers, the first attempt kept as ``M_attempt1`` with its cause; a second failure ends the study as ENGINEERING NOT EVALUABLE —
    MARGIN NOT DETERMINED."""
    repo = core.repo_root()
    cfg0 = core.load_config()
    configure_process(cfg0)
    run_dir, data_dir = Path(args.run_dir).resolve(), Path(args.data_dir).resolve()
    guard_run_dir(repo, run_dir)
    if not inside(Path(args.r1_record), run_dir):
        raise StageRefused("refused: R1's record is not under this run directory: the study has ONE run directory and ONE ledger")
    r1_rec = core.read_record(Path(args.r1_record), "r1")
    if not r1_rec.get("passed"):
        raise StageRefused("refused: M needs a passed R1 record (EC4: every check of section 7 passed in R1)")
    attempt = 2 if (run_dir / "M_attempt1").exists() else 1  # a resumed repeat records the right attempt number
    m_path = run_dir / "M" / "m.json"
    if m_path.is_file():
        prior = core.read_record(m_path, "rehearsal")
        if (run_dir / "M_attempt1").exists():
            raise StageRefused("refused: M has already been repeated once; a second failure ends the study (ENGINEERING NOT EVALUABLE — MARGIN NOT DETERMINED)")
        if (prior.get("summary") or {}).get("margin") is not None:
            raise StageRefused("refused: M determined m_t; it is not repeated")
        if not args.repeat_cause:
            raise StageRefused("refused: M did not determine m_t: repeat it once with --repeat-cause naming the cause")
        (run_dir / "M").rename(run_dir / "M_attempt1")
        core.write_record(run_dir / "M_attempt1" / "repeat_cause.json", {**core.envelope("amendment"), "cause": args.repeat_cause, "utc": core.utc_stamp()})
        attempt = 2
    cfg = cfg_with_r1_figures(cfg0, r1_rec)
    ctx = bench.context_m(cfg, data_dir, run_dir)
    deps = make_deps(cfg, data_dir.parent)
    _, hours = ledgers(run_dir, cfg)
    run = blocks.spawn_pass_runner(ctx, worker_extra("m", data_dir, repo, None) + ["--r1-record", str(args.r1_record)], timeout=float(cfg["quiet"]["pass_timeout_seconds"]))
    with torch.no_grad():
        try:
            rehearsal.run_rehearsal_stage(ctx, cfg, deps, hours, lambda r: run, data_dir / "control.bin", r1_rec)  # the blocks, the prediction and the harness figure are charged inside, once
        except (Paused, core.LedgerRefused, EngineeringStop) as e:
            # A PAUSED or stopped M writes NO m.json (only its pause record): it resumes, and never consumes the one permitted repeat. Only a COMPLETED M with fewer than five valid medians does.
            core.write_record(run_dir / "M" / "pause.json", {**core.envelope("stage_manifest"), "stage": "M", "attempt": attempt, "paused": type(e).__name__, "detail": str(e)[:300], "utc": core.utc_stamp()}, overwrite=True)
            raise
        summary = rehearsal.m_summary(ctx, cfg, hours.charged("rehearsal") / 3600.0)
        text = ""
        if summary["margin"] is not None and bench.load_stage_records(ctx)[0]:
            m_t, spread = summary["margin"]["m_t"], summary["margin"]["timing_spread"]
            with contextlib.suppress(analysis.AnalysisRefused):
                reg = e2.build_registry(ctx, cfg, r1_rec, m_t=m_t, timing_spread=spread)
                reg["thresholds"]["valid_min_repeats"] = 1
                text = report.render_report(analysis.analyse(reg), {"write_ledger_bytes": "see the write ledger", "hours": hours.charged() / 3600.0}, ctx.geometry.cells())
        outcome = "MARGIN DETERMINED" if summary["margin"] is not None else ("ENGINEERING NOT EVALUABLE — MARGIN NOT DETERMINED" if attempt == 2 else "m_t NOT DETERMINED: M may be repeated once")
        core.write_record(run_dir / "M" / "m.json", {**core.envelope("rehearsal"), "stage": "M", "attempt": attempt, "outcome": outcome, "caps_provisional": core.caps_provisional(cfg), "note": PROVISIONAL_NOTE if core.caps_provisional(cfg) else "", "summary": summary, "report_text": text}, overwrite=True)
    print(json.dumps({"m": str(run_dir / "M" / "m.json"), "cv_r": summary["cv"]["cv_r"], "margin": summary["margin"], "outcome": outcome}))
    return 0 if summary["margin"] is not None else 1


def cmd_k(args: argparse.Namespace) -> int:
    repo = core.repo_root()
    cfg = core.load_config()
    configure_process(cfg)
    run_dir, data_dir = Path(args.run_dir).resolve(), Path(args.data_dir).resolve()
    guard_run_dir(repo, run_dir)
    plan_path = Path(args.plan) if args.plan else repo / core.PLAN
    plan = planmod.Plan.load(plan_path)
    planmod.verify_plan(plan, repo, run_dir, candidate=True)
    bad = planmod.platform_problems(cfg)
    if bad:
        raise StageRefused("refused: not the platform of record: " + "; ".join(bad))
    r1_rec = core.read_record(Path(plan.data["records"]["r1"]["path"]), "r1")
    ctx = bench.context_from_plan("K", plan, run_dir, cfg)
    deps = make_deps(cfg, data_dir.parent)
    _, hours = ledgers(run_dir, cfg)
    run = blocks.spawn_pass_runner(ctx, worker_extra("k", data_dir, repo, None) + ["--plan", str(plan_path)], timeout=float(cfg["quiet"]["pass_timeout_seconds"]))
    with torch.no_grad():
        rehearsal.run_rehearsal_stage(ctx, cfg, deps, hours, lambda r: run, Path(plan.paths["control_file"]), r1_rec)
        enumeration = rehearsal.enumerate_registered_from_plan(plan)
        analysis_ok = report_ok = False
        try:
            res, text = rehearsal.analyse_rehearsal(ctx, cfg, r1_rec)
            analysis_ok = report_ok = bool(res) and bool(text)
        except analysis.AnalysisRefused as e:
            print(f"K analysis refused: {e}", file=sys.stderr)
    rec = rehearsal.k_record(ctx, cfg, plan, rehearsal.plan_file_sha(plan_path), enumeration, analysis_ok, report_ok)
    core.write_record(run_dir / "K" / "k.json", rec, overwrite=True)
    print(json.dumps({"k": str(run_dir / "K" / "k.json"), "candidate": rec["candidate"], "enumeration": enumeration}))
    return 0 if rec["candidate"]["status"] == "COMPLETE" else 1


# --- registered stages ----------------------------------------------------------------------------------------------------------------------
def load_registered(args: argparse.Namespace, stage: str) -> tuple[Path, Path, Any, Any]:
    """The process is configured FIRST (one thread, one interop thread, deterministic algorithms: the platform of record), then every precondition is checked. A refusal here is an identity refusal (exit 75, nothing written)."""
    repo = Path(args.repo) if getattr(args, "repo", None) else core.repo_root()
    run_dir = Path(args.run_dir).resolve()
    try:
        cfg = core.load_config(repo / core.CONFIG)
        configure_process(cfg)
        planmod.stages_refusing_reasons(stage, repo, run_dir, args.freeze_commit)
        plan = planmod.load_registered_plan(repo)
    except core.IdentityRefused:
        raise
    except StageRefused as e:
        raise core.IdentityRefused(str(e)) from e
    return repo, run_dir, cfg, plan


def registered_e1(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "e1")
    configure_process(cfg)
    deps = make_deps(cfg, Path(plan.paths["data_dir"]).parent)
    ledger, _ = ledgers(run_dir, cfg, plan.total_cap_seconds() / 3600.0)
    _, hours = ledgers(run_dir, cfg)
    with hours.timed("E1", "e1", deps.clock, lambda: deps.slept):
        rec = e2.run_e1(plan, cfg, deps, ledger, run_dir, now=time.time)
    print(json.dumps({"e1": rec["status"], "ledger_bytes": rec["ledger_bytes"]}))
    return 0


def registered_p(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "p")
    configure_process(cfg)
    ctx = bench.context_from_plan("E2", plan, run_dir, cfg)
    _, hours = ledgers(run_dir, cfg)
    with torch.no_grad(), hours.timed("P", "p", time.monotonic, lambda: 0.0):
        man = bench.write_prediction(ctx)
    print(json.dumps({"prediction": man["path"], "sha256": man["sha256"], "passes": man["passes"]}))
    return 0


def registered_e2(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "e2")
    configure_process(cfg)
    e1rec = read_json(e2.e1_record_path(run_dir)) if e2.e1_record_path(run_dir).is_file() else None
    if e1rec is None:
        raise StageRefused("refused: E1 has not completed (no E1 record)")
    ctx = bench.context_from_plan("E2", plan, run_dir, cfg)
    bench.load_prediction(ctx)  # refuses unless the SHA-256 is the one stage P recorded
    deps = make_deps(cfg, Path(plan.paths["data_dir"]).parent)
    ledger, hours = ledgers(run_dir, cfg)
    state0 = blocks.StageState.load(ctx.stage_dir() / "state.json")
    if args.decline_write_budget:
        blocks.decline_write_budget(state0)
        print(json.dumps({"e2": state0.data["status"]}))
        return 0
    amend = None
    if args.rerun_after_stop:
        if not args.amendment or not Path(args.amendment).is_file():
            raise StageRefused("refused: a rerun after an engineering stop needs --amendment naming a recorded amendment file")
        amend = args.rerun_after_stop
    run = blocks.spawn_pass_runner(ctx, ["--repo", str(repo), "--freeze-commit", args.freeze_commit, "--data-dir", str(Path(plan.paths["data_dir"]))], timeout=float(cfg["quiet"]["pass_timeout_seconds"]))
    with torch.no_grad():
        state = e2.run_e2(ctx, cfg, deps, ledger, hours, lambda r: run, Path(plan.paths["control_file"]), now=time.time, e1_built_at=float(e1rec["built_at"]), rerun_after_stop=amend)
    print(json.dumps({"e2": state.data["status"], "blocks": state.data.get("blocks"), "spare_used": state.data["spare_used"]}))
    return 0


def analysis_path(run_dir: Path) -> Path:
    return run_dir / "analysis" / "analysis.json"


def registered_analysis(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "analysis")
    ctx = bench.context_from_plan("E2", plan, run_dir, cfg)
    state = read_json(ctx.stage_dir() / "state.json") if (ctx.stage_dir() / "state.json").is_file() else {"status": "NOT STARTED"}
    if state["status"] not in core.FINAL_STATUSES:
        raise StageRefused(f"refused: E2's manifest says {state['status']}: the analysis reads a stage with a final status ({'; '.join(core.FINAL_STATUSES)})")
    r1_rec = core.read_record(Path(plan.data["records"]["r1"]["path"]), "r1")
    reg = e2.build_registry(ctx, cfg, r1_rec)
    res = e2.labels_of(reg)
    core.write_record(analysis_path(run_dir), {**core.envelope("analysis"), "result": res, "grid": [list(c) for c in ctx.geometry.cells()], "registry_summary": {"passes": len(reg["passes"]), "blocks": len(reg["blocks"])}}, overwrite=False)
    print(json.dumps({"EQ-A": res["EQ-A"]["label"], "EQ-B": res["EQ-B"]["label"], "EQ-D": res["EQ-D"]["label"], "scientific": res["scientific"]["label"]}))
    return 0


def registered_report(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "report")
    rec = core.read_record(analysis_path(run_dir), "analysis")
    wl = device.WriteLedger(run_dir / "write_ledger.json", int(cfg["budget"]["cap_bytes"]))
    hl = core.hours_ledger_for(run_dir / "hours_ledger.json", cfg)
    r1_rec = core.read_record(Path(plan.data["records"]["r1"]["path"]), "r1")
    record_bytes = sum(p.stat().st_size for p in run_dir.rglob("*.json") if p.is_file())  # measured; NOT charged to the 10 GB ledger
    e1rec = read_json(e2.e1_record_path(run_dir)) if e2.e1_record_path(run_dir).is_file() else {}
    after = (e1rec.get("ec3_after") or {})
    dev = {"smart_status": after.get("smart_status", core.NOT_READABLE), "free_bytes": ((after.get("free") or {}) if isinstance(after.get("free"), dict) else {}).get("free_bytes", core.NOT_READABLE), "driver_write_bytes": ((after.get("driver_since_boot") or {}) if isinstance(after.get("driver_since_boot"), dict) else {}).get("write_bytes", core.NOT_READABLE)}
    text = report.render_report(rec["result"], {"device": dev, "write_ledger_bytes": wl.total(), "hours": round(hl.charged() / 3600.0, 3), "record_bytes": record_bytes, "r1_harness": r1_rec.get("harness"), "r1_idle_figures": r1_rec.get("idle_figures")}, [tuple(c) for c in rec["grid"]])
    out = run_dir / "report" / "REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"report": str(out)}))
    return 0


def registered_delete(args: argparse.Namespace) -> int:
    repo, run_dir, cfg, plan = load_registered(args, "delete")
    if not args.independent_recomputation_done:
        raise StageRefused("refused: files are deleted after the independent recomputation: pass --independent-recomputation-done once it is recorded")
    deps = make_deps(cfg, Path(plan.paths["data_dir"]).parent)
    out: dict[str, Any] = {**core.envelope("hygiene"), "utc": core.utc_stamp(), "deleted": {}}
    for name in ("store", "rehearsal_file", "control_file"):
        out["deleted"][name] = device.delete_built_file(Path(plan.paths[name]))
    out["hygiene_after"] = system.hygiene_record(deps.run, Path(plan.paths["data_dir"]), file_exists=False)
    out["ec3_after"] = system.ec3_record(deps.run, deps.run_b, Path(plan.paths["data_dir"]), "after deletion")
    core.write_record(run_dir / "delete" / "delete.json", out, overwrite=True)
    print(json.dumps({"deleted": {k: v["absent"] for k, v in out["deleted"].items()}, "store_retained_by_snapshot": out["hygiene_after"]["store_retained_by_snapshot"]}))
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """If the study stops before the freeze, R1's files (the control file and the rehearsal file) are not left on the drive: deleted, absence checked, free space and snapshots recorded. Refused once a freeze record exists
    (then ``registered delete`` is the way) and refused without ``--confirm-study-stopped``."""
    repo = core.repo_root()
    cfg = core.load_config()
    if (repo / planmod.FREEZE_RECORD).exists():
        raise StageRefused("refused: a freeze record exists; use registered delete after the independent recomputation")
    if not args.confirm_study_stopped:
        raise StageRefused("refused: pass --confirm-study-stopped: this deletes R1's control file and rehearsal file")
    data_dir, run_dir = Path(args.data_dir).resolve(), Path(args.run_dir).resolve()
    planmod.require_data_dir_outside(repo, data_dir, str(cfg["device"]["directory_suffix"]))
    out: dict[str, Any] = {**core.envelope("hygiene"), "utc": core.utc_stamp(), "deleted": {n: device.delete_built_file(data_dir / n) for n in ("control.bin", "rehearsal.bin")}}
    out["hygiene_after"] = system.hygiene_record(system.run_command, data_dir, file_exists=False)
    core.write_record(run_dir / "cleanup" / "cleanup.json", out, overwrite=True)
    print(json.dumps({"deleted": {k: v["absent"] for k, v in out["deleted"].items()}, "store_retained_by_snapshot": out["hygiene_after"]["store_retained_by_snapshot"]}))
    return 0


REGISTERED = {"e1": registered_e1, "p": registered_p, "e2": registered_e2, "analysis": registered_analysis, "report": registered_report, "delete": registered_delete}


# --- the worker: one pass per process ----------------------------------------------------------------------------------------------------------
def work_pass(args: argparse.Namespace) -> int:
    """Re-check identity (a refusal exits 75 with nothing written), derive the pass again from the plan or the config, assert it against the prediction record, run it between two counter snapshots, hash the pages after
    the last one, write the pass record. An ENGINEERING STOP records its cause and exits 70."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    configure_process(cfg)
    run_dir = Path(args.run_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    try:
        if args.stage == "E2":
            planmod.stages_refusing_reasons("e2", repo, run_dir, args.freeze_commit)
            plan = planmod.load_registered_plan(repo)
            ctx = bench.context_from_plan("E2", plan, run_dir, cfg)
        elif args.stage == "K":
            plan = planmod.Plan.load(Path(args.plan) if args.plan else repo / core.PLAN)
            planmod.verify_plan(plan, repo, run_dir, candidate=True)
            ctx = bench.context_from_plan("K", plan, run_dir, cfg)
        else:
            ctx = bench.context_m(cfg, data_dir, run_dir)
        prediction = bench.load_prediction(ctx)
        bad = planmod.platform_problems(cfg)
        if bad:
            raise StageRefused("refused: not the platform of record: " + "; ".join(bad))
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return core.IDENTITY_EXIT
    key = core.pass_key(args.stage, args.repeat, args.k, args.s, args.attempt)
    run_b = system.run_bytes
    try:
        with torch.no_grad():
            rec = bench.execute_pass(
                ctx, args.repeat, args.k, args.s, args.attempt, prediction, device.ProcCounter(), block=args.block, role=args.role, seq=args.seq, source_repeat=args.source_repeat,
                cross_check=make_cross_check(run_b, system.run_command, ctx.file_path.parent),
            )  # fmt: skip
            bench.commit_pass(ctx, rec)
    except EngineeringStop as e:
        blocks.record_stop(ctx, key, e.cause, e.detail)
        print(str(e), file=sys.stderr)
        return core.ENGINEERING_STOP_EXIT
    return 0


# --- entry point -----------------------------------------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is5.stages")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("r0", "r1"):
        p = sub.add_parser(name)
        p.add_argument("--run-dir", required=True)
        p.add_argument("--data-dir", required=True)
    m = sub.add_parser("m")
    m.add_argument("--run-dir", required=True)
    m.add_argument("--data-dir", required=True)
    m.add_argument("--r1-record", required=True)
    m.add_argument("--repeat-cause", help="the recorded cause of the one permitted repeat of M")
    k = sub.add_parser("k")
    k.add_argument("--run-dir", required=True)
    k.add_argument("--data-dir", required=True)
    k.add_argument("--plan")
    r = sub.add_parser("registered")
    r.add_argument("stage", choices=sorted(REGISTERED))
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit")
    r.add_argument("--repo")
    r.add_argument("--rerun-after-stop")
    r.add_argument("--amendment")
    r.add_argument("--independent-recomputation-done", action="store_true")
    r.add_argument("--decline-write-budget", action="store_true", help="the human lead declines more writes after a PAUSE on the write cap")
    c = sub.add_parser("cleanup", help="delete R1's files if the study stops before the freeze")
    c.add_argument("--run-dir", required=True)
    c.add_argument("--data-dir", required=True)
    c.add_argument("--confirm-study-stopped", action="store_true")
    w = sub.add_parser("work-pass")
    w.add_argument("--stage", required=True, choices=("E2", "M", "K"))
    w.add_argument("--run-dir", required=True)
    w.add_argument("--data-dir", required=True)
    w.add_argument("--repeat", type=int, required=True)
    w.add_argument("--k", type=int, required=True)
    w.add_argument("--s", type=int, required=True)
    w.add_argument("--attempt", type=int, default=1)
    w.add_argument("--block", required=True)
    w.add_argument("--role", required=True)
    w.add_argument("--seq", type=int, required=True)
    w.add_argument("--source-repeat", type=int, default=None, help="a pass-level use of the spare: the spare repeat whose tiles and seeds this cell takes")
    w.add_argument("--repo")
    w.add_argument("--freeze-commit")
    w.add_argument("--plan")
    w.add_argument("--r1-record")
    freeze.add_commands(sub)
    return ap


STAGE_OF = {"r0": "R0", "r1": "R1", "m": "M", "k": "K", "cleanup": "cleanup"}
REGISTERED_STAGE_DIR = {"e1": "E1", "p": "P", "e2": "E2", "analysis": "analysis", "report": "report", "delete": "delete"}


def record_unhandled(run_dir: Path, args: argparse.Namespace, e: BaseException) -> None:
    """An ordinary error is a recorded ENGINEERING STOP written to ``<run>/<stage>/stops/`` (for the registered stages and workers: ``E2``, where the analysis reads them), with a key the analysis can parse; it is never resolved by a rerun."""
    if args.command == "work-pass":
        stage = getattr(args, "stage", None) or "E2"
    elif args.command == "registered":
        stage = REGISTERED_STAGE_DIR[args.stage]  # each registered stage's own folder: only E2's stops are read by the E2 analysis
    else:
        stage = STAGE_OF.get(args.command)
    if stage is None:
        return  # pre-freeze commands (candidate-plan, freeze, proposals, seed-gate) write no stop record in the registered run directory
    rec = {**core.envelope("engineering_stop"), "id": f"{stage}|{stage}|r0|unhandled|{type(e).__name__}", "stage": stage, "key": f"{stage}|r0|unhandled", "cause": type(e).__name__, "detail": str(e)[:500], "command": args.command, "utc": core.utc_stamp(), "resolved": False}
    with contextlib.suppress(OSError, ValueError):
        core.write_record(run_dir / stage / "stops" / f"unhandled_{core.utc_stamp()}.json", rec)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "r0":
            return cmd_r0(args)
        if args.command == "r1":
            return cmd_r1(args)
        if args.command == "m":
            return cmd_m(args)
        if args.command == "k":
            return cmd_k(args)
        if args.command == "registered":
            return REGISTERED[args.stage](args)
        if args.command == "work-pass":
            return work_pass(args)
        if args.command == "cleanup":
            return cmd_cleanup(args)
        return freeze.dispatch(args)
    except core.IdentityRefused as e:
        print(f"{core.PAUSED_IDENTITY}: {e}", file=sys.stderr)
        return core.IDENTITY_EXIT
    except StageRefused as e:
        print(str(e), file=sys.stderr)
        return core.IDENTITY_EXIT if args.command == "work-pass" else 2
    except (Paused, core.LedgerRefused) as e:
        print(f"PAUSED: {e}", file=sys.stderr)
        return core.PAUSED_EXIT
    except EngineeringStop as e:
        print(str(e), file=sys.stderr)
        return core.ENGINEERING_STOP_EXIT
    except analysis.AnalysisRefused as e:
        print(f"ANALYSIS REFUSED: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - an ordinary error is a recorded engineering stop, not a traceback
        rd = getattr(args, "run_dir", None)
        if rd:
            record_unhandled(Path(rd), args, e)
        print(f"ENGINEERING STOP ({type(e).__name__}): {e}", file=sys.stderr)
        return core.ENGINEERING_STOP_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
