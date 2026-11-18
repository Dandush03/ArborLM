# ruff: noqa: E501
"""Part Q freeze commands (ADR-0025 sections 10, 11 item 2, 11 item 5): ``candidate-plan``, ``caps-proposal`` and ``freeze``.

``freeze`` writes ``freeze/partq_freeze_record.json`` for the committed candidate plan and REFUSES unless: the candidate plan exists; the caps are not provisional and equal what the code proposes from the
measuring rehearsal's record (section 10 item 3); the plan equals a re-derivation from the current code and config (the ADR's hash is not compared); the import walk, re-run now, reaches only files the plan lists;
the counting rehearsal's record was made on caps that are not provisional, names the SHA-256 of THIS plan file, shows every stage COMPLETE with one forced pause and resume and one forced PAUSED — IDENTITY
and restore; the measuring rehearsal on provisional caps is not accepted as the counting record; gate G9 passes; the shared panel ledger exists and its own check passed; the delegation record's section 7 is
on this branch (the condition of section 13 item 6 for the packages); the attestations that no sealed value was opened are given (or the seal is declared broken). It writes only the freeze record; the
freeze commit and Decision 2 are the lead's acts.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from ..common import core, gates
from ..common import plan as planmod
from ..common.core import StageRefused
from . import pkgmanifest
from . import plan as qplan

DELEGATION_SECTION_7_MARKER = "## 7"


def add_commands(sub: Any) -> None:
    cp = sub.add_parser("candidate-plan", help="write the candidate freeze/partq_plan.json once")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--inputs", required=True, help="a JSON file naming every input with its path and SHA-256")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze", help="write freeze/partq_freeze_record.json for the committed candidate plan")
    f.add_argument("--measuring-rehearsal", required=True)
    f.add_argument("--counting-rehearsal", required=True)
    f.add_argument("--attest-sealed-unopened", default="", help="comma list: lead,implementer,auditor (recorded, not verified)")
    f.add_argument("--seal-broken", action="store_true")
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal", help="print the caps by code: 2 x projected per stage; total = charge before the freeze + 2 x all stages")
    c.add_argument("--measuring-rehearsal", required=True)
    c.add_argument("--charged-hours", type=float, required=True)
    c.add_argument("--units", required=True, help="a JSON file: stage -> units (the plan's counts: whole pools generated, whole reserve drawn)")


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    inputs = read_json(Path(args.inputs))
    walk = planmod.import_walk(repo, "Q")
    rec = qplan.build_candidate(repo, Path(args.run_dir).resolve(), cfg, inputs=inputs, walk=walk)
    path = qplan.write_candidate(repo, rec, supersede=args.supersede)
    print(json.dumps({"candidate_plan": str(path), "plan_file_sha256": file_sha256(path), "items": {k: len(v) for k, v in rec["items"].items()}, "caps_provisional": rec["caps_provisional"]}))
    return 0


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps are computed from a MEASURING rehearsal's record")
    rates = {k: float(v) for k, v in (meas.get("rates_seconds_per_unit") or {}).items()}
    units = {k: float(v) for k, v in read_json(Path(args.units)).items()}
    proj = qplan.project_stage_seconds(units, rates)
    print(json.dumps({"projected_seconds": proj, "proposal_hours": qplan.caps_proposal(args.charged_hours * 3600.0, proj), "rule": "stage cap = 2 x projected; total = charge before the freeze + 2 x all stages (section 10 item 3)"}))
    return 0


def delegation_section7_present(repo: Path, cfg: Any) -> bool:
    """No package outside the lock is put on any process's path before section 7 of the delegation record is on the branch the study runs from (section 13 item 6)."""
    p = repo / cfg["paths"]["delegation_record"]
    return p.is_file() and any(line.startswith(DELEGATION_SECTION_7_MARKER) for line in p.read_text(encoding="utf-8").splitlines())


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    plan_path = repo / core.PLAN_Q
    record = repo / core.FREEZE_RECORD_Q
    if record.exists():
        raise StageRefused(f"refused: {record} exists; a freeze is written once")
    plan = planmod.Plan.load(plan_path, "Q")
    if cfg["caps"]["provisional"] or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the caps are computed by code from the measuring rehearsal and set before the freeze; the candidate plan is then rewritten and rehearsed again")
    plan_sha = file_sha256(plan_path)
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring" or meas.get("caps_provisional") is not True:
        raise StageRefused("refused: --measuring-rehearsal must be the measuring rehearsal's record (made on its fixed cap)")
    rates = {k: float(v) for k, v in (meas.get("rates_seconds_per_unit") or {}).items()}
    units = {k: float(v) for k, v in (meas.get("projection_units") or {}).items()}
    proposal = qplan.caps_proposal(float(meas.get("charged_before_freeze_seconds", 0.0)), qplan.project_stage_seconds(units, rates))
    differ = qplan.caps_match_config(cfg, proposal)
    if differ:
        raise StageRefused("refused: the config's stage caps are not what the code computes from the measuring rehearsal: " + "; ".join(differ))
    walk = planmod.import_walk(repo, "Q")
    inputs = plan.data["inputs"]
    rederived = qplan.build_candidate(repo, Path(plan.data["run_dir"]), cfg, inputs=inputs, mode=plan.data["mode"], walk=walk, test_mode=True)  # the ledger is required (and read) just below
    if qplan.scientific_content(json.loads(json.dumps(core.jsonable(rederived)))) != qplan.scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and inputs: supersede it and rehearse again")
    listed = {k: v for k, v in plan.data["frozen_files"].items()}
    wp = planmod.walk_problems(walk, listed, repo)
    if wp:
        raise StageRefused("refused: " + "; ".join(wp))
    pkgmanifest.require_package_manifest(plan.data["inputs"])  # R7: the plan names the installed-package manifest (names, versions, file hashes, the shadowed lock packages)
    counting = core.read_record(Path(args.counting_rehearsal), "rehearsal")
    reh = gates.rehearsal_gate(counting, qplan.REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the counting rehearsal's record does not show every stage COMPLETE, one forced pause and resume, one forced PAUSED — IDENTITY and restore, and this plan file's SHA-256: {reh}")
    attest = [x for x in args.attest_sealed_unopened.split(",") if x]
    if not args.seal_broken and set(attest) != {"lead", "implementer", "auditor"}:
        raise StageRefused("refused: the record must state, for the lead, the implementer and the auditor, that none has opened a sealed value (--attest-sealed-unopened lead,implementer,auditor), or declare the seal broken (--seal-broken)")
    seed = gates.seed_gate("Q", cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: gate G9 did not pass: {seed['problems']}")
    ledger = plan.data.get("manifests", {}).get("panel_ledger")
    if not ledger or not (repo / ledger["path"]).is_file():
        raise StageRefused("refused: the shared panel ledger is not in the plan's manifests or not on disk")
    led = read_json(repo / ledger["path"] if not Path(ledger["path"]).is_absolute() else Path(ledger["path"]))
    chk = (led.get("p10is2") or {}).get("check") or {}
    if led.get("format") != "p10i-panel-ledger-v1" or not chk.get("ok"):
        raise StageRefused(f"refused: the panel ledger is not in the shared format or its own check did not pass: {chk}")
    if not delegation_section7_present(repo, cfg):
        raise StageRefused("refused: section 7 of the delegation record is not on this branch (section 13 item 6): no package outside the lock may be used before it is")
    rec = {
        **core.envelope("freeze_record", "Q"), "plan_file_sha256": plan_sha, "measuring_rehearsal": {"path": str(Path(args.measuring_rehearsal).resolve()), "sha256": file_sha256(Path(args.measuring_rehearsal))},
        "counting_rehearsal": {"path": str(Path(args.counting_rehearsal).resolve()), "sha256": file_sha256(Path(args.counting_rehearsal))}, "attestations": {"sealed_values_unopened_by": attest, "recorded_by": "the freeze command from the flags; not verified by code"},
        "seal_broken": bool(args.seal_broken), "seed_gate": seed, "rehearsal_gate": reh, "caps_by_code": proposal, "adr_hash_provenance_only": plan.data["adr"]["sha256"],
    }  # fmt: skip
    record.parent.mkdir(parents=True, exist_ok=True)
    write_json(record, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record), "sha256": file_sha256(record), "plan_file_sha256": plan_sha}))
    return 0


def dispatch(args: argparse.Namespace) -> int:
    return {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal}[args.command](args)
