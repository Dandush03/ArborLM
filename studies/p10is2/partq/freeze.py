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
from collections.abc import Mapping
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
    c.add_argument("--charged-hours", type=float, help="default: the measuring record's charged_before_freeze_seconds / 3600, which is what the freeze compares against")
    c.add_argument("--units", help="a JSON file: stage -> units; default: the measuring record's projection_units (what the freeze uses); write one with units-file")
    i = sub.add_parser("inputs-file", help="write the inputs JSON for candidate-plan from the config, the durable data and package copies and the repository (verifies each against its pin)")
    i.add_argument("--out", required=True)
    i.add_argument("--repo")
    u = sub.add_parser("units-file", help="write the units JSON for caps-proposal from the measuring rehearsal's record")
    u.add_argument("--measuring-rehearsal", required=True)
    u.add_argument("--out", required=True)
    k = sub.add_parser("caps-config", help="print (or with --apply write) the stage caps for the config from the measuring record by the caps rule")
    k.add_argument("--measuring-rehearsal", required=True)
    k.add_argument("--apply", action="store_true", help="edit configs/p10is2_partq.toml: the nine cap keys and caps.provisional = false (refuses unless every cap is 0.0 and provisional is true)")
    k.add_argument("--repo")


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
    units = {k: float(v) for k, v in (read_json(Path(args.units)) if args.units else meas.get("projection_units") or {}).items()}
    charged = float(args.charged_hours) * 3600.0 if args.charged_hours is not None else float(meas.get("charged_before_freeze_seconds", 0.0))
    proj = qplan.project_stage_seconds(units, rates)
    print(json.dumps({"projected_seconds": proj, "proposal_hours": qplan.caps_proposal(charged, proj), "charged_before_freeze_seconds": charged, "rule": "stage cap = 2 x projected; total = charge before the freeze + 2 x all stages (section 10 item 3)"}))
    return 0


def proposal_from_record(meas: Mapping[str, Any]) -> dict[str, float]:
    """The caps by the code's rule from a measuring record; refuses a record that lacks a rate for a stage it has units for, or lacks a registered stage."""
    rates = {k: float(v) for k, v in (meas.get("rates_seconds_per_unit") or {}).items()}
    units = {k: float(v) for k, v in (meas.get("projection_units") or {}).items()}
    missing = [s for s in qplan.STAGES if s not in units or s not in rates]
    if missing:
        raise StageRefused(f"refused: the measuring record has no rate or no units for stage(s) {missing}: a stage the registered run has was not measured; run the measuring rehearsal again")
    return dict(qplan.caps_proposal(float(meas.get("charged_before_freeze_seconds", 0.0)), qplan.project_stage_seconds(units, rates)))


def cmd_units_file(args: argparse.Namespace) -> int:
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the units come from a MEASURING rehearsal's record")
    out = Path(args.out)
    if out.exists():
        raise StageRefused(f"refused: {out} exists")
    write_json(out, {k: float(v) for k, v in (meas.get("projection_units") or {}).items()})
    print(json.dumps({"units_file": str(out), "sha256": file_sha256(out)}))
    return 0


def caps_toml(proposal: Mapping[str, float]) -> str:
    return "\n".join(f"{k} = {v}" for k, v in proposal.items())


def apply_caps(text: str, proposal: Mapping[str, float]) -> str:
    """The config text with each ``<key> = 0.0`` of ``[stage_caps]`` replaced by the proposal and ``provisional = true`` by false. Refuses a config whose caps are already set."""
    out = text
    for k, v in proposal.items():
        old = f"\n{k} = 0.0"
        if out.count(old) != 1:
            raise StageRefused(f"refused: the config does not hold exactly one unset line '{k} = 0.0' (caps already entered?)")
        out = out.replace(old, f"\n{k} = {v}")
    if out.count("\nprovisional = true") != 1:
        raise StageRefused("refused: the config does not hold exactly one 'provisional = true'")
    return out.replace("\nprovisional = true", "\nprovisional = false")


def cmd_caps_config(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps come from a MEASURING rehearsal's record")
    proposal = proposal_from_record(meas)
    if args.apply:
        path = repo / core.CONFIG_Q
        path.write_text(apply_caps(path.read_text(encoding="utf-8"), proposal), encoding="utf-8")
        print(json.dumps({"config": str(path), "applied": proposal, "next": "commit the config, then candidate-plan"}))
    else:
        print(caps_toml(proposal))
    return 0


def build_inputs_block(cfg: Mapping[str, Any], repo: Path, downloads: Path, downloads_record: Mapping[str, Any], wikitext_record: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """The plan's ``inputs`` block from records the verifying functions already produced: every model and Tatoeba file with its path and digest, the WikiText-2 files, the requirements file, ADR-0004 (the pin
    source, its working-tree hash) and the installed-package manifest. Each file entry is re-checked at the start of every registered stage (``pkgmanifest.verify_inputs``)."""
    from . import real

    block: dict[str, Any] = {}
    def entry(path: Path, upstream: str) -> dict[str, Any]:
        """The file's REAL SHA-256 (what every stage re-hashes), the upstream checksum kept apart with its kind (P10-S2 pins small model files by git blob SHA-1, 40 hex, and the large ones by SHA-256)."""
        kind = {40: "git-blob-sha1", 64: "sha256"}.get(len(upstream))
        if kind is None:
            raise StageRefused(f"refused: the upstream checksum {upstream!r} of {path} is neither 40 nor 64 hex characters")
        return {"path": str(path), "sha256": file_sha256(path), "upstream_checksum": upstream, "upstream_checksum_kind": kind}

    for name, digest in sorted(downloads_record["models"].items()):
        block[f"download:{name}"] = entry(downloads / name, digest)
    for name, spec in sorted(downloads_record["tatoeba"]["files"].items()):
        block[f"download:{name}"] = entry(downloads / name, spec["sha256"])
    wt_dir = Path(wikitext_record["directory"])
    for name in real.WIKITEXT_FILES:
        block[f"wikitext:{name}"] = entry(wt_dir / name, wikitext_record[name]["sha256"])
    req = repo / cfg["paths"]["packages_requirements"]
    if file_sha256(req) != cfg["paths"]["packages_requirements_sha256"]:
        raise StageRefused("refused: the requirements file is not the one the config pins")
    block["requirements"] = {"path": str(req.relative_to(repo)), "sha256": file_sha256(req)}  # repository files: repo-relative, resolved against the repository the stage runs from
    block["adr_0004"] = {"path": str(real.ADR_0004), "sha256": file_sha256(repo / real.ADR_0004)}
    block[pkgmanifest.KEY] = dict(manifest)
    return block


def cmd_inputs_file(args: argparse.Namespace) -> int:
    import sysconfig

    from studies.p10s2 import datagen

    from . import real, real_stages, real_world

    repo = Path(args.repo) if args.repo else core.ROOT
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    out = Path(args.out)
    if out.exists():
        raise StageRefused(f"refused: {out} exists")
    downloads = real_stages.downloads_dir(cfg)
    dl = datagen.verify_downloads(downloads, repo / real_world.TATOEBA_RECORD, root=repo)  # every model file against its constant, the Tatoeba files against the committed record
    wt = real.check_wikitext(Path(cfg["paths"]["wikitext_dir"]), real.wikitext_pins(repo))  # each parquet file against its ADR-0004 pin
    manifest = pkgmanifest.build_manifest(Path(cfg["paths"]["durable_packages"]), Path(sysconfig.get_paths()["purelib"]))
    block = build_inputs_block(cfg, repo, downloads, dl, wt, manifest)
    write_json(out, block)
    print(json.dumps({"inputs_file": str(out), "sha256": file_sha256(out), "entries": sorted(k for k in block if k != pkgmanifest.KEY), "package_files": manifest["file_count"], "package_tree_sha256": manifest["tree_sha256"], "shadowed_lock_packages": sorted(manifest["shadowed_lock_packages"])}))
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
    try:
        meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    except (ValueError, KeyError, OSError) as e:
        raise StageRefused(f"refused: --measuring-rehearsal {args.measuring_rehearsal} is not a P10IS2 rehearsal record ({type(e).__name__}: {e})") from e
    if meas.get("kind_of_rehearsal") != "measuring" or meas.get("caps_provisional") is not True:
        raise StageRefused("refused: --measuring-rehearsal must be the measuring rehearsal's record (made on its fixed cap)")
    proposal = proposal_from_record(meas)  # refuses a record that did not measure every registered stage
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
    try:
        counting = core.read_record(Path(args.counting_rehearsal), "rehearsal")
    except (ValueError, KeyError, OSError) as e:
        raise StageRefused(f"refused: --counting-rehearsal {args.counting_rehearsal} is not a P10IS2 rehearsal record ({type(e).__name__}: {e})") from e
    reh = gates.rehearsal_gate(counting, qplan.REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the counting rehearsal's record does not show every stage COMPLETE, one forced pause and resume, one forced PAUSED — IDENTITY and restore, and this plan file's SHA-256: {reh}")
    stage_lines = {s: {"seconds": (counting.get("stages", {}).get(s) or {}).get("seconds"), "cap_seconds": plan.cap_seconds(s), "within_cap": (counting.get("stages", {}).get(s) or {}).get("within_cap")} for s in qplan.REHEARSAL_STAGES}
    over = [s for s, v in stage_lines.items() if v["within_cap"] is not True]
    print(json.dumps({"counting_rehearsal_stage_seconds_against_caps": stage_lines}))
    if over:
        raise StageRefused("refused: the counting rehearsal does not show every stage within its cap (within_cap true required); not within: " + ", ".join(f"{s} {stage_lines[s]['seconds']} s of {stage_lines[s]['cap_seconds']} s" for s in over))
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
        "seal_broken": bool(args.seal_broken), "seed_gate": seed, "rehearsal_gate": reh, "counting_stage_seconds_against_caps": stage_lines, "caps_by_code": proposal, "adr_hash_provenance_only": plan.data["adr"]["sha256"],
    }  # fmt: skip
    record.parent.mkdir(parents=True, exist_ok=True)
    write_json(record, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record), "sha256": file_sha256(record), "plan_file_sha256": plan_sha}))
    return 0


def dispatch(args: argparse.Namespace) -> int:
    return {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal, "inputs-file": cmd_inputs_file, "units-file": cmd_units_file, "caps-config": cmd_caps_config}[args.command](args)
