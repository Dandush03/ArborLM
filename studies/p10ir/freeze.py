# ruff: noqa: E501
"""P10IR freeze commands (ADR-0029 section 13): ``generate-bridge`` (the bridge draws' manifests; generating a draw is not an observation of a seed by a model), ``freeze`` (writes ``freeze/freeze_record.json`` for the committed candidate plan; ``candidate-plan`` writes ``freeze/plan.json`` first),
``caps-proposal`` (prints the cap section 12 proposes from the rehearsal's ledger; nothing writes the config), ``rehearse`` (``rehearsal.py``).

``freeze`` refuses unless: the candidate plan exists; the caps are not provisional (the human lead sets them from the rehearsal); the rehearsal record shows every stage COMPLETE and gates 1 and 2 passed on the
registered checkpoints (gate 3 not run: the seal); the seed gate (gate 6) passes with the registry's checker; the attestations of section 4 are given or the seal is declared broken; P10-S1's data manifests, its
train manifest and the bridge manifests exist (they are in the plan), and the rehearsal record's candidate section names the SHA-256 of the committed plan file. It writes only the freeze record. The freeze commit is the human lead's act.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import core, gates, items, sealed
from . import plan as planmod
from .plan import StageRefused

S1_TRAIN_MANIFEST = "results/p10s1-run-2026-11-17/manifests/train.manifest.json"
S1_RUN_NAME = "P10S1-registered-attempt2-20261117"


def add_commands(sub: Any) -> None:
    g = sub.add_parser("generate-bridge", help="write the bridge draws' manifests (before the freeze)")
    g.add_argument("--run-dir", required=True)
    g.add_argument("--repo")
    cp = sub.add_parser("candidate-plan", help="write the candidate freeze/plan.json once (the rehearsal runs against it)")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--s1-run-dir", required=True)
    cp.add_argument("--seal-broken", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze", help="write freeze/freeze_record.json for the committed candidate plan")
    f.add_argument("--rehearsal", required=True, help="the rehearsal record (rehearsal.json) whose candidate section names the plan file's SHA-256")
    f.add_argument("--attest-sealed-unopened", default="", help="comma list of who states that no sealed value was opened: lead,implementer,auditor (recorded, not verified)")
    f.add_argument("--seal-broken", action="store_true", help="declare the seal broken: CONTENT labels then carry RECALL SEEN BEFORE FREEZE")
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal", help="print the cap section 12 proposes: charged + 2 x projected remaining")
    c.add_argument("--charged-hours", type=float, required=True)
    c.add_argument("--projected-remaining-hours", type=float, required=True)
    r = sub.add_parser("rehearse", help="every stage end to end against a plan of its own (synthetic; real-size cells; gates 1 and 2 on the registered checkpoints)")
    r.add_argument("--run-dir", required=True, help="a new rehearsal directory")
    r.add_argument("--phases", default="candidate,synthetic,real,gates12", help="comma list of: candidate, synthetic, real, gates12")
    r.add_argument("--candidate-plan", help="the candidate plan to rehearse (default: freeze/plan.json)")
    r.add_argument("--s1-run-dir", help="P10-S1's run directory (gates12 only)")
    r.add_argument("--draws", type=int, default=5)
    r.add_argument("--workers", type=int, default=6)
    r.add_argument("--repo")


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "generate-bridge":
        return cmd_generate_bridge(args)
    if args.command == "candidate-plan":
        return cmd_candidate_plan(args)
    if args.command == "freeze":
        return cmd_freeze(args)
    if args.command == "caps-proposal":
        print(json.dumps({"proposed_cap_hours": core.propose_cap_hours(args.charged_hours, args.projected_remaining_hours), "rule": "section 12: charged + 2 x projected remaining; the human lead sets it in the config and clears caps.provisional"}))
        return 0
    from . import rehearsal

    return rehearsal.cmd_rehearse(args)


def experiments_root() -> Path:
    from studies.p9 import core as p9core

    return Path(p9core.default_experiments_root())


def bridge_manifest_path(run_dir: Path, name: str) -> Path:
    return run_dir / "A2" / "draws" / name / "data_manifest.json"


def cmd_generate_bridge(args: argparse.Namespace) -> int:
    """The five bridge draws (complete P10-S1-style draws, section 5), hashed: nothing is trained or read on them."""
    from studies.p10s1 import core as s1

    cfg = core.load_config()
    run_dir = Path(args.run_dir)
    ctx = items.Ctx("generation", run_dir, None, experiments_root())
    for d in range(1, int(cfg["seeds"]["bridge_draws"]) + 1):
        seeds = core.bridge_seeds(d, cfg)
        path = bridge_manifest_path(run_dir, seeds.name)
        if path.exists():
            raise StageRefused(f"refused: {path} exists; a draw is generated once")
        began = time.monotonic()
        data, _ = items.load_data(ctx, {"seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": s1.FACT_TABLE, "unseen": s1.UNSEEN_FACTS}, verify=False)
        core.write_record(path, {**core.envelope("bridge_manifest"), "seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": s1.FACT_TABLE, "unseen": s1.UNSEEN_FACTS, "sha256s": data.sha256s(), "seed_values": sorted(core.seed_set_values(seeds)), "seconds": time.monotonic() - began})
        print(json.dumps({"draw": seeds.name, "manifest": str(path), "sha256": file_sha256(path)}))
    return 0


def bridge_cell_entries(cfg: Any, items_a2: list[dict[str, Any]], s1_plan: Any) -> dict[str, dict[str, Any]]:
    """The planned bridge cells (arm, sizes, seeds, run length, and P10-S1's snapshot schedule for the same arm, facts and slots, from P10-S1's frozen plan)."""
    from studies.p10s1 import core as s1

    out: dict[str, dict[str, Any]] = {}
    for it in items_a2:
        label = it["cell"]
        if label in out:
            continue
        cell = s1.make_cell("P", it["arm"], it["facts"], it["slots"], it["draw"], it["init_seed"], u_p=it["u_p"], run_updates=it["run"])
        out[label] = {
            "arm": it["arm"], "facts": it["facts"], "slots": it["slots"], "draw": it["draw"], "init_seed": it["init_seed"], "u_p": it["u_p"], "run": it["run"], "seed_name": it["seed_name"], "seed_base": it["seed_base"],
            "table_facts": it["table_facts"], "unseen": it["unseen"], "snapshots": list(s1_plan.snapshots(cell)),
        }  # fmt: skip
    return out


def build_candidate(repo: Path, run_dir: Path, s1_run_dir: Path, cfg: Any) -> dict[str, Any]:
    """The registered plan record (a pure function of the repository, the config and the two run directories): items (A1 280, A2 40), the planned bridge cells with P10-S1's snapshot schedule, the digests of
    every A1 checkpoint, the hashes of P10-S1's data manifests, train manifest and frozen plan and of the bridge manifests, the plateau lists and the D-OQ context. It carries no rehearsal and no
    attestation: those belong to the freeze record."""
    from studies.p10s1 import core as s1
    from studies.p10s1 import frozen as s1frozen

    itemset = planmod.registered_items(cfg)
    s1_plan_file = repo / core.P10S1_PLAN
    s1_plan_json = read_json(s1_plan_file)
    s1_plan = s1frozen.Frozen.from_json(s1_plan_json["frozen"])
    digests: dict[str, str] = {}
    for it in itemset[core.STAGE_A1]:
        model = s1_run_dir / "cells" / it["cell"] / "snapshots" / s1.snapshot_stem(it["update"]) / "model.pt"
        if not model.is_file():
            raise StageRefused(f"refused: {model} does not exist")
        digests[f"{it['cell']}|{it['update']}"] = file_sha256(model)
    draw_manifests: dict[str, dict[str, Any]] = {}
    for d in range(1, 6):
        name = s1.registered_draw_seeds(d).name
        p = s1_run_dir / "draws" / name / "data_manifest.json"
        draw_manifests[name] = {"path": str(p), "sha256": _require(p), "groups": [core.STAGE_A1]}
    for d in range(1, int(cfg["seeds"]["bridge_draws"]) + 1):
        name = core.bridge_seeds(d, cfg).name
        p = bridge_manifest_path(run_dir, name)
        draw_manifests[name] = {"path": str(p), "sha256": _require(p), "groups": [core.STAGE_A2]}
    manifests = {**draw_manifests, "p10s1_train_manifest": {"path": S1_TRAIN_MANIFEST, "sha256": _require(repo / S1_TRAIN_MANIFEST)}, "p10s1_frozen_plan": {"path": str(core.P10S1_PLAN), "sha256": _require(s1_plan_file)}}
    plateau: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for spec in core.primary_cells(cfg):
        plateau[spec.name] = {}
        for key, arm in (("tree", "T-OQ"), ("flat", "F-OQ")):
            rows = []
            for d in range(1, 6):
                label = core.s1_label(arm, spec.facts, spec.slots, d, spec.u_p, spec.run, cfg)
                rows.append({"label": label, "updates": [u for u in sealed.available_updates(s1_run_dir, label) if u <= spec.run]})
            plateau[spec.name][key] = rows
    dense = []
    cells = s1.registered_cells(s1_plan.plan, dense_rates=s1_plan.dense_rates)
    for spec in core.cell_specs(cfg):
        if (spec.facts, spec.slots) in s1.DOQ_CELLS:
            labels = [c.label for c in cells if c.arm == "D-OQ" and (c.facts, c.slots) == (spec.facts, spec.slots) and c.kind == "P"]
            for cp, update in (("U_P", spec.u_p), ("RUN", spec.run)):
                dense.append({"cell_name": spec.name, "checkpoint": cp, "update": update, "labels": labels})
    return planmod.build_plan(
        mode=planmod.REGISTERED, cfg=cfg, repo=repo, items=itemset, run_dir=run_dir, s1_run_dir=s1_run_dir,
        extra={
            "bridge_cells": bridge_cell_entries(cfg, itemset[core.STAGE_A2], s1_plan), "checkpoint_digests": digests, "manifests": manifests, "draw_manifests": draw_manifests, "plateau": plateau, "context": {"dense": dense},
            "p10s1_train_manifest": manifests["p10s1_train_manifest"], "p10s1_frozen_data_manifests": s1_plan_json["data_manifests"], "sizes": {"table_facts": s1.FACT_TABLE, "unseen": s1.UNSEEN_FACTS}, "synthetic": False,
            "seal": {"accesses_declared": planmod.SEAL_ACCESSES_DECLARED, "values_opened": False, "broken": False}, "p10s1_run_dir_name": S1_RUN_NAME,
        },
    )  # fmt: skip


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    """Write the CANDIDATE ``freeze/plan.json`` (ruling 5: the plan comes first; the rehearsal runs against this very file and records its SHA-256; ``freeze`` refuses unless the committed file has that hash).
    Written once; the caps may still be provisional (the plan then says so and ``freeze`` refuses it); the seal flag is the plan's own and is set by ``--seal-broken``."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    if plan_path.exists():
        raise StageRefused(f"refused: {plan_path} exists; a plan is written once")
    record = build_candidate(repo, Path(args.run_dir).resolve(), Path(args.s1_run_dir).resolve(), cfg)
    if args.seal_broken:
        record["seal"] = {**record["seal"], "broken": True}
    core.write_record(plan_path, record)
    print(json.dumps({"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "items": {k: len(v) for k, v in record["items"].items()}, "caps_provisional": record["caps_provisional"]}))
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    """Write ``freeze/freeze_record.json`` for the committed candidate plan. Refuses unless: the plan exists and its caps are not provisional (the human lead sets them), the rehearsal record shows every stage COMPLETE,
    gates 1 and 2 passed on the registered checkpoints and (ruling 5) a candidate section naming the SHA-256 of THIS plan file; the seed gate passes; the attestations of section 4 are given (or the seal is
    declared broken). It never rewrites the plan."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    record_path = repo / planmod.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    if not plan_path.is_file():
        raise StageRefused("refused: no candidate plan: write it first (candidate-plan), rehearse against it, then freeze")
    plan = planmod.Plan.load(plan_path)
    if core.caps_provisional(cfg) or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the human lead sets the caps from the rehearsal (section 12) and clears it, and the candidate plan is rewritten and rehearsed again")
    plan_sha = file_sha256(plan_path)
    rehearsal_path = Path(args.rehearsal)
    rehearsal = core.read_record(rehearsal_path, "rehearsal")
    reh = gates.rehearsal_gate(rehearsal, planmod_rehearsal_stages(), plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the rehearsal record does not show every stage COMPLETE, gates 1 and 2 passed on the registered checkpoints and the candidate plan of SHA-256 {plan_sha} rehearsed: {reh}")
    attest = [x for x in args.attest_sealed_unopened.split(",") if x]
    if not args.seal_broken and set(attest) != {"lead", "implementer", "auditor"}:
        raise StageRefused("refused: the freeze record must state, for the lead, the implementer and the auditor, that none has opened the sealed values (--attest-sealed-unopened lead,implementer,auditor), or declare the seal broken (--seal-broken)")
    if args.seal_broken != bool(plan.data.get("seal", {}).get("broken")):
        raise StageRefused("refused: --seal-broken differs from the candidate plan's seal flag")
    seed = gates.seed_gate(cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: the seed gate (gate 6) did not pass: {seed['problems']}")
    rec = {
        **core.envelope("freeze_plan"), "kind": "freeze_record", "plan_file_sha256": plan_sha, "rehearsal": {"path": str(rehearsal_path.resolve()), "sha256": file_sha256(rehearsal_path)},
        "attestations": {"sealed_values_unopened_by": attest, "recorded_by": "the freeze command from the lead's flags; not verified by code"}, "seal_broken": bool(args.seal_broken),
        "seed_gate": {k: seed[k] for k in ("passed", "roles", "declared_reuse_not_new", "checker")}, "rehearsal_gate": reh,
    }  # fmt: skip
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, rec)
    print(json.dumps({"freeze_record": str(record_path), "sha256": file_sha256(record_path), "plan_file_sha256": plan_sha}))
    return 0


def _require(path: Path) -> str:
    if not path.is_file():
        raise StageRefused(f"refused: {path} does not exist")
    return file_sha256(path)


def planmod_rehearsal_stages() -> tuple[str, ...]:
    from .stages import REHEARSAL_STAGES

    return REHEARSAL_STAGES
