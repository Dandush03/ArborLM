# ruff: noqa: E501
"""P10IR stage driver (ADR-0029 sections 10, 11, 13): ``registered <stage>`` (the entry point the fixed launch scripts call), ``freeze``, ``generate-bridge``, ``rehearse``, ``work`` (the worker processes).

Registered stages, in order: ``gates-a1``, ``a1``, ``analysis``, ``report`` (group A1) and ``gates-a2``, ``a2-train``, ``a2``, ``confirm`` (group A2: R-CONFIRM against A1's frozen analysis record; A1's records are never rewritten). Run from the repository root:
``uv run --locked python -m studies.p10ir.stages <command> ...``. Registered stages take the run directory and the freeze commit and nothing else; every other value (items, caps, seeds, paths) comes from
``freeze/plan.json`` and ``configs/p10ir_routing.toml``. They REFUSE unless the working tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan
exists and every identity in it holds, and a committed Decision 2 for the stage's group (A1 or A2) names the freeze commit (``plan.check_preconditions``, ``plan.verify_plan``, ``plan.require_decision_2``).
Every stage derives its items from ``freeze/plan.json`` only. Stages are resumable: a PAUSED stage continues and finished reads are not recomputed; the stage manifest records PAUSED or COMPLETE.

Freeze procedure (ADR-0029 section 19 ruling 5; nothing here is a freeze until the human lead's commands write the files): tests and the audit pass; ``generate-bridge`` writes the bridge draws' manifests; the lead sets the caps
in the config (``caps-proposal``) and clears ``provisional``; ``candidate-plan`` writes ``freeze/plan.json``; ``rehearse`` (candidate plan file, synthetic, real-size cells, gates 1 and 2 on the registered checkpoints)
writes ``rehearsal.json`` whose candidate section names the plan file's SHA-256; ``freeze`` writes ``freeze/freeze_record.json`` only if the committed plan has that hash; the freeze commit is made; Decision 2 for A1 (and,
separately, for A2) is committed; then ``studies/p10ir/launch/*.sh``.
"""

import argparse
import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import analysis, core, gates, items, labels, report, runner, sealed, stages_io
from . import plan as planmod
from .plan import Plan, StageRefused

READ_STAGES = {"a1": core.STAGE_A1, "a2": core.STAGE_A2}
GROUP_STAGES = {core.STAGE_A1: ("gates-a1", "a1", "analysis", "report"), core.STAGE_A2: ("gates-a2", "a2-train", "a2")}
REHEARSAL_STAGES = ("gates-a1", "a1", "gates-a2", "a2-train", "a2", "analysis", "report", "confirm")


# --- context and tasks ---------------------------------------------------------------------------------------------------------------------------------
def repo_of(args: argparse.Namespace | None = None) -> Path:
    return Path(getattr(args, "repo", None) or core.repo_root())


def ctx_for(plan: Plan, run_dir: Path, *, run_sealed: bool, experiments_root: Path | None, config_path: Path | None = None) -> items.Ctx:
    d = plan.data
    manifests = {name: Path(rec["path"]) for name, rec in (d.get("draw_manifests") or {}).items()}
    sizes = dict(d.get("sizes") or {})
    return items.Ctx(
        mode=plan.mode, run_dir=run_dir, s1_run_dir=None if d.get("s1_run_dir") is None else Path(d["s1_run_dir"]), experiments_root=experiments_root, synthetic=bool(d.get("synthetic", False)),
        run_sealed=run_sealed, config_path=config_path, manifests=manifests, index_seeds=d.get("i64_seeds"), **({"sizes": sizes} if sizes else {}),
    )  # fmt: skip


def labels_of_stage(plan: Plan, stage: str) -> list[str]:
    """The cell labels of a read stage's items, in the plan's order (from the plan only)."""
    seen: list[str] = []
    for it in plan.items(READ_STAGES[stage]):
        if it["cell"] not in seen:
            seen.append(it["cell"])
    return seen


def bridge_cells(plan: Plan) -> dict[str, dict[str, Any]]:
    cells = plan.data.get("bridge_cells")
    if not isinstance(cells, dict):
        raise StageRefused("refused: the plan has no bridge cells")
    return cells


def task_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "tasks"


def make_tasks(stage: str, plan: Plan, run_dir: Path, plan_path: Path, args: argparse.Namespace, extra: Sequence[str]) -> list[runner.Task]:
    if stage in READ_STAGES:
        labels = labels_of_stage(plan, stage)
        kind = "reads"
    elif stage == "a2-train":
        labels = list(bridge_cells(plan))
        kind = "train"
    else:
        raise ValueError(f"{stage} has no pool tasks")
    tasks = []
    for label in labels:
        result = (run_dir / "A2" / "train" / "cells" / label / "train.json") if kind == "train" else task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.done.json"
        argv = (sys.executable, "-m", "studies.p10ir.stages", "work", kind, "--stage", stage, "--labels", label, "--run-dir", str(run_dir), "--plan", str(plan_path), "--mode", plan.mode, *extra)
        tasks.append(runner.Task(label, argv, result, task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.failed.json", task_dir(run_dir, stage) / f"{stages_io.safe_name(label)}.log"))
    return tasks


# --- workers --------------------------------------------------------------------------------------------------------------------------------------------
def work_reads(ctx: items.Ctx, plan: Plan, stage: str, labels: Sequence[str]) -> int:
    """Run (or resume) every item of ``labels`` of read stage ``stage`` (items from the plan only) and write the task's done mark."""
    digests = plan.data.get("checkpoint_digests") or {}
    todo = [it for it in plan.items(READ_STAGES[stage]) if it["cell"] in labels]
    unknown = [lab for lab in labels if lab not in {it["cell"] for it in todo}]
    if unknown:
        raise StageRefused(f"refused: {unknown[0]} is not a cell of the frozen plan's {stage} items")
    for label in labels:
        for it in [i for i in todo if i["cell"] == label]:
            items.run_item(ctx, it, digests)
        core.write_record(task_dir(ctx.run_dir, stage) / f"{stages_io.safe_name(label)}.done.json", {**core.envelope("item"), "stage": READ_STAGES[stage], "cell": label, "update": 1, "complete": True, "items": [i["id"] for i in todo if i["cell"] == label]}, overwrite=True)
    return 0


def work_gates12(ctx: items.Ctx, plan: Plan, labels: Sequence[str]) -> int:
    """Gates 1 and 2 on the checkpoints of the cells in ``labels`` (rehearsal on the registered checkpoints): one result file per item under ``<run>/gates12/``."""
    for it in [i for i in plan.items(core.STAGE_A1) if i["cell"] in labels]:
        path = ctx.run_dir / "gates12" / "items" / f"{stages_io.safe_name(it['id'])}.json"
        if not path.is_file():
            core.write_record(path, {**core.envelope("gate"), "name": "gates12", "gate": items.run_gates12_item(ctx, it)})
    for label in labels:
        core.write_record(ctx.run_dir / "gates12" / "tasks" / f"{stages_io.safe_name(label)}.done.json", {**core.envelope("item"), "stage": core.STAGE_A1, "cell": label, "update": 1, "complete": True}, overwrite=True)
    return 0


def work_train(ctx: items.Ctx, plan: Plan, labels: Sequence[str]) -> int:
    from . import adapter

    cells = bridge_cells(plan)
    for label in labels:
        if label not in cells:
            raise StageRefused(f"refused: {label} is not a bridge cell of the frozen plan")
        adapter.train_bridge_cell(ctx, label, cells)
    return 0


# --- pre-read gate stages -------------------------------------------------------------------------------------------------------------------------------
def gates_record_path(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "gates.json"


def require_gates_passed(run_dir: Path, stage: str) -> dict[str, Any]:
    """A read or training stage starts only when its ``gates-*`` stage ran and every gate passed (a failure of gate 1, 5, 6 or the identity gate stops the stage before any read or training)."""
    path = gates_record_path(run_dir, stage)
    if not path.is_file():
        raise StageRefused(f"refused: no gates record at {path}: run {stage} first")
    rec = core.read_record(path, "gates_record")
    if rec.get("passed") is not True:
        raise StageRefused(f"refused: the {stage} gates did not all pass; nothing is read or trained: {rec.get('failed')}")
    return rec


def rehearsal_record_of(plan: Plan) -> tuple[dict[str, Any] | None, str | None]:
    """The rehearsal record the freeze named (registered plans: through ``freeze/freeze_record.json``, which names the SHA-256 of the committed ``plan.json`` and of the rehearsal record) and the SHA-256
    of the plan file now in force (None for plans without one)."""
    if plan.path is None:
        return None, None
    plan_sha = file_sha256(plan.path)
    rec_path = plan.path.parent / "freeze_record.json"
    if plan.mode != planmod.REGISTERED or not rec_path.is_file():
        return None, plan_sha
    fr = read_json(rec_path)
    ref = fr.get("rehearsal") or {}
    p = Path(ref.get("path", ""))
    if fr.get("plan_file_sha256") != plan_sha or not p.is_file() or file_sha256(p) != ref.get("sha256"):
        raise StageRefused("refused: the freeze record's plan or rehearsal record does not hash to what it names")
    return core.read_record(p, "rehearsal"), plan_sha


def gate1_all(plan: Plan, ctx: items.Ctx, group: str, repo: Path) -> dict[str, Any]:
    """Gate 1 for the whole group, before any read (ruling 8; section 11: a failure stops the stage). Checkpoints (A1): every checkpoint's ``model.pt`` equals the ``model_sha256`` of its ``snapshot.json``, the entry
    of its cell's ``train.json`` and the digest frozen in the plan; every ``train.json`` hashes to its task's ``result_sha256`` in the committed P10-S1 train manifest; the draws' data manifests hash to
    P10-S1's frozen ``data_manifests``. Data: every draw of the group is regenerated by the fixed generator and equals its manifest's stream hashes, and each manifest file hashes to the plan's digest.
    The per-item check stays as a second line."""
    out: dict[str, Any] = {"failed": [], "checkpoints_checked": 0, "manifests": {}}

    def fail(msg: str) -> None:
        out["failed"].append(msg)

    for name, rec in (plan.data.get("draw_manifests") or {}).items():
        if group in rec["groups"]:
            p = Path(rec["path"])
            out["manifests"][name] = p.is_file() and file_sha256(p) == rec["sha256"]
            if not out["manifests"][name]:
                fail(f"manifest {name} does not hash to the plan's digest")
    if group == core.STAGE_A1:
        digests = plan.data.get("checkpoint_digests") or {}
        cells: set[str] = set()
        for it in plan.items(core.STAGE_A1):
            try:
                g = items.identity_gate(ctx, it, digests.get(f"{it['cell']}|{it['update']}"))
            except Exception as exc:  # noqa: BLE001
                g = {"passed": False, "error": type(exc).__name__}
            out["checkpoints_checked"] += 1
            cells.add(it["cell"])
            if g["passed"] is not True:
                fail(f"checkpoint {it['id']}: {g.get('error') or 'hashes disagree'}")
        if ctx.mode == planmod.REGISTERED and len(digests) != len(plan.items(core.STAGE_A1)):
            fail("the plan does not carry a digest for every checkpoint")
        tm = plan.data.get("p10s1_train_manifest")
        if tm:
            p = Path(tm["path"]) if Path(tm["path"]).is_absolute() else repo / tm["path"]
            if not p.is_file() or file_sha256(p) != tm["sha256"]:
                fail("the committed train manifest does not hash to the plan's digest")
            else:
                by_label = {t["label"]: t.get("result_sha256") for t in read_json(p)["tasks"]}
                assert ctx.s1_run_dir is not None
                for label in sorted(cells):
                    tj = ctx.s1_run_dir / "cells" / label / "train.json"
                    if not tj.is_file() or file_sha256(tj) != by_label.get(label):
                        fail(f"train.json of {label} does not hash to the committed train manifest's result_sha256")
        frozen = plan.data.get("p10s1_frozen_data_manifests")
        if frozen:
            for name, rec in (plan.data.get("draw_manifests") or {}).items():
                if group in rec["groups"] and frozen.get(name) != rec["sha256"]:
                    fail(f"data manifest {name} does not hash to P10-S1's frozen data_manifests entry")
    seen: set[tuple[Any, ...]] = set()
    for it in plan.items(group):
        key = (it["seed_name"], it["seed_base"], it["table_facts"], it["unseen"])
        if key in seen:
            continue
        seen.add(key)
        try:
            items.load_data(ctx, it, verify=True)  # regenerated by the fixed generator and compared with the manifest's stream hashes
        except Exception as exc:  # noqa: BLE001
            fail(f"draw {it['seed_name']}: {type(exc).__name__}: {str(exc)[:200]}")
    out["draws_regenerated"] = len(seen)
    out["passed"] = not out["failed"] and bool(out["manifests"])
    return out


def run_gate_stage(stage: str, plan: Plan, ctx: items.Ctx, run_dir: Path, *, repo: Path, run_checker: bool = True, adapter_identity: bool = True) -> dict[str, Any]:
    """``gates-a1`` (gate 1 for the manifests and the frozen digests, gate 5, gate 6) and ``gates-a2`` (the same for the bridge draws' manifests, and the adapter identity gate)."""
    group = core.STAGE_A1 if stage == "gates-a1" else core.STAGE_A2
    record: dict[str, Any] = {**core.envelope("gates_record"), "stage": stage, "mode": plan.mode, "platform": gates.platform_record(), "gates": {}, "failed": []}
    cfg = ctx.cfg()
    g1 = gate1_all(plan, ctx, group, repo)
    record["gates"]["gate1_identities"] = g1
    if plan.mode == planmod.REGISTERED:
        reh_record, plan_sha = rehearsal_record_of(plan)
        reh = gates.rehearsal_gate(reh_record, REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    else:
        reh = {"passed": True, "note": f"{plan.mode} mode"}
    record["gates"]["gate5_rehearsal"] = reh
    seeds = gates.seed_gate(cfg, run_checker=run_checker and plan.mode == planmod.REGISTERED)
    record["gates"]["gate6_seeds"] = seeds
    if group == core.STAGE_A2 and adapter_identity:
        from . import adapter

        cfg_s = cfg["seeds"]
        gate_cell = [int(x) for x in cfg_s["identity_gate_cell"]]
        s1_cells = [(arm, gate_cell[0], gate_cell[1], int(cfg_s["identity_gate_draw"]), int(cfg_s["p10s1_init_base"]) + int(cfg_s["identity_gate_draw"]), 8192, 49152) for arm in ("F-OQ", "T-OQ")]
        if plan.mode != planmod.REGISTERED:
            s1_cells = [tuple(c) for c in plan.data["identity_gate_cells"]]  # type: ignore[misc]
        record["gates"]["adapter_identity"] = adapter.identity_gate(
            ctx, run_dir / stage / "identity_work", cells=s1_cells, seeds_of=(core.p10s1_draw_seeds if plan.mode == planmod.REGISTERED else _mini_seeds_of(plan)), updates=[int(u) for u in plan.data.get("identity_gate_updates") or cfg_s["identity_gate_updates"]], cfg=cfg,
        )  # fmt: skip
    failed = [n for n, g in record["gates"].items() if g.get("passed") is False]
    record["failed"], record["passed"] = failed, not failed
    core.write_record(gates_record_path(run_dir, stage), record, overwrite=True)
    return record


def _mini_seeds_of(plan: Plan) -> Any:
    from studies.p10s1 import core as s1

    seeds = plan.data["identity_seed_sets"]
    return lambda d: s1.seed_set(seeds[str(d)]["name"], seeds[str(d)]["base"])


# --- charged time, caps -------------------------------------------------------------------------------------------------------------------------------------
def ledger_of(plan: Plan, run_dir: Path, ledger_root: Path | None, repo: Path | None = None) -> core.Ledger:
    """The charged-time ledger, in ``ledger_root`` or the run directory's parent. Where it would be inside the repository it must be git-ignored (audit N3): a ledger that dirties the tree would pause every later worker."""
    root = ledger_root or run_dir.parent
    path = root / ("P10IR-ledger.json" if plan.mode == planmod.REGISTERED else f"P10IR-{plan.mode}-{run_dir.name}-ledger.json")
    if repo is not None:
        planmod.require_ignored_path(repo, path)
    return core.Ledger(path, plan.total_cap_seconds())


def item_errors(run_dir: Path, stage: str | None = None) -> list[str]:
    """Items whose worker code raised (an ``item_error`` gate): code or data errors, counted apart from gate failures. Printed in the manifest, the analysis and the report."""
    out = []
    for p in sorted(run_dir.glob(f"{stage or 'A[12]'}/items/*/item.json")):
        rec = core.read_record(p, "item")
        if "item_error" in rec.get("gates", {}):
            out.append(f"{p.parent.name}: {rec['gates']['item_error'].get('error')}")
    return out


def stage_cap_seconds(plan: Plan, stage: str, ledger: core.Ledger) -> float:
    """The stage's wall-clock cap: what remains of its group's cap and of the total (section 12: a stop on a resource cap is PAUSED)."""
    key = planmod.STAGE_CAP_KEY[stage]
    group_stages = [s for s, k in planmod.STAGE_CAP_KEY.items() if k == key]
    spent = sum(ledger.charged(s) for s in group_stages)
    return max(0.0, min(plan.cap_seconds(key) - spent, ledger.remaining()))


# --- executing a stage ----------------------------------------------------------------------------------------------------------------------------------------
def execute_stage(stage: str, plan: Plan, ctx: items.Ctx, run_dir: Path, plan_path: Path, *, repo: Path, workers: int, inline: bool, extra_worker_args: Sequence[str] = (), ledger_root: Path | None = None, run_checker: bool = True, adapter_identity: bool = True) -> dict[str, Any]:
    """One stage, resumable, from the plan only. ``inline`` runs the workers in this process (rehearsal's synthetic phase and tests); otherwise as subprocesses under ``runner.run_tasks``."""
    cfg = ctx.cfg()
    ledger = ledger_of(plan, run_dir, ledger_root, repo)
    cap = stage_cap_seconds(plan, stage, ledger)
    ledger.require_room(stage, max(cap, 1.0) if cap > 0 else 0.0)
    prior = runner.read_manifest(run_dir, stage)
    if prior is not None and prior["status"] == "COMPLETE":
        raise StageRefused(f"refused: {runner.manifest_path(run_dir, stage)} is COMPLETE; a completed stage is never rewritten")
    started = datetime.now(UTC).isoformat()
    began = time.monotonic()
    identity = {"plan_sha256": plan.sha256(), "config_sha256": plan.data["config_sha256"], "platform": gates.platform_record()}
    caps = {"stage_seconds": cap, "rss_worker_bytes": float(cfg["resources"]["rss_worker_bytes"]), "rss_aggregate_bytes": float(cfg["resources"]["rss_aggregate_bytes"])}
    if stage.startswith("gates-"):
        rec = run_gate_stage(stage, plan, ctx, run_dir, repo=repo, run_checker=run_checker, adapter_identity=adapter_identity)
        outcomes = {stage: {"status": runner.COMPLETED if rec["passed"] else runner.FAILED, "seconds": time.monotonic() - began, "peak_rss_bytes": 0, "reason": None if rec["passed"] else f"gates failed: {rec['failed']}"}}
    elif stage in ("analysis", "report", "confirm"):
        outcomes = {stage: {"status": runner.COMPLETED, "seconds": 0.0, "peak_rss_bytes": 0}}
        if stage == "analysis":
            m1 = runner.read_manifest(run_dir, "a1")
            if m1 is None or m1["status"] != "COMPLETE":
                raise StageRefused("refused: a1 is not COMPLETE: the analysis needs every A1 read")
        if stage == "confirm":
            for needed in ("a2", "analysis"):
                m = runner.read_manifest(run_dir, needed)
                if m is None or m["status"] != "COMPLETE":
                    raise StageRefused(f"refused: {needed} is not COMPLETE: the confirmation needs A2's reads and A1's frozen analysis record")
        {"analysis": run_analysis, "report": run_report, "confirm": run_confirm}[stage](plan, ctx, run_dir)
        outcomes[stage]["seconds"] = time.monotonic() - began
    else:
        if stage in ("a1", "a2-train"):
            require_gates_passed(run_dir, "gates-a1" if stage == "a1" else "gates-a2")
        if stage == "a2":
            require_gates_passed(run_dir, "gates-a2")
            m = runner.read_manifest(run_dir, "a2-train")
            if m is None or m["status"] != "COMPLETE":
                raise StageRefused("refused: a2-train is not COMPLETE: the bridge checkpoints do not all exist")
        extra = list(extra_worker_args)
        tasks = make_tasks(stage, plan, run_dir, plan_path, argparse.Namespace(), extra)
        if inline:
            outcomes = {}
            for t in tasks:
                if t.result_path.is_file():
                    outcomes[t.label] = {"status": runner.COMPLETED, "seconds": 0.0, "skipped": "result exists", "peak_rss_bytes": 0}
                    continue
                t0 = time.monotonic()
                if stage == "a2-train":
                    work_train(ctx, plan, [t.label])
                else:
                    work_reads(ctx, plan, stage, [t.label])
                outcomes[t.label] = {"status": runner.COMPLETED, "seconds": time.monotonic() - t0, "peak_rss_bytes": 0}
        else:
            outcomes, _ = runner.run_tasks(tasks, workers=workers, cap_seconds=cap, rss_worker_bytes=int(cfg["resources"]["rss_worker_bytes"]), rss_aggregate_bytes=int(cfg["resources"]["rss_aggregate_bytes"]), env={"PYTHONPATH": str(repo)})
    seconds = time.monotonic() - began
    ledger.charge(stage, run_dir.name, seconds)
    errors = item_errors(run_dir, READ_STAGES[stage]) if stage in READ_STAGES else []
    manifest = runner.write_manifest(run_dir, stage, plan.mode, outcomes, seconds, identity=identity, started=started, caps=caps, extra={"item_errors": len(errors), "item_error_list": errors[:50], "clean": not errors})
    if errors:
        print(f"WARNING: {len(errors)} item(s) raised in worker code (item_error): the stage is not clean; see the manifest")
    print(json.dumps({"stage": stage, "status": manifest["status"], "tasks": len(outcomes), "charged_seconds": round(seconds, 1)}))
    return manifest


# --- analysis and report ----------------------------------------------------------------------------------------------------------------------------------------
def _context(plan: Plan, ctx: items.Ctx) -> dict[str, Any]:
    """D-OQ's a_use at the same cells from P10-S1's records (descriptive; the dense map has no retrieval to change, section 7)."""
    out: dict[str, Any] = {}
    if ctx.s1_run_dir is None:
        return out
    from studies.p10s1 import core as s1

    for entry in plan.data.get("context", {}).get("dense", []):
        vals = []
        for lab in entry["labels"]:
            try:
                c = sealed.counts(ctx.s1_run_dir, lab, int(entry["update"]), "main")
                vals.append(sum(c[p]["useful"] for p in sealed.PANELS) / sum(c[p]["n"] for p in sealed.PANELS))
            except sealed.SealedMissing:
                continue
        out[f"D-OQ a_use, {entry['cell_name']} at {entry['checkpoint']} (mean over {len(vals)} replicates; P10-S1's recorded counts)"] = None if not vals else sum(vals) / len(vals)
    _ = s1
    return out


def _plateau(plan: Plan, ctx: items.Ctx) -> dict[str, dict[str, list[Any]]]:
    out: dict[str, dict[str, list[Any]]] = {}
    if ctx.s1_run_dir is None:
        return out
    for cell_name, arms in (plan.data.get("plateau") or {}).items():
        out[cell_name] = {}
        for arm_key, per_draw in arms.items():
            series: list[Any] = []
            for lab_updates in per_draw:
                try:
                    series.append(sealed.information_series(ctx.s1_run_dir, lab_updates["label"], [int(u) for u in lab_updates["updates"]]) if lab_updates["updates"] else None)
                except sealed.SealedMissing:
                    series.append(None)
            out[cell_name][arm_key] = series
    return out


def analysis_path(run_dir: Path) -> Path:
    return run_dir / "analysis" / "analysis.json"


def run_analysis(plan: Plan, ctx: items.Ctx, run_dir: Path) -> dict[str, Any]:
    """A1's analysis, from the plan's own items and labels (never the config's). It never looks at A2: R-CONFIRM is the separate ``confirm`` stage's (ruling 9), and this record is never rewritten."""
    from . import registry

    cfg = ctx.cfg()
    reg1 = registry.load(run_dir, core.STAGE_A1)
    a1 = analysis.analyze_stage(
        reg1, core.STAGE_A1, cfg, plateau=_plateau(plan, ctx), context=_context(plan, ctx), seal_broken=bool(plan.data.get("seal", {}).get("broken")), specs=_specs_of(plan, core.STAGE_A1),
        label_of=analysis.label_of_from_items(plan.items(core.STAGE_A1)), i64_seeds=ctx.i64(cfg),
    )  # fmt: skip
    full = analysis.analyze_all(a1, None, a2_complete=False)
    full["item_errors"] = item_errors(run_dir, core.STAGE_A1)
    full["kind"] = "analysis"
    core.write_record(analysis_path(run_dir), {**core.envelope("analysis"), **full})
    return full


def confirm_path(run_dir: Path) -> Path:
    return run_dir / "confirm" / "confirm.json"


def run_confirm(plan: Plan, ctx: items.Ctx, run_dir: Path) -> dict[str, Any]:
    """The ``confirm`` stage (group A2, ruling 9): A2's analysis, and R-CONFIRM-TREE and R-CONFIRM-INDEX against A1's FROZEN analysis record (read from disk; its SHA-256 is recorded). It writes its own record and
    report section and never rewrites A1's."""
    from . import registry

    a1_path = analysis_path(run_dir)
    if not a1_path.is_file():
        raise StageRefused("refused: no A1 analysis record to confirm against")
    a1 = read_json(a1_path)
    cfg = ctx.cfg()
    a2 = analysis.analyze_stage(
        registry.load(run_dir, core.STAGE_A2), core.STAGE_A2, cfg, specs=_specs_of(plan, core.STAGE_A2), label_of=analysis.label_of_from_items(plan.items(core.STAGE_A2)), i64_seeds=ctx.i64(cfg),
    )  # fmt: skip
    confirm = labels.r_confirm(labels.diagnosis_from_json(a1["A1"]["r_diagnosis"]), a2["_diagnosis_object"], a2_complete=True)
    record = {
        **core.envelope("confirm"), "a1_analysis_sha256": file_sha256(a1_path), "A2": analysis.public(a2), "r_confirm": confirm,
        "statement_allowed": {"caused_by_a_named_factor_at_read_time": labels.may_say_cause(confirm), "training_time_causes": False}, "item_errors": item_errors(run_dir, core.STAGE_A2),
    }  # fmt: skip
    core.write_record(confirm_path(run_dir), record)
    note = f"Mode: {plan.mode}. Plan SHA-256 {plan.sha256()}."
    out = run_dir / "confirm" / "REPORT_CONFIRM.md"
    out.write_text(report.render_confirm(record, note), encoding="utf-8")
    return record


def _specs_of(plan: Plan, stage: str) -> list[core.CellSpec]:
    """The cell specs of a stage as the plan's items name them (from the plan only)."""
    seen: dict[tuple[int, int], core.CellSpec] = {}
    for it in plan.items(stage):
        key = (it["facts"], it["slots"])
        if key not in seen:
            cps = sorted({i["update"] for i in plan.items(stage) if (i["facts"], i["slots"]) == key})
            traj = [u for u in cps if u not in (it["u_p"], it["run"])]
            seen[key] = core.CellSpec(it["facts"], it["slots"], it["role"], it["u_p"], it["run"], (traj[0], traj[1]) if len(traj) == 2 else (it["u_p"], it["run"]))
    return list(seen.values())


def run_report(plan: Plan, ctx: items.Ctx, run_dir: Path) -> Path:
    path = analysis_path(run_dir)
    if not path.is_file():
        raise StageRefused("refused: no analysis.json: run the analysis first")
    full = read_json(path)
    note = f"Mode: {plan.mode}. Plan SHA-256 {plan.sha256()}. Platform: {gates.platform_record()['platform']}."
    out = run_dir / "report" / "REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.render(full, note), encoding="utf-8")
    return out


# --- registered entry point ---------------------------------------------------------------------------------------------------------------------------------
def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name. Free arguments: the run directory and the freeze commit, nothing else."""
    if args.name not in planmod.REGISTERED_STAGES:
        raise StageRefused(f"refused: unknown registered stage {args.name!r}")
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
    planmod.require_ignored_run_dir(repo, run_dir)
    plan = planmod.load_registered_plan(repo)
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, args.freeze_commit, planmod.STAGE_GROUP[args.name])
    ctx = ctx_for(plan, run_dir, run_sealed=True, experiments_root=_experiments_root())
    manifest = execute_stage(args.name, plan, ctx, run_dir, repo / core.PLAN, repo=repo, workers=int(ctx.cfg()["resources"]["workers"]), inline=False, extra_worker_args=("--freeze-commit", args.freeze_commit, "--run-sealed"))
    return 0 if manifest["status"] != "FAILED" else 1


def _experiments_root() -> Path:
    from studies.p9 import core as p9core

    return Path(p9core.default_experiments_root())


# --- worker entry point --------------------------------------------------------------------------------------------------------------------------------------
def cmd_work(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    run_dir = Path(args.run_dir)
    plan = Plan.load(Path(args.plan))
    if plan.mode == planmod.REGISTERED:  # a registered worker re-checks the freeze, the plan and Decision 2 itself
        if Path(args.plan) != repo / core.PLAN:
            raise StageRefused(f"refused: the registered plan is {core.PLAN}")
        planmod.check_preconditions(planmod.REGISTERED, repo, args.freeze_commit)
        planmod.require_ignored_run_dir(repo, run_dir)
        planmod.verify_plan(plan, repo, run_dir)
        planmod.require_decision_2(repo, args.freeze_commit, planmod.STAGE_GROUP[args.stage])
    if args.run_sealed and plan.mode != planmod.REGISTERED:  # audit A8: a sealed value is compared only in a registered run, or against a rehearsal's own miniature records
        s1 = plan.data.get("s1_run_dir")
        if s1 is None or not Path(s1).resolve().is_relative_to(run_dir.resolve()):
            raise StageRefused("refused: --run-sealed outside registered mode needs P10-S1's records to be the rehearsal's own miniature (inside the run directory)")
    ctx = ctx_for(plan, run_dir, run_sealed=bool(args.run_sealed), experiments_root=None if plan.data.get("synthetic") else _experiments_root())
    labels = [s for s in args.labels.split(",") if s]
    if args.kind == "train":
        return work_train(ctx, plan, labels)
    if args.kind == "gates12":
        return work_gates12(ctx, plan, labels)
    return work_reads(ctx, plan, args.stage, labels)


# --- parser ----------------------------------------------------------------------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("registered", help="one registered stage (run dir and freeze commit only)")
    reg.add_argument("name", choices=planmod.REGISTERED_STAGES)
    reg.add_argument("--run-dir", required=True)
    reg.add_argument("--freeze-commit")
    reg.add_argument("--repo")
    w = sub.add_parser("work", help="worker process of a registered stage or of the rehearsal")
    w.add_argument("kind", choices=("reads", "train", "gates12"))
    w.add_argument("--stage", required=True)
    w.add_argument("--labels", required=True)
    w.add_argument("--run-dir", required=True)
    w.add_argument("--plan", required=True)
    w.add_argument("--mode", required=True, choices=planmod.MODES)
    w.add_argument("--freeze-commit")
    w.add_argument("--run-sealed", action="store_true")
    w.add_argument("--repo")
    from . import freeze as freezemod

    freezemod.add_commands(sub)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("registered", "work"):
            from studies.p10s1 import train as s1train

            s1train.configure()  # one thread, one interop thread, deterministic algorithms: the platform of record's settings (section 13) are set before the platform is checked
        if args.command == "registered":
            return cmd_registered(args)
        if args.command == "work":
            return cmd_work(args)
        from . import freeze as freezemod

        return freezemod.dispatch(args)
    except StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return runner.IDENTITY_EXIT if args.command == "work" else 2  # a worker's refusal is PAUSED — IDENTITY (resumable), not a failure
    except core.LedgerRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
