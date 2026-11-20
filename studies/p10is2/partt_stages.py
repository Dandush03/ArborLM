# ruff: noqa: E501
"""Part T command line and freeze (ADR-0025 sections 10, 11, 19): ``candidate-plan``, ``caps-proposal``, ``freeze`` and the registered entry points ``registered`` and ``work``.

A registered entry point REFUSES unless the tree is clean, the freeze commit is an ancestor of HEAD and the Part T frozen files equal their content there, the frozen plan and its freeze record exist and agree,
every identity in the plan holds, a COMMITTED Decision 2 for Part T (results/p10is2-partt-freeze-*/DECISION_2_PARTT.md) names the freeze commit, and the run directory is git-ignored or outside the repository.
Nothing is frozen today, so every registered path refuses. Exit codes: 0 done; 2 refused; 75 PAUSED — IDENTITY; 3 returned to the lead (a piece of the scientific core that is not implemented here).

``freeze`` writes only ``freeze/partt_freeze_record.json`` and REFUSES unless: caps not provisional and equal to what the code computes from the Part T measuring rehearsal; the plan equals a re-derivation
from the current code and config; the import walk reaches only listed files; the counting rehearsal names this plan file's SHA-256 and shows every stage COMPLETE, one forced pause and resume and one forced
PAUSED — IDENTITY and restore; the calibration records are not stand-ins, not SUPERSEDED and carry the frozen files' hashes (the repetition used is the one whose hashes equal them, never chosen on its values);
the pilot passed; the Part Q manifest and its ACCEPTANCE record are listed by hash; the shared panel ledger is listed by hash; gate G9 passes; the attestations are given.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import calibration as cal
from . import partt_plan
from .common import core, gates
from .common import plan as planmod
from .common.caps import caps_match_config, caps_proposal, project_stage_seconds
from .common.core import PendingLeadReview, StageRefused

EXIT_REFUSED, EXIT_IDENTITY, EXIT_LEAD, EXIT_INCOMPLETE, EXIT_RECOMPUTATION = 2, planmod.IDENTITY_EXIT, 3, 4, 5  # 4: the stage did not complete (PAUSED or a task failed): see its manifest
REGISTERED_STAGES = partt_plan.STAGES
NOT_IMPLEMENTED = (
    "the arms' training loops over the P10-S2 student, store and LoRA modules (M1, M-append, M-seq, M-ii, D1, D-append, D-seq, M-joint, D-joint, E-table) with the seeded draws of Part Q's manifest",
    "scoring of every snapshot on CPU and the recomputation", "the permutation, marker-only and words-only controls", "the keyword router, GEN readings and route accuracy", "the lookup baselines wired to the Part Q bank (R-gloss-icl through stored segments)",
    "the combined tasks C1 and C2", "the five cost measures' recording", "the Part T gates G1-G8 on real data", "the Part T rehearsals and calibration runs on MPS",
)  # fmt: skip
REHEARSAL_STAGES = partt_plan.STAGES


def repo_of(args: argparse.Namespace | None = None) -> Path:
    r = getattr(args, "repo", None) if args is not None else None
    return Path(r) if r else core.ROOT


def refuse_unless_registered_ready(repo: Path, run_dir: Path, freeze_commit: str | None, stage: str) -> planmod.Plan:
    if stage not in REGISTERED_STAGES:
        raise StageRefused(f"refused: {stage!r} is not a registered Part T stage")
    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)  # configured BEFORE the platform check (see the Part Q entry point)
    planmod.check_preconditions("T", planmod.REGISTERED, repo, freeze_commit, cfg)
    plan = planmod.load_registered_plan(repo, "T")
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, str(freeze_commit), "T")
    core.require_ignored_run_dir(repo, run_dir)
    problems = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and os.path.realpath(p) == os.path.realpath(core.DURABLE_PACKAGES)]  # normalized: a trailing slash or a symlink does not slip through
    if problems:
        raise StageRefused("refused: Part T uses the lock alone (section 13 item 6): the durable package copy is on this process's PYTHONPATH")
    return plan


def cmd_registered(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, args.stage)
    from . import partt_real, partt_tasks

    cfg = core.load_config("T", repo / core.CONFIG_T)
    if args.stage in partt_tasks.TASK_STAGES:
        man = partt_tasks.run_stage_tasks(args.stage, plan, cfg, repo, Path(args.run_dir), str(args.freeze_commit), Path(args.part_q_dir))
        print(json.dumps({"stage": args.stage, "status": man["status"], "charged_seconds": man["charged_seconds"]}))
        return 0 if man["status"] == "COMPLETE" else EXIT_INCOMPLETE
    partt_real.run_stage(args.stage, repo, Path(args.run_dir), Path(args.part_q_dir), plan)
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    """One worker: it re-checks everything the entry point checks (an identity difference exits 75 and writes nothing), then runs its one task."""
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, args.stage)
    from . import partt_real

    partt_real.run_task(args.stage, args.task_id, repo, Path(args.run_dir), Path(args.part_q_dir), plan)
    return 0


def cmd_recompute(args: argparse.Namespace) -> int:
    """The independent recomputation (stage 8): re-score every snapshot on CPU. Exit 0 if it agrees; 5 on ENGINEERING STOP — RECOMPUTATION (nothing is labelled)."""
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real

    out = partt_real.run_recompute(repo, Path(args.run_dir), Path(args.part_q_dir), plan, own_code=bool(args.own_code))
    print(json.dumps(out))
    return 0 if out["ok"] else EXIT_RECOMPUTATION


def cmd_timing(args: argparse.Namespace) -> int:
    """Stage 7, the timing benchmark: it runs ALONE (no other process of any study alive), one attempt per invocation; the quiet condition is read before each repetition. Exit 0 if measured, 4 if the attempt
    was incomplete (reschedule it)."""
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real, partt_timing

    cfg = core.load_config("T", repo / core.CONFIG_T)
    w, _gloss, _ = partt_real.build_world_real(repo, cfg, Path(args.part_q_dir), plan.data["calibration"], "registered")
    t0 = time.monotonic()
    rec = partt_timing.run_stage(cfg, Path(args.run_dir) / "timing", partt_timing.make_repetition(w, Path(args.run_dir) / "snapshots"))
    core.Ledger(Path(args.run_dir) / "charged_ledger.json", "T", max(1.0, float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0) or 1e12).charge_process("timing", "registered", "main", time.monotonic() - t0)
    print(json.dumps(core.jsonable({k: v for k, v in rec.items() if k != "record"}), default=str))
    return 0 if rec["status"] in ("MEASURED", "NOT MEASURED") else EXIT_INCOMPLETE


def cmd_cost(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real

    print(json.dumps(partt_real.run_cost(repo, Path(args.run_dir), Path(args.part_q_dir), plan)))
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    from . import partt_tasks

    print(json.dumps(partt_tasks.retry(Path(args.run_dir), args.stage, args.task_id, args.cause, bool(args.fix_changes_frozen_file))))
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from . import partt_real

    core.require_ignored_run_dir(repo_of(args), Path(args.run_dir))
    print(json.dumps(core.jsonable(partt_real.calibrate_command(repo_of(args), Path(args.part_q_dir), Path(args.run_dir), int(args.repetition))), default=str))
    return 0


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The Part T rehearsals on Part Q's accepted outputs with the rehearsal seeds (252001, 330251 + j) and D_cal only; scores are sealed."""
    from . import partt_real

    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    core.require_ignored_run_dir(repo, Path(args.run_dir))
    if not Path(args.calibration).is_file() or not (Path(args.part_q_dir) / "outputs/bundle").exists():
        raise StageRefused("refused: the rehearsal needs --calibration (the calibration record) and --part-q-dir (Part Q's accepted run directory)")
    calib = json.loads(Path(args.calibration).read_text())
    w, gloss, _ = partt_real.build_world_real(repo, cfg, Path(args.part_q_dir), calib, "rehearsal")
    run_dir = Path(args.run_dir)
    if args.kind == "measuring":
        rec = partt_real.measure_rates(w, run_dir / "snaps", gloss, updates=200)
        out = {**core.envelope("rehearsal", "T"), "kind_of_rehearsal": "measuring", "caps_provisional": True, "cannot_be_frozen_on": True, **rec}
    else:
        plan_file = repo / core.PLAN_T
        plan = planmod.Plan.load(plan_file, "T")
        out = partt_real.counting_rehearsal(w, run_dir / "snaps", gloss, plan_file_sha256=file_sha256(plan_file), caps_provisional=bool(plan.data.get("caps_provisional", True)), updates=int(calib["U"]), identity_probe=identity_probe(plan, repo, run_dir), require_mps=True)
    core.write_record(run_dir / f"rehearsal_{args.kind}.json", out, overwrite=True)
    print(json.dumps({k: out[k] for k in ("kind_of_rehearsal", "rates_seconds_per_unit", "projection_units", "forced") if k in out}, default=str))
    return 0


def identity_probe(plan: planmod.Plan, repo: Path, run_dir: Path) -> Any:
    """The forced PAUSED — IDENTITY of the counting rehearsal: a copy of the plan with one frozen hash altered is refused as PAUSED — IDENTITY, the real plan then verifies (the restore), and the probe raises."""

    def probe() -> None:
        data = json.loads(json.dumps(plan.data))
        data["frozen_files"][sorted(data["frozen_files"])[0]] = "0" * 64
        try:
            planmod.verify_plan(planmod.Plan(data, "T"), repo, Path(plan.data["run_dir"]), candidate=True)
        except StageRefused as e:
            if "PAUSED — IDENTITY" not in str(e):
                raise
        else:
            raise RuntimeError("the forced identity difference was not detected")
        planmod.verify_plan(plan, repo, Path(plan.data["run_dir"]), candidate=True)
        raise core.ForcedIdentityPause("PAUSED — IDENTITY forced and restored")

    return probe


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    calib = read_json(Path(args.calibration))
    walk = planmod.import_walk(repo, "T")
    rec = partt_plan.build_candidate(repo, Path(args.run_dir).resolve(), cfg, calib, walk=walk, manifests=read_json(Path(args.manifests)))
    path = repo / core.PLAN_T
    if path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD_T).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(path)
        target = path.parent / "superseded" / f"partt_plan-{old[:12]}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        path.rename(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(rec))
    print(json.dumps({"candidate_plan": str(path), "plan_file_sha256": file_sha256(path), "items": {k: len(v) for k, v in rec["items"].items()}}))
    return 0


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps are computed from a MEASURING rehearsal's record")
    proj = project_stage_seconds({k: float(v) for k, v in read_json(Path(args.units)).items()}, {k: float(v) for k, v in meas["rates_seconds_per_unit"].items()})
    print(json.dumps({"projected_seconds": proj, "proposal_hours": caps_proposal(args.charged_hours * 3600.0, proj)}))
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    plan_path, record = repo / core.PLAN_T, repo / core.FREEZE_RECORD_T
    if record.exists():
        raise StageRefused(f"refused: {record} exists; a freeze is written once")
    plan = planmod.Plan.load(plan_path, "T")
    if cfg["caps"]["provisional"] or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the caps are computed by code from the Part T measuring rehearsal and set before the freeze")
    plan_sha = file_sha256(plan_path)
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring" or meas.get("caps_provisional") is not True:
        raise StageRefused("refused: --measuring-rehearsal must be the Part T measuring rehearsal's record")
    proposal = caps_proposal(float(meas.get("charged_before_freeze_seconds", 0.0)), project_stage_seconds({k: float(v) for k, v in meas["projection_units"].items()}, {k: float(v) for k, v in meas["rates_seconds_per_unit"].items()}))
    differ = caps_match_config(cfg, proposal)
    if differ:
        raise StageRefused("refused: the config's stage caps are not what the code computes from the measuring rehearsal: " + "; ".join(differ))
    walk = planmod.import_walk(repo, "T")
    calib = plan.data["calibration"]
    rederived = partt_plan.build_candidate(repo, Path(plan.data["run_dir"]), cfg, calib, mode=plan.data["mode"], walk=walk, manifests=plan.data.get("manifests"))
    if json.loads(json.dumps(core.jsonable({k: v for k, v in rederived.items() if k not in ("adr", "platform")}))) != {k: v for k, v in plan.data.items() if k not in ("adr", "platform")}:
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and calibration: supersede it, repeat calibration if a training or scoring file changed (section 7.1 rule 4), and rehearse again")
    wp = planmod.walk_problems(walk, plan.data["frozen_files"], repo)
    if wp:
        raise StageRefused("refused: " + "; ".join(wp))
    files = [f for f in plan.data["frozen_files"] if f.startswith("studies/p10is2/") and f.endswith(".py")]
    records = calib.get("records") or {}
    bad = ["the plan carries no calibration records"] if not records else [f"{n}: {p}" for n, rec in records.items() for p in cal.code_identity_problems(rec, plan.data["frozen_files"], files)]
    if bad:
        raise StageRefused("refused: the calibration records do not match the frozen files: " + "; ".join(bad[:4]))
    for name in ("part_q_manifest", "part_q_acceptance", "panel_ledger"):
        m = (plan.data.get("manifests") or {}).get(name)
        p = None if not m else (Path(m["path"]) if Path(m["path"]).is_absolute() else repo / m["path"])
        if p is None or not p.is_file() or file_sha256(p) != m["sha256"]:
            raise StageRefused(f"refused: the plan does not list {name} by a hash that holds (Part T reads the Part Q manifest's files only, by hash: ruling L12)")
    counting = core.read_record(Path(args.counting_rehearsal), "rehearsal")
    reh = gates.rehearsal_gate(counting, REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    mps = counting.get("g4_mps") or {}
    if mps.get("passed") is not True or (counting.get("platform") or {}).get("machine") != gates.platform_record()["machine"] or (counting.get("platform") or {}).get("system") != gates.platform_record()["system"]:
        raise StageRefused(f"refused: gate G4 MPS against CPU must have RUN and PASSED on this machine before the freeze (a skipped gate is not a pass); the counting rehearsal's record has: {mps}")
    if not reh["passed"]:
        raise StageRefused(f"refused: the counting rehearsal's record does not show every stage COMPLETE, one forced pause and resume, one forced PAUSED — IDENTITY and restore, and this plan file's SHA-256: {reh}")
    attest = [x for x in args.attest_sealed_unopened.split(",") if x]
    if not args.seal_broken and set(attest) != {"lead", "implementer", "auditor"}:
        raise StageRefused("refused: the record must state, for the lead, the implementer and the auditor, that none has opened a sealed value, or declare the seal broken")
    seed = gates.seed_gate("T", cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: gate G9 did not pass: {seed['problems']}")
    rec = {
        **core.envelope("freeze_record", "T"), "plan_file_sha256": plan_sha, "counting_rehearsal": {"path": str(Path(args.counting_rehearsal).resolve()), "sha256": file_sha256(Path(args.counting_rehearsal))},
        "attestations": {"sealed_values_unopened_by": attest}, "seal_broken": bool(args.seal_broken), "seed_gate": seed, "rehearsal_gate": reh, "caps_by_code": proposal, "adr_hash_provenance_only": plan.data["adr"]["sha256"],
    }  # fmt: skip
    record.parent.mkdir(parents=True, exist_ok=True)
    write_json(record, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record), "sha256": file_sha256(record), "plan_file_sha256": plan_sha}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is2.partt_stages", description="P10IS2 Part T (ADR-0025). Registered entry points refuse until a freeze record and a committed Decision 2 exist.")
    sub = ap.add_subparsers(dest="command", required=True)
    cp = sub.add_parser("candidate-plan")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--calibration", required=True, help="the calibration outcome (JSON: U, rates, read layer, pilot, records)")
    cp.add_argument("--manifests", required=True, help="JSON naming part_q_manifest, part_q_acceptance, panel_ledger by path and SHA-256")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze")
    f.add_argument("--measuring-rehearsal", required=True)
    f.add_argument("--counting-rehearsal", required=True)
    f.add_argument("--attest-sealed-unopened", default="")
    f.add_argument("--seal-broken", action="store_true")
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal")
    c.add_argument("--measuring-rehearsal", required=True)
    c.add_argument("--charged-hours", type=float, required=True)
    c.add_argument("--units", required=True)
    tk = sub.add_parser("task")
    for a in ("--stage", "--task-id", "--run-dir"):
        tk.add_argument(a, required=True)
    tk.add_argument("--freeze-commit")
    tk.add_argument("--part-q-dir", default=".")
    tk.add_argument("--repo")
    co = sub.add_parser("cost")
    co.add_argument("--run-dir", required=True)
    co.add_argument("--freeze-commit")
    co.add_argument("--part-q-dir", default=".")
    co.add_argument("--repo")
    tm = sub.add_parser("timing")
    tm.add_argument("--run-dir", required=True)
    tm.add_argument("--freeze-commit")
    tm.add_argument("--part-q-dir", default=".")
    tm.add_argument("--repo")
    rc = sub.add_parser("recompute")
    rc.add_argument("--run-dir", required=True)
    rc.add_argument("--freeze-commit")
    rc.add_argument("--part-q-dir", default=".")
    rc.add_argument("--own-code", action="store_true")
    rc.add_argument("--repo")
    rt = sub.add_parser("retry")
    for a in ("--stage", "--task-id", "--run-dir", "--cause"):
        rt.add_argument(a, required=True)
    rt.add_argument("--fix-changes-frozen-file", action="store_true")
    cal = sub.add_parser("calibrate")
    cal.add_argument("--part-q-dir", required=True)
    cal.add_argument("--run-dir", required=True)
    cal.add_argument("--repetition", type=int, default=0, choices=(0, 1))
    cal.add_argument("--repo")
    for name in ("registered", "work"):
        r = sub.add_parser(name)
        r.add_argument("--part-q-dir", required=False, default=".")
        r.add_argument("--stage", required=True)
        r.add_argument("--run-dir", required=True)
        r.add_argument("--freeze-commit")
        r.add_argument("--repo")
    h = sub.add_parser("rehearse")
    h.add_argument("--kind", choices=("measuring", "counting"), required=True)
    h.add_argument("--run-dir", required=True)
    h.add_argument("--part-q-dir", required=False, default=".")
    h.add_argument("--calibration", required=False, default="calibration.json")
    h.add_argument("--repo")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        table: dict[str, Any] = {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal, "registered": cmd_registered, "work": cmd_registered, "rehearse": cmd_rehearse, "calibrate": cmd_calibrate, "task": cmd_task, "retry": cmd_retry, "recompute": cmd_recompute, "timing": cmd_timing, "cost": cmd_cost}
        return int(table[args.command](args))
    except StageRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_IDENTITY if "PAUSED — IDENTITY" in str(e) else EXIT_REFUSED
    except PendingLeadReview as e:
        print(f"PENDING LEAD REVIEW: {e}", file=sys.stderr)
        return EXIT_LEAD


if __name__ == "__main__":
    raise SystemExit(main())
