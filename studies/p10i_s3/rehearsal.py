# ruff: noqa: E501
"""P10IS3 data preparation and the rehearsals (ADR-0026 sections 4, 5, 8; rulings 15, 18).

* ``prepare-data``: the chunk table (train ranks beyond 4,095, validation), the reproduction, lineage and disjointness gates, the panel walk and the shared ledger, the nine backbone digests.
* ``rehearse r1``: the rate search on the three calibration cells: every (arm, regime, rate) run to U* with the four checkpoints, selection by code, edge-rule extensions (at most two per side), then the full control set on the
  selected-rate checkpoints, NEG-REF on every M-TREE checkpoint. Writes ``rehearsal_public.json`` (the whitelist, no loss value) and ``rehearsal_sealed`` (one archive, outside the repository, hashed). Prints no loss.
* ``rehearse r2``: seconds per update and per evaluation and bytes per snapshot (the parallel slowdown is NOT measured here: see the report).
* ``rehearse r3``: the counting rehearsal against the candidate ``freeze/plan.json`` itself (its SHA-256 goes into the record), every registered stage end to end in the DRY profile (init 330392, streams 269201 + g).
* ``rehearse synthetic``: the same code paths on random data and random backbones at tiny sizes (test-range seeds): a test device, never a registered seed.
The DRY and calibration profiles read the calibration panel only (ruling 15); BASE gates alone read the registered panel.
"""

import argparse
import copy
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, write_json

from . import analysis, calibration, core, data, items, model, planted
from . import plan as planmod
from .plan import Plan, StageRefused
from .stages import cfg_for, deep_update, resources_for, run_stage

_EXTRA: dict[str, Any] = {}  # data manifest, data directory and parent suite of a real rehearsal (set by ``cmd_rehearse``)
SYNTHETIC_OVERRIDE: dict[str, Any] = {
    "duration": {"checkpoints": [2, 4, 6, 8], "u_star": 8},
    "setting": {"panel_chunks": 8},
    "data": {"synthetic_fresh": 256},
    "rates": {"grid": [0.003, 0.03]},
    "resources": {"workers": 3},
}


# --- prepare-data and window-spans ---------------------------------------------------------------------------------------------------------
def prepare_data(cs: data.ChunkSet, val_rows: Sequence[str], cfg: Mapping[str, Any], repo: Path, consumed: Mapping[str, Sequence[int]], digests: Mapping[str, str], excluded_doc: Mapping[str, Any], out: Path, shared_ledger: Path | None, *, expected_hashes: Mapping[str, str] | None = None) -> dict[str, Any]:
    """The chunk files, the reproduction, lineage and disjointness gates, the panel walk (excluded spans from ``window-spans``) and the ledger. REFUSES unless ``excluded_doc`` says where the ADR-0025 ledger stands:
    ``read`` (its file was read) or ``ABSENT-DECLARED`` (an explicit, recorded declaration), in which case this study's own spans are written to ``shared_ledger`` first (ADR-0026 correction C7)."""
    from . import window_spans as ws

    state = (excluded_doc.get("ledger") or {}).get("state")
    if excluded_doc.get("format") != "p10i-s3-excluded-spans-v1" or state not in ("read", "ABSENT-DECLARED"):
        raise StageRefused("refused: the excluded-spans file is not a window-spans output with a ledger state (a ledger file or an explicit --ledger-absent declaration)")
    if state == "ABSENT-DECLARED" and (shared_ledger is None or shared_ledger.exists()):
        raise StageRefused("refused: with the ADR-0025 ledger absent this study writes its own spans to the ledger first: pass --shared-ledger with a path that does not exist")
    if out.joinpath("data_manifest.json").exists():
        raise StageRefused(f"refused: {out}/data_manifest.json exists")
    d = cfg["data"]
    rep_u = (int(d["rep_u_ranks"][0]), int(d["rep_u_ranks"][1]))
    g_repro = data.reproduction_gate(cs, expected_hashes)
    g_lineage = data.lineage_gate(cs.train_spans, consumed, list(range(0, 2048)) if expected_hashes is None else list(range(int(d["rep_ranks"][1]))), rep_u, int(d["fresh_start"]))
    g_disjoint = data.rep_u_fresh_disjoint(cs.train_spans, rep_u, int(d["fresh_start"]), (int(d["rep_ranks"][0]), int(d["rep_ranks"][1])))
    excluded = [(int(a), int(b), int(c)) for a, b, c in excluded_doc["spans"]]
    panels = data.walk_panels(cs.val_spans, excluded, int(d["panel_walk_start"]), int(cfg["setting"]["panel_chunks"]))
    ledger = data.ledger({"registered": panels[0], "calibration": panels[1]}, cs.val_spans, excluded)  # type: ignore[arg-type]
    files = data.write_chunk_files(cs, out)
    write_json(out / "panel_ledger.json", ledger)
    files["panel_ledger.json"] = file_sha256(out / "panel_ledger.json")
    write_json(out / "excluded_spans.json", dict(excluded_doc))
    files["excluded_spans.json"] = file_sha256(out / "excluded_spans.json")
    if state == "ABSENT-DECLARED":
        assert shared_ledger is not None
        body = ws.shared_ledger_body(val_rows, {"registered": [cs.val_spans[r] for r in panels[0]], "calibration": [cs.val_spans[r] for r in panels[1]]}, [])
        shared_ledger.parent.mkdir(parents=True, exist_ok=True)
        write_json(shared_ledger, body)
    manifest = {"files": files, "panels": {"registered": panels[0], "calibration": panels[1]}, "ledger_sha256": ledger["sha256"], "parents": dict(digests), "gates": {"reproduction": g_repro, "lineage": g_lineage, "disjoint": g_disjoint}, "counts": cs.counts, "adr0025_ledger": excluded_doc["ledger"], "shared_ledger_written": str(shared_ledger) if state == "ABSENT-DECLARED" else None}
    write_json(out / "data_manifest.json", manifest)
    return manifest


def cmd_prepare_data(args: argparse.Namespace) -> int:
    from . import parents

    repo = Path(args.repo or core.repo_root())
    cfg = core.load_config(repo / core.CONFIG)
    cs = data.corpus_from_parquet(Path(args.source), cfg)
    val_rows = data.validation_rows(Path(args.source))
    consumed = {parents.parent_dir(p): parents.consumed_ranks(repo, p) for p in range(9)}
    digests = {parents.parent_dir(p): parents.load_backbone(repo, Path(args.parent_suite), p)[1] for p in range(9)}
    doc = json.loads(Path(args.excluded_spans).read_text())
    m = prepare_data(cs, val_rows, cfg, repo, consumed, digests, doc, Path(args.out), Path(args.shared_ledger) if args.shared_ledger else None)
    print(json.dumps({"data_manifest": str(Path(args.out) / "data_manifest.json"), "gates_passed": all(x["passed"] for x in m["gates"].values()), "ledger_sha256": m["ledger_sha256"]}))
    return 0


def cmd_window_spans(args: argparse.Namespace) -> int:
    """Generate the excluded-spans file from the validation text and the P10-S2 reference tokenizer (reads real data: the lead runs it). Exactly one of ``--ledger`` and ``--ledger-absent``."""
    import tomllib

    from . import window_spans as ws

    repo = Path(args.repo or core.repo_root())
    rows = data.validation_rows(Path(args.source))
    cfg_s2 = tomllib.loads((repo / "configs" / "p10s2_transfer.toml").read_text())
    from studies.p10s2.datagen import (
        HFTokenizer,  # read-only use of P10-S2's pinned tokenizer loader
    )

    tok = HFTokenizer(Path(args.downloads))
    rec = ws.p10s2_windows(tok, rows, cfg_s2)
    doc = ws.build_excluded(rows, rec, ledger_path=Path(args.ledger) if args.ledger else None, ledger_absent=bool(args.ledger_absent))
    doc["inputs"] = {"p10s2_config_sha256": file_sha256(repo / "configs" / "p10s2_transfer.toml")}
    out = Path(args.out)
    if out.exists():
        raise StageRefused(f"refused: {out} exists")
    write_json(out, doc)
    print(json.dumps({"excluded_spans": str(out), "sha256": file_sha256(out), "windows": len(doc["windows"]), "spans": len(doc["spans"]), "ledger": doc["ledger"]["state"]}))
    return 0


# --- plans of the rehearsals ----------------------------------------------------------------------------------------------------------------
def rehearsal_plan(repo: Path, run_dir: Path, name: str, cfg_override: Mapping[str, Any], plan_items: Mapping[str, Sequence[Mapping[str, Any]]], rate_table: Mapping[str, Any], *, synthetic: bool, gate_profile: str, extra: Mapping[str, Any] | None = None) -> Plan:
    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(cfg, cfg_override)
    rec = planmod.build_plan(mode=planmod.REHEARSAL, cfg=cfg, repo=repo, run_dir=run_dir, rate_table=rate_table, extra={**_EXTRA, **dict(extra or {})})
    rec.update({"items": {k: list(v) for k, v in plan_items.items()}, "cfg_override": dict(cfg_override), "synthetic": synthetic, "gate_profile": gate_profile, "workers": int(cfg["resources"]["workers"])})
    path = run_dir / "plans" / f"{name}.json"
    core.write_record(path, rec, overwrite=True)
    return Plan.load(path)


def calibration_items(cfg: Mapping[str, Any], rates: Mapping[tuple[str, str], Sequence[float]], cells: Sequence[int] = (0, 1, 2), *, profile: str = "calibration") -> dict[str, list[dict[str, Any]]]:
    """The rate-search runs: every (arm, regime, rate, cell) to U* with the four checkpoints (no step 0), each checkpoint evaluated on the calibration panel (enabled read)."""
    seeds = core.Seeds(profile, cfg)
    ck = [int(x) for x in cfg["duration"]["checkpoints"]]
    trains, evals = [], []
    for (arm, g), rs in rates.items():
        for r in rs:
            for c in cells:
                parent = core.calibration_parent(c) if profile == "calibration" else core.parent_of(c)
                tid = items.train_id(arm, g, r, c)
                trains.append({"id": tid, "kind": "train", "profile": profile, "arm": arm, "regime": g, "cell": c, "parent": parent, "rate": r, "role": "search", "max_update": max(ck), "snapshots": [0, *ck], "init_seed": seeds.init(c), "stream_seed": seeds.stream(c, core.REGIME_INDEX[g])})  # fmt: skip
                evals += [{"id": items.eval_id(arm, g, r, c, u) + "|rs", "kind": "eval", "train": tid, "profile": profile, "arm": arm, "regime": g, "cell": c, "parent": parent, "rate": r, "update": u, "controls": "enabled", "role": "search"} for u in ck]
    return {"train": trains, "eval": evals}


def state_dir_of(run_dir: Path, plan: Plan) -> Path:
    return run_dir / "stages" / (plan.path.stem if plan.path else "plan")


def _run_pool(plan: Plan, repo: Path, run_dir: Path, stages: Sequence[str]) -> None:
    """Item records are shared in ``run_dir`` (a finished train item is skipped by every later plan); gate results and task marks are per plan, in ``stages/<plan>``."""
    assert plan.path is not None
    for st in stages:
        code = run_stage(st, plan, repo, run_dir, plan.path, mode=plan.mode, identity={"mode": plan.mode}, state_dir=state_dir_of(run_dir, plan))
        if code != 0:
            raise core.EngineeringStop(f"ENGINEERING STOP — stage {st} of {plan.path} is not COMPLETE")


def _curves(run_dir: Path, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], arm: str, regime: str, rates: Sequence[float], cells: Sequence[int], ck: Sequence[int]) -> calibration.Curves:
    """curves[rate][cell][duration] from the rate-search records: None where the run failed before that checkpoint (a non-finite event, K1) or its NLL is non-finite (ruling 5)."""
    ev = {i["id"]: i for i in plan_items["eval"]}
    out: dict[float, dict[int, dict[int, float | None]]] = {}
    for r in rates:
        out[r] = {}
        for c in cells:
            out[r][c] = {}
            for u in ck:
                it = ev[items.eval_id(arm, regime, r, c, u) + "|rs"]
                p = items.eval_record_path(run_dir, it)
                if not p.is_file():
                    raise core.EngineeringStop(f"ENGINEERING STOP — missing calibration evaluation {it['id']}")
                rec = core.read_record(p, "eval")
                out[r][c][u] = None if "skipped" in rec else rec["reads"].get(f"{core.READ_ENABLED}|0")
    return out


def run_r1(repo: Path, run_dir: Path, cfg_override: Mapping[str, Any], *, synthetic: bool, sealed_path: Path, cells: Sequence[int] = (0, 1, 2)) -> dict[str, Any]:
    """The rate search with extensions, the full control set at the selected rates, NEG-REF, the sealed archive and the public whitelist. Prints no loss value."""
    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(cfg, cfg_override)
    ck = [int(x) for x in cfg["duration"]["checkpoints"]]
    u = int(cfg["duration"]["u_star"])
    tol, maxext = float(cfg["rates"]["tie_tolerance"]), int(cfg["rates"]["max_extensions_per_side"])
    base_grid = [float(x) for x in cfg["rates"]["grid"]]
    up, down = [float(x) for x in cfg["rates"]["extension_up"]], [float(x) for x in cfg["rates"]["extension_down"]]
    ams = calibration.ARM_REGIMES
    rates: dict[tuple[str, str], list[float]] = {ag: list(base_grid) for ag in ams}
    gate_profile = "test" if synthetic else "calibration"
    profile = "test" if synthetic else "calibration"
    started = time.monotonic()
    dummy_rt = {"rates": {f"{a}|{g}": {str(d): base_grid[0] for d in ck} for a, g in ams}, "edge": {f"{a}|{g}": False for a, g in ams}}
    for rnd in range(maxext + 1):
        it = calibration_items(cfg, rates, cells, profile=profile)
        plan = rehearsal_plan(repo, run_dir, f"r1-round{rnd}", cfg_override, it, dummy_rt, synthetic=synthetic, gate_profile=gate_profile)
        if rnd == 0:
            _run_pool(plan, repo, run_dir, ("gates",))
        _run_pool(plan, repo, run_dir, ("train", "eval"))
        curves_by = {ag: _curves(run_dir, it, ag[0], ag[1], rates[ag], cells, ck) for ag in ams}
        grew = False
        for ag in ams:
            nxt = calibration.extension_needed(curves_by[ag], ck, base_grid, up, down, tol, maxext)
            for side in ("up", "down"):
                if nxt[side] is not None:
                    rates[ag].append(float(nxt[side]))  # type: ignore[arg-type]
                    grew = True
        if not grew:
            break
    rt = calibration.rate_table(curves_by, ck, u, tol)
    # the full control set on the selected-rate runs, exactly as the registered plan would run them (calibration cells)
    full_items = items.registered_items(cfg, rt, profile=profile, cells=cells)
    plan_full = rehearsal_plan(repo, run_dir, "r1-full", cfg_override, full_items, rt, synthetic=synthetic, gate_profile=gate_profile)
    _run_pool(plan_full, repo, run_dir, ("train", "eval"))
    res = resources_for(plan_full, repo, cfg_for(plan_full, repo))
    bases: dict[str, dict[str, float]] = {}
    for p in sorted({core.calibration_parent(c) if profile == "calibration" else core.parent_of(c) for c in cells}):
        e = model.evaluate(model.build_model(copy.deepcopy(res.backbone(p)), core.BASE, 0), res.panels["calibration"], expected_targets=res.expected_targets)
        bases[str(p)] = {"enabled": e, "replay": e}
    reg = items.collect_registry(run_dir, full_items, bases)
    cell_parent = {c: (core.calibration_parent(c) if profile == "calibration" else core.parent_of(c)) for c in cells}
    th = core.Thresholds.from_config(cfg).scaled(len(cells))
    stats = analysis.analyse(reg, rt, cfg, cells=cell_parent, th=th, bitwise=False, calibration_parents=())
    neg = neg_ref_all(cfg, res, full_items, run_dir, rt, profile)
    sealed = calibration.sealed_bytes(curves_by, {"statistics": stats, "neg_ref": neg, "rate_table": rt})
    sha = calibration.write_sealed(sealed_path, repo, sealed, allow_inside_repo=synthetic)
    storage = _storage(run_dir)
    gates_rec = _gate_summary(run_dir, plan_full, neg)
    public = calibration.public_summary(curves_by, cfg, gates=gates_rec, timing={"r1_wall_seconds": time.monotonic() - started}, storage=storage, sealed_sha256=sha)
    public["rounds_extended"] = {f"{a}|{g}": len(rates[(a, g)]) - len(base_grid) for a, g in ams}
    public["caps_provisional"] = True
    public["stages"] = {"R1": {"status": "COMPLETE"}}
    core.write_record(run_dir / "rehearsal_public.json", public, overwrite=True)
    print(json.dumps({"rehearsal_public": str(run_dir / "rehearsal_public.json"), "sealed_sha256": sha, "sealed_path": str(sealed_path)}))
    return public


def neg_ref_all(cfg: Mapping[str, Any], res: items.Resources, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], run_dir: Path, rt: Mapping[str, Any], profile: str) -> dict[str, Any]:
    """NEG-REF from every rehearsal M-TREE checkpoint of the selected-rate runs: P_all, P_used, X and X_mean must be 0 within 1e-6 and no per-cell D2 or D3 (ruling 9). The values go to the sealed archive; the public file gets pass or fail."""
    th = core.Thresholds.from_config(cfg)
    seeds = core.Seeds(profile, cfg)
    out: dict[str, Any] = {}
    ok = True
    for it in plan_items["eval"]:
        if it["arm"] != core.TREE or it["controls"] != "full":
            continue
        tr = [t for t in plan_items["train"] if t["id"] == it["train"]][0]
        m = items._build(res, it, seeds.init(int(it["cell"])))
        ident = items._identity({**tr})
        model.restore_snapshot(items._paths(run_dir, it["train"]) / "snapshots", m, int(it["update"]), ident)
        r = planted.neg_ref_check(m, res.panels["calibration"], seeds, th, cell=int(it["cell"]))
        out[it["id"]] = r
        ok = ok and r["passed"]
    return {"passed": ok, "cells": out}


def _storage(run_dir: Path) -> dict[str, Any]:
    sizes = [p.stat().st_size for p in run_dir.rglob("state.pt")]
    return {"snapshots": len(sizes), "total_bytes": sum(sizes), "bytes_per_snapshot_mean": (sum(sizes) / len(sizes)) if sizes else None}


def _gate_summary(run_dir: Path, plan: Plan, neg: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"neg_ref": {"passed": neg["passed"]}}
    d = run_dir / "stages" / "r1-round0" / "gates" / "results"
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        rec = core.read_record(p, "gate")
        out[p.stem] = {"passed": rec["passed"]}
    return out


# --- R2: cost -----------------------------------------------------------------------------------------------------------------------------
def run_r2(repo: Path, run_dir: Path, cfg_override: Mapping[str, Any], *, synthetic: bool, updates: int = 50) -> dict[str, Any]:
    """Seconds per update per arm, seconds per evaluation (enabled, the exhaustive read) and bytes per snapshot, at the ordinary load (the 1-minute load average is recorded; LOADED above 4 is a mark on a cost record and decides nothing)."""
    import os
    import tempfile

    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(cfg, cfg_override)
    plan = rehearsal_plan(repo, run_dir, "r2", cfg_override, {"train": [], "eval": []}, {"rates": {}, "edge": {}}, synthetic=synthetic, gate_profile="test")
    res = resources_for(plan, repo, cfg_for(plan, repo))
    timing: dict[str, Any] = {"load_average_1min": os.getloadavg()[0]}
    timing["LOADED"] = timing["load_average_1min"] > float(cfg["thresholds"]["loaded_load_average"])
    with tempfile.TemporaryDirectory(dir=run_dir) as tmp:
        for arm in core.ARMS:
            m = model.build_model(copy.deepcopy(res.backbone(0)), arm, 330392)
            stream = model.Stream(res.rows[core.REP], core.test_seed(1), fresh=False)
            t0 = time.monotonic()
            r = model.train_run(m, stream, 0.003, Path(tmp) / arm, [updates], updates, {"r2": arm})
            timing[f"seconds_per_update_{arm}"] = (time.monotonic() - t0) / max(1, r["updates_done"])
            t0 = time.monotonic()
            model.evaluate(m, res.panels["calibration"], expected_targets=res.expected_targets)
            timing[f"seconds_per_evaluation_{arm}"] = time.monotonic() - t0
            if arm == core.TREE:
                t0 = time.monotonic()
                model.evaluate(m, res.panels["calibration"], model.Ctl("exhaustive", visit=16), expected_targets=res.expected_targets)
                timing["seconds_per_exhaustive_evaluation_M-TREE"] = time.monotonic() - t0
            timing[f"bytes_per_snapshot_{arm}"] = r["bytes"]
    rec = {"timing": timing, "note": "descriptive records of this implementation on this machine; not an efficiency result; the parallel slowdown is not measured here"}
    write_json(run_dir / "r2.json", rec)
    return rec


# --- R3: the counting rehearsal ------------------------------------------------------------------------------------------------------------
DRY_OVERRIDE: dict[str, Any] = {"duration": {"checkpoints": [8, 16, 24, 32], "u_star": 32}, "setting": {"panel_chunks": 8}}


def dry_rate_table(rt: Mapping[str, Any], real_ck: Sequence[int], dry_ck: Sequence[int]) -> dict[str, Any]:
    out: dict[str, Any] = {"rates": {}, "edge": dict(rt["edge"])}
    for k, v in rt["rates"].items():
        out["rates"][k] = {str(d): v[str(r)] for r, d in zip(real_ck, dry_ck, strict=True)}
    return out


def run_r3(repo: Path, run_dir: Path, candidate: Plan, *, synthetic: bool) -> dict[str, Any]:
    """Every registered stage end to end against the candidate plan's rate table in the DRY profile (one cell: init 330392, streams 269201 + g, DRY permutation seeds; shortened checkpoints), the candidate plan file's SHA-256 recorded."""
    cfg = core.load_config(repo / core.CONFIG)
    real_ck = [int(x) for x in cfg["duration"]["checkpoints"]]
    over = copy.deepcopy(DRY_OVERRIDE) if not synthetic else deep_update(copy.deepcopy(SYNTHETIC_OVERRIDE), {"duration": {"checkpoints": [2, 4, 6, 8], "u_star": 8}})
    dry_ck = over["duration"]["checkpoints"]
    rt = dry_rate_table(candidate.rate_table, real_ck, dry_ck)
    dcfg = copy.deepcopy(dict(cfg))
    deep_update(dcfg, over)
    it = items.registered_items(dcfg, rt, profile="dry", cells=[0])
    plan = rehearsal_plan(repo, run_dir, "r3", over, it, rt, synthetic=synthetic, gate_profile="dry", extra={k: candidate.data[k] for k in ("data_manifest", "data_dir", "parent_suite") if k in candidate.data})
    _run_pool(plan, repo, run_dir, ("gates", "train", "eval"))
    full = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(full, over)
    res = resources_for(plan, repo, cfg_for(plan, repo))
    base = {"0": {"enabled": e, "replay": e} for e in [model.evaluate(model.build_model(copy.deepcopy(res.backbone(0)), core.BASE, 0), res.panels["calibration"], expected_targets=res.expected_targets)]}
    reg = items.collect_registry(run_dir, it, base)
    result = analysis.analyse(reg, rt, dcfg, cells={0: 0}, th=core.Thresholds.from_config(dcfg).scaled(1), bitwise=False)
    from . import report

    text = report.render(result, "dry")
    (run_dir / "r3_report.md").write_text(text, encoding="utf-8")
    rec = {"status": "COMPLETE", "candidate_plan_sha256_of_content": candidate.sha256(), "plan_file_sha256": file_sha256(candidate.path) if candidate.path else None, "stages": ["gates", "train", "eval", "analysis", "report"]}
    write_json(run_dir / "r3.json", rec)
    return rec


def cmd_rehearse(args: argparse.Namespace) -> int:
    repo = Path(args.repo or core.repo_root())
    run_dir = Path(args.run_dir).resolve()
    planmod.require_ignored_run_dir(repo, run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    synthetic = args.phase == "synthetic"
    over = SYNTHETIC_OVERRIDE if synthetic else {}
    if args.data_manifest:
        dm = Path(args.data_manifest).resolve()
        _EXTRA.update({"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_suite": str(Path(args.parent_suite).resolve())})
    if args.phase in ("r1", "synthetic"):
        run_r1(repo, run_dir, over, synthetic=synthetic, sealed_path=Path(args.sealed_path))
        return 0
    if args.phase == "r2":
        run_r2(repo, run_dir, over, synthetic=False)
        return 0
    cand = Plan.load(Path(args.plan) if args.plan else repo / core.PLAN)
    rec = run_r3(repo, run_dir, cand, synthetic=False)
    pub_path = run_dir / "rehearsal_public.json"
    pub = core.read_record(pub_path, "rehearsal_public") if pub_path.is_file() else {**core.envelope("rehearsal_public"), "stages": {}}
    pub["stages"] = {**pub.get("stages", {}), "R3": {"status": "COMPLETE"}, "R2": {"status": "COMPLETE" if (run_dir / "r2.json").is_file() else "MISSING"}}
    pub["candidate"] = {"status": "COMPLETE", "plan_file_sha256": rec["plan_file_sha256"]}
    pub["caps_provisional"] = bool(cand.data.get("caps_provisional"))
    core.write_record(pub_path, pub, overwrite=True)
    return 0
