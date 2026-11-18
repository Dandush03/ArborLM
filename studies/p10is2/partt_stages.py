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

EXIT_REFUSED, EXIT_IDENTITY, EXIT_LEAD = 2, planmod.IDENTITY_EXIT, 3
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
    planmod.check_preconditions("T", planmod.REGISTERED, repo, freeze_commit, cfg)
    plan = planmod.load_registered_plan(repo, "T")
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, str(freeze_commit), "T")
    core.require_ignored_run_dir(repo, run_dir)
    problems = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p == core.DURABLE_PACKAGES]
    if problems:
        raise StageRefused("refused: Part T uses the lock alone (section 13 item 6): the durable package copy is on this process's PYTHONPATH")
    return plan


def cmd_registered(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, args.stage)
    raise PendingLeadReview("the real Part T stage bodies need: " + "; ".join(NOT_IMPLEMENTED) + ". They were not run here (no training, no real data, no MPS work in the implementation).")


def cmd_rehearse(args: argparse.Namespace) -> int:
    raise PendingLeadReview(f"the Part T {args.kind} rehearsal needs Part Q's accepted outputs and: " + "; ".join(NOT_IMPLEMENTED))


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
    for name in ("registered", "work"):
        r = sub.add_parser(name)
        r.add_argument("--stage", required=True)
        r.add_argument("--run-dir", required=True)
        r.add_argument("--freeze-commit")
        r.add_argument("--repo")
    h = sub.add_parser("rehearse")
    h.add_argument("--kind", choices=("measuring", "counting"), required=True)
    h.add_argument("--run-dir", required=True)
    h.add_argument("--repo")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        table: dict[str, Any] = {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal, "registered": cmd_registered, "work": cmd_registered, "rehearse": cmd_rehearse}
        return int(table[args.command](args))
    except StageRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_IDENTITY if "PAUSED — IDENTITY" in str(e) else EXIT_REFUSED
    except PendingLeadReview as e:
        print(f"PENDING LEAD REVIEW: {e}", file=sys.stderr)
        return EXIT_LEAD


if __name__ == "__main__":
    raise SystemExit(main())
