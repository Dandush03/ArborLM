# ruff: noqa: E501
"""P10IS0 freeze commands (ADR-0023 section 10 stage 5; the pattern of ADR-0029 section 13): ``candidate-plan``, ``counting-rehearsal`` and ``freeze``.

* ``candidate_plan`` writes ``freeze/plan.json`` first (refuses to overwrite without ``supersede``, which moves the old file aside, never deletes it).
* ``counting_rehearsal`` runs against that exact file: every item resolves to a cell label, a seed set and an initialisation seed, no label repeats, the count is the plan's, and the analysis runs on a synthetic registry keyed by the plan's
  labels; its record carries the plan file's SHA-256 and whether the caps were provisional. No training.
* ``freeze`` re-derives the plan's scientific content from current code, config and ``durations.json`` and refuses any difference; refuses a rehearsal made on provisional caps or naming another plan file; refuses while the seed gate
  fails; refuses unless the lead, the implementer and the auditor each state that they did not open the sealed files (or the seal is declared broken, which prints CALIBRATION VALUES SEEN BY THE LEAD). It does not compare the ADR's hash
  (provenance only). It writes only the freeze record: the hash of every frozen input individually, the sealed files' hashes, the seed gate result and the twelve named spare values. The freeze commit is the human lead's act.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import analysis, core, sealed, seeds
from . import plan as planmod
from .plan import StageRefused


def candidate_plan(repo: Path, *, supersede: bool = False, run_dir: Path | None = None) -> dict[str, Any]:
    """Write the candidate ``freeze/plan.json`` from ``freeze/durations.json`` (which Stage R wrote) and the config."""
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    dur_path = repo / core.DURATIONS
    if not dur_path.is_file():
        raise StageRefused("refused: no freeze/durations.json: Stage R has not written it")
    if plan_path.exists():
        if not supersede:
            raise StageRefused(f"refused: {plan_path} exists; a candidate plan is replaced only with supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(plan_path)
        n = 0
        target = plan_path.parent / "superseded" / f"plan-{old[:12]}.json"
        while target.exists():  # an identical plan superseded twice keeps both files: nothing is deleted or overwritten
            n += 1
            target = plan_path.parent / "superseded" / f"plan-{old[:12]}-{n}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        plan_path.rename(target)
    durations = core.read_record(dur_path, "durations")["cell_types"]
    caps_path = repo / core.STAGE_CAPS
    caps = core.read_record(caps_path, "stage_caps") if caps_path.is_file() else {"provisional": True}
    from .profile import profile_of

    dp, mf = _draws_of(run_dir)
    record = planmod.build_plan(cfg, durations, caps=caps, profile=profile_of(run_dir), draw_plan=dp, manifests=mf, run_dir=str(run_dir.resolve()) if run_dir else None)
    record["stage_r_projection"] = stage_r_projection(run_dir, cfg)
    record["durations_sha256"] = file_sha256(dur_path)
    core.write_record(plan_path, record)
    return {"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "cells": len(record["items"]["main"]), "caps_provisional": bool(caps.get("provisional", True))}


def stage_r_projection(run_dir: Path | None, cfg: Mapping[str, Any]) -> dict[str, Any] | None:
    """The projected Stage R wall hours with one task per run (ANALYTICAL, from stage 3's rates in the run directory at the larger of the quiet and busy rates, six workers, every cell type run to the top of the base ladder: the worst case)."""
    if run_dir is None or not (run_dir / "timing" / "rates.json").is_file():
        return None
    from . import drivers, ladder
    from .profile import profile_of

    prof = profile_of(run_dir)
    rates = drivers.load_rates(run_dir, which="larger", cfg=cfg)
    cts = core.cell_types(cfg)
    lad = [prof.exp(int(e)) for e in cfg["ladder"]["base"]]
    hours = ladder.stage_r_makespan_hours(cts, rates, int(cfg["budget"]["workers"]), lad, prof.facts_of)
    return {"kind": "ANALYTICAL", "hours_with_runs_as_tasks": hours, "basis": "stage 3's rates, larger of quiet and busy, six workers, round barrier, every run to the top of the base ladder (the worst case)"}


def _draws_of(run_dir: Path | None) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """The draw plan and the SHA-256 of every draw manifest of the run directory (the plan names the data it runs on)."""
    if run_dir is None or not (run_dir / "draw_plan.json").is_file():
        return None, None
    dp = read_json(run_dir / "draw_plan.json")
    names = sorted({*dp["seed_set_of"].values()})
    return dp, {n: file_sha256(run_dir / "draws" / n / "data_manifest.json") for n in names}


def counting_rehearsal(repo: Path) -> dict[str, Any]:
    """Resolve every stage's items of the plan file to their inputs and outputs without training, and run the analysis on a synthetic registry keyed by the plan's labels. The record names the plan file's SHA-256."""
    cfg = core.load_config(repo / core.CONFIG)
    plan_path = repo / core.PLAN
    from .profile import by_name

    plan = planmod.load_plan(plan_path)
    prof = by_name(plan.get("profile", "registered"))
    problems: list[str] = []
    labels_seen: set[str] = set()
    for it in planmod.items_of(plan, "main"):
        if it["label"] in labels_seen:
            problems.append(f"duplicate label {it['label']}")
        labels_seen.add(it["label"])
        ct = core.cell_type_by_name(it["cell_type"], cfg)
        cell = core.make_cell("REG", ct, it["arm"], it["draw"], 0, cfg, prof.name)
        if cell.label != it["label"] or cell.init_seed != it["init_seed"] or core.set_of_name(it["seed_set"], cfg, prof.name).name != it["seed_set"] or it["seed_set"] != plan["draws"]["seed_set_of"][str(it["draw"])]:
            problems.append(f"item {it['label']} does not resolve to its cell, seed or set")
        if it["updates"] != core.updates_for(plan["cell_types"][it["cell_type"]]["t_exposures"], prof.facts_of(ct.facts)):
            problems.append(f"item {it['label']} has the wrong update count")
    expected = sum(10 * len(ct.arms) for ct in core.cell_types(cfg) if not plan["cell_types"][ct.name].get("removed"))
    if len(labels_seen) != expected:
        problems.append(f"the plan has {len(labels_seen)} cells; the grid gives {expected}")
    th = core.Thresholds.from_config(cfg)
    reg: dict[analysis.Key, analysis.CellRecord] = {}
    for it in planmod.items_of(plan, "main"):
        o = _synthetic_obs()
        reg[(it["cell_type"], it["arm"], it["draw"])] = analysis.CellRecord("ok", {"e512": o, "half": o, "T": o})
    durations = {n: {"t_exposures": v.get("t_exposures", 0), "convergence": "SHOWN", "reference_flags": v.get("reference_flags", {}), "removed": v.get("removed", False)} for n, v in plan["cell_types"].items()}
    ran = analysis.analyze(reg, durations, cfg=cfg)
    del th
    caps = plan.get("caps") or {}
    return {
        **core.envelope("rehearsal"), "candidate": {"status": "COMPLETE" if not problems else "FAILED", "plan_file_sha256": file_sha256(plan_path), "problems": problems}, "caps_provisional": bool(caps.get("provisional", True)),
        "items": {"main": len(labels_seen)}, "analysis_on_synthetic_registry": {"headline_step": ran["headline"]["step"], "keyed_by_labels": True},
    }  # fmt: skip


def _synthetic_obs() -> Any:
    from .labels import Obs

    return Obs((950, 1000), (950, 1000), (950, 1000), (950, 1000), True, True, False, 200, 0.01, 256, 0.0, 0.95, 0.95, 0.95)


def freeze(repo: Path, rehearsal_path: Path, *, attest_unopened: Sequence[str], seal_broken: bool = False, sealed_dir: Path | None = None, run_checker: bool = True, disclosed_reads: Sequence[str] = ()) -> dict[str, Any]:
    """Write ``freeze/freeze_record.json``. Refuses on every condition in the module docstring; writes only the freeze record."""
    cfg = core.load_config(repo / core.CONFIG)
    plan_path, record_path = repo / core.PLAN, repo / core.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    if not plan_path.is_file():
        raise StageRefused("refused: no candidate plan: write it first, rehearse against it, then freeze")
    plan = planmod.load_plan(plan_path)
    caps_path = repo / core.STAGE_CAPS
    if not caps_path.is_file() or core.read_record(caps_path, "stage_caps").get("provisional", True):
        raise StageRefused("refused: the caps are provisional or freeze/stage_caps.json is missing: the caps are set from the measured projection and the plan rewritten and rehearsed again")
    durations = core.read_record(repo / core.DURATIONS, "durations")["cell_types"]
    from .profile import by_name

    dp, mf = _draws_of(Path(plan["run_dir"])) if plan.get("run_dir") else (None, None)
    rederived = planmod.build_plan(cfg, durations, profile=by_name(plan.get("profile", "registered")), draw_plan=dp, manifests=mf, run_dir=plan.get("run_dir"))
    if json.loads(json.dumps(core.jsonable(planmod.scientific_content(rederived)))) != planmod.scientific_content(plan):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and durations.json: supersede it and rehearse again")
    reh = core.read_record(rehearsal_path, "rehearsal")
    cand = reh.get("candidate") or {}
    if reh.get("caps_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps (or does not say)")
    if cand.get("status") != "COMPLETE" or cand.get("plan_file_sha256") != file_sha256(plan_path):
        raise StageRefused("refused: the rehearsal record does not show the candidate plan of this file rehearsed to COMPLETE")
    attest = set(attest_unopened)
    if not seal_broken and attest != {"lead", "implementer", "auditor"}:
        raise StageRefused("refused: the freeze record must state, for the lead, the implementer and the auditor, that none has opened the sealed files, or declare the seal broken")
    gate = seeds.seed_gate(cfg, root=repo, run_checker=run_checker)
    if not gate["passed"]:
        raise StageRefused(f"refused: the seed gate did not pass: {gate['problems']}")
    inputs = planmod.hash_inputs(repo)
    rec = {
        **core.envelope("freeze_record"), "plan_file_sha256": file_sha256(plan_path), "inputs": inputs, "sealed_files_sha256": sealed.sealed_hashes(sealed_dir) if sealed_dir is not None else {}, "disclosed_reads": sorted(disclosed_reads),
        "attestations": {"sealed_files_unopened_by": sorted(attest), "recorded_by": "the freeze command from the flags; not verified by code"}, "seal_broken": seal_broken,
        "seed_gate": {k: gate[k] for k in ("passed", "roles", "declared_reuse_not_new", "named_spare_values", "checker")}, "rehearsal": {"path": str(rehearsal_path.resolve()), "sha256": file_sha256(rehearsal_path)},
        "adr_sha256_provenance_only": core.spec_sha256(repo),
    }  # fmt: skip
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, core.jsonable(rec))
    return {"freeze_record": str(record_path), "sha256": file_sha256(record_path), "plan_file_sha256": rec["plan_file_sha256"]}


def read_durations(repo: Path) -> Mapping[str, Any]:
    return dict(read_json(repo / core.DURATIONS))
