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
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from ..common import core, gates
from ..common import plan as planmod
from ..common.core import StageRefused
from . import pkgmanifest, reuse, reusecheck
from . import plan as qplan

DELEGATION_SECTION_7_MARKER = "## 7"


def add_commands(sub: Any) -> None:
    cp = sub.add_parser("candidate-plan", help="write the candidate freeze/partq_plan.json once")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--inputs", required=True, help="a JSON file naming every input with its path and SHA-256")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--charged-ledger", action="append", default=[], help="every Part Q charged_ledger.json charged so far (absolute paths; the measuring run's, every rehearsal's, every attempt's): their sum is the charge before the freeze the registered cap check counts")
    ru = sub.add_parser("reuse-file", help="add the reuse block (every file of an earlier attempt's six completed stages, hashed as bytes) to a copy of the inputs file")
    ru.add_argument("--source-run-dir", required=True)
    ru.add_argument("--freeze-commit", required=True, help="the full freeze commit under which the reused stages were computed")
    ru.add_argument("--base-inputs", required=True)
    ru.add_argument("--out", required=True)
    ru.add_argument("--mode", choices=("registered", "rehearsal"), default="registered")
    ru.add_argument("--repo")
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
    k.add_argument("--attempt3", action="store_true", help="the caps of a plan that reuses completed stages: reuse, regeneration, outputs, analysis and the total from the charge so far (--charged-ledger, every ledger)")
    k.add_argument("--charged-ledger", action="append", default=[])
    z = sub.add_parser("caps-reset", help="reset the entered caps to unset (a recorded correction of a cost projection before any registered result exists) so that a new measuring record can be applied")
    z.add_argument("--reason", required=True)
    z.add_argument("--repo")


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    inputs = read_json(Path(args.inputs))
    walk = planmod.import_walk(repo, "Q")
    charge = ledgers_charge(args.charged_ledger) if args.charged_ledger else None
    if inputs.get(reuse.KEY) and charge is None:
        raise StageRefused("refused: a plan that reuses completed stages needs --charged-ledger (every ledger charged so far): its caps are computed from that charge")
    rec = qplan.build_candidate(repo, Path(args.run_dir).resolve(), cfg, inputs=inputs, walk=walk, charge_before_freeze=charge)
    path = qplan.write_candidate(repo, rec, supersede=args.supersede)
    print(json.dumps({"candidate_plan": str(path), "plan_file_sha256": file_sha256(path), "items": {k: len(v) for k, v in rec["items"].items()}, "caps_provisional": rec["caps_provisional"]}))
    return 0


def projection_from_record(meas: Mapping[str, Any], *, units: Mapping[str, float] | None = None) -> dict[str, float]:
    """The projected seconds of every registered stage by the ONE formula (``qplan.CAPS_FORMULA``: measured per-process overhead + per-unit rate x units) from a measuring record made through the registered entry
    point. Refuses a record without that formula (made in one process, before the formula: its rates exclude the world build every stage process pays) and a record that lacks a stage."""
    if meas.get("caps_formula") != qplan.CAPS_FORMULA:
        raise StageRefused(f"refused: the measuring record does not carry caps_formula {qplan.CAPS_FORMULA!r}: it was not made through the registered entry point (one fresh process per stage), so its rates exclude the per-process overhead; measure again")
    rates = {k: float(v) for k, v in (meas.get("rates_seconds_per_unit") or {}).items()}
    overhead = {k: float(v) for k, v in (meas.get("overhead_seconds") or {}).items()}
    use = {k: float(v) for k, v in (units if units is not None else meas.get("projection_units") or {}).items()}
    missing = [s for s in qplan.REHEARSAL_STAGES if s not in use or s not in rates or s not in overhead]
    if missing:
        raise StageRefused(f"refused: the measuring record has no rate, overhead or units for stage(s) {missing}: a stage the registered run has was not measured; run the measuring rehearsal again")
    return qplan.project_stage_seconds({s: use[s] for s in qplan.REHEARSAL_STAGES}, rates, overhead)


def proposal_from_record(meas: Mapping[str, Any], *, units: Mapping[str, float] | None = None, charged_seconds: float | None = None) -> dict[str, float]:
    """The caps by the code's rule from a measuring record: each stage cap 2 x its projected seconds, the total the pre-freeze charge plus 2 x all stages (rounded up to 0.01 h). The caps proposal, ``caps-config`` and
    the freeze's comparison all call this function."""
    charge = float(meas.get("charged_before_freeze_seconds", 0.0)) if charged_seconds is None else charged_seconds
    return dict(qplan.caps_proposal(charge, projection_from_record(meas, units=units)))


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps are computed from a MEASURING rehearsal's record")
    units = {k: float(v) for k, v in read_json(Path(args.units)).items()} if args.units else None
    charged = float(args.charged_hours) * 3600.0 if args.charged_hours is not None else float(meas.get("charged_before_freeze_seconds", 0.0))
    proj = projection_from_record(meas, units=units)
    print(json.dumps({"projected_seconds": proj, "proposal_hours": qplan.caps_proposal(charged, proj), "charged_before_freeze_seconds": charged, "rule": "stage projected = measured per-process overhead + per-unit rate x units (whole-process-v2); stage cap = 2 x projected; total = charge before the freeze + 2 x all stages (section 10 item 3)"}))
    return 0


def ledgers_charge(paths: list[str]) -> dict[str, Any]:
    """The charge so far: the sum of every named Part Q ledger (all its stages), each listed. A path that is not absolute or does not exist is refused: nothing is guessed."""
    per: dict[str, float] = {}
    for x in paths:
        pth = Path(x)
        if not pth.is_absolute() or not pth.is_file():
            raise StageRefused(f"refused: --charged-ledger {x} must be the absolute path of an existing charged_ledger.json")
        per[str(pth)] = core.Ledger(pth, "Q", 1e12).charged()
    return {"seconds": sum(per.values()), "ledgers": per}


REMAINING = reuse.ORDER  # the stages attempt 3 runs: the reuse check, the regeneration re-check, outputs, analysis


def proposal_attempt3(meas: Mapping[str, Any], charge_seconds: float) -> dict[str, float]:
    """The caps of a plan that REUSES completed stages (addendum section 4 condition 5), by the same shared function (``qplan.caps_proposal``): each remaining stage cap is 2 x its projected seconds, the total is the
    charge so far (everything: attempts, rehearsals) plus 2 x the projection of the REMAINING stages only. ``regeneration``, ``outputs`` and ``analysis`` come from the measuring record by the whole-process formula;
    ``reuse`` hashes the reused files and builds no world: its projection is the measured per-process overhead of ``inputs`` (which hashes more bytes than the reuse set: the plan's input files), an upper bound."""
    full = projection_from_record(meas)
    hashing = reuse.HASH_PASSES_PER_STAGE * reuse.HASH_PASS_SECONDS  # every remaining stage hashes the reuse set at its start and at its end
    proj = {s: full[s] + hashing for s in ("regeneration", "outputs", "analysis")}
    proj["reuse"] = float((meas.get("overhead_seconds") or {})["inputs"]) + hashing
    return dict(qplan.caps_proposal(charge_seconds, proj))


def cmd_reuse_file(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    out = Path(args.out)
    if out.exists():
        raise StageRefused(f"refused: {out} exists")
    full = core.git(repo, "rev-parse", "--verify", "--quiet", f"{args.freeze_commit}^{{commit}}").stdout.decode().strip()
    if not full or full != args.freeze_commit:
        raise StageRefused("refused: --freeze-commit must be the FULL commit of this repository")
    block = reuse.build_block(Path(args.source_run_dir), full, args.mode)  # the files are only read, as bytes
    write_json(out, {**read_json(Path(args.base_inputs)), reuse.KEY: block})
    print(json.dumps({"inputs_file": str(out), "sha256": file_sha256(out), "reuse_file_count": block["file_count"], "reuse_tree_sha256": block["tree_sha256"], "freeze_commit": full}))
    return 0


def differing_paths(a: Any, b: Any, path: str = "") -> list[str]:
    """The paths at which two parsed JSON values differ (a path present in one only counts)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            out += [f"{path}.{k}"] if (k not in a or k not in b) else differing_paths(a[k], b[k], f"{path}.{k}")
        return out
    return [] if a == b else [path or "."]


def rederive_differences(repo: Path, plan: planmod.Plan, cfg: Mapping[str, Any], walk: Mapping[str, Any]) -> list[str]:
    """What differs between the committed plan and a re-derivation from the current code, config and inputs. The re-derivation is built with everything the plan was built from: its inputs (the reuse block included) and
    the charge before the freeze it RECORDED (``charge_before_freeze``: it is an input of the plan, not something the freeze can recompute without the ledgers; ``check_charge_unchanged`` checks the ledgers)."""
    rederived = qplan.build_candidate(repo, Path(plan.data["run_dir"]), cfg, inputs=plan.data["inputs"], mode=plan.data["mode"], walk=walk, test_mode=True, charge_before_freeze=plan.data.get("charge_before_freeze"))
    return differing_paths(qplan.scientific_content(json.loads(json.dumps(core.jsonable(rederived)))), qplan.scientific_content(plan.data))


def check_charge_unchanged(plan: planmod.Plan) -> dict[str, Any]:
    """The charge before the freeze is the one the plan recorded (the caps came from it). Each ledger the plan names must still hold at least the seconds recorded (a ledger that holds LESS was altered: refused); a ledger
    that grew since (a later attempt or rehearsal charged to it) is reported, not added: the counting rehearsal's own charge is NOT added to the cap (the auditor's ruling; its seconds go in Decision 2)."""
    rec = plan.data.get("charge_before_freeze") or {}
    now = {k: core.Ledger(Path(k), "Q", 1e12).charged() if Path(k).is_file() else None for k in (rec.get("ledgers") or {})}
    lost = [k for k, v in (rec.get("ledgers") or {}).items() if now[k] is None or now[k] < float(v) - 1e-6]
    if lost:
        raise StageRefused("refused: a ledger the plan's charge before the freeze was taken from holds less now (or is gone): " + ", ".join(lost))
    return {"recorded_seconds": rec.get("seconds"), "grown_since": {k: now[k] - float(v) for k, v in (rec.get("ledgers") or {}).items() if now[k] is not None and now[k] - float(v) > 1e-6}}


def reuse_rehearsal_gate(record: Mapping[str, Any], plan_file_sha256: str) -> dict[str, Any]:
    """The counting rehearsal of a plan that reuses stages: kind counting on non-provisional caps, this plan's SHA-256, every stage of ``reuse.ORDER`` COMPLETE, and the forced PAUSED — IDENTITY on a reused file."""
    done = {s for s, v in (record.get("stages") or {}).items() if v.get("status") == "COMPLETE"}
    missing = [s for s in reuse.ORDER if s not in done]
    forced = record.get("forced") or {}
    ok = not missing and record.get("kind_of_rehearsal") == "counting" and record.get("caps_provisional") is False and record.get("plan_file_sha256") == plan_file_sha256 and bool(forced.get("identity_on_reused_file"))
    return {"passed": ok, "missing": missing, "forced_identity_on_reused_file": bool(forced.get("identity_on_reused_file")), "plan_file_hash_matches": record.get("plan_file_sha256") == plan_file_sha256}


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
    a, b = section_span(text, "stage_caps")  # ONLY [stage_caps]: [stage_caps_attempt3] has its own writer
    body = text[a:b]
    for k, v in proposal.items():
        pat = re.compile(rf"(?m)^{k} = 0\.0(?![0-9])")
        if len(pat.findall(body)) != 1:
            raise StageRefused(f"refused: the config does not hold exactly one unset line '{k} = 0.0' in [stage_caps] (caps already entered?)")
        body = pat.sub(f"{k} = {v}", body)
    out = text[:a] + body + text[b:]
    if out.count("\nprovisional = true") != 1:
        raise StageRefused("refused: the config does not hold exactly one 'provisional = true'")
    return out.replace("\nprovisional = true", "\nprovisional = false")


def cmd_caps_config(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.ROOT
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps come from a MEASURING rehearsal's record")
    if args.attempt3:
        if not args.charged_ledger:
            raise StageRefused("refused: --attempt3 needs --charged-ledger (every ledger charged so far)")
        proposal = proposal_attempt3(meas, ledgers_charge(args.charged_ledger)["seconds"])
    else:
        proposal = proposal_from_record(meas)
    if args.apply:
        path = repo / core.CONFIG_Q
        path.write_text((apply_caps_attempt3 if args.attempt3 else apply_caps)(path.read_text(encoding="utf-8"), proposal), encoding="utf-8")
        print(json.dumps({"config": str(path), "applied": proposal, "next": "commit the config, then candidate-plan"}))
    else:
        print(caps_toml(proposal))
    return 0


CAPS_KEYS = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis", "total")


def section_span(text: str, name: str) -> tuple[int, int]:
    """The character span of the body of ``[name]`` (from its header line to the next section header)."""
    m = re.search(rf"(?m)^\[{re.escape(name)}\].*$", text)
    if not m:
        raise StageRefused(f"refused: the config has no [{name}] section")
    nxt = re.search(r"(?m)^\[", text[m.end():])
    return m.start(), m.end() + (nxt.start() if nxt else len(text) - m.end())


def apply_caps_attempt3(text: str, proposal: Mapping[str, float]) -> str:
    """Writes ONLY ``[stage_caps_attempt3]``: refuses unless every key it is about to set still reads ``0.0``; never touches ``[stage_caps]`` (attempt 2's caps, a record) or ``caps.provisional``."""
    a, b = section_span(text, "stage_caps_attempt3")
    body = text[a:b]
    for k, v in proposal.items():
        pat = re.compile(rf"(?m)^{k} = 0\.0(?![0-9])")  # exactly "0.0": not the prefix of "0.05"
        if len(pat.findall(body)) != 1:
            raise StageRefused(f"refused: [stage_caps_attempt3] does not hold exactly one unset line '{k} = 0.0' (already entered?)")
        body = pat.sub(f"{k} = {v}", body)
    return text[:a] + body + text[b:]


def reset_caps_text(text: str, stamp: str, superseded: str) -> str:
    """The config text with the nine caps set back to ``0.0``, ``provisional`` back to true, and a dated comment under ``[stage_caps]`` naming the record of the superseded values."""
    a, b = section_span(text, "stage_caps")
    body = text[a:b]
    for k in CAPS_KEYS:
        body, n = re.subn(rf"(?m)^{k}_hours = [0-9.]+", f"{k}_hours = 0.0", body)
        if n != 1:
            raise StageRefused(f"refused: the config does not hold exactly one '{k}_hours' line in [stage_caps]")
    out = text[:a] + body + text[b:]
    if out.count("\nprovisional = false") != 1:
        raise StageRefused("refused: the config does not hold exactly one 'provisional = false' (the caps are not entered)")
    out = out.replace("\nprovisional = false", "\nprovisional = true")
    marker = "[stage_caps]"
    i = out.index(marker)
    j = out.index("\n", i)
    note = f"\n# caps reset {stamp}: a correction of a cost projection made before any registered result exists; the superseded values are in {superseded}"
    return out[: j] + note + out[j:]


def cmd_caps_reset(args: argparse.Namespace) -> int:
    """Moves the entered caps into a superseded record and sets the config back to unset, by code: never a hand edit that could be mistaken for relaxing a cap after a result. Refuses once a freeze record exists and
    when the caps are not entered."""
    repo = Path(args.repo) if args.repo else core.ROOT
    if (repo / core.FREEZE_RECORD_Q).exists():
        raise StageRefused("refused: a freeze record exists; move it aside by a recorded step before correcting the caps")
    path = repo / core.CONFIG_Q
    text = path.read_text(encoding="utf-8")
    cfg = core.load_config("Q", path)
    if cfg["caps"]["provisional"]:
        raise StageRefused("refused: the caps are not entered (provisional is true): nothing to reset")
    stamp = core.utc_stamp()
    rec_path = repo / core.FREEZE_DIR / "superseded" / f"partq_caps_superseded_{stamp.replace(':', '').replace('-', '')}.json"
    if rec_path.exists():
        raise StageRefused(f"refused: {rec_path} exists")
    rec = {**core.envelope("block_record", "Q"), "what": "superseded_caps", "reason": args.reason, "utc": stamp, "stage_caps_hours": {k: float(v) for k, v in cfg["stage_caps"].items()}, "provisional_was": bool(cfg["caps"]["provisional"]),
           "config_sha256_before": file_sha256(path), "note": "A correction of a cost projection made before any registered result exists (the earlier caps came from rates measured inside one process, without the per-process overhead); not a relaxation after an observation."}  # fmt: skip
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(rec_path, core.jsonable(rec))
    path.write_text(reset_caps_text(text, stamp, str(rec_path.relative_to(repo))), encoding="utf-8")
    print(json.dumps({"config": str(path), "superseded_record": str(rec_path), "next": "commit the config and the record, then the measuring rehearsal"}))
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
    block = (plan.data.get("inputs") or {}).get(reuse.KEY)
    if block:  # attempt 3: the caps from the charge so far and the remaining stages only
        charge = plan.data.get("charge_before_freeze") or {}
        if not charge.get("seconds"):
            raise StageRefused("refused: the plan that reuses completed stages records no charge before the freeze")
        proposal = proposal_attempt3(meas, float(charge["seconds"]))
    else:
        proposal = proposal_from_record(meas)  # refuses a record that did not measure every registered stage
    differ = qplan.caps_match_config({"stage_caps": cfg["stage_caps_attempt3"]} if block else cfg, proposal)
    if differ:
        raise StageRefused("refused: the config's stage caps are not what the code computes from the measuring rehearsal: " + "; ".join(differ))
    walk = planmod.import_walk(repo, "Q")
    differing = rederive_differences(repo, plan, cfg, walk)  # the ledger is required (and read) just below
    if differing:
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and inputs in: " + ", ".join(differing[:10]) + ": supersede it and rehearse again")
    charge_info = check_charge_unchanged(plan)
    listed = {k: v for k, v in plan.data["frozen_files"].items()}
    wp = planmod.walk_problems(walk, listed, repo)
    if wp:
        raise StageRefused("refused: " + "; ".join(wp))
    pkgmanifest.require_package_manifest(plan.data["inputs"])  # R7: the plan names the installed-package manifest (names, versions, file hashes, the shadowed lock packages)
    try:
        counting = core.read_record(Path(args.counting_rehearsal), "rehearsal")
    except (ValueError, KeyError, OSError) as e:
        raise StageRefused(f"refused: --counting-rehearsal {args.counting_rehearsal} is not a P10IS2 rehearsal record ({type(e).__name__}: {e})") from e
    reuse_info: dict[str, Any] = {}
    if block:
        reuse.verify_block(block)  # condition 1: every file, byte for byte, now
        reuse.require_read_only(Path(block["source_run_dir"]), block["mode"])  # the earlier attempt's directory is protected by the file system as well as by the hashing
        reuse_info = {"files_verified": block["file_count"], "tree_sha256": block["tree_sha256"], "diff_against_earlier_freeze": reusecheck.confined_diff(repo, block["freeze_commit"]), "ledger": reusecheck.check_ledger_pin(repo, block["freeze_commit"], plan), "seeds": reusecheck.check_seeds(repo, block["freeze_commit"], plan)}
        reh = reuse_rehearsal_gate(counting, plan_sha)
    else:
        reh = gates.rehearsal_gate(counting, qplan.REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    if not reh["passed"]:
        raise StageRefused(f"refused: the counting rehearsal's record does not show every stage COMPLETE, the forced identity pause (and pause/resume of a first attempt), and this plan file's SHA-256: {reh}")
    stages_required = reuse.ORDER if block else qplan.REHEARSAL_STAGES
    stage_lines = {s: {"seconds": (counting.get("stages", {}).get(s) or {}).get("seconds"), "cap_seconds": plan.cap_seconds(s), "within_cap": (counting.get("stages", {}).get(s) or {}).get("within_cap")} for s in stages_required}
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
        "seal_broken": bool(args.seal_broken), "seed_gate": seed, "rehearsal_gate": reh, "charge_before_freeze": charge_info, "reuse": reuse_info or None, "counting_stage_seconds_against_caps": stage_lines, "caps_by_code": proposal, "adr_hash_provenance_only": plan.data["adr"]["sha256"],
    }  # fmt: skip
    record.parent.mkdir(parents=True, exist_ok=True)
    write_json(record, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record), "sha256": file_sha256(record), "plan_file_sha256": plan_sha}))
    return 0


def dispatch(args: argparse.Namespace) -> int:
    return {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal, "inputs-file": cmd_inputs_file, "units-file": cmd_units_file, "caps-config": cmd_caps_config, "reuse-file": cmd_reuse_file, "caps-reset": cmd_caps_reset}[args.command](args)
