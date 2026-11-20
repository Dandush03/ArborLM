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
    """Generate the excluded-spans file from P10-S2's RECORDED windows and token bytes and the pinned validation text: no tokenizer, no package outside the lock (needs pyarrow: ``uv run --locked --extra pilot``).
    Exactly one of ``--ledger`` and ``--ledger-absent``."""
    import tomllib

    from . import window_spans as ws

    repo = Path(args.repo or core.repo_root())
    rows = data.validation_rows(Path(args.source))
    cfg_s2_path = repo / "configs" / "p10s2_transfer.toml"
    cfg_s2 = tomllib.loads(cfg_s2_path.read_text())
    manifest = Path(args.manifest) if args.manifest else repo / "results" / "p10s2-datagen-2026-11-16" / "bundle_manifest.json"
    out = Path(args.out)
    if out.exists():
        raise StageRefused(f"refused: {out} exists")
    rec = ws.p10s2_windows_from_records(rows, Path(args.bundle), manifest, cfg_s2)
    doc = ws.build_excluded(rows, rec, ledger_path=Path(args.ledger) if args.ledger else None, ledger_absent=bool(args.ledger_absent))
    doc["inputs"] = {"p10s2_config_sha256": file_sha256(cfg_s2_path), "bundle_digests": rec["bundle_digests"], "bundle_manifest_sha256": file_sha256(manifest), "method": rec["method"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, doc)
    print(json.dumps({"excluded_spans": str(out), "sha256": file_sha256(out), "windows": len(doc["windows"]), "found_exactly_once": rec["found_exactly_once"], "spans": len(doc["spans"]), "ledger": doc["ledger"]["state"]}))
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


def _run_pool(plan: Plan, repo: Path, items_dir: Path, public_dir: Path, stages: Sequence[str]) -> None:
    """Item records are shared in ``items_dir`` (the SEALED directory: calibration and DRY values never sit in the public run directory); gate results, task marks and manifests are per plan, in ``<public>/stages/<plan>``."""
    assert plan.path is not None
    for st in stages:
        code = run_stage(st, plan, repo, items_dir, plan.path, mode=plan.mode, identity={"mode": plan.mode}, state_dir=state_dir_of(public_dir, plan))
        if code != 0:
            raise core.EngineeringStop(f"ENGINEERING STOP — stage {st} of {plan.path} is not COMPLETE")


def _curves(items_dir: Path, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], arm: str, regime: str, rates: Sequence[float], cells: Sequence[int], ck: Sequence[int]) -> calibration.Curves:
    """curves[rate][cell][duration] from the rate-search records: None where the run failed before that checkpoint (a non-finite event, K1) or its NLL is non-finite (ruling 5)."""
    ev = {i["id"]: i for i in plan_items["eval"]}
    out: dict[float, dict[int, dict[int, float | None]]] = {}
    for r in rates:
        out[r] = {}
        for c in cells:
            out[r][c] = {}
            for u in ck:
                it = ev[items.eval_id(arm, regime, r, c, u) + "|rs"]
                p = items.eval_record_path(items_dir, it)
                if not p.is_file():
                    raise core.EngineeringStop(f"ENGINEERING STOP — missing calibration evaluation {it['id']}")
                rec = core.read_record(p, "eval")
                out[r][c][u] = None if "skipped" in rec else rec["reads"].get(f"{core.READ_ENABLED}|0")
    return out


def sealed_dir_for(sealed_path: Path) -> Path:
    return sealed_path.parent / "items"


def run_r1(repo: Path, run_dir: Path, cfg_override: Mapping[str, Any], *, synthetic: bool, sealed_path: Path, cells: Sequence[int] = (0, 1, 2)) -> dict[str, Any]:
    """The rate search with extensions, the full control set at the selected rates, NEG-REF, the sealed archive and the public whitelist. Prints no loss value. Item records (every calibration NLL) are written under the
    sealed directory beside the archive, outside the repository (B4); ``run_dir`` holds plans, manifests and gate results only."""
    sealed_dir = sealed_dir_for(sealed_path)
    calibration.require_outside_repo(sealed_dir, repo, allow_inside_repo=synthetic)
    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(cfg, cfg_override)
    rules_before = planmod.rule_hashes(repo)
    ck = [int(x) for x in cfg["duration"]["checkpoints"]]
    u = int(cfg["duration"]["u_star"])
    tol, maxext = float(cfg["rates"]["tie_tolerance"]), int(cfg["rates"]["max_extensions_per_side"])
    base_grid = [float(x) for x in cfg["rates"]["grid"]]
    up, down = [float(x) for x in cfg["rates"]["extension_up"]], [float(x) for x in cfg["rates"]["extension_down"]]
    ams = calibration.ARM_REGIMES
    rates: dict[tuple[str, str], list[float]] = {ag: list(base_grid) for ag in ams}
    profile = "test" if synthetic else "calibration"
    started = time.monotonic()
    dummy_rt = {"rates": {f"{a}|{g}": {str(d): base_grid[0] for d in ck} for a, g in ams}, "edge": {f"{a}|{g}": False for a, g in ams}}
    for rnd in range(maxext + 1):
        it = calibration_items(cfg, rates, cells, profile=profile)
        plan = rehearsal_plan(repo, run_dir, f"r1-round{rnd}", cfg_override, it, dummy_rt, synthetic=synthetic, gate_profile=profile)
        if rnd == 0:
            _run_pool(plan, repo, sealed_dir, run_dir, ("gates",))
        _run_pool(plan, repo, sealed_dir, run_dir, ("train", "eval"))
        curves_by = {ag: _curves(sealed_dir, it, ag[0], ag[1], rates[ag], cells, ck) for ag in ams}
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
    plan_full = rehearsal_plan(repo, run_dir, "r1-full", cfg_override, full_items, rt, synthetic=synthetic, gate_profile=profile)
    _run_pool(plan_full, repo, sealed_dir, run_dir, ("train", "eval"))
    res = resources_for(plan_full, repo, cfg_for(plan_full, repo))
    bases: dict[str, dict[str, float]] = {}
    for p in sorted({core.calibration_parent(c) if profile == "calibration" else core.parent_of(c) for c in cells}):
        e = model.evaluate(model.build_model(copy.deepcopy(res.backbone(p)), core.BASE, 0), res.panels["calibration"], expected_targets=res.expected_targets)
        bases[str(p)] = {"enabled": e, "replay": e}
    reg = items.collect_registry(sealed_dir, full_items, bases)
    cell_parent = {c: (core.calibration_parent(c) if profile == "calibration" else core.parent_of(c)) for c in cells}
    th = core.Thresholds.from_config(cfg).scaled(len(cells))
    stats = analysis.analyse(reg, rt, cfg, cells=cell_parent, th=th, bitwise=False, calibration_parents=())
    neg = neg_ref_all(cfg, res, full_items, sealed_dir, rt, profile)
    sealed = calibration.sealed_bytes(curves_by, {"statistics": stats, "neg_ref": neg, "rate_table": rt})
    sha = calibration.write_sealed(sealed_path, repo, sealed, allow_inside_repo=synthetic)
    storage = _storage(sealed_dir)
    gates_rec = _gate_summary(run_dir, plan_full, neg)
    public = calibration.public_summary(curves_by, cfg, gates=gates_rec, timing={"r1_wall_seconds": time.monotonic() - started}, storage=storage, sealed_sha256=sha)
    public["rounds_extended"] = {f"{a}|{g}": len(rates[(a, g)]) - len(base_grid) for a, g in ams}
    public["caps_provisional"] = True
    public["stages"] = {"R1": {"status": "COMPLETE"}}
    rules_after = planmod.rule_hashes(repo)
    if rules_after != rules_before:
        raise core.EngineeringStop("ENGINEERING STOP — a rule-bearing file or configuration section changed during R1")
    public["rule_hashes"] = rules_after  # R4: the freeze refuses if any differs
    core.write_record(run_dir / "rehearsal_public.json", public, overwrite=True)
    print(json.dumps({"rehearsal_public": str(run_dir / "rehearsal_public.json"), "sealed_sha256": sha, "sealed_path": str(sealed_path)}))
    return public


def neg_ref_all(cfg: Mapping[str, Any], res: items.Resources, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], items_dir: Path, rt: Mapping[str, Any], profile: str) -> dict[str, Any]:
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
        model.restore_snapshot(items._paths(items_dir, it["train"]) / "snapshots", m, int(it["update"]), ident)
        r = planted.neg_ref_check(m, res.panels["calibration"], seeds, th, cell=int(it["cell"]))
        out[it["id"]] = r
        ok = ok and r["passed"]
    return {"passed": ok, "cells": out}


def _storage(items_dir: Path) -> dict[str, Any]:
    sizes = [p.stat().st_size for p in items_dir.rglob("state.pt")]
    return {"snapshots": len(sizes), "total_bytes": sum(sizes), "bytes_per_snapshot_mean": (sum(sizes) / len(sizes)) if sizes else None}


def _gate_summary(run_dir: Path, plan: Plan, neg: Mapping[str, Any]) -> dict[str, Any]:
    """The whitelist's gate list (section 5.3): pass or fail of NEG-REF, the planted-positive test, the prefix gates (per arm-regime), the read-equality gate and the synthetic-registry test, plus the other gates."""
    out: dict[str, Any] = {"neg_ref": {"passed": neg["passed"]}}
    d = run_dir / "stages" / "r1-round0" / "gates" / "results"
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        rec = core.read_record(p, "gate")
        out[p.stem] = {"passed": rec["passed"]}
        if p.stem == "core":
            for k, v in rec["results"].items():
                if k in ("planted_positive", "read_equality", "synthetic_registry", "base_and_disabled", "seeds", "identity", "platform"):
                    out[f"core:{k}"] = {"passed": v["passed"]}
    return out


# --- R2: cost (R5) ------------------------------------------------------------------------------------------------------------------------
def run_r2(repo: Path, run_dir: Path, cfg_override: Mapping[str, Any], *, synthetic: bool, updates: int = 50) -> dict[str, Any]:
    """R2 measured the way the caps need it (R5): worker subprocesses, each configured (one thread), on the registry's dry-rehearsal seeds; one worker alone per arm, then k = the registered worker count together (arms in
    turn), so every unit cost carries the parallel slowdown; the time of a full read set with its replay is measured, not only the enabled read. Writes ``r2.json`` with unit costs only (timings: no loss value); the cap is computed
    from it by ``candidate-plan`` (``cost.project_hours``). The load average is recorded; LOADED above 4 is a mark on a cost record and decides nothing."""
    import os
    import sys

    from . import cost, runner
    from .stages import safe

    cfg = copy.deepcopy(dict(core.load_config(repo / core.CONFIG)))
    deep_update(cfg, cfg_override)
    k = int(cfg["resources"]["workers"])
    plan = rehearsal_plan(repo, run_dir, "r2", cfg_override, {"train": [], "eval": []}, {"rates": {}, "edge": {}}, synthetic=synthetic, gate_profile="dry", extra={"r2_updates": updates})
    assert plan.path is not None
    ledger = core.Ledger(run_dir / "ledger.json", plan.cap_seconds("r2"))
    planmod.require_ignored_path(repo, ledger.path)
    out_dir = run_dir / "r2"
    base = (sys.executable, "-m", "studies.p10i_s3.stages", "work", "r2probe", "--run-dir", str(run_dir), "--plan", str(plan.path), "--repo", str(repo))

    def tasks(names: Sequence[tuple[str, str]]) -> list[runner.Task]:
        return [runner.Task(label, (*base, "--arm", arm, "--out", str(out_dir / f"{safe(label)}.json")), out_dir / f"{safe(label)}.json", out_dir / f"{safe(label)}.failed", out_dir / f"{safe(label)}.log") for label, arm in names]

    load = os.getloadavg()[0]
    single: dict[str, dict[str, float]] = {}
    spent = 0.0
    for arm in core.ARMS:  # one worker alone
        t = tasks([(f"single-{arm}", arm)])
        o, sec = runner.run_tasks(t, workers=1, cap_seconds=max(1.0, ledger.remaining()), rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=run_dir)
        spent += sec
        if o[t[0].label]["status"] != runner.COMPLETED:
            raise core.EngineeringStop(f"ENGINEERING STOP — R2 probe {t[0].label}: {o[t[0].label]}")
        single[arm] = read_json_(t[0].result_path)
    par_names = [(f"parallel-{i}-{core.ARMS[i % 3]}", core.ARMS[i % 3]) for i in range(max(k, 3))]  # k workers at once (at least one probe of every arm)
    t = tasks(par_names)
    o, sec = runner.run_tasks(t, workers=k, cap_seconds=max(1.0, ledger.remaining()), rss_worker_bytes=int(plan.data["rss_worker_bytes"]), rss_aggregate_bytes=int(plan.data["rss_aggregate_bytes"]), run_dir=run_dir)
    spent += sec
    if any(v["status"] != runner.COMPLETED for v in o.values()):
        raise core.EngineeringStop(f"ENGINEERING STOP — an R2 probe did not complete: {o}")
    ledger.charge("R2", spent)
    unit = cost.unit_costs_from_probes(single, [read_json_(x.result_path) for x in t], k)
    rec = {**core.envelope("rehearsal_public"), "unit_costs": unit, "single_worker": single, "load_average_1min": load, "LOADED": load > float(cfg["thresholds"]["loaded_load_average"]), "seeds": "the registry's dry-rehearsal values (init 330392, dry stream and permutation seeds)", "probe_updates": updates, "charged_seconds": spent, "note": "descriptive records of this implementation on this machine; not an efficiency result"}
    core.write_record(run_dir / "r2.json", rec, overwrite=True)
    return rec


def read_json_(path: Path) -> dict[str, Any]:
    from arborlm.io import read_json

    return dict(read_json(path))


# --- R3: the counting rehearsal through the REGISTERED driver (R6) -----------------------------------------------------------------------------
DRY_OVERRIDE: dict[str, Any] = {"duration": {"checkpoints": [8, 16, 24, 32], "u_star": 32}, "setting": {"panel_chunks": 8}}


def dry_rate_table(rt: Mapping[str, Any], real_ck: Sequence[int], dry_ck: Sequence[int]) -> dict[str, Any]:
    out: dict[str, Any] = {"rates": {}, "edge": dict(rt["edge"])}
    for k, v in rt["rates"].items():
        out["rates"][k] = {str(d): v[str(r)] for r, d in zip(real_ck, dry_ck, strict=True)}
    return out


def dry_items(candidate_items: Mapping[str, Sequence[Mapping[str, Any]]], real_ck: Sequence[int], dry_ck: Sequence[int], cfg: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The one documented pure function that maps the candidate plan's items to the DRY profile: keep cell 0 only; checkpoints and run lengths mapped by position (real_ck[i] -> dry_ck[i], 0 stays 0); the initialisation
    seed is the registry's dry-rehearsal value and the stream seed its dry stream of the regime; the profile is ``dry``. Rates, arms, regimes, roles and read sets are the candidate's own."""
    to_dry = {0: 0, **{int(r): int(d) for r, d in zip(real_ck, dry_ck, strict=True)}}
    seeds = core.Seeds("dry", cfg)
    trains, kept = [], set()
    for t in candidate_items["train"]:
        if t["cell"] != 0:
            continue
        kept.add(t["id"])
        trains.append({**t, "profile": "dry", "max_update": to_dry[int(t["max_update"])], "snapshots": [to_dry[int(x)] for x in t["snapshots"]], "init_seed": seeds.init(0), "stream_seed": seeds.stream(0, core.REGIME_INDEX[t["regime"]])})
    evals = []
    for e in candidate_items["eval"]:
        if e["train"] in kept:
            u = to_dry[int(e["update"])]
            evals.append({**e, "profile": "dry", "update": u, "id": items.eval_id(e["arm"], e["regime"], e["rate"], e["cell"], u)})
    return {"train": trains, "eval": evals}


def run_r3(repo: Path, run_dir: Path, sealed_dir: Path, candidate: Plan, *, synthetic: bool) -> dict[str, Any]:
    """Every registered stage, through the registered driver's own functions (``stages.execute_stage``: gates, train, eval, analysis, report), against the CANDIDATE plan file: the candidate is loaded and verified
    (``verify_plan(candidate=True)``: its identities, items and caps), its items are mapped to the DRY profile by ``dry_items``, and the process is configured and the platform checked first, as the registered entry
    point does (R6: this would have caught B1). Item records and the DRY analysis go to the sealed directory; the public report renders the whitelist only (ruling 15)."""
    from . import gates
    from .stages import execute_stage

    calibration.require_outside_repo(sealed_dir, repo, allow_inside_repo=synthetic)
    gates.configure_process()
    bad = gates.platform_problems()
    if bad and not synthetic:
        raise StageRefused("refused: not the platform of record: " + "; ".join(bad))
    if candidate.mode == planmod.REGISTERED:
        planmod.verify_plan(candidate, repo, Path(candidate.data["run_dir"]), candidate=True)
    cfg = core.load_config(repo / core.CONFIG)
    real_ck = [int(x) for x in cfg["duration"]["checkpoints"]]
    over = copy.deepcopy(DRY_OVERRIDE) if not synthetic else deep_update(copy.deepcopy(SYNTHETIC_OVERRIDE), {"duration": {"checkpoints": [2, 4, 6, 8], "u_star": 8}})
    dry_ck = over["duration"]["checkpoints"]
    rt = dry_rate_table(candidate.rate_table, real_ck, dry_ck)
    dcfg = copy.deepcopy(dict(cfg))
    deep_update(dcfg, over)
    mapped = dry_items(candidate.data["items"], real_ck, dry_ck, dcfg) if candidate.data["items"]["train"] else items.registered_items(dcfg, rt, profile="dry", cells=[0])
    extra = {k: candidate.data[k] for k in ("data_manifest", "data_dir", "parent_suite", "parent_files") if k in candidate.data}
    plan = rehearsal_plan(repo, run_dir, "r3", over, mapped, rt, synthetic=synthetic, gate_profile="dry", extra=extra)
    assert plan.path is not None
    state = state_dir_of(run_dir, plan)
    ident = {"mode": "dry", "candidate_plan_file_sha256": file_sha256(candidate.path) if candidate.path else None}
    for st in ("gates", "train", "eval", "analysis", "report"):
        code = execute_stage(st, plan, repo, run_dir, plan.path, mode=plan.mode, identity=ident, items_dir=sealed_dir, state_dir=state, out_dir=sealed_dir, whitelist_only=True)
        if code != 0:
            raise core.EngineeringStop(f"ENGINEERING STOP — R3 stage {st} did not complete (exit {code})")
    rec = {"status": "COMPLETE", "plan_file_sha256": file_sha256(candidate.path) if candidate.path else None, "stages": ["gates", "train", "eval", "analysis", "report"], "driver": "stages.execute_stage (the registered driver's functions), DRY profile"}
    write_json(run_dir / "r3.json", rec)
    return rec


def cmd_rehearse(args: argparse.Namespace) -> int:
    from . import gates

    gates.configure_process()
    repo = Path(args.repo or core.repo_root())
    run_dir = Path(args.run_dir).resolve()
    planmod.require_ignored_run_dir(repo, run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    synthetic = args.phase == "synthetic"
    over = SYNTHETIC_OVERRIDE if synthetic else {}
    if args.data_manifest:
        from . import parents

        dm = Path(args.data_manifest).resolve()
        suite = Path(args.parent_suite).resolve()
        _EXTRA.update({"data_manifest": {"path": str(dm), "sha256": file_sha256(dm)}, "data_dir": str(dm.parent), "parent_suite": str(suite), "parent_files": parents.checkpoint_files(repo, suite)})
    if args.phase in ("r1", "synthetic"):
        if not args.sealed_dir:
            raise StageRefused("refused: r1 needs an explicit --sealed-dir (outside the repository, the lead's checkout and every git working tree; about 1.4-2.6 GB of snapshots)")
        run_r1(repo, run_dir, over, synthetic=synthetic, sealed_path=Path(args.sealed_dir) / "rehearsal_sealed.json")
        return 0
    if args.phase == "r2":
        run_r2(repo, run_dir, over, synthetic=False)
        return 0
    if not args.sealed_dir:
        raise StageRefused("refused: r3 needs --sealed-dir (outside the repository) for the DRY item records")
    cand = Plan.load(Path(args.plan) if args.plan else repo / core.PLAN)
    rec = run_r3(repo, run_dir, Path(args.sealed_dir).resolve(), cand, synthetic=False)
    pub_path = run_dir / "rehearsal_public.json"
    pub = core.read_record(pub_path, "rehearsal_public") if pub_path.is_file() else {**core.envelope("rehearsal_public"), "stages": {}}
    pub["stages"] = {**pub.get("stages", {}), "R3": {"status": "COMPLETE"}, "R2": {"status": "COMPLETE" if (run_dir / "r2.json").is_file() else "MISSING"}}
    pub["candidate"] = {"status": "COMPLETE", "plan_file_sha256": rec["plan_file_sha256"]}
    pub["caps_provisional"] = bool(cand.data.get("caps_provisional"))
    core.write_record(pub_path, pub, overwrite=True)
    return 0
